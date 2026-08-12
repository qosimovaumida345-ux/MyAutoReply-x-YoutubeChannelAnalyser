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
        with open("index.html", "r") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")
    return web.Response(text="Bot is running!", content_type="text/html")


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
            save_yt_connection(
                tg_user_id=tg_user_id,
                yt_channel_id=channel_id,
                yt_channel_title=channel_title,
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                token_expiry=result["token_expiry"]
            )

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


async def start_web_server(port):
    """aiohttp web serverni ishga tushirish"""
    app = web.Application()
    app.router.add_get("/", handle_health)
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
        config.refresh_youtube_api_keys()
        # Disable bot polling tasks if it's a worker

        tasks = [run_worker_queue()]
    else:
        tasks.append(run_autopilot_worker())
        
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
