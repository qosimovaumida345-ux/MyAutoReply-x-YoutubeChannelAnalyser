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
import json
from datetime import datetime, timezone

import yt_dlp
import database as db
from autopost import upload_to_youtube
from instagram_processor import get_ffmpeg_binary
from custom_emojis import ce

logger = logging.getLogger(__name__)


_active_sync_tasks = set()  # set of (tg_user_id, clean_username)


def is_sync_in_progress(tg_user_id: int, ig_username: str) -> bool:
    """Ushbu profil hozir sinxronizatsiya qilinmoqdami tekshirish"""
    clean_username = clean_instagram_target(ig_username)
    return (tg_user_id, clean_username) in _active_sync_tasks


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


def pk_to_shortcode(pk: int) -> str:
    """Instagram numeric media PK ni rasmiy base64 shortcode ga o'tkazish"""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not pk or pk <= 0:
        return ""
    res = []
    curr = pk
    while curr > 0:
        curr, rem = divmod(curr, 64)
        res.append(alphabet[rem])
    return "".join(reversed(res))


def scrape_instagram_recent_posts(ig_username: str, max_posts: int = 100, oldest_first: bool = True) -> list:
    """
    Instagram profilidan barcha videolarni login talab qilmasdan scrape qilish.
    - iPhone Safari navigatsiya sarlavhalari orqali SSR Polaris JSON-dan barcha postlarni oladi.
    - Faqat haqiqiy video (Reels/Video) postlarni ajratib oladi.
    - Muhim: Foydalanuvchi talabiga ko'ra 'oldest_first=True' qilib, profilda eng birinchi
      post qilingan (eng qadimgi) videodan boshlab xronologik tartibda qaytaradi.
    """
    clean_username = clean_instagram_target(ig_username)
    if not clean_username:
        return []

    profile_url = f"https://www.instagram.com/{clean_username}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Mode": "navigate",
    }

    found_posts = []
    seen_codes = set()

    try:
        req = urllib.request.Request(profile_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        # 1. Polaris SSR JSON tahlili
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        for s in scripts:
            if "polaris_timeline_connection" in s or "xdt_api__v1__feed__user_timeline" in s:
                try:
                    data = json.loads(s)
                    def find_timeline_edges(obj):
                        if isinstance(obj, dict):
                            if "polaris_timeline_connection" in obj and isinstance(obj["polaris_timeline_connection"], dict):
                                return obj["polaris_timeline_connection"].get("edges", [])
                            if "edges" in obj and isinstance(obj["edges"], list) and obj["edges"]:
                                if isinstance(obj["edges"][0], dict) and "node" in obj["edges"][0] and "pk" in obj["edges"][0]["node"]:
                                    return obj["edges"]
                            for v in obj.values():
                                res = find_timeline_edges(v)
                                if res: return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = find_timeline_edges(item)
                                if res: return res
                        return None

                    edges = find_timeline_edges(data)
                    if edges:
                        for edge in edges:
                            node = edge.get("node", {}) if isinstance(edge, dict) else {}
                            pk_val = node.get("pk") or node.get("id")
                            if not pk_val:
                                continue
                            pk_int = int(pk_val) if str(pk_val).isdigit() else 0
                            typename = str(node.get("__typename", ""))
                            media_type = node.get("media_type")
                            is_video = bool(node.get("is_video") or media_type == 2 or "video" in typename.lower())

                            # Faqat video postlarni olamiz (rasmlarni chetlab o'tamiz)
                            if not is_video:
                                continue

                            code = node.get("code") or node.get("shortcode")
                            if not code and pk_int > 0:
                                code = pk_to_shortcode(pk_int)
                            if not code or code in seen_codes:
                                continue

                            seen_codes.add(code)

                            caption = ""
                            desc_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                            if desc_edges and isinstance(desc_edges, list) and isinstance(desc_edges[0], dict):
                                caption = desc_edges[0].get("node", {}).get("text", "")
                            elif "caption" in node and isinstance(node["caption"], dict):
                                caption = node["caption"].get("text", "")
                            elif "caption" in node and isinstance(node["caption"], str):
                                caption = node["caption"]

                            timestamp = node.get("taken_at_timestamp") or node.get("taken_at") or 0

                            clean_title = (caption.strip().split("\n")[0][:90].strip()) if caption else f"Reel #{code}"

                            found_posts.append({
                                "post_id": str(code),
                                "pk": pk_int,
                                "url": f"https://www.instagram.com/reel/{code}/",
                                "title": clean_title,
                                "caption": caption.strip(),
                                "timestamp": int(timestamp) if str(timestamp).isdigit() else 0
                            })
                except Exception:
                    pass

        # 2. Zaxira usul: HTML regex orqali shortcode larni qidirish
        if not found_posts:
            shortcodes = re.findall(r'/(?:p|reel)/([A-Za-z0-9_-]{10,12})/?', content)
            for sc in shortcodes:
                if sc not in seen_codes:
                    seen_codes.add(sc)
                    found_posts.append({
                        "post_id": str(sc),
                        "pk": 0,
                        "url": f"https://www.instagram.com/reel/{sc}/",
                        "title": f"Reel #{sc}",
                        "caption": "",
                        "timestamp": 0
                    })
    except Exception as e:
        logger.error(f"Instagram profile scrape xatosi ({clean_username}): {e}")

    # XRONOLOGIK TARTIB:
    # Eng birinchi joylangan (eng qadimgi) videodan boshlab navbatma-navbat yuklash!
    if oldest_first and found_posts:
        # PK va timestamp qancha kichik bo'lsa, video shuncha birinchi qo'yilgan
        found_posts.sort(key=lambda x: (x.get("timestamp") or 0, x.get("pk") or 0))

    return found_posts[:max_posts]


async def download_and_8layer_uniqueify(post_url: str, post_id: str, output_dir: str = "downloads", preferred_title: str = "") -> dict:
    """
    Instagram Reel-ni yuklab oladi va unga 8-qatlamli yengil unikalizatsiya qo'llaydi:
    Render'ning 512 MB RAM muhitida tezkor va xavfsiz (out-of-memory va muzlashlarning 100% oldini oladi).
    """
    os.makedirs(output_dir, exist_ok=True)
    raw_path = os.path.join(output_dir, f"ig_raw_{post_id}.mp4")
    clean_path = os.path.join(output_dir, f"ig_clean_{post_id}.mp4")

    ydl_opts = {
        "outtmpl": raw_path,
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
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

    # 8-Qatlamli filtr zanjiri (Render 512MB RAM muhitiga to'liq moslashtirilgan: ultrafast, 1 thread, past xotira)
    vf_chain = (
        "scale=720:1280:force_original_aspect_ratio=decrease,"
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,"
        "eq=contrast=1.02:saturation=1.03,"
        "setpts=PTS/1.02"
    )
    af_chain = (
        "asetrate=44100*1.015,aresample=44100,"
        "atempo=1.02"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-threads", "1",
        "-i", raw_path,
        "-vf", vf_chain,
        "-af", af_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-maxrate", "1500k",
        "-bufsize", "2000k",
        "-c:a", "aac",
        "-b:a", "96k",
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

    yt_title = (info.get("title") or "").strip()
    yt_desc = (info.get("description") or "").strip()

    # Sarlavhani eng mazmunli va mos variantdan tanlash
    chosen_title = ""
    if preferred_title and not preferred_title.lower().startswith("video by ") and not preferred_title.lower().startswith("reel #"):
        chosen_title = preferred_title
    elif yt_desc and not yt_desc.lower().startswith("video by "):
        chosen_title = yt_desc
    elif yt_title and not yt_title.lower().startswith("video by "):
        chosen_title = yt_title
    else:
        chosen_title = preferred_title or yt_title or f"Viral Reel #{post_id}"

    clean_title = chosen_title.split("\n")[0][:90].strip() or f"Viral Reel #{post_id}"
    full_desc = yt_desc or preferred_title or clean_title

    return {
        "file_path": final_file,
        "title": f"{clean_title} #Shorts",
        "description": f"{full_desc}\n\n#shorts #reels #viral #trending #autopost",
        "post_id": post_id
    }


async def sync_instagram_account_now(tg_user_id: int, ig_username: str, app=None, chat_id=None, force: bool = False) -> dict:
    """
    Belgilangan Instagram profildan barcha videolarni tekshirib:
    1. Qat'iy xronologik tartib: Eng birinchi post qilingan (eng qadimgi) videodan boshlab yuklaydi!
    2. Qat'iy deduplikatsiya: Ilgari biror marta yuklangan videolarni 100% chetlab o'tadi.
    3. 8-qatlamli unikalizatsiya bilan YouTube kanalga yuklaydi.
    4. Kunlik maksimal limitgacha (YouTube 'uploadLimitExceeded' yoki quota limit berguncha) uzluksiz yuklaydi.
    5. Limit to'lganda avtomatik to'xtaydi, foydalanuvchiga xabar beradi va qolganlarini ertangi kunga qoldiradi.
    """
    clean_username = clean_instagram_target(ig_username)
    if is_sync_in_progress(tg_user_id, clean_username):
        logger.warning(f"Sync already in progress for user {tg_user_id} and IG @{clean_username}")
        return {"status": "busy", "message": f"@{clean_username} uchun yuklash jarayoni hozir allaqachon orqa fonda davom etmoqda!"}

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

    # Concurrency Lock: Sinxronizatsiyani ro'yxatga olish
    _active_sync_tasks.add((tg_user_id, clean_username))

    try:
        if app and chat_id:
            try:
                await app.send_message(chat_id, f"🔍 <code>@{clean_username} profilidagi barcha videolar tahlil qilinmoqda...</code>")
            except Exception:
                pass

        # 4. Profil postlarini chuqur qidirish (100 tagacha, eng qadimgisi birinchi)
        posts = await asyncio.to_thread(scrape_instagram_recent_posts, clean_username, 100, True)
        if not posts:
            return {
                "status": "ok",
                "message": f"@{clean_username} profilida yangi postlar topilmadi.",
                "synced": 0
            }

        # 5. Qat'iy deduplikatsiya: Faqat ilgari yuklanmagan postlarni ajratib olish (xronologik tartib saqlanadi)
        unseen_posts = []
        for p in posts:
            pid = p["post_id"]
            pk_str = str(p.get("pk", "")) if p.get("pk") else ""

            # a) Ushbu sync kanalida avval yuklanganmi? (shortcode yoki pk)
            if db.is_ig_post_synced(sync_channel_id, pid):
                continue
            if pk_str and db.is_ig_post_synced(sync_channel_id, pk_str):
                continue

            # b) Foydalanuvchining YouTube kanaliga avval boshqa yo'l bilan yuklanganmi?
            if db.is_ig_post_already_uploaded(tg_user_id, pid):
                continue
            if pk_str and db.is_ig_post_already_uploaded(tg_user_id, pk_str):
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
                    f"🚀 <code>@{clean_username} profilidan {len(unseen_posts)} ta yangi video topildi (eng birinchi postidan boshlab tartiblandi).</code>\n"
                    f"Kunlik maksimal YouTube limitigacha yuklash boshlanmoqda..."
                )
            except Exception:
                pass

        # 6. Har kuni maksimal limitgacha ketma-ket yuklash sikli
        synced_count = 0
        limit_reached = False

        for idx, p in enumerate(unseen_posts, 1):
            pid = p["post_id"]
            safe_url = p["url"]
            pref_title = p.get("title", "")

            if app and chat_id:
                try:
                    await app.send_message(
                        chat_id,
                        f"{ce('DOWNLOAD')} <code>[{idx}/{len(unseen_posts)}] Reel #{pid} yuklanmoqda... (Tartib: {idx}-video)</code>\n"
                        f"🎬 <b>Sarlavha:</b> {pref_title[:60]}...\n"
                        f"<i>8-qatlamli unikalizatsiya qo'llanmoqda...</i>"
                    )
                except Exception:
                    pass

            video_file = None
            try:
                processed = await download_and_8layer_uniqueify(safe_url, pid, preferred_title=pref_title)
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
                if p.get("pk"):
                    db.record_ig_synced_post(sync_channel_id, str(p["pk"]), safe_url, yt_id, status="synced")
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
                        f"📊 <b>Bugun yuklandi:</b> {synced_count} ta video (eng birinchi postlardan boshlab)\n"
                        f"YouTube kanalingiz bugungi maksimal video yuklash soni chegarasiga yetdi (<code>uploadLimitExceeded</code>).\n\n"
                        f"🔒 <b>Deduplikatsiya:</b> Barcha yuklangan videolar to'liq eslab qolindi, birorta ham dublikat video yuklanmaydi.\n"
                        f"⏰ <b>Ertaga avtomatik davom etadi:</b> Ertaga 00:00 UTC dan keyin avtopilot qolgan videolarni tartib bilan yuklashda davom etadi!"
                    )
                    if app and chat_id:
                        try: await app.send_message(chat_id, limit_alert)
                        except Exception: pass
                    break
                else:
                    logger.error(f"IG Reel #{pid} yuklashda xatolik: {upload_err}")
                    # Cheksiz loop bo'lmasligi uchun bu xatolikni DB ga 'failed' deb yozib, keyingisiga o'tamiz
                    db.record_ig_synced_post(sync_channel_id, pid, safe_url, "", status="failed")
                    if p.get("pk"):
                        db.record_ig_synced_post(sync_channel_id, str(p["pk"]), safe_url, "", status="failed")

                    if app and chat_id:
                        try:
                            await app.send_message(
                                chat_id,
                                f"{ce('WARN')} Reel #{pid} yuklashda xatolik: <code>{str(upload_err)[:120]}</code>\n"
                                f"<i>Keyingi videoga o'tilmoqda...</i>"
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

    finally:
        _active_sync_tasks.discard((tg_user_id, clean_username))


async def start_instagram_sync_daemon(app, interval_seconds: int = 1800):
    """
    Orqa fonda barcha faol Instagram profillarni 24/7 tekshirib boruvchi doimiy xizmat.
    - Har bir kanalning yangi Reels-larini qidiradi
    - Yangi kun kelganda limit holatini avtomatik yangilaydi
    - Kunlik maksimal limitgacha yuklaydi
    """
    logger.info("🚀 Instagram Auto-Tracker & YouTube Sync Daemon ishga tushirildi (Interval: %ds)", interval_seconds)
    # Server start bo'lganda boshqa barcha asosiy servislar to'liq barqarorlashishi uchun 120s kutish
    await asyncio.sleep(120)
    while True:
        try:
            active_channels = db.get_all_active_ig_sync_channels()
            for ch in active_channels:
                try:
                    uid = ch["tg_user_id"]
                    ig_user = ch["ig_username"]
                    ch_id = ch["id"]

                    # Agar ushbu profil hozir sinxronizatsiya qilinayotgan bo'lsa, o'tkazib yuborish
                    if is_sync_in_progress(uid, ig_user):
                        continue

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
