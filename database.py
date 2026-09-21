import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

from config import DATABASE_URL

# ==================== HIGH-SPEED IN-MEMORY TTL CACHE ====================
_CACHE_STORE = {}

def _get_cached(key):
    entry = _CACHE_STORE.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None

def _set_cached(key, val, ttl_seconds=180):
    _CACHE_STORE[key] = (val, time.time() + ttl_seconds)

def _invalidate_cached(key):
    _CACHE_STORE.pop(key, None)


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


from psycopg2.pool import ThreadedConnectionPool

_DB_POOL = None

class _PooledConnWrapper:
    """Connection pool dan olingan ulanishni xavfsiz boshqarish wrapper'i"""
    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._closed = False

    def close(self):
        if not self._closed and self._pool is not None and self._conn is not None:
            self._closed = True
            try:
                self._conn.rollback()
            except Exception:
                pass
            try:
                self._pool.putconn(self._conn)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def _get_pool():
    global _DB_POOL
    if _DB_POOL is None or getattr(_DB_POOL, "closed", True):
        from config import DATABASE_URL
        if not DATABASE_URL:
            return None
        url = clean_database_url(DATABASE_URL)
        try:
            _DB_POOL = ThreadedConnectionPool(minconn=2, maxconn=20, dsn=url, cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"DATABASE POOL INIT ERROR: {e}")
            _DB_POOL = None
    return _DB_POOL


def get_db(retries: int = 3):
    """Doimiy ulanishlar zaxirasidan (Pool) o'ta tezkor (1-2ms) ulanish qaytaradi"""
    pool = _get_pool()
    if pool:
        for _ in range(retries):
            try:
                conn = pool.getconn()
                if conn.closed:
                    try:
                        pool.putconn(conn, close=True)
                    except Exception:
                        pass
                    continue
                conn.autocommit = False
                return _PooledConnWrapper(pool, conn)
            except Exception:
                pass

    # Fallback agar pool bo'sh yoki xato bersa
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
                time.sleep(1.0)
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

    # AI Video Studio $20/oy obunalar jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_video_subscriptions (
            tg_user_id BIGINT PRIMARY KEY,
            expires_at TIMESTAMP NOT NULL,
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

    # 2.1 Telegram Stars Pending Gifts (Real Telegram Sovg'alar navbati va arxivi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_gifts (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            gift_id TEXT NOT NULL,
            tier_key TEXT,
            case_name TEXT,
            prize_name TEXT,
            prize_stars INT DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            sent_at TIMESTAMP
        )
    """)

    # 2.2 Do'stga Sovg'a Qilingan Keyslar (Gift Case Vouchers)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gift_case_vouchers (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            tier_key TEXT NOT NULL,
            case_name TEXT,
            price_stars INT NOT NULL,
            created_by BIGINT NOT NULL,
            claimed_by BIGINT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW(),
            claimed_at TIMESTAMP
        )
    """)

    # 2.3 Bad Luck Protection & Mystery Case Foydalanuvchi Statistikasi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_mystery_stats (
            tg_user_id BIGINT PRIMARY KEY,
            bad_luck_streak INT DEFAULT 0,
            total_cases_opened INT DEFAULT 0,
            total_stars_spent BIGINT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 2.4 Bot foydalanuvchilarining yagona reestri (Admin boshqaruvi uchun)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_users (
            tg_user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            last_active_at TIMESTAMP DEFAULT NOW(),
            is_banned BOOLEAN DEFAULT FALSE,
            admin_notes TEXT
        )
    """)

    # Mavjud barcha jadvallardan bot_users jadvalini avtomatik to'ldirish (Auto-backfill)
    try:
        cur.execute("""
            INSERT INTO bot_users (tg_user_id, created_at, last_active_at)
            SELECT DISTINCT tg_user_id, NOW(), NOW()
            FROM user_balances
            ON CONFLICT (tg_user_id) DO NOTHING;
            
            INSERT INTO bot_users (tg_user_id, created_at, last_active_at)
            SELECT DISTINCT tg_user_id, NOW(), NOW()
            FROM user_phones
            ON CONFLICT (tg_user_id) DO NOTHING;

            INSERT INTO bot_users (tg_user_id, created_at, last_active_at)
            SELECT DISTINCT tg_user_id, NOW(), NOW()
            FROM kyc_verifications
            ON CONFLICT (tg_user_id) DO NOTHING;
            
            INSERT INTO bot_users (tg_user_id, created_at, last_active_at)
            SELECT DISTINCT tg_user_id, NOW(), NOW()
            FROM user_mystery_stats
            ON CONFLICT (tg_user_id) DO NOTHING;
        """)
    except Exception as _bfe:
        print(f"bot_users auto-backfill note: {_bfe}")


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
    
    # 8. Foydalanuvchilar Tili (Multi-Language: uz, ru, en, es)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_languages (
            tg_user_id BIGINT PRIMARY KEY,
            language TEXT DEFAULT 'uz',
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 9. Instagram Auto-Sync Channels & Synced Posts
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ig_sync_channels (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            ig_username TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            check_interval_mins INT DEFAULT 60,
            last_checked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tg_user_id, ig_username)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ig_synced_posts (
            id SERIAL PRIMARY KEY,
            sync_channel_id INT REFERENCES ig_sync_channels(id) ON DELETE CASCADE,
            ig_post_id TEXT NOT NULL,
            media_url TEXT,
            yt_video_id TEXT,
            status TEXT DEFAULT 'synced',
            synced_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(sync_channel_id, ig_post_id)
        )
    """)

    # 10. CapCut Desktop & Pro Tools Referral Pool
    cur.execute("""
        CREATE TABLE IF NOT EXISTS capcut_referral_pool (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            invite_link TEXT NOT NULL UNIQUE,
            service_name TEXT DEFAULT 'capcut',
            total_clicks INT DEFAULT 0,
            total_claims INT DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS capcut_subscriptions (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            plan_days INT NOT NULL,
            price_uzs BIGINT NOT NULL,
            license_key TEXT,
            expires_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 11. Support Desk (Gemini AI & Live Admin Tickets)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            role_intent TEXT DEFAULT 'general',
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id SERIAL PRIMARY KEY,
            ticket_id INT REFERENCES support_tickets(id) ON DELETE CASCADE,
            sender_type TEXT NOT NULL,
            message_text TEXT NOT NULL,
            media_file_id TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 12. P2P Conditional Cheklar & Check Claims
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conditional_checks (
            id SERIAL PRIMARY KEY,
            check_code VARCHAR(64) UNIQUE NOT NULL,
            creator_id BIGINT NOT NULL,
            total_amount_uzs BIGINT NOT NULL,
            amount_per_user_uzs BIGINT NOT NULL,
            max_claims INT DEFAULT 1,
            claims_count INT DEFAULT 0,
            required_channel TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS check_claims (
            id SERIAL PRIMARY KEY,
            check_id INT REFERENCES conditional_checks(id) ON DELETE CASCADE,
            tg_user_id BIGINT NOT NULL,
            amount_received_uzs BIGINT NOT NULL,
            claimed_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(check_id, tg_user_id)
        )
    """)

    # 13. Antifraud Banned Users (Kanaldan chiqqanlar)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS banned_antifraud_users (
            tg_user_id BIGINT PRIMARY KEY,
            reason TEXT,
            banned_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 14. Promo-kodlar & Kuponlar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE NOT NULL,
            discount_percent INT DEFAULT 0,
            balance_bonus_uzs BIGINT DEFAULT 0,
            max_uses INT DEFAULT 100,
            current_uses INT DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_redemptions (
            id SERIAL PRIMARY KEY,
            promo_id INT REFERENCES promo_codes(id) ON DELETE CASCADE,
            tg_user_id BIGINT NOT NULL,
            redeemed_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(promo_id, tg_user_id)
        )
    """)

    # 15. Pul Yechish (Stars & TON Cashout)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cashout_requests (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            method TEXT NOT NULL,
            target_address TEXT NOT NULL,
            amount_uzs BIGINT NOT NULL,
            currency_equivalent TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            processed_at TIMESTAMP
        )
    """)

    # 16. TON Connect Wallet (Mini App orqali ulangan hamyonlar)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_ton_wallets (
            tg_user_id BIGINT PRIMARY KEY,
            wallet_address TEXT NOT NULL,
            wallet_name TEXT,
            chain TEXT DEFAULT 'mainnet',
            connected_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 17. NFT Items (3D Model + Polygon Lazy Mint)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nft_items (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            glb_file_id TEXT,
            preview_image_id TEXT,
            ipfs_metadata_uri TEXT,
            polygon_token_id BIGINT,
            voucher_data TEXT,
            price_matic NUMERIC DEFAULT 0,
            price_uzs BIGINT DEFAULT 0,
            status TEXT DEFAULT 'draft',
            buyer_user_id BIGINT,
            minted_tx_hash TEXT,
            video_file_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # 18. HUMO Karta To'lovlari (P2P SMS avtomatlashtirish)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS humo_deposits (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            amount_uzs INTEGER NOT NULL,
            unique_amount_uzs INTEGER NOT NULL,
            sender_card_last4 VARCHAR(10),
            card_number VARCHAR(30),
            status VARCHAR(20) DEFAULT 'pending',
            sms_raw_text TEXT,
            sender_name VARCHAR(100),
            rrn_code VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_humo_deposits_pending ON humo_deposits (status, unique_amount_uzs)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_humo_deposits_user ON humo_deposits (tg_user_id, status)")

    # 18.1 HUMO Xabarnomalar Duplikatsiyasini Oldini Olish (Processed Message IDs)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS humo_processed_messages (
            message_id BIGINT PRIMARY KEY,
            exact_amount BIGINT,
            payment_id VARCHAR(100),
            processed_at TIMESTAMP DEFAULT NOW(),
            msg_time TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_humo_processed_messages_msg_id ON humo_processed_messages (message_id)")

    # 18. Mini-Games Sessions (Wheel, Mystery Box, Duel, Lottery)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS casino_game_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(64) UNIQUE NOT NULL,
            tg_user_id BIGINT NOT NULL,
            game_type VARCHAR(32) NOT NULL,
            bet_amount_uzs BIGINT NOT NULL,
            current_multiplier NUMERIC(10, 2) DEFAULT 1.0,
            status VARCHAR(32) DEFAULT 'active',
            server_seed TEXT NOT NULL,
            encrypted_hash VARCHAR(64) NOT NULL,
            game_state JSONB NOT NULL DEFAULT '{}'::jsonb,
            win_amount_uzs BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_casino_sessions_user ON casino_game_sessions(tg_user_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_casino_sessions_type ON casino_game_sessions(game_type)")

    # 19. Crash Rounds (legacy, o'chirilgan)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crash_rounds (
            id SERIAL PRIMARY KEY,
            round_number BIGINT NOT NULL,
            crash_multiplier NUMERIC(10, 2) NOT NULL,
            server_seed TEXT NOT NULL,
            encrypted_hash VARCHAR(64) NOT NULL,
            status VARCHAR(32) DEFAULT 'betting',
            started_at TIMESTAMP DEFAULT NOW(),
            crashed_at TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crash_rounds_status ON crash_rounds(status)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS crash_bets (
            id SERIAL PRIMARY KEY,
            round_id BIGINT REFERENCES crash_rounds(id) ON DELETE CASCADE,
            tg_user_id BIGINT NOT NULL,
            user_name TEXT,
            slot_num INT NOT NULL DEFAULT 1,
            bet_amount_uzs BIGINT NOT NULL,
            auto_cashout_multiplier NUMERIC(10, 2) DEFAULT 0,
            cashed_out_multiplier NUMERIC(10, 2) DEFAULT 0,
            win_amount_uzs BIGINT DEFAULT 0,
            status VARCHAR(32) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crash_bets_round ON crash_bets(round_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crash_bets_user ON crash_bets(tg_user_id, round_id)")

    # VenteBot Reseller Buyurtmalar jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventebot_reseller_orders (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            product_id INT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INT DEFAULT 1,
            amount_uzs BIGINT NOT NULL,
            amount_usd NUMERIC(10, 2) NOT NULL,
            delivery_type TEXT,
            activation_identifier TEXT,
            status VARCHAR(32) DEFAULT 'COMPLETED',
            ventebot_order_id INT,
            delivered_data TEXT,
            idempotency_key TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ventebot_orders_user ON ventebot_reseller_orders(tg_user_id)")
    
    # VIP Obunalar jadvali (69,000 UZS / oy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_vip_subscriptions (
            tg_user_id BIGINT PRIMARY KEY,
            is_vip BOOLEAN DEFAULT FALSE,
            vip_expires_at TIMESTAMP,
            plan_type TEXT DEFAULT 'vip_69k',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_vip_expires ON user_vip_subscriptions(vip_expires_at)")

    # Kanal Konkurslari jadvali (@CreatorFlow_Store)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_contests (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            prize_text TEXT NOT NULL,
            channel_msg_id BIGINT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW(),
            ends_at TIMESTAMP
        )
    """)

    # Konkurs Ishtirokchilari jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contest_participants (
            id SERIAL PRIMARY KEY,
            contest_id INT REFERENCES channel_contests(id) ON DELETE CASCADE,
            tg_user_id BIGINT NOT NULL,
            user_name TEXT,
            joined_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(contest_id, tg_user_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_contest_part_user ON contest_participants(contest_id, tg_user_id)")

    # 1. Zaxira kutish (Wishlist) jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS restock_wishlist (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            product_id INT NOT NULL,
            product_name TEXT NOT NULL,
            notified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tg_user_id, product_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_prod ON restock_wishlist(product_id, notified)")

    # 2. Tashlab ketilgan savat (Abandoned carts) jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS abandoned_carts (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            product_id INT NOT NULL,
            product_name TEXT NOT NULL,
            price_uzs BIGINT NOT NULL,
            notified BOOLEAN DEFAULT FALSE,
            resolved BOOLEAN DEFAULT FALSE,
            initiated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_abandoned_user ON abandoned_carts(tg_user_id, resolved, notified)")

    # 3. Tezkor Promokodlar (Fast Drop Promos) jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fast_drop_promos (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE NOT NULL,
            reward_type VARCHAR(32) DEFAULT 'balance',
            reward_value BIGINT NOT NULL,
            max_uses INT DEFAULT 3,
            current_uses INT DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 4. Promokod ishlatganlar jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_redemptions (
            id SERIAL PRIMARY KEY,
            promo_id INT REFERENCES fast_drop_promos(id) ON DELETE CASCADE,
            tg_user_id BIGINT NOT NULL,
            redeemed_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(promo_id, tg_user_id)
        )
    """)

    # 5. Yashirin Oltin Tanga (Easter Egg claims) jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS easter_egg_claims (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT NOT NULL,
            claim_date DATE NOT NULL,
            reward_uzs INT DEFAULT 5000,
            claimed_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tg_user_id, claim_date)
        )
    """)

    # 6. Flash Sale (Vaqtinchalik Chegirmalar) jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flash_sales (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            discount_percent INT DEFAULT 20,
            is_active BOOLEAN DEFAULT TRUE,
            ends_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


    
    # Run background migrations
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("ALTER TABLE user_balances ADD COLUMN IF NOT EXISTS balance_ton NUMERIC DEFAULT 0;")
        cur.execute("ALTER TABLE nft_items ADD COLUMN IF NOT EXISTS nft_address TEXT DEFAULT '';")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")
        
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
        _set_cached(f"cfg_{key}", value, 600)
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()

def get_config(key):
    cached = _get_cached(f"cfg_{key}")
    if cached is not None:
        return cached
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM bot_config WHERE key = %s", (key,))
        row = cur.fetchone()
        val = row["value"] if row else None
        _set_cached(f"cfg_{key}", val, 300)
        return val
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
        _invalidate_cached(f"admin_{tg_user_id}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB xato: {e}")
        return False
    finally:
        conn.close()


def is_bot_admin(tg_user_id):
    cached = _get_cached(f"admin_{tg_user_id}")
    if cached is not None:
        return bool(cached)
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM bot_admins WHERE tg_user_id = %s", (tg_user_id,))
        res = cur.fetchone() is not None
        _set_cached(f"admin_{tg_user_id}", res, 300)
        return res
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

if __name__ == "__main__":
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

def get_user_ton_balance(tg_user_id: int) -> float:
    """Foydalanuvchining TON balansini qaytaradi (default: 0.0)"""
    conn = get_db()
    if not conn: return 0.0
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_ton FROM user_balances WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        val = float(row["balance_ton"]) if row and row.get("balance_ton") is not None else 0.0
        return val
    except Exception as e:
        print(f"get_user_ton_balance error: {e}")
        return 0.0
    finally:
        conn.close()

def add_user_ton_balance(tg_user_id: int, amount_ton: float) -> float:
    """Foydalanuvchining hisobiga TON qo'shish va yangi balansni qaytarish"""
    conn = get_db()
    if not conn: return 0.0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_ton, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_ton = COALESCE(user_balances.balance_ton, 0) + EXCLUDED.balance_ton,
                updated_at = NOW()
            RETURNING balance_ton
        """, (tg_user_id, amount_ton))
        row = cur.fetchone()
        conn.commit()
        new_val = float(row["balance_ton"]) if row else 0.0
        return new_val
    except Exception as e:
        conn.rollback()
        print(f"add_user_ton_balance error: {e}")
        return 0.0
    finally:
        conn.close()

def deduct_user_ton_balance(tg_user_id: int, amount_ton: float) -> bool:
    """Balansdan TON yechish. Agar yetarli bo'lsa True, bo'lmasa False"""
    if amount_ton <= 0: return True
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_ton FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        row = cur.fetchone()
        current = float(row["balance_ton"]) if row and row.get("balance_ton") is not None else 0.0
        if current < amount_ton:
            conn.rollback()
            return False
        cur.execute(
            "UPDATE user_balances SET balance_ton = balance_ton - %s, updated_at = NOW() WHERE tg_user_id = %s",
            (amount_ton, tg_user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"deduct_user_ton_balance error: {e}")
        return False
    finally:
        conn.close()


def get_user_balance(tg_user_id: int) -> int:
    """Foydalanuvchining UZS balansini qaytaradi (default: 0) (Kesh bilan tezkor)"""
    cached = _get_cached(f"bal_{tg_user_id}")
    if cached is not None:
        return int(cached)

    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        val = int(row["balance_uzs"]) if row and row["balance_uzs"] is not None else 0
        _set_cached(f"bal_{tg_user_id}", val, 30)
        return val
    except Exception as e:
        print(f"get_user_balance error: {e}")
        return 0
    finally:
        conn.close()


def add_user_balance(tg_user_id: int, amount_uzs: int) -> int:
    """Foydalanuvchining hisobiga pul qo'shish va yangi balansni qaytarish"""
    _invalidate_cached(f"bal_{tg_user_id}")
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
        new_val = int(row["balance_uzs"]) if row else 0
        _set_cached(f"bal_{tg_user_id}", new_val, 30)
        return new_val
    except Exception as e:
        conn.rollback()
        print(f"add_user_balance error: {e}")
        return 0
    finally:
        conn.close()


