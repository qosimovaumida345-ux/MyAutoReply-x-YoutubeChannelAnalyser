"""
100% Free AI Video Generator Engine (OOM-Safe Edition).
Pollinations AI (Flux model) + Edge-TTS + FFmpeg
orqali 0 xarajat bilan to'liq avtomatik 9:16 vertikal Shorts/Reels video yaratish.
Render (512MB RAM, 1 CPU) uchun optimallashtirilgan.
"""

import os
import random
import asyncio
import logging
import urllib.parse
import aiohttp
import edge_tts
from instagram_processor import get_ffmpeg_binary
from config import generate_with_fallback_async

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "uz": "uz-UZ-SardorNeural",
    "ru": "ru-RU-DmitryNeural",
    "en": "en-US-ChristopherNeural",
    "es": "es-ES-AlvaroNeural",
    "tr": "tr-TR-AhmetNeural"
}

# Shorts uchun optimal o'lcham (RAM tejash: 1080x1920 emas)
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280


async def generate_ai_image_pollinations(prompt: str, output_path: str,
                                          width: int = VIDEO_WIDTH,
                                          height: int = VIDEO_HEIGHT) -> bool:
    """Pollinations ochiq API orqali tasvir yaratish (60s timeout, 2 urinish)"""
    encoded_prompt = urllib.parse.quote(prompt)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for attempt in range(2):
        seed = random.randint(1000, 999999)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&nologo=true&seed={seed}"
        )
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if len(content) > 5000:
                            with open(output_path, "wb") as f:
                                f.write(content)
                            return True
                    logger.warning(f"Pollinations urinish {attempt+1}: status {resp.status}")
        except asyncio.TimeoutError:
            logger.warning(f"Pollinations urinish {attempt+1}: timeout (60s)")
        except Exception as e:
            logger.error(f"Pollinations urinish {attempt+1} xato: {e}")
        # 2-urinishda 2 soniya kutish
        if attempt == 0:
            await asyncio.sleep(2)

    return False


async def generate_voiceover_edge(text: str, output_path: str, lang: str = "uz") -> bool:
    """Edge-TTS orqali bepul va jonli ovozli matn yaratish"""
    voice = VOICE_MAP.get(lang, VOICE_MAP["uz"])
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 500
    except Exception as e:
        logger.error(f"Edge-TTS ovoz generatsiya xatosi: {e}")
        return False


