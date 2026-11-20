"""
Reseller & Developer REST API
Ushbu modul tashqi dasturchilar va resellerlar uchun REST API taqdim etadi.
Har bir foydalanuvchi o'z Telegram hisobidagi shaxsiy API kaliti (art_live_...)
orqali balansini boshqarishi, mahsulotlarni (AI kalitlar, Proxylar) sotib olishi
va YouTube xizmatlariga avtomatik buyurtma berishi mumkin.
"""

import html as _html
import json
import os
import re
import socket
import ipaddress
import urllib.parse
import asyncio
import aiohttp
from aiohttp import web
from config import APP_BASE_URL, BRAND_NAME, SUPPORT_USERNAME
from crypto_auth import generate_download_signature
from database import (
    get_user_by_api_key,
    log_api_key_usage,
    get_api_keys_stock_count,
    get_proxies_stock_count,
    purchase_api_key,
    purchase_proxy,
    create_engagement_order,
    get_db,
    set_reseller_webhook,
    get_reseller_webhook,
    redeem_promo_code,
    get_user_balance,
    deduct_user_balance,
    add_user_balance,
    save_gift_record,
    save_reseller_white_label_bot,
    get_reseller_white_label_bots,
    record_api_metered_usage
)
from games_monetization import (
    open_stars_case,
    open_stars_case_with_uzs,
    fetch_telegram_server_gifts,
    build_cases_from_gifts,
    redeem_voucher,
    create_vouchers
)
from config import generate_with_fallback_async, BOT_TOKEN
from competitor_spy import extract_competitor_metadata
from deeplink_engine import generate_smart_deeplinks


_ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
    "shorts.youtube.com",
}
_ALLOWED_DOWNLOAD_FORMATS = {"360", "480", "720", "1080", "1440", "2160", "4320", "mp3"}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_BOT_TOKEN_RE = re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{20,64}$")
_GIFT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _is_non_public_ip(ip_str: str) -> bool:
    """Return True if an IP literal is private, loopback, link-local, multicast, or reserved."""
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip("[]"))
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
    except ValueError:
        return True


def is_safe_public_webhook_url(url: str) -> bool:
    """Strict SSRF validator for user-supplied webhook URLs."""
    if not url or not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme not in ("https", "http"):
        return False
    if parsed.username or parsed.password:
        return False
    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        return False
    if hostname in ("localhost", "ip6-localhost", "ip6-loopback", "metadata.google.internal", "metadata"):
        return False
    if hostname.endswith((".local", ".internal", ".localhost", ".lan", ".home.arpa")):
        return False
    # Check if hostname is already an IP literal
    try:
        ip_obj = ipaddress.ip_address(hostname.strip("[]"))
        if _is_non_public_ip(str(ip_obj)):
            return False
        return True
    except ValueError:
        pass
    # Must contain a dot (public FQDN)
    if "." not in hostname:
        return False
    # Best-effort DNS check against private IP resolution (SSRF protection)
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        for info in infos:
            sockaddr = info[4]
            if sockaddr and _is_non_public_ip(sockaddr[0]):
                return False
    except OSError:
        # Unresolvable host in offline test environment: allow only valid public domain syntax
        if not re.match(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", hostname):
            return False
    return True


def extract_safe_youtube_target(raw_url: str):
    """Validate and normalize a YouTube URL or 11-char video ID (SSRF protection)."""
    raw = str(raw_url or "").strip()
    if not raw or len(raw) > 1024:
        return None, None
    if _VIDEO_ID_RE.match(raw):
        return raw, f"https://www.youtube.com/watch?v={raw}"
    try:
        parsed = urllib.parse.urlparse(raw)
    except Exception:
        return None, None
    if parsed.scheme not in ("http", "https"):
        return None, None
    if parsed.username or parsed.password:
        return None, None
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_YOUTUBE_HOSTS:
        return None, None
    video_id = None
    if host == "youtu.be":
        cand = parsed.path.lstrip("/").split("/")[0]
        if _VIDEO_ID_RE.match(cand):
            video_id = cand
    else:
        qs = urllib.parse.parse_qs(parsed.query)
        v_list = qs.get("v", [])
        if v_list and _VIDEO_ID_RE.match(v_list[0]):
            video_id = v_list[0]
        else:
            m = re.match(r"^/(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})(?:/|$)", parsed.path)
            if m:
                video_id = m.group(1)
    safe_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else f"https://{host}{parsed.path}"
    if not video_id and parsed.query:
        safe_url = f"{safe_url}?{parsed.query}"
    return video_id, safe_url


def extract_api_key(request) -> str:
    """So'rovdan API kalitni ajratib olish (Header yoki Query)"""
    auth = request.headers.get("Authorization", "").strip()
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    if auth:
        return auth
    
    x_api_key = request.headers.get("X-API-Key", "").strip()
    if x_api_key:
        return x_api_key
        
    return request.query.get("api_key", "").strip()


def authenticate_request(request):
    """API kalitni tekshirish va foydalanuvchini olish"""
    key = extract_api_key(request)
    if not key:
        return None, web.json_response({
            "ok": False,
            "error": "unauthorized",
            "message": "API kalit topilmadi! 'Authorization: Bearer <kalit>' yoki 'X-API-Key' sarlavhasini yuboring."
        }, status=401)
        
    user = get_user_by_api_key(key)
    if not user:
        return None, web.json_response({
            "ok": False,
            "error": "invalid_api_key",
            "message": "Yaroqsiz yoki eskirgan API kalit! Bot orqali yangilang."
        }, status=401)
        
    if not user.get("is_active", True):
        return None, web.json_response({
            "ok": False,
            "error": "api_key_disabled",
            "message": "Ushbu API kalit faol emas! Bot orqali qayta yoqing yoki yangilang."
        }, status=403)
        
    log_api_key_usage(key)
    return user, None


# ==================== ENDPOINTS ====================

async def handle_api_me(request):
    """GET /api/v1/me - Foydalanuvchi ma'lumotlari va balansi"""
    user, err = authenticate_request(request)
    if err: return err
    
    balance_uzs = user.get("balance_uzs", 0)
    balance_usd = round(balance_uzs / 12800.0, 2)
    
    return web.json_response({
        "ok": True,
        "user": {
            "tg_user_id": user["tg_user_id"],
            "balance_uzs": balance_uzs,
            "balance_usd_approx": balance_usd,
            "kyc_status": user.get("kyc_status", "unverified"),
            "total_requests": user.get("total_requests", 0)
        }
    })


async def handle_api_products(request):
    """GET /api/v1/products - Barcha 25 ta Pay-As-You-Go API xizmatlari va narxlari"""
    user, err = authenticate_request(request)
    if err: return err
    
    key_stock = get_api_keys_stock_count()
    proxy_stock = get_proxies_stock_count()
    
    products = {
        "botshield_captcha": {
            "name": "BotShield Captcha as a Service (Pay-As-You-Go)",
            "service_id": "botshield_captcha",
            "price_uzs": 10,
            "stars": 1,
            "unit": "1 verification",
            "available": True,
            "demo_url": "/captcha/demo",
            "embed_script": "/captcha/widget.js",
            "description": "Sayt va botlarni spamdan himoya qiluvchi 4 xil insoniy captcha"
        },
        "openrouter": {
            "name": "OpenRouter API Key ($3 tier)",
            "service_id": "openrouter",
            "price_uzs": 38000,
            "price_usd": 3.0,
            "in_stock": key_stock.get("openrouter", 0),
            "available": key_stock.get("openrouter", 0) > 0
        },
        "gemini": {
            "name": "Google Gemini API Key ($5 tier)",
            "service_id": "gemini",
            "price_uzs": 64000,
            "price_usd": 5.0,
            "in_stock": key_stock.get("gemini", 0),
            "available": key_stock.get("gemini", 0) > 0
        },
        "groq": {
            "name": "Groq Cloud API Key (Llama 3.3 70B)",
            "service_id": "groq",
            "price_uzs": 10000,
            "price_usd": 0.8,
            "in_stock": key_stock.get("groq", 0),
            "available": key_stock.get("groq", 0) > 0
        },
        "proxy": {
            "name": "Dedicated HTTP/HTTPS Private Proxy",
            "service_id": "proxy",
            "price_uzs": 38000,
            "price_usd": 3.0,
            "in_stock": proxy_stock,
            "available": proxy_stock > 0
        }
    }
    
    ai_services = {
        "summarize": {
            "name": "YouTube Transcript AI Summary & Timecodes",
            "endpoint": "POST /api/v1/ai/summarize",
            "cost_uzs": 1000,
            "cost_stars": 4,
            "description": "YouTube video transkriptini tahlil qilib, 5 ta asosiy tezis va timecode xulosasini beradi."
        },
        "clickbait_title": {
            "name": "High-CTR Viral Title Generator & A/B Testing",
            "endpoint": "POST /api/v1/ai/clickbait-title",
            "cost_uzs": 750,
            "cost_stars": 3,
            "description": "YouTube tavsiyalar algoritmi uchun yuqori bosilish darajasiga ega sarlavhalar va psixologik triggerlar."
        },
        "shorts_hook": {
            "name": "Viral Shorts 3-Second Hook & Full Script",
            "endpoint": "POST /api/v1/ai/shorts-hook",
            "cost_uzs": 1250,
            "cost_stars": 5,
            "description": "Shorts/Reels uchun retentionni 80%+ darajada ushlab turuvchi 3-soniyalik hook va sahnama-sahna ssenariy."
        },
        "reply_comment": {
            "name": "Contextual Comment Responder with Persona",
            "endpoint": "POST /api/v1/ai/reply-comment",
            "cost_uzs": 250,
            "cost_stars": 1,
            "description": "Kanal konteksti va belgilangan persona (samimiy, ekspert, hazil) asosida izohlarga tabiiy javoblar."
        },
        "generate": {
            "name": "Universal Pay-Per-Prompt AI Generation",
            "endpoint": "POST /api/v1/ai/generate",
            "cost_uzs": 100,
            "cost_stars": 1,
            "description": "Istalgan matn, tahlil yoki so'rov uchun tezkor va tejamkor AI generatsiyasi."
        }
    }

    media_services = {
        "uniquify": {
            "name": "8-Layer Anti-Copyright Video Uniquifier",
            "endpoint": "POST /api/v1/media/uniquify",
            "cost_uzs": 3000,
            "cost_stars": 12,
            "description": "Content-ID algoritmlaridan o'tuvchi 8 qatlamli (audio pitch, micro-speed, LUT, noise, crop) unikalizatsiya."
        },
        "crop_vertical": {
            "name": "Horizontal to 9:16 Vertical Video Cropper",
            "endpoint": "POST /api/v1/media/crop-vertical",
            "cost_uzs": 2500,
            "cost_stars": 10,
            "description": "Gorizontal videoni 9:16 vertikal formatga blur fon yoki smart crop orqali moslashtirish."
        },
        "remove_silence": {
            "name": "Jump-Cut Audio Silence Remover",
            "endpoint": "POST /api/v1/media/remove-silence",
            "cost_uzs": 2000,
            "cost_stars": 8,
            "description": "Videodagi nofaol va ovozsiz bo'laklarni avtomatik qirqib, dinamik jump-cut videoga aylantirish."
        },
        "compress_telegram": {
            "name": "Native Telegram 50MB Ultra Compressor",
            "endpoint": "POST /api/v1/media/compress-telegram",
            "cost_uzs": 1000,
            "cost_stars": 4,
            "description": "2-pass bitrate optimizatsiyasi bilan videoni Telegram 50MB limitiga moslashtirish (faststart streamable)."
        },
        "downloader": {
            "name": "HD Media & Audio MP3 Extractor",
            "endpoint": "POST /api/v1/downloader",
            "cost_uzs": 50,
            "cost_stars": 1,
            "description": "YouTube videolarini 360p dan 4K gacha va audio MP3 formatida to'g'ridan yuklab olish."
        }
    }
    
    smm_services = {
        "smart_deeplink": {
            "name": "YouTube In-App Smart DeepLink & QR Generator",
            "endpoint": "POST /api/v1/smm/smart-deeplink",
            "cost_uzs": 500,
            "cost_stars": 2,
            "description": "Mobil brauzerni aylanib o'tib to'g'ridan YouTube appda ochuvchi intent havolalar va QR kod."
        },
        "spy_velocity": {
            "name": "Competitor Velocity & Viral Trend Spy",
            "endpoint": "GET /api/v1/smm/spy/velocity",
            "cost_uzs": 1500,
            "cost_stars": 6,
            "description": "Raqobatchi kanal trenddagi videolari, ko'rishlar tezligi (VPH) va o'zib ketish bo'yicha AI tavsiyalar."
        },
        "like": {
            "name": "Targeted YouTube Likes",
            "endpoint": "POST /api/v1/smm/order",
            "type": "like",
            "unit_price_uzs": 1500,
            "cost_stars": 1,
            "min_quantity": 10
        },
        "subscribe": {
            "name": "Active YouTube Subscribers",
            "endpoint": "POST /api/v1/smm/order",
            "type": "subscribe",
            "unit_price_uzs": 2500,
            "cost_stars": 2,
            "min_quantity": 10
        },
        "view": {
            "name": "High-Retention YouTube Views",
            "endpoint": "POST /api/v1/smm/order",
            "type": "view",
            "unit_price_uzs": 1500,
            "cost_stars": 1,
            "min_quantity": 50
        },
        "autostream": {
            "name": "YouTube 24/7 Autostream Cloud",
            "endpoint": "POST /api/v1/smm/order",
            "type": "autostream",
            "price_per_hour_uzs": 4000,
            "cost_stars": 12,
            "min_hours": 1
        }
    }

    gamification_services = {
        "gifts_send": {
            "name": "Direct Telegram Profile Gift Send",
            "endpoint": "POST /api/v1/gifts/send",
            "cost_uzs": 8750,
            "cost_stars": 25,
            "description": "Telegram profiliga server-side rasmiy sovg'a yuborish."
        },
        "vouchers_create": {
            "name": "Gift Voucher Generator (GIFT-XXXX)",
            "endpoint": "POST /api/v1/vouchers/create",
            "cost_uzs": 1000,
            "cost_stars": 3,
            "description": "O'z balansingizdan istalgan summadagi sovg'a vaucherlarini yaratish."
        },
        "vouchers_redeem": {
            "name": "Voucher & Promo Code Redeemer",
            "endpoint": "POST /api/v1/vouchers/redeem",
            "cost_uzs": 0,
            "cost_stars": 0,
            "description": "Sovg'a vaucheri yoki promokod orqali hisobni to'ldirish."
        },
        "cases_open": {
            "name": "Telegram Stars Mystery Case Unboxing",
            "endpoint": "POST /api/v1/cases/open",
            "cost_uzs": 5000,
            "cost_stars": 15,
            "description": "Jonli Telegram sovg'alari bilan 5 Tier keyslarni ochish."
        }
    }

    reseller_tools = {
        "bot_connect": {
            "name": "White-Label Reseller Bot Connector",
            "endpoint": "POST /api/v1/reseller/bot/connect",
            "cost_uzs": 0,
            "cost_stars": 0,
            "description": "O'z Telegram bot tokeningizni ulab, shaxsiy marja (ustama) bilan mijozlarga sotish."
        },
        "stars_invoice": {
            "name": "Telegram Stars Payment Invoice Creator",
            "endpoint": "POST /api/v1/billing/stars/invoice",
            "cost_uzs": 0,
            "cost_stars": 0,
            "description": "XTR Stars valyutasida to'g'ridan-to'g'ri to'lov havolasi yaratish."
        },
        "webhooks_set": {
            "name": "Reseller Real-Time Webhook Dispatcher",
            "endpoint": "POST /api/v1/webhooks/set",
            "cost_uzs": 0,
            "cost_stars": 0,
            "description": "Buyurtmalar va to'lovlar haqida tashqi serveringizga avtomatik bildirishnoma."
        }
    }
    
    return web.json_response({
        "ok": True,
        "currency": "UZS",
        "star_rate_uzs": 350,
        "products": products,
        "ai_services": ai_services,
        "media_services": media_services,
        "smm_services": smm_services,
        "gamification_services": gamification_services,
        "reseller_tools": reseller_tools
    })


async def handle_api_buy(request):
    """POST /api/v1/buy - Mahsulot (API kalit yoki Proxy) xarid qilish"""
    user, err = authenticate_request(request)
    if err: return err
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json", "message": "JSON tana kiritilmadi"}, status=400)
        
    service = str(data.get("service", "")).strip().lower()
    if not service:
        return web.json_response({
            "ok": False,
            "error": "missing_service",
            "message": "'service' parametri kiritilishi shart (openrouter, gemini, groq, proxy)"
        }, status=400)
        
    tg_user_id = user["tg_user_id"]
    
    if service in ("openrouter", "gemini", "groq"):
        res = purchase_api_key(tg_user_id, service)
        if res.get("ok"):
            return web.json_response({
                "ok": True,
                "service": service,
                "api_key": res.get("api_key"),
                "price_uzs": res.get("price_uzs"),
                "price_usd": res.get("price_usd"),
                "remaining_balance_uzs": res.get("new_balance")
            })
        else:
            return web.json_response({
                "ok": False,
                "error": res.get("error", "Xarid amalga oshmadi"),
                "out_of_stock": res.get("out_of_stock", False),
                "insufficient_funds": res.get("insufficient_funds", False),
                "required_uzs": res.get("required"),
                "current_uzs": res.get("current")
            }, status=400)
            
    elif service == "proxy":
        res = purchase_proxy(tg_user_id)
        if res.get("ok"):
            return web.json_response({
                "ok": True,
                "service": "proxy",
                "proxy_url": res.get("proxy_url"),
                "price_uzs": res.get("price_uzs"),
                "price_usd": res.get("price_usd"),
                "remaining_balance_uzs": res.get("new_balance")
            })
        else:
            return web.json_response({
                "ok": False,
                "error": res.get("error", "Proxy xarid qilinmadi"),
                "out_of_stock": res.get("out_of_stock", False),
                "insufficient_funds": res.get("insufficient_funds", False),
                "required_uzs": res.get("required"),
                "current_uzs": res.get("current")
            }, status=400)
    else:
        return web.json_response({
            "ok": False,
            "error": "invalid_service",
            "message": f"Noma'lum xizmat: '{service}'. Faqat 'openrouter', 'gemini', 'groq' yoki 'proxy' qabul qilinadi."
        }, status=400)


async def handle_api_smm_order(request):
    """POST /api/v1/smm/order - YouTube Layk, Obunachi buyurtma berish"""
    user, err = authenticate_request(request)
    if err: return err
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json", "message": "JSON tana kiritilmadi"}, status=400)
        
    order_type = str(data.get("order_type", "")).strip().lower()
    target_url = str(data.get("target_url", "")).strip()
    try:
        quantity = int(data.get("quantity", 0))
    except (TypeError, ValueError):
        quantity = 0
        
    if order_type not in ("like", "subscribe", "view"):
        return web.json_response({
            "ok": False,
            "error": "invalid_order_type",
            "message": "'order_type' faqat 'like', 'subscribe' yoki 'view' bo'lishi mumkin"
        }, status=400)
        
    if not target_url:
        return web.json_response({
            "ok": False,
            "error": "missing_target_url",
            "message": "'target_url' (YouTube havola) kiritilishi shart"
        }, status=400)

    _, safe_target_url = extract_safe_youtube_target(target_url)
    if not safe_target_url:
        return web.json_response({
            "ok": False,
            "error": "invalid_target_url",
            "message": "'target_url' haqiqiy YouTube havola bo'lishi shart"
        }, status=400)
    target_url = safe_target_url
        
    if quantity < 1 or quantity > 1000000:
        return web.json_response({
            "ok": False,
            "error": "invalid_quantity",
            "message": "'quantity' 1 dan 1,000,000 gacha bo'lishi kerak"
        }, status=400)
        
    rates = {
        "like": 1500,
        "subscribe": 2500,
        "view": 1500
    }
    unit_price = rates[order_type]
    total_cost = unit_price * quantity
    
    tg_user_id = user["tg_user_id"]
    conn = get_db()
    if not conn:
        return web.json_response({"ok": False, "error": "db_error", "message": "Baza bilan aloqa yo'q"}, status=500)
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        b_row = cur.fetchone()
        curr_bal = b_row["balance_uzs"] if b_row else 0
        
        if curr_bal < total_cost:
            conn.rollback()
            return web.json_response({
                "ok": False,
                "error": "insufficient_funds",
                "message": f"Balansingiz yetarli emas! Kerak: {total_cost:,} so'm, mavjud: {curr_bal:,} so'm",
                "required_uzs": total_cost,
                "current_uzs": curr_bal
            }, status=400)
            
        new_bal = curr_bal - total_cost
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))
        
        cur.execute("""
            INSERT INTO engagement_orders (tg_user_id, order_type, target_url, target_id, quantity, total_cost, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """, (tg_user_id, order_type, target_url, target_url, quantity, total_cost))
        
        o_row = cur.fetchone()
        order_id = o_row["id"] if isinstance(o_row, dict) else o_row[0]
        conn.commit()
        
        return web.json_response({
            "ok": True,
            "order_id": order_id,
            "order_type": order_type,
            "target_url": target_url,
            "quantity": quantity,
            "total_cost_uzs": total_cost,
            "remaining_balance_uzs": new_bal,
            "status": "pending"
        })
    except Exception as e:
        conn.rollback()
        print(f"[reseller_api] handle_api_smm_order error: {e}")
        return web.json_response({"ok": False, "error": "server_error", "message": "Buyurtmani yaratishda server xatoligi yuz berdi"}, status=500)
    finally:
        conn.close()


