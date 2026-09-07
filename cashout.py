"""
Cashout Engine for Telegram Stars and TON Wallet.
Foydalanuvchilar o'zlarining referal va yutuq balanslarini Telegram Stars yoki
TON hamyonlariga yechib olishlari uchun avtomatlashtirilgan admin nazoratli tizim.
"""

import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db
from config import OWNER_ID

logger = logging.getLogger(__name__)

MIN_CASHOUT_UZS = 20_000  # Minimal yechish: 20 000 so'm

# Taxminiy konvertatsiya stavkalari
STARS_PER_10K_UZS = 40     # 10 000 so'm = ~40 Telegram Stars
TON_PRICE_UZS = 70_000     # 1 TON = ~70 000 so'm

def request_user_cashout(tg_user_id: int, method: str, target_address: str, amount_uzs: int) -> tuple:
    """Pul yechish arizasini topshirish va balansni zaxiralash"""
    if amount_uzs < MIN_CASHOUT_UZS:
        return False, f"Minimal yechish summasi: {MIN_CASHOUT_UZS:,} so'm."

    clean_target = target_address.strip()
    if method == "ton" and len(clean_target) < 30:
        return False, "Noto'g'ri TON hamyon manzili! (EQ... yoki UQ... bilan boshlanishi kerak)"
    elif method == "stars" and len(clean_target) < 3:
        return False, "Noto'g'ri Telegram username yoki foydalanuvchi ma'lumoti!"

    # Ekvivalentni hisoblash
    if method == "stars":
        stars_est = int((amount_uzs / 10_000) * STARS_PER_10K_UZS)
        equiv_str = f"~{stars_est} Stars"
    else:
        ton_est = round(amount_uzs / TON_PRICE_UZS, 3)
        equiv_str = f"~{ton_est} TON"

    ok, msg = db.create_cashout_request(tg_user_id, method, clean_target, amount_uzs, equiv_str)
    return ok, msg, equiv_str

async def notify_admin_new_cashout(app, req_id: int, user, method: str, target_address: str, amount_uzs: int, equiv_str: str):
    """Yangi pul yechish arizasi haqida Adminga xabar va tasdiqlash tugmalarini yuborish"""
    user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Noma'lum"
    username_str = f"@{user.username}" if user.username else "Username yo'q"

    text = (
        f"💸 **PUL YECHISH SO'ROVI #{req_id}**\n\n"
        f"👤 **Foydalanuvchi:** {user_fullname} ({username_str})\n"
        f"🆔 **Telegram ID:** `{user.id}`\n"
        f"💳 **Usul:** `{method.upper()}`\n"
        f"🎯 **Manzil/Username:** `{target_address}`\n"
        f"💰 **Miqdor:** `{amount_uzs:,}` so'm ({equiv_str})\n"
        f"⏳ **Holat:** Kutilmoqda"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ To'landi (Tasdiqlash)", callback_data=f"adm_co_app_{req_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"adm_co_rej_{req_id}")
        ]
    ])

    try:
        await app.send_message(chat_id=OWNER_ID, text=text, reply_markup=kb)
    except Exception as e:
        logger.error(f"Adminga cashout xabarini yuborishda xato: {e}")

async def handle_admin_cashout_decision(app, req_id: int, action: str, admin_id: int) -> tuple:
    """Admin qarorini qayta ishlash (approve yoki reject)"""
    new_status = "approved" if action == "app" else "rejected"
    success = db.process_cashout_request(req_id, new_status)
    if not success:
        return False, "Ushbu so'rov allaqachon ko'rib chiqilgan yoki topilmadi."

    # Foydalanuvchini xabardor qilish
    conn = db.get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT tg_user_id, amount_uzs, method, currency_equivalent FROM cashout_requests WHERE id = %s", (req_id,))
            row = cur.fetchone()
            if row:
                uid = row["tg_user_id"]
                amt = row["amount_uzs"]
                meth = row["method"].upper()
                equiv = row["currency_equivalent"]

                if new_status == "approved":
                    u_msg = (
                        f"✅ **PULINGIZ O'TKAZIB BERILDI!**\n\n"
                        f"Miqdor: `{amt:,}` so'm ({equiv})\n"
                        f"Usul: `{meth}`\n"
                        f"To'lov admin tomonidan muvaffaqiyatli tasdiqlandi!"
                    )
                else:
                    u_msg = (
                        f"❌ **PUL YECHISH SO'ROVINGIZ RAD ETILDI!**\n\n"
                        f"Miqdor: `{amt:,}` so'm hisobingizga to'liq qaytarildi.\n"
                        f"Qo'shimcha savollar bo'lsa, qo'llab-quvvatlash bo'limiga murojaat qiling."
                    )
                try:
                    await app.send_message(chat_id=uid, text=u_msg)
                except Exception as send_err:
                    logger.debug(f"User {uid} ga cashout natijasi yuborilmadi: {send_err}")
            cur.close()
        finally:
            conn.close()

    status_txt = "tasdiqlandi va to'landi" if new_status == "approved" else "rad etildi va pul qaytarildi"
    return True, f"So'rov #{req_id} {status_txt}."
