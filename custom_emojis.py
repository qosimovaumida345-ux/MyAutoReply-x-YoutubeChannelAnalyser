"""
CreatorFlow Studio & AutoReply AI — Telegram Custom Emoji Master Registry

Ushbu modulda bot, web dashboard va barcha tizimlar uchun kerakli Custom Emoji'lar
har bir narsaning aniq nomi, qayerda ishlatilishi, nima uchunligi va zaxira (fallback) nomi bilan
tartibli reestrda saqlanadi.
"""

import random

# ==============================================================================
# 1. ASOSIY CUSTOM EMOJI REESTRI (Nom, Qayerdaligi, Nima uchunligi, ID va Fallback)
# ==============================================================================
CUSTOM_EMOJI_REGISTRY = {
    # --------------------------------------------------------------------------
    # 1. ASOSIY MENYU VA NAVIGATSIYA
    # --------------------------------------------------------------------------
    "BTN_HOME": {
        "name": "Bosh Menyu Uychasi",
        "location": "Asosiy bot menyusi va barcha bo'limlardan orqaga qaytish",
        "purpose": "Foydalanuvchini bosh sahifaga qaytarish",
        "id": "5974098293813152457",
        "fallback_name": "[Bosh Menyu]",
        "fallback_icon": "🏠"
    },
    "BTN_SERVICES": {
        "name": "Marketplace / Xizmatlar",
        "location": "Marketplace, xizmatlar do'koni va mahsulotlar menyusi",
        "purpose": "Raqamli xizmatlar va obunalar katalogini ochish",
        "id": "5864068125112144897",
        "fallback_name": "[Xizmatlar]",
        "fallback_icon": "💸"
    },
    "BTN_WALLET": {
        "name": "Hamyon va Balans",
        "location": "Hisobni to'ldirish, balansni tekshirish, pul yechish",
        "purpose": "Foydalanuvchi hisob-kitob bo'limini ko'rsatish",
        "id": "5343777479091831702",
        "fallback_name": "[Balans]",
        "fallback_icon": "💰"
    },
    "BTN_GAMES": {
        "name": "O'yinlar va Mini-App",
        "location": "Mini-o'yinlar, Keyslar, Fortune g'ildiragi va kazino",
        "purpose": "O'yinlar va yutuqli sovrinlar markaziga o'tish",
        "id": "5235989279024373566",
        "fallback_name": "[O'yinlar]",
        "fallback_icon": "🎮"
    },
    "BTN_ORDERS": {
        "name": "Mening Xaridlarim",
        "location": "Foydalanuvchining faol va bajarilgan buyurtmalari ro'yxati",
        "purpose": "Xarid qilingan kalitlar va tovarlarni ko'rish",
        "id": "5444856076954520455",
        "fallback_name": "[Xaridlarim]",
        "fallback_icon": "📋"
    },
    "BTN_REFERRAL": {
        "name": "Do'stlar / Referal",
        "location": "Taklif havolasi, referal daromadlari va do'stlar statistikasi",
        "purpose": "Do'stlarni taklif qilib bonus olish bo'limi",
        "id": "6319002678990998592",
        "fallback_name": "[Referal]",
        "fallback_icon": "👥"
    },
    "BTN_LEADERBOARD": {
        "name": "Liderlar Jadvali / Reyting",
        "location": "Eng ko'p xarid qilganlar va sovrindorlar ro'yxati",
        "purpose": "Foydalanuvchilar o'rtasida reyting va sovrinlar",
        "id": "5226431245918942763",
        "fallback_name": "[Liderlar]",
        "fallback_icon": "🏆"
    },
    "BTN_SUPPORT": {
        "name": "Qo'llab-quvvatlash / Admin",
        "location": "Texnik yordam, admin bilan jonli chat va savol-javob",
        "purpose": "Foydalanuvchi muammolarini hal qilish",
        "id": "5443038326535759644",
        "fallback_name": "[Yordam]",
        "fallback_icon": "🎧"
    },
    "BTN_SETTINGS": {
        "name": "Sozlamalar",
        "location": "Til sozlamalari, bildirishnomalar va profil boshqaruvi",
        "purpose": "Bot va akkaunt parametrlarini sozlash",
        "id": "5339081812821957844",
        "fallback_name": "[Sozlamalar]",
        "fallback_icon": "⚙️"
    },
    "BTN_DASHBOARD": {
        "name": "Web Dashboard Studio",
        "location": "WebApp tugmasi orqali CreatorFlow Studio sahifasini ochish",
        "purpose": "Interaktiv veb studiyaga bir bosishda kirish",
        "id": "6327577233305112811",
        "fallback_name": "[Studio]",
        "fallback_icon": "🌐"
    },
    "BTN_BACK": {
        "name": "Orqaga Qaytish",
        "location": "Har qanday ichki menyu va sahifalardan orqaga qaytish",
        "purpose": "Oldingi sahifaga qaytarish",
        "id": "5352759161945867747",
        "fallback_name": "[Orqaga]",
        "fallback_icon": "⬅️"
    },
    "BTN_NEXT": {
        "name": "Keyingi Sahifa",
        "location": "Mahsulotlar va jadvallar paginatsiyasi",
        "purpose": "Keyingi mahsulotlar ro'yxatini ko'rish",
        "id": "5433788045016969178",
        "fallback_name": "[Keyingi]",
        "fallback_icon": "➡️"
    },

    # --------------------------------------------------------------------------
    # 2. TO'LOVLAR VA MOLIYA TIZIMLARI
    # --------------------------------------------------------------------------
    "PAY_STARS": {
        "name": "Telegram Stars",
        "location": "Stars orqali depozit qilish, keys ochish va hisob to'ldirish",
        "purpose": "Telegram ichki valyutasi bilan to'lov qilish",
        "id": "5370784581341422520",
        "fallback_name": "[Stars]",
        "fallback_icon": "⭐"
    },
    "PAY_HUMO_UZCARD": {
        "name": "Bank Kartasi (Humo / Uzcard)",
        "location": "O'zbekiston bank kartalari orqali so'mda hisob to'ldirish",
        "purpose": "Milliy valyutada to'lov qabul qilish",
        "id": "5445353829304387411",
        "fallback_name": "[Karta]",
        "fallback_icon": "💳"
    },
    "PAY_TON_CRYPTO": {
        "name": "TON Blockchain / Kripto",
        "location": "TON Connect, Tonkeeper va CryptoPay orqali to'lovlar",
        "purpose": "Kriptovalyuta orqali tezkor to'lov",
        "id": "5078343973303485905",
        "fallback_name": "[TON]",
        "fallback_icon": "💎"
    },
    "PAY_PROMOCODE": {
        "name": "Promokod / Veb-cheklar",
        "location": "Promokod kiritish va sovg'a vaucherlarini faollashtirish",
        "purpose": "Bonus va chegirmalarni taqdim etish",
        "id": "5355235390980642171",
        "fallback_name": "[Promokod]",
        "fallback_icon": "🎟️"
    },
    "PAY_CASHOUT": {
        "name": "Mablag' Yechish (Cashout)",
        "location": "Balansdan foydalanuvchi hamyoniga pul chiqarish",
        "purpose": "Topilgan daromadlarni yechib olish",
        "id": "5463046637842608206",
        "fallback_name": "[Yechish]",
        "fallback_icon": "💸"
    },
    "PAY_VIP_CROWN": {
        "name": "VIP Oltin Toj",
        "location": "VIP Premium obuna sotib olish va imtiyozlar bo'limi",
        "purpose": "VIP foydalanuvchilarni ajratib ko'rsatish",
        "id": "5251422397893989847",
        "fallback_name": "[VIP]",
        "fallback_icon": "👑"
    },

    # --------------------------------------------------------------------------
    # 3. STATUSLAR VA BILDIRISHNOMALAR
    # --------------------------------------------------------------------------
    "STATUS_SUCCESS": {
        "name": "Muvaffaqiyatli Tasdiq",
        "location": "To'lov qabul qilindi, buyurtma tayyor, amal bajarildi xabarlari",
        "purpose": "Amal muvaffaqiyatli yakunlanganini tasdiqlash",
        "id": "5366395940808709418",
        "fallback_name": "[Muvaffaqiyatli]",
        "fallback_icon": "✅"
    },
    "STATUS_ERROR": {
        "name": "Xatolik / Bekor Qilish",
        "location": "Noto'g'ri buyruq, mablag' yetishmasligi, rad etish xabarlari",
        "purpose": "Xatolik haqida xabar berish",
        "id": "5416076321442777828",
        "fallback_name": "[Xatolik]",
        "fallback_icon": "❌"
    },
    "STATUS_WARNING": {
        "name": "Ogohlantirish",
        "location": "Zaxirada qolmadi, limit tugamoqda, ehtiyot bo'ling xabarlari",
        "purpose": "Foydalanuvchini ogohlantirish",
        "id": "5787656288934564517",
        "fallback_name": "[Ogohlantirish]",
        "fallback_icon": "⚠️"
    },
    "STATUS_LIGHTNING": {
        "name": "Tezkor / Yashin",
        "location": "Avtomatik zudlik bilan bajariladigan amallar, bot tezligi",
        "purpose": "Tezkor avtomatizatsiyani ifodalash",
        "id": "5456140674028019486",
        "fallback_name": "[Tezkor]",
        "fallback_icon": "⚡"
    },
    "STATUS_LOADING": {
        "name": "Yuklanmoqda / Qumsoat",
        "location": "Video yuklanmoqda, navbatda, qayta ishlanmoqda xabarlari",
        "purpose": "Jarayon ketayotganini ko'rsatish",
        "id": "5215579104807497179",
        "fallback_name": "[Yuklanmoqda]",
        "fallback_icon": "⏳"
    },
    "STATUS_SECURITY": {
        "name": "Xavfsizlik Qalqoni",
        "location": "3D Biometrik KYC, Anti-Sybil va xavfsiz to'lov himoyasi",
        "purpose": "Xavfsizlik va ishonchlilikni bildirish",
        "id": "5330194932781050507",
        "fallback_name": "[Himoyalangan]",
        "fallback_icon": "🛡️"
    },

    # --------------------------------------------------------------------------
    # 4. YOUTUBE VA VIDEO AVTOMATIZATSIYASI
    # --------------------------------------------------------------------------
    "MEDIA_VIDEO_FHD": {
        "name": "1080p FHD Video",
        "location": "Videoni eng yuqori sifatda (1080p) yuklab olish tugmasi",
        "purpose": "Yuqori sifatli video formatini tanlash",
        "id": "5292273171876034433",
        "fallback_name": "[1080p]",
        "fallback_icon": "🎬"
    },
    "MEDIA_VIDEO_HD": {
        "name": "720p HD Video",
        "location": "Videoni o'rtacha tezkor sifatda (720p) yuklab olish",
        "purpose": "Standart HD video formatini tanlash",
        "id": "5292273171876034433",
        "fallback_name": "[720p]",
        "fallback_icon": "🎬"
    },
    "MEDIA_AUDIO_MP3": {
        "name": "MP3 Musiqa / Audio",
        "location": "Videodan faqat musiqani (audio) ajratib olish tugmasi",
        "purpose": "Audio formatda yuklash",
        "id": "5422761017132202857",
        "fallback_name": "[MP3]",
        "fallback_icon": "🎵"
    },
    "MEDIA_SCISSORS": {
        "name": "Qaychi / Shorts Kesuvchi",
        "location": "Videolardan virusli YouTube Shorts bo'laklarini qirqib olish",
        "purpose": "Klip kesish va qirqish asbobi",
        "id": "5391199480022309848",
        "fallback_name": "[Qaychi]",
        "fallback_icon": "✂️"
    },
    "MEDIA_YOUTUBE": {
        "name": "YouTube Studio",
        "location": "YouTube kanalni ulash, tahlil qilish va post qo'yish",
        "purpose": "YouTube platformasi bilan ishlash",
        "id": "5368482410151295168",
        "fallback_name": "[YouTube]",
        "fallback_icon": "📺"
    },
    "MEDIA_AUTOPILOT": {
        "name": "Sun'iy Intellekt Avtopilot",
        "location": "Instagram Reels'dan YouTube Shorts'ga avtomatik klonlash",
        "purpose": "Avtonom robot faoliyatini ifodalash",
        "id": "5249493957578078525",
        "fallback_name": "[Avtopilot]",
        "fallback_icon": "🤖"
    },

    # --------------------------------------------------------------------------
    # 5. TELEGRAM STARS KEYS SOVRINLARI (DROPS & GIFTS)
    # --------------------------------------------------------------------------
    "GIFT_CASE_BOX": {
        "name": "Sovg'a Qutisi (Keys)",
        "location": "Stars Keyslar do'koni va keysni ochish interfeysi",
        "purpose": "Sovrinli qutini ifodalash",
        "id": "6319002678990998592",
        "fallback_name": "[Keys]",
        "fallback_icon": "🎁"
    },
    "GIFT_STAR": {
        "name": "Yulduz Sovg'asi",
        "location": "Yulduz sovrini, Stars yutug'i",
        "purpose": "Yulduzli yutuqni ko'rsatish",
        "id": "6215463953925934839",
        "fallback_name": "[Yulduz]",
        "fallback_icon": "⭐"
    },
    "GIFT_CAKE": {
        "name": "Tug'ilgan Kun Torti",
        "location": "Telegram Cake sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5440539497383087970",
        "fallback_name": "[Tort]",
        "fallback_icon": "🎂"
    },
    "GIFT_TEDDY": {
        "name": "Yumshoq Ayiqcha",
        "location": "Telegram Teddy Bear sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5258362837411045098",
        "fallback_name": "[Ayiqcha]",
        "fallback_icon": "🧸"
    },
    "GIFT_BOUQUET": {
        "name": "Gul Dastasi",
        "location": "Telegram Bouquet sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5350354474181343974",
        "fallback_name": "[Guldasta]",
        "fallback_icon": "💐"
    },
    "GIFT_CHAMPAGNE": {
        "name": "Bayram Shampani",
        "location": "Telegram Champagne sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5453902265922376865",
        "fallback_name": "[Shampan]",
        "fallback_icon": "🍾"
    },
    "GIFT_DIAMOND_RING": {
        "name": "Olmos Uzuk",
        "location": "Telegram Ring sovg'asi drop elementi",
        "purpose": "Qimmatbaho sovg'a yutug'ini bildirish",
        "id": "5427168083074628963",
        "fallback_name": "[Uzuk]",
        "fallback_icon": "💍"
    },
    "GIFT_TROPHY": {
        "name": "G'oliblik Kubogi",
        "location": "Telegram Trophy sovg'asi drop elementi",
        "purpose": "Katta sovrin yutug'ini bildirish",
        "id": "5226431245918942763",
        "fallback_name": "[Kubok]",
        "fallback_icon": "🏆"
    },
    "GIFT_ROCKET": {
        "name": "Tezkor Raketa",
        "location": "Telegram Rocket sovg'asi drop elementi",
        "purpose": "Super yutuqni bildirish",
        "id": "5465467698022468218",
        "fallback_name": "[Raketa]",
        "fallback_icon": "🚀"
    },
    "GIFT_CAP": {
        "name": "Zamonaviy Kepka",
        "location": "Telegram Cap sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5276503688347688082",
        "fallback_name": "[Kepka]",
        "fallback_icon": "🧢"
    },
    "GIFT_PLUSH": {
        "name": "Plushie O'yinchoq",
        "location": "Telegram Plushie sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5258362837411045098",
        "fallback_name": "[O'yinchoq]",
        "fallback_icon": "🐸"
    },
    "GIFT_CROWN": {
        "name": "Podshoh Toji (NFT)",
        "location": "Telegram Crown sovg'asi va eksklyuziv NFT",
        "purpose": "Nodir NFT yutug'ini bildirish",
        "id": "5251422397893989847",
        "fallback_name": "[Toj]",
        "fallback_icon": "👑"
    },
    "GIFT_PREMIUM": {
        "name": "Telegram Premium",
        "location": "Telegram Premium obunasi sovg'asi",
        "purpose": "Premium obunasi yutug'ini bildirish",
        "id": "6215463953925934839",
        "fallback_name": "[Premium]",
        "fallback_icon": "🌟"
    }
}