async def get_audio_duration(audio_path: str) -> float:
    """Audio fayl davomiyligini aniqlash"""
    ffmpeg_exe = get_ffmpeg_binary()
    ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe_exe):
        size = os.path.getsize(audio_path)
        return max(5.0, min(60.0, size / 16000.0))

    try:
        cmd = [
            ffprobe_exe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await proc.communicate()
        return float(stdout.decode().strip())
    except Exception:
        return 12.0


async def build_ai_short_video(user_prompt: str, lang: str = "uz",
                                output_dir: str = "downloads") -> dict:
    """
    OOM-Safe AI Video Pipeline:
    1. Gemini AI orqali visual prompt va script ssenariysini yozish
    2. Pollinations Flux orqali 720x1280 vertikal kadr olish (2 urinish)
    3. Edge-TTS orqali diktor ovozi yaratish
    4. FFmpeg: rasm + ovoz → MP4 (zoompan OLIB TASHLANDI — OOM oldini olish)
    """
    os.makedirs(output_dir, exist_ok=True)
    task_token = random.randint(10000, 99999)

    # 1. Gemini AI yordamida optimallashtirish
    planning_prompt = f"""
Sen YouTube Shorts va Instagram Reels bo'yicha virusli video mutaxassisisan.
Mavzu: "{user_prompt}"
Til: "{lang}"

Quyidagi formatda aniq 3 ta qismdan iborat matn qaytar (faqat ko'rsatilgan teglarni ishlat):
<TITLE>Qiziqarli CTR yuqori sarlavha</TITLE>
<PROMPT>Photorealistic 8k cinematic hyperrealistic visual prompt for image generation, highly detailed, dramatic lighting, 9:16 vertical composition, masterwork</PROMPT>
<SCRIPT>Ovozli rolik uchun qisqa, hayajonli va qiziqarli 20-30 soniyalik diktor matni (tanlangan tilda)</SCRIPT>
"""
    try:
        res = await generate_with_fallback_async(planning_prompt)
        raw_text = res.text
    except Exception as e:
        logger.warning(f"Gemini planning xato: {e}")
        raw_text = ""

    # Parse
    title = f"Fakt: {user_prompt[:50]} #Shorts"
    visual_prompt = f"cinematic high quality hyperrealistic vertical 9:16 portrait scene of {user_prompt}, unreal engine 5 render"
    script = f"Bilasizmi, {user_prompt}! Bu haqiqatdan ham aqlbovar qilmas fakt."

    if "<TITLE>" in raw_text and "</TITLE>" in raw_text:
        title = raw_text.split("<TITLE>")[1].split("</TITLE>")[0].strip()
    if "<PROMPT>" in raw_text and "</PROMPT>" in raw_text:
        visual_prompt = raw_text.split("<PROMPT>")[1].split("</PROMPT>")[0].strip()
    if "<SCRIPT>" in raw_text and "</SCRIPT>" in raw_text:
        script = raw_text.split("<SCRIPT>")[1].split("</SCRIPT>")[0].strip()

    img_path = os.path.join(output_dir, f"ai_img_{task_token}.jpg")
    audio_path = os.path.join(output_dir, f"ai_audio_{task_token}.mp3")
    final_video = os.path.join(output_dir, f"ai_short_{task_token}.mp4")

    # 2. Rasm generatsiyasi (720x1280 — Shorts uchun optimal)
    img_ok = await generate_ai_image_pollinations(visual_prompt, img_path)
    if not img_ok:
        raise RuntimeError("AI tasvir yaratib bo'lmadi! Pollinations xizmatida muammo.")

    # 3. Ovoz generatsiyasi
    audio_ok = await generate_voiceover_edge(script, audio_path, lang)
    if not audio_ok:
        # Rasm faylini tozalash
        try:
            os.remove(img_path)
        except OSError:
            pass
        raise RuntimeError("AI ovoz yaratib bo'lmadi!")

    duration = await get_audio_duration(audio_path)

    # 4. FFmpeg: Rasm + Ovoz → MP4 (OOM-Safe — zoompan OLIB TASHLANDI)
    # scale+pad: rasmni aniq 720x1280 ga moslashtiradi
    # ultrafast + 1 thread: minimal RAM va CPU sarflaydi
    ffmpeg_exe = get_ffmpeg_binary()
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"format=yuv420p"
    )

    cmd = [
        ffmpeg_exe, "-y",
        "-loop", "1",
        "-i", img_path,
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "26",
        "-threads", "1",
        "-c:a", "aac",
        "-b:a", "96k",
        "-t", str(duration + 0.5),
        "-movflags", "+faststart",
        "-shortest",
        final_video
    ]

    logger.info(f"FFmpeg render boshlandi: {task_token} ({duration:.1f}s audio)")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr_data = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr_data.decode(errors="ignore")[-500:] if stderr_data else "Unknown"
        logger.error(f"FFmpeg render xato (code {proc.returncode}): {err_msg}")

    # Tozalash (rasm va audio)
    for tmp in (img_path, audio_path):
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass

    if not os.path.exists(final_video) or os.path.getsize(final_video) < 5000:
        raise RuntimeError("FFmpeg orqali video render qilib bo'lmadi.")

    logger.info(f"AI Video tayyor: {final_video} ({os.path.getsize(final_video)} bytes)")
    return {
        "video_path": final_video,
        "title": title,
        "description": f"{title}\n\n{script}\n\n#shorts #ai #aivideostudio #viral #trending",
        "duration": duration,
        "script": script
    }
