"""
CreatorFlow Studio - Store Channel Automation Service (@CreatorFlow_Store)
Avtomatik restock, live xaridlar oqimi, aksiyalar va konkurslar boshqaruvchisi.
Barcha xabarlar tasdiqlangan Custom Emojilar bilan boyitilgan (hech qanday oddiy emoji yo'q).
Kanal xabarlari Premium userbot orqali yuboriladi (custom emojilar to'g'ri render bo'lishi uchun).
"""

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import logging
import random
from typing import Optional, List, Dict
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode


from config import STORE_CHANNEL, VIP_PRICE_UZS
from custom_emojis import ce, e
from database import (
    create_channel_contest,
    get_active_contests,
    pick_contest_winners,
    activate_user_vip,
    create_flash_sale,
    get_active_flash_sale,
    create_fast_drop_promo,
    redeem_fast_drop_promo,
    get_wishlist_users_for_product,
    mark_wishlist_notified,
    get_abandoned_carts_to_notify,
    mark_abandoned_cart_notified,
)

logger = logging.getLogger("store_channel_service")

# ==================== USERBOT CLIENT (PREMIUM CUSTOM EMOJI UCHUN) ====================
_userbot_client: Optional[Client] = None

def set_userbot_client(client: Client):
    """Userbot clientni global saqlash — custom emojilar userbot orqali kanalga yuboriladi."""
    global _userbot_client
    _userbot_client = client
    logger.info("Store channel service: Userbot client o'rnatildi (Premium custom emoji enabled).")