async def handle_api_smm_status(request):
    """GET /api/v1/smm/order/{order_id} - Buyurtma holatini tekshirish"""
    user, err = authenticate_request(request)
    if err: return err
    
    order_id_str = request.match_info.get("order_id", "")
    try:
        order_id = int(order_id_str)
    except ValueError:
        return web.json_response({"ok": False, "error": "invalid_id", "message": "Buyurtma ID si noto'g'ri"}, status=400)
        
    conn = get_db()
    if not conn: return web.json_response({"ok": False, "error": "db_error"}, status=500)
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM engagement_orders WHERE id = %s AND tg_user_id = %s", (order_id, user["tg_user_id"]))
        row = cur.fetchone()
        if not row:
            return web.json_response({"ok": False, "error": "not_found", "message": "Buyurtma topilmadi"}, status=404)
            
        return web.json_response({
            "ok": True,
            "order": {
                "id": row["id"] if isinstance(row, dict) else row[0],
                "order_type": row["order_type"] if isinstance(row, dict) else row[2],
                "target_url": row["target_url"] if isinstance(row, dict) else row[3],
                "quantity": row["quantity"] if isinstance(row, dict) else row[5],
                "completed_count": row["completed_count"] if isinstance(row, dict) else row[6],
                "total_cost_uzs": row["total_cost"] if isinstance(row, dict) else row[7],
                "status": row["status"] if isinstance(row, dict) else row[8],
                "created_at": str(row["created_at"] if isinstance(row, dict) else row[9])
            }
        })
    finally:
        conn.close()



# ==================== 5 EXPANDED DEVELOPER ENDPOINTS ====================

async def handle_api_downloader(request):
    """
    POST /api/v1/downloader - Media info & direct MP4/MP3 download extractor
    JSON payload:
      - url: YouTube video havola yoki video ID
      - format: '360', '480', '720', '1080', '1440', '2160', 'mp3' (ixtiyoriy, default '720')
    GET orqali ham ishlaydi: ?url=...&format=...
    """
    user, err = authenticate_request(request)
    if err:
        return err

    if request.method == "POST":
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid_json", "message": "JSON tana kiritilmadi"}, status=400)
    else:
        data = request.query

    raw_url = str(data.get("url", "")).strip()
    requested_format = str(data.get("format", "720")).strip().lower()
    if requested_format not in _ALLOWED_DOWNLOAD_FORMATS:
        return web.json_response({
            "ok": False,
            "error": "invalid_format",
            "message": "Noto'g'ri format! Ruxsat etilgan: 360, 480, 720, 1080, 1440, 2160, 4320, mp3"
        }, status=400)

    if not raw_url:
        return web.json_response({
            "ok": False,
            "error": "missing_url",
            "message": "'url' parametri kiritilishi shart (YouTube video havola yoki video ID)"
        }, status=400)

    # Strict YouTube URL / Video ID validation (Anti-SSRF)
    video_id, target_url = extract_safe_youtube_target(raw_url)
    if not target_url:
        return web.json_response({
            "ok": False,
            "error": "invalid_url",
            "message": "Faqat haqiqiy YouTube video havolasi yoki 11 belgili video ID qabul qilinadi"
        }, status=400)

    base_domain = APP_BASE_URL.rstrip("/")
    standard_formats = [
        {"label": "360p", "value": "360", "ext": "mp4"},
        {"label": "480p", "value": "480", "ext": "mp4"},
        {"label": "720p (HD)", "value": "720", "ext": "mp4"},
        {"label": "1080p (FHD)", "value": "1080", "ext": "mp4"},
        {"label": "1440p (2K)", "value": "1440", "ext": "mp4"},
        {"label": "2160p (4K)", "value": "2160", "ext": "mp4"},
        {"label": "MP3 (Audio 192k)", "value": "mp3", "ext": "mp3"}
    ]

    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_vr', 'android', 'tv_embedded'],
                    'player_skip': ['webpage'],
                }
            }
        }

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(target_url, download=False)

        info = await asyncio.to_thread(_extract)
        title = info.get("title", "Video")
        duration = info.get("duration", 0)
        thumbnail = info.get("thumbnail", "")
        uploader = info.get("uploader", "")
        vid = video_id or info.get("id", "")
        dl_exp, dl_sig = generate_download_signature(vid, requested_format, user['tg_user_id'])
        download_url = f"{base_domain}/api/download-file?video_id={vid}&resolution={requested_format}&tg_user_id={user['tg_user_id']}&exp={dl_exp}&sig={dl_sig}"

        return web.json_response({
            "ok": True,
            "video_id": vid,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "uploader": uploader,
            "selected_format": requested_format,
            "download_url": download_url,
            "available_formats": standard_formats
        })
    except Exception as e:
        print(f"[reseller_api] handle_api_downloader error: {e}")
        if video_id:
            dl_exp, dl_sig = generate_download_signature(video_id, requested_format, user['tg_user_id'])
            download_url = f"{base_domain}/api/download-file?video_id={video_id}&resolution={requested_format}&tg_user_id={user['tg_user_id']}&exp={dl_exp}&sig={dl_sig}"
            return web.json_response({
                "ok": True,
                "video_id": video_id,
                "title": f"YouTube Media ({video_id})",
                "selected_format": requested_format,
                "download_url": download_url,
                "available_formats": standard_formats,
                "note": "Metadata qisman tayyorlandi"
            })
        return web.json_response({
            "ok": False,
            "error": "extract_error",
            "message": "Media ma'lumotlarini ajratib bo'lmadi"
        }, status=500)


async def handle_api_gifts_available(request):
    """
    GET /api/v1/gifts/available - Telegram jonli rasmiy sovg'alar katalogi
    (Narxlar, kamyoblik va NFT sonlari bilan)
    """
    user, err = authenticate_request(request)
    if err:
        return err

    try:
        gifts = await fetch_telegram_server_gifts()
        if not gifts:
            cases = build_cases_from_gifts()
            gifts = []
            for c in cases.values():
                gifts.extend(c.get("drops", []))

        formatted = []
        for g in gifts:
            formatted.append({
                "id": g.get("id") or g.get("file_id"),
                "name": g.get("name") or g.get("prize_name", "Telegram Gift"),
                "stars": g.get("stars", 25),
                "rarity": g.get("rarity", "common"),
                "is_nft": bool(g.get("is_nft")),
                "total_count": g.get("total_count"),
                "remaining_count": g.get("remaining_count"),
                "file_id": g.get("file_id", ""),
                "file_type": g.get("file_type", "webp"),
                "icon": g.get("icon", "package"),
                "image_url": g.get("image_url")
            })

        return web.json_response({
            "ok": True,
            "count": len(formatted),
            "gifts": formatted
        })
    except Exception as e:
        print(f"[reseller_api] handle_api_gifts_available error: {e}")
        return web.json_response({"ok": False, "error": "server_error", "message": "Sovg'alar katalogini yuklashda xatolik yuz berdi"}, status=500)


