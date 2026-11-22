import asyncio
import sys
import os
import time

# Windows encoding fix
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Python 3.10+ event loop fix (Pyrogram uchun kerak)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Pyrogram 64-bit channel ID fix (ValueError: Peer id invalid: -1004493034300)
import pyrogram_patch
# Pyrogram patches applied via pyrogram_patch module

from aiohttp import web
from config import (
    SESSION_STRING,
    BOT_TOKEN,
    API_ID,
    API_HASH,
    BRAND_NAME,
    APP_BASE_URL,
    SUPPORT_USERNAME,
    get_bot_username,
    set_runtime_bot_username,
)
from autopost import exchange_code_with_redirect, get_auth_url, pending_oauth
from database import save_yt_connection

# ==================== BOT REFERENCES ====================
# ytbot instance ni saqlash (callback dan xabar yuborish uchun)
ytbot_instance = None
secondary_bot_instances = []





# ==================== GEMINI PRICE WATCHER ====================
async def gemini_price_watcher(bot):
    """Gemini 18 oylik narxini tekshirish — $0.50 dan kam bo'lsa adminga xabar yuborish"""
    from config import OWNER_ID
    from database import get_bot_config, set_bot_config

    # Read persistent last alerted price from database so restarts don't trigger repeated alerts
    last_alerted_price = None
    try:
        saved_price = await asyncio.to_thread(get_bot_config, "gemini_price_watcher_last_price")
        if saved_price:
            last_alerted_price = float(saved_price)
    except Exception as e:
        last_alerted_price = None

    THRESHOLD = 0.50
    CHECK_INTERVAL = 900  # 15 daqiqa
    PRODUCT_ID = 16

    print(f"📊 Gemini Price Watcher ishga tushdi (Product ID: {PRODUCT_ID}, Chegara: ${THRESHOLD}, Oldingi xabar: ${last_alerted_price})")
    await asyncio.sleep(60)  # Startup uchun kutish

    while True:
        try:
            from ventebot_service import ventebot_service
            data = await ventebot_service.get_products(force_refresh=True)
            products = data.get("products", [])

            gemini_product = None
            for p in products:
                if p.get("id") == PRODUCT_ID or "gemini 18" in (p.get("name") or "").lower():
                    gemini_product = p
                    break

            if gemini_product:
                price_usd = float(gemini_product.get("price_usd") or gemini_product.get("price") or 0)
                stock = gemini_product.get("stock", "N/A")
                print(f"[PriceWatcher] Gemini 18M: ${price_usd} | Zaxira: {stock}")

                if price_usd > 0 and price_usd < THRESHOLD:
                    if last_alerted_price is None or abs(price_usd - last_alerted_price) >= 0.01:
                        try:
                            alert_text = (
                                f"⚡ <b>DIQQAT! Gemini 18 oylik narxi tushdi!</b>\n\n"
                                f"📉 <b>Yangi narx:</b> <code>${price_usd}</code>\n"
                                f"🎯 <b>Chegara:</b> <code>${THRESHOLD}</code>\n"
                                f"📦 <b>Zaxira:</b> <code>{stock} ta</code>\n\n"
                                f"🛒 <i>Hoziroq xarid qilishingiz yoki zaxirani to'ldirishingiz mumkin!</i>"
                            )
                            await bot.send_message(OWNER_ID, alert_text)
                            last_alerted_price = price_usd
                            await asyncio.to_thread(set_bot_config, "gemini_price_watcher_last_price", str(price_usd))
                            print(f"[PriceWatcher] ⚡ Admin ga ogohlantirish yuborildi: ${price_usd}")
                        except Exception as send_err:
                            print(f"[PriceWatcher] Admin ga xabar yuborishda xato: {send_err}")
                else:
                    if last_alerted_price is not None and price_usd >= THRESHOLD:
                        last_alerted_price = None
                        await asyncio.to_thread(set_bot_config, "gemini_price_watcher_last_price", "")

        except Exception as e:
            print(f"[PriceWatcher] Tekshirishda xato: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


# ==================== AUTOPILOT WORKER ====================
async def run_autopilot_worker():
    import asyncio
    from database import get_all_active_autopilots, update_autopilot_last_run
    from datetime import datetime, timedelta
    
    print("🤖 Autopilot worker started")
    while True:
        try:
            now = datetime.now()
            autopilots = await asyncio.to_thread(get_all_active_autopilots)
            
            for ap in autopilots:
                user_id = ap['tg_user_id']
                topics_str = ap['topics']
                interval = ap['interval_days']
                last_run = ap['last_run']
                
                # Check if it should run
                should_run = False
                if not last_run:
                    should_run = True
                else:
                    if (now - last_run).days >= interval:
                        should_run = True
                        
                if should_run:
                    print(f"🚀 Running autopilot for user {user_id}, topics: {topics_str}")
                    
                    import random
                    topics_list = [t.strip() for t in topics_str.split(",") if t.strip()]
                    if topics_list and ytbot_instance:
                        topic = random.choice(topics_list)
                        try:
                            # send message to user to notify
                            await ytbot_instance.send_message(user_id, f"🤖 **AutoPilot Ishga Tushdi!**\n\n🔍 Qidirilmoqda: `{topic}`")
                            
                            from database import get_yt_connection
                            conn = await asyncio.to_thread(get_yt_connection, user_id)
                            if not conn:
                                await ytbot_instance.send_message(user_id, "❌ **AutoPilot Xatosi:** YouTube kanal ulanmagan! `/ytlogin` orqali ulang.")
                                continue
                                
                            channel_id = conn['yt_channel_id']
                            
                            # Start search and autopost for 1 video
                            from database import create_autopost_task
                            task_id = await asyncio.to_thread(create_autopost_task, user_id, channel_id, topic, "shorts", 1)

                            # Update last run right away so it doesn't run again if it fails
                            await asyncio.to_thread(update_autopilot_last_run, user_id)

                            if task_id:
                                print(f"[autopilot] Task {task_id} navbatga qo'shildi, marshrutlanmoqda...")
                                try:
                                    await dispatch_or_run_autopost(task_id)
                                except Exception as _dispatch_err:
                                    print(f"[autopilot] dispatch xato: {_dispatch_err}")
                            
                        except Exception as e:
                            print(f"Autopilot task error: {e}")
                            
        except Exception as e:
            print(f"Autopilot worker error: {e}")
            
        await asyncio.sleep(60 * 60) # Check every hour


async def _get_worker_bot_client(worker_id):
    """
    Faqat ROLE=main botni boshqaradi.
    Worker, autoposter yoki streamer serverlari bot sessiyasini ochmaydi,
    bu esa Telegram 409 Conflict va qotishlarni (5-8 soniyalik lag) butunlay yo'q qiladi.
    """
    return None


async def _run_autopost_task(task, worker_id, bot_client):
    """
    Bitta autopost taskni bajaradi. Ham poll-loop (run_worker_queue), ham
    tashqidan push qilingan /claim-task shu funksiyani chaqiradi — mantiq
    ikki joyda takrorlanmasin va busy-state doim to'g'ri boshqarilsin.
    """
    from database import get_user_proxy, update_autopost_task
    from autopost import autopost_worker

    task_id      = task['id']
    tg_user_id   = task['tg_user_id']
    search_query = task['search_query']
    total_count  = task['total_count']
    apply_wm     = task.get('apply_watermark', False)
    user_proxy   = get_user_proxy(tg_user_id)

    print(f"📥 [{worker_id}] Task #{task_id} olindi: '{search_query}' ({total_count} ta)")

    _autopost_busy_state["busy"] = True
    _autopost_busy_state["task_id"] = task_id
    try:
        await autopost_worker(
            task_id, tg_user_id, search_query, total_count,
            bot_client, tg_user_id,
            proxy_url=user_proxy,
            apply_watermark=apply_wm
        )
    except Exception as e:
        print(f"❌ [{worker_id}] Task #{task_id} xatosi: {e}")
        update_autopost_task(task_id, status="failed")
    finally:
        _autopost_busy_state["busy"] = False
        _autopost_busy_state["task_id"] = None


async def run_worker_queue(bot_client=None):
    """
    ROLE=worker / ROLE=autoposter uchun:
    DB dagi 'pending' autopost tasklerini oladi va bajaradi.
    Bir vaqtda bir task. Tugatgach keyingisini oladi.
    ROLE=main HTTP orqali /claim-task ga task push qilsa, u ham xuddi shu
    _autopost_busy_state dan foydalanadi — shu process ikki taskni
    baravariga boshlab qo'ymaydi.

    bot_client berilmasa (masalan to'g'ridan chaqirilganda), o'zi yaratadi.
    ROLE=worker asosiy oqimida chaqirilganda, bitta client ikkala yo'l
    (poll-loop va HTTP push) uchun umumiy ishlatilishi kerak — Pyrogram
    bitta processda ikkita bir xil sessiyani parallel ochishni yoqtirmaydi.
    """
    from database import claim_pending_autopost_task
    import asyncio
    import os

    worker_id = f"worker_{os.getpid()}"
    print(f"👷 [{worker_id}] Autopost queue worker poylamoqda...")

    if bot_client is None:
        bot_client = await _get_worker_bot_client(worker_id)

    while True:
        try:
            if _autopost_busy_state["busy"]:
                # Hozir /claim-task orqali push qilingan (yoki shu loopdan) task ishlayapti
                await asyncio.sleep(1)
                continue

            task = claim_pending_autopost_task()
            if task:
                await _run_autopost_task(task, worker_id, bot_client)
            else:
                await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ [{worker_id}] Queue loop xatosi: {e}")
            await asyncio.sleep(3)


# ==================== ROLE=main DISPATCHER ====================
# /autopost va /autostream start (yoki API orqali yaratilgan tasklar) DB ga
# yozilgandan keyin shu yerdan chaqiriladi. Tartib:
#   1. WORKER_URLS / STREAMER_URLS dagi tashqi serverlardan bo'shini topib push qiladi
#   2. Hech kim bo'sh bo'lmasa/javob bermasa va main hali RAM limitida (
#      MAIN_MAX_CONCURRENT_TASKS dan kam ish bajarayotgan) bo'lsa — main o'zi bajaradi
#   3. Aks holda hech narsa qilinmaydi — task DB da 'pending' holida qoladi,
#      keyinroq bo'shagan har qanday worker/streamer (poll orqali) yoki
#      keyingi dispatch chaqiruvi uni oladi.

async def dispatch_or_run_autopost(task_id):
    """ROLE=main: yangi yaratilgan autopost task_id ni marshrutlaydi."""
    from config import WORKER_URLS, MAIN_MAX_CONCURRENT_TASKS

    sent = await _dispatch_task_to_remote(WORKER_URLS, task_id, "autopost")
    if sent:
        return "dispatched"

    # Admin (6735799833) va Stars to'langan tasklar navbatda kutmasdan darhol bajariladi
    is_vip_priority = False
    try:
        from database import get_autopost_task_by_id
        t_info = get_autopost_task_by_id(task_id)
        if t_info:
            tg_uid = t_info.get("tg_user_id") if isinstance(t_info, dict) else t_info[1]
            stars_paid = t_info.get("is_stars_paid") if isinstance(t_info, dict) else False
            prio = t_info.get("priority", 0) if isinstance(t_info, dict) else 0
            if int(tg_uid) == 6735799833 or stars_paid or (prio and prio > 0):
                is_vip_priority = True
    except Exception as _prio_err:
        print(f"[dispatch/autopost] prio check err: {_prio_err}")

    if not is_vip_priority and _main_running_tasks["count"] >= MAIN_MAX_CONCURRENT_TASKS:
        print(f"[dispatch/autopost] Task #{task_id}: tashqi worker yo'q, main band — DB navbatida qoldi")
        return "queued"

    from database import claim_autopost_task_by_id
    task = claim_autopost_task_by_id(task_id)
    if not task:
        # Shu orada boshqa joy (masalan alohida ishlayotgan worker poll-loop) olib ulgurgan
        return "queued"

    print(f"[dispatch/autopost] Task #{task_id}: main o'zi bajaradi (VIP={is_vip_priority})")
    _main_running_tasks["count"] += 1
    try:
        asyncio.create_task(_run_main_autopost_task(task))
    except Exception:
        _main_running_tasks["count"] -= 1
        raise
    return "running_local"


async def _run_main_autopost_task(task):
    """ROLE=main o'zi autopost taskni bajarayotganda ishlaydigan wrapper (counter bilan)."""
    try:
        await _run_autopost_task(task, f"main_{os.getpid()}", ytbot_instance)
    finally:
        _main_running_tasks["count"] = max(0, _main_running_tasks["count"] - 1)


async def _poll_pending_autopost_tasks_loop():
    """ROLE=main: bazada 'pending' holatida turgan autopost vazifalarini (masalan, #1) avtomatik ishga tushiradi."""
    await asyncio.sleep(5)
    try:
        from database import reset_stale_autopost_tasks
        reset_stale_autopost_tasks(15)
    except Exception:
        pass

    while True:
        try:
            from database import get_pending_tasks
            pending = await asyncio.to_thread(get_pending_tasks)
            for t in (pending or []):
                if str(t.get("status", "")).lower() == "pending":
                    tid = t.get("id")
                    if tid:
                        await dispatch_or_run_autopost(tid)
                        break
        except Exception as e:
            print(f"[autopost-poller] xato: {e}")
        await asyncio.sleep(12)


async def dispatch_or_run_stream(task_id):
    """ROLE=main: yangi yaratilgan stream task_id ni marshrutlaydi."""
    from config import STREAMER_URLS, MAIN_MAX_CONCURRENT_TASKS

    sent = await _dispatch_task_to_remote(STREAMER_URLS, task_id, "stream")
    if sent:
        return "dispatched"

    # Admin (6735799833) darhol navbatsiz stream boshlaydi
    is_vip_priority = False
    try:
        from database import get_stream_task_by_id
        st_info = get_stream_task_by_id(task_id)
        if st_info:
            tg_uid = st_info.get("tg_user_id") if isinstance(st_info, dict) else st_info[1]
            if int(tg_uid) == 6735799833:
                is_vip_priority = True
    except Exception as _stream_prio_err:
        print(f"[dispatch/stream] prio check err: {_stream_prio_err}")

    if not is_vip_priority and _main_running_tasks["count"] >= MAIN_MAX_CONCURRENT_TASKS:
        print(f"[dispatch/stream] Task #{task_id}: tashqi streamer yo'q, main band — DB navbatida qoldi")
        return "queued"

    from database import claim_stream_task_by_id
    worker_id = f"main_streamer_{os.getpid()}"
    task = claim_stream_task_by_id(task_id, worker_id)
    if not task:
        return "queued"

    print(f"[dispatch/stream] Task #{task_id}: main o'zi bajaradi (VIP={is_vip_priority})")
    _main_running_tasks["count"] += 1
    try:
        asyncio.create_task(_run_main_stream_task(task, worker_id))
    except Exception:
        _main_running_tasks["count"] -= 1
        raise
    return "running_local"


def _is_stream_task_cancelled_sync(tid: int) -> bool:
    conn_check = get_db()
    if not conn_check:
        return False
    try:
        cur_check = conn_check.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur_check.execute("SELECT status FROM stream_tasks WHERE id=%s", (tid,))
        row = cur_check.fetchone()
        return bool(row and row.get("status") == "cancelled")
    except Exception as e:
        print(f"[main_streamer] cancel check xato: {e}")
        return False
    finally:
        try:
            conn_check.close()
        except Exception:
            pass


async def _run_main_stream_task(task, worker_id):
    """
    ROLE=main o'zi stream taskni bajarayotganda ishlaydigan wrapper.

    Muhim: start_stream_task faqat FFmpeg ni ishga tushiradi va darhol
    qaytadi — streamning tugashini kutmaydi. Shuning uchun bu yerda
    _main_running_tasks countini FFmpeg chindan tugaguncha (yoki bekor
    qilinguncha) ushlab turadigan monitor loop kerak — aks holda RAM
    limiti FFmpeg ishga tushgan zahoti "bo'shab qoladi" va main navbatdan
    tashqari yana og'ir ish olib, RAM limitini buzadi.
    """
    from autostream import start_stream_task, _streamer_state, autostream_tasks
    from database import update_stream_task, get_db
    import psycopg2.extras

    task_id = task['id']
    try:
        await start_stream_task(task, worker_id, ytbot_instance)

        # start_stream_task muvaffaqiyatsiz bo'lsa (masalan video topilmadi
        # yoki FFmpeg ishga tushmadi), _streamer_state allaqachon tozalangan —
        # monitor qilishga hojat yo'q, counter darhol bo'shaydi.
        if _streamer_state.get("task_id") != task_id:
            return

        # FFmpeg tirik ekan — tugaguncha yoki bekor qilinguncha kuzatamiz
        while _streamer_state.get("task_id") == task_id:
            proc = _streamer_state.get("proc")
            if proc and proc.poll() is not None:
                print(f"[main_streamer] FFmpeg to'xtadi (task #{task_id})")
                update_stream_task(task_id, 'completed')
                keys_to_del = [k for k, v in autostream_tasks.items() if v == proc]
                for k in keys_to_del:
                    del autostream_tasks[k]
                _streamer_state["task_id"] = None
                _streamer_state["proc"] = None
                break

            # Bekor qilinganmi tekshiramiz (masalan /autostream stop)
            if await asyncio.to_thread(_is_stream_task_cancelled_sync, task_id) and proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try: proc.kill()
                    except: pass
                print(f"[main_streamer] Stream bekor qilindi (task #{task_id})")
                _streamer_state["task_id"] = None
                _streamer_state["proc"] = None
                break

            await asyncio.sleep(5)
    finally:
        _main_running_tasks["count"] = max(0, _main_running_tasks["count"] - 1)


# ==================== WEB SERVER (OAuth Callback + Health Check) ====================

_STATIC_HTML_CACHE = {}  # {path: {"mtime": float, "html": str}}


def _get_cached_index_html():
    candidates = (os.path.join("static", "dist", "index.html"), "index.html")
    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                mtime = os.path.getmtime(candidate)
                entry = _STATIC_HTML_CACHE.get(candidate)
                if entry and entry["mtime"] == mtime:
                    return entry["html"]
                with open(candidate, "r", encoding="utf-8") as f:
                    html = f.read()
                _STATIC_HTML_CACHE[candidate] = {"mtime": mtime, "html": html}
                return html
            except Exception as err:
                print(f"[index cache] {candidate} read error: {err}")
    return None


async def handle_health(request):
    """Fast health check and precompiled MonoDeck SPA entrypoint"""
    html = _get_cached_index_html()
    if html is not None:
        return web.Response(
            text=html,
            content_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return web.Response(text=f"{BRAND_NAME} is running.", content_type="text/html")


async def handle_api_public_config(request):
    """Public brand, domain, and active Telegram bot configuration for frontend."""
    import json as _json
    return web.Response(
        text=_json.dumps({
            "ok": True,
            "brand": BRAND_NAME,
            "app_base_url": APP_BASE_URL,
            "bot_username": get_bot_username(),
            "support_username": SUPPORT_USERNAME,
        }),
        content_type="application/json",
        headers={"Cache-Control": "public, max-age=300"},
    )


async def handle_privacy_page(request):
    """Google OAuth & YouTube Data API Compliant Privacy Policy page"""
    from legal_templates import get_privacy_html
    return web.Response(
        text=get_privacy_html(),
        content_type="text/html",
        headers={
            "Cache-Control": "public, max-age=300",
        }
    )


async def handle_terms_page(request):
    """MonoDeck SaaS Terms of Service page"""
    from legal_templates import get_terms_html
    return web.Response(
        text=get_terms_html(),
        content_type="text/html",
        headers={
            "Cache-Control": "public, max-age=300",
        }
    )


async def handle_google_verification(request):
    """Google Search Console Site Verification file handler (Strict Path Traversal Protected)"""
    filename = request.match_info.get("filename", "")
    import os, re
    safe_filename = os.path.basename(filename)
    if safe_filename == filename and re.match(r"^google[a-zA-Z0-9_\-]+\.html$", safe_filename):
        full_path = os.path.join(os.getcwd(), safe_filename)
        if os.path.isfile(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                return web.Response(text=f.read().strip(), content_type="text/html", charset="utf-8")
    return web.Response(status=404, text="404 Not Found", content_type="text/plain")


async def handle_ads_txt(request):
    """Google AdSense Authorized Digital Sellers (ads.txt) handler"""
    content = "google.com, pub-4094396006908725, DIRECT, f08c47fec0942fa0\n"
    import os
    if os.path.isfile("ads.txt"):
        try:
            with open("ads.txt", "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            pass
    return web.Response(
        text=content,
        content_type="text/plain",
        charset="utf-8",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*"
        }
    )

async def handle_robots(request):
    """robots.txt handler for search engines, AI agents and crawlers"""
    content = f"""# Robots.txt for {BRAND_NAME} ({APP_BASE_URL})
# AI Agents and Web Crawlers Configuration

User-agent: Mediapartners-Google
Allow: /

User-agent: *
Allow: /
Allow: /ads.txt
Allow: /docs
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha
Allow: /captcha/
Allow: /privacy
Allow: /privacy-policy
Allow: /terms
Allow: /terms-of-service
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/
Disallow: /oauth/
Disallow: /admin/

# Explicit permissions for AI Agents to index public documentation & tools
User-agent: GPTBot
Allow: /
Allow: /docs
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/

User-agent: ClaudeBot
Allow: /
Allow: /docs
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/

User-agent: Google-Extended
Allow: /
Allow: /docs
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/

User-agent: PerplexityBot
Allow: /
Allow: /docs
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/
"""
    return web.Response(text=content, content_type="text/plain", charset="utf-8")


# ==================== STATS CACHE (YouTube API quota tejash uchun) ====================
import time as _time
import re as _re
import html as _html
import gzip as _gzip
import hmac as _hmac
import hashlib as _hashlib
import io as _io
from urllib.parse import urlparse as _urlparse, parse_qs as _parse_qs

_stats_cache = {}  # {tg_user_id: {"data": ..., "ts": time}}
_stats_refresh_inflight = set()
_CACHE_TTL = 600  # 10 daqiqa

_VIDEO_ID_PATTERN = _re.compile(r"^[A-Za-z0-9_-]{11}$")
_SLUG_PATTERN = _re.compile(r"^[A-Za-z0-9_-]{1,120}$")
_FILE_ID_PATTERN = _re.compile(r"^[A-Za-z0-9_-]{1,160}$")
_HOST_HEADER_PATTERN = _re.compile(r"^[a-zA-Z0-9.-]+(?::\d{1,5})?$")
_REGION_CODE_PATTERN = _re.compile(r"^[A-Z]{2}$")
_ALLOWED_YT_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
    "shorts.youtube.com",
}
_ALLOWED_DL_RESOLUTIONS = {"360", "480", "720", "1080", "1440", "2160", "4320", "mp3", "best", "max"}
_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_ALLOWED_VIDEO_EXTS = {".mp4", ".webm", ".mov"}
_SAFE_PROXY_CONTENT_TYPES = {
    "application/json",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/webm",
    "video/mp4",
    "application/octet-stream",
}


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _get_client_ip(request) -> str:
    """Extract client IP consistently (Cloudflare / reverse proxy aware)."""
    client_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("True-Client-IP")
    if client_ip:
        return client_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    transport = getattr(request, "transport", None)
    if transport is not None:
        peername = transport.get_extra_info("peername")
        if peername:
            return peername[0]
    return getattr(request, "remote", None) or "unknown"


def _is_https_request(request) -> bool:
    """Detect whether the external client connection is HTTPS."""
    xf_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    if xf_proto == "https":
        return True
    return getattr(request, "scheme", "http") == "https"


def _get_safe_base_url(request) -> str:
    """Build a safe base URL without trusting arbitrary Host header injection."""
    fallback = APP_BASE_URL.rstrip("/")
    raw_host = (request.headers.get("Host") or "").strip()
    if not raw_host or not _HOST_HEADER_PATTERN.match(raw_host):
        return fallback
    scheme = (request.headers.get("X-Forwarded-Proto") or getattr(request, "scheme", "https")).split(",")[0].strip().lower()
    if scheme not in ("http", "https"):
        scheme = "https"
    return f"{scheme}://{raw_host}"


def _extract_valid_video_id(raw_value: str):
    """Validate and extract an 11-character YouTube video ID from an ID or YouTube URL."""
    val = str(raw_value or "").strip()
    if not val or len(val) > 512:
        return None
    if _VIDEO_ID_PATTERN.match(val):
        return val
    try:
        parsed = _urlparse(val)
        if parsed.scheme in ("http", "https") and (parsed.hostname or "").lower() in _ALLOWED_YT_HOSTS:
            host = (parsed.hostname or "").lower()
            if host == "youtu.be":
                cand = parsed.path.lstrip("/").split("/")[0]
                if _VIDEO_ID_PATTERN.match(cand):
                    return cand
            else:
                qs = _parse_qs(parsed.query)
                v_list = qs.get("v", [])
                if v_list and _VIDEO_ID_PATTERN.match(v_list[0]):
                    return v_list[0]
                m = _re.match(r"^/(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})(?:/|$)", parsed.path)
                if m:
                    return m.group(1)
    except Exception:
        return None
    return None


def _safe_gzip_decompress(raw_bytes: bytes, max_size: int = 5 * 1024 * 1024) -> bytes:
    """Decompress gzip payload with a strict output size cap (zip-bomb defense)."""
    with _gzip.GzipFile(fileobj=_io.BytesIO(raw_bytes)) as gz:
        out = gz.read(max_size + 1)
    if len(out) > max_size:
        raise ValueError("Decompressed payload exceeds size limit")
    return out


def _require_user_auth(request, data=None, allow_admin: bool = False):
    """
    Enforce authenticated user identity and block horizontal IDOR.
    Returns (resolved_user_id, None) or (0, web.Response(401/403)).
    """
    auth_uid = get_authenticated_user_id(request, data)
    raw_target = None
    if isinstance(data, dict):
        raw_target = data.get("tg_user_id")
        if raw_target is None or raw_target == "":
            raw_target = data.get("user_id")
    if raw_target is None or raw_target == "":
        raw_target = request.query.get("tg_user_id") or request.query.get("user_id")

    target_uid = _safe_int(raw_target, 0) if raw_target not in (None, "") else 0

    if not auth_uid:
        if allow_admin and is_admin_request(request):
            if target_uid > 0:
                return target_uid, None
            return 0, web.json_response({"ok": False, "error": "tg_user_id kerak"}, status=400)
        return 0, web.json_response(
            {"ok": False, "error": "Autentifikatsiya talab qilinadi (Ruxsat berilmadi)!"},
            status=401
        )

    if target_uid > 0 and target_uid != auth_uid:
        if allow_admin and is_admin_request(request):
            return target_uid, None
        return 0, web.json_response(
            {"ok": False, "error": "Boshqa foydalanuvchi ma'lumotlariga kirish taqiqlangan!"},
            status=403
        )

    return auth_uid, None


def _compute_live_youtube_stats_sync(tg_user_id: str, channel_id, conn_data: dict):
    """Run blocking Google YouTube Data API & PostgreSQL stats fetch off the asyncio loop."""
    from googleapiclient.discovery import build
    from config import YT_CLIENT_ID, YT_CLIENT_SECRET, OWNER_ID
    from google.oauth2.credentials import Credentials
    from database import get_db, update_yt_channel_metadata
    import psycopg2.extras

    creds = Credentials(
        token=conn_data["access_token"],
        refresh_token=conn_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
    )
    yt = build("youtube", "v3", credentials=creds)

    ch_res = yt.channels().list(part="statistics,snippet,contentDetails", mine=True).execute()
    if not ch_res.get("items"):
        return None

    ch = ch_res["items"][0]
    stats = ch["statistics"]
    snippet = ch["snippet"]

    total_subs = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    total_videos = int(stats.get("videoCount", 0))

    recent_videos = []
    try:
        uploads_id = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
        if uploads_id:
            pl_items = yt.playlistItems().list(
                part="snippet", playlistId=uploads_id, maxResults=10
            ).execute().get("items", [])
            vid_ids = [i["snippet"]["resourceId"]["videoId"] for i in pl_items]
            if vid_ids:
                vids = yt.videos().list(
                    part="statistics,snippet", id=",".join(vid_ids)
                ).execute().get("items", [])
                for v in vids:
                    pub_date = v["snippet"]["publishedAt"][:10]
                    recent_videos.append({
                        "id": v["id"],
                        "title": v["snippet"]["title"][:60],
                        "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                        "views": int(v["statistics"].get("viewCount", 0)),
                        "likes": int(v["statistics"].get("likeCount", 0)),
                        "comments": int(v["statistics"].get("commentCount", 0)),
                        "published": pub_date,
                        "published_at": pub_date,
                    })
    except Exception as e:
        print(f"[api/stats] Video xato: {e}")

    avg_views = sum(v["views"] for v in recent_videos) // max(len(recent_videos), 1)
    avg_likes = sum(v["likes"] for v in recent_videos) // max(len(recent_videos), 1)
    avg_comments = sum(v["comments"] for v in recent_videos) // max(len(recent_videos), 1)
    engagement = round((avg_likes + avg_comments) / max(avg_views, 1) * 100, 2)

    autopost_stats = {"total": 0, "success": 0, "failed": 0}
    conn_db = None
    try:
        conn_db = get_db()
        if conn_db:
            cur = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "SELECT status FROM autopost_history WHERE tg_user_id=%s ORDER BY created_at DESC LIMIT 100",
                (int(tg_user_id),),
            )
            rows = cur.fetchall()
            autopost_stats["total"] = len(rows)
            autopost_stats["success"] = sum(1 for r in rows if r["status"] == "uploaded")
            autopost_stats["failed"] = sum(1 for r in rows if r["status"] == "failed")

            cur.execute(
                "SELECT id, search_query, total_count, completed_count, status FROM autopost_tasks WHERE tg_user_id=%s ORDER BY id DESC LIMIT 1",
                (int(tg_user_id),),
            )
            active_task = cur.fetchone()
            if active_task:
                autopost_stats["active_task"] = {
                    "id": active_task["id"],
                    "query": active_task["search_query"],
                    "total": active_task["total_count"],
                    "completed": active_task["completed_count"],
                    "status": active_task["status"],
                }
            conn_db.close()
    except Exception as e:
        print(f"[api/stats] Autopost tarixi xato: {e}")
        try:
            if conn_db:
                conn_db.close()
        except Exception:
            pass

    ch_title_live = snippet.get("title", "")
    ch_pfp_live = snippet.get("thumbnails", {}).get("medium", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
    try:
        update_yt_channel_metadata(
            tg_user_id=int(tg_user_id),
            yt_channel_id=conn_data.get("yt_channel_id", ""),
            channel_title=ch_title_live,
            channel_thumbnail_url=ch_pfp_live,
            subscriber_count=total_subs,
        )
    except Exception as e_upd:
        print(f"[api/stats] update_yt_channel_metadata xato: {e_upd}")

    return {
        "channel_title": ch_title_live,
        "channel_username": conn_data.get("yt_channel_username", ""),
        "channel_thumbnail": ch_pfp_live,
        "channel_country": snippet.get("country", ""),
        "subscribers": total_subs,
        "total_subscribers": total_subs,
        "total_views": total_views,
        "total_videos": total_videos,
        "avg_views": avg_views,
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "engagement_rate": engagement,
        "autopost": autopost_stats,
        "recent_videos": recent_videos,
        "is_owner": (int(tg_user_id) == OWNER_ID),
        "channel_id": conn_data.get("yt_channel_id", ""),
        "stale": False,
    }


async def _refresh_stats_bg(cache_key: str, tg_user_id: str, channel_id, conn_data: dict):
    if cache_key in _stats_refresh_inflight:
        return
    _stats_refresh_inflight.add(cache_key)
    try:
        fresh = await asyncio.to_thread(_compute_live_youtube_stats_sync, tg_user_id, channel_id, conn_data)
        if fresh:
            _stats_cache[cache_key] = {"data": fresh, "ts": _time.time()}
    except Exception as err:
        print(f"[api/stats bg] error: {err}")
    finally:
        _stats_refresh_inflight.discard(cache_key)


async def handle_api_stats(request):
    """Dashboard uchun real YouTube kanal statistikasi (non-blocking cached, Anti-IDOR himoyalangan)"""
    import json
    global _stats_cache
    uid, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    tg_user_id = str(uid)

    channel_id = request.query.get("channel_id")
    force_refresh = request.query.get("refresh") == "1" or request.query.get("force") == "1"
    cache_key = f"{tg_user_id}_{channel_id or 'default'}"
    cached = _stats_cache.get(cache_key)
    if not force_refresh and cached and (_time.time() - cached["ts"]) < _CACHE_TTL:
        return web.Response(
            text=json.dumps(cached["data"], default=str),
            content_type="application/json",
        )

    conn_data = None
    try:
        from database import get_yt_connection
        from config import OWNER_ID

        conn_data = await asyncio.to_thread(get_yt_connection, int(tg_user_id), channel_id=channel_id)
        if not conn_data or not conn_data.get("access_token"):
            return web.Response(
                text=json.dumps({"error": "not_logged_in"}),
                content_type="application/json",
            )

        # Return stale/DB snapshot immediately on initial page paint and sync live YouTube metrics in background
        if not force_refresh:
            asyncio.create_task(_refresh_stats_bg(cache_key, tg_user_id, channel_id, conn_data))
            if cached and cached.get("data"):
                stale_payload = dict(cached["data"])
                stale_payload["stale"] = True
                return web.Response(text=json.dumps(stale_payload, default=str), content_type="application/json")
            subs = int(conn_data.get("subscriber_count") or 0)
            snapshot = {
                "channel_id": conn_data.get("yt_channel_id", ""),
                "channel_title": conn_data.get("yt_channel_title", ""),
                "channel_username": conn_data.get("yt_channel_username", ""),
                "channel_thumbnail": conn_data.get("channel_thumbnail_url", ""),
                "subscribers": subs,
                "total_subscribers": subs,
                "total_views": 0,
                "total_videos": 0,
                "recent_videos": [],
                "is_owner": (int(tg_user_id) == OWNER_ID),
                "stale": True,
            }
            return web.Response(text=json.dumps(snapshot, default=str), content_type="application/json")

        response_data = await asyncio.to_thread(_compute_live_youtube_stats_sync, tg_user_id, channel_id, conn_data)
        if not response_data:
            return web.Response(
                text=json.dumps({"error": "Kanal topilmadi"}),
                content_type="application/json",
            )

        _stats_cache[cache_key] = {"data": response_data, "ts": _time.time()}
        return web.Response(
            text=json.dumps(response_data, default=str),
            content_type="application/json",
        )
    except Exception as e:
        import traceback
        print(f"[api/stats] Kritik xato: {traceback.format_exc()}")
        try:
            if conn_data:
                from config import OWNER_ID
                fallback_data = {
                    "channel_title": conn_data.get("yt_channel_title", ""),
                    "channel_username": conn_data.get("yt_channel_username", ""),
                    "channel_thumbnail": conn_data.get("channel_thumbnail_url", ""),
                    "subscribers": conn_data.get("subscriber_count", 0),
                    "total_subscribers": conn_data.get("subscriber_count", 0),
                    "total_views": 0,
                    "total_videos": 0,
                    "recent_videos": [],
                    "is_owner": (int(tg_user_id) == OWNER_ID),
                    "stale": False,
                }
                return web.Response(
                    text=json.dumps(fallback_data, default=str),
                    content_type="application/json",
                )
        except Exception:
            pass
        return web.Response(
            text=json.dumps({"error": "Statistikani yuklashda ichki xatolik yuz berdi"}),
            content_type="application/json",
            status=500,
        )


def _render_oauth_status_html(title: str, subtitle: str, badge_label: str = "OAUTH STATUS") -> str:
    from ui_theme import (
        get_editorial_base_css,
        get_fonts_head_html,
        render_editorial_footer,
        render_editorial_navbar,
    )
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{_html.escape(title)} | {_html.escape(BRAND_NAME)}</title>'
        f'<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        f'{get_fonts_head_html()}'
        f'<style>{get_editorial_base_css()}</style></head><body>'
        f'{render_editorial_navbar(active="studio")}'
        f'<main class="md-container" style="padding:56px 24px;">'
        f'<div class="md-card" style="max-width:560px;margin:0 auto;">'
        f'<div class="md-eyebrow" style="margin-bottom:14px;"><span class="md-eyebrow-dot"></span>'
        f'<span>{_html.escape(badge_label)}</span></div>'
        f'<h1 style="font-family:var(--font-display);font-size:28px;font-weight:600;margin-bottom:10px;">'
        f'{_html.escape(title)}</h1>'
        f'<p style="color:var(--ink-2);font-size:15px;margin-bottom:22px;">{subtitle}</p>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;">'
        f'<a class="md-btn md-btn-primary" href="/studio">Open Studio</a>'
        f'<a class="md-btn" href="https://t.me/{_html.escape(get_bot_username())}" target="_blank" rel="noopener noreferrer">Open Telegram Bot</a>'
        f'</div></div></main>{render_editorial_footer()}</body></html>'
    )


async def handle_oauth_youtube_start(request):
    """Launch Google OAuth 2.0 YouTube consent screen directly from the web UI."""
    uid, _ = _require_user_auth(request, allow_admin=True)
    target_uid = int(uid) if uid else 0
    auth_url = await asyncio.to_thread(get_auth_url, target_uid)
    if request.path == "/api/oauth/youtube/url" or request.query.get("format") == "json":
        return web.json_response({"ok": True, "auth_url": auth_url})
    raise web.HTTPFound(location=auth_url)


async def handle_oauth_callback(request):
    """Google OAuth callback — foydalanuvchi ruxsat bergandan keyin Google shu yerga qaytaradi"""
    code = request.query.get("code")
    state = request.query.get("state")
    error = request.query.get("error")

    if error:
        safe_error = _html.escape(str(error)[:200])
        return web.Response(
            text=_render_oauth_status_html(
                "Authorization declined",
                f"{safe_error}. Return to the Telegram bot and run /ytlogin to retry.",
                "OAUTH CANCELLED",
            ),
            content_type="text/html",
        )

    if not code:
        return web.Response(
            text=_render_oauth_status_html(
                "Missing authorization code",
                "No OAuth authorization code was provided in the callback URL.",
                "OAUTH ERROR",
            ),
            content_type="text/html",
        )

    try:
        result = await asyncio.to_thread(exchange_code_with_redirect, code, state)

        tg_user_id = result["tg_user_id"]
        if not tg_user_id:
            cookie_uid, _ = _require_user_auth(request, allow_admin=True)
            if cookie_uid:
                tg_user_id = int(cookie_uid)
        channel_title = result["channel_title"]
        channel_id = result["channel_id"]

        if tg_user_id:
            saved = await asyncio.to_thread(
                save_yt_connection,
                tg_user_id=tg_user_id,
                yt_channel_id=channel_id,
                yt_channel_title=channel_title,
                yt_channel_username=result.get("channel_username", ""),
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                token_expiry=result["token_expiry"],
                channel_thumbnail_url=result.get("channel_thumbnail", ""),
                subscriber_count=result.get("subscriber_count", 0),
            )

            if saved:
                if ytbot_instance:
                    try:
                        await ytbot_instance.send_message(
                            tg_user_id,
                            f"✅ YouTube kanalingiz muvaffaqiyatli ulandi!\n\n"
                            f"📺 Kanal: **{channel_title}**\n"
                            f"🆔 ID: `{channel_id}`\n\n"
                            f"Endi `/autopost` orqali video yuklashingiz mumkin!",
                        )
                    except Exception as e:
                        print(f"Telegram xabar yuborish xatosi: {e}")
            else:
                if ytbot_instance:
                    try:
                        await ytbot_instance.send_message(
                            tg_user_id,
                            "❌ Xatolik: Kanalingiz ma'lumotlar bazasiga saqlanmadi. Iltimos qaytadan `/ytlogin` qilib ko'ring.",
                        )
                    except Exception:
                        pass
                return web.Response(
                    text=_render_oauth_status_html(
                        "Connection save failed",
                        "Could not persist channel credentials. Return to Telegram and run /ytlogin again.",
                        "STORAGE ERROR",
                    ),
                    content_type="text/html",
                )

        safe_title = _html.escape(str(channel_title or ""))
        return web.Response(
            text=_render_oauth_status_html(
                "YouTube channel connected",
                f"Channel: <strong>{safe_title}</strong>. Return to Telegram and use <code>/autopost</code> or open Studio.",
                "CONNECTED",
            ),
            content_type="text/html",
        )

    except Exception as e:
        print(f"OAuth callback xatosi: {e}")
        return web.Response(
            text=_render_oauth_status_html(
                "Authorization failed",
                "Could not complete Google OAuth exchange. Return to Telegram and run /ytlogin.",
                "OAUTH ERROR",
            ),
            content_type="text/html",
            status=400,
        )



async def handle_api_bot_user(request):
    """Foydalanuvchi profil va balans ma'lumotlari (Anti-IDOR himoyalangan)"""
    import json
    uid, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    try:
        from database import get_user_full_details, get_user_vip_info
        from config import OWNER_ID
        
        force_sync = request.query.get("refresh", "0") in ("1", "true")
        details = get_user_full_details(uid, force_sync=force_sync)
        vip_info = get_user_vip_info(uid)
        is_owner = (uid == OWNER_ID or uid == 6735799833)
        
        resp = {
            "ok": True,
            "tg_user_id": uid,
            "first_name": details.get("first_name") or f"Creator #{uid}",
            "last_name": details.get("last_name") or "",
            "username": details.get("username") or "",
            "photo_file_id": details.get("photo_file_id"),
            "photo_url": _build_signed_avatar_url(uid, force_refresh=force_sync),
            "balance_uzs": details.get("balance_uzs", 0),
            "ton_balance": details.get("ton_balance", 0.0),
            "is_vip": bool(vip_info.get("is_vip")),
            "is_owner": is_owner
        }
        return web.Response(text=json.dumps(resp, default=str), content_type="application/json")
    except Exception as e:
        print(f"[api/bot_user] error: {e}")
        return web.Response(text=json.dumps({"ok": False, "error": "Profil ma'lumotlarini olishda xatolik yuz berdi"}), content_type="application/json", status=500)

async def handle_api_sync_profile(request):
    """Telegram profil ma'lumotlarini majburiy qayta sinxronlash (Anti-IDOR himoyalangan)"""
    import json
    try:
        data = {}
        if request.method == "POST":
            try:
                data = await request.json()
            except Exception:
                data = {}
        uid, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        user_context = {
            "first_name": str(data.get("first_name") or request.query.get("first_name") or "")[:64] or None,
            "last_name": str(data.get("last_name") or request.query.get("last_name") or "")[:64] or None,
            "username": str(data.get("username") or request.query.get("username") or "")[:64] or None,
            "photo_url": str(data.get("photo_url") or request.query.get("photo_url") or "")[:512] or None,
            "photo_file_id": str(data.get("photo_file_id") or request.query.get("photo_file_id") or "")[:160] or None
        }
        from database import sync_tg_user_profile, get_user_full_details
        sync_tg_user_profile(uid, user_context=user_context)
        details = get_user_full_details(uid, force_sync=False, user_context=user_context)
        return web.Response(text=json.dumps({"ok": True, "profile": details}, default=str), content_type="application/json")
    except Exception as e:
        print(f"[api/user/sync-profile] error: {e}")
        return web.Response(text=json.dumps({"ok": False, "error": "Profilni sinxronlashda xatolik yuz berdi"}), content_type="application/json", status=500)

async def handle_api_channel_select(request):
    """Foydalanuvchi faol YouTube kanalini tanlashi (Anti-IDOR + Channel Ownership tekshiruvi)"""
    import json
    global _stats_cache
    try:
        data = await request.json()
    except Exception:
        data = {}
    uid, auth_err = _require_user_auth(request, data)
    if auth_err:
        return auth_err
    channel_id = str(data.get("channel_id") or request.query.get("channel_id") or "").strip()
    if not channel_id:
        return web.Response(
            text=json.dumps({"ok": False, "error": "channel_id kerak"}),
            content_type="application/json",
            status=400
        )
    try:
        from database import set_default_account, get_all_yt_connections
        connections = get_all_yt_connections(uid) or []
        owned_ids = {str(c.get("yt_channel_id", "")) for c in connections}
        if owned_ids and channel_id not in owned_ids:
            return web.json_response({"ok": False, "error": "Ushbu kanal sizning hisobingizga ulanmagan!"}, status=403)
        ok = set_default_account(uid, channel_id)
        # Yangi tanlangan kanalning yangi statistikasi ko'rinishi uchun keshni tozalash
        for k in list(_stats_cache.keys()):
            if str(k).startswith(f"{uid}_"):
                _stats_cache.pop(k, None)
        return web.Response(
            text=json.dumps({"ok": ok, "selected_channel_id": channel_id}),
            content_type="application/json"
        )
    except Exception as e:
        print(f"[api/channels/select] error: {e}")
        return web.Response(
            text=json.dumps({"ok": False, "error": "Kanalni tanlashda xatolik yuz berdi"}),
            content_type="application/json",
            status=500
        )

async def handle_api_channels(request):
    """Foydalanuvchining barcha ulangan kanallari (Anti-IDOR himoyalangan)"""
    import json
    tg_id, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    try:
        from database import get_all_yt_connections, get_default_account
        connections = get_all_yt_connections(tg_id)
        default_ch_id = get_default_account(tg_id)
        
        channels = []
        for c in connections:
            ch_id = c.get("yt_channel_id", "")
            channels.append({
                "channel_id": ch_id,
                "channel_title": c.get("yt_channel_title", "Unknown"),
                "channel_username": c.get("yt_channel_username", ""),
                "thumbnail_url": c.get("channel_thumbnail_url", ""),
                "subscriber_count": c.get("subscriber_count", 0),
                "is_default": bool(default_ch_id and default_ch_id == ch_id)
            })
        return web.Response(text=json.dumps({"channels": channels, "default_channel_id": default_ch_id}), content_type="application/json")
    except Exception as e:
        print(f"[api/channels] error: {e}")
        return web.Response(text=json.dumps({"error": "Kanallarni yuklashda xatolik yuz berdi"}), content_type="application/json", status=500)

async def handle_api_autopost_tasks(request):
    """Foydalanuvchining barcha autopost vazifalari (Anti-IDOR himoyalangan)"""
    import json
    uid, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    try:
        from database import get_autopost_tasks
        tasks = get_autopost_tasks(uid)
        result = []
        for t in tasks:
            result.append({
                "id": t.get("id"),
                "channel_id": t.get("yt_channel_id"),
                "search_query": t.get("search_query"),
                "video_type": t.get("video_type"),
                "total_count": t.get("total_count"),
                "completed_count": t.get("completed_count"),
                "status": t.get("status"),
                "created_at": str(t.get("created_at"))
            })
        return web.Response(text=json.dumps({"tasks": result}), content_type="application/json")
    except Exception as e:
        print(f"[api/autopost-tasks] error: {e}")
        return web.Response(text=json.dumps({"error": "Autopost vazifalarini yuklashda xatolik yuz berdi"}), content_type="application/json", status=500)

_video_search_cache = {}  # {cache_key: {"videos": [...], "ts": float}}

async def handle_api_videos(request):
    """YouTube'dan video qidirish (keshlangan va quota-safe)"""
    import json
    q = request.query.get("q", "").strip()[:200]
    max_results = max(1, min(25, _safe_int(request.query.get("maxResults", "12"), 12)))
    video_type = request.query.get("type", "")  # "short" or ""
    if video_type not in ("", "short"):
        video_type = ""
    
    if not q:
        return web.Response(text=json.dumps({"error": "q param kerak", "videos": []}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
        
    cache_key = f"{q.lower()}_{video_type}_{max_results}"
    cached = _video_search_cache.get(cache_key)
    if cached and (_time.time() - cached["ts"]) < 1800:
        return web.Response(text=json.dumps({"videos": cached["videos"]}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
        
    try:
        from config import build_youtube_api
        yt = build_youtube_api()
        
        search_params = {
            "part": "snippet",
            "q": q,
            "type": "video",
            "maxResults": min(max_results, 25),
            "order": "relevance"
        }
        if video_type == "short":
            search_params["videoDuration"] = "short"
        
        results = yt.search().list(**search_params).execute()
        
        video_ids = [item["id"]["videoId"] for item in results.get("items", []) if item["id"].get("videoId")]
        
        videos = []
        if video_ids:
            stats_res = yt.videos().list(part="statistics,snippet,contentDetails", id=",".join(video_ids)).execute()
            for v in stats_res.get("items", []):
                videos.append({
                    "id": v["id"],
                    "title": v["snippet"]["title"],
                    "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                    "channel": v["snippet"]["channelTitle"],
                    "views": int(v["statistics"].get("viewCount", 0)),
                    "likes": int(v["statistics"].get("likeCount", 0)),
                    "comments": int(v["statistics"].get("commentCount", 0)),
                    "published": v["snippet"]["publishedAt"][:10],
                    "duration": v.get("contentDetails", {}).get("duration", ""),
                })
        
        if not videos:
            from autopost import search_youtube_candidates
            videos = await asyncio.to_thread(search_youtube_candidates, q, max_results, video_type or "shorts")

        _video_search_cache[cache_key] = {"videos": videos, "ts": _time.time()}
        return web.Response(text=json.dumps({"videos": videos}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        err_msg = str(e)
        try:
            from autopost import search_youtube_candidates
            fallback_videos = await asyncio.to_thread(search_youtube_candidates, q, max_results, video_type or "shorts")
            if fallback_videos:
                _video_search_cache[cache_key] = {"videos": fallback_videos, "ts": _time.time()}
                return web.Response(text=json.dumps({"videos": fallback_videos, "source": "yt_dlp"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
        except Exception:
            pass
        if "quotaExceeded" in err_msg or "rateLimitExceeded" in err_msg or "403" in err_msg:
            return web.Response(text=json.dumps({
                "videos": [],
                "warning": "YouTube API kunlik kvotasi yetarli emas. Iltimos keyinroq qayta urinib ko'ring."
            }), content_type="application/json")
        print(f"[api/videos] error: {err_msg}")
        return web.Response(text=json.dumps({"error": "Video qidirishda xatolik yuz berdi", "videos": []}), content_type="application/json", status=500)

async def handle_api_trending(request):
    """Trendagidagi videolar"""
    import json
    region = request.query.get("region", "UZ").strip().upper()
    if not _REGION_CODE_PATTERN.match(region):
        region = "UZ"
    try:
        from config import build_youtube_api
        yt = build_youtube_api()
        
        results = yt.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=region, maxResults=12).execute()
        videos = []
        for v in results.get("items", []):
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                "channel": v["snippet"]["channelTitle"],
                "views": int(v["statistics"].get("viewCount", 0)),
                "likes": int(v["statistics"].get("likeCount", 0)),
                "published": v["snippet"]["publishedAt"][:10],
            })
        return web.Response(text=json.dumps({"videos": videos}), content_type="application/json")
    except Exception as e:
        print(f"[api/trending] error: {e}")
        return web.Response(text=json.dumps({"error": "Trend videolarni yuklashda xatolik yuz berdi"}), content_type="application/json", status=500)

async def handle_api_health_score(request):
    """Channel Health Score (100 ballik, Anti-IDOR himoyalangan)"""
    import json
    uid, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    tg_user_id = str(uid)
    try:
        from database import get_yt_connection
        from googleapiclient.discovery import build
        from config import YT_CLIENT_ID, YT_CLIENT_SECRET
        from google.oauth2.credentials import Credentials

        conn_data = get_yt_connection(int(tg_user_id))
        if not conn_data:
            return web.Response(text=json.dumps({"error": "not_logged_in"}), content_type="application/json", status=403)

        creds = Credentials(token=conn_data["access_token"], refresh_token=conn_data["refresh_token"], token_uri="https://oauth2.googleapis.com/token", client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET)
        yt = build("youtube", "v3", credentials=creds)

        ch_res = yt.channels().list(part="statistics,snippet,contentDetails,brandingSettings", mine=True).execute()
        if not ch_res.get("items"):
            return web.Response(text=json.dumps({"error": "Kanal topilmadi"}), content_type="application/json")

        ch = ch_res["items"][0]
        stats = ch["statistics"]
        snippet = ch["snippet"]
        
        total_subs = int(stats.get("subscriberCount", 0))
        total_views = int(stats.get("viewCount", 0))
        total_videos = int(stats.get("videoCount", 0))

        # Oxirgi 20 ta video analizi
        recent_videos = []
        uploads_id = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
        if uploads_id:
            pl_items = yt.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=20).execute().get("items", [])
            vid_ids = [i["snippet"]["resourceId"]["videoId"] for i in pl_items]
            if vid_ids:
                vids = yt.videos().list(part="statistics,snippet,contentDetails", id=",".join(vid_ids)).execute().get("items", [])
                for v in vids:
                    recent_videos.append({
                        "views": int(v["statistics"].get("viewCount", 0)),
                        "likes": int(v["statistics"].get("likeCount", 0)),
                        "comments": int(v["statistics"].get("commentCount", 0)),
                        "title": v["snippet"]["title"],
                        "description": v["snippet"].get("description", ""),
                        "tags": v["snippet"].get("tags", []),
                        "published": v["snippet"]["publishedAt"],
                    })

        # Health Score hisoblash
        scores = {}
        
        # 1. SEO Score (title, description, tags)
        seo_total = 0
        for v in recent_videos:
            s = 0
            if len(v["title"]) > 20: s += 3
            if len(v["title"]) < 70: s += 2
            if len(v.get("description", "")) > 100: s += 3
            if v.get("tags") and len(v["tags"]) >= 5: s += 2
            seo_total += s
        scores["seo"] = min(round(seo_total / max(len(recent_videos), 1) * 10), 100) if recent_videos else 0
        
        # 2. Engagement Score
        avg_views = sum(v["views"] for v in recent_videos) / max(len(recent_videos), 1)
        avg_likes = sum(v["likes"] for v in recent_videos) / max(len(recent_videos), 1)
        avg_comments = sum(v["comments"] for v in recent_videos) / max(len(recent_videos), 1)
        engagement_rate = (avg_likes + avg_comments) / max(avg_views, 1) * 100
        scores["engagement"] = min(round(engagement_rate * 10), 100)
        
        # 3. Consistency Score (yuklash muntazamligi)
        from datetime import datetime
        if len(recent_videos) >= 2:
            dates = sorted([datetime.fromisoformat(v["published"].replace("Z", "+00:00")) for v in recent_videos])
            gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_gap = sum(gaps) / len(gaps)
            if avg_gap <= 2: scores["consistency"] = 100
            elif avg_gap <= 7: scores["consistency"] = 80
            elif avg_gap <= 14: scores["consistency"] = 60
            elif avg_gap <= 30: scores["consistency"] = 40
            else: scores["consistency"] = 20
        else:
            scores["consistency"] = 10
        
        # 4. Growth Score
        if total_subs > 0:
            views_per_sub = total_views / total_subs
            if views_per_sub > 100: scores["growth"] = 90
            elif views_per_sub > 50: scores["growth"] = 70
            elif views_per_sub > 20: scores["growth"] = 50
            else: scores["growth"] = 30
        else:
            scores["growth"] = 10
        
        # 5. Thumbnail/Brand Score (avatar, banner bor/yo'q)
        brand_score = 50
        if snippet.get("thumbnails", {}).get("high"): brand_score += 20
        branding = ch.get("brandingSettings", {}).get("image", {})
        if branding.get("bannerExternalUrl"): brand_score += 30
        scores["branding"] = min(brand_score, 100)
        
        # Umumiy ball
        overall = round((scores["seo"] + scores["engagement"] + scores["consistency"] + scores["growth"] + scores["branding"]) / 5)
        
        # Tavsiyalar
        tips = []
        if scores["seo"] < 60: tips.append("SEO yaxshilang: Har bir videoga 10+ tag qo'shing, sarlavhani 40-65 belgi qiling")
        if scores["engagement"] < 50: tips.append("Engagement oshiring: CTA (Call to Action) qo'shing va izohchilar bilan muloqot qiling")
        if scores["consistency"] < 60: tips.append("Muntazam yuklang: Haftada kamida 2-3 ta video yuklashga harakat qiling")
        if scores["growth"] < 50: tips.append("O'sish: SEO va trending mavzularga ko'proq e'tibor bering")
        if scores["branding"] < 70: tips.append("Branding: Professional banner va avatar qo'ying")
        
        return web.Response(text=json.dumps({
            "overall": overall,
            "scores": scores,
            "tips": tips,
            "channel_title": snippet.get("title", ""),
            "subscribers": total_subs,
            "total_views": total_views,
            "total_videos": total_videos,
            "engagement_rate": round(engagement_rate, 2),
        }, default=str), content_type="application/json")
    except Exception as e:
        import traceback
        print(f"Health Score Error: {traceback.format_exc()}")
        return web.Response(text=json.dumps({"error": "Kanal tahlilida xatolik yuz berdi"}), content_type="application/json", status=500)

async def handle_api_best_time(request):
    """Eng yaxshi yuklash vaqti (Anti-IDOR himoyalangan)"""
    import json
    uid, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    tg_user_id = str(uid)
    try:
        from database import get_yt_connection
        from googleapiclient.discovery import build
        from config import YT_CLIENT_ID, YT_CLIENT_SECRET
        from google.oauth2.credentials import Credentials
        from datetime import datetime
        from collections import defaultdict

        conn_data = get_yt_connection(int(tg_user_id))
        if not conn_data:
            return web.Response(text=json.dumps({"error": "not_logged_in"}), content_type="application/json")

        creds = Credentials(token=conn_data["access_token"], refresh_token=conn_data["refresh_token"], token_uri="https://oauth2.googleapis.com/token", client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET)
        yt = build("youtube", "v3", credentials=creds)

        ch_res = yt.channels().list(part="contentDetails", mine=True).execute()
        if not ch_res.get("items"):
            return web.Response(text=json.dumps({"error": "Kanal topilmadi"}), content_type="application/json")

        uploads_id = ch_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl_items = yt.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=50).execute().get("items", [])
        vid_ids = [i["snippet"]["resourceId"]["videoId"] for i in pl_items]
        
        hour_views = defaultdict(list)
        day_views = defaultdict(list)
        
        if vid_ids:
            vids = yt.videos().list(part="statistics,snippet", id=",".join(vid_ids[:50])).execute().get("items", [])
            for v in vids:
                pub = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
                views = int(v["statistics"].get("viewCount", 0))
                hour_views[pub.hour].append(views)
                day_views[pub.strftime("%A")].append(views)
        
        best_hours = sorted(hour_views.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0, reverse=True)[:5]
        best_days = sorted(day_views.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0, reverse=True)

        return web.Response(text=json.dumps({
            "best_hours": [{"hour": h, "avg_views": round(sum(v)/len(v))} for h, v in best_hours],
            "best_days": [{"day": d, "avg_views": round(sum(v)/len(v))} for d, v in best_days],
            "total_analyzed": len(vid_ids),
        }), content_type="application/json")
    except Exception as e:
        print(f"[api/best-time] error: {e}")
        return web.Response(text=json.dumps({"error": "Eng yaxshi vaqtni hisoblashda xatolik yuz berdi"}), content_type="application/json", status=500)

async def handle_api_autopost_task_details(request):
    """Autopost vazifasi tafsilotlari: tarixi + qidiruv bo'yicha namuna videolar ro'yxati."""
    tg_user_id, auth_err = _require_user_auth(request, allow_admin=True)
    if auth_err:
        return auth_err
    tid_str = request.match_info.get("task_id", "").strip()
    if not tid_str.isdigit():
        return web.json_response({"ok": False, "error": "Noto'g'ri task_id"}, status=400)
    task_id = int(tid_str)

    from database import get_autopost_task_by_id, get_autopost_history
    from autopost import search_youtube_candidates

    task = get_autopost_task_by_id(task_id)
    if not task:
        return web.json_response({"ok": False, "error": "Vazifa topilmadi"}, status=404)
    if int(task.get("tg_user_id", 0)) != int(tg_user_id) and not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat yo'q"}, status=403)

    history = get_autopost_history(task_id) or []
    hist_list = []
    for h in history:
        row = dict(h)
        if row.get("created_at"):
            row["created_at"] = str(row["created_at"])
        hist_list.append(row)

    task_out = dict(task)
    for dt_k in ("created_at", "updated_at"):
        if task_out.get(dt_k):
            task_out[dt_k] = str(task_out[dt_k])

    candidates = await asyncio.to_thread(
        search_youtube_candidates,
        str(task.get("search_query") or ""),
        8,
        str(task.get("video_type") or "shorts"),
    )
    return web.json_response({"ok": True, "task": task_out, "history": hist_list, "candidates": candidates})


async def handle_api_autopost_task_action(request):
    """Autopost vazifasini ishga tushirish, qayta urinish yoki o'chirish (GitHub Actions / Local)."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON"}, status=400)

    tg_user_id, auth_err = _require_user_auth(request, data, allow_admin=True)
    if auth_err:
        return auth_err

    task_id = _safe_int(data.get("task_id"), 0)
    action = str(data.get("action") or "").strip().lower()
    if task_id <= 0 or action not in ("run_now", "retry", "delete"):
        return web.json_response({"ok": False, "error": "Noto'g'ri task_id yoki action"}, status=400)

    from database import get_autopost_task_by_id, update_autopost_task, delete_autopost_task, get_db
    task = get_autopost_task_by_id(task_id)
    if not task:
        return web.json_response({"ok": False, "error": "Vazifa topilmadi"}, status=404)
    if int(task.get("tg_user_id", 0)) != int(tg_user_id) and not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat yo'q"}, status=403)

    if action == "delete":
        ok_del = delete_autopost_task(task_id, int(task["tg_user_id"]))
        return web.json_response({"ok": ok_del, "deleted": ok_del})

    selected_ids = data.get("selected_video_ids") or []
    if isinstance(selected_ids, list) and selected_ids:
        clean_ids = [v for v in (_extract_valid_video_id(str(x)) for x in selected_ids[:20]) if v]
        if clean_ids:
            conn = get_db()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE autopost_tasks SET search_query = %s, total_count = %s, updated_at = NOW() WHERE id = %s",
                        ("__IDS__:" + ",".join(clean_ids), len(clean_ids), task_id),
                    )
                    conn.commit()
                finally:
                    conn.close()

    update_autopost_task(task_id, status="pending")

    use_gh = bool(data.get("use_github")) or os.getenv("GITHUB_AUTOPOST_OFFLOAD", "false").lower() == "true"
    dispatched = "local"
    if use_gh:
        try:
            from worker_client import trigger_github_worker
            ok_gh, _ = await trigger_github_worker("autopost", f"autopost://task/{task_id}", str(task["tg_user_id"]))
            if ok_gh:
                dispatched = "github_actions"
        except Exception:
            pass

    if dispatched == "local":
        asyncio.create_task(dispatch_or_run_autopost(task_id))

    return web.json_response({"ok": True, "status": "pending", "dispatch": dispatched})


async def handle_api_video_formats(request):
    """Video uchun mavjud formatlarni olish (fallback va tezkor response bilan)"""
    import json
    raw_video_id = request.query.get("video_id") or request.query.get("id")
    if not raw_video_id:
        return web.json_response({"error": "video_id kerak"}, status=400)
    
    video_id = _extract_valid_video_id(raw_video_id)
    if not video_id:
        return web.json_response({"error": "Noto'g'ri YouTube video_id formati"}, status=400)
    
    all_resolutions = [
        {"label": "360p", "value": "360", "resolution": "360p", "format_id": "360", "available": True},
        {"label": "480p", "value": "480", "resolution": "480p", "format_id": "480", "available": True},
        {"label": "720p (HD)", "value": "720", "resolution": "720p", "format_id": "720", "available": True},
        {"label": "1080p (FHD)", "value": "1080", "resolution": "1080p", "format_id": "1080", "available": True},
        {"label": "1440p (2K)", "value": "1440", "resolution": "1440p", "format_id": "1440", "available": True},
        {"label": "2160p (4K)", "value": "2160", "resolution": "2160p", "format_id": "2160", "available": True},
        {"label": "4320p (8K)", "value": "4320", "resolution": "4320p", "format_id": "4320", "available": True},
        {"label": "MP3 (Audio)", "value": "mp3", "resolution": "MP3", "format_id": "mp3", "available": True},
    ]

    title = f"YouTube Video ({video_id})"
    duration = 0
    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    try:
        import asyncio
        import os
        import httpx
        
        # Use fast, official YouTube oEmbed API for metadata (ZERO bot detection & NO cookies needed!)
        try:
            async with httpx.AsyncClient(timeout=3.5) as http_client:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                oe_resp = await http_client.get(oembed_url)
                if oe_resp.status_code == 200:
                    oe_data = oe_resp.json()
                    title = oe_data.get("title") or title
                    thumbnail = oe_data.get("thumbnail_url") or thumbnail
        except Exception as oe_err:
            pass

        # If oEmbed succeeded, return formats immediately without invoking yt_dlp on Render
        if title != f"YouTube Video ({video_id})":
            return web.json_response({
                "ok": True,
                "title": title,
                "duration": duration,
                "thumbnail": thumbnail,
                "formats": all_resolutions,
            }, headers={"Access-Control-Allow-Origin": "*"})

        return web.json_response({
            "ok": True,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "formats": all_resolutions,
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"handle_api_video_formats fallback notice: {e}")
        return web.json_response({
            "ok": True,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "formats": all_resolutions,
            "fallback": True
        }, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_download_file(request):
    """Video yuklab olish va stream qilish (Multi-tier bypass, mobile/VR client priority, safe 200 fallback)"""
    import json
    import asyncio
    import glob
    import os
    import time
    import random
    import re
    from aiohttp import web

    try:
        raw_video_id = request.query.get("video_id", "").strip()
        resolution = str(request.query.get("resolution", "720")).lower().strip()
        if resolution.endswith("p") and resolution[:-1].isdigit():
            resolution = resolution[:-1]
        if resolution not in _ALLOWED_DL_RESOLUTIONS:
            return web.json_response({"ok": False, "error": "Noto'g'ri format (resolution) parametri"}, status=400)

        if not raw_video_id:
            return web.json_response({"ok": False, "error": "video_id kerak"}, status=400)

        # Strict 11-char YouTube video ID validation (blocks SSRF, Path Traversal, Header/HTML injection)
        video_id = _extract_valid_video_id(raw_video_id)
        if not video_id:
            return web.json_response({"ok": False, "error": "Noto'g'ri YouTube video_id"}, status=400)

        # Authentication check: session/WebApp auth OR valid HMAC download signature OR valid reseller API key
        target_chat_id = get_authenticated_user_id(request)
        q_uid = _safe_int(request.query.get("tg_user_id") or request.query.get("user_id"), 0)

        if target_chat_id:
            if q_uid > 0 and q_uid != target_chat_id and not is_admin_request(request):
                return web.json_response({"ok": False, "error": "Boshqa foydalanuvchi nomidan yuklab olish taqiqlangan!"}, status=403)
        else:
            # Check short-lived signed download token (issued by reseller_api.py)
            sig = request.query.get("sig", "").strip()
            exp = request.query.get("exp", "").strip()
            from crypto_auth import verify_download_signature
            if sig and exp and q_uid > 0 and verify_download_signature(video_id, resolution, q_uid, exp, sig):
                target_chat_id = q_uid
            else:
                # Check Reseller API key header
                api_key = request.headers.get("X-API-Key", "").strip()
                if api_key:
                    from database import get_user_by_api_key
                    api_user = get_user_by_api_key(api_key)
                    if api_user and api_user.get("is_active", True):
                        target_chat_id = int(api_user["tg_user_id"])

        if not target_chat_id:
            return web.json_response({"ok": False, "error": "Yuklab olish uchun autentifikatsiya talab qilinadi!"}, status=401)

        url = f"https://www.youtube.com/watch?v={video_id}"
        os.makedirs("downloads", exist_ok=True)
        rnd_suffix = f"{int(time.time())}_{random.randint(1000, 9999)}"
        filename = f"downloads/webdl_{video_id}_{rnd_suffix}"

        # Determine format specifier
        if resolution == "mp3":
            fmt_spec = 'b/best/18/140'
            postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        elif resolution in ["best", "max"]:
            fmt_spec = 'bestvideo+140/bestvideo+bestaudio/18/22/b/best'
            postprocessors = []
        else:
            try:
                h = int(resolution.replace("p", ""))
                fmt_spec = f'bestvideo[height<={h}]+140/bestvideo[height<={h}]+bestaudio/best[height<={h}]/18/22/b/best'
            except (ValueError, TypeError):
                fmt_spec = 'bestvideo+140/bestvideo+bestaudio/18/22/b/best'
            postprocessors = []

        # Helper function to find downloaded file
        def _find_file(base_prefix):
            base_name = os.path.basename(base_prefix)
            base_clean = os.path.splitext(base_name)[0]
            if os.path.exists("downloads"):
                for f in os.listdir("downloads"):
                    if f.startswith(base_clean) and not f.endswith(".part") and not f.endswith(".ytdl"):
                        cand = os.path.join("downloads", f)
                        if os.path.exists(cand) and os.path.getsize(cand) > 0:
                            return cand
            return None

        # Helper function to return file response
        def _make_file_response(found_path):
            ext = os.path.splitext(found_path)[1].lstrip(".").lower() or ("mp3" if resolution == "mp3" else "mp4")
            content_type = "audio/mpeg" if ext == "mp3" else ("audio/mp4" if ext == "m4a" else "video/mp4")
            dl_name = f"video_{video_id}_{resolution}.{ext}"

            response = web.FileResponse(found_path, headers={
                "Content-Disposition": f'attachment; filename="{dl_name}"',
                "Content-Type": content_type,
            })

            async def cleanup_later():
                await asyncio.sleep(90)
                try:
                    if os.path.exists(found_path):
                        os.remove(found_path)
                except Exception:
                    pass
            asyncio.create_task(cleanup_later())
            return response

        import yt_dlp

        # =========================================================================
        # MANDATORY CLOUD OFFLOAD: 24/7 GitHub Actions 7GB RAM Runner
        # Downloads MUST run on GitHub Actions runner with PO Token Provider,
        # NEVER locally on Render (512MB RAM & datacenter IP blocked by YouTube).
        # =========================================================================
        from worker_client import dispatch_task
        from config import BOT_TOKEN

        # 1. Inform user in Telegram chat immediately
        try:
            import httpx
            async def _notify_tg():
                try:
                    async with httpx.AsyncClient(timeout=4.0) as cl:
                        await cl.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": target_chat_id,
                                "text": (
                                    f"⏳ <b>Video yuklab olinmoqda...</b>\n\n"
                                    f"🎬 Video ID: <code>{video_id}</code>\n"
                                    f"📐 Sifat: <b>{resolution}</b>\n"
                                    f"☁️ <b>{BRAND_NAME} Cloud Worker</b> orqali tayyorlanmoqda va bir necha soniyada shu yerga yuboriladi!"
                                ),
                                "parse_mode": "HTML"
                            }
                        )
                except Exception:
                    pass
            asyncio.create_task(_notify_tg())
        except Exception:
            pass

        # 2. Dispatch to GitHub Actions
        try:
            asyncio.create_task(dispatch_task(
                task_type="download",
                url=url,
                chat_id=target_chat_id,
                format=resolution,
                caption=f"🎬 <b>Yuklab olingan video</b> ({video_id})\n📐 Sifat: {resolution}\n⚡ <i>{BRAND_NAME} Cloud Worker</i>",
                bot_token=BOT_TOKEN
            ))
        except Exception as gh_err:
            print(f"Cloud worker dispatch notice for user {target_chat_id}: {gh_err}")

        # 3. Return immediate friendly response to WebApp iframe
        brand_esc = _html.escape(BRAND_NAME)
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{brand_esc} • Video Yuklanmoqda</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Inter Tight', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #000000; color: #FFFFFF; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; text-align: center; }}
        .card {{ background: #0E0E10; border: 1px solid rgba(255, 255, 255, 0.12); border-top: 3px solid #FF5A1F; border-radius: 16px; padding: 32px 24px; max-width: 420px; box-shadow: 0 20px 50px rgba(0,0,0,0.75); }}
        h2 {{ margin: 0 0 12px; font-size: 20px; color: #FFFFFF; font-weight: 700; letter-spacing: -0.02em; }}
        p {{ color: #A1A1AA; font-size: 14px; line-height: 1.5; margin: 0 0 20px; }}
        b {{ color: #FF5A1F; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Video Yuklanmoqda</h2>
        <p>Video <b>{brand_esc} Cloud Worker</b> orqali yuklanmoqda va to'g'ridan-to'g'ri Telegram botingizga yuboriladi!</p>
        <p style="font-size: 12px; color: #A1A1AA; margin-bottom: 0;">Telegram bot chatini tekshiring.</p>
    </div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html", status=200)

        # =========================================================================
        # TIER 1: Clean High-Speed VR/Mobile Bypass (NO COOKIES!)
        # player_client: ['android_vr', 'android', 'tv_embedded']
        # =========================================================================
        try:
            ydl_opts_clean = {
                'outtmpl': filename + '.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'format': fmt_spec,
                'socket_timeout': 15,
                'retries': 2,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_vr', 'android', 'tv_embedded'],
                    }
                }
            }
            if postprocessors:
                ydl_opts_clean['postprocessors'] = postprocessors

            def _download_clean():
                with yt_dlp.YoutubeDL(ydl_opts_clean) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(_download_clean)
            found = _find_file(filename)
            if found:
                return _make_file_response(found)
        except Exception as e_clean:
            print(f"Tier 1 (Clean VR/Mobile) notice for {video_id}: {e_clean}")

        # =========================================================================
        # TIER 2: Fallback to Flexible Format (Clean No Cookies)
        # =========================================================================
        try:
            ydl_opts_flex = {
                'outtmpl': filename + '_flex.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'format': 'b/best' if resolution == "mp3" else '18/22/b/best',
                'socket_timeout': 15,
                'retries': 2,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_vr', 'android', 'tv_embedded'],
                    }
                }
            }
            if postprocessors:
                ydl_opts_flex['postprocessors'] = postprocessors

            def _download_flex():
                with yt_dlp.YoutubeDL(ydl_opts_flex) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(_download_flex)
            found = _find_file(filename + '_flex')
            if found:
                return _make_file_response(found)
        except Exception as e_flex:
            print(f"Tier 2 (Flexible Clean) notice for {video_id}: {e_flex}")

        # =========================================================================
        # TIER 3: Authenticated User Cookies (Only if User Has Cookies in DB)
        # Never wipe user cookies on bot error!
        # =========================================================================
        cookie_path = None
        if tg_user_id:
            try:
                from database import get_user_cookies
                user_cookies = get_user_cookies(int(tg_user_id), fallback_to_any=False)
                if user_cookies:
                    cookie_path = f"downloads/cookies_dl_{tg_user_id}.txt"
                    with open(cookie_path, "w", encoding="utf-8") as f:
                        f.write(user_cookies)

                    ydl_opts_cookies = {
                        'outtmpl': filename + '_cookie.%(ext)s',
                        'quiet': True,
                        'no_warnings': True,
                        'format': fmt_spec if resolution != "mp3" else 'b/best',
                        'cookiefile': cookie_path,
                        'socket_timeout': 15,
                        'retries': 2,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['android_vr', 'android', 'tv_embedded'],
                            }
                        }
                    }
                    if postprocessors:
                        ydl_opts_cookies['postprocessors'] = postprocessors

                    def _download_cookie():
                        with yt_dlp.YoutubeDL(ydl_opts_cookies) as ydl:
                            ydl.download([url])

                    try:
                        await asyncio.to_thread(_download_cookie)
                        found = _find_file(filename + '_cookie')
                        if found:
                            return _make_file_response(found)
                    except Exception as e_ck:
                        print(f"Tier 3 cookie download notice for user {tg_user_id}: {e_ck}")
            except Exception as e_cookie_tier:
                print(f"Tier 3 (User Cookies) notice for {video_id}: {e_cookie_tier}")
            finally:
                if cookie_path and os.path.exists(cookie_path):
                    try:
                        os.remove(cookie_path)
                    except Exception:
                        pass

        # =========================================================================
        # TIER 4: Direct Format Stream Proxy (From Google CDN via StreamResponse)
        # Guarantees file download header (Content-Disposition: attachment)
        # =========================================================================
        try:
            ydl_opts_info = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 8,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_vr', 'android', 'tv_embedded'],
                    }
                }
            }
            def _extract_direct():
                with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await asyncio.to_thread(_extract_direct)
            formats = info.get("formats", []) if info else []

            direct_url = None
            stream_ext = "mp4"
            if resolution == "mp3":
                audio_fmts = [f for f in formats if f.get("acodec") != "none" and f.get("url")]
                if audio_fmts:
                    # Prefer format 140 (m4a/aac) or highest abr
                    f140 = next((f for f in audio_fmts if f.get("format_id") == "140"), None)
                    chosen = f140 or sorted(audio_fmts, key=lambda x: x.get("abr") or 0, reverse=True)[0]
                    direct_url = chosen.get("url")
                    stream_ext = chosen.get("ext") or "m4a"
            else:
                # Progressive combined mp4 stream (contains both video and audio, e.g. format 18)
                progressive = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url")]
                if progressive:
                    direct_url = progressive[-1].get("url")
                    stream_ext = progressive[-1].get("ext") or "mp4"
                elif formats:
                    video_fmts = [f for f in formats if f.get("url")]
                    if video_fmts:
                        direct_url = video_fmts[-1].get("url")
                        stream_ext = video_fmts[-1].get("ext") or "mp4"

            if direct_url:
                import aiohttp
                dl_name = f"video_{video_id}_{resolution}.{stream_ext}"
                content_type = "audio/mpeg" if stream_ext == "mp3" else ("audio/mp4" if stream_ext == "m4a" else "video/mp4")

                # Stream directly to browser with attachment Content-Disposition header
                stream_response = web.StreamResponse(
                    status=200,
                    headers={
                        "Content-Type": content_type,
                        "Content-Disposition": f'attachment; filename="{dl_name}"',
                    }
                )
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
                    async with session.get(direct_url) as upstream:
                        if upstream.status == 200:
                            if upstream.content_length:
                                stream_response.content_length = upstream.content_length
                            await stream_response.prepare(request)
                            async for chunk in upstream.content.iter_chunked(65536):
                                await stream_response.write(chunk)
                            return stream_response
                        else:
                            # If direct stream returned redirect or forbidden, raise HTTPFound to let browser handle
                            raise web.HTTPFound(direct_url)
        except web.HTTPFound:
            raise
        except Exception as e_direct:
            print(f"Tier 4 (Direct Stream Proxy) notice for {video_id}: {e_direct}")

        # =========================================================================
        # TIER 5: Fallback Public APIs (Cobalt / Invidious / Piped)
        # =========================================================================
        try:
            import httpx
            # 1. Cobalt API instances
            cobalt_payload = {"url": url, "videoQuality": "720"}
            cobalt_endpoints = [
                "https://api.cobalt.tools",
                "https://cobalt.api.scidsg.org",
                "https://co.wuk.sh"
            ]
            async with httpx.AsyncClient(timeout=3.5, follow_redirects=True) as client:
                for cb_host in cobalt_endpoints:
                    try:
                        cb_resp = await client.post(
                            f"{cb_host}/",
                            json=cobalt_payload,
                            headers={"Accept": "application/json", "Content-Type": "application/json"}
                        )
                        if cb_resp.status_code == 200:
                            cb_data = cb_resp.json()
                            if cb_data.get("url"):
                                raise web.HTTPFound(cb_data["url"])
                    except web.HTTPFound:
                        raise
                    except Exception:
                        pass

            # 2. Invidious instances
            invidious_endpoints = [
                f"https://invidious.f5.si/api/v1/videos/{video_id}",
                f"https://invidious.private.coffee/api/v1/videos/{video_id}",
                f"https://iv.ggtyler.dev/api/v1/videos/{video_id}",
            ]
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                for ep in invidious_endpoints:
                    try:
                        resp = await client.get(ep)
                        if resp.status_code == 200:
                            data = resp.json()
                            streams = data.get("formatStreams", [])
                            if streams and len(streams) > 0 and streams[0].get("url"):
                                stream_url = streams[0]["url"]
                                raise web.HTTPFound(stream_url)
                    except web.HTTPFound:
                        raise
                    except Exception:
                        continue
        except web.HTTPFound:
            raise
        except Exception as e_fallback_api:
            print(f"Tier 5 (Public APIs) notice for {video_id}: {e_fallback_api}")

        # =========================================================================
        # TIER 6: Safe Graceful Fallback (NEVER 500 INTERNAL SERVER ERROR!)
        # =========================================================================
        accept = request.headers.get("Accept", "")
        if "text/html" in accept:
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Video Yuklab Olish</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Inter Tight', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #000000; color: #FFFFFF; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; text-align: center; }}
        .card {{ background: #0E0E10; border: 1px solid rgba(255,255,255,0.12); border-top: 3px solid #FF5A1F; border-radius: 16px; padding: 32px 24px; max-width: 420px; box-shadow: 0 20px 50px rgba(0,0,0,0.75); }}
        h2 {{ margin: 0 0 12px; font-size: 20px; color: #FFFFFF; font-weight: 700; letter-spacing: -0.02em; }}
        p {{ color: #A1A1AA; font-size: 14px; line-height: 1.5; margin: 0 0 24px; }}
        .btn {{ display: inline-block; background: #FFFFFF; color: #000000; text-decoration: none; padding: 12px 24px; border-radius: 999px; font-weight: 600; font-size: 14px; margin: 6px; }}
        .btn:hover {{ background: #FF5A1F; color: #FFFFFF; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Video Yuklab Olish</h2>
        <p>Video server orqali tayyorlanmoqda. Telegram botimiz orqali to'g'ridan-to'g'ri va tezkor yuklab olishingiz mumkin.</p>
        <a class="btn" href="https://www.youtube.com/watch?v={_html.escape(video_id)}" target="_blank" rel="noopener noreferrer">YouTube da ochish</a>
    </div>
</body>
</html>"""
            return web.Response(text=html, content_type="text/html", status=200)

        return web.json_response({
            "ok": True,
            "status": "fallback",
            "video_id": video_id,
            "download_url": f"https://www.youtube.com/watch?v={video_id}",
            "message": "Video to'g'ridan-to'g'ri yuklab olinmadi. Telegram botimiz orqali yuqori sifatda yuklab olishingiz mumkin."
        }, status=200)

    except web.HTTPFound:
        raise
    except BaseException as fatal_err:
        print(f"Top-level handle_api_download_file safe guard: {fatal_err}")
        safe_vid = _extract_valid_video_id(request.query.get("video_id", "")) or ""
        return web.json_response({
            "ok": False,
            "status": "fallback",
            "video_id": safe_vid,
            "download_url": f"https://www.youtube.com/watch?v={safe_vid}" if safe_vid else "",
            "message": "Video tayyorlanmoqda. Telegram bot orqali yuklab olishingiz mumkin."
        }, status=500)

async def handle_api_autopost_create(request):
    """Tanlangan videolarni yoki mavzu bo'yicha videolarni autopost_tasks ga qo'shish (Anti-IDOR)"""
    import json
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Noto'g'ri JSON tana"}, status=400)

        tg_user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err

        video_ids = data.get("selected_video_ids") or data.get("video_ids") or []
        topic = str(data.get("topic") or data.get("search_query") or "").strip()[:200]
        video_type = str(data.get("video_type") or "shorts").strip().lower()
        if video_type not in ("shorts", "video", "long"):
            video_type = "shorts"

        if not video_ids and not topic:
            return web.json_response({"ok": False, "error": "Video yoki mavzu tanlanmagan!"}, status=400)

        from database import get_yt_connection, get_all_yt_connections, create_autopost_task
        req_channel_id = str(data.get("channel_id") or "").strip()
        conn_data = None
        if req_channel_id:
            all_conns = get_all_yt_connections(tg_user_id) or []
            for c in all_conns:
                if str(c.get("yt_channel_id")) == req_channel_id:
                    conn_data = c
                    break
        if not conn_data:
            conn_data = get_yt_connection(tg_user_id)

        if not conn_data:
            return web.json_response({"ok": False, "error": "YouTube kanal ulanmagan! Avval kanalingizni ulang."}, status=403)

        channel_id = conn_data["yt_channel_id"]

        if video_ids and isinstance(video_ids, list):
            clean_ids = []
            for v in video_ids[:20]:
                vid = _extract_valid_video_id(str(v))
                if vid:
                    clean_ids.append(vid)
            if not clean_ids:
                return web.json_response({"ok": False, "error": "Yaroqli YouTube video ID topilmadi!"}, status=400)
            search_query = "__IDS__:" + ",".join(clean_ids)
            total_count = len(clean_ids)
        else:
            search_query = topic
            try:
                total_count = max(1, min(10, int(data.get("count") or 1)))
            except Exception:
                total_count = 1

        task_id = create_autopost_task(tg_user_id, channel_id, search_query, video_type, total_count)

        # ROLE=main: bo'sh tashqi worker qidiradi (yoki RAM limit ichida o'zi bajaradi);
        # javobni HTTP so'rovchiga darhol qaytarish uchun fon vazifasiga o'raymiz.
        if task_id:
            asyncio.create_task(dispatch_or_run_autopost(task_id))
        return web.json_response({
            "ok": True,
            "success": True,
            "task_id": task_id,
            "channel_id": channel_id,
            "search_query": search_query,
            "total_count": total_count
        })
    except Exception as e:
        print(f"[api/autopost-create] error: {e}")
        return web.json_response({"ok": False, "error": "Autopost vazifasini yaratishda xatolik yuz berdi"}, status=500)

async def handle_api_reset_db(request):
    """Admin: Bazani tozalash"""
    import json
    import os
    try:
        data = await request.json()
        tg_user_id = _safe_int(data.get("tg_user_id", 0), 0)
        admin_secret = request.headers.get("X-Admin-Secret") or data.get("admin_secret", "")
        from config import get_admin_secret
        expected_secret = get_admin_secret()
        
        from config import OWNER_ID
        import hmac
        is_admin = is_admin_request(request) or (
            bool(expected_secret) and bool(admin_secret) and hmac.compare_digest(str(admin_secret).strip(), expected_secret)
        )
        if tg_user_id != OWNER_ID or not is_admin:
            return web.json_response({"error": "Ruxsat berilmagan!"}, status=403)
            
        from database import reset_all_data
        success = reset_all_data()
        return web.json_response({"success": success})
    except Exception as e:
        print(f"[api/reset-db] error: {e}")
        return web.json_response({"error": "Bazani tozalashda ichki xatolik yuz berdi"}, status=500)


async def handle_cryptopay_webhook(request):
    """CryptoPay (@CryptoBot) to'lov webhook qabul qiluvchi"""
    from crypto_pay import verify_crypto_pay_signature
    from database import complete_payment_transaction, get_user_balance
    from config import CRYPTO_PAY_TOKEN
    import json
    
    try:
        raw_body = await request.read()
        sig = request.headers.get("crypto-pay-api-signature", "")
        
        if not CRYPTO_PAY_TOKEN:
            print("⚠️ CryptoPay webhook rad etildi: CRYPTO_PAY_TOKEN sozlanmagan!")
            return web.json_response({"ok": False, "error": "CryptoPay not configured"}, status=500)

        if not sig or not verify_crypto_pay_signature(raw_body, sig):
            print("⚠️ CryptoPay webhook noto'g'ri yoki yetishmayotgan imzo!")
            return web.json_response({"ok": False, "error": "Invalid or missing signature"}, status=403)
                
        data = json.loads(raw_body.decode("utf-8"))
        print(f"📥 CryptoPay webhook keldi: {data.get('update_type')}")
        
        if data.get("update_type") == "invoice_paid":
            payload_info = data.get("payload", {})
            invoice_id = str(payload_info.get("invoice_id", ""))
            asset = payload_info.get("asset", "USDT")
            
            raw_custom = payload_info.get("payload", "{}")
            if isinstance(raw_custom, str):
                try:
                    custom_data = json.loads(raw_custom)
                except Exception:
                    custom_data = {}
            else:
                custom_data = raw_custom or {}
                
            tx_id = custom_data.get("tx_id")
            tg_user_id = custom_data.get("tg_user_id")
            amount_uzs = custom_data.get("amount_uzs", 0)
            
            if tx_id:
                complete_payment_transaction(int(tx_id), invoice_id=invoice_id)
                new_bal = get_user_balance(tg_user_id) if tg_user_id else 0
                
                if ytbot_instance and tg_user_id:
                    notify_text = (
                        f"✅ <b>To'lov muvaffaqiyatli qabul qilindi!</b>\n\n"
                        f"🪙 <b>Usul:</b> CryptoPay ({asset})\n"
                        f"💰 <b>Qo'shilgan summa:</b> +{amount_uzs:,} so'm\n"
                        f"⚖️ <b>Joriy balansingiz:</b> {new_bal:,} so'm\n\n"
                        f"🚀 Endi layk, obuna yoki izoh xizmatlaridan foydalanishingiz mumkin!"
                    )
                    asyncio.create_task(ytbot_instance.send_message(tg_user_id, notify_text))
                    
                # Bot egasiga (@CryptoBot dagi shaxsiy hisobiga) avtomatik o'tkazish
                paid_amount = payload_info.get("amount") or custom_data.get("amount")
                owner_id = int(os.getenv("OWNER_ID", "0"))
                auto_transfer = os.getenv("AUTO_TRANSFER_CRYPTO_TO_OWNER", "true").lower() in ("true", "1", "yes")
                if owner_id and auto_transfer and paid_amount:
                    from crypto_pay import transfer_crypto_pay
                    spend_id = f"fwd_{invoice_id}_{tx_id}"
                    asyncio.create_task(transfer_crypto_pay(
                        user_id=owner_id,
                        asset=asset,
                        amount=float(paid_amount),
                        spend_id=spend_id,
                        comment=f"Avto forward: Bot to'lovi #{tx_id} ({asset})"
                    ))

        return web.json_response({"ok": True})
    except Exception as e:
        print(f"CryptoPay webhook xatosi: {e}")
        return web.json_response({"ok": False, "error": "Webhookni qayta ishlashda ichki xatolik yuz berdi"}, status=500)


async def handle_kyc_page(request):
    """3D Face & ID Biometrik Identifikatsiya sahifasi (Anti-IDOR: unauth GET does not leak DB PII)"""
    from kyc_template import get_kyc_html
    from database import is_user_kyc_verified, get_user_kyc, get_telegram_phone
    user_id = _safe_int(request.query.get("user_id", 0), 0)
    is_verified = False
    kyc_data = None
    phone = ""
    try:
        auth_uid = get_authenticated_user_id(request)
        can_read_pii = (user_id > 0 and ((auth_uid and auth_uid == user_id) or is_admin_request(request)))
        if can_read_pii:
            is_verified = is_user_kyc_verified(user_id)
            if is_verified:
                kyc_data = get_user_kyc(user_id)
            phone = str(request.query.get("phone", "")).strip() or (get_telegram_phone(user_id) or "")
        html = get_kyc_html(user_id=user_id if can_read_pii else 0, is_verified=is_verified, kyc_data=kyc_data, phone=phone)
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(self)"
        }
        return web.Response(text=html, content_type="text/html", headers=headers)
    except Exception as e:
        print(f"handle_kyc_page error: {e}")
        try:
            fallback_html = get_kyc_html(user_id=0, is_verified=False, kyc_data=None, phone="")
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=(self)"
            }
            return web.Response(text=fallback_html, content_type="text/html", headers=headers)
        except Exception:
            return web.Response(
                text="<!DOCTYPE html><html><body style='background:#000000;color:#FFFFFF;font-family:sans-serif;text-align:center;padding:50px;'>"
                     "<h2>3D Biometrik Identifikatsiya</h2>"
                     "<p>Tizim yangilanmoqda. Iltimos, bir necha daqiqadan so'ng qayta urinib ko'ring.</p>"
                     "</body></html>",
                content_type="text/html"
            )


async def handle_kyc_status(request):
    """Foydalanuvchi KYC holatini tekshirish API (Anti-IDOR himoyalangan)"""
    from database import is_user_kyc_verified, get_user_kyc
    try:
        user_id, auth_err = _require_user_auth(request, allow_admin=True)
        if auth_err:
            return auth_err
        verified = is_user_kyc_verified(user_id)
        kyc_data = get_user_kyc(user_id) if verified else None
        phone_masked = ""
        verified_at_str = ""
        face_hash_masked = ""
        if kyc_data:
            ph = str(kyc_data.get("phone_number", ""))
            if len(ph) > 6:
                phone_masked = ph[:4] + " *** ** " + ph[-2:]
            else:
                phone_masked = ph
            verified_at_str = str(kyc_data.get("verified_at", ""))[:19]
            fh = str(kyc_data.get("face_hash", ""))
            face_hash_masked = (fh[:12] + "..." + fh[-6:]) if len(fh) > 18 else fh
        return web.json_response({
            "ok": True,
            "is_verified": verified,
            "user_id": user_id,
            "phone_masked": phone_masked,
            "verified_at": verified_at_str,
            "face_hash": face_hash_masked
        })
    except Exception as e:
        print(f"handle_kyc_status error: {e}")
        return web.json_response({"ok": False, "is_verified": False, "error": "KYC holatini tekshirishda xatolik yuz berdi"}, status=500)


async def handle_kyc_submit(request):
    """3D Yuz va Telefon ma'lumotlarini qabul qilish va tekshirish (Anti-Sybil + Anti-IDOR)"""
    from database import check_kyc_duplicate, save_kyc_verification
    
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "message": "Noto'g'ri JSON ma'lumot!"}, status=400)

        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err

        phone = str(data.get("phone", "")).strip()
        face_hash = str(data.get("face_hash", "")).strip()
        
        if not phone or len(phone) < 9 or len(phone) > 20 or not _re.match(r"^\+?[0-9\s\-()]{9,20}$", phone):
            return web.json_response({"ok": False, "message": "Telefon raqami noto'g'ri kiritilgan!"}, status=400)
        if not face_hash or len(face_hash) > 128:
            return web.json_response({"ok": False, "message": "3D Yuz skaneri ma'lumotlari noto'g'ri!"}, status=400)
        
        # Takroriy hisob tekshiruvi (Anti-Sybil Deduplication)
        is_dup, reason = check_kyc_duplicate(passport_hash=None, face_hash=face_hash, phone_number=phone, exclude_tg_user_id=user_id)
        if is_dup:
            return web.json_response({"ok": False, "message": reason}, status=400)
            
        # Saqlash
        save_kyc_verification(user_id, phone, None, face_hash)
        
        # Bot orqali tasdiq xabari yuborish
        if ytbot_instance:
            safe_phone = _html.escape(phone)
            msg = (
                f"✅ <b>Tabriklaymiz! 3D Biometrik Identifikatsiya muvaffaqiyatli yakunlandi.</b>\n\n"
                f"📱 <b>Telefon:</b> {safe_phone}\n"
                f"🛡️ Anti-Sybil tekshiruvi: <b>Muvaffaqiyatli</b>\n\n"
                f"🚀 Barcha YouTube avtomatizatsiya va xizmatlar siz uchun to'liq ochildi!"
            )
            asyncio.create_task(ytbot_instance.send_message(user_id, msg))
            
        return web.json_response({"ok": True, "message": "Identifikatsiya muvaffaqiyatli tasdiqlandi!"})
    except Exception as e:
        print(f"handle_kyc_submit error: {e}")
        return web.json_response({"ok": False, "message": "Server ichki xatoligi yuz berdi"}, status=500)



async def handle_tc_manifest(request):
    """TON Connect Manifest JSON taqdim etish"""
    from ton_connect_page import get_ton_manifest
    base_url = _get_safe_base_url(request)
    manifest = get_ton_manifest(base_url)
    return web.json_response(manifest, headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache"
    })