def deduct_user_balance(tg_user_id: int, amount_uzs: int) -> bool:
    """Balansdan pul yechish. Agar yetarli bo'lsa True, bo'lmasa False"""
    _invalidate_cached(f"bal_{tg_user_id}")
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
        _set_cached(f"bal_{tg_user_id}", current - amount_uzs, 30)
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


# ==================== HUMO P2P DEPOSIT ENGINE ====================

def create_humo_deposit(tg_user_id: int, amount_uzs: int, sender_card_last4: str = None) -> dict:
    """Humo karta orqali to'lov uchun yangi buyurtma yaratish (Micro-offset kolliziyaga qarshi himoya bilan)"""
    from config import HUMO_CARD_NUMBER
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        # Avval eski pending buyurtmalarni bekor qilish
        cur.execute("""
            UPDATE humo_deposits
            SET status = 'cancelled'
            WHERE tg_user_id = %s AND status = 'pending'
        """, (tg_user_id,))
        
        # O'tgan 15 daqiqa ichida faol bo'lgan shu summadagi micro-offsetlarni olish
        cur.execute("""
            SELECT unique_amount_uzs - amount_uzs as offset_val
            FROM humo_deposits
            WHERE status = 'pending' 
              AND amount_uzs = %s 
              AND created_at > NOW() - INTERVAL '15 minutes'
        """, (amount_uzs,))
        rows = cur.fetchall()
        used_offsets = {r["offset_val"] for r in rows if r and r["offset_val"] is not None}
        
        # 1 dan 99 gacha bo'sh turgan eng kichik offsetni topish
        offset = 1
        for i in range(1, 100):
            if i not in used_offsets:
                offset = i
                break
        else:
            import random
            offset = random.randint(100, 199)
            
        unique_amount = amount_uzs + offset
        
        cur.execute("""
            INSERT INTO humo_deposits (tg_user_id, amount_uzs, unique_amount_uzs, sender_card_last4, card_number, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'pending', NOW())
            RETURNING *
        """, (tg_user_id, amount_uzs, unique_amount, sender_card_last4, HUMO_CARD_NUMBER))
        row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception as e:
        conn.rollback()
        print(f"create_humo_deposit error: {e}")
        return None
    finally:
        conn.close()

def get_user_pending_humo_deposit(tg_user_id: int) -> dict:
    """Foydalanuvchining faol (15 daqiqa ichidagi) pending to'lovini olish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM humo_deposits
            WHERE tg_user_id = %s 
              AND status = 'pending'
              AND created_at > NOW() - INTERVAL '20 minutes'
            ORDER BY created_at DESC LIMIT 1
        """, (tg_user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user_pending_humo_deposit error: {e}")
        return None
    finally:
        conn.close()

def get_humo_deposit_by_id(deposit_id: int) -> dict:
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM humo_deposits WHERE id = %s", (deposit_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_humo_deposit_by_id error: {e}")
        return None
    finally:
        conn.close()

def cancel_humo_deposit(deposit_id: int, tg_user_id: int) -> bool:
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE humo_deposits
            SET status = 'cancelled'
            WHERE id = %s AND tg_user_id = %s AND status = 'pending'
        """, (deposit_id, tg_user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"cancel_humo_deposit error: {e}")
        return False
    finally:
        conn.close()

def is_humo_message_processed(message_id: int) -> bool:
    """HUMO SMS xabari avval ko'rilgan yoki ko'rilmaganini tekshirish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM humo_processed_messages WHERE message_id = %s", (message_id,))
        return cur.fetchone() is not None
    except Exception as e:
        print(f"is_humo_message_processed error: {e}")
        return False
    finally:
        conn.close()

def mark_humo_message_processed(message_id: int, exact_amount: int = None, payment_id: str = None, msg_time = None) -> bool:
    """HUMO SMS xabarini qayta ishlanmasligi uchun ro'yxatga olish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO humo_processed_messages (message_id, exact_amount, payment_id, processed_at, msg_time)
            VALUES (%s, %s, %s, NOW(), %s)
            ON CONFLICT (message_id) DO NOTHING
        """, (message_id, exact_amount, str(payment_id) if payment_id else None, msg_time))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"mark_humo_message_processed error: {e}")
        return False
    finally:
        conn.close()

def match_and_complete_humo_deposit(parsed_data: dict) -> dict:
    """
    @HUMOcardbot dan kelgan ma'lumotlar asosida 100% avtomatik tarzda mos buyurtmani topib,
    balansga qo'shish va tranzaksiyani yakunlash.
    Barcha banklar, kartalar (Humo, Uzcard, NBU, Click, Payme va h.k.) dan kelgan to'lovlarni
    adashmasdan aniqlaydi.
    """
    if not parsed_data or not parsed_data.get("amount_uzs"):
        return None
        
    amount = int(parsed_data["amount_uzs"])
    sender_card = parsed_data.get("sender_card_last4")
    sender_name = parsed_data.get("sender_name")
    rrn_code = parsed_data.get("rrn_code")
    raw_text = parsed_data.get("raw_text") or ""
    msg_date = parsed_data.get("message_date")
    if msg_date and hasattr(msg_date, "tzinfo") and msg_date.tzinfo is None:
        from datetime import timezone
        msg_date = msg_date.replace(tzinfo=timezone.utc)
    
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        matched_deposit = None
        
        # 1-Qidiruv (Eng aniq va asosiy): Aniq unique_amount_uzs bo'yicha (masalan 1,001 yoki 50,014 so'm)
        # Pending to'lovlar birinchi o'rinda, agar foydalanuvchi bekor qilgan bo'lsa ham so'nggi 45 daqiqadagi to'lovi inobatga olinadi
        cur.execute("""
            SELECT * FROM humo_deposits
            WHERE status IN ('pending', 'cancelled')
              AND unique_amount_uzs = %s
              AND created_at > NOW() - INTERVAL '45 minutes'
            ORDER BY CASE WHEN status = 'pending' THEN 0 ELSE 1 END, created_at DESC LIMIT 1
            FOR UPDATE
        """, (amount,))
        row = cur.fetchone()
        if row:
            matched_deposit = dict(row)
            
        # 2-Qidiruv: Agar RRN kod avval kiritilgan bo'lsa yoki SMSda RRN bo'lsa
        if not matched_deposit and rrn_code:
            cur.execute("""
                SELECT * FROM humo_deposits
                WHERE status IN ('pending', 'cancelled')
                  AND rrn_code = %s
                  AND created_at > NOW() - INTERVAL '45 minutes'
                ORDER BY CASE WHEN status = 'pending' THEN 0 ELSE 1 END, created_at DESC LIMIT 1
                FOR UPDATE
            """, (rrn_code,))
            row = cur.fetchone()
            if row:
                matched_deposit = dict(row)
                
        # 3-Qidiruv: Agar foydalanuvchi to'layotgan kartasining oxirgi 4 raqamini kiritgan bo'lsa va SMSdagi yuboruvchi karta mos kelsa
        if not matched_deposit and sender_card:
            cur.execute("""
                SELECT * FROM humo_deposits
                WHERE status IN ('pending', 'cancelled')
                  AND (amount_uzs = %s OR unique_amount_uzs = %s)
                  AND sender_card_last4 = %s
                  AND created_at > NOW() - INTERVAL '45 minutes'
                ORDER BY CASE WHEN status = 'pending' THEN 0 ELSE 1 END, created_at DESC LIMIT 1
                FOR UPDATE
            """, (amount, amount, sender_card))
            row = cur.fetchone()
            if row:
                matched_deposit = dict(row)

        # 4-Qidiruv (Zaxira): Agar foydalanuvchi micro-offsetsiz to'lagan bo'lsa (amount_uzs = amount)
        # va ayni daqiqalarda shu summadagi FAQAT 1 dona pending to'lov mavjud bo'lsa (chalkashlik yo'q)
        if not matched_deposit:
            cur.execute("""
                SELECT * FROM humo_deposits
                WHERE status = 'pending'
                  AND amount_uzs = %s
                  AND created_at > NOW() - INTERVAL '30 minutes'
                FOR UPDATE
            """, (amount,))
            rows = cur.fetchall()
            if len(rows) == 1:
                matched_deposit = dict(rows[0])
                
        if not matched_deposit:
            conn.rollback()
            return None
            
        deposit_id = matched_deposit["id"]
        tg_user_id = matched_deposit["tg_user_id"]
        
        # Tranzaksiyani completed qilish
        cur.execute("""
            UPDATE humo_deposits
            SET status = 'completed',
                sms_raw_text = %s,
                sender_name = COALESCE(%s, sender_name),
                sender_card_last4 = COALESCE(%s, sender_card_last4),
                rrn_code = COALESCE(%s, rrn_code),
                completed_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (raw_text, sender_name, sender_card, rrn_code, deposit_id))
        completed_row = dict(cur.fetchone())
        
        # Balansga qo'shish
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                updated_at = NOW()
            RETURNING balance_uzs
        """, (tg_user_id, amount))
        bal_row = cur.fetchone()
        new_balance = int(bal_row["balance_uzs"]) if bal_row else 0
        _set_cached(f"bal_{tg_user_id}", new_balance, 30)
        
        # payment_transactions jadvaliga ham yozib qo'yish
        cur.execute("""
            INSERT INTO payment_transactions (tg_user_id, payment_type, amount_original, currency, amount_uzs, status, invoice_id, payload, created_at, updated_at)
            VALUES (%s, 'humo_card', %s, 'UZS', %s, 'completed', %s, %s, NOW(), NOW())
        """, (tg_user_id, float(amount), amount, f"humo_{deposit_id}", rrn_code or raw_text[:50]))
        
        conn.commit()
        
        # Referral cashback (10%)
        try:
            process_referral_cashback(tg_user_id, amount)
        except Exception as ref_e:
            print(f"Humo referral cashback error: {ref_e}")
            
        completed_row["new_balance"] = new_balance
        return completed_row
    except Exception as e:
        conn.rollback()
        print(f"match_and_complete_humo_deposit error: {e}")
        return None
    finally:
        conn.close()

