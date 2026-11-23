"""
Mono Deck Studio - Store Channel Automation Service
Kunlik takrorlanmaydigan turli xil xabarlar, custom emojilar rotatsiyasi,
restock, live xaridlar, aksiyalar va konkurslar boshqaruvchisi.
"""

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import json
import logging
import os
import random
from datetime import datetime
from typing import Optional
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from config import STORE_CHANNEL, VIP_PRICE_UZS, VIP_PRICE_STARS, BRAND_NAME, get_bot_username, extract_username_from_me
from custom_emojis import ce, get_brand_emoji
from database import (
    create_channel_contest,
    create_flash_sale,
    create_fast_drop_promo,
    get_wishlist_users_for_product,
    mark_wishlist_notified,
    get_abandoned_carts_to_notify,
    mark_abandoned_cart_notified,
)

logger = logging.getLogger("store_channel_service")

_userbot_client: Optional[Client] = None


def set_userbot_client(client: Client):
    """Userbot clientni global saqlash — custom emojilar userbot orqali kanalga yuboriladi."""
    global _userbot_client
    _userbot_client = client
    logger.info("Store channel service: Userbot client o'rnatildi.")


def _resolve_active_bot_username(client: Optional[Client] = None) -> str:
    bot_me = getattr(client, "me", None) if client else None
    if bot_me:
        return extract_username_from_me(bot_me)
    return (get_bot_username() or "monodeck_app").lstrip("@")


