"""
Worker Server — Google Cloud Shell'da ishga tushiriladi.
yt-dlp + ffmpeg og'ir ishlarni bajaradi va natijani Telegram orqali yuboradi.

Ishga tushirish:
    pip install fastapi uvicorn yt-dlp python-dotenv httpx
    uvicorn worker:app --host 0.0.0.0 --port 8080

Cloud Shell'da web preview ochish:
    Web Preview → Change port → 8080
"""

import os
import uuid
import asyncio
import shutil
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")

app = FastAPI(title="CreatorFlow Worker", version="1.0")

# ==================== DOWNLOADS PAPKASI ====================
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# ==================== BOT TOKEN (Telegram orqali video yuborish uchun) ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ==================== REQUEST MODELLARI ====================

class DownloadRequest(BaseModel):
    """Video yuklab olish so'rovi"""
    url: str
    chat_id: int
    format: str = "720"
    caption: Optional[str] = ""
    cookies_text: Optional[str] = None
    proxy: Optional[str] = None

class UniqualizeRequest(BaseModel):
    """Video unikalizatsiya so'rovi"""
    url: str
    chat_id: int
    caption: Optional[str] = ""
    cookies_text: Optional[str] = None

class ClipRequest(BaseModel):
    """Shorts clipper so'rovi"""
    url: str
    chat_id: int
    caption: Optional[str] = ""
    cookies_text: Optional[str] = None


# ==================== YORDAMCHI FUNKSIYALAR ====================

def _get_ffmpeg_binary():
    """ffmpeg binary yo'lini topish"""
    for path in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if shutil.which(path):
            return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return "ffmpeg"


def _build_ydl_opts(out_path, fmt="720", cookies_text=None, proxy=None, user_id="worker"):
    """yt-dlp parametrlarini tuzish"""
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
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb", "web"],
                "player_skip": ["webpage"],
            }
        },
        "retries": 5,
        "fragment_retries": 5,
        "skip_unavailable_fragments": True,
        "max_filesize": 50 * 1024 * 1024,
    }

    if fmt == "mp3":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]

    if cookies_text:
        cookie_path = os.path.join(DOWNLOADS_DIR, f"cookies_{user_id}.txt")
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(cookies_text)
        ydl_opts["cookiefile"] = cookie_path

    if proxy:
        ydl_opts["proxy"] = proxy

    return ydl_opts


def _find_downloaded_file(expected_path):
    """yt-dlp ba'zan extension qo'shadi — haqiqiy faylni topish"""
    if os.path.exists(expected_path):
        return expected_path
    base, _ = os.path.splitext(expected_path)
    dirname = os.path.dirname(expected_path)
    basename = os.path.basename(base)
    for f in os.listdir(dirname):
        if f.startswith(basename):
            return os.path.join(dirname, f)
    return None


async def _send_video_to_telegram(chat_id: int, file_path: str, caption: str = ""):
    """Videoni Telegram Bot API orqali to'g'ridan-to'g'ri yuborish"""
    import httpx

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN yo'q — videoni Telegram ga yuborib bo'lmaydi!")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    async with httpx.AsyncClient(timeout=300) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption[:1024] if caption else "",
                    "parse_mode": "HTML",
                    "supports_streaming": "true"
                },
                files={"video": (os.path.basename(file_path), f, "video/mp4")}
            )

        if response.status_code == 200:
            logger.info(f"Video yuborildi: chat_id={chat_id}")
            return True
        else:
            logger.error(f"Telegram API xatosi: {response.status_code} — {response.text}")
            return False


async def _send_audio_to_telegram(chat_id: int, file_path: str, caption: str = "", title: str = "Audio"):
    """Audio faylni Telegram ga yuborish"""
    import httpx

    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"

    async with httpx.AsyncClient(timeout=300) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption[:1024] if caption else "",
                    "parse_mode": "HTML",
                    "title": title[:64]
                },
                files={"audio": (os.path.basename(file_path), f, "audio/mpeg")}
            )

        return response.status_code == 200


async def _send_message_to_telegram(chat_id: int, text: str):
    """Oddiy matn xabar yuborish"""
    import httpx

    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        })
        return response.status_code == 200


# ==================== API ENDPOINTLAR ====================

