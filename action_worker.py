"""
CreatorFlow Action Worker — GitHub Actions Ubuntu runner (7 GB RAM) muhitida ishlaydi.
Video yuklash, unikalizatsiya va Shorts kesish vazifalarini bajarib,
natijani Telegram Bot API orqali to'g'ridan-to'g'ri foydalanuvchiga yuboradi.
"""

import os
import sys
import uuid
import shutil
import asyncio
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("action_worker")

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

TASK_TYPE = os.environ.get("TASK_TYPE", "download").strip().lower()
TARGET_URL = os.environ.get("TARGET_URL", "").strip()
CHAT_ID_STR = os.environ.get("CHAT_ID", "0").strip()
CHAT_ID = int(CHAT_ID_STR) if CHAT_ID_STR.lstrip("-").isdigit() else 0
FORMAT = os.environ.get("FORMAT", "720").strip()
CAPTION = os.environ.get("CAPTION", "").strip()
PROXY = os.environ.get("PROXY", "").strip() or None
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()


def _get_ffmpeg():
    for p in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if shutil.which(p):
            return p
    return "ffmpeg"


def _build_ydl_opts(out_path, fmt="720", proxy=None):
    format_map = {
        "mp3":  "bestaudio/best",
        "360":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]/best",
        "480":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
        "720":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
        "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best",
        "1440": "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
        "4k":   "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
        "8k":   "bestvideo[height<=4320]+bestaudio/best[height<=4320]/best",
        "best": "bestvideo+bestaudio/best",
    }

    ydl_opts = {
        "outtmpl": out_path,
        "format": format_map.get(fmt, format_map["720"]),
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb", "web"],
                "player_skip": ["webpage"],
            }
        },
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        "max_filesize": 50 * 1024 * 1024,
    }

    if fmt == "mp3":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]

    if proxy:
        ydl_opts["proxy"] = proxy

    return ydl_opts


def _find_downloaded_file(expected_path):
    if os.path.exists(expected_path):
        return expected_path
    base, _ = os.path.splitext(expected_path)
    dirname = os.path.dirname(expected_path)
    basename = os.path.basename(base)
    for f in os.listdir(dirname):
        if f.startswith(basename):
            return os.path.join(dirname, f)
    return None


async def _send_video(chat_id: int, file_path: str, caption: str = ""):
    import httpx
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN yo'q!")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    async with httpx.AsyncClient(timeout=300) as client:
        with open(file_path, "rb") as f:
            resp = await client.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption[:1024] if caption else "",
                    "parse_mode": "HTML",
                    "supports_streaming": "true"
                },
                files={"video": (os.path.basename(file_path), f, "video/mp4")}
            )
    return resp.status_code == 200


async def _send_audio(chat_id: int, file_path: str, caption: str = "", title: str = "Audio"):
    import httpx
    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    async with httpx.AsyncClient(timeout=300) as client:
        with open(file_path, "rb") as f:
            resp = await client.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption[:1024] if caption else "",
                    "parse_mode": "HTML",
                    "title": title[:64]
                },
                files={"audio": (os.path.basename(file_path), f, "audio/mpeg")}
            )
    return resp.status_code == 200


async def _send_msg(chat_id: int, text: str):
    import httpx
    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        })
    return resp.status_code == 200


async def handle_download():
    import yt_dlp

    task_id = uuid.uuid4().hex[:8]
    out_path = os.path.join(DOWNLOADS_DIR, f"dl_{task_id}.mp4")

    logger.info(f"Downloading: url={TARGET_URL}, fmt={FORMAT}")
    ydl_opts = _build_ydl_opts(out_path, FORMAT, PROXY)

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(TARGET_URL, download=True)

    info = await asyncio.to_thread(_dl)
    actual_path = _find_downloaded_file(out_path)
    if not actual_path:
        raise Exception("Fayl yuklab olingandan so'ng topilmadi.")

    title = info.get("title", "Video") if isinstance(info, dict) else "Video"
    cap = CAPTION or f"🎬 <b>{title[:60]}</b>\n\n⚡ <i>7 GB RAM Cloud Runner orqali yuklandi</i>"

    if FORMAT == "mp3":
        mp3_path = actual_path.rsplit(".", 1)[0] + ".mp3"
        if os.path.exists(mp3_path):
            actual_path = mp3_path
        await _send_audio(CHAT_ID, actual_path, cap, title)
    else:
        await _send_video(CHAT_ID, actual_path, cap)


