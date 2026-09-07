import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

from config import DATABASE_URL


def clean_database_url(url: str) -> str:
    """Tozalangan va xavfsiz SSL parametrli DB URL qaytaradi"""
    if not url:
        return ""
    clean = str(url).strip().strip('"').strip("'")
    if clean.startswith("postgres://"):
        clean = "postgresql://" + clean[11:]
    
    # Render va boshqa bulutli bazalar uchun SSL ni tekshirish
    if ("render.com" in clean or "dpg-" in clean) and "sslmode=" not in clean:
        clean += "?sslmode=require" if "?" not in clean else "&sslmode=require"
    return clean


def get_db(retries: int = 3):
    """PostgreSQL ulanishini qaytaradi (avtomatik qayta urinish bilan)"""
    from config import DATABASE_URL
    if not DATABASE_URL:
        print("DATABASE_URL topilmadi! Render PostgreSQL ni ulang.")
        return None
        
    url = clean_database_url(DATABASE_URL)
    
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
            conn.autocommit = False
            return conn
        except Exception as e:
            if attempt < retries:
                import time
                time.sleep(1.5)
            else:
                print(f"DATABASE ERROR (attempt {attempt}/{retries}): {e}")
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

    # Foydalanuvchilar balansi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_balances (
            tg_user_id BIGINT PRIMARY KEY,
            balance_uzs BIGINT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # To'lovlar tarixi (Telegram Stars & CryptoPay)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            payment_type TEXT NOT NULL,
            amount_original NUMERIC NOT NULL,
            currency TEXT NOT NULL,
            amount_uzs BIGINT NOT NULL,
            status TEXT DEFAULT 'pending',
            invoice_id TEXT,
            payload TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Engagement buyurtmalari (Layk, Obuna, Izoh)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS engagement_orders (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            order_type TEXT NOT NULL,
            target_url TEXT NOT NULL,
            target_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            completed_count INTEGER DEFAULT 0,
            total_cost BIGINT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # KYC & 3D Face Anti-Sybil tekshiruvi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kyc_verifications (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT UNIQUE NOT NULL,
            phone_number TEXT,
            passport_hash TEXT,
            face_hash TEXT,
            status TEXT DEFAULT 'verified',
            verified_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # AI API Keys do'koni (OpenRouter, Gemini, Groq kalitlari zaxirasi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys_stock (
            id SERIAL PRIMARY KEY,
            service_type TEXT NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            price_usd NUMERIC NOT NULL DEFAULT 3.0,
            price_uzs BIGINT NOT NULL DEFAULT 38000,
            status TEXT DEFAULT 'available',
            sold_to_user_id BIGINT,
            sold_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Telegram orqali tasdiqlangan telefon raqamlar (KYC Gate)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_phones (
            tg_user_id BIGINT PRIMARY KEY,
            phone_number TEXT NOT NULL,
            is_telegram_verified BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Dedicated Private Proxy zaxirasi ($3 — faqat download paytida ishlaydi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS proxies_stock (
            id SERIAL PRIMARY KEY,
            proxy_url TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'available',
            sold_to_user_id BIGINT,
            sold_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Autostream Cloud Sloti (Soatbay — $0.5 / soat)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS autostream_slots (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            video_url TEXT,
            stream_key TEXT,
            hours_paid INT NOT NULL,
            total_cost_uzs BIGINT NOT NULL,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP,
            pid INT
        )
    """)

    # Flux.1 AI Rasm Obunalari ($2 / hafta, 25 ta rasm)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flux_subscriptions (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT UNIQUE NOT NULL,
            generations_left INT DEFAULT 25,
            expires_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # VIP Cheksiz Pro Obuna ($15 / oy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vip_subscriptions (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Referal tizimi (10% keshbek)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            tg_user_id BIGINT PRIMARY KEY,
            referrer_id BIGINT NOT NULL,
            total_earned_uzs BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Umumiy xaridlar (500+ Prompt Pack, DeepLink QR, Unikalizatsiya, Shorts clipper)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_purchases (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            price_uzs BIGINT NOT NULL,
            payload TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Reseller & Developer API Foydalanuvchilari
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_api_keys (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT UNIQUE NOT NULL,
            api_key VARCHAR(128) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            last_used_at TIMESTAMP,
            total_requests BIGINT DEFAULT 0
        )
    """)

    # 1. Vaucherlar & Promokodlar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vouchers (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE NOT NULL,
            amount_uzs BIGINT NOT NULL,
            created_by BIGINT NOT NULL,
            used_by BIGINT,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 2. Mystery Box (Omadli Quti) Loglari
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mystery_box_logs (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            cost_uzs BIGINT NOT NULL,
            prize_type TEXT NOT NULL,
            prize_value TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 3. Omad G'ildiragi (Wheel of Fortune)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wheel_spins (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            is_free BOOLEAN DEFAULT TRUE,
            prize_type TEXT NOT NULL,
            prize_value TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 4. PvP Coin Flip Duellar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coinflip_duels (
            id SERIAL PRIMARY KEY,
            creator_id BIGINT NOT NULL,
            opponent_id BIGINT,
            amount_uzs BIGINT NOT NULL,
            choice_creator TEXT NOT NULL,
            status TEXT DEFAULT 'waiting',
            winner_id BIGINT,
            commission_uzs BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 5. Jekpot Mega Lotereya
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lottery_pools (
            id SERIAL PRIMARY KEY,
            ticket_price_uzs BIGINT DEFAULT 3000,
            pool_status TEXT DEFAULT 'active',
            winner_user_id BIGINT,
            total_collected_uzs BIGINT DEFAULT 0,
            prize_uzs BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            drawn_at TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lottery_tickets (
            id SERIAL PRIMARY KEY,
            pool_id INT REFERENCES lottery_pools(id),
            tg_user_id BIGINT NOT NULL,
            ticket_number INT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 6. Reseller Webhooks ($3/hafta)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reseller_webhooks (
            tg_user_id BIGINT PRIMARY KEY,
            webhook_url TEXT NOT NULL,
            secret_token TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 7. White-Label Botlar ($50 VIP)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS whitelabel_bots (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT NOT NULL,
            bot_token TEXT UNIQUE NOT NULL,
            bot_username TEXT,
            markup_percent INT DEFAULT 20,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
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

def get_ton_wallet() -> str:
    """Admin yoki tizim TON hamyon manzilini qaytaradi"""
    val = get_config("ton_wallet_address")
    if not val:
        val = os.getenv("TON_WALLET_ADDRESS", "")
    return (val or "").strip()

def set_ton_wallet(address: str) -> bool:
    """Admin TON hamyon manzilini bot_config ga saqlaydi"""
    return set_config("ton_wallet_address", address.strip())



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
    import tempfile
    for path in ["cookies.txt", "downloads/cookies.txt", os.path.join(tempfile.gettempdir(), "cookies.txt")]:
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


# ==================== BALANS VA TO'LOVLAR ====================

def get_user_balance(tg_user_id: int) -> int:
    """Foydalanuvchining UZS balansini qaytaradi (default: 0)"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return int(row["balance_uzs"]) if row and row["balance_uzs"] is not None else 0
    except Exception as e:
        print(f"get_user_balance error: {e}")
        return 0
    finally:
        conn.close()


def add_user_balance(tg_user_id: int, amount_uzs: int) -> int:
    """Foydalanuvchining hisobiga pul qo'shish va yangi balansni qaytarish"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                updated_at = NOW()
            RETURNING balance_uzs
        """, (tg_user_id, amount_uzs))
        row = cur.fetchone()
        conn.commit()
        return int(row["balance_uzs"]) if row else 0
    except Exception as e:
        conn.rollback()
        print(f"add_user_balance error: {e}")
        return 0
    finally:
        conn.close()


def deduct_user_balance(tg_user_id: int, amount_uzs: int) -> bool:
    """Balansdan pul yechish. Agar yetarli bo'lsa True, bo'lmasa False"""
    if amount_uzs <= 0: return True
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        row = cur.fetchone()
        current = int(row["balance_uzs"]) if row and row["balance_uzs"] is not None else 0
        if current < amount_uzs:
            conn.rollback()
            return False
        cur.execute(
            "UPDATE user_balances SET balance_uzs = balance_uzs - %s, updated_at = NOW() WHERE tg_user_id = %s",
            (amount_uzs, tg_user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"deduct_user_balance error: {e}")
        return False
    finally:
        conn.close()


def create_payment_transaction(tg_user_id: int, payment_type: str, amount_original: float, currency: str, amount_uzs: int, invoice_id: str = None, payload: str = None) -> int:
    """Yangi to'lov tranzaksiyasini yaratish (pending)"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payment_transactions (tg_user_id, payment_type, amount_original, currency, amount_uzs, status, invoice_id, payload)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s)
            RETURNING id
        """, (tg_user_id, payment_type, amount_original, currency, amount_uzs, invoice_id, payload))
        row = cur.fetchone()
        conn.commit()
        return int(row["id"]) if row else 0
    except Exception as e:
        conn.rollback()
        print(f"create_payment_transaction error: {e}")
        return 0
    finally:
        conn.close()


def get_payment_transaction(tx_id: int) -> dict:
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM payment_transactions WHERE id = %s", (tx_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_payment_transaction error: {e}")
        return None
    finally:
        conn.close()


def complete_payment_transaction(tx_id: int, invoice_id: str = None) -> dict:
    """Tranzaksiyani completed qilish va balansga qo'shish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM payment_transactions WHERE id = %s FOR UPDATE", (tx_id,))
        tx = cur.fetchone()
        if not tx:
            conn.rollback()
            return None
        if tx["status"] == "completed":
            conn.rollback()
            return dict(tx)
        
        cur.execute("""
            UPDATE payment_transactions
            SET status = 'completed',
                invoice_id = COALESCE(%s, invoice_id),
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (invoice_id, tx_id))
        updated_tx = cur.fetchone()
        
        tg_user_id = tx["tg_user_id"]
        amount_uzs = tx["amount_uzs"]
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                updated_at = NOW()
        """, (tg_user_id, amount_uzs))
        
        conn.commit()

        # Referral keshbek (10%)
        try:
            process_referral_cashback(tg_user_id, amount_uzs)
        except Exception as ref_e:
            print(f"process_referral_cashback trigger error: {ref_e}")

        return dict(updated_tx) if updated_tx else None
    except Exception as e:
        conn.rollback()
        print(f"complete_payment_transaction error: {e}")
        return None
    finally:
        conn.close()


def get_user_payment_history(tg_user_id: int, limit: int = 10):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM payment_transactions WHERE tg_user_id = %s ORDER BY created_at DESC LIMIT %s", (tg_user_id, limit))
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"get_user_payment_history error: {e}")
        return []
    finally:
        conn.close()


# ==================== ENGAGEMENT MARKETPLACE ====================

def create_engagement_order(tg_user_id: int, order_type: str, target_url: str, target_id: str, quantity: int, total_cost: int) -> int:
    """Layk, Obuna yoki Izoh buyurtmasini yaratish"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO engagement_orders (tg_user_id, order_type, target_url, target_id, quantity, total_cost, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """, (tg_user_id, order_type, target_url, target_id, quantity, total_cost))
        row = cur.fetchone()
        conn.commit()
        return int(row["id"]) if row else 0
    except Exception as e:
        conn.rollback()
        print(f"create_engagement_order error: {e}")
        return 0
    finally:
        conn.close()


def update_engagement_order(order_id: int, status: str, completed_count: int = None):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        if completed_count is not None:
            cur.execute(
                "UPDATE engagement_orders SET status = %s, completed_count = %s, updated_at = NOW() WHERE id = %s",
                (status, completed_count, order_id)
            )
        else:
            cur.execute(
                "UPDATE engagement_orders SET status = %s, updated_at = NOW() WHERE id = %s",
                (status, order_id)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"update_engagement_order error: {e}")
    finally:
        conn.close()


def get_user_engagement_orders(tg_user_id: int, limit: int = 10):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM engagement_orders WHERE tg_user_id = %s ORDER BY created_at DESC LIMIT %s", (tg_user_id, limit))
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"get_user_engagement_orders error: {e}")
        return []
    finally:
        conn.close()


# ==================== KYC & 3D FACE ANTI-SYBIL ====================

def check_kyc_duplicate(passport_hash: str = None, face_hash: str = None, phone_number: str = None, exclude_tg_user_id: int = None):
    """
    Pasport raqami, 3D yuz skaneri yoki telefon raqami allaqachon boshqa foydalanuvchiga
    tegishli ekanligini tekshirish.
    Qaytaradi: (is_duplicate: bool, reason: str)
    """
    conn = get_db()
    if not conn: return False, ""
    try:
        cur = conn.cursor()
        clauses = []
        params = []
        if passport_hash:
            clauses.append("passport_hash = %s")
            params.append(passport_hash)
        if face_hash:
            clauses.append("face_hash = %s")
            params.append(face_hash)
        if phone_number:
            clauses.append("phone_number = %s")
            params.append(phone_number)
            
        if not clauses:
            return False, ""
            
        query = f"SELECT * FROM kyc_verifications WHERE ({' OR '.join(clauses)})"
        if exclude_tg_user_id:
            query += " AND tg_user_id != %s"
            params.append(exclude_tg_user_id)
            
        cur.execute(query, tuple(params))
        row = cur.fetchone()
        if row:
            if passport_hash and row.get("passport_hash") == passport_hash:
                return True, "Ushbu pasport ma'lumotlari allaqachon boshqa hisobda ro'yxatdan o'tgan!"
            if face_hash and row.get("face_hash") == face_hash:
                return True, "Ushbu 3D yuz skaneri allaqachon boshqa Telegram akkauntiga biriktirilgan!"
            if phone_number and row.get("phone_number") == phone_number:
                return True, "Ushbu telefon raqam boshqa hisobda ro'yxatdan o'tgan!"
            return True, "Tizimda takroriy hisob aniqlandi!"
            
        return False, ""
    except Exception as e:
        print(f"check_kyc_duplicate error: {e}")
        return False, ""
    finally:
        conn.close()


def save_kyc_verification(tg_user_id: int, phone_number: str, passport_hash: str, face_hash: str) -> bool:
    """Foydalanuvchi KYC ma'lumotlarini saqlash"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO kyc_verifications (tg_user_id, phone_number, passport_hash, face_hash, status, verified_at)
            VALUES (%s, %s, %s, %s, 'verified', NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET phone_number = EXCLUDED.phone_number,
                passport_hash = EXCLUDED.passport_hash,
                face_hash = EXCLUDED.face_hash,
                status = 'verified',
                verified_at = NOW()
        """, (tg_user_id, phone_number, passport_hash, face_hash))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"save_kyc_verification error: {e}")
        return False
    finally:
        conn.close()


def is_user_kyc_verified(tg_user_id: int) -> bool:
    """Foydalanuvchi KYC dan o'tganmi?"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM kyc_verifications WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row: return False
        st = row["status"] if isinstance(row, dict) else row[0]
        return st == "verified"
    except Exception as e:
        print(f"is_user_kyc_verified error: {e}")
        return False
    finally:
        conn.close()


def get_user_kyc(tg_user_id: int):
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM kyc_verifications WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user_kyc error: {e}")
        return None
    finally:
        conn.close()


# ==================== AI API KEYS STOCK ====================

def add_api_key_to_stock(service_type: str, api_key: str, price_usd: float = None, price_uzs: int = None) -> bool:
    """Yangi API kalitni zaxiraga qo'shish"""
    conn = get_db()
    if not conn: return False
    st = service_type.strip().lower()
    if price_usd is None:
        if st == "openrouter": price_usd = 3.0
        elif st == "gemini": price_usd = 5.0
        elif st == "groq": price_usd = 0.8
        else: price_usd = 1.0
    if price_uzs is None:
        if st == "openrouter": price_uzs = 38000
        elif st == "gemini": price_uzs = 64000
        elif st == "groq": price_uzs = 10000
        else: price_uzs = 10000
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO api_keys_stock (service_type, api_key, price_usd, price_uzs, status)
            VALUES (%s, %s, %s, %s, 'available')
            ON CONFLICT (api_key) DO NOTHING
        """, (st, api_key.strip(), price_usd, price_uzs))
        inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"add_api_key_to_stock error: {e}")
        return False
    finally:
        conn.close()

def get_api_keys_stock_count() -> dict:
    """Mavjud kalitlar sonini olish: {'openrouter': count, 'gemini': count, 'groq': count}"""
    conn = get_db()
    res = {"openrouter": 0, "gemini": 0, "groq": 0}
    if not conn: return res
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT service_type, COUNT(*) as cnt
            FROM api_keys_stock
            WHERE status = 'available'
            GROUP BY service_type
        """)
        rows = cur.fetchall()
        for r in rows:
            st = r["service_type"].lower()
            res[st] = r["cnt"]
        return res
    except Exception as e:
        print(f"get_api_keys_stock_count error: {e}")
        return res
    finally:
        conn.close()

def purchase_api_key(tg_user_id: int, service_type: str) -> dict:
    """Foydalanuvchi hisobidan pul ayirib, zaxiradan 1 ta API kalit taqdim etish"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    st = service_type.strip().lower()
    try:
        cur = conn.cursor()
        # 1. Zaxiradan bitta kalitni qulflash
        cur.execute("""
            SELECT * FROM api_keys_stock
            WHERE service_type = %s AND status = 'available'
            LIMIT 1 FOR UPDATE
        """, (st,))
        key_row = cur.fetchone()
        if not key_row:
            conn.rollback()
            return {"ok": False, "out_of_stock": True, "error": "Zaxirada ushbu kalit qolmagan"}

        price_uzs = int(key_row["price_uzs"])
        
        # 2. Foydalanuvchi balansini tekshirish
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        bal_row = cur.fetchone()
        curr_bal = bal_row["balance_uzs"] if bal_row else 0
        if curr_bal < price_uzs:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": price_uzs,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Kerak: {price_uzs:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        # 3. Balansdan ayirish
        new_bal = curr_bal - price_uzs
        cur.execute("""
            UPDATE user_balances
            SET balance_uzs = %s, updated_at = NOW()
            WHERE tg_user_id = %s
        """, (new_bal, tg_user_id))

        # 4. Kalitni sold deb belgilash
        cur.execute("""
            UPDATE api_keys_stock
            SET status = 'sold', sold_to_user_id = %s, sold_at = NOW()
            WHERE id = %s
        """, (tg_user_id, key_row["id"]))

        conn.commit()
        return {
            "ok": True,
            "api_key": key_row["api_key"],
            "service_type": st,
            "price_uzs": price_uzs,
            "price_usd": float(key_row["price_usd"]),
            "new_balance": new_bal
        }
    except Exception as e:
        conn.rollback()
        print(f"purchase_api_key error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_purchased_keys(tg_user_id: int) -> list:
    """Foydalanuvchi sotib olgan barcha kalitlarni olish"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT service_type, api_key, price_usd, price_uzs, sold_at
            FROM api_keys_stock
            WHERE sold_to_user_id = %s
            ORDER BY sold_at DESC
        """, (tg_user_id,))
        return cur.fetchall() or []
    except Exception as e:
        print(f"get_user_purchased_keys error: {e}")
        return []
    finally:
        conn.close()


# ==================== TELEGRAM VERIFIED PHONES (KYC GATE) ====================

def save_telegram_phone(tg_user_id: int, phone_number: str) -> bool:
    """Telegram contact orqali yuborilgan tasdiqlangan raqamni saqlash"""
    conn = get_db()
    if not conn: return False
    clean_phone = phone_number.strip().replace(" ", "").replace("-", "")
    if not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_phones (tg_user_id, phone_number, is_telegram_verified, created_at)
            VALUES (%s, %s, TRUE, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET phone_number = EXCLUDED.phone_number,
                is_telegram_verified = TRUE
        """, (tg_user_id, clean_phone))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"save_telegram_phone error: {e}")
        return False
    finally:
        conn.close()

def get_telegram_phone(tg_user_id: int) -> str:
    """Foydalanuvchining tasdiqlangan Telegram telefon raqamini olish"""
    conn = get_db()
    if not conn: return ""
    try:
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM user_phones WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row: return ""
        return row["phone_number"] if isinstance(row, dict) else row[0]
    except Exception as e:
        print(f"get_telegram_phone error: {e}")
        return ""
    finally:
        conn.close()


# ==================== DEDICATED PROXIES STOCK ($3) ====================

def add_proxy_to_stock(proxy_url: str) -> bool:
    """Zaxiraga yangi private proxy qo'shish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO proxies_stock (proxy_url, status)
            VALUES (%s, 'available')
            ON CONFLICT (proxy_url) DO NOTHING
        """, (proxy_url.strip(),))
        inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"add_proxy_to_stock error: {e}")
        return False
    finally:
        conn.close()

