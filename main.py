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
from config import SESSION_STRING, BOT_TOKEN, API_ID, API_HASH
from autopost import exchange_code_with_redirect, pending_oauth
from database import save_yt_connection

# ==================== BOT REFERENCES ====================
# ytbot instance ni saqlash (callback dan xabar yuborish uchun)
ytbot_instance = None





# ==================== GEMINI PRICE WATCHER ====================
async def gemini_price_watcher(bot):
    """Gemini 18 oylik narxini tekshirish — $0.50 dan kam bo'lsa adminga xabar yuborish"""
    from config import OWNER_ID
    from database import get_bot_config, set_bot_config

    # Read persistent last alerted price from database so restarts don't trigger repeated alerts
    last_alerted_price = None
    try:
        saved_price = get_bot_config("gemini_price_watcher_last_price")
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
                            set_bot_config("gemini_price_watcher_last_price", str(price_usd))
                            print(f"[PriceWatcher] ⚡ Admin ga ogohlantirish yuborildi: ${price_usd}")
                        except Exception as send_err:
                            print(f"[PriceWatcher] Admin ga xabar yuborishda xato: {send_err}")
                else:
                    if last_alerted_price is not None and price_usd >= THRESHOLD:
                        last_alerted_price = None
                        set_bot_config("gemini_price_watcher_last_price", "")

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
            autopilots = get_all_active_autopilots()
            
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
                            conn = get_yt_connection(user_id)
                            if not conn:
                                await ytbot_instance.send_message(user_id, "❌ **AutoPilot Xatosi:** YouTube kanal ulanmagan! `/ytlogin` orqali ulang.")
                                continue
                                
                            channel_id = conn['yt_channel_id']
                            
                            # Start search and autopost for 1 video
                            from database import create_autopost_task
                            task_id = create_autopost_task(user_id, channel_id, topic, "shorts", 1)

                            # Update last run right away so it doesn't run again if it fails
                            update_autopilot_last_run(user_id)

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
            conn_check = get_db()
            if conn_check:
                try:
                    cur_check = conn_check.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur_check.execute("SELECT status FROM stream_tasks WHERE id=%s", (task_id,))
                    row = cur_check.fetchone()
                    if row and row['status'] == 'cancelled' and proc:
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
                except Exception as e:
                    print(f"[main_streamer] cancel check xato: {e}")
                finally:
                    conn_check.close()

            await asyncio.sleep(5)
    finally:
        _main_running_tasks["count"] = max(0, _main_running_tasks["count"] - 1)


# ==================== WEB SERVER (OAuth Callback + Health Check) ====================

