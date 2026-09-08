import os
import shutil
import urllib.parse
import re
import asyncio
import math
import json
from datetime import datetime, timedelta
from pyrogram import Client, filters, StopPropagation
from pyrogram.errors import MessageNotModified
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import (
    WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    CallbackQuery, Message,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
from googleapiclient.discovery import build

from config import OWNER_ID
from config import (
    generate_with_fallback_async, generate_with_fallback,
    BOT_TOKEN, API_ID, API_HASH, YOUTUBE_API_KEY, get_youtube_key,
    ADMIN_USERNAME, DEFAULT_PROXY, DAILY_LIMIT_USER, DAILY_LIMIT_ADMIN, get_gemini_key,
    WEB_APP_URL, CRYPTO_PAY_TOKEN
)
from database import (
    set_autopilot, get_autopilot, stop_autopilot,
    add_tracked_channel, remove_tracked_channel, get_tracked_channels,
    save_channel_snapshot, save_video_snapshot,
    get_channel_history, get_channel_growth,
    add_bot_admin, is_bot_admin, get_all_admins,
    create_autopost_task, reset_all_data, get_all_yt_connections,
    set_user_proxy, get_user_proxy, get_daily_usage, increment_usage, set_config, set_user_cookies,
    get_user_balance, add_user_balance, deduct_user_balance,
    create_payment_transaction, complete_payment_transaction, get_payment_transaction,
    get_user_payment_history, create_engagement_order, update_engagement_order,
    get_user_engagement_orders, get_every_yt_connection, is_user_kyc_verified, get_user_kyc,
    get_ton_wallet, set_ton_wallet,
    add_api_key_to_stock, get_api_keys_stock_count, purchase_api_key, get_user_purchased_keys,
    save_telegram_phone, get_telegram_phone,
    add_proxy_to_stock, get_proxies_stock_count, purchase_proxy, get_user_download_proxy,
    purchase_autostream_slot, get_user_autostream_slots, get_all_active_autostream_slots, expire_autostream_slot,
    purchase_flux_subscription, get_flux_quota, use_flux_credit,
    purchase_vip_subscription, is_user_vip,
    set_user_referrer, get_user_referrer, process_referral_cashback, get_referral_stats,
    record_user_purchase, get_user_purchases,
    get_or_create_user_api_key, regenerate_user_api_key,
    set_user_language, get_user_language, get_top_referrers, get_top_duel_winners,
    get_config, set_config
)
from locales import t, SUPPORTED_LANGUAGES
from games_monetization import (
    create_vouchers, redeem_voucher,
    open_mystery_box, get_recent_box_winners,
    can_user_free_spin, spin_wheel,
    create_duel, join_duel, cancel_duel, get_open_duels,
    buy_lottery_tickets, get_current_lottery_info, draw_lottery_if_ready,
    subscribe_webhook, get_user_webhook,
    order_whitelabel_bot, get_user_whitelabel_bots
)
from autopost import autopost_worker, get_auth_url, upload_to_youtube
from custom_emojis import EMOJI_MAP, e
from crypto_pay import create_crypto_pay_invoice, CRYPTO_PACKAGES
from instagram_processor import download_instagram_reel, is_instagram_url, get_ffmpeg_binary
from mass_engagement import _do_like, _do_comment, _do_subscribe, generate_gemini_comment, extract_video_id
import google.generativeai as genai
import uuid

AUTOPOST_ARGS_MAP = {}
USER_ORDER_STATE = {} # tg_user_id -> dict(action, step, target_url, qty, total_cost)
INSTA_CACHE = {} # cache_id -> dict(file_path, title, desc)

# Telegram Stars narx paketlari (1 Star ≈ 250-260 UZS)
STARS_PACKAGES = [
    {"stars": 15, "amount_uzs": 4000, "label": "15 ⭐ — 4,000 so'm (Minimal)"},
    {"stars": 25, "amount_uzs": 6500, "label": "25 ⭐ — 6,500 so'm"},
    {"stars": 50, "amount_uzs": 13000, "label": "50 ⭐ — 13,000 so'm"},
    {"stars": 100, "amount_uzs": 26000, "label": "100 ⭐ — 26,000 so'm"},
    {"stars": 250, "amount_uzs": 65000, "label": "250 ⭐ — 65,000 so'm"},
    {"stars": 500, "amount_uzs": 130000, "label": "500 ⭐ — 130,000 so'm"},
    {"stars": 1000, "amount_uzs": 260000, "label": "1,000 ⭐ — 260,000 so'm"},
]

# We'll create a reverse map: fallback_emoji -> custom_emoji_id (with both \ufe0f and non-\ufe0f variants)
FALLBACK_TO_ID = {}
for val in EMOJI_MAP.values():
    c_id = int(val[0])
    fb = val[1]
    FALLBACK_TO_ID[fb] = c_id
    if '\ufe0f' in fb:
        FALLBACK_TO_ID[fb.replace('\ufe0f', '')] = c_id
    else:
        FALLBACK_TO_ID[fb + '\ufe0f'] = c_id

_CODE_RE = re.compile(r'<(?:code|pre)[^>]*>[\s\S]*?</(?:code|pre)>', re.IGNORECASE)
_EXISTING_EMOJI_RE = re.compile(r'<(?:emoji|tg-emoji)[^>]*>[\s\S]*?</(?:emoji|tg-emoji)>', re.IGNORECASE)
_TAG_RE = re.compile(r'</?(?:b|strong|i|em|u|ins|s|strike|del|a|span|tg-spoiler|blockquote)(?:\s+[^<>\n\r]*)?>', re.IGNORECASE)
_ENTITY_RE = re.compile(r'&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);')

def convert_md_to_html_and_emojis(text):
    if not isinstance(text, str): return text
    
    saved_code = []
    def _save_code(m):
        saved_code.append(m.group(0))
        return f"CODEPHX{len(saved_code)-1}XPH"

    saved_emojis = []
    def _save_emoji(m):
        saved_emojis.append(m.group(0))
        return f"EMOJIPHX{len(saved_emojis)-1}XPH"

    saved_tags = []
    def _save_tag(m):
        saved_tags.append(m.group(0))
        return f"TAGPHX{len(saved_tags)-1}XPH"
        
    saved_ents = []
    def _save_ent(m):
        saved_ents.append(m.group(0))
        return f"ENTPHX{len(saved_ents)-1}XPH"

    # 1. Protect existing <code> and <pre> blocks
    text = _CODE_RE.sub(_save_code, text)
    # 2. Protect existing <emoji> or <tg-emoji> blocks
    text = _EXISTING_EMOJI_RE.sub(_save_emoji, text)
    # 3. Protect valid HTML tags (<b>, </b>, <i>, <a>, <blockquote>, etc.)
    text = _TAG_RE.sub(_save_tag, text)
    # 4. Protect valid HTML entities (&amp;, &lt;, etc.)
    text = _ENTITY_RE.sub(_save_ent, text)

    # 5. Escape raw <, >, & so Telegram HTML parser won't error on bare symbols
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # 6. Convert Markdown syntax
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text, flags=re.DOTALL)
    text = re.sub(r'(?<![\w\\])_(.*?)_(?![\w\\])', r'<i>\1</i>', text, flags=re.DOTALL)

    # Protect new <code> tags created from markdown `code`
    text = re.sub(r'<code>[\s\S]*?</code>', _save_code, text)

    # 7. Apply custom emojis (use placeholders to prevent nested tags on substrings)
    for fallback, c_id in sorted(FALLBACK_TO_ID.items(), key=lambda x: len(x[0]), reverse=True):
        if fallback in text:
            parts = text.split(fallback)
            new_text_parts = []
            for idx, part in enumerate(parts):
                new_text_parts.append(part)
                if idx < len(parts) - 1:
                    ph = f"EMOJIPHX{len(saved_emojis)}XPH"
                    saved_emojis.append(f'<emoji id="{c_id}">{fallback}</emoji>')
                    new_text_parts.append(ph)
            text = "".join(new_text_parts)

    # 8. Restore saved items in exact reverse order
    for idx, cb in enumerate(saved_code):
        text = text.replace(f"CODEPHX{idx}XPH", cb)
    for idx, ent in enumerate(saved_ents):
        text = text.replace(f"ENTPHX{idx}XPH", ent)
    for idx, tag in enumerate(saved_tags):
        text = text.replace(f"TAGPHX{idx}XPH", tag)
    for idx, em in enumerate(saved_emojis):
        text = text.replace(f"EMOJIPHX{idx}XPH", em)

    # Clean any accidental nested HTML tags inside <code> and <pre> tags (Telegram Bot API disallows them)
    def _strip_nested_in_code(m):
        tag = m.group(1)
        inner = re.sub(r'</?(?:b|strong|i|em|u|ins|s|strike|del|a|span|tg-spoiler|tg-emoji|emoji)[^>]*>', '', m.group(2))
        return f"<{tag}>{inner}</{tag}>"
    text = re.sub(r'<(code|pre)>(.*?)</\1>', _strip_nested_in_code, text, flags=re.DOTALL | re.IGNORECASE)
        
    return text

def _is_vip_user(user_id):
    if not user_id:
        return False
    try:
        from database import is_user_vip
        return bool(is_user_vip(int(user_id)))
    except Exception:
        return False

def _get_button_icon_id(cb, raw_text, web_url="", is_vip=False):
    # 1. CapCut Pro
    if any(k in cb for k in ["menu_capcut", "capcut"]):
        return "5285497929686069998" if is_vip else "5978895591894161700"
    # 2. Instagram Cloner
    if any(k in cb for k in ["menu_ig_cloner", "ig_"]):
        return "6001420655252213986" if is_vip else "4990082283701535678"
    # 3. Reels Downloader
    if any(k in cb for k in ["menu_reels", "dl_reels"]):
        return "5312147767966054472" if is_vip else "5825658700735451589"
    # 4. P2P Vouchers / Cheklar
    if any(k in cb for k in ["menu_vouchers", "claim_chk", "help_create_check"]):
        return "5420112302210817795" if is_vip else "5265197972919964944"
    # 5. Check Claim
    if any(k in cb for k in ["chk_claim", "redeem_check"]):
        return "5960914406366779993" if is_vip else "5980930633298350051"
    # 6. Anti-fraud / Xavfsizlik
    if any(k in cb for k in ["antifraud", "security_lock"]):
        return "5465443379917629504" if is_vip else "5463358164705489689"
    # 7. AI Video Studio ($20/oy)
    if any(k in cb for k in ["menu_ai_video", "aivid_"]):
        return "5249493957578078525" if is_vip else "5235837920081887219"
    # 8. Voice / Audio
    if any(k in cb for k in ["voice_", "tts_"]):
        return "5766912713586381607" if is_vip else "5895215520000513680"
    # 9. Raqobatchi Tahlili (Spy & SEO)
    if any(k in cb for k in ["menu_spy", "spy_"]):
        return "6107110845399962129" if is_vip else "5339247212012528642"
    # 10. SEO Tag
    if any(k in cb for k in ["seo_tags", "tagsgen"]):
        return "5406711411541823609" if is_vip else "5298877105000439431"
    # 11. Balansni Yechish (Cashout)
    if any(k in cb for k in ["menu_cashout", "co_method", "cashout"]):
        return "5463046637842608206" if is_vip else "4967738760021148319"
    # 12. Smart YouTube DeepLink & QR
    if any(k in cb for k in ["menu_deeplink", "deeplink"]):
        return "5224378350335707737" if is_vip else "5264938002844513934"

    # Core Navigation & Features:
    if any(k in cb for k in ["menu_support_desk", "supp_"]):
        return "5443038326535759644"
    if any(k in cb for k in ["menu_wallet", "pay_"]):
        return "5463046637842608206" if is_vip else "5343777479091831702"
    if any(k in cb for k in ["menu_games", "game_"]):
        return "5235989279024373566"
    if any(k in cb for k in ["menu_referral"]):
        return "6319002678990998592"
    if any(k in cb for k in ["menu_leaderboard"]):
        return "5226431245918942763"
    if any(k in cb for k in ["menu_marketplace", "market"]):
        return "5864068125112144897"
    if any(k in cb for k in ["help_api", "api_keys"]):
        return "5287480366330816274"
    if any(k in cb for k in ["menu_channel"]):
        return "5431504848992360576"
    if any(k in cb for k in ["menu_analytics"]):
        return "5244837092042750681"
    if any(k in cb for k in ["menu_lang"]):
        return "6017109689748164760"
    if any(k in cb for k in ["menu_help"]):
        return "5452026937172048380"
    if any(k in cb for k in ["back_main", "main_menu"]):
        return "6327577233305112811"

    # WebApps:
    if web_url:
        if "/kyc/" in web_url or "kyc" in web_url:
            return "5330194932781050507"
        return "6327577233305112811"

    # Text based detection
    if "capcut" in raw_text:
        return "5285497929686069998" if is_vip else "5978895591894161700"
    if "instagram" in raw_text or "kloner" in raw_text:
        return "6001420655252213986" if is_vip else "4990082283701535678"
    if "reels" in raw_text:
        return "5312147767966054472" if is_vip else "5825658700735451589"
    if "chek" in raw_text or "voucher" in raw_text:
        return "5420112302210817795" if is_vip else "5265197972919964944"
    if "ai video" in raw_text:
        return "5249493957578078525" if is_vip else "5235837920081887219"
    if "raqobatchi" in raw_text or "spy" in raw_text:
        return "6107110845399962129" if is_vip else "5339247212012528642"
    if "admin" in raw_text or "yordam & live" in raw_text or "support" in raw_text:
        return "5443038326535759644"
    if "yechish" in raw_text or "cashout" in raw_text:
        return "5463046637842608206" if is_vip else "4967738760021148319"
    if "deeplink" in raw_text:
        return "5224378350335707737" if is_vip else "5264938002844513934"
    if "balans" in raw_text or "to'ldirish" in raw_text or "wallet" in raw_text:
        return "5463046637842608206" if is_vip else "5343777479091831702"
    if "o'yinlar" in raw_text or "yutuq" in raw_text:
        return "5235989279024373566"
    if "marketplace" in raw_text or "xizmatlar" in raw_text:
        return "5864068125112144897"
    if "do'stlarni" in raw_text or "referal" in raw_text:
        return "6319002678990998592"
    if "liderlar" in raw_text or "jadval" in raw_text:
        return "5226431245918942763"
    if "dashboard" in raw_text:
        return "6327577233305112811"
    if "kyc" in raw_text:
        return "5330194932781050507"

    return None

def _get_button_style(cb, raw_text, web_url=""):
    if web_url:
        if "/kyc/" in web_url or "kyc" in web_url:
            return "danger"
        return "primary"

    if any(k in cb for k in ["menu_wallet", "pay_", "wallet", "box_open", "sub_check", "buy_", "stars_pkg", "crypto_pkg", "marketplace", "market", "menu_marketplace", "menu_vouchers", "menu_cashout", "aivid_buy"]) or any(k in raw_text for k in ["sotib olish", "to'ldirish", "ochish", "tekshirish", "deposit", "kassa", "marketplace", "balans & to'ldirish", "balans", "obuna", "stars bilan"]):
        return "success"

    if any(k in cb for k in ["menu_games", "game_duel", "delaccount", "dbreset", "cancel"]) or any(k in raw_text for k in ["duel", "o'yinlar", "who wins", "o'chirish", "bekor", "3d kyc"]):
        return "danger"

    if any(k in cb for k in ["back_main", "main_menu", "dashboard", "pub_aivid"]) or any(k in raw_text for k in ["web dashboard", "bosh menyu", "orqaga", "yuklash"]):
        return "primary"

    return None

_LEADING_EMOJI_PATTERN = re.compile(
    r'^[\s\U00010000-\U0010ffff\u2600-\u27bf\ufe0f\u200d\u2300-\u23ff\u2b50\u2b55\u3030\u303d\u2190-\u21ff\u2934\u2935]+',
    re.UNICODE
)

def _clean_button_text(btn_text, icon_id=None):
    if not btn_text:
        return ""
    if icon_id:
        cleaned = _LEADING_EMOJI_PATTERN.sub('', btn_text).strip()
        for fb in sorted(FALLBACK_TO_ID.keys(), key=len, reverse=True):
            if cleaned.startswith(fb):
                cleaned = cleaned[len(fb):].strip()
        return cleaned if cleaned else btn_text
    return btn_text

def _build_bot_api_reply_markup(reply_markup, user_id=None):
    """Converts Pyrogram InlineKeyboardMarkup or ReplyKeyboardMarkup to Telegram Bot API payload dict"""
    if not reply_markup:
        return None
    if isinstance(reply_markup, dict):
        return reply_markup
    if not isinstance(reply_markup, InlineKeyboardMarkup):
        if isinstance(reply_markup, ReplyKeyboardMarkup):
            kb = []
            for row in reply_markup.keyboard:
                row_btns = []
                for b in row:
                    b_dict = {"text": b.text}
                    if getattr(b, "request_contact", False):
                        b_dict["request_contact"] = True
                    if getattr(b, "request_location", False):
                        b_dict["request_location"] = True
                    row_btns.append(b_dict)
                kb.append(row_btns)
            res = {"keyboard": kb, "resize_keyboard": getattr(reply_markup, "resize_keyboard", True)}
            if getattr(reply_markup, "one_time_keyboard", False):
                res["one_time_keyboard"] = True
            return res
        if isinstance(reply_markup, ReplyKeyboardRemove):
            return {"remove_keyboard": True}
        return None

    is_vip = _is_vip_user(user_id)
    keyboard = []
    for row in reply_markup.inline_keyboard:
        row_btns = []
        for btn in row:
            btn_dict = {}
            raw_text = btn.text or ""
            cb = getattr(btn, "callback_data", None) or ""
            if isinstance(cb, bytes):
                try: cb = cb.decode("utf-8")
                except: cb = ""
            
            web_url = ""
            if getattr(btn, "web_app", None) and getattr(btn.web_app, "url", None):
                web_url = btn.web_app.url

            icon_id = _get_button_icon_id(cb, raw_text.lower(), web_url, is_vip=is_vip)
            if not icon_id:
                for fb, c_id in sorted(FALLBACK_TO_ID.items(), key=lambda x: len(x[0]), reverse=True):
                    if fb in raw_text:
                        icon_id = str(c_id)
                        break
            
            btn_dict["text"] = _clean_button_text(raw_text, icon_id)
            if icon_id:
                btn_dict["icon_custom_emoji_id"] = str(icon_id)

            style = getattr(btn, "style", None) or _get_button_style(cb, raw_text.lower(), web_url)
            if style in ("primary", "success", "danger"):
                btn_dict["style"] = style

            if btn.callback_data is not None:
                btn_dict["callback_data"] = cb
            elif btn.url is not None:
                btn_dict["url"] = btn.url
            elif getattr(btn, "web_app", None) and getattr(btn.web_app, "url", None):
                btn_dict["web_app"] = {"url": btn.web_app.url}
            elif getattr(btn, "switch_inline_query", None) is not None:
                btn_dict["switch_inline_query"] = btn.switch_inline_query
            elif getattr(btn, "switch_inline_query_current_chat", None) is not None:
                btn_dict["switch_inline_query_current_chat"] = btn.switch_inline_query_current_chat

            row_btns.append(btn_dict)
        keyboard.append(row_btns)
    return {"inline_keyboard": keyboard}

async def _bot_api_send(bot_token, chat_id, text, reply_markup=None, reply_to_message_id=None):
    if not bot_token:
        return None
    import aiohttp
    
    cid = getattr(chat_id, "id", chat_id)
    if isinstance(cid, (int, str)):
        cid = int(cid) if str(cid).lstrip("-").isdigit() else str(cid)

    rep_id = None
    if reply_to_message_id is not None:
        rep_id = getattr(reply_to_message_id, "id", getattr(reply_to_message_id, "message_id", reply_to_message_id))
        if rep_id is not None and str(rep_id).isdigit():
            rep_id = int(rep_id)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    bot_api_text = text.replace('<emoji id="', '<tg-emoji emoji-id="').replace('</emoji>', '</tg-emoji>')
    payload = {
        "chat_id": cid,
        "text": bot_api_text,
        "parse_mode": "HTML",
    }
    
    if reply_markup is not None:
        if isinstance(reply_markup, dict):
            payload["reply_markup"] = reply_markup
        else:
            bot_markup = _build_bot_api_reply_markup(reply_markup, user_id=cid)
            if bot_markup:
                payload["reply_markup"] = bot_markup
                
    if rep_id:
        payload["reply_to_message_id"] = rep_id
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=12, connect=5)) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get("ok"):
                    return data["result"]["message_id"]
                else:
                    import logging
                    logging.warning(f"Bot API sendMessage failed: {resp.status} - {data.get('description')}")
    except Exception as e:
        import logging
        logging.warning(f"Bot API send exception: {e}")
    return None

async def _bot_api_edit(bot_token, chat_id, message_id, text, reply_markup=None):
    if not bot_token:
        return False
    import aiohttp
    
    cid = getattr(chat_id, "id", chat_id)
    if isinstance(cid, (int, str)):
        cid = int(cid) if str(cid).lstrip("-").isdigit() else str(cid)

    mid = getattr(message_id, "id", getattr(message_id, "message_id", message_id))
    if mid is not None and str(mid).isdigit():
        mid = int(mid)
    else:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    bot_api_text = text.replace('<emoji id="', '<tg-emoji emoji-id="').replace('</emoji>', '</tg-emoji>')
    payload = {
        "chat_id": cid,
        "message_id": mid,
        "text": bot_api_text,
        "parse_mode": "HTML",
    }
    
    if reply_markup is not None:
        if isinstance(reply_markup, dict):
            payload["reply_markup"] = reply_markup
        else:
            bot_markup = _build_bot_api_reply_markup(reply_markup, user_id=cid)
            if bot_markup:
                payload["reply_markup"] = bot_markup

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=12, connect=5)) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get("ok"):
                    return True
                desc = data.get("description", "")
                if "message is not modified" in desc.lower():
                    return True
                if "there is no text in the message to edit" in desc.lower():
                    caption_url = f"https://api.telegram.org/bot{bot_token}/editMessageCaption"
                    caption_payload = {
                        "chat_id": cid,
                        "message_id": mid,
                        "caption": bot_api_text,
                        "parse_mode": "HTML",
                    }
                    if "reply_markup" in payload:
                        caption_payload["reply_markup"] = payload["reply_markup"]
                    async with session.post(caption_url, json=caption_payload, timeout=aiohttp.ClientTimeout(total=12, connect=5)) as c_resp:
                        c_data = await c_resp.json()
                        if c_resp.status == 200 and c_data.get("ok"):
                            return True
                import logging
                logging.warning(f"Bot API editMessageText failed: {resp.status} - {desc}")
    except Exception as e:
        import logging
        logging.warning(f"Bot API edit exception: {e}")
    return False

async def _send_bot_api_invoice(bot_token, chat_id, title, description, payload, currency, prices, provider_token=""):
    """Telegram Bot API orqali Invoice (masalan Telegram Stars) yuborish"""
    import aiohttp
    url = f"https://api.telegram.org/bot{bot_token}/sendInvoice"
    body = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "currency": currency,
        "prices": prices,
        "provider_token": provider_token,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get("ok"):
                    return data["result"]["message_id"]
                else:
                    import logging
                    logging.error(f"Bot API sendInvoice error {resp.status}: {data}")
    except Exception as e:
        import logging
        logging.warning(f"Bot API sendInvoice failed: {e}")
    return None

_orig_send_message = Client.send_message
async def _patched_send_message(self, chat_id, text, parse_mode=None, reply_markup=None, **kwargs):
    if parse_mode != ParseMode.DISABLED:
        text = convert_md_to_html_and_emojis(text)
        parse_mode = ParseMode.HTML

    bot_token = getattr(self, "bot_token", None) or BOT_TOKEN or os.getenv("BOT_TOKEN")
    if bot_token and reply_markup and isinstance(reply_markup, (InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove)):
        cid = getattr(chat_id, "id", chat_id)
        if isinstance(cid, (int, str)):
            bot_api_kb = _build_bot_api_reply_markup(reply_markup, user_id=cid)
            reply_to_id = kwargs.get("reply_to_message_id")
            msg_id = await _bot_api_send(bot_token, cid, text, bot_api_kb, reply_to_id)
            if msg_id:
                try:
                    msg = await self.get_messages(cid, msg_id)
                    if msg:
                        return msg
                except Exception:
                    pass
                from pyrogram.types import Message, Chat
                return Message(id=int(msg_id), chat=Chat(id=int(cid), type="private"), client=self)

    try:
        return await _orig_send_message(self, chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as e:
        import logging
        logging.warning(f"send_message error in ytbot.py: {e} | Text: {text[:50]}...")
        if len(text) > 4000:
            chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
            last_msg = None
            for idx, c in enumerate(chunks):
                km = reply_markup if idx == len(chunks) - 1 else None
                try:
                    last_msg = await _orig_send_message(self, chat_id, c, parse_mode=parse_mode, reply_markup=km, **kwargs)
                except Exception:
                    last_msg = await _orig_send_message(self, chat_id, c, parse_mode=None, reply_markup=km, **kwargs)
            return last_msg
        return await _orig_send_message(self, chat_id, text, parse_mode=None, reply_markup=reply_markup, **kwargs)
Client.send_message = _patched_send_message

_orig_edit_message_text = Client.edit_message_text
async def _patched_edit_message_text(self, chat_id, message_id, text, parse_mode=None, reply_markup=None, **kwargs):
    if parse_mode != ParseMode.DISABLED:
        text = convert_md_to_html_and_emojis(text)
        parse_mode = ParseMode.HTML

    bot_token = getattr(self, "bot_token", None) or BOT_TOKEN or os.getenv("BOT_TOKEN")
    if bot_token and reply_markup and isinstance(reply_markup, (InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove)):
        cid = getattr(chat_id, "id", chat_id)
        mid = getattr(message_id, "id", getattr(message_id, "message_id", message_id))
        if isinstance(cid, (int, str)) and mid:
            bot_api_kb = _build_bot_api_reply_markup(reply_markup, user_id=cid)
            ok = await _bot_api_edit(bot_token, cid, mid, text, bot_api_kb)
            if ok:
                try:
                    msg = await self.get_messages(cid, mid)
                    if msg:
                        return msg
                except Exception:
                    pass
                from pyrogram.types import Message, Chat
                return Message(id=int(mid), chat=Chat(id=int(cid), type="private"), client=self)

    try:
        return await _orig_edit_message_text(self, chat_id, message_id, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except MessageNotModified:
        return None
    except Exception as e:
        import logging
        logging.warning(f"edit_message_text fallback to raw text: {e} | Text: {text[:50]}...")
        try:
            return await _orig_edit_message_text(self, chat_id, message_id, text, parse_mode=None, reply_markup=reply_markup, **kwargs)
        except MessageNotModified:
            return None
        except Exception as e2:
            logging.error(f"edit_message_text fatal error: {e2}")
            return None
Client.edit_message_text = _patched_edit_message_text

_orig_send_photo = Client.send_photo
async def _patched_send_photo(self, chat_id, photo, caption=None, parse_mode=None, **kwargs):
    if caption and parse_mode != ParseMode.DISABLED:
        caption = convert_md_to_html_and_emojis(caption)
        parse_mode = ParseMode.HTML
    return await _orig_send_photo(self, chat_id, photo, caption=caption, parse_mode=parse_mode, **kwargs)
Client.send_photo = _patched_send_photo

_orig_send_video = Client.send_video
async def _patched_send_video(self, chat_id, video, caption=None, parse_mode=None, **kwargs):
    if caption and parse_mode != ParseMode.DISABLED:
        caption = convert_md_to_html_and_emojis(caption)
        parse_mode = ParseMode.HTML
    return await _orig_send_video(self, chat_id, video, caption=caption, parse_mode=parse_mode, **kwargs)
Client.send_video = _patched_send_video
# ================================================================

# ==================== YOUTUBE API ====================

def get_yt():
    try:
        key = get_youtube_key()
        return build("youtube", "v3", developerKey=key)
    except Exception:
        if YOUTUBE_API_KEY:
            return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        return None

# ==================== YORDAMCHI FUNKSIYALAR ====================

def fmt(num):
    """Raqamni chiroyli formatda"""
    if num is None: return "N/A"
    num = int(num)
    if num >= 1_000_000_000: return f"{num/1_000_000_000:.1f}B"
    if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
    if num >= 1_000: return f"{num/1_000:.1f}K"
    return str(num)

def fmt_full(num):
    """To'liq formatda"""
    if num is None: return "N/A"
    return f"{int(num):,}"

def growth_icon(val):
    if val > 0: return f"+{fmt(val)}"
    elif val < 0: return f"{fmt(val)}"
    return "0"

def parse_duration(dur):
    """ISO 8601 duration ni o'qiladigan formatga"""
    if not dur: return "N/A"
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', dur)
    if not match: return dur
    h, m, s = match.groups()
    parts = []
    if h: parts.append(f"{h}s")
    if m: parts.append(f"{m}d")
    if s: parts.append(f"{s}s")
    return ":".join(parts) if parts else "0:00"

def parse_duration_seconds(dur):
    """ISO 8601 ni soniyalarga"""
    if not dur: return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', dur)
    if not match: return 0
    h, m, s = match.groups()
    return int(h or 0)*3600 + int(m or 0)*60 + int(s or 0)

def time_ago(date_str):
    """Vaqtni 'X kun oldin' formatida"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        if diff.days > 365: return f"{diff.days // 365} yil oldin"
        if diff.days > 30: return f"{diff.days // 30} oy oldin"
        if diff.days > 0: return f"{diff.days} kun oldin"
        if diff.seconds > 3600: return f"{diff.seconds // 3600} soat oldin"
        if diff.seconds > 60: return f"{diff.seconds // 60} daqiqa oldin"
        return "hozirgina"
    except: return "N/A"

def estimate_earnings(views, cpm_low=0.5, cpm_high=5.0):
    """Taxminiy daromadni hisoblash"""
    low = (views / 1000) * cpm_low
    high = (views / 1000) * cpm_high
    return low, high

def engagement_rate(views, likes, comments):
    """Engagement foizini hisoblash"""
    if views == 0: return 0
    return ((likes + comments) / views) * 100

def extract_channel_id(text):
    """URL/username dan kanal identifikatorini olish"""
    if text.startswith("@"):
        return {"type": "username", "value": text[1:]}
    m = re.search(r'youtube\.com/channel/(UC[\w-]+)', text)
    if m: return {"type": "id", "value": m.group(1)}
    m = re.search(r'youtube\.com/@([\w.-]+)', text)
    if m: return {"type": "username", "value": m.group(1)}
    m = re.search(r'youtube\.com/(?:c|user)/([\w.-]+)', text)
    if m: return {"type": "username", "value": m.group(1)}
    return {"type": "username", "value": text.strip()}

def extract_video_id(text):
    """URL dan video ID"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{11})',
        r'youtube\.com/shorts/([\w-]{11})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m: return m.group(1)
    return text.strip() if len(text.strip()) == 11 else None

def extract_playlist_id(text):
    """URL dan playlist ID"""
    m = re.search(r'[?&]list=([\w-]+)', text)
    if m: return m.group(1)
    return text.strip()

# ==================== YOUTUBE API FUNKSIYALARI ====================

def get_channel(identifier):
    yt = get_yt()
    if not yt: return None
    try:
        if identifier["type"] == "id":
            r = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings,topicDetails,status", id=identifier["value"]).execute()
        else:
            r = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings,topicDetails,status", forUsername=identifier["value"]).execute()
        if not r.get("items"):
            sr = yt.search().list(part="snippet", q=identifier["value"], type="channel", maxResults=1).execute()
            if sr.get("items"):
                cid = sr["items"][0]["snippet"]["channelId"]
                r = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings,topicDetails,status", id=cid).execute()
        return r["items"][0] if r.get("items") else None
    except Exception as e:
        print(f"Channel API xato: {e}")
        return None

def get_video(video_id):
    yt = get_yt()
    if not yt: return None
    try:
        r = yt.videos().list(part="snippet,statistics,contentDetails,topicDetails,status", id=video_id).execute()
        return r["items"][0] if r.get("items") else None
    except Exception as e:
        print(f"Video API xato: {e}")
        return None

# /translate buyrug'i uchun (get_video bilan bir xil, faqat nomi mos)
get_video_stats = get_video

def get_videos_by_channel(channel_id, max_results=10, order="date"):
    yt = get_yt()
    if not yt: return []
    try:
        sr = yt.search().list(part="snippet", channelId=channel_id, order=order, type="video", maxResults=max_results).execute()
        if not sr.get("items"): return []
        ids = [i["id"]["videoId"] for i in sr["items"]]
        vr = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()
        return vr.get("items", [])
    except Exception as e:
        print(f"Videos API xato: {e}")
        return []

def get_playlists(channel_id, max_results=10):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.playlists().list(part="snippet,contentDetails", channelId=channel_id, maxResults=max_results).execute()
        return r.get("items", [])
    except: return []

def get_playlist_items(playlist_id, max_results=20):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.playlistItems().list(part="snippet,contentDetails", playlistId=playlist_id, maxResults=max_results).execute()
        return r.get("items", [])
    except: return []

def get_comments(video_id, max_results=10):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.commentThreads().list(part="snippet", videoId=video_id, maxResults=max_results, order="relevance", textFormat="plainText").execute()
        return r.get("items", [])
    except: return []

def search_youtube(query, search_type="video", max_results=10):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.search().list(part="snippet", q=query, type=search_type, maxResults=max_results).execute()
        items = r.get("items", [])
        if search_type == "video" and items:
            ids = [i["id"]["videoId"] for i in items if i["id"].get("videoId")]
            if ids:
                vr = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()
                return vr.get("items", [])
        return items
    except: return []

def get_trending(region="US", max_results=10, category_id="0"):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.videos().list(part="snippet,statistics,contentDetails", chart="mostPopular", regionCode=region, maxResults=max_results, videoCategoryId=category_id).execute()
        return r.get("items", [])
    except: return []

def get_categories(region="US"):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.videoCategories().list(part="snippet", regionCode=region).execute()
        return r.get("items", [])
    except: return []

# ==================== INLINE KEYBOARD BUILDERS ====================

def lang_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
         InlineKeyboardButton("🇪🇸 Español", callback_data="setlang_es")],
        [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="setlang_tr")],
        [InlineKeyboardButton("🏠 Bosh menyu / Main Menu", callback_data="back_main")],
    ])

def games_menu_kb(user_id=None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Omadli Quti (Mystery Box)", callback_data="box_open"),
         InlineKeyboardButton("🎰 Omad G'ildiragi (Wheel)", callback_data="spin_free")],
        [InlineKeyboardButton("⚔️ PvP Tanga Tashlash (Duel)", callback_data="game_duel_info"),
         InlineKeyboardButton("🎟️ Jekpot Mega Lotereya", callback_data="lottery_refresh")],
        [InlineKeyboardButton("🏆 Liderlar Jadvali (Top)", callback_data="menu_leaderboard"),
         InlineKeyboardButton("🎁 Do'stlarni chaqirish", callback_data="menu_referral")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
    ])

def main_menu_kb(user_id=None):
    import os
    lang = get_user_language(user_id) if user_id else "uz"
    web_url = os.environ.get("WEB_URL", WEB_APP_URL)
    kyc_text = "🛡️ 3D KYC"
    if user_id and is_user_kyc_verified(user_id):
        kyc_text = "🛡️ 3D KYC Verified"
        
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Web Dashboard", web_app=WebAppInfo(url=web_url)),
         InlineKeyboardButton(kyc_text, web_app=WebAppInfo(url=f"{web_url}/kyc/verify?user_id={user_id or 0}"))],
        [InlineKeyboardButton(t("btn_balance", lang), callback_data="menu_wallet"),
         InlineKeyboardButton(t("btn_games", lang), callback_data="menu_games")],
        [InlineKeyboardButton(t("btn_support", lang), callback_data="menu_support_desk"),
         InlineKeyboardButton(t("btn_vouchers", lang), callback_data="menu_vouchers")],
        [InlineKeyboardButton(t("btn_ig_cloner", lang), callback_data="menu_ig_cloner"),
         InlineKeyboardButton(t("btn_capcut", lang), callback_data="menu_capcut")],
        [InlineKeyboardButton(t("btn_ai_video", lang), callback_data="menu_ai_video"),
         InlineKeyboardButton(t("btn_spy", lang), callback_data="menu_spy")],
        [InlineKeyboardButton(t("btn_referral", lang), callback_data="menu_referral"),
         InlineKeyboardButton(t("btn_leaderboard", lang), callback_data="menu_leaderboard")],
        [InlineKeyboardButton(t("btn_marketplace", lang), callback_data="menu_marketplace"),
         InlineKeyboardButton("🔑 Developer API", callback_data="help_api")],
        [InlineKeyboardButton("📢 Kanal & Video", callback_data="menu_channel"),
         InlineKeyboardButton("📊 Analitika", callback_data="menu_analytics")],
        [InlineKeyboardButton(t("btn_lang", lang), callback_data="menu_lang"),
         InlineKeyboardButton(t("btn_help", lang), callback_data="menu_help")],
    ])

def wallet_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Telegram Stars orqali to'ldirish", callback_data="pay_stars_menu")],
        [InlineKeyboardButton("💎 TON (The Open Network) orqali", callback_data="pay_crypto_menu")],
        [InlineKeyboardButton("💸 Balansni Yechish (Cashout)", callback_data="menu_cashout")],
        [InlineKeyboardButton("🎟 Promokod kiritish (/redeem)", callback_data="enter_promo_code")],
        [InlineKeyboardButton("📋 To'lovlar tarixi", callback_data="pay_history")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
    ])

def stars_packages_kb():
    buttons = []
    for pkg in STARS_PACKAGES:
        buttons.append([InlineKeyboardButton(pkg["label"], callback_data=f"stars_pkg_{pkg['stars']}")])
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_wallet")])
    return InlineKeyboardMarkup(buttons)

def crypto_packages_kb():
    buttons = []
    for pkg in CRYPTO_PACKAGES:
        amt_str = str(pkg['amount']).replace('.', 'd')
        cb_val = f"crypto_pkg_{amt_str}_{pkg['asset']}"
        buttons.append([InlineKeyboardButton(pkg["label"], callback_data=cb_val)])
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_wallet")])
    return InlineKeyboardMarkup(buttons)