def set_deposit_sender_card(deposit_id: int, tg_user_id: int, card_last4: str) -> bool:
    """Foydalanuvchi to'layotgan kartasining oxirgi 4 raqamini saqlash"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE humo_deposits
            SET sender_card_last4 = %s
            WHERE id = %s AND tg_user_id = %s AND status = 'pending'
        """, (card_last4, deposit_id, tg_user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"set_deposit_sender_card error: {e}")
        return False
    finally:
        conn.close()

def set_deposit_rrn_code(deposit_id: int, tg_user_id: int, rrn_code: str) -> bool:
    """Foydalanuvchi chekdagi RRN kodini kiritganda saqlash"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE humo_deposits
            SET rrn_code = %s
            WHERE id = %s AND tg_user_id = %s AND status = 'pending'
        """, (rrn_code, deposit_id, tg_user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"set_deposit_rrn_code error: {e}")
        return False
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
        _set_cached(f"kyc_{tg_user_id}", True, 300)
        return True
    except Exception as e:
        conn.rollback()
        print(f"save_kyc_verification error: {e}")
        return False
    finally:
        conn.close()


def is_user_kyc_verified(tg_user_id: int) -> bool:
    """Foydalanuvchi KYC dan o'tganmi? (Kesh bilan tezkor)"""
    cached = _get_cached(f"kyc_{tg_user_id}")
    if cached is not None:
        return bool(cached)

    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM kyc_verifications WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row:
            _set_cached(f"kyc_{tg_user_id}", False, 180)
            return False
        st = row["status"] if isinstance(row, dict) else row[0]
        res = bool(st == "verified")
        _set_cached(f"kyc_{tg_user_id}", res, 300 if res else 60)
        return res
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
        _set_cached(f"phone_{tg_user_id}", clean_phone, 600)
        _invalidate_cached(f"tier_{tg_user_id}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"save_telegram_phone error: {e}")
        return False
    finally:
        conn.close()

def get_telegram_phone(tg_user_id: int) -> str:
    """Foydalanuvchining tasdiqlangan Telegram telefon raqamini olish (kesh bilan)"""
    cached = _get_cached(f"phone_{tg_user_id}")
    if cached is not None:
        return str(cached)
    conn = get_db()
    if not conn: return ""
    try:
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM user_phones WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row:
            _set_cached(f"phone_{tg_user_id}", "", 180)
            return ""
        val = row["phone_number"] if isinstance(row, dict) else row[0]
        _set_cached(f"phone_{tg_user_id}", val, 600)
        return val
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
    """Soatiga 2,500 so'm hisobidan Autostream bulutli sloti sotib olish"""
    price_per_hour = 2500
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
    """Oylik 69,000 so'm VIP cheksiz tarif xarid qilish"""
    price_uzs = 69000
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
        _set_cached(f"vip_{tg_user_id}", True, 300)
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
    """Foydalanuvchi VIP abonentimi? (Kesh bilan tezkor)"""
    cached = _get_cached(f"vip_{tg_user_id}")
    if cached is not None:
        return bool(cached)

    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT expires_at FROM vip_subscriptions
            WHERE tg_user_id = %s AND NOW() < expires_at
        """, (tg_user_id,))
        row = cur.fetchone()
        res = bool(row)
        _set_cached(f"vip_{tg_user_id}", res, 180)
        return res
    except Exception as e:
        print(f"is_user_vip error: {e}")
        return False
    finally:
        conn.close()

def is_user_ai_video_subscribed(tg_user_id: int) -> bool:
    """Foydalanuvchida $20/oy AI Video generator obunasi mavjudmi? (Kesh bilan tezkor)"""
    from config import OWNER_ID
    if tg_user_id == OWNER_ID:
        return True
    if is_user_vip(tg_user_id):
        return True

    cached = _get_cached(f"aivid_{tg_user_id}")
    if cached is not None:
        return bool(cached)

    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT expires_at FROM ai_video_subscriptions
            WHERE tg_user_id = %s AND NOW() < expires_at
        """, (tg_user_id,))
        row = cur.fetchone()
        res = bool(row)
        _set_cached(f"aivid_{tg_user_id}", res, 180)
        return res
    except Exception as e:
        print(f"is_user_ai_video_subscribed error: {e}")
        return False
    finally:
        conn.close()

def purchase_ai_video_subscription(tg_user_id: int, days: int = 30) -> dict:
    """Oylik 256,000 so'm ($20) AI Video cheksiz obuna xarid qilish"""
    price_uzs = 256000
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
            INSERT INTO ai_video_subscriptions (tg_user_id, expires_at, created_at)
            VALUES (%s, NOW() + INTERVAL '30 days', NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET expires_at = GREATEST(ai_video_subscriptions.expires_at, NOW()) + INTERVAL '30 days'
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
        print(f"purchase_ai_video_subscription error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def deduct_single_ai_video_fee(tg_user_id: int) -> dict:
    """Bitta AI video generatsiyasi uchun 15,000 so'm yechish"""
    from config import OWNER_ID
    if tg_user_id == OWNER_ID or is_user_ai_video_subscribed(tg_user_id):
        return {"ok": True, "free": True}
    price_uzs = 15000
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
                "error": f"Balansingiz yetarli emas! 1 ta video: {price_uzs:,} so'm, mavjud: {curr_bal:,} so'm"
            }

        new_bal = curr_bal - price_uzs
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))
        conn.commit()
        return {"ok": True, "new_balance": new_bal}
    except Exception as e:
        conn.rollback()
        print(f"deduct_single_ai_video_fee error: {e}")
        return {"ok": False, "error": str(e)}
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


# ==================== MULTI-LANGUAGE & VIRAL TRAFFIC HELPERS ====================

def set_user_language(tg_user_id: int, lang: str) -> bool:
    """Foydalanuvchi tanlagan tilni saqlash (uz, ru, en, es, tr)"""
    conn = get_db()
    if not conn: return False
    safe_lang = lang.strip().lower()[:2]
    if safe_lang not in ("uz", "ru", "en", "es", "tr"):
        safe_lang = "uz"
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_languages (tg_user_id, language, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET language = EXCLUDED.language, updated_at = NOW()
        """, (tg_user_id, safe_lang))
        conn.commit()
        _set_cached(f"lang_{tg_user_id}", safe_lang, 600)
        return True
    except Exception as e:
        conn.rollback()
        print(f"set_user_language error: {e}")
        return False
    finally:
        conn.close()

def get_user_language(tg_user_id: int) -> str:
    """Foydalanuvchi tilini olish (default: en) (Kesh bilan tezkor)"""
    cached = _get_cached(f"lang_{tg_user_id}")
    if cached is not None:
        return str(cached)

    conn = get_db()
    if not conn: return "en"
    try:
        cur = conn.cursor()
        cur.execute("SELECT language FROM user_languages WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row:
            _set_cached(f"lang_{tg_user_id}", "en", 300)
            return "en"
        lang = row["language"] if isinstance(row, dict) else row[0]
        res = lang if lang in ("uz", "ru", "en", "es", "tr") else "en"
        _set_cached(f"lang_{tg_user_id}", res, 600)
        return res
    except Exception as e:
        print(f"get_user_language error: {e}")
        return "en"
    finally:
        conn.close()

def get_top_referrers(limit: int = 5) -> list:
    """Eng ko'p referal taklif qilgan liderlar ro'yxati"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT referrer_id, COUNT(*) as ref_count, COALESCE(SUM(total_earned_uzs), 0) as total_earned
            FROM referrals
            GROUP BY referrer_id
            ORDER BY ref_count DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall() or []
        res = []
        for r in rows:
            uid = r["referrer_id"] if isinstance(r, dict) else r[0]
            cnt = r["ref_count"] if isinstance(r, dict) else r[1]
            earned = r["total_earned"] if isinstance(r, dict) else r[2]
            masked = str(uid)[:3] + "***" + str(uid)[-2:] if len(str(uid)) >= 5 else str(uid)
            res.append({"user": masked, "count": int(cnt), "earned": int(earned)})
        return res
    except Exception as e:
        print(f"get_top_referrers error: {e}")
        return []
    finally:
        conn.close()

def get_top_duel_winners(limit: int = 5) -> list:
    """Eng ko'p duel yutgan chempionlar"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT winner_id, COUNT(*) as win_count, COALESCE(SUM(amount_uzs * 2 * 0.9), 0) as total_payout
            FROM coinflip_duels
            WHERE status = 'finished' AND winner_id IS NOT NULL
            GROUP BY winner_id
            ORDER BY win_count DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall() or []
        res = []
        for r in rows:
            uid = r["winner_id"] if isinstance(r, dict) else r[0]
            cnt = r["win_count"] if isinstance(r, dict) else r[1]
            payout = r["total_payout"] if isinstance(r, dict) else r[2]
            masked = str(uid)[:3] + "***" + str(uid)[-2:] if len(str(uid)) >= 5 else str(uid)
            res.append({"user": masked, "count": int(cnt), "payout": int(payout)})
        return res
    except Exception as e:
        print(f"get_top_duel_winners error: {e}")
        return []
    finally:
        conn.close()


# ==================== 1. INSTAGRAM AUTO-SYNC & RE-POSTER ====================

def add_ig_sync_channel(tg_user_id: int, ig_username: str, check_interval_mins: int = 60) -> bool:
    """Yangi Instagram profilni avtomatik kuzatuvga qo'shish"""
    conn = get_db()
    if not conn: return False
    clean_username = ig_username.strip().lstrip("@").lower()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ig_sync_channels (tg_user_id, ig_username, check_interval_mins)
            VALUES (%s, %s, %s)
            ON CONFLICT (tg_user_id, ig_username) DO UPDATE SET is_active = TRUE, check_interval_mins = EXCLUDED.check_interval_mins
        """, (tg_user_id, clean_username, check_interval_mins))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"add_ig_sync_channel error: {e}")
        return False
    finally:
        conn.close()

def remove_ig_sync_channel(tg_user_id: int, ig_username: str) -> bool:
    """Instagram profilni username bo'yicha kuzatuvdan o'chirish"""
    conn = get_db()
    if not conn: return False
    clean_username = ig_username.strip().lstrip("@").lower()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM ig_sync_channels WHERE tg_user_id = %s AND ig_username = %s", (tg_user_id, clean_username))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"remove_ig_sync_channel error: {e}")
        return False
    finally:
        conn.close()

def get_user_ig_sync_channels(tg_user_id: int) -> list:
    """Foydalanuvchining ulangan Instagram kanallari ro'yxati"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ig_sync_channels WHERE tg_user_id = %s ORDER BY id DESC", (tg_user_id,))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_user_ig_sync_channels error: {e}")
        return []
    finally:
        conn.close()

def delete_ig_sync_channel(sync_channel_id: int, tg_user_id: int) -> bool:
    """Kuzatuvdagi Instagram kanalni o'chirish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM ig_sync_channels WHERE id = %s AND tg_user_id = %s", (sync_channel_id, tg_user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"delete_ig_sync_channel error: {e}")
        return False
    finally:
        conn.close()

def get_all_active_ig_sync_channels() -> list:
    """Barcha faol Instagram monitoring kanallarini olish"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ig_sync_channels WHERE is_active = TRUE ORDER BY id ASC")
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_active_ig_sync_channels error: {e}")
        return []
    finally:
        conn.close()

