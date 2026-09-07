"""
Smart Gemini AI Support Desk & Live Admin Hand-off Bridge
Ko'p tilli (uz, ru, en, es, tr) 4 xil rol bo'yicha aqlli AI maslahatchi va
Admin bilan jonli 2 tomonlama xabarlashuv ko'prigi.
"""

import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import generate_with_fallback_async, OWNER_ID
import database as db

logger = logging.getLogger(__name__)

SUPPORT_ROLES = {
    "developer": {
        "title": {
            "uz": "👨‍💻 Dasturchi / API Integrator",
            "ru": "👨‍💻 Разработчик / API",
            "en": "👨‍💻 Developer / API Integrator",
            "es": "👨‍💻 Desarrollador / API",
            "tr": "👨‍💻 Geliştirici / API Entegratörü"
        },
        "desc": {
            "uz": "API kalitlar, Reseller API, webhooklar va bot avtomatizatsiyasi.",
            "ru": "API ключи, Reseller API, вебхуки и автоматизация бота.",
            "en": "API keys, Reseller API, webhooks and bot automation.",
            "es": "Claves API, API de revendedor, webhooks y automatización.",
            "tr": "API anahtarları, Bayi API'si, webhooklar ve bot otomasyonu."
        },
        "system_role": "Sen tajribali dasturchi va tizim arxitektorisan. YouTube API, Reseller API, webhooklar va texnik sozlamalar bo'yicha aniq, to'liq va professional texnik javob ber."
    },
    "buyer": {
        "title": {
            "uz": "💳 Xaridor / Mijoz",
            "ru": "💳 Покупатель / Клиент",
            "en": "💳 Buyer / Customer",
            "es": "💳 Comprador / Cliente",
            "tr": "💳 Alıcı / Müşteri"
        },
        "desc": {
            "uz": "Balans to'ldirish, TON/Stars to'lovlari, xizmatlar va cheklar.",
            "ru": "Пополнение баланса, TON/Stars платежи, услуги и чеки.",
            "en": "Balance top-up, TON/Stars payments, services and vouchers.",
            "es": "Recarga de saldo, pagos en TON/Stars, servicios y cupones.",
            "tr": "Bakiye yükleme, TON/Stars ödemeleri, hizmetler ve çekler."
        },
        "system_role": "Sen xushmuomala mijozlar bo'limi mutaxassisisan. Xizmat tariflari, to'lov usullari (Stars, TON, CryptoPay) va xizmat kafolatlari bo'yicha tushunarli ma'lumot ber."
    },
    "new_user": {
        "title": {
            "uz": "🌱 Yangi Boshlovchi",
            "ru": "🌱 Новичок",
            "en": "🌱 Beginner",
            "es": "🌱 Principiante",
            "tr": "🌱 Yeni Başlayan"
        },
        "desc": {
            "uz": "Bot qanday ishlaydi, YouTube ulash, Instagram klonlash bo'yicha ko'rsatma.",
            "ru": "Как работает бот, подключение YouTube, клонирование Instagram.",
            "en": "How the bot works, connecting YouTube, Instagram cloning tutorial.",
            "es": "Cómo funciona el bot, conectar YouTube, tutorial de clonación de Instagram.",
            "tr": "Bot nasıl çalışır, YouTube bağlama, Instagram klonlama rehberi."
        },
        "system_role": "Sen sabrli murabbiysan. Botdan foydalanish bo'yicha yangi boshlovchilarga qadamma-qadam, sodda va rag'batlantiruvchi ko'rsatmalar ber."
    },
    "faq": {
        "title": {
            "uz": "❓ Ko'p So'raladigan Savollar",
            "ru": "❓ Часто Задаваемые Вопросы",
            "en": "❓ Frequently Asked Questions",
            "es": "❓ Preguntas Frecuentes",
            "tr": "❓ Sıkça Sorulan Sorular"
        },
        "desc": {
            "uz": "Tezkor javoblar, qoidalar va umumiy xavfsizlik.",
            "ru": "Быстрые ответы, правила и общая безопасность.",
            "en": "Instant answers, rules and general security.",
            "es": "Respuestas rápidas, reglas y seguridad general.",
            "tr": "Hızlı yanıtlar, kurallar ve genel güvenlik."
        },
        "system_role": "Sen bilimlar bazasi mutaxassisisan. Eng ko'p so'raladigan savollarga qisqa, aniq va lo'nda javob ber."
    }
}