async def handle_tonconnect_page(request):
    """TON Connect Telegram Mini App HTML sahifasi (Anti-IDOR + Host-Injection protected)"""
    from ton_connect_page import get_ton_connect_html
    from database import get_user_ton_wallet
    user_id = _safe_int(request.query.get("user_id", 0), 0)
    auth_uid = get_authenticated_user_id(request)
    can_read_wallet = (user_id > 0 and ((auth_uid and auth_uid == user_id) or is_admin_request(request)))

    current_wallet = get_user_ton_wallet(user_id) if can_read_wallet else None
    base_url = _get_safe_base_url(request)
    html = get_ton_connect_html(user_id=user_id if can_read_wallet else 0, current_wallet=current_wallet, base_url=base_url)
    return web.Response(text=html, content_type="text/html")


async def handle_api_tonconnect_save(request):
    """Mini App orqali ulangan TON hamyonni saqlash (Anti-IDOR himoyalangan)"""
    from database import save_user_ton_wallet, to_user_friendly_address
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "message": "Noto'g'ri JSON ma'lumot"}, status=400)

        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err

        address = str(data.get("address", "")).strip()
        address = to_user_friendly_address(address)
        wallet_name = str(data.get("wallet_name", "TON Wallet")).strip()[:64] or "TON Wallet"
        chain = str(data.get("chain", "mainnet")).strip().lower()
        if chain not in ("mainnet", "testnet"):
            chain = "mainnet"

        if not address or len(address) < 20 or len(address) > 128:
            return web.json_response({"ok": False, "message": "Noto'g'ri TON hamyon manzili"}, status=400)

        ok = save_user_ton_wallet(user_id, address, wallet_name, chain)
        if not ok:
            return web.json_response({"ok": False, "message": "Bazaga saqlashda xatolik"}, status=500)

        if ytbot_instance:
            masked_addr = address[:6] + "..." + address[-6:] if len(address) > 12 else address
            safe_wallet = _html.escape(wallet_name)
            safe_addr = _html.escape(address)
            safe_masked = _html.escape(masked_addr)
            msg = (
                f"💎 <b>TON Hamyoningiz Muvaffaqiyatli Ulandi!</b>\n\n"
                f"👛 <b>Hamyon:</b> {safe_wallet}\n"
                f"📬 <b>Manzil:</b> <code>{safe_addr}</code> ({safe_masked})\n"
                f"🌐 <b>Tarmoq:</b> TON {chain.capitalize()}\n\n"
                f"⚡ <i>Endi pul yechish (Cashout) va 3D NFT savdosida ushbu manzil avtomatik ishlatiladi!</i>"
            )
            asyncio.create_task(ytbot_instance.send_message(user_id, msg))

        return web.json_response({"ok": True, "message": "Hamyon muvaffaqiyatli saqlandi!"})
    except Exception as e:
        print(f"handle_api_tonconnect_save error: {e}")
        return web.json_response({"ok": False, "message": "Hamyonni saqlashda ichki xatolik yuz berdi"}, status=500)


