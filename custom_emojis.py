"""
CreatorFlow Studio & AutoReply AI — Telegram Custom Emoji Master Registry

Ushbu modulda bot, web dashboard va barcha tizimlar uchun 174 ta tasdiqlangan Master Reestr saqlanadi.
Barcha xizmatlar (Instagram, YouTube, Video, Audio, Comment, Support, Dashboard, Web, /goal, /boost),
barcha tovarlar va brendlar (92 ta mahsulot) to'liq qamrab olingan.
Tasdiqlanmagan placeholder IDlar tozalangan. ID bo'lmaganda toza fallback piktogramma qaytariladi.
"""

import random
import re

# ==============================================================================
# 1. ALIASES VA MOSLASHUVCHAN QISQA KALITLAR
# ==============================================================================
ALIASES = {
    "1": "NUM_STEP_1",
    "2": "NUM_STEP_2",
    "3": "NUM_STEP_3",
    "4": "NUM_STEP_4",
    "5": "NUM_STEP_5",
    "ADMIN": "BTN_SETTINGS",
    "AI": "BRAND_CHATGPT",
    "AIVIDEO": "MEDIA_AI_VIDEO",
    "AI_VIDEO": "MEDIA_AI_VIDEO",
    "ALARM": "STATUS_LOADING",
    "ANTIFRAUD_SIREN": "STATUS_SECURITY",
    "API": "DEV_API_KEY",
    "API_DOCS": "DEV_API_DOCS",
    "API_KEY": "DEV_API_KEY",
    "API_KEYS": "DEV_API_KEY",
    "APPLE": "BRAND_APPLE",
    "APPLE_BAD": "GAME_APPLE_BAD",
    "APPLE_BITTEN": "GAME_APPLE_BAD",
    "APPLE_GOOD": "GAME_APPLE_GOOD",
    "APPLE_WHOLE": "GAME_APPLE_GOOD",
    "ART": "BRAND_CANVA",
    "AUDIO": "MEDIA_AUDIO_MP3",
    "AUDIO_MP3": "MEDIA_AUDIO_MP3",
    "AUTOPILOT": "MEDIA_AUTOPILOT",
    "AUTOPOST": "TOOL_AUTOPOST",
    "BACK": "BTN_BACK",
    "BALANCE": "BTN_WALLET",
    "BALANS": "BTN_WALLET",
    "BAN": "STATUS_WARNING",
    "BANK": "PAY_HUMO_UZCARD",
    "BELL": "BTN_SUPPORT",
    "BEP20": "PAY_CRYPTO_USDT",
    "BINANCE": "PAY_BINANCE",
    "BINANCE_PAY": "PAY_BINANCE",
    "BLOCKCHAIN": "PAY_TON_CRYPTO",
    "BLOCKED": "STATUS_WARNING",
    "BNB": "PAY_CRYPTO_USDT",
    "BOLT": "STATUS_LIGHTNING",
    "BOMB": "GAME_MINES_BOMB",
    "BOOST": "TOOL_BOOST",
    "BOT": "MEDIA_AUTOPILOT",
    "BOUQUET": "GIFT_BOUQUET",
    "BOX": "GIFT_CASE_BOX",
    "BRAIN": "BRAND_BRAINFM",
    "BRAINFM": "BRAND_BRAINFM",
    "BSC": "PAY_CRYPTO_USDT",
    "BTN_BACK": "BTN_BACK",
    "BTN_NEXT": "BTN_NEXT",
    "CAKE": "GIFT_CAKE",
    "CALENDAR": "DEV_API_DOCS",
    "CANCEL": "STATUS_ERROR",
    "CANVA": "BRAND_CANVA",
    "CAP": "GIFT_CAP",
    "CAPCUT": "BRAND_CAPCUT",
    "CAPCUT_LOGO": "BRAND_CAPCUT",
    "CARD": "PAY_HUMO_UZCARD",
    "CARD_BACK": "GAME_CARD_BACK",
    "CARD_CLUBS": "GAME_CARD_CLUBS",
    "CARD_DIAMONDS": "GAME_CARD_DIAMONDS",
    "CARD_HEARTS": "GAME_CARD_HEARTS",
    "CARD_JOKER": "BTN_GAMES",
    "CARD_SPADES": "GAME_CARD_SPADES",
    "CART": "BTN_SERVICES",
    "CASH": "PAY_CASHOUT",
    "CASHBACK": "PAY_CASHOUT",
    "CASHOUT": "PAY_CASHOUT",
    "CASINO": "GAME_SLOTS",
    "CHAMPAGNE": "GIFT_CHAMPAGNE",
    "CHANNEL": "MEDIA_YOUTUBE",
    "CHART": "TOOL_CHART_GROWTH",
    "CHATGPT": "BRAND_CHATGPT",
    "CHECK": "STATUS_SUCCESS",
    "CLAUDE": "BRAND_CLAUDE",
    "CLAUDE_CODE": "BRAND_CLAUDE",
    "CLAUDECODE": "BRAND_CLAUDE",
    "CLIPPER": "MEDIA_SCISSORS",
    "CLIPPERS": "MEDIA_SCISSORS",
    "CLONER": "TOOL_IG_CLONER",
    "CODE": "DEV_CODE_SNIPPET",
    "CODEX": "BRAND_CODEX",
    "COIN": "GAME_COINFLIP",
    "COINFLIP": "GAME_COINFLIP",
    "COMMENTS": "TOOL_COMMENTS",
    "CONTENT_ID": "MEDIA_UNIKAL",
    "CRASH_BOOM": "GAME_CRASH_BOOM",
    "CRASH_PLANE": "GAME_CRASH_PLANE",
    "CRASH_ROCKET": "GAME_CRASH_PLANE",
    "CRUNCHYROLL": "BRAND_CRUNCHYROLL",
    "CREATORFLOW_LOGO": "BRAND_CREATORFLOW",
    "CROSS": "STATUS_ERROR",
    "CROWN": "PAY_VIP_CROWN",
    "CRYPTO": "PAY_TON_CRYPTO",
    "CRYPTOBOT": "PAY_CRYPTOBOT",
    "CRYPTO_BOT": "PAY_CRYPTOBOT",
    "CURSOR": "BRAND_CURSOR",
    "DASHBOARD": "BTN_DASHBOARD",
    "DEEPLINK": "TOOL_QR_CODE",
    "DESIGN": "BRAND_FIGMA",
    "DEV": "DEV_API_KEY",
    "DIAMOND_RING": "GIFT_DIAMOND_RING",
    "DOCS": "DEV_API_DOCS",
    "DOCUMENT": "BTN_ORDERS",
    "DOT_GREEN": "STATUS_SUCCESS",
    "DOWNLOAD": "MEDIA_VIDEO_FHD",
    "DUEL": "GAME_COINFLIP",
    "ERROR": "STATUS_ERROR",
    "EXPRESSVPN": "BRAND_EXPRESSVPN",
    "EXPRESS_VPN": "BRAND_EXPRESSVPN",
    "EYE": "TOOL_VIEWS",
    "FIRE": "TOOL_TREND_FIRE",
    "FLUX": "BRAND_CREATORFLOW",
    "FRIENDS": "BTN_REFERRAL",
    "GALLERY": "TOOL_THUMBNAIL",
    "GEM": "GAME_MINES_GEM",
    "GEMINI": "BRAND_GEMINI",
    "GENVIDEO": "MEDIA_AI_VIDEO",
    "GIFT": "GIFT_CASE_BOX",
    "GLOBE": "TOOL_WEB",
    "GOAL": "TOOL_GOAL",
    "GRAPH": "TOOL_CHART_GROWTH",
    "GROK": "BRAND_GROK",
    "GROQ": "BRAND_GROQ",
    "HAMYON": "BTN_WALLET",
    "HANDSHAKE": "BTN_REFERRAL",
    "HEART": "GIFT_HEART",
    "HIGGSFIELD": "BRAND_HIGGSFIELD",
    "HELP": "BTN_SUPPORT",
    "HOME": "BTN_HOME",
    "IDEA": "TOOL_PROMPT_PACK",
    "IG_CLONER": "TOOL_IG_CLONER",
    "INFO": "STATUS_LOADING",
    "INSTA": "MEDIA_INSTAGRAM",
    "INSTAGRAM": "MEDIA_INSTAGRAM",
    "INSTAGRAM_CLONER": "TOOL_IG_CLONER",
    "INSTAGRAM_LOGO": "MEDIA_INSTAGRAM",
    "INVOICE": "PAY_HUMO_UZCARD",
    "KAMI_CRASH": "GAME_CRASH_BOOM",
    "KAMI_LANDING": "GAME_CRASH_PLANE",
    "KAMI_PLANE": "GAME_CRASH_PLANE",
    "KEY": "DEV_API_KEY",
    "LAPTOP": "BRAND_WINDOWS",
    "LEADERBOARD": "BTN_LEADERBOARD",
    "LIGHTNING": "STATUS_LIGHTNING",
    "LIKE": "TOOL_LIKES",
    "LIKES": "TOOL_LIKES",
    "LINK": "TOOL_QR_CODE",
    "LIST": "BTN_ORDERS",
    "LIVE": "TOOL_LIVE_STREAM",
    "LOCK": "STATUS_SECURITY",
    "MARKET": "BTN_SERVICES",
    "MARKETPLACE": "BTN_SERVICES",
    "MASS": "TOOL_MASS_ENGAGEMENT",
    "MASS_COMMENT": "TOOL_MASS_ENGAGEMENT",
    "MASS_ENGAGEMENT": "TOOL_MASS_ENGAGEMENT",
    "MASS_LIKE": "TOOL_MASS_ENGAGEMENT",
    "MASS_SUB": "TOOL_MASS_ENGAGEMENT",
    "MEDAL_BRONZE": "BTN_LEADERBOARD",
    "MEDAL_GOLD": "BTN_LEADERBOARD",
    "MEDAL_SILVER": "BTN_LEADERBOARD",
    "MEMO": "DEV_API_DOCS",
    "MEMO_TAG": "STATUS_WARNING",
    "MERCURY": "BRAND_MERCURY",
    "MUSEAI": "BRAND_MUSEAI",
    "MUSE_AI": "BRAND_MUSEAI",
    "MINES_BOMB": "GAME_MINES_BOMB",
    "MINES_BOOM": "GAME_MINES_BOMB",
    "MINES_GEM": "GAME_MINES_GEM",
    "MINT": "TOOL_TON_NFT",
    "MOBILE": "TOOL_QR_CODE",
    "MONEY": "BTN_WALLET",
    "MP3": "MEDIA_AUDIO_MP3",
    "MYSTERY_BOX": "GIFT_CASE_BOX",
    "NEXT": "BTN_NEXT",
    "NFT": "TOOL_TON_NFT",
    "OK": "STATUS_SUCCESS",
    "OPENROUTER": "BRAND_OPENROUTER",
    "ORDERS": "BTN_ORDERS",
    "PARTY": "STATUS_LIGHTNING",
    "PAYMENT": "PAY_HUMO_UZCARD",
    "PHONE": "TOOL_QR_CODE",
    "PIN": "TOOL_GOAL",
    "PLUS": "STATUS_SUCCESS",
    "PREMIUM": "GIFT_PREMIUM",
    "PRICE_TAG": "TOOL_PRICE_TAG",
    "PROMO": "PAY_PROMOCODE",
    "PROMOCODE": "PAY_PROMOCODE",
    "PROMPTS": "TOOL_PROMPT_PACK",
    "PROMPT_PACK": "TOOL_PROMPT_PACK",
    "PROXY": "BRAND_PROXY_IPV4",
    "QR": "TOOL_QR_CODE",
    "QR_CODE": "TOOL_QR_CODE",
    "QR_DEEPLINK": "TOOL_QR_CODE",
    "REFERRAL": "BTN_REFERRAL",
    "REFRESH": "STATUS_LOADING",
    "RENDER": "MEDIA_VIDEO_FHD",
    "REPLY": "TOOL_COMMENTS",
    "REPORT": "TOOL_CHART_GROWTH",
    "RETRY": "STATUS_LOADING",
    "ROCKET": "GIFT_ROCKET",
    "ROSE": "GIFT_ROSE",
    "SCAN": "TOOL_SEARCH",
    "SCISSORS": "MEDIA_SCISSORS",
    "SCRIPT": "TOOL_SCRIPT",
    "SEARCH": "TOOL_SEARCH",
    "SECURITY": "STATUS_SECURITY",
    "SEO": "TOOL_SEO_TAGS",
    "SEO_TAG": "TOOL_SEO_TAGS",
    "SEO_TAGS": "TOOL_SEO_TAGS",
    "SERVICES": "BTN_SERVICES",
    "SETTINGS": "BTN_SETTINGS",
    "SHIELD": "STATUS_SECURITY",
    "SHORTS": "MEDIA_YOUTUBE",
    "SLOTS": "GAME_SLOTS",
    "SOLD": "STATUS_WARNING",
    "SPARKLES": "STATUS_LIGHTNING",
    "SPOTIFY": "BRAND_SPOTIFY",
    "SPY": "TOOL_SPY",
    "SPY_HAT": "TOOL_SPY",
    "STAR": "PAY_STARS",
    "STARS": "PAY_STARS",
    "STEP1": "NUM_STEP_1",
    "STEP2": "NUM_STEP_2",
    "STEP3": "NUM_STEP_3",
    "STEP4": "NUM_STEP_4",
    "STEP5": "NUM_STEP_5",
    "STOCK": "GIFT_CASE_BOX",
    "STOCK_BOX": "GIFT_CASE_BOX",
    "STOP": "STATUS_WARNING",
    "STORE": "BTN_SERVICES",
    "STREAM": "TOOL_LIVE_STREAM",
    "STREAMING": "BRAND_NETFLIX",
    "STRIPE_ATLAS": "BRAND_STRIPE_ATLAS",
    "STRIPEATLAS": "BRAND_STRIPE_ATLAS",
    "SURFSHARK": "BRAND_SURFSHARK",
    "SUBS": "TOOL_SUBS",
    "SUCCESS": "STATUS_SUCCESS",
    "SUPPORT": "BTN_SUPPORT",
    "TAGS": "TOOL_SEO_TAGS",
    "TAG_PRICE": "TOOL_PRICE_TAG",
    "TARGET": "TOOL_GOAL",
    "TEDDY": "GIFT_TEDDY",
    "THUMBIDEA": "TOOL_THUMBNAIL",
    "THUMBNAIL": "TOOL_THUMBNAIL",
    "TICKET": "PAY_PROMOCODE",
    "TIMER": "STATUS_LOADING",
    "TON": "PAY_TON_CRYPTO",
    "TONKEEPER": "PAY_TON_CRYPTO",
    "TON_NFT": "TOOL_TON_NFT",
    "TOOL_CALENDAR": "DEV_API_DOCS",
    "TOOL_COMMENTS": "TOOL_COMMENTS",
    "TOOL_EYE_VIEWS": "TOOL_VIEWS",
    "TOOL_FIRE": "TOOL_TREND_FIRE",
    "TOOL_GRAPH_UP": "TOOL_CHART_GROWTH",
    "TOOL_HEART_LIKE": "TOOL_LIKES",
    "TOOL_MIC_VOICE": "BRAND_ELEVENLABS",
    "TOOL_SPY_ANALYTICS": "TOOL_SPY",
    "TOOL_TAG_PRICE": "TOOL_PRICE_TAG",
    "TOOL_VIP_STAR": "PAY_VIP_CROWN",
    "TRANSCRIPT": "MEDIA_SUBTITLES",
    "TRC20": "PAY_CRYPTO_USDT",
    "TRON": "PAY_CRYPTO_USDT",
    "TROPHY": "GIFT_TROPHY",
    "TV": "MEDIA_YOUTUBE",
    "TXID": "DEV_API_DOCS",
    "TX_HASH": "DEV_API_DOCS",
    "UNIKAL": "MEDIA_UNIKAL",
    "USER": "BTN_REFERRAL",
    "UZCARD": "PAY_HUMO_UZCARD",
    "VERIFIED": "STATUS_SUCCESS",
    "VIDEO": "MEDIA_VIDEO_FHD",
    "VIDEO_FHD": "MEDIA_VIDEO_FHD",
    "VIDEO_HD": "MEDIA_VIDEO_HD",
    "VIEWS": "TOOL_VIEWS",
    "VIP": "PAY_VIP_CROWN",
    "VIP_STAR": "PAY_VIP_CROWN",
    "VOICE": "BRAND_ELEVENLABS",
    "VPN_SECURITY": "BRAND_NORDVPN",
    "WAIT": "STATUS_LOADING",
    "WALLET": "BTN_WALLET",
    "WALLET_CONNECT": "PAY_TON_CRYPTO",
    "WARN": "STATUS_WARNING",
    "WARNING": "STATUS_WARNING",
    "WEB": "TOOL_WEB",
    "WEBHOOK": "DEV_WEBHOOK",
    "WHEEL": "GAME_WHEEL_SPIN",
    "WAKINGUP": "BRAND_WAKINGUP",
    "WAKING_UP": "BRAND_WAKINGUP",
    "WINDOWS": "BRAND_WINDOWS",
    "YOUTUBE": "MEDIA_YOUTUBE",
    "OFFICE": "BRAND_OFFICE365",
    "OFFICE_EDU": "BRAND_OFFICE365",
    "DESIGN_VIDEO": "BRAND_CAPCUT",
    "DEV_TOOLS": "DEV_CODE_SNIPPET",
    "MEDIA_STREAMING": "BRAND_NETFLIX",
}

