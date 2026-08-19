import asyncio
import sys
import os

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

from aiohttp import web
from config import SESSION_STRING, BOT_TOKEN
from autopost import exchange_code_with_redirect, pending_oauth
from database import save_yt_connection

# ==================== BOT REFERENCES ====================
# ytbot instance ni saqlash (callback dan xabar yuborish uchun)
ytbot_instance = None



# ==================== AUTOPILOT WORKER ====================
async def run_autopilot_worker():
    import asyncio
    from database import get_all_active_autopilots, update_autopilot_last_run
    from autopost import autopost_worker
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
                            
                            # Add to background worker
                            asyncio.create_task(autopost_worker(task_id, user_id, topic, 1, ytbot_instance, user_id))
                            
                        except Exception as e:
                            print(f"Autopilot task error: {e}")
                            
        except Exception as e:
            print(f"Autopilot worker error: {e}")
            
        await asyncio.sleep(60 * 60) # Check every hour


async def run_worker_queue():
    from database import claim_pending_autopost_task
    from ytbot import autopost_worker
    import asyncio
    from pyrogram import Client
    from config import API_ID, API_HASH, BOT_TOKEN
    
    # Mock client for worker since it doesn't use telegram polling
    mock_client = Client("worker_mock", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    await mock_client.start()
    
    print("👷 Worker poylamoqda...")
    while True:
        task = claim_pending_autopost_task()
        if task:
            print(f"📥 Yangi vazifa olindi: {task['id']} - {task['search_query']}")
            from database import get_user_proxy
            user_proxy = get_user_proxy(task['tg_user_id'])
            # Run worker
            await autopost_worker(task['id'], task['tg_user_id'], task['search_query'], task['total_count'], mock_client, task['tg_user_id'], proxy_url=user_proxy, apply_watermark=task.get('apply_watermark', False))
        else:
            await asyncio.sleep(5)

# ==================== WEB SERVER (OAuth Callback + Health Check) ====================

async def handle_health(request):
    """Render health check uchun va WebApp UI"""
    import os
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")
    return web.Response(text="Bot is running!", content_type="text/html")


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
    
    # Cache tekshirish — agar 10 daqiqa ichida so'ralgan bo'lsa, qayta API chaqirmaslik
    cached = _stats_cache.get(tg_user_id)
    if cached and (_time.time() - cached["ts"]) < _CACHE_TTL:
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

        conn_data = get_yt_connection(int(tg_user_id))
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

        response_data = {
            "channel_title":    snippet.get("title", ""),
            "channel_username": conn_data.get("yt_channel_username", ""),
            "channel_thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
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
        
        # Cache'ga saqlash
        _stats_cache[tg_user_id] = {
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
                token_expiry=result["token_expiry"]
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
            channels.append({
                "channel_id": c.get("yt_channel_id", ""),
                "channel_title": c.get("yt_channel_title", "Unknown"),
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

async def handle_api_videos(request):
    """YouTube'dan video qidirish"""
    import json
    q = request.query.get("q", "")
    max_results = int(request.query.get("maxResults", "12"))
    video_type = request.query.get("type", "")  # "short" or ""
    
    if not q:
        return web.Response(text=json.dumps({"error": "q param kerak"}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
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
        
        return web.Response(text=json.dumps({"videos": videos}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)[:300]}), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, status=500)

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
        if scores["seo"] < 60: tips.append("🏷 SEO yaxshilang: Har bir videoga 10+ tag qo'shing, sarlavhani 40-65 belgi qiling")
        if scores["engagement"] < 50: tips.append("💬 Engagement oshiring: CTA (Call to Action) qo'shing va izohchilar bilan muloqot qiling")
        if scores["consistency"] < 60: tips.append("📅 Muntazam yuklang: Haftada kamida 2-3 ta video yuklashga harakat qiling")
        if scores["growth"] < 50: tips.append("📈 O'sish: SEO va trending mavzularga ko'proq e'tibor bering")
        if scores["branding"] < 70: tips.append("🖼 Branding: Professional banner va avatar qo'ying")
        
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
    """Video uchun mavjud formatlarni olish"""
    import json
    video_id = request.query.get("video_id")
    tg_user_id = request.query.get("tg_user_id")
    
    if not video_id:
        return web.json_response({"error": "video_id kerak"}, status=400)
    
    try:
        import yt_dlp
        import asyncio
        import os
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'mweb'],
                    'player_skip': ['webpage'],
                }
            }
        }
        
        cookie_path = None
        if tg_user_id:
            from database import get_user_cookies
            cookies_text = get_user_cookies(int(tg_user_id))
            if cookies_text:
                os.makedirs("downloads", exist_ok=True)
                cookie_path = f"downloads/cookies_fmt_{tg_user_id}.txt"
                with open(cookie_path, "w", encoding="utf-8") as f:
                    f.write(cookies_text)
                ydl_opts['cookiefile'] = cookie_path
        
        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        try:
            info = await asyncio.to_thread(_extract)
        finally:
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)
        
        # Collect available resolutions
        # yt-dlp dynamically handles formats and gracefully falls back to the max available if requested height is missing
        # So we can enable all options by default.
        available = True
        
        # Map standard resolutions
        all_resolutions = [
            {"label": "360p", "value": "360", "available": True},
            {"label": "480p", "value": "480", "available": True},
            {"label": "720p (HD)", "value": "720", "available": True},
            {"label": "1080p (FHD)", "value": "1080", "available": True},
            {"label": "1440p (2K)", "value": "1440", "available": True},
            {"label": "2160p (4K)", "value": "2160", "available": True},
            {"label": "4320p (8K)", "value": "4320", "available": True},
            {"label": "🎵 MP3 (Audio)", "value": "mp3", "available": True},
        ]
        
        return web.json_response({
            "title": info.get("title", "Video"),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "formats": all_resolutions,
        })
    except Exception as e:
        return web.json_response({"error": str(e)[:300]}, status=500)

