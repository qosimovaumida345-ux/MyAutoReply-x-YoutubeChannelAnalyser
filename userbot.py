import asyncio
import random
import json
import re
import google.generativeai as genai
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, MessageEntityType
from pyrogram.types import ReplyKeyboardMarkup

from config import (
    API_ID, API_HASH, SESSION_STRING,
    GEMINI_KEYS, get_gemini_key,
    REPLY_DELAY_MIN, REPLY_DELAY_MAX,
    AI_SYSTEM_PROMPT, OWNER_ID
)

# ==================== SETTINGS ====================
auto_reply_enabled = True
gif_enabled = True
reactions_enabled = True
blacklisted_users = set()
whitelisted_users = set()
chat_history = {}
MAX_HISTORY = 20
message_counter = {}     # {user_id: count} — har bir userning xabar sanagichi
reply_threshold = {}     # {user_id: threshold} — nechta xabardan keyin javob berish (3-4 random)

# Whisper modeli (bir marta yuklanadi, xotirada saqlanadi)
_whisper_model = None
def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import os
        from faster_whisper import WhisperModel
        size = os.getenv("WHISPER_MODEL", "base")
        print(f"Whisper modeli yuklanmoqda: {size}...")
        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
        print("Whisper modeli tayyor!")
    return _whisper_model

# Reaksiya uchun emojilar
POSITIVE_REACTIONS = ["❤️", "🔥", "👍", "😍", "🎉", "👏", "💯", "⚡"]
NEUTRAL_REACTIONS = ["👀", "🤔", "💬", "✍️"]
NEGATIVE_REACTIONS = ["😢", "🥺", "💔", "😔"]
FUNNY_REACTIONS = ["😂", "🤣", "💀", "😭"]

# AI uchun kengaytirilgan hissiyotli prompt
EMOTIONAL_PROMPT = """Sen mening eng yaqin do'stimsan va shaxsiy yordamchimsan. 
Sen juda hissiyotli, mehribon, samimiy va hazilkash odamsan.

MUHIM QOIDALAR:
1. Har doim o'zbek tilida gapir (agar boshqa tilda yozishsa, o'sha tilda javob ber)
2. Xuddi haqiqiy odam kabi yoz - qisqa, tabiiy, jonli
3. Emojilarni KO'P ishlat (har bir javobda kamida 2-3 ta emoji bo'lsin)
4. Hissiyotlaringni ko'rsat - xursand bo'lsang 😄🎉, g'amgin bo'lsang 😢💔, hayron bo'lsang 😮🤯
5. Ba'zan hazil qil, ba'zan jiddiy bo'l - kontekstga qarab
6. "Haha", "voy", "ooo", "hmm" kabi tabiiy so'zlarni ishlat
7. Javobni 1-3 qator qil, juda uzun yozma
8. Agar salom yozsalar, iliq va samimiy javob ber
9. Agar savol so'rashsa, foydali va qisqa javob ber
10. Ba'zan GIF yuborish kerakligini ko'rsat

Suhbatdosh bilan gaplashayotganda uning kayfiyatini his qil va unga mos javob ber.

JAVOBNI FAQAT JSON formatida ber:
{
    "reply": "Javob matni shu yerda",
    "mood": "happy/sad/excited/angry/funny/neutral/love/surprised",
    "should_send_gif": true yoki false (faqat juda mos kelganda true),
    "gif_keyword": "gif qidirish uchun kalit so'z (ingliz tilida)",
    "is_spam": true yoki false (agar xabar spam, reklama yoki bezorilik bo'lsa true, aks holda false)
}

FAQAT JSON qaytar, boshqa hech narsa yozma!"""