def is_ig_post_synced(sync_channel_id: int, ig_post_id: str) -> bool:
    """Ushbu Instagram post avval yuklanganmi?"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM ig_synced_posts WHERE sync_channel_id = %s AND ig_post_id = %s", (sync_channel_id, str(ig_post_id)))
        return bool(cur.fetchone())
    except Exception as e:
        print(f"is_ig_post_synced error: {e}")
        return False
    finally:
        conn.close()

def record_ig_synced_post(sync_channel_id: int, ig_post_id: str, media_url: str = "", yt_video_id: str = "", status: str = "synced") -> bool:
    """Yuklangan Instagram postni qayd etish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ig_synced_posts (sync_channel_id, ig_post_id, media_url, yt_video_id, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (sync_channel_id, ig_post_id) DO UPDATE SET status = EXCLUDED.status, yt_video_id = EXCLUDED.yt_video_id
        """, (sync_channel_id, str(ig_post_id), media_url, yt_video_id, status))
        cur.execute("UPDATE ig_sync_channels SET last_checked_at = NOW() WHERE id = %s", (sync_channel_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"record_ig_synced_post error: {e}")
        return False
    finally:
        conn.close()


def update_ig_sync_timestamp(sync_channel_id: int) -> bool:
    """IG sync kanalining last_checked_at vaqtini yangilash"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE ig_sync_channels SET last_checked_at = NOW() WHERE id = %s", (sync_channel_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"update_ig_sync_timestamp error: {e}")
        return False
    finally:
        conn.close()


# ==================== 2. CAPCUT DESKTOP & PRO TOOLS REFERRAL POOL ====================

def add_capcut_link(tg_user_id: int, invite_link: str, service_name: str = "capcut") -> bool:
    """Foydalanuvchi CapCut taklif havolasini hovuzga qo'shish"""
    conn = get_db()
    if not conn: return False
    link = invite_link.strip()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO capcut_referral_pool (tg_user_id, invite_link, service_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (invite_link) DO UPDATE SET is_active = TRUE
        """, (tg_user_id, link, service_name))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"add_capcut_link error: {e}")
        return False
    finally:
        conn.close()

def get_next_capcut_link(exclude_user_id: int = None, service_name: str = "capcut") -> dict:
    """Navbatdagi eng kam bosilgan faol CapCut taklif havolasini olish (Fair Rotation)"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        if exclude_user_id:
            cur.execute("""
                SELECT * FROM capcut_referral_pool
                WHERE is_active = TRUE AND service_name = %s AND tg_user_id != %s
                ORDER BY total_clicks ASC, id ASC
                LIMIT 1
            """, (service_name, exclude_user_id))
        else:
            cur.execute("""
                SELECT * FROM capcut_referral_pool
                WHERE is_active = TRUE AND service_name = %s
                ORDER BY total_clicks ASC, id ASC
                LIMIT 1
            """, (service_name,))
        row = cur.fetchone()
        if not row and exclude_user_id:
            cur.execute("""
                SELECT * FROM capcut_referral_pool
                WHERE is_active = TRUE AND service_name = %s
                ORDER BY total_clicks ASC, id ASC
                LIMIT 1
            """, (service_name,))
            row = cur.fetchone()

        if row:
            d = dict(row)
            cur.execute("UPDATE capcut_referral_pool SET total_clicks = total_clicks + 1 WHERE id = %s", (d["id"],))
            conn.commit()
            return d
        return None
    except Exception as e:
        conn.rollback()
        print(f"get_next_capcut_link error: {e}")
        return None
    finally:
        conn.close()

def get_user_capcut_links(tg_user_id: int) -> list:
    """Foydalanuvchining kiritgan CapCut havolalari statistikasi"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM capcut_referral_pool WHERE tg_user_id = %s ORDER BY id DESC", (tg_user_id,))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_user_capcut_links error: {e}")
        return []
    finally:
        conn.close()

def increment_capcut_claims(pool_id: int) -> bool:
    """Muvaffaqiyatli ro'yxatdan o'tish hisobini oshirish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE capcut_referral_pool SET total_claims = total_claims + 1 WHERE id = %s", (pool_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"increment_capcut_claims error: {e}")
        return False
    finally:
        conn.close()

add_capcut_referral = add_capcut_link
get_active_capcut_referral = get_next_capcut_link

def add_capcut_subscription(tg_user_id: int, plan_days: int, price_uzs: int, license_key: str = None) -> dict:
    """CapCut Pro obunasini bazada saqlash yoki muddatini uzaytirish"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO capcut_subscriptions (tg_user_id, plan_days, price_uzs, license_key, expires_at, status, created_at)
            VALUES (%s, %s, %s, %s, NOW() + (%s || ' days')::INTERVAL, 'active', NOW())
            RETURNING id, expires_at
        """, (tg_user_id, plan_days, price_uzs, license_key, str(plan_days)))
        row = cur.fetchone()
        conn.commit()
        exp = row["expires_at"] if isinstance(row, dict) else row[1]
        sub_id = row["id"] if isinstance(row, dict) else row[0]
        return {"ok": True, "sub_id": sub_id, "expires_at": str(exp)[:19]}
    except Exception as e:
        conn.rollback()
        print(f"add_capcut_subscription error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_capcut_subscription(tg_user_id: int) -> dict:
    """Foydalanuvchining faol CapCut Pro obunasi ma'lumotlari"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM capcut_subscriptions
            WHERE tg_user_id = %s AND expires_at > NOW() AND status = 'active'
            ORDER BY expires_at DESC
            LIMIT 1
        """, (tg_user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user_capcut_subscription error: {e}")
        return None
    finally:
        conn.close()

def is_user_capcut_pro(tg_user_id: int) -> bool:
    """Foydalanuvchida faol CapCut Pro bormi?"""
    sub = get_user_capcut_subscription(tg_user_id)
    return bool(sub)


# ==================== 3. SUPPORT DESK & LIVE ADMIN BRIDGE ====================

def create_or_get_open_ticket(tg_user_id: int, role_intent: str = "general") -> dict:
    """Foydalanuvchi uchun ochiq support ticketni olish yoki yangi ochish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM support_tickets WHERE tg_user_id = %s AND status = 'open' ORDER BY id DESC LIMIT 1", (tg_user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        cur.execute("""
            INSERT INTO support_tickets (tg_user_id, role_intent, status)
            VALUES (%s, %s, 'open')
            RETURNING *
        """, (tg_user_id, role_intent))
        new_row = cur.fetchone()
        conn.commit()
        return dict(new_row)
    except Exception as e:
        conn.rollback()
        print(f"create_or_get_open_ticket error: {e}")
        return None
    finally:
        conn.close()

def add_support_message(ticket_id: int, sender_type: str, message_text: str, media_file_id: str = None) -> bool:
    """Ticketga yangi xabar qo'shish (user yoki admin)"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO support_messages (ticket_id, sender_type, message_text, media_file_id)
            VALUES (%s, %s, %s, %s)
        """, (ticket_id, sender_type, message_text, media_file_id))
        cur.execute("UPDATE support_tickets SET updated_at = NOW() WHERE id = %s", (ticket_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"add_support_message error: {e}")
        return False
    finally:
        conn.close()

def close_support_ticket(ticket_id: int) -> bool:
    """Ticketni yopish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE support_tickets SET status = 'closed', updated_at = NOW() WHERE id = %s", (ticket_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"close_support_ticket error: {e}")
        return False
    finally:
        conn.close()

def get_ticket_by_id(ticket_id: int) -> dict:
    """Ticket ma'lumotlarini olish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM support_tickets WHERE id = %s", (ticket_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_ticket_by_id error: {e}")
        return None
    finally:
        conn.close()

def get_ticket_messages(ticket_id: int, limit: int = 15) -> list:
    """Ticketdagi oxirgi xabarlar tarixi"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM support_messages WHERE ticket_id = %s ORDER BY id ASC LIMIT %s", (ticket_id, limit))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_ticket_messages error: {e}")
        return []
    finally:
        conn.close()


# ==================== 4. P2P CONDITIONAL CHEKLAR & ANTIFRAUD ====================

def create_conditional_check(creator_id: int, check_code: str, total_amount_uzs: int, max_claims: int = 1, required_channel: str = None) -> tuple:
    """Majburiy kanalli P2P chek yaratish va balansi yechib olish"""
    conn = get_db()
    if not conn: return False, "Ma'lumotlar bazasiga ulanib bo'lmadi"
    clean_channel = required_channel.strip().lstrip("@") if required_channel else None
    amount_per_user = int(total_amount_uzs / max_claims) if max_claims > 0 else total_amount_uzs
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (creator_id,))
        row = cur.fetchone()
        bal = (row["balance_uzs"] if isinstance(row, dict) else row[0]) if row else 0
        if bal < total_amount_uzs:
            return False, "Balansingizda mablag' yetarli emas!"

        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s, updated_at = NOW() WHERE tg_user_id = %s", (total_amount_uzs, creator_id))
        cur.execute("""
            INSERT INTO conditional_checks (check_code, creator_id, total_amount_uzs, amount_per_user_uzs, max_claims, required_channel)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (check_code, creator_id, total_amount_uzs, amount_per_user, max_claims, clean_channel))
        conn.commit()
        return True, check_code
    except Exception as e:
        conn.rollback()
        print(f"create_conditional_check error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_conditional_check(check_code: str) -> dict:
    """Chek ma'lumotlarini olish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM conditional_checks WHERE check_code = %s", (check_code.strip(),))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_conditional_check error: {e}")
        return None
    finally:
        conn.close()

def claim_conditional_check(check_id: int, tg_user_id: int, amount: int) -> tuple:
    """Chekni qabul qilish va mablag'ni hisobga qo'shish"""
    conn = get_db()
    if not conn: return False, "DB xatosi"
    try:
        cur = conn.cursor()
        # Tekshirish
        cur.execute("SELECT id FROM check_claims WHERE check_id = %s AND tg_user_id = %s", (check_id, tg_user_id))
        if cur.fetchone():
            return False, "Siz ushbu chekni avval qabul qilgansiz!"

        cur.execute("SELECT * FROM conditional_checks WHERE id = %s FOR UPDATE", (check_id,))
        row = cur.fetchone()
        if not row:
            return False, "Chek topilmadi!"
        chk = dict(row)
        if not chk["is_active"] or chk["claims_count"] >= chk["max_claims"]:
            return False, "Ushbu chek allaqachon to'liq qabul qilib bo'lingan!"

        cur.execute("""
            INSERT INTO check_claims (check_id, tg_user_id, amount_received_uzs)
            VALUES (%s, %s, %s)
        """, (check_id, tg_user_id, amount))

        new_count = chk["claims_count"] + 1
        is_active = new_count < chk["max_claims"]
        cur.execute("UPDATE conditional_checks SET claims_count = %s, is_active = %s WHERE id = %s", (new_count, is_active, check_id))

        # Foydalanuvchi hisobiga pul qo'shish
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE SET balance_uzs = user_balances.balance_uzs + %s, updated_at = NOW()
        """, (tg_user_id, amount, amount))

        conn.commit()
        return True, "Muvaffaqiyatli qabul qilindi!"
    except Exception as e:
        conn.rollback()
        print(f"claim_conditional_check error: {e}")
        return False, str(e)
    finally:
        conn.close()

def is_user_antifraud_banned(tg_user_id: int) -> bool:
    """Foydalanuvchi antifraud qora ro'yxatidami? (Kesh bilan tezkor)"""
    cached = _get_cached(f"antifraud_{tg_user_id}")
    if cached is not None:
        return bool(cached)

    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT tg_user_id FROM banned_antifraud_users WHERE tg_user_id = %s", (tg_user_id,))
        res = bool(cur.fetchone())
        _set_cached(f"antifraud_{tg_user_id}", res, 180)
        return res
    except Exception as e:
        print(f"is_user_antifraud_banned error: {e}")
        return False
    finally:
        conn.close()

def ban_antifraud_user(tg_user_id: int, reason: str = "Majburiy kanaldan chiqib ketgani sababli bloklandi") -> bool:
    """Qoidabuzarni antifraud qora ro'yxatiga kiritish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO banned_antifraud_users (tg_user_id, reason)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id) DO UPDATE SET reason = EXCLUDED.reason, banned_at = NOW()
        """, (tg_user_id, reason))
        conn.commit()
        _set_cached(f"antifraud_{tg_user_id}", True, 600)
        return True
    except Exception as e:
        conn.rollback()
        print(f"ban_antifraud_user error: {e}")
        return False
    finally:
        conn.close()

def unban_antifraud_user(tg_user_id: int) -> bool:
    """Foydalanuvchini qora ro'yxatdan chiqarish"""
    _set_cached(f"antifraud_{tg_user_id}", False, 600)
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM banned_antifraud_users WHERE tg_user_id = %s", (tg_user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"unban_antifraud_user error: {e}")
        return False
    finally:
        conn.close()

def get_channel_check_claimers(required_channel: str) -> list:
    """Muayyan kanal sharti bilan chek olgan barcha userlar ro'yxati (Sentinel tekshiruvi uchun)"""
    conn = get_db()
    if not conn: return []
    clean_ch = required_channel.strip().lstrip("@")
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT cc.tg_user_id
            FROM check_claims cc
            JOIN conditional_checks c ON cc.check_id = c.id
            WHERE c.required_channel = %s
        """, (clean_ch,))
        rows = cur.fetchall() or []
        return [r["tg_user_id"] if isinstance(r, dict) else r[0] for r in rows]
    except Exception as e:
        print(f"get_channel_check_claimers error: {e}")
        return []
    finally:
        conn.close()


# ==================== 5. PROMO CODES & COUPONS ====================

def create_promo_code(code: str, balance_bonus_uzs: int, discount_percent: int = 0, max_uses: int = 100) -> bool:
    """Yangi promokod yaratish"""
    conn = get_db()
    if not conn: return False
    clean_code = code.strip().upper()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO promo_codes (code, balance_bonus_uzs, discount_percent, max_uses)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET balance_bonus_uzs = EXCLUDED.balance_bonus_uzs, max_uses = EXCLUDED.max_uses, is_active = TRUE
        """, (clean_code, balance_bonus_uzs, discount_percent, max_uses))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"create_promo_code error: {e}")
        return False
    finally:
        conn.close()

def redeem_promo_code(code: str, tg_user_id: int) -> tuple:
    """Promokodni faollashtirish"""
    conn = get_db()
    if not conn: return False, "DB xatosi", 0
    clean_code = code.strip().upper()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM promo_codes WHERE code = %s", (clean_code,))
        row = cur.fetchone()
        if not row:
            return False, "Bunday promokod mavjud emas!", 0
        promo = dict(row)
        if not promo["is_active"] or promo["current_uses"] >= promo["max_uses"]:
            return False, "Ushbu promokod tugagan yoki faol emas!", 0

        # Foydalanuvchi avval ishlatganmi?
        cur.execute("SELECT id FROM promo_redemptions WHERE promo_id = %s AND tg_user_id = %s", (promo["id"], tg_user_id))
        if cur.fetchone():
            return False, "Siz ushbu promokodni avval ishlatgansiz!", 0

        bonus = int(promo["balance_bonus_uzs"])
        cur.execute("INSERT INTO promo_redemptions (promo_id, tg_user_id) VALUES (%s, %s)", (promo["id"], tg_user_id))
        cur.execute("UPDATE promo_codes SET current_uses = current_uses + 1 WHERE id = %s", (promo["id"],))

        if bonus > 0:
            cur.execute("""
                INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (tg_user_id) DO UPDATE SET balance_uzs = user_balances.balance_uzs + %s, updated_at = NOW()
            """, (tg_user_id, bonus, bonus))

        conn.commit()
        return True, "Promokod muvaffaqiyatli faollashtirildi!", bonus
    except Exception as e:
        conn.rollback()
        print(f"redeem_promo_code error: {e}")
        return False, str(e), 0
    finally:
        conn.close()


# ==================== 6. CASHOUT (STARS & TON PUL YECHISH) ====================