# ==============================================================================
# 2. REESTR KALITINI REZOLYUTSIYA QILISH
# ==============================================================================
def resolve_registry_key(key: str) -> str:
    """Berilgan kalit yoki aliasdan asosiy registrdagi kalitlardan birini aniqlaydi."""
    k_str = str(key).strip()
    visited = set()
    while k_str in ALIASES or k_str.upper() in ALIASES:
        if k_str in visited:
            break
        visited.add(k_str)
        if k_str in ALIASES:
            k_str = ALIASES[k_str]
        elif k_str.upper() in ALIASES:
            k_str = ALIASES[k_str.upper()]
    if k_str.upper() != k_str:
        upper_k = k_str.upper()
        if upper_k in ALIASES:
            return ALIASES[upper_k]
        return upper_k
    return k_str

# ==============================================================================
# 3. MASTER REGISTRY DICT SINF
# ==============================================================================
class MasterRegistryDict(dict):
    """
    166 ta Master Reestr lug'ati.
    Tizimdagi eski nomlar, aliaslar va kichik/katta harflar uchun shaffof avtomatik rezolyutsiya bilan ta'minlangan.
    """
    def _find_key(self, key):
        if key is None:
            return None
        k_str = str(key).strip()
        if super().__contains__(k_str):
            return k_str
        k_upper = k_str.upper()
        if super().__contains__(k_upper):
            return k_upper
        resolved = resolve_registry_key(k_str)
        if super().__contains__(resolved):
            return resolved
        res_upper = str(resolved).strip().upper()
        if super().__contains__(res_upper):
            return res_upper
        return None

    def __contains__(self, key):
        return self._find_key(key) is not None

    def __getitem__(self, key):
        matched = self._find_key(key)
        if matched is not None:
            return super().__getitem__(matched)
        return super().__getitem__(key)

    def get(self, key, default=None):
        matched = self._find_key(key)
        if matched is not None:
            return super().get(matched, default)
        return default

