import os
import re
import shutil
import asyncio
import logging
import yt_dlp

logger = logging.getLogger(__name__)

def get_ffmpeg_binary():
    """Tizimda yoki imageio_ffmpeg da mavjud FFmpeg manzilini topadi"""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def is_instagram_url(text: str) -> bool:
    """Berilgan matn Instagram Reels yoki Post havolasimi?"""
    if not text or not isinstance(text, str):
        return False
    pattern = r"https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[A-Za-z0-9_-]+"
    return bool(re.search(pattern, text))


def extract_instagram_url(text: str) -> str:
    """Matndan Instagram havolasini ajratib oladi"""
    if not text:
        return ""
    match = re.search(r"https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[A-Za-z0-9_-]+", text)
    return match.group(0) if match else ""


async def download_instagram_reel(url: str, output_dir: str = "downloads", apply_anti_copyright: bool = True) -> dict:
    """
    Instagram Reels-ni yuklab oladi va avtorlik huquqi (Content ID)
    bloklanishidan saqlash uchun filtrlaydi (FFmpeg pitch/eq/metadata tozalash).
    """
    os.makedirs(output_dir, exist_ok=True)
    clean_url = extract_instagram_url(url) or url

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "insta_raw_%(id)s.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    def _extract_and_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            video_path = ydl.prepare_filename(info)
            if not os.path.exists(video_path):
                # Agar kengaytmasi mp4 bo'lib qolgan bo'lsa
                base, _ = os.path.splitext(video_path)
                if os.path.exists(base + ".mp4"):
                    video_path = base + ".mp4"
            return info, video_path

    try:
        info, raw_path = await asyncio.to_thread(_extract_and_download)
    except Exception as e:
        logger.error(f"Instagram download error: {e}")
        raise RuntimeError(f"Instagram videoni yuklab bo'lmadi: {e}")

    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Yuklangan video fayl topilmadi: {raw_path}")

    video_id = info.get("id", "reel")
    title = info.get("title") or info.get("description") or f"Instagram Reel {video_id}"
    # Qisqartirilgan va tozalangan sarlavha
    title = title.split("\n")[0][:90].strip()
    if not title:
        title = f"Viral Reel #{video_id}"

    processed_path = os.path.join(output_dir, f"insta_clean_{video_id}.mp4")

    if apply_anti_copyright:
        try:
            ffmpeg_exe = get_ffmpeg_binary()
            # Anti-copyright filtrlar:
            # 1. Video: yengil kontrast va to'yinganlik (eq filter)
            # 2. Audio: tezlik va pitch-ni 1.5% o'zgartirish (Content ID audio match chetlab o'tish)
            # 3. Metadatalarni butunlay tozalash (-map_metadata -1)
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", raw_path,
                "-vf", "eq=contrast=1.03:brightness=0.01:saturation=1.04,scale='min(1080,iw)':-2",
                "-af", "atempo=1.02,asetrate=44100*1.015,aresample=44100",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "128k",
                "-map_metadata", "-1",
                processed_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.communicate()

            if os.path.exists(processed_path) and os.path.getsize(processed_path) > 1000:
                # Xom faylni o'chiramiz
                try:
                    os.remove(raw_path)
                except Exception:
                    pass
                final_path = processed_path
            else:
                final_path = raw_path
        except Exception as filter_err:
            logger.warning(f"Anti-copyright filtr xatosi (xom video ishlatiladi): {filter_err}")
            final_path = raw_path
    else:
        final_path = raw_path

    return {
        "video_path": final_path,
        "title": title,
        "description": info.get("description") or title,
        "duration": info.get("duration", 30),
        "thumbnail": info.get("thumbnail"),
        "video_id": video_id,
        "uploader": info.get("uploader", "Instagram Creator"),
    }