async def handle_api_cases_open(request):
    """
    POST /api/v1/cases/open - Tashqi Reseller / Dasturchi Keys Ochish API
    JSON payload:
      - tier_id: 'tier_1', 'tier_2', 'tier_3', 'tier_4', 'tier_5' (default 'tier_1')
      - currency: 'uzs' yoki 'stars' (default 'uzs')
      - user_id: ixtiyoriy yutuq egasi (default - API kalit egasi)
    Mablag' qat'iy ravishda autentifikatsiyadan o'tgan API kalit egasidan yechiladi.
    """
    user, err = authenticate_request(request)
    if err:
        return err

    try:
        data = await request.json()
    except Exception:
        data = {}

    tier_id = str(data.get("tier_id", "tier_1")).strip().lower()
    payer_id = int(user["tg_user_id"])
    try:
        raw_target_uid = int(data.get("user_id", 0) or 0)
        target_user_id = raw_target_uid if raw_target_uid > 0 else payer_id
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "invalid_user_id", "message": "Noto'g'ri user_id"}, status=400)

    cases = build_cases_from_gifts()
    case = cases.get(tier_id)
    if not case:
        for c in cases.values():
            if c.get("key") == tier_id or c.get("id") == tier_id:
                case = c
                break
    if not case:
        return web.json_response({
            "ok": False,
            "error": "invalid_tier",
            "message": f"Noto'g'ri keys tanlandi: '{tier_id}'. Mavjud keyslar: tier_1, tier_2, tier_3, tier_4, tier_5"
        }, status=400)

    price_uzs = case.get("price_uzs", case["price_stars"] * 400)

    # 1. Payer balansini tekshirish
    current_bal = get_user_balance(payer_id)
    if current_bal < price_uzs:
        return web.json_response({
            "ok": False,
            "error": "insufficient_funds",
            "message": f"Balansingiz yetarli emas! Sizda: {current_bal:,} so'm bor, keys ochish uchun esa: {price_uzs:,} so'm kerak.",
            "current_balance": current_bal,
            "required_balance": price_uzs
        }, status=400)

    # 2. Payer balansidan atomik tarzda yechish
    if not deduct_user_balance(payer_id, price_uzs):
        latest_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": False,
            "error": "insufficient_funds",
            "message": f"Balansdan mablag' yechishda xatolik yuz berdi. Joriy balans: {latest_bal:,} so'm.",
            "current_balance": latest_bal,
            "required_balance": price_uzs
        }, status=400)

    # 3. Keysni ochish
    res = open_stars_case(target_user_id, tier_id, user_name=str(target_user_id))
    if not res.get("ok"):
        # Xatolik bo'lsa pulni zudlik bilan qaytarish
        add_user_balance(payer_id, price_uzs)
        return web.json_response(res, status=400)

    rem_bal = get_user_balance(payer_id)
    res["price_uzs"] = price_uzs
    res["new_balance"] = rem_bal
    res["target_user_id"] = target_user_id
    res["payer_id"] = payer_id

    # 4. Sovg'ani pending_gifts jadvaliga saqlaymiz
    try:
        save_gift_record(
            tg_user_id=target_user_id,
            prize_name=res["prize_name"],
            prize_stars=res["prize_stars"],
            case_name=res["case_name"],
            gift_id=res.get("gift_id")
        )
    except Exception:
        pass

    return web.json_response(res)


async def handle_api_vouchers_redeem(request):
    """
    POST /api/v1/vouchers/redeem - Promokod va vaucher kodini faollashtirish
    JSON payload:
      - code: Promokod yoki Vaucher matni (masalan: VIP2026, GIFT50K)
      - user_id: ixtiyoriy (default - API kalit egasi)
    """
    user, err = authenticate_request(request)
    if err:
        return err

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json", "message": "JSON tana kiritilmadi"}, status=400)

    code = str(data.get("code", "") or data.get("voucher_code", "")).strip().upper()
    if not code:
        return web.json_response({
            "ok": False,
            "error": "missing_code",
            "message": "'code' parametri kiritilishi shart"
        }, status=400)

    try:
        raw_target_uid = int(data.get("user_id", 0) or 0)
        target_user_id = raw_target_uid if raw_target_uid > 0 else user["tg_user_id"]
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "invalid_user_id", "message": "Noto'g'ri user_id"}, status=400)

    # 1. Avval vouchers jadvalidan tekshirish
    v_res = redeem_voucher(target_user_id, code)
    if v_res.get("ok"):
        v_res["type"] = "voucher"
        v_res["code"] = code
        v_res["message"] = "Vaucher muvaffaqiyatli faollashtirildi!"
        return web.json_response(v_res)

    # 2. Keyin promo_codes jadvalidan tekshirish
    success, msg, bonus = redeem_promo_code(code, target_user_id)
    if success:
        new_bal = get_user_balance(target_user_id)
        return web.json_response({
            "ok": True,
            "type": "promo_code",
            "code": code,
            "amount_uzs": bonus,
            "bonus_amount": bonus,
            "new_balance": new_bal,
            "message": msg
        })

    return web.json_response({
        "ok": False,
        "error": "invalid_code",
        "message": v_res.get("error") or msg or "Bunday promokod yoki vaucher mavjud emas!"
    }, status=400)


async def handle_api_webhooks_set(request):
    """
    POST /api/v1/webhooks/set - Reseller tashqi webhook URL manzilini biriktirish
    JSON payload:
      - webhook_url: Tashqi tizim HTTPS/HTTP webhook URL manzili
      - secret_token: Ixtiyoriy xavfsizlik tokeni (HMAC/Bearer tekshirish uchun)
    """
    user, err = authenticate_request(request)
    if err:
        return err

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json", "message": "JSON tana kiritilmadi"}, status=400)

    webhook_url = str(data.get("webhook_url", "")).strip()
    secret_token = str(data.get("secret_token", "")).strip() or None

    if not is_safe_public_webhook_url(webhook_url):
        return web.json_response({
            "ok": False,
            "error": "invalid_url",
            "message": "'webhook_url' ommaviy, xavfsiz HTTP/HTTPS manzil bo'lishi shart (ichki/lokal manzillar taqiqlangan)"
        }, status=400)

    ok = set_reseller_webhook(user["tg_user_id"], webhook_url, secret_token)
    if ok:
        return web.json_response({
            "ok": True,
            "webhook_url": webhook_url,
            "secret_token": secret_token,
            "is_active": True,
            "message": "Webhook muvaffaqiyatli saqlandi va faollashtirildi!"
        })
    else:
        return web.json_response({
            "ok": False,
            "error": "db_error",
            "message": "Webhookni saqlab bo'lmadi"
        }, status=500)


async def handle_api_webhooks_get(request):
    """
    GET /api/v1/webhooks - Hozirgi biriktirilgan webhook holati
    """
    user, err = authenticate_request(request)
    if err:
        return err

    data = get_reseller_webhook(user["tg_user_id"])
    if data:
        if data.get("expires_at"):
            data["expires_at"] = str(data["expires_at"])
        if data.get("created_at"):
            data["created_at"] = str(data["created_at"])
        return web.json_response({"ok": True, "webhook": data})
    else:
        return web.json_response({
            "ok": True,
            "webhook": None,
            "message": "Sizda faol webhook biriktirilmagan"
        })


# ==================== 1. AI PAY-AS-YOU-GO ENDPOINTS ====================

async def handle_api_ai_summarize(request):
    """
    POST /api/v1/ai/summarize - YouTube transkript xulosasi, asosiy tezislar va timecodes
    Narxi: 1,000 UZS / 4 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 1000
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json", "message": "JSON tana kiritilmadi"}, status=400)

    video_url = str(data.get("video_url", "")).strip()
    if not video_url:
        return web.json_response({"ok": False, "error": "missing_video_url", "message": "'video_url' kiritilishi shart"}, status=400)
    _, safe_video_url = extract_safe_youtube_target(video_url)
    if not safe_video_url:
        return web.json_response({"ok": False, "error": "invalid_video_url", "message": "Faqat haqiqiy YouTube video havolasi qabul qilinadi"}, status=400)
    video_url = safe_video_url

    language = str(data.get("language", "uz")).strip().lower()
    detail_level = str(data.get("detail_level", "medium")).strip().lower()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": False,
            "error": "insufficient_funds",
            "message": f"Balansingiz yetarli emas! Xizmat narxi: {COST_UZS:,} so'm, mavjud: {curr_bal:,} so'm.",
            "required_uzs": COST_UZS,
            "current_uzs": curr_bal
        }, status=402)

    try:
        meta = await asyncio.to_thread(extract_competitor_metadata, video_url)
        title = meta.get("title", "")
        desc = meta.get("description", "")
        tags = meta.get("tags", [])
        duration = meta.get("duration", 0)

        prompt = (
            f"Sen professional YouTube video tahlilchisisan.\n"
            f"Quyidagi YouTube video ma'lumotlari asosida {language} tilida chuqur va aniq xulosa tayyorla:\n"
            f"Video nomi: {title}\n"
            f"Davomiyligi: {duration} soniya\n"
            f"Tavsifi: {desc[:2000]}\n"
            f"Teglar: {', '.join(tags[:15])}\n"
            f"Tafsilot darajasi: {detail_level}\n\n"
            f"Javobni quyidagi tuzilmada ber:\n"
            f"1. QISQA XULOSA (Executive Summary - 2-3 jumla)\n"
            f"2. ASOSIY TEZISLAR (5 ta eng muhim g'oya va xulosalar)\n"
            f"3. XRONOMETRAJ VA BOBLAR (Taxminiy timecodes va qismlar)\n"
            f"4. MAQSADLI AUDITORIYA VA TAVSIYA"
        )
        ai_result = await generate_with_fallback_async(prompt)
        record_api_metered_usage(payer_id, "/api/v1/ai/summarize", COST_UZS, "success")

        new_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": True,
            "service": "ai_summarize",
            "cost_uzs": COST_UZS,
            "cost_stars": 4,
            "video_url": video_url,
            "video_title": title,
            "duration_sec": duration,
            "summary": ai_result,
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] handle_api_ai_summarize error: {e}")
        record_api_metered_usage(payer_id, "/api/v1/ai/summarize", 0, "error")
        return web.json_response({
            "ok": False,
            "error": "ai_processing_error",
            "message": f"Tahlil jarayonida xatolik yuz berdi va {COST_UZS:,} so'm hisobingizga qaytarildi."
        }, status=500)


async def handle_api_ai_clickbait_title(request):
    """
    POST /api/v1/ai/clickbait-title - High-CTR sarlavhalar va A/B test
    Narxi: 750 UZS / 3 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 750
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    topic = str(data.get("topic", "")).strip()
    if not topic:
        return web.json_response({"ok": False, "error": "missing_topic", "message": "'topic' kiritilishi shart"}, status=400)

    niche = str(data.get("niche", "general")).strip()
    count = min(max(int(data.get("count", 5)), 3), 10)
    language = str(data.get("language", "uz")).strip()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": False,
            "error": "insufficient_funds",
            "message": f"Balansingiz yetarli emas! Kerak: {COST_UZS:,} so'm, mavjud: {curr_bal:,} so'm.",
            "required_uzs": COST_UZS,
            "current_uzs": curr_bal
        }, status=402)

    try:
        prompt = (
            f"Sen YouTube CTR mutaxassisisan (MrBeast uslubi).\n"
            f"Mavzu: '{topic}' (Nisha: {niche}, Til: {language}).\n"
            f"Ushbu mavzu uchun YouTube tavsiyalar algoritmini yorib o'tuvchi aynan {count} ta High-CTR sarlavha yarat.\n"
            f"Har bir sarlavha uchun:\n"
            f"- Sarlavha matni (emojilar bilan)\n"
            f"- Psixologik trigger (Qiziqish, Qo'rquv, Shok, Foyda)\n"
            f"- Kutilayotgan CTR indeksi (foizda, masalan 11-16%)\n"
            f"- A/B test uchun muqobil variant\n"
            f"Javobni tushunarli, chiroyli ro'yxat shaklida ber."
        )
        ai_res = await generate_with_fallback_async(prompt)
        record_api_metered_usage(payer_id, "/api/v1/ai/clickbait-title", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": True,
            "service": "ai_clickbait_title",
            "cost_uzs": COST_UZS,
            "cost_stars": 3,
            "topic": topic,
            "niche": niche,
            "titles_generated": count,
            "result": ai_res,
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] handle_api_ai_clickbait_title error: {e}")
        return web.json_response({
            "ok": False,
            "error": "ai_error",
            "message": f"Xatolik yuz berdi va {COST_UZS:,} so'm balansingizga qaytarildi."
        }, status=500)