# ==============================================================================
# 4. ASOSIY 174 TA CUSTOM EMOJI MASTER REESTRI
# ==============================================================================
CUSTOM_EMOJI_REGISTRY = MasterRegistryDict({
    "BTN_HOME": {
        "num": 1,
        "name": "Bosh Menyu",
        "location": "Asosiy bot menyusi va barcha bo'limlardan bosh sahifaga qaytish",
        "purpose": "Foydalanuvchini bosh sahifaga qaytarish",
        "id": "5253733764609097441",
        "fallback_name": "[Bosh Menyu]",
        "fallback_icon": "🏠"
    },
    "BTN_SERVICES": {
        "num": 2,
        "name": "Xizmatlar / Do'kon",
        "location": "Marketplace, xizmatlar do'koni va mahsulotlar menyusi",
        "purpose": "Raqamli xizmatlar va obunalar katalogini ochish",
        "id": "5202075822118166834",
        "fallback_name": "[Xizmatlar]",
        "fallback_icon": "💸"
    },
    "BTN_WALLET": {
        "num": 3,
        "name": "Hamyon va Balans",
        "location": "Hisobni to'ldirish, balansni tekshirish, pul yechish",
        "purpose": "Foydalanuvchi hisob-kitob bo'limini ko'rsatish",
        "id": "5215420556089776398",
        "fallback_name": "[Balans]",
        "fallback_icon": "💰"
    },
    "BTN_GAMES": {
        "num": 4,
        "name": "O'yinlar va Mini-App",
        "location": "Mini-o'yinlar, Keyslar, Fortune g'ildiragi va kazino",
        "purpose": "O'yinlar va yutuqli sovrinlar markaziga o'tish",
        "id": "5258508428212445001",
        "fallback_name": "[O'yinlar]",
        "fallback_icon": "🎮"
    },
    "BTN_ORDERS": {
        "num": 5,
        "name": "Mening Xaridlarim",
        "location": "Foydalanuvchining faol va bajarilgan buyurtmalari ro'yxati",
        "purpose": "Xarid qilingan kalitlar va tovarlarni ko'rish",
        "id": "5436261671301564151",
        "fallback_name": "[Xaridlarim]",
        "fallback_icon": "📋"
    },
    "BTN_REFERRAL": {
        "num": 6,
        "name": "Do'stlar / Referal",
        "location": "Taklif havolasi, referal daromadlari va do'stlar statistikasi",
        "purpose": "Do'stlarni taklif qilib bonus olish bo'limi",
        "id": "5388670457249552219",
        "fallback_name": "[Referal]",
        "fallback_icon": "👥"
    },
    "BTN_LEADERBOARD": {
        "num": 7,
        "name": "Liderlar Jadvali / Reyting",
        "location": "Eng ko'p xarid qilganlar va sovrindorlar ro'yxati",
        "purpose": "Foydalanuvchilar o'rtasida reyting va sovrinlar",
        "id": "5226431245918942763",
        "fallback_name": "[Liderlar]",
        "fallback_icon": "🏆"
    },
    "BTN_SUPPORT": {
        "num": 8,
        "name": "Qo'llab-quvvatlash / Admin",
        "location": "Texnik yordam, admin bilan jonli chat va savol-javob",
        "purpose": "Foydalanuvchi muammolarini hal qilish",
        "id": "5307746710682869587",
        "fallback_name": "[Yordam]",
        "fallback_icon": "🎧"
    },
    "BTN_SETTINGS": {
        "num": 9,
        "name": "Sozlamalar",
        "location": "Til sozlamalari, bildirishnomalar va profil boshqaruvi",
        "purpose": "Bot va akkaunt parametrlarini sozlash",
        "id": "5341715473882955310",
        "fallback_name": "[Sozlamalar]",
        "fallback_icon": "⚙️"
    },
    "BTN_DASHBOARD": {
        "num": 10,
        "name": "Web Dashboard",
        "location": "CreatorFlow Web Studio va tahlil oynasini ochish",
        "purpose": "Web Mini-App orqali boshqarish",
        "id": "6327577233305112811",
        "fallback_name": "[Dashboard]",
        "fallback_icon": "📊"
    },
    "BTN_BACK": {
        "num": 11,
        "name": "Orqaga Qaytish",
        "location": "Katalog va sahifalarda orqaga qaytish tugmasi",
        "purpose": "Oldingi sahifaga qaytish",
        "id": "5416113713428057601",
        "fallback_name": "[Orqaga]",
        "fallback_icon": "⬅️"
    },
    "BTN_NEXT": {
        "num": 12,
        "name": "Keyingi Sahifa",
        "location": "Katalog va sahifalarda oldinga o'tish tugmasi",
        "purpose": "Keyingi sahifani ochish",
        "id": "5415758949129404605",
        "fallback_name": "[Keyingi]",
        "fallback_icon": "➡️"
    },
    "NUM_STEP_1": {
        "num": 13,
        "name": "1-Qadam",
        "location": "Qo'llanmalar va bosqichli ko'rsatmalar 1-qadami",
        "purpose": "1-bosqichni bildirish",
        "id": "5235776368905562305",
        "fallback_name": "[1]",
        "fallback_icon": "1️⃣"
    },
    "NUM_STEP_2": {
        "num": 14,
        "name": "2-Qadam",
        "location": "Qo'llanmalar va bosqichli ko'rsatmalar 2-qadami",
        "purpose": "2-bosqichni bildirish",
        "id": "5237704680372447424",
        "fallback_name": "[2]",
        "fallback_icon": "2️⃣"
    },
    "NUM_STEP_3": {
        "num": 15,
        "name": "3-Qadam",
        "location": "Qo'llanmalar va bosqichli ko'rsatmalar 3-qadami",
        "purpose": "3-bosqichni bildirish",
        "id": "5238044171767393675",
        "fallback_name": "[3]",
        "fallback_icon": "3️⃣"
    },
    "NUM_STEP_4": {
        "num": 16,
        "name": "4-Qadam",
        "location": "Qo'llanmalar va bosqichli ko'rsatmalar 4-qadami",
        "purpose": "4-bosqichni bildirish",
        "id": "5235533321001250232",
        "fallback_name": "[4]",
        "fallback_icon": "4️⃣"
    },
    "NUM_STEP_5": {
        "num": 17,
        "name": "5-Qadam",
        "location": "Qo'llanmalar va bosqichli ko'rsatmalar 5-qadami",
        "purpose": "5-bosqichni bildirish",
        "id": "5238171599152097811",
        "fallback_name": "[5]",
        "fallback_icon": "5️⃣"
    },
    "PAY_STARS": {
        "num": 18,
        "name": "Telegram Stars To'lovi",
        "location": "Keys ochish, xizmat sotib olish va stars to'lovlari",
        "purpose": "Telegram rasmiy yulduzlari orqali to'lov",
        "id": "5267500801240092311",
        "fallback_name": "[Stars]",
        "fallback_icon": "⭐"
    },
    "PAY_HUMO_UZCARD": {
        "num": 19,
        "name": "Humo / Uzcard To'lovi",
        "location": "O'zbekiston milliy to'lov tizimlari orqali hisob to'ldirish",
        "purpose": "So'm orqali avtomatik to'lov",
        "id": "5393180954594385587",
        "fallback_name": "[Humo/Uzcard]",
        "fallback_icon": "💳"
    },
    "PAY_TON_CRYPTO": {
        "num": 20,
        "name": "TON / Kripto To'lovi",
        "location": "Telegram TON tarmog'i va Tonkeeper orqali to'lov",
        "purpose": "Kriptovalyuta tranzaksiyalari",
        "id": "5078343973303485905",
        "fallback_name": "[TON]",
        "fallback_icon": "💎"
    },
    "PAY_CRYPTO_USDT": {
        "num": 21,
        "name": "Tether USDT Kripto",
        "location": "USDT TRC20 / TON tarmog'idagi stabil kripto to'lovlari",
        "purpose": "Xalqaro stabil kripto to'lovlar",
        "id": "5345889288741461772",
        "fallback_name": "[USDT]",
        "fallback_icon": "💵"
    },
    "PAY_BINANCE": {
        "num": 175,
        "name": "Binance / Binance Pay",
        "location": "Binance Pay UID va Binance birjasi orqali to'lov",
        "purpose": "Binance Pay va Read-Only depozitlar nishoni",
        "id": "",
        "fallback_name": "[Binance]",
        "fallback_icon": "🟡"
    },
    "PAY_CRYPTOBOT": {
        "num": 176,
        "name": "@CryptoBot Avto-To'lov",
        "location": "Telegram @CryptoBot (Crypto Pay) tezkor hisob-fakturasi",
        "purpose": "CryptoBot mini-ilova to'lov tugmasi",
        "id": "",
        "fallback_name": "[CryptoBot]",
        "fallback_icon": "🤖"
    },
    "PAY_PROMOCODE": {
        "num": 22,
        "name": "Promokod / Vafcher",
        "location": "Promokodlarni kiritish va bepul balans olish",
        "purpose": "Chegirma yoki bonus taqdim etish",
        "id": "5812264501625491266",
        "fallback_name": "[Promokod]",
        "fallback_icon": "🎟️"
    },
    "PAY_CASHOUT": {
        "num": 23,
        "name": "Pul Yechib Olish",
        "location": "Yutuqlar va referal pullarini kartaga yoki TON ga chiqarish",
        "purpose": "Hisobdan mablag' yechish so'rovi",
        "id": "5472250091332993630",
        "fallback_name": "[Yechish]",
        "fallback_icon": "📤"
    },
    "PAY_VIP_CROWN": {
        "num": 24,
        "name": "VIP Obuna Toji",
        "location": "Premium foydalanuvchilar va VIP klub nishoni",
        "purpose": "VIP imtiyozlarni ko'rsatish",
        "id": "5229011542011299168",
        "fallback_name": "[VIP]",
        "fallback_icon": "👑"
    },
    "STATUS_SUCCESS": {
        "num": 25,
        "name": "Muvaffaqiyat / Tasdiq",
        "location": "Barcha muvaffaqiyatli amallar, xaridlar va to'lovlar",
        "purpose": "Operatsiya to'g'ri bajarilganini bildirish",
        "id": "5980930633298350051",
        "fallback_name": "[OK]",
        "fallback_icon": "✅"
    },
    "STATUS_ERROR": {
        "num": 26,
        "name": "Xatolik / Rad Etildi",
        "location": "Xatolik yuz berganda, balans yetmaganda yoki bloklanganda",
        "purpose": "Xatoni darhol foydalanuvchiga bildirish",
        "id": "5337248355707794559",
        "fallback_name": "[Xato]",
        "fallback_icon": "❌"
    },
    "STATUS_WARNING": {
        "num": 27,
        "name": "Ogohlantirish / Diqqat",
        "location": "Muhim qoidalar, zaxirada yo'q tovarlar va ogohlantirishlar",
        "purpose": "Foydalanuvchini ehtiyotkorlikka chaqirish",
        "id": "5787656288934564517",
        "fallback_name": "[Diqqat]",
        "fallback_icon": "⚠️"
    },
    "STATUS_LIGHTNING": {
        "num": 28,
        "name": "Tezkor / Jonli Chaqmoq",
        "location": "Tezkor yetkazib berish, jonli o'yinlar va chaqmoq bildirishnomalar",
        "purpose": "Tezkorlik va faollikni ifodalash",
        "id": "5456140674028019486",
        "fallback_name": "[Tezkor]",
        "fallback_icon": "⚡"
    },
    "STATUS_LOADING": {
        "num": 29,
        "name": "Yuklanmoqda / Kutilmoqda",
        "location": "Fayllar yuklanayotganda, so'rov yuborilganda va tekshirilganda",
        "purpose": "Jarayon davom etayotganini ko'rsatish",
        "id": "5325919653615115810",
        "fallback_name": "[Yuklanmoqda]",
        "fallback_icon": "⏳"
    },
    "STATUS_SECURITY": {
        "num": 30,
        "name": "Xavfsizlik / Qalqon",
        "location": "Antifraud, himoyalangan to'lovlar va xavfsizlik nazorati",
        "purpose": "Xavfsizlik darajasini tasdiqlash",
        "id": "5330194932781050507",
        "fallback_name": "[Himoya]",
        "fallback_icon": "🛡️"
    },
    "MEDIA_VIDEO_FHD": {
        "num": 31,
        "name": "Full HD Video (1080p)",
        "location": "Video yuklab olish, 1080p va 4K format tanlovi",
        "purpose": "Yuqori sifatli video formatini ko'rsatish",
        "id": "5082592692391641768",
        "fallback_name": "[1080p]",
        "fallback_icon": "🎬"
    },
    "MEDIA_VIDEO_HD": {
        "num": 32,
        "name": "HD Video (720p)",
        "location": "Tezkor video yuklash, 720p formati",
        "purpose": "O'rtacha sifatli video formatini ifodalash",
        "id": "5334867784184641928",
        "fallback_name": "[720p]",
        "fallback_icon": "📹"
    },
    "MEDIA_AUDIO_MP3": {
        "num": 33,
        "name": "MP3 Audio Format",
        "location": "Videodan musiqa ajratish va MP3 yuklash",
        "purpose": "Musiqiy faylni ifodalash",
        "id": "5194988065222831801",
        "fallback_name": "[MP3]",
        "fallback_icon": "🎵"
    },
    "MEDIA_SCISSORS": {
        "num": 34,
        "name": "Qirqish / Montaj Qaychisi",
        "location": "Video kesish, montaj qilish va bo'laklarga ajratish",
        "purpose": "Montaj funksiyalarini ko'rsatish",
        "id": "5422781517011111694",
        "fallback_name": "[Qirqish]",
        "fallback_icon": "✂️"
    },
    "MEDIA_AUTOPILOT": {
        "num": 35,
        "name": "Autopilot / Avtomatika",
        "location": "Avtomatik kontent yaratish, avtoposting va robot",
        "purpose": "To'liq avtomatlashtirish funksiyasi",
        "id": "5287684458881756303",
        "fallback_name": "[Autopilot]",
        "fallback_icon": "🤖"
    },
    "MEDIA_UNIKAL": {
        "num": 36,
        "name": "Video Unikalizatsiya & Content ID",
        "location": "Video unikalizatsiya va Content ID cheklovlarini aylanib o'tish filtrlari",
        "purpose": "Video mualliflik huquqi filtrlari va Content ID bypass",
        "id": "5301096984617166561",
        "fallback_name": "[Unikal]",
        "fallback_icon": "🪄"
    },
    "MEDIA_AI_VIDEO": {
        "num": 37,
        "name": "AI Video Generator (/aivideo)",
        "location": "Pollinations va Edge-TTS orqali avtomatik AI video va shorts yaratish",
        "purpose": "100% tekin sun'iy intellekt video yaratish vositasi",
        "id": "5846005794767639663",
        "fallback_name": "[AIVideo]",
        "fallback_icon": "🎥"
    },
    "MEDIA_YOUTUBE": {
        "num": 38,
        "name": "YouTube Integratsiyasi",
        "location": "YouTube tahlillari, avtopost va yuklash funksiyalari",
        "purpose": "YouTube platformasini ifodalash",
        "id": "5334681713316479679",
        "fallback_name": "[YouTube]",
        "fallback_icon": "▶️"
    },
    "MEDIA_INSTAGRAM": {
        "num": 39,
        "name": "Instagram Platformasi",
        "location": "Instagram Reels, Stories va postlarni yuklash / klonlash",
        "purpose": "Instagram tarmog'ini ifodalash",
        "id": "5319160079465857105",
        "fallback_name": "[Instagram]",
        "fallback_icon": "📸"
    },
    "TOOL_VIEWS": {
        "num": 40,
        "name": "Ko'rishlar / Views Xizmati",
        "location": "YouTube va Instagram ko'rishlar sonini oshirish xizmati",
        "purpose": "SMM ko'rishlar xizmati",
        "id": "5233246225146332642",
        "fallback_name": "[Views]",
        "fallback_icon": "👁️"
    },
    "TOOL_LIKES": {
        "num": 41,
        "name": "Layklar / Likes Xizmati",
        "location": "YouTube va Instagram postlariga layk to'plash xizmati",
        "purpose": "SMM layklar xizmati",
        "id": "5255965021594203933",
        "fallback_name": "[Likes]",
        "fallback_icon": "❤️"
    },
    "TOOL_SUBS": {
        "num": 42,
        "name": "Obunachilar / Subscribers",
        "location": "YouTube kanallari va sahifalarga jonli obunachilar yig'ish",
        "purpose": "SMM obunachilar xizmati",
        "id": "5386462779634885842",
        "fallback_name": "[Obunachilar]",
        "fallback_icon": "🔔"
    },
    "TOOL_COMMENTS": {
        "num": 43,
        "name": "Izohlar / AI Replies",
        "location": "Avtomatik AI va foydalanuvchi izohlari yozish xizmati",
        "purpose": "SMM va AI izohlar xizmati",
        "id": "5443038326535759644",
        "fallback_name": "[Izohlar]",
        "fallback_icon": "💬"
    },
    "TOOL_MASS_ENGAGEMENT": {
        "num": 44,
        "name": "Ommaviy Faollik (Mass)",
        "location": "Mass like, mass comment va ommaviy jalb qilish tizimi",
        "purpose": "Keng ko'lamli faollik xizmati",
        "id": "5203993413346680064",
        "fallback_name": "[Ommaviy]",
        "fallback_icon": "👥"
    },
    "TOOL_LIVE_STREAM": {
        "num": 45,
        "name": "24/7 Jonli Efir (Stream)",
        "location": "YouTube kanallarda 24/7 uzluksiz video strim qilish xizmati",
        "purpose": "Jonli translatsiya xizmati",
        "id": "5316575093269214796",
        "fallback_name": "[Stream]",
        "fallback_icon": "📡"
    },
    "TOOL_AUTOPOST": {
        "num": 46,
        "name": "Rejali Avtoposting",
        "location": "Reja bo'yicha post va videolarni avtomatik joylashtirish",
        "purpose": "Avtomatik kontent chiqarish",
        "id": "5262540380301191210",
        "fallback_name": "[Avtopost]",
        "fallback_icon": "⏰"
    },
    "TOOL_SEO_TAGS": {
        "num": 47,
        "name": "YouTube SEO Teglar",
        "location": "Video uchun yuqori reytingli teglar va kalit so'zlar",
        "purpose": "SEO optimallashtirish xizmati",
        "id": "5298877105000439431",
        "fallback_name": "[SEO]",
        "fallback_icon": "🏷️"
    },
    "TOOL_SPY": {
        "num": 48,
        "name": "Raqobatchilar Tahlili (Spy)",
        "location": "Raqobatchi kanallar statistikasi va yashirin teglarni o'g'irlash",
        "purpose": "Ayg'oqchi tahlil vositasi",
        "id": "5818800823374713651",
        "fallback_name": "[Spy]",
        "fallback_icon": "🕵️"
    },
    "TOOL_IG_CLONER": {
        "num": 49,
        "name": "Instagram Auto-Cloner & Reposter",
        "location": "Instagram akkauntlarini avtomatik klonlash va 8 qatlamli repost",
        "purpose": "Avtomatik Instagram klonlash xizmati",
        "id": "5319160079465857105",
        "fallback_name": "[IGCloner]",
        "fallback_icon": "🔄"
    },
    "TOOL_THUMBNAIL": {
        "num": 50,
        "name": "YouTube Muqova (Thumbnail)",
        "location": "Video uchun yuqori CTR li professional muqovalar (/thumbnail)",
        "purpose": "YouTube thumbnail va muqovalar yaratish",
        "id": "5334681713316479679",
        "fallback_name": "[Thumbnail]",
        "fallback_icon": "🖼️"
    },
    "TOOL_SCRIPT": {
        "num": 51,
        "name": "AI Ssenariy & Scriptwriter (/script)",
        "location": "Video ssenariylari, ovoz matnlari va YouTube tavsiflarini yozish",
        "purpose": "AI asosida video ssenariylar tuzish",
        "id": "5837003105228558796",
        "fallback_name": "[Script]",
        "fallback_icon": "📜"
    },
    "TOOL_PROMPT_PACK": {
        "num": 52,
        "name": "500+ Viral Prompts & SEO Tags",
        "location": "Virusli sarlavhalar, retention hooklar va SEO qoliplari to'plami",
        "purpose": "YouTube va Reels uchun tayyor viral promptlar",
        "id": "5323289282499064033",
        "fallback_name": "[Prompts]",
        "fallback_icon": "💡"
    },
    "TOOL_GOAL": {
        "num": 53,
        "name": "Maqsad va Target (/goal)",
        "location": "Kanal obunachilari va ko'rishlar maqsadini belgilash (/goal)",
        "purpose": "Maqsadga erishish nishoni",
        "id": "6287439449664000621",
        "fallback_name": "[Goal]",
        "fallback_icon": "🎯"
    },
    "TOOL_BOOST": {
        "num": 54,
        "name": "Tezlashtirish va Raketa (/boost)",
        "location": "Kanal va postlarni yuqori pog'onaga tezkor ko'tarish (/boost)",
        "purpose": "Boost tezlashtirish xizmati",
        "id": "5422577888316641396",
        "fallback_name": "[Boost]",
        "fallback_icon": "🚀"
    },
    "TOOL_SEARCH": {
        "num": 55,
        "name": "Qidiruv Vositasi",
        "location": "Katalog, buyurtmalar va mahsulotlar ichidan qidirish",
        "purpose": "Tezkor izlash",
        "id": "5429419796988970289",
        "fallback_name": "[Qidiruv]",
        "fallback_icon": "🔍"
    },
    "TOOL_TREND_FIRE": {
        "num": 56,
        "name": "Trenddagi / Olov",
        "location": "Top mahsulotlar, qizg'in takliflar va trendlar",
        "purpose": "Eng xaridorgir narsalarni ko'rsatish",
        "id": "5334725814040674667",
        "fallback_name": "[Trend]",
        "fallback_icon": "🔥"
    },
    "TOOL_CHART_GROWTH": {
        "num": 57,
        "name": "O'sish Grafigi",
        "location": "YouTube statistikasi, daromadlar va so'rovlar grafigi",
        "purpose": "Ko'rsatkichlar o'sishini ifodalash",
        "id": "6154657967317717391",
        "fallback_name": "[O'sish]",
        "fallback_icon": "📈"
    },
    "TOOL_QR_CODE": {
        "num": 58,
        "name": "QR Kod va Deeplink",
        "location": "To'lovlar, avtorizatsiya va referal uchun QR kodlar",
        "purpose": "Tezkor skanerlash",
        "id": "5422814644093868925",
        "fallback_name": "[QR]",
        "fallback_icon": "📱"
    },
    "TOOL_PRICE_TAG": {
        "num": 59,
        "name": "Narx Belgisi",
        "location": "Mahsulot narxi va tariflarini belgilash",
        "purpose": "Narxni ko'rsatish",
        "id": "5298877105000439431",
        "fallback_name": "[Narx]",
        "fallback_icon": "🏷️"
    },
    "TOOL_WEB": {
        "num": 60,
        "name": "Web Studio / Internet",
        "location": "Web mini app va tashqi web integratsiyalar",
        "purpose": "Internet va Web vositalari",
        "id": "6327577233305112811",
        "fallback_name": "[Web]",
        "fallback_icon": "🌐"
    },
    "TOOL_TON_NFT": {
        "num": 61,
        "name": "TON NFT Sertifikati (/nft)",
        "location": "The Open Network (TON) blokcheynida rasmiy egalik NFT sertifikati",
        "purpose": "TON blokcheyn NFT yaratish va tekshirish",
        "id": "5265151230790884988",
        "fallback_name": "[NFT]",
        "fallback_icon": "💎"
    },
    "GIFT_CASE_BOX": {
        "num": 62,
        "name": "Mystery Keys Qutisi",
        "location": "Keyslar ro'yxati va unboxing animatsiyalari",
        "purpose": "Keys ochish o'yinini bildirish",
        "id": "5280615440928758599",
        "fallback_name": "[Keys]",
        "fallback_icon": "📦"
    },
    "GIFT_STAR": {
        "num": 63,
        "name": "Telegram Yulduz Sovg'asi",
        "location": "Keyslardan tushadigan Telegram yulduz sovg'asi",
        "purpose": "Yulduzli sovg'a yutug'i",
        "id": "5954135079662916434",
        "fallback_name": "[Yulduz]",
        "fallback_icon": "⭐"
    },
    "GIFT_CAKE": {
        "num": 64,
        "name": "Tug'ilgan Kun Torti",
        "location": "Bronze va Silver keyslardagi mazali tort sovg'asi",
        "purpose": "Klassik Telegram sovg'asini ifodalash",
        "id": "5452055425690123301",
        "fallback_name": "[Tort]",
        "fallback_icon": "🎂"
    },
    "GIFT_TEDDY": {
        "num": 65,
        "name": "Ayiqcha O'yinchoq",
        "location": "Kolleksion Telegram o'yinchoq ayiqchasi",
        "purpose": "Noyob sovg'a yutug'i",
        "id": "5280598054901145762",
        "fallback_name": "[Ayiqcha]",
        "fallback_icon": "🧸"
    },
    "GIFT_BOUQUET": {
        "num": 66,
        "name": "Guldasta Sovg'asi",
        "location": "Chiroyli guldasta Telegram sovg'asi",
        "purpose": "Sovg'alar kolleksiyasi",
        "id": "5226914197811518558",
        "fallback_name": "[Guldasta]",
        "fallback_icon": "💐"
    },
    "GIFT_ROSE": {
        "num": 67,
        "name": "Qizil Atirgul",
        "location": "Nafis atirgul sovg'asi",
        "purpose": "Telegram sovg'asi",
        "id": "5363938656874673963",
        "fallback_name": "[Atirgul]",
        "fallback_icon": "🌹"
    },
    "GIFT_CHAMPAGNE": {
        "num": 68,
        "name": "Shampan Vinosi",
        "location": "Bayramona shampan shishasi sovg'asi",
        "purpose": "Noyob sovg'a yutug'i",
        "id": "5451814216031809603",
        "fallback_name": "[Shampan]",
        "fallback_icon": "🍾"
    },
    "GIFT_DIAMOND_RING": {
        "num": 69,
        "name": "Brilliant Uzuk",
        "location": "Qimmatbaho brilliant uzuk sovg'asi",
        "purpose": "Yuqori darajadagi keys yutug'i",
        "id": "5805693218842480354",
        "fallback_name": "[Brilliant]",
        "fallback_icon": "💍"
    },
    "GIFT_TROPHY": {
        "num": 70,
        "name": "Oltin Kubok Sovg'asi",
        "location": "Chempionlik oltin kubogi",
        "purpose": "Legendary darajadagi sovg'a",
        "id": "5188344996356448758",
        "fallback_name": "[Kubok]",
        "fallback_icon": "🏆"
    },
    "GIFT_ROCKET": {
        "num": 71,
        "name": "Koinot Raketasi Sovg'asi",
        "location": "Tezuchar kosmik raketa",
        "purpose": "Katta qiymatli Telegram sovg'asi",
        "id": "5368654333397199941",
        "fallback_name": "[Raketa]",
        "fallback_icon": "🚀"
    },
    "GIFT_CAP": {
        "num": 72,
        "name": "Kolleksion Kepka Sovg'asi",
        "location": "Telegram NFT kolleksion kepkasi",
        "purpose": "NFT sovg'a yutug'i",
        "id": "5406780968537187482",
        "fallback_name": "[Kepka]",
        "fallback_icon": "🧢"
    },
    "GIFT_PLUSH": {
        "num": 73,
        "name": "Plush Kolleksion Sovg'a",
        "location": "Cheklangan miqdordagi plush o'yinchoq",
        "purpose": "Kamyob Telegram sovg'asi",
        "id": "5289944814270308338",
        "fallback_name": "[Plush]",
        "fallback_icon": "🧸"
    },
    "GIFT_CROWN": {
        "num": 74,
        "name": "Shohona Toj Sovg'asi",
        "location": "Imperatorlik toji Telegram sovg'asi",
        "purpose": "Eng oliy darajadagi sovg'a",
        "id": "5433758796289685818",
        "fallback_name": "[Toj]",
        "fallback_icon": "👑"
    },
    "GIFT_HEART": {
        "num": 75,
        "name": "Mehrli Yurak Sovg'asi",
        "location": "Telegram yurak sovg'asi",
        "purpose": "Sovg'alar to'plami",
        "id": "5280826864988873394",
        "fallback_name": "[Yurak]",
        "fallback_icon": "❤️"
    },
    "GIFT_PREMIUM": {
        "num": 76,
        "name": "Telegram Premium Obunasi",
        "location": "Keyslardan yutib olinadigan 3 va 6 oylik Premium obunalar",
        "purpose": "Rasmiy Telegram Premium yutug'i",
        "id": "5983591923883972553",
        "fallback_name": "[Premium]",
        "fallback_icon": "⭐"
    },
    "GAME_COINFLIP": {
        "num": 77,
        "name": "Tanga Tashlash (Coinflip)",
        "location": "Coinflip mini-o'yini",
        "purpose": "Tanga tashlash o'yini",
        "id": "",
        "fallback_name": "[Tanga]",
        "fallback_icon": "🪙"
    },
    "GAME_SLOTS": {
        "num": 78,
        "name": "Slot Mashinasi (777)",
        "location": "Klassik slot mashinasi kazino o'yini",
        "purpose": "Slot aylantirish o'yini",
        "id": "",
        "fallback_name": "[Slot]",
        "fallback_icon": "🎰"
    },
    "GAME_MINES_BOMB": {
        "num": 79,
        "name": "Mina Bombasi",
        "location": "Mines o'yinidagi xavfli portlovchi bomba",
        "purpose": "Minaga tushganda portlash",
        "id": "",
        "fallback_name": "[Bomba]",
        "fallback_icon": "💣"
    },
    "GAME_MINES_GEM": {
        "num": 80,
        "name": "Mina Olmosi",
        "location": "Mines o'yinidagi yutuqli toza olmos",
        "purpose": "Xavfsiz katak ochilgandagi olmos",
        "id": "",
        "fallback_name": "[Olmos]",
        "fallback_icon": "💎"
    },
    "GAME_CRASH_PLANE": {
        "num": 81,
        "name": "Crash Samolyoti / Raketa",
        "location": "Crash (Aviator) o'yinidagi parvoz qiluvchi samolyot",
        "purpose": "Ko'paytiruvchi koeffitsient o'yini",
        "id": "",
        "fallback_name": "[Samolyot]",
        "fallback_icon": "✈️"
    },
    "GAME_CRASH_BOOM": {
        "num": 82,
        "name": "Crash Portlashi",
        "location": "Crash o'yinida samolyot portlagan lahza",
        "purpose": "Parvoz yakunlanganini bildirish",
        "id": "",
        "fallback_name": "[Portlash]",
        "fallback_icon": "💥"
    },
    "GAME_APPLE_GOOD": {
        "num": 83,
        "name": "Apple Fortune: Butun Olma",
        "location": "Apple of Fortune o'yinidagi yutuqli sara olma",
        "purpose": "G'alaba qozonilgan qator",
        "id": "",
        "fallback_name": "[Olma]",
        "fallback_icon": "🍏"
    },
    "GAME_APPLE_BAD": {
        "num": 84,
        "name": "Apple Fortune: Chiqit Olma",
        "location": "Apple of Fortune o'yinidagi zaharli kemirilgan olma",
        "purpose": "O'yin to'xtagan lahza",
        "id": "",
        "fallback_name": "[Zahar]",
        "fallback_icon": "🍏"
    },
    "GAME_CARD_SPADES": {
        "num": 85,
        "name": "Qarta: Qora Qarg'a (Spades)",
        "location": "Blackjack o'yinidagi qora qarg'a kartasi",
        "purpose": "Karta o'yinlari",
        "id": "",
        "fallback_name": "[Spades]",
        "fallback_icon": "♠️"
    },
    "GAME_CARD_HEARTS": {
        "num": 86,
        "name": "Qarta: Qizil Qalb (Hearts)",
        "location": "21 Ochko va Blackjack o'yinidagi qizil qalb kartasi",
        "purpose": "Karta o'yinlari",
        "id": "",
        "fallback_name": "[Hearts]",
        "fallback_icon": "♥️"
    },
    "GAME_CARD_DIAMONDS": {
        "num": 87,
        "name": "Qarta: Qizil G'isht (Diamonds)",
        "location": "Blackjack o'yinidagi olmos kartasi",
        "purpose": "Karta o'yinlari",
        "id": "",
        "fallback_name": "[Diamonds]",
        "fallback_icon": "♦️"
    },
    "GAME_CARD_CLUBS": {
        "num": 88,
        "name": "Qarta: Qora Chillik (Clubs)",
        "location": "Blackjack o'yinidagi chillik kartasi",
        "purpose": "Karta o'yinlari",
        "id": "",
        "fallback_name": "[Clubs]",
        "fallback_icon": "♣️"
    },
    "GAME_CARD_BACK": {
        "num": 89,
        "name": "Qarta Orqa Tomoni",
        "location": "Yopiq qarta belgisi",
        "purpose": "Ochilmagan karta",
        "id": "",
        "fallback_name": "[Karta]",
        "fallback_icon": "🃏"
    },
    "GAME_WHEEL_SPIN": {
        "num": 90,
        "name": "Fortune G'ildiragi",
        "location": "Omad g'ildiragi aylantirish o'yini",
        "purpose": "Sovg'ali g'ildirak",
        "id": "",
        "fallback_name": "[G'ildirak]",
        "fallback_icon": "🎡"
    },
    "GAME_SCRATCH_COIN": {
        "num": 91,
        "name": "Scratch Omad Tangasi",
        "location": "Scratch Card o'chirish o'yini tangasi",
        "purpose": "Tezkor yutuqli scratch o'yini",
        "id": "",
        "fallback_name": "[Scratch]",
        "fallback_icon": "🪙"
    },
    "DEV_API_KEY": {
        "num": 92,
        "name": "Developer API Kalit",
        "location": "Reseller va tashqi dasturchilar API kaliti boshqaruvi",
        "purpose": "Shaxsiy API kalitni ko'rsatish",
        "id": "4994749624662098557",
        "fallback_name": "[API Kalit]",
        "fallback_icon": "🔑"
    },
    "DEV_API_DOCS": {
        "num": 93,
        "name": "API Hujjatlari (Docs)",
        "location": "REST API hujjatlari va interaktiv qo'llanma",
        "purpose": "API dokumentatsiyasiga havola",
        "id": "5255885203921973531",
        "fallback_name": "[Docs]",
        "fallback_icon": "📖"
    },
    "DEV_CODE_SNIPPET": {
        "num": 94,
        "name": "Dasturlash Koding Namunasi",
        "location": "Python, Node.js va cURL skript namunalari",
        "purpose": "Tayyor integratsiya kodlari",
        "id": "5282843764451195532",
        "fallback_name": "[Kod]",
        "fallback_icon": "💻"
    },
    "DEV_ROTATE_KEY": {
        "num": 95,
        "name": "API Kalitni Yangilash (Rotate)",
        "location": "Eski API kalitni bekor qilib yangi kalit yaratish",
        "purpose": "Kalitni xavfsiz yangilash",
        "id": "5219934485113493317",
        "fallback_name": "[Yangilash]",
        "fallback_icon": "🔄"
    },
    "DEV_WEBHOOK": {
        "num": 96,
        "name": "Developer Webhook",
        "location": "Resellerlar uchun avtomatik bildirishnoma manzili",
        "purpose": "Hodisalarni qabul qilish",
        "id": "5447410659077661506",
        "fallback_name": "[Webhook]",
        "fallback_icon": "📡"
    },
    "BRAND_CAPCUT": {
        "num": 97,
        "name": "CapCut Pro",
        "location": "Marketplaceda CapCut Pro obunasi va litsenziyasi",
        "purpose": "Professional video montaj xizmati",
        "id": "5364339557712020484",
        "fallback_name": "[CapCut]",
        "fallback_icon": "✂️"
    },
    "BRAND_CHATGPT": {
        "num": 98,
        "name": "ChatGPT Plus / Team",
        "location": "OpenAI ChatGPT Plus obunasi",
        "purpose": "Sun'iy intellekt xizmati",
        "id": "5359726582447487916",
        "fallback_name": "[ChatGPT]",
        "fallback_icon": "🤖"
    },
    "BRAND_CLAUDE": {
        "num": 99,
        "name": "Claude Pro / Opus",
        "location": "Anthropic Claude Pro va Claude Code",
        "purpose": "Kuchli AI modeli",
        "id": "6131771460986872161",
        "fallback_name": "[Claude]",
        "fallback_icon": "🧠"
    },
    "BRAND_GEMINI": {
        "num": 100,
        "name": "Google Gemini Advanced",
        "location": "Google Gemini Pro va Advanced obunalari",
        "purpose": "Google AI xizmatlari",
        "id": "5262838511161076891",
        "fallback_name": "[Gemini]",
        "fallback_icon": "✨"
    },
    "BRAND_GROK": {
        "num": 101,
        "name": "xAI Grok / Super Grok",
        "location": "Elon Musk xAI Grok obunasi va tezkor tahlil",
        "purpose": "xAI Grok modeli",
        "id": "6179337489350663129",
        "fallback_name": "[Grok]",
        "fallback_icon": "⚡"
    },
    "BRAND_CODEX": {
        "num": 102,
        "name": "Codex AI Tokenlari",
        "location": "Codex va GitHub dasturlash AI tokenlari",
        "purpose": "Dasturlash AI tokenlari",
        "id": "5275974642866105381",
        "fallback_name": "[Codex]",
        "fallback_icon": "📜"
    },
    "BRAND_ELEVENLABS": {
        "num": 103,
        "name": "ElevenLabs AI Ovoz",
        "location": "Professional ovoz klonlash va sintez xizmati",
        "purpose": "AI diktor va ovozlar",
        "id": "6219689196722854904",
        "fallback_name": "[ElevenLabs]",
        "fallback_icon": "🎙️"
    },
    "BRAND_MIDJOURNEY": {
        "num": 104,
        "name": "Midjourney AI San'at",
        "location": "AI rasm va illyustratsiya yaratish xizmati",
        "purpose": "Grafik dizayn AI",
        "id": "5359618237602480327",
        "fallback_name": "[Midjourney]",
        "fallback_icon": "🎨"
    },
    "BRAND_CANVA": {
        "num": 105,
        "name": "Canva Pro Dizayn",
        "location": "Canva Pro jamoaviy va individual litsenziyalari",
        "purpose": "Grafik dizayn platformasi",
        "id": "6127504264949408331",
        "fallback_name": "[Canva]",
        "fallback_icon": "🖌️"
    },
    "BRAND_FIGMA": {
        "num": 106,
        "name": "Figma Professional",
        "location": "Figma dizayn va UI/UX vositalari",
        "purpose": "Interfeys dizayni",
        "id": "6127461826377556681",
        "fallback_name": "[Figma]",
        "fallback_icon": "📐"
    },
    "BRAND_SPOTIFY": {
        "num": 107,
        "name": "Spotify Premium",
        "location": "Musiqiy striming xizmati obunasi",
        "purpose": "Cheksiz musiqa",
        "id": "5346074681004801565",
        "fallback_name": "[Spotify]",
        "fallback_icon": "🎧"
    },
    "BRAND_NETFLIX": {
        "num": 108,
        "name": "Netflix 4K Ultra HD",
        "location": "Netflix kino va seriallar platformasi",
        "purpose": "Film striming",
        "id": "5318911503938634641",
        "fallback_name": "[Netflix]",
        "fallback_icon": "🎬"
    },
    "BRAND_NORDVPN": {
        "num": 109,
        "name": "NordVPN Maxfiylik",
        "location": "NordVPN xavfsiz internet va shaxsiy vpn",
        "purpose": "Kiberxavfsizlik va VPN",
        "id": "5346134750417403743",
        "fallback_name": "[NordVPN]",
        "fallback_icon": "🔒"
    },
    "BRAND_WINDOWS": {
        "num": 110,
        "name": "Windows 10/11 Pro Kalit",
        "location": "Microsoft Windows original faollashtirish kalitlari",
        "purpose": "Operatsion tizim kaliti",
        "id": "6005916300600152073",
        "fallback_name": "[Windows]",
        "fallback_icon": "💻"
    },
    "BRAND_OFFICE365": {
        "num": 111,
        "name": "Microsoft Office 365",
        "location": "Word, Excel, PowerPoint rasmiy paketi",
        "purpose": "Ofis dasturlari to'plami",
        "id": "5979047775470358891",
        "fallback_name": "[Office365]",
        "fallback_icon": "📊"
    },
    "BRAND_APPLE": {
        "num": 112,
        "name": "Apple Services",
        "location": "Apple Music, Apple TV, iCloud va App Store",
        "purpose": "Apple ekotizimi xizmatlari",
        "id": "5334955749409834455",
        "fallback_name": "[Apple]",
        "fallback_icon": "🍏"
    },
    "BRAND_CURSOR": {
        "num": 113,
        "name": "Cursor AI IDE",
        "location": "Dasturchilar uchun zamonaviy AI kod muharriri",
        "purpose": "Dasturlash AI vositasi",
        "id": "6273793612715138423",
        "fallback_name": "[Cursor]",
        "fallback_icon": "⚡"
    },
    "BRAND_GITHUB": {
        "num": 114,
        "name": "GitHub Copilot",
        "location": "GitHub Copilot litsenziyasi va repozitoriylar",
        "purpose": "Kod yozish yordamchisi",
        "id": "5346181118884331907",
        "fallback_name": "[GitHub]",
        "fallback_icon": "🐙"
    },
    "BRAND_OPENROUTER": {
        "num": 115,
        "name": "OpenRouter AI API",
        "location": "Barcha global AI modellarni birlashtiruvchi API kalit",
        "purpose": "Developer AI API",
        "id": "5276345770990151994",
        "fallback_name": "[OpenRouter]",
        "fallback_icon": "🌐"
    },
    "BRAND_GROQ": {
        "num": 116,
        "name": "Groq LPU Tezkor AI",
        "location": "Ultra tezkor Groq LPU API xizmati",
        "purpose": "Tezkor AI inferens",
        "id": "6179337489350663129",
        "fallback_name": "[Groq]",
        "fallback_icon": "⚡"
    },
    "BRAND_PROXY_IPV4": {
        "num": 117,
        "name": "Proxy IPv4 / Socks5",
        "location": "Shaxsiy toza proxy serverlar (YouTube, scraping, bot)",
        "purpose": "Tarmoq proksisi",
        "id": "5848067868695991015",
        "fallback_name": "[Proxy]",
        "fallback_icon": "🌐"
    },
    "BRAND_CREATORFLOW": {
        "num": 118,
        "name": "CreatorFlow Studio Suite",
        "location": "Bizning platformaning to'liq professional ekotizimi",
        "purpose": "CreatorFlow brendi",
        "id": "5276040205541878847",
        "fallback_name": "[CreatorFlow]",
        "fallback_icon": "⚡"
    },
    "BRAND_DESCRIPT": {
        "num": 119,
        "name": "Descript Creator",
        "location": "Podkast va video transkripsiya hamda ovoz muharriri",
        "purpose": "Video & Audio muharrir",
        "id": "6131913864922537306",
        "fallback_name": "[Descript]",
        "fallback_icon": "🎙️"
    },
    "BRAND_WORDWALL": {
        "num": 120,
        "name": "Wordwall Pro",
        "location": "Interaktiv ta'lim o'yinlari va testlar platformasi",
        "purpose": "Ta'lim o'yinlari",
        "id": "5276208482360533530",
        "fallback_name": "[Wordwall]",
        "fallback_icon": "🧱"
    },
    "BRAND_GAMMA": {
        "num": 121,
        "name": "Gamma AI Presentations",
        "location": "Sun'iy intellekt yordamida tezkor taqdimot va sahifalar",
        "purpose": "AI taqdimotlar",
        "id": "5274272186549446418",
        "fallback_name": "[Gamma]",
        "fallback_icon": "📊"
    },
    "BRAND_GMAIL": {
        "num": 122,
        "name": "Gmail 2FA & Workspace",
        "location": "Xavfsiz Google akkauntlari va Google One 5TB bulut",
        "purpose": "Google akkauntlari",
        "id": "5273814673748171854",
        "fallback_name": "[Gmail]",
        "fallback_icon": "📧"
    },
    "BRAND_MIRO": {
        "num": 123,
        "name": "Miro Edu Doskasi",
        "location": "Jamoaviy fikr almashish va rejalashtirish doskasi",
        "purpose": "Hamkorlik doskasi",
        "id": "5276483446166825007",
        "fallback_name": "[Miro]",
        "fallback_icon": "🟡"
    },
    "BRAND_QUIZLET": {
        "num": 124,
        "name": "Quizlet Plus",
        "location": "Chet tillari va fanlarni o'rganish kartochkalari",
        "purpose": "Ta'lim kartochkalari",
        "id": "5273950802736619874",
        "fallback_name": "[Quizlet]",
        "fallback_icon": "🃏"
    },
    "BRAND_ZOOM": {
        "num": 125,
        "name": "Zoom Pro",
        "location": "Cheksiz guruh video konferensiyalari va darslar",
        "purpose": "Video konferensiya",
        "id": "5334932883003949665",
        "fallback_name": "[Zoom]",
        "fallback_icon": "📹"
    },
    "BRAND_KIRO": {
        "num": 126,
        "name": "Kiro AI",
        "location": "Kiro AI kreditlari va API litsenziyalari",
        "purpose": "AI vositalari",
        "id": "5273907062789678843",
        "fallback_name": "[Kiro]",
        "fallback_icon": "🔑"
    },
    "BRAND_ILOVEPDF": {
        "num": 127,
        "name": "iLovePdf Premium",
        "location": "PDF fayllarni birlashtirish, siqish va tahrirlash",
        "purpose": "PDF xizmatlari",
        "id": "6206155660283879718",
        "fallback_name": "[iLovePdf]",
        "fallback_icon": "📑"
    },
    "BRAND_ADOBE": {
        "num": 128,
        "name": "Adobe Express / Creative",
        "location": "Adobe rasmiy dizayn va foto montaj xizmatlari",
        "purpose": "Grafik dizayn paketi",
        "id": "5359320531944358335",
        "fallback_name": "[Adobe]",
        "fallback_icon": "🅰️"
    },
    "BRAND_AUTODESK": {
        "num": 129,
        "name": "Autodesk Education",
        "location": "AutoCAD, 3ds Max va Maya professional 3D litsenziyasi",
        "purpose": "Muhandislik 3D dasturlari",
        "id": "6305045014531548800",
        "fallback_name": "[Autodesk]",
        "fallback_icon": "📐"
    },
    "BRAND_PRIMEVIDEO": {
        "num": 130,
        "name": "Amazon Prime Video",
        "location": "Amazon kino va seriallar platformasi obunasi",
        "purpose": "Film striming",
        "id": "5363973751052452405",
        "fallback_name": "[PrimeVideo]",
        "fallback_icon": "📦"
    },
    "BRAND_PEACOCK": {
        "num": 131,
        "name": "Peacock TV",
        "location": "NBCUniversal rasmiy striming xizmati obunasi",
        "purpose": "Seriallar va sport",
        "id": "5276371588038563833",
        "fallback_name": "[Peacock]",
        "fallback_icon": "🦚"
    },
    "BRAND_WINK": {
        "num": 132,
        "name": "Wink Video Striming",
        "location": "Raqamli televideniye va filmlar platformasi",
        "purpose": "Kino xizmati",
        "id": "6165766565221376545",
        "fallback_name": "[Wink]",
        "fallback_icon": "😉"
    },
    "BRAND_JETBRAINS": {
        "num": 133,
        "name": "JetBrains All Products",
        "location": "PyCharm, WebStorm, IntelliJ IDEA rasmiy litsenziyasi",
        "purpose": "Dasturchi IDE to'plami",
        "id": "6190446701434648243",
        "fallback_name": "[JetBrains]",
        "fallback_icon": "💡"
    },
    "BRAND_DUOLINGO": {
        "num": 134,
        "name": "Duolingo Super",
        "location": "Reklamasiz cheksiz yuraklar bilan til o'rganish",
        "purpose": "Til o'rganish ilovasi",
        "id": "5276013701298690959",
        "fallback_name": "[Duolingo]",
        "fallback_icon": "🦉"
    },
    "BRAND_BRAINFM": {
        "num": 135,
        "name": "Brain.fm Focus Music",
        "location": "Miyani jamlash va diqqatni oshiruvchi neyro-musiqa",
        "purpose": "Diqqat musiqasi",
        "id": "6133957217088446991",
        "fallback_name": "[Brain.fm]",
        "fallback_icon": "🧠"
    },
    "BRAND_FACTORY": {
        "num": 136,
        "name": "Factory Pro",
        "location": "Dasturchilar uchun ilg'or AI agentlar va tooling",
        "purpose": "AI kod generatori",
        "id": "6131874256734136056",
        "fallback_name": "[Factory]",
        "fallback_icon": "🏭"
    },
    "BRAND_QUILLBOT": {
        "num": 137,
        "name": "Quillbot Premium",
        "location": "Professional matn parafrazlash va grammatika tuzatish",
        "purpose": "Matn tekshiruvchi",
        "id": "6165819144211014986",
        "fallback_name": "[Quillbot]",
        "fallback_icon": "🪶"
    },
    "BRAND_CUSTOMERIO": {
        "num": 138,
        "name": "Customer.io Marketing",
        "location": "Avtomatlashtirilgan marketing xabarnomalari xizmati",
        "purpose": "Marketing platformasi",
        "id": "5380107177224622569",
        "fallback_name": "[Customer.io]",
        "fallback_icon": "📧"
    },
    "BRAND_FIN": {
        "num": 139,
        "name": "Fin AI Agent",
        "location": "Intercom asosidagi ilg'or AI mijozlar servis agenti",
        "purpose": "AI qo'llab-quvvatlash",
        "id": "5321533581472842536",
        "fallback_name": "[Fin AI]",
        "fallback_icon": "🤖"
    },
    "BRAND_FRAMER": {
        "num": 140,
        "name": "Framer Pro",
        "location": "Kod yozmasdan interaktiv va zamonaviy web-sayt yaratish",
        "purpose": "Sayt yaratish",
        "id": "6165465672697521810",
        "fallback_name": "[Framer]",
        "fallback_icon": "📐"
    },
    "BRAND_GRANOLA": {
        "num": 141,
        "name": "Granola Business",
        "location": "Zoom va Google Meet uchrashuvlari uchun aqlli AI qaydlar",
        "purpose": "AI uchrashuv qaydlari",
        "id": "6131964704450420501",
        "fallback_name": "[Granola]",
        "fallback_icon": "📝"
    },
    "BRAND_GUMLOOP": {
        "num": 142,
        "name": "Gumloop Pro",
        "location": "AI vositalarni kodsiz avtomatlashtirish tizimi",
        "purpose": "Ish oqimi avtomatizatsiyasi",
        "id": "6134256000783360676",
        "fallback_name": "[Gumloop]",
        "fallback_icon": "🔄"
    },
    "BRAND_JAM": {
        "num": 143,
        "name": "Jam Team",
        "location": "1 marta bosish bilan xatoliklarni (bug) videoga olish",
        "purpose": "QA va xatoliklar nazorati",
        "id": "6131721072430556781",
        "fallback_name": "[Jam]",
        "fallback_icon": "🐞"
    },
    "BRAND_TRADINGVIEW": {
        "num": 144,
        "name": "TradingView Premium",
        "location": "Kripto va aksiyalar birjasining professional grafikalari",
        "purpose": "Birja tahlili",
        "id": "5275983151196317807",
        "fallback_name": "[TradingView]",
        "fallback_icon": "📈"
    },
    "BRAND_LINEAR": {
        "num": 145,
        "name": "Linear Business",
        "location": "Zamonaviy jamoaviy loyiha va vazifalar boshqaruvi",
        "purpose": "Loyiha boshqaruvi",
        "id": "6134000510358789940",
        "fallback_name": "[Linear]",
        "fallback_icon": "📐"
    },
    "BRAND_MOBBIN": {
        "num": 146,
        "name": "Mobbin Design",
        "location": "Minglab real mobil va web interfeyslar kutubxonasi",
        "purpose": "Dizayn ilhom manbai",
        "id": "6328009693562150576",
        "fallback_name": "[Mobbin]",
        "fallback_icon": "📱"
    },
    "BRAND_POSTHOG": {
        "num": 147,
        "name": "PostHog Scale",
        "location": "Foydalanuvchilar harakati va session replay analitikasi",
        "purpose": "Mahsulot tahlili",
        "id": "6133923175177657835",
        "fallback_name": "[PostHog]",
        "fallback_icon": "🦔"
    },
    "BRAND_RAILWAY": {
        "num": 148,
        "name": "Railway Hosting",
        "location": "Ilovalar va ma'lumotlar bazalarini tezkor bulutga yuklash",
        "purpose": "Bulutli platforma",
        "id": "6131830684290916405",
        "fallback_name": "[Railway]",
        "fallback_icon": "🚂"
    },
    "BRAND_READWISE": {
        "num": 149,
        "name": "Readwise Reader",
        "location": "Kitoblar, maqolalar va tvitlardan asosiy fikrlarni saqlash",
        "purpose": "Mutolaa yordamchisi",
        "id": "6298810706292645760",
        "fallback_name": "[Readwise]",
        "fallback_icon": "📚"
    },
    "BRAND_RESEND": {
        "num": 150,
        "name": "Resend Email",
        "location": "Dasturchilar uchun ultra tezkor email jo'natish API",
        "purpose": "Email xizmati",
        "id": "5377760419978978059",
        "fallback_name": "[Resend]",
        "fallback_icon": "✉️"
    },
    "BRAND_SUPERCUT": {
        "num": 151,
        "name": "Supercut Pro",
        "location": "Jamoaviy tezkor video montaj va kontent tahrirlash",
        "purpose": "Video montaj",
        "id": "6132002787925434276",
        "fallback_name": "[Supercut]",
        "fallback_icon": "✂️"
    },
    "BRAND_WISPR": {
        "num": 152,
        "name": "Wispr Flow",
        "location": "Nutqni real vaqtda aniq matnga aylantirish xizmati",
        "purpose": "Ovozdan matnga",
        "id": "6131833836796912125",
        "fallback_name": "[Wispr]",
        "fallback_icon": "🗣️"
    },
    "BRAND_HMA": {
        "num": 153,
        "name": "HMA HideMyAss VPN",
        "location": "Global serverlar orqali shaxsiy IP ni yashirish",
        "purpose": "Maxfiy VPN",
        "id": "5275995997443500362",
        "fallback_name": "[HMA]",
        "fallback_icon": "🫏"
    },
    "BRAND_MAGICPATTERNS": {
        "num": 154,
        "name": "Magic Patterns",
        "location": "AI yordamida tezkor UI komponentlar yaratish",
        "purpose": "Dizayn prototiplari",
        "id": "5273751499074223574",
        "fallback_name": "[MagicPatterns]",
        "fallback_icon": "✨"
    },
    "BRAND_WARP": {
        "num": 155,
        "name": "Warp Terminal",
        "location": "Sun'iy intellekt integratsiyalangan zamonaviy terminal",
        "purpose": "Dasturchi terminali",
        "id": "6283060193634821331",
        "fallback_name": "[Warp]",
        "fallback_icon": "💻"
    },
    "BRAND_PROTONVPN": {
        "num": 156,
        "name": "Proton VPN Plus",
        "location": "Shveytsariya qonunlari bilan himoyalangan maxfiy VPN",
        "purpose": "Kriptografik VPN",
        "id": "5273929435274322900",
        "fallback_name": "[ProtonVPN]",
        "fallback_icon": "🛡️"
    },
    "BRAND_NOTION": {
        "num": 157,
        "name": "Notion Plus / Business",
        "location": "Hujjatlar, loyihalar va shaxsiy bilimlarni boshqarish",
        "purpose": "Ish maydoni",
        "id": "6129603885481860870",
        "fallback_name": "[Notion]",
        "fallback_icon": "📓"
    },
    "BRAND_SUPABASE": {
        "num": 158,
        "name": "Supabase Pro",
        "location": "PostgreSQL, Auth va Realtime o'z ichiga olgan Firebase muqobili",
        "purpose": "Bulutli backend",
        "id": "6132184989028064930",
        "fallback_name": "[Supabase]",
        "fallback_icon": "⚡"
    },
    "BRAND_N8N": {
        "num": 159,
        "name": "n8n Workflow",
        "location": "Istalgan tizimlarni bir-biriga bog'lovchi ochiq kodli avtomatika",
        "purpose": "Integratsiyalar",
        "id": "6133957427541843855",
        "fallback_name": "[n8n]",
        "fallback_icon": "🔀"
    },
    "BRAND_MANUS": {
        "num": 160,
        "name": "Manus Pro",
        "location": "Mustaqil murakkab vazifalarni bajaruvchi avtonom AI agent",
        "purpose": "Avtonom AI",
        "id": "6328009693562150576",
        "fallback_name": "[Manus]",
        "fallback_icon": "🤖"
    },
    "BRAND_LOVABLE": {
        "num": 161,
        "name": "Lovable Pro",
        "location": "Tabiiy tildagi so'rovlar asosida to'liq web ilovalar qurish",
        "purpose": "Full-stack AI",
        "id": "6104729848675050039",
        "fallback_name": "[Lovable]",
        "fallback_icon": "❤️"
    },
    "BRAND_COURSERA": {
        "num": 162,
        "name": "Coursera Plus",
        "location": "Dunyoning top universitetlari sertifikatli onlayn kurslari",
        "purpose": "Onlayn ta'lim",
        "id": "5276430257291831252",
        "fallback_name": "[Coursera]",
        "fallback_icon": "🎓"
    },
    "BRAND_REPLIT": {
        "num": 163,
        "name": "Replit Core",
        "location": "Brauzerning o'zida dasturlash va 1 marta bosish bilan deploy",
        "purpose": "Bulutli IDE",
        "id": "6105050957609968229",
        "fallback_name": "[Replit]",
        "fallback_icon": "🚀"
    },
    "BRAND_SCRIBD": {
        "num": 164,
        "name": "Scribd Audio & Books",
        "location": "Cheksiz audio kitoblar, jurnallar va hujjatlar kutubxonasi",
        "purpose": "Elektron kutubxona",
        "id": "5276279375090720678",
        "fallback_name": "[Scribd]",
        "fallback_icon": "📚"
    },
    "BRAND_SNAPCHAT": {
        "num": 165,
        "name": "Snapchat Plus",
        "location": "Snapchat ijtimoiy tarmog'ining eksklyuziv imkoniyatlari",
        "purpose": "Ijtimoiy tarmoq",
        "id": "5330248916224983855",
        "fallback_name": "[Snapchat]",
        "fallback_icon": "👻"
    },
    "BRAND_HBOMAX": {
        "num": 166,
        "name": "HBO Max Streaming",
        "location": "Warner Bros filmlari, Game of Thrones va seriallar",
        "purpose": "Film striming",
        "id": "6131816893150929122",
        "fallback_name": "[HBOMax]",
        "fallback_icon": "📺"
    },
    "BRAND_EXPRESSVPN": {
        "num": 167,
        "name": "ExpressVPN",
        "location": "Xavfsiz va tezkor VPN xizmati",
        "purpose": "VPN va xavfsizlik tovarlari",
        "id": "5418095256719633735",
        "fallback_name": "[ExpressVPN]",
        "fallback_icon": "🛡️"
    },
    "BRAND_SURFSHARK": {
        "num": 168,
        "name": "Surfshark VPN",
        "location": "Cheksiz qurilmalar uchun xavfsiz VPN",
        "purpose": "VPN va maxfiylik tovarlari",
        "id": "5417830390381456686",
        "fallback_name": "[Surfshark]",
        "fallback_icon": "🦈"
    },
    "BRAND_HIGGSFIELD": {
        "num": 169,
        "name": "Higgsfield AI",
        "location": "AI video va visual generatsiya platformasi",
        "purpose": "AI video generatsiya tovarlari",
        "id": "5415617713424870892",
        "fallback_name": "[Higgsfield]",
        "fallback_icon": "🎥"
    },
    "BRAND_MERCURY": {
        "num": 170,
        "name": "Mercury Bank",
        "location": "AQSH biznes bank hisobi va fintech",
        "purpose": "Xalqaro biznes va fintech xizmatlari",
        "id": "5418036918178851295",
        "fallback_name": "[Mercury]",
        "fallback_icon": "💳"
    },
    "BRAND_STRIPE_ATLAS": {
        "num": 171,
        "name": "Stripe Atlas",
        "location": "AQSHda kompaniya (LLC/C-Corp) ochish xizmati",
        "purpose": "Biznes va to'lov infratuzilmasi",
        "id": "5415751574670587373",
        "fallback_name": "[StripeAtlas]",
        "fallback_icon": "🌐"
    },
    "BRAND_CRUNCHYROLL": {
        "num": 172,
        "name": "Crunchyroll",
        "location": "Anime va manga striming xizmati",
        "purpose": "Anime striming va obunalar",
        "id": "5418134847728168399",
        "fallback_name": "[Crunchyroll]",
        "fallback_icon": "🎬"
    },
    "BRAND_MUSEAI": {
        "num": 173,
        "name": "Muse AI",
        "location": "Zamonaviy AI video qidiruv va hosting platformasi",
        "purpose": "AI video va media vositalari",
        "id": "5418345906716058813",
        "fallback_name": "[MuseAI]",
        "fallback_icon": "🤖"
    },
    "BRAND_WAKINGUP": {
        "num": 174,
        "name": "Waking Up",
        "location": "Sam Harris meditatsiya va ong ilovasi",
        "purpose": "Salomatlik, meditatsiya va ta'lim tovarlari",
        "id": "5417975255333383045",
        "fallback_name": "[WakingUp]",
        "fallback_icon": "🧠"
    },
})