async def handle_api_tonconnect_disconnect(request):
    """Ulangan TON hamyonni uzish (Anti-IDOR himoyalangan)"""
    from database import delete_user_ton_wallet
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "message": "Noto'g'ri JSON ma'lumot"}, status=400)

        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err

        delete_user_ton_wallet(user_id)
        if ytbot_instance:
            asyncio.create_task(ytbot_instance.send_message(
                user_id,
                "🔗 <b>TON hamyoningiz hisobingizdan uzildi.</b>\n"
                "Istalgan vaqtda qayta ulashingiz mumkin."
            ))
        return web.json_response({"ok": True, "message": "Hamyon uzildi"})
    except Exception as e:
        print(f"handle_api_tonconnect_disconnect error: {e}")
        return web.json_response({"ok": False, "message": "Hamyonni uzishda ichki xatolik yuz berdi"}, status=500)


async def handle_nft_metadata(request):
    """TON TEP-64 standartiga mos NFT metadata JSON qaytarish"""
    import database as db
    from config import WEB_APP_URL
    item_id_raw = request.match_info.get("item_id", "")
    item_id_str = item_id_raw.replace(".json", "")
    try:
        item_id = int(item_id_str)
    except ValueError:
        return web.Response(text="Noto'g'ri ID", status=400)
    
    item = db.get_nft_item(item_id)
    if not item:
        return web.Response(text="NFT topilmadi", status=404)
    
    title = item.get("title", "NFT")
    img_name = "NFT.png"
    if "Heart" in title or "Yurak" in title:
        img_name = "HEART.png"
    elif "Premium" in title or "Star" in title or "Yulduz" in title:
        img_name = "TG_PREMIUM.png"
        
    web_url = os.environ.get("WEB_URL", WEB_APP_URL).rstrip("/")
    image_url = f"{web_url}/api/nft/image/{img_name}"
    video_url = f"{web_url}/api/nft/video/{img_name.replace('.png', '.mp4')}"
    
    metadata = {
        "name": f"{title} #{item_id}",
        "description": item.get("description", "Exclusive 3D Telegram Collectible NFT"),
        "image": image_url,
        "content_url": video_url,
        "animation_url": video_url,
        "collection": {
            "name": "Telegram 3D Artifacts",
            "family": "Telegram Artifacts",
            "description": "Telegram eksklyuziv 3D artefaktlar to'plami",
            "image": image_url
        },
        "collection_name": "Telegram 3D Artifacts",
        "attributes": [
            {"trait_type": "Collection", "value": "Telegram 3D Artifacts"},
            {"trait_type": "Format", "value": "3D GLTF (.glb) + 4K Video (.mp4)"},
            {"trait_type": "Item ID", "value": f"#{item_id}"}
        ]
    }
    return web.json_response(metadata, headers={"Access-Control-Allow-Origin": "*"})