async def handle_api_ai_shorts_hook(request):
    """
    POST /api/v1/ai/shorts-hook - Viral 3-soniyalik Hook va ssenariy
    Narxi: 1,250 UZS / 5 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 1250
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    topic = str(data.get("topic", "")).strip()
    if not topic:
        return web.json_response({"ok": False, "error": "missing_topic", "message": "'topic' kiritilishi shart"}, status=400)

    audience = str(data.get("target_audience", "general")).strip()
    duration = int(data.get("duration_sec", 45))
    language = str(data.get("language", "uz")).strip()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": False,
            "error": "insufficient_funds",
            "required_uzs": COST_UZS,
            "current_uzs": curr_bal
        }, status=402)

    try:
        prompt = (
            f"Sen viral YouTube Shorts va Reels ssenariynavisisan.\n"
            f"Mavzu: '{topic}'. Auditoriya: {audience}. Davomiyligi: {duration} soniya. Til: {language}.\n"
            f"Quyidagi qat'iy talablar asosida ssenariy yoz:\n"
            f"1. 0-3 SONIYA (VIRAL VISUAL & AUDIO HOOK): Foydalanuvchi videoni o'tkazib yubormasligi uchun ekranda nima bo'ladi va qanday shok jumla aytiladi.\n"
            f"2. 3-15 SONIYA (INTRIGA VA MUAMMO): Qiziqishni maksimal darajaga ko'tarish.\n"
            f"3. 15-{max(duration-5, 20)} SONIYA (YECHIM VA KULMINATSIYA): Asosiy qism va kutilmagan burilish.\n"
            f"4. SO'NGGI 5 SONIYA (LOOP CTA): Videoni qayta tomosha qildiruvchi (seamless loop) chaqiriq.\n"
            f"5. TAVSIYA ETILGAN OVOZ VA SOUND EFFECTLAR (SFX)"
        )
        ai_res = await generate_with_fallback_async(prompt)
        record_api_metered_usage(payer_id, "/api/v1/ai/shorts-hook", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": True,
            "service": "ai_shorts_hook",
            "cost_uzs": COST_UZS,
            "cost_stars": 5,
            "topic": topic,
            "script": ai_res,
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] ai_error: {e}")
        return web.json_response({"ok": False, "error": "ai_error", "message": "Xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_ai_reply_comment(request):
    """
    POST /api/v1/ai/reply-comment - Persona bilan kontekstual izoh qaytaruvchi
    Narxi: 250 UZS / 1 Star
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 250
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    comment = str(data.get("comment_text", "")).strip()
    if not comment:
        return web.json_response({"ok": False, "error": "missing_comment_text", "message": "'comment_text' kiritilishi shart"}, status=400)

    persona = str(data.get("persona", "friendly")).strip().lower()
    channel_ctx = str(data.get("channel_context", "")).strip()
    language = str(data.get("language", "uz")).strip()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        prompt = (
            f"YouTube video izohiga professional javob yoz.\n"
            f"Foydalanuvchi izohi: '{comment}'\n"
            f"Kanal konteksti: '{channel_ctx}'\n"
            f"Javob beruvchi personasi: {persona} (Masalan: samimiy, ekspert, hazilkash yoki qo'llab-quvvatlovchi)\n"
            f"Til: {language}\n"
            f"Talab: Izoh egasini keyingi videolarni ko'rishga va muloqotga undovchi tabiiy, insoniy javob matni yoz (2-3 ta variant taqdim et)."
        )
        ai_res = await generate_with_fallback_async(prompt)
        record_api_metered_usage(payer_id, "/api/v1/ai/reply-comment", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": True,
            "service": "ai_reply_comment",
            "cost_uzs": COST_UZS,
            "cost_stars": 1,
            "persona": persona,
            "reply_options": ai_res,
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] ai_error: {e}")
        return web.json_response({"ok": False, "error": "ai_error", "message": "Xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_ai_generate(request):
    """
    POST /api/v1/ai/generate - Pay-Per-Prompt umumiy AI generatsiya
    Narxi: 100 UZS / 1 Star
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 100
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    prompt = str(data.get("prompt", "")).strip()
    if not prompt:
        return web.json_response({"ok": False, "error": "missing_prompt", "message": "'prompt' kiritilishi shart"}, status=400)

    sys_inst = str(data.get("system_instruction", "")).strip()
    full_prompt = f"{sys_inst}\n\n{prompt}" if sys_inst else prompt

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        ai_res = await generate_with_fallback_async(full_prompt)
        record_api_metered_usage(payer_id, "/api/v1/ai/generate", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)
        return web.json_response({
            "ok": True,
            "service": "ai_generate",
            "cost_uzs": COST_UZS,
            "cost_stars": 1,
            "response": ai_res,
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] ai_error: {e}")
        return web.json_response({"ok": False, "error": "ai_error", "message": "Xatolik yuz berdi, mablag' qaytarildi."}, status=500)


# ==================== 2. MEDIA PAY-AS-YOU-GO ENDPOINTS ====================

async def handle_api_media_uniquify(request):
    """
    POST /api/v1/media/uniquify - 8-qatlamli Anti-Copyright unikalizatsiya
    Narxi: 3,000 UZS / 12 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 3000
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    video_url = str(data.get("video_url", "")).strip()
    if not video_url:
        return web.json_response({"ok": False, "error": "missing_video_url", "message": "'video_url' kiritilishi shart"}, status=400)
    _, safe_video_url = extract_safe_youtube_target(video_url)
    if not safe_video_url:
        return web.json_response({"ok": False, "error": "invalid_video_url", "message": "Faqat haqiqiy YouTube video havolasi qabul qilinadi"}, status=400)
    video_url = safe_video_url

    intensity = str(data.get("intensity", "medium")).strip().lower()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        layers_applied = [
            {"layer": 1, "name": "Micro Speed Shift", "param": "setpts=0.985*PTS (1.5% tezlashuv)", "status": "active"},
            {"layer": 2, "name": "Acoustic Pitch Shift", "param": "asetrate=44100*1.015,aresample=44100", "status": "active"},
            {"layer": 3, "name": "Dynamic Color Grading", "param": "eq=contrast=1.04:brightness=0.01:saturation=1.06", "status": "active"},
            {"layer": 4, "name": "Smart Edge Micro-Crop", "param": "crop=in_w*0.98:in_h*0.98", "status": "active"},
            {"layer": 5, "name": "Subtle Zoom Oscillation", "param": "zoompan d=1:s=1080x1920:fps=30", "status": "active"},
            {"layer": 6, "name": "Imperceptible Film Noise", "param": "noise=alls=2:allf=t+u", "status": "active"},
            {"layer": 7, "name": "EXIF & Metadata Stripper", "param": "-map_metadata -1 -map_chapters -1", "status": "active"},
            {"layer": 8, "name": "Sub-Harmonic Audio Bed", "param": "amix=inputs=2:duration=first:dropout_transition=2", "status": "active"}
        ]
        ffmpeg_filter_complex = (
            "-vf \"setpts=0.985*PTS,crop=in_w*0.98:in_h*0.98,eq=contrast=1.04:brightness=0.01:saturation=1.06,noise=alls=2:allf=t+u\" "
            "-af \"asetrate=44100*1.015,aresample=44100\" -map_metadata -1"
        )
        base_domain = APP_BASE_URL.rstrip("/")
        task_id = f"uniq_{payer_id}_{int(asyncio.get_event_loop().time())}"

        record_api_metered_usage(payer_id, "/api/v1/media/uniquify", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "media_uniquify",
            "task_id": task_id,
            "cost_uzs": COST_UZS,
            "cost_stars": 12,
            "video_url": video_url,
            "intensity": intensity,
            "total_layers": 8,
            "layers": layers_applied,
            "ffmpeg_pipeline": ffmpeg_filter_complex,
            "download_stream_url": f"{base_domain}/api/download-file?video_id=processed_{task_id}&tg_user_id={payer_id}",
            "status": "ready",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] media_error: {e}")
        return web.json_response({"ok": False, "error": "media_error", "message": "Media ishlovida xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_media_crop_vertical(request):
    """
    POST /api/v1/media/crop-vertical - Gorizontaldan 9:16 vertikal formatga o'tkazish
    Narxi: 2,500 UZS / 10 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 2500
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    video_url = str(data.get("video_url", "")).strip()
    if not video_url:
        return web.json_response({"ok": False, "error": "missing_video_url", "message": "'video_url' kiritilishi shart"}, status=400)
    _, safe_video_url = extract_safe_youtube_target(video_url)
    if not safe_video_url:
        return web.json_response({"ok": False, "error": "invalid_video_url", "message": "Faqat haqiqiy YouTube video havolasi qabul qilinadi"}, status=400)
    video_url = safe_video_url

    mode = str(data.get("mode", "blur_background")).strip().lower()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        base_domain = APP_BASE_URL.rstrip("/")
        task_id = f"vert_{payer_id}_{int(asyncio.get_event_loop().time())}"

        filter_chain = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:25[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        ) if mode == "blur_background" else "crop=ih*9/16:ih:(iw-ow)/2:0,scale=1080:1920"

        record_api_metered_usage(payer_id, "/api/v1/media/crop-vertical", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "media_crop_vertical",
            "task_id": task_id,
            "cost_uzs": COST_UZS,
            "cost_stars": 10,
            "target_aspect_ratio": "9:16 (1080x1920)",
            "mode": mode,
            "filter_chain": filter_chain,
            "result_url": f"{base_domain}/api/download-file?video_id=vertical_{task_id}&tg_user_id={payer_id}",
            "status": "ready",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] media_error: {e}")
        return web.json_response({"ok": False, "error": "media_error", "message": "Media ishlovida xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_media_remove_silence(request):
    """
    POST /api/v1/media/remove-silence - Jump-cut sukunatni kesib tashlash
    Narxi: 2,000 UZS / 8 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 2000
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    video_url = str(data.get("video_url", "")).strip()
    if not video_url:
        return web.json_response({"ok": False, "error": "missing_video_url"}, status=400)

    threshold_db = int(data.get("silence_threshold_db", -30))
    min_silence = float(data.get("min_silence_duration_sec", 0.5))

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        base_domain = APP_BASE_URL.rstrip("/")
        task_id = f"silence_{payer_id}_{int(asyncio.get_event_loop().time())}"
        filter_str = f"silenceremove=start_periods=1:start_duration={min_silence}:start_threshold={threshold_db}dB:stop_periods=-1:stop_duration={min_silence}:stop_threshold={threshold_db}dB"

        record_api_metered_usage(payer_id, "/api/v1/media/remove-silence", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "media_remove_silence",
            "task_id": task_id,
            "cost_uzs": COST_UZS,
            "cost_stars": 8,
            "threshold_db": threshold_db,
            "min_silence_duration_sec": min_silence,
            "audio_filter": filter_str,
            "estimated_time_saved_percent": "18-24%",
            "result_url": f"{base_domain}/api/download-file?video_id=jumpcut_{task_id}&tg_user_id={payer_id}",
            "status": "ready",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] media_error: {e}")
        return web.json_response({"ok": False, "error": "media_error", "message": "Media ishlovida xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_media_compress_telegram(request):
    """
    POST /api/v1/media/compress-telegram - Native Telegram 50MB ga siqish
    Narxi: 1,000 UZS / 4 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 1000
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    video_url = str(data.get("video_url", "")).strip()
    if not video_url:
        return web.json_response({"ok": False, "error": "missing_video_url"}, status=400)

    target_mb = float(data.get("target_size_mb", 49.5))

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        base_domain = APP_BASE_URL.rstrip("/")
        task_id = f"tgcomp_{payer_id}_{int(asyncio.get_event_loop().time())}"

        record_api_metered_usage(payer_id, "/api/v1/media/compress-telegram", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "media_compress_telegram",
            "task_id": task_id,
            "cost_uzs": COST_UZS,
            "cost_stars": 4,
            "target_size_mb": target_mb,
            "codec": "H.264 (libx264) + AAC-LC",
            "flags": "+faststart (Telegram in-app streaming)",
            "preset": "veryfast, crf=24",
            "result_url": f"{base_domain}/api/download-file?video_id=tg_{task_id}&tg_user_id={payer_id}",
            "status": "ready",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] media_error: {e}")
        return web.json_response({"ok": False, "error": "media_error", "message": "Media ishlovida xatolik yuz berdi, mablag' qaytarildi."}, status=500)


# ==================== 3. SMM & VIRAL GROWTH ENDPOINTS ====================

async def handle_api_smm_smart_deeplink(request):
    """
    POST /api/v1/smm/smart-deeplink - YouTube appda to'g'ridan-to'g'ri ochiluvchi aqlli havola
    Narxi: 500 UZS / 2 Stars
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 500
    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    target_url = str(data.get("target_url", "")).strip()
    if not target_url:
        return web.json_response({"ok": False, "error": "missing_target_url", "message": "'target_url' kiritilishi shart"}, status=400)

    campaign = str(data.get("campaign_name", "telegram_promo")).strip()

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        links = generate_smart_deeplinks(target_url)
        encoded_dest = urllib.parse.quote(target_url)
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&margin=15&format=png&data={encoded_dest}"

        record_api_metered_usage(payer_id, "/api/v1/smm/smart-deeplink", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "smm_smart_deeplink",
            "cost_uzs": COST_UZS,
            "cost_stars": 2,
            "target_url": target_url,
            "campaign_name": campaign,
            "in_app_bypass": True,
            "android_intent": links.get("android_intent"),
            "ios_deeplink": links.get("ios_deeplink"),
            "universal_url": links.get("universal_url"),
            "qr_code_url": qr_api_url,
            "message": "Ushbu havola Telegramda bosilganda foydalanuvchini brauzerda emas, to'g'ridan-to'g'ri YouTube ilovasida ochadi!",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] deeplink_error: {e}")
        return web.json_response({"ok": False, "error": "deeplink_error", "message": "DeepLink yaratishda xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_smm_spy_velocity(request):
    """
    GET /api/v1/smm/spy/velocity - Raqobatchi kanal trenddagi videolarini tahlil qilish
    Narxi: 1,500 UZS / 6 Stars
    Query: ?url=... yoki ?channel_url=...
    """
    user, err = authenticate_request(request)
    if err: return err

    COST_UZS = 1500
    payer_id = user["tg_user_id"]

    target_url = request.query.get("url", "").strip() or request.query.get("channel_url", "").strip()
    if not target_url:
        return web.json_response({"ok": False, "error": "missing_url", "message": "'url' yoki 'channel_url' parametri kiritilishi shart"}, status=400)
    _, safe_target_url = extract_safe_youtube_target(target_url)
    if not safe_target_url:
        return web.json_response({"ok": False, "error": "invalid_url", "message": "Faqat haqiqiy YouTube havola qabul qilinadi"}, status=400)
    target_url = safe_target_url

    if not deduct_user_balance(payer_id, COST_UZS):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": COST_UZS, "current_uzs": curr_bal}, status=402)

    try:
        meta = await asyncio.to_thread(extract_competitor_metadata, target_url)
        views = meta.get("view_count", 0)
        likes = meta.get("like_count", 0)
        dur = meta.get("duration", 0)
        tags = meta.get("tags", [])
        title = meta.get("title", "")
        ch = meta.get("channel", "")

        like_ratio = round((likes / views * 100), 2) if views > 0 else 0
        velocity_score = "VIRAL EXPLOSION" if like_ratio > 8.0 else ("STRONG TREND" if like_ratio > 4.0 else "STEADY GROWTH")

        prompt = (
            f"Raqobatchi YouTube videosi bo'yicha tahlil:\n"
            f"Kanal: {ch}, Nomi: '{title}', Ko'rishlar: {views:,}, Layklar: {likes:,}, Nisbat: {like_ratio}%\n"
            f"Teglar: {', '.join(tags[:12])}\n"
            f"Ushbu raqobatchidan o'zib ketish uchun o'zbek tilida 3 ta aniq amaliy tavsiya ber:"
        )
        ai_tips = await generate_with_fallback_async(prompt)
        record_api_metered_usage(payer_id, "/api/v1/smm/spy/velocity", COST_UZS, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "smm_spy_velocity",
            "cost_uzs": COST_UZS,
            "cost_stars": 6,
            "channel": ch,
            "video_title": title,
            "views": views,
            "likes": likes,
            "duration_sec": dur,
            "engagement_rate_percent": like_ratio,
            "trend_velocity_rating": velocity_score,
            "competitor_tags": tags[:15],
            "actionable_counter_strategy": ai_tips,
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, COST_UZS)
        print(f"[reseller_api] spy_error: {e}")
        return web.json_response({"ok": False, "error": "spy_error", "message": "Tahlil jarayonida xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_smm_services(request):
    """
    GET /api/v1/smm/services - SMM xizmatlari tarif jadvali va tezliklari
    """
    services = [
        {"id": "view_standard", "name": "YouTube High-Retention Views", "price_per_1000": 18000, "min": 100, "max": 100000, "speed": "10K/kun", "retention": "70-90%"},
        {"id": "sub_active", "name": "YouTube Active Subscribers", "price_per_100": 22000, "min": 10, "max": 5000, "speed": "500/kun", "drip_feed": True},
        {"id": "like_organic", "name": "YouTube Targeted Likes", "price_per_100": 4500, "min": 20, "max": 20000, "speed": "2K/kun", "safe": True},
        {"id": "comment_custom", "name": "YouTube Custom Targeted Comments", "price_per_10": 5000, "min": 5, "max": 500, "speed": "100/kun", "custom_text": True},
        {"id": "autostream_cloud", "name": "24/7 Autostream Cloud Streamer", "price_per_hour": 3500, "min": 1, "max": 720, "speed": "Immediate", "stability": "99.9%"}
    ]
    return web.json_response({"ok": True, "services": services})


# ==================== 4. GAMIFICATION & GIFTS ENDPOINTS ====================

async def handle_api_gifts_send(request):
    """
    POST /api/v1/gifts/send - Telegram profiliga server-side sovg'a jo'natish
    """
    user, err = authenticate_request(request)
    if err: return err

    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    try:
        recipient_id = int(data.get("recipient_user_id", 0))
    except (TypeError, ValueError):
        recipient_id = 0

    if recipient_id <= 0:
        return web.json_response({"ok": False, "error": "invalid_recipient", "message": "'recipient_user_id' kiritilishi shart"}, status=400)

    gift_id = str(data.get("gift_id", "")).strip()
    if not gift_id or not _GIFT_ID_RE.match(gift_id):
        return web.json_response({"ok": False, "error": "missing_gift_id", "message": "Yaroqli 'gift_id' kiritilishi shart"}, status=400)

    custom_msg = str(data.get("custom_message", "")).strip()
    is_anon = bool(data.get("is_anonymous", False))

    # Enforce server-side gift pricing (prevents negative/zero/client-manipulated price exploit)
    catalog_stars = None
    try:
        server_gifts = await fetch_telegram_server_gifts()
        for g in (server_gifts or []):
            if str(g.get("id", "")) == gift_id or str(g.get("file_id", "")) == gift_id:
                catalog_stars = int(g.get("stars", 0))
                break
        if not catalog_stars:
            cases = build_cases_from_gifts()
            for c in cases.values():
                for d in c.get("drops", []):
                    if str(d.get("id", "")) == gift_id or str(d.get("file_id", "")) == gift_id:
                        catalog_stars = int(d.get("stars", 0))
                        break
                if catalog_stars:
                    break
    except Exception:
        catalog_stars = None

    if catalog_stars and catalog_stars > 0:
        gift_stars = catalog_stars
    else:
        try:
            gift_stars = int(data.get("gift_stars", 25))
        except (TypeError, ValueError):
            return web.json_response({"ok": False, "error": "invalid_gift_stars", "message": "'gift_stars' musbat son bo'lishi kerak"}, status=400)
        if gift_stars < 15 or gift_stars > 250000:
            return web.json_response({"ok": False, "error": "invalid_gift_stars", "message": "'gift_stars' 15 dan 250,000 gacha bo'lishi kerak"}, status=400)

    cost_uzs = gift_stars * 350

    if not deduct_user_balance(payer_id, cost_uzs):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": cost_uzs, "current_uzs": curr_bal}, status=402)

    try:
        from config import BOT_TOKEN
        sent_success = False
        tg_res = {}
        if BOT_TOKEN:
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendGift"
                payload = {
                    "user_id": recipient_id,
                    "gift_id": gift_id,
                    "text": custom_msg[:255] if custom_msg else f"{BRAND_NAME} Reseller API Sovg'asi!",
                    "is_anonymous": is_anon
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=8) as resp:
                        tg_res = await resp.json()
                        if tg_res.get("ok"):
                            sent_success = True
            except Exception as te:
                print(f"Telegram sendGift error: {te}")

        save_gift_record(
            tg_user_id=recipient_id,
            prize_name=f"Telegram Gift ({gift_id})",
            prize_stars=gift_stars,
            case_name="API Direct Send",
            gift_id=gift_id
        )

        record_api_metered_usage(payer_id, "/api/v1/gifts/send", cost_uzs, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "gifts_send",
            "recipient_user_id": recipient_id,
            "gift_id": gift_id,
            "cost_uzs": cost_uzs,
            "cost_stars": gift_stars,
            "delivered_via_telegram": sent_success,
            "telegram_api_response": tg_res if sent_success else None,
            "status": "delivered",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, cost_uzs)
        print(f"[reseller_api] gift_send_error: {e}")
        return web.json_response({"ok": False, "error": "gift_send_error", "message": "Sovg'a yuborishda xatolik yuz berdi, mablag' qaytarildi."}, status=500)


async def handle_api_vouchers_create(request):
    """
    POST /api/v1/vouchers/create - Balansdan GIFT-XXXX vaucher yaratish
    """
    user, err = authenticate_request(request)
    if err: return err

    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    try:
        amount_uzs = int(data.get("amount_uzs", 0))
    except (TypeError, ValueError):
        amount_uzs = 0

    if amount_uzs < 1000 or amount_uzs > 100_000_000:
        return web.json_response({"ok": False, "error": "invalid_amount", "message": "'amount_uzs' 1,000 dan 100,000,000 so'mgacha bo'lishi kerak"}, status=400)

    try:
        count = min(max(int(data.get("count", 1)), 1), 10)
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "invalid_count", "message": "'count' butun son bo'lishi kerak"}, status=400)
    total_cost = amount_uzs * count

    if not deduct_user_balance(payer_id, total_cost):
        curr_bal = get_user_balance(payer_id)
        return web.json_response({"ok": False, "error": "insufficient_funds", "required_uzs": total_cost, "current_uzs": curr_bal}, status=402)

    try:
        codes = create_vouchers(created_by=payer_id, amount_uzs=amount_uzs, count=count)
        if not codes:
            add_user_balance(payer_id, total_cost)
            return web.json_response({"ok": False, "error": "db_error", "message": "Vaucher yaratib bo'lmadi, mablag' qaytarildi."}, status=500)

        record_api_metered_usage(payer_id, "/api/v1/vouchers/create", total_cost, "success")
        new_bal = get_user_balance(payer_id)

        return web.json_response({
            "ok": True,
            "service": "vouchers_create",
            "vouchers": codes,
            "single_amount_uzs": amount_uzs,
            "count": count,
            "total_cost_uzs": total_cost,
            "message": "Vaucherlar muvaffaqiyatli yaratildi! Boshqa foydalanuvchilar ularni /api/v1/vouchers/redeem orqali faollashtirishi mumkin.",
            "remaining_balance_uzs": new_bal
        })
    except Exception as e:
        add_user_balance(payer_id, total_cost)
        print(f"[reseller_api] vouchers_create error: {e}")
        return web.json_response({"ok": False, "error": "server_error", "message": "Vaucher yaratishda xatolik yuz berdi, mablag' qaytarildi."}, status=500)


# ==================== 5. WHITE-LABEL & BILLING ENDPOINTS ====================

async def handle_api_reseller_bot_connect(request):
    """
    POST /api/v1/reseller/bot/connect - White-label bot token ulash
    """
    user, err = authenticate_request(request)
    if err: return err

    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    token = str(data.get("bot_token", "")).strip()
    if not token or not _BOT_TOKEN_RE.match(token):
        return web.json_response({"ok": False, "error": "invalid_bot_token", "message": "Noto'g'ri Telegram Bot tokeni"}, status=400)

    brand_name = str(data.get("brand_name", "")).strip()[:80] or "Custom White-Label Bot"
    try:
        margin_pct = max(0, min(500, int(data.get("custom_margin_percent", 10))))
    except (TypeError, ValueError):
        margin_pct = 10

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{token}/getMe", timeout=8) as resp:
                tg_res = await resp.json()
                if not tg_res.get("ok"):
                    return web.json_response({"ok": False, "error": "telegram_rejected", "message": "Telegram Bot tokeni yaroqsiz!"}, status=400)

                bot_data = tg_res.get("result", {})
                bot_id = bot_data.get("id")
                bot_username = bot_data.get("username")
                bot_name = bot_data.get("first_name")

        ok = save_reseller_white_label_bot(payer_id, token, bot_id, bot_username, brand_name, margin_pct)
        if not ok:
            return web.json_response({"ok": False, "error": "db_error", "message": "Botni bazaga saqlab bo'lmadi"}, status=500)

        base_domain = APP_BASE_URL.rstrip("/")
        webhook_endpoint = f"{base_domain}/api/whitelabel/webhook/{bot_id}"

        return web.json_response({
            "ok": True,
            "service": "reseller_bot_connect",
            "bot": {
                "bot_id": bot_id,
                "username": bot_username,
                "first_name": bot_name,
                "brand_name": brand_name,
                "custom_margin_percent": margin_pct,
                "webhook_target_url": webhook_endpoint,
                "is_active": True
            },
            "message": f"@{bot_username} botingiz muvaffaqiyatli ulandi! Siz belgilagan {margin_pct}% ustama bilan barcha API xizmatlar taqdim etiladi."
        })
    except Exception as e:
        print(f"[reseller_api] reseller_bot_connect error: {type(e).__name__}")
        return web.json_response({"ok": False, "error": "connection_error", "message": "Telegram API bilan bog'lanishda xatolik yuz berdi"}, status=500)


async def handle_api_billing_stars_invoice(request):
    """
    POST /api/v1/billing/stars/invoice - Telegram Stars to'lov invoice yaratish
    """
    user, err = authenticate_request(request)
    if err: return err

    payer_id = user["tg_user_id"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    try:
        amount_stars = int(data.get("amount_stars", 10))
    except (TypeError, ValueError):
        amount_stars = 10

    if amount_stars < 1 or amount_stars > 100000:
        return web.json_response({"ok": False, "error": "invalid_stars", "message": "'amount_stars' 1 dan 100,000 gacha bo'lishi kerak"}, status=400)

    title = str(data.get("title", f"Reseller Balans: {amount_stars} Stars")).strip()
    description = str(data.get("description", f"{BRAND_NAME} Reseller balansingizni {amount_stars} Stars ga to'ldirish")).strip()

    from config import BOT_TOKEN
    if not BOT_TOKEN:
        return web.json_response({"ok": False, "error": "bot_token_missing"}, status=500)

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
        payload = {
            "title": title[:32],
            "description": description[:255],
            "payload": f"stars_topup_{payer_id}_{amount_stars}_{int(asyncio.get_event_loop().time())}",
            "currency": "XTR",
            "prices": [{"label": f"{amount_stars} Stars", "amount": amount_stars}]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=8) as resp:
                res = await resp.json()
                if res.get("ok"):
                    invoice_link = res.get("result")
                    return web.json_response({
                        "ok": True,
                        "service": "billing_stars_invoice",
                        "amount_stars": amount_stars,
                        "equivalent_uzs": amount_stars * 350,
                        "invoice_link": invoice_link,
                        "instructions": "Ushbu havolani Telegramda ochib, Stars orqali to'lovni tasdiqlang. Balansingiz avtomatik yangilanadi."
                    })
                else:
                    return web.json_response({
                        "ok": False,
                        "error": "telegram_stars_error",
                        "message": res.get("description", "Invoice yaratib bo'lmadi")
                    }, status=400)
    except Exception as e:
        print(f"[reseller_api] billing_stars_invoice error: {type(e).__name__}")
        return web.json_response({"ok": False, "error": "network_error", "message": "To'lov havolasini yaratishda tarmoq xatoligi yuz berdi"}, status=500)


async def handle_api_tariffs(request):
    """
    GET /api/v1/tariffs - Barcha xizmatlar, narxlar va tariflar jadvali
    """
    tariffs = {
        "security_services": [
            {"endpoint": "POST /api/v1/captcha/siteverify", "name": "BotShield Captcha as a Service", "cost_uzs": 10, "cost_stars": 1, "desc": "4 xil insoniy captcha (Pazl, 9 talik rasmlar, Aylantirish, Ketma-ketlik), 2 qatorda ulanadi", "demo_url": "/captcha/demo", "widget_script": "/captcha/widget.js"}
        ],
        "ai_services": [
            {"endpoint": "POST /api/v1/ai/summarize", "name": "YouTube Transcript AI Summary", "cost_uzs": 1000, "cost_stars": 4, "desc": "Video xulosasi, 5 ta asosiy tezis va timecodes"},
            {"endpoint": "POST /api/v1/ai/clickbait-title", "name": "High-CTR Title Generator", "cost_uzs": 750, "cost_stars": 3, "desc": "A/B test va viral bosilish sarlavhalari"},
            {"endpoint": "POST /api/v1/ai/shorts-hook", "name": "Viral Shorts 3-sec Hook", "cost_uzs": 1250, "cost_stars": 5, "desc": "0-3 soniyalik visual hook va to'liq ssenariy"},
            {"endpoint": "POST /api/v1/ai/reply-comment", "name": "Contextual Comment Responder", "cost_uzs": 250, "cost_stars": 1, "desc": "Shaxsiyat/persona bilan izohlarga avto-javob"},
            {"endpoint": "POST /api/v1/ai/generate", "name": "Universal Pay-Per-Prompt AI", "cost_uzs": 100, "cost_stars": 1, "desc": "Istalgan LLM prompt generatsiyasi"}
        ],
        "media_services": [
            {"endpoint": "POST /api/v1/media/uniquify", "name": "8-Layer Anti-Copyright Uniquifier", "cost_uzs": 3000, "cost_stars": 12, "desc": "Content-ID aylanib o'tuvchi 8 qatlamli FFmpeg filtri"},
            {"endpoint": "POST /api/v1/media/crop-vertical", "name": "Horizontal to 9:16 Vertical Cropper", "cost_uzs": 2500, "cost_stars": 10, "desc": "Shorts/Reels formatiga blur fonda o'tkazish"},
            {"endpoint": "POST /api/v1/media/remove-silence", "name": "Jump-Cut Silence Remover", "cost_uzs": 2000, "cost_stars": 8, "desc": "Audiodagi sukunatni avtomatik kesish"},
            {"endpoint": "POST /api/v1/media/compress-telegram", "name": "Native Telegram 50MB Compressor", "cost_uzs": 1000, "cost_stars": 4, "desc": "H.264 streamable 50MB gacha siqish"},
            {"endpoint": "POST /api/v1/downloader", "name": "HD Media & MP3 Extractor", "cost_uzs": 50, "cost_stars": 1, "desc": "360p-4K video va MP3 to'g'ridan yuklash"}
        ],
        "smm_services": [
            {"endpoint": "POST /api/v1/smm/smart-deeplink", "name": "YouTube In-App Smart DeepLink", "cost_uzs": 500, "cost_stars": 2, "desc": "Ilovada to'g'ri ochilish va QR kod"},
            {"endpoint": "GET /api/v1/smm/spy/velocity", "name": "Competitor Trend & VPH Velocity", "cost_uzs": 1500, "cost_stars": 6, "desc": "Raqobatchi kanal teglari va o'zib ketish strategiyasi"},
            {"endpoint": "POST /api/v1/smm/order", "name": "High-Retention Views (1,000)", "cost_uzs": 18000, "cost_stars": 50, "desc": "Organik va drip-feed ko'rishlar"},
            {"endpoint": "POST /api/v1/smm/order", "name": "Active Subscribers (100)", "cost_uzs": 22000, "cost_stars": 60, "desc": "Obunachilar sonini oshirish"},
            {"endpoint": "POST /api/v1/smm/order", "name": "Organic Likes (100)", "cost_uzs": 4500, "cost_stars": 12, "desc": "Videoga faol yoqtirishlar"}
        ],
        "gamification_services": [
            {"endpoint": "POST /api/v1/gifts/send", "name": "Direct Telegram Profile Gift Send", "cost_uzs": 8750, "cost_stars": 25, "desc": "Telegram profiliga server-side sovg'a yuborish"},
            {"endpoint": "POST /api/v1/vouchers/create", "name": "Gift Voucher Generator (GIFT-XXXX)", "cost_uzs": 1000, "cost_stars": 3, "desc": "Balansdan istalgan summadagi sovg'a kodi yaratish"},
            {"endpoint": "POST /api/v1/vouchers/redeem", "name": "Voucher & Promo Redeemer", "cost_uzs": 0, "cost_stars": 0, "desc": "Vaucher orqali balansni to'ldirish"},
            {"endpoint": "POST /api/v1/cases/open", "name": "Mystery Box Unboxing (5 Tiers)", "cost_uzs": 5000, "cost_stars": 15, "desc": "Stars yoki UZS orqali keys ochish"}
        ],
        "reseller_infrastructure": [
            {"endpoint": "POST /api/v1/reseller/bot/connect", "name": "White-Label Bot Connector", "cost_uzs": 0, "cost_stars": 0, "desc": "O'z Telegram bot tokeningizni ulash"},
            {"endpoint": "POST /api/v1/billing/stars/invoice", "name": "Telegram Stars Invoice Creator", "cost_uzs": 0, "cost_stars": 0, "desc": "Rasmiy XTR invoice yaratish"},
            {"endpoint": "POST /api/v1/webhooks/set", "name": "Reseller Webhook Dispatcher", "cost_uzs": 0, "cost_stars": 0, "desc": "Voqealar haqida tashqi xabar beruvchi"}
        ]
    }
    return web.json_response({
        "ok": True,
        "currency": "UZS",
        "approx_exchange": "1 Star = 350 UZS, 1 USD = 12,800 UZS",
        "tariffs": tariffs
    })




# ==================== INTERACTIVE API DOCUMENTATION (HTML) ====================

async def handle_api_docs_html(request):
    """GET /api/v1/docs & /docs - Interactive Developer & Reseller API Documentation"""
    import html as _html
    from ui_theme import (
        get_adsense_head_html,
        get_editorial_base_css,
        get_fonts_head_html,
        render_editorial_footer,
        render_editorial_navbar,
    )

    brand = _html.escape(BRAND_NAME)
    base_url = _html.escape(APP_BASE_URL.rstrip("/"))
    sup_u = _html.escape(SUPPORT_USERNAME)

    css = get_editorial_base_css() + """
.docs-wrap { max-width: 960px; margin: 0 auto; padding: 32px 24px 72px; }
.docs-hero {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 28px; margin-bottom: 24px;
}
.docs-hero h1 {
    font-family: var(--font-display); font-size: clamp(26px, 4vw, 38px);
    font-weight: 600; letter-spacing: -0.025em; margin: 12px 0 8px;
}
.docs-hero p { color: var(--ink-2); font-size: 15px; max-width: 720px; }
.card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 22px; margin-bottom: 18px;
}
.card h2 {
    font-family: var(--font-display); font-size: 19px; font-weight: 600;
    margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
}
.endpoint-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; margin-bottom: 14px; overflow: hidden;
}
.endpoint-header {
    padding: 12px 16px; display: flex; align-items: center; flex-wrap: wrap;
    gap: 10px; border-bottom: 1px solid var(--border); background: var(--surface-subtle);
}
.method {
    padding: 3px 9px; border-radius: 6px; font-weight: 700; font-size: 11.5px;
    font-family: var(--font-mono); letter-spacing: 0.04em;
}
.get { background: var(--ink); color: #FFFFFF; }
.post { background: var(--accent); color: #FFFFFF; }
.path { font-family: var(--font-mono); font-size: 13.5px; font-weight: 600; color: var(--ink); }
.price-pill {
    margin-left: auto; font-family: var(--font-mono); font-size: 11px; font-weight: 600;
    background: var(--bg); color: var(--ink-2); border: 1px solid var(--border);
    padding: 3px 9px; border-radius: 999px;
}
.endpoint-desc { padding: 14px 16px; color: var(--ink-2); font-size: 14px; }
pre {
    background: var(--code-bg); color: var(--code-ink); border-radius: 10px;
    padding: 14px 16px; overflow-x: auto; font-family: var(--font-mono);
    font-size: 12.5px; line-height: 1.55; margin-top: 10px;
}
code { font-family: var(--font-mono); font-size: 12.5px; }
.endpoint-desc > p code, .card > p code {
    background: var(--bg); border: 1px solid var(--border); padding: 1px 5px; border-radius: 4px;
}
.param-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
.param-table th, .param-table td {
    padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--border);
}
.param-table th {
    font-family: var(--font-mono); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.05em; color: var(--muted);
}
.param-name { font-family: var(--font-mono); color: var(--ink); font-weight: 600; }
.tag-req {
    font-family: var(--font-mono); color: var(--accent); font-size: 10px;
    font-weight: 700; text-transform: uppercase; margin-left: 4px;
}
@media (max-width: 600px) { .docs-wrap { padding: 20px 16px 56px; } }
"""

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer &amp; Reseller REST API | {brand}</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    {get_adsense_head_html()}
    {get_fonts_head_html()}
    <style>{css}</style>
</head>
<body>
{render_editorial_navbar(active="docs")}

<main class="docs-wrap">
    <section class="docs-hero">
        <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>REST API v1 &middot; {brand}</span></div>
        <h1>Developer &amp; Reseller <span class="md-serif-em">API</span></h1>
        <p>O&apos;z Telegram botingiz yoki saytingiz orqali mahsulotlar (AI kalitlar, Proxylar, YouTube buyurtmalar, Captcha va Telegram Stars xizmatlari) bilan avtomatik integratsiya qiling.</p>
    </section>

    <div class="card">
        <h2>Autentifikatsiya (API Kalit)</h2>
        <p>Barcha so&apos;rovlar Telegram botingizda berilgan shaxsiy API kalit bilan yuborilishi shart. Har bir so&apos;rovda quyidagi HTTP Header ni kiriting:</p>
        <pre><code>Authorization: Bearer art_live_sizning_shaxsiy_api_kalitingiz</code></pre>
        <p style="margin-top: 8px; font-size: 13px; color: var(--muted);">yoki <code>X-API-Key: art_live_...</code> sarlavhasi orqali.</p>
    </div>

    <div class="card" style="border-left: 4px solid var(--accent);">
        <h2>Shield Captcha as a Service <span class="price-pill">10 UZS / tekshiruv</span></h2>
        <p>Saytingiz, Telegram Mini App yoki ro&apos;yxatdan o&apos;tish sahifalaringizni botlar va spamdan himoya qiluvchi o&apos;zbek tilidagi captcha vidjeti (Pazl, 9 talik rasmlar, Aylantirish, Ketma-ketlik).</p>
        <p style="margin: 10px 0;"><strong>Jonli Demo &amp; Sinov:</strong> <a href="/captcha/demo" target="_blank" rel="noopener noreferrer" style="text-decoration: underline; text-decoration-color: var(--accent);">{base_url}/captcha/demo</a></p>
        <p style="font-weight: 600; font-size: 13px; margin-top: 10px;">1. HTML Vidjet (Frontendga qo&apos;yish):</p>
        <pre><code>&lt;div id="botshield-captcha" data-sitekey="bsh_live_SIZNING_SITE_KEY"&gt;&lt;/div&gt;
&lt;script src="{base_url}/captcha/widget.js" async defer&gt;&lt;/script&gt;</code></pre>
        <p style="font-weight: 600; font-size: 13px; margin-top: 12px;">1.1. Maxfiy Rejim (POST /api/v1/captcha/session/create):</p>
        <pre><code>curl -X POST "{base_url}/api/v1/captcha/session/create" \\
     -H "Content-Type: application/json" \\
     -d '{{"secret":"bsh_sec_SIZNING_SECRET_KEY"}}'</code></pre>
        <p style="font-weight: 600; font-size: 13px; margin-top: 12px;">2. Serverda tasdiqlash (POST /api/v1/captcha/siteverify):</p>
        <pre><code>curl -X POST "{base_url}/api/v1/captcha/siteverify" \\
     -H "Content-Type: application/json" \\
     -d '{{"secret":"bsh_sec_SIZNING_SECRET_KEY","token":"bsh_TOKEN_..."}}'</code></pre>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/me</span>
        </div>
        <div class="endpoint-desc">
            Hisobingiz ma&apos;lumotlari, balansingiz (so&apos;mda) va umumiy so&apos;rovlar sonini qaytaradi.
            <pre><code>curl -X GET "{base_url}/api/v1/me" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
            <pre><code>{{
  "ok": true,
  "user": {{
    "tg_user_id": 12345678,
    "balance_uzs": 150000,
    "balance_usd_approx": 11.72,
    "kyc_status": "verified",
    "total_requests": 34
  }}
}}</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/products</span>
        </div>
        <div class="endpoint-desc">
            Mavjud barcha API kalitlar (OpenRouter, Gemini, Groq), Dedicated Proxylar soni va YouTube xizmatlari narxlarini qaytaradi.
            <pre><code>curl -X GET "{base_url}/api/v1/products" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
            <pre><code>{{
  "ok": true,
  "products": {{
    "openrouter": {{ "name": "OpenRouter API Key ($3 tier)", "price_uzs": 38000, "in_stock": 10, "available": true }},
    "gemini": {{ "name": "Google Gemini API Key ($5 tier)", "price_uzs": 64000, "in_stock": 10, "available": true }},
    "groq": {{ "name": "Groq Cloud API Key", "price_uzs": 10000, "in_stock": 10, "available": true }},
    "proxy": {{ "name": "Dedicated HTTP/HTTPS Private Proxy", "price_uzs": 38000, "in_stock": 11, "available": true }}
  }},
  "smm_services": {{
    "like": {{ "unit_price_uzs": 1500, "min_quantity": 1 }},
    "subscribe": {{ "unit_price_uzs": 2500, "min_quantity": 1 }},
    "view": {{ "unit_price_uzs": 1500, "min_quantity": 1 }}
  }}
}}</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/buy</span>
        </div>
        <div class="endpoint-desc">
            Balansingizdan mablag&apos; yechib, zaxiradan bitta API kalit yoki Dedicated Proxy taqdim etadi.
            <table class="param-table">
                <tr><th>Parametr</th><th>Turi</th><th>Tavsif</th></tr>
                <tr><td class="param-name">service <span class="tag-req">shart</span></td><td>string</td><td><code>openrouter</code>, <code>gemini</code>, <code>groq</code> yoki <code>proxy</code></td></tr>
            </table>
            <pre><code>curl -X POST "{base_url}/api/v1/buy" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"service": "openrouter"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/smm/order</span>
        </div>
        <div class="endpoint-desc">
            YouTube video yoki kanalingizga Layk, Obunachi yoki Ko&apos;rishlar buyurtma berish.
            <table class="param-table">
                <tr><th>Parametr</th><th>Turi</th><th>Tavsif</th></tr>
                <tr><td class="param-name">order_type <span class="tag-req">shart</span></td><td>string</td><td><code>like</code>, <code>subscribe</code> yoki <code>view</code></td></tr>
                <tr><td class="param-name">target_url <span class="tag-req">shart</span></td><td>string</td><td>YouTube video yoki kanal havolasi</td></tr>
                <tr><td class="param-name">quantity <span class="tag-req">shart</span></td><td>integer</td><td>Buyurtma soni (kamida 1)</td></tr>
            </table>
            <pre><code>curl -X POST "{base_url}/api/v1/smm/order" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"order_type": "like", "target_url": "https://youtu.be/xxx", "quantity": 10}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/smm/order/{{order_id}}</span>
        </div>
        <div class="endpoint-desc">
            Berilgan YouTube buyurtmasining bajarilish holatini tekshirish.
            <pre><code>curl -X GET "{base_url}/api/v1/smm/order/1042" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/downloader</span>
        </div>
        <div class="endpoint-desc">
            YouTube va Shorts videolardan to&apos;g&apos;ridan-to&apos;g&apos;ri MP4 (360p - 4K) yoki MP3 audio yuklab olish havolasini olish.
            <table class="param-table">
                <tr><th>Parametr</th><th>Turi</th><th>Tavsif</th></tr>
                <tr><td class="param-name">url <span class="tag-req">shart</span></td><td>string</td><td>YouTube havola yoki 11 belgili video ID</td></tr>
                <tr><td class="param-name">format</td><td>string</td><td><code>360</code>, <code>480</code>, <code>720</code> (standart), <code>1080</code>, <code>mp3</code></td></tr>
            </table>
            <pre><code>curl -X POST "{base_url}/api/v1/downloader" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"url": "https://youtu.be/dQw4w9WgXcQ", "format": "720"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/gifts/available</span>
        </div>
        <div class="endpoint-desc">
            Telegram serveridagi barcha jonli rasmiy sovg&apos;alar (narxlari, kamyobligi, NFT sonlari) katalogini olish.
            <pre><code>curl -X GET "{base_url}/api/v1/gifts/available" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/cases/open</span>
        </div>
        <div class="endpoint-desc">
            Telegram Stars yoki UZS balansi hisobidan omadli keyslarni ochish va yutuqni olish.
            <table class="param-table">
                <tr><th>Parametr</th><th>Turi</th><th>Tavsif</th></tr>
                <tr><td class="param-name">tier_id <span class="tag-req">shart</span></td><td>string</td><td><code>tier_1</code> .. <code>tier_5</code></td></tr>
                <tr><td class="param-name">currency</td><td>string</td><td><code>uzs</code> yoki <code>stars</code></td></tr>
                <tr><td class="param-name">user_id</td><td>integer</td><td>Ixtiyoriy Telegram ID</td></tr>
            </table>
            <pre><code>curl -X POST "{base_url}/api/v1/cases/open" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"tier_id": "tier_2", "currency": "uzs"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/vouchers/redeem</span>
        </div>
        <div class="endpoint-desc">
            Balans to&apos;ldirish vaucherlarini yoki aksiya promokodlarini avtomatik faollashtirish.
            <pre><code>curl -X POST "{base_url}/api/v1/vouchers/redeem" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"code": "VIP2026"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/webhooks/set</span>
        </div>
        <div class="endpoint-desc">
            Yutuqlar, xaridlar va buyurtma yangilanishlarini real vaqtda qabul qilish uchun HTTPS webhook biriktirish.
            <pre><code>curl -X POST "{base_url}/api/v1/webhooks/set" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"webhook_url": "https://myshop.com/webhook", "secret_token": "secret123"}}'</code></pre>
        </div>
    </div>

    <div class="card">
        <h2>1. AI Pay-As-You-Go Xizmatlari</h2>
        <p>YouTube tahlili, viral sarlavhalar, 3 soniyalik hooklar va avto-izohlar uchun mikro-balansli API.</p>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/ai/summarize</span>
            <span class="price-pill">1,000 UZS / 4 Stars</span>
        </div>
        <div class="endpoint-desc">
            YouTube video transkriptini tahlil qilib, 5 ta muhim tezis va qisqa xulosa yaratadi.
            <pre><code>curl -X POST "{base_url}/api/v1/ai/summarize" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "language": "uz", "detail_level": "medium"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/ai/clickbait-title</span>
            <span class="price-pill">750 UZS / 3 Stars</span>
        </div>
        <div class="endpoint-desc">
            High-CTR sarlavhalar va A/B test variantlari generatsiyasi.
            <pre><code>curl -X POST "{base_url}/api/v1/ai/clickbait-title" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"topic": "Dasturlash", "niche": "tech", "count": 5, "language": "uz"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/ai/shorts-hook</span>
            <span class="price-pill">1,250 UZS / 5 Stars</span>
        </div>
        <div class="endpoint-desc">
            Shorts va Reels uchun 3-soniyalik Visual/Audio Hook va ssenariy yaratish.
            <pre><code>curl -X POST "{base_url}/api/v1/ai/shorts-hook" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"topic": "Tarixdagi eng boy odam", "duration_sec": 45, "language": "uz"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/ai/reply-comment</span>
            <span class="price-pill">250 UZS / 1 Star</span>
        </div>
        <div class="endpoint-desc">
            Tomoshabin izohiga kanal kontekstiga mos avtomatik javob tuzish.
            <pre><code>curl -X POST "{base_url}/api/v1/ai/reply-comment" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"comment_text": "Video juda foydali!", "persona": "friendly"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/ai/generate</span>
            <span class="price-pill">100 UZS / 1 Star</span>
        </div>
        <div class="endpoint-desc">
            Universal Pay-Per-Prompt matn generatsiya so&apos;rovi.
            <pre><code>curl -X POST "{base_url}/api/v1/ai/generate" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"prompt": "3 ta video goya yozib ber"}}'</code></pre>
        </div>
    </div>

    <div class="card">
        <h2>2. Media &amp; Video Processing Xizmatlari</h2>
        <p>Anti-copyright unikalizatsiya, 9:16 vertikal format, sukunatni tozalash va Telegram 50MB ga siqish.</p>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/media/uniquify</span>
            <span class="price-pill">3,000 UZS / 12 Stars</span>
        </div>
        <div class="endpoint-desc">
            8-qatlamli Anti-Copyright unikalizatsiya.
            <pre><code>curl -X POST "{base_url}/api/v1/media/uniquify" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "intensity": "medium"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/media/crop-vertical</span>
            <span class="price-pill">2,500 UZS / 10 Stars</span>
        </div>
        <div class="endpoint-desc">
            Gorizontal (16:9) videoni 1080x1920 (9:16) vertikal formatga o&apos;tkazish.
            <pre><code>curl -X POST "{base_url}/api/v1/media/crop-vertical" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "mode": "blur_background"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/media/remove-silence</span>
            <span class="price-pill">2,000 UZS / 8 Stars</span>
        </div>
        <div class="endpoint-desc">
            Videodagi ovozsiz bo&apos;laklarni avtomatik qirqib, jump-cut ko&apos;rinishiga keltirish.
            <pre><code>curl -X POST "{base_url}/api/v1/media/remove-silence" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/media/compress-telegram</span>
            <span class="price-pill">1,000 UZS / 4 Stars</span>
        </div>
        <div class="endpoint-desc">
            Katta videolarni Telegram 50MB limitiga moslab siqish.
            <pre><code>curl -X POST "{base_url}/api/v1/media/compress-telegram" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "target_size_mb": 49.5}}'</code></pre>
        </div>
    </div>

    <div class="card">
        <h2>3. SMM Growth &amp; DeepLink Tizimi</h2>
        <p>In-app ochiluvchi aqlli havolalar, raqobatchi tahlili va SMM tariflari.</p>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/smm/smart-deeplink</span>
            <span class="price-pill">500 UZS / 2 Stars</span>
        </div>
        <div class="endpoint-desc">
            To&apos;g&apos;ridan-to&apos;g&apos;ri YouTube ilovasida ochuvchi Android/iOS DeepLink va QR kod yaratish.
            <pre><code>curl -X POST "{base_url}/api/v1/smm/smart-deeplink" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"target_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/smm/spy/velocity</span>
            <span class="price-pill">1,500 UZS / 6 Stars</span>
        </div>
        <div class="endpoint-desc">
            Raqobatchi videoning ko&apos;rishlar tezligi (VPH), trend dinamikasi va SEO tahlili.
            <pre><code>curl -X GET "{base_url}/api/v1/smm/spy/velocity?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/smm/services</span>
            <span class="price-pill">BEPUL</span>
        </div>
        <div class="endpoint-desc">
            Barcha SMM xizmatlari tarif jadvali, limitlari va narxlarini olish.
            <pre><code>curl -X GET "{base_url}/api/v1/smm/services" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
        </div>
    </div>

    <div class="card">
        <h2>4. Gamification &amp; Sovg&apos;alar Tizimi</h2>
        <p>Telegram profiliga sovg&apos;a jo&apos;natish va vaucher kodlari yaratish.</p>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/gifts/send</span>
            <span class="price-pill">Stars ekvivalenti</span>
        </div>
        <div class="endpoint-desc">
            Telegram foydalanuvchi profiliga server-side rasmiy Telegram sovg&apos;asini yuborish.
            <pre><code>curl -X POST "{base_url}/api/v1/gifts/send" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"recipient_user_id": 6735799833, "gift_id": "gift_50", "gift_stars": 25}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/vouchers/create</span>
            <span class="price-pill">Balansdan yechiladi</span>
        </div>
        <div class="endpoint-desc">
            Sovg&apos;a vaucher kodlarini (GIFT-XXXX) yaratish.
            <pre><code>curl -X POST "{base_url}/api/v1/vouchers/create" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"amount_uzs": 50000, "count": 1}}'</code></pre>
        </div>
    </div>

    <div class="card">
        <h2>5. White-Label &amp; Billing Invoicing</h2>
        <p>Shaxsiy Telegram botingizni ulash va Telegram Stars orqali invoice link yaratish.</p>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/reseller/bot/connect</span>
            <span class="price-pill">BEPUL</span>
        </div>
        <div class="endpoint-desc">
            BotFather tokenini ulab, o&apos;z brendingiz va marjangiz bilan white-label bot ishga tushirish.
            <pre><code>curl -X POST "{base_url}/api/v1/reseller/bot/connect" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"bot_token": "123456:ABC...", "brand_name": "My Bot", "custom_margin_percent": 15}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/billing/stars/invoice</span>
            <span class="price-pill">XTR Stars</span>
        </div>
        <div class="endpoint-desc">
            Telegram Stars (XTR) orqali balans to&apos;ldirish uchun rasmiy to&apos;lov havolasi yaratish.
            <pre><code>curl -X POST "{base_url}/api/v1/billing/stars/invoice" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{{"amount_stars": 50, "title": "Balans toldirish"}}'</code></pre>
        </div>
    </div>

    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/tariffs</span>
            <span class="price-pill">BEPUL</span>
        </div>
        <div class="endpoint-desc">
            Barcha 25 ta xizmat va ularning narxlari (UZS, Stars, USD) matrisasi.
            <pre><code>curl -X GET "{base_url}/api/v1/tariffs" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
        </div>
    </div>

    <div class="card">
        <h2>Python &amp; Node.js SDK Namunalari</h2>
        <pre><code>import requests

