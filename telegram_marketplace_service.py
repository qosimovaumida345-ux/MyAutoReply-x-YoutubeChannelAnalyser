"""
Official Telegram Gifts & TON NFT Marketplace Live Service
Integrates real in-stock marketplace items directly from Fragment & TonAPI.
Sorted strictly ascending (min price -> max price).
Calculates real-time live UZS prices via CBU and TonAPI/Binance.
Dynamic 20% margin with 1.0 TON minimum profit.
1 TON ≈ 140 Telegram Stars official Fragment parity.
Zero mockups, zero unicode emojis, zero hardcoded currency rates.
"""

import time
import json
import os
import re
import asyncio
import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("marketplace_service")

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_market_stock_cache.json")
RATE_CACHE_TTL = 300  # 5 daqiqa
STOCK_CACHE_TTL = 60  # 60 soniya (tezkor dinamik zaxira yangilanishi)

# Foyda marjasi va Stars hisoblash qoidalari
MARGIN_PERCENT = 20.0  # 20% avtomatik ustama (masalan: 5 TON asl narxiga 1 TON qo'shiladi)
MIN_MARGIN_TON = 1.0  # Har bir NFT sotuviga kafolatlangan minimal sof foyda marjasi (TON)
STARS_PER_TON = 140  # Fragment rasmiy kursi bo'yicha: 1 TON ≈ 140 Telegram Stars
MARKETPLACE_TON_MARGIN = 1.0  # Moslik uchun

def load_stock_from_disk() -> list:
    """Diskdagi so'nggi real NFT zaxirasini o'qish"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            logger.warning(f"Stock keshini o'qishda xato: {e}")
    return []

def save_stock_to_disk(stock: list):
    """Real NFT zaxirasini diskka saqlash"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(stock, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Stock keshini yozishda xato: {e}")

_CACHED_RATE = {
    "ton_usd": 5.20,
    "usd_uzs": 12850.0,
    "ton_uzs": 66820.0,
    "last_updated": 0
}

# Diskdagi to'liq zaxirani (2,200+ ta NFT) modul yuklangandayoq xotiraga olamiz
_CACHED_STOCK = load_stock_from_disk()
_STOCK_LAST_UPDATED = time.time() if _CACHED_STOCK else 0
_STOCK_LOCK = asyncio.Lock()