# ==============================================================================
# 5. BRENDLAR VA TOVARLAR BO'YICHA CUSTOM EMOJI XARITASI (BRAND_EMOJIS_MAP)
# ==============================================================================
BRAND_TO_REGISTRY_KEY = {
    "chatgpt": "BRAND_CHATGPT",
    "chat gpt": "BRAND_CHATGPT",
    "openai": "BRAND_CHATGPT",
    "gpt": "BRAND_CHATGPT",
    "claude": "BRAND_CLAUDE",
    "claude code": "BRAND_CLAUDE",
    "claudecode": "BRAND_CLAUDE",
    "claude 3.5": "BRAND_CLAUDE",
    "claude opus": "BRAND_CLAUDE",
    "claude pro": "BRAND_CLAUDE",
    "anthropic": "BRAND_CLAUDE",
    "gemini": "BRAND_GEMINI",
    "google ai": "BRAND_GEMINI",
    "grok": "BRAND_GROK",
    "xai": "BRAND_GROK",
    "codex": "BRAND_CODEX",
    "cursor": "BRAND_CURSOR",
    "developer api": "DEV_API_KEY",
    "reseller api": "DEV_API_KEY",
    "api docs": "DEV_API_DOCS",
    "api keys": "DEV_API_KEY",
    "api kalit": "DEV_API_KEY",
    "manus": "BRAND_MANUS",
    "factory": "BRAND_FACTORY",
    "lovable": "BRAND_LOVABLE",
    "lovalbe": "BRAND_LOVABLE",
    "replit": "BRAND_REPLIT",
    "kiro": "BRAND_KIRO",
    "openrouter": "BRAND_OPENROUTER",
    "groq": "BRAND_GROQ",
    "flux": "BRAND_CREATORFLOW",
    "fin ia": "BRAND_FIN",
    "fin": "BRAND_FIN",
    "capcut": "BRAND_CAPCUT",
    "supercut": "BRAND_SUPERCUT",
    "descript": "BRAND_DESCRIPT",
    "elevenlabs": "BRAND_ELEVENLABS",
    "eleven": "BRAND_ELEVENLABS",
    "brain.fm": "BRAND_BRAINFM",
    "brain fm": "BRAND_BRAINFM",
    "wispr flow": "BRAND_WISPR",
    "wispr": "BRAND_WISPR",
    "gamma": "BRAND_GAMMA",
    "figma": "BRAND_FIGMA",
    "framer": "BRAND_FRAMER",
    "canva": "BRAND_CANVA",
    "adobe": "BRAND_ADOBE",
    "magic patterns": "BRAND_MAGICPATTERNS",
    "mobbin": "BRAND_MOBBIN",
    "miro": "BRAND_MIRO",
    "midjourney": "BRAND_MIDJOURNEY",
    "quillbot": "BRAND_QUILLBOT",
    "jetbrains": "BRAND_JETBRAINS",
    "railway": "BRAND_RAILWAY",
    "warp": "BRAND_WARP",
    "n8n": "BRAND_N8N",
    "linear": "BRAND_LINEAR",
    "autodesk": "BRAND_AUTODESK",
    "ilovepdf": "BRAND_ILOVEPDF",
    "wordwall": "BRAND_WORDWALL",
    "quizlet": "BRAND_QUIZLET",
    "customer.io": "BRAND_CUSTOMERIO",
    "granola": "BRAND_GRANOLA",
    "gumloop": "BRAND_GUMLOOP",
    "jam team": "BRAND_JAM",
    "jam": "BRAND_JAM",
    "trading view": "BRAND_TRADINGVIEW",
    "tradingview": "BRAND_TRADINGVIEW",
    "posthog": "BRAND_POSTHOG",
    "readwise": "BRAND_READWISE",
    "resend": "BRAND_RESEND",
    "supabase": "BRAND_SUPABASE",
    "github": "BRAND_GITHUB",
    "copilot": "BRAND_GITHUB",
    "spotify": "BRAND_SPOTIFY",
    "netflix": "BRAND_NETFLIX",
    "amazon": "BRAND_PRIMEVIDEO",
    "prime video": "BRAND_PRIMEVIDEO",
    "prime": "BRAND_PRIMEVIDEO",
    "peacock": "BRAND_PEACOCK",
    "apple tv": "BRAND_APPLE",
    "apple music": "BRAND_APPLE",
    "wink": "BRAND_WINK",
    "youtube premium": "MEDIA_YOUTUBE",
    "youtube": "MEDIA_YOUTUBE",
    "hbo max": "BRAND_HBOMAX",
    "hbo": "BRAND_HBOMAX",
    "expressvpn": "BRAND_EXPRESSVPN",
    "express vpn": "BRAND_EXPRESSVPN",
    "surfshark": "BRAND_SURFSHARK",
    "surf shark": "BRAND_SURFSHARK",
    "nordvpn": "BRAND_NORDVPN",
    "nord vpn": "BRAND_NORDVPN",
    "nord": "BRAND_NORDVPN",
    "proton vpn": "BRAND_PROTONVPN",
    "protonvpn": "BRAND_PROTONVPN",
    "proton": "BRAND_PROTONVPN",
    "hma": "BRAND_HMA",
    "proxy": "BRAND_PROXY_IPV4",
    "proxies": "BRAND_PROXY_IPV4",
    "zoom": "BRAND_ZOOM",
    "snapchat": "BRAND_SNAPCHAT",
    "microsoft 365": "BRAND_OFFICE365",
    "microsoft office": "BRAND_OFFICE365",
    "microsoft": "BRAND_OFFICE365",
    "office 365": "BRAND_OFFICE365",
    "office": "BRAND_OFFICE365",
    "windows 10": "BRAND_WINDOWS",
    "windows 11": "BRAND_WINDOWS",
    "windows": "BRAND_WINDOWS",
    "gmail": "BRAND_GMAIL",
    "google drive": "BRAND_GMAIL",
    "notion": "BRAND_NOTION",
    "duolingo": "BRAND_DUOLINGO",
    "coursera": "BRAND_COURSERA",
    "cousera": "BRAND_COURSERA",
    "scribd": "BRAND_SCRIBD",
    "apple pay": "BRAND_APPLE",
    "apple": "BRAND_APPLE",
    "creatorflow": "BRAND_CREATORFLOW",
    "stock_box": "GIFT_CASE_BOX",
    "out_of_stock": "STATUS_WARNING",
    "store": "BTN_SERVICES",
    "stars": "PAY_STARS",
    "ton": "PAY_TON_CRYPTO",
    "humo": "PAY_HUMO_UZCARD",
    "uzcard": "PAY_HUMO_UZCARD",
    "autostream": "TOOL_LIVE_STREAM",
    "prompt pack": "TOOL_PROMPT_PACK",
    "prompts": "TOOL_PROMPT_PACK",
    "deeplink": "TOOL_QR_CODE",
    "smart qr": "TOOL_QR_CODE",
    "qr code": "TOOL_QR_CODE",
    "qr": "TOOL_QR_CODE",
    "unikal": "MEDIA_UNIKAL",
    "unikalizatsiya": "MEDIA_UNIKAL",
    "clipper": "MEDIA_SCISSORS",
    "shorts kesish": "MEDIA_SCISSORS",
    "layk": "TOOL_LIKES",
    "like": "TOOL_LIKES",
    "obuna": "TOOL_SUBS",
    "obunachi": "TOOL_SUBS",
    "subscribe": "TOOL_SUBS",
    "izoh": "TOOL_COMMENTS",
    "comment": "TOOL_COMMENTS",
    "views": "TOOL_VIEWS",
    "ko'rish": "TOOL_VIEWS",
    "vip": "PAY_VIP_CROWN",
    "mystery box": "GIFT_CASE_BOX",
    "super to'plam": "GIFT_CASE_BOX",
    "bundle": "GIFT_CASE_BOX",
    "starter pack": "GIFT_CASE_BOX",
    "ai master pack": "BRAND_CHATGPT",
    "bolt.new": "DEV_CODE_SNIPPET",
    "bolt": "DEV_CODE_SNIPPET",
    "muse ai": "BRAND_MUSEAI",
    "muse": "BRAND_MUSEAI",
    "museai": "BRAND_MUSEAI",
    "arize": "DEV_CODE_SNIPPET",
    "pangram": "BRAND_CANVA",
    "speechify": "BRAND_ELEVENLABS",
    "airtable": "BRAND_NOTION",
    "runway": "MEDIA_AI_VIDEO",
    "higgsfield": "BRAND_HIGGSFIELD",
    "higgsfield ai": "BRAND_HIGGSFIELD",
    "mercury": "BRAND_MERCURY",
    "mercury bank": "BRAND_MERCURY",
    "stripe atlas": "BRAND_STRIPE_ATLAS",
    "stripe": "BRAND_STRIPE_ATLAS",
    "waking up": "BRAND_WAKINGUP",
    "wakingup": "BRAND_WAKINGUP",
    "waking": "BRAND_WAKINGUP",
    "crunchyroll": "BRAND_CRUNCHYROLL",
    "crunchy roll": "BRAND_CRUNCHYROLL",
    "ᴄʀᴜɴᴄʜʏʀᴏʟʟ": "BRAND_CRUNCHYROLL",
    "autodesk": "BRAND_AUTODESK",
}

