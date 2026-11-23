"""Eski CreatorFlow bot foydalanuvchilariga yangi botga o'tish haqida xabar yuborish.

Ishlatish:
  python scripts/migration_notice.py --old-token-env OLD_BOT_TOKEN            # dry-run (hech narsa yubormaydi)
  python scripts/migration_notice.py --old-token-env OLD_BOT_TOKEN --send     # haqiqiy yuborish

Eski bot tokeni faqat environment o'zgaruvchisidan olinadi (chatga yoki faylga yozilmaydi).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def api(token: str, method: str, payload: dict | None = None, timeout: int = 15) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"ok": False, "error_code": e.code, "description": str(e)}
    except Exception as e:
        return {"ok": False, "description": f"{type(e).__name__}: {e}"}


def build_message(new_username: str) -> tuple[str, dict]:
    text = (
        "🚀 <b>Biz yangi botga — Mono Deck Studio ga ko'chdik!</b>\n\n"
        "Sizga yanada tez, barqaror va qulay xizmat ko'rsatish uchun "
        f"yangi rasmiy botimiz <b>@{new_username}</b> (Mono Deck Studio) ishga tushdi.\n\n"
        "✨ <b>Yangiliklar:</b>\n"
        "• Yangi dizayn va tezkor veb-studio (monodeck.site)\n"
        "• YouTube Auto-Post + avtomatik watermark tozalash\n"
        "• Downloader, Cases, Upgrader va AI Store bo'limlari\n"
        "• Barcha balans va ma'lumotlaringiz saqlanadi — yo'qolmaydi\n\n"
        "⚠️ <b>Muhim:</b> eski bot <b>1–2 kun ichida butunlay o'chiriladi</b>. "
        "Uzilishsiz foydalanish uchun hoziroq yangi botga o'ting 👇"
    )
    markup = {
        "inline_keyboard": [[{"text": "➡️ Mono Deck Studio ga o'tish", "url": f"https://t.me/{new_username}?start=migrated"}]]
    }
    return text, markup


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-token-env", default="OLD_BOT_TOKEN")
    ap.add_argument("--new-username", default="monodeck_app")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Test uchun: faqat birinchi N ta foydalanuvchi")
    ap.add_argument("--only", type=int, default=0, help="Faqat bitta tg_user_id ga yuborish (test)")
    args = ap.parse_args()

    old_token = os.getenv(args.old_token_env, "").strip()
    if not old_token:
        print(f"XATO: {args.old_token_env} environment o'zgaruvchisi bo'sh.")
        return 2

    me = api(old_token, "getMe")
    if not me.get("ok"):
        print("XATO: eski bot tokeni yaroqsiz:", me.get("description"))
        return 2
    print(f"Eski bot: {me['result'].get('first_name')} @{me['result'].get('username')}")

    import config
    new_username = (args.new_username or config.get_bot_username()).lstrip("@")
    print(f"Yangi bot: @{new_username}")
    if new_username.lower() == me["result"].get("username", "").lower():
        print("XATO: yangi va eski bot bir xil.")
        return 2

    import database
    conn = database.get_db()
    if not conn:
        print("XATO: bazaga ulanib bo'lmadi.")
        return 2
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT tg_user_id FROM bot_users WHERE tg_user_id IS NOT NULL ORDER BY tg_user_id")
        ids = [(r["tg_user_id"] if isinstance(r, dict) else r[0]) for r in cur.fetchall()]
    finally:
        conn.close()
    if args.only:
        ids = [args.only]
    if args.limit:
        ids = ids[: args.limit]
    print(f"Qabul qiluvchilar: {len(ids)} ta")

    text, markup = build_message(new_username)
    if not args.send:
        print("\n--- DRY-RUN: quyidagi xabar yuboriladi ---\n" + text)
        print("\nHech narsa yuborilmadi. Yuborish uchun --send qo'shing.")
        return 0

    sent = blocked = failed = 0
    for i, uid in enumerate(ids, 1):
        res = api(old_token, "sendMessage", {
            "chat_id": uid, "text": text, "parse_mode": "HTML",
            "disable_web_page_preview": True, "reply_markup": markup,
        })
        if res.get("ok"):
            sent += 1
            if str(uid) == "6735799833":
                msg_id = (res.get("result") or {}).get("message_id")
                print(f"  [OWNER DELIVERED] uid={uid} ok=True message_id={msg_id}")
        elif res.get("error_code") == 429:
            wait = int((res.get("parameters") or {}).get("retry_after", 5)) + 1
            time.sleep(wait)
            res = api(old_token, "sendMessage", {
                "chat_id": uid, "text": text, "parse_mode": "HTML",
                "disable_web_page_preview": True, "reply_markup": markup,
            })
            sent += 1 if res.get("ok") else 0
            failed += 0 if res.get("ok") else 1
        elif res.get("error_code") in (400, 403):
            blocked += 1
        else:
            failed += 1
        if i % 25 == 0:
            print(f"  {i}/{len(ids)} — yuborildi={sent} bloklagan/yo'q={blocked} xato={failed}")
        time.sleep(0.05)
    print(f"\nTAYYOR: yuborildi={sent}, bloklagan/chat yo'q={blocked}, xato={failed}, jami={len(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
