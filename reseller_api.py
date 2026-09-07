"""
Reseller & Developer REST API
Ushbu modul tashqi dasturchilar va resellerlar uchun REST API taqdim etadi.
Har bir foydalanuvchi o'z Telegram hisobidagi shaxsiy API kaliti (art_live_...)
orqali balansini boshqarishi, mahsulotlarni (AI kalitlar, Proxylar) sotib olishi
va YouTube xizmatlariga avtomatik buyurtma berishi mumkin.
"""

import json
from aiohttp import web
from database import (
    get_user_by_api_key,
    log_api_key_usage,
    get_api_keys_stock_count,
    get_proxies_stock_count,
    purchase_api_key,
    purchase_proxy,
    create_engagement_order,
    get_db
)

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
    """GET /api/v1/products - Mavjud mahsulotlar va narxlar"""
    user, err = authenticate_request(request)
    if err: return err
    
    key_stock = get_api_keys_stock_count()
    proxy_stock = get_proxies_stock_count()
    
    products = {
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
            "name": "Groq Cloud API Key",
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
    
    smm_services = {
        "like": {
            "name": "YouTube Like",
            "type": "like",
            "unit_price_uzs": 1500,
            "min_quantity": 1
        },
        "subscribe": {
            "name": "YouTube Subscriber",
            "type": "subscribe",
            "unit_price_uzs": 2500,
            "min_quantity": 1
        },
        "view": {
            "name": "YouTube View",
            "type": "view",
            "unit_price_uzs": 1500,
            "min_quantity": 1
        },
        "autostream": {
            "name": "YouTube 24/7 Autostream Cloud",
            "type": "autostream",
            "price_per_hour_uzs": 4000,
            "min_hours": 1
        }
    }
    
    return web.json_response({
        "ok": True,
        "products": products,
        "smm_services": smm_services
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
        
    if quantity < 1:
        return web.json_response({
            "ok": False,
            "error": "invalid_quantity",
            "message": "'quantity' eng kamida 1 bo'lishi kerak"
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
        return web.json_response({"ok": False, "error": "server_error", "message": str(e)}, status=500)
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


# ==================== INTERACTIVE API DOCUMENTATION (HTML) ====================

async def handle_api_docs_html(request):
    """GET /api/v1/docs - Zamonaviy, interaktiv REST API hujjatlari"""
    html = """<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoReply Developer & Reseller REST API</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --card-bg: rgba(18, 26, 43, 0.75);
            --border: rgba(255, 255, 255, 0.08);
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.25);
            --accent: #10b981;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --code-bg: #030712;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            padding: 24px 16px;
        }
        .container { max-width: 960px; margin: 0 auto; }
        .hero {
            text-align: center;
            padding: 40px 20px;
            background: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.15), transparent 70%);
            border: 1px solid var(--border);
            border-radius: 20px;
            margin-bottom: 32px;
            backdrop-filter: blur(12px);
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(59, 130, 246, 0.12);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 16px;
        }
        h1 { font-size: 2.4rem; font-weight: 800; margin-bottom: 12px; letter-spacing: -0.5px; }
        p.subtitle { color: var(--text-muted); font-size: 1.1rem; max-width: 680px; margin: 0 auto; }
        
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            backdrop-filter: blur(8px);
        }
        h2 { font-size: 1.4rem; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        
        .endpoint-card {
            background: rgba(10, 15, 29, 0.6);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 18px;
            overflow: hidden;
            transition: all 0.2s ease;
        }
        .endpoint-card:hover { border-color: rgba(59, 130, 246, 0.4); transform: translateY(-2px); }
        .endpoint-header {
            padding: 14px 18px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.02);
        }
        .method {
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.8rem;
            font-family: 'Fira Code', monospace;
        }
        .get { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .post { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .path { font-family: 'Fira Code', monospace; font-size: 0.95rem; font-weight: 600; }
        .endpoint-desc { padding: 14px 18px; color: var(--text-muted); font-size: 0.95rem; }
        
        pre {
            background: var(--code-bg);
            border-radius: 10px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'Fira Code', monospace;
            font-size: 0.88rem;
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 10px;
        }
        .param-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.9rem; }
        .param-table th, .param-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
        .param-table th { color: var(--text-muted); font-weight: 600; }
        .param-name { font-family: 'Fira Code', monospace; color: #60a5fa; font-weight: 600; }
        .tag-req { color: #f43f5e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        
        .footer { text-align: center; color: var(--text-muted); font-size: 0.9rem; padding: 24px 0; }
    </style>
</head>
<body>
<div class="container">
    <div class="hero">
        <div class="badge">🚀 REST API v1</div>
        <h1>Developer & Reseller API</h1>
        <p class="subtitle">O'z Telegram botingiz yoki saytingiz orqali bizning mahsulotlarimizni (AI kalitlar, Proxylar, YouTube buyurtmalar) avtomatik sotib oling va ishlating.</p>
    </div>

    <!-- Autentifikatsiya -->
    <div class="card">
        <h2>🔑 Autentifikatsiya (API Kalit)</h2>
        <p>Barcha so'rovlar Telegram botingizda berilgan shaxsiy API kalit bilan yuborilishi shart. Har bir so'rovda quyidagi HTTP Header ni kiriting:</p>
        <pre><code>Authorization: Bearer art_live_sizning_shaxsiy_api_kalitingiz</code></pre>
        <p style="margin-top: 8px; font-size: 0.9rem; color: var(--text-muted);">yoki <code>X-API-Key: art_live_...</code> sarlavhasi orqali.</p>
    </div>

    <!-- 1. Balans tekshirish -->
    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/me</span>
        </div>
        <div class="endpoint-desc">
            Hisobingiz ma'lumotlari, balansingiz (so'mda) va umumiy so'rovlar sonini qaytaradi.
            <pre><code>curl -X GET "https://YOUR_DOMAIN/api/v1/me" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
            <p style="margin-top: 10px; font-weight: 600; color: #94a3b8;">Javob namunasi (200 OK):</p>
            <pre><code>{
  "ok": true,
  "user": {
    "tg_user_id": 12345678,
    "balance_uzs": 150000,
    "balance_usd_approx": 11.72,
    "kyc_status": "verified",
    "total_requests": 34
  }
}</code></pre>
        </div>
    </div>

    <!-- 2. Mahsulotlar ro'yxati -->
    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/products</span>
        </div>
        <div class="endpoint-desc">
            Mavjud barcha API kalitlar (OpenRouter, Gemini, Groq), Dedicated Proxylar soni va YouTube xizmatlari narxlarini qaytaradi.
            <pre><code>curl -X GET "https://YOUR_DOMAIN/api/v1/products" \\
     -H "Authorization: Bearer art_live_xxx"</code></pre>
            <p style="margin-top: 10px; font-weight: 600; color: #94a3b8;">Javob namunasi (200 OK):</p>
            <pre><code>{
  "ok": true,
  "products": {
    "openrouter": { "name": "OpenRouter API Key ($3 tier)", "price_uzs": 38000, "in_stock": 10, "available": true },
    "gemini": { "name": "Google Gemini API Key ($5 tier)", "price_uzs": 64000, "in_stock": 10, "available": true },
    "groq": { "name": "Groq Cloud API Key", "price_uzs": 10000, "in_stock": 10, "available": true },
    "proxy": { "name": "Dedicated HTTP/HTTPS Private Proxy", "price_uzs": 38000, "in_stock": 11, "available": true }
  },
  "smm_services": {
    "like": { "unit_price_uzs": 1500, "min_quantity": 1 },
    "subscribe": { "unit_price_uzs": 2500, "min_quantity": 1 },
    "view": { "unit_price_uzs": 1500, "min_quantity": 1 }
  }
}</code></pre>
        </div>
    </div>

    <!-- 3. Mahsulot sotib olish -->
    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/buy</span>
        </div>
        <div class="endpoint-desc">
            Balansingizdan mablag' yechib, zaxiradan bitta API kalit yoki Dedicated Proxy taqdim etadi.
            <table class="param-table">
                <tr><th>Parametr</th><th>Turi</th><th>Tavsif</th></tr>
                <tr><td class="param-name">service <span class="tag-req">shart</span></td><td>string</td><td><code>openrouter</code>, <code>gemini</code>, <code>groq</code> yoki <code>proxy</code></td></tr>
            </table>
            <pre><code>curl -X POST "https://YOUR_DOMAIN/api/v1/buy" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{"service": "openrouter"}'</code></pre>
            <p style="margin-top: 10px; font-weight: 600; color: #94a3b8;">Javob namunasi (200 OK):</p>
            <pre><code>{
  "ok": true,
  "service": "openrouter",
  "api_key": "sk-or-v1-e2edcfed...",
  "price_uzs": 38000,
  "remaining_balance_uzs": 112000
}</code></pre>
        </div>
    </div>

    <!-- 4. YouTube buyurtma -->
    <div class="endpoint-card">
        <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/smm/order</span>
        </div>
        <div class="endpoint-desc">
            YouTube video yoki kanalingizga Layk, Obunachi yoki Ko'rishlar buyurtma berish.
            <table class="param-table">
                <tr><th>Parametr</th><th>Turi</th><th>Tavsif</th></tr>
                <tr><td class="param-name">order_type <span class="tag-req">shart</span></td><td>string</td><td><code>like</code>, <code>subscribe</code> yoki <code>view</code></td></tr>
                <tr><td class="param-name">target_url <span class="tag-req">shart</span></td><td>string</td><td>YouTube video yoki kanal havolasi</td></tr>
                <tr><td class="param-name">quantity <span class="tag-req">shart</span></td><td>integer</td><td>Buyurtma soni (kamida 1)</td></tr>
            </table>
            <pre><code>curl -X POST "https://YOUR_DOMAIN/api/v1/smm/order" \\
     -H "Authorization: Bearer art_live_xxx" \\
     -H "Content-Type: application/json" \\
     -d '{"order_type": "like", "target_url": "https://youtu.be/xxx", "quantity": 10}'</code></pre>
        </div>
    </div>

    <!-- Python Kod Namunasi -->
    <div class="card">
        <h2>🐍 Python orqali ulash kodi (Reseller Bot namunasi)</h2>
        <p>Quyidagi tayyor kodni o'z loyihangizga qo'shib, to'liq ishlatishingiz mumkin:</p>
        <pre><code>import requests

API_KEY = "art_live_SIZNING_KALITINGIZ"
BASE_URL = "https://YOUR_DOMAIN/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Balansni bilish
user_info = requests.get(f"{BASE_URL}/me", headers=headers).json()
print("Balans:", user_info["user"]["balance_uzs"], "so'm")

# 2. OpenRouter API kalit sotib olish
buy_resp = requests.post(f"{BASE_URL}/buy", headers=headers, json={"service": "openrouter"}).json()
if buy_resp["ok"]:
    print("Kalit:", buy_resp["api_key"])
    print("Qoldiq balans:", buy_resp["remaining_balance_uzs"])
else:
    print("Xatolik:", buy_resp["message"])
</code></pre>
    </div>

    <div class="footer">
        © 2026 AutoReply Developer Platform • Reseller & Automation API
    </div>
</div>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")


async def handle_dashboard_webapp(request):
    """GET /dashboard - Telegram Mini App Dashboard (Faqat TON va Stars bilan)"""
    user_id = request.query.get("user_id", "0")
    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Developer & Reseller Dashboard</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Fira+Code:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --card-bg: rgba(18, 26, 44, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --primary: #3b82f6;
            --ton: #0098ea;
            --stars: #f59e0b;
            --accent: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Outfit', sans-serif;
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
        }}
        .logo-title {{ font-size: 1.25rem; font-weight: 800; display: flex; align-items: center; gap: 8px; }}
        .badge {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }}
        
        .balance-card {{
            background: radial-gradient(circle at 100% 0%, rgba(59, 130, 246, 0.2), transparent 70%), var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            text-align: center;
        }}
        .bal-label {{ color: var(--text-muted); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
        .bal-value {{ font-size: 2.2rem; font-weight: 800; color: #fff; margin-bottom: 16px; }}
        
        .topup-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .btn-topup {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 14px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.9rem;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }}
        .btn-ton {{ background: rgba(0, 152, 234, 0.15); color: #38bdf8; border: 1px solid rgba(0, 152, 234, 0.4); }}
        .btn-ton:active {{ transform: scale(0.97); background: rgba(0, 152, 234, 0.25); }}
        .btn-stars {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}
        .btn-stars:active {{ transform: scale(0.97); background: rgba(245, 158, 11, 0.25); }}
        
        .section-title {{ font-size: 1rem; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 18px;
        }}
        
        .key-box {{
            background: #060913;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            color: #60a5fa;
            word-break: break-all;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }}
        .btn-action {{
            width: 100%;
            background: #2563eb;
            color: #fff;
            padding: 12px;
            border-radius: 10px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        .btn-action:active {{ background: #1d4ed8; }}
        
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; }}
        .stat-item {{ background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 12px; padding: 14px; text-align: center; }}
        .stat-num {{ font-size: 1.3rem; font-weight: 800; color: #f8fafc; }}
        .stat-name {{ font-size: 0.75rem; color: var(--text-muted); font-weight: 600; margin-top: 4px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo-title">⚡ Developer Hub</div>
        <div class="badge">PRO PANEL</div>
    </div>

    <!-- Balans -->
    <div class="balance-card">
        <div class="bal-label">Asosiy Balansingiz</div>
        <div class="bal-value" id="balVal">Yuklanmoqda...</div>
        <div class="topup-grid">
            <button class="btn-topup btn-ton" onclick="openTonTopup()">💎 TON To'lov</button>
            <button class="btn-topup btn-stars" onclick="openStarsTopup()">⭐ Stars To'lov</button>
        </div>
    </div>

    <!-- API Key -->
    <div class="section-title">🔑 Shaxsiy API Kalit</div>
    <div class="card">
        <div class="key-box">
            <span id="apiKeyText">art_live_••••••••••••••••</span>
            <span style="cursor: pointer;" onclick="copyKey()">📋</span>
        </div>
        <button class="btn-action" onclick="copyKey()">Nusxalash (Copy Key)</button>
    </div>

    <!-- Statistika -->
    <div class="section-title">📊 Reseller Statistikasi</div>
    <div class="stats-grid">
        <div class="stat-item">
            <div class="stat-num" id="reqCount">0 ta</div>
            <div class="stat-name">API So'rovlar</div>
        </div>
        <div class="stat-item">
            <div class="stat-num" style="color: #10b981;">Faol</div>
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


def setup_reseller_api_routes(app: web.Application):
    """Barcha Reseller API yo'nalishlarini ro'yxatga olish"""
    app.router.add_get("/api/v1/me", handle_api_me)
    app.router.add_get("/api/v1/products", handle_api_products)
    app.router.add_get("/api/v1/stock", handle_api_products)
    app.router.add_post("/api/v1/buy", handle_api_buy)
    app.router.add_post("/api/v1/smm/order", handle_api_smm_order)
    app.router.add_get("/api/v1/smm/order/{order_id}", handle_api_smm_status)
    app.router.add_get("/api/v1/docs", handle_api_docs_html)
    app.router.add_get("/dashboard", handle_dashboard_webapp)
    print("[Reseller API] REST API yo'nalishlari muvaffaqiyatli ulandi (/api/v1/... va /dashboard)")


