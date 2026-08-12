import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

from config import DATABASE_URL


def get_db():
    """PostgreSQL ulanishini qaytaradi"""
    if not DATABASE_URL:
        print("DATABASE_URL topilmadi! Render PostgreSQL ni ulang.")
        return None
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = False
    return conn


def init_db():
    """Jadvallarni yaratish (PostgreSQL)"""
    conn = get_db()
    if not conn:
        print("Database ulanmadi. DATABASE_URL ni tekshiring.")
        return
    cur = conn.cursor()
    
    # YouTube kanal kuzatish jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tracked_channels (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            channel_id TEXT NOT NULL,
            channel_title TEXT,
            added_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(chat_id, channel_id)
        )
    """)
    
    # Kanal statistikasi jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_snapshots (
            id SERIAL PRIMARY KEY,
            channel_id TEXT NOT NULL,
            subscribers BIGINT DEFAULT 0,
            total_views BIGINT DEFAULT 0,
            total_videos BIGINT DEFAULT 0,
            snapshot_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Video statistikasi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS video_snapshots (
            id SERIAL PRIMARY KEY,
            video_id TEXT NOT NULL,
            channel_id TEXT,
            title TEXT,
            views BIGINT DEFAULT 0,
            likes BIGINT DEFAULT 0,
            comments BIGINT DEFAULT 0,
            snapshot_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # YouTube kanal ulanishlari (auto-post uchun)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS yt_connections (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            yt_channel_id TEXT NOT NULL,
            yt_channel_title TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TIMESTAMP,
            connected_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tg_user_id, yt_channel_id)
        )
    """)
    
    # Auto-post vazifalar (topshiriqlar)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS autopost_tasks (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            yt_channel_id TEXT NOT NULL,
            search_query TEXT NOT NULL,
            video_type TEXT DEFAULT 'shorts',
            total_count INTEGER NOT NULL,
            completed_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),\n            apply_watermark BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Auto-post tarixi (qaysi videolar yuklandi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS autopost_history (
            id SERIAL PRIMARY KEY,
            task_id INTEGER REFERENCES autopost_tasks(id) ON DELETE CASCADE,
            tg_user_id BIGINT NOT NULL,
            source_video_id TEXT NOT NULL,
            source_title TEXT,
            uploaded_video_id TEXT,
            uploaded_title TEXT,
            status TEXT DEFAULT 'pending',
            error_msg TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Bot adminlari (avtorizatsiyadan o'tganlar)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_admins (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            added_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Bot maxfiy sozlamalari (cookies, tokens va h.k.)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT NOW(),\n            apply_watermark BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Foydalanuvchi sozlamalari (proxy, kunlik limit)
    cur.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
            tg_user_id BIGINT PRIMARY KEY,
            proxy_ip TEXT,
            daily_usage INTEGER DEFAULT 0,
            last_usage_date DATE DEFAULT CURRENT_DATE
        )
    """)
    cur.execute('''\n        CREATE TABLE IF NOT EXISTS autopilot_settings (
            tg_user_id BIGINT PRIMARY KEY,
            topics TEXT,
            interval_days INTEGER DEFAULT 2,
            last_run TIMESTAMP DEFAULT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    # Check and add yt_cookies column if it doesn't exist
    try:
        cur.execute("ALTER TABLE user_settings ADD COLUMN yt_cookies TEXT;")
    except Exception:
        conn.rollback()
    else:
        conn.commit()
    
    conn.commit()
    cur.close()
    conn.close()
    print("PostgreSQL database tayyor!")


# ==================== BOT CONFIG ====================

def set_config(key, value):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bot_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()",
            (key, value, value)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()

def get_config(key):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM bot_config WHERE key = %s", (key,))
        row = cur.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


# ==================== USER SETTINGS (Proxy + Limit) ====================

def set_user_proxy(tg_user_id, proxy_ip):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_settings (tg_user_id, proxy_ip) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO UPDATE SET proxy_ip = %s",
            (tg_user_id, proxy_ip, proxy_ip)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()

def get_user_proxy(tg_user_id):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT proxy_ip FROM user_settings WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return row["proxy_ip"] if row else None
    finally:
        conn.close()

def get_daily_usage(tg_user_id):
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT daily_usage, last_usage_date FROM user_settings WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row:
            return 0
        # Agar kun o'zgargan bo'lsa, limitni qayta boshlash
        from datetime import date
        if row["last_usage_date"] != date.today():
            cur.execute("UPDATE user_settings SET daily_usage = 0, last_usage_date = CURRENT_DATE WHERE tg_user_id = %s", (tg_user_id,))
            conn.commit()
            return 0
        return row["daily_usage"]
    finally:
        conn.close()

def increment_usage(tg_user_id, amount=1):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_settings (tg_user_id, daily_usage, last_usage_date) 
            VALUES (%s, %s, CURRENT_DATE)
            ON CONFLICT (tg_user_id) DO UPDATE SET daily_usage = user_settings.daily_usage + %s, last_usage_date = CURRENT_DATE
        """, (tg_user_id, amount, amount))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
    finally:
        conn.close()


# ==================== BOT ADMINS ====================

def add_bot_admin(tg_user_id, username=None):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bot_admins (tg_user_id, username) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO UPDATE SET username = %s",
            (tg_user_id, username, username)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()


def is_bot_admin(tg_user_id):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM bot_admins WHERE tg_user_id = %s", (tg_user_id,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def get_all_admins():
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bot_admins ORDER BY added_at DESC")
        return cur.fetchall()
    finally:
        conn.close()


# ==================== TRACKED CHANNELS ====================

def add_tracked_channel(chat_id, channel_id, channel_title):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tracked_channels (chat_id, channel_id, channel_title) VALUES (%s, %s, %s) ON CONFLICT (chat_id, channel_id) DO UPDATE SET channel_title = %s",
            (chat_id, channel_id, channel_title, channel_title)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()


def remove_tracked_channel(chat_id, channel_id):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tracked_channels WHERE chat_id = %s AND channel_id = %s", (chat_id, channel_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
    finally:
        conn.close()


def get_tracked_channels(chat_id):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tracked_channels WHERE chat_id = %s", (chat_id,))
        return cur.fetchall()
    finally:
        conn.close()


# ==================== CHANNEL SNAPSHOTS ====================

def save_channel_snapshot(channel_id, subscribers, total_views, total_videos):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO channel_snapshots (channel_id, subscribers, total_views, total_videos) VALUES (%s, %s, %s, %s)",
            (channel_id, subscribers, total_views, total_videos)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
    finally:
        conn.close()


def get_channel_history(channel_id, limit=14):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM channel_snapshots WHERE channel_id = %s ORDER BY snapshot_at DESC LIMIT %s", (channel_id, limit))
        return cur.fetchall()
    finally:
        conn.close()


def get_channel_growth(channel_id):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM channel_snapshots WHERE channel_id = %s ORDER BY snapshot_at DESC LIMIT 2", (channel_id,))
        rows = cur.fetchall()
        if len(rows) < 2:
            return None
        latest = rows[0]
        previous = rows[1]
        return {
            "sub_growth": latest["subscribers"] - previous["subscribers"],
            "view_growth": latest["total_views"] - previous["total_views"],
            "video_growth": latest["total_videos"] - previous["total_videos"],
            "latest": dict(latest),
            "previous": dict(previous),
        }
    finally:
        conn.close()


# ==================== VIDEO SNAPSHOTS ====================

def save_video_snapshot(video_id, channel_id, title, views, likes, comments):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO video_snapshots (video_id, channel_id, title, views, likes, comments) VALUES (%s, %s, %s, %s, %s, %s)",
            (video_id, channel_id, title, views, likes, comments)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
    finally:
        conn.close()


# ==================== YT CONNECTIONS (Auto-Post uchun) ====================

def save_yt_connection(tg_user_id, yt_channel_id, yt_channel_title, access_token, refresh_token, token_expiry=None):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO yt_connections (tg_user_id, yt_channel_id, yt_channel_title, access_token, refresh_token, token_expiry)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tg_user_id, yt_channel_id)
            DO UPDATE SET access_token = %s, refresh_token = %s, token_expiry = %s
        """, (tg_user_id, yt_channel_id, yt_channel_title, access_token, refresh_token, token_expiry,
              access_token, refresh_token, token_expiry))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()


def get_yt_connection(tg_user_id):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM yt_connections WHERE tg_user_id = %s ORDER BY connected_at DESC LIMIT 1", (tg_user_id,))
        return cur.fetchone()
    finally:
        conn.close()


def get_all_yt_connections(tg_user_id):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM yt_connections WHERE tg_user_id = %s", (tg_user_id,))
        return cur.fetchall()
    finally:
        conn.close()


def delete_yt_connection(tg_user_id, yt_channel_id):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM yt_connections WHERE tg_user_id = %s AND yt_channel_id = %s", (tg_user_id, yt_channel_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()


# ==================== AUTO-POST TASKS ====================

def create_autopost_task(tg_user_id, yt_channel_id, search_query, video_type, total_count, apply_watermark=False):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO autopost_tasks (tg_user_id, yt_channel_id, search_query, video_type, total_count, apply_watermark)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (tg_user_id, yt_channel_id, search_query, video_type, total_count, apply_watermark))
        task_id = cur.fetchone()["id"]
        conn.commit()
        return task_id
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return None
    finally:
        conn.close()


def update_autopost_task(task_id, status=None, completed_count=None):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        updates = ["updated_at = NOW()"]
        params = []
        if status:
            updates.append("status = %s")
            params.append(status)
        if completed_count is not None:
            updates.append("completed_count = %s")
            params.append(completed_count)
        params.append(task_id)
        cur.execute(f"UPDATE autopost_tasks SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
    finally:
        conn.close()


def get_autopost_tasks(tg_user_id, status=None):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM autopost_tasks WHERE tg_user_id = %s AND status = %s ORDER BY created_at DESC", (tg_user_id, status))
        else:
            cur.execute("SELECT * FROM autopost_tasks WHERE tg_user_id = %s ORDER BY created_at DESC LIMIT 20", (tg_user_id,))
        return cur.fetchall()
    finally:
        conn.close()


def get_pending_tasks():
    """Kutayotgan barcha vazifalarni olish (background worker uchun)"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM autopost_tasks WHERE status IN ('pending', 'running') ORDER BY created_at ASC")
        return cur.fetchall()
    finally:
        conn.close()


