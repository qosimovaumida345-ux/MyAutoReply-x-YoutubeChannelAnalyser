"""
100% Free AI Video Generator Engine.
Pollinations AI (Flux model) + Edge-TTS + FFmpeg Ken Burns Effect
orqali 0 xarajat bilan to'liq avtomatik 9:16 vertikal Shorts/Reels video yaratish
va 1-bosishda YouTube kanalga yuklash tizimi.
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

async def generate_ai_image_pollinations(prompt: str, output_path: str, width: int = 1080, height: int = 1920) -> bool:
    """Pollinations ochiq API orqali yuqori aniqlikdagi tasvir yaratish"""
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1000, 999999)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    if len(content) > 5000:
                        with open(output_path, "wb") as f:
                            f.write(content)
                        return True
                logger.warning(f"Pollinations javobi: status {resp.status}")
                return False
    except Exception as e:
        logger.error(f"Pollinations rasm yuklashda xato: {e}")
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
        # Taxminiy davomiylik hisobi: fayl hajmiga qarab (128kbps = ~16KB/s)
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

async def build_ai_short_video(user_prompt: str, lang: str = "uz", output_dir: str = "downloads") -> dict:
    """
    To'liq jarayon:
    1. Gemini AI orqali visual prompt va script ssenariysini yozish
    2. Pollinations Flux orqali 9:16 vertikal kadr olish
    3. Edge-TTS orqali diktor ovozi yaratish
    4. FFmpeg orqali dinamik Ken Burns (zoom-pan) animatsiya bilan MP4 formatga birlashtirish
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

    # 2. Rasm generatsiyasi
    img_ok = await generate_ai_image_pollinations(visual_prompt, img_path)
    if not img_ok:
        raise RuntimeError("AI tasvir yaratib bo'lmadi!")

    # 3. Ovoz generatsiyasi
    audio_ok = await generate_voiceover_edge(script, audio_path, lang)
    if not audio_ok:
        raise RuntimeError("AI ovoz yaratib bo'lmadi!")

    duration = await get_audio_duration(audio_path)
    fps = 25
    total_frames = int(duration * fps) + 15

    # 4. FFmpeg Ken Burns Effect (Zoompan 1080x1920)
    ffmpeg_exe = get_ffmpeg_binary()
    vf = (
        f"zoompan=z='min(zoom+0.0015,1.35)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},"
        f"eq=contrast=1.02:saturation=1.05"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-loop", "1",
        "-i", img_path,
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(duration + 0.5),
        "-pix_fmt", "yuv420p",
        "-shortest",
        final_video
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await proc.communicate()

    # Tozalash
    try:
        if os.path.exists(img_path): os.remove(img_path)
        if os.path.exists(audio_path): os.remove(audio_path)
    except: pass

    if not os.path.exists(final_video) or os.path.getsize(final_video) < 5000:
        raise RuntimeError("FFmpeg orqali video render qilib bo'lmadi.")

    return {
        "video_path": final_video,
        "title": title,
        "description": f"{title}\n\n{script}\n\n#shorts #ai #pollinations #viral #trending",
        "duration": duration,
        "script": script
    }