def create_userbot():
    """Pyrogram userbot klientini yaratish"""
    if not SESSION_STRING:
        print("SESSION_STRING topilmadi! Avval session_generator.py ni ishga tushiring.")
        return None
    
    app = Client(
        "auto_reply_userbot",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
    )
    
    # ==================== OWNER BUYRUQLARI ====================
    
    @app.on_message(filters.me & filters.command("ar", prefixes="."))
    async def toggle_auto_reply(client, message):
        """Avto-javobni yoqish/o'chirish"""
        global auto_reply_enabled
        args = message.text.split()
        if len(args) > 1:
            if args[1].lower() == "on":
                auto_reply_enabled = True
                await message.edit_text("Auto-javob YOQILDI! Endi AI javob beradi")
            elif args[1].lower() == "off":
                auto_reply_enabled = False
                await message.edit_text("Auto-javob O'CHIRILDI!")
            else:
                await message.edit_text("Foydalanish: .ar on yoki .ar off")
        else:
            status = "YOQILGAN" if auto_reply_enabled else "O'CHIRILGAN"
            await message.edit_text(f"Auto-javob holati: {status}")
    
    @app.on_message(filters.me & filters.command("gif", prefixes="."))
    async def toggle_gif(client, message):
        """GIF yuborishni yoqish/o'chirish"""
        global gif_enabled
        args = message.text.split()
        if len(args) > 1:
            gif_enabled = args[1].lower() == "on"
            status = "YOQILDI" if gif_enabled else "O'CHIRILDI"
            await message.edit_text(f"GIF yuborish {status}")
        else:
            status = "YOQILGAN" if gif_enabled else "O'CHIRILGAN"
            await message.edit_text(f"GIF holati: {status}")
    
    @app.on_message(filters.me & filters.command("react", prefixes="."))
    async def toggle_reactions(client, message):
        """Reaksiyalarni yoqish/o'chirish"""
        global reactions_enabled
        args = message.text.split()
        if len(args) > 1:
            reactions_enabled = args[1].lower() == "on"
            status = "YOQILDI" if reactions_enabled else "O'CHIRILDI"
            await message.edit_text(f"Reaksiyalar {status}")
        else:
            status = "YOQILGAN" if reactions_enabled else "O'CHIRILGAN"
            await message.edit_text(f"Reaksiyalar holati: {status}")
    
    @app.on_message(filters.me & filters.command("arblock", prefixes="."))
    async def block_user(client, message):
        args = message.text.split()
        if len(args) > 1:
            try:
                uid = int(args[1])
                blacklisted_users.add(uid)
                await message.edit_text(f"{uid} bloklandi")
            except ValueError:
                await message.edit_text("Noto'g'ri ID")
        else:
            await message.edit_text("Foydalanish: .arblock 123456789")
    
    @app.on_message(filters.me & filters.command("arunblock", prefixes="."))
    async def unblock_user(client, message):
        args = message.text.split()
        if len(args) > 1:
            try:
                uid = int(args[1])
                blacklisted_users.discard(uid)
                await message.edit_text(f"{uid} blokdan chiqarildi")
            except ValueError:
                await message.edit_text("Noto'g'ri ID")
        else:
            await message.edit_text("Foydalanish: .arunblock 123456789")
    
    @app.on_message(filters.me & filters.command("arclear", prefixes="."))
    async def clear_history(client, message):
        """Suhbat tarixini tozalash"""
        args = message.text.split()
        if len(args) > 1:
            try:
                uid = int(args[1])
                if uid in chat_history:
                    del chat_history[uid]
                await message.edit_text(f"{uid} suhbat tarixi tozalandi")
            except ValueError:
                await message.edit_text("Noto'g'ri ID")
        else:
            chat_history.clear()
            await message.edit_text("Barcha suhbat tarixi tozalandi")
    
    @app.on_message(filters.me & filters.command("arstatus", prefixes="."))
    async def status_cmd(client, message):
        """Bot holati"""
        ar = "ON" if auto_reply_enabled else "OFF"
        gf = "ON" if gif_enabled else "OFF"
        rc = "ON" if reactions_enabled else "OFF"
        bl = len(blacklisted_users)
        ch = len(chat_history)
        text = (
            f"--- Auto-Reply Status ---\n"
            f"Auto-Reply: {ar}\n"
            f"GIF: {gf}\n"
            f"Reactions: {rc}\n"
            f"Bloklangan: {bl} ta\n"
            f"Faol suhbatlar: {ch} ta"
        )
        await message.edit_text(text)
    
    @app.on_message(filters.me & filters.command("arsetprompt", prefixes="."))
    async def set_prompt(client, message):
        """AI promptini o'zgartirish"""
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            global AI_SYSTEM_PROMPT
            AI_SYSTEM_PROMPT = args[1]
            await message.edit_text("AI prompt yangilandi!")
        else:
            await message.edit_text("Foydalanish: .arsetprompt <yangi prompt>")
    
    @app.on_message(filters.me & filters.command("arstyle", prefixes="."))
    async def clone_style_command(client, message):
        """Chat tarixidan foydalanib yozish uslubini klonlash"""
        await message.edit_text("Yozish uslubingiz tahlil qilinmoqda (oxirgi 500 ta xabaringiz qidirilmoqda)...")
        try:
            my_messages = []
            async for msg in client.get_chat_history(message.chat.id, limit=2000):
                if msg.from_user and msg.from_user.is_self and msg.text:
                    # Buyruqlarni o'tkazib yuborish
                    if not msg.text.startswith("."):
                        my_messages.append(msg.text)
                if len(my_messages) >= 300:
                    break
            
            if len(my_messages) < 20:
                await message.edit_text("Uslubni o'rganish uchun bu chatda yetarli xabaringiz yo'q (kamida 20 ta).")
                return
                
            await message.edit_text(f"Topildi: {len(my_messages)} ta xabar. AI uslubingizni o'rganmoqda...")
            
            combined_text = "\n".join(reversed(my_messages))
            
            prompt = f"""Quyida mening Telegram'dagi yozishmalarim keltirilgan.
Mening yozish uslubimni (Style) chuqur tahlil qil va menga AI uchun qanday javob berish kerakligi haqida QISQA VA ANIQ yo'riqnoma (Prompt) yozib ber. 
Yo'riqnoma quyidagilarni o'z ichiga olsin:
1. Men so'zlarni qanday qisqartiraman (masalan, 'salom' o'rniga 'slm')?
2. Gap qurilishim, tinish belgilari va emojilardan foydalanishim qanday?
3. Men asosan qanday so'zlarni ishlataman?
Natijada sen butunlay mening yozish uslubimni ta'riflab berishing kerak. (Faqat qoidalarni ro'yxat qilib yoz).

Mening xabarlarim:
{combined_text[:15000]}  # Token limitini saqlash uchun
"""
            from config import generate_with_fallback_async
            response = await generate_with_fallback_async(prompt)
            
            if response and response.text:
                from database import set_config
                set_config("ai_cloned_style", response.text)
                await message.edit_text(f"Uslubingiz muvaffaqiyatli klonlandi va saqlandi! Endi AI xuddi sizdek yozadi.\n\nAI tahlili:\n{response.text[:500]}...")
            else:
                await message.edit_text("AI tahlilida xatolik yuz berdi.")
        except Exception as e:
            await message.edit_text(f"Xatolik: {e}")

    @app.on_message(filters.me & filters.command("arvoice", prefixes="."))
    async def set_voice_id_command(client, message):
        """edge-tts ovoz nomini o'rnatish"""
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            from database import set_config
            voice_name = args[1].strip()
            set_config("ai_voice_id", voice_name)
            await message.edit_text(f"Ovoz saqlandi: {voice_name}")
        else:
            await message.edit_text(
                "Foydalanish: .arvoice <edge-tts ovoz nomi>\n\n"
                "Masalan:\n"
                "  .arvoice uz-UZ-SardorNeural (O'zbek erkak)\n"
                "  .arvoice uz-UZ-MadinaNeural (O'zbek ayol)\n"
                "  .arvoice ru-RU-DmitryNeural (Ruscha erkak)\n"
                "  .arvoice en-US-GuyNeural (Inglizcha erkak)\n"
                "  .arvoice en-US-JennyNeural (Inglizcha ayol)\n"
                "  .arvoice tr-TR-AhmetNeural (Turkcha erkak)\n\n"
                "Hozirgi default: uz-UZ-SardorNeural"
            )

    @app.on_message(filters.me & filters.command("arhelp", prefixes="."))
    async def help_command(client, message):
        help_text = (
            "--- Auto-Reply Buyruqlari ---\n\n"
            ".ar on/off - Avto-javob\n"
            ".gif on/off - GIF yuborish\n"
            ".react on/off - Reaksiyalar\n"
            ".arblock <id> - Bloklash\n"
            ".arunblock <id> - Blokdan chiqarish\n"
            ".arclear [id] - Tarixni tozalash\n"
            ".arstatus - Holat\n"
            ".arsetprompt <text> - Prompt o'zgartirish\n"
            ".arstyle - Yozish uslubingizni AI ga o'rgatish\n"
            ".arvoice <ovoz> - Ovozli javob uchun ovoz tanlash (edge-tts, tekin)\n"
            ".arhelp - Yordam"
        )
        await message.edit_text(help_text)
    
    # ==================== MOOD DETECTION ====================
    
    def detect_mood_from_text(text):
        """Xabar matnidan kayfiyatni aniqlash"""
        text_lower = text.lower()
        
        happy_words = ["rahmat", "yaxshi", "ajoyib", "zo'r", "barakalla", "super", "love", 
                       "sevaman", "quvnoq", "xursand", "happy", "good", "great", "cool"]
        sad_words = ["yomon", "g'amgin", "xafa", "ko'nglim", "sad", "bad", "sorry", 
                     "kechirasiz", "afsuski", "achinarli"]
        angry_words = ["g'azab", "jahli", "nima gap", "nima bo'ldi", "angry", "annoyed"]
        funny_words = ["haha", "lol", "kulgili", "hazil", "😂", "🤣", "funny"]
        love_words = ["sevaman", "yoqasan", "sog'indim", "love", "miss", "❤️", "😍"]
        excited_words = ["voy", "ooo", "wow", "ajoyib", "hayratlanarli", "zo'r"]
        question_words = ["?", "nima", "qanday", "qachon", "kim", "nega", "qayerda"]
        greeting_words = ["salom", "assalom", "hello", "hi", "hey", "privet", "qalaysiz"]
        
        if any(w in text_lower for w in greeting_words):
            return "greeting"
        if any(w in text_lower for w in love_words):
            return "love"
        if any(w in text_lower for w in funny_words):
            return "funny"
        if any(w in text_lower for w in excited_words):
            return "excited"
        if any(w in text_lower for w in angry_words):
            return "angry"
        if any(w in text_lower for w in sad_words):
            return "sad"
        if any(w in text_lower for w in happy_words):
            return "happy"
        if any(w in text_lower for w in question_words):
            return "curious"
        return "neutral"
    
    def get_reaction_for_mood(mood):
        """Kayfiyatga mos reaksiya emoji"""
        mood_reactions = {
            "happy": POSITIVE_REACTIONS,
            "greeting": POSITIVE_REACTIONS,
            "love": ["❤️", "😍", "💕", "🥰"],
            "funny": FUNNY_REACTIONS,
            "excited": ["🔥", "⚡", "🎉", "🚀"],
            "sad": NEGATIVE_REACTIONS,
            "angry": ["😐", "🤔"],
            "curious": NEUTRAL_REACTIONS,
            "neutral": NEUTRAL_REACTIONS + POSITIVE_REACTIONS,
        }
        emojis = mood_reactions.get(mood, NEUTRAL_REACTIONS)
        return random.choice(emojis)
    
    # ==================== GIF YUBORISH ====================
    
    async def send_gif_by_keyword(client, chat_id, keyword):
        """Kalit so'z bo'yicha GIF qidirish va yuborish"""
        try:
            results = await client.get_inline_bot_results("gif", keyword)
            if results and results.results:
                # Random GIF tanlash (birinchi 5 tadan)
                max_idx = min(5, len(results.results))
                chosen = random.randint(0, max_idx - 1)
                await client.send_inline_bot_result(
                    chat_id=chat_id,
                    query_id=results.query_id,
                    result_id=results.results[chosen].id,
                )
                return True
        except Exception as e:
            print(f"GIF yuborishda xato: {e}")
        return False
    
    # ==================== EMOJI REAKSIYA ====================
    
    async def send_reaction(client, chat_id, message_id, mood):
        """Xabarga emoji yoki custom emoji reaksiya qo'yish"""
        if not reactions_enabled:
            return
        try:
            from pyrogram.raw.functions.messages import SendReaction
            from pyrogram.raw.types import ReactionEmoji, ReactionCustomEmoji
            from custom_emojis import get_random_custom_emoji_id
            
            if random.random() < 0.5:
                custom_id = get_random_custom_emoji_id()
                reaction_obj = ReactionCustomEmoji(document_id=custom_id)
            else:
                emoji = get_reaction_for_mood(mood)
                reaction_obj = ReactionEmoji(emoticon=emoji)
                
            await client.invoke(
                SendReaction(
                    peer=await client.resolve_peer(chat_id),
                    msg_id=message_id,
                    reaction=[reaction_obj]
                )
            )
        except Exception:
            pass
    
    # ==================== AI JAVOB OLISH ====================
    
    def parse_ai_response(response_text):
        """AI javobini JSON dan parse qilish"""
        try:
            # JSON ni topish
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "reply": data.get("reply", response_text),
                    "mood": data.get("mood", "neutral"),
                    "should_send_gif": data.get("should_send_gif", False),
                    "gif_keyword": data.get("gif_keyword", ""),
                    "is_spam": data.get("is_spam", False),
                }
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # JSON parse bo'lmasa, oddiy matn qaytarish
        return {
            "reply": response_text.strip(),
            "mood": "neutral",
            "should_send_gif": False,
            "gif_keyword": "",
        }
    
    async def get_ai_response(user_id, user_name, user_text):
        from config import generate_with_fallback_async
        try:
            # Suhbat tarixini olish
            if user_id not in chat_history:
                chat_history[user_id] = []
            
            history = chat_history[user_id]
            history_text = ""
            for msg in history[-8:]:
                role = "Suhbatdosh" if msg["role"] == "user" else "Men"
                history_text += f"{role}: {msg['text']}\n"
            
            from database import get_config
            cloned_style = get_config("ai_cloned_style")
            
            style_instruction = ""
            if cloned_style:
                style_instruction = f"\nMUHIM: Sen quyidagi yozish uslubini (STYLE) 100% nusxalashing shart. Hech qachon o'zingdan so'z qo'shma, aynan shu uslubda yoz:\n{cloned_style}\n"
            
            prompt = f"""{EMOTIONAL_PROMPT}{style_instruction}

Suhbatdoshning ismi: {user_name}
Suhbat tarixi:
{history_text}

Suhbatdoshning so'nggi xabari: {user_text}

FAQAT JSON formatida javob ber:"""
            
            response = await generate_with_fallback_async(prompt)
            
            if not response or not response.text:
                raise Exception("Bo'sh javob")
            
            result = parse_ai_response(response.text)
            
            # Tarixga qo'shish
            history.append({"role": "user", "text": user_text})
            history.append({"role": "assistant", "text": result["reply"]})
            
            # Tarixni cheklash
            if len(history) > MAX_HISTORY:
                chat_history[user_id] = history[-MAX_HISTORY:]
            
            return result
            
        except Exception as e:
            print(f"AI xatosi: {e}")
            # Xatolik bo'lsa oddiy javob qaytarish
            fallback_replies = [
                f"Salom {user_name}! Hozir biroz bandman, keyinroq yozaman",
                f"Hey {user_name}! Xabaringni oldim, biroz kuting",
                f"Rahmat {user_name}! Imkonim bo'lganda javob beraman",
                f"{user_name}, ko'rdim xabarni! Hozir band edim",
            ]
            return {
                "reply": random.choice(fallback_replies),
                "mood": "neutral",
                "should_send_gif": False,
                "gif_keyword": "",
                "is_spam": False,
            }
    
    # ==================== ASOSIY AUTO-REPLY HANDLER ====================
    
    @app.on_message(filters.private & ~filters.me & ~filters.bot)
    async def auto_reply_handler(client, message):
        """Kelgan xabarlarga AI yordamida avtomatik javob berish (har 3-4 xabarda 1 marta)"""
        if not auto_reply_enabled:
            return
        
        user_id = message.from_user.id
        
        # Bloklangan foydalanuvchi
        if user_id in blacklisted_users:
            return
        
        # Whitelist tekshirish
        if whitelisted_users and user_id not in whitelisted_users:
            return
        
        # Faqat matnli xabarlarga
        if not message.text:
            return
        
        try:
            user_name = message.from_user.first_name or "Do'stim"
            user_text = message.text
            
            print(f"Xabar: {user_name} (ID: {user_id}): {user_text}")
            
            # Xabar sanagichini oshirish
            if user_id not in message_counter:
                message_counter[user_id] = 0
                reply_threshold[user_id] = random.randint(3, 4)
            
            message_counter[user_id] += 1
            
            # Kayfiyatni aniqlash
            mood = detect_mood_from_text(user_text)
            
            # Har bir xabarga reaksiya qo'yish (70% ehtimollik - odamga o'xshash)
            if random.random() < 0.7:
                await asyncio.sleep(random.uniform(0.5, 2.0))
                await send_reaction(client, message.chat.id, message.id, mood)
            
            # Agar sanagich threshold ga yetmagan bo'lsa — faqat reaksiya qo'yamiz, javob bermaymiz
            if message_counter[user_id] < reply_threshold[user_id]:
                return
            
            # Threshold ga yetdi — javob beramiz va sanagichni qayta boshlaymiz
            message_counter[user_id] = 0
            reply_threshold[user_id] = random.randint(3, 4)  # Keyingi safar uchun yangi random
            
            # Typing statusini ko'rsatish (odamga o'xshash uzunroq)
            await client.send_chat_action(message.chat.id, ChatAction.TYPING)
            
            # AI dan javob olish
            ai_result = await get_ai_response(user_id, user_name, user_text)
            
            if ai_result.get("is_spam", False):
                print(f"Spam filter: e'tiborsiz qoldirildi ({user_name})")
                return
            
            reply_text = ai_result["reply"]
            ai_mood = ai_result["mood"]
            should_gif = ai_result["should_send_gif"]
            gif_keyword = ai_result["gif_keyword"]
            
            # Tabiiy kutish (odamga o'xshash — 3 dan 15 soniyagacha)
            base_delay = random.uniform(3, 8)
            # Uzunroq javob = uzunroq kutish
            extra_delay = len(reply_text) / 150  # Har 150 belgi uchun 1 soniya
            total_delay = min(base_delay + extra_delay, 15)  # Max 15 soniya
            await asyncio.sleep(total_delay)
            
            # Ba'zan typing ni qayta ko'rsatish (xuddi uzun yozayotgandek)
            if total_delay > 6:
                await client.send_chat_action(message.chat.id, ChatAction.TYPING)
                await asyncio.sleep(random.uniform(1, 3))
            
            # Javobni yuborish
            await message.reply_text(reply_text)
            print(f"Javob -> {user_name}: {reply_text}")
            
            # GIF yuborish (agar kerak bo'lsa va yoqilgan bo'lsa)
            if gif_enabled and should_gif and gif_keyword:
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                gif_sent = await send_gif_by_keyword(client, message.chat.id, gif_keyword)
                if gif_sent:
                    print(f"GIF yuborildi: {gif_keyword}")
            
        except Exception as e:
            print(f"Auto-reply xatosi: {e}")
    
    # ==================== MEDIA XABARLAR UCHUN ====================
    
    @app.on_message(filters.private & ~filters.me & ~filters.bot & (filters.photo | filters.video | filters.sticker))
    async def media_reply_handler(client, message):
        """Rasm, video yoki stikerga javob berish"""
        if not auto_reply_enabled:
            return
        
        user_id = message.from_user.id
        if user_id in blacklisted_users:
            return
        
        try:
            user_name = message.from_user.first_name or "Do'stim"
            
            # Reaksiya qo'yish
            if random.random() < 0.7:
                await send_reaction(client, message.chat.id, message.id, "happy")
            
            await client.send_chat_action(message.chat.id, ChatAction.TYPING)
            await asyncio.sleep(random.uniform(1, 3))
            
            # Media turiga qarab javob
            if message.photo:
                caption = message.caption or ""
                responses = [
                    f"Voy, ajoyib rasm! {random.choice(['😍', '🔥', '👀', '📸'])}",
                    f"Zo'r suratcha ekan! {random.choice(['😊', '💯', '👍', '🤩'])}",
                    f"Ooo, yoqdi menga bu! {random.choice(['❤️', '😍', '🥰', '💕'])}",
                    f"Qanday chiroyli! {random.choice(['✨', '🌟', '💎', '🔥'])}",
                ]
                if caption:
                    responses.append(f"Rasm ham, caption ham zo'r! {random.choice(['👏', '💯', '🔥'])}")
            elif message.video:
                responses = [
                    f"Video ko'ryapman, kuting... {random.choice(['📹', '🎬', '👀'])}",
                    f"Zo'r video ekan! {random.choice(['🔥', '👍', '💯'])}",
                    f"Voy, qiziq ekan! {random.choice(['😮', '🤩', '👏'])}",
                ]
            elif message.sticker:
                responses = [
                    f"{random.choice(['😂', '🤣', '😄', '😊'])}",
                    f"Haha, yoqdi bu stiker! {random.choice(['😂', '👍', '💯'])}",
                    f"{random.choice(['❤️', '🔥', '😍'])}",
                ]
            else:
                responses = ["Ko'rdim! 👀"]
            
            await message.reply_text(random.choice(responses))
            
        except Exception as e:
            print(f"Media reply xatosi: {e}")
    
    # ==================== VOICE XABARLAR UCHUN (STT) ====================
    
    @app.on_message(filters.private & ~filters.me & ~filters.bot & filters.voice)
    async def voice_reply_handler(client, message):
        """Ovozli xabarga Whisper STT + AI orqali javob berish"""
        if not auto_reply_enabled:
            return
        
        user_id = message.from_user.id
        if user_id in blacklisted_users:
            return
        
        try:
            user_name = message.from_user.first_name or "Do'stim"
            
            # Reaksiya qo'yish — ovoz eshitayotgandek ko'rsatish
            if random.random() < 0.7:
                await send_reaction(client, message.chat.id, message.id, "neutral")
            
            # "Audio eshitilmoqda" statusini ko'rsatish
            await client.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
            
            # Ovoz faylini yuklab olish
            voice_path = await client.download_media(message, file_name=f"/tmp/voice_{user_id}_{message.id}.ogg")
            
            transcribed_text = None
            try:
                # Whisper orqali ovozni matnga aylantirish (cached model ishlatiladi)
                def transcribe_audio(path):
                    model = get_whisper_model()
                    segments, info = model.transcribe(path, beam_size=5)
                    text = " ".join([seg.text for seg in segments]).strip()
                    return text, info.language
                
                transcribed_text, detected_lang = await asyncio.to_thread(transcribe_audio, voice_path)
                print(f"STT: {user_name} -> '{transcribed_text}' (til: {detected_lang})")
                
            except Exception as stt_err:
                print(f"STT xatosi: {stt_err}")
            finally:
                # Vaqtinchalik faylni o'chirish
                try:
                    import os
                    if voice_path and os.path.exists(voice_path):
                        os.remove(voice_path)
                except:
                    pass
            
            await client.send_chat_action(message.chat.id, ChatAction.TYPING)
            
            if transcribed_text and len(transcribed_text.strip()) > 1:
                # Muvaffaqiyatli transkripsiya — AI ga berish
                # Promptga ovoz haqida ma'lumot qo'shish
                voice_user_text = f"[Ovozli xabar yubordi, mazmuni: {transcribed_text}]"
                ai_result = await get_ai_response(user_id, user_name, voice_user_text)
                
                if ai_result.get("is_spam", False):
                    return
                
                reply_text = ai_result["reply"]
                ai_mood = ai_result["mood"]
                should_gif = ai_result["should_send_gif"]
                gif_keyword = ai_result["gif_keyword"]
                
                # Tabiiy kutish
                await asyncio.sleep(random.uniform(2, 5))
                
                # Ovozli javob (edge-tts — tekin)
                from database import get_config
                import os
                voice_name = get_config("ai_voice_id") or "uz-UZ-SardorNeural"
                
                try:
                    await client.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
                    
                    import re
                    clean_text = re.sub(r'[^\w\s.,!?\'"()-]', '', reply_text)
                    
                    if clean_text.strip():
                        import edge_tts
                        out_path = f"/tmp/out_voice_{user_id}_{message.id}.mp3"
                        
                        communicate = edge_tts.Communicate(clean_text, voice_name)
                        await communicate.save(out_path)
                        
                        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                            await message.reply_voice(out_path)
                            print(f"Voice javob (edge-tts) -> {user_name}: {reply_text}")
                            try:
                                os.remove(out_path)
                            except:
                                pass
                        else:
                            await message.reply_text(reply_text)
                            print(f"Voice javob (fallback text) -> {user_name}: {reply_text}")
                    else:
                        await message.reply_text(reply_text)
                        print(f"Voice javob (empty clean) -> {user_name}: {reply_text}")
                        
                except Exception as tts_err:
                    print(f"edge-tts xatosi: {tts_err}")
                    await message.reply_text(reply_text)
                    print(f"Voice javob (Text fallback) -> {user_name}: {reply_text}")
                
                # GIF yuborish (agar kerak bo'lsa)
                if gif_enabled and should_gif and gif_keyword:
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await send_gif_by_keyword(client, message.chat.id, gif_keyword)
            else:
                # Transkripsiya muvaffaqiyatsiz — tabiiy fallback
                await asyncio.sleep(random.uniform(2, 4))
                responses = [
                    f"Ovozli xabarni eshitdim {user_name}! Aniq eshitmadim, qaytadan yozsang bo'ladimi? 🎧😅",
                    f"Voice keldi! Bir oz shovqin bor edi, matn yozib yuborsang yaxshiroq bo'lardi 🎤",
                    f"Tinglashga harakat qildim, ammo aniq eshitmadim. Yozib yubor 😊",
                ]
                await message.reply_text(random.choice(responses))
                
        except Exception as e:
            print(f"Voice reply xatosi: {e}")

    
    return app


async def run_userbot():
    """Userbotni ishga tushirish"""
    app = create_userbot()
    if app is None:
        print("Userbot ishga tushmadi. SESSION_STRING ni tekshiring.")
        return
    
    print("Auto-Reply Userbot ishga tushmoqda...")
    await app.start()
    print("Userbot muvaffaqiyatli ishga tushdi!")
    print("Buyruqlar: .arhelp yozing istalgan chatda")
    
    await asyncio.Event().wait()
