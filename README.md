# AutoReply + YouTube Analytics Bot

Telegram Auto-Reply Userbot va YouTube Analytics Bot — bitta repoda.

## Xususiyatlar

### Auto-Reply Userbot
- Gemini AI orqali hissiyotli avtomatik javob
- GIF yuborish va emoji reaksiyalar
- Rasm, video, stiker, voice xabarlarga javob
- 10 ta Gemini API kaliti rotation

### YouTube Analytics Bot (100+ funksiya)
- Kanal va video statistikasi
- Kanallarni solishtirish va kuzatib borish
- Trending, qidiruv, engagement tahlili
- Daromad taxmini va milestone tracking
- 18 ta YouTube API kaliti rotation
- Inline tugmalar va menyular

## Texnologiyalar
- Python + Pyrogram (Telegram)
- Google Gemini AI (auto-reply)
- YouTube Data API v3 (analytics)
- PostgreSQL (Render free database)

## O'rnatish

1. `.env.example` dan `.env` nusxa oling
2. Barcha kalitlarni to'ldiring
3. `pip install -r requirements.txt`
4. `python session_generator.py` (birinchi marta)
5. `python main.py`

## Render.com ga Deploy

1. GitHub reponi Render ga ulang
2. **PostgreSQL** database yarating (Free plan)
3. Internal Database URL ni `DATABASE_URL` ga qo'shing
4. Barcha env variablelarni sozlang
5. Deploy!

## Render PostgreSQL qo'shish

1. Render Dashboard > **New** > **PostgreSQL**
2. Name: `autoreply-db`, Plan: **Free**
3. **Create Database** bosing
4. **Internal Database URL** ni nusxalang
5. Web Service > **Environment** > `DATABASE_URL` ga joylashtiring
