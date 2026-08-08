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
            updated_at TIMESTAMP DEFAULT NOW()
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
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
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

def create_autopost_task(tg_user_id, yt_channel_id, search_query, video_type, total_count):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO autopost_tasks (tg_user_id, yt_channel_id, search_query, video_type, total_count)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (tg_user_id, yt_channel_id, search_query, video_type, total_count))
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