@app.get("/health")
async def health_check():
    """Worker server holatini tekshirish"""
    return {
        "status": "ok",
        "worker": "creatorflow-worker",
        "timestamp": datetime.utcnow().isoformat(),
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "bot_token": bool(BOT_TOKEN)
    }


@app.post("/download")
async def download_video(req: DownloadRequest):
    """Video yuklab olish va Telegram ga yuborish"""
    import yt_dlp

    task_id = uuid.uuid4().hex[:8]
    out_path = os.path.join(DOWNLOADS_DIR, f"dl_{task_id}.mp4")

    logger.info(f"Download boshlandi: task={task_id}, url={req.url}, format={req.format}")

    try:
        ydl_opts = _build_ydl_opts(out_path, req.format, req.cookies_text, req.proxy, task_id)

        def _dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(req.url, download=True)

        info = await asyncio.to_thread(_dl)

        actual_path = _find_downloaded_file(out_path)
        if not actual_path:
            await _send_message_to_telegram(req.chat_id, "❌ Videoni yuklab bo'lmadi. Havolani tekshirib qayta urinib ko'ring.")
            return JSONResponse({"ok": False, "error": "File not found after download"}, status_code=500)

        title = info.get("title", "Video") if isinstance(info, dict) else "Video"
        caption = req.caption or f"🎬 <b>{title[:60]}</b>"

        if req.format == "mp3":
            mp3_path = actual_path.rsplit(".", 1)[0] + ".mp3"
            if os.path.exists(mp3_path):
                actual_path = mp3_path
            sent = await _send_audio_to_telegram(req.chat_id, actual_path, caption, title)
        else:
            sent = await _send_video_to_telegram(req.chat_id, actual_path, caption)

        if sent:
            logger.info(f"Task {task_id} muvaffaqiyatli yakunlandi")
            return {"ok": True, "task_id": task_id, "title": title}
        else:
            return JSONResponse({"ok": False, "error": "Failed to send to Telegram"}, status_code=500)

    except Exception as e:
        logger.error(f"Download xatosi (task={task_id}): {e}")
        await _send_message_to_telegram(req.chat_id, f"❌ Videoni yuklab bo'lmadi: {str(e)[:200]}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    finally:
        for pattern in [out_path, out_path.rsplit(".", 1)[0] + ".mp3"]:
            if os.path.exists(pattern):
                try: os.remove(pattern)
                except: pass
        for f in os.listdir(DOWNLOADS_DIR):
            if task_id in f:
                try: os.remove(os.path.join(DOWNLOADS_DIR, f))
                except: pass


@app.post("/uniqualize")
async def uniqualize_video(req: UniqualizeRequest):
    """Video unikalizatsiya (Content ID bypass)"""
    import yt_dlp

    task_id = uuid.uuid4().hex[:8]
    raw_path = os.path.join(DOWNLOADS_DIR, f"unikal_raw_{task_id}.mp4")
    clean_path = os.path.join(DOWNLOADS_DIR, f"unikal_clean_{task_id}.mp4")

    logger.info(f"Unikalizatsiya boshlandi: task={task_id}")

    try:
        ydl_opts = _build_ydl_opts(raw_path, "720", req.cookies_text, None, task_id)

        def _dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(req.url, download=True)

        info = await asyncio.to_thread(_dl)

        actual_raw = _find_downloaded_file(raw_path)
        if not actual_raw:
            await _send_message_to_telegram(req.chat_id, "❌ Videoni yuklab bo'lmadi.")
            return JSONResponse({"ok": False, "error": "Download failed"}, status_code=500)

        ffmpeg_exe = _get_ffmpeg_binary()
        cmd = [
            ffmpeg_exe, "-y", "-i", actual_raw,
            "-vf", "eq=contrast=1.03:brightness=0.01:saturation=1.04,scale='min(1080,iw)':-2",
            "-af", "atempo=1.02,asetrate=44100*1.015,aresample=44100",
            "-map_metadata", "-1",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            clean_path
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        if not os.path.exists(clean_path):
            await _send_message_to_telegram(req.chat_id, "❌ Videoni qayta ishlashda xatolik yuz berdi.")
            return JSONResponse({"ok": False, "error": "FFmpeg processing failed"}, status_code=500)

        title = info.get("title", "Unikal Video") if isinstance(info, dict) else "Unikal Video"
        caption = req.caption or (
            f"⚡ <b>Video Muvaffaqiyatli Unikalizatsiya Qilindi!</b>\n\n"
            f"🎬 <b>Sarlavha:</b> {title[:70]}\n"
            f"🛡️ <b>Qo'llangan himoya choralari:</b>\n"
            f"• Audio pitch shift (+1.5% va +2% tempo)\n"
            f"• Video EQ gamma, kontrast va to'yinganlik filtrlari\n"
            f"• Barcha metadatalar olib tashlandi"
        )

        sent = await _send_video_to_telegram(req.chat_id, clean_path, caption)

        if sent:
            return {"ok": True, "task_id": task_id, "title": title}
        else:
            return JSONResponse({"ok": False, "error": "Failed to send to Telegram"}, status_code=500)

    except Exception as e:
        logger.error(f"Unikalizatsiya xatosi (task={task_id}): {e}")
        await _send_message_to_telegram(req.chat_id, f"❌ Unikalizatsiya jarayonida xatolik: {str(e)[:200]}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    finally:
        for path in [raw_path, clean_path]:
            if os.path.exists(path):
                try: os.remove(path)
                except: pass
        for f in os.listdir(DOWNLOADS_DIR):
            if task_id in f:
                try: os.remove(os.path.join(DOWNLOADS_DIR, f))
                except: pass


@app.post("/clip")
async def clip_shorts(req: ClipRequest):
    """Uzun videodan 3 ta Shorts kesib chiqarish"""
    import yt_dlp

    task_id = uuid.uuid4().hex[:8]
    raw_path = os.path.join(DOWNLOADS_DIR, f"clipper_raw_{task_id}.mp4")

    logger.info(f"Shorts clipper boshlandi: task={task_id}")

    try:
        ydl_opts = _build_ydl_opts(raw_path, "720", req.cookies_text, None, task_id)

        def _dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(req.url, download=True)

        info = await asyncio.to_thread(_dl)
        duration = int(info.get("duration", 180)) if isinstance(info, dict) else 180
        title = info.get("title", "Video") if isinstance(info, dict) else "Video"

        actual_raw = _find_downloaded_file(raw_path)
        if not actual_raw:
            await _send_message_to_telegram(req.chat_id, "❌ Videoni yuklab bo'lmadi.")
            return JSONResponse({"ok": False, "error": "Download failed"}, status_code=500)

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

        ffmpeg_exe = _get_ffmpeg_binary()
        sent_count = 0

        for seg in segments:
            seg_path = os.path.join(DOWNLOADS_DIR, f"clip_{task_id}_s{seg['num']}.mp4")
            seg_dur = seg["end"] - seg["start"]

            cmd = [
                ffmpeg_exe, "-y",
                "-ss", str(seg["start"]), "-t", str(seg_dur),
                "-i", actual_raw,
                "-vf", "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                seg_path
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            if os.path.exists(seg_path):
                caption = (
                    f"✂️ <b>Shorts #{seg['num']}/3</b> — {title[:50]}\n"
                    f"📝 {seg['hook']}\n"
                    f"⏱ {seg_dur} soniya"
                )
                sent = await _send_video_to_telegram(req.chat_id, seg_path, caption)
                if sent:
                    sent_count += 1
                try: os.remove(seg_path)
                except: pass

        if sent_count > 0:
            await _send_message_to_telegram(
                req.chat_id,
                f"✅ <b>{sent_count}/3 ta Shorts muvaffaqiyatli tayyorlandi!</b>\n"
                f"🎬 Asl video: {title[:60]}"
            )
            return {"ok": True, "task_id": task_id, "clips_sent": sent_count}
        else:
            await _send_message_to_telegram(req.chat_id, "❌ Shorts tayyorlashda xatolik yuz berdi.")
            return JSONResponse({"ok": False, "error": "No clips generated"}, status_code=500)

    except Exception as e:
        logger.error(f"Clipper xatosi (task={task_id}): {e}")
        await _send_message_to_telegram(req.chat_id, f"❌ Shorts kesishda xatolik: {str(e)[:200]}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    finally:
        for f in os.listdir(DOWNLOADS_DIR):
            if task_id in f:
                try: os.remove(os.path.join(DOWNLOADS_DIR, f))
                except: pass


# ==================== ISHGA TUSHIRISH ====================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Worker server ishga tushmoqda: port={port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