# ==============================================================================
# 2. XIZMATLAR VA KOMPANIYALAR BRENDLARI XARITASI (Marketplace Services)
# ==============================================================================
BRAND_EMOJIS_MAP = {
    "creatorflow": "5902340522852227618",
    "our_logo": "5902340522852227618",
    "logo": "5902340522852227618",
    "bot_logo": "5902340522852227618",
    "chatgpt": "6149863405130879277",
    "openai": "6149863405130879277",
    "gpt": "6149863405130879277",
    "claude": "5899837428797020489",
    "gemini": "5262838511161076891",
    "capcut": "5978895591894161700",
    "elevenlabs": "5276358956539751308",
    "figma": "5275973813937423325",
    "canva": "5274132119075989107",
    "spotify": "5274194232893024229",
    "netflix": "5276399801678735778",
    "nordvpn": "5273747423150253161",
    "stars": "5370784581341422520",
    "ton": "5078343973303485905",
    "humo": "5445353829304387411",
    "uzcard": "5445353829304387411"
}

# Mavjud tizimlar bilan 100% orqaga moslik (Backward Compatibility)
EMOJI_MAP = {
    k: (v["id"], v["fallback_icon"]) for k, v in CUSTOM_EMOJI_REGISTRY.items()
}

CUSTOM_EMOJI_POOL = [
    v["id"] for v in CUSTOM_EMOJI_REGISTRY.values() if v.get("id")
]

