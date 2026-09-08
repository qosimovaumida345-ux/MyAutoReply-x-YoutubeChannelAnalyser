"""
CapCut Pro — Pullik Sotish Tizimi.
Foydalanuvchilar CapCut Pro Desktop va Mobile litsenziyalarini bot orqali xarid qiladi.
Tariflar:
  - 30 kunlik obuna: 99,000 so'm ($8) / 400 ⭐ Stars
  - 90 kunlik obuna: 249,000 so'm ($19) / 1,000 ⭐ Stars (16% chegirma)
  - 365 kunlik obuna: 799,000 so'm ($62) / 3,000 ⭐ Stars (33% chegirma)
"""

import uuid
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db
from custom_emojis import ce

logger = logging.getLogger(__name__)

# CapCut Pro rasmiy narxlari
CAPCUT_PRICES = {
    "30": {
        "days": 30,
        "price_uzs": 99000,
        "stars": 400,
        "label": "1 Oylik",
        "price_label": "99,000 so'm ($8)",
        "stars_label": "400 ⭐"
    },
    "90": {
        "days": 90,
        "price_uzs": 249000,
        "stars": 1000,
        "label": "3 Oylik",
        "price_label": "249,000 so'm ($19)",
        "stars_label": "1,000 ⭐"
    },
    "365": {
        "days": 365,
        "price_uzs": 799000,
        "stars": 3000,
        "label": "1 Yillik",
        "price_label": "799,000 so'm ($62)",
        "stars_label": "3,000 ⭐"
    },
}

LEGAL_DISCLAIMER_WARNING = (
    f"{ce('WARN')} <b>OGOHLANTIRISH & OMMAVIY OFERTA (DISCLAIMER):</b>\n"
    f"Barcha raqamli litsenziyalar, promo-kodlar va mahsulotlar promo-aksiyalar hamda reseller dasturlari "
    f"doirasida taqdim etiladi. Agar promo-kod muddati o'tgan (expired) bo'lsa, uchinchi tomon platformasi (CapCut) "
    f"tomonidan rad etilsa yoki mintaqaviy cheklovga uchrasa — ma'muriyat javobgar emas va mablag' mutlaqo qaytarilmaydi (NO REFUNDS). "
    f"Xarid qilish orqali siz ushbu shartlarga o'z ixtiyoringiz bilan 100% to'liq rozilik bildirasiz va keyinchalik hech qanday e'tiroz yoki da'vo qilmaysiz."
)

def generate_capcut_license_key() -> str:
    """Noyob CapCut Pro litsenziya kalitini generatsiya qilish"""
    raw = uuid.uuid4().hex.upper()
    return f"CAPCUT-PRO-{raw[:4]}-{raw[4:8]}-{raw[8:12]}"

def get_capcut_menu_text(user_id: int, lang: str = "uz") -> str:
    """CapCut Pro sotuv sahifasi matni"""
    bal = db.get_user_balance(user_id)
    sub = db.get_user_capcut_subscription(user_id)
    
    sub_status = (
        f"{ce('CROWN')} <b>Sizda faol CapCut Pro mavjud!</b>\n"
        f"{ce('CALENDAR')} Tugash muddati: <code>{sub.get('expires_at')}</code>\n"
        f"{ce('KEY')} Litsenziya: <code>{sub.get('license_key', 'Faol')}</code>\n\n"
    ) if sub else ""

    text = (
        f"{ce('CAPCUT_LOGO')} <b>CapCut Pro — Rasmiy Pullik Litsenziya Markazi</b>\n\n"
        f"{sub_status}"
        f"CapCut Pro bilan kompyuter va telefoningizda professional darajada video montaj qiling:\n\n"
        f"{ce('GEMINI')} <b>Pro Imkoniyatlar:</b>\n"
        f"• {ce('FLUX')} 10,000+ VIP effektlar, animatsiyalar va filtrlar\n"
        f"• {ce('AUDIO')} Litsenziyalangan mualliflik huquqisiz audio kutubxona\n"
        f"• {ce('BOT')} AI Avtomatik Subtitrlar va Avto-Kesish\n"
        f"• {ce('VIDEO')} 4K 60FPS eksport va Suv belgisiz (No Watermark)\n"
        f"• {ce('LIGHTNING')} Cloud Storage va Tezkor renderlash\n\n"
        f"{ce('TON')} <b>Rasmiy Tariflar:</b>\n"
        f"• {ce('CALENDAR')} <b>1 Oylik:</b> <code>99,000 so'm</code> ($8) yoki {ce('STAR')} 400 Stars <i>(NO REFUNDS)</i>\n"
        f"• {ce('CALENDAR')} <b>3 Oylik:</b> <code>249,000 so'm</code> ($19) yoki {ce('STAR')} 1,000 Stars <i>(16% tejash, NO REFUNDS)</i>\n"
        f"• {ce('CALENDAR')} <b>1 Yillik:</b> <code>799,000 so'm</code> ($62) yoki {ce('STAR')} 3,000 Stars <i>(33% tejash, NO REFUNDS)</i>\n\n"
        f"{ce('MONEY')} <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
        f"<i>Xarid qilganingizdan so'ng hisobingizga darhol litsenziya kaliti taqdim etiladi!</i>\n\n"
        f"{LEGAL_DISCLAIMER_WARNING}"
    )
    return text

