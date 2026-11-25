import os
import re
import time
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp

from config import (
    VENTEBOT_API_KEY,
    VENTEBOT_BASE_URL,
    USD_TO_UZS_RATE,
    RESELLER_MARKUP_PERCENT,
    DEFAULT_VENTEBOT_BASE_URL,
    get_ventebot_base_url,
    normalize_ventebot_base_url,
)
from database import (
    get_user_balance,
    deduct_user_balance,
    add_user_balance,
    save_ventebot_order,
    update_ventebot_order_status,
)
from currency_service import currency_service

logger = logging.getLogger("ventebot_service")

# ==================== TOKEN BUCKET RATE LIMITER ====================
class VenteBotRateLimiter:
    """
    VenteBot 60 req/min chekloviga qat'iy rioya qiluvchi token-bucket cheklovchi.
    Xavfsizlik uchun daqiqasiga maksimal 55 ta so'rov bilan cheklangan.
    """
    def __init__(self, max_tokens: int = 55, refill_period: float = 60.0):
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.refill_period = refill_period
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            if elapsed > 0:
                refill = (elapsed / self.refill_period) * self.max_tokens
                self.tokens = min(self.max_tokens, self.tokens + refill)
                self.last_refill = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (self.refill_period / self.max_tokens)
                logger.warning(f"VenteBot rate limit buffer faol. Kutilmoqda: {wait_time:.2f}s")
                await asyncio.sleep(max(0.1, wait_time))
                self.tokens = 1

            self.tokens -= 1


# ==================== IN-MEMORY TTL CACHE ====================
class TTLCache:
    """
    Xotiradagi yuqori tezlikdagi kesh (Katalog, hamyon va narxlar uchun).
    """
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry:
            val, expires_at = entry
            if time.time() < expires_at:
                return val
            # Eskirgan keshni o'chirish
            self._store.pop(key, None)
        return None

    def set(self, key: str, val: Any, ttl_seconds: int):
        self._store[key] = (val, time.time() + ttl_seconds)

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        active = sum(1 for v in self._store.values() if v[1] > now)
        return {"total_keys": len(self._store), "active_keys": active}

    def clear(self):
        self._store.clear()


# ==================== VENTEBOT CLIENT ====================
SUPPORTED_PRODUCT_LANGS = frozenset({"en", "fr", "ar", "zh", "vi", "ru", "tr", "pt"})
_MUSE_INVITE_RE = re.compile(r"^[A-Za-z0-9]{6}$")