def marketplace_menu_kb():
    from database import get_api_keys_stock_count, get_proxies_stock_count
    stock = get_api_keys_stock_count()
    op_stock = stock.get("openrouter", 0)
    gm_stock = stock.get("gemini", 0)
    gq_stock = stock.get("groq", 0)
    pr_stock = get_proxies_stock_count()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌐 Private Proxy ($3) [{pr_stock} ta]", callback_data="mkt_view_proxy"),
         InlineKeyboardButton(f"⚡ Autostream Cloud (4k/s)", callback_data="mkt_view_autostream")],
        [InlineKeyboardButton(f"🎨 500+ Prompt Pack ($3)", callback_data="mkt_view_prompts"),
         InlineKeyboardButton(f"👑 VIP Cheksiz Pro ($15/oy)", callback_data="mkt_view_vip")],
        [InlineKeyboardButton(f"🌐 OpenRouter API ($3) [{op_stock} ta]", callback_data="mkt_view_openrouter"),
         InlineKeyboardButton(f"✨ Gemini API ($5) [{gm_stock} ta]", callback_data="mkt_view_gemini")],
        [InlineKeyboardButton(f"⚡ Groq Cloud API (10k) [{gq_stock} ta]", callback_data="mkt_view_groq"),
         InlineKeyboardButton(f"🎨 Flux.1 AI Rasm ($2/h)", callback_data="mkt_view_flux")],
        [InlineKeyboardButton(f"📲 DeepLink & QR (3k)", callback_data="mkt_view_deeplink"),
         InlineKeyboardButton(f"⚡ Video Unikal (1.5k)", callback_data="mkt_view_unikal")],
        [InlineKeyboardButton(f"✂️ 3 ta Shorts Kesish ($1)", callback_data="mkt_view_clipper"),
         InlineKeyboardButton(f"💎 Referal & Keshbek (10%)", callback_data="mkt_view_ref")],
        [InlineKeyboardButton("👍 Layk (1,500 so'm)", callback_data="mkt_order_like"),
         InlineKeyboardButton("🔔 Obuna (2,500 so'm)", callback_data="mkt_order_subscribe"),
         InlineKeyboardButton("💬 Izoh (1,000 so'm)", callback_data="mkt_order_comment")],
        [InlineKeyboardButton("🔑 Mening xaridlarim", callback_data="mkt_my_purchases"),
         InlineKeyboardButton("📋 Buyurtmalarim", callback_data="mkt_my_orders")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
    ])

def order_quantity_kb(action_type):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 ta (Test)", callback_data=f"mkt_qty_{action_type}_1"),
         InlineKeyboardButton("3 ta", callback_data=f"mkt_qty_{action_type}_3"),
         InlineKeyboardButton("5 ta", callback_data=f"mkt_qty_{action_type}_5")],
        [InlineKeyboardButton("10 ta", callback_data=f"mkt_qty_{action_type}_10"),
         InlineKeyboardButton("25 ta", callback_data=f"mkt_qty_{action_type}_25"),
         InlineKeyboardButton("50 ta", callback_data=f"mkt_qty_{action_type}_50")],
        [InlineKeyboardButton("100 ta", callback_data=f"mkt_qty_{action_type}_100")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_cancel")],
    ])

def order_confirm_kb(action_type, qty, total_cost):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, tasdiqlayman", callback_data=f"mkt_confirm_{action_type}_{qty}_{total_cost}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_cancel")],
    ])

def channel_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 To'liq statistika", callback_data="ch_full"),
         InlineKeyboardButton("👥 Obunachilar", callback_data="ch_subs")],
        [InlineKeyboardButton("🎬 So'nggi videolar", callback_data="ch_recent"),
         InlineKeyboardButton("🔥 Ommabop videolar", callback_data="ch_popular")],
        [InlineKeyboardButton("📂 Pleylistlar", callback_data="ch_playlists"),
         InlineKeyboardButton("ℹ️ Kanal haqida", callback_data="ch_about")],
        [InlineKeyboardButton("🖼 Banner/Avatar", callback_data="ch_banner"),
         InlineKeyboardButton("🔑 Kalit so'zlar", callback_data="ch_keywords")],
        [InlineKeyboardButton("⏱ Upload chastotasi", callback_data="ch_frequency"),
         InlineKeyboardButton("💰 Daromad taxmini", callback_data="ch_earnings")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def video_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 To'liq statistika", callback_data="vid_full"),
         InlineKeyboardButton("👍 Likelar", callback_data="vid_likes")],
        [InlineKeyboardButton("💬 Izohlar", callback_data="vid_comments"),
         InlineKeyboardButton("🏷 Teglar", callback_data="vid_tags")],
        [InlineKeyboardButton("🖼 Thumbnail", callback_data="vid_thumb"),
         InlineKeyboardButton("📝 Tavsif", callback_data="vid_desc")],
        [InlineKeyboardButton("⚡ Engagement", callback_data="vid_engage"),
         InlineKeyboardButton("⏱ Davomiyligi", callback_data="vid_duration")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def analytics_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 O'sish tahlili", callback_data="an_growth"),
         InlineKeyboardButton("⚖️ Solishtirish", callback_data="an_compare")],
        [InlineKeyboardButton("❤️ Engagement rate", callback_data="an_engage"),
         InlineKeyboardButton("📉 O'rtacha ko'rishlar", callback_data="an_avgviews")],
        [InlineKeyboardButton("🏆 Top videolar", callback_data="an_top"),
         InlineKeyboardButton("👎 Eng kam ko'rilgan", callback_data="an_bottom")],
        [InlineKeyboardButton("💸 Daromad taxmini", callback_data="an_earnings"),
         InlineKeyboardButton("🎯 Milestone", callback_data="an_milestone")],
        [InlineKeyboardButton("📄 To'liq hisobot", callback_data="an_report"),
         InlineKeyboardButton("🚀 Upload tezligi", callback_data="an_uploadrate")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def search_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Video qidirish", callback_data="sr_video"),
         InlineKeyboardButton("Kanal qidirish", callback_data="sr_channel")],
        [InlineKeyboardButton("Pleylist qidirish", callback_data="sr_playlist")],
        [InlineKeyboardButton("Orqaga", callback_data="back_main")],
    ])

def tracking_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="tr_add"),
         InlineKeyboardButton("➖ Kanal o'chirish", callback_data="tr_remove")],
        [InlineKeyboardButton("📋 Mening ro'yxatim", callback_data="tr_list"),
         InlineKeyboardButton("🔄 Barchasini tekshirish", callback_data="tr_checkall")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def tools_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 URL dan ID olish", callback_data="tl_id"),
         InlineKeyboardButton("🖼 Thumbnail olish", callback_data="tl_thumb")],
        [InlineKeyboardButton("⚔️ Kanal solishtirish", callback_data="tl_compare"),
         InlineKeyboardButton("🧮 Kalkulyator", callback_data="tl_calc")],
        [InlineKeyboardButton("📂 Kategoriyalar", callback_data="tl_categories"),
         InlineKeyboardButton("🌍 Davlat trending", callback_data="tl_region")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def trending_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("US", callback_data="trend_US"),
         InlineKeyboardButton("UZ", callback_data="trend_UZ"),
         InlineKeyboardButton("RU", callback_data="trend_RU")],
        [InlineKeyboardButton("KR", callback_data="trend_KR"),
         InlineKeyboardButton("JP", callback_data="trend_JP"),
         InlineKeyboardButton("GB", callback_data="trend_GB")],
        [InlineKeyboardButton("TR", callback_data="trend_TR"),
         InlineKeyboardButton("IN", callback_data="trend_IN"),
         InlineKeyboardButton("DE", callback_data="trend_DE")],
        [InlineKeyboardButton("Orqaga", callback_data="back_main")],
    ])

def channel_action_kb(channel_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 So'nggi videolar", callback_data=f"cact_recent_{channel_id}"),
         InlineKeyboardButton("🔥 Ommabop", callback_data=f"cact_popular_{channel_id}")],
        [InlineKeyboardButton("📂 Pleylistlar", callback_data=f"cact_playlists_{channel_id}"),
         InlineKeyboardButton("📈 O'sish", callback_data=f"cact_growth_{channel_id}")],
        [InlineKeyboardButton("📄 To'liq hisobot", callback_data=f"cact_report_{channel_id}"),
         InlineKeyboardButton("💰 Daromad", callback_data=f"cact_earn_{channel_id}")],
        [InlineKeyboardButton("📌 Kuzatishga olish", callback_data=f"cact_track_{channel_id}"),
         InlineKeyboardButton("🔄 Yangilash", callback_data=f"cact_refresh_{channel_id}")],
    ])

def video_action_kb(video_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Izohlar", callback_data=f"vact_comments_{video_id}"),
         InlineKeyboardButton("🏷 Teglar", callback_data=f"vact_tags_{video_id}")],
        [InlineKeyboardButton("🖼 Thumbnail", callback_data=f"vact_thumb_{video_id}"),
         InlineKeyboardButton("⚡ Engagement", callback_data=f"vact_engage_{video_id}")],
        [InlineKeyboardButton("🔄 Yangilash", callback_data=f"vact_refresh_{video_id}")],
    ])

def back_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
    ])

def help_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanal & Video", callback_data="help_channel"),
         InlineKeyboardButton("📊 Analitika & Trend", callback_data="help_analytics")],
        [InlineKeyboardButton("🧠 AI & Shorts", callback_data="help_ai"),
         InlineKeyboardButton("🎥 24/7 Jonli Efir", callback_data="help_stream")],
        [InlineKeyboardButton("🔑 Reseller & API", callback_data="help_api"),
         InlineKeyboardButton("🎰 O'yinlar & Yutuqlar", callback_data="help_games")],
        [InlineKeyboardButton("🤖 Shaxsiy Userbot", callback_data="help_userbot"),
         InlineKeyboardButton("⚙️ Sozlash & Asboblar", callback_data="help_tools")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
    ])

# ==================== BOT YARATISH ====================

