"""
Instagram Account Auto-Cloner & Reposter.
Belgilangan Instagram profildan barcha Reel-larni avtomatik kuzatish,
8-qatlamli sun'iy intellektual va texnik unikalizatsiya (anti-copyright) qo'llash,
qat'iy deduplikatsiya (hech qachon ikkita bir xil videoni qayta yuklamaslik)
va ulangan YouTube kanalga kunlik maksimal limitgacha avtomatik yuklash tizimi.
"""

import os
import re
import sys
import shutil
import asyncio
import logging
import urllib.request
from datetime import datetime, timezone

import yt_dlp
import database as db
from autopost import upload_to_youtube
from instagram_processor import get_ffmpeg_binary
from custom_emojis import ce

logger = logging.getLogger(__name__)


def clean_instagram_target(target: str) -> str:
    """
    Foydalanuvchi kiritgan har qanday Instagram manzilini toza username ga aylantiradi.
    Masalan:
      - '@cristiano' -> 'cristiano'
      - 'https://www.instagram.com/cristiano/' -> 'cristiano'
      - 'https://instagram.com/cristiano/reels' -> 'cristiano'
    """
    clean = str(target).strip()
    if "instagram.com/" in clean.lower():
        # URL dan username ni ajratib olish
        try:
            after = clean.lower().split("instagram.com/")[1]
            parts = [p for p in after.split("/") if p and p not in ("reels", "p", "reel", "stories")]
            if parts:
                clean = parts[0].split("?")[0]
        except Exception:
            pass
    clean = clean.lstrip("@").strip().lower()
    # Harflar, raqamlar, pastki chiziq va nuqtalarni qoldirish
    clean = re.sub(r"[^a-z0-9_.]", "", clean)
    return clean


def add_instagram_target(tg_user_id: int, ig_username: str, interval_mins: int = 60) -> bool:
    """Foydalanuvchi kuzatuv ro'yxatiga Instagram profilini qo'shish"""
    clean_username = clean_instagram_target(ig_username)
    if not clean_username:
        return False
    return db.add_ig_sync_channel(tg_user_id, clean_username, interval_mins)


def get_instagram_targets(tg_user_id: int) -> list:
    """Foydalanuvchining barcha kuzatilayotgan Instagram profillari"""
    return db.get_user_ig_sync_channels(tg_user_id)


def remove_instagram_target(tg_user_id: int, ig_username: str) -> bool:
    """Kuzatuvdan chiqarish"""
    clean_username = clean_instagram_target(ig_username)
    return db.remove_ig_sync_channel(tg_user_id, clean_username)


def scrape_instagram_recent_posts(ig_username: str, max_posts: int = 100) -> list:
    """
    Instagram profilidan barcha mavjud postlar/reellarni login talab qilmasdan scrape qilish.
    Maksimal limitgacha (default: 100 ta video) ro'yxatni chiqaradi.
    """
    clean_username = clean_instagram_target(ig_username)
    if not clean_username:
        return []

    urls_to_try = [
        f"https://www.instagram.com/{clean_username}/reels/",
        f"https://www.instagram.com/{clean_username}/"
    ]

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "playlistend": max_posts,
        "ignoreerrors": True,
    }

    found_entries = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for u in urls_to_try:
            try:
                res = ydl.extract_info(u, download=False)
                if res and "entries" in res and res["entries"]:
                    for item in res["entries"]:
                        if item:
                            found_entries.append(item)
                    if found_entries:
                        break
            except Exception as e:
                logger.debug(f"IG yt-dlp scrape xatosi ({u}): {e}")
                continue

    # Tartiblash va deduplikatsiya
    results = []
    seen_ids = set()

    for entry in found_entries:
        pid = entry.get("id")
        if not pid and entry.get("url"):
            # URL dan post ID / shortcode ni topish
            m = re.search(r"/(?:reel|p)/([A-Za-z0-9_-]+)", entry.get("url", ""))
            if m:
                pid = m.group(1)

        if not pid or pid in seen_ids:
            continue

        seen_ids.add(pid)
        post_url = entry.get("url")
        if not post_url or not post_url.startswith("http"):
            post_url = f"https://www.instagram.com/reel/{pid}/"

        raw_title = entry.get("title") or f"Viral Reel #{pid}"
        results.append({
            "post_id": str(pid),
            "url": post_url,
            "title": raw_title
        })
        if len(results) >= max_posts:
            break

    # Fallback: Agar yt_dlp orqali topilmasa, ochiq HTML orqali shortcode larni qidirish
    if not results:
        try:
            req = urllib.request.Request(
                f"https://www.instagram.com/{clean_username}/reels/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")
                shortcodes = re.findall(r'/(?:p|reel)/([A-Za-z0-9_-]{10,12})/?', html_text)
                for sc in shortcodes:
                    if sc not in seen_ids:
                        seen_ids.add(sc)
                        results.append({
                            "post_id": str(sc),
                            "url": f"https://www.instagram.com/reel/{sc}/",
                            "title": f"Reel #{sc}"
                        })
                        if len(results) >= max_posts:
                            break
        except Exception as fb_err:
            logger.debug(f"IG fallback scrape error for {clean_username}: {fb_err}")

    return results


