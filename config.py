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
SECONDARY_BOT_TOKEN = os.getenv("SECONDARY_BOT_TOKEN", "").strip()
SECONDARY_BOT_TOKENS = list(
    dict.fromkeys(
        t.strip()
        for t in (os.getenv("SECONDARY_BOT_TOKENS", "") + "," + SECONDARY_BOT_TOKEN).split(",")
        if t.strip() and t.strip() != BOT_TOKEN
    )
)


def get_all_bot_tokens() -> list[str]:
    """Return deduplicated list of configured primary and secondary Telegram bot tokens."""
    candidates = [BOT_TOKEN or os.getenv("BOT_TOKEN", "")]
    if SECONDARY_BOT_TOKEN:
        candidates.append(SECONDARY_BOT_TOKEN)
    env_sec = os.getenv("SECONDARY_BOT_TOKEN", "").strip()
    if env_sec:
        candidates.append(env_sec)
    candidates.extend(SECONDARY_BOT_TOKENS)
    for part in os.getenv("SECONDARY_BOT_TOKENS", "").split(","):
        if part.strip():
            candidates.append(part.strip())
    return list(dict.fromkeys(t.strip() for t in candidates if t and t.strip()))

# ==================== HUMOCARD SMS LISTENER ====================
HUMO_SESSION_STRING = os.getenv("HUMO_SESSION_STRING", "").strip()
HUMO_CARD_NUMBER = os.getenv("HUMO_CARD_NUMBER", "9860 1266 0245 6058").strip()
HUMO_CARD_HOLDER = os.getenv("HUMO_CARD_HOLDER", "Qosimova Umida").strip()

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
        "gemini-flash-latest",
        "gemini-3.8-flash",
        "gemini-flash-lite-latest",
    ]
    
    last_error = None
    genai.configure(api_key=get_gemini_key())
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt, request_options={"timeout": 10})
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
DATABASE_URL = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")

# ==================== AUTO-REPLY SOZLAMALARI ====================
REPLY_DELAY_MIN = int(os.getenv("REPLY_DELAY_MIN", "1"))
REPLY_DELAY_MAX = int(os.getenv("REPLY_DELAY_MAX", "4"))

AI_SYSTEM_PROMPT = os.getenv("AI_SYSTEM_PROMPT", 
    "Sen mening shaxsiy yordamchimsan. Men hozir bandman. "
    "Mening o'rnimga kelgan xabarga qisqa, do'stona va o'zbek tilida javob yoz. "
    "Xuddi odam yozgandek tabiiy bo'lsin. Emoji ham ishlat.")

# ==================== OWNER & ADMIN SETTINGS ====================
OWNER_ID = int(os.getenv("OWNER_ID", "6735799833"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "6735799833"))
ADMIN_IDS = [6735799833] + ([OWNER_ID] if OWNER_ID and OWNER_ID != 6735799833 else [])
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "aiko_64").lstrip("@")  # Asosiy admin username
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "").strip()

def get_admin_secret() -> str:
    """Xavfsiz admin maxfiy kaliti (sukut bo'yicha bo'sh, hardcoded zaxira yo'q)"""
    return os.getenv("ADMIN_SECRET", "").strip()


# ==================== PROXY ====================
DEFAULT_PROXY = os.getenv("DEFAULT_PROXY", "")  # masalan: socks5://user:pass@host:port

# ==================== KUNLIK LIMITLAR ====================
DAILY_LIMIT_USER = 15    # Oddiy foydalanuvchilar uchun kunlik limit
DAILY_LIMIT_ADMIN = 999  # Admin uchun (deyarli cheksiz)

# ==================== WORKER SERVER ====================
# Google Cloud Shell yoki boshqa serverda ishlaydigan Worker API manzili
# Video yuklab olish (yt-dlp) va qayta ishlash (ffmpeg) shu serverda bajariladi
WORKER_API_URL = os.getenv("WORKER_API_URL", "").strip().rstrip("/")

# ==================== BRAND & CUSTOM DOMAIN (MONODECK) ====================
BRAND_NAME = os.getenv("BRAND_NAME", "MonoDeck").strip() or "MonoDeck"
BRAND_TAGLINE = os.getenv(
    "BRAND_TAGLINE",
    "Creator Studio, Telegram Tools & Developer Platform"
).strip() or "Creator Studio, Telegram Tools & Developer Platform"

def _resolve_app_base_url() -> str:
    candidates = (
        os.getenv("APP_BASE_URL"),
        os.getenv("WEB_APP_URL"),
        os.getenv("RENDER_EXTERNAL_URL"),
    )
    for item in candidates:
        clean = str(item or "").strip().rstrip("/")
        if not clean or "botclient-d1jn.onrender.com" in clean.lower():
            continue
        if not clean.startswith(("http://", "https://")):
            clean = "https://" + clean
        return clean
    return "https://monodeck.site"

APP_BASE_URL = _resolve_app_base_url()
WEB_APP_URL = APP_BASE_URL
APP_DOMAIN = APP_BASE_URL.split("://", 1)[-1].split("/", 1)[0]

def get_web_app_url() -> str:
    """Resolve current web URL safely, rejecting legacy botclient-d1jn.onrender.com even in WEB_URL env."""
    for candidate in (
        os.getenv("WEB_URL"),
        os.getenv("APP_BASE_URL"),
        os.getenv("WEB_APP_URL"),
        APP_BASE_URL,
    ):
        clean = str(candidate or "").strip().rstrip("/")
        if not clean or "botclient-d1jn.onrender.com" in clean.lower():
            continue
        if not clean.startswith(("http://", "https://")):
            clean = "https://" + clean
        return clean
    return "https://monodeck.site"