async def _send_channel_message(bot_client: Client, text: str, reply_markup=None) -> Optional[int]:
    if not STORE_CHANNEL:
        return None

    if _userbot_client:
        try:
            msg = await _userbot_client.send_message(
                STORE_CHANNEL, text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            return msg.id if msg else None
        except Exception as ub_err:
            logger.warning(f"Userbot orqali kanalga yuborishda xato: {ub_err}, bot ga fallback...")

    try:
        msg = await bot_client.send_message(STORE_CHANNEL, text, reply_markup=reply_markup)
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
    order_id: Optional[str] = None,
) -> bool:
    if not STORE_CHANNEL:
        return False

    try:
        raw_name = (user_name or "Foydalanuvchi").strip()
        if raw_name.startswith("@") and len(raw_name) > 3:
            masked_name = f"@{raw_name[1]}***{raw_name[-1]}"
        elif len(raw_name) > 2:
            masked_name = f"{raw_name[0]}***{raw_name[-1]}"
        else:
            masked_name = "Mijoz"

        bot_username = _resolve_active_bot_username(client)
        order_str = f"#{order_id}" if order_id else f"#{random.randint(10000, 99999)}"

        text = (
            f"{ce('CART')} <b>YANGI XARID AMALGA OSHIRILDI!</b>\n\n"
            f"{ce('USER')} <b>Xaridor:</b> <code>{masked_name}</code>\n"
            f"{get_brand_emoji(product_name)} <b>Mahsulot:</b> <b>{product_name}</b>\n"
            f"{ce('MONEY')} <b>Narxi:</b> <code>{price_uzs:,} so'm</code>\n"
            f"{ce('KEY')} <b>Buyurtma ID:</b> <code>{order_str}</code>\n"
            f"{ce('SUCCESS')} <b>Holat:</b> Muvaffaqiyatli yetkazildi\n\n"
            f"{ce('ROCKET')} <i>Mono Deck Studio orqali 24/7 tezkor va kafolatli xarid!</i>"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{ce('BTN_SERVICES')} Xarid qilish", url=f"https://t.me/{bot_username}?start=store")],
            [InlineKeyboardButton(f"{ce('MEDIA_AUTOPILOT')} Mono Deck Studio", url=f"https://t.me/{bot_username}")],
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        return True
    except Exception as err:
        logger.error(f"broadcast_channel_purchase xatosi: {err}")
        return False


# ==================== RESTOCK E'LONLARI ====================

async def send_channel_restock_alert(client: Client, items_summary: Optional[str] = None) -> bool:
    if not STORE_CHANNEL:
        return False

    try:
        bot_username = _resolve_active_bot_username(client)
        if not items_summary:
            items_summary = (
                f"• {ce('BRAND_CAPCUT')} <b>CapCut Pro (1-12 oylik)</b> — Zaxira to'ldirildi!\n"
                f"• {ce('CHATGPT')} <b>ChatGPT Plus / OpenAI API</b> — Yangi kalitlar keldi!\n"
                f"• {ce('GEMINI')} <b>Gemini Flash & Pro API</b> — Arzon narxlarda tayyor!\n"
                f"• {ce('STAR')} <b>Telegram Stars & Mystery Cases</b> — Jonli drop tizimi!\n"
                f"• {ce('VIP')} <b>Mono Deck Studio VIP ({VIP_PRICE_UZS:,} UZS)</b> — Qayta ochiq!"
            )

        text = (
            f"{ce('FIRE')} <b>DO'KON ZAXIRASI YANGILANDI!</b>\n\n"
            f"{ce('MONEY')} Hurmatli obunachilar, <b>Mono Deck Studio</b> do'koniga yangi raqamli xizmatlar kelib tushdi:\n\n"
            f"{items_summary}\n\n"
            f"{ce('ROCKET')} <b>Barcha mahsulotlar soniyalarda avtomatik yetkaziladi!</b>"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{ce('BTN_SERVICES')} Do'konga kirish", url=f"https://t.me/{bot_username}?start=store")],
            [InlineKeyboardButton(f"{ce('PAY_VIP_CROWN')} VIP Tarif ({VIP_PRICE_UZS:,} UZS)", url=f"https://t.me/{bot_username}?start=vip")],
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        return True
    except Exception as err:
        logger.error(f"send_channel_restock_alert xatosi: {err}")
        return False


# ==================== XILMA-XIL KUNLIK POST SHABLONLARI ====================

DAILY_OPENERS = [
    ("MORNING_BOOST", "☀️ <b>Yangi kun, yangi kontent imkoniyatlari!</b>"),
    ("CREATOR_TIP", "💡 <b>Bugungi ijodkor maslahati & imkoniyat:</b>"),
    ("STUDIO_UPDATE", "⚡ <b>Mono Deck Studio — Kunlik Tavsiya:</b>"),
    ("PRO_SPOTLIGHT", "🎬 <b>YouTube & Reels Avtomatlashtirish:</b>"),
    ("GROWTH_EDGE", "📈 <b>Kanalingizni keyingi bosqichga olib chiqing:</b>"),
    ("SMART_WORKFLOW", "🤖 <b>Vaqtingizni tejaydigan aqlli tizim:</b>"),
]

DAILY_CLOSERS = [
    "👇 <i>Hoziroq sinab ko'ring — hammasi 1 klikda:</i>",
    "🔥 <i>Web Studio (monodeck.site) va Telegram bot sinxron ishlaydi:</i>",
    "⚙️ <i>Avtomatik tizim 24/7 xizmatingizda:</i>",
    "💎 <i>O'zbekistonlik kontent-meykerlar tanlovi:</i>",
]

# 14 ta mutlaqo har xil mavzu, har xil format va alohida custom emoji to'plami
PROMO_TEMPLATES = [
    {
        "id": "autopost_watermark",
        "emoji_theme": ("VIDEO", "SHIELD", "ROCKET"),
        "title": "AVTO-POSTING + WATERMARK TOZALASH!",
        "body": (
            f"{ce('VIDEO')} <b>YouTube Shorts ga blind emas — oldindan ko'rib post qiling!</b>\n\n"
            f"{ce('SHIELD')} Yuklashdan oldin har bir videoni saytda namuna sifatida tomosha qilasiz\n"
            f"{ce('LIGHTNING')} Videoda TikTok/Reels logosi bo'lsa, server avtomatik aniqlab tozalaydi\n"
            f"{ce('ROCKET')} GitHub 7 GB RAM Cloud Worker orqali tez va sifatli yuklanadi"
        ),
        "btn_text": "Auto-Post ni ochish",
        "start_param": "studio",
    },
    {
        "id": "vip_studio",
        "emoji_theme": ("VIP", "CHECK", "MONEY"),
        "title": "MONO DECK STUDIO VIP — CHEKSIZ QUVVAT!",
        "body": (
            f"{ce('VIP')} <b>Kunlik limitlarsiz professional ishlang!</b>\n\n"
            f"{ce('CHECK')} Cheksiz video yuklash (4K) va MP3 ajratish\n"
            f"{ce('CHECK')} 24/7 Priority Queue navbatsiz video qayta ishlash\n"
            f"{ce('CHECK')} Barcha xizmatlardan keshbek va yopiq aksiyalar\n\n"
            f"{ce('MONEY')} <b>Narxi:</b> <code>{VIP_PRICE_UZS:,} so'm</code> yoki {VIP_PRICE_STARS} Stars"
        ),
        "btn_text": "VIP Tarifni ko'rish",
        "start_param": "vip",
    },
    {
        "id": "autostream_247",
        "emoji_theme": ("MEDIA_AUTOPILOT", "STATUS_LOADING", "CHANNEL"),
        "title": "24/7 JONLI EFIR (AUTOSTREAM) CLOUD!",
        "body": (
            f"{ce('MEDIA_AUTOPILOT')} <b>Kompyuteringizni yoqmasdan YouTube Live qiling!</b>\n\n"
            f"{ce('STATUS_LOADING')} Musiqa, lo-fi yoki tayyor videoni 24 soat uzluksiz efirga uzating\n"
            f"{ce('CHANNEL')} Soatlik tomosha (watch hours) va obunachilarni tabiiy oshiring\n"
            f"{ce('SUCCESS')} Barcha oqim bulutli serverda ishlaydi"
        ),
        "btn_text": "Autostream ni boshlash",
        "start_param": "stream",
    },
    {
        "id": "cases_upgrader",
        "emoji_theme": ("GIFT", "WHEEL", "TROPHY"),
        "title": "MYSTERY CASES & GIFT UPGRADER!",
        "body": (
            f"{ce('GIFT')} <b>Rasmiy Telegram sovg'alari va Premium yutib oling!</b>\n\n"
            f"{ce('WHEEL')} Gift Upgrader da kursor g'ildiragi orqali 1.5x dan 100x gacha ko'taring\n"
            f"{ce('TROPHY')} Yutgan sovg'angizni Telegram profilingizga chiqaring yoki 75% UZS ga soting\n"
            f"{ce('SPARKLES')} Kunlik 7 kunlik Streak bonusini olishni unutmang"
        ),
        "btn_text": "Keyslarni ochish",
        "start_param": "cases",
    },
    {
        "id": "ai_seo_pack",
        "emoji_theme": ("SEO_TAG", "BOT", "CHART_GROWTH"),
        "title": "AI YOUTUBE SEO & VIRAL SKRIPTLAR!",
        "body": (
            f"{ce('SEO_TAG')} <b>Videolaringiz tavsiya (Recommendations) ga chiqmayaptimi?</b>\n\n"
            f"{ce('BOT')} Sun'iy intellekt kanalingiz mavzusiga mos High-CTR sarlavha va teglar yozadi\n"
            f"{ce('TOOL_CHART_GROWTH')} Raqobatchi videolarni /spy orqali soniyada tahlil qiling\n"
            f"{ce('CHECK')} Natija: ko'proq ko'rish va yuqori CTR"
        ),
        "btn_text": "AI SEO ni sinash",
        "start_param": "seo",
    },
    {
        "id": "ai_keys_store",
        "emoji_theme": ("DEV_API_KEY", "CHATGPT", "GEMINI"),
        "title": "CLAUDE, CHATGPT VA GEMINI API KALITLAR!",
        "body": (
            f"{ce('DEV_API_KEY')} <b>Dasturchilar va loyihalar uchun hamyonbop API kalitlar!</b>\n\n"
            f"{ce('CHATGPT')} OpenAI / OpenRouter / Groq tayyor tokenlar\n"
            f"{ce('GEMINI')} Google Gemini & Claude Code ruxsatlari\n"
            f"{ce('CART')} HUMO / Uzcard orqali to'lash — kalit darhol beriladi"
        ),
        "btn_text": "AI Do'konni ochish",
        "start_param": "store",
    },
    {
        "id": "web_studio_launch",
        "emoji_theme": ("BTN_DASHBOARD", "LINK", "VERIFIED"),
        "title": "MONODECK.SITE — VEB STUDIO PULTI!",
        "body": (
            f"{ce('BTN_DASHBOARD')} <b>Endi faqat bot emas — to'liq veb platforma ham bor!</b>\n\n"
            f"{ce('LINK')} Brauzer yoki Telegram Mini App orqali barcha YouTube kanallaringizni ulang\n"
            f"{ce('VERIFIED')} Real-time statistika, video namunalari, downloader va keyslar bitta joyda\n"
            f"{ce('SPARKLES')} Sinab ko'rish bepul"
        ),
        "btn_text": "Web Studio ga kirish",
        "start_param": "studio",
    },
    {
        "id": "fast_downloader",
        "emoji_theme": ("DOWNLOAD", "MEDIA_AUDIO_MP3", "CLIPPERS"),
        "title": "YOUTUBE, TIKTOK VA INSTAGRAM YUKLOVCHI!",
        "body": (
            f"{ce('DOWNLOAD')} <b>Link tashlang — soniyalarda toza video yoki MP3 oling!</b>\n\n"
            f"{ce('CLIPPERS')} Reels va Shorts larni logotipsiz yuqori sifatda yuklash\n"
            f"{ce('MEDIA_AUDIO_MP3')} Istalgan klipdan toza audio ajratib olish\n"
            f"{ce('ROCKET')} 7 GB Cloud Runner katta fayllarni ham qotmasdan tortadi"
        ),
        "btn_text": "Video yuklash",
        "start_param": "dl",
    },
    {
        "id": "daily_streak_perks",
        "emoji_theme": ("FIRE", "TICKET", "STAR"),
        "title": "7 KUNLIK STREAK — HAR KUNI SOVG'A!",
        "body": (
            f"{ce('FIRE')} <b>Mono Deck Studio ga har kuni kirishning foydasi bor!</b>\n\n"
            f"{ce('TICKET')} 1-kundan 6-kungacha bepul AI SEO, Skript va Unikalizatsiya VIP\n"
            f"{ce('STAR')} 7-kuni esa <b>100 Telegram Stars</b> bonusi to'g'ri balansingizga tushadi\n"
            f"{ce('CHECK')} Hech qanday promokod shart emas — avtomatik faollashadi"
        ),
        "btn_text": "Kunlik sovg'ani olish",
        "start_param": "cases",
    },
    {
        "id": "ig_cloner_tool",
        "emoji_theme": ("INSTAGRAM", "SHIELD", "YOUTUBE"),
        "title": "INSTAGRAM REELS AUTO-KLONER!",
        "body": (
            f"{ce('MEDIA_YOUTUBE')} <b>Instagram dagi eng zo'r Reels larni YouTube Shorts ga olib chiqing!</b>\n\n"
            f"{ce('SHIELD')} 8-qatlamli unikalizatsiya + metadata tozalash\n"
            f"{ce('VIDEO')} Audio va ranglar balansini avtomatik yangilash\n"
            f"{ce('ROCKET')} Kunlik kanal kontentingiz hech qachon to'xtab qolmaydi"
        ),
        "btn_text": "Auto-Kloner ni ko'rish",
        "start_param": "igcloner",
    },
    {
        "id": "pvp_battles_duel",
        "emoji_theme": ("DUEL", "CROWN", "CASH"),
        "title": "1v1 PVP CASE BATTLES — BELLASHUV!",
        "body": (
            f"{ce('DUEL')} <b>Boshqa foydalanuvchilar bilan jonli 1v1 keys oching!</b>\n\n"
            f"{ce('CROWN')} Kimning drop qiymati yuqori chiqsa — ikkala bankni ham yutib oladi\n"
            f"{ce('CASH')} Agar raqib topilmasa, istalgan payt 100% pulingizni qaytarib olasiz\n"
            f"{ce('GIFT')} Demo Spin orqali oldin bepul tekshirib ko'ring"
        ),
        "btn_text": "PvP Duel ochish",
        "start_param": "cases",
    },
    {
        "id": "capcut_design_apps",
        "emoji_theme": ("BRAND_CAPCUT", "KEY", "VERIFIED"),
        "title": "CAPCUT PRO VA MONTAJ VOSITALARI!",
        "body": (
            f"{ce('BRAND_CAPCUT')} <b>Pro montaj vositalarisiz video sifatini ko'tarish qiyin!</b>\n\n"
            f"{ce('KEY')} Do'konda CapCut Pro va kreativ paketlar doimiy mavjud\n"
            f"{ce('VERIFIED')} Kafolatlangan muddat va tezkor qo'llab-quvvatlash\n"
            f"{ce('MONEY')} Mahalliy HUMO / Uzcard orqali qulay to'lov"
        ),
        "btn_text": "CapCut Pro olish",
        "start_param": "capcut",
    },
    {
        "id": "referral_cashback",
        "emoji_theme": ("USER", "CASH", "LINK"),
        "title": "DO'STLARNI TAKLIF QILING — 10% DAROMAD!",
        "body": (
            f"{ce('USER')} <b>Sizning shaxsiy referal havolangiz pul ishlab berishi mumkin!</b>\n\n"
            f"{ce('LINK')} Do'stingizga havolangizni yuboring — ular har bir xarid qilganda sizga bonus tushadi\n"
            f"{ce('CASH')} Yig'ilgan mablag'ni AI xizmatlar, API kalitlar yoki keyslarga sarflang\n"
            f"{ce('CHECK')} Botda /referral buyrug'ini bosing"
        ),
        "btn_text": "Referal havolani olish",
        "start_param": "referral",
    },
    {
        "id": "reseller_developer_api",
        "emoji_theme": ("BOT", "DEV_API_KEY", "SHIELD"),
        "title": "DEVELOPER & RESELLER API INTEGRATSIYA!",
        "body": (
            f"{ce('DEV_API_KEY')} <b>O'z loyihangiz yoki botingizga video yuklash va SEO API ulang!</b>\n\n"
            f"{ce('BOT')} REST API hujjatlari: monodeck.site/docs\n"
            f"{ce('SHIELD')} Yuqori tezlik, shaxsiy token va real-time balans nazorati\n"
            f"{ce('ROCKET')} Ishlab chiquvchilar uchun tayyor endpointlar"
        ),
        "btn_text": "API hujjatlarini ko'rish",
        "start_param": "api",
    },
]


def _load_recent_promo_ids() -> list[str]:
    try:
        from database import get_bot_config
        raw = get_bot_config("store_channel_recent_promo_ids")
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed][-10:]
    except Exception:
        pass
    return []


def _save_recent_promo_ids(ids: list[str]) -> None:
    try:
        from database import set_bot_config
        set_bot_config("store_channel_recent_promo_ids", json.dumps(ids[-10:]))
    except Exception:
        pass


def select_next_daily_promo(promo_index: Optional[int] = None) -> dict:
    """
    Oxirgi 10 ta yuborilgan shablonni takrorlamasdan keyingi xilma-xil kunlik postni tanlaydi.
    """
    if promo_index is not None:
        return dict(PROMO_TEMPLATES[int(promo_index) % len(PROMO_TEMPLATES)])

    recent = _load_recent_promo_ids()
    pool = [p for p in PROMO_TEMPLATES if p["id"] not in recent]
    if not pool:
        # Barcha 14 tasi aylanib chiqqan bo'lsa, eng oxirgi 3 tasini chiqarib tashlab yangidan tanlaymiz
        last_few = set(recent[-3:])
        pool = [p for p in PROMO_TEMPLATES if p["id"] not in last_few] or list(PROMO_TEMPLATES)

    # Kun sanasini ham aralashtirib deterministik bo'lmagan xilma-xillik yaratish
    picked = random.choice(pool)
    recent.append(picked["id"])
    _save_recent_promo_ids(recent)
    return dict(picked)


def _format_promo_body_values(promo: dict) -> dict:
    out = dict(promo)
    try:
        out["body"] = str(out["body"]).format(VIP_PRICE_UZS=VIP_PRICE_UZS, VIP_PRICE_STARS=VIP_PRICE_STARS)
    except Exception:
        pass
    return out


async def _maybe_reword_daily_intro(promo_title: str) -> Optional[str]:
    """Agar GEMINI_API_KEY mavjud bo'lsa, har kunlik kirish jumlasini biroz boshqacha jonli qiladi."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = (
            "Write ONE fresh, short, natural Uzbek hook line (max 11 words, no hashtags, no markdown, no emojis) "
            f"for a Telegram channel post about Mono Deck Studio feature: {promo_title}. "
            f"Today is {datetime.now().strftime('%A %Y-%m-%d')}."
        )
        resp = await asyncio.to_thread(
            lambda: client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        )
        line = (getattr(resp, "text", "") or "").strip().splitlines()[0].strip(" \"'*#")
        if 8 <= len(line) <= 110:
            return line
    except Exception:
        pass
    return None


async def send_channel_promo(client: Client, promo_index: Optional[int] = None) -> bool:
    """Kanalga har kuni har xil format va custom emojilar bilan kunlik post yuborish."""
    if not STORE_CHANNEL:
        return False

    try:
        promo = _format_promo_body_values(select_next_daily_promo(promo_index))
        bot_username = _resolve_active_bot_username(client)
        emoji_keys = promo.get("emoji_theme") or ("ROCKET", "STAR", "CHECK")
        lead_emoji = ce(emoji_keys[0])
        tail_emoji = ce(emoji_keys[-1])

        ai_hook = await _maybe_reword_daily_intro(promo["title"])
        _, fallback_opener = random.choice(DAILY_OPENERS)
        opener_line = f"<b>{ai_hook}</b>" if ai_hook else fallback_opener
        closer_line = random.choice(DAILY_CLOSERS)

        text = (
            f"{lead_emoji} <b>{promo['title']}</b>\n"
            f"{opener_line}\n\n"
            f"{promo['body']}\n\n"
            f"{closer_line}\n"
            f"{tail_emoji} <b>Bot:</b> @{bot_username} · <b>Web:</b> monodeck.site"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{ce('ROCKET')} {promo['btn_text']}", url=f"https://t.me/{bot_username}?start={promo['start_param']}")],
            [InlineKeyboardButton(f"{ce('BTN_HOME')} Mono Deck Studio", url=f"https://t.me/{bot_username}")],
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        logger.info(f"Kanalga kunlik xilma-xil post yuborildi: {promo['id']}")
        return True
    except Exception as err:
        logger.error(f"send_channel_promo xatosi: {err}")
        return False


# ==================== SOVRINLI KONKURSLAR ====================

async def create_and_post_contest(
    client: Client,
    title: str = "Haftalik Omadli Ishtirokchi Konkursi",
    prize_text: str = "1 Oylik Mono Deck Studio VIP (69,000 UZS) + 100 Stars",
    duration_hours: int = 48,
) -> Optional[int]:
    if not STORE_CHANNEL:
        return None

    try:
        bot_username = _resolve_active_bot_username(client)
        contest_id = create_channel_contest(title=title, prize_text=prize_text, duration_hours=duration_hours)
        if not contest_id:
            return None

        text = (
            f"{ce('TICKET')} <b>MONO DECK STUDIO KONKURS! #{contest_id}</b>\n\n"
            f"{ce('TROPHY')} <b>Bosh sovrin:</b>\n"
            f"<b>{prize_text}</b>\n\n"
            f"{ce('ROCKET')} <b>Ishtirok etish shartlari:</b>\n"
            f"1. {ce('CHANNEL')} {STORE_CHANNEL} kanalimizga a'zo bo'lish\n"
            f"2. {ce('PHONE')} Botda telefon raqamingizni tasdiqlash\n"
            f"3. Pastdagi <b>«Ishtirok etish»</b> tugmasini bosish\n\n"
            f"{ce('WAIT')} <b>Muddat:</b> {duration_hours} soat"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{ce('GIFT_TROPHY')} Konkursda ishtirok etish", url=f"https://t.me/{bot_username}?start=contest_{contest_id}")],
            [InlineKeyboardButton(f"{ce('MEDIA_AUTOPILOT')} Botga o'tish", url=f"https://t.me/{bot_username}")],
        ])

        await _send_channel_message(client, text, reply_markup=kb)
        return contest_id
    except Exception as err:
        logger.error(f"create_and_post_contest xatosi: {err}")
        return None


# ==================== FLASH SALE ====================

async def send_channel_flash_sale(
    client: Client,
    title: str = "Tungi Happy Hour Chegirmasi",
    discount_percent: int = 20,
    duration_hours: int = 2,
) -> bool:
    if not STORE_CHANNEL:
        return False
    try:
        create_flash_sale(title, discount_percent, duration_hours)
        bot_username = _resolve_active_bot_username(client)

        text = (
            f"{ce('FIRE')} <b>FLASH SALE! {title.upper()}!</b>\n\n"
            f"{ce('CASH')} <b>Chegirma hajmi:</b> Barcha raqamli tovarlarga <b>-{discount_percent}%</b> chegirma!\n"
            f"{ce('TIMER')} <b>Davomiyligi:</b> Faqat <b>{duration_hours} soat</b> davomida amal qiladi!\n\n"
            f"{ce('BOX')} <i>Mono Deck Studio do'konidagi AI kalitlar va xizmatlarni arzon narxda oling.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Chegirmada xarid qilish", url=f"https://t.me/{bot_username}?start=store")],
            [InlineKeyboardButton(f"VIP Tarif ({VIP_PRICE_UZS:,} UZS)", url=f"https://t.me/{bot_username}?start=vip")],
        ])
        await _send_channel_message(client, text, reply_markup=kb)
        return True
    except Exception as err:
        logger.error(f"send_channel_flash_sale xatosi: {err}")
        return False


# ==================== TEZKOR DROP PROMOKODLAR ====================

async def send_channel_drop_promo(
    client: Client,
    code: str,
    reward_uzs: int = 10000,
    max_uses: int = 3,
    duration_minutes: int = 60,
) -> bool:
    if not STORE_CHANNEL:
        return False
    try:
        create_fast_drop_promo(code, "balance", reward_uzs, max_uses, duration_minutes)
        bot_username = _resolve_active_bot_username(client)

        text = (
            f"{ce('FIRE')} <b>TEZKOR PROMOKOD DROP!</b>\n\n"
            f"{ce('KEY')} <b>Promokod:</b> <code>{code}</code>\n"
            f"{ce('MONEY')} <b>Yutuq:</b> <code>+{reward_uzs:,} so'm</code> balansingizga!\n"
            f"{ce('LOCK')} <b>Cheklov:</b> Faqat birinchi <b>{max_uses}</b> ta tezkor obunachi uchun!\n"
            f"{ce('WAIT')} <b>Amal qilish vaqti:</b> {duration_minutes} daqiqa"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Promokodni faollashtirish", url=f"https://t.me/{bot_username}?start=promo_{code}")],
            [InlineKeyboardButton("Mono Deck Studio", url=f"https://t.me/{bot_username}")],
        ])
        await _send_channel_message(client, text, reply_markup=kb)
        return True
    except Exception as err:
        logger.error(f"send_channel_drop_promo xatosi: {err}")
        return False


# ==================== WISHLIST NOTIFIER ====================

async def notify_wishlist_users(
    client: Client,
    product_id: int,
    product_name: str,
    price_uzs: int = 0,
) -> int:
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
        [InlineKeyboardButton("Do'konga o'tish", callback_data="menu_marketplace")],
    ])

    for uid in user_ids:
        try:
            await client.send_message(uid, text, reply_markup=kb)
            notified_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Wishlist xabari yuborilmadi ({uid}): {e}")

    mark_wishlist_notified(product_id)
    return notified_count


# ==================== ABANDONED CART RETARGETING ====================

async def check_and_notify_abandoned_carts(client: Client) -> int:
    carts = await asyncio.to_thread(get_abandoned_carts_to_notify, minutes_ago=20)
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
                f"{ce('SHIELD')} <i>Mahsulot siz uchun zaxirada vaqtinchalik saqlab turilibdi.</i>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Xaridni davom ettirish", callback_data=f"vb_item_{p_id}_ai")],
                [InlineKeyboardButton("Savatni tozalash", callback_data=f"cart_cancel_{cart_id}")],
            ])

            await client.send_message(uid, text, reply_markup=kb)
            await asyncio.to_thread(mark_abandoned_cart_notified, cart_id)
            notified += 1
            await asyncio.sleep(0.15)
        except Exception as err:
            logger.warning(f"Abandoned cart notification error (cart {cart.get('id')}): {err}")
            await asyncio.to_thread(mark_abandoned_cart_notified, cart.get("id"))

    return notified


# ==================== AVTOPILOT SIKLI (KUNLIK XILMA-XIL POSTING) ====================

async def run_channel_autopilot(client: Client):
    """
    Kunlik kanal avtopiloti:
    - Har 24 soatda takrorlanmaydigan yangi mavzu va custom emojilar bilan post joylaydi.
    - Har 5 daqiqada tashlab ketilgan savatlarni tekshiradi.
    """
    logger.info("Mono Deck Studio kanal avtopilot xizmati ishga tushirildi...")
    await asyncio.sleep(60)

    import time
    from database import get_bot_config, set_bot_config

    MIN_PROMO_INTERVAL_SECONDS = 24 * 3600

    while True:
        try:
            await check_and_notify_abandoned_carts(client)

            last_promo_str = await asyncio.to_thread(get_bot_config, "store_channel_last_promo_time")
            try:
                last_promo_time = float(last_promo_str) if last_promo_str else 0.0
            except Exception:
                last_promo_time = 0.0

            now = time.time()
            if (now - last_promo_time) >= MIN_PROMO_INTERVAL_SECONDS:
                sent = await send_channel_promo(client, promo_index=None)
                if sent:
                    await asyncio.to_thread(set_bot_config, "store_channel_last_promo_time", str(now))

            await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"run_channel_autopilot sikl xatosi: {e}")
            await asyncio.sleep(60)