async def download_and_8layer_uniqueify(post_url: str, post_id: str, output_dir: str = "downloads") -> dict:
    """
    Instagram Reel-ni yuklab oladi va unga 8-qatlamli unikalizatsiya qo'llaydi:
    1. Video Eq (kontrast +3%, yorug'lik +1%, to'yinganlik +4%)
    2. Micro-crop 99.5% (tasvir barmoq izini buzish)
    3. Scale va 9:16 vertical pad (1080x1920)
    4. Video Speed (1.02x tezlashtirish)
    5. Audio Pitch shift (1.015x chastota siljishi)
    6. Audio Speed (1.02x temp)
    7. Highpass/Lowpass filtering (ultratovush / infratovush tebranishlarini tozalash)
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
        "nocheckcertificate": True,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post_url, download=True)
            return info

    info = await asyncio.to_thread(_download)
    if not os.path.exists(raw_path):
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

    title = (info.get("title") or info.get("description") or f"Viral Reel #{post_id}").strip()
    clean_title = title.split("\n")[0][:90].strip() or f"Viral Reel #{post_id}"

    return {
        "file_path": final_file,
        "title": f"{clean_title} #Shorts",
        "description": f"{title}\n\n#shorts #reels #viral #trending #autopost",
        "post_id": post_id
    }


async def sync_instagram_account_now(tg_user_id: int, ig_username: str, app=None, chat_id=None, force: bool = False) -> dict:
    """
    Belgilangan Instagram profildan barcha videolarni tekshirib:
    1. Qat'iy deduplikatsiya: Ilgari biror marta yuklangan videolarni 100% chetlab o'tadi.
    2. 8-qatlamli unikalizatsiya bilan YouTube kanalga yuklaydi.
    3. Kunlik maksimal limitgacha (YouTube 'uploadLimitExceeded' yoki quota limit berguncha) uzluksiz yuklaydi.
    4. Limit to'lganda avtomatik to'xtaydi, foydalanuvchiga xabar beradi va qolganlarini ertangi kunga qoldiradi.
    """
    clean_username = clean_instagram_target(ig_username)
    targets = get_instagram_targets(tg_user_id)
    target = next((t for t in targets if t["ig_username"].lower() == clean_username), None)
    if not target:
        return {"status": "error", "message": f"Kuzatilayotgan @{clean_username} profili topilmadi."}

    sync_channel_id = target["id"]

    # 1. YouTube OAuth ulanishini tekshirish
    yt_conn = db.get_yt_connection(tg_user_id)
    if not yt_conn or not yt_conn.get("access_token"):
        return {"status": "error", "message": "YouTube kanalingiz ulanmagan! Avval /ytlogin orqali kanalingizni ulang."}

    # 2. Yangi kun kelgan bo'lsa, limit holatini avtomatik tiklash
    db.reset_ig_sync_daily_limit_if_new_day(sync_channel_id)

    # 3. Agar bugungi limit to'lgan bo'lsa va majburiy (force) bo'lmasa — kutish
    if not force and db.is_ig_sync_daily_limit_hit_today(sync_channel_id):
        msg = (
            f"⚠️ <b>YouTube Kunlik Yuklash Limiti Bugun To'lgan!</b>\n\n"
            f"@{clean_username} uchun YouTube kanalingizda bugungi kunlik yuklash limiti tugagan.\n"
            f"⏰ <b>Avtomatik davom etish:</b> Ertaga 00:00 UTC dan keyin tizim avtomatik davom ettiradi."
        )
        if app and chat_id:
            try: await app.send_message(chat_id, msg)
            except Exception: pass
        return {"status": "limit_reached", "message": msg, "synced": 0}

    if app and chat_id:
        try:
            await app.send_message(chat_id, f"🔍 <code>@{clean_username} profilidagi barcha videolar tahlil qilinmoqda...</code>")
        except Exception:
            pass

    # 4. Profil postlarini chuqur qidirish (100 tagacha)
    posts = await asyncio.to_thread(scrape_instagram_recent_posts, clean_username, 100)
    if not posts:
        return {
            "status": "ok",
            "message": f"@{clean_username} profilida yangi postlar topilmadi.",
            "synced": 0
        }

    # 5. Qat'iy deduplikatsiya: Faqat ilgari yuklanmagan postlarni ajratib olish
    unseen_posts = []
    for p in posts:
        pid = p["post_id"]
        # a) Ushbu sync kanalida avval yuklanganmi?
        if db.is_ig_post_synced(sync_channel_id, pid):
            continue
        # b) Foydalanuvchining YouTube kanaliga avval boshqa yo'l bilan yuklanganmi?
        if db.is_ig_post_already_uploaded(tg_user_id, pid):
            continue
        unseen_posts.append(p)

    if not unseen_posts:
        return {
            "status": "ok",
            "message": f"@{clean_username} profilidagi barcha ({len(posts)} ta) video allaqachon YouTube kanalingizga yuklangan. Dublikat yo'q!",
            "synced": 0
        }

    if app and chat_id:
        try:
            await app.send_message(
                chat_id,
                f"🚀 <code>@{clean_username} profilidan {len(unseen_posts)} ta yangi video topildi.</code>\n"
                f"Kunlik maksimal limitgacha yuklash boshlanmoqda..."
            )
        except Exception:
            pass

    # 6. Har kuni maksimal limitgacha ketma-ket yuklash sikli
    synced_count = 0
    limit_reached = False

    for idx, p in enumerate(unseen_posts, 1):
        pid = p["post_id"]
        safe_url = p["url"]

        if app and chat_id:
            try:
                await app.send_message(
                    chat_id,
                    f"{ce('DOWNLOAD')} <code>[{idx}/{len(unseen_posts)}] Reel #{pid} yuklanmoqda...</code>\n"
                    f"<i>8-qatlamli unikalizatsiya qo'llanmoqda...</i>"
                )
            except Exception:
                pass

        video_file = None
        try:
            processed = await download_and_8layer_uniqueify(safe_url, pid)
            video_file = processed["file_path"]

            # YouTube ga yuklash
            yt_id = await asyncio.to_thread(
                upload_to_youtube,
                video_file,
                processed["title"],
                processed["description"],
                yt_conn
            )

            # Bazada muvaffaqiyatli deb qayd etish (hech qachon qayta yuklanmaydi)
            db.record_ig_synced_post(sync_channel_id, pid, safe_url, yt_id, status="synced")
            db.increment_ig_synced_count(sync_channel_id)
            synced_count += 1

            if app and chat_id:
                try:
                    yt_url = f"https://youtu.be/{yt_id}"
                    await app.send_message(
                        chat_id,
                        f"{ce('CHECK')} <b>[{synced_count}] Muvaffaqiyatli YouTube ga joylandi!</b>\n"
                        f"{ce('VIDEO')} <b>Sarlavha:</b> {processed['title']}\n"
                        f"{ce('LINK')} <b>YouTube havola:</b> <a href=\"{yt_url}\">Ko'rish</a>"
                    )
                except Exception:
                    pass

            # Faylni tozalash
            if video_file and os.path.exists(video_file):
                try: os.remove(video_file)
                except Exception: pass

            # YouTube API rate limiting oralig'i (10 soniya)
            await asyncio.sleep(10)

        except Exception as upload_err:
            # Faylni tozalash
            if video_file and os.path.exists(video_file):
                try: os.remove(video_file)
                except Exception: pass

            err_str = str(upload_err).lower()
            is_limit_error = any(kw in err_str for kw in [
                "uploadlimitexceeded",
                "quotaexceeded",
                "exceeded the number of videos",
                "upload limit",
                "quota limit",
                "daily upload limit",
                "rate limit"
            ])

            if is_limit_error:
                # KUNLIK LIMITGA YETILDI!
                limit_reached = True
                db.set_ig_sync_daily_limit_hit(sync_channel_id)
                logger.warning(f"YouTube daily upload limit reached for user {tg_user_id}: {upload_err}")

                limit_alert = (
                    f"⚠️ <b>YouTube Kunlik Video Yuklash Limiti To'ldi!</b>\n\n"
                    f"📊 <b>Bugun yuklandi:</b> {synced_count} ta yangi video\n"
                    f"YouTube kanalingiz bugungi maksimal video yuklash soni chegarasiga yetdi (<code>uploadLimitExceeded</code>).\n\n"
                    f"🔒 <b>Deduplikatsiya:</b> Barcha yuklangan videolar to'liq eslab qolindi, birorta ham dublikat video yuklanmaydi.\n"
                    f"⏰ <b>Ertaga avtomatik davom etadi:</b> Ertaga YouTube limiti yangilanishi bilan orqa fondagi avtopilot qolgan videolarni yuklashda davom etadi!"
                )
                if app and chat_id:
                    try: await app.send_message(chat_id, limit_alert)
                    except Exception: pass
                break
            else:
                logger.error(f"IG Reel #{pid} yuklashda xatolik: {upload_err}")
                if app and chat_id:
                    try:
                        await app.send_message(
                            chat_id,
                            f"{ce('WARN')} Reel #{pid} yuklashda xatolik yuz berdi: <code>{str(upload_err)[:150]}</code>"
                        )
                    except Exception:
                        pass

    db.update_ig_sync_timestamp(sync_channel_id)

    if limit_reached:
        return {
            "status": "limit_reached",
            "message": f"Bugungi YouTube upload limiti to'ldi. {synced_count} ta yangi video yuklandi. Qolganlari ertaga davom ettiriladi.",
            "synced": synced_count
        }

    return {
        "status": "ok",
        "message": f"Tekshiruv yakunlandi! Jami {synced_count} ta yangi video muvaffaqiyatli YouTube ga joylandi.",
        "synced": synced_count
    }


async def start_instagram_sync_daemon(app, interval_seconds: int = 1800):
    """
    Orqa fonda barcha faol Instagram profillarni 24/7 tekshirib boruvchi doimiy xizmat.
    - Har bir kanalning yangi Reels-larini qidiradi
    - Yangi kun kelganda limit holatini avtomatik yangilaydi
    - Kunlik maksimal limitgacha yuklaydi
    """
    logger.info("🚀 Instagram Auto-Tracker & YouTube Sync Daemon ishga tushirildi (Interval: %ds)", interval_seconds)
    while True:
        try:
            active_channels = db.get_all_active_ig_sync_channels()
            for ch in active_channels:
                try:
                    uid = ch["tg_user_id"]
                    ig_user = ch["ig_username"]
                    ch_id = ch["id"]

                    # Yangi kun kelgan bo'lsa limitni tozalash
                    db.reset_ig_sync_daily_limit_if_new_day(ch_id)

                    # Agar bugun allaqachon limitga yetgan bo'lsa — ertangi kunga qoldirish
                    if db.is_ig_sync_daily_limit_hit_today(ch_id):
                        continue

                    # Profilni tekshirish va yuklash
                    await sync_instagram_account_now(uid, ig_user, app=app, chat_id=uid, force=False)
                except Exception as inner_e:
                    logger.error(f"IG daemon error for channel {ch.get('ig_username')}: {inner_e}")

        except Exception as e:
            logger.error(f"IG sync daemon fatal error: {e}")

        await asyncio.sleep(interval_seconds)