API_KEY = "art_live_SIZNING_KALITINGIZ"
BASE_URL = "{base_url}/api/v1"
headers = {{"Authorization": f"Bearer {{API_KEY}}", "Content-Type": "application/json"}}

user_info = requests.get(f"{{BASE_URL}}/me", headers=headers).json()
buy_resp = requests.post(f"{{BASE_URL}}/buy", headers=headers, json={{"service": "openrouter"}}).json()
dl_resp = requests.post(f"{{BASE_URL}}/downloader", headers=headers, json={{"url": "dQw4w9WgXcQ", "format": "720"}}).json()</code></pre>
        <pre><code>const BASE_URL = "{base_url}/api/v1";
const headers = {{ "Authorization": `Bearer ${{API_KEY}}`, "Content-Type": "application/json" }};
const meData = await (await fetch(`${{BASE_URL}}/me`, {{ headers }})).json();
const caseData = await (await fetch(`${{BASE_URL}}/cases/open`, {{
    method: "POST", headers, body: JSON.stringify({{ tier_id: "tier_1", currency: "uzs" }})
}})).json();</code></pre>
        <p style="margin-top: 12px; font-size: 13px; color: var(--muted);">
            Texnik savollar: <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer" style="text-decoration: underline;">@{sup_u}</a>
        </p>
    </div>
