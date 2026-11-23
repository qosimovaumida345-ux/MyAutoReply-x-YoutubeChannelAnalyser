"""Bazadagi test/soxta userlarni xavfsiz tozalovchi CLI skript.

Ishlatish:
  python scripts/clean_fake_users.py --dry-run
  python scripts/clean_fake_users.py --apply
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Haqiqiy bazadan soxta userlarni o'chirish")
    ap.add_argument("--dry-run", action="store_true", help="Faqat ko'rish, o'chirmaslik")
    args = ap.parse_args()

    dry = not args.apply
    import database
    token = os.getenv("BOT_TOKEN", "").strip()
    res = database.purge_fake_and_test_users(bot_token=token, dry_run=dry)
    print(f"Result (dry_run={dry}): {res}")
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