class BrandEmojisMap(dict):
    """
    Brendlar bo'yicha Custom Emoji ID xaritasi.
    CUSTOM_EMOJI_REGISTRY bilan bevosita bog'langan bo'lib, reestrdagi ID o'zgarganda avtomatik aks etadi.
    Katta-kichik harflar va bo'shliqlarga nisbatan chidamli.
    """
    def _find_brand_key(self, key):
        if key is None:
            return None
        k_lower = str(key).strip().lower()
        if super().__contains__(k_lower):
            return k_lower
        if super().__contains__(key):
            return key
        return None

    def __contains__(self, key):
        return self._find_brand_key(key) is not None

    def __getitem__(self, key):
        matched = self._find_brand_key(key)
        if matched is not None:
            reg_key = super().__getitem__(matched)
            if isinstance(reg_key, str) and reg_key in CUSTOM_EMOJI_REGISTRY:
                return CUSTOM_EMOJI_REGISTRY[reg_key].get("id", "")
            return reg_key
        return super().__getitem__(key)

    def get(self, key, default=""):
        matched = self._find_brand_key(key)
        if matched is not None:
            reg_key = super().__getitem__(matched)
            if isinstance(reg_key, str) and reg_key in CUSTOM_EMOJI_REGISTRY:
                return CUSTOM_EMOJI_REGISTRY[reg_key].get("id", "")
            return reg_key
        return default

    def items(self):
        for k in self.keys():
            yield (k, self[k])

    def values(self):
        for k in self.keys():
            yield self[k]

