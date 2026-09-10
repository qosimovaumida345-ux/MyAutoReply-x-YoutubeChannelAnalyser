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
            
        username = (message.from_user.username or "").lower() if message.from_user else ""
        first_name = (message.from_user.first_name or "").lower() if message.from_user else ""
        
        # @HUMOcardbot yoki humo xabari ekanligini aniqlash
        is_humo_bot = "humocard" in username or "humo" in username or "humo" in first_name
        has_payment_markers = any(k in message.text.lower() for k in [
            "tushum", "popolneniye", "пополнение", "qabul qilindi", "o'tkazma"
        ])
        
        if not is_humo_bot and not has_payment_markers:
            return
            
        logger.info(f"Yangi to'lov SMS xabari tutildi! Sender: @{username}")
        
        # 1. SMS ni parse qilish
        parsed = parse_humo_sms(message.text)
        if not parsed or not parsed.get("amount_uzs"):
            logger.info("SMS tahlil qilindi, lekin tushum summasi topilmadi.")
            return
            
        logger.info(f"SMS muvaffaqiyatli parse qilindi: {parsed['amount_uzs']:,} UZS (Karta: {parsed.get('card_last4')}, RRN: {parsed.get('rrn_code')})")
        
        # 2. Bazadan pending buyurtma bilan solishtirish va to'ldirish
        completed = db.match_and_complete_humo_deposit(parsed)
        if completed:
            logger.info(f"✅ TO'LOV MUVAFFAQIYATLI MOS KELDI! User: {completed['tg_user_id']}, Summa: {completed['amount_uzs']:,} so'm")
            global _main_bot_client
            await notify_user_and_admin(completed, _main_bot_client)
        else:
            logger.warning(f"⚠️ SMS summasiga ({parsed['amount_uzs']:,} so'm) mos keladigan faol pending buyurtma topilmadi!")

    return app


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