def create_cashout_request(tg_user_id: int, method: str, target_address: str, amount_uzs: int, currency_equiv: str = "") -> tuple:
    """Balansni yechish uchun so'rov qoldirish. Qaytaradi: (ok, msg, req_id)"""
    conn = get_db()
    if not conn: return False, "DB xatosi", 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        row = cur.fetchone()
        bal = (row["balance_uzs"] if isinstance(row, dict) else row[0]) if row else 0
        if bal < amount_uzs:
            return False, "Balansingizda mablag' yetarli emas!", 0

        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s, updated_at = NOW() WHERE tg_user_id = %s", (amount_uzs, tg_user_id))
        cur.execute("""
            INSERT INTO cashout_requests (tg_user_id, method, target_address, amount_uzs, currency_equivalent, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """, (tg_user_id, method, target_address.strip(), amount_uzs, currency_equiv))
        id_row = cur.fetchone()
        req_id = (id_row["id"] if isinstance(id_row, dict) else id_row[0]) if id_row else 0
        conn.commit()
        return True, "Pul yechish so'rovingiz qabul qilindi. Admin tekshiruvidan so'ng o'tkazib beriladi!", req_id
    except Exception as e:
        conn.rollback()
        print(f"create_cashout_request error: {e}")
        return False, str(e), 0
    finally:
        conn.close()


def get_pending_cashout_requests(limit: int = 20) -> list:
    """Kutilayotgan pul yechish so'rovlari"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cashout_requests WHERE status = 'pending' ORDER BY id ASC LIMIT %s", (limit,))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_pending_cashout_requests error: {e}")
        return []
    finally:
        conn.close()

def process_cashout_request(request_id: int, status: str) -> bool:
    """Pul yechish so'rovini tasdiqlash yoki bekor qilish (agar rejected bo'lsa pul qaytariladi)"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cashout_requests WHERE id = %s AND status = 'pending' FOR UPDATE", (request_id,))
        row = cur.fetchone()
        if not row: return False
        req = dict(row)

        cur.execute("UPDATE cashout_requests SET status = %s, processed_at = NOW() WHERE id = %s", (status, request_id))
        if status == "rejected":
            # Pulni foydalanuvchiga qaytarish
            cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs + %s, updated_at = NOW() WHERE tg_user_id = %s", (req["amount_uzs"], req["tg_user_id"]))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"process_cashout_request error: {e}")
        return False
    finally:
        conn.close()


# ==================== 7. TON CONNECT WALLET ====================

import base64

def crc16(data: bytes) -> bytes:
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc.to_bytes(2, byteorder='big')

def to_user_friendly_address(raw_addr: str) -> str:
    if not isinstance(raw_addr, str) or ":" not in raw_addr:
        return raw_addr
    try:
        wc_str, hex_str = raw_addr.split(":", 1)
        if len(hex_str) != 64:
            return raw_addr
        wc = int(wc_str)
        # 0x51 is for non-bounceable user-friendly address
        payload = bytes([0x51, wc & 0xFF]) + bytes.fromhex(hex_str)
        crc = crc16(payload)
        return base64.urlsafe_b64encode(payload + crc).decode('utf-8').replace('=', '')
    except Exception:
        return raw_addr

def save_user_ton_wallet(tg_user_id: int, wallet_address: str, wallet_name: str = "", chain: str = "mainnet") -> bool:
    """Foydalanuvchining ulangan TON hamyonini saqlash yoki yangilash"""
    wallet_address = to_user_friendly_address(wallet_address.strip())
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_ton_wallets (tg_user_id, wallet_address, wallet_name, chain, connected_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE SET
                wallet_address = EXCLUDED.wallet_address,
                wallet_name = EXCLUDED.wallet_name,
                chain = EXCLUDED.chain,
                connected_at = NOW()
        """, (tg_user_id, wallet_address.strip(), wallet_name, chain))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"save_user_ton_wallet error: {e}")
        return False
    finally:
        conn.close()


def get_user_ton_wallet(tg_user_id: int) -> dict | None:
    """Foydalanuvchining ulangan TON hamyonini olish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_ton_wallets WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user_ton_wallet error: {e}")
        return None
    finally:
        conn.close()


def delete_user_ton_wallet(tg_user_id: int) -> bool:
    """Foydalanuvchining ulangan TON hamyonini o'chirish/uzish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_ton_wallets WHERE tg_user_id = %s", (tg_user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"delete_user_ton_wallet error: {e}")
        return False
    finally:
        conn.close()


# ==================== 8. 3D NFT STUDIO ITEMS ====================

def create_nft_item(tg_user_id: int, title: str, description: str = "", glb_file_id: str = "",
                    preview_image_id: str = "", ipfs_metadata_uri: str = "",
                    polygon_token_id: int = 0, voucher_data: str = "",
                    price_uzs: int = 0, price_matic: float = 0.0,
                    video_file_path: str = "", glb_file_path: str = "",
                    status: str = "draft") -> int:
    """Yangi 3D NFT elementini bazaga kiritish (qaytaradi: nft_item_id)"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO nft_items (
                tg_user_id, title, description, glb_file_id, preview_image_id,
                ipfs_metadata_uri, polygon_token_id, voucher_data,
                price_uzs, price_matic, video_file_path, glb_file_path,
                status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            tg_user_id, title, description, glb_file_id, preview_image_id,
            ipfs_metadata_uri, polygon_token_id, voucher_data,
            price_uzs, price_matic, video_file_path, glb_file_path, status
        ))
        row = cur.fetchone()
        item_id = (row["id"] if isinstance(row, dict) else row[0]) if row else 0
        conn.commit()
        return item_id
    except Exception as e:
        conn.rollback()
        print(f"create_nft_item error: {e}")
        return 0
    finally:
        conn.close()


def get_all_nfts(limit: int = 50) -> list:
    """Barcha NFT elementlarini olish (admin panel uchun)"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM nft_items ORDER BY id DESC LIMIT %s", (limit,))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_nfts error: {e}")
        return []
    finally:
        conn.close()


def get_nft_item(item_id: int) -> dict | None:
    """Bitta NFT elementini ID bo'yicha olish"""
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM nft_items WHERE id = %s", (item_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_nft_item error: {e}")
        return None
    finally:
        conn.close()


def get_user_nfts(tg_user_id: int) -> list:
    """Foydalanuvchining barcha yaratgan NFT larini olish"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM nft_items WHERE tg_user_id = %s ORDER BY id DESC", (tg_user_id,))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_user_nfts error: {e}")
        return []
    finally:
        conn.close()


def get_listed_nfts(limit: int = 20) -> list:
    """Sotuvga qo'yilgan (status='listed') NFT lar ro'yxati"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM nft_items WHERE status = 'listed' ORDER BY id DESC LIMIT %s", (limit,))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_listed_nfts error: {e}")
        return []
    finally:
        conn.close()


def update_nft_status(item_id: int, status: str = None, price_uzs: int = None,
                      buyer_user_id: int = None, tx_hash: str = None,
                      nft_address: str = None) -> bool:
    """NFT holatini yangilash (draft, listed, sold, cancelled)"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        updates = []
        params = []
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if price_uzs is not None:
            updates.append("price_uzs = %s")
            params.append(price_uzs)
        if buyer_user_id is not None:
            updates.append("buyer_user_id = %s")
            params.append(buyer_user_id)
        if tx_hash is not None:
            updates.append("minted_tx_hash = %s")
            params.append(tx_hash)
        if nft_address is not None:
            updates.append("nft_address = %s")
            params.append(nft_address)
        
        if not updates:
            return True
            
        params.append(item_id)
        query = f"UPDATE nft_items SET {', '.join(updates)} WHERE id = %s"
        cur.execute(query, tuple(params))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"update_nft_status error: {e}")
        return False
    finally:
        conn.close()


def get_pending_nft_mints() -> list:
    """Kutilayotgan (pending_mint) va TON manzili bor NFT larni olish"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tg_user_id, buyer_user_id, title, description, nft_address, status, created_at
            FROM nft_items
            WHERE status = 'pending_mint'
              AND nft_address IS NOT NULL
              AND nft_address != ''
            ORDER BY id ASC
        """)
        return [dict(r) for r in (cur.fetchall() or [])]
    except Exception as e:
        print(f"get_pending_nft_mints error: {e}")
        return []
    finally:
        conn.close()


def set_bot_config(key: str, val: str) -> bool:
    """bot_config jadvaliga sozlamani saqlash"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bot_config (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """, (key, str(val)))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"set_bot_config error: {e}")
        return False
    finally:
        conn.close()


def get_bot_config(key: str, default: str = None) -> str:
    """bot_config jadvalidan sozlamani olish"""
    conn = get_db()
    if not conn: return default
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM bot_config WHERE key = %s", (key,))
        row = cur.fetchone()
        return str(row["value"]) if row and row.get("value") is not None else default
    except Exception as e:
        print(f"get_bot_config error: {e}")
        return default
    finally:
        conn.close()


# ==================== ADMIN SERVICE TOGGLE (Xizmatlarni yoqish/o'chirish) ====================

# Admin boshqaradigan barcha xizmatlar ro'yxati
ADMIN_SERVICES = {
    "ventebot_store": "🚀 VenteBot Do'koni",
    "mystery_box": "🎁 Mystery Box",
    "pvp_battles": "⚔️ PvP Battles",
    "wheel_spin": "🎰 Wheel Spin",
    "duel": "🎮 Duel",
    "lottery": "🎟️ Lotereya",
    "marketplace": "🛒 Marketplace",
    "crypto_pay": "💎 CryptoPay",
    "flux_ai": "🎨 Flux AI",
    "vip": "👑 VIP",
    "upgrader": "🔄 Upgrader",
    "scratch_cards": "🎫 Scratch Cards",
    "daily_streak": "📅 Daily Streak",
}


def is_service_disabled(service_key: str) -> bool:
    """Xizmat admin tomonidan o'chirilganmi tekshirish (60s kesh bilan)"""
    cache_key = f"svc_off_{service_key}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached == "1"

    conn = get_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM bot_config WHERE key = %s", (f"service_disabled_{service_key}",))
        row = cur.fetchone()
        disabled = bool(row and str(row.get("value", "") if isinstance(row, dict) else row[0]) == "1")
        _set_cached(cache_key, "1" if disabled else "0", 60)
        return disabled
    except Exception as e:
        print(f"is_service_disabled error: {e}")
        return False
    finally:
        conn.close()


def toggle_service(service_key: str, disabled: bool) -> bool:
    """Xizmatni yoqish (disabled=False) yoki o'chirish (disabled=True)"""
    _invalidate_cached(f"svc_off_{service_key}")
    conn = get_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        val = "1" if disabled else "0"
        cur.execute("""
            INSERT INTO bot_config (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """, (f"service_disabled_{service_key}", val))
        conn.commit()
        _set_cached(f"svc_off_{service_key}", val, 60)
        return True
    except Exception as e:
        conn.rollback()
        print(f"toggle_service error: {e}")
        return False
    finally:
        conn.close()


def get_all_service_states() -> dict:
    """Barcha xizmatlar holati: {key: True/False (disabled)}"""
    result = {k: False for k in ADMIN_SERVICES}
    conn = get_db()
    if not conn:
        return result
    try:
        cur = conn.cursor()
        keys = [f"service_disabled_{k}" for k in ADMIN_SERVICES]
        placeholders = ",".join(["%s"] * len(keys))
        cur.execute(f"SELECT key, value FROM bot_config WHERE key IN ({placeholders})", keys)
        rows = cur.fetchall()
        for row in rows:
            k = (row["key"] if isinstance(row, dict) else row[0]).replace("service_disabled_", "")
            v = str(row["value"] if isinstance(row, dict) else row[1])
            if k in result:
                result[k] = (v == "1")
        return result
    except Exception as e:
        print(f"get_all_service_states error: {e}")
        return result
    finally:
        conn.close()


# ==================== VENTEBOT RESELLER ORDER REPOSITORY ====================

