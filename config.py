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

def get_gemini_key():
    """Har safar random Gemini API kalitini qaytaradi (rate limit dan qochish uchun)"""
    if not GEMINI_KEYS:
        raise ValueError("GEMINI_KEYS topilmadi! .env faylni tekshiring.")
    return random.choice(GEMINI_KEYS)

# ==================== YOUTUBE DATA API ====================
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ==================== AUTO-REPLY SOZLAMALARI ====================
REPLY_DELAY_MIN = int(os.getenv("REPLY_DELAY_MIN", "1"))
REPLY_DELAY_MAX = int(os.getenv("REPLY_DELAY_MAX", "4"))

AI_SYSTEM_PROMPT = os.getenv("AI_SYSTEM_PROMPT", 
    "Sen mening shaxsiy yordamchimsan. Men hozir bandman. "
    "Mening o'rnimga kelgan xabarga qisqa, do'stona va o'zbek tilida javob yoz. "
    "Xuddi odam yozgandek tabiiy bo'lsin. Emoji ham ishlat.")

# ==================== OWNER SETTINGS ====================
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # Sizning Telegram ID raqamingiz