def get_proxies_stock_count() -> int:
    """Mavjud erkin proxylar soni"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM proxies_stock WHERE status = 'available'")
        row = cur.fetchone()
        if not row: return 0
        return row["cnt"] if isinstance(row, dict) else row[0]
    except Exception as e:
        print(f"get_proxies_stock_count error: {e}")
        return 0
    finally:
        conn.close()

def purchase_proxy(tg_user_id: int) -> dict:
    """Foydalanuvchi hisobidan 38,000 so'm yechib, zaxiradan 1 ta dedicated proxy biriktirish"""
    price_uzs = 38000
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        # 1. Zaxiradan bitta proxyni qulflash
        cur.execute("""
            SELECT * FROM proxies_stock
            WHERE status = 'available'
            LIMIT 1 FOR UPDATE
        """)
        p_row = cur.fetchone()
        if not p_row:
            conn.rollback()
            return {"ok": False, "out_of_stock": True, "error": "Zaxirada hozircha bo'sh proxy qolmagan"}

        # 2. Balans tekshirish
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        bal_row = cur.fetchone()
        curr_bal = bal_row["balance_uzs"] if bal_row else 0
        if curr_bal < price_uzs:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": price_uzs,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Kerak: {price_uzs:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        # 3. Balansdan yechish
        new_bal = curr_bal - price_uzs
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))

        # 4. Proxyni sotilgan deb belgilash
        cur.execute("""
            UPDATE proxies_stock
            SET status = 'sold', sold_to_user_id = %s, sold_at = NOW()
            WHERE id = %s
        """, (tg_user_id, p_row["id"]))

        # 5. Userga download proxy qilib biriktirish
        proxy_url = p_row["proxy_url"]
        cur.execute("""
            INSERT INTO user_proxies (tg_user_id, proxy_url, is_active, updated_at)
            VALUES (%s, %s, TRUE, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET proxy_url = EXCLUDED.proxy_url, is_active = TRUE, updated_at = NOW()
        """, (tg_user_id, proxy_url))

        conn.commit()
        return {
            "ok": True,
            "proxy_url": proxy_url,
            "price_uzs": price_uzs,
            "new_balance": new_bal
        }
    except Exception as e:
        conn.rollback()
        print(f"purchase_proxy error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_download_proxy(tg_user_id: int) -> str:
    """Foydalanuvchining yuklab olish (download) uchun biriktirilgan proxiesini olish"""
    conn = get_db()
    if not conn: return ""
    try:
        cur = conn.cursor()
        cur.execute("SELECT proxy_url FROM user_proxies WHERE tg_user_id = %s AND is_active = TRUE", (tg_user_id,))
        row = cur.fetchone()
        if not row: return ""
        return row["proxy_url"] if isinstance(row, dict) else row[0]
    except Exception as e:
        print(f"get_user_download_proxy error: {e}")
        return ""
    finally:
        conn.close()


# ==================== AUTOSTREAM CLOUD SLOTS ($0.5 / SOAT) ====================

def purchase_autostream_slot(tg_user_id: int, hours: int, video_url: str = "", stream_key: str = "") -> dict:
    """Soatiga 4,000 so'm hisobidan Autostream bulutli sloti sotib olish"""
    price_per_hour = 4000
    total_cost = hours * price_per_hour
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        bal_row = cur.fetchone()
        curr_bal = bal_row["balance_uzs"] if bal_row else 0
        if curr_bal < total_cost:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": total_cost,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Kerak: {total_cost:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        new_bal = curr_bal - total_cost
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))

        cur.execute("""
            INSERT INTO autostream_slots (tg_user_id, video_url, stream_key, hours_paid, total_cost_uzs, status, started_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, 'active', NOW(), NOW() + (%s || ' hours')::INTERVAL)
            RETURNING id, expires_at
        """, (tg_user_id, video_url, stream_key, hours, total_cost, str(hours)))
        res = cur.fetchone()
        slot_id = res["id"] if isinstance(res, dict) else res[0]
        expires_at = res["expires_at"] if isinstance(res, dict) else res[1]

        conn.commit()
        return {
            "ok": True,
            "slot_id": slot_id,
            "hours": hours,
            "total_cost": total_cost,
            "new_balance": new_bal,
            "expires_at": str(expires_at)[:19]
        }
    except Exception as e:
        conn.rollback()
        print(f"purchase_autostream_slot error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_autostream_slots(tg_user_id: int) -> list:
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, hours_paid, total_cost_uzs, status, started_at, expires_at, (NOW() < expires_at) as is_running
            FROM autostream_slots
            WHERE tg_user_id = %s
            ORDER BY id DESC
            LIMIT 5
        """, (tg_user_id,))
        return cur.fetchall() or []
    except Exception as e:
        print(f"get_user_autostream_slots error: {e}")
        return []
    finally:
        conn.close()

def get_all_active_autostream_slots() -> list:
    """Muddati o'tmagan faol autostream slotlari"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM autostream_slots
            WHERE status = 'active' AND NOW() < expires_at
        """)
        return cur.fetchall() or []
    except Exception as e:
        print(f"get_all_active_autostream_slots error: {e}")
        return []
    finally:
        conn.close()

def expire_autostream_slot(slot_id: int) -> bool:
    """Muddati tugagan stream slotini to'xtatish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE autostream_slots SET status = 'expired' WHERE id = %s", (slot_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"expire_autostream_slot error: {e}")
        return False
    finally:
        conn.close()


# ==================== FLUX.1 AI IMAGE SUBSCRIPTION ($2 / HAFTA) ====================

def purchase_flux_subscription(tg_user_id: int) -> dict:
    """Haftasiga 25,000 so'm ($2) to'lab, 25 ta fotoreal rasm generatsiya kvotasini olish"""
    price_uzs = 25000
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        bal_row = cur.fetchone()
        curr_bal = bal_row["balance_uzs"] if bal_row else 0
        if curr_bal < price_uzs:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": price_uzs,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Kerak: {price_uzs:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        new_bal = curr_bal - price_uzs
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))

        cur.execute("""
            INSERT INTO flux_subscriptions (tg_user_id, generations_left, expires_at, updated_at)
            VALUES (%s, 25, NOW() + INTERVAL '7 days', NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET generations_left = flux_subscriptions.generations_left + 25,
                expires_at = GREATEST(flux_subscriptions.expires_at, NOW()) + INTERVAL '7 days',
                updated_at = NOW()
            RETURNING generations_left, expires_at
        """, (tg_user_id,))
        res = cur.fetchone()
        left = res["generations_left"] if isinstance(res, dict) else res[0]
        exp = res["expires_at"] if isinstance(res, dict) else res[1]

        conn.commit()
        return {
            "ok": True,
            "generations_left": left,
            "expires_at": str(exp)[:19],
            "new_balance": new_bal
        }
    except Exception as e:
        conn.rollback()
        print(f"purchase_flux_subscription error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_flux_quota(tg_user_id: int) -> dict:
    conn = get_db()
    if not conn: return {"active": False, "left": 0}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT generations_left, expires_at, (NOW() < expires_at AND generations_left > 0) as is_active
            FROM flux_subscriptions
            WHERE tg_user_id = %s
        """, (tg_user_id,))
        row = cur.fetchone()
        if not row: return {"active": False, "left": 0}
        active = bool(row["is_active"] if isinstance(row, dict) else row[2])
        left = int(row["generations_left"] if isinstance(row, dict) else row[0])
        exp = str(row["expires_at"] if isinstance(row, dict) else row[1])[:19]
        return {"active": active, "left": left, "expires_at": exp}
    except Exception as e:
        print(f"get_flux_quota error: {e}")
        return {"active": False, "left": 0}
    finally:
        conn.close()

def use_flux_credit(tg_user_id: int) -> bool:
    """1 ta rasm generatsiya kreditini kamaytirish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE flux_subscriptions
            SET generations_left = generations_left - 1, updated_at = NOW()
            WHERE tg_user_id = %s AND generations_left > 0 AND NOW() < expires_at
        """, (tg_user_id,))
        used = cur.rowcount > 0
        conn.commit()
        return used
    except Exception as e:
        conn.rollback()
        print(f"use_flux_credit error: {e}")
        return False
    finally:
        conn.close()


# ==================== VIP CHEKSIZ PRO OBUNA ($15 / OY) ====================

def purchase_vip_subscription(tg_user_id: int) -> dict:
    """Oylik 192,000 so'm ($15) VIP cheksiz tarif xarid qilish"""
    price_uzs = 192000
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        bal_row = cur.fetchone()
        curr_bal = bal_row["balance_uzs"] if bal_row else 0
        if curr_bal < price_uzs:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": price_uzs,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Kerak: {price_uzs:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        new_bal = curr_bal - price_uzs
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))

        cur.execute("""
            INSERT INTO vip_subscriptions (tg_user_id, expires_at, created_at)
            VALUES (%s, NOW() + INTERVAL '30 days', NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET expires_at = GREATEST(vip_subscriptions.expires_at, NOW()) + INTERVAL '30 days'
            RETURNING expires_at
        """, (tg_user_id,))
        res = cur.fetchone()
        exp = res["expires_at"] if isinstance(res, dict) else res[0]

        conn.commit()
        return {
            "ok": True,
            "expires_at": str(exp)[:19],
            "new_balance": new_bal
        }
    except Exception as e:
        conn.rollback()
        print(f"purchase_vip_subscription error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def is_user_vip(tg_user_id: int) -> bool:
    """Foydalanuvchi VIP abonentimi?"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT expires_at FROM vip_subscriptions
            WHERE tg_user_id = %s AND NOW() < expires_at
        """, (tg_user_id,))
        row = cur.fetchone()
        return bool(row)
    except Exception as e:
        print(f"is_user_vip error: {e}")
        return False
    finally:
        conn.close()


