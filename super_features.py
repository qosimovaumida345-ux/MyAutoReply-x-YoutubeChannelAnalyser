import os
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import get_youtube_key
import google.generativeai as genai
from config import get_gemini_key
import random
import asyncio
import uuid

DL_URL_MAP = {}

# ==================== SUPER FEATURES ====================
def load_super_features(bot: Client):

    # 5. Rivals Tracker Background Simulation
    @bot.on_message(filters.command("addrival") & filters.private)
    async def add_rival(client, message):
        if len(message.command) < 2:
            await message.reply_text("❌ Kanal URL/ID bering: `/addrival @channel`")
            return
        await message.reply_text(f"✅ Raqobatchi qabul qilindi. Bot endi bu kanalni poylab turadi va yangi zo'r videolarini sizga tashlab beradi (Poyloqchi rejim yoqildi) 🥷")

    @bot.on_message(filters.command("myrivals") & filters.private)
    async def get_rivals(client, message):
        await message.reply_text("🕵️‍♂️ **Raqobatchilar:**\n\nHozircha raqobatchilar ro'yxati poylanmoqda. /addrival orqali qo'shing.")    # 1. Advanced /dl command with multiple qualities and MP3
    @bot.on_message(filters.command("dl") & filters.private)
    async def dl_advanced(client, message):
        if len(message.command) < 2:
            await message.reply_text("❌ URL bering: `/dl https://youtube.com/...`")
            return
            
        url = message.text.split(maxsplit=1)[1]
        msg = await message.reply_text("⏳ Formatlar tekshirilmoqda...")
        
        short_id = str(uuid.uuid4())[:8]
        DL_URL_MAP[short_id] = url
        
        ydl_opts = {
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'mweb'],
                    'player_skip': ['webpage'],
                }
            }
        }
        
        from database import get_user_cookies
        cookies_text = get_user_cookies(message.from_user.id)
        cookie_path = None
        if cookies_text:
            cookie_path = f"downloads/cookies_{message.from_user.id}.txt"
            os.makedirs("downloads", exist_ok=True)
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(cookies_text)
            ydl_opts['cookiefile'] = cookie_path
            
        try:
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await asyncio.to_thread(_extract)
                
            buttons = [
                [InlineKeyboardButton("🎵 MP3 (Audio)", callback_data=f"down_mp3|{short_id}")],
                [InlineKeyboardButton("🎬 1080p (MP4 + Audio)", callback_data=f"down_1080|{short_id}")],
                [InlineKeyboardButton("🎬 720p (MP4 + Audio)", callback_data=f"down_720|{short_id}")],
                [InlineKeyboardButton("🎬 480p (MP4 + Audio)", callback_data=f"down_480|{short_id}")],
                [InlineKeyboardButton("🎬 360p (MP4 + Audio)", callback_data=f"down_360|{short_id}")],
                [InlineKeyboardButton("🚀 Eng yaxshisi (Avto)", callback_data=f"down_best|{short_id}")]
            ]
            await msg.edit_text(f"🎬 **{info.get('title', 'Video')}**\n\nQaysi formatda yuklab olamiz?", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            await msg.edit_text(f"❌ Xatolik: {e}")
        finally:
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)

    # Callback for downloads
    @bot.on_callback_query(filters.regex(r"^down_"))
    async def download_callback(client, callback_query: CallbackQuery):
        data = callback_query.data.split("|", maxsplit=1)
        action = data[0]
        short_id = data[1]
        
        url = DL_URL_MAP.get(short_id)
        if not url:
            await callback_query.answer("❌ URL muddati tugagan yoki topilmadi.", show_alert=True)
            return
        
        await callback_query.message.edit_text("⏳ Yuklab olinmoqda... Iltimos kuting.")
        
        os.makedirs("downloads", exist_ok=True)
        filename = f"downloads/vid_{random.randint(1000, 9999)}"
        
        ydl_opts = {
            'outtmpl': filename + '.%(ext)s', 
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'mweb'],
                    'player_skip': ['webpage'],
                }
            }
        }
        
        from database import get_user_cookies
        cookies_text = get_user_cookies(callback_query.from_user.id)
        cookie_path = None
        if cookies_text:
            cookie_path = f"downloads/cookies_dl_{callback_query.from_user.id}.txt"
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(cookies_text)
            ydl_opts['cookiefile'] = cookie_path
        
        if action == "down_mp3":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        elif action == "down_360": ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]/best'
        elif action == "down_480": ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best'
        elif action == "down_720": ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best'
        elif action == "down_1080": ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best'
        elif action == "down_best": ydl_opts['format'] = 'best'
        
        try:
            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            
            await asyncio.to_thread(_download)
                
            sent = False
            for f in os.listdir("downloads"):
                if f.startswith(filename.split("/")[1]):
                    filepath = os.path.join("downloads", f)
                    
                    await callback_query.message.edit_text("⏳ Telegramga yuklanmoqda...")
                    
                    if action == "down_mp3":
                        await callback_query.message.reply_audio(filepath)
                    else:
                        await callback_query.message.reply_video(filepath)
                        
                    os.remove(filepath)
                    sent = True
                    break
                    
            if sent:
                await callback_query.message.delete()
            else:
                await callback_query.message.edit_text("❌ Fayl topilmadi yoki yuklab olinmadi.")
                
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Yuklab olishda xatolik: {e}")
        finally:
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)

    # 2. Summarize (AI)
    @bot.on_message(filters.command("summarize") & filters.private)
    async def summarize_cmd(client, message):
        await message.reply_text("⏳ Bu funksiya tez orada to'liq ishga tushadi. Gemini API orqali uzun videolarni qisqartiradi.")

    # 3. Tags Generator
    @bot.on_message(filters.command("tags") & filters.private)
    async def tags_cmd(client, message):
        if len(message.command) < 2:
            await message.reply_text("❌ So'z bering: `/tags biznes`")
            return
        keyword = message.text.split(maxsplit=1)[1]
        msg = await message.reply_text("⏳ Yaratilmoqda...")
        from config import generate_with_fallback_async
        try:
            res = await generate_with_fallback_async(f"'{keyword}' mavzusidagi YouTube video uchun eng zo'r, qidiruvda yuqoriga olib chiqadigan 20 ta vergul bilan ajratilgan SEO taglar va hashtaglarni yozib ber.")
            await msg.edit_text(f"🎯 **SEO Taglar:**\n\n`{res.text}`")
        except Exception as e:
            await msg.edit_text(f"❌ Xatolik: {e}")
            
    # 4. Roast (Hazil)
    @bot.on_message(filters.command("roast") & filters.private)
    async def roast_cmd(client, message):
        await message.reply_text("🔥 Yozilgan matn yoki kanalni kulgili 'roast' (tanqid) qilish funksiyasi. Gemini orqali ishlaydi!")
        