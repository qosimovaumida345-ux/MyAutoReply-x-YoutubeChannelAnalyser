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
    # 1. ASOSIY MENYU VA NAVIGATSIYA (1-12)
    # --------------------------------------------------------------------------
    "BTN_HOME": {
        "num": 1,
        "name": "Bosh Menyu Uychasi",
        "location": "Asosiy bot menyusi va barcha bo'limlardan orqaga qaytish",
        "purpose": "Foydalanuvchini bosh sahifaga qaytarish",
        "id": "5438499684270238914",
        "fallback_name": "[Bosh Menyu]",
        "fallback_icon": "🏠"
    },
    "BTN_SERVICES": {
        "num": 2,
        "name": "Marketplace / Xizmatlar",
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
        "id": "5265197972919964944",
        "fallback_name": "[Balans]",
        "fallback_icon": "💰"
    },
    "BTN_GAMES": {
        "num": 4,
        "name": "O'yinlar va Mini-App",
        "location": "Mini-o'yinlar, Keyslar, Fortune g'ildiragi va kazino",
        "purpose": "O'yinlar va yutuqli sovrinlar markaziga o'tish",
        "id": "5213430392798851273",
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
        "id": "5944970130554359187",
        "fallback_name": "[Referal]",
        "fallback_icon": "👥"
    },
    "BTN_LEADERBOARD": {
        "num": 7,
        "name": "Liderlar Jadvali / Reyting",
        "location": "Eng ko'p xarid qilganlar va sovrindorlar ro'yxati",
        "purpose": "Foydalanuvchilar o'rtasida reyting va sovrinlar",
        "id": "5307608734858484532",
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
        "id": "4967490064234840998",
        "fallback_name": "[Sozlamalar]",
        "fallback_icon": "⚙️"
    },
    "BTN_DASHBOARD": {
        "num": 10,
        "name": "Web Dashboard Studio",
        "location": "WebApp tugmasi orqali CreatorFlow Studio sahifasini ochish",
        "purpose": "Interaktiv veb studiyaga bir bosishda kirish",
        "id": "5336852359723100852",
        "fallback_name": "[Studio]",
        "fallback_icon": "🌐"
    },
    "BTN_BACK": {
        "num": 11,
        "name": "Orqaga Qaytish",
        "location": "Har qanday ichki menyu va sahifalardan orqaga qaytish",
        "purpose": "Oldingi sahifaga qaytarish",
        "id": "5416113713428057601",
        "fallback_name": "[Orqaga]",
        "fallback_icon": "⬅️"
    },
    "BTN_NEXT": {
        "num": 12,
        "name": "Keyingi Sahifa",
        "location": "Mahsulotlar va jadvallar paginatsiyasi",
        "purpose": "Keyingi mahsulotlar ro'yxatini ko'rish",
        "id": "5415758949129404605",
        "fallback_name": "[Keyingi]",
        "fallback_icon": "➡️"
    },

    # --------------------------------------------------------------------------
    # 2. TO'LOVLAR VA MOLIYA TIZIMLARI (13-18)
    # --------------------------------------------------------------------------
    "PAY_STARS": {
        "num": 13,
        "name": "Telegram Stars",
        "location": "Stars orqali depozit qilish, keys ochish va hisob to'ldirish",
        "purpose": "Telegram ichki valyutasi bilan to'lov qilish",
        "id": "5370784581341422520",
        "fallback_name": "[Stars]",
        "fallback_icon": "⭐"
    },
    "PAY_HUMO_UZCARD": {
        "num": 14,
        "name": "Bank Kartasi (Humo / Uzcard)",
        "location": "O'zbekiston bank kartalari orqali so'mda hisob to'ldirish",
        "purpose": "Milliy valyutada to'lov qabul qilish",
        "id": "5445353829304387411",
        "fallback_name": "[Karta]",
        "fallback_icon": "💳"
    },
    "PAY_TON_CRYPTO": {
        "num": 15,
        "name": "TON Blockchain / Kripto",
        "location": "TON Connect, Tonkeeper va CryptoPay orqali to'lovlar",
        "purpose": "Kriptovalyuta orqali tezkor to'lov",
        "id": "5077829135573714360",
        "fallback_name": "[TON]",
        "fallback_icon": "💎"
    },
    "PAY_PROMOCODE": {
        "num": 16,
        "name": "Promokod / Veb-cheklar",
        "location": "Promokod kiritish va sovg'a vaucherlarini faollashtirish",
        "purpose": "Bonus va chegirmalarni taqdim etish",
        "id": "6187973994273050060",
        "fallback_name": "[Promokod]",
        "fallback_icon": "🎟️"
    },
    "PAY_CASHOUT": {
        "num": 17,
        "name": "Mablag' Yechish (Cashout)",
        "location": "Balansdan foydalanuvchi hamyoniga pul chiqarish",
        "purpose": "Topilgan daromadlarni yechib olish",
        "id": "5472250091332993630",
        "fallback_name": "[Yechish]",
        "fallback_icon": "💸"
    },
    "PAY_VIP_CROWN": {
        "num": 18,
        "name": "VIP Oltin Toj",
        "location": "VIP Premium obuna sotib olish va imtiyozlar bo'limi",
        "purpose": "VIP foydalanuvchilarni ajratib ko'rsatish",
        "id": "5274225173837394638",
        "fallback_name": "[VIP]",
        "fallback_icon": "👑"
    },

    # --------------------------------------------------------------------------
    # 3. STATUSLAR VA BILDIRISHNOMALAR (19-24)
    # --------------------------------------------------------------------------
    "STATUS_SUCCESS": {
        "num": 19,
        "name": "Muvaffaqiyatli Tasdiq",
        "location": "To'lov qabul qilindi, buyurtma tayyor, amal bajarildi xabarlari",
        "purpose": "Amal muvaffaqiyatli yakunlanganini tasdiqlash",
        "id": "5350722806281676158",
        "fallback_name": "[Muvaffaqiyatli]",
        "fallback_icon": "✅"
    },
    "STATUS_ERROR": {
        "num": 20,
        "name": "Xatolik / Bekor Qilish",
        "location": "Noto'g'ri buyruq, mablag' yetishmasligi, rad etish xabarlari",
        "purpose": "Xatolik haqida xabar berish",
        "id": "5391352243419108983",
        "fallback_name": "[Xatolik]",
        "fallback_icon": "❌"
    },
    "STATUS_WARNING": {
        "num": 21,
        "name": "Ogohlantirish",
        "location": "Zaxirada qolmadi, limit tugamoqda, ehtiyot bo'ling xabarlari",
        "purpose": "Foydalanuvchini ogohlantirish",
        "id": "5395358455768837479",
        "fallback_name": "[Ogohlantirish]",
        "fallback_icon": "⚠️"
    },
    "STATUS_LIGHTNING": {
        "num": 22,
        "name": "Tezkor / Yashin",
        "location": "Avtomatik zudlik bilan bajariladigan amallar, bot tezligi",
        "purpose": "Tezkor avtomatizatsiyani ifodalash",
        "id": "5258203794772085854",
        "fallback_name": "[Tezkor]",
        "fallback_icon": "⚡"
    },
    "STATUS_LOADING": {
        "num": 23,
        "name": "Yuklanmoqda / Qumsoat",
        "location": "Video yuklanmoqda, navbatda, qayta ishlanmoqda xabarlari",
        "purpose": "Jarayon ketayotganini ko'rsatish",
        "id": "6113844439292054570",
        "fallback_name": "[Yuklanmoqda]",
        "fallback_icon": "⏳"
    },
    "STATUS_SECURITY": {
        "num": 24,
        "name": "Xavfsizlik Qalqoni",
        "location": "3D Biometrik KYC, Anti-Sybil va xavfsiz to'lov himoyasi",
        "purpose": "Xavfsizlik va ishonchlilikni bildirish",
        "id": "5348129380474306311",
        "fallback_name": "[Himoyalangan]",
        "fallback_icon": "🛡️"
    },

    # --------------------------------------------------------------------------
    # 4. YOUTUBE VA VIDEO AVTOMATIZATSIYASI (25-30)
    # --------------------------------------------------------------------------
    "MEDIA_VIDEO_FHD": {
        "num": 25,
        "name": "1080p FHD Video",
        "location": "Videoni eng yuqori sifatda (1080p) yuklab olish tugmasi",
        "purpose": "Yuqori sifatli video formatini tanlash",
        "id": "5082592692391641768",
        "fallback_name": "[1080p]",
        "fallback_icon": "🎬"
    },
    "MEDIA_VIDEO_HD": {
        "num": 26,
        "name": "720p HD Video",
        "location": "Videoni o'rtacha tezkor sifatda (720p) yuklab olish",
        "purpose": "Standart HD video formatini tanlash",
        "id": "5334867784184641928",
        "fallback_name": "[720p]",
        "fallback_icon": "🎬"
    },
    "MEDIA_AUDIO_MP3": {
        "num": 27,
        "name": "MP3 Musiqa / Audio",
        "location": "Videodan faqat musiqani (audio) ajratib olish tugmasi",
        "purpose": "Audio formatda yuklash",
        "id": "5194988065222831801",
        "fallback_name": "[MP3]",
        "fallback_icon": "🎵"
    },
    "MEDIA_SCISSORS": {
        "num": 28,
        "name": "Qaychi / Shorts Kesuvchi",
        "location": "Videolardan virusli YouTube Shorts bo'laklarini qirqib olish",
        "purpose": "Klip kesish va qirqish asbobi",
        "id": "5422781517011111694",
        "fallback_name": "[Qaychi]",
        "fallback_icon": "✂️"
    },
    "MEDIA_YOUTUBE": {
        "num": 29,
        "name": "YouTube Studio",
        "location": "YouTube kanalni ulash, tahlil qilish va post qo'yish",
        "purpose": "YouTube platformasi bilan ishlash",
        "id": "4999366254943798100",
        "fallback_name": "[YouTube]",
        "fallback_icon": "📺"
    },
    "MEDIA_AUTOPILOT": {
        "num": 30,
        "name": "Sun'iy Intellekt Avtopilot",
        "location": "Instagram Reels'dan YouTube Shorts'ga avtomatik klonlash",
        "purpose": "Avtonom robot faoliyatini ifodalash",
        "id": "5258093637450866522",
        "fallback_name": "[Avtopilot]",
        "fallback_icon": "🤖"
    },

    # --------------------------------------------------------------------------
    # 5. TELEGRAM STARS KEYS SOVRINLARI (DROPS & GIFTS) (31-43)
    # --------------------------------------------------------------------------
    "GIFT_CASE_BOX": {
        "num": 31,
        "name": "Sovg'a Qutisi (Keys)",
        "location": "Stars Keyslar do'koni va keysni ochish interfeysi",
        "purpose": "Sovrinli qutini ifodalash",
        "id": "5280615440928758599",
        "fallback_name": "[Keys]",
        "fallback_icon": "🎁"
    },
    "GIFT_STAR": {
        "num": 32,
        "name": "Yulduz Sovg'asi",
        "location": "Yulduz sovrini, Stars yutug'i",
        "purpose": "Yulduzli yutuqni ko'rsatish",
        "id": "5954135079662916434",
        "fallback_name": "[Yulduz]",
        "fallback_icon": "⭐"
    },
    "GIFT_CAKE": {
        "num": 33,
        "name": "Tug'ilgan Kun Torti",
        "location": "Telegram Cake sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5375428965701792222",
        "fallback_name": "[Tort]",
        "fallback_icon": "🎂"
    },
    "GIFT_TEDDY": {
        "num": 34,
        "name": "Yumshoq Ayiqcha",
        "location": "Telegram Teddy Bear sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5280598054901145762",
        "fallback_name": "[Ayiqcha]",
        "fallback_icon": "🧸"
    },
    "GIFT_BOUQUET": {
        "num": 35,
        "name": "Gul Dastasi",
        "location": "Telegram Bouquet sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5192959294470895031",
        "fallback_name": "[Guldasta]",
        "fallback_icon": "💐"
    },
    "GIFT_CHAMPAGNE": {
        "num": 36,
        "name": "Bayram Shampani",
        "location": "Telegram Champagne sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5177355596680135376",
        "fallback_name": "[Shampan]",
        "fallback_icon": "🍾"
    },
    "GIFT_DIAMOND_RING": {
        "num": 37,
        "name": "Olmos Uzuk",
        "location": "Telegram Ring sovg'asi drop elementi",
        "purpose": "Qimmatbaho sovg'a yutug'ini bildirish",
        "id": "5355255362578573990",
        "fallback_name": "[Uzuk]",
        "fallback_icon": "💍"
    },
    "GIFT_TROPHY": {
        "num": 38,
        "name": "G'oliblik Kubogi",
        "location": "Telegram Trophy sovg'asi drop elementi",
        "purpose": "Katta sovrin yutug'ini bildirish",
        "id": "5226431245918942763",
        "fallback_name": "[Kubok]",
        "fallback_icon": "🏆"
    },
    "GIFT_ROCKET": {
        "num": 39,
        "name": "Tezkor Raketa",
        "location": "Telegram Rocket sovg'asi drop elementi",
        "purpose": "Super yutuqni bildirish",
        "id": "5312211050014202213",
        "fallback_name": "[Raketa]",
        "fallback_icon": "🚀"
    },
    "GIFT_CAP": {
        "num": 40,
        "name": "Zamonaviy Kepka",
        "location": "Telegram Cap sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5411472846645914012",
        "fallback_name": "[Kepka]",
        "fallback_icon": "🧢"
    },
    "GIFT_PLUSH": {
        "num": 41,
        "name": "Plushie O'yinchoq",
        "location": "Telegram Plushie sovg'asi drop elementi",
        "purpose": "Sovg'a yutug'ini bildirish",
        "id": "5192879906295397710",
        "fallback_name": "[O'yinchoq]",
        "fallback_icon": "🐸"
    },
    "GIFT_CROWN": {
        "num": 42,
        "name": "Podshoh Toji (NFT)",
        "location": "Telegram Crown sovg'asi va eksklyuziv NFT",
        "purpose": "Nodir NFT yutug'ini bildirish",
        "id": "5217822164362739968",
        "fallback_name": "[Toj]",
        "fallback_icon": "👑"
    },
    "GIFT_PREMIUM": {
        "num": 43,
        "name": "Telegram Premium",
        "location": "Telegram Premium obunasi sovg'asi",
        "purpose": "Premium obunasi yutug'ini bildirish",
        "id": "5983591923883972553",
        "fallback_name": "[Premium]",
        "fallback_icon": "🌟"
    },

    # --------------------------------------------------------------------------
    # 6. MINI-O'YINLAR VA KAZINO (44-57)
    # --------------------------------------------------------------------------
    "GAME_COINFLIP": {
        "num": 44,
        "name": "Tanga Tashlash (Coinflip)",
        "location": "PvP Duel tanga tashlash bellashuvi tugmasi va natijasi",
        "purpose": "Tangani ifodalash",
        "id": "5269254848703902904",
        "fallback_name": "[Tanga]",
        "fallback_icon": "🪙"
    },
    "GAME_SLOTS": {
        "num": 45,
        "name": "Slot 777 / Kazino Barabani",
        "location": "Slot mashinasi mini-o'yini",
        "purpose": "Kazino barabanini ifodalash",
        "id": "5235989279024373566",
        "fallback_name": "[Slot]",
        "fallback_icon": "🎰"
    },
    "GAME_MINES_BOMB": {
        "num": 46,
        "name": "Saper Bombasi (Mina)",
        "location": "Mines (Saper) o'yinida portlash katagi",
        "purpose": "Bombani ifodalash",
        "id": "5375445874988036618",
        "fallback_name": "[Bomba]",
        "fallback_icon": "💣"
    },
    "GAME_MINES_GEM": {
        "num": 47,
        "name": "Saper Olmosi (Xavfsiz)",
        "location": "Mines (Saper) o'yinida xavfsiz yutuq katagi",
        "purpose": "Xavfsiz olmosni ifodalash",
        "id": "5427168083074628963",
        "fallback_name": "[Olmos]",
        "fallback_icon": "💎"
    },
    "GAME_CRASH_ROCKET": {
        "num": 48,
        "name": "Aviator / Crash Uchog'i",
        "location": "Live Crash (Aviator) mini-o'yinida parvoz qiluvchi uchoq",
        "purpose": "Uchuvchi samolyotni ifodalash",
        "id": "5251238414379918054",
        "fallback_name": "[Uchoq]",
        "fallback_icon": "🚀"
    },
    "GAME_CRASH_BOOM": {
        "num": 49,
        "name": "Aviator Portlashi (Crash)",
        "location": "Aviator o'yinida uchog' qulaganda chiqadigan portlash",
        "purpose": "O'yin to'xtaganini ifodalash",
        "id": "5312556885075829938",
        "fallback_name": "[Portlash]",
        "fallback_icon": "💥"
    },
    "GAME_APPLE_GOOD": {
        "num": 50,
        "name": "Omadli Butun Olma",
        "location": "Apple of Fortune o'yinida yutuqli qator",
        "purpose": "Yaxshi olmani ifodalash",
        "id": "5318947543009224152",
        "fallback_name": "[Yashil Olma]",
        "fallback_icon": "🍏"
    },
    "GAME_APPLE_BAD": {
        "num": 51,
        "name": "Tishlangan / Qurt Olma",
        "location": "Apple of Fortune o'yinida yutqazuvchi qator",
        "purpose": "Yaroqsiz olmani ifodalash",
        "id": "5332628018869319821",
        "fallback_name": "[Qurt Olma]",
        "fallback_icon": "🍎"
    },
    "GAME_CARD_HEARTS": {
        "num": 52,
        "name": "Karta Qizil Yurak",
        "location": "21 (Blackjack) o'yinida yurak kartalari",
        "purpose": "Qizil yurak mastini ifodalash",
        "id": "",
        "fallback_name": "[Yurak]",
        "fallback_icon": "♥️"
    },
    "GAME_CARD_SPADES": {
        "num": 53,
        "name": "Karta Qora Qarg'a",
        "location": "21 (Blackjack) o'yinida qarg'a kartalari",
        "purpose": "Qora qarg'a mastini ifodalash",
        "id": "",
        "fallback_name": "[Qarg'a]",
        "fallback_icon": "♠️"
    },
    "GAME_CARD_DIAMONDS": {
        "num": 54,
        "name": "Karta Qizil G'isht",
        "location": "21 (Blackjack) o'yinida g'isht kartalari",
        "purpose": "G'isht mastini ifodalash",
        "id": "",
        "fallback_name": "[G'isht]",
        "fallback_icon": "♦️"
    },
    "GAME_CARD_CLUBS": {
        "num": 55,
        "name": "Karta Qora Chillik",
        "location": "21 (Blackjack) o'yinida chillik kartalari",
        "purpose": "Chillik mastini ifodalash",
        "id": "",
        "fallback_name": "[Chillik]",
        "fallback_icon": "♣️"
    },
    "GAME_CARD_BACK": {
        "num": 56,
        "name": "Yopiq Karta Orqasi",
        "location": "Diler kartasi yopiq turganda",
        "purpose": "Yashirin kartani ifodalash",
        "id": "",
        "fallback_name": "[Yopiq Karta]",
        "fallback_icon": "🂠"
    },
    "GAME_WHEEL_SPIN": {
        "num": 57,
        "name": "Aylanuvchi Charxpalak",
        "location": "Lucky Wheel kundalik aylantirish tugmasi",
        "purpose": "Omad g'ildiragini ifodalash",
        "id": "5017339507666584402",
        "fallback_name": "[Charxpalak]",
        "fallback_icon": "🎯"
    },

    # --------------------------------------------------------------------------
    # 7. XIZMATLAR VA TOP BRENDLAR (58-70)
    # --------------------------------------------------------------------------
    "BRAND_CHATGPT": {
        "num": 58,
        "name": "ChatGPT / OpenAI Logotipi",
        "location": "Marketplace'da ChatGPT Plus / OpenAI tovarlari",
        "purpose": "OpenAI mahsulotlarini belgilash",
        "id": "6134246530380472478",
        "fallback_name": "[ChatGPT]",
        "fallback_icon": "🤖"
    },
    "BRAND_CLAUDE": {
        "num": 59,
        "name": "Claude / Anthropic Logotipi",
        "location": "Marketplace'da Claude Pro / Anthropic tovarlari",
        "purpose": "Claude mahsulotlarini belgilash",
        "id": "6131771460986872161",
        "fallback_name": "[Claude]",
        "fallback_icon": "🧠"
    },
    "BRAND_GEMINI": {
        "num": 60,
        "name": "Google Gemini Logotipi",
        "location": "Marketplace'da Gemini Advanced tovarlari va narx kuzatuvchi",
        "purpose": "Gemini mahsulotlarini belgilash",
        "id": "5262838511161076891",
        "fallback_name": "[Gemini]",
        "fallback_icon": "🔷"
    },
    "BRAND_CAPCUT": {
        "num": 61,
        "name": "CapCut Pro Logotipi",
        "location": "CapCut Pro obunalari va almashuv bo'limi",
        "purpose": "CapCut mahsulotlarini belgilash",
        "id": "5978895591894161700",
        "fallback_name": "[CapCut]",
        "fallback_icon": "🎬"
    },
    "BRAND_ELEVENLABS": {
        "num": 62,
        "name": "ElevenLabs Ovoz AI Logotipi",
        "location": "Ovoz klonlash va audio generatsiya xizmatlari",
        "purpose": "ElevenLabs xizmatini belgilash",
        "id": "6219689196722854904",
        "fallback_name": "[ElevenLabs]",
        "fallback_icon": "🔊"
    },
    "BRAND_FIGMA": {
        "num": 63,
        "name": "Figma Dizayn Logotipi",
        "location": "Figma Pro obunasi xizmati",
        "purpose": "Figma mahsulotini belgilash",
        "id": "6127461826377556681",
        "fallback_name": "[Figma]",
        "fallback_icon": "🎨"
    },
    "BRAND_CANVA": {
        "num": 64,
        "name": "Canva Pro Logotipi",
        "location": "Canva Pro obunasi xizmati",
        "purpose": "Canva mahsulotini belgilash",
        "id": "5274132119075989107",
        "fallback_name": "[Canva]",
        "fallback_icon": "🎨"
    },
    "BRAND_SPOTIFY": {
        "num": 65,
        "name": "Spotify Premium Logotipi",
        "location": "Spotify Premium musiqa obunasi",
        "purpose": "Spotify mahsulotini belgilash",
        "id": "5346074681004801565",
        "fallback_name": "[Spotify]",
        "fallback_icon": "🎵"
    },
    "BRAND_NETFLIX": {
        "num": 66,
        "name": "Netflix 4K Logotipi",
        "location": "Netflix Premium obunasi",
        "purpose": "Netflix mahsulotini belgilash",
        "id": "5318911503938634641",
        "fallback_name": "[Netflix]",
        "fallback_icon": "🍿"
    },
    "BRAND_NORDVPN": {
        "num": 67,
        "name": "NordVPN Logotipi",
        "location": "NordVPN xavfsiz VPN obunasi",
        "purpose": "VPN mahsulotini belgilash",
        "id": "5273929435274322900",
        "fallback_name": "[NordVPN]",
        "fallback_icon": "🛡️"
    },
    "BRAND_WINDOWS": {
        "num": 68,
        "name": "Windows / Microsoft Logotipi",
        "location": "Windows litsenziya kalitlari va Office tovarlari",
        "purpose": "Windows mahsulotlarini belgilash",
        "id": "5276035412358374909",
        "fallback_name": "[Windows]",
        "fallback_icon": "🪟"
    },
    "BRAND_APPLE": {
        "num": 69,
        "name": "Apple Logotipi",
        "location": "Apple ID, iCloud va Apple TV xizmatlari",
        "purpose": "Apple mahsulotlarini belgilash",
        "id": "5334955749409834455",
        "fallback_name": "[Apple]",
        "fallback_icon": "🍏"
    },
    "BRAND_CURSOR": {
        "num": 70,
        "name": "Cursor IDE AI Logotipi",
        "location": "Cursor AI dasturchi obunasi tovari",
        "purpose": "Cursor mahsulotini belgilash",
        "id": "6273793612715138423",
        "fallback_name": "[Cursor]",
        "fallback_icon": "💻"
    },

    # --------------------------------------------------------------------------
    # 8. QO'SHIMCHA ASBOBLAR VA STATISTIKA (71-82)
    # --------------------------------------------------------------------------
    "TOOL_SEARCH": {
        "num": 71,
        "name": "Qidiruv / Lupa",
        "location": "Katalogda tovar yoki kanal qidirish tugmasi",
        "purpose": "Qidiruv amalini ifodalash",
        "id": "5429419796988970289",
        "fallback_name": "[Qidiruv]",
        "fallback_icon": "🔍"
    },
    "TOOL_FIRE": {
        "num": 72,
        "name": "Trend / Olov",
        "location": "Eng ko'p sotilgan xizmatlar va trendlar",
        "purpose": "Ommaboplikni ifodalash",
        "id": "5256047523620995497",
        "fallback_name": "[Trend]",
        "fallback_icon": "🔥"
    },
    "TOOL_EYE_VIEWS": {
        "num": 73,
        "name": "Ko'rishlar Soni (Views)",
        "location": "YouTube kanal statistikasi va ko'rishlar",
        "purpose": "Ko'rishlar sonini ifodalash",
        "id": "5210956306952758910",
        "fallback_name": "[Ko'rishlar]",
        "fallback_icon": "👁️"
    },
    "TOOL_HEART_LIKE": {
        "num": 74,
        "name": "Layklar (Likes)",
        "location": "Video layklari va obunachilar hissiyoti",
        "purpose": "Layklarni ifodalash",
        "id": "5251583347498434053",
        "fallback_name": "[Layk]",
        "fallback_icon": "❤️"
    },
    "TOOL_COMMENTS": {
        "num": 75,
        "name": "Izohlar (Comments)",
        "location": "Video izohlari va fikrlar statistikasi",
        "purpose": "Izohlarni ifodalash",
        "id": "5253687331717659694",
        "fallback_name": "[Izohlar]",
        "fallback_icon": "💬"
    },
    "TOOL_CALENDAR": {
        "num": 76,
        "name": "Taqvim / Sana",
        "location": "Post rejalashtirish sanasi va muddat",
        "purpose": "Vaqt va sanani ifodalash",
        "id": "5413879192267805083",
        "fallback_name": "[Taqvim]",
        "fallback_icon": "📅"
    },
    "TOOL_GRAPH_UP": {
        "num": 77,
        "name": "O'sish Grafigi",
        "location": "Kanal o'sishi ko'rsatkichi",
        "purpose": "Ijobiy rivojlanishni ifodalash",
        "id": "5258194577772274087",
        "fallback_name": "[O'sish]",
        "fallback_icon": "📈"
    },
    "TOOL_SPY_ANALYTICS": {
        "num": 78,
        "name": "Raqobatchi Tahlili (Spy)",
        "location": "Raqobatchi kanallarni kuzatish asbobi",
        "purpose": "Tahlil va josuslik asbobini ifodalash",
        "id": "5818800823374713651",
        "fallback_name": "[Tahlilchi]",
        "fallback_icon": "🕵️"
    },
    "TOOL_MIC_VOICE": {
        "num": 79,
        "name": "Mikrofon / Ovoz",
        "location": "AI ovozli xabarlar va diktor ovozi",
        "purpose": "Ovozli xizmatlarni ifodalash",
        "id": "5429413328768224565",
        "fallback_name": "[Mikrofon]",
        "fallback_icon": "🎙️"
    },
    "TOOL_QR_CODE": {
        "num": 80,
        "name": "QR Kod / DeepLink",
        "location": "To'lov QR kodi va referal QR havolasi",
        "purpose": "QR kodni ifodalash",
        "id": "5440410042773824003",
        "fallback_name": "[QR Kod]",
        "fallback_icon": "📲"
    },
    "TOOL_TAG_PRICE": {
        "num": 81,
        "name": "Narx Birkasi",
        "location": "Chegirma va aksiyalar birkasi",
        "purpose": "Narxni ajratib ko'rsatish",
        "id": "5298877105000439431",
        "fallback_name": "[Narx]",
        "fallback_icon": "🏷️"
    },
    "TOOL_VIP_STAR": {
        "num": 82,
        "name": "Yorqin Yulduzcha Nishoni",
        "location": "VIP foydalanuvchi laqabi yonidagi nishon",
        "purpose": "Premium maqomini ifodalash",
        "id": "5229011542011299168",
        "fallback_name": "[Yulduzcha]",
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
    "chatgpt": "6134246530380472478",
    "openai": "6134246530380472478",
    "gpt": "6134246530380472478",
    "claude": "6131771460986872161",
    "gemini": "5262838511161076891",
    "capcut": "5978895591894161700",
    "elevenlabs": "6219689196722854904",
    "figma": "6127461826377556681",
    "canva": "5274132119075989107",
    "spotify": "5346074681004801565",
    "netflix": "5318911503938634641",
    "nordvpn": "5273929435274322900",
    "windows": "5276035412358374909",
    "apple": "5334955749409834455",
    "cursor": "6273793612715138423",
    "stars": "5370784581341422520",
    "ton": "5077829135573714360",
    "humo": "5445353829304387411",
    "uzcard": "5445353829304387411"
}