def create_ytbot():
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi!")
        return None
    
    bot = Client("yt_analytics_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    
    # Adminni tekshirish: OWNER_ID, bot_admins jadvali yoki username bo'yicha
    def check_is_admin(user):
        if not user:
            return False
        if OWNER_ID and user.id == OWNER_ID:
            return True
        if is_bot_admin(user.id):
            return True
        if user.username:
            target_admin = ADMIN_USERNAME.lstrip("@").lower().strip()
            user_uname = user.username.lstrip("@").lower().strip()
            if target_admin and user_uname == target_admin:
                return True
        return False

    # /dl, /seo, /ideas, /translate kabi buyruqlar uchun kunlik limit tekshiruvi
    # (admin uchun cheklovsiz, oddiy foydalanuvchi uchun /autopost bilan bir xil limit)
    def can_use_bot(user):
        if not user:
            return False
        if check_is_admin(user):
            return True
        if not is_user_kyc_verified(user.id):
            return False
        if is_user_vip(user.id):
            return True
        daily_used = get_daily_usage(user.id)
        return daily_used < DAILY_LIMIT_USER

    # ==================== /start ====================

    # ==================== /status ====================

    # ==================== /apikeys ====================
    @bot.on_message(filters.command("apikeys") & filters.private)
    async def cmd_apikeys(client, message):
        """YouTube API kalitlari holatini tekshirish (Faqat admin uchun)"""
        from config import OWNER_ID, ADMIN_USERNAME, YOUTUBE_API_KEYS, WORKING_YT_KEYS, reset_yt_keys, remove_bad_yt_key
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        if not check_is_admin(message.from_user):
            await message.reply("❌ Bu buyruq faqat admin uchun!")
            return
            
        if not YOUTUBE_API_KEYS:
            await message.reply("⚠️ Hech qanday YouTube API kaliti topilmadi (.env faylni tekshiring).")
            return
            
        wait_msg = await message.reply(f"🔍 **{len(YOUTUBE_API_KEYS)}** ta API kalit tekshirilmoqda...")
        
        # Reset before checking
        reset_yt_keys()
        
        results = []
        import asyncio
        
        def check_key(key):
            try:
                # Quota ni tekshirish uchun kichik so'rov
                yt = build('youtube', 'v3', developerKey=key, cache_discovery=False)
                yt.videos().list(part="id", chart="mostPopular", maxResults=1).execute()
                return True, None
            except HttpError as e:
                err_msg = str(e)
                if "quotaExceeded" in err_msg or "dailyLimitExceeded" in err_msg:
                    return False, "Quota Limit"
                elif "API key not valid" in err_msg or "API_KEY_INVALID" in err_msg:
                    return False, "Yaroqsiz kalit"
                else:
                    return False, f"Xato: {err_msg[:50]}"
            except Exception as e:
                return False, f"Xato: {str(e)[:50]}"
                
        good_keys = 0
        for idx, key in enumerate(YOUTUBE_API_KEYS, 1):
            masked_key = f"{key[:5]}...{key[-5:]}" if len(key) > 10 else "Noma'lum"
            is_valid, err_reason = await asyncio.to_thread(check_key, key)
            
            if is_valid:
                results.append(f"{idx}. `{masked_key}` - ✅ Ishlayapti")
                good_keys += 1
            else:
                results.append(f"{idx}. `{masked_key}` - ❌ {err_reason}")
                remove_bad_yt_key(key)
                
        res_text = f"📊 **API Kalitlar Holati:**\n\n" + "\n".join(results)
        res_text += f"\n\n🔄 **Jami ishlayotganlar:** {good_keys}/{len(YOUTUBE_API_KEYS)}"
        if good_keys == 0:
            res_text += "\n⚠️ Barcha kalitlar limitdan oshgan yoki yaroqsiz!"
        else:
            res_text += "\n✅ Ishlaydigan kalitlar avtomatik tanlandi."
            
        await wait_msg.edit_text(res_text, parse_mode=ParseMode.MARKDOWN)

    @bot.on_message(filters.command("status") & filters.private)
    async def cmd_status(client, message):
        """Kanal va Proxy ulanish holatini ko'rish — /status"""
        tg_user_id = str(message.from_user.id)
        
        # 1. YT Login Status
        from database import get_yt_connection
        conn = get_yt_connection(tg_user_id)
        
        if conn:
            yt_status = f"✅ Ulangan\n📺 Kanal: **{conn['yt_channel_title']}**\n🆔 ID: `{conn['yt_channel_id']}`"
        else:
            yt_status = "❌ Ulanmagan\n`/ytlogin` orqali ulaning."
            
        # 2. Proxy Status
        from database import get_config
        import aiohttp
        proxy_url = get_config("proxy_url")
        
        proxy_status = "❌ O'rnatilmagan"
        if proxy_url:
            proxy_status = f"🔄 Tekshirilmoqda... (`{proxy_url[:20]}...`)"
            wait_msg = await message.reply("⏳ Proxy ulanishi tekshirilmoqda...")
            is_working = False
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://www.youtube.com", proxy=proxy_url, timeout=5) as resp:
                        if resp.status == 200:
                            is_working = True
            except Exception:
                pass
            
            if is_working:
                proxy_status = f"✅ O'rnatilgan va Ishlayapti! (`{proxy_url[:20]}...`)"
            else:
                proxy_status = f"⚠️ O'rnatilgan, lekin ulanishda xatolik (Ishlamayapti)"
            await wait_msg.delete()
            
        text = f"📊 **Tizim Holati**\n\n**YouTube Holati:**\n{yt_status}\n\n**Proxy Holati:**\n{proxy_status}"
        await message.reply(text, parse_mode=ParseMode.MARKDOWN)

    @bot.on_message(filters.command("start"))
    async def start_cmd(client, message):
        user_id = message.from_user.id
        is_admin = check_is_admin(message.from_user)

        # 1. Referal argument tekshiruvi: /start ref_123456 yoki /start 123456
        parts = message.text.strip().split()
        if len(parts) > 1:
            ref_arg = parts[1]
            ref_id_str = ref_arg.replace("ref_", "")
            if ref_id_str.isdigit():
                ref_id = int(ref_id_str)
                if ref_id != user_id:
                    added = set_user_referrer(user_id, ref_id)
                    if added:
                        try:
                            ref_lang = get_user_language(ref_id)
                            notify_txt = t("ref_joined_notify", ref_lang)
                            await client.send_message(ref_id, notify_txt)
                        except Exception:
                            pass

        # 2. Xavfsizlik & KYC tekshiruvi (Adminlardan tashqari hamma uchun majburiy)
        if not is_admin and not is_user_kyc_verified(user_id):
            import os
            ph = get_telegram_phone(user_id)
            web_url = os.environ.get("WEB_URL", WEB_APP_URL)
            if not ph:
                # 1-bosqich: Faqat Telegram orqali telefon raqam ulashish (qo'lda yozish taqiqlangan)
                reply_kb = ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Telefon raqamimni ulashish", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
                txt = (
                    f"{e('SHIELD')} <b>Xavfsizlik & 3D Biometrik Identifikatsiya</b>\n\n"
                    f"Hurmatli foydalanuvchi, firibgarlik (fake va soxta akkauntlar)ning oldini olish "
                    f"hamda hisobingiz xavfsizligini ta'minlash uchun botdan foydalanishdan avval "
                    f"shaxsingizni tasdiqlashingiz shart!\n\n"
                    f"⚠️ <b>Qo'lda telefon raqam yozish qabul qilinmaydi (aldovning oldini olish uchun).</b>\n"
                    f"Iltimos, pastdagi <b>«📱 Telefon raqamimni ulashish»</b> tugmasi orqali o'z akkauntingizga ulangan raqamni yuboring:"
                )
                await message.reply_text(txt, reply_markup=reply_kb)
                return
            else:
                # 2-bosqich: 3D yuz skaneri (MediaPipe)
                txt = (
                    f"{e('SHIELD')} <b>Shaxsingizni tasdiqlash (2-bosqich)</b>\n\n"
                    f"📱 <b>Bog'langan raqam:</b> <code>{ph}</code>\n\n"
                    f"Telefon raqamingiz muvaffaqiyatli saqlangan. Endi pastdagi tugmani bosib "
                    f"<b>3D Yuz Skaneri (MediaPipe)</b> orqali biometrik tekshiruvdan o'ting.\n\n"
                    f"<i>Skanerdan o'tganingizdan so'ng botning barcha xizmatlari siz uchun avtomatik ochiladi!</i>"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛡️ 3D Yuz Skaneridan O'tish", web_app=WebAppInfo(url=f"{web_url}/kyc/verify?user_id={user_id}&phone={ph}"))]
                ])
                await message.reply_text("Iltimos, pastdagi tugma orqali yuz skaneridan o'ting:", reply_markup=ReplyKeyboardRemove())
                await message.reply_text(txt, reply_markup=kb)
                return

        # Agar foydalanuvchi tasdiqlangan (yoki admin) bo'lsa:
        lang = get_user_language(user_id)

        # 3. Deep link PvP duel chaqiruvi tekshiruvi: /start duel_5000
        if len(parts) > 1 and parts[1].startswith("duel_"):
            d_amt = parts[1].replace("duel_", "")
            if d_amt.isdigit():
                await message.reply_text(
                    f"⚔️ <b>Do'stingiz sizni PvP Duelga chaqirdi!</b>\n\n"
                    f"💰 Garov summasi: <code>{int(d_amt):,} so'm</code>\n\n"
                    f"O'ynash uchun buyruq: <code>/duel {d_amt} burgut</code> yoki <code>/duel {d_amt} panja</code>"
                )

        # 4. Majburiy kanal obunasini tekshirish (Admin bo'lmasa)
        ch = get_config("force_sub_channel")
        if ch and not is_admin:
            try:
                member = await client.get_chat_member(ch, user_id)
                if not member or getattr(member, "status", None) in ("left", "kicked"):
                    ch_clean = ch.replace("@", "")
                    ch_url = f"https://t.me/{ch_clean}"
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton(t("btn_join_channel", lang), url=ch_url)],
                        [InlineKeyboardButton(t("btn_verify_sub", lang), callback_data="sub_check")]
                    ])
                    await message.reply_text(t("force_sub_title", lang), reply_markup=kb)
                    return
            except Exception as _fe:
                print(f"forcesub start error: {_fe}")

        name = (message.from_user.first_name or "Foydalanuvchi") if message.from_user else "Foydalanuvchi"
        text = t("main_menu", lang, name=name)
        await message.reply_text(text, reply_markup=main_menu_kb(user_id))

    # ==================== TELEGRAM KONTAKT (TELEFON RAQAM) QABUL QILISH ====================
    @bot.on_message(filters.contact & filters.private)
    async def handle_contact_share(client, message):
        user_id = message.from_user.id
        contact = message.contact

        if contact.user_id != user_id:
            await message.reply_text(
                "❌ <b>Xatolik!</b> Iltimos, faqat o'zingizning Telegram hisobingizga ulangan raqamni ulashing!\n"
                "Boshqa shaxslarning kontaktini yuborish taqiqlanadi.",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📱 Telefon raqamimni ulashish", request_contact=True)]], resize_keyboard=True)
            )
            return

        phone = contact.phone_number.strip()
        save_telegram_phone(user_id, phone)
        import os
        web_url = os.environ.get("WEB_URL", WEB_APP_URL)
        
        txt = (
            f"{e('CHECK')} <b>Telefon raqamingiz muvaffaqiyatli tasdiqlandi:</b> <code>{phone}</code>\n\n"
            f"{e('SHIELD')} <b>2-bosqich:</b> Anti-Sybil 3D Biometrik Yuz Skaneri (MediaPipe 468 mesh).\n\n"
            f"Kamerangizni yoqib, boshni to'g'riga, chapga va o'ngga burib haqiqiy shaxs ekanligingizni tasdiqlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡️ 3D Yuz Skaneridan O'tish (KYC)", web_app=WebAppInfo(url=f"{web_url}/kyc/verify?user_id={user_id}&phone={phone}"))]
        ])
        await message.reply_text("Telefon raqamingiz tizimga bog'landi.", reply_markup=ReplyKeyboardRemove())
        await message.reply_text(txt, reply_markup=kb)
    
    # ==================== /help ====================
    HELP_MAIN_TEXT = (
        "📖 <b>YouTube Analytics & Automation Bot — Yordam</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang va unga tegishli buyruqlar bilan tanishing:\n\n"
        "⚡ <b>Tezkor buyruqlar:</b>\n"
        "• <code>/start</code> — Botni ishga tushirish\n"
        "• <code>/menu</code> — Asosiy menyu\n"
        "• <code>/balance</code> — Balansni tekshirish (TON & Stars)\n"
        "• <code>/box</code> — Omadli Quti (Mystery Box)\n"
        "• <code>/wheel</code> — Omad G'ildiragi (Kunlik bepul spin)\n"
        "• <code>/duel</code> — PvP Tanga Tashlash (Coin Flip)\n"
        "• <code>/lottery</code> — Jekpot Mega Lotereya\n"
        "• <code>/api</code> — Developer & Reseller REST API\n"
        "• <code>/dashboard</code> — WebApp Dashboard Mini App\n"
        "• <code>/shortfactory</code> — AI Shorts video generatori\n"
        "• <code>/autostream</code> — 24/7 Jonli efir boshqaruvchisi\n\n"
        "👇 <i>Bo'limlar bo'yicha batafsil ko'rish uchun quyidagi tugmalardan foydalaning:</i>"
    )

    HELP_SECTIONS = {
        "help_channel": (
            "📢 <b>Kanal va Video Buyruqlari:</b>\n\n"
            "• <code>/channel &lt;kanal&gt;</code> — Kanal umumiy statistikasi\n"
            "• <code>/about &lt;kanal&gt;</code> — Kanal haqida to'liq ma'lumot\n"
            "• <code>/subs &lt;kanal&gt;</code> — Obunachilar soni\n"
            "• <code>/totalviews &lt;kanal&gt;</code> — Jami ko'rishlar soni\n"
            "• <code>/videocount &lt;kanal&gt;</code> — Jami videolar soni\n"
            "• <code>/banner &lt;kanal&gt;</code> — Kanal banner rasmi\n"
            "• <code>/avatar &lt;kanal&gt;</code> — Profil rasmi (HD)\n"
            "• <code>/keywords &lt;kanal&gt;</code> — Kanal kalit so'zlari\n"
            "• <code>/desc &lt;kanal&gt;</code> — Kanal tavsifi\n"
            "• <code>/video &lt;url&gt;</code> — Video statistikasi\n"
            "• <code>/recent &lt;kanal&gt;</code> — Oxirgi yuklangan videolar\n"
            "• <code>/popular &lt;kanal&gt;</code> — Eng mashhur videolar\n"
            "• <code>/comments &lt;url&gt;</code> — Izohlarni ko'rish\n"
            "• <code>/tags &lt;url&gt;</code> — Video teglari\n"
            "• <code>/thumbnail &lt;url&gt;</code> — Thumbnail muqovani olish\n"
            "• <code>/playlists &lt;kanal&gt;</code> — Pleylistlar ro'yxati\n"
            "• <code>/dl &lt;url&gt;</code> — Video yoki audioni yuklab olish"
        ),
        "help_analytics": (
            "📊 <b>Analitika va Monitoring Buyruqlari:</b>\n\n"
            "• <code>/compare &lt;k1&gt; &lt;k2&gt;</code> — Kanallarni o'zaro solishtirish\n"
            "• <code>/growth &lt;kanal&gt;</code> — Kanal o'sish dinamikasi\n"
            "• <code>/engagement &lt;kanal&gt;</code> — Auditoriya faolligi (Like/Comment nisbati)\n"
            "• <code>/earnings &lt;kanal&gt;</code> — Kanalning taxminiy daromadi\n"
            "• <code>/milestone &lt;kanal&gt;</code> — Keyingi marraga erishish vaqti\n"
            "• <code>/report &lt;kanal&gt;</code> — To'liq tahliliy hisobot\n"
            "• <code>/search &lt;so'z&gt;</code> — Video qidiruv\n"
            "• <code>/trending</code> — YouTube trenddagi videolar\n"
            "• <code>/track &lt;kanal&gt;</code> — Raqobatchini kuzatuvga olish\n"
            "• <code>/untrack &lt;kanal&gt;</code> — Kuzatuvdan chiqarish\n"
            "• <code>/mylist</code> — Kuzatuvdagi kanallar ro'yxati\n"
            "• <code>/checkall</code> — Barcha kuzatuvdagilarni tekshirish\n"
            "• <code>/live &lt;kanal&gt;</code> — Jonli efir bor-yo'qligini tekshirish"
        ),
        "help_ai": (
            "🧠 <b>AI Yordamchi va Avtomatlashtirish:</b>\n\n"
            "• <code>/shortfactory [mavzu]</code> — Shorts Factory (AI video yasash)\n"
            "• <code>/seo &lt;mavzu&gt;</code> — SEO tahlili va kalit so'zlar\n"
            "• <code>/tagsgen &lt;mavzu&gt;</code> — AI SEO teglar generatsiyasi\n"
            "• <code>/clickbait &lt;mavzu&gt;</code> — Jozibador sarlavhalar\n"
            "• <code>/ideas &lt;mavzu&gt;</code> — Video g'oyalari\n"
            "• <code>/script &lt;mavzu&gt;</code> — Video ssenariysi\n"
            "• <code>/shorts &lt;url&gt;</code> — Shorts uchun ssenariy g'oyalari\n"
            "• <code>/thumbidea &lt;mavzu&gt;</code> — Thumbnail g'oyalari\n"
            "• <code>/summarize &lt;url&gt;</code> — Video mazmunini qisqartirish\n"
            "• <code>/roast &lt;kanal&gt;</code> — Kanalni AI yordamida tanqid qilish\n"
            "• <code>/audit &lt;kanal&gt;</code> — Kanal auditi\n"
            "• <code>/autopost &lt;soni&gt; &lt;qidiruv&gt;</code> — Avto-post qisqa video yuklash\n"
            "• <code>/autopilot</code> — Avtopilot sozlamalari"
        ),
        "help_stream": (
            "🎥 <b>24/7 Jonli Efir va Reaksiya:</b>\n\n"
            "• <code>/setstreamkey &lt;key&gt;</code> — YouTube Stream Key sozlash\n"
            "• <code>/autostream start &lt;qidiruv&gt;</code> — 24/7 jonli efirni boshlash\n"
            "• <code>/autostream stop</code> — Jonli efirni to'xtatish\n"
            "• <code>/autostream status</code> — Efir holatini tekshirish\n"
            "• <code>/reaction &lt;video&gt; &lt;reaktor&gt;</code> — PiP Reaksiya video yasash"
        ),
        "help_api": (
            "🔑 <b>Developer & Reseller REST API:</b>\n\n"
            "• <code>/api</code> — Shaxsiy API kalitingiz va Python kodi\n"
            "• <code>/stock</code> — Do'kondagi API kalitlar va proksilar soni\n"
            "• <code>/dashboard</code> — Developer WebApp Mini App paneli\n"
            "• <code>/webhook &lt;url&gt; [hafta]</code> — Real-time Webhook obunasi ($3/hafta)\n"
            "• <code>/createbot &lt;token&gt;</code> — 1-Click White-Label Bot ($50 VIP)\n\n"
            "🌐 <i>REST API Dokumentatsiyasi: /api buyrug'i orqali ochiladi.</i>"
        ),
        "help_games": (
            "🎰 <b>O'yinlar va Monetizatsiya:</b>\n\n"
            "• <code>/box</code> — Omadli Quti (Mystery Box — 6,000 so'm / 15 Stars)\n"
            "• <code>/wheel</code> yoki <code>/spin</code> — Omad G'ildiragi (Kunlik bepul spin)\n"
            "• <code>/duel &lt;summa&gt; [burgut|panja]</code> — PvP Tanga Tashlash (Coin Flip)\n"
            "• <code>/lottery</code> — Jekpot Mega Lotereya (3,000 so'm / bilet)\n"
            "• <code>/redeem &lt;kod&gt;</code> — Sovg'a vaucherini faollashtirish\n"
            "• <code>/makegift &lt;summa&gt; [soni]</code> — Sovg'a vaucherlari yaratish (Admin)\n"
            "• <code>/balance</code> — Balansni tekshirish va to'ldirish"
        ),
        "help_userbot": (
            "🤖 <b>Shaxsiy Userbot Buyruqlari (Guruh va chatlarda):</b>\n\n"
            "• <code>.ar on/off</code> — Avto-javob funksiyasi\n"
            "• <code>.gif on/off</code> — GIF animatsiya yuborish\n"
            "• <code>.react on/off</code> — Avto-reaksiyalar\n"
            "• <code>.arstyle</code> — Shaxsiy yozish uslubini o'rgatish\n"
            "• <code>.arvoice &lt;voice&gt;</code> — Ovozli xabar bilan javob (edge-tts)\n"
            "• <code>.arsetprompt &lt;text&gt;</code> — Userbot promptini o'rnatish\n"
            "• <code>.arblock &lt;id&gt;</code> — ID bo'yicha bloklash\n"
            "• <code>.arunblock &lt;id&gt;</code> — Blokdan chiqarish\n"
            "• <code>.arstatus</code> — Userbot holatini ko'rish\n"
            "• <code>.arhelp</code> — Userbot yordami"
        ),
        "help_tools": (
            "⚙️ <b>Sozlash va Qo'shimcha Asboblar:</b>\n\n"
            "• <code>/ytlogin</code> — YouTube kanalini Google orqali ulash\n"
            "• <code>/login_status</code> — Ulangan kanallar ro'yxati\n"
            "• <code>/delaccount</code> — Ulangan kanalni uzish\n"
            "• <code>/defaultacc</code> — Asosiy kanalni tanlash\n"
            "• <code>/setcookies</code> — YouTube Cookies faylini yuklash\n"
            "• <code>/setproxy &lt;ip:port&gt;</code> — Shaxsiy proksi o'rnatish\n"
            "• <code>/myproxy</code> — Joriy proksini ko'rish\n"
            "• <code>/setton &lt;manzil&gt;</code> — TON hamyon manzilini kiritish\n"
            "• <code>/myton</code> — Saqlangan TON hamyon\n"
            "• <code>/id &lt;url&gt;</code> — Video/kanal URL dan ID ajratish\n"
            "• <code>/categories</code> — YouTube kategoriyalari\n"
            "• <code>/ping</code> — Server tezligini tekshirish"
        )
    }

    @bot.on_message(filters.command("help"))
    async def help_cmd(client, message):
        await message.reply_text(HELP_MAIN_TEXT, reply_markup=help_menu_kb())

    @bot.on_callback_query(filters.regex(r"^help_(.+)$"))
    async def help_callback(client, callback_query: CallbackQuery):
        sec = callback_query.matches[0].group(1)
        full_key = f"help_{sec}"
        if full_key in HELP_SECTIONS:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Yordam bo'limlari", callback_data="help_main"),
                 InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
            ])
            await callback_query.message.edit_text(HELP_SECTIONS[full_key], reply_markup=kb)
        else:
            await callback_query.message.edit_text(HELP_MAIN_TEXT, reply_markup=help_menu_kb())
        await callback_query.answer()
    
    # ==================== /myid ====================
    @bot.on_message(filters.command("myid"))
    async def myid_cmd(client, message):
        user_id = message.from_user.id
        await message.reply_text(
            f"{e('PIN')} **Sizning Telegram ID raqamingiz:**\n\n"
            f"`{user_id}`\n\n"
            f"Buni Web Dashboard tizimiga kirish uchun ishlating.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )
    
    @bot.on_message(filters.command("menu"))
    async def menu_cmd(client, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        name = (message.from_user.first_name or "Foydalanuvchi") if message.from_user else "Foydalanuvchi"
        await message.reply_text(t("main_menu", lang, name=name), reply_markup=main_menu_kb(user_id))

    # ==================== /balance & /balans ====================
    @bot.on_message(filters.command(["balance", "balans"]))
    async def balance_cmd(client, message):
        user_id = message.from_user.id
        bal = get_user_balance(user_id)
        text = (
            f"{e('MONEY')} <b>Sizning Balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"{e('STAR')} <b>Telegram Stars</b> yoki {e('CRYPTO')} <b>CryptoPay</b> orqali "
            f"hisobingizni bir zumda to'ldirishingiz mumkin.\n\n"
            f"{e('PIN')} To'lov usulini tanlang:"
        )
        await message.reply_text(text, reply_markup=wallet_menu_kb())

    # ==================== /marketplace & /xizmatlar ====================
    @bot.on_message(filters.command(["marketplace", "xizmatlar"]))
    async def marketplace_cmd(client, message):
        user_id = message.from_user.id
        if not can_use_bot(message.from_user):
            await message.reply_text(f"{e('WARN')} Ushbu bo'limdan foydalanish uchun avval shaxsingizni tasdiqlang! /start ni bosing.")
            return
        bal = get_user_balance(user_id)
        from database import get_api_keys_stock_count, get_proxies_stock_count
        stock = get_api_keys_stock_count()
        op_stock = stock.get("openrouter", 0)
        gm_stock = stock.get("gemini", 0)
        gq_stock = stock.get("groq", 0)
        pr_stock = get_proxies_stock_count()
        text = (
            f"{e('CASH')} <b>Marketplace & Raqamli Xizmatlar Do'koni</b>\n\n"
            f"{e('MONEY')} <b>Joriy balans:</b> <code>{bal:,} so'm</code>\n\n"
            f"<b>🌐 Proxy & Server Quvvati:</b>\n"
            f"• {e('PROXY')} <b>Dedicated Private Proxy:</b> $3 (38,000 so'm) — <i>Zaxirada: {pr_stock} ta</i>\n"
            f"• {e('STREAM')} <b>24/7 Autostream Cloud Slot:</b> $0.5 / soat (6,000 so'm/soat)\n\n"
            f"<b>🤖 AI API Kalitlar:</b>\n"
            f"• {e('OPENROUTER')} <b>OpenRouter API ($3):</b> 38,000 so'm — <i>Zaxirada: {op_stock} ta</i>\n"
            f"• {e('GEMINI')} <b>Google Gemini API ($5):</b> 64,000 so'm — <i>Zaxirada: {gm_stock} ta</i>\n"
            f"• {e('GROQ')} <b>Groq Cloud API (gptoss 120b):</b> 10,000 so'm — <i>Zaxirada: {gq_stock} ta</i>\n\n"
            f"<b>🎨 AI Kreativ & Kontent:</b>\n"
            f"• {e('FLUX')} <b>Flux.1 AI Rasm Generatsiya:</b> $2/hafta (25,000 so'm, 25 ta rasm)\n"
            f"• {e('IDEA')} <b>500+ Viral Prompt & SEO Tag Pack:</b> $3 (38,000 so'm)\n"
            f"• {e('CLIPPER')} <b>3 ta Vertical Shorts Kesish:</b> $1 (12,800 so'm) / video\n\n"
            f"<b>⚡ Kanal Rivojlantirish & DeepLink:</b>\n"
            f"• {e('QR_DEEPLINK')} <b>YouTube DeepLink & Smart QR:</b> 3,000 so'm\n"
            f"• {e('LIGHTNING')} <b>Video Unikalizatsiya & Content ID:</b> 1,500 so'm\n"
            f"• 👑 <b>VIP Cheksiz Pro Obuna:</b> $15 / oy (192,000 so'm)\n"
            f"• 💎 <b>Referal & 10% Keshbek Tizimi</b>\n\n"
            f"{e('PIN')} Kerakli mahsulot yoki xizmatni tanlang:"
        )
        await message.reply_text(text, reply_markup=marketplace_menu_kb())

    # ==================== /kyc ====================
    @bot.on_message(filters.command("kyc"))
    async def kyc_cmd(client, message):
        user_id = message.from_user.id
        from database import is_user_kyc_verified, get_user_kyc
        is_verified = is_user_kyc_verified(user_id)
        web_url = os.environ.get("WEB_URL", WEB_APP_URL)
        
        if is_verified:
            kyc_data = get_user_kyc(user_id) or {}
            ph = str(kyc_data.get("phone_number", ""))
            phone_masked = (ph[:4] + " *** ** " + ph[-2:]) if len(ph) > 6 else ph
            verified_at = str(kyc_data.get("verified_at", ""))[:19]
            text = (
                f"{e('VERIFIED')} <b>3D Biometrik Identifikatsiya: TASDIQLANGAN</b>\n\n"
                f"✅ <b>Sizning shaxsingiz real tasdiqlangan!</b>\n"
                f"🛡️ <b>Anti-Sybil Holati:</b> Real Foydalanuvchi\n"
                f"📱 <b>Bog'langan telefon:</b> <code>{phone_masked}</code>\n"
                f"📅 <b>Tasdiqlangan sana:</b> {verified_at}\n\n"
                f"✨ Barcha YouTube xizmatlari va do'kon siz uchun to'liq ochiq."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛡️ Sertifikatni Ko'rish", web_app=WebAppInfo(url=f"{web_url}/kyc/verify?user_id={user_id}"))],
                [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
            ])
            await message.reply_text(text, reply_markup=kb)
            return

        text = (
            f"{e('SHIELD')} <b>3D Yuz & Pasport Biometrik Identifikatsiyasi</b>\n\n"
            f"Holat: ⚠️ <b>Hali tasdiqlanmagansiz!</b>\n\n"
            f"Anti-Sybil tizimi orqali har bir shaxs faqat 1 ta Telegram akkaunt orqali ro'yxatdan o'tishi mumkin.\n"
            f"Kameraga ruxsat berib haqiqiy yuzingizni skanerlash uchun quyidagi tugmani bosing:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡️ 3D Yuz Skanerini Ochish", web_app=WebAppInfo(url=f"{web_url}/kyc/verify?user_id={user_id}"))],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await message.reply_text(text, reply_markup=kb)

    # ==================== /instagram ====================
    @bot.on_message(filters.command("instagram"))
    async def instagram_cmd(client, message):
        text = (
            f"{e('INSTA')} <b>Instagram Reels Yuklash & YouTube Shorts</b>\n\n"
            f"{e('LIGHTNING')} Instagram Reels havolasini shunchaki botga yuboring!\n\n"
            f"Avtomatik imkoniyatlar:\n"
            f"• {e('CHECK')} Eng yuqori sifatda videoni yuklash\n"
            f"• {e('SHIELD')} Content ID (avtorlik huquqi) bloklanishiga qarshi audio pitch va video EQ filtrlash\n"
            f"• {e('SHORTS')} 1 tugma bilan YouTube kanalingizga Shorts qilib joylash!\n\n"
            f"<i>Misol havola: https://www.instagram.com/reel/C7.../</i>"
        )
        await message.reply_text(text, reply_markup=main_menu_kb(message.from_user.id))
    
    # ==================== /flux (FLUX.1 AI RASM GENERATSIYASI) ====================
    @bot.on_message(filters.command(["flux", "fluxai"]) & filters.private)
    async def flux_cmd(client, message):
        user = message.from_user
        if not can_use_bot(user):
            await message.reply_text(f"{e('SHIELD')} <b>Iltimos, avval 3D identifikatsiyadan o'ting!</b>\n/start ni bosing.")
            return

        user_id = user.id
        quota = get_flux_quota(user_id)
        if not quota.get("active") or quota.get("left", 0) <= 0:
            text = (
                f"{e('FLUX')} <b>Flux.1 AI Tasvir Generatori Obunasi</b>\n\n"
                f"Sizda faol Flux.1 obunasi mavjud emas yoki haftalik 25 ta generatsiya limiti tugagan!\n\n"
                f"💵 <b>Haftalik obuna narxi:</b> $2 (<code>25,000 so'm</code> / hafta)\n"
                f"🎯 <b>Limit:</b> Haftasiga 25 ta fotorealistik rasm generatsiyasi.\n\n"
                f"Obunani xarid qilish uchun pastdagi tugmani bosing:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{e('FLUX')} Flux.1 Obunani Xarid Qilish", callback_data="mkt_view_flux")],
                [InlineKeyboardButton("🛒 Do'kon", callback_data="menu_marketplace")]
            ])
            await message.reply_text(text, reply_markup=kb)
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2 or not args[1].strip():
            await message.reply_text(
                f"{e('FLUX')} <b>Flux.1 AI — Tasvir yaratish:</b>\n\n"
                f"Foydalanish: <code>/flux &lt;tasvir prompti&gt;</code>\n"
                f"Masalan: <code>/flux cybernetic lion in neon tokyo street, 8k, photorealistic</code>\n\n"
                f"🎯 Qolgan generatsiya balansingiz: <b>{quota.get('left')} ta</b>"
            )
            return

        prompt_text = args[1].strip()
        wait_msg = await message.reply_text(f"{e('WAIT')} <b>Flux.1 AI tasvir yaratmoqda...</b>\n<i>Prompt: {prompt_text}</i>")

        try:
            encoded_prompt = urllib.parse.quote(prompt_text)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=1024&height=1024&nologo=true"
            use_flux_credit(user_id)
            updated_quota = get_flux_quota(user_id)
            caption = (
                f"{e('FLUX')} <b>Flux.1 AI Tasvir Tayyor!</b>\n\n"
                f"📝 <b>Prompt:</b> <code>{prompt_text}</code>\n"
                f"🎯 <b>Qolgan limit:</b> <code>{updated_quota.get('left')} ta</code>\n"
                f"📅 <b>Obuna tugash sanasi:</b> <i>{str(updated_quota.get('expires_at', ''))[:16]}</i>"
            )
            await message.reply_photo(photo=image_url, caption=caption)
            await wait_msg.delete()
        except Exception as err:
            await wait_msg.edit_text(f"{e('ERROR')} Tasvir yaratishda xatolik: {err}")

    # ==================== /ping ====================
    @bot.on_message(filters.command("ping"))
    async def ping_cmd(client, message):
        start = datetime.now()
        msg = await message.reply_text("Pong!")
        diff = (datetime.now() - start).microseconds / 1000
        await msg.edit_text(f"Pong! `{diff:.0f}ms`", parse_mode=ParseMode.MARKDOWN)

    # ==================== /setstreamkey ====================
    @bot.on_message(filters.command("setstreamkey"))
    async def setstreamkey_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/setstreamkey <YouTube Stream Key>`")
            return
        
        from database import set_stream_key
        key = args[1].strip()
        if set_stream_key(message.from_user.id, key):
            await message.reply_text("✅ Stream Key muvaffaqiyatli saqlandi! Endi `/autostream start` buyrug'idan foydalanishingiz mumkin.")
        else:
            await message.reply_text("❌ Stream Keyni saqlashda xatolik yuz berdi. (Avval /ytlogin orqali ulaning).")

    # ==================== /autostream ====================
    @bot.on_message(filters.command("autostream"))
    async def autostream_cmd(client, message):
        args = message.text.split(maxsplit=2)
        if len(args) < 2:
            await message.reply_text(
                "📡 **Autostream buyruqlari:**\n\n"
                "`/autostream start @Username` — kanal Shorts videolaridan stream\n"
                "`/autostream start lofi music` — mavzu bo'yicha stream\n"
                "`/autostream stop` — to'xtatish\n"
                "`/autostream status` — holat tekshirish\n\n"
                "**Misol:**\n"
                "`/autostream start @HisYTStory`"
            )
            return

        action = args[1].lower()
        tg_user_id = message.from_user.id

        if action == "start":
            if len(args) < 3:
                await message.reply_text(
                    "❌ Manba kiriting!\n\n"
                    "Kanal: `/autostream start @Username`\n"
                    "Mavzu: `/autostream start lofi music`"
                )
                return
            query = args[2].strip()

            # ROLE=main — to'g'ridan chaqirmasdan DB queue ga yozamiz
            from database import get_stream_key, create_stream_task, get_user_stream_status
            stream_key = get_stream_key(tg_user_id)
            if not stream_key:
                await message.reply_text(
                    "❌ Stream Key o'rnatilmagan!\n\n"
                    "YouTube Studio → Go Live → Stream Settings → Stream Key\n"
                    "Keyin: `/setstreamkey <key>`"
                )
                return

            # Avvalgi aktiv stream bormi?
            existing = get_user_stream_status(tg_user_id)
            if existing:
                await message.reply_text(
                    "⚠️ Sizda allaqachon bitta translatsiya jarayonda!\n"
                    "Avval to'xtating: `/autostream stop`"
                )
                return

            task_id = create_stream_task(tg_user_id, message.chat.id, query, stream_key)
            if task_id:
                await message.reply_text(
                    f"📡 **Stream navbatga qo'shildi!**\n\n"
                    f"🔍 Manba: `{query}`\n"
                    f"🆔 Task ID: `{task_id}`\n\n"
                    "Bo'sh streamer qidirilmoqda...\n"
                    "Holat: `/autostream status`"
                )
                # ROLE=main: avval tashqi STREAMER_URLS dagi bo'sh serverga push
                # qilishga urinamiz; hech kim bo'sh bo'lmasa RAM limiti ichida
                # main o'zi bajaradi; aks holda task DB da 'pending' qoladi va
                # istalgan streamer (poll orqali) yoki keyingi dispatch uni oladi.
                try:
                    from main import dispatch_or_run_stream
                    import asyncio as _asyncio
                    _asyncio.create_task(dispatch_or_run_stream(task_id))
                except Exception as _dispatch_err:
                    print(f"[stream dispatch] xato: {_dispatch_err}")
            else:
                await message.reply_text("❌ Stream task yaratishda xatolik yuz berdi.")

        elif action == "stop":
            from database import cancel_user_stream_tasks, get_user_stream_status
            task = get_user_stream_status(tg_user_id)
            cancel_user_stream_tasks(tg_user_id)
            await message.reply_text("🛑 Stream to'xtatish buyrug'i yuborildi. Streamer worker uni to'xtatadi.")

        elif action == "status":
            from database import get_user_stream_status
            task = get_user_stream_status(tg_user_id)
            if task:
                await message.reply_text(
                    f"📊 **Stream holati:** `{task['status']}`\n"
                    f"🔍 Manba: `{task['search_query']}`\n"
                    f"🕐 Boshlangan: `{task['created_at']}`"
                )
            else:
                await message.reply_text("🔴 Hozir hech qanday stream ketmayapti.")
        else:
            await message.reply_text("Noma'lum komanda. Foydalanish: `start`, `stop`, `status`")
    
    # ==================== /channel ====================
    @bot.on_message(filters.command("channel"))
    async def channel_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/channel <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        if not YOUTUBE_API_KEY:
            await message.reply_text("YouTube API kaliti sozlanmagan!")
            return
        
        wait = await message.reply_text("Qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        
        s, st = ch["snippet"], ch["statistics"]
        subs = int(st.get("subscriberCount", 0))
        views = int(st.get("viewCount", 0))
        vids = int(st.get("videoCount", 0))
        avg = views // vids if vids > 0 else 0
        created = s.get("publishedAt", "")[:10]
        country = s.get("country", "N/A")
        save_channel_snapshot(ch["id"], subs, views, vids)
        
        text = (
            f"**{s['title']}**\n\n"
            f"{'='*28}\n\n"
            f"Obunachilar: `{fmt(subs)}` ({fmt_full(subs)})\n"
            f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
            f"Videolar: `{fmt(vids)}` ({fmt_full(vids)})\n"
            f"O'rtacha ko'rish/video: `{fmt(avg)}`\n"
            f"Yaratilgan: `{created}`\n"
            f"Davlat: `{country}`\n"
            f"ID: `{ch['id']}`"
        )
        await wait.edit_text(text, reply_markup=channel_action_kb(ch["id"]), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /subs ====================
    @bot.on_message(filters.command("subs"))
    async def subs_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/subs <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        subs = int(ch["statistics"].get("subscriberCount", 0))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nObunachilar: **{fmt_full(subs)}**",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /totalviews ====================
    @bot.on_message(filters.command("totalviews"))
    async def totalviews_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/totalviews <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        views = int(ch["statistics"].get("viewCount", 0))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nUmumiy ko'rishlar: **{fmt_full(views)}**",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /videocount ====================
    @bot.on_message(filters.command("videocount"))
    async def videocount_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/videocount <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        vids = int(ch["statistics"].get("videoCount", 0))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nVideolar soni: **{fmt_full(vids)}**",
            parse_mode=ParseMode.MARKDOWN
        )

    # ==================== /ytlogin ====================
    
    @bot.on_message(filters.command("ytlogin"))
    async def ytlogin_cmd(client, message):
        try:
            url = get_auth_url(message.from_user.id)
            text = (
                "🔗 **YouTube kanalingizni ulash uchun quyidagi linkni bosing:**\n\n"
                f"[➡️ Google orqali ruxsat berish]({url})\n\n"
                "**Qadamlar:**\n"
                "1️⃣ Yuqoridagi linkni bosing\n"
                "2️⃣ YouTube kanalingiz bor Gmail akkauntni tanlang\n"
                "3️⃣ \"Allow\" (Ruxsat berish) tugmasini bosing\n"
                "4️⃣ Avtomatik ulanadi — bu yerga qaytib xabar keladi!\n\n"
                "_Ruxsat berganingizdan so'ng, bot avtomatik xabar yuboradi._"
            )
            await message.reply_text(text, disable_web_page_preview=True)
        except Exception as e:
            await message.reply_text(f"❌ Xatolik yuz berdi: {e}")
            
    # ==================== /setproxy & /myproxy ====================
    @bot.on_message(filters.command("setproxy"))
    async def setproxy_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("❌ `Noto'g'ri format! Foydalanish: /setproxy http://ip:port yoki /setproxy socks5://user:pass@ip:port`", parse_mode=ParseMode.MARKDOWN)
            return
        proxy = args[1].strip()
        user_id = message.from_user.id
        if set_user_proxy(user_id, proxy):
            await message.reply_text(f"✅ `Proxy muvaffaqiyatli saqlandi:` `{proxy}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("❌ `Bazaga saqlashda xatolik yuz berdi.`", parse_mode=ParseMode.MARKDOWN)

    @bot.on_message(filters.command("myproxy"))
    async def myproxy_cmd(client, message):
        user_id = message.from_user.id
        proxy = get_user_proxy(user_id)
        if proxy:
            await message.reply_text(f"🌐 `Sizning proxy sozlamangiz:` `{proxy}`", parse_mode=ParseMode.MARKDOWN)
        else:
            def_p = DEFAULT_PROXY or "o'rnatilmagan"
            await message.reply_text(f"🌐 `Sizda shaxsiy proxy yo'q. Default proxy:` `{def_p}`", parse_mode=ParseMode.MARKDOWN)

    # ==================== /setton & /myton ====================
    @bot.on_message(filters.command(["setton", "tonwallet"]))
    async def setton_cmd(client, message):
        is_admin = check_is_admin(message.from_user)
        if not is_admin:
            await message.reply_text("❌ Bu buyruq faqat bot admini uchun!")
            return
            
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            curr = get_ton_wallet()
            txt = (
                f"ℹ️ <b>TON / GRAM Hamyon manzili sozlamasi</b>\n\n"
                f"💎 <b>Joriy manzil:</b> <code>{curr or 'Hali kiritilmagan'}</code>\n\n"
                f"O'zgartirish uchun:\n"
                f"<code>/setton &lt;hamyon_manzilingiz&gt;</code> deb yuboring.\n"
                f"<i>(Masalan: /setton UQ... yoki EQ...)</i>"
            )
            await message.reply_text(txt)
            return
            
        wallet_address = args[1].strip()
        if len(wallet_address) < 24:
            await message.reply_text("❌ Noto'g'ri TON hamyon manzili! Manzil uzunligi kamida 24 belgi bo'lishi kerak.")
            return
            
        if set_ton_wallet(wallet_address):
            await message.reply_text(
                f"✅ <b>TON / GRAM hamyon manzili muvaffaqiyatli saqlandi!</b>\n\n"
                f"💎 <b>Manzil:</b> <code>{wallet_address}</code>\n\n"
                f"🚀 Endi foydalanuvchilar GRAM (TON) orqali to'lov qilganda ushbu manzil va Tonkeeper / Telegram Wallet havolasi avtomatik ko'rsatiladi."
            )
        else:
            await message.reply_text("❌ Bazaga saqlashda xatolik yuz berdi.")

    @bot.on_message(filters.command("myton"))
    async def myton_cmd(client, message):
        curr = get_ton_wallet()
        if curr:
            await message.reply_text(f"💎 <b>O'rnatilgan TON / GRAM hamyon manzili:</b>\n<code>{curr}</code>")
        else:
            await message.reply_text("ℹ️ TON hamyon manzili hali o'rnatilmagan. O'rnatish: <code>/setton &lt;manzil&gt;</code>")

    # ==================== /addkey & /stock (AI API Keys Do'koni) ====================
    @bot.on_message(filters.command("addkey"))
    async def addkey_cmd(client, message):
        if not check_is_admin(message.from_user):
            await message.reply_text("⛔ Bu buyruq faqat bot administratorlari uchun!")
            return
            
        parts = message.text.strip().split()
        if len(parts) < 3:
            await message.reply_text(
                "ℹ️ <b>Foydalanish:</b>\n"
                "<code>/addkey &lt;openrouter|gemini&gt; &lt;key1&gt; [key2 key3 ...]</code>\n\n"
                "<b>Misollar:</b>\n"
                "<code>/addkey openrouter sk-or-v1-xxx sk-or-v1-yyy</code>\n"
                "<code>/addkey gemini AIzaSyxxx AIzaSyyy</code>"
            )
            return
            
        service = parts[1].lower()
        if service not in ("openrouter", "gemini", "groq"):
            await message.reply_text("❌ Noto'g'ri xizmat nomi! Faqat <code>openrouter</code>, <code>gemini</code> yoki <code>groq</code> kiriting.")
            return
            
        keys = parts[2:]
        added_count = 0
        for k in keys:
            k_clean = k.strip()
            if k_clean and add_api_key_to_stock(service, k_clean):
                added_count += 1
                
        stock = get_api_keys_stock_count()
        total_now = stock.get(service, 0)
        service_names = {
            "openrouter": "OpenRouter ($3)",
            "gemini": "Google Gemini ($5)",
            "groq": "Groq Cloud API (10,000 so'm)"
        }
        await message.reply_text(
            f"✅ <b>{added_count} ta API kalit muvaffaqiyatli zaxiraga qo'shildi!</b>\n\n"
            f"🤖 <b>Xizmat:</b> {service_names.get(service, service)}\n"
            f"📦 <b>Jami mavjud zaxira:</b> <code>{total_now} ta</code>"
        )

    # ==================== /addproxy ====================
    @bot.on_message(filters.command("addproxy"))
    async def addproxy_cmd(client, message):
        if not check_is_admin(message.from_user):
            await message.reply_text("⛔ Bu buyruq faqat bot administratorlari uchun!")
            return
            
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.reply_text(
                "ℹ️ <b>Foydalanish:</b>\n"
                "<code>/addproxy &lt;proxy1&gt; [proxy2 proxy3 ...]</code>\n\n"
                "<b>Misollar:</b>\n"
                "<code>/addproxy http://user:pass@1.2.3.4:8080 socks5://user:pass@5.6.7.8:1080</code>"
            )
            return
            
        proxies = parts[1:]
        added_count = 0
        for p in proxies:
            p_clean = p.strip()
            if p_clean and add_proxy_to_stock(p_clean):
                added_count += 1
                
        total_now = get_proxies_stock_count()
        await message.reply_text(
            f"✅ <b>{added_count} ta Dedicated Proxy muvaffaqiyatli zaxiraga qo'shildi!</b>\n\n"
            f"🌐 <b>Jami mavjud proxy zaxirasi:</b> <code>{total_now} ta</code>"
        )

    @bot.on_message(filters.command(["stock", "keystock"]))
    async def stock_cmd(client, message):
        stock = get_api_keys_stock_count()
        op_count = stock.get("openrouter", 0)
        gm_count = stock.get("gemini", 0)
        gq_count = stock.get("groq", 0)
        pr_count = get_proxies_stock_count()
        await message.reply_text(
            f"📦 <b>Mavjud Mahsulotlar Zaxirasi:</b>\n\n"
            f"• 🌐 <b>Dedicated Private Proxies ($3):</b> <code>{pr_count} ta</code>\n"
            f"• 🌐 <b>OpenRouter API ($3):</b> <code>{op_count} ta</code>\n"
            f"• ✨ <b>Google Gemini API ($5):</b> <code>{gm_count} ta</code>\n"
            f"• ⚡ <b>Groq Cloud API (10k so'm):</b> <code>{gq_count} ta</code>\n\n"
            f"<i>Kalit qo'shish: /addkey &lt;openrouter|gemini|groq&gt; &lt;key1...&gt;\nProxy qo'shish: /addproxy &lt;proxy1...&gt;</i>"
        )

    # ==================== /api & Developer Platform ====================
    @bot.on_message(filters.command(["api", "developer", "reseller"]))
    async def api_cmd(client, message):
        user_id = message.from_user.id
        res = get_or_create_user_api_key(user_id)
        if not res.get("ok"):
            await message.reply_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
            return
            
        api_key = res["api_key"]
        total_reqs = res.get("total_requests", 0)
        bal = get_user_balance(user_id)
        
        base_domain = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        docs_url = f"{base_domain}/api/v1/docs" if base_domain else "https://sizning-botingiz.onrender.com/api/v1/docs"
        
        text = (
            f"{e('API')} <b>Developer & Reseller REST API</b>\n\n"
            f"O'z Telegram botingiz, saytingiz yoki skriptingizni bizning bot bilan bog'lang va mahsulotlarimizni (AI kalitlar, Proxylar, YouTube buyurtmalar) to'liq avtomatlashtirilgan tarzda sotib oling!\n\n"
            f"🔑 <b>Sizning Shaxsiy API Kalitingiz:</b>\n"
            f"<code>{api_key}</code> <i>(Nusxalash uchun ustiga bosing)</i>\n\n"
            f"💰 <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n"
            f"📊 <b>Amalga oshirilgan so'rovlar:</b> <code>{total_reqs} ta</code>\n\n"
            f"🌐 <b>API Asosiy Manzil (Base URL):</b>\n"
            f"<code>{base_domain or 'https://...onrender.com'}/api/v1</code>\n\n"
            f"⚡ <b>Avtorizatsiya sarlavhasi (Header):</b>\n"
            f"<code>Authorization: Bearer {api_key}</code>\n\n"
            f"<i>Quyidagi tugmalar orqali tayyor Python kodini olishingiz yoki kalitingizni yangilashingiz mumkin.</i>"
        )
        
        buttons = [
            [
                InlineKeyboardButton(f"{e('REFRESH')} Kalitni yangilash (Rotate)", callback_data="api_regen"),
                InlineKeyboardButton(f"{e('MEMO')} Python Kod Namunasi", callback_data="api_code_sample")
            ]
        ]
        if docs_url.startswith("http"):
            buttons.append([InlineKeyboardButton(f"{e('GLOBE')} Web Dokumentatsiya (Docs)", url=docs_url)])
            
        kb = InlineKeyboardMarkup(buttons)
        await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)

    @bot.on_callback_query(filters.regex(r"^api_regen$"))
    async def api_regen_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        res = regenerate_user_api_key(user_id)
        if not res.get("ok"):
            await callback_query.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return
            
        new_key = res["api_key"]
        bal = get_user_balance(user_id)
        base_domain = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        docs_url = f"{base_domain}/api/v1/docs" if base_domain else "https://sizning-botingiz.onrender.com/api/v1/docs"
        
        text = (
            f"{e('API')} <b>Developer & Reseller REST API</b>\n\n"
            f"🔄 <b>Yangi API kalit yaratildi! Eski kalit bekor qilindi.</b>\n\n"
            f"🔑 <b>Yangi Shaxsiy API Kalitingiz:</b>\n"
            f"<code>{new_key}</code> <i>(Nusxalash uchun ustiga bosing)</i>\n\n"
            f"💰 <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"🌐 <b>API Asosiy Manzil (Base URL):</b>\n"
            f"<code>{base_domain or 'https://...onrender.com'}/api/v1</code>\n\n"
            f"⚡ <b>Header:</b>\n"
            f"<code>Authorization: Bearer {new_key}</code>"
        )
        
        buttons = [
            [
                InlineKeyboardButton(f"{e('REFRESH')} Qayta yangilash", callback_data="api_regen"),
                InlineKeyboardButton(f"{e('MEMO')} Python Kod Namunasi", callback_data="api_code_sample")
            ]
        ]
        if docs_url.startswith("http"):
            buttons.append([InlineKeyboardButton(f"{e('GLOBE')} Web Dokumentatsiya (Docs)", url=docs_url)])
            
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        await callback_query.answer("✅ API kalit muvaffaqiyatli yangilandi!")

    @bot.on_callback_query(filters.regex(r"^api_code_sample$"))
    async def api_code_sample_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        res = get_or_create_user_api_key(user_id)
        api_key = res.get("api_key", "art_live_sizning_kalitingiz")
        base_domain = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/") or "https://SIZNING_DOMAIN.onrender.com"
        
        sample_code = (
            f"import requests\n\n"
            f"API_KEY = \"{api_key}\"\n"
            f"BASE_URL = \"{base_domain}/api/v1\"\n\n"
            f"headers = {{\n"
            f"    \"Authorization\": f\"Bearer {{API_KEY}}\",\n"
            f"    \"Content-Type\": \"application/json\"\n"
            f"}}\n\n"
            f"# 1. Balansni tekshirish\n"
            f"me = requests.get(f\"{{BASE_URL}}/me\", headers=headers).json()\n"
            f"print(\"Balans:\", me[\"user\"][\"balance_uzs\"], \"so'm\")\n\n"
            f"# 2. OpenRouter API kalit sotib olish\n"
            f"buy = requests.post(f\"{{BASE_URL}}/buy\", headers=headers, json={{\"service\": \"openrouter\"}}).json()\n"
            f"if buy[\"ok\"]:\n"
            f"    print(\"Olingan kalit:\", buy[\"api_key\"])\n"
            f"    print(\"Qoldiq balans:\", buy[\"remaining_balance_uzs\"])\n"
            f"else:\n"
            f"    print(\"Xatolik:\", buy[\"message\"])\n"
        )
        
        text = (
            f"🐍 <b>Reseller Bot yaratish uchun tayyor Python kodi:</b>\n\n"
            f"<pre><code class=\"language-python\">{sample_code}</code></pre>\n\n"
            f"<i>Ushbu kod orqali o'z botingizdan bizning bot bazasidagi mahsulotlarni avtomatik sotishingiz mumkin!</i>"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{e('BACK')} Orqaga", callback_data="api_back_info")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        await callback_query.answer()

    @bot.on_callback_query(filters.regex(r"^api_back_info$"))
    async def api_back_info_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        res = get_or_create_user_api_key(user_id)
        api_key = res.get("api_key", "")
        total_reqs = res.get("total_requests", 0)
        bal = get_user_balance(user_id)
        base_domain = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        docs_url = f"{base_domain}/api/v1/docs" if base_domain else "https://sizning-botingiz.onrender.com/api/v1/docs"
        
        text = (
            f"{e('API')} <b>Developer & Reseller REST API</b>\n\n"
            f"O'z Telegram botingiz, saytingiz yoki skriptingizni bizning bot bilan bog'lang va mahsulotlarimizni (AI kalitlar, Proxylar, YouTube buyurtmalar) to'liq avtomatlashtirilgan tarzda sotib oling!\n\n"
            f"🔑 <b>Sizning Shaxsiy API Kalitingiz:</b>\n"
            f"<code>{api_key}</code> <i>(Nusxalash uchun ustiga bosing)</i>\n\n"
            f"💰 <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n"
            f"📊 <b>Amalga oshirilgan so'rovlar:</b> <code>{total_reqs} ta</code>\n\n"
            f"🌐 <b>API Asosiy Manzil (Base URL):</b>\n"
            f"<code>{base_domain or 'https://...onrender.com'}/api/v1</code>\n\n"
            f"⚡ <b>Avtorizatsiya sarlavhasi (Header):</b>\n"
            f"<code>Authorization: Bearer {api_key}</code>\n\n"
            f"<i>Quyidagi tugmalar orqali tayyor Python kodini olishingiz yoki kalitingizni yangilashingiz mumkin.</i>"
        )
        buttons = [
            [
                InlineKeyboardButton(f"{e('REFRESH')} Kalitni yangilash (Rotate)", callback_data="api_regen"),
                InlineKeyboardButton(f"{e('MEMO')} Python Kod Namunasi", callback_data="api_code_sample")
            ]
        ]
        if docs_url.startswith("http"):
            buttons.append([InlineKeyboardButton(f"{e('GLOBE')} Web Dokumentatsiya (Docs)", url=docs_url)])
            
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        await callback_query.answer()

    # ==================== 1. /box (Mystery Box - Omadli Quti) ====================
    @bot.on_message(filters.command(["box", "mystery", "omad"]))
    async def box_cmd(client, message):
        user_id = message.from_user.id
        bal = get_user_balance(user_id)
        cost = 6000
        recent = get_recent_box_winners(3)
        recent_text = ""
        if recent:
            recent_text = "\n\n🔥 <b>Oxirgi yutuqlar:</b>\n" + "\n".join([f"• @user_{r['user']} ➔ <b>{r['prize']}</b>" for r in recent])
            
        text = (
            f"🎁 <b>Omadli Quti (Mystery Box)</b>\n\n"
            f"Qutini oching va omadingizni sinang! Qutidan <b>OpenRouter ($3)</b>, <b>Google Gemini ($5)</b>, "
            f"<b>Groq API</b> yoki <b>Katta Keshbek</b> yutib olishingiz mumkin!\n\n"
            f"💰 <b>Ochish narxi:</b> <code>{cost:,} so'm</code> (yoki 15 ⭐ Stars)\n"
            f"💳 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
            f"{recent_text}\n\n"
            f"<i>Yutish imkoniyati kazino modeli asosida ishlaydi. Omad tilaymiz!</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Qutini ochish (6,000 so'm)", callback_data="box_open")],
            [InlineKeyboardButton(f"{e('STAR')} 15 ⭐ Stars bilan ochish", callback_data="star_buy_15")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^box_open$"))
    async def box_open_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        await callback_query.message.edit_text(
            "🎁 <b>Quti ochilmoqda...</b>\n\n"
            "[ ▰▰▰▰▰▰▱▱▱ ] ⏳"
        )
        await asyncio.sleep(1.0)
        
        res = open_mystery_box(user_id, cost_uzs=6000)
        if not res.get("ok"):
            err_msg = res.get("error", "Xatolik yuz berdi")
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{e('MONEY')} Balansni to'ldirish", callback_data="btn_balance")]])
            await callback_query.message.edit_text(f"❌ {err_msg}", reply_markup=kb)
            return
            
        prize_type = res["prize_type"]
        title = res["prize_title"]
        val = res.get("prize_value", "")
        rem_bal = res.get("remaining_balance", 0)
        
        if prize_type == "lose":
            res_text = (
                f"😢 <b>Afsus, bu safar quti bo'sh chiqdi!</b>\n\n"
                f"Omad keyingi safar albatta kulib boqadi! Yana urinib ko'rasizmi?\n\n"
                f"💰 <b>Qoldiq balansingiz:</b> <code>{rem_bal:,} so'm</code>"
            )
        else:
            val_display = f"\n🔑 <b>Mukofot kodi:</b> <code>{val}</code>" if val and len(val) > 10 else ""
            res_text = (
                f"🎉 <b>TABRIKLAYMIZ! YUTUQ!</b>\n\n"
                f"🏆 <b>Yutug'ingiz:</b> {title}"
                f"{val_display}\n\n"
                f"💰 <b>Qoldiq balansingiz:</b> <code>{rem_bal:,} so'm</code>"
            )
            
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Yana ochish (6,000 so'm)", callback_data="box_open")],
            [InlineKeyboardButton(f"{e('BACK')} Bosh menyu", callback_data="back_main")]
        ])
        await callback_query.message.edit_text(res_text, reply_markup=kb)


    # ==================== 2. /wheel & /spin (Omad G'ildiragi) ====================
    @bot.on_message(filters.command(["wheel", "spin"]))
    async def wheel_cmd(client, message):
        user_id = message.from_user.id
        can_free = can_user_free_spin(user_id)
        bal = get_user_balance(user_id)
        
        status_text = "🟢 <b>Bugungi bepul spiningiz mavjud!</b>" if can_free else "⏳ <b>Bugungi bepul spin ishlatilgan.</b> (Qo'shimcha spin: 3,000 so'm)"
        text = (
            f"🎰 <b>Omad G'ildiragi (Wheel of Fortune)</b>\n\n"
            f"Har kuni 1 marta bepul aylantiring va pul mukofotlari yoki API kalitlarni yutib oling!\n\n"
            f"{status_text}\n"
            f"💰 <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"🎁 <b>Sovg'alar:</b> 200 so'm, 500 so'm, 1,000 so'm, 2,500 so'm, Groq Cloud API!"
        )
        buttons = []
        if can_free:
            buttons.append([InlineKeyboardButton("🎯 Bepul aylantirish (Spin)", callback_data="spin_free")])
        buttons.append([InlineKeyboardButton("💎 Pullik aylantirish (3,000 so'm)", callback_data="spin_paid")])
        
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    @bot.on_callback_query(filters.regex(r"^spin_(free|paid)$"))
    async def spin_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        is_free = (callback_query.data == "spin_free")
        
        await callback_query.message.edit_text("🎰 <b>G'ildirak aylanmoqda...</b>\n\n[ 🔄 🔄 🔄 🔄 🔄 ]")
        await asyncio.sleep(1.0)
        
        res = spin_wheel(user_id, is_free=is_free)
        if not res.get("ok"):
            await callback_query.answer(res.get("error", "Xatolik!"), show_alert=True)
            return
            
        prize = res["title"]
        new_bal = res["new_balance"]
        
        text = (
            f"🎰 <b>Omad G'ildiragi Natijasi:</b>\n\n"
            f"🎉 <b>Mukofot:</b> {prize}\n"
            f"💰 <b>Yangi balansingiz:</b> <code>{new_bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Yana aylantirish (3,000 so'm)", callback_data="spin_paid")],
            [InlineKeyboardButton(f"{e('BACK')} Bosh menyu", callback_data="back_main")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb)


    # ==================== 3. /duel (PvP Coin Flip - 10% Komissiya) ====================
    @bot.on_message(filters.command("duel"))
    async def duel_cmd(client, message):
        user_id = message.from_user.id
        parts = message.text.strip().split()
        if len(parts) < 2:
            open_duels = get_open_duels(5)
            duels_text = ""
            if open_duels:
                duels_text = "\n\n⚔️ <b>Hozirgi faol duellar:</b>\n" + "\n".join([f"• Duel #{d['id']}: <code>{d['amount_uzs']:,} so'm</code> ({d['choice'].upper()})" for d in open_duels])
            await message.reply_text(
                f"⚔️ <b>PvP Tanga Tashlash Duellari (Coin Flip)</b>\n\n"
                f"Boshqa foydalanuvchilar bilan pul tikib o'ynang! G'olib jami bankning 90%ini oladi (10% kassa xizmati).\n\n"
                f"ℹ️ <b>Foydalanish:</b>\n"
                f"<code>/duel &lt;summa&gt; [burgut|panja]</code>\n\n"
                f"<b>Misollar:</b>\n"
                f"• <code>/duel 5000 burgut</code>\n"
                f"• <code>/duel 10000 panja</code>"
                f"{duels_text}"
            )
            return
            
        try:
            amount = int(parts[1])
        except ValueError:
            await message.reply_text("❌ Noto'g'ri summa! Masalan: <code>/duel 5000 burgut</code>")
            return
            
        choice = parts[2].lower() if len(parts) > 2 else "burgut"
        if choice not in ("burgut", "panja"):
            choice = "burgut"
            
        res = create_duel(user_id, amount, choice)
        if not res.get("ok"):
            await message.reply_text(f"❌ {res.get('error', 'Xatolik!')}")
            return
            
        duel_id = res["duel_id"]
        creator_name = message.from_user.first_name or "O'yinchi"
        text = (
            f"⚔️ <b>Yangi Duel e'lon qilindi!</b>\n\n"
            f"👤 <b>Yaratuvchi:</b> {creator_name}\n"
            f"💰 <b>Garov:</b> <code>{amount:,} so'm</code>\n"
            f"🦅 <b>Tanlov:</b> {choice.upper()}\n"
            f"🏆 <b>G'olib oladi:</b> <code>{int(amount * 2 * 0.9):,} so'm</code> (10% kassa)\n\n"
            f"<i>Kim duelga kirishga tayyor? Quyidagi tugmani bosing!</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚔️ Duelga kirish ({amount:,} so'm)", callback_data=f"duel_join_{duel_id}")],
            [InlineKeyboardButton("🚫 Bekor qilish (Yaratuvchi uchun)", callback_data=f"duel_cancel_{duel_id}")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^duel_join_(\d+)$"))
    async def duel_join_callback(client, callback_query: CallbackQuery):
        duel_id = int(callback_query.matches[0].group(1))
        opponent_id = callback_query.from_user.id
        
        await callback_query.answer("🪙 Tanga tashlanmoqda...", show_alert=False)
        res = join_duel(duel_id, opponent_id)
        if not res.get("ok"):
            await callback_query.answer(res.get("error", "Xatolik!"), show_alert=True)
            return
            
        coin = res["coin_result"]
        winner_id = res["winner_id"]
        payout = res["payout"]
        opp_name = callback_query.from_user.first_name or "Raqib"
        winner_tag = f"<b>{opp_name}</b>" if winner_id == opponent_id else "<b>Duel Yaratuvchisi</b>"
        
        coin_icon = "🦅 Burgut" if coin == "burgut" else "🪙 Panja"
        text = (
            f"🪙 <b>Tanga tashlandi: {coin_icon}!</b>\n\n"
            f"🏆 <b>G'OLIB:</b> {winner_tag}\n"
            f"💰 <b>Yutuq summasi:</b> <code>{payout:,} so'm</code> hisobiga o'tkazildi!\n"
            f"🏛 <b>Kassa xizmati (10%):</b> <code>{res['commission']:,} so'm</code>\n\n"
            f"<i>Yangi duel boshlash uchun: /duel &lt;summa&gt;</i>"
        )
        await callback_query.message.edit_text(text)

    @bot.on_callback_query(filters.regex(r"^duel_cancel_(\d+)$"))
    async def duel_cancel_callback(client, callback_query: CallbackQuery):
        duel_id = int(callback_query.matches[0].group(1))
        user_id = callback_query.from_user.id
        res = cancel_duel(duel_id, user_id)
        if not res.get("ok"):
            await callback_query.answer(res.get("error", "Faqat duel yaratuvchisi bekor qilishi mumkin!"), show_alert=True)
            return
        await callback_query.message.edit_text(f"🚫 Duel #{duel_id} bekor qilindi va {res['refunded_amount']:,} so'm hisobingizga qaytarildi.")
        await callback_query.answer("Duel bekor qilindi.")


    # ==================== 4. /lottery (Jekpot Mega Lotereya) ====================
    @bot.on_message(filters.command(["lottery", "lotereya"]))
    async def lottery_cmd(client, message):
        user_id = message.from_user.id
        info = get_current_lottery_info()
        bal = get_user_balance(user_id)
        
        sold = info["tickets_sold"]
        bank = info["total_bank"]
        prize = info["prize_fund"]
        
        text = (
            f"🎟 <b>Jekpot Mega Lotereya (Tiraj #{info['pool_id']})</b>\n\n"
            f"Kichik bilet narxi bilan katta jekpot yutib oling!\n\n"
            f"🎫 <b>1 ta bilet narxi:</b> <code>3,000 so'm</code> (yoki 10 Stars)\n"
            f"📊 <b>Sotilgan biletlar:</b> <code>{sold} ta</code>\n"
            f"💰 <b>Umumiy jamg'arma:</b> <code>{bank:,} so'm</code>\n"
            f"🏆 <b>G'olibga beriladigan Jekpot:</b> <code>{prize:,} so'm</code> (65%)\n"
            f"💳 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"<i>15 ta bilet to'planganda g'olib avtomatik e'lon qilinadi!</i>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎟 1 ta bilet (3,000 so'm)", callback_data="lottery_buy_1"),
                InlineKeyboardButton("🎟 5 ta bilet (15,000 so'm)", callback_data="lottery_buy_5")
            ],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="lottery_refresh")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^lottery_buy_(\d+)$"))
    async def lottery_buy_callback(client, callback_query: CallbackQuery):
        count = int(callback_query.matches[0].group(1))
        user_id = callback_query.from_user.id
        res = buy_lottery_tickets(user_id, count)
        if not res.get("ok"):
            await callback_query.answer(res.get("error", "Balansingiz yetarli emas!"), show_alert=True)
            return
            
        ticket_nums = ", ".join([f"#{n}" for n in res["tickets"]])
        await callback_query.answer(f"✅ {count} ta bilet xarid qilindi!", show_alert=False)
        
        draw_res = draw_lottery_if_ready(min_tickets=15)
        if draw_res.get("ok"):
            await callback_query.message.reply_text(
                f"🎉 <b>LOTEREYA YAKUNLANDI! G'OLIB ANIQLANDI!</b>\n\n"
                f"🏆 <b>Yutuqli bilet:</b> #{draw_res['winning_ticket']}\n"
                f"💰 <b>G'olib mukofoti:</b> <code>{draw_res['prize_uzs']:,} so'm</code> hisobiga o'tkazildi!\n"
                f"🏛 <b>Kassa sof daromadi (35%):</b> <code>{draw_res['house_profit']:,} so'm</code>\n\n"
                f"🚀 <i>Yangi tiraj boshlandi! Yangi biletlar xarid qilish mumkin.</i>"
            )
            
        info = get_current_lottery_info()
        bal = get_user_balance(user_id)
        text = (
            f"🎟 <b>Jekpot Mega Lotereya</b>\n\n"
            f"✅ <b>Sizning yangi biletlaringiz:</b> {ticket_nums}\n\n"
            f"📊 <b>Jami sotilgan:</b> {info['tickets_sold']} ta\n"
            f"🏆 <b>G'olibga Jekpot:</b> <code>{info['prize_fund']:,} so'm</code>\n"
            f"💰 <b>Balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎟 Yana 1 ta (3,000)", callback_data="lottery_buy_1"),
                InlineKeyboardButton("🎟 Yana 5 ta (15,000)", callback_data="lottery_buy_5")
            ],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="lottery_refresh")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^lottery_refresh$"))
    async def lottery_refresh_callback(client, callback_query: CallbackQuery):
        info = get_current_lottery_info()
        user_id = callback_query.from_user.id
        bal = get_user_balance(user_id)
        text = (
            f"🎟 <b>Jekpot Mega Lotereya (Tiraj #{info['pool_id']})</b>\n\n"
            f"🎫 <b>1 ta bilet narxi:</b> <code>3,000 so'm</code>\n"
            f"📊 <b>Sotilgan biletlar:</b> <code>{info['tickets_sold']} ta</code>\n"
            f"🏆 <b>G'olibga Jekpot:</b> <code>{info['prize_fund']:,} so'm</code>\n"
            f"💳 <b>Balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎟 1 ta bilet (3,000 so'm)", callback_data="lottery_buy_1"),
                InlineKeyboardButton("🎟 5 ta bilet (15,000 so'm)", callback_data="lottery_buy_5")
            ],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="lottery_refresh")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb)
        await callback_query.answer("Yangilandi!")


    # ==================== 5. /makegift & /redeem (Vaucherlar) ====================
    @bot.on_message(filters.command("makegift"))
    async def makegift_cmd(client, message):
        if not check_is_admin(message.from_user):
            await message.reply_text("⛔ Bu buyruq faqat bot administratorlari uchun!")
            return
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.reply_text("ℹ️ <b>Foydalanish:</b> <code>/makegift &lt;summa&gt; [soni]</code>\n\n<b>Masalan:</b> <code>/makegift 10000 5</code>")
            return
        try:
            amount = int(parts[1])
            count = int(parts[2]) if len(parts) > 2 else 1
        except ValueError:
            await message.reply_text("❌ Noto'g'ri qiymatlar kiritildi!")
            return
            
        codes = create_vouchers(message.from_user.id, amount, count)
        if not codes:
            await message.reply_text("❌ Vaucher yaratishda xatolik yuz berdi!")
            return
            
        codes_text = "\n".join([f"• <code>{c}</code>" for c in codes])
        await message.reply_text(
            f"✅ <b>{count} ta sovg'a vaucheri yaratildi!</b>\n\n"
            f"💰 <b>Har birining qiymati:</b> <code>{amount:,} so'm</code>\n\n"
            f"🎁 <b>Promokodlar:</b>\n{codes_text}\n\n"
            f"<i>Foydalanuvchilar /redeem &lt;kod&gt; orqali faollashtirishi mumkin.</i>"
        )

    @bot.on_message(filters.command("redeem"))
    async def redeem_cmd(client, message):
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.reply_text("ℹ️ <b>Foydalanish:</b> <code>/redeem &lt;kod&gt;</code>\n\n<b>Masalan:</b> <code>/redeem GIFT-XXXX-YYYY</code>")
            return
        code = parts[1].strip()
        res = redeem_voucher(message.from_user.id, code)
        if not res.get("ok"):
            await message.reply_text(f"❌ {res.get('error', 'Yaroqsiz vaucher!')}")
            return
            
        await message.reply_text(
            f"🎉 <b>Vaucher muvaffaqiyatli faollashtirildi!</b>\n\n"
            f"💰 <b>Hisobingizga qo'shildi:</b> <code>+{res['amount_uzs']:,} so'm</code>\n"
            f"💳 <b>Yangi balansingiz:</b> <code>{res['new_balance']:,} so'm</code>"
        )


    # ==================== 6. /createbot (1-Click White-Label Bot $50) ====================
    @bot.on_message(filters.command("createbot"))
    async def createbot_cmd(client, message):
        parts = message.text.strip().split()
        user_id = message.from_user.id
        if len(parts) < 2:
            await message.reply_text(
                f"🤖 <b>1-Click White-Label Bot Platformasi ($50 / 640,000 so'm)</b>\n\n"
                f"O'zingizning nomingiz ostida alohida Telegram bot oching! Biz sizning botingizni butunlay avtomatik backend va zaxiralar bilan ta'minlaymiz, barcha ustama foyda o'zingizda qoladi!\n\n"
                f"ℹ️ <b>Foydalanish:</b>\n"
                f"<code>/createbot &lt;botfather_token&gt;</code>\n\n"
                f"<b>Qadamlar:</b>\n"
                f"1. @BotFather ga boring va yangi bot oching.\n"
                f"2. Berilgan tokenni <code>/createbot &lt;token&gt;</code> orqali yuboring."
            )
            return
            
        token = parts[1].strip()
        res = order_whitelabel_bot(user_id, token)
        if not res.get("ok"):
            await message.reply_text(f"❌ {res.get('error', 'Xatolik!')}")
            return
            
        await message.reply_text(
            f"🚀 <b>White-Label Botingiz muvaffaqiyatli ulandi!</b>\n\n"
            f"✅ Botingiz bizning ulgurji zaxiralarimiz va to'lov tizimimiz bilan to'liq integratsiya qilindi.\n"
            f"💰 <b>Qoldiq balansingiz:</b> <code>{res['new_balance']:,} so'm</code>"
        )


    # ==================== 7. /webhook (Reseller Webhooks $3/hafta) ====================
    @bot.on_message(filters.command("webhook"))
    async def webhook_cmd(client, message):
        parts = message.text.strip().split()
        user_id = message.from_user.id
        if len(parts) < 2:
            existing = get_user_webhook(user_id)
            exist_text = ""
            if existing:
                exist_text = f"\n\n🌐 <b>Faol webhookingiz:</b> <code>{existing['webhook_url']}</code>\n⏳ <b>Muddati:</b> {existing['expires_at'][:16]}"
            await message.reply_text(
                f"⚡ <b>Reseller Webhook & Real-Time Push ($3 / hafta)</b>\n\n"
                f"Buyurtmalaringiz holati o'zgarganda yoki yangi zaxira kelganda o'z serveringizga lahzali xabar (HTTP POST) oling!\n\n"
                f"ℹ️ <b>Foydalanish:</b>\n"
                f"<code>/webhook &lt;https://saytingiz.uz/webhook&gt; [hafta_soni]</code>\n\n"
                f"<b>Masalan:</b> <code>/webhook https://reseller-bot.com/cb 1</code>"
                f"{exist_text}"
            )
            return
            
        url = parts[1].strip()
        weeks = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        res = subscribe_webhook(user_id, url, weeks)
        if not res.get("ok"):
            await message.reply_text(f"❌ {res.get('error', 'Xatolik!')}")
            return
            
        await message.reply_text(
            f"✅ <b>Webhook obunangiz faollashtirildi!</b>\n\n"
            f"🌐 <b>URL:</b> <code>{res['webhook_url']}</code>\n"
            f"🔐 <b>Secret Token:</b> <code>{res['secret_token']}</code>\n"
            f"⏳ <b>Amal qilish muddati:</b> {res['expires_at'][:16]}\n"
            f"💰 <b>Qoldiq balansingiz:</b> <code>{res['new_balance']:,} so'm</code>"
        )


    # ==================== 8. /dashboard (Developer & Reseller Mini App) ====================
    @bot.on_message(filters.command(["dashboard", "devpanel"]))
    async def dashboard_cmd(client, message):
        user_id = message.from_user.id
        base_domain = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        dash_url = f"{base_domain}/dashboard?user_id={user_id}" if base_domain else f"https://sizning-botingiz.onrender.com/dashboard?user_id={user_id}"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard Mini App ni ochish", web_app=WebAppInfo(url=dash_url))]
        ])
        await message.reply_text(
            "📊 <b>Developer & Reseller Dashboard Mini App</b>\n\n"
            "Telegram ichida to'liq interaktiv boshqaruv paneli:\n"
            "• Jonli balans va so'rovlar grafigi\n"
            "• API kalitni nusxalash va boshqarish\n"
            "• 💎 <b>TON</b> va ⭐ <b>Telegram Stars</b> orqali 1-klikda to'ldirish\n\n"
            "<i>Pastdagi tugmani bosing:</i>",
            reply_markup=kb
        )

    # ==================== MULTI-LANGUAGE (i18n) ====================
    @bot.on_message(filters.command(["lang", "language", "til"]))
    async def lang_cmd(client, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        await message.reply_text(t("select_lang", lang), reply_markup=lang_menu_kb())

    @bot.on_callback_query(filters.regex(r"^menu_lang$"))
    async def menu_lang_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        lang = get_user_language(user_id)
        await callback_query.message.edit_text(t("select_lang", lang), reply_markup=lang_menu_kb())
        await callback_query.answer()

    @bot.on_callback_query(filters.regex(r"^setlang_(uz|ru|en|es|tr)$"))
    async def set_lang_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        selected_lang = callback_query.matches[0].group(1)
        set_user_language(user_id, selected_lang)
        confirm_text = t("lang_changed", selected_lang)
        await callback_query.answer(f"✅ {SUPPORTED_LANGUAGES.get(selected_lang, selected_lang)}")
        name = (callback_query.from_user.first_name or "Foydalanuvchi") if callback_query.from_user else "Foydalanuvchi"
        await callback_query.message.edit_text(
            f"{confirm_text}\n\n{t('main_menu', selected_lang, name=name)}",
            reply_markup=main_menu_kb(user_id)
        )

    # ==================== GAMES HUB ====================
    @bot.on_callback_query(filters.regex(r"^menu_games$"))
    async def menu_games_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        lang = get_user_language(user_id)
        bal = get_user_balance(user_id)
        text = t("games_title", lang, balance=bal)
        await callback_query.message.edit_text(text, reply_markup=games_menu_kb(user_id))
        await callback_query.answer()

    @bot.on_callback_query(filters.regex(r"^game_duel_info$"))
    async def game_duel_info_callback(client, callback_query: CallbackQuery):
        open_duels = get_open_duels(5)
        duels_text = ""
        if open_duels:
            duels_text = "\n\n⚔️ <b>Hozirgi faol duellar:</b>\n" + "\n".join([f"• Duel #{d['id']}: <code>{d['amount_uzs']:,} so'm</code> ({d['choice'].upper()})" for d in open_duels])
        text = (
            f"⚔️ <b>PvP Tanga Tashlash (Coin Flip)</b>\n\n"
            f"Boshqa o'yinchilar bilan garov boylab o'ynang! G'olib jami bankning 90%ini oladi (10% kassa xizmati).\n\n"
            f"ℹ️ <b>Qanday o'ynash kerak:</b>\n"
            f"Chatda <code>/duel &lt;summa&gt; [burgut|panja]</code> buyrug'ini yuboring.\n\n"
            f"<b>Masalan:</b> <code>/duel 5000 burgut</code>"
            f"{duels_text}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ O'yinlar menyusi", callback_data="menu_games")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb)
        await callback_query.answer()

    # ==================== VIRAL REFERRAL SYSTEM ====================
    @bot.on_message(filters.command(["ref", "referral", "invite"]))
    async def referral_cmd(client, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        me = await client.get_me()
        bot_user = me.username or "AutoReplyBot"
        ref_link = f"https://t.me/{bot_user}?start=ref_{user_id}"
        stats = get_referral_stats(user_id)
        share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(t('ref_share_message', lang))}"
        
        text = t(
            "referral_title",
            lang,
            invited_count=stats["invited_count"],
            total_earned=stats["total_earned"],
            ref_link=ref_link
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_share_ref", lang), url=share_url)],
            [InlineKeyboardButton("🎁 Omadli Qutini ochish (/box)", callback_data="box_open")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="back_main")]
        ])
        await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)

    @bot.on_callback_query(filters.regex(r"^menu_referral$"))
    async def menu_referral_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        lang = get_user_language(user_id)
        me = await client.get_me()
        bot_user = me.username or "AutoReplyBot"
        ref_link = f"https://t.me/{bot_user}?start=ref_{user_id}"
        stats = get_referral_stats(user_id)
        share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(t('ref_share_message', lang))}"
        
        text = t(
            "referral_title",
            lang,
            invited_count=stats["invited_count"],
            total_earned=stats["total_earned"],
            ref_link=ref_link
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_share_ref", lang), url=share_url)],
            [InlineKeyboardButton("🎁 Omadli Qutini ochish (/box)", callback_data="box_open")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="back_main")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        await callback_query.answer()

    # ==================== LEADERBOARD (REYTING) ====================
    @bot.on_message(filters.command(["leaderboard", "top", "reyting"]))
    async def leaderboard_cmd(client, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        
        top_refs = get_top_referrers(5)
        top_duels = get_top_duel_winners(5)
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        ref_lines = [f"{medals[idx] if idx < 5 else '•'} ID: <code>{r['user']}</code> ➔ <b>{r['count']} ta</b> do'st ({r['earned']:,} so'm)" for idx, r in enumerate(top_refs)]
        duel_lines = [f"{medals[idx] if idx < 5 else '•'} ID: <code>{d['user']}</code> ➔ <b>{d['count']} ta</b> yutuq ({d['payout']:,} so'm)" for idx, d in enumerate(top_duels)]
        
        ref_str = "\n".join(ref_lines) if ref_lines else "<i>Hozircha ma'lumotlar yo'q</i>"
        duel_str = "\n".join(duel_lines) if duel_lines else "<i>Hozircha ma'lumotlar yo'q</i>"
        
        text = t("leaderboard_title", lang, top_referrers=ref_str, top_duels=duel_str)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Do'stlarni chaqirish", callback_data="menu_referral")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^menu_leaderboard$"))
    async def menu_leaderboard_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        lang = get_user_language(user_id)
        
        top_refs = get_top_referrers(5)
        top_duels = get_top_duel_winners(5)
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        ref_lines = [f"{medals[idx] if idx < 5 else '•'} ID: <code>{r['user']}</code> ➔ <b>{r['count']} ta</b> ({r['earned']:,} so'm)" for idx, r in enumerate(top_refs)]
        duel_lines = [f"{medals[idx] if idx < 5 else '•'} ID: <code>{d['user']}</code> ➔ <b>{d['count']} ta</b> ({d['payout']:,} so'm)" for idx, d in enumerate(top_duels)]
        
        ref_str = "\n".join(ref_lines) if ref_lines else "<i>Hozircha ma'lumotlar yo'q</i>"
        duel_str = "\n".join(duel_lines) if duel_lines else "<i>Hozircha ma'lumotlar yo'q</i>"
        
        text = t("leaderboard_title", lang, top_referrers=ref_str, top_duels=duel_str)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Do'stlarni chaqirish", callback_data="menu_referral")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await callback_query.message.edit_text(text, reply_markup=kb)
        await callback_query.answer()

    # ==================== FORCE SUB (KANALGA MAJBURIY OBUNA) ====================
    @bot.on_message(filters.command("forcesub"))
    async def forcesub_cmd(client, message):
        if not check_is_admin(message.from_user):
            await message.reply_text("⛔ Bu buyruq faqat bot administratorlari uchun!")
            return
        parts = message.text.strip().split()
        if len(parts) < 2:
            current_ch = get_config("force_sub_channel") or "O'rnatilmagan (OFF)"
            await message.reply_text(
                f"📢 <b>Majburiy Kanal Obunasi Sozlamalari</b>\n\n"
                f"Hozirgi kanal: <code>{current_ch}</code>\n\n"
                f"ℹ️ <b>Foydalanish:</b>\n"
                f"• <code>/forcesub @kanalingiz</code> — Kanalni biriktirish\n"
                f"• <code>/forcesub off</code> — Majburiy obunani o'chirish\n\n"
                f"<i>Eslatma: Bot ushbu kanalda administrator bo'lishi shart!</i>"
            )
            return
        arg = parts[1].strip()
        if arg.lower() in ("off", "stop", "none", "0"):
            set_config("force_sub_channel", "")
            await message.reply_text("✅ Majburiy kanal obunasi o'chirildi.")
        else:
            set_config("force_sub_channel", arg)
            await message.reply_text(f"✅ Majburiy obuna kanali o'rnatildi: <b>{arg}</b>\nBot kanalda admin ekanligiga ishonch hosil qiling.")

    @bot.on_callback_query(filters.regex(r"^sub_check$"))
    async def sub_check_callback(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        lang = get_user_language(user_id)
        ch = get_config("force_sub_channel")
        if not ch:
            await callback_query.message.edit_text(t("sub_success", lang), reply_markup=main_menu_kb(user_id))
            await callback_query.answer()
            return
        try:
            member = await client.get_chat_member(ch, user_id)
            if member and getattr(member, "status", None) not in ("left", "kicked"):
                await callback_query.message.edit_text(t("sub_success", lang), reply_markup=main_menu_kb(user_id))
                await callback_query.answer("✅ Rahmat! A'zolik tasdiqlandi.")
                return
        except Exception as e:
            print(f"sub check error: {e}")
        await callback_query.answer(t("sub_not_found", lang), show_alert=True)

    # ==================== INLINE QUERY (GURUHLAR UCHUN VIRAL INVITATION) ====================
    @bot.on_inline_query()
    async def handle_inline_query(client, inline_query: InlineQuery):
        user_id = inline_query.from_user.id
        me = await client.get_me()
        bot_user = me.username or "AutoReplyBot"
        q = inline_query.query.strip().lower()
        
        duel_amount = 5000
        parts = q.split()
        if len(parts) > 1 and parts[1].isdigit():
            duel_amount = int(parts[1])
            
        results = [
            InlineQueryResultArticle(
                title="⚔️ PvP Tanga Tashlash Dueli",
                description=f"{duel_amount:,} so'm garov bilan do'stingizni duelga chorlang!",
                input_message_content=InputTextMessageContent(
                    f"⚔️ <b>PvP Tanga Tashlash (Coin Flip) Chaqiruvi!</b>\n\n"
                    f"👤 <b>Chaqiruvchi:</b> {inline_query.from_user.first_name}\n"
                    f"💰 <b>Garov:</b> <code>{duel_amount:,} so'm</code>\n"
                    f"🏆 <b>G'olib oladi:</b> <code>{int(duel_amount * 2 * 0.9):,} so'm</code>\n\n"
                    f"<i>Kim duelga kirishga tayyor? Pastdagi tugmani bosing!</i>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⚔️ Duelga kirish ({duel_amount:,} so'm)", url=f"https://t.me/{bot_user}?start=duel_{duel_amount}")]
                ])
            ),
            InlineQueryResultArticle(
                title="🎁 Omadli Quti (Mystery Box)",
                description="Do'stlaringizga Mystery Box ulashing va mukofot yuting!",
                input_message_content=InputTextMessageContent(
                    f"🎁 <b>Omadli Quti (Mystery Box)</b>\n\n"
                    f"Qutini oching va <b>OpenRouter ($3)</b>, <b>Google Gemini ($5)</b> yoki <b>Katta Keshbek</b> yutib oling!\n\n"
                    f"👇 <i>Pastdagi tugma orqali bepul omadingizni sinang:</i>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 Qutini ochish", url=f"https://t.me/{bot_user}?start=ref_{user_id}")]
                ])
            )
        ]
        await inline_query.answer(results=results, cache_time=5)

    # ==================== /dl & /download (VIRAL VIDEO DOWNLOADER) ====================
    @bot.on_message(filters.command(["dl", "download"]))
    async def dl_video_cmd(client, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        me = await client.get_me()
        bot_user = me.username or "AutoReplyBot"
        
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text(
                f"📥 <b>Video yuklab olish (YouTube & Instagram)</b>\n\n"
                f"ℹ️ <b>Foydalanish:</b>\n"
                f"<code>/dl &lt;video havolasi&gt;</code>\n\n"
                f"<i>Masalan: /dl https://www.youtube.com/shorts/... yoki Instagram Reels</i>"
            )
            return
            
        target_url = parts[1].strip()
        wait_msg = await message.reply_text("⏳ <i>Video yuklab olinmoqda va tayyorlanmoqda...</i>")
        
        os.makedirs("downloads", exist_ok=True)
        out_path = f"downloads/dl_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
        
        try:
            if is_instagram_url(target_url):
                info = await download_instagram_reel(target_url)
                if info and os.path.exists(info.get("video_path", "")):
                    v_title = info.get("title", "Instagram Reel")
                    promo = t("dl_promo_caption", lang, bot_user=bot_user)
                    caption = f"🎬 <b>{v_title[:60]}</b>{promo}"
                    await message.reply_video(video=info["video_path"], caption=caption, supports_streaming=True)
                    await wait_msg.delete()
                    return
            
            import yt_dlp
            ydl_opts = {
                "outtmpl": out_path,
                "format": "bestvideo[height<=720][filesize<45M]+bestaudio/best[height<=720][filesize<45M]/best[filesize<45M]/best",
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                "max_filesize": 50 * 1024 * 1024
            }
            def _dl_yt():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(target_url, download=True)
            
            info = await asyncio.to_thread(_dl_yt)
            
            actual_path = out_path
            if not os.path.exists(out_path):
                base, _ = os.path.splitext(out_path)
                for f in os.listdir("downloads"):
                    if f.startswith(os.path.basename(base)):
                        actual_path = os.path.join("downloads", f)
                        break
                        
            if os.path.exists(actual_path):
                v_title = info.get("title", "Video") if isinstance(info, dict) else "Video"
                promo = t("dl_promo_caption", lang, bot_user=bot_user)
                caption = f"🎬 <b>{v_title[:60]}</b>{promo}"
                await message.reply_video(video=actual_path, caption=caption, supports_streaming=True)
                await wait_msg.delete()
                try: os.remove(actual_path)
                except: pass
            else:
                await wait_msg.edit_text("❌ Videoni yuklab bo'lmadi. Havolani tekshirib qayta urinib ko'ring.")
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
            if os.path.exists(out_path):
                try: os.remove(out_path)
                except: pass

    # ==================== /autopost ====================
    
    @bot.on_message(filters.command("autopost"))
    async def autopost_cmd(client, message):
        user_id = message.from_user.id
        is_admin = check_is_admin(message.from_user)

        # Limit tekshirish
        daily_used = get_daily_usage(user_id)
        limit = DAILY_LIMIT_ADMIN if is_admin else DAILY_LIMIT_USER

        if daily_used >= limit:
            await message.reply_text(
                f"⏳ `Kunlik limitingiz ({limit} ta) tugadi! Ertaga qayta urinib ko'ring.`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Ulanish tekshiruvi
        from database import get_all_yt_connections
        connections = get_all_yt_connections(user_id)
        if not connections:
            await message.reply_text("❌ `Siz hali YouTube kanalingizni ulamadingiz! Avval /ytlogin orqali ulang.`", parse_mode=ParseMode.MARKDOWN)
            return

        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.reply_text(
                "📋 **To'g'ri foydalanish:**\n\n"
                "`/autopost <soni> <mavzu>`\n\n"
                "**Masalan:**\n"
                "• `/autopost 3 gaming`\n"
                "• `/autopost 5 funny cats`\n"
                "• `/autopost 2 cooking recipe`\n\n"
                "⚡ Keyin bot sizdan **Shorts** yoki **Katta video** ekanligini so'raydi.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        try:
            count = int(args[1])
            topic = args[2]

            remaining = limit - daily_used
            if count > remaining:
                await message.reply_text(
                    f"❌ `Siz bugun max {remaining} ta video yuklay olasiz! (Kunlik limit: {limit} ta)`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Vaqtinchalik saqlash
            short_id = str(uuid.uuid4())[:8]
            AUTOPOST_ARGS_MAP[short_id] = {
                "count": count, 
                "topic": topic, 
                "user_id": user_id,
                "connections": connections
            }
            
            # 1-qadam: Shorts yoki Video tanlash
            buttons = [
                [InlineKeyboardButton("🩳 Shorts (Qisqa videolar)", callback_data=f"ap_type|{short_id}|shorts")],
                [InlineKeyboardButton("🎬 Katta Video (Uzun)", callback_data=f"ap_type|{short_id}|video")]
            ]
            await message.reply_text(
                f"📺 **{count} ta video** mavzu: **'{topic}'**\n\n"
                f"Qanday turdagi video qidiramiz?",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN
            )
                
        except ValueError:
            await message.reply_text("❌ `Soni raqam bo'lishi kerak!`", parse_mode=ParseMode.MARKDOWN)

    
    # ==================== /setcookies ====================
    
    @bot.on_message(filters.command("setcookies"))
    async def setcookies_cmd(client, message):
        doc = message.document
        if not doc:
            await message.reply_text("❌ `Siz fayl yubormadingiz!\n\nTo'g'ri usul: Faylni Telegramga yuklayotganda, izoh (caption) qismiga /setcookies deb yozing.`", parse_mode=ParseMode.MARKDOWN)
            return
            
        if not doc.file_name.endswith(".txt"):
            await message.reply_text("❌ `Iltimos, faqat .txt formatidagi fayl yuklang (masalan cookies.txt).`", parse_mode=ParseMode.MARKDOWN)
            return
            
        try:
            # Faylni xotiraga yuklash
            file_path = await client.download_media(message)
            with open(file_path, 'r', encoding='utf-8') as f:
                cookies_text = f.read()
            import os
            os.remove(file_path)
            
            # Bazaga saqlash
            if set_user_cookies(message.from_user.id, cookies_text):
                await message.reply_text("✅ `Cookies muvaffaqiyatli saqlandi! Endi /autopost ishlab ketadi.`", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text("❌ `Bazaga saqlashda xatolik yuz berdi.`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await message.reply_text(f"❌ `Faylni o'qishda xatolik: {e}`", parse_mode=ParseMode.MARKDOWN)

    # ==================== /about ====================
    @bot.on_message(filters.command("about"))
    async def about_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/about <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        desc = ch["snippet"].get("description", "Tavsif mavjud emas")[:1000]
        country = ch["snippet"].get("country", "N/A")
        created = ch["snippet"].get("publishedAt", "")[:10]
        custom_url = ch["snippet"].get("customUrl", "N/A")
        text = (
            f"**{ch['snippet']['title']}** haqida\n\n"
            f"{'='*28}\n\n"
            f"Custom URL: `{custom_url}`\n"
            f"Davlat: `{country}`\n"
            f"Yaratilgan: `{created}`\n"
            f"ID: `{ch['id']}`\n\n"
            f"Tavsif:\n{desc}"
        )
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /country ====================
    @bot.on_message(filters.command("country"))
    async def country_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/country <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        country = ch["snippet"].get("country", "Noma'lum")
        await message.reply_text(f"**{ch['snippet']['title']}**\n\nDavlat: **{country}**", parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /created ====================
    @bot.on_message(filters.command("created"))
    async def created_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/created <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        created = ch["snippet"].get("publishedAt", "")[:10]
        age = time_ago(ch["snippet"].get("publishedAt", ""))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nYaratilgan: **{created}** ({age})",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /keywords ====================
    @bot.on_message(filters.command("keywords"))
    async def keywords_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/keywords <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        bs = ch.get("brandingSettings", {}).get("channel", {})
        kw = bs.get("keywords", "Kalit so'zlar topilmadi")
        await message.reply_text(
            f"**{ch['snippet']['title']}** kalit so'zlari:\n\n`{kw}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /banner ====================
    @bot.on_message(filters.command("banner"))
    async def banner_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/banner <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        bi = ch.get("brandingSettings", {}).get("image", {})
        banner = bi.get("bannerExternalUrl", "")
        if banner:
            await message.reply_photo(banner, caption=f"**{ch['snippet']['title']}** banner rasmi", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("Bu kanalda banner rasmi topilmadi.")
    
    # ==================== /avatar ====================
    @bot.on_message(filters.command("avatar"))
    async def avatar_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/avatar <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        thumbs = ch["snippet"].get("thumbnails", {})
        url = thumbs.get("high", thumbs.get("medium", thumbs.get("default", {}))).get("url", "")
        if url:
            await message.reply_photo(url, caption=f"**{ch['snippet']['title']}** profil rasmi", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("Profil rasmi topilmadi.")
    
    # ==================== /video ====================
    @bot.on_message(filters.command("video"))
    async def video_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/video <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        wait = await message.reply_text("Qidirilmoqda...")
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await wait.edit_text("Video topilmadi. URL ni tekshiring.")
            return
        v = get_video(vid_id)
        if not v:
            await wait.edit_text("Video ma'lumotlari topilmadi.")
            return
        
        sn, st = v["snippet"], v["statistics"]
        views = int(st.get("viewCount", 0))
        likes = int(st.get("likeCount", 0))
        comments = int(st.get("commentCount", 0))
        dur = parse_duration(v.get("contentDetails", {}).get("duration", ""))
        published = sn.get("publishedAt", "")[:10]
        ago = time_ago(sn.get("publishedAt", ""))
        eng = engagement_rate(views, likes, comments)
        lr = (likes / views * 100) if views > 0 else 0
        low, high = estimate_earnings(views)
        
        save_video_snapshot(vid_id, sn.get("channelId", ""), sn["title"], views, likes, comments)
        
        text = (
            f"**{sn['title']}**\n\n"
            f"{'='*28}\n\n"
            f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
            f"Likelar: `{fmt(likes)}` ({fmt_full(likes)})\n"
            f"Izohlar: `{fmt(comments)}` ({fmt_full(comments)})\n"
            f"Like/View: `{lr:.2f}%`\n"
            f"Engagement: `{eng:.2f}%`\n"
            f"Davomiyligi: `{dur}`\n"
            f"Chop etilgan: `{published}` ({ago})\n"
            f"Kanal: {sn.get('channelTitle', 'N/A')}\n"
            f"Taxminiy daromad: `${low:.0f} - ${high:.0f}`\n"
            f"ID: `{vid_id}`"
        )
        await wait.edit_text(text, reply_markup=video_action_kb(vid_id), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /recent ====================
    @bot.on_message(filters.command("recent"))
    async def recent_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/recent <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("So'nggi videolar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        text = f"**{ch['snippet']['title']}** - So'nggi videolar\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            likes = int(vs.get("likeCount", 0))
            ago = time_ago(v["snippet"].get("publishedAt", ""))
            text += f"**{i}.** {v['snippet']['title'][:45]}\n"
            text += f"   `{fmt(views)}` ko'rish | `{fmt(likes)}` like | {ago}\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /popular ====================
    @bot.on_message(filters.command("popular"))
    async def popular_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/popular <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Eng ommabop videolar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="viewCount")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        text = f"**{ch['snippet']['title']}** - Eng ommabop\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            likes = int(vs.get("likeCount", 0))
            text += f"**{i}.** {v['snippet']['title'][:45]}\n"
            text += f"   `{fmt(views)}` ko'rish | `{fmt(likes)}` like\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /playlists ====================
    @bot.on_message(filters.command("playlists"))
    async def playlists_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/playlists <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Pleylistlar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        pls = get_playlists(ch["id"], max_results=15)
        if not pls:
            await wait.edit_text("Pleylistlar topilmadi.")
            return
        text = f"**{ch['snippet']['title']}** - Pleylistlar\n\n{'='*28}\n\n"
        for i, p in enumerate(pls, 1):
            count = p.get("contentDetails", {}).get("itemCount", 0)
            text += f"**{i}.** {p['snippet']['title'][:45]}\n"
            text += f"   `{count}` ta video\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /compare ====================
    @bot.on_message(filters.command("compare"))
    async def compare_cmd(client, message):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.reply_text(
                "Foydalanish: `/compare <kanal1> <kanal2>`\n\n"
                "Misol: `/compare @mkbhd @linustechtips`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        wait = await message.reply_text("Kanallar solishtirilmoqda...")
        ch1 = get_channel(extract_channel_id(args[1]))
        ch2 = get_channel(extract_channel_id(args[2]))
        if not ch1 or not ch2:
            await wait.edit_text("Kanallardan biri topilmadi.")
            return
        
        s1, s2 = ch1["statistics"], ch2["statistics"]
        sub1, sub2 = int(s1.get("subscriberCount",0)), int(s2.get("subscriberCount",0))
        v1, v2 = int(s1.get("viewCount",0)), int(s2.get("viewCount",0))
        vc1, vc2 = int(s1.get("videoCount",0)), int(s2.get("videoCount",0))
        avg1 = v1//vc1 if vc1 else 0
        avg2 = v2//vc2 if vc2 else 0
        
        w_sub = ch1["snippet"]["title"] if sub1>sub2 else ch2["snippet"]["title"]
        w_view = ch1["snippet"]["title"] if v1>v2 else ch2["snippet"]["title"]
        w_avg = ch1["snippet"]["title"] if avg1>avg2 else ch2["snippet"]["title"]
        
        text = (
            f"**Solishtirish**\n\n{'='*28}\n\n"
            f"| | **{ch1['snippet']['title'][:15]}** | **{ch2['snippet']['title'][:15]}** |\n"
            f"|---|---|---|\n"
            f"| Obunachilar | `{fmt(sub1)}` | `{fmt(sub2)}` |\n"
            f"| Ko'rishlar | `{fmt(v1)}` | `{fmt(v2)}` |\n"
            f"| Videolar | `{fmt(vc1)}` | `{fmt(vc2)}` |\n"
            f"| O'rtacha | `{fmt(avg1)}` | `{fmt(avg2)}` |\n\n"
            f"{'='*28}\n\n"
            f"Obunachilar bo'yicha: **{w_sub}**\n"
            f"Ko'rishlar bo'yicha: **{w_view}**\n"
            f"O'rtacha bo'yicha: **{w_avg}**"
        )
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /growth ====================
    @bot.on_message(filters.command("growth"))
    async def growth_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/growth <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Tahlil qilinmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        st = ch["statistics"]
        subs = int(st.get("subscriberCount",0))
        views = int(st.get("viewCount",0))
        vids = int(st.get("videoCount",0))
        save_channel_snapshot(ch["id"], subs, views, vids)
        g = get_channel_growth(ch["id"])
        
        text = f"**{ch['snippet']['title']}** - O'sish\n\n{'='*28}\n\n"
        text += f"Obunachilar: `{fmt(subs)}` ({fmt_full(subs)})\n"
        text += f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
        text += f"Videolar: `{fmt(vids)}`\n\n"
        if g:
            text += f"{'='*28}\n\nOxirgi tekshiruvdan beri:\n\n"
            text += f"Obunachilar: {growth_icon(g['sub_growth'])}\n"
            text += f"Ko'rishlar: {growth_icon(g['view_growth'])}\n"
            text += f"Videolar: {growth_icon(g['video_growth'])}\n"
            text += f"\nOldingi: `{g['previous']['snapshot_at'][:19]}`"
        else:
            text += "\nO'sish ma'lumotlari hali yetarli emas."
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /engagement ====================
    @bot.on_message(filters.command("engagement"))
    async def engagement_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/engagement <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Engagement hisoblanmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        
        total_views, total_likes, total_comments = 0, 0, 0
        for v in videos:
            vs = v["statistics"]
            total_views += int(vs.get("viewCount", 0))
            total_likes += int(vs.get("likeCount", 0))
            total_comments += int(vs.get("commentCount", 0))
        
        eng = engagement_rate(total_views, total_likes, total_comments)
        lr = (total_likes / total_views * 100) if total_views else 0
        cr = (total_comments / total_views * 100) if total_views else 0
        
        level = "Juda yaxshi" if eng > 5 else "Yaxshi" if eng > 3 else "O'rtacha" if eng > 1 else "Past"
        
        text = (
            f"**{ch['snippet']['title']}** - Engagement\n\n{'='*28}\n\n"
            f"Oxirgi {len(videos)} ta video asosida:\n\n"
            f"Engagement Rate: **{eng:.2f}%** ({level})\n"
            f"Like Rate: `{lr:.2f}%`\n"
            f"Comment Rate: `{cr:.4f}%`\n\n"
            f"Umumiy ko'rishlar: `{fmt(total_views)}`\n"
            f"Umumiy likelar: `{fmt(total_likes)}`\n"
            f"Umumiy izohlar: `{fmt(total_comments)}`"
        )
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /earnings ====================
    @bot.on_message(filters.command("earnings"))
    async def earnings_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/earnings <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        views = int(ch["statistics"].get("viewCount", 0))
        low, high = estimate_earnings(views)
        
        videos = get_videos_by_channel(ch["id"], max_results=5, order="date")
        monthly_views = 0
        for v in videos:
            monthly_views += int(v["statistics"].get("viewCount", 0))
        m_low, m_high = estimate_earnings(monthly_views)
        
        text = (
            f"**{ch['snippet']['title']}** - Daromad taxmini\n\n{'='*28}\n\n"
            f"Umumiy taxminiy daromad:\n"
            f"  `${low:,.0f}` - `${high:,.0f}`\n\n"
            f"So'nggi videolar asosida (oylik taxmin):\n"
            f"  `${m_low:,.0f}` - `${m_high:,.0f}`\n\n"
            f"CPM oralig'i: $0.50 - $5.00\n\n"
            f"Bu faqat taxmin. Haqiqiy daromad niche, davlat va "
            f"reklama turlariga bog'liq."
        )
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /milestone ====================
    @bot.on_message(filters.command("milestone"))
    async def milestone_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/milestone <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        subs = int(ch["statistics"].get("subscriberCount", 0))
        milestones = [100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000, 100000000]
        next_m = None
        for m in milestones:
            if subs < m:
                next_m = m
                break
        
        text = f"**{ch['snippet']['title']}** - Milestone\n\n{'='*28}\n\n"
        text += f"Hozirgi obunachilar: **{fmt_full(subs)}**\n\n"
        if next_m:
            remaining = next_m - subs
            progress = (subs / next_m) * 100
            bar_len = 20
            filled = int(bar_len * progress / 100)
            bar = "|" * filled + "." * (bar_len - filled)
            text += f"Keyingi milestone: **{fmt(next_m)}**\n"
            text += f"Qoldi: **{fmt_full(remaining)}** obunachi\n"
            text += f"Progress: `[{bar}]` {progress:.1f}%\n"
        else:
            text += "Barcha asosiy milestonelarni qo'lga kiritgan!"
        
        # O'tilgan milestonlar
        passed = [m for m in milestones if subs >= m]
        if passed:
            text += f"\n\nO'tilgan milestonelar: "
            text += ", ".join([f"`{fmt(m)}`" for m in passed])
        
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /report ====================
    @bot.on_message(filters.command("report"))
    async def report_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/report <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("To'liq hisobot tayyorlanmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        
        sn, st = ch["snippet"], ch["statistics"]
        subs = int(st.get("subscriberCount",0))
        views = int(st.get("viewCount",0))
        vids = int(st.get("videoCount",0))
        avg = views//vids if vids else 0
        created = sn.get("publishedAt","")[:10]
        country = sn.get("country","N/A")
        low, high = estimate_earnings(views)
        
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        t_views, t_likes, t_comments = 0, 0, 0
        durations = []
        for v in videos:
            vs = v["statistics"]
            t_views += int(vs.get("viewCount",0))
            t_likes += int(vs.get("likeCount",0))
            t_comments += int(vs.get("commentCount",0))
            durations.append(parse_duration_seconds(v.get("contentDetails",{}).get("duration","")))
        
        eng = engagement_rate(t_views, t_likes, t_comments) if t_views else 0
        avg_dur = sum(durations)//len(durations) if durations else 0
        avg_dur_min = avg_dur // 60
        avg_dur_sec = avg_dur % 60
        
        save_channel_snapshot(ch["id"], subs, views, vids)
        
        text = (
            f"**{sn['title']}** - TO'LIQ HISOBOT\n\n"
            f"{'='*30}\n\n"
            f"**ASOSIY STATISTIKA**\n"
            f"Obunachilar: `{fmt_full(subs)}`\n"
            f"Ko'rishlar: `{fmt_full(views)}`\n"
            f"Videolar: `{fmt_full(vids)}`\n"
            f"O'rtacha/video: `{fmt(avg)}`\n"
            f"Davlat: `{country}`\n"
            f"Yaratilgan: `{created}`\n\n"
            f"**ENGAGEMENT (oxirgi {len(videos)} video)**\n"
            f"Engagement: `{eng:.2f}%`\n"
            f"O'rtacha ko'rish: `{fmt(t_views//len(videos) if videos else 0)}`\n"
            f"O'rtacha like: `{fmt(t_likes//len(videos) if videos else 0)}`\n"
            f"O'rtacha izoh: `{fmt(t_comments//len(videos) if videos else 0)}`\n"
            f"O'rtacha davomiylik: `{avg_dur_min}d {avg_dur_sec}s`\n\n"
            f"**DAROMAD TAXMINI**\n"
            f"Umumiy: `${low:,.0f}` - `${high:,.0f}`\n\n"
            f"{'='*30}\n"
            f"ID: `{ch['id']}`"
        )
        await wait.edit_text(text, reply_markup=channel_action_kb(ch["id"]), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /comments ====================
    @bot.on_message(filters.command("comments"))
    async def comments_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/comments <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        wait = await message.reply_text("Izohlar yuklanmoqda...")
        comments = get_comments(vid_id, max_results=10)
        if not comments:
            await wait.edit_text("Izohlar topilmadi yoki o'chirilgan.")
            return
        text = f"**Top izohlar**\n\n{'='*28}\n\n"
        for i, c in enumerate(comments, 1):
            sn = c["snippet"]["topLevelComment"]["snippet"]
            author = sn.get("authorDisplayName","")[:20]
            txt = sn.get("textDisplay","")[:100]
            likes = int(sn.get("likeCount",0))
            text += f"**{i}. {author}** ({fmt(likes)} like)\n{txt}\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /tags ====================
    @bot.on_message(filters.command("tags"))
    async def tags_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/tags <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        v = get_video(vid_id)
        if not v:
            await message.reply_text("Video ma'lumotlari topilmadi.")
            return
        tags = v["snippet"].get("tags", [])
        if not tags:
            await message.reply_text("Bu videoda teglar topilmadi.")
            return
        text = f"**{v['snippet']['title'][:40]}** - Teglar\n\n"
        text += f"Jami: **{len(tags)}** ta teg\n\n"
        text += " | ".join([f"`{t}`" for t in tags[:40]])
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /thumbnail ====================
    @bot.on_message(filters.command("thumbnail"))
    async def thumbnail_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/thumbnail <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        url = f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg"
        await message.reply_photo(url, caption=f"Video thumbnail\nID: `{vid_id}`", parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /search ====================
    @bot.on_message(filters.command("search"))
    async def search_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/search <so'z>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Qidirilmoqda...")
        results = search_youtube(args[1], "video", 10)
        if not results:
            await wait.edit_text("Natija topilmadi.")
            return
        text = f"**Qidiruv:** `{args[1]}`\n\n{'='*28}\n\n"
        for i, v in enumerate(results, 1):
            vs = v.get("statistics", {})
            views = int(vs.get("viewCount", 0))
            ago = time_ago(v["snippet"].get("publishedAt", ""))
            text += f"**{i}.** {v['snippet']['title'][:45]}\n"
            text += f"   {v['snippet'].get('channelTitle','')} | `{fmt(views)}` | {ago}\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /searchch ====================
    @bot.on_message(filters.command("searchch"))
    async def searchch_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/searchch <kanal nomi>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Kanallar qidirilmoqda...")
        results = search_youtube(args[1], "channel", 10)
        if not results:
            await wait.edit_text("Natija topilmadi.")
            return
        text = f"**Kanal qidiruvi:** `{args[1]}`\n\n{'='*28}\n\n"
        buttons = []
        for i, ch in enumerate(results, 1):
            sn = ch["snippet"]
            title = sn.get("title", sn.get("channelTitle", "N/A"))[:40]
            desc = sn.get("description", "")[:60]
            text += f"**{i}.** {title}\n   {desc}\n\n"
            cid = ch.get("id", {})
            if isinstance(cid, dict):
                cid = cid.get("channelId", "")
            if cid and len(buttons) < 5:
                buttons.append([InlineKeyboardButton(f"{i}. {title[:25]}", callback_data=f"cact_refresh_{cid}")])
        kb = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("Bosh menyu", callback_data="back_main")]]) if buttons else back_main_kb()
        await wait.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /trending ====================
    @bot.on_message(filters.command("trending"))
    async def trending_cmd(client, message):
        args = message.text.split()
        region = args[1].upper() if len(args) > 1 else "US"
        wait = await message.reply_text(f"Trending ({region}) yuklanmoqda...")
        videos = get_trending(region, max_results=10)
        if not videos:
            await wait.edit_text("Trending topilmadi.")
            return
        text = f"**Trending - {region}**\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            text += f"**{i}.** {v['snippet']['title'][:40]}\n"
            text += f"   {v['snippet'].get('channelTitle','')} | `{fmt(views)}`\n\n"
        await wait.edit_text(text, reply_markup=trending_menu_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /track ====================
    @bot.on_message(filters.command("track"))
    async def track_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/track <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        st = ch["statistics"]
        subs, views, vids = int(st.get("subscriberCount",0)), int(st.get("viewCount",0)), int(st.get("videoCount",0))
        add_tracked_channel(message.from_user.id, ch["id"], ch["snippet"]["title"])
        save_channel_snapshot(ch["id"], subs, views, vids)
        await message.reply_text(
            f"**{ch['snippet']['title']}** kuzatishga qo'shildi!\n\n"
            f"Obunachilar: `{fmt(subs)}`\n"
            f"O'sishni ko'rish: `/growth {ch['snippet']['title']}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /untrack ====================
    @bot.on_message(filters.command("untrack"))
    async def untrack_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/untrack <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if ch:
            remove_tracked_channel(message.from_user.id, ch["id"])
            await message.reply_text(f"**{ch['snippet']['title']}** kuzatishdan olib tashlandi.", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("Kanal topilmadi.")
    
    # ==================== /mylist ====================
    @bot.on_message(filters.command("mylist"))
    async def mylist_cmd(client, message):
        channels = get_tracked_channels(message.from_user.id)
        if not channels:
            await message.reply_text("Hali hech qanday kanal kuzatilmayapti.\n\nQo'shish: `/track <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        text = "**Kuzatayotgan kanallarim**\n\n"
        buttons = []
        for i, ch in enumerate(channels, 1):
            text += f"**{i}.** {ch['channel_title']}\n"
            buttons.append([InlineKeyboardButton(f"{ch['channel_title'][:30]}", callback_data=f"cact_refresh_{ch['channel_id']}")])
        kb = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("Bosh menyu", callback_data="back_main")]])
        await message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /checkall ====================
    @bot.on_message(filters.command("checkall"))
    async def checkall_cmd(client, message):
        channels = get_tracked_channels(message.from_user.id)
        if not channels:
            await message.reply_text("Kuzatuvdagi kanallar yo'q.", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Barcha kanallar tekshirilmoqda...")
        text = "**Barcha kanallar holati**\n\n"
        for ch_data in channels:
            chinfo = get_channel({"type": "id", "value": ch_data["channel_id"]})
            if chinfo:
                st = chinfo["statistics"]
                subs = int(st.get("subscriberCount",0))
                views = int(st.get("viewCount",0))
                vids = int(st.get("videoCount",0))
                save_channel_snapshot(ch_data["channel_id"], subs, views, vids)
                g = get_channel_growth(ch_data["channel_id"])
                growth_text = ""
                if g:
                    growth_text = f" ({growth_icon(g['sub_growth'])})"
                text += f"**{chinfo['snippet']['title']}**\n"
                text += f"  `{fmt(subs)}`{growth_text} sub | `{fmt(views)}` views\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /topvideos ====================
    @bot.on_message(filters.command("topvideos"))
    async def topvideos_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/topvideos <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Top videolar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="viewCount")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        videos.sort(key=lambda x: int(x["statistics"].get("viewCount",0)), reverse=True)
        text = f"**{ch['snippet']['title']}** - TOP 10\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            likes = int(vs.get("likeCount", 0))
            eng = engagement_rate(views, likes, int(vs.get("commentCount",0)))
            medal = ["1.", "2.", "3."][i-1] if i <= 3 else f"{i}."
            text += f"**{medal}** {v['snippet']['title'][:40]}\n"
            text += f"   `{fmt(views)}` ko'rish | `{fmt(likes)}` like | eng: `{eng:.1f}%`\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /avgviews ====================
    @bot.on_message(filters.command("avgviews"))
    async def avgviews_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/avgviews <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if not videos:
            await message.reply_text("Videolar topilmadi.")
            return
        views_list = [int(v["statistics"].get("viewCount",0)) for v in videos]
        likes_list = [int(v["statistics"].get("likeCount",0)) for v in videos]
        avg_v = sum(views_list) // len(views_list)
        avg_l = sum(likes_list) // len(likes_list)
        max_v = max(views_list)
        min_v = min(views_list)
        text = (
            f"**{ch['snippet']['title']}** - O'rtacha\n\n{'='*28}\n\n"
            f"Oxirgi {len(videos)} ta video:\n\n"
            f"O'rtacha ko'rish: **{fmt_full(avg_v)}**\n"
            f"O'rtacha like: **{fmt_full(avg_l)}**\n"
            f"Eng ko'p: **{fmt_full(max_v)}**\n"
            f"Eng kam: **{fmt_full(min_v)}**\n"
            f"Farq: **{fmt_full(max_v - min_v)}**"
        )
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /uploadfreq ====================
    @bot.on_message(filters.command("uploadfreq"))
    async def uploadfreq_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/uploadfreq <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if len(videos) < 2:
            await message.reply_text("Yetarli ma'lumot yo'q.")
            return
        dates = []
        for v in videos:
            try:
                dt = datetime.fromisoformat(v["snippet"]["publishedAt"].replace('Z', '+00:00'))
                dates.append(dt)
            except: pass
        if len(dates) < 2:
            await message.reply_text("Sana ma'lumotlari topilmadi.")
            return
        dates.sort(reverse=True)
        diffs = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
        avg_days = sum(diffs) / len(diffs)
        per_week = 7 / avg_days if avg_days > 0 else 0
        per_month = 30 / avg_days if avg_days > 0 else 0
        
        text = (
            f"**{ch['snippet']['title']}** - Upload chastotasi\n\n{'='*28}\n\n"
            f"Oxirgi {len(videos)} ta video asosida:\n\n"
            f"O'rtacha interval: **{avg_days:.1f} kun**\n"
            f"Haftasiga: **{per_week:.1f}** ta video\n"
            f"Oyiga: **{per_month:.1f}** ta video\n"
        )
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /id ====================
    @bot.on_message(filters.command("id"))
    async def id_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/id <URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        url = args[1]
        vid_id = extract_video_id(url)
        ch_id = extract_channel_id(url)
        pl_id = extract_playlist_id(url) if "list=" in url else None
        
        text = "**URL dan ID**\n\n"
        if vid_id and len(vid_id) == 11:
            text += f"Video ID: `{vid_id}`\n"
        if ch_id:
            text += f"Kanal: `{ch_id['value']}` ({ch_id['type']})\n"
        if pl_id and pl_id != url.strip():
            text += f"Playlist ID: `{pl_id}`\n"
        if text == "**URL dan ID**\n\n":
            text += "ID aniqlab bo'lmadi. URL ni tekshiring."
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /categories ====================
    @bot.on_message(filters.command("categories"))
    async def categories_cmd(client, message):
        args = message.text.split()
        region = args[1].upper() if len(args) > 1 else "US"
        cats = get_categories(region)
        if not cats:
            await message.reply_text("Kategoriyalar topilmadi.")
            return
        text = f"**YouTube kategoriyalari ({region})**\n\n"
        for c in cats:
            text += f"`{c['id']}` - {c['snippet']['title']}\n"
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /playlist ====================
    @bot.on_message(filters.command("playlist"))
    async def playlist_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/playlist <URL yoki ID>`", parse_mode=ParseMode.MARKDOWN)
            return
        pl_id = extract_playlist_id(args[1])
        items = get_playlist_items(pl_id, max_results=15)
        if not items:
            await message.reply_text("Pleylist topilmadi yoki bo'sh.")
            return
        text = f"**Pleylist videolari** ({len(items)} ta)\n\n{'='*28}\n\n"
        for i, item in enumerate(items, 1):
            sn = item["snippet"]
            text += f"**{i}.** {sn['title'][:45]}\n"
            text += f"   {sn.get('videoOwnerChannelTitle','')[:30]}\n\n"
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /desc ====================
    @bot.on_message(filters.command("desc"))
    async def desc_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/desc <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        v = get_video(vid_id)
        if not v:
            await message.reply_text("Video ma'lumotlari topilmadi.")
            return
        desc = v["snippet"].get("description", "Tavsif yo'q")[:2000]
        await message.reply_text(f"**{v['snippet']['title'][:40]}**\n\n{desc}", parse_mode=ParseMode.MARKDOWN)
    
    

    # ==================== MASS ENGAGEMENT COMMANDS ====================
    async def get_engagement_users(client, message):
        from database import get_db
        import psycopg2.extras
        is_admin = check_is_admin(message.from_user)
        conn = get_db()
        users = []
        if conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if hasattr(psycopg2, 'extras') else conn.cursor()
            if is_admin:
                cur.execute("SELECT * FROM yt_connections")
            else:
                cur.execute("SELECT * FROM yt_connections WHERE tg_user_id = %s", (message.from_user.id,))
            users = cur.fetchall()
            conn.close()
        return users, is_admin

    @bot.on_message(filters.command("login_status"))
    async def login_status_cmd(client, message):
        from database import get_db
        conn = get_db()
        if not conn:
            await message.reply_text("❌ Xatolik yuz berdi. DB ulanmagan.")
            return
            
        from config import OWNER_ID
        is_admin = str(message.from_user.id) == str(OWNER_ID)
        cur = conn.cursor()
        if is_admin:
            cur.execute("SELECT tg_user_id, yt_channel_title, yt_channel_id FROM yt_connections")
            users = cur.fetchall()
            conn.close()
            if not users:
                await message.reply_text("Hech qanday kanal ulanmagan.")
                return
            text = "👨‍💻 **Barcha Ulangan Kanallar (Admin Panel):**\n\n"
            for u in users:
                text += f"👤 User: `{u['tg_user_id']}`\n📺 Kanal: **{u['yt_channel_title']}**\n🆔 ID: `{u['yt_channel_id']}`\n\n"
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


        else:
            cur.execute("SELECT yt_channel_title, yt_channel_id FROM yt_connections WHERE tg_user_id = %s", (message.from_user.id,))
            users = cur.fetchall()
            conn.close()
            if not users:
                await message.reply_text("❌ Siz hali YouTube kanalingizni ulamagansiz. `/ytlogin` orqali ulang.")
                return
            text = "👤 **Sizning ulangan kanallaringiz:**\n\n"
            for u in users:
                text += f"📺 Kanal: **{u['yt_channel_title']}**\n🆔 ID: `{u['yt_channel_id']}`\n\n"
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @bot.on_message(filters.command("delaccount"))
    async def delaccount_cmd(client, message):
        from database import get_all_yt_connections
        tg_user_id = message.from_user.id
        accounts = get_all_yt_connections(tg_user_id)
        
        if not accounts:
            await message.reply_text("Sizda ulanishlar mavjud emas.")
            return
            
        buttons = []
        for acc in accounts:
            title = acc.get('yt_channel_title', 'Unknown')
            ch_id = acc.get('yt_channel_id', '')
            buttons.append([InlineKeyboardButton(f"🗑 {title}", callback_data=f"delacc_{ch_id}")])
            
        await message.reply_text(
            "O'chirmoqchi bo'lgan akkauntingizni tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    @bot.on_callback_query(filters.regex(r"^delacc_"))
    async def cb_delacc(client, cb: CallbackQuery):
        ch_id = cb.data.replace("delacc_", "")
        buttons = [
            [
                InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"delconf_{ch_id}"),
                InlineKeyboardButton("❌ Yo'q", callback_data="delcancel")
            ]
        ]
        await cb.message.edit_text(
            "⚠️ **Siz ishonchingiz komilmi?**\nBu akkaunt orqali boshqa autopost va mass action amallari bajarilmaydi.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    @bot.on_callback_query(filters.regex(r"^delconf_"))
    async def cb_delconf(client, cb: CallbackQuery):
        ch_id = cb.data.replace("delconf_", "")
        tg_user_id = cb.from_user.id
        from database import delete_yt_connection
        delete_yt_connection(tg_user_id, ch_id)
        await cb.message.edit_text("✅ Akkaunt muvaffaqiyatli o'chirildi!")
        
    @bot.on_callback_query(filters.regex(r"^delcancel$"))
    async def cb_delcancel(client, cb: CallbackQuery):
        await cb.message.edit_text("❌ Bekor qilindi.")

    # ==================== /save_def ====================
    @bot.on_message(filters.command("save_def"))
    async def save_def_cmd(client, message):
        from database import get_all_yt_connections, get_default_account
        tg_user_id = message.from_user.id
        accounts = get_all_yt_connections(tg_user_id)
        
        if not accounts:
            await message.reply_text("❌ Sizda ulangan YouTube akkauntlar yo'q.\n`/ytlogin` orqali ulang.", parse_mode=ParseMode.MARKDOWN)
            return
        
        current_default = get_default_account(tg_user_id)
        
        buttons = []
        for acc in accounts:
            title = acc.get('yt_channel_title', 'Unknown')
            ch_id = acc.get('yt_channel_id', '')
            marker = " ✅" if ch_id == current_default else ""
            buttons.append([InlineKeyboardButton(f"📺 {title}{marker}", callback_data=f"setdef_{ch_id}")])
        
        text = "⚙️ **Default akkauntni tanlang:**\n\n"
        text += "Bu akkaunt autopost, mass action va boshqa amallarda avtomatik ishlatiladi.\n"
        if current_default:
            def_name = next((a.get('yt_channel_title', '?') for a in accounts if a.get('yt_channel_id') == current_default), "?")
            text += f"\n🟢 Hozirgi default: **{def_name}**"
        else:
            text += "\n🔴 Hozirda default akkaunt belgilanmagan."
        
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)
    
    @bot.on_callback_query(filters.regex(r"^setdef_"))
    async def cb_setdef(client, cb: CallbackQuery):
        ch_id = cb.data.replace("setdef_", "")
        tg_user_id = cb.from_user.id
        
        from database import set_default_account, get_all_yt_connections
        
        accounts = get_all_yt_connections(tg_user_id)
        acc_name = next((a.get('yt_channel_title', '?') for a in accounts if a.get('yt_channel_id') == ch_id), ch_id)
        
        success = set_default_account(tg_user_id, ch_id)
        if success:
            await cb.message.edit_text(
                f"✅ **Default akkaunt saqlandi!**\n\n"
                f"📺 **{acc_name}**\n\n"
                f"Endi `/autopost` va `/mass` buyruqlarida bu akkaunt avtomatik ishlatiladi.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await cb.message.edit_text("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")

    @bot.on_message(filters.command("mass_like"))
    async def mass_like_cmd(client, message):
        from mass_engagement import run_mass_engagement
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/mass_like <video_id>`", parse_mode=ParseMode.MARKDOWN)
            return
        video_id = args[1]
        users, is_admin = await get_engagement_users(client, message)
        if not users:
            await message.reply_text("❌ Hech qanday YouTube ulanish topilmadi. Avval /ytlogin qiling.")
            return
        msg = "👑 **Admin Mode:** Barcha" if is_admin else "👤 **User Mode:** Sizning"
        await message.reply_text(f"👍 {msg} hisoblar orqali Like bosish boshlandi! (Topilgan hisoblar: {len(users)})\nVideo ID: `{video_id}`", parse_mode=ParseMode.MARKDOWN)
        import asyncio
        asyncio.create_task(run_mass_engagement("like", video_id, users, message.chat.id, client))

    @bot.on_message(filters.command("mass_comment"))
    async def mass_comment_cmd(client, message):
        from mass_engagement import run_mass_engagement
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/mass_comment <video_id>`", parse_mode=ParseMode.MARKDOWN)
            return
        video_id = args[1]
        users, is_admin = await get_engagement_users(client, message)
        if not users:
            await message.reply_text("❌ Hech qanday YouTube ulanish topilmadi.")
            return
        msg = "👑 **Admin Mode:** Barcha" if is_admin else "👤 **User Mode:** Sizning"
        await message.reply_text(f"💬 {msg} hisoblar orqali Comment yozish boshlandi! (Topilgan: {len(users)})\nVideo ID: `{video_id}`", parse_mode=ParseMode.MARKDOWN)
        import asyncio
        asyncio.create_task(run_mass_engagement("comment", video_id, users, message.chat.id, client))

    @bot.on_message(filters.command("mass_sub"))
    async def mass_sub_cmd(client, message):
        from mass_engagement import run_mass_engagement
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/mass_sub <channel_id>`", parse_mode=ParseMode.MARKDOWN)
            return
        channel_id = args[1]
        users, is_admin = await get_engagement_users(client, message)
        if not users:
            await message.reply_text("❌ Hech qanday YouTube ulanish topilmadi.")
            return
        msg = "👑 **Admin Mode:** Barcha" if is_admin else "👤 **User Mode:** Sizning"
        await message.reply_text(f"🔔 {msg} hisoblar orqali Obuna bo'lish boshlandi! (Topilgan: {len(users)})\nChannel ID: `{channel_id}`", parse_mode=ParseMode.MARKDOWN)
        import asyncio
        asyncio.create_task(run_mass_engagement("subscribe", channel_id, users, message.chat.id, client))

    # 2-qadam: Shorts yoki Video tanlangandan keyin
    @bot.on_callback_query(filters.regex(r"^ap_type\|"))
    async def autopost_type_select(client, callback_query: CallbackQuery):
        data = callback_query.data.split("|")
        short_id = data[1]
        video_type = data[2]  # "shorts" yoki "video"
        
        args = AUTOPOST_ARGS_MAP.get(short_id)
        if not args:
            await callback_query.answer("❌ Muddati tugagan. Qaytadan /autopost yuboring.", show_alert=True)
            return
        
        topic = args["topic"]
        # Qidiruv so'zini to'g'ri shakllantirish
        if video_type == "shorts":
            query = f"{topic} shorts"
        else:
            query = topic
        
        args["query"] = query
        args["video_type"] = video_type
        
        connections = args["connections"]
        
        # Default akkaunt tekshirish
        from database import get_default_account
        default_ch_id = get_default_account(callback_query.from_user.id)
        
        # Agar default akkaunt belgilangan va u connections ichida bo'lsa, darhol ishlatish
        default_conn = None
        if default_ch_id:
            default_conn = next((c for c in connections if c.get('yt_channel_id') == default_ch_id), None)
        
        if default_conn:
            # Default akkaunt topildi — darhol watermark so'rash
            yt_channel_id = default_ch_id
            args["yt_channel_id"] = yt_channel_id
            
            user_id = args["user_id"]
            count = args["count"]
            
            task_id = create_autopost_task(user_id, yt_channel_id, query, video_type, count)
            if task_id:
                from database import update_autopost_task
                update_autopost_task(task_id, status="awaiting_choice")
                increment_usage(user_id, count)
                
                type_text = "🩳 Shorts" if video_type == "shorts" else "🎬 Katta video"
                buttons = [
                    [InlineKeyboardButton("✅ Watermark bilan", callback_data=f"ap_wm|{task_id}")],
                    [InlineKeyboardButton("❌ Aslidek (Watermarksiz)", callback_data=f"ap_nowm|{task_id}")]
                ]
                await callback_query.message.edit_text(
                    f"✅ Tur: **{type_text}** | Mavzu: **'{topic}'** | Video soni: **{count}**\n\n"
                    f"Video ustiga YouTube kanalingiz nomi va rasmi (watermark) qo'yilsinmi?", 
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await callback_query.message.edit_text("❌ `Xatolik yuz berdi. DB ni tekshiring.`", parse_mode=ParseMode.MARKDOWN)
        elif len(connections) > 1:
            # Ko'p kanal bor, default belgilanmagan — kanal tanlash menyusi
            buttons = []
            for c in connections:
                ch_title = c.get('yt_channel_title', 'Noma\'lum')
                buttons.append([InlineKeyboardButton(f"📺 {ch_title}", callback_data=f"ap_ch|{short_id}|{c['yt_channel_id']}")])
                
            type_text = "🩳 Shorts" if video_type == "shorts" else "🎬 Katta video"
            await callback_query.message.edit_text(
                f"✅ Tur: **{type_text}** | Mavzu: **'{topic}'**\n\n"
                f"📺 **Qaysi kanalga video yuklaymiz?**\n\n"
                f"💡 _Default akkaunt saqlash uchun /save\\_def yozing._",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # 1 ta kanal, default belgilanmagan — yagona kanalni ishlatish
            yt_channel_id = connections[0]["yt_channel_id"]
            args["yt_channel_id"] = yt_channel_id
            
            user_id = args["user_id"]
            count = args["count"]
            
            task_id = create_autopost_task(user_id, yt_channel_id, query, video_type, count)
            if task_id:
                from database import update_autopost_task
                update_autopost_task(task_id, status="awaiting_choice")
                increment_usage(user_id, count)
                
                type_text = "🩳 Shorts" if video_type == "shorts" else "🎬 Katta video"
                buttons = [
                    [InlineKeyboardButton("✅ Watermark bilan", callback_data=f"ap_wm|{task_id}")],
                    [InlineKeyboardButton("❌ Aslidek (Watermarksiz)", callback_data=f"ap_nowm|{task_id}")]
                ]
                await callback_query.message.edit_text(
                    f"✅ Tur: **{type_text}** | Mavzu: **'{topic}'** | Video soni: **{count}**\n\n"
                    f"Video ustiga YouTube kanalingiz nomi va rasmi (watermark) qo'yilsinmi?", 
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await callback_query.message.edit_text("❌ `Xatolik yuz berdi. DB ni tekshiring.`", parse_mode=ParseMode.MARKDOWN)

    # 3-qadam (multi-account): Kanal tanlangandan keyin
    @bot.on_callback_query(filters.regex(r"^ap_ch\|"))
    async def autopost_channel_select(client, callback_query: CallbackQuery):
        data = callback_query.data.split("|")
        short_id = data[1]
        yt_channel_id = data[2]
        
        args = AUTOPOST_ARGS_MAP.get(short_id)
        if not args:
            await callback_query.answer("❌ Muddati tugagan. Qaytadan /autopost yuboring.", show_alert=True)
            return
            
        user_id = args["user_id"]
        count = args["count"]
        query = args["query"]
        topic = args["topic"]
        video_type = args.get("video_type", "video")
        
        task_id = create_autopost_task(user_id, yt_channel_id, query, video_type, count)
        
        if task_id:
            from database import update_autopost_task
            update_autopost_task(task_id, status="awaiting_choice")
            increment_usage(user_id, count)
            
            type_text = "🩳 Shorts" if video_type == "shorts" else "🎬 Katta video"
            buttons = [
                [InlineKeyboardButton("✅ Watermark bilan", callback_data=f"ap_wm|{task_id}")],
                [InlineKeyboardButton("❌ Aslidek (Watermarksiz)", callback_data=f"ap_nowm|{task_id}")]
            ]
            await callback_query.message.edit_text(
                f"✅ Tur: **{type_text}** | Mavzu: **'{topic}'** | Video soni: **{count}**\n\n"
                f"Video ustiga YouTube kanalingiz nomi va rasmi (watermark) qo'yilsinmi?", 
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await callback_query.message.edit_text("❌ `Xatolik yuz berdi. DB ni tekshiring.`", parse_mode=ParseMode.MARKDOWN)

    # ==================== /dbreset (Admin only) ====================
    @bot.on_message(filters.command("dbreset"))
    async def dbreset_cmd(client, message):
        if not check_is_admin(message.from_user):
            await message.reply_text("❌ `Sizda huquq yo'q!`", parse_mode=ParseMode.MARKDOWN)
            return
        
        from database import reset_all_data
        success = reset_all_data()
        if success:
            await message.reply_text("✅ `Baza to'liq tozalandi (TRUNCATE)! Hamma yozuvlar, tokenlar, settings o'chdi.`", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("❌ `Xatolik yuz berdi, baza tozalanmadi!`", parse_mode=ParseMode.MARKDOWN)

    @bot.on_callback_query(filters.regex(r"^ap_wm\|") | filters.regex(r"^ap_nowm\|"))
    async def ap_watermark_callback(client, callback_query: CallbackQuery):
        data = callback_query.data.split("|")
        action = data[0]
        task_id = int(data[1])
        
        user_id = callback_query.from_user.id
        from database import get_autopost_task_by_id
        task = get_autopost_task_by_id(task_id)
        if not task:
            await callback_query.message.edit_text("❌ Vazifa topilmadi!")
            return
            
        query = task["search_query"]
        count = task["total_count"]
        user_proxy = get_user_proxy(user_id) or DEFAULT_PROXY
        
        apply_watermark = (action == "ap_wm")

        # apply_watermark ni DB ga saqlaymiz
        from database import update_autopost_task
        update_autopost_task(task_id, status="pending")

        # Watermark flagni DB ga yozish (worker o'qiydi)
        conn_db = None
        try:
            from database import get_db
            conn_db = get_db()
            if conn_db:
                cur_db = conn_db.cursor()
                cur_db.execute(
                    "UPDATE autopost_tasks SET apply_watermark=%s WHERE id=%s",
                    (apply_watermark, task_id)
                )
                conn_db.commit()
        except Exception as _e:
            print(f"watermark update error: {_e}")
        finally:
            if conn_db:
                try: conn_db.close()
                except: pass

        await callback_query.message.edit_text(
            f"✅ `Auto-post navbatga qo'shildi!`\n"
            f"📋 `{count}` ta video · `{query}`\n"
            f"Watermark: {'Yoqilgan ✅' if apply_watermark else 'O`chirilgan ❌'}\n\n"
            "Bo'sh worker qidirilmoqda..."
        )

        # ROLE=main: avval tashqi WORKER_URLS dagi bo'sh serverga push qilishga
        # urinamiz; hech kim bo'sh bo'lmasa RAM limiti ichida main o'zi bajaradi;
        # aks holda task DB da 'pending' qoladi va istalgan worker/autoposter
        # (poll orqali) yoki keyingi dispatch uni oladi. Fon vazifasiga o'ramiz —
        # aks holda bu callback handler boshqa foydalanuvchilarning callback
        # so'rovlarini tashqi /status javobini kutib turib kechiktirib qo'yadi.
        try:
            from main import dispatch_or_run_autopost
            import asyncio as _asyncio
            _asyncio.create_task(dispatch_or_run_autopost(task_id))
        except Exception as _dispatch_err:
            print(f"[autopost dispatch] xato: {_dispatch_err}")

    @bot.on_callback_query(filters.regex(r"^(back_main|main_menu)$"))
    async def cb_back_main(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        lang = get_user_language(user_id)
        name = (cb.from_user.first_name or "Foydalanuvchi") if cb.from_user else "Foydalanuvchi"
        await cb.message.edit_text(t("main_menu", lang, name=name), reply_markup=main_menu_kb(user_id))
        await cb.answer()
    
    @bot.on_callback_query(filters.regex(r"^menu_(wallet|marketplace|instagram|channel|video|analytics|search|tracking|tools|trending|help)$"))
    async def cb_menu(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        if not check_is_admin(cb.from_user) and not is_user_kyc_verified(user_id):
            await cb.answer("⚠️ Botdan foydalanish uchun avval 3D biometrik identifikatsiyadan o'ting! /start ni bosing.", show_alert=True)
            return

        menu = cb.data.replace("menu_", "")
        
        if menu == "wallet":
            bal = get_user_balance(user_id)
            lang = get_user_language(user_id)
            text = t("balance_text", lang, balance=bal)
            await cb.message.edit_text(text, reply_markup=wallet_menu_kb())
            await cb.answer()
            return
            
        if menu == "marketplace":
            bal = get_user_balance(user_id)
            from database import get_api_keys_stock_count, get_proxies_stock_count
            stock = get_api_keys_stock_count()
            op_stock = stock.get("openrouter", 0)
            gm_stock = stock.get("gemini", 0)
            gq_stock = stock.get("groq", 0)
            pr_stock = get_proxies_stock_count()
            text = (
                f"{e('CASH')} <b>Marketplace & Raqamli Xizmatlar Do'koni</b>\n\n"
                f"{e('MONEY')} <b>Joriy balans:</b> <code>{bal:,} so'm</code>\n\n"
                f"<b>🌐 Proxy & Server Quvvati:</b>\n"
                f"• {e('PROXY')} <b>Dedicated Private Proxy:</b> $3 (38,000 so'm) — <i>Zaxirada: {pr_stock} ta</i>\n"
                f"• {e('STREAM')} <b>24/7 Autostream Cloud Slot:</b> $0.5 / soat (6,000 so'm/soat)\n\n"
                f"<b>🤖 AI API Kalitlar:</b>\n"
                f"• {e('OPENROUTER')} <b>OpenRouter API ($3):</b> 38,000 so'm — <i>Zaxirada: {op_stock} ta</i>\n"
                f"• {e('GEMINI')} <b>Google Gemini API ($5):</b> 64,000 so'm — <i>Zaxirada: {gm_stock} ta</i>\n"
                f"• {e('GROQ')} <b>Groq Cloud API (gptoss 120b):</b> 10,000 so'm — <i>Zaxirada: {gq_stock} ta</i>\n\n"
                f"<b>🎨 AI Kreativ & Kontent:</b>\n"
                f"• {e('FLUX')} <b>Flux.1 AI Rasm Generatsiya:</b> $2/hafta (25,000 so'm, 25 ta rasm)\n"
                f"• {e('IDEA')} <b>500+ Viral Prompt & SEO Tag Pack:</b> $3 (38,000 so'm)\n"
                f"• {e('CLIPPER')} <b>3 ta Vertical Shorts Kesish:</b> $1 (12,800 so'm) / video\n\n"
                f"<b>⚡ Kanal Rivojlantirish & DeepLink:</b>\n"
                f"• {e('QR_DEEPLINK')} <b>YouTube DeepLink & Smart QR:</b> 3,000 so'm\n"
                f"• {e('LIGHTNING')} <b>Video Unikalizatsiya & Content ID:</b> 1,500 so'm\n"
                f"• 👑 <b>VIP Cheksiz Pro Obuna:</b> $15 / oy (192,000 so'm)\n"
                f"• 💎 <b>Referal & 10% Keshbek Tizimi</b>\n\n"
                f"{e('PIN')} Kerakli mahsulot yoki xizmatni tanlang:"
            )
            await cb.message.edit_text(text, reply_markup=marketplace_menu_kb())
            await cb.answer()
            return
            
        if menu == "instagram":
            text = (
                f"{e('INSTA')} <b>Instagram Reels Yuklash & YouTube Shorts</b>\n\n"
                f"{e('LIGHTNING')} Instagram Reels havolasini to'g'ridan-to'g'ri botga yuboring!\n\n"
                f"Xususiyatlar:\n"
                f"• {e('CHECK')} Eng yuqori sifatda videoni yuklab beradi\n"
                f"• {e('SHIELD')} Avtorlik huquqi (Content ID) filtri avtomatik qo'llanadi\n"
                f"• {e('SHORTS')} To'g'ridan-to'g'ri YouTube kanalingizga Shorts qilib joylaydi!\n\n"
                f"{e('PIN')} Instagram video havolasini chatga yuboring:"
            )
            await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")]]))
            await cb.answer()
            return

        menus = {
            "channel": ("**Kanal tahlili**\n\nKanal nomini yoki URL ni buyruq bilan yuboring:", channel_menu_kb()),
            "video": ("**Video tahlili**\n\nVideo URL ni buyruq bilan yuboring:", video_menu_kb()),
            "analytics": ("**Analitika va O'sish**\n\nKanal nomini buyruq bilan yuboring:", analytics_menu_kb()),
            "search": ("**Qidiruv**\n\nQidiruv so'zini buyruq bilan yuboring:", search_menu_kb()),
            "tracking": ("**Kanal kuzatuvi**\n\nKanallarni kuzatib boring:", tracking_menu_kb()),
            "tools": ("**Asboblar**\n\nTurli foydali vositalar:", tools_menu_kb()),
            "trending": ("**Trending**\n\nDavlatni tanlang:", trending_menu_kb()),
            "help": ("**Yordam**\n\nKategoriyani tanlang:", help_menu_kb()),
        }
        if menu in menus:
            text, kb = menus[menu]
            await cb.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            await cb.answer()
            return
        cb.continue_propagation()

    # ==================== TO'LOV VA MARKETPLACE CALLBACKLARI ====================
    
    @bot.on_callback_query(filters.regex(r"^pay_stars_menu$"))
    async def cb_pay_stars_menu(client, cb: CallbackQuery):
        text = (
            f"{e('STAR')} <b>Telegram Stars orqali hisob to'ldirish</b>\n\n"
            f"Telegram Stars — Telegramning rasmiy xavfsiz to'lov vositasi.\n"
            f"O'zingizga ma'qul bo'lgan paketni tanlang:"
        )
        await cb.message.edit_text(text, reply_markup=stars_packages_kb())
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^stars_pkg_(\d+)$"))
    async def cb_stars_pkg(client, cb: CallbackQuery):
        stars = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        amount_uzs = 12500
        for pkg in STARS_PACKAGES:
            if pkg["stars"] == stars:
                amount_uzs = pkg["amount_uzs"]
                break
        tx_id = create_payment_transaction(user_id, "stars", stars, "XTR", amount_uzs)
        bot_token = getattr(client, "bot_token", None) or BOT_TOKEN
        payload = f"stars_{user_id}_{stars}_{amount_uzs}_{tx_id}"
        res = await _send_bot_api_invoice(
            bot_token=bot_token,
            chat_id=cb.message.chat.id,
            title=f"⭐ {stars} Telegram Stars",
            description=f"Hisobingizga +{amount_uzs:,} so'm qo'shiladi",
            payload=payload,
            currency="XTR",
            prices=[{"label": f"{stars} Stars", "amount": stars}],
            provider_token=""
        )
        if res:
            await cb.answer("To'lov cheki yuborildi! Yuqoridagi chek orqali to'lang.", show_alert=False)
        else:
            await cb.answer("To'lov chekini yaratib bo'lmadi!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^pay_crypto_menu$"))
    async def cb_pay_crypto_menu(client, cb: CallbackQuery):
        text = (
            f"{e('CRYPTO')} <b>CryptoPay (@CryptoBot) orqali to'ldirish</b>\n\n"
            f"USDT yoki GRAM (sobiq TON) orqali bir zumda to'ldiring.\n"
            f"Kerakli paketni tanlang:"
        )
        await cb.message.edit_text(text, reply_markup=crypto_packages_kb())
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^crypto_pkg_([0-9d]+)_([A-Z]+)$"))
    async def cb_crypto_pkg(client, cb: CallbackQuery):
        raw_amount = cb.matches[0].group(1).replace('d', '.')
        amount = float(raw_amount)
        asset = cb.matches[0].group(2)
        user_id = cb.from_user.id
        
        amount_uzs = int(amount * 13000) if asset == "USDT" else int(amount * 20000)
        for pkg in CRYPTO_PACKAGES:
            if pkg["asset"] == asset and float(pkg["amount"]) == amount:
                amount_uzs = pkg["amount_uzs"]
                break

        # ================= TON TO'G'RIDAN-TO'G'RI BLOCKCHAIN TO'LOVI =================
        if asset == "TON":
            ton_wallet = get_ton_wallet()
            if not ton_wallet:
                await cb.answer("⚠️ Botda TON hamyon hali o'rnatilmagan. Adminga murojaat qiling yoki Stars orqali to'ldiring.", show_alert=True)
                return

            tx_id = create_payment_transaction(user_id, "ton_direct", amount, "TON", amount_uzs)
            nano_amount = int(amount * 1e9)
            tonkeeper_link = f"https://app.tonkeeper.com/transfer/{ton_wallet}?amount={nano_amount}&text=tx_{tx_id}"

            text = (
                f"{e('CRYPTO')} <b>TON orqali to'lov</b>\n\n"
                f"💰 <b>Balansga qo'shiladi:</b> +{amount_uzs:,} so'm\n"
                f"🪙 <b>To'lov miqdori:</b> <code>{amount} TON</code>\n"
                f"🆔 <b>To'lov kodi (Izoh):</b> <code>tx_{tx_id}</code>\n\n"
                f"<b>To'lov qilish tartibi:</b>\n"
                f"1. Quyidagi <b>«📲 Tonkeeper orqali to'lash»</b> tugmasini bosing (barcha ma'lumotlar avtomatik to'ldiriladi, faqat tasdiqlaysiz).\n\n"
                f"2. <b>Yoki qo'lda o'tkazish uchun:</b>\n"
                f"💎 <b>Hamyon:</b> (nusxalash uchun ustiga bosing)\n"
                f"<code>{ton_wallet}</code>\n"
                f"💬 <b>Izoh (MEMO/Comment):</b> <code>tx_{tx_id}</code>\n\n"
                f"⚠️ <b>DIQQAT:</b> O'tkazma izoh (comment) qismiga <code>tx_{tx_id}</code> deb yozishingiz shart! Aks holda tizim to'lovni avtomatik aniqlay olmaydi.\n\n"
                f"<i>To'laganingizdan so'ng 5-15 soniyada hisobingiz avtomatik to'ldiriladi yoki quyidagi «🔍 Tekshirish» tugmasini bosing.</i>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📲 Tonkeeper orqali to'lash ({amount} TON)", url=tonkeeper_link)],
                [InlineKeyboardButton("🔍 To'lovni tekshirish", callback_data=f"check_ton_tx_{tx_id}")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_wallet")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
            return

        # ================= USDT UCHUN CRYPTOPAY =================
        tx_id = create_payment_transaction(user_id, "cryptopay", amount, asset, amount_uzs)
        try:
            invoice_res = await create_crypto_pay_invoice(user_id, asset, amount, amount_uzs, tx_id)
            if invoice_res.get("ok"):
                pay_url = invoice_res["pay_url"]
                text = (
                    f"{e('CRYPTO')} <b>USDT orqali to'lov</b>\n\n"
                    f"💰 <b>Balansga qo'shiladi:</b> +{amount_uzs:,} so'm\n"
                    f"🪙 <b>To'lov summasi:</b> {amount} {asset}\n"
                    f"🆔 <b>Buyurtma ID:</b> <code>#{tx_id}</code>\n\n"
                    f"⚡ To'lovni amalga oshirish uchun quyidagi tugmani bosing:\n"
                    f"<i>(To'lovdan so'ng hisobingiz 1-2 soniyada avtomatik to'ldiriladi)</i>"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"💳 To'lov qilish ({amount} {asset})", url=pay_url)],
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_wallet")]
                ])
                await cb.message.edit_text(text, reply_markup=kb)
            else:
                await cb.answer(f"Xato: {invoice_res.get('error', 'Invoice yaratib bo`lmadi')}", show_alert=True)
        except Exception as inv_err:
            await cb.answer(f"To'lov tizimi xatosi: {inv_err}", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^check_ton_tx_(\d+)$"))
    async def cb_check_ton_tx(client, cb: CallbackQuery):
        tx_id = int(cb.matches[0].group(1))
        from ton_checker import verify_and_credit_ton_tx
        
        await cb.answer("🔍 Blockchain tekshirilmoqda...", show_alert=False)
        res = await verify_and_credit_ton_tx(tx_id)
        if res.get("ok"):
            tx = res.get("tx", {})
            amount_uzs = tx.get("amount_uzs", 0)
            amount_ton = tx.get("amount_original", 1.0)
            new_bal = res.get("new_balance") or get_user_balance(cb.from_user.id)
            text = (
                f"✅ <b>To'lov muvaffaqiyatli qabul qilindi!</b>\n\n"
                f"🪙 <b>To'lov:</b> {amount_ton} GRAM (TON)\n"
                f"💰 <b>Qo'shilgan summa:</b> +{amount_uzs:,} so'm\n"
                f"⚖️ <b>Joriy balansingiz:</b> {new_bal:,} so'm\n\n"
                f"🚀 Endi layk, obuna yoki izoh xizmatlaridan bemalol foydalanishingiz mumkin!"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Xizmatlar do'koni", callback_data="menu_marketplace")],
                [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
        else:
            await cb.answer(
                f"⏳ To'lov hali TON tarmog'ida tasdiqlanmadi.\n\n"
                f"1. To'lovni yubordingizmi?\n"
                f"2. Izoh (memo) ga 'tx_{tx_id}' deb kiritdingizmi?\n\n"
                f"Blockchainda tasdiqlanish uchun 5-15 soniya vaqt oladi. Birozdan so'ng yana bosing.",
                show_alert=True
            )

    @bot.on_callback_query(filters.regex(r"^pay_history$"))
    async def cb_pay_history(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        history = get_user_payment_history(user_id, limit=5)
        if not history:
            text = f"{e('INFO')} Sizda hali to'lovlar tarixi mavjud emas."
        else:
            lines = [f"{e('LIST')} <b>Oxirgi to'lovlar:</b>\n"]
            for h in history:
                st = "✅ Bajarildi" if h['status'] == 'completed' else "⏳ Kutilmoqda"
                lines.append(f"• #{h['id']} — +{h['amount_uzs']:,} so'm ({h['payment_type'].upper()}) [{st}]")
            text = "\n".join(lines)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_wallet")]])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_order_(like|subscribe|comment)$"))
    async def cb_mkt_order(client, cb: CallbackQuery):
        action = cb.matches[0].group(1)
        user_id = cb.from_user.id
        USER_ORDER_STATE[user_id] = {"action": action, "step": "awaiting_url"}
        
        names = {"like": "Layk", "subscribe": "Obuna", "comment": "Izoh"}
        prompt_text = (
            f"{e('TARGET')} <b>{names.get(action)} buyurtma berish</b>\n\n"
            f"{e('LINK')} Iltimos, YouTube video yoki kanal havolasini chatga yuboring:\n"
            f"<i>(Masalan: https://youtu.be/xxx yoki https://youtube.com/@channel)</i>"
        )
        await cb.message.edit_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_cancel")]])
        )
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_qty_(like|subscribe|comment)_(\d+)$"))
    async def cb_mkt_qty(client, cb: CallbackQuery):
        action = cb.matches[0].group(1)
        qty = int(cb.matches[0].group(2))
        user_id = cb.from_user.id
        
        state = USER_ORDER_STATE.get(user_id, {})
        target_url = state.get("target_url", "")
        if not target_url:
            await cb.answer("Iltimos, avval havolani yuboring!", show_alert=True)
            return
            
        prices = {"like": 1500, "subscribe": 2500, "comment": 1000}
        price_per_item = prices.get(action, 1500)
        total_cost = qty * price_per_item
        
        user_bal = get_user_balance(user_id)
        if user_bal < total_cost:
            text = (
                f"{e('WARN')} <b>Balansingizda mablag' yetarli emas!</b>\n\n"
                f"💰 <b>Joriy balans:</b> {user_bal:,} so'm\n"
                f"💸 <b>Buyurtma summasi:</b> {total_cost:,} so'm\n"
                f"⚠️ <b>Yetishmayotgan summa:</b> {(total_cost - user_bal):,} so'm\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ Telegram Stars orqali to'ldirish", callback_data="pay_stars_menu")],
                [InlineKeyboardButton("🪙 CryptoPay orqali to'ldirish", callback_data="pay_crypto_menu")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
            return
            
        state["qty"] = qty
        state["total_cost"] = total_cost
        USER_ORDER_STATE[user_id] = state
        
        names = {"like": "Layk", "subscribe": "Obuna", "comment": "Izoh"}
        confirm_text = (
            f"{e('TARGET')} <b>Buyurtmani tasdiqlash</b>\n\n"
            f"🎯 <b>Xizmat:</b> {names.get(action)}\n"
            f"🔗 <b>Manzil:</b> <code>{target_url}</code>\n"
            f"🔢 <b>Miqdor:</b> {qty} ta\n"
            f"💰 <b>Jami summa:</b> {total_cost:,} so'm\n\n"
            f"Buyurtmani tasdiqlaysizmi?"
        )
        await cb.message.edit_text(confirm_text, reply_markup=order_confirm_kb(action, qty, total_cost))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_(like|subscribe|comment)_(\d+)_(\d+)$"))
    async def cb_mkt_confirm(client, cb: CallbackQuery):
        action = cb.matches[0].group(1)
        qty = int(cb.matches[0].group(2))
        total_cost = int(cb.matches[0].group(3))
        user_id = cb.from_user.id
        
        state = USER_ORDER_STATE.pop(user_id, {})
        target_url = state.get("target_url")
        if not target_url:
            await cb.answer("Buyurtma muddati tugagan. Qaytadan boshlang.", show_alert=True)
            return
            
        success = deduct_user_balance(user_id, total_cost)
        if not success:
            await cb.answer("Balansda mablag' yetarli emas!", show_alert=True)
            return
            
        target_id = extract_video_id(target_url)
        order_id = create_engagement_order(user_id, action, target_url, target_id, qty, total_cost)
        
        await cb.message.edit_text(
            f"{e('SUCCESS')} <b>Buyurtma #{order_id} muvaffaqiyatli qabul qilindi!</b>\n\n"
            f"🎯 <b>Xizmat:</b> {action.upper()}\n"
            f"🔢 <b>Miqdor:</b> {qty} ta\n"
            f"💰 <b>To'langan:</b> {total_cost:,} so'm\n\n"
            f"🛡️ Akkauntlar orqali xavfsiz bajarish boshlandi...",
            reply_markup=main_menu_kb(user_id)
        )
        await cb.answer()
        
        asyncio.create_task(execute_engagement_order_task(order_id, user_id, action, target_url, qty, client, cb.message.chat.id))

    @bot.on_callback_query(filters.regex(r"^mkt_cancel$"))
    async def cb_mkt_cancel(client, cb: CallbackQuery):
        USER_ORDER_STATE.pop(cb.from_user.id, None)
        await cb.message.edit_text("Buyurtma bekor qilindi.", reply_markup=main_menu_kb(cb.from_user.id))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_my_orders$"))
    async def cb_mkt_my_orders(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        orders = get_user_engagement_orders(user_id, limit=5)
        if not orders:
            text = f"{e('INFO')} Sizda hali buyurtmalar yo'q."
        else:
            lines = [f"{e('LIST')} <b>Mening buyurtmalarim:</b>\n"]
            for o in orders:
                lines.append(f"• #{o['id']} {o['order_type'].upper()} — {o['completed_count']}/{o['quantity']} ta [{o['status'].upper()}]")
            text = "\n".join(lines)
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]]))
        await cb.answer()

    # ==================== AI API KEYS DO'KONI (OpenRouter $3, Gemini $5, Groq 10k) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_(openrouter|gemini|groq)$"))
    async def cb_mkt_view_key(client, cb: CallbackQuery):
        service = cb.matches[0].group(1).lower()
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        stock = get_api_keys_stock_count()
        cur_stock = stock.get(service, 0)
        
        if service == "openrouter":
            price_uzs = 38000
            desc = (
                f"{e('OPENROUTER')} <b>OpenRouter API Kalit ($3 balans bilan)</b>\n\n"
                f"• GPT-4o, Claude 3.5 Sonnet, Llama 3 va 100+ AI modellarini bitta API orqali ishlatish imkoniyati!\n"
                f"• Rasmiy hisobda $3 dollar balans mavjud.\n"
                f"• Butun dunyo bo'yicha hech qanday VPN va cheklovlarsiz ishlaydi.\n\n"
                f"💵 <b>Narxi:</b> $3 — <code>{price_uzs:,} so'm</code>\n"
                f"📦 <b>Zaxirada mavjud:</b> <code>{cur_stock} ta</code>\n"
                f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
            )
        elif service == "gemini":
            price_uzs = 64000
            desc = (
                f"{e('GEMINI')} <b>Google Gemini API Kalit ($5 balans)</b>\n\n"
                f"• Gemini 1.5 Pro va Flash modellari uchun yuqori tezlikdagi rasmiy API kalit!\n"
                f"• YouTube izohlari, avtomatizatsiya va matn yaratish uchun ideal.\n"
                f"• Rasmiy Google AI Studio kaliti, xavfsiz va faol.\n\n"
                f"💵 <b>Narxi:</b> $5 — <code>{price_uzs:,} so'm</code>\n"
                f"📦 <b>Zaxirada mavjud:</b> <code>{cur_stock} ta</code>\n"
                f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
            )
        else: # groq
            price_uzs = 10000
            desc = (
                f"{e('GROQ')} <b>Groq Cloud API Kalit (Ultra-Tezkor LPU)</b>\n\n"
                f"• Dunyodagi eng tezkor AI arxitekturasi: sekundiga 500+ token tezlik!\n"
                f"• <b>gptoss 120b</b> va <b>Llama 3.3 70B</b> modellarini maksimal tezlikda ishlatish uchun.\n"
                f"• Dasturchilar, botlar va avtomatizatsiya uchun tayyor kalit.\n\n"
                f"💵 <b>Narxi:</b> <code>{price_uzs:,} so'm</code> ($0.8)\n"
                f"📦 <b>Zaxirada mavjud:</b> <code>{cur_stock} ta</code>\n"
                f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
            )
            
        buttons = []
        if cur_stock > 0:
            buttons.append([InlineKeyboardButton(f"🛒 Sotib olish ({price_uzs:,} so'm)", callback_data=f"mkt_buy_{service}")])
        else:
            buttons.append([InlineKeyboardButton("⚠️ Hozircha zaxirada tugagan", callback_data="mkt_stock_empty")])
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")])
        
        await cb.message.edit_text(desc, reply_markup=InlineKeyboardMarkup(buttons))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_stock_empty$"))
    async def cb_mkt_stock_empty(client, cb: CallbackQuery):
        await cb.answer("Ushbu mahsulot hozirda zaxirada qolmagan. Tez orada administrator tomonidan qo'shiladi!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^mkt_buy_(openrouter|gemini|groq)$"))
    async def cb_mkt_buy_key(client, cb: CallbackQuery):
        service = cb.matches[0].group(1).lower()
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        prices = {"openrouter": 38000, "gemini": 64000, "groq": 10000}
        names = {"openrouter": "OpenRouter API ($3)", "gemini": "Google Gemini API ($5)", "groq": "Groq Cloud API (10k)"}
        price_uzs = prices.get(service, 10000)
        service_name = names.get(service, service)
        
        if bal < price_uzs:
            diff = price_uzs - bal
            text = (
                f"{e('WARN')} <b>Balansingizda mablag' yetarli emas!</b>\n\n"
                f"Xarid uchun: <code>{price_uzs:,} so'm</code>\n"
                f"Joriy balansingiz: <code>{bal:,} so'm</code>\n"
                f"Yetishmayotgan summa: <code>{diff:,} so'm</code>\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 TON orqali to'ldirish", callback_data="pay_ton_menu")],
                [InlineKeyboardButton("🪙 CryptoPay orqali to'ldirish", callback_data="pay_crypto_menu")],
                [InlineKeyboardButton("⭐ Stars orqali to'ldirish", callback_data="pay_stars_menu")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"mkt_view_{service}")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
            await cb.answer()
            return
            
        confirm_text = (
            f"🛒 <b>Xaridni tasdiqlash</b>\n\n"
            f"Mahsulot: <b>{service_name}</b>\n"
            f"Narxi: <code>{price_uzs:,} so'm</code>\n"
            f"Joriy balansingiz: <code>{bal:,} so'm</code>\n"
            f"Xariddan so'ng qoladi: <code>{(bal - price_uzs):,} so'm</code>\n\n"
            f"Hisobingizdan mablag' yechilib, kalit darhol ko'rsatiladi. Tasdiqlaysizmi?"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ha, xarid qilaman", callback_data=f"mkt_confirm_key_{service}")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"mkt_view_{service}")]
        ])
        await cb.message.edit_text(confirm_text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_key_(openrouter|gemini|groq)$"))
    async def cb_mkt_confirm_key(client, cb: CallbackQuery):
        service = cb.matches[0].group(1).lower()
        user_id = cb.from_user.id
        
        res = purchase_api_key(user_id, service)
        if not res.get("ok"):
            err = res.get("error", "Xatolik yuz berdi")
            await cb.answer(f"Xatolik: {err}", show_alert=True)
            return
            
        names = {"openrouter": "OpenRouter API ($3)", "gemini": "Google Gemini API ($5)", "groq": "Groq Cloud API"}
        service_name = names.get(service, service)
        api_key = res.get("api_key", "")
        new_bal = res.get("new_balance", 0)
        
        text = (
            f"🎉 <b>Xaridingiz muvaffaqiyatli amalga oshirildi!</b>\n\n"
            f"🤖 <b>Mahsulot:</b> {service_name}\n"
            f"💰 <b>To'langan summa:</b> {res.get('price_uzs', 0):,} so'm\n"
            f"⚖️ <b>Qolgan balansingiz:</b> {new_bal:,} so'm\n\n"
            f"🔑 <b>Sizning shaxsiy API kalitingiz:</b>\n"
            f"<code>{api_key}</code>\n\n"
            f"<i>💡 Nusxalash uchun kalit ustiga bir marta bosing! Ushbu kalit profilingizda ham saqlanib qoladi.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Mening xaridlarim", callback_data="mkt_my_purchases")],
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer("Xarid muvaffaqiyatli yakunlandi!", show_alert=False)

    # ==================== DEDICATED PRIVATE PROXY ($3 / 38,000 so'm) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_proxy$"))
    async def cb_mkt_view_proxy(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        pr_stock = get_proxies_stock_count()
        user_proxy = get_user_download_proxy(user_id)
        price_uzs = 38000

        status_line = f"🟢 <b>Faol shaxsiy proxiyingiz:</b> <code>{user_proxy}</code>" if user_proxy else "⚪ Sizda hali shaxsiy proxy ulanmagan"

        desc = (
            f"{e('PROXY')} <b>Dedicated Private Proxy (Shaxsiy Toza IP)</b>\n\n"
            f"• <b>Faqat video yuklab olishda (download):</b> YouTube tezlikni cheklamasligi va bloklamasligi uchun.\n"
            f"• <b>Qat'iy xavfsizlik:</b> Ushbu proxy yuklab olish tugagach ajratiladi va oddiy bot/API so'rovlarida sarflanmaydi.\n"
            f"• <b>1 xarid = 1 toza proxy:</b> Faqat sizning akkauntingizga biriktiriladi.\n\n"
            f"{status_line}\n\n"
            f"💵 <b>Narxi:</b> $3 — <code>{price_uzs:,} so'm</code>\n"
            f"📦 <b>Zaxirada mavjud:</b> <code>{pr_stock} ta</code>\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        buttons = []
        if pr_stock > 0:
            buttons.append([InlineKeyboardButton(f"🛒 Sotib olish ({price_uzs:,} so'm)", callback_data="mkt_buy_proxy")])
        else:
            buttons.append([InlineKeyboardButton("⚠️ Zaxirada hozircha qolmagan", callback_data="mkt_stock_empty")])
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")])
        await cb.message.edit_text(desc, reply_markup=InlineKeyboardMarkup(buttons))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_buy_proxy$"))
    async def cb_mkt_buy_proxy(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        price_uzs = 38000
        if bal < price_uzs:
            diff = price_uzs - bal
            text = (
                f"{e('WARN')} <b>Balansingizda mablag' yetarli emas!</b>\n\n"
                f"Kerak: <code>{price_uzs:,} so'm</code>, mavjud: <code>{bal:,} so'm</code> (yetishmayapti: <code>{diff:,} so'm</code>)\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🪙 CryptoPay orqali to'ldirish", callback_data="pay_crypto_menu")],
                [InlineKeyboardButton("⭐ Stars orqali to'ldirish", callback_data="pay_stars_menu")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="mkt_view_proxy")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
            await cb.answer()
            return

        confirm_text = (
            f"🛒 <b>Xaridni tasdiqlash</b>\n\n"
            f"Mahsulot: <b>Dedicated Private Proxy (Dedicated IP)</b>\n"
            f"Narxi: <code>{price_uzs:,} so'm</code>\n"
            f"Joriy balans: <code>{bal:,} so'm</code>\n"
            f"Qoladi: <code>{(bal - price_uzs):,} so'm</code>\n\n"
            f"Tasdiqlaysizmi?"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ha, xarid qilaman", callback_data="mkt_confirm_proxy")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_view_proxy")]
        ])
        await cb.message.edit_text(confirm_text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_proxy$"))
    async def cb_mkt_confirm_proxy(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        res = purchase_proxy(user_id)
        if not res.get("ok"):
            await cb.answer(f"Xatolik: {res.get('error', 'Xarid qilib bo`lmadi')}", show_alert=True)
            return

        proxy_url = res.get("proxy_url", "")
        new_bal = res.get("new_balance", 0)
        text = (
            f"🎉 <b>Dedicated Proxy muvaffaqiyatli biriktirildi!</b>\n\n"
            f"🌐 <b>Proxy manzili:</b> <code>{proxy_url}</code>\n"
            f"💰 <b>Yechilgan summa:</b> 38,000 so'm ($3)\n"
            f"⚖️ <b>Qolgan balans:</b> {new_bal:,} so'm\n\n"
            f"✅ <i>Ushbu proxy faqat va faqat /dl orqali video yuklab olayotganingizda ishlatiladi.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Mening xaridlarim", callback_data="mkt_my_purchases")],
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer("Proxy muvaffaqiyatli biriktirildi!", show_alert=False)

    # ==================== 24/7 AUTOSTREAM CLOUD SLOTS ($0.5 / SOAT) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_autostream$"))
    async def cb_mkt_view_autostream(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        active_slots = get_user_autostream_slots(user_id)

        slot_lines = ""
        if active_slots:
            slot_lines = "\n\n<b>Sizning slotlaringiz:</b>\n"
            for s in active_slots:
                st = "🟢 Jonli efirda" if s.get("is_running") else "⚪ Tugagan"
                slot_lines += f"• #{s['id']} — {s['hours_paid']} soat [{st}] (tugash: {str(s['expires_at'])[:16]})\n"

        desc = (
            f"{e('STREAM')} <b>24/7 Autostream Bulutli Efir Serveri</b>\n\n"
            f"• Telefon yoki kompyuteringizni yoqib o'tirmasdan YouTube kanalingizda 24/7 jonli efir uzating!\n"
            f"• Soatbay to'lov: <b>soatiga 4,000 so'm ($0.3)</b>.\n"
            f"• <b>Avtomatik o'chish:</b> Sotib olingan vaqt tugashi bilan efir serveri avtomatik to'xtaydi.{slot_lines}\n\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"Efir davomiyligini tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 soat — 4,000 so'm", callback_data="mkt_stream_h_1"),
             InlineKeyboardButton("3 soat — 12,000 so'm", callback_data="mkt_stream_h_3")],
            [InlineKeyboardButton("6 soat — 24,000 so'm", callback_data="mkt_stream_h_6"),
             InlineKeyboardButton("12 soat — 48,000 so'm", callback_data="mkt_stream_h_12")],
            [InlineKeyboardButton("24 soat (1 kun) — 96,000 so'm", callback_data="mkt_stream_h_24")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_stream_h_(\d+)$"))
    async def cb_mkt_stream_h(client, cb: CallbackQuery):
        hours = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        cost = hours * 4000

        if bal < cost:
            diff = cost - bal
            text = (
                f"{e('WARN')} <b>Balansingizda mablag' yetarli emas!</b>\n\n"
                f"{hours} soatlik slot uchun: <code>{cost:,} so'm</code>\n"
                f"Joriy balansingiz: <code>{bal:,} so'm</code> (yetishmayapti: <code>{diff:,} so'm</code>)\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🪙 CryptoPay orqali to'ldirish", callback_data="pay_crypto_menu")],
                [InlineKeyboardButton("⭐ Stars orqali to'ldirish", callback_data="pay_stars_menu")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="mkt_view_autostream")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
            await cb.answer()
            return

        confirm_text = (
            f"🛒 <b>Autostream slotini tasdiqlash</b>\n\n"
            f"Davomiyligi: <b>{hours} soat</b>\n"
            f"Narxi: <code>{cost:,} so'm</code> (${hours*0.5})\n"
            f"Joriy balansingiz: <code>{bal:,} so'm</code>\n"
            f"Xariddan so'ng: <code>{(bal - cost):,} so'm</code>\n\n"
            f"⚠️ Vaqt tugashi bilan efir serveri avtomatik o'chadi. Tasdiqlaysizmi?"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ha, sotib olaman", callback_data=f"mkt_confirm_stream_{hours}")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_view_autostream")]
        ])
        await cb.message.edit_text(confirm_text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_stream_(\d+)$"))
    async def cb_mkt_confirm_stream(client, cb: CallbackQuery):
        hours = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        res = purchase_autostream_slot(user_id, hours)
        if not res.get("ok"):
            await cb.answer(f"Xatolik: {res.get('error')}", show_alert=True)
            return

        exp_time = res.get("expires_at", "")
        new_bal = res.get("new_balance", 0)
        text = (
            f"🎉 <b>Autostream Cloud Sloti faollashtirildi!</b>\n\n"
            f"⏱ <b>Faol vaqt:</b> {hours} soat\n"
            f"📅 <b>Efir to'xtash vaqti:</b> <code>{exp_time}</code>\n"
            f"💰 <b>Yechilgan summa:</b> {res.get('total_cost'):,} so'm\n"
            f"⚖️ <b>Qolgan balans:</b> {new_bal:,} so'm\n\n"
            f"🚀 <b>Efirni boshlash uchun:</b>\n"
            f"1. <code>/setstreamkey &lt;Stream_Key&gt;</code> (YouTube studio kalitini kiriting)\n"
            f"2. <code>/autostream start &lt;mavzu yoki video&gt;</code> buyrug'ini yuboring."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Mening xaridlarim", callback_data="mkt_my_purchases")],
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer("Autostream muvaffaqiyatli ochildi!", show_alert=False)

    # ==================== 500+ VIRAL PROMPT & SEO TAGS PACK ($3) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_prompts$"))
    async def cb_mkt_view_prompts(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        price_uzs = 38000
        desc = (
            f"{e('IDEA')} <b>500+ Virusli Prompt & SEO Taglar To'plami</b>\n\n"
            f"• <b>Millionlab ko'rish to'plagan formulalar:</b> Shorts va videolar uchun clickbait sarlavha shablonlari.\n"
            f"• <b>Retention sirlari:</b> Tomoshabinni dastlabki 5 soniyada ushlab qoluvchi 50+ Hook skriptlari.\n"
            f"• <b>Yuqori reytingli SEO teglari:</b> Har bir soha bo'yicha eng kuchli kalit so'zlar to'plami.\n\n"
            f"💵 <b>Narxi:</b> $3 — <code>{price_uzs:,} so'm</code>\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"Xariddan so'ng to'liq to'plam darhol chatda ochiladi va profilingizda saqlanadi."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🛒 Xarid qilish ({price_uzs:,} so'm)", callback_data="mkt_confirm_prompts")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_prompts$"))
    async def cb_mkt_confirm_prompts(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        price_uzs = 38000
        if bal < price_uzs:
            await cb.answer("Balansingizda mablag' yetarli emas!", show_alert=True)
            return

        res = record_user_purchase(user_id, "prompt_pack", "500+ Viral Prompts & SEO Tags", price_uzs)
        if not res.get("ok"):
            await cb.answer(f"Xatolik: {res.get('error')}", show_alert=True)
            return

        prompts_text = (
            f"🎉 <b>500+ Virusli Prompt & SEO Taglar To'plami ochildi!</b>\n\n"
            f"🔥 <b>Top 5 Viral Clickbait Qoliplari:</b>\n"
            f"1. <i>«Nega hamma [Mavzu] haqida xato o'ylaydi? (Haqiqat oshkor bo'ldi)»</i>\n"
            f"2. <i>«Men [Raqam] kun davomida faqat [Amal] qildim va mana nima yuz berdi...»</i>\n"
            f"3. <i>«99% odam bilmaydigan [Mavzu] sirli usuli»</i>\n"
            f"4. <i>«Bu xatoni qilmang: [Mavzu] siz bilishingiz shart bo'lgan qoida!»</i>\n"
            f"5. <i>«[Yil] da [Mavzu] bilan qanday qilib 0 dan natijaga erishish mumkin?»</i>\n\n"
            f"⚡ <b>Shorts Retention Hooks (Birinchi 3 soniya):</b>\n"
            f"• <i>«Videoni o'tkazib yubormang, chunki bu sizning [Mavzu]ingizni o'zgartiradi...»</i>\n"
            f"• <i>«Agar siz ham shunday qilayotgan bo'lsangiz, zudlik bilan to'xtating!»</i>\n"
            f"• <i>«Oxirigacha ko'ring, natijasi sizni hayratda qoldiradi!»</i>\n\n"
            f"🏷️ <b>High-Rank SEO Teglar:</b>\n"
            f"<code>youtube growth, viral shorts, video montaj, trends, maslahatlar, sirlar, darslik, qiziqarli</code>\n\n"
            f"💡 <i>Ushbu to'plam profilingizda doimiy saqlanib qoladi.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Mening xaridlarim", callback_data="mkt_my_purchases")],
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(prompts_text, reply_markup=kb)
        await cb.answer("Muvaffaqiyatli xarid qilindi!", show_alert=False)

    # ==================== VIP CHEKSIZ PRO OBUNA ($15 / OY) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_vip$"))
    async def cb_mkt_view_vip(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        is_vip = is_user_vip(user_id)
        price_uzs = 192000
        vip_status = "👑 <b>Siz hozirda faol VIP a'zosiz!</b>" if is_vip else "⚪ Sizda hali VIP obuna mavjud emas"

        desc = (
            f"👑 <b>VIP Cheksiz Pro Obuna ($15 / oy)</b>\n\n"
            f"• <b>Cheksiz Kunlik Limit:</b> Kunlik buyruqlar, video yuklash (/dl) va tahlillar cheklovi butunlay bekor qilinadi.\n"
            f"• <b>Prioritetli Navbat:</b> Avtopost va video render jarayonlarida eng yuqori server tezligi.\n"
            f"• <b>Eksklyuziv Imkoniyatlar:</b> Kelajakdagi barcha yangi AI modellariga birinchi navbatda kirish.\n\n"
            f"{vip_status}\n\n"
            f"💵 <b>Narxi:</b> $15 — <code>{price_uzs:,} so'm</code> (30 kun)\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"👑 VIP Obuna Bo'lish ({price_uzs:,} so'm)", callback_data="mkt_confirm_vip")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_vip$"))
    async def cb_mkt_confirm_vip(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        res = purchase_vip_subscription(user_id)
        if not res.get("ok"):
            await cb.answer(f"Xatolik: {res.get('error')}", show_alert=True)
            return

        exp = res.get("expires_at", "")
        new_bal = res.get("new_balance", 0)
        text = (
            f"👑 <b>Tabriklaymiz, siz VIP Pro a'zosisiz!</b>\n\n"
            f"📅 <b>Muddati:</b> <code>{exp}</code> gacha\n"
            f"💰 <b>Yechilgan summa:</b> 192,000 so'm ($15)\n"
            f"⚖️ <b>Qolgan balans:</b> {new_bal:,} so'm\n\n"
            f"🚀 Barcha kunlik cheklovlar bekor qilindi. Bemalol cheksiz foydalaning!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer("VIP Pro faollashtirildi!", show_alert=False)

    # ==================== FLUX.1 AI RASM OBUNASI ($2 / HAFTA) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_flux$"))
    async def cb_mkt_view_flux(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        quota = get_flux_quota(user_id)
        price_uzs = 25000

        q_status = f"🎨 <b>Mavjud rasm krediti:</b> {quota['left']} ta (tugash: {quota.get('expires_at')})" if quota["active"] else "⚪ Sizda faol rasm obunasi yo'q"

        desc = (
            f"{e('FLUX')} <b>Flux.1 AI Rasm Generatsiya Obunasi</b>\n\n"
            f"• Midjourney va DALL-E 3 darajasidagi eng fotorealistik AI rasm modeli.\n"
            f"• YouTube muqova (thumbnail) va kreativ rasmlar uchun maxsus sozlangan.\n"
            f"• <b>Tarif:</b> Haftasiga 25 ta rasm generatsiya qilish krediti.\n\n"
            f"{q_status}\n\n"
            f"💵 <b>Narxi:</b> $2 — <code>{price_uzs:,} so'm</code> (7 kunlik obuna)\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"<i>Xariddan so'ng botda /flux &lt;tavsif&gt; buyrug'i orqali rasm yarata olasiz.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎨 Obuna bo'lish ({price_uzs:,} so'm)", callback_data="mkt_confirm_flux")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_confirm_flux$"))
    async def cb_mkt_confirm_flux(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        res = purchase_flux_subscription(user_id)
        if not res.get("ok"):
            await cb.answer(f"Xatolik: {res.get('error')}", show_alert=True)
            return

        exp = res.get("expires_at", "")
        new_bal = res.get("new_balance", 0)
        text = (
            f"🎨 <b>Flux.1 AI Rasm obunasi faollashtirildi!</b>\n\n"
            f"🖼 <b>Generatsiyalar soni:</b> 25 ta rasm\n"
            f"📅 <b>Amal qilish muddati:</b> <code>{exp}</code> gacha\n"
            f"💰 <b>Yechilgan summa:</b> 25,000 so'm ($2)\n"
            f"⚖️ <b>Qolgan balans:</b> {new_bal:,} so'm\n\n"
            f"🚀 <b>Rasm yaratish uchun:</b>\n"
            f"<code>/flux &lt;rasm tavsifi&gt;</code> deb yuboring!\n"
            f"<i>(Masalan: /flux cyberpunk uslubidagi YouTube thumbnail)</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Mening xaridlarim", callback_data="mkt_my_purchases")],
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer("Flux.1 obunasi ochildi!", show_alert=False)

    # ==================== YOUTUBE DEEPLINK & SMART QR (3,000 SO'M) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_deeplink$"))
    async def cb_mkt_view_deeplink(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        price_uzs = 3000
        desc = (
            f"{e('QR_DEEPLINK')} <b>YouTube DeepLink & Smart QR Kod</b>\n\n"
            f"• <b>Ilovada to'g'ridan-to'g'ri ochilish:</b> Instagram bio, TikTok yoki reklamadan bosgan odam brauzerda emas, to'g'ridan-to'g'ri YouTube mobil ilovasida ochadi.\n"
            f"• <b>Konversiya o'sishi:</b> Brauzerda login so'ramaydi, 1 bosishda layk va obuna bo'lishadi!\n"
            f"• <b>Stilistik Smart QR:</b> Chop etish yoki postlar uchun tayyor QR kod birga taqdim etiladi.\n\n"
            f"💵 <b>Narxi:</b> <code>{price_uzs:,} so'm</code>\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📲 Yaratish ({price_uzs:,} so'm)", callback_data="mkt_order_deeplink")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_order_deeplink$"))
    async def cb_mkt_order_deeplink(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        if bal < 3000:
            await cb.answer("Balansingiz yetarli emas (kerak: 3,000 so'm)", show_alert=True)
            return
        USER_ORDER_STATE[user_id] = {"action": "deeplink", "step": "awaiting_deeplink_url"}
        text = (
            f"{e('QR_DEEPLINK')} <b>YouTube kanal yoki video havolasini chatga yuboring:</b>\n\n"
            f"<i>Masalan: https://youtube.com/@KanalNomi yoki https://youtu.be/xxx</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_cancel")]])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    # ==================== VIDEO UNIKALIZATSIYA (1,500 SO'M) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_unikal$"))
    async def cb_mkt_view_unikal(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        price_uzs = 1500
        desc = (
            f"{e('LIGHTNING')} <b>Video Unikalizatsiya & Content ID Tozalash</b>\n\n"
            f"• <b>Algoritmik himoya:</b> Metadata tozalash, 1% tezlik o'zgartirish, mikro audio-pitch siljitish va rang filtri (LUT).\n"
            f"• Qayta yuklangan videolarning bloklanish xavfini keskin kamaytiradi.\n\n"
            f"⚠️ <b>DIQQAT (Ogohlantirish):</b>\n"
            f"YouTube Content ID va mualliflik huquqi algoritmlari doimiy yangilanib turadi. "
            f"Ushbu xizmat videoni unikalizatsiya qilish ehtimolini oshiradi, biroq 100% kafolat bermaydi. "
            f"<b>Qaytarib berilmaydi (NO REFUNDS)!</b>\n\n"
            f"💵 <b>Narxi:</b> <code>{price_uzs:,} so'm</code> / video\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚡ Unikalizatsiya Qilish ({price_uzs:,} so'm)", callback_data="mkt_order_unikal")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_order_unikal$"))
    async def cb_mkt_order_unikal(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        if bal < 1500:
            await cb.answer("Balansingiz yetarli emas (kerak: 1,500 so'm)", show_alert=True)
            return
        USER_ORDER_STATE[user_id] = {"action": "unikal", "step": "awaiting_unikal_video"}
        text = (
            f"{e('LIGHTNING')} <b>Unikalizatsiya qilinadigan video havolasini chatga yuboring:</b>\n\n"
            f"<i>(Masalan: https://youtu.be/xxx yoki video fayl)</i>\n\n"
            f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_cancel")]])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    # ==================== 3 TA SHORTS KESISH ($1 / 12,800 SO'M) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_clipper$"))
    async def cb_mkt_view_clipper(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        price_uzs = 12800
        desc = (
            f"{e('CLIPPER')} <b>Uzun Videodan Avtomatik 3 ta Shorts Kesish</b>\n\n"
            f"• Podkast, intervyu yoki uzun videongizdan sun'iy intellekt eng qiziqarli 3 ta vertikal Shorts tayyorlaydi.\n"
            f"• Har bir qism uchun alohida qiziqarli sarlavha va virusli hook aniqlanadi.\n\n"
            f"⚠️ <b>DIQQAT (Ogohlantirish):</b>\n"
            f"AI algoritmlari videoning eng faol joylarini avtomatik tahlil qilib kesadi. "
            f"Kadrlash, markazlashtirish yoki video sifati ba'zi videolarda kutilgandek chiqmasligi mumkin. "
            f"<b>Qaytarib berilmaydi (NO REFUNDS)!</b>\n\n"
            f"💵 <b>Narxi:</b> $1 — <code>{price_uzs:,} so'm</code> / video\n"
            f"💰 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✂️ Shorts Kesish ({price_uzs:,} so'm)", callback_data="mkt_order_clipper")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_order_clipper$"))
    async def cb_mkt_order_clipper(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        bal = get_user_balance(user_id)
        if bal < 12800:
            await cb.answer("Balansingiz yetarli emas (kerak: 12,800 so'm)", show_alert=True)
            return
        USER_ORDER_STATE[user_id] = {"action": "clipper", "step": "awaiting_clipper_url"}
        text = (
            f"{e('CLIPPER')} <b>Uzun video havolasini chatga yuboring:</b>\n\n"
            f"<i>(Masalan: https://youtube.com/watch?v=xxx)</i>\n\n"
            f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="mkt_cancel")]])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    # ==================== REFERAL & KESHBEK TIZIMI (10%) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_view_ref$"))
    async def cb_mkt_view_ref(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        stats = get_referral_stats(user_id)
        bot_info = await client.get_me()
        bot_uname = bot_info.username or "Bot"
        ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"

        desc = (
            f"💎 <b>Shaxsiy Referal & 10% Keshbek Tizimi</b>\n\n"
            f"Do'stlaringizni botga taklif qiling va ularning <b>har bir to'lovidan 10% keshbek</b> oling!\n\n"
            f"🔗 <b>Sizning shaxsiy havolangiz:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"👥 <b>Taklif qilingan do'stlar:</b> <code>{stats['invited_count']} ta</code>\n"
            f"💰 <b>Jami ishlangan keshbek:</b> <code>{stats['total_earned']:,} so'm</code>\n\n"
            f"<i>💡 Keshbek to'g'ridan-to'g'ri botdagi balansingizga qo'shiladi va istalgan xaridlar uchun ishlatilishi mumkin.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Do'stlarga ulashish", url=f"https://t.me/share/url?url={ref_link}&text=YouTube%20Analytics%20va%20Avtomatizatsiya%20boti!")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_marketplace")]
        ])
        await cb.message.edit_text(desc, reply_markup=kb)
        await cb.answer()

    # ==================== MENING XARIDLARIM (KEYS, PROXIES, SUBS) ====================
    @bot.on_callback_query(filters.regex(r"^mkt_my_purchases$"))
    async def cb_mkt_my_purchases(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        keys = get_user_purchased_keys(user_id)
        proxy = get_user_download_proxy(user_id)
        is_vip = is_user_vip(user_id)
        flux_q = get_flux_quota(user_id)
        purchases = get_user_purchases(user_id)

        lines = [f"🔑 <b>Mening Xaridlarim & Xizmatlarim:</b>\n"]

        # VIP status
        if is_vip:
            lines.append("👑 <b>VIP Pro Obuna:</b> ✅ FAOL (Cheksiz)")
        else:
            lines.append("👑 <b>VIP Pro Obuna:</b> ⚪ Faol emas")

        # Proxy
        if proxy:
            lines.append(f"🌐 <b>Dedicated Download Proxy:</b> <code>{proxy}</code>")

        # Flux
        if flux_q["active"]:
            lines.append(f"🎨 <b>Flux.1 Rasm Krediti:</b> {flux_q['left']} ta rasm (tugash: {flux_q.get('expires_at')})")

        # Keys
        if keys:
            lines.append("\n<b>Sotib olingan API Kalitlar:</b>")
            for k in keys:
                st = k['service_type'].upper()
                lines.append(f"• {st}: <code>{k['api_key']}</code>")

        # Other purchases
        if purchases:
            lines.append("\n<b>Boshqa Xaridlar:</b>")
            for p in purchases[:5]:
                p_date = str(p.get("created_at", ""))[:16].replace("T", " ")
                lines.append(f"• {p['item_name']} — {p['price_uzs']:,} so'm ({p_date})")

        text = "\n".join(lines)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mkt_my_keys$"))
    async def cb_mkt_my_keys(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        keys = get_user_purchased_keys(user_id)
        if not keys:
            text = f"{e('INFO')} Sizda hali xarid qilingan API kalitlar mavjud emas."
        else:
            lines = [f"{e('KEY')} <b>Sotib olgan API kalitlaringiz:</b>\n"]
            for idx, k in enumerate(keys, 1):
                st_names = {"openrouter": "OpenRouter", "gemini": "Google Gemini", "groq": "Groq Cloud"}
                st_name = st_names.get(k["service_type"], k["service_type"])
                sold_date = str(k.get("sold_at", ""))[:16].replace("T", " ")
                lines.append(f"{idx}. <b>{st_name} (${k['price_usd']})</b>")
                lines.append(f"   🔑 <code>{k['api_key']}</code>")
                lines.append(f"   📅 Xarid: <i>{sold_date}</i>\n")
            lines.append("<i>Kalitlarni nusxalash uchun ustiga bir marta bosing.</i>")
            text = "\n".join(lines)
            
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Do'konga qaytish", callback_data="menu_marketplace")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^insta_dl_([a-f0-9]+)$"))
    async def cb_insta_dl(client, cb: CallbackQuery):
        cache_id = cb.matches[0].group(1)
        data = INSTA_CACHE.get(cache_id)
        if not data or not os.path.exists(data.get("video_path", "")):
            await cb.answer("Video fayli topilmadi yoki muddati tugagan.", show_alert=True)
            return
        await cb.answer("Video yuborilmoqda...")
        user_id = cb.from_user.id
        lang = get_user_language(user_id)
        me = await client.get_me()
        bot_user = me.username or "AutoReplyBot"
        promo = t("dl_promo_caption", lang, bot_user=bot_user)
        await client.send_video(
            cb.message.chat.id,
            video=data["video_path"],
            caption=f"{e('CHECK')} <b>Instagram Reels</b>\n\n{data.get('title', '')}{promo}"
        )

    @bot.on_callback_query(filters.regex(r"^insta_pub_([a-f0-9]+)$"))
    async def cb_insta_pub(client, cb: CallbackQuery):
        cache_id = cb.matches[0].group(1)
        data = INSTA_CACHE.get(cache_id)
        if not data or not os.path.exists(data.get("video_path", "")):
            await cb.answer("Video fayli topilmadi!", show_alert=True)
            return
        user_id = cb.from_user.id
        from database import get_default_account, get_all_yt_connections
        def_acc = get_default_account(user_id)
        if not def_acc:
            conns = get_all_yt_connections(user_id)
            def_acc = conns[0] if conns else None
        if not def_acc:
            await cb.answer("YouTube kanalingiz ulanmagan! Avval /ytlogin qiling.", show_alert=True)
            return
            
        await cb.message.edit_text(f"{e('WAIT')} <b>Shorts YouTube-ga yuklanmoqda...</b>")
        try:
            res_id = await asyncio.to_thread(
                upload_to_youtube,
                data["video_path"],
                data["title"][:90] + " #Shorts",
                data.get("description", "") + "\n\nUploaded via YouTube Automation Bot",
                def_acc
            )
            if res_id:
                yt_link = f"https://youtube.com/shorts/{res_id}"
                await cb.message.edit_text(
                    f"{e('SUCCESS')} <b>Video muvaffaqiyatli YouTube Shorts-ga joylandi!</b>\n\n"
                    f"📺 <b>Havola:</b> <a href=\"{yt_link}\">{yt_link}</a>",
                    reply_markup=main_menu_kb(user_id)
                )
            else:
                await cb.message.edit_text(f"{e('ERROR')} YouTube ga yuklashda xatolik yuz berdi.", reply_markup=main_menu_kb(user_id))
        except Exception as pub_err:
            await cb.message.edit_text(f"{e('ERROR')} Xatolik: {pub_err}", reply_markup=main_menu_kb(user_id))
    
    # Channel menu callbacks
    @bot.on_callback_query(filters.regex("^ch_"))
    async def cb_channel_menu(client, cb: CallbackQuery):
        action = cb.data.replace("ch_", "")
        hints = {
            "full": "To'liq statistika olish uchun:\n`/channel <kanal nomi yoki URL>`",
            "subs": "Obunachilar soni:\n`/subs <kanal>`",
            "recent": "So'nggi videolar:\n`/recent <kanal>`",
            "popular": "Eng ommabop videolar:\n`/popular <kanal>`",
            "playlists": "Pleylistlar:\n`/playlists <kanal>`",
            "about": "Kanal haqida:\n`/about <kanal>`",
            "banner": "Banner rasmi:\n`/banner <kanal>`",
            "keywords": "Kalit so'zlar:\n`/keywords <kanal>`",
            "frequency": "Upload chastotasi:\n`/uploadfreq <kanal>`",
            "earnings": "Daromad taxmini:\n`/earnings <kanal>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_channel")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Video menu callbacks
    @bot.on_callback_query(filters.regex("^vid_"))
    async def cb_video_menu(client, cb: CallbackQuery):
        action = cb.data.replace("vid_", "")
        hints = {
            "full": "To'liq statistika:\n`/video <URL>`",
            "likes": "Video likelari:\n`/video <URL>`",
            "comments": "Izohlar:\n`/comments <URL>`",
            "tags": "Teglar:\n`/tags <URL>`",
            "thumb": "Thumbnail:\n`/thumbnail <URL>`",
            "desc": "Tavsif:\n`/desc <URL>`",
            "engage": "Engagement:\n`/video <URL>`",
            "duration": "Davomiyligi:\n`/video <URL>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_video")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Analytics menu callbacks
    @bot.on_callback_query(filters.regex("^an_"))
    async def cb_analytics_menu(client, cb: CallbackQuery):
        action = cb.data.replace("an_", "")
        hints = {
            "growth": "O'sish tahlili:\n`/growth <kanal>`",
            "compare": "Solishtirish:\n`/compare <kanal1> <kanal2>`",
            "engage": "Engagement:\n`/engagement <kanal>`",
            "avgviews": "O'rtacha ko'rishlar:\n`/avgviews <kanal>`",
            "top": "Top videolar:\n`/topvideos <kanal>`",
            "bottom": "Eng kam ko'rilgan:\n`/topvideos <kanal>`",
            "earnings": "Daromad taxmini:\n`/earnings <kanal>`",
            "milestone": "Milestone:\n`/milestone <kanal>`",
            "report": "To'liq hisobot:\n`/report <kanal>`",
            "uploadrate": "Upload tezligi:\n`/uploadfreq <kanal>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_analytics")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Search callbacks
    @bot.on_callback_query(filters.regex("^sr_"))
    async def cb_search_menu(client, cb: CallbackQuery):
        action = cb.data.replace("sr_", "")
        hints = {
            "video": "Video qidirish:\n`/search <so'z>`",
            "channel": "Kanal qidirish:\n`/searchch <nom>`",
            "playlist": "Pleylist:\n`/playlist <URL yoki ID>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_search")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Tracking callbacks
    @bot.on_callback_query(filters.regex("^tr_"))
    async def cb_tracking_menu(client, cb: CallbackQuery):
        action = cb.data.replace("tr_", "")
        hints = {
            "add": "Kanal qo'shish:\n`/track <kanal>`",
            "remove": "Kanal o'chirish:\n`/untrack <kanal>`",
            "list": "Ro'yxat:\n`/mylist`",
            "checkall": "Barchasini tekshirish:\n`/checkall`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_tracking")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Tools callbacks
    @bot.on_callback_query(filters.regex("^tl_"))
    async def cb_tools_menu(client, cb: CallbackQuery):
        action = cb.data.replace("tl_", "")
        hints = {
            "id": "URL dan ID:\n`/id <URL>`",
            "thumb": "Thumbnail olish:\n`/thumbnail <URL>`",
            "compare": "Solishtirish:\n`/compare <kanal1> <kanal2>`",
            "calc": "Kalkulyator - ko'rishlar bo'yicha daromad:\n`/earnings <kanal>`",
            "categories": "Kategoriyalar:\n`/categories [davlat_kodi]`",
            "region": "Davlat trending:\n`/trending [davlat_kodi]`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_tools")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Trending region callbacks
    @bot.on_callback_query(filters.regex("^trend_"))
    async def cb_trending(client, cb: CallbackQuery):
        region = cb.data.replace("trend_", "")
        await cb.answer(f"Trending {region} yuklanmoqda...")
        videos = get_trending(region, max_results=10)
        if not videos:
            await cb.message.edit_text(f"Trending ({region}) topilmadi.", reply_markup=trending_menu_kb())
            return
        text = f"**Trending - {region}**\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            text += f"**{i}.** {v['snippet']['title'][:40]}\n"
            text += f"   {v['snippet'].get('channelTitle','')} | `{fmt(views)}`\n\n"
        await cb.message.edit_text(text, reply_markup=trending_menu_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # Help category callbacks
    @bot.on_callback_query(filters.regex("^help_"))
    async def cb_help(client, cb: CallbackQuery):
        cat = cb.data.replace("help_", "")
        helps = {
            "channel": (
                "**Kanal buyruqlari:**\n\n"
                "`/channel` - To'liq statistika\n"
                "`/subs` - Obunachilar\n"
                "`/totalviews` - Umumiy ko'rishlar\n"
                "`/videocount` - Videolar soni\n"
                "`/about` - Kanal haqida\n"
                "`/country` - Davlat\n"
                "`/created` - Yaratilgan sana\n"
                "`/keywords` - Kalit so'zlar\n"
                "`/banner` - Banner rasmi\n"
                "`/avatar` - Profil rasmi\n"
                "`/playlists` - Pleylistlar"
            ),
            "video": (
                "**Video buyruqlari:**\n\n"
                "`/video` - To'liq statistika\n"
                "`/comments` - Izohlar\n"
                "`/tags` - Teglar\n"
                "`/thumbnail` - Thumbnail\n"
                "`/desc` - Tavsif\n"
                "`/playlist` - Pleylist videolari"
            ),
            "analytics": (
                "**Analitika buyruqlari:**\n\n"
                "`/growth` - O'sish tahlili\n"
                "`/engagement` - Engagement rate\n"
                "`/earnings` - Daromad taxmini\n"
                "`/milestone` - Milestone\n"
                "`/report` - To'liq hisobot\n"
                "`/compare` - Solishtirish\n"
                "`/topvideos` - Top videolar\n"
                "`/avgviews` - O'rtacha ko'rishlar\n"
                "`/uploadfreq` - Upload chastotasi"
            ),
            "search": (
                "**Qidiruv buyruqlari:**\n\n"
                "`/search` - Video qidirish\n"
                "`/searchch` - Kanal qidirish\n"
                "`/trending` - Trending videolar\n"
                "`/categories` - Kategoriyalar"
            ),
            "tracking": (
                "**Kuzatuv buyruqlari:**\n\n"
                "`/track` - Kanalni kuzatishga olish\n"
                "`/untrack` - Kuzatishdan olish\n"
                "`/mylist` - Kuzatuvdagi kanallar\n"
                "`/checkall` - Barchasini tekshirish"
            ),
            "tools": (
                "**Asboblar:**\n\n"
                "`/id` - URL dan ID ajratish\n"
                "`/thumbnail` - Thumbnail olish\n"
                "`/compare` - Kanallarni solishtirish\n"
                "`/categories` - Kategoriyalar\n"
                "`/rivals` - Raqobatchilarni topish\n"
                "`/sponsor <kanal>` - Homiylik narxini hisoblash\n"
                "`/live <kanal>` - Jonli efirni tekshirish\n"
                "`/schedule <kanal>` - Yuklash jadvalini tahlili\n"
                "`/money <video url>` - Video daromadi tahlili\n"
                "`/summarize <video URL>` - Videoni qisqacha mazmuni\n"
                "`/ping` - Bot tezligini tekshirish"
            ),
            "ai": (
                "**🧠 AI Yordamchi:**\n\n"
                "`/seo <mavzu>` - SEO optimizatsiya\n"
                "`/tagsgen <mavzu>` - Mavzu bo'yicha teglar yaratish\n"
                "`/clickbait <mavzu>` - Clickbait sarlavhalar\n"
                "`/thumbidea <mavzu>` - Thumbnail g'oyalar\n"
                "`/reply <izoh>` - Izohga aqlli javob qaytarish\n"
                "`/script <mavzu>` - Ssenariy yozish\n"
                "`/ideas <mavzu>` - Video g'oyalar yaratish\n"
                "`/shorts <video URL>` - Shorts g'oyalarini olish\n"
                "`/translate <video URL>` - Sarlavhani tarjima qilish\n"
                "`/roast <kanal>` - Kanalni AI tanqidi (roast)\n"
                "`/audit <kanal URL>` - Kanalni AI tahlili"
            ),
            "download": (
                "**⬇️ Yuklab olish:**\n\n"
                "`/dl <URL>` - Video yoki Audio yuklab olish (Tez kunda)"
            ),
        }
        text = helps.get(cat, "Yordam topilmadi")
        await cb.message.edit_text(text, reply_markup=help_menu_kb(), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Channel action callbacks (kanal sahifasidagi tugmalar)
    @bot.on_callback_query(filters.regex("^cact_"))
    async def cb_channel_action(client, cb: CallbackQuery):
        parts = cb.data.split("_", 2)
        if len(parts) < 3:
            await cb.answer("Xato")
            return
        action = parts[1]
        channel_id = parts[2]
        
        await cb.answer(f"Yuklanmoqda...")
        
        if action == "recent":
            videos = get_videos_by_channel(channel_id, max_results=10, order="date")
            if not videos:
                await cb.message.edit_text("Videolar topilmadi.", reply_markup=back_main_kb())
                return
            ch = get_channel({"type": "id", "value": channel_id})
            title = ch["snippet"]["title"] if ch else channel_id
            text = f"**{title}** - So'nggi videolar\n\n{'='*28}\n\n"
            for i, v in enumerate(videos, 1):
                vs = v["statistics"]
                views = int(vs.get("viewCount", 0))
                ago = time_ago(v["snippet"].get("publishedAt", ""))
                text += f"**{i}.** {v['snippet']['title'][:45]}\n"
                text += f"   `{fmt(views)}` ko'rish | {ago}\n\n"
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "popular":
            videos = get_videos_by_channel(channel_id, max_results=10, order="viewCount")
            if not videos:
                await cb.message.edit_text("Videolar topilmadi.", reply_markup=back_main_kb())
                return
            ch = get_channel({"type": "id", "value": channel_id})
            title = ch["snippet"]["title"] if ch else channel_id
            text = f"**{title}** - Ommabop\n\n{'='*28}\n\n"
            for i, v in enumerate(videos, 1):
                vs = v["statistics"]
                views = int(vs.get("viewCount", 0))
                text += f"**{i}.** {v['snippet']['title'][:45]}\n   `{fmt(views)}`\n\n"
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "playlists":
            pls = get_playlists(channel_id, max_results=10)
            if not pls:
                await cb.message.edit_text("Pleylistlar topilmadi.", reply_markup=back_main_kb())
                return
            text = "**Pleylistlar**\n\n"
            for i, p in enumerate(pls, 1):
                count = p.get("contentDetails", {}).get("itemCount", 0)
                text += f"**{i}.** {p['snippet']['title'][:40]} (`{count}` video)\n\n"
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "growth":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            st = ch["statistics"]
            subs = int(st.get("subscriberCount",0))
            views = int(st.get("viewCount",0))
            vids = int(st.get("videoCount",0))
            save_channel_snapshot(channel_id, subs, views, vids)
            g = get_channel_growth(channel_id)
            text = f"**{ch['snippet']['title']}** - O'sish\n\n"
            text += f"Obunachilar: `{fmt(subs)}`\nKo'rishlar: `{fmt(views)}`\n\n"
            if g:
                text += f"Sub o'sish: {growth_icon(g['sub_growth'])}\n"
                text += f"View o'sish: {growth_icon(g['view_growth'])}\n"
            else:
                text += "O'sish ma'lumotlari hali yetarli emas."
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "report":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            sn, st = ch["snippet"], ch["statistics"]
            subs = int(st.get("subscriberCount",0))
            views = int(st.get("viewCount",0))
            vids = int(st.get("videoCount",0))
            avg = views//vids if vids else 0
            low, high = estimate_earnings(views)
            text = (
                f"**{sn['title']}** - HISOBOT\n\n{'='*28}\n\n"
                f"Obunachilar: `{fmt_full(subs)}`\n"
                f"Ko'rishlar: `{fmt_full(views)}`\n"
                f"Videolar: `{fmt_full(vids)}`\n"
                f"O'rtacha/video: `{fmt(avg)}`\n"
                f"Daromad: `${low:,.0f}` - `${high:,.0f}`"
            )
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "earn":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            views = int(ch["statistics"].get("viewCount", 0))
            low, high = estimate_earnings(views)
            text = (
                f"**{ch['snippet']['title']}** - Daromad\n\n"
                f"Umumiy: `${low:,.0f}` - `${high:,.0f}`\n"
                f"CPM: $0.50 - $5.00"
            )
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "track":
            add_tracked_channel(cb.from_user.id, channel_id, "")
            ch = get_channel({"type": "id", "value": channel_id})
            if ch:
                st = ch["statistics"]
                save_channel_snapshot(channel_id, int(st.get("subscriberCount",0)), int(st.get("viewCount",0)), int(st.get("videoCount",0)))
                add_tracked_channel(cb.from_user.id, channel_id, ch["snippet"]["title"])
            await cb.message.edit_text("Kanal kuzatishga qo'shildi!", reply_markup=channel_action_kb(channel_id))
        
        elif action == "refresh":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            sn, st = ch["snippet"], ch["statistics"]
            subs = int(st.get("subscriberCount",0))
            views = int(st.get("viewCount",0))
            vids = int(st.get("videoCount",0))
            avg = views//vids if vids else 0
            save_channel_snapshot(channel_id, subs, views, vids)
            text = (
                f"**{sn['title']}** (yangilandi)\n\n{'='*28}\n\n"
                f"Obunachilar: `{fmt(subs)}` ({fmt_full(subs)})\n"
                f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
                f"Videolar: `{fmt(vids)}`\n"
                f"O'rtacha: `{fmt(avg)}`"
            )
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
    
    # Video action callbacks
    @bot.on_callback_query(filters.regex("^vact_"))
    async def cb_video_action(client, cb: CallbackQuery):
        parts = cb.data.split("_", 2)
        if len(parts) < 3:
            await cb.answer("Xato")
            return
        action = parts[1]
        video_id = parts[2]
        
        await cb.answer("Yuklanmoqda...")
        
        if action == "comments":
            comments = get_comments(video_id, max_results=10)
            if not comments:
                await cb.message.edit_text("Izohlar topilmadi.", reply_markup=video_action_kb(video_id))
                return
            text = "**Top izohlar**\n\n"
            for i, c in enumerate(comments, 1):
                sn = c["snippet"]["topLevelComment"]["snippet"]
                author = sn.get("authorDisplayName","")[:20]
                txt = sn.get("textDisplay","")[:80]
                likes = int(sn.get("likeCount",0))
                text += f"**{i}. {author}** ({fmt(likes)} like)\n{txt}\n\n"
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "tags":
            v = get_video(video_id)
            if not v:
                await cb.message.edit_text("Video topilmadi.", reply_markup=back_main_kb())
                return
            tags = v["snippet"].get("tags", [])
            text = f"**Teglar** ({len(tags)} ta)\n\n"
            text += " | ".join([f"`{t}`" for t in tags[:30]]) if tags else "Teglar topilmadi"
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "thumb":
            url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            await cb.message.reply_photo(url, caption=f"Thumbnail: `{video_id}`", parse_mode=ParseMode.MARKDOWN)
            await cb.answer()
        
        elif action == "engage":
            v = get_video(video_id)
            if not v:
                await cb.message.edit_text("Video topilmadi.", reply_markup=back_main_kb())
                return
            st = v["statistics"]
            views = int(st.get("viewCount",0))
            likes = int(st.get("likeCount",0))
            comments_count = int(st.get("commentCount",0))
            eng = engagement_rate(views, likes, comments_count)
            lr = (likes/views*100) if views else 0
            text = (
                f"**{v['snippet']['title'][:40]}** - Engagement\n\n"
                f"Engagement: `{eng:.2f}%`\n"
                f"Like rate: `{lr:.2f}%`\n"
                f"Ko'rishlar: `{fmt(views)}`\n"
                f"Likelar: `{fmt(likes)}`\n"
                f"Izohlar: `{fmt(comments_count)}`"
            )
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "refresh":
            v = get_video(video_id)
            if not v:
                await cb.message.edit_text("Video topilmadi.", reply_markup=back_main_kb())
                return
            sn, st = v["snippet"], v["statistics"]
            views = int(st.get("viewCount",0))
            likes = int(st.get("likeCount",0))
            comments_count = int(st.get("commentCount",0))
            eng = engagement_rate(views, likes, comments_count)
            text = (
                f"**{sn['title']}** (yangilandi)\n\n{'='*28}\n\n"
                f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
                f"Likelar: `{fmt(likes)}`\n"
                f"Izohlar: `{fmt(comments_count)}`\n"
                f"Engagement: `{eng:.2f}%`"
            )
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /testformats ====================
    @bot.on_message(filters.command("testformats") & filters.private)
    async def cmd_test_formats(client, message):
        """Render serverda mavjud formatlarni tekshirish — /testformats [video_id]"""
        from config import ADMIN_USERNAME
        
        # Only admin can run this (diagnostic command)
        if not check_is_admin(message.from_user):
            await message.reply("❌ Bu buyruq faqat bot egasi uchun.")
            return
        
        args = message.text.split()
        video_id = args[1] if len(args) > 1 else "dQw4w9WgXcQ"
        
        msg = await message.reply(f"🔍 `{video_id}` uchun formatlar tekshirilmoqda...\n_(Render logs ga ham yoziladi)_")
        
        try:
            from autopost import test_available_formats
            results = await asyncio.to_thread(test_available_formats, video_id)
            
            lines = [f"📊 **Format Test Natijalari** (`{video_id}`):\n"]
            for client_name, data in results.items():
                if 'error' in data:
                    lines.append(f"❌ `{client_name}` → {data['error'][:60]}")
                else:
                    emoji = "✅" if data['http_only'] > 0 else "⚠️"
                    lines.append(
                        f"{emoji} `{client_name}` → "
                        f"jami: {data['total']} | "
                        f"HTTP: {data['http_only']} | "
                        f"max: {data['best']}p"
                    )
            
            lines.append("\n_To'liq natija Render logs da ko'rinadi_")
            await msg.edit_text("\n".join(lines))
        
        except Exception as e:
            await msg.edit_text(f"❌ Test xatosi: `{str(e)[:200]}`")


    # ==================== /dl (MOVED TO SUPER FEATURES) ====================
    # (Removed mock cmd_dl here so super_features.py can handle it)

    # ==================== /seo ====================
    @bot.on_message(filters.command("seo") & filters.private)
    async def cmd_seo(client, message):
        """AI yordamida SEO (Sarlavha, Ta'rif, Taglar) — /seo <mavzu>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Mavzu kiritilmadi!**\nMasalan: `/seo Python darslari`")
            return
            
        topic = args[1].strip()
        wait_msg = await message.reply("🤖 AI o'ylamoqda...")
        
        try:
            import google.generativeai as genai
            
            prompt = (
                f"Siz professional YouTube SEO mutaxassisisiz. Qisqa va lo'nda javob bering.\n"
                f"Mavzu: '{topic}'\n"
                f"Shu mavzuda YouTube video uchun quyidagilarni o'zbek tilida yozib bering:\n"
                f"1. 3 ta jozibador sarlavha varianti.\n"
                f"2. Qisqa va qiziqarli video tavsifi (description).\n"
                f"3. 15-20 ta qidiruvbop taglar (vergul bilan ajratilgan)."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text.replace('**', '') if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"📊 **SEO Natijasi:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /ideas ====================
    @bot.on_message(filters.command("ideas") & filters.private)
    async def cmd_ideas(client, message):
        """Video g'oyalar yaratish — /ideas <mavzu>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Mavzu kiritilmadi!**\nMasalan: `/ideas Dasturlash`")
            return
            
        topic = args[1].strip()
        wait_msg = await message.reply("🤖 AI g'oyalar o'ylamoqda...")
        
        try:
            import google.generativeai as genai
            
            prompt = (
                f"Mavzu: '{topic}'.\n"
                f"Shu mavzu bo'yicha YouTube'da ko'p ko'riladigan, qiziqarli va kreativ 5 ta aniq video g'oyasini o'zbek tilida qisqa yozib bering."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text.replace('**', '') if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"💡 **Video G'oyalar:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /translate ====================
    @bot.on_message(filters.command("translate") & filters.private)
    async def cmd_translate(client, message):
        """Video sarlavhasini tarjima qilish — /translate <video URL yoki ID>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **URL kiritilmadi!**\nMasalan: `/translate <URL>`")
            return
            
        video_id = extract_video_id(args[1])
        if not video_id:
            await message.reply("❌ Yaroqsiz YouTube URL yoki ID.")
            return
            
        wait_msg = await message.reply("🔄 Video ma'lumotlari olinmoqda va tarjima qilinmoqda...")
        
        try:
            video = get_video_stats(video_id)
            if not video:
                await wait_msg.edit_text("❌ Video topilmadi.")
                return
                
            title = video['snippet']['title']
            desc = video['snippet'].get('description', '')[:500]
            
            import google.generativeai as genai
            
            prompt = (
                f"Quyidagi YouTube video sarlavhasi va ta'rifini o'zbek tiliga professional tarjima qilib ber.\n\n"
                f"Sarlavha: {title}\n"
                f"Ta'rif: {desc}"
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"🇺🇿 **Tarjima:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /script ====================
    @bot.on_message(filters.command("script") & filters.private)
    async def cmd_script(client, message):
        """Video uchun ssenariy yozish — /script <mavzu>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Mavzu kiritilmadi!**\nMasalan: `/script 5 daqiqada blinchik tayyorlash`")
            return
            
        topic = args[1].strip()
        wait_msg = await message.reply("🤖 AI ssenariy yozmoqda, biroz kuting...")
        
        try:
            import google.generativeai as genai
            
            prompt = (
                f"Mavzu: '{topic}'.\n"
                f"YouTube video uchun qisqa va qiziqarli ssenariy yozib ber (O'zbek tilida). "
                f"Ssenariy qismlari: Kirish (Hook), Asosiy qism va Xulosa (Call to action). "
                f"Juda uzun bo'lmasin, taxminan 3 daqiqalik video uchun."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"📝 **Video Ssenariysi:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /shorts ====================
    @bot.on_message(filters.command("shorts") & filters.private)
    async def cmd_shorts(client, message):
        """Videodan shorts g'oyalarini olish — /shorts <video URL yoki ID>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **URL kiritilmadi!**\nMasalan: `/shorts <URL>`")
            return
            
        video_id = extract_video_id(args[1])
        if not video_id:
            await message.reply("❌ Yaroqsiz YouTube URL yoki ID.")
            return
            
        wait_msg = await message.reply("🔄 Video ma'lumotlari tahlil qilinmoqda...")
        
        try:
            video = get_video_stats(video_id)
            if not video:
                await wait_msg.edit_text("❌ Video topilmadi.")
                return
                
            title = video['snippet']['title']
            desc = video['snippet'].get('description', '')[:1000]
            
            import google.generativeai as genai
            
            prompt = (
                f"Quyidagi YouTube video (Sarlavha: {title}, Ta'rif: {desc}) asosida "
                f"1 daqiqalik 2-3 ta qiziqarli Shorts videolari uchun g'oyalar va matnlar (skriptlar) "
                f"yozib bering (O'zbek tilida)."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"📱 **Shorts G'oyalar:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /audit ====================
    @bot.on_message(filters.command("audit") & filters.private)
    async def cmd_audit(client, message):
        """Kanalni AI tahlili — /audit <kanal URL>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Kanal kiritilmadi!**\nMasalan: `/audit @PewDiePie`")
            return
            
        query = args[1].strip()
        wait_msg = await message.reply("🔍 Kanal qidirilmoqda...")
        
        try:
            ch_data = get_channel(extract_channel_id(query))
            if not ch_data:
                await wait_msg.edit_text("❌ Kanal topilmadi.")
                return
                
            stats = ch_data["statistics"]
            subs = int(stats.get("subscriberCount", 0))
            views = int(stats.get("viewCount", 0))
            vids = int(stats.get("videoCount", 0))
            title = ch_data["snippet"]["title"]
            desc = ch_data["snippet"].get("description", "")[:500]
            
            await wait_msg.edit_text("🤖 AI kanal ma'lumotlarini o'rganmoqda...")
            
            import google.generativeai as genai
            
            prompt = (
                f"Sen professional YouTube audit mutaxassisisan.\n"
                f"Kanal: {title}\n"
                f"Obunachilar: {subs}, Ko'rishlar: {views}, Videolar: {vids}\n"
                f"Ta'rif: {desc}\n\n"
                f"Shu ma'lumotlar asosida ushbu kanalga o'zbek tilida qisqa baho va rivojlanish uchun 3 ta maslahat ber."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"📈 **Kanal Auditi: {title}**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /rivals ====================
    @bot.on_message(filters.command("rivals") & filters.private)
    async def cmd_rivals(client, message):
        """Raqobatchi kanallarni topish — /rivals <kanal URL yoki ID>"""
        if not can_use_bot(message.from_user): return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Kanal kiritilmadi!**\nMasalan: `/rivals @PewDiePie`")
            return
            
        query = args[1].strip()
        wait_msg = await message.reply("🔍 Kanal qidirilmoqda...")
        
        try:
            ch_data = get_channel(extract_channel_id(query))
            if not ch_data:
                await wait_msg.edit_text("❌ Kanal topilmadi.")
                return
                
            channel_id = ch_data['id']
            title = ch_data['snippet']['title']
            
            await wait_msg.edit_text("🔍 Raqobatchilar izlanmoqda...")
            
            from googleapiclient.discovery import build
            key = get_youtube_key()
            yt = build('youtube', 'v3', developerKey=key, cache_discovery=False)
            
            req = yt.search().list(
                q=title,
                type="channel",
                part="snippet",
                maxResults=6
            )
            res = await asyncio.to_thread(req.execute)
            
            items = res.get('items', [])
            rivals = []
            for item in items:
                ch_title = item['snippet']['title']
                ch_id = item['snippet']['channelId']
                if ch_id != channel_id:
                    rivals.append(f"🔗 [{ch_title}](https://youtube.com/channel/{ch_id})")
                    
            if rivals:
                text = f"🤺 **{title}** uchun ehtimoliy raqobatchi yoki o'xshash kanallar:\n\n" + "\n".join(rivals)
            else:
                text = "❌ Raqobatchi kanallar topilmadi."
                
            await wait_msg.edit_text(text, disable_web_page_preview=True)
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")


        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")


    # ==================== /roast ====================
    @bot.on_message(filters.command("roast") & filters.private)
    async def cmd_roast(client, message):
        """Kanalni AI yordamida hazilomuz tanqid qilish (roast) — /roast <kanal>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Kanal kiritilmadi!**\nMasalan: `/roast @MrBeast`")
            return
            
        query = args[1].strip()
        wait_msg = await message.reply("🔍 Kanal qidirilmoqda...")
        
        try:
            ch_data = get_channel(extract_channel_id(query))
            if not ch_data:
                await wait_msg.edit_text("❌ Kanal topilmadi.")
                return
                
            stats = ch_data["statistics"]
            subs = int(stats.get("subscriberCount", 0))
            views = int(stats.get("viewCount", 0))
            vids = int(stats.get("videoCount", 0))
            title = ch_data["snippet"]["title"]
            desc = ch_data["snippet"].get("description", "")[:500]
            
            await wait_msg.edit_text("🔥 AI kanalni qovurmoqda (roasting)...")
            
            import google.generativeai as genai
            from config import get_gemini_key
            import asyncio
            
            prompt = (
                f"Sen qattiqqo'l, lekin kulgili YouTube tanqidchisisan (roaster). "
                f"Quyidagi kanalni o'zbek tilida hazilomuz, biroz sarkazm bilan qattiq tanqid qil (roast). Lekin haqorat qilma, faqat statistika va ta'rif ustidan kul. "
                f"Kanal nomi: {title}\n"
                f"Obunachilar: {subs}, Ko'rishlar: {views}, Videolar: {vids}\n"
                f"Ta'rif: {desc}"
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"🔥 **{title} ROAST:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /sponsor ====================
    @bot.on_message(filters.command("sponsor") & filters.private)
    async def cmd_sponsor(client, message):
        """Kanal uchun homiylik (sponsorship) narxini hisoblash — /sponsor <kanal>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Kanal kiritilmadi!**\nMasalan: `/sponsor @MrBeast`")
            return
            
        wait_msg = await message.reply("🔍 Kanal tahlil qilinmoqda...")
        try:
            ch = get_channel(extract_channel_id(args[1]))
            if not ch:
                await wait_msg.edit_text("❌ Kanal topilmadi.")
                return
                
            videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
            if not videos:
                await wait_msg.edit_text("❌ Videolar topilmadi.")
                return
                
            views_list = [int(v["statistics"].get("viewCount",0)) for v in videos]
            avg_views = sum(views_list) // len(views_list) if views_list else 0
            
            low_cost = (avg_views / 1000) * 15
            high_cost = (avg_views / 1000) * 30
            
            title = ch['snippet']['title']
            
            text = (
                f"🤝 **{title} - Homiylik narxi (Sponsorship)**\n\n"
                f"📊 **O'rtacha ko'rishlar (oxirgi 10 video):** `{fmt_full(avg_views)}`\n\n"
                f"💰 **Tavsiya etilgan homiylik narxi (1 ta video uchun):**\n"
                f"💵 `${low_cost:,.0f}` - `${high_cost:,.0f}`\n\n"
                f"_(Hisob-kitob homiylik bozori standartlariga (CPM $15-$30) asoslangan. "
                f"Aniq narx kanal nishasi va auditoriyasiga qarab o'zgarishi mumkin)._"
            )
            await wait_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /tagsgen ====================
    @bot.on_message(filters.command("tagsgen") & filters.private)
    async def cmd_tagsgen(client, message):
        """Mavzu bo'yicha eng yaxshi teglarni yaratish — /tagsgen <mavzu>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Mavzu kiritilmadi!**\nMasalan: `/tagsgen Minecraft`")
            return
            
        topic = args[1].strip()
        wait_msg = await message.reply("🤖 AI teglar yaratmoqda...")
        
        try:
            import google.generativeai as genai
            from config import get_gemini_key
            import asyncio
            
            prompt = (
                f"Siz YouTube SEO mutaxassisisiz. '{topic}' mavzusidagi video uchun eng ko'p qidiriladigan, "
                f"trenddagi 30 ta teglarni (tags) vergul bilan ajratilgan holda o'zbek, rus va ingliz tillarida yozib bering. Faqat teglarni qaytaring."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"🏷 **'{topic}' uchun teglar:**\n\n`{res_text[:4000]}`")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /thumbidea ====================
    @bot.on_message(filters.command("thumbidea") & filters.private)
    async def cmd_thumbidea(client, message):
        """Video uchun thumbnail g'oyasini olish — /thumbidea <mavzu>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Mavzu kiritilmadi!**\nMasalan: `/thumbidea Vlog`")
            return
            
        topic = args[1].strip()
        wait_msg = await message.reply("🤖 AI thumbnail dizaynini o'ylamoqda...")
        
        try:
            import google.generativeai as genai
            from config import get_gemini_key
            import asyncio
            
            prompt = (
                f"Siz professional YouTube dizaynerisiz. '{topic}' mavzusidagi video uchun CTR ni "
                f"maksimal darajaga ko'taradigan 2 xil Thumbnail (video muqovasi) g'oyasini tasvirlab bering. "
                f"Rasmning fonida nima bo'lishi kerak, qanday matn bo'lishi kerakligini o'zbek tilida yozing."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"🖼 **Thumbnail G'oyalari:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /reply ====================
    @bot.on_message(filters.command("reply") & filters.private)
    async def cmd_reply(client, message):
        """Izohga aqlli javob qaytarish — /reply <izoh matni>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Izoh kiritilmadi!**\nMasalan: `/reply Zo'r video!`")
            return
            
        comment = args[1].strip()
        wait_msg = await message.reply("🤖 AI javob tayyorlamoqda...")
        
        try:
            import google.generativeai as genai
            from config import get_gemini_key
            import asyncio
            
            prompt = (
                f"Siz mashhur YouTube ijodkorisiz. Videongizga kelgan izoh: '{comment}'. "
                f"Unga chiroyli va qiziqarli (minnatdorchilik, hazil) javob yozing. O'zbek tilida."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"💬 **Izoh:** {comment}\n\n🤖 **AI Javobi:**\n`{res_text[:4000]}`")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /clickbait ====================
    @bot.on_message(filters.command("clickbait") & filters.private)
    async def cmd_clickbait(client, message):
        """Mavzu bo'yicha jozibador sarlavhalar — /clickbait <mavzu>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Mavzu kiritilmadi!**\nMasalan: `/clickbait Uyda pul ishlash`")
            return
            
        topic = args[1].strip()
        wait_msg = await message.reply("🤖 AI sarlavhalar o'ylamoqda...")
        
        try:
            import google.generativeai as genai
            from config import get_gemini_key
            import asyncio
            
            prompt = (
                f"'{topic}' mavzusida YouTube uchun 5 ta juda jozibador, odamlarni bosishga majbur qiladigan "
                f"(clickbait, lekin aldamchi bo'lmagan) sarlavha variantlarini o'zbek tilida yozib ber."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"🎣 **Clickbait Sarlavhalar:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /summarize ====================
    @bot.on_message(filters.command("summarize") & filters.private)
    async def cmd_summarize(client, message):
        """Videoni AI yordamida qisqacha mazmunini chiqarish — /summarize <video URL>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **URL kiritilmadi!**\nMasalan: `/summarize <URL>`")
            return
            
        video_id = extract_video_id(args[1])
        if not video_id:
            await message.reply("❌ Yaroqsiz YouTube URL yoki ID.")
            return
            
        wait_msg = await message.reply("🔄 Video ma'lumotlari tahlil qilinmoqda...")
        
        try:
            v = get_video(video_id)
            if not v:
                await wait_msg.edit_text("❌ Video topilmadi.")
                return
                
            title = v['snippet']['title']
            desc = v['snippet'].get('description', '')[:2500]
            
            import google.generativeai as genai
            from config import get_gemini_key
            import asyncio
            
            prompt = (
                f"Siz professional yordamchisiz. Quyidagi YouTube video haqida ma'lumot asosida uning qisqacha mazmunini (xulosasini) o'zbek tilida yozib bering.\n\n"
                f"Sarlavha: {title}\n"
                f"Ta'rif: {desc}\n\n"
                f"Iltimos, asosiy g'oyalarni ajratib, o'qishli qilib yozing."
            )
            
            response = await generate_with_fallback_async(prompt)
            res_text = response.text if response.text else "Natija topilmadi."
            await wait_msg.edit_text(f"📝 **Video Xulosasi:**\n\n{res_text[:4000]}")
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /live ====================
    @bot.on_message(filters.command("live") & filters.private)
    async def cmd_live(client, message):
        """Kanalda jonli efir borligini tekshirish — /live <kanal>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Kanal kiritilmadi!**\nMasalan: `/live @PewDiePie`")
            return
            
        query = args[1].strip()
        wait_msg = await message.reply("🔍 Kanal qidirilmoqda...")
        
        try:
            ch_data = get_channel(extract_channel_id(query))
            if not ch_data:
                await wait_msg.edit_text("❌ Kanal topilmadi.")
                return
                
            channel_id = ch_data['id']
            title = ch_data['snippet']['title']
            
            await wait_msg.edit_text(f"🔍 {title} da jonli efirlar izlanmoqda...")
            
            yt = get_yt()
            if not yt:
                await wait_msg.edit_text("❌ YouTube API xatosi.")
                return
                
            import asyncio
            req = yt.search().list(
                channelId=channel_id,
                eventType="live",
                type="video",
                part="snippet",
                maxResults=5
            )
            res = await asyncio.to_thread(req.execute)
            
            items = res.get('items', [])
            if not items:
                await wait_msg.edit_text(f"🔴 **{title}** da ayni vaqtda jonli efir yo'q.")
                return
                
            text = f"🟢 **{title}** dagi joriy jonli efirlar:\n\n"
            for item in items:
                v_title = item['snippet']['title']
                v_id = item['id']['videoId']
                text += f"▶️ [{v_title}](https://youtube.com/watch?v={v_id})\n\n"
                
            await wait_msg.edit_text(text, disable_web_page_preview=True)
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /schedule ====================
    @bot.on_message(filters.command("schedule") & filters.private)
    async def cmd_schedule(client, message):
        """Kanal video yuklash jadvalini tahlil qilish — /schedule <kanal>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **Kanal kiritilmadi!**\nMasalan: `/schedule @PewDiePie`")
            return
            
        wait_msg = await message.reply("🔍 Jadval tahlil qilinmoqda...")
        try:
            ch = get_channel(extract_channel_id(args[1]))
            if not ch:
                await wait_msg.edit_text("❌ Kanal topilmadi.")
                return
                
            videos = get_videos_by_channel(ch["id"], max_results=15, order="date")
            if not videos:
                await wait_msg.edit_text("❌ Videolar topilmadi.")
                return
                
            days = [0]*7
            hours = [0]*24
            
            from datetime import datetime
            for v in videos:
                try:
                    dt = datetime.fromisoformat(v["snippet"]["publishedAt"].replace('Z', '+00:00'))
                    days[dt.weekday()] += 1
                    hours[dt.hour] += 1
                except: pass
                
            weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
            best_day = weekdays[days.index(max(days))]
            best_hour = hours.index(max(hours))
            
            text = f"📅 **{ch['snippet']['title']}** yuklash jadvali\n_(oxirgi {len(videos)} video asosida)_\n\n"
            text += f"🔥 **Eng ko'p yuklanadigan kun:** {best_day}\n"
            text += f"⏰ **Eng faol soat (UTC):** {best_hour}:00\n\n"
            
            text += "**Hafta kunlari bo'yicha:**\n"
            for i, d in enumerate(weekdays):
                if days[i] > 0:
                    text += f"• {d}: {days[i]} ta video\n"
                    
            await wait_msg.edit_text(text)
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

    # ==================== /money ====================
    @bot.on_message(filters.command("money") & filters.private)
    async def cmd_money(client, message):
        """Video daromadini aniqroq tahlil qilish — /money <video URL>"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 **URL kiritilmadi!**\nMasalan: `/money <URL>`")
            return
            
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply("❌ Video topilmadi.")
            return
            
        wait_msg = await message.reply("🔍 Daromad tahlil qilinmoqda...")
        try:
            v = get_video(vid_id)
            if not v:
                await wait_msg.edit_text("❌ Video ma'lumotlari topilmadi.")
                return
                
            st = v["statistics"]
            sn = v["snippet"]
            views = int(st.get("viewCount",0))
            
            dur = parse_duration_seconds(v.get("contentDetails",{}).get("duration",""))
            
            base_rpm_low = 1.0
            base_rpm_high = 3.5
            
            if dur > 480: # 8 minutes
                base_rpm_low *= 1.5
                base_rpm_high *= 1.8
                
            low_earn = (views / 1000) * base_rpm_low
            high_earn = (views / 1000) * base_rpm_high
            
            text = (
                f"💸 **{sn['title'][:40]}** - Daromad\n\n"
                f"👁 **Ko'rishlar:** {fmt_full(views)}\n"
                f"⏱ **Davomiyligi:** {parse_duration(v.get('contentDetails',{}).get('duration',''))}\n\n"
                f"💰 **Taxminiy daromad:** `${low_earn:,.0f}` - `${high_earn:,.0f}`\n\n"
                f"📊 _Taxminiy RPM (har 1000 ko'rish uchun): ${base_rpm_low:.2f} - ${base_rpm_high:.2f}_\n"
                f"_(Bu ko'rsatkich video uzunligi asosida hisoblandi, >8 min videolarda qo'shimcha reklamalar bo'lishi hisobga olindi)_"
            )
            await wait_msg.edit_text(text)
            
        except Exception as e:
            await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")


    # ==================== /autopilot ====================
    @bot.on_message(filters.command("autopilot") & filters.private)
    async def cmd_autopilot(client, message):
        """Auto-pilot orqali bot har kuni (yoki 2 kunda 1) o'zi video yuklashi — /autopilot on <mavzu>"""
        args = message.text.split(maxsplit=1)
        
        if len(args) < 2:
            await message.reply(
                "🤖 **AutoPilot Yordam:**\n\n"
                "`/autopilot on <mavzular>` - Avtomatik yuklashni yoqish (masalan: `/autopilot on Minecraft, Roblox`)\n"
                "`/autopilot off` - Avtomatik yuklashni o'chirish\n"
                "`/autopilot status` - Holatni ko'rish"
            )
            return
            
        action = args[1].strip()
        user_id = message.from_user.id
        
        if action.lower() == "off":
            if stop_autopilot(user_id):
                await message.reply("🛑 AutoPilot o'chirildi.")
            else:
                await message.reply("❌ Xatolik yuz berdi.")
            return
            
        if action.lower() == "status":
            st = get_autopilot(user_id)
            if st and st['is_active']:
                await message.reply(f"✅ **AutoPilot faol!**\n\n📝 Mavzular: {st['topics']}\n⏱ Interval: Har {st['interval_days']} kunda\n🕒 Oxirgi yuklash: {st['last_run'] or 'Hali ishlamadi'}")
            else:
                await message.reply("❌ AutoPilot o'chirilgan yoki o'rnatilmagan.")
            return
            
        if action.lower().startswith("on "):
            topics = action[3:].strip()
            if not topics:
                await message.reply("📝 Mavzularni kiritishingiz kerak!")
                return
                
            from database import is_bot_admin
            interval = 1 if is_bot_admin(user_id) else 2
            
            if set_autopilot(user_id, topics, interval):
                await message.reply(f"✅ **AutoPilot Muvaffaqiyatli Yoqildi!**\n\n📝 Mavzular: {topics}\n⏱ Interval: Har {interval} kunda\n\n_Bot belgilangan vaqtda o'zi avtomatik tarzda video qidirib kanalga yuklaydi._")
            else:
                await message.reply("❌ AutoPilot ni saqlashda xatolik yuz berdi.")
            return
            
        await message.reply("Noma'lum buyruq.")

    async def execute_engagement_order_task(order_id, user_id, action_type, target_url, qty, client, chat_id):
        """
        Ulangan YouTube akkauntlar orqali xavfsiz va random intervallar bilan
        layk, obuna yoki izoh topshiriqlarini bajaradi.
        """
        from database import get_every_yt_connection, update_engagement_order, update_yt_tokens
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build as google_build
        from google.auth.transport.requests import Request
        from config import YT_CLIENT_ID, YT_CLIENT_SECRET
        import random

        update_engagement_order(order_id, "processing")
        all_conns = get_every_yt_connection()
        if not all_conns:
            update_engagement_order(order_id, "failed")
            await client.send_message(
                chat_id,
                f"{e('ERROR')} <b>Buyurtmani bajarish uchun tizimda ulangan YouTube akkaunt topilmadi!</b>\n"
                f"Mablag' qaytarilishi yoki tekshirish uchun adminga murojaat qiling."
            )
            return

        random.shuffle(all_conns)
        selected_users = all_conns[:qty]
        target_id = extract_video_id(target_url)

        action_names = {
            "like": ("Layk", e("LIKE")),
            "subscribe": ("Obuna", e("SUBS")),
            "comment": ("Izoh", e("COMMENTS"))
        }
        name, icon = action_names.get(action_type, (action_type, "⚡"))

        await client.send_message(
            chat_id,
            f"{icon} <b>Buyurtma #{order_id} boshlandi!</b>\n\n"
            f"🎯 <b>Xizmat:</b> {name}\n"
            f"🔢 <b>Miqdor:</b> {len(selected_users)} ta\n"
            f"🛡️ <i>Amallar xavfsiz tasodifiy oraliq bilan ijro etilmoqda...</i>"
        )

        success_count = 0
        failed_count = 0

        for idx, u in enumerate(selected_users, 1):
            try:
                creds = Credentials(
                    token=u['access_token'],
                    refresh_token=u.get('refresh_token'),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=YT_CLIENT_ID,
                    client_secret=YT_CLIENT_SECRET
                )
                if creds.expired or creds.expiry is None:
                    try:
                        await asyncio.to_thread(creds.refresh, Request())
                        update_yt_tokens(u['tg_user_id'], u['yt_channel_id'], creds.token)
                    except Exception as ref_e:
                        print(f"Token refresh error: {ref_e}")

                yt_service = google_build("youtube", "v3", credentials=creds)

                if action_type == "like":
                    await asyncio.to_thread(_do_like, yt_service, target_id)
                elif action_type == "subscribe":
                    await asyncio.to_thread(_do_subscribe, yt_service, target_id)
                elif action_type == "comment":
                    video_title = "super video"
                    try:
                        res = await asyncio.to_thread(yt_service.videos().list, part="snippet", id=target_id)
                        res_data = res.execute()
                        if res_data.get("items"):
                            video_title = res_data["items"][0]["snippet"]["title"]
                    except Exception:
                        pass
                    comment_text = await generate_gemini_comment(video_title)
                    await asyncio.to_thread(_do_comment, yt_service, target_id, comment_text)

                success_count += 1
                update_engagement_order(order_id, "processing", completed_count=success_count)
            except Exception as err:
                failed_count += 1
                print(f"Order #{order_id} item failed: {err}")

            if idx < len(selected_users):
                delay = random.randint(15, 35)
                await asyncio.sleep(delay)

        final_status = "completed" if success_count > 0 else "failed"
        update_engagement_order(order_id, final_status, completed_count=success_count)

        await client.send_message(
            chat_id,
            f"{e('SUCCESS')} <b>Buyurtma #{order_id} yakunlandi!</b>\n\n"
            f"{icon} <b>Xizmat:</b> {name}\n"
            f"✅ <b>Muvaffaqiyatli:</b> {success_count}/{len(selected_users)}\n"
            f"❌ <b>Xatoliklar:</b> {failed_count}\n\n"
            f"Rahmat! Yana buyurtma berish uchun /menu ni bosing."
        )

    # ==================== TELEGRAM STARS TO'LOV HANDLERLARI ====================
    from pyrogram.raw.types import UpdateBotPrecheckoutQuery, UpdateNewMessage, MessageService, MessageActionPaymentSentMe, PeerUser

    @bot.on_raw_update()
    async def handle_raw_payment_update(client, update, users, chats):
        # 1. Stars PreCheckoutQuery
        if isinstance(update, UpdateBotPrecheckoutQuery):
            bot_token = getattr(client, "bot_token", None) or BOT_TOKEN
            url = f"https://api.telegram.org/bot{bot_token}/answerPreCheckoutQuery"
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(url, json={"pre_checkout_query_id": str(update.query_id), "ok": True}, timeout=aiohttp.ClientTimeout(total=10))
            except Exception as e:
                print(f"answerPreCheckoutQuery error: {e}")
            return

        # 2. Stars Successful Payment
        if isinstance(update, UpdateNewMessage):
            msg = update.message
            if isinstance(msg, MessageService) and isinstance(getattr(msg, "action", None), MessageActionPaymentSentMe):
                action = msg.action
                raw_payload = action.payload.decode("utf-8", errors="ignore") if isinstance(action.payload, bytes) else str(action.payload or "")
                
                user_id = None
                if hasattr(msg, "from_id") and isinstance(msg.from_id, PeerUser):
                    user_id = msg.from_id.user_id
                elif hasattr(msg, "peer_id") and isinstance(msg.peer_id, PeerUser):
                    user_id = msg.peer_id.user_id

                parts = raw_payload.split("_")
                if len(parts) >= 5 and parts[0] == "stars":
                    try:
                        tx_id = int(parts[4])
                        amount_uzs = int(parts[3])
                        charge_id = getattr(action.charge, "id", "") if hasattr(action, "charge") else ""
                        complete_payment_transaction(tx_id, invoice_id=str(charge_id))
                        if user_id:
                            new_bal = get_user_balance(user_id)
                            await client.send_message(
                                user_id,
                                f"{e('SUCCESS')} <b>To'lovingiz muvaffaqiyatli qabul qilindi!</b>\n\n"
                                f"{e('STAR')} <b>Telegram Stars:</b> {action.total_amount} ⭐\n"
                                f"{e('MONEY')} <b>Qo'shilgan summa:</b> +{amount_uzs:,} so'm\n"
                                f"{e('BALANCE')} <b>Joriy balansingiz:</b> {new_bal:,} so'm\n\n"
                                f"{e('ROCKET')} Endi layk, obuna va izoh xizmatlaridan bemalol foydalanishingiz mumkin!",
                                reply_markup=main_menu_kb(user_id)
                            )
                    except Exception as pay_err:
                        print(f"Stars payment error: {pay_err}")
                elif raw_payload.startswith("aivid_sub_"):
                    try:
                        u_id = int(raw_payload.split("_")[2])
                        from database import get_db
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            cur.execute("""
                                INSERT INTO ai_video_subscriptions (tg_user_id, expires_at, created_at)
                                VALUES (%s, NOW() + INTERVAL '30 days', NOW())
                                ON CONFLICT (tg_user_id) DO UPDATE
                                SET expires_at = GREATEST(ai_video_subscriptions.expires_at, NOW()) + INTERVAL '30 days'
                            """, (u_id,))
                            conn.commit()
                            conn.close()
                        await client.send_message(
                            u_id,
                            f"🎉 <b>AI Video Studio $20/oy obunangiz faollashdi!</b>\n\n"
                            f"Telegram Stars orqali 1,000 ⭐ to'lovingiz qabul qilindi. 30 kun davomida cheksiz AI videolar yaratishingiz mumkin!",
                            reply_markup=main_menu_kb(u_id)
                        )
                    except Exception as aivid_pay_err:
                        print(f"Stars aivid_sub error: {aivid_pay_err}")

    # ==================== VIDEO FAYL UNIKALIZATSIYA HANDLER ====================
    @bot.on_message((filters.video | filters.document) & filters.private)
    async def video_file_unikal_handler(client, message):
        user_id = message.from_user.id
        if user_id in USER_ORDER_STATE:
            st = USER_ORDER_STATE[user_id]
            if st.get("step") == "awaiting_unikal_video":
                USER_ORDER_STATE.pop(user_id, None)
                bal = get_user_balance(user_id)
                price_uzs = 1500
                if bal < price_uzs:
                    await message.reply_text(f"{e('ERROR')} <b>Balansingiz yetarli emas!</b> Kerak: <code>{price_uzs:,} so'm</code>, sizda: <code>{bal:,} so'm</code>.\n/balance orqali to'ldiring.")
                    return

                wait_msg = await message.reply_text(
                    f"{e('WAIT')} <b>Video fayli qabul qilindi. Yuklab olinmoqda va Content ID unikalizatsiya filtri qo'llanmoqda...</b>\n\n"
                    f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                )

                deduct_user_balance(user_id, price_uzs)
                record_user_purchase(user_id, "Video Unikalizatsiya & Content ID (Fayl)", price_uzs, {"file_id": getattr(message.video or message.document, "file_id", "")})

                os.makedirs("downloads", exist_ok=True)
                raw_path = f"downloads/unikal_raw_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
                clean_path = f"downloads/unikal_clean_{user_id}_{uuid.uuid4().hex[:6]}.mp4"

                try:
                    await message.download(file_name=raw_path)
                    ffmpeg_exe = get_ffmpeg_binary()
                    cmd = [
                        ffmpeg_exe, "-y", "-i", raw_path,
                        "-vf", "eq=contrast=1.03:brightness=0.01:saturation=1.04,scale='min(1080,iw)':-2",
                        "-af", "atempo=1.02,asetrate=44100*1.015,aresample=44100",
                        "-map_metadata", "-1",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-c:a", "aac", "-b:a", "128k",
                        clean_path
                    ]
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    await proc.communicate()

                    if os.path.exists(clean_path):
                        caption = (
                            f"{e('LIGHTNING')} <b>Video Faylingiz Muvaffaqiyatli Unikalizatsiya Qilindi!</b>\n\n"
                            f"🛡️ <b>Qo'llangan himoya choralari:</b>\n"
                            f"• Audio pitch shift (+1.5% va +2% tempo) — Content ID ovoz to'lqinini chetlab o'tish\n"
                            f"• Video EQ gamma, kontrast va to'yinganlik filtrlari\n"
                            f"• Barcha metadatalar butunlay olib tashlandi\n\n"
                            f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                        )
                        await message.reply_video(video=clean_path, caption=caption, supports_streaming=True)
                        await wait_msg.delete()
                    else:
                        await wait_msg.edit_text(f"{e('ERROR')} Videoni qayta ishlashda xatolik yuz berdi.")
                except Exception as file_err:
                    await wait_msg.edit_text(f"{e('ERROR')} Video faylni unikalizatsiya qilishda xatolik: {file_err}\n⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>")
                finally:
                    if os.path.exists(raw_path):
                        try: os.remove(raw_path)
                        except: pass
                    if os.path.exists(clean_path):
                        try: os.remove(clean_path)
                        except: pass
                return

    # ==================== AI ROUTER (Aqlli Yo'naltirish) ====================
    @bot.on_message(filters.text & ~filters.regex(r"^/") & filters.private)
    async def ai_routing_handler(client, message):
        user_text = message.text.strip()
        if not user_text:
            return

        user_id = message.from_user.id

        # 1. Buyurtma jarayonidagi havola tekshiruvi
        if user_id in USER_ORDER_STATE:
            st = USER_ORDER_STATE[user_id]
            if st.get("step") == "awaiting_url":
                if "youtube.com" in user_text or "youtu.be" in user_text or user_text.startswith("@") or len(user_text) >= 10:
                    st["target_url"] = user_text
                    st["step"] = "awaiting_qty"
                    action = st["action"]
                    names = {"like": "Layk", "subscribe": "Obuna", "comment": "Izoh"}
                    await message.reply_text(
                        f"{e('CHECK')} <b>Havola qabul qilindi:</b> <code>{user_text}</code>\n\n"
                        f"{e('TARGET')} Nechta {names.get(action, '')} kerak? Tanlang:",
                        reply_markup=order_quantity_kb(action)
                    )
                    return

            elif st.get("step") == "awaiting_deeplink_url":
                USER_ORDER_STATE.pop(user_id, None)
                bal = get_user_balance(user_id)
                price_uzs = 3000
                if bal < price_uzs:
                    await message.reply_text(f"{e('ERROR')} <b>Balansingiz yetarli emas!</b> Kerak: <code>{price_uzs:,} so'm</code>, sizda: <code>{bal:,} so'm</code>.\n/balance orqali to'ldiring.")
                    return
                
                target_url = user_text.strip()
                if not ("youtube.com" in target_url or "youtu.be" in target_url or target_url.startswith("@")):
                    await message.reply_text(f"{e('ERROR')} <b>Iltimos, haqiqiy YouTube havola yoki kanal nomini yuboring!</b>")
                    return
                
                deduct_user_balance(user_id, price_uzs)
                record_user_purchase(user_id, "YouTube DeepLink & Smart QR", price_uzs, {"url": target_url})
                
                intent_url = target_url
                m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", target_url)
                if m:
                    vid = m.group(1)
                    intent_url = f"vnd.youtube://www.youtube.com/watch?v={vid}"
                elif "@" in target_url:
                    ch_handle = target_url.split("@")[-1].split("/")[0].split("?")[0]
                    intent_url = f"vnd.youtube://www.youtube.com/@{ch_handle}"

                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={urllib.parse.quote(target_url)}"
                caption = (
                    f"{e('QR_DEEPLINK')} <b>YouTube DeepLink & Smart QR Kod Tayyor!</b>\n\n"
                    f"🔗 <b>Asl Havola:</b> <code>{target_url}</code>\n"
                    f"⚡ <b>Mobil App Intent (DeepLink):</b>\n<code>{intent_url}</code>\n\n"
                    f"📲 <i>Ushbu havola telefonlarda brauzerda emas, to'g'ridan-to'g'ri YouTube mobil ilovasida ochiladi va obuna bo'lish konversiyasini maksimal darajaga ko'taradi!</i>\n\n"
                    f"🖼️ <b>Smart QR Kod:</b> Postlar, bannerlar va vizitkalar uchun tayyor."
                )
                try:
                    await message.reply_photo(photo=qr_url, caption=caption)
                except Exception:
                    await message.reply_text(f"{caption}\n\n🖼️ <b>QR Kod rasm:</b> {qr_url}")
                return

            elif st.get("step") == "awaiting_unikal_video":
                USER_ORDER_STATE.pop(user_id, None)
                bal = get_user_balance(user_id)
                price_uzs = 1500
                if bal < price_uzs:
                    await message.reply_text(f"{e('ERROR')} <b>Balansingiz yetarli emas!</b> Kerak: <code>{price_uzs:,} so'm</code>, sizda: <code>{bal:,} so'm</code>.\n/balance orqali to'ldiring.")
                    return
                
                target_url = user_text.strip()
                if not ("youtube.com" in target_url or "youtu.be" in target_url or is_instagram_url(target_url)):
                    await message.reply_text(f"{e('ERROR')} <b>Iltimos, video havolasini (YouTube yoki Instagram) yuboring!</b>")
                    return
                
                wait_msg = await message.reply_text(
                    f"{e('WAIT')} <b>Video yuklab olinmoqda va Content ID unikalizatsiya filtri qo'llanmoqda...</b>\n\n"
                    f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                )
                
                deduct_user_balance(user_id, price_uzs)
                record_user_purchase(user_id, "Video Unikalizatsiya & Content ID", price_uzs, {"url": target_url})
                
                os.makedirs("downloads", exist_ok=True)
                raw_path = f"downloads/unikal_raw_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
                clean_path = f"downloads/unikal_clean_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
                
                try:
                    import yt_dlp
                    ydl_opts = {
                        "outtmpl": raw_path,
                        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
                        "merge_output_format": "mp4",
                        "quiet": True,
                        "no_warnings": True
                    }
                    def _dl():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            return ydl.extract_info(target_url, download=True)
                    info = await asyncio.to_thread(_dl)
                    if not os.path.exists(raw_path):
                        base, _ = os.path.splitext(raw_path)
                        for f in os.listdir("downloads"):
                            if f.startswith(os.path.basename(base)):
                                raw_path = os.path.join("downloads", f)
                                break
                    
                    ffmpeg_exe = get_ffmpeg_binary()
                    cmd = [
                        ffmpeg_exe, "-y", "-i", raw_path,
                        "-vf", "eq=contrast=1.03:brightness=0.01:saturation=1.04,scale='min(1080,iw)':-2",
                        "-af", "atempo=1.02,asetrate=44100*1.015,aresample=44100",
                        "-map_metadata", "-1",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-c:a", "aac", "-b:a", "128k",
                        clean_path
                    ]
                    
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.communicate()
                    
                    if os.path.exists(clean_path):
                        v_title = info.get("title", "Unikal Video") if isinstance(info, dict) else "Unikal Video"
                        caption = (
                            f"{e('LIGHTNING')} <b>Video Muvaffaqiyatli Unikalizatsiya Qilindi!</b>\n\n"
                            f"🎬 <b>Sarlavha:</b> {v_title[:70]}\n"
                            f"🛡️ <b>Qo'llangan himoya choralari:</b>\n"
                            f"• Audio pitch shift (+1.5% va +2% tempo) — Content ID ovoz to'lqinini chetlab o'tish\n"
                            f"• Video EQ gamma, kontrast va to'yinganlik filtrlari\n"
                            f"• Barcha metadatalar butunlay olib tashlandi\n\n"
                            f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                        )
                        await message.reply_video(video=clean_path, caption=caption, supports_streaming=True)
                        await wait_msg.delete()
                    else:
                        await wait_msg.edit_text(f"{e('ERROR')} Videoni qayta ishlashda xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
                except Exception as unikal_err:
                    await wait_msg.edit_text(f"{e('ERROR')} Unikalizatsiya jarayonida xatolik: {unikal_err}\n⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>")
                finally:
                    if os.path.exists(raw_path):
                        try: os.remove(raw_path)
                        except: pass
                    if os.path.exists(clean_path):
                        try: os.remove(clean_path)
                        except: pass
                return

            elif st.get("step") == "awaiting_clipper_url":
                USER_ORDER_STATE.pop(user_id, None)
                bal = get_user_balance(user_id)
                price_uzs = 12800
                if bal < price_uzs:
                    await message.reply_text(f"{e('ERROR')} <b>Balansingiz yetarli emas!</b> Kerak: <code>{price_uzs:,} so'm</code> ($1).\n/balance orqali to'ldiring.")
                    return
                
                target_url = user_text.strip()
                if not ("youtube.com" in target_url or "youtu.be" in target_url):
                    await message.reply_text(f"{e('ERROR')} <b>Iltimos, haqiqiy YouTube video havolasini yuboring!</b>")
                    return
                
                wait_msg = await message.reply_text(
                    f"{e('WAIT')} <b>Uzun video tahlil qilinmoqda va 3 ta vertikal Shorts tayyorlanmoqda...</b>\n\n"
                    f"<i>Bu 1-2 daqiqa vaqt olishi mumkin.</i>\n"
                    f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                )
                
                deduct_user_balance(user_id, price_uzs)
                record_user_purchase(user_id, "Smart Shorts Clipper (3 ta Shorts)", price_uzs, {"url": target_url})
                
                os.makedirs("downloads", exist_ok=True)
                raw_path = f"downloads/clipper_raw_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
                
                try:
                    import yt_dlp
                    ydl_opts = {
                        "outtmpl": raw_path,
                        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
                        "merge_output_format": "mp4",
                        "quiet": True,
                        "no_warnings": True
                    }
                    def _dl():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            return ydl.extract_info(target_url, download=True)
                    info = await asyncio.to_thread(_dl)
                    duration = int(info.get("duration", 180)) if isinstance(info, dict) else 180
                    title = info.get("title", "Video") if isinstance(info, dict) else "Video"
                    
                    if not os.path.exists(raw_path):
                        base, _ = os.path.splitext(raw_path)
                        for f in os.listdir("downloads"):
                            if f.startswith(os.path.basename(base)):
                                raw_path = os.path.join("downloads", f)
                                break
                    
                    # Compute 3 segments: each 25-40 seconds
                    s1_start = max(5, int(duration * 0.15))
                    s1_end = min(s1_start + 35, duration - 10)
                    
                    s2_start = max(s1_end + 10, int(duration * 0.45))
                    s2_end = min(s2_start + 40, duration - 10)
                    
                    s3_start = max(s2_end + 10, int(duration * 0.75))
                    s3_end = min(s3_start + 35, duration - 2)
                    
                    segments = [
                        {"num": 1, "start": s1_start, "end": s1_end, "hook": "Buni hech kim kutmagan edi! 🔥"},
                        {"num": 2, "start": s2_start, "end": s2_end, "hook": "Eng muhim va hayratlanarli qismi 😱"},
                        {"num": 3, "start": s3_start, "end": s3_end, "hook": "Oxirigacha ko'ring, xulosa qiling! ⚡"}
                    ]
                    
                    ffmpeg_exe = get_ffmpeg_binary()
                    for seg in segments:
                        clip_path = f"downloads/clip_{user_id}_{seg['num']}_{uuid.uuid4().hex[:4]}.mp4"
                        clip_dur = seg["end"] - seg["start"]
                        if clip_dur < 10:
                            clip_dur = 20
                        
                        cmd = [
                            ffmpeg_exe, "-y",
                            "-ss", str(seg["start"]),
                            "-i", raw_path,
                            "-t", str(clip_dur),
                            "-vf", "crop=ih*9/16:ih,scale=720:1280",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            clip_path
                        ]
                        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        await proc.communicate()
                        
                        if os.path.exists(clip_path):
                            caption = (
                                f"{e('CLIPPER')} <b>Shorts #{seg['num']} Tayyor!</b>\n\n"
                                f"🎬 <b>Mavzu:</b> {title[:50]}\n"
                                f"🎣 <b>Virusli Hook:</b> {seg['hook']}\n"
                                f"⏱ <b>Vaqti:</b> {seg['start']}s — {seg['end']}s ({clip_dur}s)\n"
                                f"📱 <b>Format:</b> 9:16 Vertikal Full HD\n"
                                f"🏷️ <i>#Shorts #YouTube #Viral</i>\n\n"
                                f"⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                            )
                            await message.reply_video(video=clip_path, caption=caption, supports_streaming=True)
                            try: os.remove(clip_path)
                            except: pass
                    
                    await wait_msg.delete()
                    await message.reply_text(
                        f"{e('SUCCESS')} <b>3 ta vertikal Shorts videongiz muvaffaqiyatli yetkazildi!</b>\n"
                        f"Kanalga yuklab trendga chiqishingiz mumkin! 🚀"
                    )
                except Exception as clip_err:
                    await wait_msg.edit_text(f"{e('ERROR')} Shorts kesishda xatolik yuz berdi: {clip_err}\n⚠️ <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>")
                finally:
                    if os.path.exists(raw_path):
                        try: os.remove(raw_path)
                        except: pass
                return

        # 2. Instagram Reels havola tekshiruvi
        if is_instagram_url(user_text):
            wait_msg = await message.reply_text(
                f"{e('WAIT')} <b>Instagram Reels yuklab olinmoqda va Content ID filtri qo'llanmoqda...</b>"
            )
            try:
                info = await download_instagram_reel(user_text)
                cid = uuid.uuid4().hex[:8]
                INSTA_CACHE[cid] = info
                caption_preview = (
                    f"{e('INSTA')} <b>Instagram Reel tayyor!</b>\n\n"
                    f"🎬 <b>Sarlavha:</b> {info['title']}\n"
                    f"⏱ <b>Davomiyligi:</b> {info['duration']} soniya\n"
                    f"🛡️ <i>Content ID filtri qo'llandi (Audio pitch + Video EQ)</i>\n\n"
                    f"Kerakli amalni tanlang:"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎬 YouTube Shorts ga joylash", callback_data=f"insta_pub_{cid}")],
                    [InlineKeyboardButton("⬇️ Videoni chatga yuklab olish", callback_data=f"insta_dl_{cid}")],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]
                ])
                await wait_msg.edit_text(caption_preview, reply_markup=kb)
                return
            except Exception as dl_err:
                await wait_msg.edit_text(f"{e('ERROR')} Instagram videoni yuklab bo'lmadi: {dl_err}")
                return
            
        try:
            prompt = f"""Foydalanuvchi Telegram botga quyidagi matnni yozdi:
"{user_text}"

Botda quyidagi buyruqlar bor:
1. /compare <kanal1> <kanal2> - ikki kanalni taqqoslash
2. /autopost <soni> <mavzu> - videolarni avto post qilish
3. /channel <kanal> - kanal statistikasini ko'rish
4. /video <url> - video statistikasini ko'rish
5. /trending - trenddagi videolarni ko'rish
6. /search <so'z> - videolar qidirish
7. /balance - hisob balansi va to'lovlar
8. /marketplace - layk, obuna, izoh buyurtma berish
9. /instagram - Instagram Reels yuklash

Vazifang: Foydalanuvchi niyatini aniqla. 
Agar foydalanuvchi kanal taqqoslashni so'rasa yoki boshqa buyruqqa mos keladigan narsa so'rasa, mos Telegram buyrug'ini aniq qaytar.
Javobingni FAQAT JSON formatida ber:
{{
    "action": "command" yoki "text",
    "result": "buyruq matni (masalan /compare ch1 ch2) YOKI foydalanuvchiga do'stona javob"
}}"""
            res = generate_with_fallback(prompt)
            if res and res.text:
                json_match = re.search(r'\{[\s\S]*\}', res.text)
                if json_match:
                    data = json.loads(json_match.group())
                    act = data.get("action")
                    val = data.get("result", "")
                    if act == "command" and val.startswith("/"):
                        await message.reply_text(f"`🎯 AI yo'naltirishi: {val}`\n\nBuyruq ijro etilmoqda...", parse_mode=ParseMode.MARKDOWN)
                        message.text = val
                        cmd_name = val.split()[0][1:]
                        if cmd_name == "compare":
                            await compare_cmd(client, message)
                        elif cmd_name == "channel":
                            await channel_cmd(client, message)
                        elif cmd_name == "video":
                            await video_cmd(client, message)
                        elif cmd_name == "search":
                            await search_cmd(client, message)
                        elif cmd_name == "trending":
                            await trending_cmd(client, message)
                        elif cmd_name == "autopost":
                            await autopost_cmd(client, message)
                        elif cmd_name in ("balance", "balans"):
                            await balance_cmd(client, message)
                        elif cmd_name in ("marketplace", "xizmatlar"):
                            await marketplace_cmd(client, message)
                        elif cmd_name == "instagram":
                            await instagram_cmd(client, message)
                        return
                    else:
                        await message.reply_text(f"`{val}`", parse_mode=ParseMode.MARKDOWN)
                        return
        except Exception as e:
            print(f"AI routing xato: {e}")
        
        await message.reply_text("`Yordam uchun /help ni bosing.`", parse_mode=ParseMode.MARKDOWN)
    from super_features import load_super_features
    load_super_features(bot)
    from mega_features import load_mega_features
    load_mega_features(bot)
    return bot


async def autostream_expiration_worker(bot: Client):
    """Har 60 soniyada faol autostream slotlarini tekshiradi va muddati tugaganlarini to'xtatadi"""
    from database import cancel_user_stream_tasks
    while True:
        try:
            active_slots = get_all_active_autostream_slots()
            now = datetime.now()
            for slot in active_slots:
                exp_str = slot.get("expires_at")
                if exp_str:
                    try:
                        exp_dt = datetime.fromisoformat(exp_str)
                    except Exception:
                        continue
                    if now >= exp_dt:
                        slot_id = slot["id"]
                        user_id = slot["user_id"]
                        expire_autostream_slot(slot_id)
                        cancel_user_stream_tasks(user_id)
                        try:
                            await bot.send_message(
                                user_id,
                                f"{e('WARN')} <b>Autostream Cloud Slotingiz Muddati Tugadi!</b>\n\n"
                                f"• Slot ID: <code>#{slot_id}</code>\n"
                                f"• Stream avtomatik to'xtatildi.\n\n"
                                f"Davom ettirish uchun /marketplace orqali yangi soat sotib olishingiz mumkin (soatiga 6,000 so'm / $0.5)."
                            )
                        except Exception as notify_err:
                            print(f"Slot #{slot_id} notification error: {notify_err}")
        except Exception as e:
            print(f"Autostream worker xato: {e}")
        await asyncio.sleep(60)


async def run_ytbot():
    bot = create_ytbot()
    if bot is None:
        print("YouTube Bot ishga tushmadi. BOT_TOKEN ni tekshiring.")
        return
    print("YouTube Analytics Bot ishga tushmoqda...")
    await bot.start()
    print("YouTube Analytics Bot muvaffaqiyatli ishga tushdi!")
    asyncio.create_task(autostream_expiration_worker(bot))
    from vouchers_engine import start_antifraud_sentinel_daemon
    from instagram_cloner import start_instagram_sync_daemon
    asyncio.create_task(start_antifraud_sentinel_daemon(bot, interval_seconds=3600))
    asyncio.create_task(start_instagram_sync_daemon(bot, interval_seconds=1800))
    await asyncio.Event().wait()