def get_capcut_pro_keyboard(user_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """CapCut Pro sotish menyusi tugmalari"""
    buttons = [
        [
            InlineKeyboardButton("💳 1 Oylik (99,000 so'm)", callback_data="capcut_buy_30"),
            InlineKeyboardButton("⭐ 400 Stars", callback_data="capcut_stars_30")
        ],
        [
            InlineKeyboardButton("💳 3 Oylik (249,000 so'm)", callback_data="capcut_buy_90"),
            InlineKeyboardButton("⭐ 1,000 Stars", callback_data="capcut_stars_90")
        ],
        [
            InlineKeyboardButton("💳 1 Yillik (799,000 so'm)", callback_data="capcut_buy_365"),
            InlineKeyboardButton("⭐ 3,000 Stars", callback_data="capcut_stars_365")
        ],
        [
            InlineKeyboardButton("🔑 Mening Obunam", callback_data="capcut_my_status"),
            InlineKeyboardButton("💰 Hisobni To'ldirish", callback_data="menu_wallet")
        ],
        [
            InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def purchase_capcut_pro(tg_user_id: int, plan_key: str) -> dict:
    """CapCut Pro obunasini balansdan sotib olish va bazada faollashtirish"""
    plan = CAPCUT_PRICES.get(plan_key)
    if not plan:
        return {"ok": False, "error": "Noto'g'ri tarif tanlandi!"}

    price_uzs = plan["price_uzs"]
    days = plan["days"]

    # Litsenziya kaliti yaratish
    license_key = generate_capcut_license_key()

    # Balansdan pul yechish va xaridni qayd etish (atomik)
    rec_res = db.record_user_purchase(
        tg_user_id,
        item_type="capcut_pro",
        item_name=f"CapCut Pro {plan['label']}",
        price_uzs=price_uzs,
        payload=license_key
    )
    if not rec_res.get("ok"):
        return rec_res

    # Bazada obunani saqlash / uzaytirish
    sub_res = db.add_capcut_subscription(
        tg_user_id=tg_user_id,
        plan_days=days,
        price_uzs=price_uzs,
        license_key=license_key
    )

    new_bal = rec_res.get("new_balance", db.get_user_balance(tg_user_id))

    return {
        "ok": True,
        "plan_label": plan["label"],
        "price_label": plan["price_label"],
        "days": days,
        "license_key": license_key,
        "expires_at": sub_res.get("expires_at", f"{days} kun"),
        "new_balance": new_bal
    }


def activate_capcut_pro_stars(tg_user_id: int, plan_key: str, stars_amount: int = 0) -> dict:
    """CapCut Pro obunasini Telegram Stars to'lovi orqali faollashtirish"""
    plan = CAPCUT_PRICES.get(plan_key)
    if not plan:
        return {"ok": False, "error": "Noto'g'ri tarif tanlandi!"}

    days = plan["days"]
    license_key = generate_capcut_license_key()

    sub_res = db.add_capcut_subscription(
        tg_user_id=tg_user_id,
        plan_days=days,
        price_uzs=plan["price_uzs"],
        license_key=license_key
    )

    # user_purchases jadvaliga yozish (Stars orqali to'langan)
    conn = db.get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_purchases (tg_user_id, item_type, item_name, price_uzs, payload, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (tg_user_id, "capcut_pro_stars", f"CapCut Pro {plan['label']} ({stars_amount} ⭐)", 0, license_key))
            conn.commit()
        except Exception as e:
            print(f"record capcut stars purchase error: {e}")
        finally:
            conn.close()

    return {
        "ok": True,
        "plan_label": plan["label"],
        "days": days,
        "license_key": license_key,
        "expires_at": sub_res.get("expires_at", f"{days} kun")
    }