class VenteBotClient:
    """
    VenteBot Reseller API v1.2.0 bilan xavfsiz va keshlangan integratsiya xizmati.
    """
    def __init__(self):
        self.base_url = get_ventebot_base_url()
        self.api_key = VENTEBOT_API_KEY
        self.cache = TTLCache()
        self.rate_limiter = VenteBotRateLimiter(max_tokens=55, refill_period=60.0)
        self._order_locks: Dict[int, asyncio.Lock] = {}
        self._etags: Dict[str, str] = {}
        self._last_good_catalog: Dict[str, Dict[str, Any]] = {}

    def _resolve_base_url(self) -> str:
        raw = str(getattr(self, "base_url", "") or "").strip()
        if raw and raw != VENTEBOT_BASE_URL:
            return normalize_ventebot_base_url(raw, default=DEFAULT_VENTEBOT_BASE_URL)
        return get_ventebot_base_url()

    @staticmethod
    async def _safe_json(resp) -> Dict[str, Any]:
        try:
            data = await resp.json(content_type=None)
            return data if isinstance(data, dict) else {"data": data}
        except Exception:
            try:
                txt = (await resp.text())[:300]
            except Exception:
                txt = ""
            return {"message": txt or f"HTTP {getattr(resp, 'status', 0)}"}

    @staticmethod
    def _friendly_error_message(status: int, code: str, raw_msg: str) -> str:
        low = str(raw_msg or "").lower()
        if status == 404 or "application not found" in low:
            return "Do'kon API manzili vaqtincha topilmadi. Iltimos, birozdan so'ng qayta urinib ko'ring."
        if status in (401, 403):
            return "Do'kon API kaliti yoki ruxsatida muammo bor. Administrator bilan bog'laning."
        if status == 429:
            return "So'rovlar limiti oshib ketdi. Bir necha soniyadan so'ng qayta urinib ko'ring."
        if status in (502, 503, 504):
            return "Do'kon serverida texnik profilaktika ketmoqda. Birozdan so'ng qayta urinib ko'ring."
        return str(raw_msg or f"Server xatosi (HTTP {status})")

    def _get_user_lock(self, tg_user_id: int) -> asyncio.Lock:
        if tg_user_id not in self._order_locks:
            self._order_locks[tg_user_id] = asyncio.Lock()
        return self._order_locks[tg_user_id]

    def _get_headers(self) -> Dict[str, str]:
        key = self.api_key or os.getenv("VENTEBOT_API_KEY", "")
        return {
            "X-Reseller-Key": key,
            "X-API-Key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def calculate_dynamic_markup_percent(price_usd: float, category: str = "", stock: Optional[int] = None) -> float:
        """
        Dinamik Smart Marja (50% dan 100% gacha):
        Foydalanuvchi talabi:
        - Asl narxi $1 bo'lgan narsa $1.50 dan ko'proq, maksimum $2.00 bo'lsin (50% - 100% oralig'ida).
        - Statik 150% olib tashlandi, narx darajasi va talabga ko'ra avtomatik belgilanadi.
        """
        if not price_usd or price_usd <= 0:
            return 50.0

        # Narx darajasiga (Bracket) ko'ra asosiy marja:
        if price_usd <= 1.0:
            # $0.01 - $1.00: 70% marja ($1.00 -> $1.70, $0.50 -> $0.85)
            base_markup = 70.0
        elif price_usd <= 3.0:
            # $1.01 - $3.00: 60% marja ($2.00 -> $3.20)
            base_markup = 60.0
        elif price_usd <= 10.0:
            # $3.01 - $10.00: 55% marja ($5.00 -> $7.75)
            base_markup = 55.0
        else:
            # $10.00+: 50% marja ($20.00 -> $30.00)
            base_markup = 50.0

        # Talab (Scarcity indicator): Agar zaxira kam bo'lsa (<= 5 ta) +5% qo'shiladi
        if stock is not None and 0 < stock <= 5:
            base_markup += 5.0

        # Qat'iy chegara: 50.0% dan kam emas, 100.0% dan ko'p emas!
        return max(50.0, min(100.0, base_markup))

    @staticmethod
    def calculate_retail_usd(price_usd: float, category: str = "", stock: Optional[int] = None) -> float:
        """
        Dynamic Retail USD narxini hisoblash (50% - 100% marja).
        $1 lik tovar qat'iy $1.50 - $2.00 oralig'ida bo'ladi!
        """
        if not price_usd or price_usd <= 0:
            return 0.0
        markup = VenteBotClient.calculate_dynamic_markup_percent(price_usd, category, stock)
        retail = price_usd * (1.0 + (markup / 100.0))
        return round(retail, 2)

    def convert_usd_to_uzs(self, price_usd: float, current_rate: Optional[float] = None, category: str = "", stock: Optional[int] = None) -> int:
        """
        Dynamic Smart Pricing Formula (Asl narxidan 50% - 100% marja bilan UZS narxi):
        - Asl narx: price_usd
        - Sotuv USD narxi: calculate_retail_usd(price_usd, category, stock)
        - Real-time USD kursi: currency_service (O'zbekiston Markaziy Banki CBU.uz API)
        - UZS ga o'tkazish: retail_usd * rate
        - Yaxlitlash: 1,000 so'mgacha yaxlitlanadi
        - Minimal narx: 10,000 so'm
        """
        if not price_usd or price_usd <= 0:
            return 0
        retail_usd = self.calculate_retail_usd(price_usd, category, stock)
        rate = float(current_rate or currency_service.get_cached_usd_rate() or USD_TO_UZS_RATE or 12850.0)
        uzs = int(round(retail_usd * rate, -3))
        return max(1000, uzs)


    @staticmethod
    def is_in_stock(p: Dict[str, Any]) -> bool:
        """Tovar zaxirada mavjudligini aniqlash (None: cheksiz/aktivatsiya, >0: zaxira bor)."""
        stock = p.get("stock")
        if stock is None:
            return True
        try:
            return int(stock) > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def categorize_product(p: Dict[str, Any]) -> str:
        """92+ ta tovarning har birini 6 ta qulay toifaga ajratadi (nomi bo'yicha birinchi navbatda)"""
        raw_name = (p.get("name") or "")
        desc = (p.get("description") or "").lower()

        small_caps = str.maketrans('ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ', 'abcdefghijklmnopqrstuvwxyz')
        name = raw_name.lower().translate(small_caps)

        if "test product" in name:
            return "test"

        rules = [
            ("media_streaming", [
                "youtube", "spotify", "netflix", "prime video", "apple tv", "apple music",
                "hbo max", "hbomax", "peacock", "wink", "crunchyroll"
            ]),
            ("ai", [
                "chatgpt", "chat gpt", "openai", "gpt", "claude", "gemini", "google ai",
                "grok", "xai", "cursor", "manus", "factory", "lovable", "replit", "kiro",
                "codex", "openrouter", "groq", "flux", "midjourney", "fin ia", "fin ai", "fin",
                "muse ai", "bolt.new", "bolt", "arize"
            ]),
            ("design_video", [
                "capcut", "supercut", "descript", "eleven reader", "elevenlabs", "eleven labs", "eleven", "brain.fm",
                "wispr", "gamma", "figma", "framer", "canva", "adobe", "magic patterns",
                "mobbin", "miro", "autodesk", "speechify", "runway", "higgsfield", "pangram"
            ]),
            ("dev_tools", [
                "supabase", "resend", "railway", "warp", "n8n", "linear", "jetbrains",
                "posthog", "jam team", "gumloop", "customer.io"
            ]),
            ("vpn_security", [
                "nordvpn", "nord vpn", "nord", "proton vpn", "protonvpn", "proton", "hma", "proxy", "vpn",
                "surfshark", "expressvpn", "express vpn", "snapchat"
            ]),
            ("office_edu", [
                "duolingo", "coursera", "cousera", "notion", "readwise", "granola", "microsoft",
                "office 365", "office", "windows", "gmail", "google drive", "trading view",
                "tradingview", "scribd", "airtable", "waking up", "mercury", "stripe atlas", "stripe",
                "wordwall", "quizlet", "ilovepdf", "quillbot", "zoom"
            ])
        ]

        for cat, keywords in rules:
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, name) or (len(kw) > 4 and kw in name):
                    return cat

        # Tavsif bo'yicha fallback (agar nomida topilmasa)
        combined = name + " " + desc
        for cat, keywords in rules:
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, combined):
                    return cat

        return "ai"

    # -------------------------------------------------------------
    # 1. ACCOUNT & WALLET (/api/reseller/me)
    # -------------------------------------------------------------
    async def get_me(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Reseller hisobi va hamyon balansini tekshirish.
        Kesh muddati: 60 soniya.
        """
        cache_key = "vb_me"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        key = self.api_key or os.getenv("VENTEBOT_API_KEY", "")
        if not key:
            return {
                "success": False,
                "code": "KEY_NOT_CONFIGURED",
                "message": "VENTEBOT_API_KEY sozlanmagan",
                "wallet_balance": 0.0,
            }

        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/me"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await self._safe_json(resp)
                    if resp.status == 200 and data.get("success"):
                        self.cache.set(cache_key, data, ttl_seconds=60)
                        return data
                    err_code = data.get("code", f"HTTP_{resp.status}")
                    raw_msg = data.get("message") or data.get("detail") or "Do'kon hisob ma'lumotlarini olib bo'lmadi"
                    return {
                        "success": False,
                        "code": err_code,
                        "message": self._friendly_error_message(resp.status, err_code, raw_msg),
                        "wallet_balance": 0.0,
                    }
        except Exception as e:
            logger.error(f"get_me xatolik: {e}")
            return {
                "success": False,
                "code": "NETWORK_ERROR",
                "message": f"Serverga ulanishda xatolik: {str(e)}",
                "wallet_balance": 0.0,
            }

    # -------------------------------------------------------------
    # 2. PRODUCTS CATALOG (/api/reseller/products)
    # -------------------------------------------------------------
    async def get_products(self, lang: str = "uz", force_refresh: bool = False, in_stock_only: bool = False) -> Dict[str, Any]:
        """
        Faol tovarlar katalogini olish.
        Kesh muddati: Dinamik (Admin panel orqali sozlanadi, odatiy: 60s).
        Barcha mahsulotlar toifaga ajratiladi va so'mdagi marjali narxi hisoblanadi.
        Mavjud (in-stock) tovarlar avtomatik birinchi navbatda saralanadi.
        """
        cache_key = f"vb_products_{lang}"
        from telemetry_service import get_dynamic_config, record_outgoing_call
        dyn_ttl = int(get_dynamic_config("product_cache_ttl", 60))

        if not force_refresh and dyn_ttl > 0:
            cached = self.cache.get(cache_key)
            if cached:
                record_outgoing_call("VenteBot", f"/api/reseller/products?lang={lang}", 0.4, status="ok", cached=True)
                products = cached.get("products", [])
                if in_stock_only:
                    products = [p for p in products if self.is_in_stock(p)]
                return {**cached, "products": products}

        upstream_lang = lang if lang in SUPPORTED_PRODUCT_LANGS else "en"
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/products?lang={upstream_lang}"
        req_headers = self._get_headers()
        if not force_refresh and cache_key in self._etags and cache_key in self._last_good_catalog:
            req_headers["If-None-Match"] = self._etags[cache_key]

        t0 = time.perf_counter()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=req_headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    record_outgoing_call("VenteBot", f"/api/reseller/products?lang={upstream_lang}", dur_ms, status="ok" if resp.status in (200, 304) else f"HTTP {resp.status}", cached=False)
                    if resp.status == 304 and cache_key in self._last_good_catalog:
                        prev = self._last_good_catalog[cache_key]
                        if dyn_ttl > 0:
                            self.cache.set(cache_key, prev, ttl_seconds=dyn_ttl)
                        products = prev.get("products", [])
                        if in_stock_only:
                            products = [p for p in products if self.is_in_stock(p)]
                        return {**prev, "products": products}

                    if resp.status == 200:
                        raw_data = await self._safe_json(resp)
                        etag = resp.headers.get("ETag")
                        if etag:
                            self._etags[cache_key] = etag
                        raw_products = raw_data if isinstance(raw_data, list) else raw_data.get("products", raw_data.get("items", []))
                        raw_services = raw_data.get("services", []) if isinstance(raw_data, dict) else []
                        live_rate = await currency_service.get_usd_to_uzs_rate()
                        processed_products = []
                        for p in raw_products:
                            if bool(p.get("api_test")) or str(p.get("delivery_type") or "").lower() == "api_test":
                                continue
                            cat = self.categorize_product(p)
                            if cat == "test":
                                continue  # Vendor test tovarini mijozlarga ko'rsatmaslik
                            p_copy = dict(p)
                            cost_usd = float(p.get("price_usd") or p.get("price") or 0)
                            stock_val = p.get("stock")
                            retail_usd = self.calculate_retail_usd(cost_usd, category=cat, stock=stock_val)
                            p_copy["category"] = cat
                            p_copy["cost_price_usd"] = cost_usd
                            p_copy["retail_price_usd"] = retail_usd
                            p_copy["price_uzs"] = self.convert_usd_to_uzs(cost_usd, current_rate=live_rate, category=cat, stock=stock_val)
                            processed_products.append(p_copy)

                        # Mavjud (in-stock) tovarlarni oldinga, zaxirasi tugaganlarni oxiriga saralash
                        processed_products.sort(key=lambda p: 0 if self.is_in_stock(p) else 1)

                        res = {"success": True, "products": processed_products, "services": raw_services}
                        self._last_good_catalog[cache_key] = res
                        if dyn_ttl > 0:
                            self.cache.set(cache_key, res, ttl_seconds=dyn_ttl)

                        if in_stock_only:
                            return {
                                "success": True,
                                "products": [p for p in processed_products if self.is_in_stock(p)],
                                "services": raw_services,
                            }
                        return res
                    else:
                        err_data = await self._safe_json(resp)
                        err_code = err_data.get("code", f"HTTP_{resp.status}")
                        raw_msg = err_data.get("message") or err_data.get("detail") or "Mahsulotlar katalogini olib bo'lmadi"
                        logger.warning(f"VenteBot get_products HTTP {resp.status} ({err_code}): {raw_msg}")
                        if not force_refresh and cache_key in self._last_good_catalog:
                            stale = self._last_good_catalog[cache_key]
                            products = stale.get("products", [])
                            if in_stock_only:
                                products = [p for p in products if self.is_in_stock(p)]
                            return {**stale, "products": products, "stale": True}
                        return {
                            "success": False,
                            "code": err_code,
                            "message": self._friendly_error_message(resp.status, err_code, raw_msg),
                            "products": [],
                        }
        except Exception as e:
            logger.error(f"get_products xatolik: {e}")
            if not force_refresh and cache_key in self._last_good_catalog:
                stale = self._last_good_catalog[cache_key]
                products = stale.get("products", [])
                if in_stock_only:
                    products = [p for p in products if self.is_in_stock(p)]
                return {**stale, "products": products, "stale": True}
            return {
                "success": False,
                "code": "NETWORK_ERROR",
                "message": "Do'kon serveriga ulanishda vaqtinchalik xatolik yuz berdi.",
                "products": [],
            }

    # -------------------------------------------------------------
    # 3. QUOTE (/api/reseller/quote)
    # -------------------------------------------------------------
    async def get_quote(self, product_id: int, quantity: int = 1) -> Dict[str, Any]:
        """
        Xariddan oldin mahsulot narxini aniq hisoblab berish.
        Kesh: 5 daqiqa.
        """
        cache_key = f"vb_quote_{product_id}_{quantity}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/quote"
        payload = {"product_id": int(product_id), "quantity": int(quantity)}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await self._safe_json(resp)
                    if resp.status == 200 and data.get("success"):
                        live_rate = await currency_service.get_usd_to_uzs_rate()
                        quote = data.get("quote", {})
                        unit_usd = float(quote.get("unit_price") or 0)
                        total_usd = float(quote.get("total") or 0)
                        quote["cost_unit_usd"] = unit_usd
                        quote["cost_total_usd"] = total_usd
                        quote["retail_unit_usd"] = self.calculate_retail_usd(unit_usd)
                        quote["retail_total_usd"] = self.calculate_retail_usd(total_usd)
                        quote["unit_price_uzs"] = self.convert_usd_to_uzs(unit_usd, current_rate=live_rate)
                        quote["total_uzs"] = self.convert_usd_to_uzs(total_usd, current_rate=live_rate)
                        data["quote"] = quote
                        self.cache.set(cache_key, data, ttl_seconds=30)
                        return data
                    return data
        except Exception as e:
            logger.error(f"get_quote xatolik: {e}")
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------
    # 4. ATOMIC PURCHASE PIPELINE (So'm yechish, VenteBot buyurtma, Rollback)
    # -------------------------------------------------------------
    async def buy_product_with_uzs(
        self,
        tg_user_id: int,
        product_id: int,
        quantity: int = 1,
        activation_identifier: str = "",
    ) -> Dict[str, Any]:
        """
        Markaziy xarid jarayoni:
        1. User-level async qulf (double-spending ning oldini oladi).
        2. Tovarni topish va UZS narxini hisoblash.
        3. Foydalanuvchi so'm balansini tekshirish.
        4. Pre-flight: Admin VenteBot hamyonida USD yetarliligini tekshirish.
        5. PostgreSQL `SELECT ... FOR UPDATE` orqali so'mni yechish.
        6. VenteBot API ga idempotent buyurtma yuborish.
        7. Agar VenteBot buyurtmani bajarsa — tovar ma'lumotlarini saqlash va berish.
        8. Agar VenteBot rad etsa yoki xatolik bersa — PULNI 100% AVTOMATIK QAYTARISH (Refund).
        """
        if int(quantity or 0) <= 0:
            return {"success": False, "message": "Xarid miqdori kamida 1 ta bo'lishi kerak"}

        user_lock = self._get_user_lock(tg_user_id)
        async with user_lock:
            # 1. Tovarni katalogdan izlash
            catalog = await self.get_products()
            if not catalog.get("success"):
                return {"success": False, "message": "Katalog ma'lumotlarini yuklab bo'lmadi"}

            product = next((p for p in catalog.get("products", []) if p.get("id") == int(product_id)), None)
            if not product:
                return {"success": False, "message": f"Bunday mahsulot topilmadi (ID: {product_id})"}

            product_name = product.get("name", "Digital Item")
            price_usd = float(product.get("price_usd") or 0)
            delivery_type = product.get("delivery_type", "stock")
            stock = product.get("stock")

            if stock is not None and stock < quantity:
                return {"success": False, "message": f"Kechirasiz, mahsulot zaxirada yetarli emas (Mavjud: {stock} ta)"}

            # Aktivatsiya tovarlari uchun identifikator tekshiruvi
            clean_ident = (activation_identifier or "").strip()
            if delivery_type == "activation" and not clean_ident:
                return {
                    "success": False,
                    "code": "IDENTIFIER_REQUIRED",
                    "message": "Ushbu xizmat uchun faollashtirish ma'lumoti (Telegram username, ID yoki email) kiritilishi shart",
                }

            live_rate = await currency_service.get_usd_to_uzs_rate()
            total_usd = round(price_usd * quantity, 2)
            total_uzs = self.convert_usd_to_uzs(price_usd, current_rate=live_rate) * quantity

            # 2. Foydalanuvchi balansini tekshirish
            user_bal = get_user_balance(tg_user_id)
            if user_bal < total_uzs:
                return {
                    "success": False,
                    "code": "INSUFFICIENT_BALANCE",
                    "message": f"Balansingizda mablag' yetarli emas! Kerak: {total_uzs:,} so'm, sizda: {user_bal:,} so'm.",
                    "required_uzs": total_uzs,
                    "current_uzs": user_bal,
                }

            # 3. Pre-flight: Admin VenteBot Reseller hamyonini tekshirish
            me = await self.get_me()
            admin_wallet_bal = float(me.get("wallet_balance", 0.0))
            if admin_wallet_bal < total_usd:
                logger.critical(
                    f"DIQQAT! Admin VenteBot wallet balansi tovar uchun yetarli emas! "
                    f"Kerak: ${total_usd}, Mavjud: ${admin_wallet_bal}"
                )
                return {
                    "success": False,
                    "code": "STORE_MAINTENANCE",
                    "message": "Texnik profilaktika tufayli tovar vaqtincha sotuvda emas. Iltimos, birozdan so'ng urinib ko'ring.",
                }

            # 4. Foydalanuvchi balansidan so'mni yechish (Atomic DB Lock)
            deducted = deduct_user_balance(tg_user_id, total_uzs)
            if not deducted:
                return {
                    "success": False,
                    "code": "DEDUCTION_FAILED",
                    "message": "Balansdan mablag' yechishda xatolik yuz berdi. Tranzaksiya bekor qilindi.",
                }

            # 5. Idempotent kalit yaratish va VenteBot ga buyurtma berish
            idempotency_key = f"vb_{tg_user_id}_{product_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            await self.rate_limiter.acquire()
            url = f"{self._resolve_base_url()}/api/reseller/orders"
            payload: Dict[str, Any] = {
                "product_id": int(product_id),
                "quantity": int(quantity),
                "customer_reference": f"tg_user_{tg_user_id}",
                "idempotency_key": idempotency_key,
            }
            if clean_ident:
                payload["activation_identifier"] = clean_ident[:500]

            order_success = False
            needs_lookup = False
            uncertain_pending = False
            ventebot_order_data: Dict[str, Any] = {}
            error_reason = ""

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=30, connect=10),
                    ) as resp:
                        resp_data = await self._safe_json(resp)
                        order_obj = resp_data.get("order") if isinstance(resp_data.get("order"), dict) else {}
                        if not order_obj and isinstance(resp_data, dict):
                            order_obj = resp_data

                        if resp.status in (200, 201) and (resp_data.get("success") is True or order_obj.get("id")):
                            merged = {**resp_data, **order_obj}
                            if str(merged.get("status", "")).upper() == "CANCELLED":
                                error_reason = "Buyurtma yetkazib beruvchi tomonidan bekor qilindi (CANCELLED)"
                            else:
                                order_success = True
                                ventebot_order_data = merged
                        else:
                            if resp.status in (409, 502, 503, 504):
                                needs_lookup = True
                            error_reason = (
                                resp_data.get("message")
                                or resp_data.get("detail")
                                or resp_data.get("error")
                                or (order_obj.get("message") if isinstance(order_obj, dict) else None)
                                or f"VenteBot xatosi: HTTP {resp.status}"
                            )
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.error(f"VenteBot order HTTP so'rov xatosi: {e}")
                needs_lookup = True
                error_reason = f"Tarmoq uzilishi: {str(e)}"
            except Exception as e:
                logger.error(f"VenteBot order HTTP so'rov xatosi: {e}")
                error_reason = f"Tarmoq uzilishi: {str(e)}"

            # 5b. Timeout / 503 / 409 bo'lganda idempotency_key orqali tiklash (/orders/lookup)
            if not order_success and needs_lookup:
                lookup = await self.lookup_order(idempotency_key)
                results = lookup.get("results") or []
                if results and isinstance(results[0], dict):
                    req_status = str(results[0].get("request_status") or "").lower()
                    found_order = results[0].get("order") if isinstance(results[0].get("order"), dict) else {}
                    if req_status == "completed" and found_order:
                        if str(found_order.get("status", "")).upper() == "CANCELLED":
                            error_reason = "Buyurtma bekor qilindi (CANCELLED)"
                        else:
                            order_success = True
                            ventebot_order_data = found_order
                    elif req_status in ("in_progress", "uncertain"):
                        uncertain_pending = True
                        ventebot_order_data = found_order or {"status": "PAID_PENDING_DELIVERY"}

            # 5c. PAID_PENDING_DELIVERY bo'lsa tezkor 2 marta tekshirish
            if order_success and not ventebot_order_data.get("items"):
                cur_status = str(ventebot_order_data.get("status", "")).upper()
                vb_id = ventebot_order_data.get("id")
                if cur_status == "PAID_PENDING_DELIVERY" and vb_id:
                    for delay in (2.0, 4.0):
                        await asyncio.sleep(delay)
                        polled = await self.get_order_details(int(vb_id))
                        p_status = str(polled.get("status", "")).upper()
                        if p_status == "CANCELLED":
                            order_success = False
                            error_reason = "Buyurtma yetkazib berishda bekor qilindi (CANCELLED)"
                            break
                        if p_status == "COMPLETED" or polled.get("items"):
                            ventebot_order_data = {**ventebot_order_data, **polled}
                            break

            # 6. Muvaffaqiyatsiz bo'lsa — AVTOMATIK REFUND
            if not order_success and not uncertain_pending:
                logger.warning(
                    f"VenteBot buyurtma xatosi! Foydalanuvchi {tg_user_id} ga {total_uzs} so'm qaytarilmoqda. Sabab: {error_reason}"
                )
                add_user_balance(tg_user_id, total_uzs)
                save_ventebot_order(
                    tg_user_id=tg_user_id,
                    product_id=product_id,
                    product_name=product_name,
                    quantity=quantity,
                    amount_uzs=total_uzs,
                    amount_usd=total_usd,
                    delivery_type=delivery_type,
                    activation_identifier=clean_ident,
                    status="REFUNDED",
                    ventebot_order_id=None,
                    delivered_data=error_reason,
                    idempotency_key=idempotency_key,
                )
                return {
                    "success": False,
                    "code": "ORDER_FAILED_REFUNDED",
                    "message": f"Buyurtma berishda xatolik yuz berdi: {error_reason}. Mablag'ingiz ({total_uzs:,} so'm) to'liq balansingizga qaytarildi!",
                }

            # 7. Muvaffaqiyatli xarid — Keshni tozalash va Bazaga saqlash
            self.cache.delete("vb_me")  # Balans o'zgardi
            self.cache.delete(f"vb_products_uz")
            new_user_bal = get_user_balance(tg_user_id)

            status_val = str(ventebot_order_data.get("status", "COMPLETED") or "COMPLETED").upper()
            delivered_items = ventebot_order_data.get("items", []) if status_val == "COMPLETED" else []
            delivered_text = ""
            if delivered_items:
                delivered_text = "\n".join([str(item.get("account_data", "")).strip() for item in delivered_items if item.get("account_data")])
            if not delivered_text and status_val == "COMPLETED" and ventebot_order_data.get("account_data"):
                delivered_text = str(ventebot_order_data.get("account_data")).strip()
            if not delivered_text:
                if status_val in ("AWAITING_ACTIVATION", "AWAITING_ACTIVATION_INFO"):
                    delivered_text = "Faollashtirish jarayonda (AWAITING_ACTIVATION). Tez orada taqdim etiladi."
                elif status_val == "PAID_PENDING_DELIVERY":
                    delivered_text = "Yetkazib berilishi kutilmoqda (PAID_PENDING_DELIVERY)."

            db_order_id = save_ventebot_order(
                tg_user_id=tg_user_id,
                product_id=product_id,
                product_name=product_name,
                quantity=quantity,
                amount_uzs=total_uzs,
                amount_usd=total_usd,
                delivery_type=delivery_type,
                activation_identifier=clean_ident,
                status=ventebot_order_data.get("status", "COMPLETED"),
                ventebot_order_id=ventebot_order_data.get("id"),
                delivered_data=delivered_text or str(ventebot_order_data),
                idempotency_key=idempotency_key,
            )

            return {
                "success": True,
                "order_id": db_order_id,
                "ventebot_order_id": ventebot_order_data.get("id"),
                "product_name": product_name,
                "quantity": quantity,
                "amount_uzs": total_uzs,
                "amount_usd": total_usd,
                "new_balance_uzs": new_user_bal,
                "delivery_type": delivery_type,
                "status": ventebot_order_data.get("status"),
                "delivered_data": delivered_text,
                "items": delivered_items,
            }

    # -------------------------------------------------------------
    # 5. ORDER DETAILS & RECOVERY (/api/reseller/orders/{id}, /lookup)
    # -------------------------------------------------------------
    async def get_order_details(self, ventebot_order_id: int) -> Dict[str, Any]:
        """Buyurtma holatini VenteBot'dan qayta tekshirish"""
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/orders/{ventebot_order_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await self._safe_json(resp)
                    if isinstance(data, dict):
                        order_obj = data.get("order") if isinstance(data.get("order"), dict) else {}
                        return {**data, **order_obj}
                    return data
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def lookup_order(self, idempotency_key: str) -> Dict[str, Any]:
        """Timeout yoki 503 dan keyin idempotency_key bo'yicha buyurtmani tiklash."""
        clean_key = str(idempotency_key or "").strip()
        if not clean_key:
            return {"success": False, "found": False, "results": []}
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/orders/lookup"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"idempotency_key": clean_key},
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await self._safe_json(resp)
                    if resp.status == 200 and isinstance(data, dict):
                        return data
                    return {"success": False, "found": False, "results": [], "status_code": resp.status}
        except Exception as e:
            logger.error(f"lookup_order xatolik: {e}")
            return {"success": False, "found": False, "results": [], "message": str(e)}

    async def submit_activation_identifier(self, ventebot_order_id: int, activation_identifier: str) -> Dict[str, Any]:
        """AWAITING_ACTIVATION_INFO buyurtmasi uchun aktivatsiya ma'lumotini yuborish."""
        clean_ident = str(activation_identifier or "").strip()
        if len(clean_ident) < 2:
            return {"success": False, "message": "Aktivatsiya ma'lumoti kamida 2 ta belgidan iborat bo'lishi kerak"}
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/orders/{int(ventebot_order_id)}/activation-identifier"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"activation_identifier": clean_ident[:500]},
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as resp:
                    data = await self._safe_json(resp)
                    if resp.status == 200 and data.get("success"):
                        return data
                    return {
                        "success": False,
                        "message": self._friendly_error_message(resp.status, str(data.get("code") or ""), str(data.get("message") or data.get("detail") or "")),
                    }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------
    # 6. MUSE AI TOKEN BUFF (/api/reseller/muse-buff)
    # -------------------------------------------------------------
    async def get_muse_catalog(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Muse AI token to'ldirish xizmati mavjudligi va narxini olish."""
        cache_key = "vb_muse_catalog"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/muse-buff"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await self._safe_json(resp)
                    if resp.status == 200 and data.get("success"):
                        svc = dict(data.get("service") or {})
                        live_rate = await currency_service.get_usd_to_uzs_rate()
                        cost_per_b = float(svc.get("price_per_billion") or 0.20)
                        svc["cost_per_billion_usd"] = cost_per_b
                        svc["retail_per_billion_usd"] = self.calculate_retail_usd(cost_per_b, category="ai")
                        svc["price_per_billion_uzs"] = self.convert_usd_to_uzs(cost_per_b, current_rate=live_rate, category="ai")
                        res = {**data, "service": svc}
                        self.cache.set(cache_key, res, ttl_seconds=60)
                        return res
                    return {
                        "success": False,
                        "available": False,
                        "message": self._friendly_error_message(resp.status, str(data.get("code") or ""), str(data.get("message") or "")),
                    }
        except Exception as e:
            logger.error(f"get_muse_catalog xatolik: {e}")
            return {"success": False, "available": False, "message": "Muse AI xizmatini yuklashda xatolik"}

    async def get_muse_quote(self, invite_code: str, quantity: int) -> Dict[str, Any]:
        """Muse AI token buyurtmasi narxini hisoblash (1-30B)."""
        code_clean = str(invite_code or "").strip().upper()
        if not _MUSE_INVITE_RE.match(code_clean):
            return {"success": False, "message": "Invite kod 6 ta harf/raqamdan iborat bo'lishi kerak (masalan: ABBADJ)"}
        qty = int(quantity or 0)
        if qty < 1 or qty > 30:
            return {"success": False, "message": "Token miqdori 1 dan 30 milliardgacha (1-30) bo'lishi kerak"}
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/muse-buff/quote"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"invite_code": code_clean, "quantity": qty},
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await self._safe_json(resp)
                    if resp.status == 200 and data.get("success"):
                        quote = dict(data.get("quote") or {})
                        live_rate = await currency_service.get_usd_to_uzs_rate()
                        total_usd = float(quote.get("total_usd") or 0)
                        quote["retail_total_usd"] = self.calculate_retail_usd(total_usd, category="ai")
                        quote["total_uzs"] = self.convert_usd_to_uzs(total_usd, current_rate=live_rate, category="ai")
                        return {**data, "quote": quote}
                    return {
                        "success": False,
                        "message": self._friendly_error_message(resp.status, str(data.get("code") or ""), str(data.get("message") or data.get("detail") or "")),
                    }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def buy_muse_buff_with_uzs(self, tg_user_id: int, invite_code: str, quantity: int) -> Dict[str, Any]:
        """Muse AI tokenlarini UZS balansdan atomik sotib olish."""
        code_clean = str(invite_code or "").strip().upper()
        if not _MUSE_INVITE_RE.match(code_clean):
            return {"success": False, "message": "Invite kod 6 ta harf/raqamdan iborat bo'lishi kerak (masalan: ABBADJ)"}
        qty = int(quantity or 0)
        if qty < 1 or qty > 30:
            return {"success": False, "message": "Token miqdori 1 dan 30 milliardgacha (1-30) bo'lishi kerak"}

        user_lock = self._get_user_lock(tg_user_id)
        async with user_lock:
            cat = await self.get_muse_catalog()
            if not cat.get("success") or not cat.get("available"):
                return {"success": False, "message": cat.get("message") or "Muse AI xizmati hozircha mavjud emas"}
            svc = cat.get("service") or {}
            cost_per_b = float(svc.get("cost_per_billion_usd") or svc.get("price_per_billion") or 0.20)
            total_usd = round(cost_per_b * qty, 2)
            live_rate = await currency_service.get_usd_to_uzs_rate()
            total_uzs = self.convert_usd_to_uzs(cost_per_b, current_rate=live_rate, category="ai") * qty

            user_bal = get_user_balance(tg_user_id)
            if user_bal < total_uzs:
                return {
                    "success": False,
                    "code": "INSUFFICIENT_BALANCE",
                    "message": f"Balansingizda mablag' yetarli emas! Kerak: {total_uzs:,} so'm, sizda: {user_bal:,} so'm.",
                }

            me = await self.get_me()
            if float(me.get("wallet_balance", 0.0)) < total_usd:
                return {
                    "success": False,
                    "code": "STORE_MAINTENANCE",
                    "message": "Texnik profilaktika tufayli xizmat vaqtincha mavjud emas.",
                }

            if not deduct_user_balance(tg_user_id, total_uzs):
                return {"success": False, "message": "Balansdan mablag' yechishda xatolik yuz berdi."}

            idem_key = f"muse_{tg_user_id}_{code_clean}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            await self.rate_limiter.acquire()
            url = f"{self._resolve_base_url()}/api/reseller/muse-buff/orders"
            payload = {
                "invite_code": code_clean,
                "quantity": qty,
                "customer_reference": f"tg_user_{tg_user_id}",
                "idempotency_key": idem_key,
            }
            order_ok = False
            order_data: Dict[str, Any] = {}
            err_msg = ""
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        rdata = await self._safe_json(resp)
                        ord_obj = rdata.get("order") if isinstance(rdata.get("order"), dict) else {}
                        if resp.status in (200, 201) and (rdata.get("success") or ord_obj.get("id")):
                            if str(ord_obj.get("fulfillment_status", "")).lower() == "failed_refunded":
                                err_msg = "Muse AI to'ldirish rad etildi (failed_refunded)"
                            else:
                                order_ok = True
                                order_data = {**rdata, **ord_obj}
                        else:
                            err_msg = self._friendly_error_message(resp.status, str(rdata.get("code") or ""), str(rdata.get("message") or rdata.get("detail") or ""))
            except Exception as e:
                err_msg = f"Tarmoq xatoligi: {e}"

            if not order_ok:
                add_user_balance(tg_user_id, total_uzs)
                save_ventebot_order(
                    tg_user_id=tg_user_id,
                    product_id=int(svc.get("product_id") or 999),
                    product_name=f"Muse AI Buff ({qty}B Tokens)",
                    quantity=qty,
                    amount_uzs=total_uzs,
                    amount_usd=total_usd,
                    delivery_type="muse_buff",
                    activation_identifier=code_clean,
                    status="REFUNDED",
                    ventebot_order_id=None,
                    delivered_data=err_msg,
                    idempotency_key=idem_key,
                )
                return {
                    "success": False,
                    "message": f"Buyurtma amalga oshmadi: {err_msg}. Mablag'ingiz ({total_uzs:,} so'm) qaytarildi.",
                }

            self.cache.delete("vb_me")
            f_status = str(order_data.get("fulfillment_status") or order_data.get("status") or "pending")
            db_status = "COMPLETED" if f_status == "succeeded" else "PAID_PENDING_DELIVERY"
            delivered_txt = f"Invite: {code_clean} | {qty}B token | Holat: {f_status}"
            db_oid = save_ventebot_order(
                tg_user_id=tg_user_id,
                product_id=int(svc.get("product_id") or 999),
                product_name=f"Muse AI Buff ({qty}B Tokens)",
                quantity=qty,
                amount_uzs=total_uzs,
                amount_usd=total_usd,
                delivery_type="muse_buff",
                activation_identifier=code_clean,
                status=db_status,
                ventebot_order_id=order_data.get("id"),
                delivered_data=delivered_txt,
                idempotency_key=idem_key,
            )
            return {
                "success": True,
                "order_id": db_oid,
                "ventebot_order_id": order_data.get("id"),
                "product_name": f"Muse AI Buff ({qty}B Tokens)",
                "quantity": qty,
                "amount_uzs": total_uzs,
                "new_balance_uzs": get_user_balance(tg_user_id),
                "status": db_status,
                "delivered_data": delivered_txt,
            }

    async def get_muse_order(self, muse_order_id: int) -> Dict[str, Any]:
        """Muse AI buyurtma holatini tekshirish."""
        await self.rate_limiter.acquire()
        url = f"{self._resolve_base_url()}/api/reseller/muse-buff/orders/{int(muse_order_id)}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return await self._safe_json(resp)
        except Exception as e:
            return {"success": False, "message": str(e)}


# Global singleton instance
ventebot_service = VenteBotClient()