async def handle_nft_image(request):
    """NFT muqova rasmini yuborish (Path Traversal & Extension Allowlist himoyalangan)"""
    raw_filename = request.match_info.get("filename", "").strip()
    clean_name = os.path.basename(raw_filename)
    if (
        not clean_name
        or clean_name != raw_filename
        or ".." in clean_name
        or "/" in clean_name
        or "\\" in clean_name
        or clean_name.lower().startswith(("cookies_", "webdl_"))
    ):
        return web.Response(text="Noto'g'ri fayl nomi", status=400)

    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        return web.Response(text="Ruxsat etilmagan fayl formati", status=403)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    allowed_dirs = [
        os.path.realpath(os.path.join(base_dir, "nft_assets")),
        os.path.realpath(os.path.join(base_dir, "downloads"))
    ]

    file_path = os.path.join(base_dir, "nft_assets", clean_name)
    if not os.path.exists(file_path):
        file_path = os.path.join(base_dir, "downloads", clean_name)

    real_path = os.path.realpath(file_path)
    if not any(real_path.startswith(ad + os.sep) for ad in allowed_dirs) or not os.path.exists(real_path) or not os.path.isfile(real_path):
        return web.Response(text="Rasm topilmadi", status=404)

    content_type = "image/png"
    if ext in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    elif ext == ".webp":
        content_type = "image/webp"
    elif ext == ".gif":
        content_type = "image/gif"

    if ext == ".gif":
        return web.FileResponse(real_path, headers={
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=604800, immutable",
            "Access-Control-Allow-Origin": "*"
        })

    try:
        target_w = int(request.query.get("w", "240"))
    except Exception:
        target_w = 240
    target_w = max(48, min(512, target_w))
    cache_key = f"nft:{clean_name}:{target_w}"
    cached_entry = _RASTER_FAST_CACHE.get(cache_key)
    if not cached_entry:
        with open(real_path, "rb") as rf:
            raw_img = rf.read()
        compact_data, compact_mime = _compress_raster_image(raw_img, max_dim=target_w, quality=80)
        cached_entry = _cache_raster_put(cache_key, compact_data, compact_mime)

    body_bytes, resp_mime, etag = cached_entry
    resp_headers = {
        "Cache-Control": "public, max-age=604800, immutable",
        "Access-Control-Allow-Origin": "*",
        "ETag": etag,
        "Content-Length": str(len(body_bytes)),
    }
    if request.headers.get("If-None-Match") == etag:
        return web.Response(status=304, headers=resp_headers)
    return web.Response(body=body_bytes, content_type=resp_mime, headers=resp_headers)

_FRAGMENT_IMG_CACHE = {}
_FRAGMENT_IMG_CACHE_MAX = 200

async def handle_fragment_image_proxy(request):
    """Fragment CDN dagi NFT rasmini yuklab beruvchi proxy API (Strict Slug Validation + Bounded Cache)"""
    slug = request.match_info.get("slug", "").strip()
    if not slug or not _SLUG_PATTERN.match(slug) or len(slug) > 80:
        return web.Response(status=400, text="Invalid slug")

    cache_entry = _RASTER_FAST_CACHE.get(f"frag:{slug}")
    if cache_entry:
        c_bytes, c_mime, etag = cache_entry
        return web.Response(
            body=c_bytes,
            content_type=c_mime,
            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=604800, immutable", "ETag": etag, "Content-Length": str(len(c_bytes))}
        )
        
    if slug in _FRAGMENT_IMG_CACHE:
        return web.Response(
            body=_FRAGMENT_IMG_CACHE[slug],
            content_type="image/jpeg",
            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=604800, immutable"}
        )
        
    url = f"https://nft.fragment.com/gift/{slug}.medium.jpg"
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=False) as resp:
                if resp.status == 200:
                    upstream_ct = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip().lower()
                    if not upstream_ct.startswith("image/"):
                        return web.Response(status=502, text="Invalid upstream media type")
                    img_bytes = await resp.content.read(5 * 1024 * 1024 + 1)
                    if len(img_bytes) > 5 * 1024 * 1024:
                        return web.Response(status=502, text="Upstream image too large")
                    compact_data, compact_mime = _compress_raster_image(img_bytes, max_dim=240, quality=80)
                    _, _, etag = _cache_raster_put(f"frag:{slug}", compact_data, compact_mime)
                    return web.Response(
                        body=compact_data,
                        content_type=compact_mime,
                        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=604800, immutable", "ETag": etag, "Content-Length": str(len(compact_data))}
                    )
                else:
                    return web.Response(status=resp.status, text="Image not found on Fragment")
    except Exception as e:
        print(f"[fragment-image-proxy] error for {slug}: {e}")
        return web.Response(status=502, text="Image proxy unavailable")

async def handle_nft_video(request):
    """NFT 3D video animatsiyasini yuborish (Path Traversal & Extension Allowlist himoyalangan)"""
    raw_filename = request.match_info.get("filename", "").strip()
    clean_name = os.path.basename(raw_filename)
    if (
        not clean_name
        or clean_name != raw_filename
        or ".." in clean_name
        or "/" in clean_name
        or "\\" in clean_name
        or clean_name.lower().startswith(("cookies_", "webdl_"))
    ):
        return web.Response(text="Noto'g'ri fayl nomi", status=400)

    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in _ALLOWED_VIDEO_EXTS:
        return web.Response(text="Ruxsat etilmagan video formati", status=403)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    allowed_dirs = [
        os.path.realpath(os.path.join(base_dir, "nft_assets")),
        os.path.realpath(os.path.join(base_dir, "downloads"))
    ]

    file_path = os.path.join(base_dir, "nft_assets", clean_name)
    if not os.path.exists(file_path):
        file_path = os.path.join(base_dir, "downloads", clean_name)

    real_path = os.path.realpath(file_path)
    if not any(real_path.startswith(ad + os.sep) for ad in allowed_dirs) or not os.path.exists(real_path) or not os.path.isfile(real_path):
        return web.Response(text="Video topilmadi", status=404)

    content_type = "video/webm" if ext == ".webm" else ("video/quicktime" if ext == ".mov" else "video/mp4")
    return web.FileResponse(real_path, headers={
        "Content-Type": content_type,
        "Cache-Control": "public, max-age=86400",
        "Access-Control-Allow-Origin": "*"
    })


_LIVE_GIFTS_CACHE = {"data": None, "ts": 0}

async def handle_api_stars_live_gifts(request):
    """Telegram Bot API getAvailableGifts orqali real Telegram sovg'alarini olish"""
    import time as _t
    now = _t.time()
    if _LIVE_GIFTS_CACHE["data"] and (now - _LIVE_GIFTS_CACHE["ts"] < 300):
        return web.json_response({"ok": True, "source": "cache", "gifts": _LIVE_GIFTS_CACHE["data"]}, headers={"Access-Control-Allow-Origin": "*"})

    from config import BOT_TOKEN
    import aiohttp
    if BOT_TOKEN:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getAvailableGifts"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    res = await resp.json()
                    if res.get("ok"):
                        gifts = res.get("result", {}).get("gifts", [])
                        _LIVE_GIFTS_CACHE["data"] = gifts
                        _LIVE_GIFTS_CACHE["ts"] = now
                        return web.json_response({"ok": True, "source": "telegram_api", "gifts": gifts}, headers={"Access-Control-Allow-Origin": "*"})
        except Exception as e:
            print(f"Telegram getAvailableGifts error: {e}")

    # Fallback to official Telegram catalog
    from games_monetization import STARS_CASES
    all_drops = []
    for c in STARS_CASES.values():
        all_drops.extend(c.get("drops", []))
    return web.json_response({"ok": True, "source": "official_catalog", "gifts": all_drops}, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_cases(request):
    """5 Tier Telegram Stars Mystery Cases ma'lumotlari (Telegram serveridan jonli)"""
    from games_monetization import build_cases_from_gifts
    cases_dict = build_cases_from_gifts()
    return web.json_response(
        {"ok": True, "cases": list(cases_dict.values())},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=30"
        }
    )

async def handle_api_stars_open_case(request):
    """Web Dashboard orqali to'langan Stars keysi yutug'ini tekshirish va unboxing natijasi (Anti-IDOR)"""
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Noto'g'ri JSON ma'lumot"}, status=400)

        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err

        tier_id = str(data.get("tier_id", "tier_1")).strip()
        from config import OWNER_ID

        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)

        from database import get_db
        # 1. Bot orqali to'langan so'nggi 3 daqiqadagi haqiqiy yutuqni tekshirish
        conn = get_db()
        recent_gift = None
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT prize_name, prize_stars, case_name, gift_id, status, created_at
                    FROM pending_gifts
                    WHERE tg_user_id = %s AND created_at >= NOW() - INTERVAL '3 minutes'
                    ORDER BY id DESC LIMIT 1
                """, (user_id,))
                recent_gift = cur.fetchone()
            except Exception:
                pass
            finally:
                conn.close()

        if recent_gift:
            from games_monetization import build_cases_from_gifts
            cases = build_cases_from_gifts()
            case = cases.get(tier_id) or cases.get("tier_1")
            matching_drop = None
            for d in case.get("drops", []):
                if d.get("id") == recent_gift.get("gift_id") or d.get("name") == recent_gift.get("prize_name"):
                    matching_drop = d
                    break
            if not matching_drop and case.get("drops"):
                matching_drop = case["drops"][0]

            return web.json_response({
                "ok": True,
                "tier": case["id"],
                "case_name": recent_gift.get("case_name") or case["name"],
                "cost_stars": case["price_stars"],
                "prize_stars": recent_gift.get("prize_stars") or (matching_drop.get("stars") if matching_drop else 25),
                "prize_name": recent_gift.get("prize_name") or (matching_drop.get("name") if matching_drop else "Telegram Sovg'a"),
                "rarity": matching_drop.get("rarity", "rare") if matching_drop else "rare",
                "icon": matching_drop.get("icon", "package") if matching_drop else "package",
                "file_id": matching_drop.get("file_id", "") if matching_drop else "",
                "file_type": matching_drop.get("file_type", "webp") if matching_drop else "webp",
                "gift_id": recent_gift.get("gift_id") or "",
                "is_nft": matching_drop.get("is_nft", False) if matching_drop else False,
            })

        # 2. Agar haqiqiy autentifikatsiyalangan bot egasi (Owner) bo'lsa
        if user_id == OWNER_ID:
            from games_monetization import open_stars_case
            res = open_stars_case(user_id, tier_id)
            return web.json_response(res)

        # Aks holda to'lov tasdiqlanmagan xakerlik / bepul spam urinishi
        return web.json_response({
            "ok": False,
            "error": "To'lov tasdiqlanmadi yoki Stars balansi yetarli emas. Iltimos, so'm balansi yoki rasmiy Stars to'lovi orqali oching."
        }, status=402)
    except Exception as e:
        print(f"[api/stars/open-case] error: {e}")
        return web.json_response({"ok": False, "error": "Keysni ochishda ichki xatolik yuz berdi"}, status=500)

_TELEGRAM_FILE_CACHE = {}  # { file_id: (content, content_type, timestamp) }
_TG_FILE_CACHE_MAX = 200
_TG_FILE_CACHE_TTL = 3600  # 1 soat

_GIFT_ID_TO_FILE_ID = {
    "5170145012310081615": "CAACAgIAAxUAAWrS2uM_EewXTXxghtF9VyKlBMUvAAJ8GwACkoTYS_itxFzPIpm1PQQ",  # Red Heart / Green Star (15)
    "5170233102089322756": "CAACAgIAAxUAAWrS2uO_yFyaqnGsGU2Rb6B3zOCwAAKtVAACmj_pSnvPkDQv_sivPQQ",  # Teddy Bear (15)
    "5170250947678437525": "CAACAgIAAxUAAWrS2uM0EZJ7Dun5N1H-6YKcZfl3AAKNSAACsU84SMuB4ge7V_wGPQQ",  # Gift Box (25)
    "5168103777563050263": "CAACAgIAAxUAAWrS2uMBc0LraApyb-75XswisR0tAAJxGQAC1P-BS9CYmaAv74KEPQQ",  # Red Rose (25)
    "5170144170496491616": "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E",  # Delicious Cake (50)
    "5170314324215857265": "CAACAgIAAxUAAWrS2uNt8sIHLaoAAZeEbczG8VU45QAC3iUAAkUg4ErI5hOgFM9DXj0E",  # Bouquet of Flowers (50)
    "5170564780938756245": "CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ",  # Space Rocket (50)
    "6028601630662853006": "CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ",  # Champagne Bottle (50)
    "5168043875654172773": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",  # Golden Trophy (100)
    "5170690322832818290": "CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ",  # Diamond Ring (100)
    "5170521118301225164": "CAACAgIAAxUAAWrS2uOdst4ZTcyZTnYZPBO024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ",  # Blue Diamond (100)
}

_GIFT_ID_TO_LOCAL_WEBP = {
    "5170145012310081615": "gift_star.webp",
    "5170233102089322756": "gift_star.webp",
    "5170250947678437525": "delicious_cake.webp",
    "5168103777563050263": "gift_bouquet.webp",
    "5170144170496491616": "delicious_cake.webp",
    "5170314324215857265": "gift_bouquet.webp",
    "5170564780938756245": "gift_rocket.webp",
    "6028601630662853006": "champagne_bottle.webp",
    "5168043875654172773": "star_trophy.webp",
    "5170690322832818290": "diamond_ring.webp",
    "5170521118301225164": "diamond_ring.webp",
}

_LOCAL_LOTTIE_KEY_MAP = {
    # Numeric Telegram Gift IDs
    "5170145012310081615": "heart-box",
    "5170233102089322756": "teddy-bear",
    "5170250947678437525": "gift-box",
    "5168103777563050263": "red-rose",
    "5170144170496491616": "delicious-cake",
    "5170314324215857265": "bouquet-flowers",
    "5170564780938756245": "space-rocket",
    "6028601630662853006": "champagne-bottle",
    "5168043875654172773": "golden-trophy",
    "5170690322832818290": "diamond-ring",
    "5170521118301225164": "blue-diamond",
    # Canonical Slugs & Aliases
    "heart-box": "heart-box",
    "red-heart": "heart-box",
    "teddy-bear": "teddy-bear",
    "gift-box": "gift-box",
    "green-star": "gift-box",
    "red-rose": "red-rose",
    "delicious-cake": "delicious-cake",
    "birthday-cake": "delicious-cake",
    "bouquet-flowers": "bouquet-flowers",
    "space-rocket": "space-rocket",
    "champagne-bottle": "champagne-bottle",
    "golden-trophy": "golden-trophy",
    "star-trophy": "golden-trophy",
    "diamond-ring": "diamond-ring",
    "blue-diamond": "blue-diamond",
    # Telegram file_id strings (both bots / environments)
    "CAACAgIAAxUAAWrS2uM_EewXTXxghtF9VyKlBMUvAAJ8GwACkoTYS_itxFzPIpm1PQQ": "heart-box",
    "CAACAgIAAxUAAWrgfG5D8b9uP4T6jX-N7aLmKRVhAAJ8GwACkoTYS_itxFzPIpm1PQQ": "heart-box",
    "CAACAgIAAxUAAWrS2uO_yFyaqnGsGU2Rb6B3zOCwAAKtVAACmj_pSnvPkDQv_sivPQQ": "teddy-bear",
    "CAACAgIAAxUAAWrgfG7ba9v2H5mE3cR8wLpXyKZaAAKtVAACmj_pSnvPkDQv_sivPQQ": "teddy-bear",
    "CAACAgIAAxUAAWrS2uM0EZJ7Dun5N1H-6YKcZfl3AAKNSAACsU84SMuB4ge7V_wGPQQ": "gift-box",
    "CAACAgIAAxUAAWrgfG7_wG9nK2xL5vM8pQrTyWZcAAKNSAACsU84SMuB4ge7V_wGPQQ": "gift-box",
    "CAACAgIAAxUAAWrS2uMBc0LraApyb-75XswisR0tAAJxGQAC1P-BS9CYmaAv74KEPQQ": "red-rose",
    "CAACAgIAAxUAAWrgfG7pQ9xK4mN7vL2wYrTzXZa9AAJxGQAC1P-BS9CYmaAv74KEPQQ": "red-rose",
    "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E": "delicious-cake",
    "CAACAgIAAxUAAWrgfG5990QACgRgAApWfiUpqxk-ZAWRQxj0E": "delicious-cake",
    "CAACAgIAAxUAAWrS2uNt8sIHLaoAAZeEbczG8VU45QAC3iUAAkUg4ErI5hOgFM9DXj0E": "bouquet-flowers",
    "CAACAgIAAxUAAWrgfG7xVU45QAC3iUAAkUg4ErI5hOgFM9DXj0E": "bouquet-flowers",
    "CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ": "space-rocket",
    "CAACAgIAAxUAAWrgfG7cFzHFAALLGwAC14mRSzvrMNfF90DPPQQ": "space-rocket",
    "CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ": "champagne-bottle",
    "CAACAgIAAxUAAWrgfG5KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ": "champagne-bottle",
    "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ": "golden-trophy",
    "CAACAgIAAxUAAWrgfG7ii_xcAAKZGwACzagQS38R6izkF899PQQ": "golden-trophy",
    "CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ": "diamond-ring",
    "CAACAgIAAxUAAWrgfG7dly-gAALoTwACJx74Ss1NNn7ovmiePQQ": "diamond-ring",
    "CAACAgIAAxUAAWrS2uOdst4ZTcyZTnYZPBO024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ": "blue-diamond",
    "CAACAgIAAxUAAWrgfG5024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ": "blue-diamond",
}

def _get_local_gift_lottie_bytes(identifier: str):
    """Mahalliy nft_assets/gifts_lottie/ papkasidan rasmiy Telegram .tgs (decompressed Lottie JSON) ni o'qiydi."""
    if not identifier:
        return None
    import os
    clean_id = str(identifier).strip()
    slug_key = _LOCAL_LOTTIE_KEY_MAP.get(clean_id) or _LOCAL_LOTTIE_KEY_MAP.get(clean_id.lower())
    if not slug_key:
        # Check prefix/suffix match for CAACAg file_ids whose unique tail matches known stickers
        tail_map = {
            "koTYS_itxFzPIpm1PQQ": "heart-box",
            "mj_pSnvPkDQv_sivPQQ": "teddy-bear",
            "sU84SMuB4ge7V_wGPQQ": "gift-box",
            "1P-BS9CYmaAv74KEPQQ": "red-rose",
            "pWfiUpqxk-ZAWRQxj0E": "delicious-cake",
            "kUg4ErI5hOgFM9DXj0E": "bouquet-flowers",
            "14mRSzvrMNfF90DPPQQ": "space-rocket",
            "y0WJSqKYQ7cuIwaJPQQ": "champagne-bottle",
            "zagQS38R6izkF899PQQ": "golden-trophy",
            "Jx74Ss1NNn7ovmiePQQ": "diamond-ring",
            "QEjwS6XKX-OK2k1MPQQ": "blue-diamond",
        }
        for tail, mapped_slug in tail_map.items():
            if clean_id.endswith(tail):
                slug_key = mapped_slug
                break
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lottie_dir = os.path.realpath(os.path.join(base_dir, "nft_assets", "gifts_lottie"))
    candidates = []
    if slug_key and _SLUG_PATTERN.match(slug_key):
        candidates.append(os.path.join(lottie_dir, f"{slug_key}.json"))
    if _SLUG_PATTERN.match(clean_id):
        candidates.append(os.path.join(lottie_dir, f"{clean_id}.json"))
    for p in candidates:
        real_p = os.path.realpath(p)
        if not real_p.startswith(lottie_dir + os.sep):
            continue
        if os.path.isfile(real_p):
            try:
                with open(real_p, "rb") as f:
                    data = f.read()
                if data and len(data) > 200:
                    return data
            except Exception:
                pass
    return None

