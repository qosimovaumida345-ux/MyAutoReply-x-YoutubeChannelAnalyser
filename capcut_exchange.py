"""
CapCut Desktop & Pro Tools Referral Exchange Hub.
Foydalanuvchilar o'zlarining CapCut Desktop / Pro taklif havolalarini (invite link)
tizimga kiritadi va botga yangi kirgan foydalanuvchilarga rotatsiya asosida tarqatiladi.
Natijada ikkala tomon ham 7 kunlik (va 70 kungacha yig'iluvchi) bepul CapCut Pro litsenziyasiga ega bo'ladi!
"""

import logging
import re
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db

logger = logging.getLogger(__name__)

CAPCUT_GUIDE_TEXT = (
    "🎬 **CAPCUT PRO NI 7 KUNDAN 70 KUNGACHA BEPUL OLISH TIZIMI!**\n\n"
    "CapCut Desktop (kompyuter versiyasi) yangi foydalanuvchilarga referal dasturi orqali "
    "**1 hafta bepul Pro obuna** taqdim etadi.\n\n"
    "💎 **Bu qanday ishlaydi?**\n"
    "1️⃣ Quyidagi '🎁 Bepul Pro Olish' tugmasini bosing va navbatdagi ishtirokchining havolasi orqali CapCut Desktop-ni o'rnating.\n"
    "2️⃣ Kompyuteringizda ro'yxatdan o'ting — sizga darhol 7 kunlik CapCut Pro beriladi!\n"
    "3️⃣ O'zingizning CapCut Desktop taklif havolangizni botga qo'shing — sizning havolangiz orqali boshqa yangi foydalanuvchilar kiradi va har bir odam uchun yana +7 kun Pro qo'shiladi (jami 70 kungacha)!\n\n"
    "🚀 Hammasi 100% tekin va o'zaro hamkorlikka asoslangan!"
)

def is_valid_capcut_link(url: str) -> bool:
    """CapCut yoki tegishli rasmiy servis havolasini tekshirish"""
    if not url or not isinstance(url, str):
        return False
    pattern = r"https?://(?:www\.)?(?:capcut\.(?:com|net)|mobile\.capcut\.com)/[A-Za-z0-9_\-\.\?&=/%]+"
    return bool(re.search(pattern, url)) or ("capcut" in url.lower() and url.startswith("http"))

def submit_referral_link(tg_user_id: int, invite_link: str, service_name: str = "capcut") -> tuple:
    """Foydalanuvchi havolasini umumiy hovuzga qo'shish"""
    clean_link = invite_link.strip()
    if not is_valid_capcut_link(clean_link):
        return False, "⚠️ Noto'g'ri havola! Havola rasmiy CapCut taklif havolasi bo'lishi kerak (masalan: https://www.capcut.com/...)"

    success = db.add_capcut_referral(tg_user_id, clean_link, service_name)
    if not success:
        return False, "Ushbu havola allaqachon tizimda mavjud yoki bazada xatolik yuz berdi."

    return True, "🎉 **Havolangiz muvaffaqiyatli qabul qilindi!**\nU navbatdagi yangi foydalanuvchilarga beriladi va ular har safar kirganda sizga Pro kunlar qo'shiladi!"

def get_next_invite_link(exclude_user_id: int = None, service_name: str = "capcut") -> dict:
    """Eng kam bosilgan yoki navbatdagi faol havolani olish"""
    return db.get_active_capcut_referral(exclude_user_id, service_name)

def get_capcut_menu_keyboard(has_active_link: bool = False, lang: str = "uz") -> InlineKeyboardMarkup:
    """CapCut almashinuv markazi menyusi"""
    buttons = [
        [InlineKeyboardButton("🎁 Bepul Pro Havola Olish", callback_data="capcut_get_pro")],
        [InlineKeyboardButton("➕ O'z Havolamni Qo'shish", callback_data="capcut_add_link")],
        [InlineKeyboardButton("📊 Mening Havolalarim Statistikasi", callback_data="capcut_my_stats")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(buttons)
