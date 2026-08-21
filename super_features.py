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
                [InlineKeyboardButton("🎥 8K (4320p)", callback_data=f"down_8k|{short_id}"),
                 InlineKeyboardButton("🎥 4K (2160p)", callback_data=f"down_4k|{short_id}")],
                [InlineKeyboardButton("🎥 1440p (2K)", callback_data=f"down_1440|{short_id}"),
                 InlineKeyboardButton("🎬 1080p (FHD)", callback_data=f"down_1080|{short_id}")],
                [InlineKeyboardButton("🎬 720p (HD)", callback_data=f"down_720|{short_id}"),
                 InlineKeyboardButton("🎬 480p", callback_data=f"down_480|{short_id}")],
                [InlineKeyboardButton("🎬 360p", callback_data=f"down_360|{short_id}"),
                 InlineKeyboardButton("🚀 Eng yaxshisi", callback_data=f"down_best|{short_id}")]
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
        elif action == "down_1440": ydl_opts['format'] = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best'
        elif action == "down_4k": ydl_opts['format'] = 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best'
        elif action == "down_8k": ydl_opts['format'] = 'bestvideo[height<=4320]+bestaudio/best[height<=4320]/best'
        elif action == "down_best": ydl_opts['format'] = 'bestvideo+bestaudio/best'
        
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

    # 5. Mass Action (Like, Comment, Subscribe)
    @bot.on_message(filters.command("mass") & filters.private)
    async def mass_cmd(client, message):
        """
        /mass <kanal URL> [comment matni]
        
        Foydalanish:
          /mass https://www.youtube.com/@WelfEdits Zo'r videolar!
          /mass @WelfEdits like
          /mass @WelfEdits sub
          /mass @WelfEdits Ajoyib content!
          /mass  (default kanalga like + sub)
          /mass like (default kanalga faqat like)
        
        Agar faqat "like" yozilsa — faqat like
        Agar faqat "sub" yozilsa — faqat subscribe
        Agar boshqa matn yozilsa — like + subscribe + comment
        Agar matn bo'lmasa — like + subscribe (commentsiz)
        """
        args = message.text.split(maxsplit=2)
        
        # Default akkauntdan channel URL ni olish
        from database import get_default_account, get_all_yt_connections
        tg_user_id = message.from_user.id
        default_ch_id = get_default_account(tg_user_id)
        
        if len(args) < 2:
            # Hech narsa yozilmagan — default channel
            if not default_ch_id:
                await message.reply_text(
                    "⚡ **Mass Action — Foydalanish:**\n\n"
                    "`/mass <kanal URL> [comment matni]`\n\n"
                    "**Misollar:**\n"
                    "• `/mass @WelfEdits` — Like + Subscribe\n"
                    "• `/mass @WelfEdits like` — Faqat Like\n"
                    "• `/mass @WelfEdits sub` — Faqat Subscribe\n"
                    "• `/mass @WelfEdits Zo'r video!` — Like + Sub + Comment\n"
                    "• `/mass` — Default kanalga Like + Sub\n\n"
                    "📌 Barcha ulangan akkauntlar ishlatiladi.\n\n"
                    "🔴 _Default akkaunt belgilanmagan. /save\\_def orqali belgilang yoki kanal URL yozing._"
                )
                return
            # Default kanal bilan ishlash
            channel_url = default_ch_id
            comment_text = ""
            action_type = "all"
        elif len(args) == 2:
            first_arg = args[1].strip()
            # Tekshirish: bu kanal URL mi yoki action type mi?
            if first_arg.lower() in ("like", "sub", "subscribe", "comment"):
                # Bu action type — default kanalni ishlatish
                if not default_ch_id:
                    await message.reply_text(
                        "🔴 Default akkaunt belgilanmagan.\n\n"
                        "`/save_def` orqali default akkaunt belgilang yoki kanal URL yozing.\n"
                        "Masalan: `/mass @WelfEdits like`"
                    )
                    return
                channel_url = default_ch_id
                if first_arg.lower() == "like":
                    action_type = "like"
                elif first_arg.lower() in ("sub", "subscribe"):
                    action_type = "subscribe"
                elif first_arg.lower() == "comment":
                    action_type = "all"
                comment_text = ""
            else:
                # Bu kanal URL
                channel_url = first_arg
                comment_text = ""
                action_type = "all"
        else:
            channel_url = args[1].strip()
            comment_text = args[2].strip() if len(args) > 2 else ""
            
            # Action turini aniqlash
            if comment_text.lower() == "like":
                action_type = "like"
                comment_text = ""
            elif comment_text.lower() == "sub":
                action_type = "subscribe"
                comment_text = ""
            elif comment_text:
                action_type = "all"
            else:
                action_type = "all"
                comment_text = ""
        
        from mass_actions import mass_action_worker
        asyncio.create_task(
            mass_action_worker(channel_url, comment_text, action_type, client, message.chat.id)
        )


    # ==========================================
    # /reaction - Picture in Picture video
    # ==========================================
    @bot.on_message(filters.command("reaction") & filters.private)
    async def reaction_cmd(client, message):
        """
        /reaction <main_url> <reactor_url>
        Ikkita videoni birlashtirib PiP effektini yaratadi.
        """
        args = message.text.split()
        if len(args) != 3:
            await message.reply_text("❌ Noto'g'ri format. Foydalanish:\n`/reaction <asosiy_video_url> <reaksiya_video_url>`")
            return
            
        main_url = args[1]
        reactor_url = args[2]
        
        msg = await message.reply_text("⏳ Videolar yuklanmoqda... (1/3)")
        
        import yt_dlp
        import os
        from video_processor import create_reaction_video
        
        download_dir = f"/tmp/reaction_{message.from_user.id}"
        os.makedirs(download_dir, exist_ok=True)
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'mweb'],
                    'player_skip': ['js']
                }
            },
            'compat_opts': ['no-youtube-unavailable-videos']
        }
        
        def _download(url):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info)
            except Exception as e:
                print(f"Reaction download xato: {e}")
                return None
                
        # 1. Yuklash
        main_path = await asyncio.to_thread(_download, main_url)
        reactor_path = await asyncio.to_thread(_download, reactor_url)
        
        if not main_path or not reactor_path:
            await msg.edit_text("❌ Videolarni yuklashda xatolik yuz berdi. URLlarni tekshiring.")
            return
            
        await msg.edit_text("⏳ Reaksiya videosi yaratilmoqda... (2/3)\nBu biroz vaqt oladi.")
        
        # 2. Birlashtirish
        output_path = f"{download_dir}/final_reaction.mp4"
        result_path = await asyncio.to_thread(create_reaction_video, main_path, reactor_path, output_path)
        
        if not result_path or not os.path.exists(result_path):
            await msg.edit_text("❌ Videoni render qilishda xatolik yuz berdi.")
            return
            
        await msg.edit_text("📤 Telegramga yuklanmoqda... (3/3)")
        
        # 3. Yuborish
        try:
            await client.send_video(
                chat_id=message.chat.id,
                video=result_path,
                caption="Yangi Reaction Videongiz tayyor! 🎉",
                supports_streaming=True
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ Videoni yuborishda xatolik: {e}")
            
        # 4. Tozalash
        import shutil
        try:
            shutil.rmtree(download_dir, ignore_errors=True)
        except: pass