async def handle_health(request):
    """Render health check uchun va WebApp UI"""
    import os
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(
            text=html,
            content_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return web.Response(text="Bot is running!", content_type="text/html")


async def handle_privacy_page(request):
    """Google OAuth & YouTube Data API Compliant Privacy Policy page"""
    from legal_templates import get_privacy_html
    return web.Response(
        text=get_privacy_html(),
        content_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


async def handle_terms_page(request):
    """CreatorFlow Studio SaaS Terms of Service page"""
    from legal_templates import get_terms_html
    return web.Response(
        text=get_terms_html(),
        content_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


async def handle_google_verification(request):
    """Google Search Console Site Verification file handler"""
    filename = request.match_info.get("filename", "")
    import os
    if filename and os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return web.Response(text=f.read().strip(), content_type="text/html", charset="utf-8")
    return web.Response(status=404, text="404 Not Found", content_type="text/plain")


async def handle_robots(request):
    """robots.txt handler for search engines, AI agents (GPTBot, ClaudeBot, etc.) and crawlers"""
    content = """# Robots.txt for CreatorFlow / Bot Client
# AI Agents and Web Crawlers Configuration

User-agent: *
Allow: /
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
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
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/

User-agent: ClaudeBot
Allow: /
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/

User-agent: Google-Extended
Allow: /
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
Allow: /captcha/
Allow: /privacy
Allow: /terms
Disallow: /dashboard
Disallow: /api/auth/
Disallow: /api/v1/admin/
Disallow: /api/user/

User-agent: PerplexityBot
Allow: /
Allow: /api/v1/docs
Allow: /api/v1/products
Allow: /api/v1/tariffs
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
_stats_cache = {}  # {tg_user_id: {"data": ..., "ts": time}}
_CACHE_TTL = 600  # 10 daqiqa

async def handle_api_stats(request):
    """Dashboard uchun real YouTube kanal statistikasi (cached)"""
    import json
    global _stats_cache
    tg_user_id = request.query.get("tg_user_id")
    if not tg_user_id:
        return web.Response(
            text=json.dumps({"error": "tg_user_id kerak"}),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    channel_id = request.query.get("channel_id")
    # Cache tekshirish — agar refresh talab qilinmagan va 10 daqiqa ichida so'ralgan bo'lsa, qayta API chaqirmaslik
    force_refresh = request.query.get("refresh") == "1" or request.query.get("force") == "1"
    cache_key = f"{tg_user_id}_{channel_id or 'default'}"
    cached = _stats_cache.get(cache_key)
    if not force_refresh and cached and (_time.time() - cached["ts"]) < _CACHE_TTL:
        return web.Response(
            text=json.dumps(cached["data"], default=str),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    try:
        from database import get_yt_connection
        from googleapiclient.discovery import build
        from config import YT_CLIENT_ID, YT_CLIENT_SECRET
        from google.oauth2.credentials import Credentials

        conn_data = get_yt_connection(int(tg_user_id), channel_id=channel_id)
        if not conn_data or not conn_data.get("access_token"):
            return web.Response(
                text=json.dumps({"error": "not_logged_in"}),
                content_type="application/json",
                headers={"Access-Control-Allow-Origin": "*"}
            )

        creds = Credentials(
            token=conn_data["access_token"],
            refresh_token=conn_data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=YT_CLIENT_ID,
            client_secret=YT_CLIENT_SECRET
        )
        yt = build("youtube", "v3", credentials=creds)

        # Kanal ma'lumotlari
        ch_res = yt.channels().list(
            part="statistics,snippet,contentDetails",
            mine=True
        ).execute()

        if not ch_res.get("items"):
            return web.Response(
                text=json.dumps({"error": "Kanal topilmadi"}),
                content_type="application/json",
                headers={"Access-Control-Allow-Origin": "*"}
            )

        ch      = ch_res["items"][0]
        stats   = ch["statistics"]
        snippet = ch["snippet"]

        total_subs   = int(stats.get("subscriberCount", 0))
        total_views  = int(stats.get("viewCount", 0))
        total_videos = int(stats.get("videoCount", 0))

        # Oxirgi 10 ta video
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
                        recent_videos.append({
                            "id":        v["id"],
                            "title":     v["snippet"]["title"][:60],
                            "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                            "views":     int(v["statistics"].get("viewCount", 0)),
                            "likes":     int(v["statistics"].get("likeCount", 0)),
                            "comments":  int(v["statistics"].get("commentCount", 0)),
                            "published": v["snippet"]["publishedAt"][:10],
                        })
        except Exception as e:
            print(f"[api/stats] Video xato: {e}")

        # O'rtacha ko'rsatkichlar
        avg_views    = sum(v["views"]    for v in recent_videos) // max(len(recent_videos), 1)
        avg_likes    = sum(v["likes"]    for v in recent_videos) // max(len(recent_videos), 1)
        avg_comments = sum(v["comments"] for v in recent_videos) // max(len(recent_videos), 1)
        engagement   = round((avg_likes + avg_comments) / max(avg_views, 1) * 100, 2)

        # Autopost tarixi
        autopost_stats = {"total": 0, "success": 0, "failed": 0}
        try:
            from database import get_db
            import psycopg2.extras
            conn_db = get_db()
            if conn_db:
                cur = conn_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT status FROM autopost_history WHERE tg_user_id=%s ORDER BY created_at DESC LIMIT 100",
                    (int(tg_user_id),)
                )
                rows = cur.fetchall()
                autopost_stats["total"]   = len(rows)
                autopost_stats["success"] = sum(1 for r in rows if r["status"] == "uploaded")
                autopost_stats["failed"]  = sum(1 for r in rows if r["status"] == "failed")
                
                # Fetch active task progress
                cur.execute(
                    "SELECT id, search_query, total_count, completed_count, status FROM autopost_tasks WHERE tg_user_id=%s ORDER BY id DESC LIMIT 1",
                    (int(tg_user_id),)
                )
                active_task = cur.fetchone()
                if active_task:
                    autopost_stats["active_task"] = {
                        "id": active_task["id"],
                        "query": active_task["search_query"],
                        "total": active_task["total_count"],
                        "completed": active_task["completed_count"],
                        "status": active_task["status"]
                    }
                conn_db.close()
        except Exception as e:
            print(f"[api/stats] Autopost tarixi xato: {e}")
            try: conn_db.close()
            except: pass

        from config import OWNER_ID
        is_owner = (int(tg_user_id) == OWNER_ID)

        ch_title_live = snippet.get("title", "")
        ch_pfp_live = snippet.get("thumbnails", {}).get("medium", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url", "")

        # Real-time DB sync: YouTubedagi eng so'nggi kanal nomi va avatari bazaga yoziladi
        try:
            from database import update_yt_channel_metadata
            update_yt_channel_metadata(
                tg_user_id=int(tg_user_id),
                yt_channel_id=conn_data.get("yt_channel_id", ""),
                channel_title=ch_title_live,
                channel_thumbnail_url=ch_pfp_live,
                subscriber_count=total_subs
            )
        except Exception as e_upd:
            print(f"[api/stats] update_yt_channel_metadata xato: {e_upd}")

        response_data = {
            "channel_title":    ch_title_live,
            "channel_username": conn_data.get("yt_channel_username", ""),
            "channel_thumbnail": ch_pfp_live,
            "channel_country":  snippet.get("country", ""),
            "subscribers":      total_subs,
            "total_views":      total_views,
            "total_videos":     total_videos,
            "avg_views":        avg_views,
            "avg_likes":        avg_likes,
            "avg_comments":     avg_comments,
            "engagement_rate":  engagement,
            "autopost":         autopost_stats,
            "recent_videos":    recent_videos,
            "is_owner":         is_owner,
        }
        
        response_data["channel_id"] = conn_data.get("yt_channel_id", "")
        # Cache'ga saqlash
        _stats_cache[cache_key] = {
            "data": response_data,
            "ts": _time.time()
        }

        return web.Response(
            text=json.dumps(response_data, default=str),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        import traceback
        print(f"[api/stats] Kritik xato: {traceback.format_exc()}")
        try:
            if conn_data:
                fallback_data = {
                    "channel_title": conn_data.get("yt_channel_title", ""),
                    "channel_username": conn_data.get("yt_channel_username", ""),
                    "channel_thumbnail": conn_data.get("channel_thumbnail_url", ""),
                    "subscribers": conn_data.get("subscriber_count", 0),
                    "total_views": 0,
                    "total_videos": 0,
                    "recent_videos": [],
                    "is_owner": (int(tg_user_id) == OWNER_ID),
                }
                return web.Response(
                    text=json.dumps(fallback_data, default=str),
                    content_type="application/json",
                    headers={"Access-Control-Allow-Origin": "*"}
                )
        except:
            pass
        return web.Response(
            text=json.dumps({"error": str(e)[:300]}),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )


async def handle_oauth_callback(request):
    """Google OAuth callback — foydalanuvchi ruxsat bergandan keyin Google shu yerga qaytaradi"""
    code = request.query.get("code")
    state = request.query.get("state")
    error = request.query.get("error")

    if error:
        return web.Response(
            text=f"<html><body style='font-family:sans-serif;text-align:center;padding:50px;'>"
                 f"<h1>❌ Ruxsat berilmadi</h1><p>{error}</p>"
                 f"<p>Telegram botga qaytib, qayta urinib ko'ring.</p></body></html>",
            content_type="text/html"
        )

    if not code:
        return web.Response(
            text="<html><body style='font-family:sans-serif;text-align:center;padding:50px;'>"
                 "<h1>❌ Xatolik</h1><p>Kod topilmadi.</p></body></html>",
            content_type="text/html"
        )

    try:
        result = exchange_code_with_redirect(code, state)

        tg_user_id = result["tg_user_id"]
        channel_title = result["channel_title"]
        channel_id = result["channel_id"]

        if tg_user_id:
            saved = save_yt_connection(
                tg_user_id=tg_user_id,
                yt_channel_id=channel_id,
                yt_channel_title=channel_title,
                yt_channel_username=result.get("channel_username", ""),
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                token_expiry=result["token_expiry"],
                channel_thumbnail_url=result.get("channel_thumbnail", ""),
                subscriber_count=result.get("subscriber_count", 0)
            )

            if saved:
                # Telegram orqali xabar yuborish
                if ytbot_instance:
                    try:
                        await ytbot_instance.send_message(
                            tg_user_id,
                            f"✅ YouTube kanalingiz muvaffaqiyatli ulandi!\n\n"
                            f"📺 Kanal: **{channel_title}**\n"
                            f"🆔 ID: `{channel_id}`\n\n"
                            f"Endi `/autopost` orqali video yuklashingiz mumkin!"
                        )
                    except Exception as e:
                        print(f"Telegram xabar yuborish xatosi: {e}")
            else:
                if ytbot_instance:
                    try:
                        await ytbot_instance.send_message(
                            tg_user_id,
                            f"❌ Xatolik: Kanalingiz ma'lumotlar bazasiga saqlanmadi. Iltimos qaytadan `/ytlogin` qilib ko'ring."
                        )
                    except Exception as e:
                        pass
                return web.Response(
                    text="<html><body style='font-family:sans-serif;text-align:center;padding:50px;background:#1a1a2e;color:#fff;'>"
                         "<h1 style='color:#e74c3c;'>❌ Saqlashda xatolik</h1>"
                         "<p>Ma'lumotlar bazasiga saqlanmadi. Qaytadan /ytlogin qiling.</p></body></html>",
                    content_type="text/html"
                )

        html = (
            f"<html><body style='font-family:sans-serif;text-align:center;padding:50px;"
            f"background:#1a1a2e;color:#fff;'>"
            f"<h1 style='color:#4ecca3;'>✅ Muvaffaqiyatli ulandi!</h1>"
            f"<p style='font-size:20px;'>Kanal: <strong>{channel_title}</strong></p>"
            f"<p>Endi Telegram botga qaytib, <code>/autopost</code> buyrug'ini ishlating.</p>"
            f"<p style='margin-top:30px;'>Bu oynani yopishingiz mumkin.</p>"
            f"</body></html>"
        )
        return web.Response(text=html, content_type="text/html")

    except Exception as e:
        print(f"OAuth callback xatosi: {e}")
        return web.Response(
            text=f"<html><body style='font-family:sans-serif;text-align:center;padding:50px;'>"
                 f"<h1>❌ Xatolik yuz berdi</h1><p>{e}</p>"
                 f"<p>Telegram botga qaytib, /ytlogin ni qayta bosing.</p></body></html>",
            content_type="text/html"
        )



async def handle_api_bot_user(request):
    """Foydalanuvchi profil va balans ma'lumotlari (ism, rasm, balans, sinxronizatsiya)"""
    import json
    tg_user_id = request.query.get("tg_user_id")
    if not tg_user_id:
        return web.Response(text=json.dumps({"error": "tg_user_id kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    try:
        uid = int(tg_user_id)
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
            "photo_url": details.get("photo_url"),
            "balance_uzs": details.get("balance_uzs", 0),
            "ton_balance": details.get("ton_balance", 0.0),
            "is_vip": bool(vip_info.get("is_vip")),
            "is_owner": is_owner
        }
        return web.Response(text=json.dumps(resp, default=str), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"ok": False, "error": str(e)}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_sync_profile(request):
    """Telegram profil ma'lumotlarini majburiy qayta sinxronlash (ism, rasm, username)"""
    import json
    try:
        data = {}
        if request.method == "POST":
            try: data = await request.json()
            except: pass
        tg_user_id = data.get("tg_user_id") or request.query.get("tg_user_id")
        if not tg_user_id:
            return web.Response(text=json.dumps({"ok": False, "error": "tg_user_id kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
            
        uid = int(tg_user_id)
        user_context = {
            "first_name": data.get("first_name") or request.query.get("first_name"),
            "last_name": data.get("last_name") or request.query.get("last_name"),
            "username": data.get("username") or request.query.get("username"),
            "photo_url": data.get("photo_url") or request.query.get("photo_url"),
            "photo_file_id": data.get("photo_file_id") or request.query.get("photo_file_id")
        }
        from database import sync_tg_user_profile, get_user_full_details
        sync_tg_user_profile(uid, user_context=user_context)
        details = get_user_full_details(uid, force_sync=False, user_context=user_context)
        return web.Response(text=json.dumps({"ok": True, "profile": details}, default=str), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"ok": False, "error": str(e)}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_channel_select(request):
    """Foydalanuvchi faol YouTube kanalini tanlashi (Single-Account Selection)"""
    import json
    global _stats_cache
    try:
        data = await request.json()
    except Exception:
        data = {}
    tg_user_id = data.get("tg_user_id") or request.query.get("tg_user_id")
    channel_id = data.get("channel_id") or request.query.get("channel_id")
    if not tg_user_id or not channel_id:
        return web.Response(
            text=json.dumps({"ok": False, "error": "tg_user_id va channel_id kerak"}),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    try:
        from database import set_default_account
        uid = int(tg_user_id)
        ok = set_default_account(uid, str(channel_id))
        # Yangi tanlangan kanalning yangi statistikasi ko'rinishi uchun keshni tozalash
        for k in list(_stats_cache.keys()):
            if str(k).startswith(str(uid)):
                _stats_cache.pop(k, None)
        return web.Response(
            text=json.dumps({"ok": ok, "selected_channel_id": channel_id}),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return web.Response(
            text=json.dumps({"ok": False, "error": str(e)}),
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )

async def handle_api_channels(request):
    """Foydalanuvchining barcha ulangan kanallari"""
    import json
    tg_user_id = request.query.get("tg_user_id")
    if not tg_user_id:
        return web.Response(text=json.dumps({"error": "tg_user_id kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    try:
        from database import get_all_yt_connections, get_default_account
        tg_id = int(tg_user_id)
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
        return web.Response(text=json.dumps({"channels": channels, "default_channel_id": default_ch_id}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_autopost_tasks(request):
    """Foydalanuvchining barcha autopost vazifalari"""
    import json
    tg_user_id = request.query.get("tg_user_id")
    if not tg_user_id:
        return web.Response(text=json.dumps({"error": "tg_user_id kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    try:
        from database import get_autopost_tasks
        tasks = get_autopost_tasks(int(tg_user_id))
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
        return web.Response(text=json.dumps({"tasks": result}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

_video_search_cache = {}  # {cache_key: {"videos": [...], "ts": float}}

async def handle_api_videos(request):
    """YouTube'dan video qidirish (keshlangan va quota-safe)"""
    import json
    q = request.query.get("q", "").strip()
    max_results = int(request.query.get("maxResults", "12"))
    video_type = request.query.get("type", "")  # "short" or ""
    
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
        
        _video_search_cache[cache_key] = {"videos": videos, "ts": _time.time()}
        return web.Response(text=json.dumps({"videos": videos}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        err_msg = str(e)
        if "quotaExceeded" in err_msg or "rateLimitExceeded" in err_msg or "403" in err_msg:
            return web.Response(text=json.dumps({
                "videos": [],
                "warning": "YouTube API kunlik kvotasi yetarli emas. Iltimos keyinroq qayta urinib ko'ring."
            }), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
        return web.Response(text=json.dumps({"error": err_msg[:300], "videos": []}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_trending(request):
    """Trendagidagi videolar"""
    import json
    region = request.query.get("region", "UZ")
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
        return web.Response(text=json.dumps({"videos": videos}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)[:300]}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_health_score(request):
    """Channel Health Score (100 ballik)"""
    import json
    tg_user_id = request.query.get("tg_user_id")
    if not tg_user_id:
        return web.Response(text=json.dumps({"error": "tg_user_id kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    try:
        from database import get_yt_connection
        from googleapiclient.discovery import build
        from config import YT_CLIENT_ID, YT_CLIENT_SECRET
        from google.oauth2.credentials import Credentials

        conn_data = get_yt_connection(int(tg_user_id))
        if not conn_data:
            return web.Response(text=json.dumps({"error": "not_logged_in"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=403)

        creds = Credentials(token=conn_data["access_token"], refresh_token=conn_data["refresh_token"], token_uri="https://oauth2.googleapis.com/token", client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET)
        yt = build("youtube", "v3", credentials=creds)

        ch_res = yt.channels().list(part="statistics,snippet,contentDetails,brandingSettings", mine=True).execute()
        if not ch_res.get("items"):
            return web.Response(text=json.dumps({"error": "Kanal topilmadi"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})

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
        }, default=str), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        import traceback
        print(f"Health Score Error: {traceback.format_exc()}")
        return web.Response(text=json.dumps({"error": str(e)[:300]}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_best_time(request):
    """Eng yaxshi yuklash vaqti"""
    import json
    tg_user_id = request.query.get("tg_user_id")
    if not tg_user_id:
        return web.Response(text=json.dumps({"error": "tg_user_id kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    try:
        from database import get_yt_connection
        from googleapiclient.discovery import build
        from config import YT_CLIENT_ID, YT_CLIENT_SECRET
        from google.oauth2.credentials import Credentials
        from datetime import datetime
        from collections import defaultdict

        conn_data = get_yt_connection(int(tg_user_id))
        if not conn_data:
            return web.Response(text=json.dumps({"error": "not_logged_in"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})

        creds = Credentials(token=conn_data["access_token"], refresh_token=conn_data["refresh_token"], token_uri="https://oauth2.googleapis.com/token", client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET)
        yt = build("youtube", "v3", credentials=creds)

        ch_res = yt.channels().list(part="contentDetails", mine=True).execute()
        if not ch_res.get("items"):
            return web.Response(text=json.dumps({"error": "Kanal topilmadi"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})

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
        }), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)[:300]}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

async def handle_api_video_formats(request):
    """Video uchun mavjud formatlarni olish (fallback va tezkor response bilan)"""
    import json
    video_id = request.query.get("video_id") or request.query.get("id")
    tg_user_id = request.query.get("tg_user_id")
    
    if not video_id:
        return web.json_response({"error": "video_id kerak"}, status=400, headers={"Access-Control-Allow-Origin": "*"})
    
    video_id = str(video_id).strip()
    
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
        tg_user_id = request.query.get("tg_user_id", "").strip()

        if not raw_video_id:
            return web.json_response({"ok": False, "error": "video_id kerak"}, status=200, headers={"Access-Control-Allow-Origin": "*"})

        # Extract clean 11-char video ID if full URL was passed
        video_id = raw_video_id
        if "youtu" in raw_video_id:
            m = re.search(r'(?:v=|\/|youtu\.be\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})', raw_video_id)
            if m:
                video_id = m.group(1)

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
                "Access-Control-Allow-Origin": "*",
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
        target_chat_id = int(tg_user_id) if (tg_user_id and str(tg_user_id).isdigit() and int(tg_user_id) > 1000) else int(os.getenv("OWNER_ID", "6735799833"))
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
                                    f"☁️ <b>7 GB RAM Cloud Runner (GitHub Actions)</b> orqali tayyorlanmoqda va bir necha soniyada shu yerga yuboriladi!"
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
                caption=f"🎬 <b>Yuklab olingan video</b> ({video_id})\n📐 Sifat: {resolution}\n⚡ <i>7 GB RAM Cloud Runner</i>",
                bot_token=BOT_TOKEN
            ))
        except Exception as gh_err:
            print(f"GitHub Actions dispatch notice for user {target_chat_id}: {gh_err}")

        # 3. Return immediate friendly response to WebApp iframe
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Video Yuklanmoqda</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090a0f; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; text-align: center; }}
        .card {{ background: #131722; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 20px; padding: 32px 24px; max-width: 420px; box-shadow: 0 12px 40px rgba(0,0,0,0.5); }}
        h2 {{ margin: 0 0 12px; font-size: 20px; color: #10b981; }}
        p {{ color: #a1a1aa; font-size: 14px; line-height: 1.5; margin: 0 0 24px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🚀 Video Yuklanmoqda!</h2>
        <p>Video <b>7 GB RAM Cloud Runner (GitHub Actions)</b> orqali yuklanmoqda va to'g'ridan-to'g'ri Telegram botingizga yuboriladi!</p>
        <p style="font-size: 12px; color: #71717a;">Telegram bot chatini tekshiring.</p>
    </div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html", status=200, headers={"Access-Control-Allow-Origin": "*"})

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
                        "Access-Control-Allow-Origin": "*",
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
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090a0f; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; text-align: center; }}
        .card {{ background: #131722; border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 32px 24px; max-width: 420px; box-shadow: 0 12px 40px rgba(0,0,0,0.5); }}
        h2 {{ margin: 0 0 12px; font-size: 20px; color: #00f2fe; }}
        p {{ color: #a1a1aa; font-size: 14px; line-height: 1.5; margin: 0 0 24px; }}
        .btn {{ display: inline-block; background: linear-gradient(135deg, #7342e2, #00f2fe); color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 999px; font-weight: 700; font-size: 14px; margin: 6px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Video Yuklab Olish</h2>
        <p>Video server orqali tayyorlanmoqda. Telegram botimiz orqali to'g'ridan-to'g'ri va tezkor yuklab olishingiz mumkin.</p>
        <a class="btn" href="https://www.youtube.com/watch?v={video_id}" target="_blank">YouTube da ochish</a>
    </div>
</body>
</html>"""
            return web.Response(text=html, content_type="text/html", status=200, headers={"Access-Control-Allow-Origin": "*"})

        return web.json_response({
            "ok": True,
            "status": "fallback",
            "video_id": video_id,
            "download_url": f"https://www.youtube.com/watch?v={video_id}",
            "message": "Video to'g'ridan-to'g'ri yuklab olinmadi. Telegram botimiz orqali yuqori sifatda yuklab olishingiz mumkin."
        }, status=200, headers={"Access-Control-Allow-Origin": "*"})

    except web.HTTPFound:
        raise
    except BaseException as fatal_err:
        print(f"Top-level handle_api_download_file safe guard: {fatal_err}")
        return web.json_response({
            "ok": True,
            "status": "fallback",
            "video_id": request.query.get("video_id", ""),
            "download_url": f"https://www.youtube.com/watch?v={request.query.get('video_id', '')}",
            "message": "Video tayyorlanmoqda. Telegram bot orqali yuklab olishingiz mumkin."
        }, status=200, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_autopost_create(request):
    """Tanlangan videolarni autopost_tasks ga qo'shish"""
    import json
    try:
        data = await request.json()
        tg_user_id = data.get("tg_user_id")
        video_ids = data.get("video_ids", [])
        
        if not tg_user_id or not video_ids:
            return web.json_response({"error": "Ma'lumot to'liq emas"}, status=400)
            
        tg_user_id = int(tg_user_id)
        from database import get_yt_connection, create_autopost_task
        conn_data = get_yt_connection(tg_user_id)
        
        if not conn_data:
            return web.json_response({"error": "Kanal ulanmagan"}, status=403)
            
        channel_id = conn_data['yt_channel_id']
        
        # Maxsus format: __IDS__:vid1,vid2
        search_query = "__IDS__:" + ",".join(video_ids)
        task_id = create_autopost_task(tg_user_id, channel_id, search_query, "shorts", len(video_ids))

        # ROLE=main: bo'sh tashqi worker qidiradi (yoki RAM limit ichida o'zi bajaradi);
        # javobni HTTP so'rovchiga darhol qaytarish uchun fon vazifasiga o'raymiz.
        if task_id:
            asyncio.create_task(dispatch_or_run_autopost(task_id))
        return web.json_response({"success": True, "task_id": task_id})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_api_reset_db(request):
    """Admin: Bazani tozalash"""
    import json
    import os
    try:
        data = await request.json()
        tg_user_id = int(data.get("tg_user_id", 0))
        admin_secret = request.headers.get("X-Admin-Secret") or data.get("admin_secret", "")
        from config import get_admin_secret
        expected_secret = get_admin_secret()
        
        from config import OWNER_ID
        if tg_user_id != OWNER_ID or not admin_secret or admin_secret != expected_secret:
            return web.json_response({"error": "Ruxsat berilmagan!"}, status=403)
            
        from database import reset_all_data
        success = reset_all_data()
        return web.json_response({"success": success})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


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
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_kyc_page(request):
    """3D Face & ID Biometrik Identifikatsiya sahifasi"""
    from kyc_template import get_kyc_html
    from database import is_user_kyc_verified, get_user_kyc, get_telegram_phone
    user_id = 0
    is_verified = False
    kyc_data = None
    phone = str(request.query.get("phone", "")).strip()
    try:
        user_id = int(request.query.get("user_id", 0))
        if user_id:
            is_verified = is_user_kyc_verified(user_id)
            if is_verified:
                kyc_data = get_user_kyc(user_id)
            if not phone:
                phone = get_telegram_phone(user_id)
        html = get_kyc_html(user_id=user_id, is_verified=is_verified, kyc_data=kyc_data, phone=phone)
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        return web.Response(text=html, content_type="text/html", headers=headers)
    except Exception as e:
        print(f"handle_kyc_page error: {e}")
        try:
            fallback_html = get_kyc_html(user_id=user_id, is_verified=False, kyc_data=None, phone=phone)
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            return web.Response(text=fallback_html, content_type="text/html", headers=headers)
        except Exception as _fe:
            return web.Response(
                text="<!DOCTYPE html><html><body style='background:#080c14;color:#fff;font-family:sans-serif;text-align:center;padding:50px;'>"
                     "<h2>🛡️ 3D Biometrik Identifikatsiya</h2>"
                     "<p>Tizim yangilanmoqda. Iltimos, bir necha daqiqadan so'ng qayta urinib ko'ring.</p>"
                     "</body></html>",
                content_type="text/html"
            )


async def handle_kyc_status(request):
    """Foydalanuvchi KYC holatini tekshirish API"""
    from database import is_user_kyc_verified, get_user_kyc
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"ok": False, "is_verified": False, "message": "user_id kiritilmadi"})
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
        return web.json_response({"ok": False, "is_verified": False, "error": str(e)})


async def handle_kyc_submit(request):
    """3D Yuz va Telefon ma'lumotlarini qabul qilish va tekshirish (Anti-Sybil)"""
    import hashlib
    import json
    from database import check_kyc_duplicate, save_kyc_verification
    
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        phone = str(data.get("phone", "")).strip()
        face_hash = str(data.get("face_hash", "")).strip()
        
        if not user_id:
            return web.json_response({"ok": False, "message": "Foydalanuvchi ID topilmadi!"}, status=400)
        if not phone or len(phone) < 9:
            return web.json_response({"ok": False, "message": "Telefon raqami noto'g'ri kiritilgan!"}, status=400)
        if not face_hash:
            return web.json_response({"ok": False, "message": "3D Yuz skaneri ma'lumotlari topilmadi!"}, status=400)
        
        # Takroriy hisob tekshiruvi (Anti-Sybil Deduplication)
        is_dup, reason = check_kyc_duplicate(passport_hash=None, face_hash=face_hash, phone_number=phone, exclude_tg_user_id=user_id)
        if is_dup:
            return web.json_response({"ok": False, "message": reason}, status=400)
            
        # Saqlash
        save_kyc_verification(user_id, phone, None, face_hash)
        
        # Bot orqali tasdiq xabari yuborish
        if ytbot_instance:
            msg = (
                f"✅ <b>Tabriklaymiz! 3D Biometrik Identifikatsiya muvaffaqiyatli yakunlandi.</b>\n\n"
                f"📱 <b>Telefon:</b> {phone}\n"
                f"🛡️ Anti-Sybil tekshiruvi: <b>Muvaffaqiyatli</b>\n\n"
                f"🚀 Barcha YouTube avtomatizatsiya va xizmatlar siz uchun to'liq ochildi!"
            )
            asyncio.create_task(ytbot_instance.send_message(user_id, msg))
            
        return web.json_response({"ok": True, "message": "Identifikatsiya muvaffaqiyatli tasdiqlandi!"})
    except Exception as e:
        print(f"handle_kyc_submit error: {e}")
        return web.json_response({"ok": False, "message": f"Server xatosi: {str(e)}"}, status=500)



async def handle_tc_manifest(request):
    """TON Connect Manifest JSON taqdim etish"""
    from ton_connect_page import get_ton_manifest
    host = request.headers.get("Host", "localhost")
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    base_url = f"{scheme}://{host}"
    manifest = get_ton_manifest(base_url)
    return web.json_response(manifest, headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache"
    })


async def handle_tonconnect_page(request):
    """TON Connect Telegram Mini App HTML sahifasi"""
    from ton_connect_page import get_ton_connect_html
    from database import get_user_ton_wallet
    user_id = 0
    try:
        user_id = int(request.query.get("user_id", 0))
    except (ValueError, TypeError):
        pass
    
    current_wallet = get_user_ton_wallet(user_id) if user_id else None
    host = request.headers.get("Host", "localhost")
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    base_url = f"{scheme}://{host}"
    html = get_ton_connect_html(user_id=user_id, current_wallet=current_wallet, base_url=base_url)
    return web.Response(text=html, content_type="text/html")


async def handle_api_tonconnect_save(request):
    """Mini App orqali ulangan TON hamyonni saqlash"""
    from database import save_user_ton_wallet, to_user_friendly_address
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        address = str(data.get("address", "")).strip()
        address = to_user_friendly_address(address)
        wallet_name = str(data.get("wallet_name", "TON Wallet")).strip()
        chain = str(data.get("chain", "mainnet")).strip()

        if not user_id:
            return web.json_response({"ok": False, "message": "user_id topilmadi"}, status=400)
        if not address or len(address) < 20:
            return web.json_response({"ok": False, "message": "Noto'g'ri TON hamyon manzili"}, status=400)

        ok = save_user_ton_wallet(user_id, address, wallet_name, chain)
        if not ok:
            return web.json_response({"ok": False, "message": "Bazaga saqlashda xatolik"}, status=500)

        if ytbot_instance:
            masked_addr = address[:6] + "..." + address[-6:] if len(address) > 12 else address
            msg = (
                f"💎 <b>TON Hamyoningiz Muvaffaqiyatli Ulandi!</b>\n\n"
                f"👛 <b>Hamyon:</b> {wallet_name}\n"
                f"📬 <b>Manzil:</b> <code>{address}</code> ({masked_addr})\n"
                f"🌐 <b>Tarmoq:</b> TON {chain.capitalize()}\n\n"
                f"⚡ <i>Endi pul yechish (Cashout) va 3D NFT savdosida ushbu manzil avtomatik ishlatiladi!</i>"
            )
            asyncio.create_task(ytbot_instance.send_message(user_id, msg))

        return web.json_response({"ok": True, "message": "Hamyon muvaffaqiyatli saqlandi!"})
    except Exception as e:
        print(f"handle_api_tonconnect_save error: {e}")
        return web.json_response({"ok": False, "message": str(e)}, status=500)


async def handle_api_tonconnect_disconnect(request):
    """Ulangan TON hamyonni uzish"""
    from database import delete_user_ton_wallet
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"ok": False, "message": "user_id topilmadi"}, status=400)

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
        return web.json_response({"ok": False, "message": str(e)}, status=500)


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
    """NFT muqova rasmini yuborish (CTF / Path Traversal himoyalangan)"""
    raw_filename = request.match_info.get("filename", "").strip()
    clean_name = os.path.basename(raw_filename)
    if not clean_name or ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        return web.Response(text="Noto'g'ri fayl nomi", status=400)

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
    lower_f = clean_name.lower()
    if lower_f.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif lower_f.endswith(".webp"):
        content_type = "image/webp"
    elif lower_f.endswith(".svg"):
        content_type = "image/svg+xml"
    elif lower_f.endswith(".gif"):
        content_type = "image/gif"

    return web.FileResponse(real_path, headers={
        "Content-Type": content_type,
        "Cache-Control": "public, max-age=604800, immutable",
        "Access-Control-Allow-Origin": "*"
    })

_FRAGMENT_IMG_CACHE = {}

async def handle_fragment_image_proxy(request):
    """Fragment CDN dagi NFT rasmini yuklab beruvchi proxy API (CORS va offline brauzerlar uchun)"""
    slug = request.match_info.get("slug", "").strip()
    if not slug:
        return web.Response(status=400, text="slug is required")
        
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
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    _FRAGMENT_IMG_CACHE[slug] = img_bytes
                    return web.Response(
                        body=img_bytes,
                        content_type="image/jpeg",
                        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=604800, immutable"}
                    )
                else:
                    return web.Response(status=resp.status, text="Image not found on Fragment")
    except Exception as e:
        return web.Response(status=500, text=str(e))

async def handle_nft_video(request):
    """NFT 3D video animatsiyasini yuborish (CTF / Path Traversal himoyalangan)"""
    raw_filename = request.match_info.get("filename", "").strip()
    clean_name = os.path.basename(raw_filename)
    if not clean_name or ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        return web.Response(text="Noto'g'ri fayl nomi", status=400)

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

    return web.FileResponse(real_path, headers={
        "Content-Type": "video/mp4",
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
    """Web Dashboard orqali to'langan Stars keysi yutug'ini tekshirish va unboxing natijasi"""
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        from config import OWNER_ID
        if user_id <= 0:
            return web.json_response({"ok": False, "error": "Foydalanuvchi ID talab qilinadi"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

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
            }, headers={"Access-Control-Allow-Origin": "*"})

        # 2. Agar bot egasi (Owner) bo'lsa
        if user_id == OWNER_ID:
            from games_monetization import open_stars_case
            res = open_stars_case(user_id, tier_id)
            return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})

        # Aks holda to'lov tasdiqlanmagan xakerlik / bepul spam urinishi
        return web.json_response({
            "ok": False,
            "error": "To'lov tasdiqlanmadi yoki Stars balansi yetarli emas. Iltimos, so'm balansi yoki rasmiy Stars to'lovi orqali oching."
        }, status=402, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

_TELEGRAM_FILE_CACHE = {}  # { file_id: (content, content_type, timestamp) }
_TG_FILE_CACHE_MAX = 200
_TG_FILE_CACHE_TTL = 3600  # 1 soat

_GIFT_ID_TO_FILE_ID = {
    "5170144170496491616": "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E",  # Cake
    "6028601630662853006": "CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ",  # Champagne
    "5170314324215857265": "CAACAgIAAxUAAWrS2uNt8sIHLaoAAZeEbczG8VU45QAC3iUAAkUg4ErI5hOgFM9DXj0E",  # Bouquet
    "5168043875654172773": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",  # Trophy
    "5170690322832818290": "CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ",  # Ring
    "5170564780938756245": "CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ",  # Rocket
    "5170521118301225164": "CAACAgIAAxUAAWrS2uOdst4ZTcyZTnYZPBO024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ",  # Blue Diamond
    "5170145012310081615": "CAACAgIAAxUAAWrS2uM_EewXTXxghtF9VyKlBMUvAAJ8GwACkoTYS_itxFzPIpm1PQQ",  # Green Star
    "5170250947678437525": "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E",
}

_GIFT_ID_TO_LOCAL_WEBP = {
    "5170144170496491616": "delicious_cake.webp",
    "6028601630662853006": "champagne_bottle.webp",
    "5170314324215857265": "gift_bouquet.webp",
    "5168043875654172773": "star_trophy.webp",
    "5170690322832818290": "diamond_ring.webp",
    "5170564780938756245": "gift_rocket.webp",
    "5170521118301225164": "diamond_ring.webp",
    "5170145012310081615": "gift_star.webp",
    "5170250947678437525": "delicious_cake.webp",
}

async def handle_api_telegram_file(request):
    """Telegramdan file_id orqali faylni (TGS/WEBM/PNG/JPG) yuklab, frontendga uzatuvchi proxy API (RAM LRU kesh va Zero-404 fallback bilan)"""
    file_id = request.match_info.get("file_id", "").strip()
    if not file_id:
        return web.Response(status=400, text="file_id is required")
        
    import time
    import os
    now = time.time()

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=604800, immutable"
    }

    # 1. RAM keshdan tekshirish
    cached = _TELEGRAM_FILE_CACHE.get(file_id)
    if cached and (now - cached[2]) < _TG_FILE_CACHE_TTL:
        return web.Response(
            body=cached[0],
            content_type=cached[1],
            headers=headers
        )

    # 2. Agar numeric gift_id berilgan bo'lsa, uni haqiqiy Telegram sticker file_id ga tarjima qilish
    actual_file_id = _GIFT_ID_TO_FILE_ID.get(file_id, file_id)

    try:
        from config import BOT_TOKEN
        import aiohttp
        import gzip
        token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
        if not token:
            # Token bo'lmasa, darhol lokal assetdan qaytarish
            local_name = _GIFT_ID_TO_LOCAL_WEBP.get(file_id, "delicious_cake.webp")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            lp = os.path.join(base_dir, "nft_assets", local_name)
            if os.path.exists(lp):
                with open(lp, "rb") as f:
                    content = f.read()
                return web.Response(body=content, content_type="image/webp", headers=headers)
            return web.Response(status=500, text="BOT_TOKEN not configured")
            
        async with aiohttp.ClientSession() as session:
            # 1. file_path ni olish
            file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={actual_file_id}"
            async with session.get(file_url, timeout=6) as r1:
                res1 = await r1.json()
                if not res1.get("ok"):
                    # Telegramda topilmasa, kafolatlangan lokal WebP assetdan uzatamiz (Zero 404)
                    local_name = _GIFT_ID_TO_LOCAL_WEBP.get(file_id, "delicious_cake.webp")
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    lp = os.path.join(base_dir, "nft_assets", local_name)
                    if os.path.exists(lp):
                        with open(lp, "rb") as f:
                            content = f.read()
                        _TELEGRAM_FILE_CACHE[file_id] = (content, "image/webp", now)
                        return web.Response(body=content, content_type="image/webp", headers=headers)
                    return web.Response(status=404, text="File not found on Telegram")
                file_path = res1["result"]["file_path"]
                
            # 2. Faylning o'zini yuklab uzatish
            download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            async with session.get(download_url, timeout=12) as r2:
                if r2.status != 200:
                    local_name = _GIFT_ID_TO_LOCAL_WEBP.get(file_id, "delicious_cake.webp")
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    lp = os.path.join(base_dir, "nft_assets", local_name)
                    if os.path.exists(lp):
                        with open(lp, "rb") as f:
                            content = f.read()
                        _TELEGRAM_FILE_CACHE[file_id] = (content, "image/webp", now)
                        return web.Response(body=content, content_type="image/webp", headers=headers)
                    return web.Response(status=502, text="Failed to download from Telegram")
                    
                content = await r2.read()
                
                # Agar TGS (gzipped lottie) bo'lsa decompress qilib toza JSON uzatamiz
                if file_path.endswith(".tgs"):
                    try:
                        content = gzip.decompress(content)
                        content_type = "application/json"
                    except Exception:
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
                    content_type = r2.headers.get("Content-Type", "application/octet-stream")
                    
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
        local_name = _GIFT_ID_TO_LOCAL_WEBP.get(file_id, "delicious_cake.webp")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        lp = os.path.join(base_dir, "nft_assets", local_name)
        if os.path.exists(lp):
            with open(lp, "rb") as f:
                content = f.read()
            return web.Response(body=content, content_type="image/webp", headers=headers)
        return web.Response(status=500, text=f"Proxy error: {e}")

async def handle_api_stars_open_case_uzs(request):
    """Web Dashboard orqali UZS (so'm) balansi bilan keys ochish (Anti-IDOR himoyalangan)"""
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi (Ruxsat berilmadi)!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
        from games_monetization import open_stars_case_with_uzs, process_pending_gifts_batch
        res = open_stars_case_with_uzs(user_id, tier_id)
        if res.get("ok"):
            import asyncio
            from config import BOT_TOKEN
            asyncio.create_task(process_pending_gifts_batch(bot_token=BOT_TOKEN, limit=5))
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_create_invoice(request):
    """Telegram Stars to'lovi uchun Telegram createInvoiceLink yaratish"""
    try:
        import time as _t
        data = await request.json()
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        user_id = int(data.get("user_id", 0))
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
                data = await resp.json()
                if data.get("ok"):
                    return web.json_response({"ok": True, "invoice_link": data.get("result")}, headers={"Access-Control-Allow-Origin": "*"})
                return web.json_response({"ok": False, "error": data.get("description", "Invoice yaratilmadi")}, status=400, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


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
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        host_id = auth_uid
        host_name = str(data.get("user_name", "")).strip()
        tier_id = str(data.get("tier_id", "tier_1")).strip()
        import database
        if database.is_user_banned(host_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
        from games_monetization import create_case_battle
        res = create_case_battle(host_id, host_name, tier_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_pvp_join(request):
    """PvP jangga qo'shilish va g'olibni aniqlash (Anti-IDOR)"""
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        guest_id = auth_uid
        battle_id = str(data.get("battle_id", "")).strip()
        guest_name = str(data.get("user_name", "")).strip()
        import database
        if database.is_user_banned(guest_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
        from games_monetization import join_and_resolve_battle
        res = join_and_resolve_battle(battle_id, guest_id, guest_name)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_pvp_cancel(request):
    """PvP keys jangini bekor qilish va hostga mablag'ni qaytarish (Anti-IDOR)"""
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        host_id = auth_uid
        battle_id = str(data.get("battle_id", "")).strip()
        from games_monetization import cancel_case_battle
        res = cancel_case_battle(battle_id, host_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

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
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_ton_rate(request):
    """Real-time live TON va UZS kursini olish"""
    try:
        from telegram_marketplace_service import get_sync_live_ton_rate
        rate = get_sync_live_ton_rate()
        return web.json_response({"ok": True, "rate": rate}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_user_inventory(request):
    """Foydalanuvchining shaxsiy yutib olgan sovg'alari va NFT lari"""
    try:
        user_id = int(request.query.get("user_id", 0) or request.query.get("tg_user_id", 0))
        if user_id <= 0:
            return web.json_response({"ok": True, "gifts": []}, headers={"Access-Control-Allow-Origin": "*"})
        import database
        raw_gifts = database.get_user_gift_history(user_id, limit=50)
        formatted = []
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync, get_sync_live_ton_rate
            
        market_stock = fetch_live_marketplace_stock_sync()
        rate = get_sync_live_ton_rate()
        ton_uzs = rate.get("ton_uzs", 15700.0)

        # Standart sovg'alar rasmlari xaritasi (Zero mockups, zero emojis)
        STANDARD_GIFT_IMAGES = {
            "cake": "/api/nft/image/delicious_cake.webp",
            "star": "/api/nft/image/gift_star.webp",
            "teddy": "https://nft.fragment.com/gift/toybear-7605.medium.jpg",
            "bouquet": "/api/nft/image/gift_bouquet.webp",
            "champagne": "/api/nft/image/champagne_bottle.webp",
            "diamond_ring": "/api/nft/image/diamond_ring.webp",
            "trophy": "/api/nft/image/star_trophy.webp",
            "rocket": "/api/nft/image/gift_rocket.webp",
            "cap": "/api/nft/image/durov_cap.webp",
            "plush": "/api/nft/image/plush_pepe.webp",
            "crown": "/api/nft/image/royal_crown.webp",
            "package": "/api/nft/image/delicious_cake.webp"
        }

        for g_idx, g in enumerate(raw_gifts):
            stars = int(g.get("prize_stars") or 25)
            p_name = g.get("prize_name") or "Telegram Sovg'a"
            p_lower = p_name.lower()
            icon = "package"
            if "cake" in p_lower: icon = "cake"
            elif "star" in p_lower: icon = "star"
            elif "teddy" in p_lower or "bear" in p_lower: icon = "teddy"
            elif "bouquet" in p_lower or "flower" in p_lower: icon = "bouquet"
            elif "champagne" in p_lower: icon = "champagne"
            elif "ring" in p_lower or "diamond" in p_lower: icon = "diamond_ring"
            elif "trophy" in p_lower: icon = "trophy"
            elif "rocket" in p_lower: icon = "rocket"
            elif "cap" in p_lower: icon = "cap"
            elif "plush" in p_lower or "pepe" in p_lower: icon = "plush"
            elif "crown" in p_lower: icon = "crown"
            
            # Haqiqiy NFT tekshiruvi: faqat foydalanuvchi haqiqatan NFT yutgan bo'lsa
            is_nft = bool(g.get("is_nft") or "nft" in p_lower or "collectible" in p_lower or (stars >= 1000 and "telegram sovg" not in p_lower))
            rarity = "legendary" if (stars >= 500 or is_nft) else ("rare" if stars >= 50 else "common")

            image_url = g.get("image_url") or ""
            backdrop = "transparent"
            matched_edition = g.get("edition") or ""

            if is_nft and market_stock:
                matched_item = None
                for it in market_stock:
                    if it["collection"].lower() in p_lower or it["name"].lower() in p_lower:
                        matched_item = it
                        break
                if matched_item:
                    if not image_url: image_url = matched_item["image_url"]
                    if not matched_edition: matched_edition = matched_item.get("edition", "")
                    backdrop = matched_item.get("backdrop", backdrop)
            
            if not is_nft:
                # Agar generic "Telegram Sovg'asi" bo'lsa, har birini alohida chiroyli haqiqiy sovg'a sifatida ko'rsatish
                if "telegram sovg" in p_lower or p_name == "Telegram Gift" or icon == "package":
                    distinct_gifts = [
                        ("Delicious Cake", "cake", "/api/nft/image/delicious_cake.webp", 15),
                        ("Green Star", "star", "/api/nft/image/gift_star.webp", 25),
                        ("Teddy Bear", "teddy", "https://nft.fragment.com/gift/toybear-7605.medium.jpg", 50),
                        ("Bouquet of Flowers", "bouquet", "/api/nft/image/gift_bouquet.webp", 50)
                    ]
                    chosen = distinct_gifts[g_idx % len(distinct_gifts)]
                    p_name, icon, image_url = chosen[0], chosen[1], chosen[2]
                    stars = chosen[3]
            
            if not image_url:
                image_url = STANDARD_GIFT_IMAGES.get(icon, "/api/nft/image/delicious_cake.webp")

            formatted.append({
                "id": g.get("id"),
                "prize_name": p_name,
                "prize_stars": stars,
                "rarity": rarity,
                "icon": icon,
                "is_nft": is_nft,
                "image_url": image_url,
                "backdrop": backdrop,
                "edition": matched_edition,
                "price_uzs": stars * 400,
                "price_ton": round((stars * 400) / max(1.0, ton_uzs), 2),
                "status": g.get("status", "pending"),
                "date": str(g.get("created_at") or "Yaqinda")[:10]
            })
        return web.json_response({"ok": True, "gifts": formatted, "rate": rate}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

_NFT_ANIMATION_CACHE = {}

_STANDARD_GIFT_SLUGS_TO_FILE_ID = {
    "golden-trophy": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",
    "star-trophy": "CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ",
    "delicious-cake": "CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E",
    "champagne-bottle": "CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ",
    "bouquet-flowers": "CAACAgIAAxUAAWrS2uNt8sIHLaoAAZeEbczG8VU45QAC3iUAAkUg4ErI5hOgFM9DXj0E",
    "diamond-ring": "CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ",
    "space-rocket": "CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ",
    "blue-diamond": "CAACAgIAAxUAAWrS2uOdst4ZTcyZTnYZPBO024_GAAIbHgACQEjwS6XKX-OK2k1MPQQ",
}

EMPTY_LOTTIE_JSON = b'{"v":"5.5.7","fr":60,"ip":0,"op":60,"w":100,"h":100,"nm":"empty","ddd":0,"assets":[],"layers":[]}'

async def handle_api_nft_animation(request):
    """
    Fragment Telegram Gift NFT larining va standart Telegram sovg'alarining rasmiy .tgs Lottie
    vektor animatsiyasini decompress qilib, toza JSON sifatida qaytaradi (RAM kesh & Zero-Crash fallback).
    """
    slug = request.match_info.get("slug", "").strip()
    if not slug:
        return web.Response(status=400, text="slug is required")
        
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=604800, immutable"
    }

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
            import gzip
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
                                    raw = await r2.read()
                                    try:
                                        decompressed = gzip.decompress(raw)
                                    except Exception:
                                        decompressed = raw
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
        import gzip
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    raw_data = await resp.read()
                    try:
                        decompressed = gzip.decompress(raw_data)
                    except Exception:
                        decompressed = raw_data
                    _NFT_ANIMATION_CACHE[slug] = decompressed
                    return web.Response(
                        body=decompressed,
                        content_type="application/json",
                        headers=headers
                    )
                else:
                    # lit-html insertBefore xatoligining oldini olish uchun bo'sh lottie JSON qaytaramiz (Zero 404 crash)
                    return web.Response(
                        body=EMPTY_LOTTIE_JSON,
                        content_type="application/json",
                        headers=headers
                    )
    except Exception as e:
        return web.Response(
            body=EMPTY_LOTTIE_JSON,
            content_type="application/json",
            headers=headers
        )

async def handle_api_stars_upgrader_inventory(request):
    """Upgrader uchun mavjud bo'lgan barcha darajadagi sovg'alar va NFT lar (Cheksiz to'liq katalog)"""
    try:
        from database import get_available_gift_inventory
        db_inventory = get_available_gift_inventory(limit=50) or []
        
        # Barcha narx toifalaridagi rasmiy sovg'alar va NFT lar (15 dan 6,000 Stars gacha)
        full_catalog = [
            {"id": "up_1", "stars": 15, "name": "Delicious Cake", "icon": "cake", "file_type": "webp", "image_url": "/api/nft/image/delicious_cake.webp", "is_nft": False, "rarity": "common"},
            {"id": "up_2", "stars": 25, "name": "Green Star", "icon": "star", "file_type": "webp", "image_url": "/api/nft/image/gift_star.webp", "is_nft": False, "rarity": "common"},
            {"id": "up_3", "stars": 50, "name": "Teddy Bear", "icon": "teddy", "file_type": "webp", "image_url": "https://nft.fragment.com/gift/toybear-7605.medium.jpg", "is_nft": False, "rarity": "common"},
            {"id": "up_4", "stars": 50, "name": "Bouquet of Flowers", "icon": "bouquet", "file_type": "webp", "image_url": "/api/nft/image/gift_bouquet.webp", "is_nft": False, "rarity": "common"},
            {"id": "up_5", "stars": 75, "name": "Champagne Bottle", "icon": "champagne", "file_type": "webp", "image_url": "/api/nft/image/champagne_bottle.webp", "is_nft": False, "rarity": "rare"},
            {"id": "up_6", "stars": 100, "name": "Diamond Ring", "icon": "diamond_ring", "file_type": "webp", "image_url": "/api/nft/image/diamond_ring.webp", "is_nft": False, "rarity": "rare"},
            {"id": "up_7", "stars": 150, "name": "Desk Calendar NFT", "icon": "calendar", "file_type": "webp", "image_url": "/api/nft/image/desk_calendar.webp", "is_nft": True, "rarity": "rare"},
            {"id": "up_8", "stars": 250, "name": "Magic Potion NFT", "icon": "potion", "file_type": "webp", "image_url": "/api/nft/image/magic_potion.webp", "is_nft": True, "rarity": "rare"},
            {"id": "up_9", "stars": 500, "name": "Space Rocket", "icon": "rocket", "file_type": "webp", "image_url": "/api/nft/image/gift_rocket.webp", "is_nft": False, "rarity": "legendary"},
            {"id": "up_10", "stars": 550, "name": "Swiss Watch NFT", "icon": "watch", "file_type": "webp", "image_url": "/api/nft/image/swiss_watch.webp", "is_nft": True, "rarity": "legendary"},
            {"id": "up_11", "stars": 750, "name": "Durov's Cap NFT", "icon": "cap", "file_type": "webp", "image_url": "/api/nft/image/durov_cap.webp", "is_nft": True, "rarity": "legendary"},
            {"id": "up_12", "stars": 1000, "name": "Star Trophy NFT", "icon": "trophy", "file_type": "webp", "image_url": "/api/nft/image/star_trophy.webp", "is_nft": True, "rarity": "legendary"},
            {"id": "up_13", "stars": 1200, "name": "Heart Locket NFT", "icon": "locket", "file_type": "webp", "image_url": "/api/nft/image/heart_locket.webp", "is_nft": True, "rarity": "legendary"},
            {"id": "up_14", "stars": 1500, "name": "Plush Pepe NFT", "icon": "plush", "file_type": "webp", "image_url": "/api/nft/image/plush_pepe.webp", "is_nft": True, "rarity": "legendary"},
            {"id": "up_15", "stars": 2500, "name": "B-Day Candle NFT", "icon": "candle", "file_type": "webp", "image_url": "/api/nft/image/bday_candle.webp", "is_nft": True, "rarity": "legendary"},
            {"id": "up_16", "stars": 3500, "name": "Snoop Cigar NFT", "icon": "cigar", "file_type": "webp", "image_url": "/api/nft/image/snoop_cigar.webp", "is_nft": True, "rarity": "transcendent"},
            {"id": "up_17", "stars": 5000, "name": "Vintage Cigar NFT", "icon": "cigar", "file_type": "webp", "image_url": "/api/nft/image/vintage_cigar.webp", "is_nft": True, "rarity": "transcendent"},
            {"id": "up_18", "stars": 6000, "name": "Golden Dragon NFT", "icon": "dragon", "file_type": "webp", "image_url": "/api/nft/image/golden_dragon.webp", "is_nft": True, "rarity": "transcendent"}
        ]
        
        combined = []
        for it in db_inventory:
            g_name = str(it.get("gift_name") or it.get("name") or "")
            g_icon = str(it.get("icon") or "")
            img_url = it.get("image_url")
            if not img_url:
                if "champagne" in g_name.lower() or g_icon == "champagne":
                    img_url = "/api/nft/image/champagne_bottle.webp"
                elif "bouquet" in g_name.lower() or g_icon == "bouquet":
                    img_url = "/api/nft/image/gift_bouquet.webp"
                elif "ring" in g_name.lower() or "diamond" in g_name.lower() or g_icon in ("diamond_ring", "ring"):
                    img_url = "/api/nft/image/diamond_ring.webp"
                elif "trophy" in g_name.lower() or g_icon == "trophy":
                    img_url = "/api/nft/image/star_trophy.webp"
                elif "rocket" in g_name.lower() or g_icon == "rocket":
                    img_url = "/api/nft/image/gift_rocket.webp"
                elif "star" in g_name.lower() or g_icon == "star":
                    img_url = "/api/nft/image/gift_star.webp"
                else:
                    img_url = "/api/nft/image/delicious_cake.webp"
                it["image_url"] = img_url
            combined.append(it)

        existing_names = {str(it.get("gift_name") or it.get("name")).lower() for it in combined}
        for cat_item in full_catalog:
            if cat_item["name"].lower() not in existing_names:
                combined.append({
                    "id": cat_item["id"],
                    "gift_name": cat_item["name"],
                    "name": cat_item["name"],
                    "stars_value": cat_item["stars"],
                    "stars": cat_item["stars"],
                    "icon": cat_item["icon"],
                    "file_type": cat_item["file_type"],
                    "image_url": cat_item["image_url"],
                    "is_nft": cat_item["is_nft"],
                    "rarity": cat_item["rarity"]
                })
        return web.json_response({"ok": True, "inventory": combined}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_marketplace_buy_invoice(request):
    """
    NFT ni Telegram Stars orqali sotib olish uchun rasmiy Telegram createInvoiceLink yaratadi.
    """
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        slug = str(data.get("slug", "")).strip()
        
        if user_id <= 0 or not slug:
            return web.json_response({"ok": False, "error": "user_id va slug talab qilinadi"}, status=400, headers={"Access-Control-Allow-Origin": "*"})
            
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
            
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync, is_nft_live_on_sale, remove_nft_from_cache
        if not is_nft_live_on_sale(slug):
            remove_nft_from_cache(slug)
            return web.json_response({
                "ok": False,
                "error": "Ushbu NFT yaqindagina Fragmentda sotilgan yoki ayni paytda mavjud emas! Sahifa yangilandi, iltimos boshqasini tanlang."
            }, status=400, headers={"Access-Control-Allow-Origin": "*"})
            
        stock = fetch_live_marketplace_stock_sync()
        target = None
        for it in stock:
            if it.get("slug") == slug or it.get("id") == slug:
                target = it
                break
                
        if not target:
            return web.json_response({"ok": False, "error": "NFT topilmadi yoki sotilgan!"}, status=404, headers={"Access-Control-Allow-Origin": "*"})
            
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
                    }, headers={"Access-Control-Allow-Origin": "*"})
                else:
                    return web.json_response({
                        "ok": False,
                        "error": res_data.get("description", "Invoice yaratib bo'lmadi")
                    }, status=400, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_stars_marketplace_buy(request):
    """
    Fragment Telegram Gift NFT ni to'g'ridan-to'g'ri bot orqali so'm balansi bilan sotib olish (Anti-IDOR).
    """
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid
        slug = str(data.get("slug", "")).strip()
        
        if not slug:
            return web.json_response({"ok": False, "error": "slug talab qilinadi!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})
            
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
            
        from telegram_marketplace_service import fetch_live_marketplace_stock_sync, get_sync_live_ton_rate
        market_stock = fetch_live_marketplace_stock_sync()
        target_item = None
        for it in market_stock:
            if it.get("slug") == slug or it.get("id") == slug:
                target_item = it
                break
                
        if not target_item:
            return web.json_response({"ok": False, "error": "Tanlangan NFT topilmadi yoki allaqachon sotilgan!"}, status=404, headers={"Access-Control-Allow-Origin": "*"})
            
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
            }, status=400, headers={"Access-Control-Allow-Origin": "*"})
            
        if not database.deduct_user_balance(user_id, price_uzs):
            return web.json_response({"ok": False, "error": "Mablag'ni hisobdan yechishda xatolik yuz berdi!"}, status=500, headers={"Access-Control-Allow-Origin": "*"})
            
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
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_upgrader(request):
    """Nazoratli Upgrader aylanishi (Anti-IDOR)"""
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
        item_stars = int(data.get("item_stars", 15))
        target_stars = int(data.get("target_stars", 50))
        target_name = str(data.get("target_name", "Gift")).strip()
        target_icon = str(data.get("target_icon", "package")).strip()
        target_inventory_id = data.get("target_inventory_id")
        if target_inventory_id is not None:
            try:
                target_inventory_id = int(target_inventory_id)
            except Exception:
                target_inventory_id = None
        from games_monetization import execute_upgrade_roll
        res = execute_upgrade_roll(user_id, item_stars, target_stars, target_name, target_icon, target_inventory_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_daily_streak(request):
    """Foydalanuvchi kunlik streak holatini olish"""
    try:
        user_id = int(request.query.get("user_id", 0))
        from games_monetization import get_user_streak
        res = get_user_streak(user_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def handle_api_stars_daily_claim(request):
    """Kunlik bepul xizmat sovg'asini olish (Anti-IDOR)"""
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
        from games_monetization import claim_daily_streak
        res = claim_daily_streak(user_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

_SCRATCH_COOLDOWN = {}

async def handle_api_stars_scratch_card(request):
    """Tirnaladigan omad chiptasini o'ynash (1,000 UZS / 3 soniya cheklov) yoki holatini olish"""
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
            }, headers={"Access-Control-Allow-Origin": "*"})

        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id") or data.get("tg_user_id") or 0)
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid

        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

        # Rate-limiting: 3 soniyalik cooldown
        import time as _time
        now = _time.time()
        last_played = _SCRATCH_COOLDOWN.get(user_id, 0)
        if now - last_played < 3.0:
            return web.json_response({"ok": False, "error": "Iltimos, har bir urinish orasida 3 soniya kuting!"}, status=429, headers={"Access-Control-Allow-Origin": "*"})

        # Balans tekshirish va 1,000 so'm yechish
        bal = database.get_user_balance(user_id)
        TICKET_PRICE = 1000
        if bal < TICKET_PRICE:
            return web.json_response({
                "ok": False,
                "error": f"Balansingiz yetarli emas! Chipta narxi: {TICKET_PRICE:,} so'm. Balansingiz: {bal:,} so'm."
            }, status=400, headers={"Access-Control-Allow-Origin": "*"})

        database.deduct_user_balance(user_id, TICKET_PRICE)
        _SCRATCH_COOLDOWN[user_id] = now

        from games_monetization import play_scratch_card
        res = play_scratch_card(user_id)
        res["new_balance"] = database.get_user_balance(user_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

handle_api_stars_scratch_play = handle_api_stars_scratch_card

async def handle_api_stars_redeem(request):
    """Yutuqlarni CapCut Pro yoki AI xizmatlariga almashtirish (Anti-IDOR)"""
    try:
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"ok": False, "error": "Autentifikatsiya talab qilinadi!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid
        import database
        if database.is_user_banned(user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})
        service_id = str(data.get("service_id", "")).strip()
        from games_monetization import redeem_creator_service
        res = redeem_creator_service(user_id, service_id)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


# ==================== VENTEBOT RESELLER API HANDLERS ====================

async def handle_api_reseller_products(request):
    """VenteBot raqamli tovarlar katalogi (keshlangan, so'mdagi narxlar bilan)"""
    try:
        from ventebot_service import ventebot_service
        lang = request.query.get("lang", "uz")
        force = request.query.get("refresh", "0") in ("1", "true")
        res = await ventebot_service.get_products(lang=lang, force_refresh=force)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_reseller_quote(request):
    """VenteBot tovar narxini hisoblab berish (so'm va USD da)"""
    try:
        from ventebot_service import ventebot_service
        data = await request.json()
        product_id = int(data.get("product_id", 0))
        qty = int(data.get("quantity", 1))
        res = await ventebot_service.get_quote(product_id=product_id, quantity=qty)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_reseller_buy(request):
    """Foydalanuvchi so'm balansidan xarid qilish va VenteBot ga buyurtma yuborish (Anti-IDOR)"""
    try:
        from ventebot_service import ventebot_service
        data = await request.json()
        auth_uid = get_authenticated_user_id(request, data)
        target_uid = int(data.get("user_id", 0))
        if not auth_uid or (target_uid > 0 and auth_uid != target_uid):
            return web.json_response({"success": False, "message": "Autentifikatsiya talab qilinadi (Ruxsat berilmadi)!"}, status=401, headers={"Access-Control-Allow-Origin": "*"})
        user_id = auth_uid
        product_id = int(data.get("product_id", 0))
        qty = int(data.get("quantity", 1))
        activation_identifier = str(data.get("activation_identifier", "")).strip()

        if user_id <= 0 or product_id <= 0:
            return web.json_response({"success": False, "message": "user_id va product_id kiritilishi shart"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        if qty <= 0:
            return web.json_response({"success": False, "message": "Miqdor kamida 1 ta bo'lishi kerak"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        res = await ventebot_service.buy_product_with_uzs(
            tg_user_id=user_id,
            product_id=product_id,
            quantity=qty,
            activation_identifier=activation_identifier,
        )
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_reseller_my_orders(request):
    """Foydalanuvchining avvalgi xaridlari ro'yxati"""
    try:
        from database import get_user_ventebot_orders
        user_id = int(request.query.get("user_id", 0))
        if user_id <= 0:
            return web.json_response({"success": False, "orders": []}, headers={"Access-Control-Allow-Origin": "*"})
        orders = get_user_ventebot_orders(user_id)
        for o in orders:
            if "created_at" in o and hasattr(o["created_at"], "isoformat"):
                o["created_at"] = o["created_at"].isoformat()
        return web.json_response({"success": True, "orders": orders}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_reseller_admin_wallet(request):
    """Admin uchun VenteBot hamyon balansi va ma'lumotlari"""
    try:
        from ventebot_service import ventebot_service
        from config import OWNER_ID
        secret = request.headers.get("X-Admin-Secret") or request.query.get("secret")
        user_id = int(request.query.get("user_id", 0))
        from config import get_admin_secret
        expected_secret = get_admin_secret()
        
        is_admin = bool(secret and expected_secret and secret == expected_secret)
        if not is_admin and user_id and user_id == OWNER_ID:
            auth_header = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
            if auth_header and auth_header in _AUTH_TOKENS and _AUTH_TOKENS[auth_header].get("tg_user_id") == OWNER_ID:
                is_admin = True

        if not is_admin:
            return web.json_response({"success": False, "message": "Ruxsat berilmadi (Admin ruxsati zarur)"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

        force = request.query.get("refresh", "0") in ("1", "true")
        me = await ventebot_service.get_me(force_refresh=force)
        return web.json_response(me, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


# ==================== RATE LIMITING & SECURITY MIDDLEWARE ====================
_IP_RATE_LIMITS = {}      # { ip: [timestamp, ...] }
_SENSITIVE_IP_LIMITS = {} # { ip: [timestamp, ...] }

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

    # Test yoki ichki chaqiruvlar uchun
    test_auth = request.headers.get("X-Test-Auth") or request.headers.get("X-Internal-Secret")
    if test_auth and expected_secret and test_auth == expected_secret:
        if data and isinstance(data, dict):
            return int(data.get("user_id") or data.get("tg_user_id") or 0)
        return int(request.query.get("user_id") or request.query.get("tg_user_id") or 0)

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
            from urllib.parse import parse_qsl
            import hmac, hashlib, json
            btoken = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
            if btoken:
                parsed = dict(parse_qsl(raw_init_data, keep_blank_values=True))
                if "hash" in parsed:
                    received_hash = parsed.pop("hash")
                    auth_date = int(parsed.get("auth_date", 0))
                    now = time.time()
                    if 0 < auth_date <= now + 60 and (now - auth_date <= 86400):
                        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
                        secret_key = hmac.new(b"WebAppData", btoken.encode("utf-8"), hashlib.sha256).digest()
                        calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
                        if hmac.compare_digest(calc_hash.lower(), received_hash.lower()):
                            user_obj = json.loads(parsed.get("user", "{}"))
                            return int(user_obj.get("id", 0))
        except Exception:
            pass

    return 0

@web.middleware
def _add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if response.content_type == "text/html":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:; "
            "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org telegram:;"
        )
    return response

@web.middleware
async def security_and_rate_limit_middleware(request, handler):
    # 1. HTTP Method Guard (Block dangerous/unsupported methods)
    if request.method in ("TRACE", "TRACK", "CONNECT"):
        return _add_security_headers(web.Response(status=405, text="Method Not Allowed"))

    # 2. Extract Real Client IP (handles proxies like Render / Cloudflare)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        peername = request.transport.get_extra_info('peername')
        client_ip = peername[0] if peername else "unknown"

    import time
    now = time.time()
    t_start = time.perf_counter()
    path = request.path.rstrip("/")

    from telemetry_service import get_dynamic_config, record_api_call

    # 3. Sensitive Endpoints Strict Rate Limit (OTP Request & Verification)
    if path in ("/api/auth/request-otp", "/api/auth/request_otp"):
        ip_history = _SENSITIVE_IP_LIMITS.setdefault(client_ip, [])
        otp_win = float(get_dynamic_config("otp_rate_limit_window", 120))
        otp_max = int(get_dynamic_config("otp_rate_limit_max", 3))
        _SENSITIVE_IP_LIMITS[client_ip] = [t for t in ip_history if now - t < otp_win]
        if len(_SENSITIVE_IP_LIMITS[client_ip]) >= otp_max:
            return _add_security_headers(web.json_response({
                "ok": False,
                "error": f"Juda ko'p so'rov yuborildi! Iltimos {int(otp_win)} soniya kuting."
            }, status=429, headers={"Retry-After": str(int(otp_win)), "Access-Control-Allow-Origin": "*"}))
        _SENSITIVE_IP_LIMITS[client_ip].append(now)

    # 4. Global Anti-DoS Rate Limiting (Dynamic configurable burst and minute windows)
    if not path.startswith(("/static", "/favicon.ico")):
        ip_hits = _IP_RATE_LIMITS.setdefault(client_ip, [])
        _IP_RATE_LIMITS[client_ip] = [t for t in ip_hits if now - t < 60]
        burst_win = float(get_dynamic_config("dos_burst_window", 2))
        burst_max = int(get_dynamic_config("dos_burst_max", 30))
        min_max = int(get_dynamic_config("dos_minute_max", 90))
        recent_burst = [t for t in _IP_RATE_LIMITS[client_ip] if now - t < burst_win]
        if len(recent_burst) > burst_max or len(_IP_RATE_LIMITS[client_ip]) > min_max:
            return _add_security_headers(web.json_response({
                "ok": False,
                "error": "Too Many Requests (DoS protection active). Iltimos bir oz kuting."
            }, status=429, headers={"Retry-After": "5", "Access-Control-Allow-Origin": "*"}))
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
        return _add_security_headers(web.json_response({"ok": False, "error": "Server ichki xatoligi yuz berdi"}, status=500, headers={"Access-Control-Allow-Origin": "*"}))
    finally:
        latency_ms = (time.perf_counter() - t_start) * 1000.0
        record_api_call(request.method, path or "/", status_code, latency_ms, client_ip)

    # 6. Attach OWASP Security Headers
    return _add_security_headers(response)


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

    # 1. Kriptografik HMAC-SHA256 imzoli tokenni tekshirish (Cookie yoki Header)
    token_candidates = [
        request.cookies.get("cf_adm_sig"),
        request.headers.get("X-Admin-Signature"),
        request.headers.get("Authorization", "").replace("Bearer ", "").strip(),
        request.query.get("admin_sig")
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
    resp.set_cookie("cf_adm_sig", signed_token, max_age=12 * 3600, path="/", samesite="Lax", httponly=True)
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

    peer_ip = request.remote or "unknown"
    now = time.time()

    # Rate limiting: 10 daqiqada 5 ta muvaffaqiyatsiz urinishdan keyin bloklash
    recent_fails = [t for t in _ADMIN_VERIFY_FAILURES.get(peer_ip, []) if now - t < 600]
    _ADMIN_VERIFY_FAILURES[peer_ip] = recent_fails
    if len(recent_fails) >= 5:
        return web.json_response({
            "ok": False,
            "error": "Ko'p xato urinishlar qilindi! Xavfsizlik yuzasidan 10 daqiqaga bloklandingiz."
        }, status=429, headers={"Access-Control-Allow-Origin": "*"})

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
            }, status=403, headers={"Access-Control-Allow-Origin": "*"})

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
            }, status=403, headers={"Access-Control-Allow-Origin": "*"})

        # Muvaffaqiyatli kirish - xatoliklar sonini tozalash
        _ADMIN_VERIFY_FAILURES.pop(peer_ip, None)

        from crypto_auth import generate_signed_admin_token
        # Xavfsiz 12 soatlik HMAC-SHA256 sessiya tokeni
        signed_token = generate_signed_admin_token(tg_user_id=6735799833, ttl_seconds=12 * 3600)

        resp = web.json_response({
            "ok": True,
            "message": "Admin ruxsati muvaffaqiyatli tasdiqlandi",
            "token": signed_token
        }, headers={"Access-Control-Allow-Origin": "*"})

        # Xavfsiz SameSite=Lax HttpOnly cookie lar o'rnatish
        resp.set_cookie("cf_adm_sig", signed_token, max_age=12 * 3600, path="/", samesite="Lax", httponly=True)
        resp.del_cookie("cf_auth_owner", path="/")
        resp.del_cookie("admin_key", path="/")

        return resp
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


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
        return web.json_response({"ok": False, "error": "Ruxsat berilmadi (Admin kaliti talab qilinadi)"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

    from telemetry_service import get_telemetry_snapshot
    snapshot = get_telemetry_snapshot(request.app)
    return web.json_response(snapshot, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_telemetry_config(request):
    """Admin-only dynamic config setter (TTL va DoS parametrlarini yangilash)"""
    if not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat berilmadi"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

    try:
        body = await request.json()
        from telemetry_service import update_dynamic_config
        updated = update_dynamic_config(body)
        return web.json_response({"ok": True, "config": updated}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_telemetry_purge(request):
    """Admin-only cache purge trigger"""
    if not is_admin_request(request):
        return web.json_response({"ok": False, "error": "Ruxsat berilmadi"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

    try:
        body = await request.json()
        category = body.get("category", "all")
        from telemetry_service import purge_cache
        res = purge_cache(category)
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400, headers={"Access-Control-Allow-Origin": "*"})


# ==================== WEB DASHBOARD OTP & WEBAPP AUTH ====================
_LOGIN_OTPS = {}  # { tg_user_id: { "otp": "123456", "expires_at": float, "cooldown_until": float, "attempts": int } }
_AUTH_TOKENS = {} # { token: { "tg_user_id": int, "created_at": float } }

async def handle_api_auth_request_otp(request):
    """Foydalanuvchi Telegram ID kiritganda 6-raqamli OTP generatsiya qilib Telegramga yuborish"""
    try:
        import time, random, aiohttp
        data = await request.json()
        raw_uid = data.get("tg_user_id")
        if not raw_uid:
            return web.json_response({"ok": False, "error": "Telegram User ID kiritilishi shart!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        try:
            tg_user_id = int(raw_uid)
            if tg_user_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return web.json_response({"ok": False, "error": "Telegram User ID musbat son bo'lishi kerak!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        now = time.time()
        prev = _LOGIN_OTPS.get(tg_user_id)
        if prev and now < prev.get("cooldown_until", 0):
            wait_sec = int(prev.get("cooldown_until", 0) - now)
            return web.json_response({"ok": False, "error": f"Iltimos {wait_sec} soniyadan keyin qayta urinib ko'ring!"}, status=429, headers={"Access-Control-Allow-Origin": "*"})

        otp_code = f"{random.randint(100000, 999999)}"
        _LOGIN_OTPS[tg_user_id] = {
            "otp": otp_code,
            "expires_at": now + 300, # 5 daqiqa
            "cooldown_until": now + 30, # 30 soniya cooldown
            "attempts": 0
        }

        from config import BOT_TOKEN
        token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
        if not token:
            return web.json_response({"ok": False, "error": "BOT_TOKEN sozlanmagan!"}, status=500, headers={"Access-Control-Allow-Origin": "*"})

        web_base_url = os.getenv("WEB_URL", "https://botclient-d1jn.onrender.com").rstrip("/")
        one_click_url = f"{web_base_url}/?tg_user_id={tg_user_id}&otp={otp_code}"
        bot_username = os.getenv("BOT_USERNAME", "AutoReplyBot").replace("@", "")

        msg_text = (
            f"🔐 <b>CreatorFlow Web Dashboard</b>\n\n"
            f"Sizning bir martalik kirish kodingiz:\n"
            f"👉 <code>{otp_code}</code> 👈\n\n"
            f"⏳ Ushbu kod <b>5 daqiqa</b> davomida amal qiladi.\n"
            f"Xavfsizlik maqsadida uni begonalarga bermang!\n\n"
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
                    return web.json_response({
                        "ok": True,
                        "message": "Tasdiqlash kodi Telegram botingizga yuborildi!",
                        "tg_user_id": tg_user_id
                    }, headers={"Access-Control-Allow-Origin": "*"})
                else:
                    err_desc = resp_data.get("description", "")
                    if "blocked" in err_desc.lower() or "chat not found" in err_desc.lower():
                        user_msg = f"Telegram botimizga (@{bot_username}) avval /start yuboring, so'ngra kodni so'rang!"
                    else:
                        user_msg = f"Telegramga xabar yuborishda xatolik: {err_desc}"
                    return web.json_response({"ok": False, "error": user_msg}, status=400, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"handle_api_auth_request_otp error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_auth_verify_otp(request):
    """6-raqamli OTP kodni tekshirish va sessiya tokenini berish"""
    try:
        import time, secrets
        data = await request.json()
        raw_uid = data.get("tg_user_id")
        raw_otp = str(data.get("otp", "")).strip()

        if not raw_uid or not raw_otp:
            return web.json_response({"ok": False, "error": "Telegram ID va tasdiqlash kodi talab qilinadi!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        tg_user_id = int(raw_uid)
        session = _LOGIN_OTPS.get(tg_user_id)
        if not session:
            return web.json_response({"ok": False, "error": "Tasdiqlash kodi so'ralmagan yoki muddati o'tgan! Qaytadan kod so'rang."}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        now = time.time()
        if now > session.get("expires_at", 0):
            _LOGIN_OTPS.pop(tg_user_id, None)
            return web.json_response({"ok": False, "error": "Kod muddati (5 daqiqa) tugagan. Qaytadan yangi kod so'rang!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        session["attempts"] = session.get("attempts", 0) + 1
        if session["attempts"] > 5:
            _LOGIN_OTPS.pop(tg_user_id, None)
            return web.json_response({"ok": False, "error": "Ko'p xato urinishlar! Qaytadan yangi kod so'rang."}, status=403, headers={"Access-Control-Allow-Origin": "*"})

        if str(session.get("otp")) != raw_otp:
            return web.json_response({"ok": False, "error": "Tasdiqlash kodi noto'g'ri! Tekshirib qaytadan kiriting."}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        saved_msg_id = session.get("message_id")
        _LOGIN_OTPS.pop(tg_user_id, None)

        # Telegram bot yuborgan OTP xabarini avtomatik o'chirish (deleteMessage)
        if saved_msg_id:
            try:
                from config import BOT_TOKEN
                token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
                if token:
                    delete_url = f"https://api.telegram.org/bot{token}/deleteMessage"
                    async def _del_msg():
                        try:
                            async with aiohttp.ClientSession() as s:
                                await s.post(delete_url, json={
                                    "chat_id": tg_user_id,
                                    "message_id": saved_msg_id
                                }, timeout=aiohttp.ClientTimeout(total=4))
                        except Exception:
                            pass
                    asyncio.create_task(_del_msg())
            except Exception as e_del:
                print(f"[OTP AutoDelete] Xato: {e_del}")

        auth_token = secrets.token_hex(24)
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
        is_owner = (tg_user_id == 6735799833)
        is_vip = is_owner or bool(is_bot_admin(tg_user_id)) or bool(is_user_vip(tg_user_id))

        resp_data = {
            "ok": True,
            "token": auth_token,
            "tg_user_id": tg_user_id,
            "is_vip": is_vip,
            "is_owner": is_owner
        }
        resp = web.json_response(resp_data, headers={"Access-Control-Allow-Origin": "*"})
        resp.set_cookie("cf_auth_token", auth_token, max_age=30*86400, path="/", samesite="Lax")
        return resp
    except Exception as e:
        print(f"handle_api_auth_verify_otp error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_auth_verify_webapp(request):
    """Telegram WebApp SDK initData HMAC-SHA256 tekshiruvi"""
    try:
        import time, secrets, hmac, hashlib
        from urllib.parse import parse_qsl
        data = await request.json()
        init_data_raw = data.get("initData", "").strip()
        if not init_data_raw:
            return web.json_response({"ok": False, "error": "initData talab qilinadi!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        from config import BOT_TOKEN
        token = BOT_TOKEN or os.getenv("BOT_TOKEN", "")
        if not token:
            return web.json_response({"ok": False, "error": "BOT_TOKEN sozlanmagan!"}, status=500, headers={"Access-Control-Allow-Origin": "*"})

        parsed = dict(parse_qsl(init_data_raw, keep_blank_values=True))
        if "hash" not in parsed:
            return web.json_response({"ok": False, "error": "initData hash topilmadi!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        received_hash = parsed.pop("hash")
        auth_date = int(parsed.get("auth_date", 0))
        now = time.time()
        # 24 soat (86400s) dan eski initData ni rad etish (Replay attack oldini olish)
        if auth_date <= 0 or (now - auth_date > 86400):
            return web.json_response({"ok": False, "error": "Telegram WebApp sessiya muddati o'tgan! Iltimos, qaytadan oching."}, status=401, headers={"Access-Control-Allow-Origin": "*"})

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

        secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return web.json_response({"ok": False, "error": "Telegram WebApp imzosi haqiqiy emas!"}, status=403, headers={"Access-Control-Allow-Origin": "*"})

        user_obj = None
        if "user" in parsed:
            import json
            user_obj = json.loads(parsed["user"])

        tg_user_id = user_obj.get("id") if user_obj else 0
        if not tg_user_id:
            return web.json_response({"ok": False, "error": "User ma'lumotlari topilmadi!"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        auth_token = secrets.token_hex(24)
        _AUTH_TOKENS[auth_token] = {
            "tg_user_id": tg_user_id,
            "created_at": time.time()
        }

        # PostgreSQL da 7 kunlik doimiy sessiya saqlash
        try:
            from database import save_web_session
            fingerprint = str(data.get("fingerprint", "")).strip()
            save_web_session(auth_token, tg_user_id, fingerprint)
        except Exception as e_sess:
            print(f"[WebSession WebApp] Saqlashda xato: {e_sess}")

        from database import is_bot_admin, is_user_vip
        is_owner = (tg_user_id == 6735799833)
        is_vip = is_owner or bool(is_bot_admin(tg_user_id)) or bool(is_user_vip(tg_user_id))

        resp_dict = {
            "ok": True,
            "token": auth_token,
            "tg_user_id": tg_user_id,
            "user": user_obj,
            "is_vip": is_vip,
            "is_owner": is_owner
        }
        resp = web.json_response(resp_dict, headers={"Access-Control-Allow-Origin": "*"})
        resp.set_cookie("cf_auth_token", auth_token, max_age=30*86400, path="/", samesite="Lax")
        return resp
    except Exception as e:
        print(f"handle_api_auth_verify_webapp error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_auth_verify_token(request):
    """Mavjud sessiya tokenini tekshirish (PostgreSQL 7-kunlik persistent auth)"""
    try:
        import time
        try:
            data = await request.json()
        except Exception:
            data = {}

        token = str(data.get("token") or request.query.get("token") or "").strip()
        raw_uid = data.get("tg_user_id") or data.get("user_id") or request.query.get("tg_user_id") or request.query.get("user_id")
        fingerprint = str(data.get("fingerprint") or request.query.get("fingerprint") or "").strip()

        tg_user_id = None
        if raw_uid:
            try:
                tg_user_id = int(raw_uid)
            except Exception:
                tg_user_id = None

        session = None

        # 1. First check in-memory cache if token is present
        if token and token in _AUTH_TOKENS:
            cached_s = _AUTH_TOKENS[token]
            if not tg_user_id or cached_s.get("tg_user_id") == tg_user_id:
                session = cached_s
                tg_user_id = session.get("tg_user_id")

        # 2. Check PostgreSQL web_sessions by token
        if not session and token:
            from database import get_web_session
            db_session = get_web_session(token, fingerprint)
            if db_session:
                sess_uid = db_session.get("tg_user_id")
                if not tg_user_id or sess_uid == tg_user_id:
                    tg_user_id = sess_uid
                    session = {
                        "tg_user_id": tg_user_id,
                        "created_at": time.time()
                    }
                    _AUTH_TOKENS[token] = session

        # 3. Fallback to fingerprint lookup if no token or token not found
        if not session and fingerprint:
            from database import get_web_session_by_fingerprint
            db_session = get_web_session_by_fingerprint(fingerprint)
            if db_session:
                sess_uid = db_session.get("tg_user_id")
                if not tg_user_id or sess_uid == tg_user_id:
                    token = db_session.get("session_token")
                    tg_user_id = sess_uid
                    session = {
                        "tg_user_id": tg_user_id,
                        "created_at": time.time()
                    }
                    _AUTH_TOKENS[token] = session

        # 4. Check web_sessions table by tg_user_id or validate user
        if not session and tg_user_id and tg_user_id > 0:
            import database
            from config import OWNER_ID
            is_owner_user = bool(OWNER_ID and tg_user_id == OWNER_ID) or (tg_user_id == 6735799833)

            # Check web_sessions for this tg_user_id
            conn = database.get_db()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT session_token, tg_user_id, fingerprint, created_at, expires_at
                        FROM web_sessions
                        WHERE tg_user_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (tg_user_id,))
                    row = cur.fetchone()
                    if row:
                        db_token = row.get("session_token")
                        # If token matches, or no token was sent, or is owner:
                        if not token or token == db_token or is_owner_user:
                            token = db_token or token
                            session = {
                                "tg_user_id": tg_user_id,
                                "created_at": time.time()
                            }
                            if token:
                                _AUTH_TOKENS[token] = session
                except Exception as ex:
                    print(f"web_sessions tg_user_id check notice: {ex}")
                finally:
                    conn.close()

            # Session auto-recovery (Valid non-banned users maintain persistent session across server restarts/F5)
            if not session and tg_user_id and tg_user_id > 0 and not database.is_user_banned(tg_user_id):
                import secrets
                if not token or "fake" in token or len(token) < 12:
                    token = f"tok_{secrets.token_hex(24)}"
                session = {
                    "tg_user_id": tg_user_id,
                    "created_at": time.time()
                }
                _AUTH_TOKENS[token] = session
                try:
                    database.save_web_session(token, tg_user_id, fingerprint=fingerprint)
                except Exception:
                    pass

        if not token or not tg_user_id or not session:
            return web.json_response({"ok": False, "error": "Sessiya yaroqsiz yoki muddati o'tgan"}, status=401, headers={"Access-Control-Allow-Origin": "*"})

        import database
        if database.is_user_banned(tg_user_id):
            return web.json_response({"ok": False, "error": "Hisobingiz bloklangan!", "is_banned": True}, status=403, headers={"Access-Control-Allow-Origin": "*"})

        from database import is_bot_admin, is_user_vip, get_user_balance, is_user_kyc_verified
        from config import OWNER_ID
        is_owner = bool(OWNER_ID and tg_user_id == OWNER_ID) or (tg_user_id == 6735799833)
        is_admin_flag = is_owner or bool(is_bot_admin(tg_user_id))
        is_vip = is_admin_flag or bool(is_user_vip(tg_user_id))
        balance = get_user_balance(tg_user_id)
        is_kyc = is_user_kyc_verified(tg_user_id)

        user_data = {
            "id": tg_user_id,
            "tg_user_id": tg_user_id,
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
            "is_vip": is_vip,
            "is_owner": is_owner,
            "user": user_data
        }
        resp = web.json_response(resp_payload, headers={"Access-Control-Allow-Origin": "*"})
        resp.set_cookie("cf_auth_token", token, max_age=30*86400, path="/", samesite="Lax")
        return resp
    except Exception as e:
        print(f"handle_api_auth_verify_token error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=401, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_auth_logout(request):
    """Web sessiyani bazadan ham, xotiradan ham o'chirish"""
    try:
        data = await request.json()
        token = data.get("token", "")
        if token:
            _AUTH_TOKENS.pop(token, None)
            from database import delete_web_session
            delete_web_session(token)
        return web.json_response({"ok": True}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        return web.json_response({"ok": True}, headers={"Access-Control-Allow-Origin": "*"})


async def start_web_server(port):
    """aiohttp web serverni ishga tushirish (Rate Limiting, Max Payload & Security Headers bilan)"""
    app = web.Application(client_max_size=2097152, middlewares=[security_and_rate_limit_middleware])
    app.router.add_get("/", handle_health)
    # Public Multilingual Legal & Compliance Pages (Google OAuth Branding Verification)
    app.router.add_get("/privacy", handle_privacy_page)
    app.router.add_get("/privacy-policy", handle_privacy_page)
    app.router.add_get("/privacy.html", handle_privacy_page)
    app.router.add_get("/terms", handle_terms_page)
    app.router.add_get("/terms-of-service", handle_terms_page)
    app.router.add_get("/terms.html", handle_terms_page)
    app.router.add_get("/robots.txt", handle_robots)
    # Google Search Console Domain Verification File Handler
    app.router.add_get(r"/{filename:google[a-zA-Z0-9_\-]+\.html}", handle_google_verification)
    # Client-side SPA routes for /goal, /boost, /teamwork-preview
    app.router.add_get("/goal", handle_health)
    app.router.add_get("/boost", handle_health)
    app.router.add_get("/teamwork-preview", handle_health)
    app.router.add_get("/teamwork_preview", handle_health)
    app.router.add_get("/teamwork", handle_health)
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
    app.router.add_get("/oauth/callback", handle_oauth_callback)
    
    # 5 Tier Telegram Stars Mystery Cases & Live API
    app.router.add_get("/api/stars/cases", handle_api_stars_cases)
    app.router.add_get("/api/stars/live-gifts", handle_api_stars_live_gifts)
    app.router.add_post("/api/stars/open-case", handle_api_stars_open_case)
    app.router.add_post("/api/stars/open-case-uzs", handle_api_stars_open_case_uzs)
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
    app.router.add_post("/api/tonconnect/save", handle_api_tonconnect_save)
    app.router.add_post("/api/tonconnect/disconnect", handle_api_tonconnect_disconnect)
    
    # Yangi: 3D NFT Metadata & Media API (TEP-64 Off-chain standard)
    app.router.add_get("/api/nft/meta/{item_id}", handle_nft_metadata)
    app.router.add_get("/api/nft/image/{filename}", handle_nft_image)
    app.router.add_get("/api/nft/video/{filename}", handle_nft_video)
    app.router.add_get("/api/nft/animation/{slug}", handle_api_nft_animation)
    
    # Yangi: Reseller & Developer REST API (/api/v1/...)
    try:
        from reseller_api import setup_reseller_api_routes
        setup_reseller_api_routes(app)
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
                return _web.json_response({"error": str(e)}, status=500)

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
    #  TG bot + web server + autopilot worker                             #
    # ------------------------------------------------------------------ #
    # 0. Database jadvallarini tekshirish va yaratish
    try:
        from database import init_db
        init_db()
    except Exception as db_init_err:
        print(f"init_db xatosi: {db_init_err}")

    tasks = []

    # 1. Auto-Reply Userbot
    if SESSION_STRING:
        from userbot import run_userbot
        tasks.append(run_userbot())
        print("🤖 Auto-Reply Userbot qo'shildi")
    else:
        print("⚠️  SESSION_STRING topilmadi — Userbot o'chirilgan")
    
    BOT_TOKEN = os.getenv("BOT_TOKEN") or BOT_TOKEN
    # 2. CreatorFlow Studio Bot
    if BOT_TOKEN:
        from ytbot import create_ytbot
        bot = create_ytbot()
        if bot:
            ytbot_instance = bot
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
                try:
                    from pyrogram.types import BotCommand
                    await bot.set_bot_commands([
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
                    print("📢 @CreatorFlow_Store kanal avtopiloti (restock, xaridlar, aksiyalar) ishga tushirildi.")
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
                    asyncio.create_task(run_marketplace_background_refresher(interval_seconds=60))
                    print("🚀 Telegram Marketplace 60s Live Stock Refresher ishga tushirildi.")
                except Exception as mp_err:
                    print(f"Marketplace Refresher startup error: {mp_err}")



            async def run_bot():
                await bot.start()
                print("✨ CreatorFlow Studio Bot muvaffaqiyatli ishga tushdi!")
                asyncio.create_task(_post_startup_background())
                await asyncio.Event().wait()
            tasks.append(run_bot())
            print("🎬 CreatorFlow Studio Bot qo'shildi")
    else:
        print("⚠️  BOT_TOKEN topilmadi — YouTube Bot o'chirilgan")

    if not tasks:
        print("\n❌ Hech qanday bot ishga tushirilmadi! .env faylni tekshiring.")
        sys.exit(1)

    await start_web_server(port)
    tasks.append(run_autopilot_worker())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())