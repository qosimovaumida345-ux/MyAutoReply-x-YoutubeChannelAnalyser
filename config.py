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
        print(f"Xato kalit olib tashlandi. Qolgan kalitlar: {len(WORKING_YT_KEYS)}")

def reset_yt_keys():
    global WORKING_YT_KEYS
    WORKING_YT_KEYS = list(YOUTUBE_API_KEYS)



YT_CLIENT_ID = os.getenv("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET", "")

def get_yt_client_id():
    from database import get_global_setting
    return YT_CLIENT_ID or get_global_setting("YT_CLIENT_ID") or ""

def get_yt_client_secret():
    from database import get_global_setting
    return YT_CLIENT_SECRET or get_global_setting("YT_CLIENT_SECRET") or ""

def refresh_youtube_api_keys():
    from database import get_global_setting
    global WORKING_YT_KEYS, YOUTUBE_API_KEYS
    keys_str = os.getenv("YOUTUBE_API_KEYS", "") or get_global_setting("YOUTUBE_API_KEYS") or ""
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if keys:
        YOUTUBE_API_KEYS = keys
        WORKING_YT_KEYS = list(keys)


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