async def handle_api_telegram_file(request):
    """Telegramdan file_id orqali faylni (TGS/WEBM/PNG/JPG) yuklab, frontendga uzatuvchi proxy API (Strict Validation + Zip-Bomb Defense)"""
    file_id = request.match_info.get("file_id", "").strip()
    if not file_id or not _FILE_ID_PATTERN.match(file_id):
        return web.Response(status=400, text="Invalid file_id")
        
    import time
    import os
    import gzip
    now = time.time()

    # 2. Agar numeric gift_id berilgan bo'lsa, uni haqiqiy Telegram sticker file_id ga tarjima qilish
    actual_file_id = _GIFT_ID_TO_FILE_ID.get(file_id, file_id)

    is_gift = (
        file_id in _GIFT_ID_TO_FILE_ID
        or file_id in _GIFT_ID_TO_LOCAL_WEBP
        or file_id in _LOCAL_LOTTIE_KEY_MAP
        or actual_file_id in _GIFT_ID_TO_FILE_ID.values()
        or file_id.startswith("CAAC")
    )

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=604800, immutable" if is_gift else "public, max-age=3600, stale-while-revalidate=86400"
    }

    # 0. Mahalliy rasmiy Telegram Lottie (.tgs -> JSON) fayllaridan tezkor uzatish (Render va har qanday BOT_TOKEN da 100% ishlaydi)
    local_lottie = _get_local_gift_lottie_bytes(file_id) or _get_local_gift_lottie_bytes(actual_file_id)
    if local_lottie:
        _TELEGRAM_FILE_CACHE[file_id] = (local_lottie, "application/json", now)
        return web.Response(
            body=local_lottie,
            content_type="application/json",
            headers=headers
        )

    # 1. RAM keshdan tekshirish
    cached = _TELEGRAM_FILE_CACHE.get(file_id)
    if cached and (now - cached[2]) < _TG_FILE_CACHE_TTL:
        if not is_gift and cached[1] == "image/webp":
            _TELEGRAM_FILE_CACHE.pop(file_id, None)
        else:
            c_body, c_type = cached[0], cached[1]
            if isinstance(c_body, (bytes, bytearray)) and c_body[:2] == b"\x1f\x8b":
                try:
                    c_body = gzip.decompress(c_body)
                    c_type = "application/json"
                    _TELEGRAM_FILE_CACHE[file_id] = (c_body, c_type, now)
                except Exception:
                    pass
            return web.Response(
                body=c_body,
                content_type=c_type,
                headers=headers
            )

    try:
        from config import BOT_TOKEN
        import aiohttp
        token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
        if not token:
            if is_gift and file_id in _GIFT_ID_TO_LOCAL_WEBP:
                local_name = _GIFT_ID_TO_LOCAL_WEBP[file_id]
                base_dir = os.path.dirname(os.path.abspath(__file__))
                lp = os.path.join(base_dir, "nft_assets", local_name)
                if os.path.exists(lp):
                    with open(lp, "rb") as f:
                        content = f.read()
                    return web.Response(body=content, content_type="image/webp", headers=headers)
            return web.Response(status=404, text="File not found")
            
        async with aiohttp.ClientSession() as session:
            # 1. file_path ni olish
            file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={actual_file_id}"
            file_path = None
            async with session.get(file_url, timeout=6) as r1:
                res1 = await r1.json()
                if res1.get("ok"):
                    file_path = res1["result"]["file_path"]
                else:
                    # Fresh profile photo fallback ONLY for authenticated user (blocks unauth user enumeration)
                    if not is_gift and (file_id.startswith("AQAD") or "wrong file_id" in str(res1).lower()):
                        try:
                            target_tg_id = get_authenticated_user_id(request)
                            if target_tg_id > 0:
                                async with session.get(f"https://api.telegram.org/bot{token}/getUserProfilePhotos?user_id={target_tg_id}&limit=1", timeout=4) as up_r:
                                    up_json = await up_r.json()
                                    if up_json.get("ok") and up_json.get("result", {}).get("photos"):
                                        fresh_fid = up_json["result"]["photos"][0][-1]["file_id"]
                                        async with session.get(f"https://api.telegram.org/bot{token}/getFile?file_id={fresh_fid}", timeout=4) as fresh_r:
                                            fresh_json = await fresh_r.json()
                                            if fresh_json.get("ok"):
                                                file_path = fresh_json["result"]["file_path"]
                        except Exception as e_fresh:
                            print(f"[handle_api_telegram_file] Fresh photo fallback error: {e_fresh}")

                if not file_path:
                    if is_gift and file_id in _GIFT_ID_TO_LOCAL_WEBP:
                        local_name = _GIFT_ID_TO_LOCAL_WEBP[file_id]
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        lp = os.path.join(base_dir, "nft_assets", local_name)
                        if os.path.exists(lp):
                            with open(lp, "rb") as f:
                                content = f.read()
                            _TELEGRAM_FILE_CACHE[file_id] = (content, "image/webp", now)
                            return web.Response(body=content, content_type="image/webp", headers=headers)
                    return web.Response(status=404, text="File not found on Telegram")
                
            # 2. Faylning o'zini yuklab uzatish
            download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            async with session.get(download_url, timeout=12) as r2:
                if r2.status != 200:
                    if is_gift and file_id in _GIFT_ID_TO_LOCAL_WEBP:
                        local_name = _GIFT_ID_TO_LOCAL_WEBP[file_id]
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        lp = os.path.join(base_dir, "nft_assets", local_name)
                        if os.path.exists(lp):
                            with open(lp, "rb") as f:
                                content = f.read()
                            _TELEGRAM_FILE_CACHE[file_id] = (content, "image/webp", now)
                            return web.Response(body=content, content_type="image/webp", headers=headers)
                    return web.Response(status=502, text="Failed to download from Telegram")
                    
                content = await r2.content.read(10 * 1024 * 1024 + 1)
                if len(content) > 10 * 1024 * 1024:
                    return web.Response(status=502, text="Upstream file too large")
                
                # Agar TGS (gzipped lottie, masalan 'stickers/file_27' yoki '.tgs') bo'lsa decompress qilib toza JSON uzatamiz
                if file_path.endswith(".tgs") or (isinstance(content, (bytes, bytearray)) and content[:2] == b"\x1f\x8b"):
                    try:
                        content = _safe_gzip_decompress(content, max_size=5 * 1024 * 1024)
                        content_type = "application/json"
                    except Exception:
                        content_type = "application/octet-stream"
                elif isinstance(content, (bytes, bytearray)) and content[:1] == b"{" and b'"layers"' in content[:512]:
                    content_type = "application/json"
                elif file_path.endswith(".webm"):
                    content_type = "video/webm"
                elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                    content_type = "image/jpeg"
                elif file_path.endswith(".png"):
                    content_type = "image/png"
                elif file_path.endswith(".webp"):
                    content_type = "image/webp"
                else:
                    upstream_ct = (r2.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip().lower()
                    content_type = upstream_ct if upstream_ct in _SAFE_PROXY_CONTENT_TYPES else "application/octet-stream"
                    
                # Keshga saqlash (LRU eviksiya)
                if len(_TELEGRAM_FILE_CACHE) >= _TG_FILE_CACHE_MAX:
                    oldest_k = min(_TELEGRAM_FILE_CACHE, key=lambda k: _TELEGRAM_FILE_CACHE[k][2])
                    _TELEGRAM_FILE_CACHE.pop(oldest_k, None)
                _TELEGRAM_FILE_CACHE[file_id] = (content, content_type, now)

                return web.Response(
                    body=content,
                    content_type=content_type,
                    headers=headers
                )
    except Exception as e:
        if is_gift and file_id in _GIFT_ID_TO_LOCAL_WEBP:
            local_name = _GIFT_ID_TO_LOCAL_WEBP[file_id]
            base_dir = os.path.dirname(os.path.abspath(__file__))
            lp = os.path.join(base_dir, "nft_assets", local_name)
            if os.path.exists(lp):
                with open(lp, "rb") as f:
                    content = f.read()
                return web.Response(body=content, content_type="image/webp", headers=headers)
        return web.Response(status=404, text="File not found")

async def handle_favicon(request):
    """Serve MonoDeck SVG brand favicon or .ico with long-term cache headers"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    is_svg = request.path.endswith(".svg")
    if is_svg:
        from ui_theme import FAVICON_SVG
        return web.Response(
            text=FAVICON_SVG,
            content_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=604800, immutable",
                "Access-Control-Allow-Origin": "*",
            },
        )
    fp = os.path.join(base_dir, "favicon.ico")
    if not os.path.exists(fp):
        fp = os.path.join(base_dir, "nft_assets", "favicon.ico")
    if os.path.exists(fp):
        with open(fp, "rb") as f:
            content = f.read()
        return web.Response(body=content, content_type="image/x-icon", headers={
            "Cache-Control": "public, max-age=604800, immutable",
            "Access-Control-Allow-Origin": "*"
        })
    from ui_theme import FAVICON_SVG
    return web.Response(text=FAVICON_SVG, content_type="image/svg+xml")

def _make_avatar_sig(user_id: int) -> str:
    """Build HMAC-SHA256 signature binding an avatar URL to its Telegram user_id."""
    import crypto_auth
    secret = crypto_auth._get_signing_key()
    return _hmac.new(secret, f"avatar:{int(user_id)}".encode("utf-8"), _hashlib.sha256).hexdigest()[:20]


def _verify_avatar_sig(user_id: int, sig: str) -> bool:
    """Verify avatar URL signature in constant time."""
    if not sig or not isinstance(sig, str) or len(sig.strip()) < 16:
        return False
    return _hmac.compare_digest(_make_avatar_sig(user_id), sig.strip())


def _build_signed_avatar_url(user_id: int, force_refresh: bool = False) -> str:
    """Build signed avatar URL suitable for <img> tags (works in Mini App iframes without cookies)."""
    base = f"/api/user/avatar/{int(user_id)}?sig={_make_avatar_sig(int(user_id))}"
    if force_refresh:
        base += f"&refresh=1&v={int(time.time())}"
    return base


_RASTER_FAST_CACHE: dict[str, tuple[bytes, str, str]] = {}
_RASTER_FAST_CACHE_MAX = 256


def _compress_raster_image(raw_bytes: bytes, max_dim: int = 96, quality: int = 82) -> tuple[bytes, str]:
    """Downscale and compress static raster images to compact WebP without breaking animations."""
    if not raw_bytes or len(raw_bytes) < 12:
        return raw_bytes, "application/octet-stream"
    fallback_mime = _detect_raster_mime(raw_bytes) or "image/jpeg"
    try:
        from io import BytesIO
        from PIL import Image, ImageOps
        with Image.open(BytesIO(raw_bytes)) as img:
            # Skip multi-frame animated images (e.g., animated WebP/GIF)
            if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
                return raw_bytes, fallback_mime
            img = ImageOps.exif_transpose(img)
            if max_dim > 0 and (img.width > max_dim or img.height > max_dim):
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            out = BytesIO()
            img.save(out, format="WEBP", quality=quality, method=4)
            compact = out.getvalue()
            if compact and (len(compact) < len(raw_bytes) or fallback_mime != "image/webp"):
                return compact, "image/webp"
    except Exception:
        pass
    return raw_bytes, fallback_mime


def _cache_raster_put(key: str, data: bytes, mime: str) -> tuple[bytes, str, str]:
    etag = f'"{_hashlib.sha256(data).hexdigest()[:16]}"'
    if len(_RASTER_FAST_CACHE) >= _RASTER_FAST_CACHE_MAX:
        _RASTER_FAST_CACHE.pop(next(iter(_RASTER_FAST_CACHE)), None)
    _RASTER_FAST_CACHE[key] = (data, mime, etag)
    return data, mime, etag


def _detect_raster_mime(data: bytes):
    """Validate image magic bytes and return safe raster MIME type or None."""
    if not data or len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _is_safe_tg_avatar_url(url: str) -> bool:
    """Strictly allow HTTPS Telegram CDN avatar URLs only (SSRF guard)."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = _urlparse(url.strip())
        if parsed.scheme != "https":
            return False
        host = (parsed.hostname or "").lower()
        return (
            host in ("t.me", "telegram.org", "cdn4.telegram-cdn.org", "cdn5.telegram-cdn.org", "cdn1.telegram-cdn.org")
            or host.endswith(".telegram-cdn.org")
            or host.endswith(".telesco.pe")
        )
    except Exception:
        return False


async def handle_api_user_avatar(request):
    """Foydalanuvchining rasmiy Telegram avatarini HMAC imzo/autentifikatsiya orqali yuklovchi endpoint (Zero fake fallback)"""
    import aiohttp

    uid_str = request.match_info.get("user_id", "").strip()
    if not uid_str.isdigit():
        return web.Response(status=400, text="Invalid user_id")
    user_id = int(uid_str)
    if user_id <= 0 or user_id > 10**14:
        return web.Response(status=400, text="Invalid user_id")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    avatars_dir = os.path.realpath(os.path.join(base_dir, "nft_assets", "user_avatars"))
    os.makedirs(avatars_dir, exist_ok=True)
    local_avatar = os.path.realpath(os.path.join(avatars_dir, f"{user_id}.jpg"))
    if not local_avatar.startswith(avatars_dir + os.sep):
        return web.Response(status=400, text="Invalid user_id")

    refresh = request.query.get("refresh", "0") in ("1", "true")
    sig = request.query.get("sig", "").strip()
    auth_uid = get_authenticated_user_id(request)
    is_authorized = _verify_avatar_sig(user_id, sig) or (auth_uid and auth_uid == user_id) or is_admin_request(request)

    headers = {
        "Cache-Control": "no-store" if refresh else "public, max-age=3600, stale-while-revalidate=86400",
        "Access-Control-Allow-Origin": "*",
    }

    def _serve_compact_avatar(raw_data: bytes, persist_path: str | None = None):
        compact_data, compact_mime = _compress_raster_image(raw_data, max_dim=96, quality=82)
        if persist_path and (len(raw_data) > 10240 or compact_data != raw_data):
            try:
                with open(persist_path, "wb") as wf:
                    wf.write(compact_data)
            except Exception:
                pass
        _, _, etag = _cache_raster_put(f"avatar:{user_id}", compact_data, compact_mime)
        resp_headers = {**headers, "ETag": etag, "Content-Length": str(len(compact_data))}
        if not refresh and request.headers.get("If-None-Match") == etag:
            return web.Response(status=304, headers=resp_headers)
        return web.Response(body=compact_data, content_type=compact_mime, headers=resp_headers)

    # 1. Serve cached disk image if valid raster and fresh (< 6h) when not force-refreshed
    cache_ttl = 21600
    if not refresh and os.path.exists(local_avatar) and os.path.getsize(local_avatar) > 64:
        try:
            age = time.time() - os.path.getmtime(local_avatar)
            with open(local_avatar, "rb") as f:
                cached_bytes = f.read()
            cached_mime = _detect_raster_mime(cached_bytes)
            if cached_mime and (age < cache_ttl or not is_authorized):
                return _serve_compact_avatar(cached_bytes, persist_path=local_avatar if len(cached_bytes) > 10240 else None)
        except Exception:
            pass

    if not is_authorized:
        return web.Response(status=404, text="Avatar not found", headers={"Cache-Control": "no-store"})

    # 2. Fetch fresh Telegram profile photo via Bot API (getUserProfilePhotos -> getFile -> file)
    try:
        from config import BOT_TOKEN
        token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
        if token and not token.startswith("123456:"):
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{token}/getUserProfilePhotos?user_id={user_id}&limit=1"
                async with session.get(url, timeout=5) as r:
                    res = await r.json()
                    if res.get("ok") and res.get("result", {}).get("photos"):
                        sizes = res["result"]["photos"][0]
                        best_photo = sizes[1] if len(sizes) > 1 else sizes[0]
                        fid = best_photo["file_id"]
                        async with session.get(f"https://api.telegram.org/bot{token}/getFile?file_id={fid}", timeout=5) as fr:
                            fres = await fr.json()
                            if fres.get("ok"):
                                fp = fres["result"]["file_path"]
                                dl_url = f"https://api.telegram.org/file/bot{token}/{fp}"
                                async with session.get(dl_url, timeout=10) as dr:
                                    if dr.status == 200:
                                        img_data = await dr.content.read(2 * 1024 * 1024 + 1)
                                        mime = _detect_raster_mime(img_data)
                                        if mime and len(img_data) <= 2 * 1024 * 1024:
                                            return _serve_compact_avatar(img_data, persist_path=local_avatar)

                # 3. Fallback: persisted Telegram CDN photo_url from bot_users (if privacy restricted Bot API photos)
                try:
                    import database
                    conn = database.get_db()
                    if conn:
                        try:
                            cur = conn.cursor()
                            cur.execute("SELECT photo_url FROM bot_users WHERE tg_user_id = %s", (user_id,))
                            prow = cur.fetchone()
                            db_url = (prow["photo_url"] if isinstance(prow, dict) else prow[0]) if prow else None
                        finally:
                            conn.close()
                        if db_url and _is_safe_tg_avatar_url(str(db_url)):
                            async with session.get(str(db_url).strip(), timeout=8) as dr2:
                                if dr2.status == 200:
                                    img_data = await dr2.content.read(2 * 1024 * 1024 + 1)
                                    mime = _detect_raster_mime(img_data)
                                    if mime and len(img_data) <= 2 * 1024 * 1024:
                                        return _serve_compact_avatar(img_data, persist_path=local_avatar)
                except Exception:
                    pass
    except Exception as e:
        print(f"[handle_api_user_avatar] Error fetching for {user_id}: {e}")

    # Serve stale valid cache if network transiently failed
    if os.path.exists(local_avatar) and os.path.getsize(local_avatar) > 64:
        try:
            with open(local_avatar, "rb") as f:
                stale_bytes = f.read()
            stale_mime = _detect_raster_mime(stale_bytes)
            if stale_mime:
                return _serve_compact_avatar(stale_bytes)
        except Exception:
            pass

    return web.Response(status=404, text="Avatar not found", headers={"Cache-Control": "private, max-age=120"})

async def handle_api_stars_open_case_uzs(request):
    """Web Dashboard orqali UZS (so'm) balansi bilan keys ochish (Anti-IDOR himoyalangan).
    Yutilgan sovg'a foydalanuvchining shaxsiy inventariga (pending_gifts) tushadi (avto-withdraw qilinmaydi, Upgraderda bepul ishlatish mumkin).
    """
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Noto'g'ri JSON ma'lumot"}, status=400)
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
        from games_monetization import open_stars_case_with_uzs
        res = open_stars_case_with_uzs(user_id, tier_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/open-case-uzs] error: {e}")
        return web.json_response({"ok": False, "error": "Keysni ochishda ichki xatolik yuz berdi"}, status=500)

async def handle_api_stars_create_invoice(request):
    """Telegram Stars to'lovi uchun Telegram createInvoiceLink yaratish (Anti-IDOR)"""
    try:
        import time as _t
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Noto'g'ri JSON ma'lumot"}, status=400)
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        from games_monetization import STARS_CASES
        case = STARS_CASES.get(tier_id)
        if not case:
            for c in STARS_CASES.values():
                if c["key"] == tier_id or c["id"] == tier_id:
                    case = c
                    break
        if not case:
            return web.json_response({"ok": False, "error": "Keys topilmadi"}, status=404)

        from config import BOT_TOKEN
        import aiohttp
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
        payload = {
            "title": case["name"],
            "description": case["description"],
            "payload": f"stars_box_{case['key']}_{user_id}_{int(_t.time())}",
            "currency": "XTR",
            "prices": [{"label": case["name"], "amount": case["price_stars"]}]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                tg_data = await resp.json()
                if tg_data.get("ok"):
                    return web.json_response({"ok": True, "invoice_link": tg_data.get("result")})
                return web.json_response({"ok": False, "error": tg_data.get("description", "Invoice yaratilmadi")}, status=400)
    except Exception as e:
        print(f"[api/stars/create-invoice] error: {type(e).__name__}")
        return web.json_response({"ok": False, "error": "To'lov havolasini yaratishda xatolik yuz berdi"}, status=500)


async def handle_api_stars_recent_drops(request):
    """Jonli so'nggi unboxing va yutuqlar lentasi"""
    from games_monetization import get_recent_drops
    drops = get_recent_drops(15)
    return web.json_response({"ok": True, "drops": drops}, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_pvp_battles(request):
    """Ochiq PvP janglar ro'yxati"""
    from games_monetization import get_open_case_battles
    battles = get_open_case_battles()
    return web.json_response({"ok": True, "battles": battles}, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_pvp_create(request):
    """Yangi PvP keys jangi ochish (Anti-IDOR)"""
    try:
        data = await request.json()
        host_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        host_name = str(data.get("user_name", "")).strip()[:64]
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        import database
        if database.is_user_banned(host_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
        from games_monetization import create_case_battle
        res = create_case_battle(host_id, host_name, tier_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/pvp/create] error: {e}")
        return web.json_response({"ok": False, "error": "PvP jangini yaratishda xatolik yuz berdi"}, status=500)

async def handle_api_stars_pvp_join(request):
    """PvP jangga qo'shilish va g'olibni aniqlash (Anti-IDOR)"""
    try:
        data = await request.json()
        guest_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        battle_id = str(data.get("battle_id", "")).strip()
        guest_name = str(data.get("user_name", "")).strip()[:64]
        import database
        if database.is_user_banned(guest_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
        from games_monetization import join_and_resolve_battle
        res = join_and_resolve_battle(battle_id, guest_id, guest_name)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/pvp/join] error: {e}")
        return web.json_response({"ok": False, "error": "PvP jangga qo'shilishda xatolik yuz berdi"}, status=500)

async def handle_api_stars_pvp_cancel(request):
    """PvP keys jangini bekor qilish va hostga mablag'ni qaytarish (Anti-IDOR)"""
    try:
        data = await request.json()
        host_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        battle_id = str(data.get("battle_id", "")).strip()
        from games_monetization import cancel_case_battle
        res = cancel_case_battle(battle_id, host_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/pvp/cancel] error: {e}")
        return web.json_response({"ok": False, "error": "PvP jangini bekor qilishda xatolik yuz berdi"}, status=500)

async def handle_api_stars_marketplace_nfts(request):
    """
    Getgems & Fragment rasmiy marketplace dagi barcha real sotuvdagi NFT lar.
    Qat'iy narx bo'yicha o'sish tartibida (ASC: min -> max).
    1 TON kursi CBU va TonAPI dan real-time olinib, har bir buyumning
    aniq so'mdagi (UZS) va Stars dagi qiymati hisoblanadi.
    """
    try:
        from telegram_marketplace_service import get_live_marketplace_stock_asc, get_sync_live_ton_rate
        stock = await get_live_marketplace_stock_asc()
        rate = get_sync_live_ton_rate()
        return web.json_response({
            "ok": True,
            "total": len(stock),
            "rate": rate,
            "items": stock
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[api/stars/marketplace-nfts] error: {e}")
        return web.json_response({"ok": False, "error": "Marketplace katalogini yuklashda ichki xatolik yuz berdi"}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_ton_rate(request):
    """Real-time live TON va UZS kursini olish"""
    try:
        from telegram_marketplace_service import get_sync_live_ton_rate
        rate = get_sync_live_ton_rate()
        return web.json_response({"ok": True, "rate": rate}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[api/stars/ton-rate] error: {e}")
        return web.json_response({"ok": False, "error": "TON kursini olishda ichki xatolik yuz berdi"}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_user_inventory(request):
    """Foydalanuvchining shaxsiy yutib olgan sovg'alari va NFT lari (Anti-IDOR himoyalangan)"""
    try:
        user_id, auth_err = _require_user_auth(request, allow_admin=True)
        if auth_err:
            return auth_err
        import database
        import re
        raw_gifts = database.get_user_gift_history(user_id, limit=50)
        formatted = []
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync, get_sync_live_ton_rate

        market_stock = fetch_live_marketplace_stock_sync() or []
        rate = get_sync_live_ton_rate()
        ton_uzs = rate.get("ton_uzs", 15700.0)

        STANDARD_GIFT_MEDIA = {
            "cake": {
                "file_id": "5170144170496491616",
                "slug": "delicious-cake",
                "image_url": "/api/nft/image/delicious_cake.webp",
            },
            "star": {
                "file_id": "5170250947678437525",
                "slug": "gift-box",
                "image_url": "/api/nft/image/gift_star.webp",
            },
            "heart": {
                "file_id": "5170145012310081615",
                "slug": "heart-box",
                "image_url": "/api/nft/image/gift_star.webp",
            },
            "teddy": {
                "file_id": "5170233102089322756",
                "slug": "teddy-bear",
                "image_url": "https://nft.fragment.com/gift/toybear-7605.medium.jpg",
            },
            "bouquet": {
                "file_id": "5170314324215857265",
                "slug": "bouquet-flowers",
                "image_url": "/api/nft/image/gift_bouquet.webp",
            },
            "champagne": {
                "file_id": "6028601630662853006",
                "slug": "champagne-bottle",
                "image_url": "/api/nft/image/champagne_bottle.webp",
            },
            "diamond_ring": {
                "file_id": "5170690322832818290",
                "slug": "diamond-ring",
                "image_url": "/api/nft/image/diamond_ring.webp",
            },
            "blue_diamond": {
                "file_id": "5170521118301225164",
                "slug": "blue-diamond",
                "image_url": "/api/nft/image/diamond_ring.webp",
            },
            "trophy": {
                "file_id": "5168043875654172773",
                "slug": "golden-trophy",
                "image_url": "/api/nft/image/star_trophy.webp",
            },
            "rocket": {
                "file_id": "5170564780938756245",
                "slug": "space-rocket",
                "image_url": "/api/nft/image/gift_rocket.webp",
            },
            "rose": {
                "file_id": "5168103777563050263",
                "slug": "red-rose",
                "image_url": "/api/nft/image/gift_bouquet.webp",
            },
            "package": {
                "file_id": "5170250947678437525",
                "slug": "gift-box",
                "image_url": "/api/nft/image/delicious_cake.webp",
            },
        }

        NFT_KEYWORD_SLUGS = [
            ("chill flame", "chillflame-102714"),
            ("desk calendar", "deskcalendar-269416"),
            ("b-day candle", "bdaycandle-149535"),
            ("bday candle", "bdaycandle-149535"),
            ("tama gadget", "tamagadget-10816"),
            ("snoop cigar", "snoopcigar-56790"),
            ("vintage cigar", "vintagecigar-1305"),
            ("swiss watch", "swisswatch-19581"),
            ("durov", "durovscap-3226"),
            ("plush pepe", "plushpepe-2163"),
            ("pepe", "plushpepe-2163"),
            ("heart locket", "heartlocket-416"),
            ("scared cat", "scaredcat-15008"),
            ("magic potion", "magicpotion-1036"),
            ("toy bear", "toybear-7605"),
            ("diamond ring #", "diamondring-26180"),
            ("golden dragon", "vintagecigar-1305"),
            ("crown", "swisswatch-19581"),
        ]

        for g_idx, g in enumerate(raw_gifts):
            stars = int(g.get("prize_stars") or 25)
            p_name = str(g.get("prize_name") or "Telegram Sovg'a")
            raw_gid = str(g.get("gift_id") or "").strip()
            p_lower = p_name.lower()

            if p_lower == "green star":
                p_name = "Gift Box"
                p_lower = "gift box"

            icon = "package"
            if "cake" in p_lower: icon = "cake"
            elif "heart" in p_lower: icon = "heart"
            elif "star" in p_lower: icon = "star"
            elif "teddy" in p_lower or "bear" in p_lower: icon = "teddy"
            elif "bouquet" in p_lower or "flower" in p_lower: icon = "bouquet"
            elif "rose" in p_lower: icon = "rose"
            elif "champagne" in p_lower: icon = "champagne"
            elif "blue diamond" in p_lower: icon = "blue_diamond"
            elif "ring" in p_lower or "diamond" in p_lower: icon = "diamond_ring"
            elif "trophy" in p_lower: icon = "trophy"
            elif "rocket" in p_lower: icon = "rocket"
            elif "cap" in p_lower: icon = "cap"
            elif "plush" in p_lower or "pepe" in p_lower: icon = "plush"
            elif "crown" in p_lower: icon = "crown"

            has_fragment_slug = bool(re.match(r"^[a-z0-9]+-\d+$", raw_gid, re.I))
            is_nft = bool(
                has_fragment_slug
                or g.get("is_nft")
                or "nft" in p_lower
                or "collectible" in p_lower
                or "#" in p_name
                or (stars >= 550 and "telegram sovg" not in p_lower and "premium" not in p_lower)
            )
            rarity = "legendary" if (stars >= 500 or is_nft) else ("rare" if stars >= 50 else "common")

            image_url = g.get("image_url") or ""
            backdrop = "linear-gradient(145deg, #18181b 0%, #09090b 100%)"
            matched_edition = g.get("edition") or ""
            resolved_file_id = ""
            resolved_slug = raw_gid.lower() if has_fragment_slug else ""
            file_type = "tgs"

            if is_nft:
                if market_stock:
                    matched_item = None
                    for it in market_stock:
                        it_slug = str(it.get("slug") or "").lower()
                        if (resolved_slug and it_slug == resolved_slug) or it.get("collection", "").lower() in p_lower or it.get("name", "").lower() in p_lower:
                            matched_item = it
                            break
                    if matched_item:
                        if not resolved_slug:
                            resolved_slug = str(matched_item.get("slug") or "")
                        if not image_url:
                            image_url = matched_item.get("image_url") or ""
                        if not matched_edition:
                            matched_edition = matched_item.get("edition", "")
                        backdrop = matched_item.get("backdrop", backdrop)
                if not resolved_slug:
                    for kw, kw_slug in NFT_KEYWORD_SLUGS:
                        if kw in p_lower:
                            resolved_slug = kw_slug
                            break
                    if not resolved_slug:
                        resolved_slug = "chillflame-102714"
                if not image_url and resolved_slug:
                    image_url = f"https://nft.fragment.com/gift/{resolved_slug}.medium.jpg"
            else:
                # Standart Telegram sovg'asi
                if "telegram sovg" in p_lower or p_name == "Telegram Gift":
                    distinct_gifts = [
                        ("Delicious Cake", "cake", 15),
                        ("Gift Box", "package", 25),
                        ("Teddy Bear", "teddy", 50),
                        ("Bouquet of Flowers", "bouquet", 50),
                        ("Red Rose", "rose", 25),
                        ("Champagne Bottle", "champagne", 50),
                    ]
                    chosen = distinct_gifts[g_idx % len(distinct_gifts)]
                    p_name, icon, stars = chosen[0], chosen[1], chosen[2]

                std_meta = STANDARD_GIFT_MEDIA.get(icon, STANDARD_GIFT_MEDIA["cake"])
                resolved_file_id = std_meta["file_id"]
                resolved_slug = std_meta["slug"]
                if not image_url:
                    image_url = std_meta["image_url"]

            formatted.append({
                "id": g.get("id"),
                "gift_id": resolved_file_id or raw_gid or resolved_slug,
                "prize_name": p_name,
                "prize_stars": stars,
                "rarity": rarity,
                "icon": icon,
                "is_nft": is_nft,
                "file_id": resolved_file_id,
                "file_type": file_type,
                "slug": resolved_slug,
                "image_url": image_url,
                "backdrop": backdrop,
                "edition": matched_edition,
                "price_uzs": stars * 400,
                "price_ton": round((stars * 400) / max(1.0, ton_uzs), 2),
                "status": g.get("status", "pending"),
                "date": str(g.get("created_at") or "Yaqinda")[:10]
            })
        return web.json_response({"ok": True, "gifts": formatted, "rate": rate})
    except Exception as e:
        print(f"[api/stars/user-inventory] error: {e}")
        return web.json_response({"ok": False, "error": "Inventarni yuklashda ichki xatolik yuz berdi"}, status=500)

_NFT_ANIMATION_CACHE = {}
_NFT_ANIMATION_CACHE_MAX = 200

_STANDARD_GIFT_SLUGS_TO_FILE_ID = {
    "golden-trophy": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",
    "star-trophy": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",
    "delicious-cake": "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E",
    "birthday-cake": "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E",
    "champagne-bottle": "CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ",
    "bouquet-flowers": "CAACAgIAAxUAAWrS2uNt8sIHLaoAAZeEbczG8VU45QAC3iUAAkUg4ErI5hOgFM9DXj0E",
    "diamond-ring": "CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ",
    "space-rocket": "CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ",
    "blue-diamond": "CAACAgIAAxUAAWrS2uOdst4ZTcyZTnYZPBO024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ",
    "heart-box": "CAACAgIAAxUAAWrS2uM_EewXTXxghtF9VyKlBMUvAAJ8GwACkoTYS_itxFzPIpm1PQQ",
    "green-star": "CAACAgIAAxUAAWrS2uM0EZJ7Dun5N1H-6YKcZfl3AAKNSAACsU84SMuB4ge7V_wGPQQ",
    "red-heart": "CAACAgIAAxUAAWrS2uM_EewXTXxghtF9VyKlBMUvAAJ8GwACkoTYS_itxFzPIpm1PQQ",
    "teddy-bear": "CAACAgIAAxUAAWrS2uO_yFyaqnGsGU2Rb6B3zOCwAAKtVAACmj_pSnvPkDQv_sivPQQ",
    "gift-box": "CAACAgIAAxUAAWrS2uM0EZJ7Dun5N1H-6YKcZfl3AAKNSAACsU84SMuB4ge7V_wGPQQ",
    "red-rose": "CAACAgIAAxUAAWrS2uMBc0LraApyb-75XswisR0tAAJxGQAC1P-BS9CYmaAv74KEPQQ",
    **_GIFT_ID_TO_FILE_ID,
}

EMPTY_LOTTIE_JSON = b'{"v":"5.5.7","fr":60,"ip":0,"op":60,"w":100,"h":100,"nm":"empty","ddd":0,"assets":[],"layers":[]}'

async def handle_api_nft_animation(request):
    """
    Fragment Telegram Gift NFT larining va standart Telegram sovg'alarining rasmiy .tgs Lottie
    vektor animatsiyasini decompress qilib, toza JSON sifatida qaytaradi (Strict Slug + Zip-Bomb + Bounded Cache).
    """
    slug = request.match_info.get("slug", "").strip()
    if not slug or not _SLUG_PATTERN.match(slug):
        return web.Response(status=400, text="Invalid slug")
        
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=604800, immutable"
    }

    # 0. Mahalliy rasmiy Telegram Lottie (.tgs -> JSON) fayllaridan tezkor uzatish
    local_lottie = _get_local_gift_lottie_bytes(slug)
    if local_lottie:
        if len(_NFT_ANIMATION_CACHE) >= _NFT_ANIMATION_CACHE_MAX:
            _NFT_ANIMATION_CACHE.pop(next(iter(_NFT_ANIMATION_CACHE)), None)
        _NFT_ANIMATION_CACHE[slug] = local_lottie
        return web.Response(
            body=local_lottie,
            content_type="application/json",
            headers=headers
        )

    if slug in _NFT_ANIMATION_CACHE:
        return web.Response(
            body=_NFT_ANIMATION_CACHE[slug],
            content_type="application/json",
            headers=headers
        )

    # 1. Standart Telegram sovg'alari uchun Bot API orqali rasmiy sticker .tgs olish
    if slug in _STANDARD_GIFT_SLUGS_TO_FILE_ID:
        try:
            from config import BOT_TOKEN
            import aiohttp
            import os
            token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
            if token:
                file_id = _STANDARD_GIFT_SLUGS_TO_FILE_ID[slug]
                async with aiohttp.ClientSession() as session:
                    file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
                    async with session.get(file_url, timeout=6) as r1:
                        res1 = await r1.json()
                        if res1.get("ok"):
                            file_path = res1["result"]["file_path"]
                            download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                            async with session.get(download_url, timeout=10) as r2:
                                if r2.status == 200:
                                    raw = await r2.content.read(2 * 1024 * 1024 + 1)
                                    if len(raw) <= 2 * 1024 * 1024:
                                        try:
                                            decompressed = _safe_gzip_decompress(raw, max_size=5 * 1024 * 1024)
                                        except Exception:
                                            decompressed = raw
                                        if len(_NFT_ANIMATION_CACHE) >= _NFT_ANIMATION_CACHE_MAX:
                                            _NFT_ANIMATION_CACHE.pop(next(iter(_NFT_ANIMATION_CACHE)), None)
                                        _NFT_ANIMATION_CACHE[slug] = decompressed
                                        return web.Response(
                                            body=decompressed,
                                            content_type="application/json",
                                            headers=headers
                                        )
        except Exception as tg_anim_err:
            print(f"Standard gift animation fetch note for {slug}: {tg_anim_err}")

    # 2. Fragment NFT collectible lar uchun Fragment CDN dan .tgs olish
    url = f"https://nft.fragment.com/gift/{slug}.tgs"
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=False) as resp:
                if resp.status == 200:
                    raw_data = await resp.content.read(2 * 1024 * 1024 + 1)
                    if len(raw_data) > 2 * 1024 * 1024:
                        return web.Response(body=EMPTY_LOTTIE_JSON, content_type="application/json", headers=headers)
                    try:
                        decompressed = _safe_gzip_decompress(raw_data, max_size=5 * 1024 * 1024)
                    except Exception:
                        decompressed = raw_data
                    if len(_NFT_ANIMATION_CACHE) >= _NFT_ANIMATION_CACHE_MAX:
                        _NFT_ANIMATION_CACHE.pop(next(iter(_NFT_ANIMATION_CACHE)), None)
                    _NFT_ANIMATION_CACHE[slug] = decompressed
                    return web.Response(
                        body=decompressed,
                        content_type="application/json",
                        headers=headers
                    )
                else:
                    return web.Response(
                        body=EMPTY_LOTTIE_JSON,
                        content_type="application/json",
                        headers=headers
                    )
    except Exception:
        return web.Response(
            body=EMPTY_LOTTIE_JSON,
            content_type="application/json",
            headers=headers
        )

async def handle_api_stars_upgrader_inventory(request):
    """Upgrader uchun barcha darajadagi (1.5x dan 100x gacha, 15 Stars dan 250,000 Stars gacha)
    haqiqiy 60fps animatsiyali Telegram sovg'alari va Fragment Collectible NFT lar katalogi.
    """
    try:
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync

        # 1. Asosiy barcha multiplikator diapazonlarini qamrab oluvchi rasmiy katalog (har biri haqiqiy .tgs animatsiyaga ega)
        base_catalog = [
            {
                "id": "5170233102089322756", "stars": 15, "name": "Teddy Bear", "icon": "teddy",
                "file_id": "5170233102089322756",
                "slug": "teddy-bear", "file_type": "tgs", "image_url": "https://nft.fragment.com/gift/toybear-7605.medium.jpg",
                "is_nft": False, "rarity": "common"
            },
            {
                "id": "5170145012310081615", "stars": 15, "name": "Heart Box", "icon": "heart",
                "file_id": "5170145012310081615",
                "slug": "heart-box", "file_type": "tgs", "image_url": "/api/nft/image/gift_star.webp",
                "is_nft": False, "rarity": "common"
            },
            {
                "id": "5170250947678437525", "stars": 25, "name": "Gift Box", "icon": "package",
                "file_id": "5170250947678437525",
                "slug": "gift-box", "file_type": "tgs", "image_url": "/api/nft/image/delicious_cake.webp",
                "is_nft": False, "rarity": "common"
            },
            {
                "id": "5168103777563050263", "stars": 35, "name": "Red Rose", "icon": "rose",
                "file_id": "5168103777563050263",
                "slug": "red-rose", "file_type": "tgs", "image_url": "/api/nft/image/gift_bouquet.webp",
                "is_nft": False, "rarity": "common"
            },
            {
                "id": "5170144170496491616", "stars": 50, "name": "Delicious Cake", "icon": "cake",
                "file_id": "5170144170496491616",
                "slug": "delicious-cake", "file_type": "tgs", "image_url": "/api/nft/image/delicious_cake.webp",
                "is_nft": False, "rarity": "common"
            },
            {
                "id": "5170314324215857265", "stars": 75, "name": "Bouquet of Flowers", "icon": "bouquet",
                "file_id": "5170314324215857265",
                "slug": "bouquet-flowers", "file_type": "tgs", "image_url": "/api/nft/image/gift_bouquet.webp",
                "is_nft": False, "rarity": "rare"
            },
            {
                "id": "6028601630662853006", "stars": 100, "name": "Champagne Bottle", "icon": "champagne",
                "file_id": "CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ",
                "slug": "champagne-bottle", "file_type": "tgs", "image_url": "/api/nft/image/champagne_bottle.webp",
                "is_nft": False, "rarity": "rare"
            },
            {
                "id": "5170690322832818290", "stars": 150, "name": "Diamond Ring", "icon": "diamond_ring",
                "file_id": "CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ",
                "slug": "diamond-ring", "file_type": "tgs", "image_url": "/api/nft/image/diamond_ring.webp",
                "is_nft": False, "rarity": "rare"
            },
            {
                "id": "5168043875654172773", "stars": 200, "name": "Golden Trophy", "icon": "trophy",
                "file_id": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",
                "slug": "golden-trophy", "file_type": "tgs", "image_url": "/api/nft/image/star_trophy.webp",
                "is_nft": False, "rarity": "rare"
            },
            {
                "id": "5170521118301225164", "stars": 250, "name": "Blue Diamond Gift", "icon": "diamond_ring",
                "file_id": "CAACAgIAAxUAAWrS2uOdst4ZTcyZTnYZPBO024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ",
                "slug": "blue-diamond", "file_type": "tgs", "image_url": "/api/nft/image/diamond_ring.webp",
                "is_nft": False, "rarity": "rare"
            },
            {
                "id": "5170564780938756245", "stars": 300, "name": "Space Rocket", "icon": "rocket",
                "file_id": "CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ",
                "slug": "space-rocket", "file_type": "tgs", "image_url": "/api/nft/image/gift_rocket.webp",
                "is_nft": False, "rarity": "epic"
            },
            {
                "id": "chillflame-102714", "stars": 400, "name": "Chill Flame #102714 NFT", "icon": "star",
                "file_id": "", "slug": "chillflame-102714", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/chillflame-102714.medium.jpg",
                "is_nft": True, "rarity": "epic"
            },
            {
                "id": "tamagadget-10816", "stars": 500, "name": "Tama Gadget #10816 NFT", "icon": "package",
                "file_id": "", "slug": "tamagadget-10816", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/tamagadget-10816.medium.jpg",
                "is_nft": True, "rarity": "epic"
            },
            {
                "id": "bdaycandle-149535", "stars": 750, "name": "B-Day Candle #149535 NFT", "icon": "candle",
                "file_id": "", "slug": "bdaycandle-149535", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/bdaycandle-149535.medium.jpg",
                "is_nft": True, "rarity": "legendary"
            },
            {
                "id": "deskcalendar-269416", "stars": 1000, "name": "Desk Calendar #269416 NFT", "icon": "calendar",
                "file_id": "", "slug": "deskcalendar-269416", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/deskcalendar-269416.medium.jpg",
                "is_nft": True, "rarity": "legendary"
            },
            {
                "id": "magicpotion-1036", "stars": 1500, "name": "Magic Potion #1036 NFT", "icon": "potion",
                "file_id": "", "slug": "magicpotion-1036", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/magicpotion-1036.medium.jpg",
                "is_nft": True, "rarity": "legendary"
            },
            {
                "id": "snoopcigar-56790", "stars": 2500, "name": "Snoop Cigar #56790 NFT", "icon": "cigar",
                "file_id": "", "slug": "snoopcigar-56790", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/snoopcigar-56790.medium.jpg",
                "is_nft": True, "rarity": "legendary"
            },
            {
                "id": "diamondring-26180", "stars": 4000, "name": "Diamond Ring #26180 NFT", "icon": "ring",
                "file_id": "", "slug": "diamondring-26180", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/diamondring-26180.medium.jpg",
                "is_nft": True, "rarity": "legendary"
            },
            {
                "id": "toybear-7605", "stars": 5000, "name": "Toy Bear #7605 NFT", "icon": "teddy",
                "file_id": "", "slug": "toybear-7605", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/toybear-7605.medium.jpg",
                "is_nft": True, "rarity": "legendary"
            },
            {
                "id": "vintagecigar-1305", "stars": 6720, "name": "Vintage Cigar #1305 NFT", "icon": "cigar",
                "file_id": "", "slug": "vintagecigar-1305", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/vintagecigar-1305.medium.jpg",
                "is_nft": True, "rarity": "transcendent"
            },
            {
                "id": "swisswatch-19581", "stars": 10000, "name": "Swiss Watch #19581 NFT", "icon": "watch",
                "file_id": "", "slug": "swisswatch-19581", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/swisswatch-19581.medium.jpg",
                "is_nft": True, "rarity": "transcendent"
            },
            {
                "id": "plushpepe-2163", "stars": 25000, "name": "Plush Pepe #2163 NFT", "icon": "plush",
                "file_id": "", "slug": "plushpepe-2163", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/plushpepe-2163.medium.jpg",
                "is_nft": True, "rarity": "transcendent"
            },
            {
                "id": "scaredcat-15008", "stars": 50000, "name": "Scared Cat #15008 NFT", "icon": "cat",
                "file_id": "", "slug": "scaredcat-15008", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/scaredcat-15008.medium.jpg",
                "is_nft": True, "rarity": "transcendent"
            },
            {
                "id": "durovscap-3226", "stars": 75000, "name": "Durov's Cap #3226 NFT", "icon": "cap",
                "file_id": "", "slug": "durovscap-3226", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/durovscap-3226.medium.jpg",
                "is_nft": True, "rarity": "transcendent"
            },
            {
                "id": "heartlocket-416", "stars": 150000, "name": "Heart Locket #416 NFT", "icon": "locket",
                "file_id": "", "slug": "heartlocket-416", "file_type": "tgs",
                "image_url": "https://nft.fragment.com/gift/heartlocket-416.medium.jpg",
                "is_nft": True, "rarity": "transcendent"
            },
        ]

        combined = []
        seen_slugs = set()

        for cat_item in base_catalog:
            seen_slugs.add(cat_item["slug"])
            combined.append({
                "id": cat_item["id"],
                "gift_name": cat_item["name"],
                "name": cat_item["name"],
                "stars_value": cat_item["stars"],
                "stars": cat_item["stars"],
                "icon": cat_item["icon"],
                "file_id": cat_item["file_id"],
                "slug": cat_item["slug"],
                "file_type": "tgs",
                "image_url": cat_item["image_url"],
                "is_nft": cat_item["is_nft"],
                "rarity": cat_item["rarity"],
            })

        # 2. Live Fragment Marketplace stock'dan ham qo'shimcha real NFT larni qo'shish
        market_stock = fetch_live_marketplace_stock_sync() or []
        for m_item in market_stock[:60]:
            m_slug = str(m_item.get("slug") or "").strip()
            if not m_slug or m_slug in seen_slugs:
                continue
            seen_slugs.add(m_slug)
            m_stars = int(m_item.get("stars") or 840)
            m_name = f"{m_item.get('name', 'NFT')} {m_item.get('edition', '')}".strip()
            combined.append({
                "id": m_slug,
                "gift_name": m_name,
                "name": m_name,
                "stars_value": m_stars,
                "stars": m_stars,
                "icon": "star",
                "file_id": "",
                "slug": m_slug,
                "file_type": "tgs",
                "image_url": m_item.get("image_url") or f"https://nft.fragment.com/gift/{m_slug}.medium.jpg",
                "is_nft": True,
                "rarity": "legendary" if m_stars < 5000 else "transcendent",
            })

        combined.sort(key=lambda x: int(x.get("stars") or 0))
        return web.json_response({"ok": True, "inventory": combined}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[api/stars/upgrader/inventory] error: {e}")
        return web.json_response({"ok": False, "error": "Upgrader katalogini yuklashda ichki xatolik yuz berdi"}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_marketplace_buy_invoice(request):
    """
    NFT ni Telegram Stars orqali sotib olish uchun rasmiy Telegram createInvoiceLink yaratadi (Anti-IDOR).
    """
    try:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Noto'g'ri JSON ma'lumot"}, status=400)
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        slug = str(data.get("slug", "")).strip()
        
        if not slug or not _SLUG_PATTERN.match(slug):
            return web.json_response({"ok": False, "error": "Yaroqli slug talab qilinadi"}, status=400)
            
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
            
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync, is_nft_live_on_sale, remove_nft_from_cache
        if not is_nft_live_on_sale(slug):
            remove_nft_from_cache(slug)
            return web.json_response({
                "ok": False,
                "error": "Ushbu NFT yaqindagina Fragmentda sotilgan yoki ayni paytda mavjud emas! Sahifa yangilandi, iltimos boshqasini tanlang."
            }, status=400)
            
        stock = fetch_live_marketplace_stock_sync()
        target = None
        for it in stock:
            if it.get("slug") == slug or it.get("id") == slug:
                target = it
                break
                
        if not target:
            return web.json_response({"ok": False, "error": "NFT topilmadi yoki sotilgan!"}, status=404)
            
        from config import BOT_TOKEN
        import aiohttp
        import time as _t
        
        stars_amount = int(target.get("stars", 100))
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
        payload = {
            "title": f"NFT: {target['name']}"[:32],
            "description": f"{target['name']} ({target.get('collection', 'Telegram NFT')}) - Rasmiy Collectible xaridi"[:255],
            "payload": f"stars_nft_{slug}_{user_id}_{int(_t.time())}",
            "currency": "XTR",
            "prices": [{"label": target["name"][:32], "amount": stars_amount}]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                res_data = await resp.json()
                if res_data.get("ok"):
                    return web.json_response({
                        "ok": True,
                        "invoice_link": res_data.get("result"),
                        "stars": stars_amount,
                        "name": target["name"],
                        "slug": slug
                    })
                else:
                    return web.json_response({
                        "ok": False,
                        "error": res_data.get("description", "Invoice yaratib bo'lmadi")
                    }, status=400)
    except Exception as e:
        print(f"[api/stars/marketplace/buy-invoice] error: {type(e).__name__}")
        return web.json_response({"ok": False, "error": "To'lov havolasini yaratishda ichki xatolik yuz berdi"}, status=500)


async def handle_api_stars_marketplace_buy(request):
    """
    Fragment Telegram Gift NFT ni to'g'ridan-to'g'ri bot orqali so'm balansi bilan sotib olish (Anti-IDOR).
    """
    try:
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        slug = str(data.get("slug", "")).strip()
        
        if not slug or not _SLUG_PATTERN.match(slug):
            return web.json_response({"ok": False, "error": "Yaroqli slug talab qilinadi!"}, status=400)
            
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
            
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync, get_sync_live_ton_rate
        market_stock = fetch_live_marketplace_stock_sync()
        target_item = None
        for it in market_stock:
            if it.get("slug") == slug or it.get("id") == slug:
                target_item = it
                break
                
        if not target_item:
            return web.json_response({"ok": False, "error": "Tanlangan NFT topilmadi yoki allaqachon sotilgan!"}, status=404)
            
        rate = get_sync_live_ton_rate()
        ton_uzs = rate.get("ton_uzs", 15703.0)
        price_ton = float(target_item.get("price_ton", 5.0))
        price_uzs = int(target_item.get("price_uzs") or round(price_ton * ton_uzs))
        price_stars = int(target_item.get("stars", 100))
        
        user_balance_uzs = database.get_user_balance(user_id)
        if user_balance_uzs < price_uzs:
            return web.json_response({
                "ok": False,
                "error": f"Balansingiz yetarli emas! Ushbu NFT narxi: {price_uzs:,} so'm, sizda: {user_balance_uzs:,} so'm bor. Iltimos, avval bot orqali balansingizni to'ldiring.",
                "need_deposit": True,
                "current_balance": user_balance_uzs,
                "required_balance": price_uzs
            }, status=400)
            
        if not database.deduct_user_balance(user_id, price_uzs):
            return web.json_response({"ok": False, "error": "Mablag'ni hisobdan yechishda xatolik yuz berdi!"}, status=500)
            
        # NFT ni pending_gifts ga yozish
        rec_id = database.save_gift_record(
            tg_user_id=user_id,
            gift_id=slug,
            tier_key="marketplace",
            case_name="Fragment Marketplace Direct Buy",
            prize_name=f"{target_item['name']} {target_item.get('edition', '')}".strip(),
            prize_stars=price_stars,
            status="pending",
            cost_uzs=price_uzs,
            cost_stars=price_stars,
            payment_method="uzs"
        )
        
        # Bot tokeni orqali jo'natish navbatini chaqirish
        try:
            import asyncio
            from games_monetization import process_pending_gifts_batch
            from config import BOT_TOKEN
            asyncio.create_task(process_pending_gifts_batch(bot_token=BOT_TOKEN, limit=5))
            
            # Foydalanuvchiga to'liq Fragment havolasi bilan bot orqali bildirishnoma yuborish
            import urllib.request, json
            slug_url = f"https://fragment.com/gift/{slug}"
            notify_txt = (
                f"🎉 <b>TABRIKLAYMIZ! XARID MUVAFFAQIYATLI!</b>\n\n"
                f"🎁 <b>Sovg'a:</b> <b>{target_item['name']} {target_item.get('edition', '')}</b>\n"
                f"💰 <b>To'landi:</b> {price_uzs:,} so'm ({price_stars} Stars)\n"
                f"📦 <b>Buyurtma ID:</b> #{rec_id}\n"
                f"🔗 <b>Fragment rasmiy havolasi:</b>\n<a href=\"{slug_url}\">{slug_url}</a>\n\n"
                f"<i>Sovg'a profilingizga yuborilmoqda!</i>"
            )
            req_data = json.dumps({
                "chat_id": user_id,
                "text": notify_txt,
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🔗 Fragment.com da Ko'rish", "url": slug_url}]
                    ]
                }
            }).encode("utf-8")
            req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as _: pass
        except Exception as notify_err:
            print(f"Direct buy notify warning: {notify_err}")
            
        new_balance = database.get_user_balance(user_id)
        return web.json_response({
            "ok": True,
            "message": f"Tabriklaymiz! {target_item['name']} {target_item.get('edition', '')} so'm balansingizdan muvaffaqiyatli xarid qilindi!",
            "item": target_item,
            "new_balance": new_balance,
            "record_id": rec_id
        })
    except Exception as e:
        print(f"[api/stars/marketplace/buy] error: {e}")
        return web.json_response({"ok": False, "error": "Xarid jarayonida ichki xatolik yuz berdi"}, status=500)

async def handle_api_stars_upgrader(request):
    """Nazoratli Upgrader aylanishi (Anti-IDOR + Server-Side Authoritative Source Stars Enforcement)"""
    try:
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
        target_name = str(data.get("target_name", "Gift")).strip()[:80]
        target_icon = str(data.get("target_icon", "package")).strip()[:32]
        target_slug = str(data.get("target_slug") or "").strip()[:80]
        multiplier = data.get("multiplier")
        source_inventory_id = data.get("source_inventory_id")
        if source_inventory_id is not None:
            source_inventory_id = _safe_int(source_inventory_id, 0) or None
        target_inventory_id = data.get("target_inventory_id")
        if target_inventory_id is not None:
            target_inventory_id = _safe_int(target_inventory_id, 0) or None

        # SECURITY: Read authoritative source item_stars from DB rather than trusting client-supplied item_stars
        db_item_stars = None
        conn = database.get_db()
        if conn:
            try:
                cur = conn.cursor()
                if source_inventory_id:
                    cur.execute("""
                        SELECT id, prize_stars FROM pending_gifts
                        WHERE id = %s AND tg_user_id = %s
                          AND COALESCE(status, 'pending') NOT IN ('burned', 'upgraded_used', 'recycled', 'withdrawn', 'sent')
                        LIMIT 1
                    """, (source_inventory_id, user_id))
                    srow = cur.fetchone()
                else:
                    srow = None
                if not srow:
                    cur.execute("""
                        SELECT id, prize_stars FROM pending_gifts
                        WHERE tg_user_id = %s
                          AND COALESCE(status, 'pending') NOT IN ('burned', 'upgraded_used', 'recycled', 'withdrawn', 'sent')
                        ORDER BY id DESC LIMIT 1
                    """, (user_id,))
                    srow = cur.fetchone()
                if srow:
                    source_inventory_id = int(srow["id"] if isinstance(srow, dict) else srow[0])
                    db_item_stars = max(1, int(srow["prize_stars"] if isinstance(srow, dict) else (srow[1] or 15)))
            finally:
                conn.close()

        if db_item_stars is None:
            return web.json_response({
                "ok": False,
                "need_inventory": True,
                "error": "Inventaringizda upgrade qilish uchun yaroqli sovg'a topilmadi!"
            }, status=400)

        item_stars = db_item_stars
        raw_target_stars = max(1, _safe_int(data.get("target_stars", int(round(item_stars * 2))), int(round(item_stars * 2))))
        target_stars = max(int(round(item_stars * 1.5)), min(int(round(item_stars * 100.0)), raw_target_stars))

        from games_monetization import execute_upgrade_roll
        res = execute_upgrade_roll(
            user_id=user_id,
            item_stars=item_stars,
            target_stars=target_stars,
            target_name=target_name,
            target_icon=target_icon,
            target_inventory_id=target_inventory_id,
            source_inventory_id=source_inventory_id,
            target_slug=target_slug,
            multiplier=multiplier,
        )
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/upgrader] error: {e}")
        return web.json_response({"ok": False, "error": "Upgrader jarayonida ichki xatolik yuz berdi"}, status=500)

async def handle_api_stars_withdraw_gift(request):
    """Foydalanuvchining shaxsiy inventaridagi sovg'ani Telegram profiliga qabul qilish (yechib olish)"""
    try:
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        record_id = _safe_int(data.get("record_id", 0), 0)
        if record_id <= 0:
            return web.json_response({"ok": False, "error": "Sovg'a ID ko'rsatilmadi!"}, status=400)

        from database import get_db
        conn = get_db()
        if not conn:
            return web.json_response({"ok": False, "error": "Baza xatosi!"}, status=500)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, gift_id, prize_name, prize_stars, status
                FROM pending_gifts
                WHERE id = %s AND tg_user_id = %s
                  AND COALESCE(status, 'pending') NOT IN ('burned', 'upgraded_used', 'recycled', 'withdrawn', 'sent')
                FOR UPDATE
            """, (record_id, user_id))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return web.json_response({"ok": False, "error": "Sovg'a inventarda topilmadi yoki allaqachon yechib olingan!"}, status=404)

            gift_id = row["gift_id"] if isinstance(row, dict) else row[1]
            prize_name = row["prize_name"] if isinstance(row, dict) else row[2]

            cur.execute("""
                UPDATE pending_gifts
                SET status = 'sent', sent_at = NOW(), updated_at = NOW()
                WHERE id = %s AND tg_user_id = %s
            """, (record_id, user_id))
            conn.commit()

            import asyncio
            from games_monetization import send_telegram_gift
            from config import BOT_TOKEN
            async def _bg_send():
                try:
                    await send_telegram_gift(user_id=user_id, gift_id=gift_id, bot_token=BOT_TOKEN)
                except Exception as _e:
                    print(f"[Withdraw Send Error]: {_e}")
            asyncio.create_task(_bg_send())

            return web.json_response({
                "ok": True,
                "message": f"Tabriklaymiz! {prize_name} sovg'asi Telegram profilingizga muvaffaqiyatli yuborildi!",
                "record_id": record_id
            })
        finally:
            conn.close()
    except Exception as e:
        print(f"[api/stars/withdraw-gift] error: {e}")
        return web.json_response({"ok": False, "error": "Sovg'ani yechib olishda ichki xatolik yuz berdi"}, status=500)


async def handle_api_stars_recycle_gift(request):
    """Foydalanuvchining inventardagi sovg'ani 75% keshbek evaziga sotishi (Server-Side Authoritative Prize Stars)"""
    try:
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        record_id = _safe_int(data.get("record_id", 0), 0)
        if record_id <= 0:
            return web.json_response({"ok": False, "error": "Sovg'a ID ko'rsatilmadi!"}, status=400)

        # SECURITY: Read authoritative prize_stars and active status from DB (never trust client-supplied prize_stars!)
        from database import get_db
        conn = get_db()
        if not conn:
            return web.json_response({"ok": False, "error": "Baza bilan aloqa yo'q!"}, status=500)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT prize_stars, status
                FROM pending_gifts
                WHERE id = %s AND tg_user_id = %s
                  AND COALESCE(status, 'pending') NOT IN ('burned', 'upgraded_used', 'recycled', 'withdrawn', 'sent')
                LIMIT 1
            """, (record_id, user_id))
            row = cur.fetchone()
            if not row:
                return web.json_response({"ok": False, "error": "Sovg'a topilmadi yoki allaqachon ishlatilgan!"}, status=404)
            db_prize_stars = max(1, int(row["prize_stars"] if isinstance(row, dict) else (row[0] or 15)))
        finally:
            conn.close()

        from games_monetization import recycle_pending_gift
        res = recycle_pending_gift(record_id, user_id, db_prize_stars)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/recycle-gift] error: {e}")
        return web.json_response({"ok": False, "error": "Sovg'ani almashtirishda ichki xatolik yuz berdi"}, status=500)

async def handle_api_stars_daily_streak(request):
    """Foydalanuvchi kunlik streak holatini olish (Anti-IDOR, guest user_id=0 safe)"""
    try:
        raw_uid = _safe_int(request.query.get("user_id") or request.query.get("tg_user_id") or 0, 0)
        if raw_uid <= 0 and not get_authenticated_user_id(request):
            return web.json_response({"ok": True, "streak": 0, "can_claim": False, "days": []})
        user_id, auth_err = _require_user_auth(request, allow_admin=True)
        if auth_err:
            return auth_err
        from games_monetization import get_user_streak
        res = get_user_streak(user_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/daily-streak] error: {e}")
        return web.json_response({"ok": False, "error": "Streak holatini yuklashda ichki xatolik yuz berdi"}, status=500)

async def handle_api_stars_daily_claim(request):
    """Kunlik bepul xizmat sovg'asini olish (Anti-IDOR)"""
    try:
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
        from games_monetization import claim_daily_streak
        res = claim_daily_streak(user_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/daily-streak/claim] error: {e}")
        return web.json_response({"ok": False, "error": "Kunlik bonusni olishda ichki xatolik yuz berdi"}, status=500)

_SCRATCH_COOLDOWN = {}

async def handle_api_stars_scratch_card(request):
    """Tirnaladigan omad chiptasini o'ynash (1,000 UZS / 3 soniya cheklov, Atomic Balance Check) yoki holatini olish"""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if request.method == "GET":
            return web.json_response({
                "ok": True,
                "ticket_price": 1000,
                "cooldown": 3,
                "title": "Omadli Skretch Chipta",
                "description": "3 ta bir xil belgi tushsa — yutuq sizniki!"
            })

        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err

        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)

        # Rate-limiting: 3 soniyalik cooldown
        import time as _time
        now = _time.time()
        last_played = _SCRATCH_COOLDOWN.get(user_id, 0)
        if now - last_played < 3.0:
            return web.json_response({"ok": False, "error": "Iltimos, har bir urinish orasida 3 soniya kuting!"}, status=429)

        # Balans tekshirish va 1,000 so'mni atomik yechish (TOCTOU double-spend himoyasi)
        bal = database.get_user_balance(user_id)
        TICKET_PRICE = 1000
        if bal < TICKET_PRICE:
            return web.json_response({
                "ok": False,
                "error": f"Balansingiz yetarli emas! Chipta narxi: {TICKET_PRICE:,} so'm. Balansingiz: {bal:,} so'm."
            }, status=400)

        if not database.deduct_user_balance(user_id, TICKET_PRICE):
            return web.json_response({
                "ok": False,
                "error": "Balansdan mablag' yechib bo'lmadi (hisobingiz yetarli emas)!"
            }, status=400)
        _SCRATCH_COOLDOWN[user_id] = now

        from games_monetization import play_scratch_card
        res = play_scratch_card(user_id)
        res["new_balance"] = database.get_user_balance(user_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/scratch-card] error: {e}")
        return web.json_response({"ok": False, "error": "Skretch chipta jarayonida ichki xatolik yuz berdi"}, status=500)

handle_api_stars_scratch_play = handle_api_stars_scratch_card

async def handle_api_stars_redeem(request):
    """Yutuqlarni CapCut Pro yoki AI xizmatlariga almashtirish (Anti-IDOR)"""
    try:
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403)
        service_id = str(data.get("service_id", "")).strip()
        from games_monetization import redeem_creator_service
        res = redeem_creator_service(user_id, service_id)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/stars/redeem] error: {e}")
        return web.json_response({"ok": False, "error": "Xizmatni almashtirishda ichki xatolik yuz berdi"}, status=500)


# ==================== VENTEBOT RESELLER API HANDLERS ====================

async def handle_api_reseller_products(request):
    """VenteBot raqamli tovarlar katalogi (keshlangan, so'mdagi narxlar bilan)"""
    try:
        from ventebot_service import ventebot_service
        lang = request.query.get("lang", "uz")
        force = request.query.get("refresh", "0") in ("1", "true")

        # in_stock query parametrini tahlil qilish
        in_stock_raw = request.query.get("in_stock")
        in_stock_only = False
        if in_stock_raw is not None:
            val = in_stock_raw.strip().lower()
            if val in ("1", "true", "yes"):
                in_stock_only = True

        res = await ventebot_service.get_products(
            lang=lang,
            force_refresh=force,
            in_stock_only=in_stock_only
        )
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[api/reseller/products] error: {e}")
        return web.json_response({"success": False, "error": "Mahsulotlar katalogini yuklashda xatolik yuz berdi"}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_reseller_quote(request):
    """VenteBot tovar narxini hisoblab berish (so'm va USD da)"""
    try:
        from ventebot_service import ventebot_service
        data = await request.json()
        product_id = _safe_int(data.get("product_id", 0), 0)
        qty = _safe_int(data.get("quantity", 1), 1)
        if product_id <= 0 or qty < 1 or qty > 100:
            return web.json_response({"success": False, "error": "Noto'g'ri product_id yoki quantity (1..100)"}, status=400)
        res = await ventebot_service.get_quote(product_id=product_id, quantity=qty)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/reseller/quote] error: {e}")
        return web.json_response({"success": False, "error": "Narxni hisoblashda xatolik yuz berdi"}, status=500)


async def handle_api_reseller_buy(request):
    """Foydalanuvchi so'm balansidan xarid qilish va VenteBot ga buyurtma yuborish (Anti-IDOR)"""
    try:
        from ventebot_service import ventebot_service
        data = await request.json()
        user_id, auth_err = _require_user_auth(request, data)
        if auth_err:
            return auth_err
        product_id = _safe_int(data.get("product_id", 0), 0)
        qty = _safe_int(data.get("quantity", 1), 1)
        activation_identifier = str(data.get("activation_identifier", "")).strip()[:256]

        if user_id <= 0 or product_id <= 0:
            return web.json_response({"success": False, "message": "user_id va product_id kiritilishi shart"}, status=400)

        if qty <= 0 or qty > 100:
            return web.json_response({"success": False, "message": "Miqdor 1 dan 100 gacha bo'lishi kerak"}, status=400)

        res = await ventebot_service.buy_product_with_uzs(
            tg_user_id=user_id,
            product_id=product_id,
            quantity=qty,
            activation_identifier=activation_identifier,
        )
        return web.json_response(res)
    except Exception as e:
        print(f"[api/reseller/buy] error: {e}")
        return web.json_response({"success": False, "error": "Xarid jarayonida ichki xatolik yuz berdi"}, status=500)


async def handle_api_reseller_my_orders(request):
    """Foydalanuvchining avvalgi xaridlari ro'yxati (Anti-IDOR himoyalangan)"""
    try:
        from database import get_user_ventebot_orders
        auth_uid = get_authenticated_user_id(request)
        target_uid = _safe_int(request.query.get("user_id", 0), 0)
        if not auth_uid and not is_admin_request(request):
            return web.json_response({"success": False, "message": "Autentifikatsiya talab qilinadi!"}, status=401)
        if target_uid > 0 and auth_uid != target_uid and not is_admin_request(request):
            return web.json_response({"success": False, "message": "Boshqa foydalanuvchi buyurtmalarini ko'rish taqiqlangan!"}, status=403)
        user_id = auth_uid or target_uid
        if user_id <= 0:
            return web.json_response({"success": False, "orders": []})
        orders = get_user_ventebot_orders(user_id)
        for o in orders:
            if "created_at" in o and hasattr(o["created_at"], "isoformat"):
                o["created_at"] = o["created_at"].isoformat()
        return web.json_response({"success": True, "orders": orders})
    except Exception as e:
        print(f"[api/reseller/my-orders] error: {e}")
        return web.json_response({"success": False, "error": "Buyurtmalar ro'yxatini yuklashda xatolik yuz berdi"}, status=500)


async def handle_api_reseller_admin_wallet(request):
    """Admin uchun VenteBot hamyon balansi va ma'lumotlari"""
    try:
        from ventebot_service import ventebot_service
        if not is_admin_request(request):
            return web.json_response({"success": False, "message": "Ruxsat berilmadi (Admin ruxsati zarur)"}, status=403)

        force = request.query.get("refresh", "0") in ("1", "true")
        me = await ventebot_service.get_me(force_refresh=force)
        return web.json_response(me)
    except Exception as e:
        print(f"[api/reseller/admin/wallet] error: {e}")
        return web.json_response({"success": False, "error": "Hamyon ma'lumotlarini yuklashda xatolik yuz berdi"}, status=500)


# ==================== RATE LIMITING & SECURITY MIDDLEWARE ====================
_IP_RATE_LIMITS = {}      # { ip: [timestamp, ...] }
_SENSITIVE_IP_LIMITS = {} # { ip: [timestamp, ...] }

def _get_configured_bot_tokens() -> list[str]:
    """Return deduplicated primary and secondary Telegram bot tokens."""
    import config as _cfg
    raw = [
        BOT_TOKEN or "",
        getattr(_cfg, "BOT_TOKEN", "") or "",
        os.getenv("BOT_TOKEN", "") or "",
        getattr(_cfg, "SECONDARY_BOT_TOKEN", "") or "",
        os.getenv("SECONDARY_BOT_TOKEN", "") or "",
    ]
    for t in (getattr(_cfg, "SECONDARY_BOT_TOKENS", None) or []):
        raw.append(str(t))
    for part in os.getenv("SECONDARY_BOT_TOKENS", "").split(","):
        if part.strip():
            raw.append(part.strip())
    return list(dict.fromkeys(str(t).strip() for t in raw if str(t).strip()))


def _verify_webapp_init_data_hmac(raw_init_data: str) -> tuple[bool, dict | None, str]:
    """Validate Telegram WebApp initData against any configured bot token (primary or secondary)."""
    from urllib.parse import parse_qsl
    import hmac, hashlib, json
    tokens = _get_configured_bot_tokens()
    if not tokens:
        return False, None, "token_missing"
    parsed = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    if "hash" not in parsed:
        return False, None, "hash_missing"
    received_hash = str(parsed.pop("hash")).strip().lower()
    auth_date = _safe_int(parsed.get("auth_date", 0), 0)
    now = time.time()
    if auth_date <= 0 or auth_date > now + 60 or (now - auth_date > 86400):
        return False, None, "expired"
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    for btoken in tokens:
        secret_key = hmac.new(b"WebAppData", btoken.encode("utf-8"), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(calc_hash.lower(), received_hash):
            user_obj = None
            if "user" in parsed:
                try:
                    user_obj = json.loads(parsed["user"])
                except Exception:
                    return False, None, "bad_user"
            return True, user_obj, "ok"
    return False, None, "bad_signature"


def get_authenticated_user_id(request, data=None) -> int:
    """
    So'rov yuborgan haqiqiy foydalanuvchini aniqlash (Anti-IDOR).
    1. Authorization: Bearer <token>
    2. X-Auth-Token sarlavhasi
    3. Telegram WebApp initData HMAC-SHA256 imzosi (X-Telegram-Init-Data yoki body initData)
    4. Internal service yoki test secret (X-Internal-Secret / X-Test-Auth)
    Agar token topilmasa yoki yaroqsiz bo'lsa, 0 qaytaradi.
    """
    import time
    from config import OWNER_ID, get_admin_secret
    expected_secret = get_admin_secret()

    # Test yoki ichki chaqiruvlar uchun (constant-time taqqoslash)
    test_auth = request.headers.get("X-Test-Auth") or request.headers.get("X-Internal-Secret")
    if test_auth and expected_secret and _hmac.compare_digest(str(test_auth).strip(), expected_secret):
        if data and isinstance(data, dict):
            return _safe_int(data.get("user_id") or data.get("tg_user_id") or 0, 0)
        return _safe_int(request.query.get("user_id") or request.query.get("tg_user_id") or 0, 0)

    # 1. Bearer / Auth Token tekshiruvi (Headers yoki Cookie orqali)
    auth_header = request.headers.get("Authorization", "").strip()
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Auth-Token", "").strip()
    if not token:
        token = request.cookies.get("cf_auth_token", "").strip() or request.cookies.get("auth_token", "").strip()

    if token:
        if token in _AUTH_TOKENS:
            cached_info = _AUTH_TOKENS[token]
            if time.time() - cached_info.get("created_at", 0) < 7 * 86400:
                return int(cached_info.get("tg_user_id", 0))
            else:
                _AUTH_TOKENS.pop(token, None)
        # PostgreSQL dagi doimiy sessiyadan tekshirish
        try:
            from database import get_web_session
            sess = get_web_session(token)
            if sess and sess.get("tg_user_id"):
                uid = int(sess["tg_user_id"])
                _AUTH_TOKENS[token] = {"tg_user_id": uid, "created_at": time.time()}
                return uid
        except Exception:
            pass

    # 2. Telegram WebApp initData HMAC-SHA256 tekshiruvi
    raw_init_data = request.headers.get("X-Telegram-Init-Data", "").strip()
    if not raw_init_data and data and isinstance(data, dict):
        raw_init_data = str(data.get("initData", "")).strip()

    if raw_init_data:
        try:
            ok_wa, user_obj, _ = _verify_webapp_init_data_hmac(raw_init_data)
            if ok_wa and isinstance(user_obj, dict):
                return int(user_obj.get("id", 0))
        except Exception:
            pass

    return 0

def _add_security_headers(response, request=None):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if "Permissions-Policy" not in response.headers:
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if request is not None and _is_https_request(request):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if response.content_type == "text/html":
        # Supports Telegram WebApp iframes and Google AdSense previews seamlessly
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:; "
            "object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org https://*.google.com telegram:;"
        )
    return response

_SENSITIVE_NO_STORE_PREFIXES = (
    "/api/auth/",
    "/api/admin/",
    "/api/bot_user",
    "/api/stats",
    "/api/channels",
    "/api/autopost",
    "/api/user/",
    "/api/stars/user-",
    "/api/reseller/my-orders",
    "/api/reseller/admin/",
    "/kyc/status",
)

@web.middleware
async def security_and_rate_limit_middleware(request, handler):
    # 1. HTTP Method Guard (Block dangerous/unsupported methods)
    if request.method in ("TRACE", "TRACK", "CONNECT"):
        return _add_security_headers(web.Response(status=405, text="Method Not Allowed"), request)

    # 2. Extract Real Client IP (Anti-Spoofing: Cloudflare CF-Connecting-IP first, then trusted reverse proxy hop)
    client_ip = _get_client_ip(request)

    import time
    now = time.time()
    t_start = time.perf_counter()
    path = request.path.rstrip("/")

    from telemetry_service import get_dynamic_config, record_api_call

    # 3. Sensitive Endpoints Strict Rate Limit (OTP Request & Verification + WebApp Auth)
    if path in ("/api/auth/request-otp", "/api/auth/request_otp"):
        rate_key = f"otp_req:{client_ip}"
        ip_history = _SENSITIVE_IP_LIMITS.setdefault(rate_key, [])
        otp_win = float(get_dynamic_config("otp_rate_limit_window", 120))
        otp_max = int(get_dynamic_config("otp_rate_limit_max", 3))
        _SENSITIVE_IP_LIMITS[rate_key] = [t for t in ip_history if now - t < otp_win]
        if len(_SENSITIVE_IP_LIMITS[rate_key]) >= otp_max:
            return _add_security_headers(web.json_response({
                "ok": False,
                "error": f"Juda ko'p so'rov yuborildi! Iltimos {int(otp_win)} soniya kuting."
            }, status=429, headers={"Retry-After": str(int(otp_win))}), request)
        _SENSITIVE_IP_LIMITS[rate_key].append(now)
    elif path in ("/api/auth/verify-otp", "/api/auth/verify_otp", "/api/auth/verify-webapp", "/api/auth/verify_webapp"):
        rate_key = f"otp_ver:{client_ip}"
        ip_history = _SENSITIVE_IP_LIMITS.setdefault(rate_key, [])
        ver_win = 120.0
        ver_max = 10
        _SENSITIVE_IP_LIMITS[rate_key] = [t for t in ip_history if now - t < ver_win]
        if len(_SENSITIVE_IP_LIMITS[rate_key]) >= ver_max:
            return _add_security_headers(web.json_response({
                "ok": False,
                "error": "Juda ko'p kirish urinishi! Iltimos 2 daqiqadan so'ng qayta urinib ko'ring."
            }, status=429, headers={"Retry-After": "120"}), request)
        _SENSITIVE_IP_LIMITS[rate_key].append(now)

    if len(_SENSITIVE_IP_LIMITS) > 2000:
        cutoff = now - 300
        for k in [k for k, v in _SENSITIVE_IP_LIMITS.items() if not v or v[-1] < cutoff]:
            _SENSITIVE_IP_LIMITS.pop(k, None)

    # 4. Global Anti-DoS Rate Limiting (Faqat statik media va ommaviy kataloglar ozod qilingan)
    EXEMPT_PREFIXES = (
        "/assets",
        "/static",
        "/favicon.ico",
        "/favicon.svg",
        "/api/public-config",
        "/api/nft",
        "/api/telegram-file",
        "/api/admin/telemetry/stream",
        "/api/stars/cases",
        "/api/stars/marketplace-nfts",
        "/api/stars/upgrader/inventory",
        "/api/stars/recent-drops",
        "/api/stars/pvp-battles"
    )
    if not any(path.startswith(pfx) for pfx in EXEMPT_PREFIXES):
        ip_hits = _IP_RATE_LIMITS.setdefault(client_ip, [])
        _IP_RATE_LIMITS[client_ip] = [t for t in ip_hits if now - t < 60]
        burst_win = float(get_dynamic_config("dos_burst_window", 2))
        burst_max = int(get_dynamic_config("dos_burst_max", 150))
        min_max = int(get_dynamic_config("dos_minute_max", 600))
        recent_burst = [t for t in _IP_RATE_LIMITS[client_ip] if now - t < burst_win]
        if len(recent_burst) > burst_max or len(_IP_RATE_LIMITS[client_ip]) > min_max:
            return _add_security_headers(web.json_response({
                "ok": False,
                "error": "Too Many Requests (DoS protection active). Iltimos bir oz kuting."
            }, status=429, headers={"Retry-After": "5"}), request)
        _IP_RATE_LIMITS[client_ip].append(now)

    # Clean memory if tracked IPs grow large
    if len(_IP_RATE_LIMITS) > 2000:
        cutoff = now - 60
        keys_to_del = [k for k, v in _IP_RATE_LIMITS.items() if not v or v[-1] < cutoff]
        for k in keys_to_del:
            _IP_RATE_LIMITS.pop(k, None)

    # 5. Handler Execution & Global Exception Shield
    status_code = 200
    try:
        response = await handler(request)
        status_code = getattr(response, "status", 200)
    except web.HTTPException as http_ex:
        status_code = http_ex.status
        raise
    except Exception as e:
        print(f"[Unhandled API Error] {path}: {e}")
        status_code = 500
        return _add_security_headers(web.json_response({"ok": False, "error": "Server ichki xatoligi yuz berdi"}, status=500), request)
    finally:
        latency_ms = (time.perf_counter() - t_start) * 1000.0
        record_api_call(request.method, path or "/", status_code, latency_ms, client_ip)

    if any(path.startswith(pfx) for pfx in _SENSITIVE_NO_STORE_PREFIXES) and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-store, private"

    if (
        "gzip" in request.headers.get("Accept-Encoding", "").lower()
        and isinstance(response, web.Response)
        and not isinstance(response, web.FileResponse)
        and not getattr(response, "prepared", False)
        and "Content-Encoding" not in response.headers
        and path not in ("/api/admin/telemetry/stream", "/api/download-file", "/api/download_file")
        and (getattr(response, "content_type", "") or "").startswith(
            ("text/", "application/json", "application/javascript", "image/svg+xml")
        )
    ):
        response.enable_compression()

    # 6. Attach OWASP Security Headers
    return _add_security_headers(response, request)


# ==================== ADMIN-ONLY OBSERVABILITY & TELEMETRY HANDLERS ====================

_ADMIN_VERIFY_FAILURES = {}  # { ip: [timestamp, ...] }

def is_admin_request(request) -> bool:
    """
    Haqiqiy Admin Huquqini Tekshirish (Zero Telegram ID Backdoor).
    Faqatgina to'g'ri HMAC-SHA256 imzoli sessiya tokeni (cf_adm_sig) yoki
    haqiqiy ADMIN_SECRET maxfiy paroli (yoki uning SHA-256 xeshi) taqdim etilgandagina True qaytaradi.
    HECH QACHON Telegram account ID (6735799833) ga asoslanib adminlik berilmaydi!
    """
    from crypto_auth import verify_signed_admin_token
    from urllib.parse import unquote
    import hmac
    import hashlib

    # 1. Kriptografik HMAC-SHA256 imzoli tokenni tekshirish (Cookie yoki Header — URL query string taqiqlangan)
    auth_hdr = request.headers.get("Authorization", "").strip()
    bearer_tok = auth_hdr[7:].strip() if auth_hdr.startswith("Bearer ") else ""
    token_candidates = [
        request.cookies.get("cf_adm_sig"),
        request.headers.get("X-Admin-Signature"),
        bearer_tok
    ]
    for cand in token_candidates:
        if cand:
            clean_cand = unquote(str(cand).strip())
            if "." in clean_cand:
                verified_payload = verify_signed_admin_token(clean_cand)
                if verified_payload:
                    return True

    # 2. To'g'ridan-to'g'ri maxfiy admin paroli yoki uning SHA-256 xeshini tekshirish
    from config import get_admin_secret
    expected_secret = get_admin_secret()
    if not expected_secret:
        return False

    expected_hash = hashlib.sha256(expected_secret.encode("utf-8")).hexdigest()

    # Sarlavhalar orqali tekshirish
    h_sec = request.headers.get("X-Admin-Secret") or request.headers.get("X-Admin-Key")
    if h_sec:
        clean_h = unquote(str(h_sec).strip())
        # Hech qachon oddiy raqamli ID qabul qilinmaydi
        if clean_h.isdigit() and len(clean_h) < 12:
            return False
        if hmac.compare_digest(clean_h, expected_secret) or hmac.compare_digest(clean_h.lower(), expected_hash):
            return True

    return False


async def handle_admin_telemetry_ui(request):
    """Admin-only n8n-style Observability & Telemetry UI"""
    if not is_admin_request(request):
        from telemetry_service import render_admin_login_portal
        html = render_admin_login_portal()
        return web.Response(text=html, content_type="text/html")

    from crypto_auth import generate_signed_admin_token
    signed_token = generate_signed_admin_token(tg_user_id=6735799833, ttl_seconds=12 * 3600)
    from telemetry_service import render_telemetry_html
    html = render_telemetry_html(admin_key=signed_token)
    resp = web.Response(text=html, content_type="text/html")
    resp.set_cookie("cf_adm_sig", signed_token, max_age=12 * 3600, path="/", samesite="Lax", httponly=True, secure=_is_https_request(request))
    # Eski zaif cookie larni bekor qilish
    resp.del_cookie("cf_auth_owner", path="/")
    resp.del_cookie("admin_key", path="/")
    return resp


async def handle_api_admin_verify(request):
    """
    Admin kalitini tekshirish va brauzerga xavfsiz HMAC-SHA256 imzoli sessiya cookie sini o'rnatish.
    Brute-force va DoS dan himoyalangan (IP bo'yicha cheklov).
    Raw yoki SHA-256 xesh qabul qiladi. Telegram ID lar mutlaqo qabul qilinmaydi!
    """
    import time
    import hmac
    import hashlib
    from urllib.parse import unquote

    peer_ip = _get_client_ip(request)
    now = time.time()

    # Evict stale entries if failure tracker grows large
    if len(_ADMIN_VERIFY_FAILURES) > 2000:
        cutoff = now - 600
        for k in [k for k, v in _ADMIN_VERIFY_FAILURES.items() if not v or v[-1] < cutoff]:
            _ADMIN_VERIFY_FAILURES.pop(k, None)

    # Rate limiting: 10 daqiqada 5 ta muvaffaqiyatsiz urinishdan keyin bloklash
    recent_fails = [t for t in _ADMIN_VERIFY_FAILURES.get(peer_ip, []) if now - t < 600]
    _ADMIN_VERIFY_FAILURES[peer_ip] = recent_fails
    if len(recent_fails) >= 5:
        return web.json_response({
            "ok": False,
            "error": "Ko'p xato urinishlar qilindi! Xavfsizlik yuzasidan 10 daqiqaga bloklandingiz."
        }, status=429)

    try:
        data = await request.json()
        key = str(data.get("key", "")).strip()
        key_hash = str(data.get("key_hash", "")).strip().lower()
        
        from config import OWNER_ID, get_admin_secret
        clean_key = unquote(key)
        expected_secret = get_admin_secret()
        if not expected_secret:
            return web.json_response({"ok": False, "error": "Serverda ADMIN_SECRET sozlanmagan!"}, status=500)

        expected_hash = hashlib.sha256(expected_secret.encode("utf-8")).hexdigest()

        # XAVFSIZLIK: Telegram ID larni admin paroli sifatida mutlaqo bloklash!
        forbidden_candidates = {str(OWNER_ID), "6735799833"}
        forbidden_hashes = {hashlib.sha256(fc.encode("utf-8")).hexdigest() for fc in forbidden_candidates if fc}
        if clean_key in forbidden_candidates or key in forbidden_candidates or key_hash in forbidden_hashes:
            recent_fails.append(now)
            _ADMIN_VERIFY_FAILURES[peer_ip] = recent_fails
            return web.json_response({
                "ok": False,
                "error": "Telegram ID admin paroli bo'la olmaydi! Maxfiy admin parolini kiriting."
            }, status=403)

        is_valid = False

        # 1. Agar oldingi signed token taqdim etilgan bo'lsa
        if clean_key and "." in clean_key:
            from crypto_auth import verify_signed_admin_token
            if verify_signed_admin_token(clean_key):
                is_valid = True

        # 2. Xesh bo'yicha tekshirish (Client-side SHA-256)
        if not is_valid and key_hash:
            if hmac.compare_digest(key_hash, expected_hash):
                is_valid = True

        # 3. Plaintext kalit taqdim etilgan bo'lsa (constant-time taqqoslash)
        if not is_valid and clean_key:
            if hmac.compare_digest(clean_key.lower(), expected_hash):
                is_valid = True
            elif hmac.compare_digest(clean_key, expected_secret):
                is_valid = True

        if not is_valid:
            recent_fails.append(now)
            _ADMIN_VERIFY_FAILURES[peer_ip] = recent_fails
            return web.json_response({
                "ok": False,
                "error": "Noto'g'ri maxfiy parol! Ruxsat berilmadi."
            }, status=403)

        # Muvaffaqiyatli kirish - xatoliklar sonini tozalash
        _ADMIN_VERIFY_FAILURES.pop(peer_ip, None)

        from crypto_auth import generate_signed_admin_token
        # Xavfsiz 12 soatlik HMAC-SHA256 sessiya tokeni
        signed_token = generate_signed_admin_token(tg_user_id=6735799833, ttl_seconds=12 * 3600)

        resp = web.json_response({
            "ok": True,
            "message": "Admin ruxsati muvaffaqiyatli tasdiqlandi",
            "token": signed_token
        })

        # Xavfsiz SameSite=Lax HttpOnly (+ Secure on HTTPS) cookie lar o'rnatish
        resp.set_cookie("cf_adm_sig", signed_token, max_age=12 * 3600, path="/", samesite="Lax", httponly=True, secure=_is_https_request(request))
        resp.del_cookie("cf_auth_owner", path="/")
        resp.del_cookie("admin_key", path="/")

        return resp
    except Exception as e:
        print(f"[api/admin/verify] error: {e}")
        return web.json_response({"ok": False, "error": "Admin tekshiruvida ichki xatolik yuz berdi"}, status=500)


async def handle_api_admin_logout(request):
    """Admin sessiyasini xavfsiz tugatish (Cookie larni o'chirish)"""
    resp = web.json_response({"ok": True, "message": "Admin sessiyasi tugatildi"})
    resp.del_cookie("cf_adm_sig", path="/")
    resp.del_cookie("cf_auth_owner", path="/")
    resp.del_cookie("admin_key", path="/")
    return resp


async def handle_api_telemetry_stream(request):
    """Admin-only real-time telemetriya oqimi JSON"""
    if not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat berilmadi (Admin kaliti talab qilinadi)"}, status=403)

    from telemetry_service import get_telemetry_snapshot
    snapshot = get_telemetry_snapshot(request.app)
    return web.json_response(snapshot)


async def handle_api_telemetry_config(request):
    """Admin-only dynamic config setter (TTL va DoS parametrlarini yangilash)"""
    if not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat berilmadi"}, status=403)

    try:
        body = await request.json()
        from telemetry_service import update_dynamic_config
        updated = update_dynamic_config(body)
        return web.json_response({"ok": True, "config": updated})
    except Exception as e:
        print(f"[api/admin/telemetry/config] error: {e}")
        return web.json_response({"ok": False, "error": "Sozlamalarni yangilashda xatolik yuz berdi"}, status=400)


async def handle_api_telemetry_purge(request):
    """Admin-only cache purge trigger"""
    if not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat berilmadi"}, status=403)

    try:
        body = await request.json()
        category = body.get("category", "all")
        from telemetry_service import purge_cache
        res = purge_cache(category)
        return web.json_response(res)
    except Exception as e:
        print(f"[api/admin/telemetry/purge] error: {e}")
        return web.json_response({"ok": False, "error": "Keshni tozalashda xatolik yuz berdi"}, status=400)


# ==================== WEB DASHBOARD OTP & WEBAPP AUTH ====================
_LOGIN_OTPS = {}  # { tg_user_id: { "otp": "123456", "expires_at": float, "cooldown_until": float, "attempts": int } }
_AUTH_TOKENS = {} # { token: { "tg_user_id": int, "created_at": float } }

async def handle_api_auth_request_otp(request):
    """Foydalanuvchi Telegram ID kiritganda CSPRNG 6-raqamli OTP generatsiya qilib Telegramga yuborish"""
    try:
        import time, secrets, json, aiohttp
        data = await request.json()
        raw_uid = data.get("tg_user_id")
        if not raw_uid:
            return web.json_response({"ok": False, "error": "Telegram User ID kiritilishi shart!"}, status=400)

        try:
            tg_user_id = int(raw_uid)
            if tg_user_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return web.json_response({"ok": False, "error": "Telegram User ID musbat son bo'lishi kerak!"}, status=400)

        now = time.time()
        if len(_LOGIN_OTPS) > 5000:
            for k in [k for k, v in _LOGIN_OTPS.items() if now > v.get("expires_at", 0)]:
                _LOGIN_OTPS.pop(k, None)

        prev = _LOGIN_OTPS.get(tg_user_id)
        if prev and now < prev.get("cooldown_until", 0):
            wait_sec = int(prev.get("cooldown_until", 0) - now)
            return web.json_response({"ok": False, "error": f"Iltimos {wait_sec} soniyadan keyin qayta urinib ko'ring!"}, status=429)

        # CSPRNG 6-digit OTP
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        _LOGIN_OTPS[tg_user_id] = {
            "otp": otp_code,
            "expires_at": now + 300, # 5 daqiqa
            "cooldown_until": now + 30, # 30 soniya cooldown
            "attempts": 0
        }

        from config import BOT_TOKEN
        token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
        if not token:
            return web.json_response({"ok": False, "error": "BOT_TOKEN sozlanmagan!"}, status=500)

        web_base_url = APP_BASE_URL.rstrip("/")
        one_click_url = f"{web_base_url}/?tg_user_id={tg_user_id}&otp={otp_code}"
        bot_username = get_bot_username()

        # Telegram Custom Emojilar (Rasmiy tekshirilgan tg-emoji ID lari)
        lock_ce = '<tg-emoji emoji-id="5330194932781050507">🛡️</tg-emoji>'
        key_ce = '<tg-emoji emoji-id="4994749624662098557">🔑</tg-emoji>'
        time_ce = '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>'
        shield_ce = '<tg-emoji emoji-id="5330194932781050507">🛡️</tg-emoji>'

        msg_text = (
            f"{lock_ce} <b>{BRAND_NAME} Web Dashboard</b>\n\n"
            f"Sizning bir martalik kirish kodingiz:\n"
            f"{key_ce} <code>{otp_code}</code> {key_ce}\n\n"
            f"{time_ce} Ushbu kod <b>5 daqiqa</b> davomida amal qiladi.\n"
            f"{shield_ce} Xavfsizlik maqsadida uni begonalarga bermang!\n\n"
            f"Yoki pastdagi tugma orqali to'g'ridan-to'g'ri tizimga kiring:"
        )

        send_payload = {
            "chat_id": tg_user_id,
            "text": msg_text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "🚀 1-Click Kirish (Dashboard)", "url": one_click_url}]
                ]
            }
        }

        tg_api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with aiohttp.ClientSession() as session:
            async with session.post(tg_api_url, json=send_payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                resp_data = await resp.json()
                if resp_data.get("ok"):
                    sent_msg_id = resp_data.get("result", {}).get("message_id")
                    if tg_user_id in _LOGIN_OTPS:
                        _LOGIN_OTPS[tg_user_id]["message_id"] = sent_msg_id
                    try:
                        from database import set_bot_config
                        set_bot_config(f"otp_{tg_user_id}", json.dumps({
                            "otp": otp_code,
                            "expires_at": now + 300,
                            "cooldown_until": now + 30,
                            "attempts": 0,
                            "message_id": sent_msg_id
                        }))
                    except Exception:
                        pass
                    return web.json_response({
                        "ok": True,
                        "message": "Tasdiqlash kodi Telegram botingizga yuborildi!",
                        "tg_user_id": tg_user_id
                    })
                else:
                    err_desc = resp_data.get("description", "")
                    if "blocked" in err_desc.lower() or "chat not found" in err_desc.lower():
                        user_msg = f"Telegram botimizga (@{bot_username}) avval /start yuboring, so'ngra kodni so'rang!"
                    else:
                        user_msg = "Telegramga tasdiqlash kodini yuborib bo'lmadi. Qayta urinib ko'ring."
                    return web.json_response({"ok": False, "error": user_msg}, status=400)
    except Exception as e:
        print(f"handle_api_auth_request_otp error: {type(e).__name__}")
        return web.json_response({"ok": False, "error": "Tasdiqlash kodini yuborishda ichki xatolik yuz berdi"}, status=500)


async def handle_api_auth_verify_otp(request):
    """6-raqamli OTP kodni tekshirish va sessiya tokenini berish (Constant-time + Persistent Brute-Force Lockout)"""
    try:
        import time, secrets, json, aiohttp
        data = await request.json()
        raw_uid = data.get("tg_user_id")
        raw_otp = str(data.get("otp", "")).strip()

        if not raw_uid or not raw_otp:
            return web.json_response({"ok": False, "error": "Telegram ID va tasdiqlash kodi talab qilinadi!"}, status=400)

        tg_user_id = _safe_int(raw_uid, 0)
        if tg_user_id <= 0:
            return web.json_response({"ok": False, "error": "Noto'g'ri Telegram ID!"}, status=400)

        session = _LOGIN_OTPS.get(tg_user_id)
        if not session:
            try:
                from database import get_bot_config
                raw_cfg = get_bot_config(f"otp_{tg_user_id}")
                if raw_cfg:
                    session = json.loads(raw_cfg)
                    _LOGIN_OTPS[tg_user_id] = session
            except Exception:
                session = None

        if not session:
            return web.json_response({"ok": False, "error": "Tasdiqlash kodi so'ralmagan yoki muddati o'tgan! Qaytadan kod so'rang."}, status=400)

        now = time.time()
        if now > session.get("expires_at", 0):
            _LOGIN_OTPS.pop(tg_user_id, None)
            try:
                from database import set_bot_config
                set_bot_config(f"otp_{tg_user_id}", "")
            except Exception:
                pass
            return web.json_response({"ok": False, "error": "Kod muddati (5 daqiqa) tugagan. Qaytadan yangi kod so'rang!"}, status=400)

        session["attempts"] = int(session.get("attempts", 0)) + 1
        _LOGIN_OTPS[tg_user_id] = session

        if not _hmac.compare_digest(str(session.get("otp", "")), raw_otp):
            if session["attempts"] >= 5:
                _LOGIN_OTPS.pop(tg_user_id, None)
                try:
                    from database import set_bot_config
                    set_bot_config(f"otp_{tg_user_id}", "")
                except Exception:
                    pass
                return web.json_response({"ok": False, "error": "Ko'p xato urinishlar! Qaytadan yangi kod so'rang."}, status=403)
            # Persist incremented attempt counter back to DB so restarts cannot reset brute-force count
            try:
                from database import set_bot_config
                set_bot_config(f"otp_{tg_user_id}", json.dumps(session))
            except Exception:
                pass
            return web.json_response({"ok": False, "error": "Tasdiqlash kodi noto'g'ri! Tekshirib qaytadan kiriting."}, status=400)

        saved_msg_id = session.get("message_id")
        _LOGIN_OTPS.pop(tg_user_id, None)
        try:
            from database import set_bot_config
            set_bot_config(f"otp_{tg_user_id}", "")
        except Exception:
            pass

        # Telegram bot yuborgan OTP xabarini avtomatik darhol o'chirish (deleteMessage)
        if saved_msg_id:
            try:
                from config import BOT_TOKEN
                token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
                if token:
                    delete_url = f"https://api.telegram.org/bot{token}/deleteMessage"
                    async with aiohttp.ClientSession() as s:
                        async with s.post(delete_url, json={
                            "chat_id": tg_user_id,
                            "message_id": saved_msg_id
                        }, timeout=aiohttp.ClientTimeout(total=5)) as del_res:
                            del_json = await del_res.json()
                            print(f"[OTP AutoDelete] Message {saved_msg_id} deleted via Bot API: {del_json}")
            except Exception as e_del:
                print(f"[OTP AutoDelete] Bot API xatosi: {e_del}")

            if ytbot_instance:
                try:
                    await ytbot_instance.delete_messages(chat_id=tg_user_id, message_ids=[saved_msg_id])
                    print(f"[OTP AutoDelete] Pyrogram delete_messages {saved_msg_id} muvaffaqiyatli")
                except Exception:
                    pass

        auth_token = secrets.token_hex(32)
        if len(_AUTH_TOKENS) > 10000:
            cutoff = now - 7 * 86400
            for k in [k for k, v in _AUTH_TOKENS.items() if v.get("created_at", 0) < cutoff]:
                _AUTH_TOKENS.pop(k, None)
        _AUTH_TOKENS[auth_token] = {
            "tg_user_id": tg_user_id,
            "created_at": now
        }

        # PostgreSQL da 7 kunlik doimiy sessiya saqlash (Server restartida logout bo'lmaydi)
        try:
            from database import save_web_session
            fingerprint = str(data.get("fingerprint", "")).strip()
            save_web_session(auth_token, tg_user_id, fingerprint)
        except Exception as e_sess:
            print(f"[WebSession] Saqlashda xato: {e_sess}")

        from database import is_bot_admin, is_user_vip
        from config import OWNER_ID
        is_owner = bool(OWNER_ID and tg_user_id == OWNER_ID) or (tg_user_id == 6735799833)
        is_vip = is_owner or bool(is_bot_admin(tg_user_id)) or bool(is_user_vip(tg_user_id))

        resp_data = {
            "ok": True,
            "token": auth_token,
            "tg_user_id": tg_user_id,
            "photo_url": _build_signed_avatar_url(tg_user_id),
            "is_vip": is_vip,
            "is_owner": is_owner
        }
        resp = web.json_response(resp_data)
        resp.set_cookie("cf_auth_token", auth_token, max_age=7 * 86400, path="/", samesite="Lax", httponly=True, secure=_is_https_request(request))
        return resp
    except Exception as e:
        print(f"handle_api_auth_verify_otp error: {e}")
        return web.json_response({"ok": False, "error": "Kodni tekshirishda ichki xatolik yuz berdi"}, status=500)


async def handle_api_auth_verify_webapp(request):
    """Telegram WebApp SDK initData HMAC-SHA256 tekshiruvi (asosiy va ikkilamchi botlarni qo'llab-quvvatlaydi)"""
    try:
        import time, secrets
        data = await request.json()
        init_data_raw = str(data.get("initData", "")).strip()
        if not init_data_raw:
            return web.json_response({"ok": False, "error": "initData talab qilinadi!"}, status=400)

        from config import OWNER_ID
        ok_wa, user_obj, err_code = _verify_webapp_init_data_hmac(init_data_raw)
        if not ok_wa:
            if err_code == "token_missing":
                return web.json_response({"ok": False, "error": "BOT_TOKEN sozlanmagan!"}, status=500)
            if err_code == "hash_missing":
                return web.json_response({"ok": False, "error": "initData hash topilmadi!"}, status=400)
            if err_code == "expired":
                return web.json_response({"ok": False, "error": "Telegram WebApp sessiya muddati o'tgan! Iltimos, qaytadan oching."}, status=401)
            if err_code == "bad_user":
                return web.json_response({"ok": False, "error": "User ma'lumotlari noto'g'ri formatda!"}, status=400)
            return web.json_response({"ok": False, "error": "Telegram WebApp imzosi haqiqiy emas!"}, status=403)

        now = time.time()
        tg_user_id = _safe_int(user_obj.get("id") if isinstance(user_obj, dict) else 0, 0)
        if tg_user_id <= 0:
            return web.json_response({"ok": False, "error": "User ma'lumotlari topilmadi!"}, status=400)

        auth_token = secrets.token_hex(32)
        _AUTH_TOKENS[auth_token] = {
            "tg_user_id": tg_user_id,
            "created_at": now
        }

        # PostgreSQL da 7 kunlik doimiy sessiya saqlash
        try:
            from database import save_web_session
            fingerprint = str(data.get("fingerprint", "")).strip()
            save_web_session(auth_token, tg_user_id, fingerprint)
        except Exception as e_sess:
            print(f"[WebSession WebApp] Saqlashda xato: {e_sess}")

        from database import is_bot_admin, is_user_vip
        is_owner = bool(OWNER_ID and tg_user_id == OWNER_ID) or (tg_user_id == 6735799833)
        is_vip = is_owner or bool(is_bot_admin(tg_user_id)) or bool(is_user_vip(tg_user_id))

        signed_avatar_url = _build_signed_avatar_url(tg_user_id)
        resp_dict = {
            "ok": True,
            "token": auth_token,
            "tg_user_id": tg_user_id,
            "user": user_obj,
            "photo_url": signed_avatar_url,
            "is_vip": is_vip,
            "is_owner": is_owner
        }
        resp = web.json_response(resp_dict)
        resp.set_cookie("cf_auth_token", auth_token, max_age=7 * 86400, path="/", samesite="Lax", httponly=True, secure=_is_https_request(request))
        return resp
    except Exception as e:
        print(f"handle_api_auth_verify_webapp error: {e}")
        return web.json_response({"ok": False, "error": "WebApp autentifikatsiyasida ichki xatolik yuz berdi"}, status=500)


async def handle_api_auth_verify_token(request):
    """Mavjud sessiya tokenini qat'iy tekshirish (Zero unauthenticated tg_user_id / fingerprint session takeover)"""
    try:
        import time
        try:
            data = await request.json()
        except Exception:
            data = {}

        auth_header = request.headers.get("Authorization", "").strip()
        bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        token = str(
            (data.get("token") if isinstance(data, dict) else "")
            or bearer_token
            or request.headers.get("X-Auth-Token", "")
            or request.cookies.get("cf_auth_token", "")
            or request.cookies.get("auth_token", "")
        ).strip()

        raw_uid = (
            (data.get("tg_user_id") or data.get("user_id") if isinstance(data, dict) else None)
            or request.query.get("tg_user_id")
            or request.query.get("user_id")
        )
        fingerprint = str((data.get("fingerprint") if isinstance(data, dict) else "") or "").strip()

        requested_uid = _safe_int(raw_uid, 0) if raw_uid not in (None, "") else 0

        if not token or len(token) < 16:
            return web.json_response({"ok": False, "error": "Sessiya tokeni talab qilinadi"}, status=401)

        now = time.time()
        session = None
        tg_user_id = 0

        # 1. Check in-memory cache with strict 7-day TTL
        if token in _AUTH_TOKENS:
            cached_s = _AUTH_TOKENS[token]
            if now - cached_s.get("created_at", 0) < 7 * 86400:
                sess_uid = _safe_int(cached_s.get("tg_user_id"), 0)
                if sess_uid > 0:
                    if requested_uid > 0 and sess_uid != requested_uid:
                        return web.json_response({"ok": False, "error": "Token boshqa foydalanuvchiga tegishli!"}, status=403)
                    session = cached_s
                    tg_user_id = sess_uid
            else:
                _AUTH_TOKENS.pop(token, None)

        # 2. Check PostgreSQL web_sessions strictly by token
        if not session:
            from database import get_web_session
            db_session = get_web_session(token, fingerprint)
            if db_session:
                sess_uid = _safe_int(db_session.get("tg_user_id"), 0)
                if sess_uid > 0:
                    if requested_uid > 0 and sess_uid != requested_uid:
                        return web.json_response({"ok": False, "error": "Token boshqa foydalanuvchiga tegishli!"}, status=403)
                    tg_user_id = sess_uid
                    session = {
                        "tg_user_id": tg_user_id,
                        "created_at": now
                    }
                    _AUTH_TOKENS[token] = session

        if not session or tg_user_id <= 0:
            return web.json_response({"ok": False, "error": "Sessiya yaroqsiz yoki muddati o'tgan"}, status=401)

        import database
        if database.is_user_banned(tg_user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!", "is_banned": True}, status=403)

        from database import is_bot_admin, is_user_vip, get_user_balance, is_user_kyc_verified
        from config import OWNER_ID
        is_owner = bool(OWNER_ID and tg_user_id == OWNER_ID) or (tg_user_id == 6735799833)
        is_admin_flag = is_owner or bool(is_bot_admin(tg_user_id))
        is_vip = is_admin_flag or bool(is_user_vip(tg_user_id))
        balance = get_user_balance(tg_user_id)
        is_kyc = is_user_kyc_verified(tg_user_id)

        signed_avatar_url = _build_signed_avatar_url(tg_user_id)
        user_data = {
            "id": tg_user_id,
            "tg_user_id": tg_user_id,
            "photo_url": signed_avatar_url,
            "is_vip": is_vip,
            "is_admin": is_admin_flag,
            "is_owner": is_owner,
            "balance_uzs": balance,
            "is_kyc": is_kyc
        }

        resp_payload = {
            "ok": True,
            "token": token,
            "tg_user_id": tg_user_id,
            "photo_url": signed_avatar_url,
            "is_vip": is_vip,
            "is_owner": is_owner,
            "user": user_data
        }
        resp = web.json_response(resp_payload)
        resp.set_cookie("cf_auth_token", token, max_age=7 * 86400, path="/", samesite="Lax", httponly=True, secure=_is_https_request(request))
        return resp
    except Exception as e:
        print(f"handle_api_auth_verify_token error: {e}")
        return web.json_response({"ok": False, "error": "Sessiyani tekshirishda xatolik yuz berdi"}, status=401)


async def handle_api_auth_logout(request):
    """Web sessiyani bazadan ham, xotiradan ham o'chirish va HttpOnly cookie ni tozalash"""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}
        auth_header = request.headers.get("Authorization", "").strip()
        bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        tokens_to_revoke = {
            str(data.get("token", "") if isinstance(data, dict) else "").strip(),
            bearer_token,
            request.headers.get("X-Auth-Token", "").strip(),
            request.cookies.get("cf_auth_token", "").strip(),
            request.cookies.get("auth_token", "").strip(),
        }
        for tok in tokens_to_revoke:
            if tok:
                _AUTH_TOKENS.pop(tok, None)
                try:
                    from database import delete_web_session
                    delete_web_session(tok)
                except Exception:
                    pass
    except Exception:
        pass
    resp = web.json_response({"ok": True})
    resp.del_cookie("cf_auth_token", path="/")
    resp.del_cookie("auth_token", path="/")
    return resp


async def start_web_server(port):
    """aiohttp web serverni ishga tushirish (Rate Limiting, Max Payload & Security Headers bilan)"""
    app = web.Application(client_max_size=2097152, middlewares=[security_and_rate_limit_middleware])
    app.router.add_get("/", handle_health)
    app.router.add_get("/api/public-config", handle_api_public_config)
    # Public Multilingual Legal & Compliance Pages (Google OAuth Branding Verification)
    app.router.add_get("/privacy", handle_privacy_page)
    app.router.add_get("/privacy-policy", handle_privacy_page)
    app.router.add_get("/privacy.html", handle_privacy_page)
    app.router.add_get("/terms", handle_terms_page)
    app.router.add_get("/terms-of-service", handle_terms_page)
    app.router.add_get("/terms.html", handle_terms_page)
    app.router.add_get("/robots.txt", handle_robots)
    app.router.add_get("/ads.txt", handle_ads_txt)
    # Google Search Console Domain Verification File Handler
    app.router.add_get(r"/{filename:google[a-zA-Z0-9_\-]+\.html}", handle_google_verification)
    # Client-side SPA routes (dedicated URLs + legacy aliases)
    for _spa_path in (
        "/login",
        "/signin",
        "/studio",
        "/analytics",
        "/downloader",
        "/videos",
        "/cases",
        "/nfts",
        "/goal",
        "/boost",
        "/teamwork-preview",
        "/teamwork_preview",
        "/teamwork",
    ):
        app.router.add_get(_spa_path, handle_health)
    _dist_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "dist", "assets")
    if os.path.isdir(_dist_assets):
        app.router.add_static("/assets", _dist_assets, append_version=False)
    # Secure Web Dashboard Authentication (OTP + WebApp HMAC)
    app.router.add_post("/api/auth/request-otp", handle_api_auth_request_otp)
    app.router.add_post("/api/auth/request_otp", handle_api_auth_request_otp)
    app.router.add_post("/api/auth/verify-otp", handle_api_auth_verify_otp)
    app.router.add_post("/api/auth/verify_otp", handle_api_auth_verify_otp)
    app.router.add_post("/api/auth/verify-webapp", handle_api_auth_verify_webapp)
    app.router.add_post("/api/auth/verify_webapp", handle_api_auth_verify_webapp)
    app.router.add_post("/api/auth/verify-token", handle_api_auth_verify_token)
    app.router.add_post("/api/auth/verify_token", handle_api_auth_verify_token)
    app.router.add_get("/api/auth/verify-token", handle_api_auth_verify_token)
    app.router.add_get("/api/auth/verify_token", handle_api_auth_verify_token)
    app.router.add_post("/api/auth/logout", handle_api_auth_logout)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/bot_user", handle_api_bot_user)
    app.router.add_get("/api/user/sync-profile", handle_api_sync_profile)
    app.router.add_post("/api/user/sync-profile", handle_api_sync_profile)
    app.router.add_get("/api/channels", handle_api_channels)
    app.router.add_post("/api/channels/select", handle_api_channel_select)
    app.router.add_get("/api/autopost-tasks", handle_api_autopost_tasks)
    app.router.add_get("/api/autopost-tasks/{task_id}/details", handle_api_autopost_task_details)
    app.router.add_post("/api/autopost-tasks/action", handle_api_autopost_task_action)
    app.router.add_get("/api/videos", handle_api_videos)
    app.router.add_get("/api/trending", handle_api_trending)
    app.router.add_get("/api/health-score", handle_api_health_score)
    app.router.add_get("/api/best-time", handle_api_best_time)
    app.router.add_post("/api/autopost-create", handle_api_autopost_create)
    app.router.add_get("/api/video-formats", handle_api_video_formats)
    app.router.add_get("/api/video_formats", handle_api_video_formats)
    app.router.add_get("/api/download-file", handle_api_download_file)
    app.router.add_get("/api/download_file", handle_api_download_file)
    app.router.add_post("/api/reset-db", handle_api_reset_db)
    app.router.add_get("/oauth/youtube/start", handle_oauth_youtube_start)
    app.router.add_get("/api/oauth/youtube/url", handle_oauth_youtube_start)
    app.router.add_get("/oauth/callback", handle_oauth_callback)
    
    # 5 Tier Telegram Stars Mystery Cases & Live API
    app.router.add_get("/api/stars/cases", handle_api_stars_cases)
    app.router.add_get("/api/stars/live-gifts", handle_api_stars_live_gifts)
    app.router.add_post("/api/stars/open-case", handle_api_stars_open_case)
    app.router.add_post("/api/stars/open-case-uzs", handle_api_stars_open_case_uzs)
    app.router.add_get("/favicon.ico", handle_favicon)
    app.router.add_get("/favicon.svg", handle_favicon)
    app.router.add_get("/api/user/avatar/{user_id}", handle_api_user_avatar)
    app.router.add_get("/api/telegram-file/{file_id}", handle_api_telegram_file)
    app.router.add_post("/api/stars/create-invoice", handle_api_stars_create_invoice)

    # Yangi 6 ta Monetizatsiya & O'yin API lari
    app.router.add_get("/api/stars/recent-drops", handle_api_stars_recent_drops)
    app.router.add_get("/api/stars/pvp-battles", handle_api_stars_pvp_battles)
    app.router.add_post("/api/stars/pvp-battle/create", handle_api_stars_pvp_create)
    app.router.add_post("/api/stars/pvp-battle/join", handle_api_stars_pvp_join)
    app.router.add_post("/api/stars/pvp-battle/cancel", handle_api_stars_pvp_cancel)
    app.router.add_post("/api/stars/upgrader", handle_api_stars_upgrader)
    app.router.add_get("/api/stars/upgrader/inventory", handle_api_stars_upgrader_inventory)
    app.router.add_get("/api/stars/user-inventory", handle_api_stars_user_inventory)
    app.router.add_get("/api/stars/user-gifts", handle_api_stars_user_inventory)
    app.router.add_post("/api/stars/withdraw-gift", handle_api_stars_withdraw_gift)
    app.router.add_post("/api/stars/recycle-gift", handle_api_stars_recycle_gift)
    app.router.add_get("/api/stars/daily-streak", handle_api_stars_daily_streak)
    app.router.add_post("/api/stars/daily-streak/claim", handle_api_stars_daily_claim)
    app.router.add_post("/api/stars/scratch-card/play", handle_api_stars_scratch_card)
    app.router.add_get("/api/stars/scratch-card/play", handle_api_stars_scratch_card)
    app.router.add_post("/api/stars/scratch_card/play", handle_api_stars_scratch_card)
    app.router.add_get("/api/stars/scratch_card/play", handle_api_stars_scratch_card)
    app.router.add_get("/api/stars/scratch-card/status", handle_api_stars_scratch_card)
    app.router.add_get("/api/stars/scratch_card/status", handle_api_stars_scratch_card)
    app.router.add_post("/api/stars/redeem-service", handle_api_stars_redeem)
    app.router.add_post("/api/stars/upgrader/roll", handle_api_stars_upgrader)
    app.router.add_post("/api/stars/store/redeem", handle_api_stars_redeem)
    app.router.add_post("/api/stars/pvp/create", handle_api_stars_pvp_create)
    app.router.add_post("/api/stars/pvp/join", handle_api_stars_pvp_join)
    app.router.add_post("/api/stars/pvp/cancel", handle_api_stars_pvp_cancel)
    app.router.add_get("/api/stars/marketplace-nfts", handle_api_stars_marketplace_nfts)
    app.router.add_get("/api/stars/ton-rate", handle_api_stars_ton_rate)
    app.router.add_post("/api/stars/marketplace/buy", handle_api_stars_marketplace_buy)
    app.router.add_post("/api/stars/marketplace/buy-invoice", handle_api_stars_marketplace_buy_invoice)
    app.router.add_get("/api/nft/fragment-image/{slug}", handle_fragment_image_proxy)

    # VenteBot Reseller API (so'm balansi, xavfsiz atomik buyurtma va kesh)
    app.router.add_get("/api/reseller/products", handle_api_reseller_products)
    app.router.add_post("/api/reseller/quote", handle_api_reseller_quote)
    app.router.add_post("/api/reseller/buy", handle_api_reseller_buy)
    app.router.add_get("/api/reseller/my-orders", handle_api_reseller_my_orders)
    app.router.add_get("/api/reseller/admin/wallet", handle_api_reseller_admin_wallet)

    # Yangi: CryptoPay Webhook va KYC WebApp
    app.router.add_post("/webhook/cryptopay", handle_cryptopay_webhook)
    app.router.add_get("/kyc/verify", handle_kyc_page)
    app.router.add_get("/kyc", handle_kyc_page)
    app.router.add_get("/kyc/face-scan", handle_kyc_page)
    app.router.add_get("/kyc/status", handle_kyc_status)
    app.router.add_post("/kyc/submit", handle_kyc_submit)
    
    # Yangi: TON Connect Mini App & Manifest
    app.router.add_get("/tonconnect-manifest.json", handle_tc_manifest)
    app.router.add_get("/tonconnect/page", handle_tonconnect_page)
    app.router.add_get("/ton", handle_tonconnect_page)
    app.router.add_post("/api/tonconnect/save", handle_api_tonconnect_save)
    app.router.add_post("/api/tonconnect/disconnect", handle_api_tonconnect_disconnect)
    
    # Yangi: 3D NFT Metadata & Media API (TEP-64 Off-chain standard)
    app.router.add_get("/api/nft/meta/{item_id}", handle_nft_metadata)
    app.router.add_get("/api/nft/image/{filename}", handle_nft_image)
    app.router.add_get("/api/nft/video/{filename}", handle_nft_video)
    app.router.add_get("/api/nft/animation/{slug}", handle_api_nft_animation)
    
    # Yangi: Reseller & Developer REST API (/api/v1/...) + Clean Aliases (/docs, /captcha)
    try:
        from reseller_api import (
            handle_api_docs_html,
            handle_captcha_demo_page,
            setup_reseller_api_routes,
        )
        setup_reseller_api_routes(app)
        app.router.add_get("/docs", handle_api_docs_html)
        app.router.add_get("/captcha", handle_captcha_demo_page)
    except Exception as e:
        print(f"reseller_api ulanish xatosi: {e}")
    
    # Admin Observability & n8n-Style Telemetry Flow
    app.router.add_get("/admin/telemetry", handle_admin_telemetry_ui)
    app.router.add_get("/admin/flow", handle_admin_telemetry_ui)
    app.router.add_post("/api/admin/verify", handle_api_admin_verify)
    app.router.add_get("/api/admin/telemetry/stream", handle_api_telemetry_stream)
    app.router.add_post("/api/admin/telemetry/config", handle_api_telemetry_config)
    app.router.add_post("/api/admin/telemetry/purge", handle_api_telemetry_purge)
    app.router.add_post("/api/admin/logout", handle_api_admin_logout)
    app.router.add_get("/api/admin/logout", handle_api_admin_logout)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server {port}-portda ishga tushdi (OAuth callback, CryptoPay, TON Connect & KYC tayyor)")
    return runner


# ==================== MAIN ====================

async def main():
    """
    ROLE env o'zgaruvchisiga qarab ishga tushirish:

      ROLE=main        → TG bot (userbot + ytbot) + web server + autopilot worker
      ROLE=worker      → Faqat autopost worker queue (bot polling yo'q)
      ROLE=streamer    → Faqat autostream HTTP API server (FFmpeg manager)
      ROLE=downloader  → Faqat download HTTP API server (yt-dlp)
      ROLE=autoposter  → Faqat autopost worker queue (worker bilan bir xil)
    """
    global ytbot_instance

    role = os.environ.get("ROLE", "main")
    port = int(os.environ.get("PORT", 3000))

    print(f"\n========================================")
    print(f"🚀 Ishga tushirilmoqda... ROLE: {role}")
    print(f"========================================\n")

    # ------------------------------------------------------------------ #
    #  ROLE = streamer                                                     #
    #  DB queue dan stream tasklerini olib FFmpeg bilan ishga tushiradi   #
    #  Agar 2 ta odam stream qilsa — 2 ta streamer instance parallel ishl #
    # ------------------------------------------------------------------ #
    if role == "streamer":
        from aiohttp import web as _web
        from autostream import _streamer_state, start_stream_task, run_streamer_queue

        bot_client_holder = {"client": None}

        async def _handle_health_simple(request):
            return _web.Response(text="streamer ok")

        async def _handle_status_streamer(request):
            return _web.json_response({
                "role": "streamer",
                "busy": _streamer_state["task_id"] is not None,
                "task_id": _streamer_state["task_id"],
            })

        async def _handle_claim_task_streamer(request):
            try:
                data = await request.json()
                task_id = int(data["task_id"])
            except Exception as e:
                return _web.json_response({"ok": False, "error": f"bad request: {e}"}, status=400)

            if _streamer_state["task_id"] is not None:
                return _web.json_response({"ok": False, "error": "busy"}, status=409)

            from database import claim_stream_task_by_id
            worker_id = f"pushed_streamer_{os.getpid()}"
            task = claim_stream_task_by_id(task_id, worker_id)
            if not task:
                # Boshqa streamer allaqachon olgan yoki bekor qilingan bo'lishi mumkin
                return _web.json_response({"ok": False, "error": "task_not_available"}, status=409)

            asyncio.create_task(
                start_stream_task(task, worker_id, bot_client_holder["client"])
            )
            return _web.json_response({"ok": True, "task_id": task_id})

        app = _web.Application()
        app.router.add_get("/", _handle_health_simple)
        app.router.add_get("/status", _handle_status_streamer)
        app.router.add_post("/claim-task", _handle_claim_task_streamer)

        runner = _web.AppRunner(app)
        await runner.setup()
        site = _web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"📡 Streamer service {port}-portda tayyor (/status, /claim-task)")

        # Streamer bot client ochmaydi — faqat ROLE=main botni boshqaradi
        bot_client_holder["client"] = None

        await run_streamer_queue(port, bot_client=None)
        return

    # ------------------------------------------------------------------ #
    #  ROLE = downloader                                                   #
    #  Faqat yt-dlp download HTTP API — bot yo'q, FFmpeg yo'q             #
    # ------------------------------------------------------------------ #
    if role == "downloader":
        from aiohttp import web as _web

        async def _handle_download(request):
            try:
                data = await request.json()
                search_query = data["query"]
                tg_user_id   = int(data.get("tg_user_id", 0))
                limit        = int(data.get("limit", 6))
                chat_id      = data.get("chat_id", tg_user_id)

                from autostream import download_videos
                paths = await download_videos(search_query, chat_id, tg_user_id=tg_user_id, limit=limit)
                return _web.json_response({"ok": True, "paths": paths})
            except Exception as e:
                print(f"[downloader] _handle_download error: {e}")
                return _web.json_response({"error": "Yuklab olishda ichki xatolik yuz berdi"}, status=500)

        async def _handle_health_dl(request):
            return _web.Response(text="downloader ok")

        app = _web.Application()
        app.router.add_get("/", _handle_health_dl)
        app.router.add_post("/download", _handle_download)

        runner = _web.AppRunner(app)
        await runner.setup()
        site = _web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"📥 Downloader service {port}-portda tayyor")
        await asyncio.Event().wait()
        return

    # ------------------------------------------------------------------ #
    #  ROLE = worker  yoki  ROLE = autoposter                             #
    #  Faqat autopost worker queue — bot polling yo'q                     #
    #  /status va /claim-task — ROLE=main dan HTTP orqali push qabul      #
    #  qilish uchun (bo'sh bo'lsa darhol oladi, band bo'lsa rad etadi,    #
    #  shunda main DB navbatiga yozib qo'yaveradi).                       #
    # ------------------------------------------------------------------ #
    if role in ("worker", "autoposter"):
        from aiohttp import web as _web

        bot_client_holder = {"client": None}

        async def _handle_health_worker(request):
            return _web.Response(text=f"{role} ok")

        async def _handle_status_worker(request):
            return _web.json_response({
                "role": role,
                "busy": _autopost_busy_state["busy"],
                "task_id": _autopost_busy_state["task_id"],
            })

        async def _handle_claim_task_worker(request):
            import json
            try:
                data = await request.json()
                task_id = int(data["task_id"])
            except Exception as e:
                return _web.json_response({"ok": False, "error": f"bad request: {e}"}, status=400)

            if _autopost_busy_state["busy"]:
                return _web.json_response({"ok": False, "error": "busy"}, status=409)

            from database import claim_autopost_task_by_id
            task = claim_autopost_task_by_id(task_id)
            if not task:
                # Boshqa worker allaqachon olgan bo'lishi mumkin — bu xato emas
                return _web.json_response({"ok": False, "error": "task_not_available"}, status=409)

            worker_id = f"pushed_{os.getpid()}"
            asyncio.create_task(
                _run_autopost_task(task, worker_id, bot_client_holder["client"])
            )
            return _web.json_response({"ok": True, "task_id": task_id})

        app = _web.Application()
        app.router.add_get("/", _handle_health_worker)
        app.router.add_get("/status", _handle_status_worker)
        app.router.add_post("/claim-task", _handle_claim_task_worker)

        runner = _web.AppRunner(app)
        await runner.setup()
        site = _web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"👷 {role.upper()} service {port}-portda tayyor (/status, /claim-task)")

        # Worker bot client ochmaydi — faqat ROLE=main botni boshqaradi
        bot_client_holder["client"] = None

        await run_worker_queue(bot_client=None)
        return

    # ------------------------------------------------------------------ #
    #  ROLE = main  (default)                                             #
    #  Web server binds first (<50ms), then DB init & Telegram bots       #
    # ------------------------------------------------------------------ #
    await start_web_server(port)

    def _safe_init_db():
        try:
            from database import init_db
            init_db()
        except Exception as db_init_err:
            print(f"init_db xatosi: {db_init_err}")

    await asyncio.to_thread(_safe_init_db)

    tasks = []

    # 1. MonoDeck Userbot
    if SESSION_STRING:
        from userbot import run_userbot
        tasks.append(run_userbot())
        print(f"🤖 {BRAND_NAME} Userbot qo'shildi")
    else:
        print("⚠️  SESSION_STRING topilmadi — Userbot o'chirilgan")
    
    BOT_TOKEN = os.getenv("BOT_TOKEN") or BOT_TOKEN
    # 2. MonoDeck Bot
    if BOT_TOKEN:
        from ytbot import create_ytbot
        bot = create_ytbot()
        if bot:
            ytbot_instance = bot
            async def _register_bot_commands(target_bot):
                try:
                    from pyrogram.types import BotCommand
                    await target_bot.set_bot_commands([
                        BotCommand("start", "Botni ishga tushirish"),
                        BotCommand("menu", "Asosiy menyuni ochish"),
                        BotCommand("help", "Barcha buyruqlar va yordam"),
                        BotCommand("support", "Gemini AI Yordam & Live Admin"),
                        BotCommand("check", "P2P Shartli Chek yaratish"),
                        BotCommand("igcloner", "Instagram Auto-Kloner"),
                        BotCommand("capcut", "CapCut Pro Xarid Qilish (Pullik)"),
                        BotCommand("aivideo", "AI Video Studio ($20/oy)"),
                        BotCommand("spy", "Raqobatchi Tahlili (Spy & SEO)"),
                        BotCommand("cashout", "Balansni Yechish (Stars & TON)"),
                        BotCommand("deeplink", "Smart YouTube DeepLink & QR"),
                        BotCommand("balance", "Hisob balansi va to'lovlar"),
                        BotCommand("redeem", "Promokod / Vaucher faollashtirish"),
                        BotCommand("newpromo", "Yangi promokod yaratish (Admin)"),
                        BotCommand("box", "Omadli Quti (Mystery Box)"),
                        BotCommand("wheel", "Omad G'ildiragi (Kunlik spin)"),
                        BotCommand("duel", "PvP Tanga Tashlash (Coin Flip)"),
                        BotCommand("lottery", "Jekpot Mega Lotereya"),
                        BotCommand("makegift", "Sovg'a vaucheri yaratish (Admin)"),
                        BotCommand("api", "Developer & Reseller REST API"),
                        BotCommand("dashboard", "Developer WebApp Dashboard"),
                        BotCommand("stock", "API kalit va Proksi zaxirasi"),
                        BotCommand("webhook", "Reseller Webhook ($3/hafta)"),
                        BotCommand("createbot", "1-Click White-Label Bot ($50)"),
                        BotCommand("shortfactory", "Shorts Factory (AI video yasash)"),
                        BotCommand("autostream", "24/7 jonli efirni boshlash"),
                        BotCommand("setstreamkey", "Stream Key ni sozlash"),
                        BotCommand("reaction", "Reaksiya (PiP) video yasash"),
                        BotCommand("autopost", "Avtomatik qisqa video yuklash"),
                        BotCommand("autopilot", "Avtopilot rejim sozlamalari"),
                        BotCommand("setton", "TON hamyon manzilini sozlash"),
                        BotCommand("myton", "TON hamyon manzilini ko'rish"),
                        BotCommand("ytlogin", "YouTube akkauntni ulash"),
                        BotCommand("login_status", "Akkaunt ulanish holati"),
                        BotCommand("delaccount", "Akkauntni uzish"),
                        BotCommand("setcookies", "YouTube Cookies yuklash"),
                        BotCommand("setproxy", "Shaxsiy proksi o'rnatish"),
                        BotCommand("myproxy", "Joriy proksini ko'rish"),
                        BotCommand("myid", "Telegram ID ni ko'rish"),
                        BotCommand("ping", "Bot tezligi va server holati"),
                        BotCommand("status", "Tizim va API holatini ko'rish"),
                        BotCommand("channel", "Kanal umumiy statistikasi"),
                        BotCommand("recent", "Oxirgi videolar"),
                        BotCommand("popular", "Eng mashhur videolar"),
                        BotCommand("growth", "Kanal o'sish analitikasi"),
                        BotCommand("engagement", "Auditoriya faolligi (like/comment)"),
                        BotCommand("earnings", "Daromad (tahminiy)"),
                        BotCommand("milestone", "Maqsadlarga yetish vaqti"),
                        BotCommand("goal", "Kanal maqsadlari & milestone (/goal)"),
                        BotCommand("boost", "Kanal va postlarni tezlashtirish (/boost)"),
                        BotCommand("teamwork", "Jamoaviy hamkorlik & rollar (/teamwork)"),
                        BotCommand("report", "Kanalning to'liq hisoboti"),
                        BotCommand("compare", "Raqobatchi bilan solishtirish"),
                        BotCommand("comments", "Videodagi oxirgi izohlar"),
                        BotCommand("tags", "Videodan teglarni olish"),
                        BotCommand("thumbnail", "Video muqovasini yuklab olish"),
                        BotCommand("search", "YouTube dan video qidirish"),
                        BotCommand("trending", "Trenddagi videolar"),
                        BotCommand("track", "Raqobatchini kuzatuvga qo'shish"),
                        BotCommand("untrack", "Kuzatuvdan olib tashlash"),
                        BotCommand("mylist", "Kuzatilayotgan kanallar"),
                        BotCommand("addrival", "Raqobatchi kanal qo'shish"),
                        BotCommand("myrivals", "Raqobatchilar ro'yxati"),
                        BotCommand("rivals", "Kanal raqobatchilari tahlili"),
                        BotCommand("mass", "Ommaviy harakatlar (Like/Comment)"),
                        BotCommand("dl", "Videoni yuklab olish"),
                        BotCommand("seo", "SEO tahlil va maslahatlar"),
                        BotCommand("tagsgen", "AI orqali SEO teglar yaratish"),
                        BotCommand("ideas", "Yangi video g'oyalari (AI)"),
                        BotCommand("script", "Video ssenariy yozish (AI)"),
                        BotCommand("shorts", "Shorts uchun ssenariy (AI)"),
                        BotCommand("thumbidea", "Thumbnail g'oyalari (AI)"),
                        BotCommand("clickbait", "Clickbait sarlavhalar (AI)"),
                        BotCommand("rewrite", "Tavsifni qayta yozish (AI)"),
                        BotCommand("roast", "Kanalni AI yordamida tanqid qilish"),
                        BotCommand("audit", "Kanalni audit qilish (AI)"),
                        BotCommand("summarize", "Videoni AI orqali qisqartirish"),
                        BotCommand("categories", "YouTube kategoriyalari ro'yxati"),
                        BotCommand("id", "URL dan video/kanal ID olish"),
                        BotCommand("live", "Jonli efir holatini tekshirish"),
                        BotCommand("nft", "3D NFT Studio (Bepul yaratish)"),
                    ])
                except Exception as e:
                    print(f"Bot commands xatosi: {e}")

            async def _post_startup_background():
                """Og'ir tarmoq so'rovlarini fon rejimida bajarish (asosiy bot javob berish tezligini 0ms ga tushirish)"""
                try:
                    from ton_checker import start_ton_watcher_task
                    start_ton_watcher_task(bot)
                except Exception as ton_err:
                    print(f"TON watcher ishga tushirishda xato: {ton_err}")
                try:
                    from mega_features import start_nft_watcher_task
                    start_nft_watcher_task(bot)
                except Exception as nft_err:
                    print(f"NFT watcher ishga tushirishda xato: {nft_err}")
                await _register_bot_commands(bot)
                try:
                    from ytbot import AUTO_EMOJI_MAP
                    from custom_emojis import CUSTOM_EMOJI_POOL
                    ids = [int(str(i).strip()) for i in CUSTOM_EMOJI_POOL if str(i).strip().isdigit()]
                    stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=ids)
                    for s in stickers:
                        if getattr(s, 'emoji', None):
                            AUTO_EMOJI_MAP[s.emoji] = s.custom_emoji_id
                    print(f"🌟 Yuklangan maxsus emojilar soni: {len(AUTO_EMOJI_MAP)}")
                except Exception as e:
                    print(f"Maxsus emojilarni yuklashda xatolik: {e}")

                try:
                    from humo_listener import start_humo_listener_background
                    start_humo_listener_background(bot)
                except Exception as e:
                    print(f"Humo listener startup error: {e}")

                try:
                    from games_monetization import fetch_telegram_server_gifts
                    server_gifts = await fetch_telegram_server_gifts(BOT_TOKEN)
                    print(f"🎁 Telegram serveridan {len(server_gifts)} ta rasmiy sovg'a yuklandi va STARS_CASES yangilandi.")
                except Exception as gift_err:
                    print(f"Server gifts startup error: {gift_err}")

                try:
                    from ytbot import gift_autoflush_worker
                    asyncio.create_task(gift_autoflush_worker(bot))
                    print("🎁 Telegram Stars Sovg'alarni avto-yuboruvchi (AutoFlush Worker) ishga tushirildi.")
                except Exception as flush_err:
                    print(f"AutoFlush worker startup error: {flush_err}")

                try:
                    asyncio.create_task(gemini_price_watcher(bot))
                    print("📊 Gemini 18M Price Watcher ishga tushirildi ($0.50 dan kam bo'lsa ogohlantirish)")
                except Exception as pw_err:
                    print(f"Gemini Price Watcher startup error: {pw_err}")

                try:
                    from store_channel_service import run_channel_autopilot
                    asyncio.create_task(run_channel_autopilot(bot))
                    print(f"📢 @{get_bot_username()} Store kanal avtopiloti ishga tushirildi.")
                except Exception as cp_err:
                    print(f"Kanal avtopilot xatosi: {cp_err}")

                try:
                    from instagram_cloner import start_instagram_sync_daemon
                    asyncio.create_task(start_instagram_sync_daemon(bot, interval_seconds=1800))
                    print("📸 Instagram Auto-Tracker & YouTube Sync Daemon ishga tushirildi.")
                except Exception as ig_err:
                    print(f"Instagram Sync Daemon startup xatosi: {ig_err}")
                try:
                    from telegram_marketplace_service import run_marketplace_background_refresher
                    asyncio.create_task(run_marketplace_background_refresher(interval_seconds=300))
                    print("🚀 Telegram Marketplace 300s Background Stock Refresher ishga tushirildi.")
                except Exception as mp_err:
                    print(f"Marketplace Refresher startup error: {mp_err}")



            async def run_bot():
                await bot.start()
                try:
                    me = await bot.get_me()
                    if getattr(me, "username", None):
                        set_runtime_bot_username(me.username)
                except Exception:
                    pass
                print(f"✨ {BRAND_NAME} Bot (@{get_bot_username()}) muvaffaqiyatli ishga tushdi!")
                asyncio.create_task(_post_startup_background())
                await asyncio.Event().wait()
            tasks.append(run_bot())
            print(f"🎬 {BRAND_NAME} Bot qo'shildi")

        # 3. Ikkilamchi bepul botlar (SECONDARY_BOT_TOKEN / SECONDARY_BOT_TOKENS) — bitta umumiy baza va tizimda
        secondary_tokens = [t for t in _get_configured_bot_tokens() if t != BOT_TOKEN]
        for idx, sec_token in enumerate(secondary_tokens, start=1):
            sec_bot = create_ytbot(bot_token=sec_token, session_name=f"yt_analytics_bot_secondary_{idx}")
            if not sec_bot:
                continue
            secondary_bot_instances.append(sec_bot)

            async def _run_secondary_bot(client=sec_bot, slot=idx):
                await client.start()
                sec_uname = ""
                try:
                    me_sec = await client.get_me()
                    sec_uname = getattr(me_sec, "username", "") or ""
                except Exception:
                    pass
                await _register_bot_commands(client)
                print(f"✨ {BRAND_NAME} Secondary Bot #{slot} (@{sec_uname}) bitta umumiy bazaga ulandi!")
                await asyncio.Event().wait()

            tasks.append(_run_secondary_bot())
            print(f"🎬 {BRAND_NAME} Secondary Bot #{idx} qo'shildi")
    else:
        print("⚠️  BOT_TOKEN topilmadi — YouTube Bot o'chirilgan")

    if not tasks:
        print(f"⚠️  Bot tokenlari topilmadi — {BRAND_NAME} web-only rejimda ishlamoqda.")
        await asyncio.Event().wait()
        return

    tasks.append(run_autopilot_worker())
    tasks.append(_poll_pending_autopost_tasks_loop())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())