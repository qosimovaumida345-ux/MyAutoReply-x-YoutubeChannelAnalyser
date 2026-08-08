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


# ==================== WEB SERVER (OAuth Callback + Health Check) ====================

async def handle_health(request):
    """Render health check uchun"""
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

    print("\n" + "=" * 40)
    print("🚀 Barcha botlar ishga tushirilmoqda...")
    print("=" * 40 + "\n")

    # Web Server (OAuth callback + health check)
    port = int(os.environ.get("PORT", 10000))
    await start_web_server(port)

    # Startup: log available formats for debugging
    print("\n[STARTUP] Running format availability test on server...")
    try:
        from autopost import test_available_formats
        await asyncio.to_thread(test_available_formats)
    except Exception as e:
        print(f"[STARTUP] Format test error (non-critical): {e}")
    print("[STARTUP] Format test complete. Check logs above.\n")

    # Barcha botlarni parallel ishga tushirish
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
