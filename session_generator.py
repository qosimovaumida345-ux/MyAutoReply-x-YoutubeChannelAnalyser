"""
Session String Generator
========================
Bu skriptni faqat BIRINCHI MARTA kompyuteringizda ishga tushiring.
U sizning Telegram akkauntingizga ulanib, SESSION_STRING yaratadi.
Keyin o'sha stringni .env faylingizga qo'ying.

Ishga tushirish:
    python session_generator.py
"""

import asyncio
import sys
import os

# Windows encoding fix
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Python 3.10+ event loop fix
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client
from config import API_ID, API_HASH


async def main():
    print("=" * 50)
    print("[*] Telegram Session String Generator")
    print("=" * 50)
    print()
    print("Bu sizning akkauntingizga ulanadi.")
    print("Telefon raqamingiz va tasdiqlash kodini kiritishingiz kerak.")
    print()
    
    app = Client(
        "session_generator",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    async with app:
        session_string = await app.export_session_string()
        
        print()
        print("=" * 50)
        print("[+] SESSION STRING MUVAFFAQIYATLI YARATILDI!")
        print("=" * 50)
        print()
        print("Quyidagi stringni .env faylingizga qo'ying:")
        print()
        print(f"SESSION_STRING={session_string}")
        print()
        print("[!] BU STRINGNI HECH KIMGA BERMANG!")
        print("    Bu string orqali akkauntingizga kirish mumkin.")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