# ==================== REFERAL & KESHBEK TIZIMI (10%) ====================

def set_user_referrer(tg_user_id: int, referrer_id: int) -> bool:
    """Foydalanuvchini taklif qilgan odamni biriktirish"""
    if tg_user_id == referrer_id: return False
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO referrals (tg_user_id, referrer_id, total_earned_uzs, created_at)
            VALUES (%s, %s, 0, NOW())
            ON CONFLICT (tg_user_id) DO NOTHING
        """, (tg_user_id, referrer_id))
        inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"set_user_referrer error: {e}")
        return False
    finally:
        conn.close()

def get_user_referrer(tg_user_id: int) -> int:
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT referrer_id FROM referrals WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row: return 0
        return int(row["referrer_id"] if isinstance(row, dict) else row[0])
    except Exception as e:
        print(f"get_user_referrer error: {e}")
        return 0
    finally:
        conn.close()

def process_referral_cashback(tg_user_id: int, deposit_uzs: int) -> dict:
    """To'lov amalga oshirilganda taklif qilgan odamga 10% keshbek berish"""
    referrer_id = get_user_referrer(tg_user_id)
    if not referrer_id or deposit_uzs <= 0:
        return {"has_referrer": False}

    bonus = int(deposit_uzs * 0.10)
    if bonus <= 0:
        return {"has_referrer": False}

    conn = get_db()
    if not conn: return {"has_referrer": False}
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                updated_at = NOW()
        """, (referrer_id, bonus))

        cur.execute("""
            UPDATE referrals
            SET total_earned_uzs = total_earned_uzs + %s
            WHERE tg_user_id = %s
        """, (bonus, tg_user_id))

        conn.commit()
        return {
            "has_referrer": True,
            "referrer_id": referrer_id,
            "bonus_uzs": bonus
        }
    except Exception as e:
        conn.rollback()
        print(f"process_referral_cashback error: {e}")
        return {"has_referrer": False}
    finally:
        conn.close()

def get_referral_stats(tg_user_id: int) -> dict:
    """Foydalanuvchining referal statistikasi"""
    conn = get_db()
    res = {"invited_count": 0, "total_earned": 0}
    if not conn: return res
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(total_earned_uzs), 0) as earned
            FROM referrals
            WHERE referrer_id = %s
        """, (tg_user_id,))
        row = cur.fetchone()
        if row:
            res["invited_count"] = int(row["cnt"] if isinstance(row, dict) else row[0])
            res["total_earned"] = int(row["earned"] if isinstance(row, dict) else row[1])
        return res
    except Exception as e:
        print(f"get_referral_stats error: {e}")
        return res
    finally:
        conn.close()


