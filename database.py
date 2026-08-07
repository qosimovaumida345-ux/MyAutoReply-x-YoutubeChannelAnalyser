import sqlite3
import json
from datetime import datetime, timezone


DB_PATH = "analytics.db"


def get_db():
    """SQLite ulanishini qaytaradi"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Jadvallarni yaratish"""
    conn = get_db()
    cursor = conn.cursor()
    
    # YouTube kanal kuzatish jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL,
            channel_title TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, channel_id)
        )
    """)
    
    # Kanal statistikasi jadvali (har safar tekshirganda yangi yozuv)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            subscribers INTEGER DEFAULT 0,
            total_views INTEGER DEFAULT 0,
            total_videos INTEGER DEFAULT 0,
            snapshot_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Video statistikasi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            channel_id TEXT,
            title TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            snapshot_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database tayyor!")


def add_tracked_channel(chat_id: int, channel_id: str, channel_title: str):
    """Yangi kanalni kuzatishga qo'shish"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO tracked_channels (chat_id, channel_id, channel_title) VALUES (?, ?, ?)",
            (chat_id, channel_id, channel_title)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()


def remove_tracked_channel(chat_id: int, channel_id: str):
    """Kanalni kuzatishdan olib tashlash"""
    conn = get_db()
    conn.execute(
        "DELETE FROM tracked_channels WHERE chat_id = ? AND channel_id = ?",
        (chat_id, channel_id)
    )
    conn.commit()
    conn.close()


def get_tracked_channels(chat_id: int):
    """Foydalanuvchining kuzatayotgan kanallari ro'yxati"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tracked_channels WHERE chat_id = ?",
        (chat_id,)
    ).fetchall()
    conn.close()
    return rows


def save_channel_snapshot(channel_id: str, subscribers: int, total_views: int, total_videos: int):
    """Kanal statistikasining suratini saqlash"""
    conn = get_db()
    conn.execute(
        "INSERT INTO channel_snapshots (channel_id, subscribers, total_views, total_videos) VALUES (?, ?, ?, ?)",
        (channel_id, subscribers, total_views, total_videos)
    )
    conn.commit()
    conn.close()


def save_video_snapshot(video_id: str, channel_id: str, title: str, views: int, likes: int, comments: int):
    """Video statistikasining suratini saqlash"""
    conn = get_db()
    conn.execute(
        "INSERT INTO video_snapshots (video_id, channel_id, title, views, likes, comments) VALUES (?, ?, ?, ?, ?, ?)",
        (video_id, channel_id, title, views, likes, comments)
    )
    conn.commit()
    conn.close()


def get_channel_history(channel_id: str, limit: int = 14):
    """Kanal statistikasi tarixini olish (oxirgi N ta snapshot)"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM channel_snapshots WHERE channel_id = ? ORDER BY snapshot_at DESC LIMIT ?",
        (channel_id, limit)
    ).fetchall()
    conn.close()
    return rows


def get_channel_growth(channel_id: str):
    """Oxirgi 2 ta snapshotni solishtirish orqali o'sishni hisoblash"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM channel_snapshots WHERE channel_id = ? ORDER BY snapshot_at DESC LIMIT 2",
        (channel_id,)
    ).fetchall()
    conn.close()
    
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


# Boshlanganda jadvallarni yaratish
init_db()