BRAND_EMOJIS_MAP = BrandEmojisMap(BRAND_TO_REGISTRY_KEY)

# ==============================================================================
# 6. TEZKOR KARTA VA POOL
# ==============================================================================
EMOJI_MAP = {}
for k, v in CUSTOM_EMOJI_REGISTRY.items():
    val = (v.get("id", ""), v.get("fallback_icon", "✨"))
    EMOJI_MAP[k] = val
    EMOJI_MAP[k.lower()] = val

for alias, reg_key in ALIASES.items():
    if reg_key in CUSTOM_EMOJI_REGISTRY:
        reg_item = CUSTOM_EMOJI_REGISTRY[reg_key]
        val = (reg_item.get("id", ""), reg_item.get("fallback_icon", "✨"))
        EMOJI_MAP[alias] = val
        EMOJI_MAP[alias.lower()] = val

CUSTOM_EMOJI_POOL = [
    str(v["id"]).strip() for v in CUSTOM_EMOJI_REGISTRY.values()
    if v.get("id") and str(v.get("id")).strip().isdigit()
]

# Backward compatibility alias
VERIFIED_CUSTOM_EMOJIS = CUSTOM_EMOJI_REGISTRY

# ==============================================================================
# 7. YORDAMCHI FUNKSIYALAR
# ==============================================================================
def get_custom_emoji_info(key: str) -> dict:
    """Emoji haqidagi to'liq metama'lumotlarni qaytaradi."""
    reg_key = resolve_registry_key(key)
    return CUSTOM_EMOJI_REGISTRY.get(reg_key, {
        "name": key,
        "location": "Noma'lum",
        "purpose": "Noma'lum",
        "id": "",
        "fallback_name": f"[{key}]",
        "fallback_icon": "✨"
    })

