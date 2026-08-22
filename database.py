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
        
    url = DATABASE_URL
    if "onrender.com" in url and "sslmode=" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"
        
    try:
        conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        return None


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
            yt_channel_username TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TIMESTAMP,
            connected_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tg_user_id, yt_channel_id)
        )
    """)
    
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='yt_connections' AND column_name='yt_channel_username'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE yt_connections ADD COLUMN yt_channel_username TEXT")
        
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='yt_connections' AND column_name='stream_key'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE yt_connections ADD COLUMN stream_key TEXT")
        
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='yt_connections' AND column_name='stream_active'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE yt_connections ADD COLUMN stream_active BOOLEAN DEFAULT FALSE")
    
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
            updated_at TIMESTAMP DEFAULT NOW(),
            apply_watermark BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Check if apply_watermark column exists
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='autopost_tasks' AND column_name='apply_watermark'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE autopost_tasks ADD COLUMN apply_watermark BOOLEAN DEFAULT FALSE")

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
    
    # Stream vazifalar (streamer worker uchun queue)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stream_tasks (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            search_query TEXT NOT NULL,
            stream_key TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            worker_id TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
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
            updated_at TIMESTAMP DEFAULT NOW(),
            apply_watermark BOOLEAN DEFAULT FALSE
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
    cur.execute('''
        CREATE TABLE IF NOT EXISTS autopilot_settings (
            tg_user_id BIGINT PRIMARY KEY,
            topics TEXT,
            interval_days INTEGER DEFAULT 2,
            last_run TIMESTAMP DEFAULT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    # Check and add yt_cookies column if it doesn't exist
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user_settings' AND column_name='yt_cookies'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE user_settings ADD COLUMN yt_cookies TEXT;")
        
    # Check and add default_yt_channel_id column if it doesn't exist
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user_settings' AND column_name='default_yt_channel_id'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE user_settings ADD COLUMN default_yt_channel_id TEXT;")
    
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

def set_default_account(tg_user_id, channel_id):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_settings (tg_user_id, default_yt_channel_id) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO UPDATE SET default_yt_channel_id = %s",
            (tg_user_id, channel_id, channel_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato default account saqlashda: {e}")
        return False
    finally:
        conn.close()

def get_default_account(tg_user_id):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT default_yt_channel_id FROM user_settings WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return row["default_yt_channel_id"] if row else None
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

def save_yt_connection(tg_user_id, yt_channel_id, yt_channel_title, yt_channel_username, access_token, refresh_token, token_expiry=None):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()

        # ? FIX 1: Avval bu channel_id boshqa tg_user_id ga tegishli ekanini tekshir
        cur.execute(
            "SELECT tg_user_id FROM yt_connections WHERE yt_channel_id = %s",
            (yt_channel_id,)
        )
        existing = cur.fetchone()

        if existing and existing['tg_user_id'] != tg_user_id:
            # Bir xil kanal, boshqa foydalanuvchi -> eski yozuvni yangi foydalanuvchiga ko'chir
            print(f"[DB] Kanal {yt_channel_id} allaqachon mavjud (tg={existing['tg_user_id']}), tg={tg_user_id} ga yangilanmoqda")
            cur.execute("""
                UPDATE yt_connections
                SET tg_user_id      = %s,
                    yt_channel_title = %s,
                    yt_channel_username = %s,
                    access_token    = %s,
                    refresh_token   = %s,
                    token_expiry    = %s,
                    connected_at    = NOW()
                WHERE yt_channel_id = %s
            """, (tg_user_id, yt_channel_title, yt_channel_username, access_token, refresh_token, token_expiry, yt_channel_id))
        else:
            # ? FIX 2: ON CONFLICT -> yt_channel_title ham yangilansin (avval yangilanmayotgan edi!)
            cur.execute("""
                INSERT INTO yt_connections
                    (tg_user_id, yt_channel_id, yt_channel_title, yt_channel_username, access_token, refresh_token, token_expiry)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tg_user_id, yt_channel_id)
                DO UPDATE SET
                    yt_channel_title = EXCLUDED.yt_channel_title,
                    yt_channel_username = EXCLUDED.yt_channel_username,
                    access_token    = EXCLUDED.access_token,
                    refresh_token   = EXCLUDED.refresh_token,
                    token_expiry    = EXCLUDED.token_expiry,
                    connected_at    = NOW()
            """, (tg_user_id, yt_channel_id, yt_channel_title, yt_channel_username, access_token, refresh_token, token_expiry))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[DB] save_yt_connection xato: {e}")
        return False
    finally:
        conn.close()


def get_yt_connection(tg_user_id):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        
        # Default account ni tekshiramiz
        cur.execute("SELECT default_yt_channel_id FROM user_settings WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        default_ch_id = row["default_yt_channel_id"] if row else None
        
        if default_ch_id:
            cur.execute("SELECT * FROM yt_connections WHERE tg_user_id = %s AND yt_channel_id = %s", (tg_user_id, default_ch_id))
            conn_data = cur.fetchone()
            if conn_data:
                return conn_data
                
        # Agar default yo'q bo'lsa yoki topilmasa, eng oxirgi ulanganini olamiz
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


def get_every_yt_connection():
    """Barcha foydalanuvchilarning barcha ulangan YouTube akkauntlarini olish (mass action uchun)"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM yt_connections WHERE access_token IS NOT NULL")
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
        try:
            cur.execute('''
                INSERT INTO autopost_tasks (tg_user_id, yt_channel_id, search_query, video_type, total_count, apply_watermark)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            ''', (tg_user_id, yt_channel_id, search_query, video_type, total_count, apply_watermark))
        except Exception:
            conn.rollback()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO autopost_tasks (tg_user_id, yt_channel_id, search_query, video_type, total_count)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (tg_user_id, yt_channel_id, search_query, video_type, total_count))
            
        res = cur.fetchone()
        task_id = res["id"] if isinstance(res, dict) else res[0]
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