async def _send_channel_message(bot_client: Client, text: str, reply_markup=None) -> Optional[int]:
    """
    Kanalga xabar yuborish. Avval userbot (Premium) orqali harakat qiladi —
    custom emojilar to'g'ri render bo'lishi uchun.
    Agar userbot mavjud bo'lmasa yoki xato bo'lsa, bot client orqali yuboradi.
    """
    if not STORE_CHANNEL:
        return None

    # 1. Userbot orqali yuborish (Premium = custom emoji ishlaydi)
    if _userbot_client:
        try:
            msg = await _userbot_client.send_message(
                STORE_CHANNEL, text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            logger.info("Kanal xabari USERBOT (Premium) orqali yuborildi — custom emojilar faol.")
            return msg.id if msg else None
        except Exception as ub_err:
            logger.warning(f"Userbot orqali kanalga yuborishda xato: {ub_err}, bot ga fallback...")

    # 2. Bot orqali fallback
    try:
        msg = await bot_client.send_message(STORE_CHANNEL, text, reply_markup=reply_markup)
        logger.info("Kanal xabari BOT orqali yuborildi (custom emoji fallback).")
        return msg.id if msg else None
    except Exception as bot_err:
        logger.error(f"Bot orqali kanalga yuborishda xato: {bot_err}")
        return None


# ==================== LIVE XARIDLAR (PURCHASE BROADCAST) ====================

async def broadcast_channel_purchase(
    client: Client,
    user_name: str,
    product_name: str,
    price_uzs: int,
    order_id: Optional[str] = None
) -> bool:
    """
    Bot orqali yangi tovar yoki VIP sotib olinganda @CreatorFlow_Store kanaliga
    chiroyli tasdiqlangan xabar yuborish.
    """
    if not STORE_CHANNEL:
        return False

    try:
        # Xaridor nomini xavfsiz maskalash (e.g. Jasur -> J****r, @user -> @u***r)
        raw_name = (user_name or "Foydalanuvchi").strip()
        if raw_name.startswith("@") and len(raw_name) > 3:
            masked_name = f"@{raw_name[1]}***{raw_name[-1]}"
        elif len(raw_name) > 2:
            masked_name = f"{raw_name[0]}***{raw_name[-1]}"
        else:
            masked_name = "Mijoz"

        bot_me = getattr(client, "me", None)
        bot_username = bot_me.username if bot_me else "CreatorFlow_StudioBot"

        order_str = f"#{order_id}" if order_id else f"#{random.randint(10000, 99999)}"

        text = (
            f"{ce('CART')} <b>YANGI XARID AMALGA OSHIRILDI!</b>\n\n"
            f"{ce('USER')} <b>Xaridor:</b> <code>{masked_name}</code>\n"
            f"{ce('GIFT')} <b>Mahsulot:</b> <b>{product_name}</b>\n"
            f"{ce('MONEY')} <b>Narxi:</b> <code>{price_uzs:,} so'm</code>\n"
            f"{ce('KEY')} <b>Buyurtma ID:</b> <code>{order_str}</code>\n"
            f"{ce('SUCCESS')} <b>Holat:</b> Muvaffaqiyatli yetkazildi\n\n"
            f"{ce('ROCKET')} <i>CreatorFlow Studio orqali 24/7 tezkor va kafolatli xarid!</i>"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Xarid qilish", url=f"https://t.me/{bot_username}?start=store")],
            [InlineKeyboardButton(f"Botga o'tish", url=f"https://t.me/{bot_username}")]
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        logger.info(f"Kanalga xarid xabari yuborildi: {product_name} - {price_uzs} so'm")
        return True
    except Exception as err:
        logger.error(f"broadcast_channel_purchase xatosi: {err}")
        return False


# ==================== RESTOCK E'LONLARI (RESTOCK ALERTS) ====================

async def send_channel_restock_alert(client: Client, items_summary: Optional[str] = None) -> bool:
    """
    Do'konda tovarlar to'ldirilganda (restock) kanalga e'lon joylash.
    """
    if not STORE_CHANNEL:
        return False

    try:
        bot_me = getattr(client, "me", None)
        bot_username = bot_me.username if bot_me else "CreatorFlow_StudioBot"

        if not items_summary:
            items_summary = (
                f"• {ce('CROWN')} <b>CapCut Pro (1-12 oylik)</b> — Zaxira to'liq to'ldirildi!\n"
                f"• {ce('CHATGPT')} <b>ChatGPT Plus / OpenAI API</b> — Yangi kalitlar keldi!\n"
                f"• {ce('GEMINI')} <b>Gemini 1.5/2.0 Flash & Pro</b> — Cheksiz tokenlar!\n"
                f"• {ce('STAR')} <b>Telegram Stars & Sovg'alar</b> — Eng arzon narxlarda!\n"
                f"• {ce('VIP')} <b>CreatorFlow VIP Status ({VIP_PRICE_UZS:,} UZS)</b> — Qayta ochiq!"
            )

        text = (
            f"{ce('FIRE')} <b>KATTA RESTOCK! DO'KON ZAXIRASI YANGILANDI!</b>\n\n"
            f"{ce('MONEY')} Hurmatli obunachilar, CreatorFlow Studio do'koniga yangi tovarlar va raqamli xizmatlar kelib tushdi:\n\n"
            f"{items_summary}\n\n"
            f"{ce('ROCKET')} <b>Barcha mahsulotlar avtomatlashtirilgan tarzda soniyalarda yetkaziladi!</b>\n"
            f"{ce('KEY')} Xarid qilish uchun quyidagi tugmani bosing:"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Do'konga kirish", url=f"https://t.me/{bot_username}?start=store")],
            [InlineKeyboardButton(f"VIP Tarif (69,000 UZS)", url=f"https://t.me/{bot_username}?start=vip")]
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        logger.info("Kanalga restock e'loni yuborildi.")
        return True
    except Exception as err:
        logger.error(f"send_channel_restock_alert xatosi: {err}")
        return False


# ==================== REKLAMA VA AKSIYALAR (PROMO MESSAGES) ====================

PROMO_TEMPLATES = [
    {
        "id": "vip_promo",
        "title": "CREATORFLOW VIP TARIF — CHEKSIZ IMKONIYATLAR!",
        "body": (
            f"{ce('VIP')} <b>CreatorFlow VIP bilan ishingizni 10 barobar tezlashtiring!</b>\n\n"
            f"{ce('CHECK')} <b>Cheksiz video yuklash va tahlil</b> (kunlik limitsiz)\n"
            f"{ce('CHECK')} <b>24/7 Ustuvor navbat</b> (Priority Worker & Streamer)\n"
            f"{ce('CHECK')} <b>Restock tovarlarini birinchi xarid qilish huquqi</b>\n"
            f"{ce('CHECK')} <b>Do'kon tovarlariga eksklyuziv keshbek</b>\n"
            f"{ce('CHECK')} <b>VIP yopiq konkurslar va sovg'alarda ishtirok</b>\n\n"
            f"{ce('MONEY')} <b>Oylik obuna narxi:</b> <code>69,000 so'm</code> (yoki 250 Stars)"
        ),
        "btn_text": "VIP Faollashtirish (69,000 UZS)",
        "start_param": "vip"
    },
    {
        "id": "autostream_promo",
        "title": "24/7 YOUTUBE JONLI EFIR & AVTO-POSTING!",
        "body": (
            f"{ce('ROCKET')} <b>Kanalingizni avtopilotda rivojlantiring!</b>\n\n"
            f"{ce('VIDEO')} YouTube kanalingizga 24/7 to'xtovsiz jonli efir (Live Stream) uzatish\n"
            f"{ce('CLIPPERS')} Avtomatik Shorts video generatsiyasi va rejalashtirish\n"
            f"{ce('SEO_TAG')} AI SEO tavsiflar va trend teglarni avtomatik joylash\n\n"
            f"{ce('SUCCESS')} <i>Hammasi serverda uzluksiz ishlaydi!</i>"
        ),
        "btn_text": "Avtopilotni Yoqish",
        "start_param": "stream"
    },
    {
        "id": "games_promo",
        "title": "OMADLI QUTI & OMAD G'ILDIRAGI — SOVRINLAR YUTIB OLING!",
        "body": (
            f"{ce('GIFT')} <b>Bot ichida har kuni bepul yutuqlar!</b>\n\n"
            f"{ce('WHEEL')} <b>Lucky Wheel:</b> Kunlik bepul aylantirish (Stars va TON yutuqlari)\n"
            f"{ce('MYSTERY_BOX')} <b>Mystery Box:</b> Omadli qutilarni ochib litsenziyalar yutish\n"
            f"{ce('DUEL')} <b>PvP Duel:</b> Do'stlaringiz bilan tanga tashlash bellashuvi"
        ),
        "btn_text": "O'yinlarni O'ynash",
        "start_param": "games"
    }
]

async def send_channel_promo(client: Client, promo_index: Optional[int] = None) -> bool:
    """
    Kanalga davriy reklama postini yuborish.
    """
    if not STORE_CHANNEL:
        return False

    try:
        if promo_index is None:
            promo = random.choice(PROMO_TEMPLATES)
        else:
            promo = PROMO_TEMPLATES[promo_index % len(PROMO_TEMPLATES)]

        bot_me = getattr(client, "me", None)
        bot_username = bot_me.username if bot_me else "CreatorFlow_StudioBot"

        text = (
            f"{ce('CREATORFLOW_LOGO')} <b>{promo['title']}</b>\n\n"
            f"{promo['body']}\n\n"
            f"{ce('LINK')} <b>Hoziroq botga kiring:</b> @{bot_username}"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{promo['btn_text']}", url=f"https://t.me/{bot_username}?start={promo['start_param']}")],
            [InlineKeyboardButton("Bosh Menyu", url=f"https://t.me/{bot_username}")]
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        logger.info(f"Kanalga reklama yuborildi: {promo['id']}")
        return True
    except Exception as err:
        logger.error(f"send_channel_promo xatosi: {err}")
        return False


# ==================== SOVRINLI KONKURSLAR (GIVEAWAYS) ====================

async def create_and_post_contest(
    client: Client,
    title: str = "Haftalik Omadli Ishtirokchi Konkursi",
    prize_text: str = "1 Oylik CreatorFlow VIP (69,000 UZS) + 100 Stars",
    duration_hours: int = 48
) -> Optional[int]:
    """
    @CreatorFlow_Store kanalida rasmiy konkurs e'lon qilish va DB ga saqlash.
    """
    if not STORE_CHANNEL:
        return None

    try:
        bot_me = getattr(client, "me", None)
        bot_username = bot_me.username if bot_me else "CreatorFlow_StudioBot"

        contest_id = create_channel_contest(
            title=title,
            prize_text=prize_text,
            duration_hours=duration_hours
        )

        if not contest_id:
            return None

        text = (
            f"{ce('TICKET')} <b>CREATORFLOW MEGA KONKURS! #{contest_id}</b>\n\n"
            f"{ce('TROPHY')} <b>Bosh sovrin:</b>\n"
            f"<b>{prize_text}</b>\n\n"
            f"{ce('ROCKET')} <b>Ishtirok etish shartlari juda oddiy:</b>\n"
            f"1. {ce('CHANNEL')} {STORE_CHANNEL} kanalimizga a'zo bo'lish\n"
            f"2. {ce('PHONE')} Botda telefon raqamingizni tasdiqlash\n"
            f"3. Pastdagi <b>«Ishtirok etish»</b> tugmasini bosish!\n\n"
            f"{ce('WAIT')} <b>Muddat:</b> {duration_hours} soat\n"
            f"{ce('SPARKLES')} <i>G'oliblar tizim tomonidan tasodifiy (random) tarzda aniqlanadi!</i>"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Konkursda ishtirok etish", url=f"https://t.me/{bot_username}?start=contest_{contest_id}")],
            [InlineKeyboardButton("Botga o'tish", url=f"https://t.me/{bot_username}")]
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        return contest_id
    except Exception as err:
        logger.error(f"create_and_post_contest xatosi: {err}")
        return None


# ==================== FLASH SALE (CHEGIRMA AKSIYALARI) ====================

async def send_channel_flash_sale(
    client: Client,
    title: str = "Tungi Happy Hour Chegirmasi",
    discount_percent: int = 20,
    duration_hours: int = 2
) -> bool:
    """Kanalga vaqtinchalik Flash Sale e'lonini joylash va DB ga kiritish"""
    if not STORE_CHANNEL:
        return False
    try:
        sale_id = create_flash_sale(title, discount_percent, duration_hours)
        bot_me = getattr(client, "me", None)
        bot_username = bot_me.username if bot_me else "CreatorFlow_StudioBot"

        text = (
            f"{ce('FIRE')} <b>SUPER FLASH SALE! {title.upper()}!</b>\n\n"
            f"{ce('CASH')} <b>Chegirma hajmi:</b> Barcha raqamli tovarlarga <b>-{discount_percent}%</b> chegirma!\n"
            f"{ce('TIMER')} <b>Davomiyligi:</b> Faqat <b>{duration_hours} soat</b> davomida amal qiladi!\n\n"
            f"{ce('BOX')} <i>CapCut Pro, OpenAI kalitlar, Gemini va barcha xizmatlarni arzon narxda oling!</i>\n"
            f"{ce('ROCKET')} <b>Vaqt ketdi! Xarid qilish uchun quyidagi tugmani bosing:</b>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Chegirmada xarid qilish", url=f"https://t.me/{bot_username}?start=store")],
            [InlineKeyboardButton("VIP Tarif (69,000 UZS)", url=f"https://t.me/{bot_username}?start=vip")]
        ])
        await _send_channel_message(client, text, reply_markup=kb)
        logger.info(f"Kanalga Flash Sale e'loni yuborildi: {title} (-{discount_percent}%)")
        return True
    except Exception as err:
        logger.error(f"send_channel_flash_sale xatosi: {err}")
        return False


# ==================== TEZKOR DROP PROMOKODLAR (FAST-FINGER DROP) ====================

async def send_channel_drop_promo(
    client: Client,
    code: str,
    reward_uzs: int = 10000,
    max_uses: int = 3,
    duration_minutes: int = 60
) -> bool:
    """Kanalga cheklangan va tezkor promokod tashlash"""
    if not STORE_CHANNEL:
        return False
    try:
        create_fast_drop_promo(code, "balance", reward_uzs, max_uses, duration_minutes)
        bot_me = getattr(client, "me", None)
        bot_username = bot_me.username if bot_me else "CreatorFlow_StudioBot"

        text = (
            f"{ce('FIRE')} <b>TEZKOR PROMOKOD DROP! (Fast-Finger)</b>\n\n"
            f"{ce('KEY')} <b>Promokod:</b> <code>{code}</code>\n"
            f"{ce('MONEY')} <b>Yutuq:</b> <code>+{reward_uzs:,} so'm</code> balansingizga!\n"
            f"{ce('LOCK')} <b>Cheklov:</b> Faqat birinchi <b>{max_uses}</b> ta tezkor obunachi uchun!\n"
            f"{ce('WAIT')} <b>Amal qilish vaqti:</b> {duration_minutes} daqiqa\n\n"
            f"{ce('SPARKLES')} <i>Promokodni botga kirib yuboring yoki quyidagi tugmani bosing:</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Promokodni faollashtirish", url=f"https://t.me/{bot_username}?start=promo_{code}")],
            [InlineKeyboardButton("Botga o'tish", url=f"https://t.me/{bot_username}")]
        ])
        await _send_channel_message(client, text, reply_markup=kb)
        logger.info(f"Kanalga tezkor promokod tashlandi: {code}")
        return True
    except Exception as err:
        logger.error(f"send_channel_drop_promo xatosi: {err}")
        return False