def e(key: str) -> str:
    """Fallback piktogrammani qaytaradi."""
    info = get_custom_emoji_info(key)
    return info.get("fallback_icon", "") or info.get("fallback_name", "✨")

def custom_emoji(key: str) -> str:
    """
    Telegram xabarlarida chiroyli Custom Emoji chiqishi uchun <emoji id="..."> HTML tegi.
    Agar ID bo'lmasa, toza fallback icon yoki nom chiqariladi.
    """
    info = get_custom_emoji_info(key)
    c_id = info.get("id", "")
    fb = info.get("fallback_icon", "") or info.get("fallback_name", "")
    if c_id and str(c_id).strip().isdigit():
        return f'<emoji id="{c_id}">{fb}</emoji>'
    return fb

ce = custom_emoji

def clean_btn_text(text: str) -> str:
    """Tugma (InlineKeyboardButton yoki KeyboardButton) matnidagi barcha HTML va <emoji id="..."> teglarini tozalaydi."""
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    # <emoji id="123">✅</emoji> -> ✅
    clean = re.sub(r'<emoji id="[^"]*">(.*?)</emoji>', r'\1', text, flags=re.DOTALL)
    clean = re.sub(r'<tg-emoji id="[^"]*">(.*?)</tg-emoji>', r'\1', clean, flags=re.DOTALL)
    # Boshqa HTML teglari (<b>, </i> va h.k.) ni tozalash
    clean = re.sub(r'<[^>]+>', '', clean)
    return clean.strip()