# ==============================================================================
# 3. YORDAMCHI FUNKSIYALAR
# ==============================================================================
def get_custom_emoji_info(key: str) -> dict:
    """Emoji haqidagi to'liq metama'lumotlarni qaytaradi."""
    return CUSTOM_EMOJI_REGISTRY.get(key, {
        "name": key,
        "location": "Noma'lum",
        "purpose": "Noma'lum",
        "id": "",
        "fallback_name": f"[{key}]",
        "fallback_icon": "✨"
    })

def e(key: str) -> str:
    """Fallback piktogrammani qaytaradi."""
    if key in CUSTOM_EMOJI_REGISTRY:
        return CUSTOM_EMOJI_REGISTRY[key]["fallback_icon"]
    return "✨"

def custom_emoji(key: str) -> str:
    """
    Telegram xabarlarida chiroyli Custom Emoji chiqishi uchun <emoji id="..."> HTML tegi.
    Agar ID bo'lmasa, fallback icon chiqariladi.
    """
    if key in CUSTOM_EMOJI_REGISTRY:
        info = CUSTOM_EMOJI_REGISTRY[key]
        c_id = info.get("id")
        fb = info.get("fallback_icon", "✨")
        if c_id:
            return f'<emoji id="{c_id}">{fb}</emoji>'
        return fb
    return "✨"

ce = custom_emoji

def get_button_icon_id(key: str) -> str:
    """InlineKeyboardButton icon_custom_emoji_id parametri uchun ID qaytaradi."""
    if key in CUSTOM_EMOJI_REGISTRY:
        return CUSTOM_EMOJI_REGISTRY[key].get("id", "")
    return ""

def get_random_custom_emoji_id() -> int:
    """Reaksiyalar uchun pool'dan ixtiyoriy ID qaytaradi."""
    if CUSTOM_EMOJI_POOL:
        return int(random.choice(CUSTOM_EMOJI_POOL))
    return 5366395940808709418