# ==================== WISHLIST NOTIFIER (ZAXIRA KELGANDA XABAR) ====================

async def notify_wishlist_users(
    client: Client,
    product_id: int,
    product_name: str,
    price_uzs: int = 0
) -> int:
    """Mahsulot zaxirasi to'ldirilganda kutayotgan mijozlarga DM xabar yuborish"""
    user_ids = get_wishlist_users_for_product(product_id)
    if not user_ids:
        return 0

    notified_count = 0
    text = (
        f"{ce('BELL')} <b>DIQQAT! SIZ KUTGAN MAHSULOT ZAXIRADA!</b>\n\n"
        f"{ce('BOX')} <b>Mahsulot:</b> <b>{product_name}</b>\n"
        f"{ce('MONEY')} <b>Narxi:</b> <code>{price_uzs:,} so'm</code>\n\n"
        f"{ce('ROCKET')} <i>Zaxira soni cheklangan bo'lishi mumkin. Hoziroq xarid qilishga ulguring!</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Xarid qilish", callback_data=f"vb_item_{product_id}_ai")],
        [InlineKeyboardButton("Do'konga o'tish", callback_data="menu_marketplace")]
    ])

    for uid in user_ids:
        try:
            await client.send_message(uid, text, reply_markup=kb)
            notified_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Wishlist xabari yuborilmadi ({uid}): {e}")

    mark_wishlist_notified(product_id)
    logger.info(f"Wishlist: {notified_count} ta foydalanuvchiga xabar yuborildi.")
    return notified_count


