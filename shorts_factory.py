import os
import asyncio
import tempfile
import yt_dlp
import google.generativeai as genai
import edge_tts
from config import get_gemini_key

TEMP_DIR = tempfile.gettempdir()
BACKGROUND_URL = "https://www.youtube.com/watch?v=n_Dv4JMiwK8"  # Subway Surfers No Copyright
DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
CACHED_BG = os.path.join(DOWNLOADS_DIR, "background_shorts.mp4")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def generate_fact(topic=""):
    genai.configure(api_key=get_gemini_key())
    
    prompt = f"Sen juda qiziqarli faktlar aytib beradigan Youtubersan. 30-40 soniyada o'qiladigan, odamlarni hayratda qoldiradigan bitta qisqa qiziqarli fakt yoz. Format: Faqat fakt matni. Hech qanday salomlashish yoki ortiqcha narsa yozma."
    if topic:
        prompt += f" Mavzu: {topic}"
        
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error with latest: {e}")
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text.strip()
        except Exception as e2:
            print(f"Gemini error with base: {e2}")
            return "Bilasizmi, dunyodagi eng katta cho'l Sahroyi Kabir emas, Antarktida hisoblanadi. Chunki cho'l deganda qurg'oqchilik nazarda tutiladi, Antarktida esa yiliga eng kam yog'ingarchilik bo'ladigan joydir!"

async def ensure_background_video():
    if not os.path.exists(CACHED_BG):
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': CACHED_BG,
            'quiet': False,
            'nocheckcertificate': True
        }
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([BACKGROUND_URL])
        await asyncio.to_thread(download)
    return CACHED_BG

async def create_short(topic=""):
    # 1. Fact
    fact_text = await generate_fact(topic)
    
    # 2. TTS
    tts_path = os.path.join(TEMP_DIR, f"tts_{os.urandom(4).hex()}.mp3")
    communicate = edge_tts.Communicate(fact_text, "uz-UZ-SardorNeural")
    await communicate.save(tts_path)
    
    # 3. BG Video
    bg_path = await ensure_background_video()
    
    # 4. FFmpeg Composite
    out_path = os.path.join(TEMP_DIR, f"short_{os.urandom(4).hex()}.mp4")
    
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_path,
        "-i", tts_path,
        "-filter_complex", 
        "[0:v]crop=ih*(9/16):ih,scale=1080:1920[v1];[v1]drawtext=text='BILASIZMI?':fontcolor=yellow:fontsize=120:x=(w-text_w)/2:y=200:box=1:boxcolor=black@0.5[vout]",
        "-map", "[vout]",
        "-map", "1:a",
        "-shortest",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        out_path
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        print(f"FFmpeg Error: {stderr.decode()}")
        raise Exception("Videoni yaratishda xatolik yuz berdi.")
        
    return out_path, fact_text