# ==============================================================================
# 3. KODDAGI QISQA NOMLAR VA ALIASLAR XARITASI (Codebase Aliases Map)
# ==============================================================================
ALIASES = {
    # Tugmalar (Buttons)
    "HOME": "BTN_HOME",
    "SERVICES": "BTN_SERVICES",
    "WALLET": "BTN_WALLET",
    "GAMES": "BTN_GAMES",
    "ORDERS": "BTN_ORDERS",
    "REFERRAL": "BTN_REFERRAL",
    "LEADERBOARD": "BTN_LEADERBOARD",
    "SUPPORT": "BTN_SUPPORT",
    "SETTINGS": "BTN_SETTINGS",
    "DASHBOARD": "BTN_DASHBOARD",
    "BACK": "BTN_BACK",
    "NEXT": "BTN_NEXT",
    "PREV": "BTN_BACK",

    # To'lov va Moliya
    "STARS": "PAY_STARS",
    "STAR": "PAY_STARS",
    "YULDUZ": "PAY_STARS",
    "HUMO": "PAY_HUMO_UZCARD",
    "UZCARD": "PAY_HUMO_UZCARD",
    "CARD": "PAY_HUMO_UZCARD",
    "BANK": "PAY_HUMO_UZCARD",
    "KARTA": "PAY_HUMO_UZCARD",
    "TON": "PAY_TON_CRYPTO",
    "CRYPTO": "PAY_TON_CRYPTO",
    "TONKEEPER": "PAY_TON_CRYPTO",
    "WALLET_CONNECT": "PAY_TON_CRYPTO",
    "BLOCKCHAIN": "PAY_TON_CRYPTO",
    "PROMO": "PAY_PROMOCODE",
    "PROMOCODE": "PAY_PROMOCODE",
    "TICKET": "PAY_PROMOCODE",
    "VOUCHER": "PAY_PROMOCODE",
    "CHEK": "PAY_PROMOCODE",
    "CHECK": "PAY_PROMOCODE",
    "CASHOUT": "PAY_CASHOUT",
    "CASH": "PAY_CASHOUT",
    "CASHBACK": "PAY_CASHOUT",
    "PLUS": "PAY_CASHOUT",
    "YECHISH": "PAY_CASHOUT",
    "WITHDRAW": "PAY_CASHOUT",
    "WITHDRAWAL": "PAY_CASHOUT",
    "VIP": "PAY_VIP_CROWN",
    "CROWN": "PAY_VIP_CROWN",
    "VIP_CROWN": "PAY_VIP_CROWN",
    "TOJ": "PAY_VIP_CROWN",
    "MONEY": "BTN_WALLET",
    "BALANCE": "BTN_WALLET",
    "BALANS": "BTN_WALLET",
    "WALLET": "BTN_WALLET",
    "HAMYON": "BTN_WALLET",

    # Statuslar va Xabarlar
    "SUCCESS": "STATUS_SUCCESS",
    "CHECK": "STATUS_SUCCESS",
    "VERIFIED": "STATUS_SUCCESS",
    "DOT_GREEN": "STATUS_SUCCESS",
    "ERROR": "STATUS_ERROR",
    "CROSS": "STATUS_ERROR",
    "CANCEL": "STATUS_ERROR",
    "DOT_RED": "STATUS_ERROR",
    "WARN": "STATUS_WARNING",
    "WARNING": "STATUS_WARNING",
    "STOP": "STATUS_WARNING",
    "BAN": "STATUS_WARNING",
    "FORBIDDEN": "STATUS_WARNING",
    "NO_ENTRY": "STATUS_WARNING",
    "BLOCKED": "STATUS_WARNING",
    "SOLD": "STATUS_WARNING",
    "LIGHTNING": "STATUS_LIGHTNING",
    "BOLT": "STATUS_LIGHTNING",
    "LOADING": "STATUS_LOADING",
    "WAIT": "STATUS_LOADING",
    "TIMER": "STATUS_LOADING",
    "ALARM": "STATUS_LOADING",
    "REFRESH": "STATUS_LOADING",
    "RETRY": "STATUS_LOADING",
    "SECURITY": "STATUS_SECURITY",
    "SHIELD": "STATUS_SECURITY",
    "LOCK": "STATUS_SECURITY",
    "KEY": "STATUS_SECURITY",
    "PROXY": "STATUS_SECURITY",
    "ANTIFRAUD_SIREN": "STATUS_SECURITY",

    # Media va Video / Audio
    "VIDEO_FHD": "MEDIA_VIDEO_FHD",
    "VIDEO_HD": "MEDIA_VIDEO_HD",
    "VIDEO": "MEDIA_VIDEO_FHD",
    "FILM": "MEDIA_VIDEO_FHD",
    "GALLERY": "MEDIA_VIDEO_FHD",
    "AUDIO": "MEDIA_AUDIO_MP3",
    "AUDIO_MP3": "MEDIA_AUDIO_MP3",
    "SCISSORS": "MEDIA_SCISSORS",
    "CLIPPER": "MEDIA_SCISSORS",
    "CLIPPERS": "MEDIA_SCISSORS",
    "YOUTUBE": "MEDIA_YOUTUBE",
    "SHORTS": "MEDIA_YOUTUBE",
    "CHANNEL": "MEDIA_YOUTUBE",
    "SUBS": "MEDIA_YOUTUBE",
    "TV": "MEDIA_YOUTUBE",
    "AUTOPILOT": "MEDIA_AUTOPILOT",
    "STREAM": "MEDIA_AUTOPILOT",
    "LIVE": "MEDIA_AUTOPILOT",
    "BOT": "MEDIA_AUTOPILOT",

    # Sovg'alar va Boxlar
    "GIFT": "GIFT_CASE_BOX",
    "BOX": "GIFT_CASE_BOX",
    "STOCK_BOX": "GIFT_CASE_BOX",
    "STOCK": "GIFT_CASE_BOX",
    "MYSTERY_BOX": "GIFT_CASE_BOX",
    "CAKE": "GIFT_CAKE",
    "TEDDY": "GIFT_TEDDY",
    "BOUQUET": "GIFT_BOUQUET",
    "CHAMPAGNE": "GIFT_CHAMPAGNE",
    "PARTY": "GIFT_CHAMPAGNE",
    "DIAMOND_RING": "GIFT_DIAMOND_RING",
    "MINT": "GIFT_DIAMOND_RING",
    "TROPHY": "GIFT_TROPHY",
    "MEDAL_GOLD": "GIFT_TROPHY",
    "MEDAL_SILVER": "GIFT_TROPHY",
    "MEDAL_BRONZE": "GIFT_TROPHY",
    "ROCKET": "GIFT_ROCKET",
    "CAP": "GIFT_CAP",
    "PLUSH": "GIFT_PLUSH",
    "PREMIUM": "GIFT_PREMIUM",
    "NFT": "GIFT_PREMIUM",

    # O'yinlar va Kazino
    "COINFLIP": "GAME_COINFLIP",
    "COIN": "GAME_COINFLIP",
    "DUEL": "GAME_COINFLIP",
    "SLOTS": "GAME_SLOTS",
    "CASINO": "GAME_SLOTS",
    "MINES_BOMB": "GAME_MINES_BOMB",
    "BOMB": "GAME_MINES_BOMB",
    "MINES_GEM": "GAME_MINES_GEM",
    "CRASH_ROCKET": "GAME_CRASH_ROCKET",
    "CRASH_PLANE": "GAME_CRASH_ROCKET",
    "KAMI_PLANE": "GAME_CRASH_ROCKET",
    "CRASH_BOOM": "GAME_CRASH_BOOM",
    "MINES_BOOM": "GAME_CRASH_BOOM",
    "KAMI_CRASH": "GAME_CRASH_BOOM",
    "KAMI_LANDING": "STATUS_SUCCESS",
    "APPLE_GOOD": "GAME_APPLE_GOOD",
    "APPLE_WHOLE": "GAME_APPLE_GOOD",
    "APPLE_BAD": "GAME_APPLE_BAD",
    "APPLE_BITTEN": "GAME_APPLE_BAD",
    "CARD_HEARTS": "GAME_CARD_HEARTS",
    "CARD_SPADES": "GAME_CARD_SPADES",
    "CARD_DIAMONDS": "GAME_CARD_DIAMONDS",
    "CARD_CLUBS": "GAME_CARD_CLUBS",
    "CARD_BACK": "GAME_CARD_BACK",
    "CARD_JOKER": "BTN_GAMES",
    "WHEEL": "GAME_WHEEL_SPIN",
    "TARGET": "GAME_WHEEL_SPIN",

    # Brendlar
    "CHATGPT": "BRAND_CHATGPT",
    "OPENAI": "BRAND_CHATGPT",
    "GPT": "BRAND_CHATGPT",
    "AI": "BRAND_CHATGPT",
    "CLAUDE": "BRAND_CLAUDE",
    "CLAUDE_CODE": "BRAND_CLAUDE",
    "BRAIN": "BRAND_CLAUDE",
    "GEMINI": "BRAND_GEMINI",
    "OPENROUTER": "BRAND_GEMINI",
    "CAPCUT": "BRAND_CAPCUT",
    "CAPCUT_LOGO": "BRAND_CAPCUT",
    "ELEVENLABS": "BRAND_ELEVENLABS",
    "FIGMA": "BRAND_FIGMA",
    "DESIGN": "BRAND_FIGMA",
    "CANVA": "BRAND_CANVA",
    "ART": "BRAND_CANVA",
    "FLUX": "BRAND_CANVA",
    "SPOTIFY": "BRAND_SPOTIFY",
    "NETFLIX": "BRAND_NETFLIX",
    "NORDVPN": "BRAND_NORDVPN",
    "WINDOWS": "BRAND_WINDOWS",
    "APPLE": "BRAND_APPLE",
    "CURSOR": "BRAND_CURSOR",
    "API": "BRAND_CURSOR",
    "DEVELOPER": "BRAND_CURSOR",
    "DEV": "BRAND_CURSOR",
    "CODE": "BRAND_CURSOR",
    "RENDER": "BRAND_CURSOR",
    "GROQ": "STATUS_LIGHTNING",

    # Instrumentlar va Yordamchilar
    "SEARCH": "TOOL_SEARCH",
    "SCAN": "TOOL_SEARCH",
    "FIRE": "TOOL_FIRE",
    "VIEWS": "TOOL_EYE_VIEWS",
    "LIKE": "TOOL_HEART_LIKE",
    "HEART": "TOOL_HEART_LIKE",
    "COMMENTS": "TOOL_COMMENTS",
    "CALENDAR": "TOOL_CALENDAR",
    "CHART": "TOOL_GRAPH_UP",
    "GRAPH_UP": "TOOL_GRAPH_UP",
    "GROWTH_UP": "TOOL_GRAPH_UP",
    "GROWTH_DOWN": "STATUS_WARNING",
    "SPY": "TOOL_SPY_ANALYTICS",
    "SPY_HAT": "TOOL_SPY_ANALYTICS",
    "VOICE": "TOOL_MIC_VOICE",
    "MIC": "TOOL_MIC_VOICE",
    "QR": "TOOL_QR_CODE",
    "QR_CODE": "TOOL_QR_CODE",
    "QR_DEEPLINK": "TOOL_QR_CODE",
    "DEEPLINK": "TOOL_QR_CODE",
    "LINK": "TOOL_QR_CODE",
    "PHONE": "TOOL_QR_CODE",
    "MOBILE": "TOOL_QR_CODE",
    "PRICE_TAG": "TOOL_TAG_PRICE",
    "TAG_PRICE": "TOOL_TAG_PRICE",
    "TAGS": "TOOL_TAG_PRICE",
    "PIN": "TOOL_TAG_PRICE",
    "PIN_LOCATION": "TOOL_TAG_PRICE",
    "SEO_TAG": "TOOL_TAG_PRICE",
    "VIP_STAR": "TOOL_VIP_STAR",
    "SPARKLES": "TOOL_VIP_STAR",
    "IDEA": "TOOL_VIP_STAR",
    "CREATORFLOW_LOGO": "TOOL_VIP_STAR",
    "CART": "BTN_SERVICES",
    "STORE": "BTN_SERVICES",
    "MARKETPLACE": "BTN_SERVICES",
    "USER": "BTN_REFERRAL",
    "FRIENDS": "BTN_REFERRAL",
    "MEMO": "BTN_ORDERS",
    "DOCUMENT": "BTN_ORDERS",
    "INVOICE": "BTN_ORDERS",
    "LIST": "BTN_ORDERS",
    "REPORT": "BTN_SUPPORT",
    "HELP": "BTN_SUPPORT",
    "INFO": "BTN_SUPPORT",
    "BELL": "BTN_SUPPORT",
    "HANDSHAKE": "BTN_SUPPORT",
    "ADMIN": "BTN_SETTINGS",
    "DOWNLOAD": "MEDIA_VIDEO_FHD",
    "DOWNLOADER": "MEDIA_VIDEO_FHD",
    "YUKLASH": "MEDIA_VIDEO_FHD",
    "VIDEO": "MEDIA_VIDEO_FHD",
    "VIDEO_FHD": "MEDIA_VIDEO_FHD",
    "VIDEO_HD": "MEDIA_VIDEO_HD",
    "INSTA": "MEDIA_VIDEO_HD",
    "INSTAGRAM_LOGO": "MEDIA_VIDEO_HD",
    "WEB": "BTN_DASHBOARD",
    "GLOBE": "BTN_DASHBOARD"
}