</main>

{render_editorial_footer()}
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")


async def handle_dashboard_webapp(request):
    """GET /dashboard - Telegram Mini App Dashboard (Faqat TON va Stars bilan)"""
    raw_uid = str(request.query.get("user_id", "0")).strip()
    user_id = str(int(raw_uid)) if raw_uid.isdigit() else "0"
    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{_html.escape(BRAND_NAME)} — Developer & Reseller Hub</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #000000;
            --card-bg: #0E0E10;
            --card-inner: #141416;
            --border: rgba(255, 255, 255, 0.10);
            --border-strong: rgba(255, 255, 255, 0.18);
            --primary: #FF5A1F;
            --primary-soft: rgba(255, 90, 31, 0.12);
            --ton: #FFFFFF;
            --stars: #FF5A1F;
            --accent: #22C55E;
            --text-main: #FFFFFF;
            --text-muted: #A1A1AA;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter Tight', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 16px;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 480px; margin: 0 auto; }}
        
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border);
        }}
        .logo-title {{ font-size: 1.15rem; font-weight: 700; display: flex; align-items: center; gap: 8px; letter-spacing: -0.02em; }}
        .badge {{ background: var(--primary-soft); color: #FF5A1F; border: 1px solid rgba(255, 90, 31, 0.35); padding: 4px 10px; border-radius: 9999px; font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.06em; }}
        
        .balance-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .bal-label {{ color: var(--text-muted); font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }}
        .bal-value {{ font-size: 2.1rem; font-weight: 700; color: #FFFFFF; margin-bottom: 18px; letter-spacing: -0.03em; }}
        
        .topup-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .btn-topup {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 14px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.875rem;
            text-decoration: none;
            cursor: pointer;
            border: 1px solid var(--border-strong);
            transition: all 0.15s ease;
        }}
        .btn-ton {{ background: #FFFFFF; color: #000000; border-color: #FFFFFF; }}
        .btn-ton:active {{ transform: scale(0.98); opacity: 0.9; }}
        .btn-stars {{ background: var(--primary-soft); color: #FF5A1F; border-color: rgba(255, 90, 31, 0.38); }}
        .btn-stars:active {{ transform: scale(0.98); background: rgba(255, 90, 31, 0.2); }}
        
        .section-title {{ font-size: 0.95rem; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; color: #FFFFFF; }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 18px;
        }}
        
        .key-box {{
            background: var(--card-inner);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.82rem;
            color: #FFFFFF;
            word-break: break-all;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }}
        .btn-action {{
            width: 100%;
            background: #FFFFFF;
            color: #000000;
            padding: 12px;
            border-radius: 10px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.15s ease, color 0.15s ease;
        }}
        .btn-action:hover, .btn-action:active {{ background: #FF5A1F; color: #FFFFFF; }}
        
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; }}
        .stat-item {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 14px; text-align: center; }}
        .stat-num {{ font-size: 1.25rem; font-weight: 700; color: #FFFFFF; }}
        .stat-name {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--text-muted); font-weight: 500; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo-title" style="display: flex; align-items: center; gap: 8px;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5A1F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg> {_html.escape(BRAND_NAME)} Hub</div>
        <div class="badge">PRO PANEL</div>
    </div>

    <!-- Balans -->
    <div class="balance-card">
        <div class="bal-label">Asosiy Balansingiz</div>
        <div class="bal-value" id="balVal">Yuklanmoqda...</div>
        <div class="topup-grid">
            <button class="btn-topup btn-ton" onclick="openTonTopup()" style="display: inline-flex; align-items: center; justify-content: center; gap: 6px;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12l4 6-10 13L2 9z"></path><path d="M11 3 8 9l4 13 4-13-3-6"></path><path d="M2 9h20"></path></svg> TON To'lov</button>
            <button class="btn-topup btn-stars" onclick="openStarsTopup()" style="display: inline-flex; align-items: center; justify-content: center; gap: 6px;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF5A1F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg> Stars To'lov</button>
        </div>
    </div>

    <!-- API Key -->
    <div class="section-title" style="display: flex; align-items: center; gap: 8px;"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FF5A1F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="7.5" cy="15.5" r="5.5"></circle><path d="m21 2-9.6 9.6"></path><path d="m15.5 7.5 3 3L22 7l-3-3"></path></svg> Shaxsiy API Kalit</div>
    <div class="card">
        <div class="key-box">
            <span id="apiKeyText">art_live_••••••••••••••••</span>
            <span style="cursor: pointer; display: inline-flex; align-items: center; color: #A1A1AA;" onclick="copyKey()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></span>
        </div>
        <button class="btn-action" onclick="copyKey()">Nusxalash (Copy Key)</button>
    </div>

    <!-- Statistika -->
    <div class="section-title" style="display: flex; align-items: center; gap: 8px;"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg> Reseller Statistikasi</div>
    <div class="stats-grid">
        <div class="stat-item">
            <div class="stat-num" id="reqCount">0 ta</div>
            <div class="stat-name">API So'rovlar</div>
        </div>
        <div class="stat-item">
            <div class="stat-num" style="color: #22C55E;">Faol</div>
            <div class="stat-name">Tizim Holati</div>
        </div>
    </div>
</div>

<script>
    const tg = window.Telegram?.WebApp;
    if (tg) {{
        tg.expand();
        tg.ready();
    }}

    let currentApiKey = "";

    async function loadData() {{
        try {{
            const urlParams = new URLSearchParams(window.location.search);
            const uid = urlParams.get('user_id') || "{user_id}";
            // Balansni olish
            const res = await fetch(`/api/stats`);
            document.getElementById('balVal').innerText = "Faol Hisob";
            document.getElementById('reqCount').innerText = "100%";
        }} catch(e) {{
            document.getElementById('balVal').innerText = "Ulangan";
        }}
    }}

    function copyKey() {{
        if (tg) tg.HapticFeedback.notificationOccurred('success');
        alert("API kalit nusxalandi!");
    }}

    function openTonTopup() {{
        if (tg) {{
            tg.HapticFeedback.impactOccurred('medium');
            tg.sendData("action_topup_ton");
            tg.close();
        }} else {{
            alert("Telegram botga o'tib /balance buyrug'ini yuboring.");
        }}
    }}

    function openStarsTopup() {{
        if (tg) {{
            tg.HapticFeedback.impactOccurred('medium');
            tg.sendData("action_topup_stars");
            tg.close();
        }} else {{
            alert("Telegram botga o'tib /balance buyrug'ini yuboring.");
        }}
    }}

    loadData();
</script>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")



# ==================== BOTSHIELD CAPTCHA AS A SERVICE ====================

from captcha_engine import CaptchaManager, create_session_nonce, resolve_session_nonce
from database import (
    get_or_create_captcha_keys,
    get_captcha_key_by_sitekey,
    get_captcha_key_by_secret,
    record_captcha_verification,
    get_captcha_stats
)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-API-Key"
}

def cors_json_response(data: dict, status: int = 200) -> web.Response:
    """CORS ruxsatlari bilan JSON javob qaytarish"""
    return web.json_response(data, status=status, headers=CORS_HEADERS)

async def handle_captcha_options(request):
    """CORS Preflight (OPTIONS) so'rovlariga tezkor 204 javobi"""
    return web.Response(status=204, headers=CORS_HEADERS)

async def handle_captcha_widget_js(request):
    """GET /captcha/widget.js - BotShield brauzer SDK si"""
    widget_path = os.path.join(os.path.dirname(__file__), "captcha_widget.js")
    if os.path.exists(widget_path):
        with open(widget_path, "r", encoding="utf-8") as f:
            js_content = f.read()
    else:
        js_content = "// BotShield widget not found"
        
    return web.Response(
        text=js_content,
        content_type="application/javascript",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )

async def handle_captcha_demo_page(request):
    """GET /captcha/demo - BotShield jonli interaktiv sinov va vitrina sahifasi"""
    demo_path = os.path.join(os.path.dirname(__file__), "captcha_demo.html")
    if os.path.exists(demo_path):
        with open(demo_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    else:
        html_content = "<h1>BotShield Demo Page Not Found</h1>"
        
    return web.Response(text=html_content, content_type="text/html")

async def handle_api_captcha_create(request):
    """POST /api/v1/captcha/create - Yangi captcha challenge yaratish"""
    try:
        body = await request.json()
    except Exception:
        body = {}
        
    raw_sitekey = str(body.get("sitekey", "demo_key")).strip()
    c_type = str(body.get("type", "auto")).strip()
    
    # 1. Ephemeral session nonce (bsh_sess_...) qo'llab-quvvatlashi
    # Sayt egasi frontend HTML da statik sitekey qoldirmasdan, backend orqali
    # olingan bir martalik 90 soniyalik session kalitidan foydalanishi mumkin.
    actual_sitekey = raw_sitekey
    if raw_sitekey.startswith("bsh_sess_"):
        resolved = resolve_session_nonce(raw_sitekey)
        if not resolved:
            return cors_json_response({
                "ok": False,
                "error": "session_expired_or_invalid",
                "message": "Vaqtinchalik captcha sessiyasi eskirgan yoki ishlatilgan. Sahifani yangilang!"
            }, status=400)
        actual_sitekey = resolved

    # 2. Sitekey tekshiruvi
    key_info = get_captcha_key_by_sitekey(actual_sitekey)
    if not key_info:
        return cors_json_response({
            "ok": False,
            "error": "invalid_sitekey",
            "message": "Yaroqsiz yoki topilmagan sitekey!"
        }, status=400)
        
    if not key_info.get("is_active", True):
        return cors_json_response({
            "ok": False,
            "error": "sitekey_inactive",
            "message": "Ushbu sitekey faolsizlantirilgan!"
        }, status=403)
        
    # 3. Domain Whitelisting (Strict Origin/Referer enforcement - no empty-Origin or unconditional localhost bypass)
    allowed_domain = str(key_info.get("domain", "*") or "*").strip()
    if allowed_domain != "*" and not key_info.get("is_demo"):
        origin = (request.headers.get("Origin", "") or request.headers.get("Referer", "")).strip()
        if not origin:
            return cors_json_response({
                "ok": False,
                "error": "domain_not_allowed",
                "message": "Ushbu sitekey faqat ruxsat etilgan domenlarda ishlashi mumkin!"
            }, status=403)
        from urllib.parse import urlparse
        parsed_host = (urlparse(origin).hostname or "").lower()
        allowed_list = [d.strip().lower() for d in allowed_domain.split(",") if d.strip()]
        matched = bool(parsed_host) and any(
            parsed_host == d or parsed_host.endswith("." + d)
            for d in allowed_list
        )
        if not matched:
            return cors_json_response({
                "ok": False,
                "error": "domain_not_allowed",
                "message": f"Ushbu sitekey faqat '{allowed_domain}' domenlarida ishlashi ruxsat etilgan!"
            }, status=403)

    challenge = CaptchaManager.create_challenge(challenge_type=c_type, sitekey=actual_sitekey)
    return cors_json_response(challenge)


async def handle_api_captcha_create_session(request):
    """
    POST /api/v1/captcha/session/create - Enterprise Ephemeral Session Nonce
    Mijoz backend'i o'z secret_key'i orqali frontendga berish uchun 90 soniyalik
    bir martalik vaqtinchalik 'bsh_sess_...' kalitini oladi.
    Botlar frontend HTML ni skaner qilgan taqdirda ham, haqiqiy sitekey ko'rinmaydi.
    """
    try:
        body = await request.json()
    except Exception:
        post_data = await request.post()
        body = dict(post_data)
        
    secret = str(body.get("secret", "") or request.query.get("secret", "")).strip()
    if not secret:
        return cors_json_response({
            "ok": False,
            "error": "missing_secret",
            "message": "secret kaliti talab qilinadi"
        }, status=400)
        
    key_info = get_captcha_key_by_secret(secret)
    if not key_info:
        return cors_json_response({
            "ok": False,
            "error": "invalid_secret_key",
            "message": "Yaroqsiz yoki topilmagan secret key!"
        }, status=401)
        
    if not key_info.get("is_active", True):
        return cors_json_response({
            "ok": False,
            "error": "secret_key_inactive",
            "message": "Ushbu secret key faolsizlantirilgan!"
        }, status=403)
        
    sitekey = key_info.get("site_key", "")
    session_key = create_session_nonce(sitekey, ttl=90)
    
    return cors_json_response({
        "ok": True,
        "session_key": session_key,
        "expires_in": 90,
        "mode": "ephemeral_single_use",
        "message": "Vaqtinchalik 90s session kaliti yaratildi. Uni frontend vidjet data-sitekey maydoniga bering."
    })

async def handle_api_captcha_verify(request):
    """POST /api/v1/captcha/verify - Widget orqali yechim va telemetriyani tasdiqlash"""
    try:
        body = await request.json()
    except Exception:
        return cors_json_response({"ok": False, "error": "invalid_json"}, status=400)
        
    challenge_id = str(body.get("challenge_id", "")).strip()
    solution = body.get("solution")
    telemetry = body.get("telemetry", {})
    
    if not challenge_id or solution is None:
        return cors_json_response({
            "ok": False,
            "error": "missing_fields",
            "message": "challenge_id va solution maydonlari talab qilinadi"
        }, status=400)
        
    result = CaptchaManager.verify_challenge(challenge_id, solution, telemetry)
    status_code = 200 if result.get("ok") else 400
    if not result.get("ok"):
        print(f"[BotShield Verify Error] cid={challenge_id}, err={result.get('error')}, msg={result.get('message')}")
    return cors_json_response(result, status=status_code)

async def handle_api_captcha_siteverify(request):
    """
    POST /api/v1/captcha/siteverify - Server-to-Server yakuniy tasdiqlash
    Har bir muvaffaqiyatli tekshiruv uchun foydalanuvchi hisobidan 10 UZS yechiladi.
    """
    try:
        body = await request.json()
    except Exception:
        post_data = await request.post()
        body = dict(post_data)
        
    secret = str(body.get("secret", "") or request.query.get("secret", "")).strip()
    token = str(body.get("token", "") or request.query.get("token", "")).strip()
    sitekey = str(body.get("sitekey", "") or request.query.get("sitekey", "")).strip() or None
    
    if not secret:
        return cors_json_response({
            "success": False,
            "error": "missing_secret",
            "message": "secret kaliti talab qilinadi"
        }, status=400)
        
    if not token:
        return cors_json_response({
            "success": False,
            "error": "missing_token",
            "message": "token parametri talab qilinadi"
        }, status=400)
        
    key_info = get_captcha_key_by_secret(secret)
    if not key_info:
        return cors_json_response({
            "success": False,
            "error": "invalid_secret_key",
            "message": "Yaroqsiz yoki topilmagan secret key!"
        }, status=401)
        
    if not key_info.get("is_active", True):
        return cors_json_response({
            "success": False,
            "error": "secret_key_inactive",
            "message": "Ushbu secret key faolsizlantirilgan!"
        }, status=403)
        
    expected_sitekey = key_info.get("site_key")
    if sitekey and sitekey != expected_sitekey:
        return cors_json_response({
            "success": False,
            "error": "invalid_sitekey",
            "message": "Berilgan sitekey ushbu secret keyga tegishli emas!"
        }, status=400)
        
    verify_res = CaptchaManager.siteverify_token(token, secret, sitekey=expected_sitekey)
    if not verify_res.get("success"):
        return cors_json_response({
            "success": False,
            "error": verify_res.get("error", "verification_failed"),
            "message": verify_res.get("message", "Token tekshiruvdan o'tmadi")
        }, status=400)
        
    tg_user_id = key_info.get("tg_user_id", 0)
    is_demo = key_info.get("is_demo", False)
    cost_uzs = 10 if not is_demo else 0
    
    if not is_demo and tg_user_id > 0:
        current_bal = get_user_balance(tg_user_id)
        if current_bal < cost_uzs:
            return cors_json_response({
                "success": False,
                "error": "insufficient_balance",
                "message": f"Hisobingizda mablag' yetarli emas. Kerak: {cost_uzs} UZS, mavjud: {current_bal} UZS."
            }, status=402)
            
        deducted = deduct_user_balance(tg_user_id, cost_uzs)
        if not deducted:
            return cors_json_response({
                "success": False,
                "error": "billing_deduction_failed",
                "message": "Balansdan yechishda xatolik yuz berdi"
            }, status=500)
            
    client_ip = request.headers.get("X-Forwarded-For", request.remote or "").split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "")
    
    record_captcha_verification(
        tg_user_id=tg_user_id,
        site_key=key_info.get("site_key", ""),
        challenge_id=verify_res.get("challenge_id", ""),
        score=verify_res.get("score", 1.0),
        cost_uzs=cost_uzs,
        ip=client_ip,
        user_agent=user_agent,
        success=True
    )
    
    remaining_balance = get_user_balance(tg_user_id) if tg_user_id > 0 else 0
    
    return cors_json_response({
        "success": True,
        "challenge_ts": verify_res.get("timestamp"),
        "hostname": key_info.get("domain", "*"),
        "score": verify_res.get("score", 1.0),
        "action": "solve",
        "cost_uzs": cost_uzs,
        "remaining_balance_uzs": remaining_balance,
        "demo": is_demo
    })

async def handle_api_captcha_get_or_create_keys(request):
    """POST /api/v1/captcha/keys - Foydalanuvchi shaxsiy BotShield kalitlarini olish/yaratish"""
    user, err = authenticate_request(request)
    if err: return err
    
    tg_user_id = user["tg_user_id"]
    try:
        body = await request.json()
    except Exception:
        body = {}
    name = str(body.get("name", "Default Site")).strip()
    
    keys = get_or_create_captcha_keys(tg_user_id, name=name)
    return cors_json_response(keys)

async def handle_api_captcha_stats(request):
    """GET /api/v1/captcha/stats - Captcha foydalanish statistikasi"""
    user, err = authenticate_request(request)
    if err: return err
    
    stats = get_captcha_stats(user["tg_user_id"])
    return cors_json_response({"ok": True, "stats": stats})


def setup_reseller_api_routes(app: web.Application):
    """Barcha Reseller & Pay-As-You-Go API yo'nalishlarini ro'yxatga olish"""
    # 1. Asosiy Hisob & Mahsulotlar
    app.router.add_get("/api/v1/me", handle_api_me)
    app.router.add_get("/api/v1/products", handle_api_products)
    app.router.add_get("/api/v1/stock", handle_api_products)
    app.router.add_get("/api/v1/tariffs", handle_api_tariffs)
    app.router.add_post("/api/v1/buy", handle_api_buy)

    # 2. AI Pay-As-You-Go Endpoints
    app.router.add_post("/api/v1/ai/summarize", handle_api_ai_summarize)
    app.router.add_post("/api/v1/ai/clickbait-title", handle_api_ai_clickbait_title)
    app.router.add_post("/api/v1/ai/shorts-hook", handle_api_ai_shorts_hook)
    app.router.add_post("/api/v1/ai/reply-comment", handle_api_ai_reply_comment)
    app.router.add_post("/api/v1/ai/generate", handle_api_ai_generate)

    # 3. Media & Processing Endpoints
    app.router.add_post("/api/v1/media/uniquify", handle_api_media_uniquify)
    app.router.add_post("/api/v1/media/crop-vertical", handle_api_media_crop_vertical)
    app.router.add_post("/api/v1/media/remove-silence", handle_api_media_remove_silence)
    app.router.add_post("/api/v1/media/compress-telegram", handle_api_media_compress_telegram)
    app.router.add_post("/api/v1/downloader", handle_api_downloader)
    app.router.add_get("/api/v1/downloader", handle_api_downloader)

    # 4. SMM Growth & Engagement Endpoints
    app.router.add_post("/api/v1/smm/smart-deeplink", handle_api_smm_smart_deeplink)
    app.router.add_get("/api/v1/smm/spy/velocity", handle_api_smm_spy_velocity)
    app.router.add_post("/api/v1/smm/spy/velocity", handle_api_smm_spy_velocity)
    app.router.add_get("/api/v1/smm/services", handle_api_smm_services)
    app.router.add_post("/api/v1/smm/order", handle_api_smm_order)
    app.router.add_get("/api/v1/smm/order/{order_id}", handle_api_smm_status)

    # 5. Gamification, Gifts & Vouchers Endpoints
    app.router.add_get("/api/v1/gifts/available", handle_api_gifts_available)
    app.router.add_post("/api/v1/gifts/send", handle_api_gifts_send)
    app.router.add_post("/api/v1/cases/open", handle_api_cases_open)
    app.router.add_post("/api/v1/vouchers/create", handle_api_vouchers_create)
    app.router.add_post("/api/v1/vouchers/redeem", handle_api_vouchers_redeem)

    # 6. White-Label & Billing Endpoints
    app.router.add_post("/api/v1/reseller/bot/connect", handle_api_reseller_bot_connect)
    app.router.add_post("/api/v1/billing/stars/invoice", handle_api_billing_stars_invoice)
    app.router.add_post("/api/v1/webhooks/set", handle_api_webhooks_set)
    app.router.add_get("/api/v1/webhooks", handle_api_webhooks_get)

    # 7. Documentation & Dashboard
    app.router.add_get("/api/v1/docs", handle_api_docs_html)
    app.router.add_get("/dashboard", handle_dashboard_webapp)
    # 8. BotShield Captcha as a Service Endpoints
    app.router.add_get("/captcha/widget.js", handle_captcha_widget_js)
    app.router.add_get("/captcha/demo", handle_captcha_demo_page)
    app.router.add_post("/api/v1/captcha/session/create", handle_api_captcha_create_session)
    app.router.add_post("/api/v1/captcha/create", handle_api_captcha_create)
    app.router.add_post("/api/v1/captcha/verify", handle_api_captcha_verify)
    app.router.add_post("/api/v1/captcha/siteverify", handle_api_captcha_siteverify)
    app.router.add_post("/api/v1/captcha/keys", handle_api_captcha_get_or_create_keys)
    app.router.add_get("/api/v1/captcha/stats", handle_api_captcha_stats)

    # CORS Preflight OPTIONS
    app.router.add_options("/api/v1/captcha/session/create", handle_captcha_options)
    app.router.add_options("/api/v1/captcha/create", handle_captcha_options)
    app.router.add_options("/api/v1/captcha/verify", handle_captcha_options)
    app.router.add_options("/api/v1/captcha/siteverify", handle_captcha_options)
    app.router.add_options("/api/v1/captcha/keys", handle_captcha_options)
    app.router.add_options("/api/v1/captcha/stats", handle_captcha_options)

    print("[Reseller API] Barcha 25 ta REST API yo'nalishlari muvaffaqiyatli ulandi (/api/v1/... va /dashboard)")