async def handle_uniqualize():
    import yt_dlp

    task_id = uuid.uuid4().hex[:8]
    raw_path = os.path.join(DOWNLOADS_DIR, f"raw_{task_id}.mp4")
    clean_path = os.path.join(DOWNLOADS_DIR, f"clean_{task_id}.mp4")

    logger.info(f"Uniqualizing: url={TARGET_URL}")
    ydl_opts = _build_ydl_opts(raw_path, "720", PROXY)

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(TARGET_URL, download=True)

    info = await asyncio.to_thread(_dl)
    actual_raw = _find_downloaded_file(raw_path)
    if not actual_raw:
        raise Exception("Asosiy video yuklanmadi.")

    ffmpeg_bin = _get_ffmpeg()
    cmd = [
        ffmpeg_bin, "-y", "-i", actual_raw,
        "-vf", "eq=contrast=1.03:brightness=0.01:saturation=1.04,scale='min(1080,iw)':-2",
        "-af", "atempo=1.02,asetrate=44100*1.015,aresample=44100",
        "-map_metadata", "-1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        clean_path
    ]

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()

    if not os.path.exists(clean_path):
        raise Exception("FFmpeg orqali unikalizatsiya qilishda xatolik yuz berdi.")

    title = info.get("title", "Unikal Video") if isinstance(info, dict) else "Unikal Video"
    cap = CAPTION or (
        f"⚡ <b>Video Muvaffaqiyatli Unikalizatsiya Qilindi!</b>\n\n"
        f"🎬 <b>Sarlavha:</b> {title[:70]}\n"
        f"🛡️ <b>Qo'llangan himoya choralari:</b>\n"
        f"• Audio pitch shift (+1.5% va +2% tempo)\n"
        f"• Video EQ gamma, kontrast va to'yinganlik filtrlari\n"
        f"• Barcha metadatalar to'liq tozalandi\n\n"
        f"☁️ <i>7 GB RAM Cloud Runner</i>"
    )

    await _send_video(CHAT_ID, clean_path, cap)


async def handle_clip():
    import yt_dlp

    task_id = uuid.uuid4().hex[:8]
    raw_path = os.path.join(DOWNLOADS_DIR, f"clip_raw_{task_id}.mp4")

    logger.info(f"Shorts clipping: url={TARGET_URL}")
    ydl_opts = _build_ydl_opts(raw_path, "720", PROXY)

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(TARGET_URL, download=True)

    info = await asyncio.to_thread(_dl)
    duration = int(info.get("duration", 180)) if isinstance(info, dict) else 180
    title = info.get("title", "Video") if isinstance(info, dict) else "Video"

    actual_raw = _find_downloaded_file(raw_path)
    if not actual_raw:
        raise Exception("Asosiy video yuklanmadi.")

    s1_start = max(5, int(duration * 0.15))
    s1_end = min(s1_start + 35, duration - 10)
    s2_start = max(s1_end + 10, int(duration * 0.45))
    s2_end = min(s2_start + 40, duration - 10)
    s3_start = max(s2_end + 10, int(duration * 0.75))
    s3_end = min(s3_start + 35, duration - 2)

    segments = [
        {"num": 1, "start": s1_start, "end": s1_end, "hook": "Buni hech kim kutmagan edi! 🔥"},
        {"num": 2, "start": s2_start, "end": s2_end, "hook": "Eng muhim va hayratlanarli qismi 😱"},
        {"num": 3, "start": s3_start, "end": s3_end, "hook": "Oxirigacha ko'ring, xulosa qiling! ⚡"}
    ]

    ffmpeg_bin = _get_ffmpeg()
    for seg in segments:
        seg_path = os.path.join(DOWNLOADS_DIR, f"clip_{task_id}_s{seg['num']}.mp4")
        seg_dur = seg["end"] - seg["start"]

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(seg["start"]), "-t", str(seg_dur),
            "-i", actual_raw,
            "-vf", "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            seg_path
        ]

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()

        if os.path.exists(seg_path):
            cap = (
                f"✂️ <b>Shorts #{seg['num']}: {seg['hook']}</b>\n\n"
                f"🎬 Asl video: <i>{title[:50]}</i>\n"
                f"⏱ Vaqt: {seg['start']}s - {seg['end']}s ({seg_dur} soniya)\n"
                f"📐 Format: 9:16 Vertikal (1080x1920)\n\n"
                f"☁️ <i>7 GB RAM Cloud Runner</i>"
            )
            await _send_video(CHAT_ID, seg_path, cap)


async def main():
    if not TARGET_URL or not CHAT_ID:
        logger.error(f"Noto'g'ri parametrlar: TARGET_URL={TARGET_URL}, CHAT_ID={CHAT_ID}")
        sys.exit(1)

    logger.info(f"Ish boshlandi: TASK_TYPE={TASK_TYPE}, URL={TARGET_URL}, CHAT_ID={CHAT_ID}")

    try:
        if TASK_TYPE == "download":
            await handle_download()
        elif TASK_TYPE == "uniqualize":
            await handle_uniqualize()
        elif TASK_TYPE == "clip":
            await handle_clip()
        else:
            logger.error(f"Noma'lum TASK_TYPE: {TASK_TYPE}")
            await _send_msg(CHAT_ID, f"❌ Noma'lum vazifa turi: {TASK_TYPE}")
            sys.exit(1)

        logger.info("Vazifa muvaffaqiyatli bajarildi!")

    except Exception as e:
        logger.exception(f"Xatolik yuz berdi: {e}")
        await _send_msg(CHAT_ID, f"❌ <b>Videoni qayta ishlashda xatolik:</b>\n{str(e)[:300]}")
        sys.exit(1)

    finally:
        try:
            for f in os.listdir(DOWNLOADS_DIR):
                fp = os.path.join(DOWNLOADS_DIR, f)
                if os.path.isfile(fp):
                    os.remove(fp)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
