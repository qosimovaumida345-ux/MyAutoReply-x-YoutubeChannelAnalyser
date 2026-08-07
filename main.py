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

from config import SESSION_STRING, BOT_TOKEN

async def dummy_server(reader, writer):
    """Render.com Port binding talabini qondirish uchun oddiy server"""
    writer.write(b"HTTP/1.1 200 OK\r\n\r\nBot is running!")
    await writer.drain()
    writer.close()

async def main():
    """Ikkala botni bir vaqtda ishga tushirish"""
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
        from ytbot import run_ytbot
        tasks.append(run_ytbot())
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
    # Render.com uchun Web Server (Portni band qilish)
    port = int(os.environ.get("PORT", 10000))
    server = await asyncio.start_server(dummy_server, '0.0.0.0', port)
    print(f"🌐 Dummy web server {port}-portda ishga tushdi (Render uchun)")
    tasks.append(server.serve_forever())
    
    # Barcha botlarni parallel ishga tushirish
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
