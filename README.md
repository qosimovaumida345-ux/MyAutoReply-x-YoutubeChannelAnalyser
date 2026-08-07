# 🤖 AutoReply + 🎬 YouTube Analytics Bot

Bitta repo ichida ikkita kuchli Telegram bot:

1. **Auto-Reply Userbot** — Shaxsiy akkauntingizga kelgan xabarlarga Gemini AI yordamida avtomatik javob beradi
2. **YouTube Analytics Bot** — YouTube kanallarni tahlil qiladi (obunachilar, ko'rishlar, likelar, o'sish dinamikasi)

---

## ⚡ Tez o'rnatish

### 1. Repository ni klonlash
```bash
git clone https://github.com/YOUR_USERNAME/AutoReply.git
cd AutoReply
```

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. .env faylini sozlash
```bash
cp .env.example .env
```
Keyin `.env` faylini ochib, quyidagi qiymatlarni to'ldiring.

### 4. Session String olish (bir martalik)
```bash
python session_generator.py
```
- Telefon raqamingizni kiriting
- Telegram'dan kelgan kodni kiriting
- Chiqadigan `SESSION_STRING` ni `.env` fayliga qo'ying

### 5. Ishga tushirish
```bash
python main.py
```

---

## 📋 .env da nima to'ldirish kerak

| O'zgaruvchi | Qaerdan olish | Majburiymi? |
|---|---|---|
| `API_ID` | [my.telegram.org](https://my.telegram.org) | ✅ Ha |
| `API_HASH` | [my.telegram.org](https://my.telegram.org) | ✅ Ha |
| `SESSION_STRING` | `python session_generator.py` | ✅ Ha (Userbot uchun) |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) | ✅ Ha (YT Bot uchun) |
| `GEMINI_KEYS` | [aistudio.google.com](https://aistudio.google.com) | ✅ Ha |
| `YOUTUBE_API_KEY` | [Google Cloud Console](https://console.cloud.google.com) | ✅ Ha (YT Bot uchun) |
| `OWNER_ID` | [@userinfobot](https://t.me/userinfobot) | Ixtiyoriy |

---

## 🤖 Auto-Reply Userbot Buyruqlari

Istalgan chatda o'zingiz yozasiz:

| Buyruq | Vazifasi |
|---|---|
| `.ar on` | Avto-javobni yoqish |
| `.ar off` | Avto-javobni o'chirish |
| `.ar` | Hozirgi holatni ko'rish |
| `.arblock <id>` | Foydalanuvchini bloklash |
| `.arunblock <id>` | Blokdan chiqarish |
| `.arhelp` | Yordam |

---

## 🎬 YouTube Bot Buyruqlari

Bot ga Telegram orqali yozasiz:

| Buyruq | Vazifasi |
|---|---|
| `/start` | Bosh menyu |
| `/channel <nom/URL>` | Kanal to'liq statistikasi |
| `/video <URL>` | Video statistikasi |
| `/recent <nom/URL>` | So'nggi 5 ta video tahlili |
| `/track <nom/URL>` | Kanalni kuzatishga olish |
| `/growth <nom/URL>` | O'sish dinamikasi |
| `/mylist` | Kuzatayotgan kanallarim |
| `/untrack <nom/URL>` | Kuzatishdan olib tashlash |

---

## 🚀 Render.com da deploy qilish

### 1. GitHub ga push qiling
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/AutoReply.git
git push -u origin main
```

### 2. Render.com da yangi xizmat yaratish
1. [render.com](https://render.com) ga kiring
2. **New** > **Background Worker** tanlang
3. GitHub repo ni ulang
4. Sozlamalar:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`

### 3. Environment Variables qo'shish
Render dashboard da **Environment** bo'limiga boring va quyidagi o'zgaruvchilarni qo'shing:

```
API_ID=33801766
API_HASH=9dcb3eeaabe2c2a81938907a418f9818
SESSION_STRING=<session_generator.py dan olgan stringingiz>
BOT_TOKEN=<bot token>
GEMINI_KEYS=<kalit1>,<kalit2>,<kalit3>
YOUTUBE_API_KEY=<youtube api kalitingiz>
OWNER_ID=<sizning telegram id>
REPLY_DELAY_MIN=1
REPLY_DELAY_MAX=4
AI_SYSTEM_PROMPT=Sen mening shaxsiy yordamchimsan...
```

### 4. Deploy!
**Manual Deploy** > **Deploy latest commit** tugmasini bosing.

---

## ⚠️ Muhim eslatmalar

- **SESSION_STRING** ni hech kimga bermang! U orqali akkauntingizga kirish mumkin.
- Auto-reply faqat **shaxsiy (private)** xabarlarga javob beradi.
- Telegramning spam filtridan qochish uchun javob berish orasida 1-4 soniya kutish qo'shilgan.
- Render.com ning bepul planida SQLite ma'lumotlar qayta deployda o'chishi mumkin.

---

## 📁 Loyiha tuzilishi

```
AutoReply/
├── main.py               # Asosiy ishga tushirish fayli
├── config.py              # Sozlamalar (.env dan o'qiydi)
├── userbot.py             # Auto-Reply Userbot
├── ytbot.py               # YouTube Analytics Bot
├── database.py            # SQLite ma'lumotlar bazasi
├── session_generator.py   # Session string yaratuvchi
├── requirements.txt       # Python kutubxonalar
├── .env.example           # Namuna sozlamalar fayli
├── .gitignore             # Git uchun e'tiborsiz fayllar
├── Procfile               # Render uchun
├── render.yaml            # Render Blueprint
└── README.md              # Shu fayl
```

---

## 📄 Litsenziya

MIT License