def btn_emoji(key: str) -> str:
    """Tugmalar uchun xavfsiz toza piktogramma (hech qanday <emoji id="..."> tegisiz)."""
    return e(key)

be = btn_emoji

# ==================== PYROGRAM BUTTON SANITIZATION PATCH ====================
# Telegram Bot API tugma (InlineKeyboardButton va KeyboardButton) text parametrida
# HTML teglarni parse qilmaydi. Agar tugmaga <emoji id="..."> berilsa, u Telegramda xom kod
# bo'lib ko'rinib qoladi. Ushbu patch barcha tugmalarni avtomatik tozalaydi.
try:
    from pyrogram.types import InlineKeyboardButton as _IKB, KeyboardButton as _KB
    if not getattr(_IKB, "_botshield_sanitized", False):
        _orig_ikb_init = _IKB.__init__
        def _patched_ikb_init(self, text, *args, **kwargs):
            _orig_ikb_init(self, clean_btn_text(text), *args, **kwargs)
        _IKB.__init__ = _patched_ikb_init
        _IKB._botshield_sanitized = True

    if not getattr(_KB, "_botshield_sanitized", False):
        _orig_kb_init = _KB.__init__
        def _patched_kb_init(self, text, *args, **kwargs):
            _orig_kb_init(self, clean_btn_text(text), *args, **kwargs)
        _KB.__init__ = _patched_kb_init
        _KB._botshield_sanitized = True
except Exception:
    pass

def get_button_icon_id(key: str) -> str:
    """InlineKeyboardButton icon_custom_emoji_id parametri uchun ID qaytaradi."""
    info = get_custom_emoji_info(key)
    c_id = info.get("id", "")
    return str(c_id) if c_id and str(c_id).strip().isdigit() else ""

def get_random_custom_emoji_id() -> int:
    """Reaksiyalar uchun pool'dan ixtiyoriy ID qaytaradi."""
    if CUSTOM_EMOJI_POOL:
        return int(random.choice(CUSTOM_EMOJI_POOL))
    return 0

SMALL_CAPS_TRANS = str.maketrans(
    'ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ',
    'abcdefghijklmnopqrstuvwxyz'
)

def get_brand_registry_key(name: str) -> str:
    """Mahsulot nomiga qarab mos keluvchi brand registry kalitini aniqlaydi."""
    raw_str = str(name).lower()
    name_lower = raw_str.translate(SMALL_CAPS_TRANS)
    
    matches = []
    for brand, reg_key in BRAND_TO_REGISTRY_KEY.items():
        brand_norm = brand.lower().translate(SMALL_CAPS_TRANS)
        if brand_norm in name_lower:
            is_word = bool(re.search(r"\b" + re.escape(brand_norm) + r"\b", name_lower))
            # Qisqa so'zlar (<= 3 belgi: hbo, fin, gpt, ton, vip, qr) faqat mustaqil so'z sifatida mos kelsin
            if len(brand_norm) <= 3 and not is_word:
                continue
            pos = name_lower.find(brand_norm)
            matches.append((not is_word, pos, -len(brand_norm), reg_key))
            
    if matches:
        matches.sort(key=lambda x: (x[0], x[1], x[2]))
        return matches[0][3]

    # Umumiy sohalar bo'yicha aqlli moslashtirish (fallbackdan oldin)
    if any(k in name_lower for k in ["video", "clip", "shorts", "movie", "kino"]):
        return "MEDIA_VIDEO_FHD"
    if any(k in name_lower for k in ["audio", "voice", "musiqa", "sound", "mp3", "speech"]):
        return "BRAND_ELEVENLABS"
    if any(k in name_lower for k in ["ai", "agent", "gpt", "model", "prompt"]):
        return "BRAND_CHATGPT"
    if any(k in name_lower for k in ["vpn", "proxy", "security"]):
        return "BRAND_NORDVPN"
    if any(k in name_lower for k in ["code", "dev", "script", "terminal", "ide"]):
        return "DEV_CODE_SNIPPET"
    if any(k in name_lower for k in ["stream", "live", "efir"]):
        return "TOOL_LIVE_STREAM"
    if any(k in name_lower for k in ["design", "art", "photo", "rasm"]):
        return "BRAND_CANVA"
        
    return "GIFT_CASE_BOX"

def get_brand_emoji(name: str) -> str:
    """Mahsulot nomi bo'yicha formatlangan custom emoji yoki chiroyli fallback ikonkasi."""
    reg_key = get_brand_registry_key(name)
    return ce(reg_key)

def get_brand_emoji_id(name: str) -> str:
    """Mahsulot nomi bo'yicha Telegram button icon custom emoji ID."""
    reg_key = get_brand_registry_key(name)
    return get_button_icon_id(reg_key)