# ==================== ABANDONED CART RETARGETING (SAVATNI ESLATISH) ====================

async def check_and_notify_abandoned_carts(client: Client) -> int:
    """Tashlab ketilgan savatlarni tekshirish va muloyim eslatma yuborish"""
    carts = get_abandoned_carts_to_notify(minutes_ago=20)
    if not carts:
        return 0

    notified = 0
    for cart in carts:
        try:
            cart_id = cart["id"]
            uid = cart["tg_user_id"]
            p_name = cart["product_name"]
            p_id = cart["product_id"]
            p_price = cart.get("price_uzs", 0)

            text = (
                f"{ce('CART')} <b>Savatdagi mahsulotingiz sizni kutmoqda!</b>\n\n"
                f"Hurmatli ijodkor, siz <b>{p_name}</b> (<code>{p_price:,} so'm</code>) xaridini ko'rib chiqayotgan edingiz.\n\n"
                f"{ce('SHIELD')} <i>Mahsulot siz uchun zaxirada vaqtinchalik saqlab turilibdi.</i>\n"
                f"{ce('ROCKET')} Xaridni yakunlashni xohlaysizmi?"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Xaridni davom ettirish", callback_data=f"vb_item_{p_id}_ai")],
                [InlineKeyboardButton("Savatni tozalash", callback_data=f"cart_cancel_{cart_id}")]
            ])

            await client.send_message(uid, text, reply_markup=kb)
            mark_abandoned_cart_notified(cart_id)
            notified += 1
            await asyncio.sleep(0.15)
        except Exception as err:
            logger.warning(f"Abandoned cart notification error (cart {cart.get('id')}): {err}")
            mark_abandoned_cart_notified(cart.get("id"))

    if notified > 0:
        logger.info(f"Tashlab ketilgan {notified} ta savat bo'yicha eslatma yuborildi.")
    return notified