BOT_USERNAME = os.getenv("BOT_USERNAME", "monodeck_app").strip().lstrip("@") or "monodeck_app"
_RUNTIME_BOT_USERNAME = ""

def set_runtime_bot_username(username: str) -> None:
    global _RUNTIME_BOT_USERNAME
    clean = str(username or "").strip().lstrip("@")
    if clean:
        _RUNTIME_BOT_USERNAME = clean

def get_bot_username() -> str:
    return _RUNTIME_BOT_USERNAME or os.getenv("BOT_USERNAME", "").strip().lstrip("@") or BOT_USERNAME

def extract_username_from_me(me_obj) -> str:
    """Pyrogram get_me() dan asosiy username ni olish (Fragment collectible me.usernames ni ham qo'llab-quvvatlaydi)."""
    if not me_obj:
        return get_bot_username()
    direct = str(getattr(me_obj, "username", "") or "").strip().lstrip("@")
    if direct:
        return direct
    usernames = getattr(me_obj, "usernames", None) or []
    for item in usernames:
        uname = str(getattr(item, "username", "") or "").strip().lstrip("@")
        if uname and getattr(item, "active", True):
            return uname
    for item in usernames:
        uname = str(getattr(item, "username", "") or "").strip().lstrip("@")
        if uname:
            return uname
    return get_bot_username()

SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "monodeck_support").strip().lstrip("@") or "monodeck_support"
ADSENSE_CLIENT_ID = os.getenv("ADSENSE_CLIENT_ID", "ca-pub-4094396006908725").strip() or "ca-pub-4094396006908725"

# ==================== CRYPTOPAY, BINANCE & WEBAPP ====================
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "").strip()
BINANCE_UID = os.getenv("BINANCE_UID", "").strip()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
USDT_TRC20_ADDRESS = os.getenv("USDT_TRC20_ADDRESS", "").strip()
USDT_BEP20_ADDRESS = os.getenv("USDT_BEP20_ADDRESS", "").strip()
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "").strip()
TON_WALLET_MEMO = os.getenv("TON_WALLET_MEMO", "").strip()

# ==================== VENTEBOT RESELLER API ====================
VENTEBOT_API_KEY = os.getenv("VENTEBOT_API_KEY", "").strip()
VENTEBOT_BASE_URL = os.getenv("VENTEBOT_BASE_URL", "https://web-production-1c7b1.up.railway.app").rstrip("/")
USD_TO_UZS_RATE = int(os.getenv("USD_TO_UZS_RATE", "12850"))
RESELLER_MARKUP_PERCENT = float(os.getenv("RESELLER_MARKUP_PERCENT", "60.0"))

# ==================== MONO DECK STUDIO CHANNEL & VIP ====================
DEFAULT_STORE_CHANNEL = "@MonoDeckStudio"
STORE_CHANNEL_NAME = (
    os.getenv("STORE_CHANNEL_NAME", "Mono Deck Studio | Checks & News").strip()
    or "Mono Deck Studio | Checks & News"
)
_LEGACY_STORE_CHANNEL_SLUGS = frozenset({"creatorflow_store"})


def normalize_channel_handle(raw: str, default: str = "") -> str:
    """Normalize a Telegram channel handle/URL/ID, replacing legacy @CreatorFlow_Store with default."""
    val = str(raw or "").strip()
    if not val:
        return default
    low = val.lower()
    if low in ("off", "none", "0", "false", "disabled"):
        return ""
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if low.startswith(prefix):
            val = val[len(prefix):].split("?", 1)[0].strip("/")
            low = val.lower()
            break
    slug = val.lstrip("@").strip()
    if not slug or slug.lower() in _LEGACY_STORE_CHANNEL_SLUGS:
        return default
    if slug.lstrip("-").isdigit():
        return slug
    return f"@{slug}"


STORE_CHANNEL = normalize_channel_handle(os.getenv("STORE_CHANNEL", ""), default=DEFAULT_STORE_CHANNEL)


def get_store_channel() -> str:
    """Resolve official Mono Deck Studio channel (@MonoDeckStudio), auto-upgrading stale @CreatorFlow_Store."""
    env_val = os.getenv("STORE_CHANNEL")
    if env_val is not None:
        return normalize_channel_handle(env_val, default=DEFAULT_STORE_CHANNEL)
    return normalize_channel_handle(STORE_CHANNEL, default=DEFAULT_STORE_CHANNEL)


VIP_PRICE_UZS = int(os.getenv("VIP_PRICE_UZS", "69000"))
VIP_PRICE_STARS = int(os.getenv("VIP_PRICE_STARS", "250"))

# ==================== FEATURE TOGGLES ====================
KYC_ENABLED = os.getenv("KYC_ENABLED", "false").lower() in ("true", "1", "yes")
_raw_crypto_enable = os.getenv("ENABLE_CRYPTO_PAY", "").strip().lower()
if _raw_crypto_enable in ("false", "0", "no"):
    ENABLE_CRYPTO_PAY = False
elif _raw_crypto_enable in ("true", "1", "yes"):
    ENABLE_CRYPTO_PAY = True
else:
    ENABLE_CRYPTO_PAY = bool(
        BINANCE_API_KEY
        or CRYPTO_PAY_TOKEN
        or TON_WALLET_ADDRESS
        or USDT_TRC20_ADDRESS
        or USDT_BEP20_ADDRESS
    )
