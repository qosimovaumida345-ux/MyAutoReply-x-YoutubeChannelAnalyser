"""
HUMO SMS Listener Service (Pyrogram Userbot)
@HUMOcardbot dan kelgan xabarlarni real vaqt rejimida ushlab,
avtomatik tarzda balansni to'ldiradi.
"""
import asyncio
import logging

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import API_ID, API_HASH, HUMO_SESSION_STRING, OWNER_ID, BOT_TOKEN
from humo_parser import parse_humo_sms
import database as db
from custom_emojis import ce, e

logger = logging.getLogger("humo_listener")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

_listener_client = None
_main_bot_client = None


async def notify_user_and_admin(completed_deposit: dict, main_bot=None):
    """To'lov qabul qilinganda foydalanuvchiga va adminga xabar yuborish"""
    user_id = completed_deposit.get("tg_user_id")
    amount = completed_deposit.get("amount_uzs", 0)
    new_bal = completed_deposit.get("new_balance", 0)
    rrn = completed_deposit.get("rrn_code") or ""
    sender = completed_deposit.get("sender_name") or completed_deposit.get("sender_card_last4") or ""
    
    text = (
        f"{ce('SUCCESS')} <b>TO'LOV QABUL QILINDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ce('CARD')} <b>To'lov usuli:</b> HUMO Karta\n"
        f"{ce('MONEY')} <b>Hisobga qo'shildi:</b> +{amount:,} so'm\n"
        f"{ce('BALANCE')} <b>Joriy balans:</b> <code>{new_bal:,} so'm</code>\n"
    )
    if rrn:
        text += f"{ce('INVOICE')} <b>Tranzaksiya:</b> <code>{rrn}</code>\n"
    if sender:
        text += f"👤 <b>Yuboruvchi:</b> <code>{sender}</code>\n"
        
    text += (
        f"\n{ce('LIGHTNING')} <i>Mablag'ingiz hisobingizga avtomatik tarzda bir zumda o'tkazildi!</i>\n\n"
        f"{ce('CASHBACK')} <i>Do'stlaringiz bilan botni ulashing va har bir to'lovdan 10% keshbek oling!</i>"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{e('MONEY')} Balans Menyusi", callback_data="menu_wallet")],
        [InlineKeyboardButton(f"{e('MARKETPLACE')} Xizmatlar Do'koni", callback_data="menu_marketplace")],
    ])

    # 1. Userga yuborish
    sent = False
    if main_bot and user_id:
        try:
            await main_bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
            sent = True
        except Exception as err:
            logger.warning(f"Userga to'lov xabarnomasi yuborishda xato: {err}")

    # Fallback: Agar main_bot orqali yuborib bo'lmasa, Telegram Bot API orqali yuborish
    if not sent and user_id and BOT_TOKEN:
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "HTML"
                }, timeout=aiohttp.ClientTimeout(total=5))
        except Exception as api_err:
            logger.warning(f"Bot API fallback xabarnoma xatosi: {api_err}")

    # 2. Adminga xabar
    if OWNER_ID:
        admin_text = (
            f"💰 <b>YANGI HUMO TO'LOV TUSHDI!</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> <code>{user_id}</code>\n"
            f"💵 <b>Summa:</b> +{amount:,} so'm\n"
            f"💳 <b>Karta:</b> {completed_deposit.get('card_number', '')}\n"
            f"📝 <b>SMS matni:</b>\n<code>{completed_deposit.get('sms_raw_text', '')[:200]}</code>"
        )
        if main_bot:
            try:
                await main_bot.send_message(chat_id=OWNER_ID, text=admin_text)
            except Exception:
                pass


def to_utc_datetime(dt):
    """Pyrogram yoki boshqa manbadan kelgan datetime ni xavfsiz UTC ga aylantiradi"""
    if dt is None:
        return None
    from datetime import timezone
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def process_humo_message_obj(message: Message) -> bool:
    """Humo xabarini qat'iy tekshirib, faqat haqiqiy yangi to'lovni tasdiqlaydi"""
    try:
        msg_id = message.id
        msg_dt = to_utc_datetime(message.date)
        raw_text = message.text or message.caption or ""
        
        if not raw_text:
            return False

        # 1. Agar ushbu xabar IDsi avval ko'rilgan bo'lsa, mutlaqo qayta ishlanmaydi!
        if msg_id and db.is_humo_message_processed(msg_id):
            return False

        parsed = parse_humo_sms(raw_text)
        if not parsed or not parsed.get("amount_uzs"):
            if msg_id:
                db.mark_humo_message_processed(msg_id, msg_time=msg_dt)
            return False

        amount = parsed["amount_uzs"]
        logger.info(f"🔍 [HUMO] Xabar #{msg_id} ({msg_dt}): summa={amount} so'm")

        parsed["message_id"] = msg_id
        parsed["message_date"] = msg_dt

        # 2. Bazadan pending buyurtma bilan solishtirish va to'ldirish
        completed = db.match_and_complete_humo_deposit(parsed)
        if completed:
            if msg_id:
                db.mark_humo_message_processed(
                    msg_id,
                    exact_amount=amount,
                    payment_id=str(completed.get("id")),
                    msg_time=msg_dt
                )
            logger.info(f"✅ [HUMO] TO'LOV MUVAFFAQIYATLI TASDIQLANDI! Foydalanuvchi {completed['tg_user_id']} ga +{amount:,} so'm qo'shildi.")
            global _main_bot_client
            await notify_user_and_admin(completed, _main_bot_client)
            return True
        else:
            logger.info(f"ℹ️ [HUMO] {amount:,} so'mga mos keluvchi to'lov hisobi topilmadi yoki bu eski xabar.")
            # Agar xabar 10 daqiqadan eski bo'lsa, kelgusida qayta tekshirib yurmaslik uchun processed deb belgilaymiz
            from datetime import datetime, timezone, timedelta
            now_utc = datetime.now(timezone.utc)
            if msg_dt and msg_dt < (now_utc - timedelta(minutes=10)):
                if msg_id:
                    db.mark_humo_message_processed(msg_id, exact_amount=amount, msg_time=msg_dt)
            return False
    except Exception as e:
        logger.error(f"process_humo_message_obj xatolik: {e}")
        return False


