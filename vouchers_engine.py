"""
P2P Conditional Cheklar (@wallet uslubida) va Antifraud Sentinel Tizimi.
Homiy kanalga majburiy obuna sharti bilan chek tarqatish va
kanaldan chiqqan qoidabuzarlarni botdan butunlay avtomatik bloklash.
"""

import uuid
import logging
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import database as db
from custom_emojis import e, ce

logger = logging.getLogger(__name__)

RED_ANTIFRAUD_WARNING = (
    f"{ce('ANTIFRAUD_SIREN')} <b>DIQQAT: QAT'IY XAVFSIZLIK QOIDASI!</b>\n\n"
    f"Ushbu chek mablag'ini qabul qilgandan so'ng, agar siz ko'rsatilgan homiy kanaldan "
    f"chiqib ketsangiz — {ce('LOCK')} <b>bot siz uchun BUTUNLAY BLOKLANADI</b> va barcha xizmatlaringiz, "
    f"balansingiz zudlik bilan muzlatiladi!\n\n"
    f"Iltimos, mablag'ni olishdan avval kanal a'zoligingizni doimiy saqlab qolishingizga ishonch hosil qiling."
)

def generate_check_code() -> str:
    """Noyob chek kodini generatsiya qiladi"""
    return "CHK-" + uuid.uuid4().hex[:8].upper()

def create_p2p_check(creator_id: int, total_amount_uzs: int, max_claims: int, required_channel: str = None) -> tuple:
    """
    Foydalanuvchi balansidan pul yechib yangi shartli chek yaratish.
    """
    clean_channel = (required_channel or "").strip().lstrip("@")
    code = generate_check_code()
    success, msg = db.create_conditional_check(
        creator_id=creator_id,
        check_code=code,
        total_amount_uzs=total_amount_uzs,
        max_claims=max_claims,
        required_channel=clean_channel if clean_channel else None
    )
    if not success:
        return False, msg, None
    return True, f"Chek muvaffaqiyatli yaratildi!\nKod: `{code}`", code

def get_check_claim_keyboard(check_code: str, required_channel: str = None) -> InlineKeyboardMarkup:
    """Chekni olish uchun tugmalar"""
    buttons = []
    if required_channel:
        clean_ch = required_channel.strip().lstrip("@")
        buttons.append([InlineKeyboardButton("📢 Homiy kanalga a'zo bo'lish", url=f"https://t.me/{clean_ch}")])
    buttons.append([InlineKeyboardButton("💸 Chekni qabul qilish", callback_data=f"claim_chk_{check_code}")])
    return InlineKeyboardMarkup(buttons)

async def verify_channel_membership(app, channel_username: str, user_id: int) -> bool:
    """Foydalanuvchining homiy kanalda a'zoligini tekshirish"""
    clean_ch = channel_username.strip().lstrip("@")
    try:
        member = await app.get_chat_member(f"@{clean_ch}", user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        return False
    except Exception as e:
        logger.warning(f"Kanal a'zoligini tekshirishda xato (@{clean_ch}, user={user_id}): {e}")
        # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa ham xavfsizlik uchun tekshirish
        return False

async def process_check_claim(app, user_id: int, check_code: str) -> tuple:
    """
    Chekni tekshirish, obunani ko'rish va hisobga o'tkazish.
    """
    # 1. User allaqachon bloklanganmi?
    if db.is_user_antifraud_banned(user_id):
        return False, f"{ce('ERROR')} Siz qoidabuzarlik (kanaldan chiqib ketish) sababli botdan bloklangansiz! Chek ola olmaysiz."

    check = db.get_conditional_check(check_code)
    if not check:
        return False, f"{ce('ERROR')} Bunday chek topilmadi yoki muddati tugagan."

    if not check["is_active"]:
        return False, f"{ce('ERROR')} Ushbu chekdan barcha foydalanuvchilar olib bo'lgan."

    # 2. Homiy kanal obunasi talab qilinadimi?
    req_ch = check.get("required_channel")
    if req_ch:
        is_member = await verify_channel_membership(app, req_ch, user_id)
        if not is_member:
            return False, f"{ce('WARN')} Ushbu chekni olish uchun avval @{req_ch} kanaliga obuna bo'lishingiz shart!\n\n{RED_ANTIFRAUD_WARNING}"

    # 3. Bazada claim qilish
    ok, msg = db.claim_conditional_check(check["id"], user_id, check["amount_per_user_uzs"])
    if not ok:
        return False, f"{ce('ERROR')} {msg}"

    amount = check["amount_per_user_uzs"]
    congrats = (
        f"{ce('PARTY')} <b>Tabriklaymiz! Chek hisobingizga o'tkazildi!</b>\n\n"
        f"{ce('MONEY')} <b>Miqdor:</b> <code>{amount:,}</code> so'm\n"
        f"{ce('CARD')} Yangi balansingizga qo'shildi.\n\n"
        f"{RED_ANTIFRAUD_WARNING}"
    )
    return True, congrats


async def run_antifraud_sentinel_once(app):
    """
    Barcha homiy kanallardagi faol chek oluvchilarni a'zoligini tekshirish.
    Agar a'zolik bekor qilingan bo'lsa -> Zudlik bilan BAN beriladi!
    """
    conn = db.get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        # Barcha homiy kanallarni olamiz
        cur.execute("SELECT DISTINCT required_channel FROM conditional_checks WHERE required_channel IS NOT NULL AND required_channel != ''")
        channels = [r["required_channel"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
        cur.close()
    finally:
        conn.close()

    for channel in channels:
        claimers = db.get_channel_check_claimers(channel)
        for uid in claimers:
            if db.is_user_antifraud_banned(uid):
                continue
            is_sub = await verify_channel_membership(app, channel, uid)
            if not is_sub:
                logger.warning(f"🚨 ANTIFRAUD: User {uid} homiy kanal (@{channel}) dan chiqib ketdi! BAN berilmoqda...")
                db.ban_antifraud_user(uid, reason=f"Homiy kanal (@{channel}) dan chiqib ketgani sababli botdan chetlashtirildi")
                try:
                    ban_notification = (
                        f"{ce('LOCK')} <b>HISOBINGIZ BUTUNLAY BLOKLANDI!</b>\n\n"
                        f"Siz shartli chek olganingizdan so'ng homiy kanal (@{channel}) dan chiqib ketdingiz.\n"
                        f"Xavfsizlik tizimi qoidalariga binoan hisobingiz va botdagi barcha xizmatlaringiz muzlatildi."
                    )
                    await app.send_message(chat_id=uid, text=ban_notification)
                except Exception as send_err:
                    logger.debug(f"User {uid} ga ban xabari yuborilmadi: {send_err}")

async def start_antifraud_sentinel_daemon(app, interval_seconds: int = 3600):
    """Orqa fonda har soatda ishlovchi antifraud qo'riqchisi"""
    while True:
        try:
            await run_antifraud_sentinel_once(app)
        except Exception as e:
            logger.error(f"Antifraud sentinel siklida xato: {e}")
        await asyncio.sleep(interval_seconds)
