import asyncio
import random
import google.generativeai as genai
from pyrogram import Client, filters
from pyrogram.enums import ChatAction

from config import (
    API_ID, API_HASH, SESSION_STRING,
    GEMINI_KEYS, get_gemini_key,
    REPLY_DELAY_MIN, REPLY_DELAY_MAX,
    AI_SYSTEM_PROMPT, OWNER_ID
)

# ==================== USERBOT SETTINGS ====================
auto_reply_enabled = True  # Avto-javob yoqilganmi
whitelisted_users = set()  # Faqat shu foydalanuvchilarga javob berish (bo'sh = hammaga)
blacklisted_users = set()  # Bu foydalanuvchilarga javob BERMASLIK

# So'nggi suhbatlar konteksti (xotira)
chat_history = {}
MAX_HISTORY = 10  # Har bir chat uchun max xabar soni xotirada


def create_userbot():
    """Pyrogram userbot klientini yaratish"""
    if not SESSION_STRING:
        print("⚠️  SESSION_STRING topilmadi! Avval session_generator.py ni ishga tushiring.")
        return None
    
    app = Client(
        "auto_reply_userbot",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
    )
    
    # ==================== BUYRUQLAR (O'zingiz uchun) ====================
    
    @app.on_message(filters.me & filters.command("ar", prefixes="."))
    async def toggle_auto_reply(client, message):
        """Avto-javobni yoqish/o'chirish: .ar on / .ar off"""
        global auto_reply_enabled
        
        args = message.text.split()
        if len(args) > 1:
            if args[1].lower() == "on":
                auto_reply_enabled = True
                await message.edit_text("✅ **Avto-javob YOQILDI!**")
            elif args[1].lower() == "off":
                auto_reply_enabled = False
                await message.edit_text("🔴 **Avto-javob O'CHIRILDI!**")
            else:
                await message.edit_text("ℹ️ Foydalanish: `.ar on` yoki `.ar off`")
        else:
            status = "✅ YOQILGAN" if auto_reply_enabled else "🔴 O'CHIRILGAN"
            await message.edit_text(f"🤖 **Avto-javob holati:** {status}")
    
    @app.on_message(filters.me & filters.command("arblock", prefixes="."))
    async def block_user(client, message):
        """Foydalanuvchini bloklash: .arblock <user_id>"""
        args = message.text.split()
        if len(args) > 1:
            try:
                uid = int(args[1])
                blacklisted_users.add(uid)
                await message.edit_text(f"🚫 `{uid}` avto-javob bloklanganlar ro'yxatiga qo'shildi.")
            except ValueError:
                await message.edit_text("❌ Noto'g'ri ID. Raqam kiriting.")
        else:
            await message.edit_text("ℹ️ Foydalanish: `.arblock 123456789`")
    
    @app.on_message(filters.me & filters.command("arunblock", prefixes="."))
    async def unblock_user(client, message):
        """Foydalanuvchini blokdan chiqarish: .arunblock <user_id>"""
        args = message.text.split()
        if len(args) > 1:
            try:
                uid = int(args[1])
                blacklisted_users.discard(uid)
                await message.edit_text(f"✅ `{uid}` blokdan chiqarildi.")
            except ValueError:
                await message.edit_text("❌ Noto'g'ri ID.")
        else:
            await message.edit_text("ℹ️ Foydalanish: `.arunblock 123456789`")
    
    @app.on_message(filters.me & filters.command("arhelp", prefixes="."))
    async def help_command(client, message):
        """Yordam: .arhelp"""
        help_text = """
🤖 **Auto-Reply Userbot Buyruqlari**

`.ar on` — Avto-javobni yoqish
`.ar off` — Avto-javobni o'chirish
`.ar` — Hozirgi holatni ko'rish
`.arblock <id>` — Foydalanuvchini bloklash
`.arunblock <id>` — Blokdan chiqarish
`.arhelp` — Shu yordam xabarini ko'rish
        """
        await message.edit_text(help_text)
    
    # ==================== AUTO-REPLY HANDLER ====================
    
    @app.on_message(filters.private & ~filters.me & ~filters.bot)
    async def auto_reply_handler(client, message):
        """Kelgan xabarlarga AI yordamida avtomatik javob berish"""
        global auto_reply_enabled
        
        if not auto_reply_enabled:
            return
        
        user_id = message.from_user.id
        
        # Bloklangan foydalanuvchiga javob bermaslik
        if user_id in blacklisted_users:
            return
        
        # Whitelist bo'lsa, faqat ro'yxatdagilarga javob berish
        if whitelisted_users and user_id not in whitelisted_users:
            return
        
        # Faqat matnli xabarlarga javob berish
        if not message.text:
            return
        
        try:
            user_name = message.from_user.first_name or "Foydalanuvchi"
            user_text = message.text
            
            print(f"📩 {user_name} (ID: {user_id}): {user_text}")
            
            # Chat tarixini yangilash
            if user_id not in chat_history:
                chat_history[user_id] = []
            chat_history[user_id].append({"role": "user", "text": user_text})
            
            # Tarixni cheklash
            if len(chat_history[user_id]) > MAX_HISTORY:
                chat_history[user_id] = chat_history[user_id][-MAX_HISTORY:]
            
            # "Yozyapti..." statusini ko'rsatish
            await client.send_chat_action(message.chat.id, ChatAction.TYPING)
            
            # Gemini API kalitini olish (random rotation)
            api_key = get_gemini_key()
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            # Suhbat tarixidan kontekst yaratish
            history_context = ""
            for msg in chat_history[user_id][-6:]:  # Oxirgi 6 ta xabar
                role = "Suhbatdosh" if msg["role"] == "user" else "Men"
                history_context += f"{role}: {msg['text']}\n"
            
            prompt = f"""{AI_SYSTEM_PROMPT}

Suhbat tarixi:
{history_context}

Suhbatdoshning so'nggi xabari: {user_text}

Javob yoz:"""
            
            # AI dan javob olish
            response = model.generate_content(prompt)
            reply_text = response.text.strip()
            
            # Tarixga qo'shish
            chat_history[user_id].append({"role": "assistant", "text": reply_text})
            
            # Tabiiy ko'rinish uchun random kutish
            delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
            await asyncio.sleep(delay)
            
            # Javobni yuborish
            await message.reply_text(reply_text)
            print(f"🤖 → {user_name}: {reply_text}")
            
        except Exception as e:
            print(f"❌ Auto-reply xatosi: {e}")
    
    return app


async def run_userbot():
    """Userbotni ishga tushirish"""
    app = create_userbot()
    if app is None:
        print("❌ Userbot ishga tushmadi. SESSION_STRING ni tekshiring.")
        return
    
    print("🚀 Auto-Reply Userbot ishga tushmoqda...")
    await app.start()
    print("✅ Userbot muvaffaqiyatli ishga tushdi!")
    print("📋 Buyruqlar: .arhelp yozing istalgan chatda")
    
    # Abadiy ishlash
    await asyncio.Event().wait()
