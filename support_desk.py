"""
Smart Gemini AI Support Desk & Live Admin Hand-off Bridge
Ko'p tilli (uz, ru, en, es, tr) 4 xil rol bo'yicha aqlli AI maslahatchi va
Admin bilan jonli 2 tomonlama xabarlashuv ko'prigi.
"""

import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import generate_with_fallback_async, OWNER_ID
import database as db
from custom_emojis import e, ce

logger = logging.getLogger(__name__)

SUPPORT_ROLES = {
    "developer": {
        "title": {
            "uz": f"{e('DEV_API_KEY')} Dasturchi / API Integrator",
            "ru": f"{e('DEV_API_KEY')} Разработчик / API",
            "en": f"{e('DEV_API_KEY')} Developer / API Integrator",
            "es": f"{e('DEV_API_KEY')} Desarrollador / API",
            "tr": f"{e('DEV_API_KEY')} Geliştirici / API Entegratörü"
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
            "uz": f"{ce('PAY_HUMO_UZCARD')} Xaridor / Mijoz",
            "ru": f"{ce('PAY_HUMO_UZCARD')} Покупатель / Клиент",
            "en": f"{ce('PAY_HUMO_UZCARD')} Buyer / Customer",
            "es": f"{ce('PAY_HUMO_UZCARD')} Comprador / Cliente",
            "tr": f"{ce('PAY_HUMO_UZCARD')} Alıcı / Müşteri"
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
            "uz": f"{ce('TOOL_PROMPT_PACK')} Yangi Boshlovchi",
            "ru": f"{ce('TOOL_PROMPT_PACK')} Новичок",
            "en": f"{ce('TOOL_PROMPT_PACK')} Beginner",
            "es": f"{ce('TOOL_PROMPT_PACK')} Principiante",
            "tr": f"{ce('TOOL_PROMPT_PACK')} Yeni Başlayan"
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
            "uz": f"{ce('BTN_SUPPORT')} Ko'p So'raladigan Savollar",
            "ru": f"{ce('BTN_SUPPORT')} Часто Задаваемые Вопросы",
            "en": f"{ce('BTN_SUPPORT')} Frequently Asked Questions",
            "es": f"{ce('BTN_SUPPORT')} Preguntas Frecuentes",
            "tr": f"{ce('BTN_SUPPORT')} Sıkça Sorulan Sorular"
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
    "uz": f"{ce('WAIT')} <b>Xabaringiz adminga yetkazildi!</b>\n\nIltimos, biroz kuting. Admin tez orada sizga bevosita javob yozadi. Javob xabari shu yerda keladi.",
    "ru": f"{ce('WAIT')} <b>Ваше сообщение передано администратору!</b>\n\nПожалуйста, подождите немного. Администратор скоро свяжется с вами напрямую.",
    "en": f"{ce('WAIT')} <b>Your message has been forwarded to the administrator!</b>\n\nPlease wait a moment. The administrator will reply to you directly very shortly.",
    "es": f"{ce('WAIT')} <b>¡Su mensaje ha sido enviado al administrador!</b>\n\nPor favor espere un momento. El administrador le responderá directamente muy pronto.",
    "tr": f"{ce('WAIT')} <b>Mesajınız yöneticiye iletildi!</b>\n\nLütfen biraz bekleyin. Yönetici çok yakında size doğrudan yanıt verecektir."
}

def get_support_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Yordam markazi bosh sahifasi (Rol tanlash)"""
    rows = []
    for role_key, data in SUPPORT_ROLES.items():
        title = data["title"].get(lang, data["title"]["uz"])
        rows.append([InlineKeyboardButton(title, callback_data=f"supp_role_{role_key}")])
    
    back_text = f"{ce('BTN_BACK')} Orqaga" if lang == "uz" else (f"{ce('BTN_BACK')} Назад" if lang == "ru" else f"{ce('BTN_BACK')} Back")
    rows.append([InlineKeyboardButton(back_text, callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

def get_role_view_keyboard(role_key: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Tanlangan rol bo'yicha savol berish yoki Adminga bog'lanish tugmalari"""
    admin_call_txt = {
        "uz": f"{ce('BTN_SETTINGS')} Admin bilan jonli bog'lanish",
        "ru": f"{ce('BTN_SETTINGS')} Живая связь с админом",
        "en": f"{ce('BTN_SETTINGS')} Live Chat with Admin",
        "es": f"{ce('BTN_SETTINGS')} Chatear con Administrador",
        "tr": f"{ce('BTN_SETTINGS')} Yönetici ile Canlı Sohbet"
    }.get(lang, f"{ce('BTN_SETTINGS')} Admin bilan jonli bog'lanish")

    back_txt = f"{ce('BTN_BACK')} Bo'limlar" if lang == "uz" else (f"{ce('BTN_BACK')} Разделы" if lang == "ru" else f"{ce('BTN_BACK')} Categories")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{ce('DEV_API_DOCS')} Savol berish (AI)", callback_data=f"supp_ask_{role_key}")],
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
        import asyncio
        res = await asyncio.wait_for(generate_with_fallback_async(prompt), timeout=25)
        if res and hasattr(res, "text") and res.text:
            return res.text.strip()
        elif isinstance(res, str) and res.strip():
            return res.strip()
        raise ValueError("AI bo'sh javob qaytardi")
    except asyncio.TimeoutError:
        logger.warning(f"Support AI javob berish vaqti tugadi (25s timeout): {user_question[:50]}")
        timeout_msg = {
            "uz": "⏳ Sun'iy intellekt xizmatida kutish vaqti uzaydi (server band). Murojaatingiz adminga yetkazildi!",
            "ru": "⏳ Время ответа ИИ превысило лимит (сервер перегружен). Ваш запрос передан администратору!",
            "en": "⏳ AI response timed out (server busy). Your request has been forwarded to the administrator!"
        }
        return timeout_msg.get(lang, timeout_msg["uz"])
    except Exception as e:
        logger.error(f"Support AI xatosi ({type(e).__name__}): {e}")
        err_str = str(e).lower()
        if any(term in err_str for term in ["429", "resourceexhausted", "quota", "rate limit", "rate_limit"]):
            rate_limit_msg = {
                "uz": "⚠️ Sun'iy intellekt xizmatida so'rovlar limiti oshdi (Rate Limit). Birozdan so'ng qayta urinib ko'ring yoki adminga murojaat qiling.",
                "ru": "⚠️ Превышен лимит запросов к ИИ (Rate Limit). Пожалуйста, повторите чуть позже или свяжитесь с администратором.",
                "en": "⚠️ AI service rate limit reached. Please try again shortly or contact support."
            }
            return rate_limit_msg.get(lang, rate_limit_msg["uz"])
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
    ticket_data = db.create_or_get_open_ticket(user_id, role_intent=role_key)
    ticket_id = ticket_data.get("id") if ticket_data else 1
    if ticket_id:
        try:
            db.add_support_message(ticket_id, sender_type="user", message_text=message_text)
        except Exception as db_err:
            logger.error(f"Support message save error: {db_err}")

    admin_text = (
        f"{ce('WARN')} <b>YANGI MUROJAAT #{ticket_id or 'NEW'}</b>\n\n"
        f"{ce('USER')} <b>Foydalanuvchi:</b> {user_fullname} ({username_str})\n"
        f"{ce('KEY')} <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"{ce('GLOBE')} <b>Til:</b> <code>{lang}</code>\n"
        f"{ce('SEO_TAG')} <b>Kategoriya:</b> <code>{role_key.upper()}</code>\n\n"
        f"{ce('COMMENTS')} <b>Xabar:</b>\n{message_text}"
    )

    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Javob berish", callback_data=f"adm_rep_ticket_{ticket_id}_{user_id}")]
    ])

    sent_ok = False
    if OWNER_ID:
        try:
            await app.send_message(
                chat_id=OWNER_ID,
                text=admin_text,
                reply_markup=admin_keyboard
            )
            sent_ok = True
        except Exception as e:
            logger.error(f"Adminga Pyrogram orqali xabar yuborishda xato: {e}")

        # Fallback via direct Bot API if Pyrogram fails
        if not sent_ok:
            try:
                import os, aiohttp
                bot_token = os.getenv("BOT_TOKEN", "")
                if bot_token:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": OWNER_ID,
                        "text": admin_text,
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": [
                                [{"text": "💬 Javob berish", "callback_data": f"adm_rep_ticket_{ticket_id}_{user_id}"}]
                            ]
                        }
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            data = await resp.json()
                            if data.get("ok"):
                                sent_ok = True
            except Exception as e2:
                logger.error(f"Adminga Bot API orqali xabar yuborishda xato: {e2}")

    return ticket_id