def save_ventebot_order(tg_user_id: int, product_id: int, product_name: str, quantity: int,
                        amount_uzs: int, amount_usd: float, delivery_type: str = "",
                        activation_identifier: str = "", status: str = "COMPLETED",
                        ventebot_order_id: int = None, delivered_data: str = "",
                        idempotency_key: str = "") -> int:
    """VenteBot orqali berilgan yangi buyurtmani bazaga saqlash"""
    conn = get_db()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ventebot_reseller_orders (
                tg_user_id, product_id, product_name, quantity, amount_uzs,
                amount_usd, delivery_type, activation_identifier, status,
                ventebot_order_id, delivered_data, idempotency_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO UPDATE SET
                status = EXCLUDED.status,
                ventebot_order_id = EXCLUDED.ventebot_order_id,
                delivered_data = EXCLUDED.delivered_data
            RETURNING id
        """, (
            tg_user_id, product_id, product_name, quantity, amount_uzs,
            amount_usd, delivery_type, activation_identifier, status,
            ventebot_order_id, delivered_data, idempotency_key
        ))
        row = cur.fetchone()
        conn.commit()
        return int(row["id"]) if row else 0
    except Exception as e:
        conn.rollback()
        print(f"save_ventebot_order error: {e}")
        return 0
    finally:
        conn.close()


def get_user_ventebot_orders(tg_user_id: int, limit: int = 20) -> list:
    """Foydalanuvchining VenteBot orqali sotib olgan buyurtmalari tarixi"""
    conn = get_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM ventebot_reseller_orders
            WHERE tg_user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (tg_user_id, limit))
        rows = cur.fetchall()
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        print(f"get_user_ventebot_orders error: {e}")
        return []
    finally:
        conn.close()


def update_ventebot_order_status(order_id: int, status: str, delivered_data: str = None) -> bool:
    """VenteBot buyurtmasi statusini yangilash (masalan, REFUNDED yoki COMPLETED)"""
    conn = get_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        if delivered_data is not None:
            cur.execute("""
                UPDATE ventebot_reseller_orders
                SET status = %s, delivered_data = %s
                WHERE id = %s
            """, (status, delivered_data, order_id))
        else:
            cur.execute("""
                UPDATE ventebot_reseller_orders
                SET status = %s
                WHERE id = %s
            """, (status, order_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"update_ventebot_order_status error: {e}")
        return False
    finally:
        conn.close()


# ==================== TELEGRAM STARS REAL GIFTS & PENDING QUEUE ====================

def save_gift_record(
    tg_user_id: int,
    gift_id: str,
    tier_key: str = "",
    case_name: str = "",
    prize_name: str = "",
    prize_stars: int = 0,
    status: str = "pending",
    error_message: str = None
) -> int:
    """Yangi yutilgan sovg'a yozuvini saqlash (status: 'sent', 'pending', 'pending_balance', 'pending_privacy', 'failed')"""
    conn = get_db()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        sent_at_sql = "NOW()" if status == "sent" else "NULL"
        cur.execute(f"""
            INSERT INTO pending_gifts (
                tg_user_id, gift_id, tier_key, case_name, prize_name, prize_stars, status, error_message, created_at, updated_at, sent_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), {sent_at_sql})
            RETURNING id
        """, (tg_user_id, str(gift_id), tier_key, case_name, prize_name, prize_stars, status, error_message))
        res = cur.fetchone()
        conn.commit()
        if res:
            return res["id"] if isinstance(res, dict) else res[0]
        return 0
    except Exception as e:
        conn.rollback()
        print(f"save_gift_record error: {e}")
        return 0
    finally:
        conn.close()


def get_pending_gifts(status: str = None, limit: int = 100) -> list:
    """Kutilayotgan sovg'alarni olish (status berilmasa, barcha yuborilmaganlar olinadi)"""
    conn = get_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        if status:
            cur.execute("""
                SELECT id, tg_user_id, gift_id, tier_key, case_name, prize_name, prize_stars, status, error_message, created_at
                FROM pending_gifts
                WHERE status = %s
                ORDER BY prize_stars ASC, id ASC
                LIMIT %s
            """, (status, limit))
        else:
            cur.execute("""
                SELECT id, tg_user_id, gift_id, tier_key, case_name, prize_name, prize_stars, status, error_message, created_at
                FROM pending_gifts
                WHERE status != 'sent'
                ORDER BY prize_stars ASC, id ASC
                LIMIT %s
            """, (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            if isinstance(r, dict):
                results.append(r)
            else:
                results.append({
                    "id": r[0],
                    "tg_user_id": r[1],
                    "gift_id": r[2],
                    "tier_key": r[3],
                    "case_name": r[4],
                    "prize_name": r[5],
                    "prize_stars": r[6],
                    "status": r[7],
                    "error_message": r[8],
                    "created_at": r[9]
                })
        return results
    except Exception as e:
        print(f"get_pending_gifts error: {e}")
        return []
    finally:
        conn.close()


def update_gift_record_status(record_id: int, status: str, error_message: str = None) -> bool:
    """Sovg'a yozuvi statusini yangilash (masalan, yuborilganda 'sent')"""
    conn = get_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        if status == "sent":
            cur.execute("""
                UPDATE pending_gifts
                SET status = %s, error_message = %s, sent_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """, (status, error_message, record_id))
        else:
            cur.execute("""
                UPDATE pending_gifts
                SET status = %s, error_message = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, error_message, record_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"update_gift_record_status error: {e}")
        return False
    finally:
        conn.close()


def get_user_gift_history(tg_user_id: int, limit: int = 20) -> list:
    """Foydalanuvchining sovg'alar tarixi"""
    conn = get_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, gift_id, case_name, prize_name, prize_stars, status, created_at, sent_at
            FROM pending_gifts
            WHERE tg_user_id = %s
            ORDER BY id DESC
            LIMIT %s
        """, (tg_user_id, limit))
        rows = cur.fetchall()
        results = []
        for r in rows:
            if isinstance(r, dict):
                results.append(r)
            else:
                results.append({
                    "id": r[0],
                    "gift_id": r[1],
                    "case_name": r[2],
                    "prize_name": r[3],
                    "prize_stars": r[4],
                    "status": r[5],
                    "created_at": r[6],
                    "sent_at": r[7]
                })
        return results
    except Exception as e:
        print(f"get_user_gift_history error: {e}")
        return []
    finally:
        conn.close()


def get_user_total_stars_spent(tg_user_id: int) -> int:
    """Foydalanuvchining botda jami sarflagan Stars miqdorini aniqlash (Telegram Premium filtri uchun)"""
    conn = get_db()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        # 1. user_mystery_stats dan tekshirish
        cur.execute("SELECT total_stars_spent FROM user_mystery_stats WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if row:
            spent = row["total_stars_spent"] if isinstance(row, dict) else row[0]
            if spent and spent > 0:
                return int(spent)
        
        # 2. Agar mavjud bo'lmasa mystery_box_logs dan yig'ish
        cur.execute("""
            SELECT COALESCE(SUM(cost_uzs), 0)
            FROM mystery_box_logs
            WHERE tg_user_id = %s AND prize_type LIKE 'stars_%%'
        """, (tg_user_id,))
        m_row = cur.fetchone()
        sum_spent = m_row[0] if m_row else 0
        return int(sum_spent)
    except Exception as e:
        print(f"get_user_total_stars_spent error: {e}")
        return 0
    finally:
        conn.close()


def get_user_bad_luck_streak(tg_user_id: int) -> int:
    """Foydalanuvchining joriy ketma-ket omadsizlik soni"""
    conn = get_db()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT bad_luck_streak FROM user_mystery_stats WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if row:
            return row["bad_luck_streak"] if isinstance(row, dict) else row[0]
        return 0
    except Exception as e:
        return 0
    finally:
        conn.close()


def update_user_bad_luck(tg_user_id: int, is_loss: bool, stars_cost: int = 0) -> int:
    """Omadsizlik sonini yangilash va umumiy sarflangan Starsni yozish"""
    conn = get_db()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_mystery_stats (tg_user_id, bad_luck_streak, total_cases_opened, total_stars_spent, updated_at)
            VALUES (%s, %s, 1, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET bad_luck_streak = CASE WHEN %s THEN user_mystery_stats.bad_luck_streak + 1 ELSE 0 END,
                total_cases_opened = user_mystery_stats.total_cases_opened + 1,
                total_stars_spent = user_mystery_stats.total_stars_spent + %s,
                updated_at = NOW()
            RETURNING bad_luck_streak
        """, (tg_user_id, 1 if is_loss else 0, stars_cost, is_loss, stars_cost))
        row = cur.fetchone()
        conn.commit()
        if row:
            return row["bad_luck_streak"] if isinstance(row, dict) else row[0]
        return 0
    except Exception as e:
        conn.rollback()
        print(f"update_user_bad_luck error: {e}")
        return 0
    finally:
        conn.close()


def recycle_gift_record(record_id: int, tg_user_id: int, refund_uzs: int) -> dict:
    """
    Sovg'ani 75% keshbek evaziga sotish (Recycle).
    Kassada 25% sof foyda qoladi, bot Stars sarflamaydi, foydalanuvchi balansiga so'm qo'shiladi.
    """
    conn = get_db()
    if not conn:
        return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status, prize_name, prize_stars FROM pending_gifts WHERE id = %s AND tg_user_id = %s FOR UPDATE", (record_id, tg_user_id))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return {"ok": False, "error": "Sovg'a topilmadi!"}
            
        status = row["status"] if isinstance(row, dict) else row[1]
        prize_name = row["prize_name"] if isinstance(row, dict) else row[2]
        
        if status in ("sent", "recycled"):
            conn.rollback()
            return {"ok": False, "error": f"Ushbu sovg'a allaqachon {status} qilingan!"}

        # 1. Sovg'a holatini recycled ga o'tkazamiz
        cur.execute("""
            UPDATE pending_gifts
            SET status = 'recycled', error_message = 'Foydalanuvchi 75%% keshbekka sotdi', updated_at = NOW()
            WHERE id = %s
        """, (record_id,))

        # 2. Foydalanuvchi balansiga 75% keshbek qo'shamiz
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                updated_at = NOW()
            RETURNING balance_uzs
        """, (tg_user_id, refund_uzs))
        b_res = cur.fetchone()
        new_bal = b_res["balance_uzs"] if isinstance(b_res, dict) else b_res[0]

        conn.commit()
        _invalidate_cached(f"bal_{tg_user_id}")
        return {
            "ok": True,
            "refund_uzs": refund_uzs,
            "new_balance": new_bal,
            "prize_name": prize_name
        }
    except Exception as e:
        conn.rollback()
        print(f"recycle_gift_record error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def create_gift_case_voucher(created_by: int, tier_key: str, case_name: str, price_stars: int) -> str:
    """Do'stga keys sovg'a qilish uchun maxsus vaucher kod yaratish"""
    import secrets
    conn = get_db()
    if not conn:
        return ""
    code = "GCASE-" + secrets.token_hex(4).upper()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO gift_case_vouchers (code, tier_key, case_name, price_stars, created_by, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (code, tier_key, case_name, price_stars, created_by))
        conn.commit()
        return code
    except Exception as e:
        conn.rollback()
        print(f"create_gift_case_voucher error: {e}")
        return ""
    finally:
        conn.close()


def claim_gift_case_voucher(code: str, claimed_by: int) -> dict:
    """Do'stga berilgan keys vaucherini ochish"""
    conn = get_db()
    if not conn:
        return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    clean_code = str(code).strip().upper()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM gift_case_vouchers WHERE code = %s FOR UPDATE", (clean_code,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return {"ok": False, "error": "Bunday sovg'a keys vaucheri topilmadi!"}

        status = row["status"] if isinstance(row, dict) else row[6]
        if status != "active":
            conn.rollback()
            return {"ok": False, "error": "Ushbu sovg'a keys allaqachon ochilgan yoki bekor qilingan!"}

        tier_key = row["tier_key"] if isinstance(row, dict) else row[2]
        case_name = row["case_name"] if isinstance(row, dict) else row[3]
        created_by = row["created_by"] if isinstance(row, dict) else row[5]

        # Holatini claimed ga o'tkazish
        cur.execute("""
            UPDATE gift_case_vouchers
            SET status = 'claimed', claimed_by = %s, claimed_at = NOW()
            WHERE code = %s
        """, (claimed_by, clean_code))
        conn.commit()

        return {
            "ok": True,
            "tier_key": tier_key,
            "case_name": case_name,
            "created_by": created_by
        }
    except Exception as e:
        conn.rollback()
        print(f"claim_gift_case_voucher error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ==================== 2.4 ADMIN FOYDALANUVCHILAR & HAMYON BOSHQARUVI ====================

def record_user_activity(tg_user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Har qanday foydalanuvchi murojaatida uni bot_users jadvaliga saqlash va faolligini yangilash (5 daqiqalik kesh bilan)"""
    cache_key = f"act_{tg_user_id}"
    if _get_cached(cache_key):
        return
    _set_cached(cache_key, True, 300)

    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bot_users (tg_user_id, username, first_name, last_name, created_at, last_active_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (tg_user_id) DO UPDATE SET
                username = COALESCE(EXCLUDED.username, bot_users.username),
                first_name = COALESCE(EXCLUDED.first_name, bot_users.first_name),
                last_name = COALESCE(EXCLUDED.last_name, bot_users.last_name),
                last_active_at = NOW()
        """, (tg_user_id, username, first_name, last_name))
        
        # User_balances jadvalida ham bo'lmasa yaratib qo'yamiz
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, 0, NOW())
            ON CONFLICT (tg_user_id) DO NOTHING
        """, (tg_user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"record_user_activity error: {e}")
    finally:
        conn.close()


def sync_tg_user_profile(tg_user_id: int):
    """Telegram Bot API orqali foydalanuvchining ism va username ini avtomatik yangilash"""
    try:
        import urllib.request, json
        from config import BOT_TOKEN
        if not BOT_TOKEN: return None
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat?chat_id={tg_user_id}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                res = data.get("result", {})
                uname = res.get("username")
                fname = res.get("first_name")
                lname = res.get("last_name")
                c = get_db()
                if c:
                    cr = c.cursor()
                    cr.execute("""
                        INSERT INTO bot_users (tg_user_id, username, first_name, last_name, last_active_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (tg_user_id) DO UPDATE
                        SET username = COALESCE(EXCLUDED.username, bot_users.username),
                            first_name = COALESCE(EXCLUDED.first_name, bot_users.first_name),
                            last_name = COALESCE(EXCLUDED.last_name, bot_users.last_name),
                            last_active_at = NOW()
                    """, (tg_user_id, uname, fname, lname))
                    c.commit()
                    c.close()
                return {"username": uname, "first_name": fname, "last_name": lname}
    except Exception:
        pass
    return None


def get_all_bot_users(page: int = 1, limit: int = 10, search: str = "") -> dict:
    """Admin uchun barcha foydalanuvchilar ro'yxati (sahifalangan va qidiruv bilan)"""
    conn = get_db()
    if not conn: return {"users": [], "total_count": 0, "total_pages": 1, "page": 1}
    offset = (max(1, page) - 1) * limit
    try:
        cur = conn.cursor()
        params = []
        where_clause = ""
        clean_s = str(search).strip()
        if clean_s:
            s_like = f"%{clean_s.lstrip('@')}%"
            if clean_s.isdigit():
                where_clause = "WHERE u.tg_user_id = %s OR u.username ILIKE %s OR u.first_name ILIKE %s"
                params.extend([int(clean_s), s_like, s_like])
            else:
                where_clause = "WHERE u.username ILIKE %s OR u.first_name ILIKE %s"
                params.extend([s_like, s_like])

        # Jami foydalanuvchilar soni
        cur.execute(f"SELECT COUNT(*) as count FROM bot_users u {where_clause}", tuple(params))
        cnt_row = cur.fetchone()
        total_count = cnt_row["count"] if isinstance(cnt_row, dict) else cnt_row[0]

        # Foydalanuvchilar ma'lumotlari
        query = f"""
            SELECT 
                u.tg_user_id,
                u.username,
                u.first_name,
                u.last_name,
                u.created_at,
                u.last_active_at,
                u.is_banned,
                COALESCE(b.balance_uzs, 0) AS balance_uzs,
                COALESCE(ms.total_stars_spent, 0) AS total_stars_spent,
                COALESCE(ms.bad_luck_streak, 0) AS bad_luck_streak,
                p.phone_number
            FROM bot_users u
            LEFT JOIN user_balances b ON b.tg_user_id = u.tg_user_id
            LEFT JOIN user_mystery_stats ms ON ms.tg_user_id = u.tg_user_id
            LEFT JOIN user_phones p ON p.tg_user_id = u.tg_user_id
            {where_clause}
            ORDER BY u.last_active_at DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        query_params = params + [limit, offset]
        cur.execute(query, tuple(query_params))
        rows = cur.fetchall()
        users = [dict(r) for r in rows]
        
        # Username yoki ism yetishmayotgan bo'lsa jonli Telegram API orqali to'ldiramiz
        for u in users:
            if not u.get("username") and not u.get("first_name"):
                enriched = sync_tg_user_profile(u["tg_user_id"])
                if enriched:
                    if enriched.get("username"): u["username"] = enriched["username"]
                    if enriched.get("first_name"): u["first_name"] = enriched["first_name"]
                    if enriched.get("last_name"): u["last_name"] = enriched["last_name"]

        total_pages = max(1, (total_count + limit - 1) // limit)
        return {
            "users": users,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page
        }
    except Exception as e:
        print(f"get_all_bot_users error: {e}")
        return {"users": [], "total_count": 0, "total_pages": 1, "page": 1}
    finally:
        conn.close()


def get_user_full_details(tg_user_id: int) -> dict:
    """Bitta foydalanuvchining barcha hamyon, sovg'a va xavfsizlik ma'lumotlari"""
    user_data = {
        "tg_user_id": tg_user_id,
        "username": None,
        "first_name": "Foydalanuvchi",
        "last_name": None,
        "created_at": None,
        "last_active_at": None,
        "is_banned": bool(is_user_antifraud_banned(tg_user_id)),
        "is_kyc_verified": bool(is_user_kyc_verified(tg_user_id)),
        "balance_uzs": int(get_user_balance(tg_user_id)),
        "ton_balance": float(get_user_ton_balance(tg_user_id)),
        "ton_wallet": get_user_ton_wallet(tg_user_id),
        "phone_number": None,
        "total_stars_spent": 0,
        "bad_luck_streak": 0,
        "total_cases_opened": 0,
        "gifts_count": 0,
        "purchases_count": 0,
        "purchases_spent_uzs": 0
    }
    conn = get_db()
    if not conn: return user_data
    try:
        cur = conn.cursor()
        # Profile
        try:
            cur.execute("SELECT * FROM bot_users WHERE tg_user_id = %s", (tg_user_id,))
            u_row = cur.fetchone()
            if u_row:
                for k, v in dict(u_row).items():
                    if k in user_data and v is not None:
                        user_data[k] = v
            if not user_data.get("username") or user_data.get("first_name") == "Foydalanuvchi":
                enriched = sync_tg_user_profile(tg_user_id)
                if enriched:
                    if enriched.get("username"): user_data["username"] = enriched["username"]
                    if enriched.get("first_name"): user_data["first_name"] = enriched["first_name"]
                    if enriched.get("last_name"): user_data["last_name"] = enriched["last_name"]
        except Exception:
            conn.rollback()

        # Telefon raqami
        try:
            cur.execute("SELECT phone_number FROM user_phones WHERE tg_user_id = %s", (tg_user_id,))
            p_row = cur.fetchone()
            if p_row:
                user_data["phone_number"] = p_row["phone_number"] if isinstance(p_row, dict) else p_row[0]
        except Exception:
            conn.rollback()

        # Mystery Stats (Stars sarfi, streak, o'yinlar)
        try:
            cur.execute("SELECT total_stars_spent, bad_luck_streak, total_cases_opened FROM user_mystery_stats WHERE tg_user_id = %s", (tg_user_id,))
            m_row = cur.fetchone()
            if m_row:
                user_data["total_stars_spent"] = m_row.get("total_stars_spent", 0) or 0
                user_data["bad_luck_streak"] = m_row.get("bad_luck_streak", 0) or 0
                user_data["total_cases_opened"] = m_row.get("total_cases_opened", 0) or 0
        except Exception:
            conn.rollback()

        # Sovg'alar soni
        try:
            cur.execute("SELECT COUNT(*) as count FROM pending_gifts WHERE tg_user_id = %s", (tg_user_id,))
            g_row = cur.fetchone()
            if g_row:
                user_data["gifts_count"] = g_row.get("count", 0) if isinstance(g_row, dict) else g_row[0]
        except Exception:
            conn.rollback()

        # Xaridlar soni va sarflangan summa
        try:
            cur.execute("SELECT COUNT(*) as count, COALESCE(SUM(total_cost_uzs), 0) as spent_uzs FROM user_purchases WHERE tg_user_id = %s", (tg_user_id,))
            pur_row = cur.fetchone()
            if pur_row:
                user_data["purchases_count"] = pur_row.get("count", 0) if isinstance(pur_row, dict) else pur_row[0]
                user_data["purchases_spent_uzs"] = pur_row.get("spent_uzs", 0) if isinstance(pur_row, dict) else pur_row[1]
        except Exception:
            conn.rollback()

        return user_data
    except Exception as e:
        print(f"get_user_full_details error: {e}")
        return user_data
    finally:
        conn.close()



def admin_set_user_balance(tg_user_id: int, new_balance_uzs: int) -> int:
    """Admin foydalanuvchi balansini aniq summaga o'rnatishi"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE 
            SET balance_uzs = EXCLUDED.balance_uzs, updated_at = NOW()
            RETURNING balance_uzs
        """, (tg_user_id, max(0, int(new_balance_uzs))))
        b_res = cur.fetchone()
        nb = b_res["balance_uzs"] if isinstance(b_res, dict) else b_res[0]
        conn.commit()
        _invalidate_cached(f"bal_{tg_user_id}")
        return nb
    except Exception as e:
        conn.rollback()
        print(f"admin_set_user_balance error: {e}")
        raise
    finally:
        conn.close()


def admin_adjust_user_balance(tg_user_id: int, delta_uzs: int) -> int:
    """Admin foydalanuvchi balansiga summa qo'shishi yoki ayirishi"""
    conn = get_db()
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, GREATEST(0, %s), NOW())
            ON CONFLICT (tg_user_id) DO UPDATE 
            SET balance_uzs = GREATEST(0, user_balances.balance_uzs + %s), updated_at = NOW()
            RETURNING balance_uzs
        """, (tg_user_id, delta_uzs, delta_uzs))
        b_res = cur.fetchone()
        nb = b_res["balance_uzs"] if isinstance(b_res, dict) else b_res[0]
        conn.commit()
        _invalidate_cached(f"bal_{tg_user_id}")
        return nb
    except Exception as e:
        conn.rollback()
        print(f"admin_adjust_user_balance error: {e}")
        raise
    finally:
        conn.close()


def admin_toggle_user_ban(tg_user_id: int, is_banned: bool, reason: str = "") -> bool:
    """Admin foydalanuvchini bloklash yoki blokdan chiqarishi"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE bot_users
            SET is_banned = %s, admin_notes = %s
            WHERE tg_user_id = %s
        """, (is_banned, reason if reason else None, tg_user_id))
        
        if is_banned:
            cur.execute("""
                INSERT INTO banned_antifraud_users (tg_user_id, reason, banned_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (tg_user_id, reason or "Admin tomonidan bloklandi"))
        else:
            cur.execute("DELETE FROM banned_antifraud_users WHERE tg_user_id = %s", (tg_user_id,))
            
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"admin_toggle_user_ban error: {e}")
        return False
    finally:
        conn.close()


# ==================== VIP SUBSCRIPTIONS (69,000 UZS) ====================

def is_user_vip(tg_user_id: int) -> bool:
    """Foydalanuvchida faol VIP status mavjudligini tekshirish (kesh bilan)"""
    cached = _get_cached(f"vip_{tg_user_id}")
    if cached is not None:
        return bool(cached)

    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT is_vip, vip_expires_at FROM user_vip_subscriptions
            WHERE tg_user_id = %s
        """, (tg_user_id,))
        row = cur.fetchone()
        if not row:
            _set_cached(f"vip_{tg_user_id}", False, 180)
            return False
        
        is_vip = bool(row["is_vip"] if isinstance(row, dict) else row[0])
        exp = row["vip_expires_at"] if isinstance(row, dict) else row[1]
        
        if is_vip and exp:
            import datetime
            if datetime.datetime.now() > exp:
                cur.execute("UPDATE user_vip_subscriptions SET is_vip = FALSE WHERE tg_user_id = %s", (tg_user_id,))
                conn.commit()
                _set_cached(f"vip_{tg_user_id}", False, 180)
                return False

        _set_cached(f"vip_{tg_user_id}", is_vip, 300 if is_vip else 180)
        return is_vip
    except Exception as e:
        print(f"is_user_vip error: {e}")
        return False
    finally:
        conn.close()

def get_user_vip_info(tg_user_id: int) -> dict:
    """Foydalanuvchi VIP obunasi haqida to'liq ma'lumot (kesh bilan)"""
    cached = _get_cached(f"vip_info_{tg_user_id}")
    if cached is not None:
        return cached

    conn = get_db()
    if not conn: return {"is_vip": False}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_vip_subscriptions WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row:
            res = {"is_vip": False, "tg_user_id": tg_user_id}
            _set_cached(f"vip_info_{tg_user_id}", res, 300)
            return res
        d = dict(row)
        import datetime
        exp = d.get("vip_expires_at")
        if exp and datetime.datetime.now() > exp:
            d["is_vip"] = False
        _set_cached(f"vip_info_{tg_user_id}", d, 300)
        return d
    except Exception as e:
        print(f"get_user_vip_info error: {e}")
        return {"is_vip": False}
    finally:
        conn.close()

def activate_user_vip(tg_user_id: int, days: int = 30, plan_type: str = "vip_69k") -> bool:
    """Foydalanuvchiga VIP tarifni faollashtirish yoki muddatini uzaytirish"""
    conn = get_db()
    if not conn: return False
    try:
        import datetime
        cur = conn.cursor()
        cur.execute("SELECT vip_expires_at, is_vip FROM user_vip_subscriptions WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        
        now = datetime.datetime.now()
        if row and (row["is_vip"] if isinstance(row, dict) else row[1]):
            curr_exp = row["vip_expires_at"] if isinstance(row, dict) else row[0]
            start_date = curr_exp if curr_exp and curr_exp > now else now
        else:
            start_date = now
            
        new_exp = start_date + datetime.timedelta(days=days)
        
        cur.execute("""
            INSERT INTO user_vip_subscriptions (tg_user_id, is_vip, vip_expires_at, plan_type, updated_at)
            VALUES (%s, TRUE, %s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET is_vip = TRUE,
                vip_expires_at = EXCLUDED.vip_expires_at,
                plan_type = EXCLUDED.plan_type,
                updated_at = NOW()
        """, (tg_user_id, new_exp, plan_type))
        conn.commit()
        _set_cached(f"vip_{tg_user_id}", True, 300)
        _invalidate_cached(f"vip_info_{tg_user_id}")
        _invalidate_cached(f"tier_{tg_user_id}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"activate_user_vip error: {e}")
        return False
    finally:
        conn.close()

def get_user_verification_tier(tg_user_id: int) -> dict:
    """
    Foydalanuvchining verifikatsiya va tarif darajasini aniqlash (kesh bilan):
    - tier 1: "unverified" (telefon yoki kanal a'zoligi yo'q)
    - tier 2: "half_verified" (telefon raqam tasdiqlangan + kanalga a'zo)
    - tier 3: "full_verified" (3D face biometrik tasdiqlangan)
    - tier 4: "vip" (69,000 UZS lik VIP faol)
    """
    cached = _get_cached(f"tier_{tg_user_id}")
    if cached is not None:
        return cached

    has_phone = bool(get_telegram_phone(tg_user_id))
    is_face = is_user_kyc_verified(tg_user_id)
    vip_active = is_user_vip(tg_user_id)
    
    if vip_active:
        tier_code = "vip"
        tier_level = 4
        tier_title = "CreatorFlow VIP (69,000 UZS)"
    elif is_face:
        tier_code = "full_verified"
        tier_level = 3
        tier_title = "To'liq Tasdiqlangan (3D Biometrik)"
    elif has_phone:
        tier_code = "half_verified"
        tier_level = 2
        tier_title = "Yarim Tasdiqlangan (Telefon + Kanal)"
    else:
        tier_code = "unverified"
        tier_level = 1
        tier_title = "Tasdiqlanmagan"

    res = {
        "tier_level": tier_level,
        "tier_code": tier_code,
        "tier_title": tier_title,
        "has_phone": has_phone,
        "is_face_verified": is_face,
        "is_vip": vip_active
    }
    _set_cached(f"tier_{tg_user_id}", res, 180)
    return res


# ==================== CHANNEL CONTESTS & GIVEAWAYS ====================

def create_channel_contest(title: str, prize_text: str, duration_hours: int = 24, channel_msg_id: int = None) -> int:
    """Kanal uchun yangi konkurs yaratish"""
    conn = get_db()
    if not conn: return 0
    try:
        import datetime
        ends_at = datetime.datetime.now() + datetime.timedelta(hours=duration_hours)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO channel_contests (title, prize_text, channel_msg_id, status, ends_at)
            VALUES (%s, %s, %s, 'active', %s)
            RETURNING id
        """, (title, prize_text, channel_msg_id, ends_at))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if isinstance(row, dict) else row[0]
    except Exception as e:
        conn.rollback()
        print(f"create_channel_contest error: {e}")
        return 0
    finally:
        conn.close()

def join_channel_contest(contest_id: int, tg_user_id: int, user_name: str = "") -> tuple:
    """Foydalanuvchini konkursga ro'yxatdan o'tkazish"""
    conn = get_db()
    if not conn: return False, "Database xatoligi"
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, ends_at FROM channel_contests WHERE id = %s", (contest_id,))
        c = cur.fetchone()
        if not c:
            return False, "Konkurs topilmadi"
        
        status = c["status"] if isinstance(c, dict) else c[0]
        ends_at = c["ends_at"] if isinstance(c, dict) else c[1]
        import datetime
        if status != "active" or (ends_at and datetime.datetime.now() > ends_at):
            return False, "Ushbu konkurs yakunlangan"

        cur.execute("""
            INSERT INTO contest_participants (contest_id, tg_user_id, user_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (contest_id, tg_user_id) DO NOTHING
            RETURNING id
        """, (contest_id, tg_user_id, user_name))
        row = cur.fetchone()
        conn.commit()
        if row:
            return True, "Muvaffaqiyatli qatnashdingiz! Omad yor bo'lsin!"
        else:
            return False, "Siz ushbu konkursda allaqachon ro'yxatdan o'tgansiz!"
    except Exception as e:
        conn.rollback()
        print(f"join_channel_contest error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_active_contests() -> list:
    """Hozirgi faol konkurslarni olish"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, COUNT(p.id) as participants_count
            FROM channel_contests c
            LEFT JOIN contest_participants p ON p.contest_id = c.id
            WHERE c.status = 'active' AND (c.ends_at IS NULL OR c.ends_at > NOW())
            GROUP BY c.id
            ORDER BY c.id DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        print(f"get_active_contests error: {e}")
        return []
    finally:
        conn.close()

def pick_contest_winners(contest_id: int, winners_count: int = 1) -> list:
    """Konkurs g'oliblarini tasodifiy aniqlash"""
    conn = get_db()
    if not conn: return []
    try:
        import random
        cur = conn.cursor()
        cur.execute("SELECT tg_user_id, user_name FROM contest_participants WHERE contest_id = %s", (contest_id,))
        participants = cur.fetchall()
        if not participants:
            return []
        p_list = [dict(p) for p in participants]
        winners = random.sample(p_list, min(len(p_list), winners_count))
        cur.execute("UPDATE channel_contests SET status = 'completed' WHERE id = %s", (contest_id,))
        conn.commit()
        return winners
    except Exception as e:
        conn.rollback()
        print(f"pick_contest_winners error: {e}")
        return []
    finally:
        conn.close()


# ==================== 1. WISHLIST / RESTOCK ALERTS ====================

def add_to_wishlist(tg_user_id: int, product_id: int, product_name: str) -> tuple:
    """Foydalanuvchini tovar zaxirasi to'ldirilganda eslatish ro'yxatiga qo'shish"""
    conn = get_db()
    if not conn: return False, "Database xatosi"
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO restock_wishlist (tg_user_id, product_id, product_name, notified, created_at)
            VALUES (%s, %s, %s, FALSE, NOW())
            ON CONFLICT (tg_user_id, product_id) DO UPDATE
            SET notified = FALSE, created_at = NOW()
            RETURNING id
        """, (tg_user_id, product_id, product_name))
        conn.commit()
        return True, "Zaxiraga kelganda sizga darhol xabar yuboramiz!"
    except Exception as e:
        conn.rollback()
        print(f"add_to_wishlist error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_wishlist_users_for_product(product_id: int) -> list:
    """Ushbu mahsulotni kutayotgan foydalanuvchilar ID ro'yxati"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT tg_user_id FROM restock_wishlist WHERE product_id = %s AND notified = FALSE", (product_id,))
        rows = cur.fetchall()
        return [r["tg_user_id"] if isinstance(r, dict) else r[0] for r in rows] if rows else []
    except Exception as e:
        print(f"get_wishlist_users_for_product error: {e}")
        return []
    finally:
        conn.close()

def mark_wishlist_notified(product_id: int):
    """Kutayotganlarga xabar yuborilgan deb belgilash"""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("UPDATE restock_wishlist SET notified = TRUE WHERE product_id = %s", (product_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"mark_wishlist_notified error: {e}")
    finally:
        conn.close()


# ==================== 2. ABANDONED CARTS (TASHLAB KETILGAN SAVAT) ====================

def record_cart_initiated(tg_user_id: int, product_id: int, product_name: str, price_uzs: int):
    """Foydalanuvchi to'lov bosqichiga kelganda qayd etish"""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO abandoned_carts (tg_user_id, product_id, product_name, price_uzs, notified, resolved, initiated_at)
            VALUES (%s, %s, %s, %s, FALSE, FALSE, NOW())
        """, (tg_user_id, product_id, product_name, price_uzs))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"record_cart_initiated error: {e}")
    finally:
        conn.close()

def resolve_cart(tg_user_id: int, product_id: int = None):
    """Xarid amalga oshgach savatni yopish"""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        if product_id:
            cur.execute("UPDATE abandoned_carts SET resolved = TRUE WHERE tg_user_id = %s AND product_id = %s AND resolved = FALSE", (tg_user_id, product_id))
        else:
            cur.execute("UPDATE abandoned_carts SET resolved = TRUE WHERE tg_user_id = %s AND resolved = FALSE", (tg_user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"resolve_cart error: {e}")
    finally:
        conn.close()

def get_abandoned_carts_to_notify(minutes_ago: int = 20) -> list:
    """20-30 daqiqa oldin boshlangan, lekin xarid qilinmagan savatlar ro'yxati"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tg_user_id, product_id, product_name, price_uzs
            FROM abandoned_carts
            WHERE resolved = FALSE AND notified = FALSE
              AND initiated_at <= NOW() - (%s || ' minutes')::INTERVAL
              AND initiated_at >= NOW() - INTERVAL '2 hours'
            LIMIT 20
        """, (str(minutes_ago),))
        rows = cur.fetchall()
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        print(f"get_abandoned_carts_to_notify error: {e}")
        return []
    finally:
        conn.close()

def mark_abandoned_cart_notified(cart_id: int):
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("UPDATE abandoned_carts SET notified = TRUE WHERE id = %s", (cart_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"mark_abandoned_cart_notified error: {e}")
    finally:
        conn.close()


# ==================== 3. FAST DROP PROMOS (TEZKOR PROMOKODLAR) ====================

def create_fast_drop_promo(code: str, reward_type: str = "balance", reward_value: int = 10000, max_uses: int = 3, duration_minutes: int = 60) -> int:
    """Kanalga tashlanadigan cheklangan promokod yaratish"""
    conn = get_db()
    if not conn: return 0
    try:
        import datetime
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO fast_drop_promos (code, reward_type, reward_value, max_uses, current_uses, expires_at)
            VALUES (%s, %s, %s, %s, 0, %s)
            ON CONFLICT (code) DO UPDATE
            SET reward_value = EXCLUDED.reward_value,
                max_uses = EXCLUDED.max_uses,
                current_uses = 0,
                expires_at = EXCLUDED.expires_at
            RETURNING id
        """, (code.strip().upper(), reward_type, reward_value, max_uses, expires_at))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if isinstance(row, dict) else row[0]
    except Exception as e:
        conn.rollback()
        print(f"create_fast_drop_promo error: {e}")
        return 0
    finally:
        conn.close()

def redeem_fast_drop_promo(code: str, tg_user_id: int) -> tuple:
    """Promokodni faollashtirish va mukofot berish"""
    conn = get_db()
    if not conn: return False, "Database xatoligi", 0
    try:
        clean_code = code.strip().upper()
        cur = conn.cursor()
        cur.execute("SELECT * FROM fast_drop_promos WHERE code = %s FOR UPDATE", (clean_code,))
        promo = cur.fetchone()
        if not promo:
            return False, "Promokod topilmadi yoki noto'g'ri!", 0
        
        p = dict(promo)
        import datetime
        if p.get("expires_at") and datetime.datetime.now() > p["expires_at"]:
            return False, "Ushbu promokodning amal qilish muddati tugagan!", 0
        if p.get("current_uses", 0) >= p.get("max_uses", 1):
            return False, "Kechirasiz! Ushbu promokodning limit soni allaqachon tugagan!", 0

        # Oldin ishlatganmi?
        cur.execute("SELECT id FROM promo_redemptions WHERE promo_id = %s AND tg_user_id = %s", (p["id"], tg_user_id))
        if cur.fetchone():
            return False, "Siz ushbu promokodni allaqachon faollashtirgansiz!", 0

        # Ro'yxatdan o'tkazish
        cur.execute("INSERT INTO promo_redemptions (promo_id, tg_user_id) VALUES (%s, %s)", (p["id"], tg_user_id))
        cur.execute("UPDATE fast_drop_promos SET current_uses = current_uses + 1 WHERE id = %s", (p["id"],))

        # Mukofotni berish
        reward_type = p.get("reward_type", "balance")
        reward_val = p.get("reward_value", 0)
        
        if reward_type == "balance":
            cur.execute("""
                INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (tg_user_id) DO UPDATE
                SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                    updated_at = NOW()
            """, (tg_user_id, reward_val))
            conn.commit()
            return True, f"Tabriklaymiz! Hisobingizga +{reward_val:,} so'm bonus berildi!", reward_val
        elif reward_type == "vip":
            conn.commit()
            activate_user_vip(tg_user_id, days=reward_val)
            return True, f"Tabriklaymiz! Sizga {reward_val} kunlik CreatorFlow VIP berildi!", reward_val
        else:
            conn.commit()
            return True, "Promokod muvaffaqiyatli ishlatildi!", reward_val
    except Exception as e:
        conn.rollback()
        print(f"redeem_fast_drop_promo error: {e}")
        return False, str(e), 0
    finally:
        conn.close()


# ==================== 4. EASTER EGG (YASHIRIN OLTIN TANGA) ====================

def claim_daily_easter_egg(tg_user_id: int, reward_uzs: int = 5000) -> tuple:
    """Foydalanuvchi menyular orasida topgan Yashirin Oltin Tangani yechib olishi"""
    conn = get_db()
    if not conn: return False, "Database xatoligi"
    try:
        import datetime
        today = datetime.date.today()
        cur = conn.cursor()
        cur.execute("SELECT id FROM easter_egg_claims WHERE tg_user_id = %s AND claim_date = %s", (tg_user_id, today))
        if cur.fetchone():
            return False, "Siz bugungi Yashirin Oltin Tangani allaqachon topgansiz! Ertaga yana qidiring."

        cur.execute("""
            INSERT INTO easter_egg_claims (tg_user_id, claim_date, reward_uzs)
            VALUES (%s, %s, %s)
        """, (tg_user_id, today, reward_uzs))
        
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (tg_user_id) DO UPDATE
            SET balance_uzs = user_balances.balance_uzs + %s,
                updated_at = NOW()
        """, (tg_user_id, reward_uzs, reward_uzs))
        conn.commit()
        return True, f"Qoyilmaqom! Yashirin Oltin Tangani topdingiz va hisobingizga +{reward_uzs:,} so'm qo'shildi!"
    except Exception as e:
        conn.rollback()
        print(f"claim_daily_easter_egg error: {e}")
        return False, str(e)
    finally:
        conn.close()


# ==================== 5. FLASH SALE (VAQTINCHALIK CHEGIRMALAR) ====================

def create_flash_sale(title: str, discount_percent: int = 20, duration_hours: int = 2) -> int:
    """Kanal va do'kon uchun cheklangan vaqtli chegirma yaratish"""
    conn = get_db()
    if not conn: return 0
    try:
        import datetime
        ends_at = datetime.datetime.now() + datetime.timedelta(hours=duration_hours)
        cur = conn.cursor()
        cur.execute("UPDATE flash_sales SET is_active = FALSE WHERE is_active = TRUE")
        cur.execute("""
            INSERT INTO flash_sales (title, discount_percent, is_active, ends_at)
            VALUES (%s, %s, TRUE, %s)
            RETURNING id
        """, (title, discount_percent, ends_at))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if isinstance(row, dict) else row[0]
    except Exception as e:
        conn.rollback()
        print(f"create_flash_sale error: {e}")
        return 0
    finally:
        conn.close()

def get_active_flash_sale() -> dict:
    """Aktiv Flash Sale mavjudligini tekshirish"""
    conn = get_db()
    if not conn: return None
    try:
        import datetime
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM flash_sales
            WHERE is_active = TRUE AND ends_at > NOW()
            ORDER BY id DESC LIMIT 1
        """)
        row = cur.fetchone()
        if not row: return None
        d = dict(row)
        now = datetime.datetime.now()
        rem_seconds = max(0, int((d["ends_at"] - now).total_seconds()))
        d["remaining_minutes"] = rem_seconds // 60
        return d
    except Exception as e:
        print(f"get_active_flash_sale error: {e}")
        return None
    finally:
        conn.close()


# ==================== CLAUDE CODE & CODEX TERMINAL SETUP ====================
def get_openrouter_key_for_setup() -> str:
    """Claude Code / Codex setup uchun bazadagi OpenRouter kalitini olish (o'chirmasdan / statusini o'zgartirmasdan)"""
    conn = get_db()
    if not conn:
        import os
        return os.getenv("OPENROUTER_API_KEY", "")
    try:
        cur = conn.cursor()
        # 1. Avval api_keys_stock jadvalidan mavjud yoki eng oxirgi openrouter kalitini olish
        cur.execute("""
            SELECT api_key FROM api_keys_stock 
            WHERE service_type = 'openrouter' 
            ORDER BY id DESC LIMIT 1
        """)
        row = cur.fetchone()
        if row and row.get("api_key"):
            return str(row["api_key"]).strip()
        
        # 2. Agar api_keys_stock da bo'lmasa, user_api_keys dan
        cur.execute("""
            SELECT api_key FROM user_api_keys 
            WHERE is_active = TRUE 
            ORDER BY id DESC LIMIT 1
        """)
        row2 = cur.fetchone()
        if row2 and row2.get("api_key"):
            return str(row2["api_key"]).strip()
            
        import os
        return os.getenv("OPENROUTER_API_KEY", "")
    except Exception as e:
        print(f"get_openrouter_key_for_setup error: {e}")
        import os
        return os.getenv("OPENROUTER_API_KEY", "")
    finally:
        conn.close()


def has_user_purchased_ai_coding_agent(tg_user_id: int) -> bool:
    """Foydalanuvchi Claude Code / Codex setup xizmatini oldin sotib olganligini tekshirish"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM user_purchases 
            WHERE tg_user_id = %s AND item_type = 'ai_coding_agent' 
            LIMIT 1
        """, (tg_user_id,))
        return cur.fetchone() is not None
    except Exception as e:
        print(f"has_user_purchased_ai_coding_agent error: {e}")
        return False
    finally:
        conn.close()


def record_ai_coding_agent_purchase(tg_user_id: int, price_uzs: int = 15000) -> dict:
    """Foydalanuvchi hisobidan 15,000 so'm yechib, setup xaridini qayd qilish"""
    return record_user_purchase(
        tg_user_id=tg_user_id,
        item_type="ai_coding_agent",
        item_name="Claude Code & Codex Terminal Setup",
        price_uzs=price_uzs,
        payload="model:nvidia/nemotron-3-ultra-550b-a55b:free"
    )









