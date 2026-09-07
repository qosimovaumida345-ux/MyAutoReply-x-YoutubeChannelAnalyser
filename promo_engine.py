"""
Promo Codes & Discount Coupons Engine.
Admin tomonidan maxsus promokodlar (/newpromo) yaratish va
foydalanuvchilar tomonidan tezkor faollashtirish (/redeem).
"""

import logging
import database as db

logger = logging.getLogger(__name__)

def admin_create_promo(code: str, bonus_uzs: int, max_uses: int = 100, discount_percent: int = 0) -> tuple:
    """Admin yangi promokod yaratishi"""
    clean_code = code.strip().upper()
    if len(clean_code) < 3:
        return False, "Promokod kamida 3 ta belgidan iborat bo'lishi kerak."

    if bonus_uzs <= 0 and discount_percent <= 0:
        return False, "Bonus miqdori yoki chegirma foizi 0 dan katta bo'lishi shart."

    success = db.create_promo_code(
        code=clean_code,
        balance_bonus_uzs=bonus_uzs,
        discount_percent=discount_percent,
        max_uses=max_uses
    )
    if not success:
        return False, "Promokod yaratishda xatolik (balki bu kod allaqachon mavjuddir)."

    return True, (
        f"✅ **Yangi promokod yaratildi!**\n\n"
        f"🎟 **Kod:** `{clean_code}`\n"
        f"💰 **Bonus:** `{bonus_uzs:,}` so'm\n"
        f"👥 **Maksimal faollashtirish:** `{max_uses}` marta\n"
        f"💡 Foydalanuvchilar `/redeem {clean_code}` orqali olishlari mumkin."
    )

def user_redeem_promo(user_id: int, code: str) -> tuple:
    """Foydalanuvchi promokodni faollashtirishi"""
    clean_code = code.strip().upper()
    if not clean_code:
        return False, "Iltimos, promokodni kiriting: `/redeem KOD`"

    # Antifraud tekshiruvi
    if db.is_user_antifraud_banned(user_id):
        return False, "🚫 Hisobingiz antifraud tizimi tomonidan cheklangan!"

    ok, msg, bonus = db.redeem_promo_code(clean_code, user_id)
    if not ok:
        return False, msg

    return True, (
        f"🎉 **TABRIKLAYMIZ! Promokod faollashtirildi!**\n\n"
        f"🎟 **Kod:** `{clean_code}`\n"
        f"💰 **Hisobingizga qo'shildi:** `+{bonus:,}` so'm\n"
        f"💳 Yangilangan balansingizni hisobingizda ko'rishingiz mumkin."
    )