def reset_all_data():
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        tables = [
            "autopost_history", "autopost_tasks", "autopilot_settings", 
            "channel_snapshots", "user_settings", "yt_connections"
        ]
        for table in tables:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE")
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False
    finally:
        conn.close()


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

def get_user_cookies(user_id=None):
    import os
    conn = get_db()
    if conn:
        cur = conn.cursor()
        try:
            if user_id:
                cur.execute("SELECT yt_cookies FROM user_settings WHERE tg_user_id = %s", (user_id,))
                res = cur.fetchone()
                if res and res.get("yt_cookies") and len(res["yt_cookies"].strip()) > 20:
                    return res["yt_cookies"].strip()
            
            # Fallback: Agar bu userda bo'lmasa, bazadagi istalgan cookie ni olish
            cur.execute("SELECT yt_cookies FROM user_settings WHERE yt_cookies IS NOT NULL AND length(yt_cookies) > 20 ORDER BY tg_user_id ASC LIMIT 1")
            res = cur.fetchone()
            if res and res.get("yt_cookies") and len(res["yt_cookies"].strip()) > 20:
                return res["yt_cookies"].strip()
        except Exception as e:
            print(f"Error getting user cookies: {e}")
        finally:
            cur.close()
            conn.close()

    # Fallback 2: Fayl tizimidagi cookies.txt ni tekshirish
    for path in ["cookies.txt", "downloads/cookies.txt", "/tmp/cookies.txt"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if len(content) > 20:
                        return content
            except Exception as e:
                print(f"Error reading {path}: {e}")

    return None

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
        cur = conn.cursor()
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

def claim_autopost_task_by_id(task_id):
    """
    Masofaviy worker (HTTP orqali push qilingan) aniq bitta task_id ni oladi.
    claim_pending_autopost_task bilan bir xil, faqat tasodifiy pending emas —
    main tomonidan tanlangan ID. FOR UPDATE SKIP LOCKED tufayli hali ham
    xavfsiz — agar boshqa worker allaqachon shu taskni olgan bo'lsa, None qaytadi.
    """
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute('''
            UPDATE autopost_tasks
            SET status = 'processing', updated_at = NOW()
            WHERE id = (
                SELECT id FROM autopost_tasks
                WHERE id = %s AND status = 'pending'
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        ''', (task_id,))
        task = cur.fetchone()
        conn.commit()
        return task
    except Exception as e:
        print("claim_autopost_task_by_id error:", e)
        conn.rollback()
        return None
    finally:
        conn.close()

def update_yt_tokens(tg_user_id, yt_channel_id, access_token, refresh_token=None):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        if refresh_token:
            cur.execute("""
                UPDATE yt_connections 
                SET access_token = %s, refresh_token = %s
                WHERE tg_user_id = %s AND yt_channel_id = %s
            """, (access_token, refresh_token, tg_user_id, yt_channel_id))
        else:
            cur.execute("""
                UPDATE yt_connections 
                SET access_token = %s
                WHERE tg_user_id = %s AND yt_channel_id = %s
            """, (access_token, tg_user_id, yt_channel_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating yt_tokens: {e}")
        return False
    finally:
        conn.close()

def set_stream_key(tg_user_id, stream_key):
    conn = get_db()
    if not conn: return False
    try:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT default_yt_channel_id FROM user_settings WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        default_ch_id = row["default_yt_channel_id"] if row else None

        if default_ch_id:
            cur.execute("UPDATE yt_connections SET stream_key = %s WHERE tg_user_id = %s AND yt_channel_id = %s", (stream_key, tg_user_id, default_ch_id))
        else:
            cur.execute("UPDATE yt_connections SET stream_key = %s WHERE tg_user_id = %s", (stream_key, tg_user_id))

        conn.commit()
        return True
    except Exception as e:
        print("set_stream_key error:", e)
        return False
    finally:
        conn.close()

def get_stream_key(tg_user_id):
    conn = get_db()
    if not conn: return None
    try:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT default_yt_channel_id FROM user_settings WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        default_ch_id = row["default_yt_channel_id"] if row else None

        if default_ch_id:
            cur.execute("SELECT stream_key FROM yt_connections WHERE tg_user_id = %s AND yt_channel_id = %s", (tg_user_id, default_ch_id))
        else:
            cur.execute("SELECT stream_key FROM yt_connections WHERE tg_user_id = %s ORDER BY connected_at DESC LIMIT 1", (tg_user_id,))

        res = cur.fetchone()
        return res["stream_key"] if res else None
    except Exception as e:
        print("get_stream_key error:", e)
        return None
    finally:
        conn.close()


# ==================== STREAM TASK QUEUE ====================

def create_stream_task(tg_user_id, chat_id, search_query, stream_key):
    """Stream vazifasini DB ga qo'shish (streamer worker uchun)"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        # Jadval yo'q bo'lsa yaratish (init_db ishlamagan bo'lsa ham ishlaydi)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stream_tasks (
                id SERIAL PRIMARY KEY,
                tg_user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                search_query TEXT NOT NULL,
                stream_key TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                worker_id TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()

        # Bitta foydalanuvchi uchun bir vaqtda bitta aktiv task bo'lishi kerak
        cur.execute(
            "UPDATE stream_tasks SET status='cancelled' WHERE tg_user_id=%s AND status IN ('pending','running')",
            (tg_user_id,)
        )
        cur.execute(
            """INSERT INTO stream_tasks (tg_user_id, chat_id, search_query, stream_key, status)
               VALUES (%s, %s, %s, %s, 'pending') RETURNING id""",
            (tg_user_id, chat_id, search_query, stream_key)
        )
        task_id = cur.fetchone()["id"]
        conn.commit()
        return task_id
    except Exception as e:
        print("create_stream_task error:", e)
        conn.rollback()
        return None
    finally:
        conn.close()


def _ensure_stream_tasks_table(cur, conn):
    """stream_tasks jadvali yo'q bo'lsa yaratish (har doim xavfsiz)"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stream_tasks (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            search_query TEXT NOT NULL,
            stream_key TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            worker_id TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()


def claim_pending_stream_task(worker_id):
    """Bo'sh streamer worker tomonidan vazifa olish (atomic)"""
    conn = get_db()
    if not conn: return None
    try:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        _ensure_stream_tasks_table(cur, conn)
        cur.execute("""
            UPDATE stream_tasks
            SET status = 'running', worker_id = %s, updated_at = NOW()
            WHERE id = (
                SELECT id FROM stream_tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        """, (worker_id,))
        task = cur.fetchone()
        conn.commit()
        return dict(task) if task else None
    except Exception as e:
        print("claim_pending_stream_task error:", e)
        conn.rollback()
        return None
    finally:
        conn.close()


def claim_stream_task_by_id(task_id, worker_id):
    """
    Masofaviy streamer (HTTP orqali push qilingan) aniq bitta stream task_id
    ni oladi. claim_pending_stream_task bilan bir xil mantiq, faqat main
    tomonidan tanlangan ID. FOR UPDATE SKIP LOCKED bilan xavfsiz.
    """
    conn = get_db()
    if not conn: return None
    try:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        _ensure_stream_tasks_table(cur, conn)
        cur.execute("""
            UPDATE stream_tasks
            SET status = 'running', worker_id = %s, updated_at = NOW()
            WHERE id = (
                SELECT id FROM stream_tasks
                WHERE id = %s AND status = 'pending'
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        """, (worker_id, task_id))
        task = cur.fetchone()
        conn.commit()
        return dict(task) if task else None
    except Exception as e:
        print("claim_stream_task_by_id error:", e)
        conn.rollback()
        return None
    finally:
        conn.close()


def update_stream_task(task_id, status):
    """Stream vazifasi statusini yangilash"""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE stream_tasks SET status=%s, updated_at=NOW() WHERE id=%s",
            (status, task_id)
        )
        conn.commit()
    except Exception as e:
        print("update_stream_task error:", e)
    finally:
        conn.close()


def cancel_user_stream_tasks(tg_user_id):
    """Foydalanuvchining barcha aktiv stream tasklerini bekor qilish"""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE stream_tasks SET status='cancelled', updated_at=NOW() WHERE tg_user_id=%s AND status IN ('pending','running')",
            (tg_user_id,)
        )
        conn.commit()
    except Exception as e:
        print("cancel_user_stream_tasks error:", e)
    finally:
        conn.close()


def get_user_stream_status(tg_user_id):
    """Foydalanuvchining joriy stream task statusini olish"""
    conn = get_db()
    if not conn: return None
    try:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        _ensure_stream_tasks_table(cur, conn)
        cur.execute(
            "SELECT * FROM stream_tasks WHERE tg_user_id=%s AND status IN ('pending','running') ORDER BY created_at DESC LIMIT 1",
            (tg_user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print("get_user_stream_status error:", e)
        return None
    finally:
        conn.close()