# ==============================================================================
# 4. ORQAGA MOSLIK (Backward Compatibility Map)
# ==============================================================================
EMOJI_MAP = {}
for k, v in CUSTOM_EMOJI_REGISTRY.items():
    EMOJI_MAP[k] = (v.get("id", ""), v.get("fallback_icon", "✨"))

for alias, reg_key in ALIASES.items():
    if reg_key in CUSTOM_EMOJI_REGISTRY:
        reg_item = CUSTOM_EMOJI_REGISTRY[reg_key]
        EMOJI_MAP[alias] = (reg_item.get("id", ""), reg_item.get("fallback_icon", "✨"))

CUSTOM_EMOJI_POOL = [
    str(v["id"]).strip() for v in CUSTOM_EMOJI_REGISTRY.values()
    if v.get("id") and str(v.get("id")).strip().isdigit()
]

# Backward compatibility alias
VERIFIED_CUSTOM_EMOJIS = CUSTOM_EMOJI_REGISTRY

# ==============================================================================
# 5. YORDAMCHI FUNKSIYALAR
# ==============================================================================
def resolve_registry_key(key: str) -> str:
    """Berilgan kalit yoki aliasdan asosiy registrdagi kalitni aniqlaydi."""
    k_str = str(key).strip()
    if k_str in CUSTOM_EMOJI_REGISTRY:
        return k_str
    if k_str.upper() in CUSTOM_EMOJI_REGISTRY:
        return k_str.upper()
    if k_str in ALIASES:
        return ALIASES[k_str]
    if k_str.upper() in ALIASES:
        return ALIASES[k_str.upper()]
    return k_str

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
    return info.get("fallback_icon", "✨")

def custom_emoji(key: str) -> str:
    """
    Telegram xabarlarida chiroyli Custom Emoji chiqishi uchun <emoji id="..."> HTML tegi.
    Agar ID bo'lmasa, fallback icon chiqariladi.
    """
    info = get_custom_emoji_info(key)
    c_id = info.get("id", "")
    fb = info.get("fallback_icon", "✨")
    if c_id and str(c_id).strip().isdigit():
        return f'<emoji id="{c_id}">{fb}</emoji>'
    return fb

ce = custom_emoji

def get_button_icon_id(key: str) -> str:
    """InlineKeyboardButton icon_custom_emoji_id parametri uchun ID qaytaradi."""
    info = get_custom_emoji_info(key)
    c_id = info.get("id", "")
    return str(c_id) if c_id and str(c_id).strip().isdigit() else ""

def get_random_custom_emoji_id() -> int:
    """Reaksiyalar uchun pool'dan ixtiyoriy ID qaytaradi."""
    if CUSTOM_EMOJI_POOL:
        return int(random.choice(CUSTOM_EMOJI_POOL))
    return 5366395940808709418