async def handle_api_download_file(request):
    """Video yuklab olish va stream qilish"""
    import json
    import asyncio
    import glob
    import os
    
    video_id = request.query.get("video_id")
    resolution = request.query.get("resolution", "720")
    tg_user_id = request.query.get("tg_user_id")
    
    if not video_id:
        return web.json_response({"error": "video_id kerak"}, status=400)
    
    try:
        import yt_dlp
        import random
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        os.makedirs("downloads", exist_ok=True)
        filename = f"downloads/webdl_{random.randint(10000, 99999)}"
        
        ydl_opts = {
            'outtmpl': filename + '.%(ext)s',
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'mweb'],
                    'player_skip': ['webpage'],
                }
            }
        }
        
        cookie_path = None
        if tg_user_id:
            from database import get_user_cookies
            cookies_text = get_user_cookies(int(tg_user_id))
            if cookies_text:
                cookie_path = f"downloads/cookies_dl_{tg_user_id}.txt"
                with open(cookie_path, "w", encoding="utf-8") as f:
                    f.write(cookies_text)
                ydl_opts['cookiefile'] = cookie_path
        
        if resolution == "mp3":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        else:
            h = int(resolution)
            ydl_opts['format'] = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        try:
            await asyncio.to_thread(_download)
        finally:
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)
        
        # Find downloaded file
        base = os.path.basename(filename)
        found = None
        for f in os.listdir("downloads"):
            if f.startswith(base):
                found = os.path.join("downloads", f)
                break
        
        if not found or not os.path.exists(found):
            return web.json_response({"error": "Fayl topilmadi"}, status=500)
        
        # Stream the file
        content_type = "audio/mpeg" if resolution == "mp3" else "video/mp4"
        dl_name = f"video_{video_id}_{resolution}.{'mp3' if resolution == 'mp3' else 'mp4'}"
        
        response = web.FileResponse(found, headers={
            "Content-Disposition": f'attachment; filename="{dl_name}"',
            "Access-Control-Allow-Origin": "*",
        })
        
        # Cleanup after response (schedule deletion)
        async def cleanup_later():
            await asyncio.sleep(60)
            try:
                if os.path.exists(found):
                    os.remove(found)
            except:
                pass
        asyncio.create_task(cleanup_later())
        
        return response
    except Exception as e:
        return web.json_response({"error": str(e)[:300]}, status=500)

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
        
        # Trigger background worker instantly
        from autopost import autopost_worker
        import asyncio
        # We don't have direct access to the Telegram client in the web app, so we pass None
        asyncio.create_task(autopost_worker(task_id, tg_user_id, search_query, len(video_ids), ytbot_instance, tg_user_id))
        
        return web.json_response({"success": True, "task_id": task_id})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_api_reset_db(request):
    """Admin: Bazani tozalash"""
    import json
    try:
        data = await request.json()
        tg_user_id = int(data.get("tg_user_id", 0))
        
        from config import OWNER_ID
        if tg_user_id != OWNER_ID:
            return web.json_response({"error": "Siz admin emassiz!"}, status=403)
            
        from database import reset_all_data
        success = reset_all_data()
        return web.json_response({"success": success})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def start_web_server(port):
    """aiohttp web serverni ishga tushirish"""
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/channels", handle_api_channels)
    app.router.add_get("/api/autopost-tasks", handle_api_autopost_tasks)
    app.router.add_get("/api/videos", handle_api_videos)
    app.router.add_get("/api/trending", handle_api_trending)
    app.router.add_get("/api/health-score", handle_api_health_score)
    app.router.add_get("/api/best-time", handle_api_best_time)
    app.router.add_post("/api/autopost-create", handle_api_autopost_create)
    app.router.add_get("/api/video-formats", handle_api_video_formats)
    app.router.add_get("/api/download-file", handle_api_download_file)
    app.router.add_post("/api/reset-db", handle_api_reset_db)
    app.router.add_get("/oauth/callback", handle_oauth_callback)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server {port}-portda ishga tushdi (OAuth callback tayyor)")
    return runner