WAITING_MESSAGES = {
    "uz": "⏳ **Xabaringiz adminga yetkazildi!**\n\nIltimos, biroz kuting. Admin tez orada sizga bevosita javob yozadi. Javob xabari shu yerda keladi.",
    "ru": "⏳ **Ваше сообщение передано администратору!**\n\nПожалуйста, подождите немного. Администратор скоро свяжется с вами напрямую.",
    "en": "⏳ **Your message has been forwarded to the administrator!**\n\nPlease wait a moment. The administrator will reply to you directly very shortly.",
    "es": "⏳ **¡Su mensaje ha sido enviado al administrador!**\n\nPor favor espere un momento. El administrador le responderá directamente muy pronto.",
    "tr": "⏳ **Mesajınız yöneticiye iletildi!**\n\nLütfen biraz bekleyin. Yönetici çok yakında size doğrudan yanıt verecektir."
}

def get_support_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Yordam markazi bosh sahifasi (Rol tanlash)"""
    rows = []
    for role_key, data in SUPPORT_ROLES.items():
        title = data["title"].get(lang, data["title"]["uz"])
        rows.append([InlineKeyboardButton(title, callback_data=f"supp_role_{role_key}")])
    
    back_text = "⬅️ Orqaga" if lang == "uz" else ("⬅️ Назад" if lang == "ru" else "⬅️ Back")
    rows.append([InlineKeyboardButton(back_text, callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def get_role_view_keyboard(role_key: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Tanlangan rol bo'yicha savol berish yoki Adminga bog'lanish tugmalari"""
    admin_call_txt = {
        "uz": "👤 Admin bilan jonli bog'lanish",
        "ru": "👤 Живая связь с админом",
        "en": "👤 Live Chat with Admin",
        "es": "👤 Chatear con Administrador",
        "tr": "👤 Yönetici ile Canlı Sohbet"
    }.get(lang, "👤 Admin bilan jonli bog'lanish")

    back_txt = "⬅️ Bo'limlar" if lang == "uz" else ("⬅️ Разделы" if lang == "ru" else "⬅️ Categories")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✍️ Savol berish (AI)", callback_data=f"supp_ask_{role_key}")],
        [InlineKeyboardButton(admin_call_txt, callback_data=f"supp_live_{role_key}")],
        [InlineKeyboardButton(back_txt, callback_data="support_desk_root")]
    ])

async def generate_support_answer(user_question: str, role_key: str, lang: str = "uz") -> str:
    """Gemini AI orqali rolga xos professional javob tayyorlash"""
    role_info = SUPPORT_ROLES.get(role_key, SUPPORT_ROLES["faq"])
    system_role = role_info["system_role"]

    prompt = f"""
{system_role}
Foydalanuvchiga quyidagi tilda javob ber: '{lang}'.
Javobing juda do'stona, aniq va amaliy bo'lsin. Kerakli joylarda emoji va markdown formatlashdan foydalan.

Foydalanuvchi savoli:
\"\"\"{user_question}\"\"\"
"""
    try:
        res = await generate_with_fallback_async(prompt)
        return res.text.strip()
    except Exception as e:
        logger.error(f"Support AI xatosi: {e}")
        err_msg = {
            "uz": "Kechirasiz, sun'iy intellekt xizmati hozirda band. Iltimos, admin bilan to'g'ridan-to'g'ri bog'laning!",
            "ru": "Извините, сервис ИИ сейчас перегружен. Пожалуйста, свяжитесь напрямую с администратором!",
            "en": "Sorry, AI assistant is currently busy. Please contact the administrator directly!"
        }
        return err_msg.get(lang, err_msg["uz"])

async def forward_to_admin(app, user, role_key: str, message_text: str, lang: str = "uz") -> int:
    """
    Foydalanuvchi murojaatini Adminga (OWNER_ID) yuboradi va
    [Javob berish 💬] tugmasini qo'shadi.
    Bazaga yangi chipta (ticket) va xabarni saqlaydi.
    """
    user_id = user.id
    user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Noma'lum"
    username_str = f"@{user.username}" if user.username else "Username yo'q"

    # Bazada chipta yaratamiz
    ticket_id = db.create_support_ticket(user_id, role_intent=role_key)
    if ticket_id:
        db.add_support_message(ticket_id, sender_type="user", message_text=message_text)

    admin_text = (
        f"🚨 **YANGI MUROJAAT #{ticket_id or 'NEW'}**\n\n"
        f"👤 **Foydalanuvchi:** {user_fullname} ({username_str})\n"
        f"🆔 **Telegram ID:** `{user_id}`\n"
        f"🌐 **Til:** `{lang}`\n"
        f"🏷 **Kategoriya:** `{role_key.upper()}`\n\n"
        f"💬 **Xabar:**\n{message_text}"
    )

    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Javob berish", callback_data=f"adm_rep_ticket_{ticket_id}_{user_id}")]
    ])

    try:
        await app.send_message(
            chat_id=OWNER_ID,
            text=admin_text,
            reply_markup=admin_keyboard
        )
    except Exception as e:
        logger.error(f"Adminga xabar yuborishda xato: {e}")

    return ticket_id