def create_humo_listener_app() -> Client:
    """HUMO Listener Pyrogram Userbot klientini yaratish"""
    if not HUMO_SESSION_STRING:
        return None
        
    app = Client(
        name="humo_sms_listener",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=HUMO_SESSION_STRING,
        in_memory=True
    )
    
    @app.on_message(filters.private)
    async def handle_incoming_humo_message(client: Client, message: Message):
        if not message.text:
            return
            
        sender_username = (message.from_user.username or "").lower() if message.from_user else ""
        sender_id = message.from_user.id if message.from_user else 0
        chat_username = (message.chat.username or "").lower() if message.chat else ""
        chat_id = message.chat.id if message.chat else 0

        # Faqat Humo bot (@humocardbot, ID: 856254490) dan kelgan haqiqiy xabarlar
        is_humo = (
            sender_username == "humocardbot"
            or chat_username == "humocardbot"
            or sender_id == 856254490
            or chat_id == 856254490
        )
        if not is_humo:
            return
            
        logger.info(f"⚡️ [REALTIME] Yangi Humo xabarnomasi qabul qilindi (ID={message.id})")
        await process_humo_message_obj(message)

    return app


async def mark_startup_old_messages(client: Client):
    """Bot qayta ishga tushganda o'tmishdagi barcha eski to'lovlarni processed deb belgilaydi"""
    try:
        logger.info("🧹 Eski Humo xabarlarini tozalash va ro'yxatga olish...")
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        count = 0
        async for msg in client.get_chat_history("humocardbot", limit=50):
            if not msg or not msg.id:
                continue
            msg_dt = to_utc_datetime(msg.date)
            # Agar xabar 2 daqiqadan eski bo'lsa va allaqachon processed bo'lmasa, uni eski deb belgilaymiz
            if msg_dt and msg_dt < (now_utc - timedelta(minutes=2)):
                if not db.is_humo_message_processed(msg.id):
                    db.mark_humo_message_processed(msg.id, msg_time=msg_dt)
                    count += 1
        if count > 0:
            logger.info(f"✅ {count} ta eski Humo xabari ro'yxatga olindi (kelajak to'lovlariga xalaqit bermaydi).")
    except Exception as e:
        logger.error(f"mark_startup_old_messages xatolik: {e}")


async def scan_recent_humo_deposits(client: Client):
    """Faqat hali ko'rib chiqilmagan va so'nggi daqiqalardagi to'lovlarni tekshiradi"""
    try:
        async for msg in client.get_chat_history("humocardbot", limit=5):
            if not msg or not msg.id or not msg.text:
                continue
            if db.is_humo_message_processed(msg.id):
                continue
            await process_humo_message_obj(msg)
    except Exception as e:
        logger.error(f"scan_recent_humo_deposits xatolik: {e}")


async def humo_periodic_checker(client: Client):
    """Har 40 soniyada zaxira sifatida faqat yangi xabarlarni tekshiruvchi task"""
    while True:
        try:
            await asyncio.sleep(40)
            if client.is_connected:
                await scan_recent_humo_deposits(client)
        except asyncio.CancelledError:
            break
        except Exception:
            pass


async def run_humo_listener_task(main_bot=None):
    """Background task sifatida listenerni ishga tushirish"""
    global _main_bot_client, _listener_client
    _main_bot_client = main_bot
    
    if not HUMO_SESSION_STRING:
        logger.info("HUMO_SESSION_STRING topilmadi. Karta SMS listener o'chirilgan.")
        return
        
    try:
        _listener_client = create_humo_listener_app()
        if not _listener_client:
            return
            
        logger.info("HUMO SMS Listener Userbot ishga tushmoqda...")
        await _listener_client.start()
        me = await _listener_client.get_me()
        logger.info(f"✅ HUMO SMS Listener muvaffaqiyatli ulandi! Account: {me.first_name} (@{me.username or me.phone_number})")
        
        # 1. Eski xabarlarni ro'yxatga olib, kelajakdagi yangi hisoblarga daxlsizligini ta'minlaymiz
        await mark_startup_old_messages(_listener_client)
        
        # 2. Zaxira davriy tekshiruvchini ishga tushirish (har 40 soniyada)
        asyncio.create_task(humo_periodic_checker(_listener_client))
        
    except Exception as e:
        logger.error(f"HUMO SMS Listener ulanish xatosi: {e}")


def start_humo_listener_background(main_bot=None):
    """Asosiy bot event loopida ishga tushirish"""
    try:
        asyncio.create_task(run_humo_listener_task(main_bot))
    except Exception as e:
        logger.error(f"start_humo_listener_background xatosi: {e}")


if __name__ == "__main__":
    # Mustaqil xizmat sifatida ishga tushirish (agar alohida worker kerak bo'lsa)
    print("HUMO SMS Listener ishga tushirilmoqda...")
    loop = asyncio.get_event_loop()
    app = create_humo_listener_app()
    if app:
        app.run()
    else:
        print("XATO: HUMO_SESSION_STRING kiritilmagan!")