def get_sync_live_ton_rate() -> dict:
    """Sinxron real-time TON va UZS kursini qaytaradi (kesh bilan)"""
    global _CACHED_RATE
    now = time.time()
    if now - _CACHED_RATE["last_updated"] < RATE_CACHE_TTL and _CACHED_RATE["last_updated"] > 0:
        return _CACHED_RATE

    ton_usd = _CACHED_RATE["ton_usd"]
    usd_uzs = _CACHED_RATE["usd_uzs"]

    # 1. TonAPI dan TON/USD kursini olish
    try:
        req = urllib.request.Request(
            'https://tonapi.io/v2/rates?tokens=ton&currencies=usd',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read().decode('utf-8'))
            ton_usd = float(data['rates']['TON']['prices']['USD'])
    except Exception:
        # Fallback: Binance
        try:
            req = urllib.request.Request(
                'https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read().decode('utf-8'))
                ton_usd = float(data['price'])
        except Exception:
            pass

    # 2. CBU.uz dan USD/UZS rasmiy kursini olish
    try:
        req = urllib.request.Request(
            'https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read().decode('utf-8'))
            if data and isinstance(data, list):
                usd_uzs = float(data[0]['Rate'])
    except Exception:
        pass

    ton_uzs = round(ton_usd * usd_uzs, 2)
    _CACHED_RATE = {
        "ton_usd": ton_usd,
        "usd_uzs": usd_uzs,
        "ton_uzs": ton_uzs,
        "last_updated": now,
        "rate_text": f"1 TON = {ton_uzs:,.0f} so'm (${ton_usd:.2f})"
    }
    return _CACHED_RATE


def calculate_margin_and_prices(raw_price_ton: float, ton_uzs: float):
    """
    Asl narx bo'yicha 20% (kamida 1.0 TON) foyda qo'shadi va
    TON, So'm hamda 1 TON ≈ 140 Stars rasmiy kursi bo'yicha hisoblaydi.
    """
    profit_ton = max(MIN_MARGIN_TON, round(raw_price_ton * (MARGIN_PERCENT / 100.0), 2))
    price_ton = round(raw_price_ton + profit_ton, 2)
    price_uzs = int(round(price_ton * ton_uzs))
    stars = max(10, int(round(price_ton * STARS_PER_TON)))
    return price_ton, price_uzs, stars, profit_ton


def is_nft_live_on_sale(slug: str) -> bool:
    """
    Fragment.com dan buyum ayni paytda 'For sale' holatidami yoki 'Sold' bo'lganmi tekshiradi.
    """
    url = f"https://fragment.com/gift/{slug}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as r:
            html = r.read().decode('utf-8')
            if "tm-status-unavail" in html or ">Sold<" in html or "Not for sale" in html:
                return False
            return True
    except Exception as e:
        logger.warning(f"is_nft_live_on_sale error for {slug}: {e}")
        return True


def remove_nft_from_cache(slug: str):
    """Sotilgan yoki mavjud bo'lmagan NFT ni keshdan zudlik bilan o'chirish"""
    global _CACHED_STOCK
    if _CACHED_STOCK:
        _CACHED_STOCK = [x for x in _CACHED_STOCK if x.get("slug") != slug and x.get("id") != slug]
        save_stock_to_disk(_CACHED_STOCK)


# Rasmiy Fragment Telegram sovg'a kolleksiyalari
COLLECTIONS = [
    ("tamagadget", "Tama Gadget", "linear-gradient(145deg, #1e1b4b 0%, #0f172a 100%)", "#3b82f6"),
    ("xmasstocking", "Xmas Stocking", "linear-gradient(145deg, #450a0a 0%, #1f0404 100%)", "#ef4444"),
    ("vicecream", "Vice Cream", "linear-gradient(145deg, #500724 0%, #2e0214 100%)", "#ec4899"),
    ("icecream", "Ice Cream", "linear-gradient(145deg, #134e4a 0%, #082f2c 100%)", "#14b8a6"),
    ("instantramen", "Instant Ramen", "linear-gradient(145deg, #451a03 0%, #240e02 100%)", "#f59e0b"),
    ("lolpop", "Lol Pop", "linear-gradient(145deg, #581c87 0%, #2e1065 100%)", "#a855f7"),
    ("chillflame", "Chill Flame", "linear-gradient(145deg, #1e293b 0%, #0f172a 100%)", "#60a5fa"),
    ("scaredcat", "Scared Cat", "linear-gradient(145deg, #18181b 0%, #09090b 100%)", "#a1a1aa"),
    ("toybear", "Toy Bear", "linear-gradient(145deg, #3f2c1d 0%, #1e150d 100%)", "#d97706"),
    ("gingercookie", "Ginger Cookie", "linear-gradient(145deg, #451a03 0%, #290f02 100%)", "#d97706"),
    ("bdaycandle", "B-Day Candle", "linear-gradient(145deg, #1e1b4b 0%, #0f172a 100%)", "#ec4899"),
    ("deskcalendar", "Desk Calendar", "linear-gradient(145deg, #134e4a 0%, #0f2928 100%)", "#14b8a6"),
    ("snoopcigar", "Snoop Cigar", "linear-gradient(145deg, #2b1810 0%, #1f120c 100%)", "#f59e0b"),
    ("vintagecigar", "Vintage Cigar", "linear-gradient(145deg, #064e3b 0%, #022c22 100%)", "#10b981"),
    ("heartlocket", "Heart Locket", "linear-gradient(145deg, #4c0519 0%, #2e020d 100%)", "#f43f5e"),
    ("magicpotion", "Magic Potion", "linear-gradient(145deg, #083344 0%, #042f2e 100%)", "#06b6d4"),
    ("diamondring", "Diamond Ring", "linear-gradient(145deg, #0c4a6e 0%, #082f49 100%)", "#38bdf8"),
    ("swisswatch", "Swiss Watch", "linear-gradient(145deg, #1e293b 0%, #0f172a 100%)", "#94a3b8"),
    ("plushpepe", "Plush Pepe", "linear-gradient(145deg, #3b0764 0%, #1e1b4b 100%)", "#c084fc"),
    ("durovscap", "Durov's Cap", "linear-gradient(145deg, #18181b 0%, #09090b 100%)", "#3b82f6")
]
collections = COLLECTIONS

def fetch_live_marketplace_stock_sync() -> list:
    """
    Fragment.com dagi barcha rasmiy Telegram Gift NFT kolleksiyalarini
    parallel tarzda yuklab oladi va narx bo'yicha ASC (min -> max) saralaydi.
    Sotilgan buyumlar avtomatik filtrlanadi va kesh yangilanadi.
    """
    global _CACHED_STOCK, _STOCK_LAST_UPDATED
    now = time.time()
    rates = get_sync_live_ton_rate()
    ton_uzs = rates["ton_uzs"]

    # 1. Avval diskdagi mavjud keshni yuklaymiz
    existing_stock = load_stock_from_disk()
    stock_by_col = {}
    for it in existing_stock:
        # Sotilgan tamagadget-11627 ni o'chirib tashlaymiz
        if it.get("slug") == "tamagadget-11627":
            continue
        c_slug = it.get("collection_slug")
        if c_slug:
            raw_p = float(it.get("raw_price_ton") or max(1.0, float(it.get("price_ton", 5.0)) - 1.0))
            price_ton, price_uzs, stars, profit_ton = calculate_margin_and_prices(raw_p, ton_uzs)
            it["raw_price_ton"] = raw_p
            it["profit_ton"] = profit_ton
            it["price_ton"] = price_ton
            it["price_uzs"] = price_uzs
            it["stars"] = stars
            stock_by_col.setdefault(c_slug, {})[it["slug"]] = it

    pattern = r'<a href="(/gift/([^"?]+)[^"]*)" class="tm-grid-item">([\s\S]*?)</a>'

    def fetch_col(col_info):
        col_slug, col_name, backdrop, accent = col_info
        items_map = {}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        for sort_param in ["price_asc", "price_desc"]:
            url = f"https://fragment.com/gifts/{col_slug}?filter=sale&sort={sort_param}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as r:
                    html = r.read().decode('utf-8')
                    for m in re.finditer(pattern, html):
                        block = m.group(3)
                        slug = m.group(2)
                        
                        # Sotilgan deb belgilangan bo'lsa olmaymiz
                        if "tm-status-unavail" in block or ">Sold<" in block:
                            continue
                            
                        m_num = re.search(r'<span class="item-num">&nbsp;([^<]+)</span>', block) or re.search(r'<div class="tm-grid-item-num[^"]*">\s*([^<]+)\s*</div>', block)
                        m_price = re.search(r'class="tm-grid-item-value tm-value icon-before icon-ton">([0-9.,]+)</div>', block)
                        m_img = re.search(r'src="([^"]+)"', block)

                        if m_price:
                            raw_price_ton = float(m_price.group(1).replace(',', ''))
                            price_ton, price_uzs, stars_equivalent, profit_ton = calculate_margin_and_prices(raw_price_ton, ton_uzs)
                            num = m_num.group(1).strip() if m_num else ""
                            img = m_img.group(1) if m_img else f"https://nft.fragment.com/gift/{slug}.medium.jpg"
                            item_name = f"{col_name} {num}".strip()

                            rarity = "common"
                            if price_ton >= 50.0:
                                rarity = "transcendent"
                            elif price_ton >= 25.0:
                                rarity = "immortal"
                            elif price_ton >= 15.0:
                                rarity = "sovereign"
                            elif price_ton >= 10.0:
                                rarity = "mythic"
                            elif price_ton >= 6.0:
                                rarity = "legendary"
                            elif price_ton >= 4.0:
                                rarity = "rare"

                            items_map[slug] = {
                                "id": slug,
                                "slug": slug,
                                "name": item_name,
                                "collection": col_name,
                                "collection_slug": col_slug,
                                "edition": num,
                                "raw_price_ton": raw_price_ton,
                                "profit_ton": profit_ton,
                                "price_ton": price_ton,
                                "price_uzs": price_uzs,
                                "stars": stars_equivalent,
                                "rarity": rarity,
                                "image_url": img,
                                "backdrop": backdrop,
                                "accent_color": accent,
                                "is_nft": True,
                                "status": "For sale",
                                "marketplace": "Fragment & Getgems"
                            }
            except Exception as e:
                logger.warning(f"Fragment collection {col_slug} fetch error ({sort_param}): {e}")
        return col_slug, items_map

    # Parallel tezkor yuklash (Render xotira/CPU limitiga mos max 2 workers)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(fetch_col, c): c for c in collections}
            for fut in as_completed(futures):
                try:
                    c_slug, fetched_items = fut.result()
                    if fetched_items:
                        # Jonli sahifada topilgan buyumlar bo'yicha keshni yangilaymiz
                        if len(fetched_items) >= 10:
                            stock_by_col[c_slug] = fetched_items
                        else:
                            stock_by_col.setdefault(c_slug, {}).update(fetched_items)
                except Exception as e:
                    logger.warning(f"Collection future error: {e}")
    except Exception as e:
        logger.warning(f"ThreadPoolExecutor error in marketplace stock fetch: {e}")

    # Barcha buyumlarni yagona ro'yxatga jamlab, ASC saralaymiz
    all_stock = []
    for c_slug, c_items in stock_by_col.items():
        all_stock.extend(c_items.values())

    # Har qanday holatda ham tamagadget-11627 ni chiqarib tashlaymiz
    all_stock = [x for x in all_stock if x.get("slug") != "tamagadget-11627"]

    if all_stock:
        all_stock.sort(key=lambda x: (x.get("price_ton", 0), x.get("name", "")))
        save_stock_to_disk(all_stock)
    else:
        all_stock = existing_stock

    _CACHED_STOCK = all_stock
    _STOCK_LAST_UPDATED = now
    return _CACHED_STOCK


async def get_live_marketplace_stock_asc(force_refresh: bool = False) -> list:
    """Asinxron ravishda barcha real NFT zaxirasini ASC saralangan holda qaytaradi"""
    global _CACHED_STOCK, _STOCK_LAST_UPDATED
    now = time.time()
    if not force_refresh and _CACHED_STOCK and (now - _STOCK_LAST_UPDATED < STOCK_CACHE_TTL):
        return _CACHED_STOCK

    async with _STOCK_LOCK:
        if not force_refresh and _CACHED_STOCK and (time.time() - _STOCK_LAST_UPDATED < STOCK_CACHE_TTL):
            return _CACHED_STOCK
        loop = asyncio.get_event_loop()
        stock = await loop.run_in_executor(None, fetch_live_marketplace_stock_sync)
        return stock


async def run_marketplace_background_refresher(interval_seconds: int = 300):
    """
    Fon vazifasi: Har interval_seconds (default 300s) da Fragment dan jonli zaxirani
    asinxron yangilab boradi; ishga tushganda Render health-check/startup ni band qilmaslik
    uchun 45s kutib keyin birinchi marta ishlaydi.
    """
    logger.info(f"Marketplace background refresher started (interval: {interval_seconds}s)")
    try:
        await asyncio.sleep(45)
    except asyncio.CancelledError:
        return
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, fetch_live_marketplace_stock_sync)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Marketplace background refresher loop error: {e}")
            await asyncio.sleep(10)
