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
import hashlib
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


def shortcode_to_pk(shortcode: str) -> int:
    """Instagram base64 shortcode ni raqamli media PK ga o'tkazish."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    code = str(shortcode or "").strip()
    if not code or not re.fullmatch(r"[A-Za-z0-9_-]{8,14}", code):
        return 0
    pk = 0
    for ch in code:
        pk = pk * 64 + alphabet.index(ch)
    return pk


def parse_ig_pk(raw_pk) -> int:
    """'4028904842105002765_25025320' yoki int dan toza raqamli media PK ni ajratib oladi."""
    s = str(raw_pk or "").strip()
    if not s:
        return 0
    first_part = s.split("_", 1)[0].strip()
    return int(first_part) if first_part.isdigit() else 0


def compute_title_fingerprint(text: str) -> str:
    """Sarlavha/caption dan hashtag va belgilarsiz barqaror barmoq izi (fingerprint) yaratadi."""
    s = str(text or "").lower()
    s = re.sub(r"[#@][a-z0-9_.]+", " ", s)
    s = re.sub(r"[^a-z0-9а-яёўқғҳ]+", "", s)
    return s[:120]


def compute_file_sha256(file_path: str) -> str:
    """Video fayl baytlarining SHA-256 xeshini hisoblash."""
    if not file_path or not os.path.exists(file_path):
        return ""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def scrape_instagram_recent_posts(ig_username: str, max_posts: int = 100, oldest_first: bool = True) -> list:
    """
    Instagram profilidan barcha Reels/Video postlarni ko'p manbali (multi-source) usulda oladi:
    1. Profil bosh sahifasi (/) va /reels/ SSR Polaris JSON
    2. /embed/ SSR JSON
    3. yt_dlp flat-playlist zaxira ekstraktori (12 tadan ko'p Reels uchun)
    Barcha topilgan postlar shortcode <-> pk bo'yicha birlashtiriladi va xronologik tartiblanadi.
    """
    clean_username = clean_instagram_target(ig_username)
    if not clean_username:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Mode": "navigate",
    }

    found_posts = []
    seen_codes = set()
    seen_pks = set()

    def _add_post(code: str = "", pk_val=0, caption: str = "", timestamp=0):
        pk_int = parse_ig_pk(pk_val)
        c = str(code or "").strip()
        if not c and pk_int > 0:
            c = pk_to_shortcode(pk_int)
        if pk_int <= 0 and c:
            pk_int = shortcode_to_pk(c)
        if not c or c in seen_codes:
            return
        if pk_int > 0 and pk_int in seen_pks:
            return
        seen_codes.add(c)
        if pk_int > 0:
            seen_pks.add(pk_int)
        cap_clean = str(caption or "").strip()
        clean_title = (cap_clean.split("\n")[0][:90].strip()) if cap_clean else f"Reel #{c}"
        ts_int = int(timestamp) if str(timestamp).isdigit() else 0
        found_posts.append({
            "post_id": c,
            "pk": pk_int,
            "url": f"https://www.instagram.com/reel/{c}/",
            "title": clean_title,
            "caption": cap_clean,
            "timestamp": ts_int,
        })

    def _extract_caption(node: dict) -> str:
        desc_edges = node.get("edge_media_to_caption", {}).get("edges", []) if isinstance(node.get("edge_media_to_caption"), dict) else []
        if desc_edges and isinstance(desc_edges, list) and isinstance(desc_edges[0], dict):
            return desc_edges[0].get("node", {}).get("text", "") or ""
        cap = node.get("caption")
        if isinstance(cap, dict):
            return cap.get("text", "") or ""
        if isinstance(cap, str):
            return cap
        return ""

    def _walk_json_for_media(obj, assume_video: bool = False):
        if isinstance(obj, dict):
            for list_key in ("edges", "items"):
                arr = obj.get(list_key)
                if isinstance(arr, list) and arr:
                    for item in arr:
                        if not isinstance(item, dict):
                            continue
                        node = item.get("node") or item.get("media") or item
                        if not isinstance(node, dict):
                            continue
                        pk_val = node.get("pk") or node.get("id")
                        code = node.get("code") or node.get("shortcode") or ""
                        if pk_val or code:
                            typename = str(node.get("__typename", ""))
                            media_type = node.get("media_type")
                            is_vid = bool(
                                assume_video
                                or node.get("is_video")
                                or media_type == 2
                                or "video" in typename.lower()
                                or node.get("video_versions")
                            )
                            if is_vid:
                                _add_post(
                                    code=code,
                                    pk_val=pk_val,
                                    caption=_extract_caption(node),
                                    timestamp=node.get("taken_at_timestamp") or node.get("taken_at") or 0,
                                )
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    _walk_json_for_media(v, assume_video=assume_video)
        elif isinstance(obj, list):
            for elem in obj:
                if isinstance(elem, (dict, list)):
                    _walk_json_for_media(elem, assume_video=assume_video)

    # 1. Profil (/) va (/reels/) SSR Polaris JSON
    for suffix, is_reels_tab in (("/", False), ("/reels/", True)):
        page_url = f"https://www.instagram.com/{clean_username}{suffix}"
        try:
            req = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
            for s in scripts:
                if any(k in s for k in ("polaris_timeline_connection", "xdt_api__v1__feed__user_timeline", "clips", "edges")):
                    try:
                        data = json.loads(s)
                        _walk_json_for_media(data, assume_video=is_reels_tab)
                    except Exception:
                        pass
            if not found_posts and not is_reels_tab:
                for sc in re.findall(r'/(?:p|reel)/([A-Za-z0-9_-]{10,12})/?', content):
                    _add_post(code=sc)
        except Exception as e:
            logger.debug(f"Instagram SSR fetch ({page_url}) error: {e}")

    # 2. /embed/ sahifasidan qo'shimcha Reels/Video shortcode larini olish
    if len(found_posts) < max_posts:
        embed_url = f"https://www.instagram.com/{clean_username}/embed/"
        try:
            req = urllib.request.Request(embed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                emb_html = resp.read().decode("utf-8", errors="ignore")
            unesc = emb_html.replace('\\"', '"').replace('\\/', '/')
            for sc, is_vid in re.findall(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{9,14})"[^{}]{0,400}?"is_video"\s*:\s*(true|false)', unesc):
                if is_vid == "true":
                    _add_post(code=sc)
        except Exception as e:
            logger.debug(f"Instagram embed fetch ({clean_username}) error: {e}")

    # 3. yt_dlp flat-playlist zaxira usuli (chuqur tarix uchun)
    if len(found_posts) < min(max_posts, 15):
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "playlistend": max_posts,
                "nocheckcertificate": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.instagram.com/{clean_username}/reels/", download=False)
            for entry in (info or {}).get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                eid = str(entry.get("id") or "").strip()
                eurl = str(entry.get("url") or entry.get("webpage_url") or "")
                m_sc = re.search(r'/(?:p|reel|reels)/([A-Za-z0-9_-]{9,14})/?', eurl)
                code = m_sc.group(1) if m_sc else (eid if re.fullmatch(r"[A-Za-z0-9_-]{9,14}", eid) and not eid.isdigit() else "")
                _add_post(
                    code=code,
                    pk_val=eid if eid.isdigit() or "_" in eid else 0,
                    caption=entry.get("title") or entry.get("description") or "",
                    timestamp=entry.get("timestamp") or 0,
                )
        except Exception as e:
            logger.debug(f"Instagram yt_dlp flat-playlist fallback ({clean_username}): {e}")

    # XRONOLOGIK TARTIB: Eng birinchi joylangan (eng qadimgi) videodan boshlab yuklash
    if oldest_first and found_posts:
        found_posts.sort(key=lambda x: (x.get("pk") or 0, x.get("timestamp") or 0))

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

    raw_sha256 = compute_file_sha256(raw_path)
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
        "post_id": post_id,
        "file_sha256": raw_sha256,
        "title_fingerprint": compute_title_fingerprint(full_desc or clean_title),
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
    yt_channel_id = str(yt_conn.get("yt_channel_id") or "")

    # 2. Yangi kun kelgan bo'lsa, limit holatini avtomatik tiklash va vaqtinchalik xatolarni tozalash
    db.reset_ig_sync_daily_limit_if_new_day(sync_channel_id)
    db.reset_transient_failed_ig_posts(sync_channel_id)

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
        batch_seen_ids = set()
        for p in posts:
            pid = str(p["post_id"]).strip()
            pk_int = parse_ig_pk(p.get("pk")) or shortcode_to_pk(pid)
            pk_str = str(pk_int) if pk_int > 0 else ""
            if pid in batch_seen_ids or (pk_str and pk_str in batch_seen_ids):
                continue

            # a) Ushbu sync kanalida avval yuklanganmi? (shortcode yoki pk)
            if db.is_ig_post_synced(sync_channel_id, pid):
                continue
            if pk_str and db.is_ig_post_synced(sync_channel_id, pk_str):
                continue

            # b) Foydalanuvchining ulangan YouTube kanaliga avval yuklanganmi?
            tfp = compute_title_fingerprint(p.get("caption") or p.get("title") or "")
            if db.is_ig_post_already_uploaded(
                tg_user_id,
                pid,
                yt_channel_id=yt_channel_id,
                media_pk=pk_str,
                title_fingerprint=tfp,
            ):
                continue

            batch_seen_ids.add(pid)
            if pk_str:
                batch_seen_ids.add(pk_str)
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
        consecutive_failures = 0

        for idx, p in enumerate(unseen_posts, 1):
            pid = str(p["post_id"]).strip()
            pk_int = parse_ig_pk(p.get("pk")) or shortcode_to_pk(pid)
            pk_str = str(pk_int) if pk_int > 0 else ""
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
                file_sha256 = processed.get("file_sha256", "")
                tfp = processed.get("title_fingerprint", "")

                # Yuklab olingan fayl baytlari (SHA-256) bo'yicha qo'shimcha dublikat tekshiruvi
                if file_sha256 and db.is_ig_post_already_uploaded(
                    tg_user_id, pid, yt_channel_id=yt_channel_id, media_pk=pk_str, file_sha256=file_sha256
                ):
                    if video_file and os.path.exists(video_file):
                        try: os.remove(video_file)
                        except Exception: pass
                    db.record_ig_synced_post(
                        sync_channel_id, pid, safe_url, "", status="synced",
                        tg_user_id=tg_user_id, yt_channel_id=yt_channel_id,
                        ig_username=clean_username, media_pk=pk_str,
                        file_sha256=file_sha256, title_fingerprint=tfp,
                    )
                    continue

                # YouTube ga yuklash
                yt_id = await asyncio.to_thread(
                    upload_to_youtube,
                    video_file,
                    processed["title"],
                    processed["description"],
                    yt_conn
                )

                # Bazada muvaffaqiyatli deb qayd etish (hech qachon qayta yuklanmaydi)
                db.record_ig_synced_post(
                    sync_channel_id, pid, safe_url, yt_id, status="synced",
                    tg_user_id=tg_user_id, yt_channel_id=yt_channel_id,
                    ig_username=clean_username, media_pk=pk_str,
                    file_sha256=file_sha256, title_fingerprint=tfp,
                )
                db.increment_ig_synced_count(sync_channel_id)
                synced_count += 1
                consecutive_failures = 0

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
                is_limit_error = any(kw in err_str for kw in (
                    "uploadlimitexceeded",
                    "quotaexceeded",
                    "exceeded the number of videos",
                    "daily upload limit",
                ))
                is_auth_error = any(kw in err_str for kw in (
                    "invalid_grant",
                    "unauthorized",
                    "invalid_credentials",
                    "refresherror",
                    "token has been expired",
                ))
                is_transient_source_error = any(kw in err_str for kw in (
                    "http error 429",
                    "too many requests",
                    "login required",
                    "rate-limit",
                    "timed out",
                    "connection reset",
                ))

                if is_limit_error:
                    # KUNLIK LIMITGA YETILDI! Videoni failed qilmaymiz — ertaga aynan shundan davom etadi.
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
                elif is_auth_error:
                    logger.error(f"YouTube OAuth error during IG sync for user {tg_user_id}: {upload_err}")
                    if app and chat_id:
                        try:
                            await app.send_message(
                                chat_id,
                                f"⚠️ <b>YouTube OAuth Token Eskirgan Yoki Bekor Qilingan!</b>\n\n"
                                f"Iltimos, /ytlogin buyrug'i orqali YouTube kanalingizni qayta ulang. "
                                f"Qolgan videolar saqlab qolindi va keyingi tekshiruvda yuklanadi."
                            )
                        except Exception:
                            pass
                    break
                elif is_transient_source_error:
                    logger.warning(f"Transient Instagram/network error on #{pid}: {upload_err}")
                    if force and app and chat_id:
                        try:
                            await app.send_message(
                                chat_id,
                                f"{ce('WARN')} Instagram vaqtinchalik cheklovi: <code>{str(upload_err)[:120]}</code>\n"
                                f"<i>Keyingi avtopilot siklida qayta uriniladi.</i>"
                            )
                        except Exception:
                            pass
                    break
                else:
                    consecutive_failures += 1
                    logger.error(f"IG Reel #{pid} yuklashda xatolik: {upload_err}")
                    db.record_ig_synced_post(
                        sync_channel_id, pid, safe_url, "", status="failed",
                        tg_user_id=tg_user_id, yt_channel_id=yt_channel_id,
                        ig_username=clean_username, media_pk=pk_str,
                        error_msg=str(upload_err)[:200],
                    )

                    if app and chat_id:
                        try:
                            await app.send_message(
                                chat_id,
                                f"{ce('WARN')} Reel #{pid} yuklashda xatolik: <code>{str(upload_err)[:120]}</code>\n"
                                f"<i>Keyingi videoga o'tilmoqda...</i>"
                            )
                        except Exception:
                            pass
                    if consecutive_failures >= 3:
                        logger.warning(f"Stopping IG sync for @{clean_username} after 3 consecutive failures")
                        break

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


_daemon_started = False


async def start_instagram_sync_daemon(app, interval_seconds: int = 1800):
    """
    Orqa fonda barcha faol Instagram profillarni 24/7 tekshirib boruvchi doimiy xizmat.
    - Har bir kanalning yangi Reels-larini qidiradi
    - Yangi kun kelganda limit holatini avtomatik yangilaydi
    - Kunlik maksimal limitgacha yuklaydi
    """
    global _daemon_started
    if _daemon_started:
        logger.info("Instagram Auto-Tracker Daemon allaqachon ishlamoqda, ikkinchi nusxa ishga tushirilmadi.")
        return
    _daemon_started = True
    logger.info("🚀 Instagram Auto-Tracker & YouTube Sync Daemon ishga tushirildi (Interval: %ds)", interval_seconds)
    # Server start bo'lganda boshqa barcha asosiy servislar to'liq barqarorlashishi uchun 120s kutish
    await asyncio.sleep(120)
    while True:
        try:
            if db.is_db_in_cooldown():
                await asyncio.sleep(interval_seconds)
                continue
            active_channels = await asyncio.to_thread(db.get_all_active_ig_sync_channels)
            for ch in active_channels:
                try:
                    uid = ch["tg_user_id"]
                    ig_user = ch["ig_username"]
                    ch_id = ch["id"]

                    # Agar ushbu profil hozir sinxronizatsiya qilinayotgan bo'lsa, o'tkazib yuborish
                    if is_sync_in_progress(uid, ig_user):
                        continue

                    # Yangi kun kelgan bo'lsa limitni tozalash
                    await asyncio.to_thread(db.reset_ig_sync_daily_limit_if_new_day, ch_id)

                    # Agar bugun allaqachon limitga yetgan bo'lsa — ertangi kunga qoldirish
                    if await asyncio.to_thread(db.is_ig_sync_daily_limit_hit_today, ch_id):
                        continue

                    # Profilni tekshirish va yuklash
                    await sync_instagram_account_now(uid, ig_user, app=app, chat_id=uid, force=False)
                except Exception as inner_e:
                    logger.error(f"IG daemon error for channel {ch.get('ig_username')}: {inner_e}")

        except Exception as e:
            logger.error(f"IG sync daemon fatal error: {e}")

        await asyncio.sleep(interval_seconds)