# ==================== AUTO-POST HISTORY ====================


def has_video_been_posted(tg_user_id, source_video_id):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM autopost_history WHERE tg_user_id = %s AND source_video_id = %s AND status = 'uploaded'", (tg_user_id, source_video_id))
        row = cur.fetchone()
        return bool(row)
    except:
        return False
    finally:
        conn.close()

def add_autopost_history(task_id, tg_user_id, source_video_id, source_title):

    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO autopost_history (task_id, tg_user_id, source_video_id, source_title)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (task_id, tg_user_id, source_video_id, source_title))
        history_id = cur.fetchone()["id"]
        conn.commit()
        return history_id
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return None
    finally:
        conn.close()


def update_autopost_history(history_id, status, uploaded_video_id=None, uploaded_title=None, error_msg=None):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE autopost_history SET status = %s, uploaded_video_id = %s, uploaded_title = %s, error_msg = %s
            WHERE id = %s
        """, (status, uploaded_video_id, uploaded_title, error_msg, history_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()


def get_autopost_history(task_id):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM autopost_history WHERE task_id = %s ORDER BY created_at ASC", (task_id,))
        return cur.fetchall()
    finally:
        conn.close()


def is_video_already_posted(tg_user_id, source_video_id):
    """Bu video allaqachon yuklangan yoki yo'qligini tekshirish (dublikat oldini olish)"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM autopost_history WHERE tg_user_id = %s AND source_video_id = %s AND status = 'uploaded'",
            (tg_user_id, source_video_id)
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


