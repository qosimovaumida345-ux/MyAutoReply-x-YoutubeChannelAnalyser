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
    """CapCut Pro sotuv sahifasi matni (5 ta tilda)"""
    bal = db.get_user_balance(user_id)
    sub = db.get_user_capcut_subscription(user_id)
    
    status_titles = {
        "uz": ("Sizda faol CapCut Pro mavjud!", "Tugash muddati:", "Litsenziya:"),
        "ru": ("У вас активен CapCut Pro!", "Срок действия:", "Лицензия:"),
        "en": ("You have an active CapCut Pro!", "Expires at:", "License:"),
        "es": ("¡Tienes CapCut Pro activo!", "Vencimiento:", "Licencia:"),
        "tr": ("Aktif CapCut Pro aboneliğiniz var!", "Bitiş tarihi:", "Lisans:")
    }
    st_active, st_exp, st_lic = status_titles.get(lang, status_titles["uz"])

    sub_status = (
        f"{ce('BRAND_CAPCUT')} <b>{st_active}</b>\n"
        f"{ce('CALENDAR')} {st_exp} <code>{sub.get('expires_at')}</code>\n"
        f"{ce('DEV_API_KEY')} {st_lic} <code>{sub.get('license_key', 'Active')}</code>\n\n"
    ) if sub else ""

    headers = {
        "uz": (
            f"{ce('BRAND_CAPCUT')} <b>CapCut Pro — Rasmiy Pullik Litsenziya Markazi</b>\n\n"
            f"{sub_status}"
            f"CapCut Pro bilan kompyuter va telefoningizda professional darajada video montaj qiling:\n\n"
            f"{ce('BRAND_CAPCUT')} <b>Pro Imkoniyatlar:</b>\n"
            f"• {ce('STATUS_LIGHTNING')} 10,000+ VIP effektlar, animatsiyalar va filtrlar\n"
            f"• {ce('MEDIA_AUDIO_MP3')} Litsenziyalangan mualliflik huquqisiz audio kutubxona\n"
            f"• {ce('MEDIA_AUTOPILOT')} AI Avtomatik Subtitrlar va Avto-Kesish\n"
            f"• {ce('MEDIA_VIDEO_FHD')} 4K 60FPS eksport va Suv belgisiz (No Watermark)\n"
            f"• {ce('STATUS_LIGHTNING')} Cloud Storage va Tezkor renderlash\n\n"
            f"{ce('TOOL_PRICE_TAG')} <b>Rasmiy Tariflar:</b>\n"
            f"• {ce('CALENDAR')} <b>1 Oylik:</b> <code>99,000 so'm</code> ($8) yoki {ce('PAY_STARS')} 400 Stars <i>(NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>3 Oylik:</b> <code>249,000 so'm</code> ($19) yoki {ce('PAY_STARS')} 1,000 Stars <i>(16% tejash, NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>1 Yillik:</b> <code>799,000 so'm</code> ($62) yoki {ce('PAY_STARS')} 3,000 Stars <i>(33% tejash, NO REFUNDS)</i>\n\n"
            f"{ce('BTN_WALLET')} <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"<i>Xarid qilganingizdan so'ng hisobingizga darhol litsenziya kaliti taqdim etiladi!</i>\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        ),
        "ru": (
            f"{ce('BRAND_CAPCUT')} <b>CapCut Pro — Официальный Центр Лицензий</b>\n\n"
            f"{sub_status}"
            f"Редактируйте видео на профессиональном уровне на ПК и смартфонах с CapCut Pro:\n\n"
            f"{ce('BRAND_CAPCUT')} <b>Pro Возможности:</b>\n"
            f"• {ce('STATUS_LIGHTNING')} 10,000+ VIP эффектов, анимаций и фильтров\n"
            f"• {ce('MEDIA_AUDIO_MP3')} Лицензированная аудиотека без авторских прав\n"
            f"• {ce('MEDIA_AUTOPILOT')} ИИ автоматические субтитры и умная нарезка\n"
            f"• {ce('MEDIA_VIDEO_FHD')} Экспорт 4K 60FPS без водяного знака (No Watermark)\n"
            f"• {ce('STATUS_LIGHTNING')} Облачное хранилище и быстрый рендеринг\n\n"
            f"{ce('TOOL_PRICE_TAG')} <b>Официальные тарифы:</b>\n"
            f"• {ce('CALENDAR')} <b>1 Месяц:</b> <code>99,000 сум</code> ($8) или {ce('PAY_STARS')} 400 Stars <i>(NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>3 Месяца:</b> <code>249,000 сум</code> ($19) или {ce('PAY_STARS')} 1,000 Stars <i>(Скидка 16%, NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>1 Год:</b> <code>799,000 сум</code> ($62) или {ce('PAY_STARS')} 3,000 Stars <i>(Скидка 33%, NO REFUNDS)</i>\n\n"
            f"{ce('BTN_WALLET')} <b>Ваш баланс:</b> <code>{bal:,} сум</code>\n\n"
            f"<i>После покупки лицензионный ключ будет выдан мгновенно!</i>\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        ),
        "en": (
            f"{ce('BRAND_CAPCUT')} <b>CapCut Pro — Official License Center</b>\n\n"
            f"{sub_status}"
            f"Edit professional-grade videos on desktop and mobile with CapCut Pro:\n\n"
            f"{ce('BRAND_CAPCUT')} <b>Pro Features:</b>\n"
            f"• {ce('STATUS_LIGHTNING')} 10,000+ VIP effects, transitions & filters\n"
            f"• {ce('MEDIA_AUDIO_MP3')} Royalty-free licensed audio library\n"
            f"• {ce('MEDIA_AUTOPILOT')} AI Auto-Captions & Smart Auto-Cut\n"
            f"• {ce('MEDIA_VIDEO_FHD')} 4K 60FPS export without watermark\n"
            f"• {ce('STATUS_LIGHTNING')} Cloud storage & ultra-fast rendering\n\n"
            f"{ce('TOOL_PRICE_TAG')} <b>Official Plans:</b>\n"
            f"• {ce('CALENDAR')} <b>1 Month:</b> <code>99,000 UZS</code> ($8) or {ce('PAY_STARS')} 400 Stars <i>(NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>3 Months:</b> <code>249,000 UZS</code> ($19) or {ce('PAY_STARS')} 1,000 Stars <i>(Save 16%, NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>1 Year:</b> <code>799,000 UZS</code> ($62) or {ce('PAY_STARS')} 3,000 Stars <i>(Save 33%, NO REFUNDS)</i>\n\n"
            f"{ce('BTN_WALLET')} <b>Your balance:</b> <code>{bal:,} UZS</code>\n\n"
            f"<i>License key will be delivered instantly after purchase!</i>\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        ),
        "es": (
            f"{ce('BRAND_CAPCUT')} <b>CapCut Pro — Centro Oficial de Licencias</b>\n\n"
            f"{sub_status}"
            f"Edita videos de calidad profesional en PC y móviles con CapCut Pro:\n\n"
            f"{ce('BRAND_CAPCUT')} <b>Funciones Pro:</b>\n"
            f"• {ce('STATUS_LIGHTNING')} Más de 10,000 efectos VIP, filtros y transiciones\n"
            f"• {ce('MEDIA_AUDIO_MP3')} Biblioteca de audio sin derechos de autor\n"
            f"• {ce('MEDIA_AUTOPILOT')} Subtítulos automáticos con IA y autocorte\n"
            f"• {ce('MEDIA_VIDEO_FHD')} Exportación 4K a 60FPS sin marca de agua\n"
            f"• {ce('STATUS_LIGHTNING')} Almacenamiento en la nube y renderizado veloz\n\n"
            f"{ce('TOOL_PRICE_TAG')} <b>Planes Oficiales:</b>\n"
            f"• {ce('CALENDAR')} <b>1 Mes:</b> <code>99,000 UZS</code> ($8) o {ce('PAY_STARS')} 400 Stars <i>(NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>3 Meses:</b> <code>249,000 UZS</code> ($19) o {ce('PAY_STARS')} 1,000 Stars <i>(Ahorra 16%, NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>1 Año:</b> <code>799,000 UZS</code> ($62) o {ce('PAY_STARS')} 3,000 Stars <i>(Ahorra 33%, NO REFUNDS)</i>\n\n"
            f"{ce('BTN_WALLET')} <b>Tu saldo:</b> <code>{bal:,} UZS</code>\n\n"
            f"<i>¡La clave de activación se entrega al instante tras la compra!</i>\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        ),
        "tr": (
            f"{ce('BRAND_CAPCUT')} <b>CapCut Pro — Resmi Lisans Merkezi</b>\n\n"
            f"{sub_status}"
            f"CapCut Pro ile bilgisayarınızda ve telefonunuzda profesyonel videolar oluşturun:\n\n"
            f"{ce('BRAND_CAPCUT')} <b>Pro Özellikler:</b>\n"
            f"• {ce('STATUS_LIGHTNING')} 10,000+ VIP efekt, animasyon ve filtre\n"
            f"• {ce('MEDIA_AUDIO_MP3')} Telifsiz lisanslı müzik kütüphanesi\n"
            f"• {ce('MEDIA_AUTOPILOT')} Yapay zeka ile otomatik altyazı ve kesim\n"
            f"• {ce('MEDIA_VIDEO_FHD')} Filigransız 4K 60FPS video dışa aktarma\n"
            f"• {ce('STATUS_LIGHTNING')} Bulut depolama ve yüksek hızlı işleme\n\n"
            f"{ce('TOOL_PRICE_TAG')} <b>Resmi Tarifeler:</b>\n"
            f"• {ce('CALENDAR')} <b>1 Aylık:</b> <code>99,000 UZS</code> ($8) veya {ce('PAY_STARS')} 400 Stars <i>(NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>3 Aylık:</b> <code>249,000 UZS</code> ($19) veya {ce('PAY_STARS')} 1,000 Stars <i>(%16 tasarruf, NO REFUNDS)</i>\n"
            f"• {ce('CALENDAR')} <b>1 Yıllık:</b> <code>799,000 UZS</code> ($62) veya {ce('PAY_STARS')} 3,000 Stars <i>(%33 tasarruf, NO REFUNDS)</i>\n\n"
            f"{ce('BTN_WALLET')} <b>Bakiyeniz:</b> <code>{bal:,} UZS</code>\n\n"
            f"<i>Satın aldıktan hemen sonra lisans anahtarı teslim edilir!</i>\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        )
    }
    return headers.get(lang, headers["uz"])

def get_capcut_pro_keyboard(user_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """CapCut Pro sotish menyusi tugmalari (5 ta tilda)"""
    lbls = {
        "uz": ("1 Oylik (99,000 so'm)", "3 Oylik (249,000 so'm)", "1 Yillik (799,000 so'm)", "Mening Obunam", "Hisobni To'ldirish", "Bosh Menyu"),
        "ru": ("1 Месяц (99,000 сум)", "3 Месяца (249,000 сум)", "1 Год (799,000 сум)", "Моя Подписка", "Пополнить Баланс", "Главное Меню"),
        "en": ("1 Month (99,000 UZS)", "3 Months (249,000 UZS)", "1 Year (799,000 UZS)", "My Subscription", "Top Up Balance", "Main Menu"),
        "es": ("1 Mes (99,000 UZS)", "3 Meses (249,000 UZS)", "1 Año (799,000 UZS)", "Mi Suscripción", "Recargar Saldo", "Menú Principal"),
        "tr": ("1 Aylık (99,000 UZS)", "3 Aylık (249,000 UZS)", "1 Yıllık (799,000 UZS)", "Aboneliğim", "Bakiye Yükle", "Ana Menü")
    }
    p1, p3, py, my_sub, top_up, b_home = lbls.get(lang, lbls["uz"])

    buttons = [
        [
            InlineKeyboardButton(f"{ce('PAY_HUMO_UZCARD')} {p1}", callback_data="capcut_buy_30"),
            InlineKeyboardButton(f"{ce('PAY_STARS')} 400 Stars", callback_data="capcut_stars_30")
        ],
        [
            InlineKeyboardButton(f"{ce('PAY_HUMO_UZCARD')} {p3}", callback_data="capcut_buy_90"),
            InlineKeyboardButton(f"{ce('PAY_STARS')} 1,000 Stars", callback_data="capcut_stars_90")
        ],
        [
            InlineKeyboardButton(f"{ce('PAY_HUMO_UZCARD')} {py}", callback_data="capcut_buy_365"),
            InlineKeyboardButton(f"{ce('PAY_STARS')} 3,000 Stars", callback_data="capcut_stars_365")
        ],
        [
            InlineKeyboardButton(f"{ce('DEV_API_KEY')} {my_sub}", callback_data="capcut_my_status"),
            InlineKeyboardButton(f"{ce('BTN_WALLET')} {top_up}", callback_data="menu_wallet")
        ],
        [
            InlineKeyboardButton(f"{ce('BTN_HOME')} {b_home}", callback_data="back_main")
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
