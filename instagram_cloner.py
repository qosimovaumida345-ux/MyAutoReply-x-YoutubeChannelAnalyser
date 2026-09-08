"""
Instagram Account Auto-Cloner & Reposter.
Belgilangan Instagram profildan yangi Reel-larni avtomatik yuklab olish,
8-qatlamli sun'iy intellektual/texnik unikalizatsiya (anti-copyright) qo'llash
va ulangan YouTube kanalga avtomatik yuklash tizimi.
"""

import os
import shutil
import asyncio
import logging
import yt_dlp
import database as db
from autopost import upload_to_youtube
from instagram_processor import get_ffmpeg_binary
from custom_emojis import ce

logger = logging.getLogger(__name__)

def add_instagram_target(tg_user_id: int, ig_username: str, interval_mins: int = 60) -> bool:
    """Foydalanuvchi kuzatuv ro'yxatiga Instagram profilini qo'shish"""
    clean_username = ig_username.strip().lstrip("@").lower()
    return db.add_ig_sync_channel(tg_user_id, clean_username, interval_mins)

def get_instagram_targets(tg_user_id: int) -> list:
    """Foydalanuvchining barcha kuzatilayotgan Instagram profillari"""
    return db.get_user_ig_sync_channels(tg_user_id)

def remove_instagram_target(tg_user_id: int, ig_username: str) -> bool:
    """Kuzatuvdan chiqarish"""
    clean_username = ig_username.strip().lstrip("@").lower()
    return db.remove_ig_sync_channel(tg_user_id, clean_username)

def scrape_instagram_recent_posts(ig_username: str, max_posts: int = 5) -> list:
    """
    Instagram profilidan oxirgi postlar/reellarni login talab qilmasdan scrape qilish.
    """
    clean_username = ig_username.strip().lstrip("@").lower()
    urls_to_try = [
        f"https://www.instagram.com/{clean_username}/reels/",
        f"https://www.instagram.com/{clean_username}/"
    ]
    
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "playlistend": max_posts,
    }

    found_entries = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for u in urls_to_try:
            try:
                res = ydl.extract_info(u, download=False)
                if res and "entries" in res:
                    for item in res["entries"]:
                        if item:
                            found_entries.append(item)
                    if found_entries:
                        break
            except Exception as e:
                logger.debug(f"IG scrape xatosi ({u}): {e}")
                continue

    # Tartiblash va deduplikatsiya
    results = []
    seen_ids = set()
    for entry in found_entries:
        pid = entry.get("id") or entry.get("url", "").split("/")[-2]
        if not pid or pid in seen_ids:
            continue
        seen_ids.add(pid)
        post_url = entry.get("url")
        if not post_url or not post_url.startswith("http"):
            post_url = f"https://www.instagram.com/reel/{pid}/"
        results.append({
            "post_id": str(pid),
            "url": post_url,
            "title": entry.get("title") or f"Viral Reel #{pid}"
        })
        if len(results) >= max_posts:
            break

    return results