# ==================== MAIN ====================

async def main():
    """Ikkala botni bir vaqtda ishga tushirish"""
    global ytbot_instance
    tasks = []

    # 1. Auto-Reply Userbot
    if SESSION_STRING:
        from userbot import run_userbot
        tasks.append(run_userbot())
        print("🤖 Auto-Reply Userbot qo'shildi")
    else:
        print("⚠️  SESSION_STRING topilmadi — Userbot o'chirilgan")
        print("   ➡️  Avval session_generator.py ni ishga tushiring")

    # 2. YouTube Analytics Bot
    if BOT_TOKEN:
        from ytbot import create_ytbot
        bot = create_ytbot()
        if bot:
            ytbot_instance = bot
            async def run_bot():
                await bot.start()
                print("🎬 YouTube Analytics Bot muvaffaqiyatli ishga tushdi!")
                
                # Fetch custom emoji fallbacks to map them accurately
                try:
                    from ytbot import AUTO_EMOJI_MAP
                    from custom_emojis import CUSTOM_EMOJI_POOL
                    ids = [int(i) for i in CUSTOM_EMOJI_POOL]
                    stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=ids)
                    for s in stickers:
                        if getattr(s, 'emoji', None):
                            AUTO_EMOJI_MAP[s.emoji] = s.custom_emoji_id
                    print(f"🌟 Yuklangan maxsus emojilar soni: {len(AUTO_EMOJI_MAP)}")
                except Exception as e:
                    print(f"Maxsus emojilarni yuklashda xatolik: {e}")

                await asyncio.Event().wait()
            tasks.append(run_bot())
            print("🎬 YouTube Analytics Bot qo'shildi")
    else:
        print("⚠️  BOT_TOKEN topilmadi — YouTube Bot o'chirilgan")

    if not tasks:
        print("\n❌ Hech qanday bot ishga tushirilmadi!")
        print("   .env faylni tekshiring.")
        sys.exit(1)


    role = os.environ.get("ROLE", "main")
    print(f"\n========================================")
    print(f"🚀 Barcha xizmatlar ishga tushirilmoqda... ROLE: {role}")
    print(f"========================================\n")

    port = int(os.environ.get("PORT", 3000))
    await start_web_server(port)

    if role == "worker":
        import config
        # Disable bot polling tasks if it's a worker

        tasks = [run_worker_queue()]
    else:
        tasks.append(run_autopilot_worker())
        
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