# ==================== INIT ====================

try:
    init_db()
except Exception as e:
    print(f"Database init xatosi: {e}")
    print("DATABASE_URL ni tekshiring yoki Render PostgreSQL ni ulang.")

def set_user_cookies(user_id, cookies_text):
    conn = get_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO user_settings (tg_user_id, yt_cookies)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id) DO UPDATE SET yt_cookies = %s
        """, (user_id, cookies_text, cookies_text))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error setting user cookies: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_user_cookies(user_id):
    conn = get_db()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT yt_cookies FROM user_settings WHERE tg_user_id = %s", (user_id,))
        res = cur.fetchone()
        return res["yt_cookies"] if res else None
    except Exception as e:
        print(f"Error getting user cookies: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# ==================== AUTOPILOT CONFIG ====================
def set_autopilot(user_id, topics, interval_days):
    conn = get_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO autopilot_settings (tg_user_id, topics, interval_days, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (tg_user_id) DO UPDATE SET topics = %s, interval_days = %s, is_active = TRUE
        """, (user_id, topics, interval_days, topics, interval_days))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error setting autopilot: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_autopilot(user_id):
    conn = get_db()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT topics, interval_days, is_active, last_run FROM autopilot_settings WHERE tg_user_id = %s", (user_id,))
        res = cur.fetchone()
        if res:
            return {"topics": res["topics"], "interval_days": res["interval_days"], "is_active": res["is_active"], "last_run": res["last_run"]}
        return None
    except Exception as e:
        print(f"Error getting autopilot: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def stop_autopilot(user_id):
    conn = get_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE autopilot_settings SET is_active = FALSE WHERE tg_user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error stopping autopilot: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_all_active_autopilots():
    conn = get_db()
    if not conn: return []
    cur = conn.cursor()
    try:
        cur.execute("SELECT tg_user_id, topics, interval_days, last_run FROM autopilot_settings WHERE is_active = TRUE")
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "tg_user_id": r["tg_user_id"],
                "topics": r["topics"],
                "interval_days": r["interval_days"],
                "last_run": r["last_run"]
            })
        return result
    except Exception as e:
        print(f"Error fetching active autopilots: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def update_autopilot_last_run(user_id):
    conn = get_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE autopilot_settings SET last_run = NOW() WHERE tg_user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating autopilot last run: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_autopost_task_by_id(task_id):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM autopost_tasks WHERE id = %s", (task_id,))
        return cur.fetchone()
    finally:
        conn.close()

def claim_pending_autopost_task():
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if 'psycopg2.extras' in db else conn.cursor()
        cur.execute('''
            UPDATE autopost_tasks 
            SET status = 'processing', updated_at = NOW() 
            WHERE id = (
                SELECT id FROM autopost_tasks 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                FOR UPDATE SKIP LOCKED 
                LIMIT 1
            ) 
            RETURNING *
        ''')
        task = cur.fetchone()
        conn.commit()
        return task
    except Exception as e:
        print("Claim task error:", e)
        conn.rollback()
        return None
    finally:
        conn.close()