async def download_and_8layer_uniqueify(post_url: str, post_id: str, output_dir: str = "downloads") -> dict:
    """
    Instagram Reel-ni yuklab oladi va unga 8-qatlamli unikalizatsiya qo'llaydi:
    1. Video Eq (kontrast +3%, to'yinganlik +4%)
    2. Micro-crop 99.5% (tasvir barmoq izini buzish)
    3. Scale va 9:16 vertical pad (1080x1920)
    4. Video Speed (1.02x tezlashtirish)
    5. Audio Pitch shift (1.015x chastota siljishi)
    6. Audio Speed (1.02x temp)
    7. Highpass/Lowpass filtering (ultratovush / infratovush tebranishlarini kesish)
    8. To'liq metadata tozalash (-map_metadata -1 va +bitexact)
    """
    os.makedirs(output_dir, exist_ok=True)
    raw_path = os.path.join(output_dir, f"ig_raw_{post_id}.mp4")
    clean_path = os.path.join(output_dir, f"ig_clean_{post_id}.mp4")

    ydl_opts = {
        "outtmpl": raw_path,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post_url, download=True)
            return info

    info = await asyncio.to_thread(_download)
    if not os.path.exists(raw_path):
        # Ba'zan fayl boshqa kengaytmada tushgan bo'lishi mumkin
        base, _ = os.path.splitext(raw_path)
        for ext in [".mp4", ".mkv", ".webm"]:
            if os.path.exists(base + ext):
                raw_path = base + ext
                break

    ffmpeg_exe = get_ffmpeg_binary()

    # 8-Qatlamli filtr zanjiri
    vf_chain = (
        "eq=contrast=1.03:brightness=0.01:saturation=1.04,"
        "crop=in_w*0.995:in_h*0.995,"
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        "setpts=PTS/1.02"
    )
    af_chain = (
        "highpass=f=25,lowpass=f=19500,"
        "asetrate=44100*1.015,aresample=44100,"
        "atempo=1.02"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", raw_path,
        "-vf", vf_chain,
        "-af", af_chain,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-map_metadata", "-1",
        "-fflags", "+bitexact",
        clean_path
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
    except Exception as e:
        logger.error(f"FFmpeg 8-layer uniqueify xatosi: {e}")

    final_file = clean_path if (os.path.exists(clean_path) and os.path.getsize(clean_path) > 1000) else raw_path

    # Xom faylni tozalash
    if final_file != raw_path and os.path.exists(raw_path):
        try: os.remove(raw_path)
        except Exception: pass

    title = info.get("title") or info.get("description") or f"Viral Reel #{post_id}"
    clean_title = title.split("\n")[0][:90].strip() or f"Viral Reel #{post_id}"

    return {
        "file_path": final_file,
        "title": f"{clean_title} #Shorts",
        "description": f"{title}\n\n#shorts #reels #viral #trending",
        "post_id": post_id
    }

async def sync_instagram_account_now(tg_user_id: int, ig_username: str, app=None, chat_id=None) -> dict:
    """
    Belgilangan Instagram profildan barcha yangi videolarni tekshirib,
    ulangan YouTube kanalga avtomat yuklash.
    """
    clean_username = ig_username.strip().lstrip("@").lower()
    targets = get_instagram_targets(tg_user_id)
    target = next((t for t in targets if t["ig_username"].lower() == clean_username), None)
    if not target:
        return {"status": "error", "message": f"Kuzatilayotgan @{clean_username} profili topilmadi."}

    sync_channel_id = target["id"]

    # Foydalanuvchining YouTube kanali ulanmagan bo'lsa xabar berish
    yt_conn = db.get_yt_connection(tg_user_id)
    if not yt_conn or not yt_conn.get("access_token"):
        return {"status": "error", "message": "YouTube kanalingiz ulanmagan! Avval /ytlogin orqali ulang."}

    if app and chat_id:
        try: await app.send_message(chat_id, f"🔍 `@{clean_username} profili tekshirilmoqda...`")
        except: pass

    posts = await asyncio.to_thread(scrape_instagram_recent_posts, clean_username, 4)
    if not posts:
        return {"status": "ok", "message": f"@{clean_username} profilida yangi postlar topilmadi.", "synced": 0}

    synced_count = 0
    for p in posts:
        pid = p["post_id"]
        # Allaqachon yuklanganmi?
        if db.is_ig_post_synced(sync_channel_id, pid):
            continue

        if app and chat_id:
            try: await app.send_message(chat_id, f"{ce('DOWNLOAD')} <code>Yangi Reel topildi (#{pid}). 8-qatlamli unikalizatsiya va YouTube ga yuklash boshlandi...</code>")
            except: pass

        try:
            processed = await download_and_8layer_uniqueify(p["url"], pid)
            video_file = processed["file_path"]

            # YouTube ga yuklash
            yt_id = await asyncio.to_thread(
                upload_to_youtube,
                video_file,
                processed["title"],
                processed["description"],
                yt_conn
            )

            # Bazada belgilash
            db.record_ig_synced_post(sync_channel_id, pid, p["url"], yt_id, status="synced")
            synced_count += 1

            if app and chat_id:
                try:
                    yt_url = f"https://youtu.be/{yt_id}"
                    await app.send_message(
                        chat_id,
                        f"{ce('CHECK')} <b>Muvaffaqiyatli yuklandi!</b>\n"
                        f"{ce('VIDEO')} <b>Sarlavha:</b> {processed['title']}\n"
                        f"{ce('LINK')} <b>YouTube havola:</b> <a href=\"{yt_url}\">Ko'rish</a>"
                    )
                except: pass

            # Faylni o'chirish
            if os.path.exists(video_file):
                try: os.remove(video_file)
                except: pass

        except Exception as upload_err:
            logger.error(f"IG Reel #{pid} yuklashda xato: {upload_err}")
            if app and chat_id:
                try: await app.send_message(chat_id, f"{ce('WARN')} Reel #{pid} yuklashda xatolik: {upload_err}")
                except: pass

    db.update_ig_sync_timestamp(sync_channel_id)
    return {"status": "ok", "message": f"Tekshiruv yakunlandi. {synced_count} ta yangi video YouTube ga yuklandi.", "synced": synced_count}

async def start_instagram_sync_daemon(app, interval_seconds: int = 1800):
    """Orqa fonda barcha faol profillarni tekshirib boruvchi sikl"""
    while True:
        try:
            active_channels = db.get_all_active_ig_sync_channels()
            for ch in active_channels:
                try:
                    await sync_instagram_account_now(ch["tg_user_id"], ch["ig_username"], app=app, chat_id=ch["tg_user_id"])
                except Exception as inner_e:
                    logger.error(f"IG daemon error for channel {ch.get('ig_username')}: {inner_e}")
        except Exception as e:
            logger.error(f"IG sync daemon fatal error: {e}")
        await asyncio.sleep(interval_seconds)
