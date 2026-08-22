import os
import random
from dotenv import load_dotenv

load_dotenv()

# ==================== TELEGRAM API ====================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# ==================== TELEGRAM BOT ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ==================== GEMINI AI ====================
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]

_gemini_index = 0
def get_gemini_key():
    """Round-robin Gemini API kaliti (har safar navbatdagisi)"""
    global _gemini_index
    if not GEMINI_KEYS:
        raise ValueError("GEMINI_KEYS topilmadi! .env faylni tekshiring.")
    key = GEMINI_KEYS[_gemini_index % len(GEMINI_KEYS)]
    _gemini_index += 1
    return key

def generate_with_fallback(prompt):
    """Fallback zanjiri bilan Gemini AI orqali kontent yaratish"""
    import google.generativeai as genai
    import asyncio
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-pro-preview",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    
    last_error = None
    genai.configure(api_key=get_gemini_key())
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt)
            if res and res.text:
                return res
        except Exception as e:
            last_error = e
            print(f"[{model_name}] xato: {e}. Keyingi modelga o'tilmoqda...")
            continue
            
    raise Exception(f"Barcha Gemini modellari ishlamay qoldi. Oxirgi xato: {last_error}")

async def generate_with_fallback_async(prompt):
    import asyncio
    return await asyncio.to_thread(generate_with_fallback, prompt)

# ==================== YOUTUBE DATA API ====================
YOUTUBE_API_KEYS = [k.strip() for k in os.getenv("YOUTUBE_API_KEYS", "").split(",") if k.strip()]
# Backward compatibility
YOUTUBE_API_KEY = YOUTUBE_API_KEYS[0] if YOUTUBE_API_KEYS else os.getenv("YOUTUBE_API_KEY", "")

WORKING_YT_KEYS = list(YOUTUBE_API_KEYS)
_yt_index = 0

def get_youtube_key():
    """Round-robin YouTube API kaliti (kvota limit dan qochish uchun)"""
    global _yt_index
    keys_to_use = WORKING_YT_KEYS if WORKING_YT_KEYS else YOUTUBE_API_KEYS
    if not keys_to_use:
        raise ValueError("YOUTUBE_API_KEYS topilmadi!")
    
    key = keys_to_use[_yt_index % len(keys_to_use)]
    _yt_index += 1
    return key

def remove_bad_yt_key(key):
    if key in WORKING_YT_KEYS:
        WORKING_YT_KEYS.remove(key)
        print(f"⚠️ Xato kalit olib tashlandi. Qolgan kalitlar: {len(WORKING_YT_KEYS)}")

def build_youtube_api():
    """YouTube API clientini yaratish (403 quota error bo'lsa keyingi kalitga o'tadi)"""
    from googleapiclient.discovery import build as yt_build
    keys_to_try = list(WORKING_YT_KEYS if WORKING_YT_KEYS else YOUTUBE_API_KEYS)
    last_error = None
    for key in keys_to_try:
        try:
            service = yt_build("youtube", "v3", developerKey=key)
            # Test the key with a lightweight call
            service.videos().list(part="id", id="dQw4w9WgXcQ").execute()
            return service
        except Exception as e:
            err_str = str(e)
            if "quota" in err_str.lower() or "403" in err_str:
                print(f"⚠️ YouTube API Key quota tugadi, keyingi kalitga o'tilmoqda...")
                remove_bad_yt_key(key)
                last_error = e
                continue
            else:
                # Not a quota error - return this service anyway
                return yt_build("youtube", "v3", developerKey=key)
    # All keys exhausted
    raise Exception(f"Barcha YouTube API kalitlarining kvotasi tugagan! Kalitlar soni: {len(YOUTUBE_API_KEYS)}. Oxirgi xato: {last_error}")

def reset_yt_keys():
    global WORKING_YT_KEYS
    WORKING_YT_KEYS = list(YOUTUBE_API_KEYS)



YT_CLIENT_ID = os.getenv("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET", "")

# ==================== DATABASE ====================
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ==================== AUTO-REPLY SOZLAMALARI ====================
REPLY_DELAY_MIN = int(os.getenv("REPLY_DELAY_MIN", "1"))
REPLY_DELAY_MAX = int(os.getenv("REPLY_DELAY_MAX", "4"))

AI_SYSTEM_PROMPT = os.getenv("AI_SYSTEM_PROMPT", 
    "Sen mening shaxsiy yordamchimsan. Men hozir bandman. "
    "Mening o'rnimga kelgan xabarga qisqa, do'stona va o'zbek tilida javob yoz. "
    "Xuddi odam yozgandek tabiiy bo'lsin. Emoji ham ishlat.")

# ==================== OWNER SETTINGS ====================
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ==================== ADMIN (Username orqali) ====================
ADMIN_USERNAME = "WebDev999"  # Asosiy admin username

# ==================== PROXY ====================
DEFAULT_PROXY = os.getenv("DEFAULT_PROXY", "")  # masalan: socks5://user:pass@host:port

# ==================== KUNLIK LIMITLAR ====================
DAILY_LIMIT_USER = 15    # Oddiy foydalanuvchilar uchun kunlik limit
DAILY_LIMIT_ADMIN = 999  # Admin uchun (deyarli cheksiz)

# ==================== MULTI-SERVICE ROUTING (ROLE=main) ====================
# ROLE=main boshqa serverlarga (ROLE=worker/autoposter, ROLE=streamer) vazifa
# yubormoqchi bo'lsa, ularning to'liq HTTP manzillarini shu yerga yoziladi.
# Masalan Render'da: WORKER_URLS=https://myworker.onrender.com,https://myworker2.onrender.com
# Bo'sh qoldirilsa — main hech kimga yubormaydi, faqat DB navbatiga yozadi
# (eski workerlar/streamerlar DB'ni poll qilib baribir oladi, agar ular alohida ishga tushirilgan bo'lsa).
WORKER_URLS = [u.strip().rstrip("/") for u in os.getenv("WORKER_URLS", "").split(",") if u.strip()]
STREAMER_URLS = [u.strip().rstrip("/") for u in os.getenv("STREAMER_URLS", "").split(",") if u.strip()]

# HTTP orqali boshqa serverga /status va /claim-task so'rovlari uchun timeout (soniya)
DISPATCH_HTTP_TIMEOUT = float(os.getenv("DISPATCH_HTTP_TIMEOUT", "4"))

# ROLE=main o'zi bir vaqtda nechta og'ir vazifani (autopost yoki stream) bajaraoladi.
# Tashqi worker/streamer topilmasa yoki hammasi band bo'lsa, shu limitgacha main o'zi ham qiladi.
# 0 qilib qo'ysangiz — main hech qachon o'zi bajarmaydi, faqat DB navbatiga yozadi.
MAIN_MAX_CONCURRENT_TASKS = int(os.getenv("MAIN_MAX_CONCURRENT_TASKS", "1"))