# ==================== GENERAL PURCHASES (PROMPT PACK, DEEPLINK, UNIKALIZATSIYA, CLIPPER) ====================

def record_user_purchase(tg_user_id: int, item_type: str, item_name: str, price_uzs: int, payload: str = "") -> dict:
    """Balansdan pul yechib, xaridni saqlash"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        bal_row = cur.fetchone()
        curr_bal = bal_row["balance_uzs"] if bal_row else 0
        if curr_bal < price_uzs:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": price_uzs,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Kerak: {price_uzs:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        new_bal = curr_bal - price_uzs
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))

        cur.execute("""
            INSERT INTO user_purchases (tg_user_id, item_type, item_name, price_uzs, payload, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (tg_user_id, item_type, item_name, price_uzs, payload))
        p_res = cur.fetchone()
        purchase_id = p_res["id"] if isinstance(p_res, dict) else p_res[0]

        conn.commit()
        return {
            "ok": True,
            "purchase_id": purchase_id,
            "new_balance": new_bal,
            "item_type": item_type,
            "item_name": item_name
        }
    except Exception as e:
        conn.rollback()
        print(f"record_user_purchase error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_purchases(tg_user_id: int, item_type: str = None) -> list:
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        if item_type:
            cur.execute("""
                SELECT * FROM user_purchases
                WHERE tg_user_id = %s AND item_type = %s
                ORDER BY id DESC
            """, (tg_user_id, item_type))
        else:
            cur.execute("""
                SELECT * FROM user_purchases
                WHERE tg_user_id = %s
                ORDER BY id DESC
            """, (tg_user_id,))
        return cur.fetchall() or []
    except Exception as e:
        print(f"get_user_purchases error: {e}")
        return []
    finally:
        conn.close()


# ==================== RESELLER & DEVELOPER USER API KEYS ====================

def generate_secure_api_key() -> str:
    import secrets
    return "art_live_" + secrets.token_hex(20)

def get_or_create_user_api_key(tg_user_id: int) -> dict:
    """Foydalanuvchining shaxsiy Developer API kalitini olish yoki yangi yaratish"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_api_keys WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if row:
            api_key = row["api_key"] if isinstance(row, dict) else row[2]
            is_active = row["is_active"] if isinstance(row, dict) else row[3]
            created_at = row["created_at"] if isinstance(row, dict) else row[4]
            total_requests = row["total_requests"] if isinstance(row, dict) else row[6]
            return {
                "ok": True,
                "api_key": api_key,
                "is_active": is_active,
                "created_at": str(created_at),
                "total_requests": total_requests
            }
        
        # Yangi kalit yaratish
        new_key = generate_secure_api_key()
        cur.execute("""
            INSERT INTO user_api_keys (tg_user_id, api_key)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id) DO UPDATE SET api_key = EXCLUDED.api_key
            RETURNING api_key, created_at
        """, (tg_user_id, new_key))
        res = cur.fetchone()
        conn.commit()
        api_key = res["api_key"] if isinstance(res, dict) else res[0]
        created_at = res["created_at"] if isinstance(res, dict) else res[1]
        return {
            "ok": True,
            "api_key": api_key,
            "is_active": True,
            "created_at": str(created_at),
            "total_requests": 0
        }
    except Exception as e:
        conn.rollback()
        print(f"get_or_create_user_api_key error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def regenerate_user_api_key(tg_user_id: int) -> dict:
    """Foydalanuvchining API kalitini yangilash (Rotate)"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        new_key = generate_secure_api_key()
        cur.execute("""
            INSERT INTO user_api_keys (tg_user_id, api_key, is_active)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (tg_user_id) DO UPDATE 
            SET api_key = EXCLUDED.api_key, is_active = TRUE
            RETURNING api_key
        """, (tg_user_id, new_key))
        res = cur.fetchone()
        conn.commit()
        api_key = res["api_key"] if isinstance(res, dict) else res[0]
        return {"ok": True, "api_key": api_key}
    except Exception as e:
        conn.rollback()
        print(f"regenerate_user_api_key error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_by_api_key(api_key: str) -> dict:
    """API kalit orqali foydalanuvchi ma'lumotlari va balansini tekshirish"""
    conn = get_db()
    if not conn: return None
    key_clean = str(api_key).strip()
    if not key_clean: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT k.tg_user_id, k.is_active, k.total_requests,
                   COALESCE(b.balance_uzs, 0) as balance_uzs,
                   COALESCE(v.status, 'unverified') as kyc_status
            FROM user_api_keys k
            LEFT JOIN user_balances b ON b.tg_user_id = k.tg_user_id
            LEFT JOIN kyc_verifications v ON v.tg_user_id = k.tg_user_id
            WHERE k.api_key = %s
        """, (key_clean,))
        row = cur.fetchone()
        if not row: return None
        if isinstance(row, dict):
            return {
                "tg_user_id": row["tg_user_id"],
                "is_active": row["is_active"],
                "balance_uzs": int(row["balance_uzs"]),
                "kyc_status": row["kyc_status"],
                "total_requests": int(row["total_requests"])
            }
        else:
            return {
                "tg_user_id": row[0],
                "is_active": row[1],
                "total_requests": int(row[2]),
                "balance_uzs": int(row[3]),
                "kyc_status": row[4]
            }
    except Exception as e:
        print(f"get_user_by_api_key error: {e}")
        return None
    finally:
        conn.close()

def log_api_key_usage(api_key: str):
    """API chaqiruv hisoblagichini oshirish"""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_api_keys 
            SET total_requests = total_requests + 1, last_used_at = NOW()
            WHERE api_key = %s
        """, (api_key.strip(),))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"log_api_key_usage error: {e}")
    finally:
        conn.close()