# ==================== AVTOPILOT SIKLI (AUTOPILOT RUNNER) ====================

async def run_channel_autopilot(client: Client):
    """
    Kanal uchun fon jarayoni:
    - Har 8-12 soatda avtomatik ravishda yangi aksiya, konkurs yoki restock eslatmasini joylaydi.
    - Har 5 daqiqada tashlab ketilgan savatlarni tekshirib eslatadi.
    """
    logger.info("Kanal avtopilot xizmati ishga tushirildi (@CreatorFlow_Store)...")
    await asyncio.sleep(60)  # Bot to'liq yuklanishini kutish

    promo_counter = 0
    loop_ticks = 0
    while True:
        try:
            # 1. Tashlab ketilgan savatlarni tekshirish (har 5 daqiqada)
            await check_and_notify_abandoned_carts(client)

            # 2. Reklama postini har 8 soatda (96 ta 5-daqiqalik sikl = 8 soat) yuborish
            if loop_ticks % 96 == 0:
                await send_channel_promo(client, promo_index=promo_counter)
                promo_counter += 1

            loop_ticks += 1
            await asyncio.sleep(300) # 5 daqiqa
        except asyncio.CancelledError:
            logger.info("Kanal avtopilot to'xtatildi.")
            break
        except Exception as e:
            logger.error(f"run_channel_autopilot sikl xatosi: {e}")
            await asyncio.sleep(60)
