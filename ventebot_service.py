import os
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
)
from database import (
    get_user_balance,
    deduct_user_balance,
    add_user_balance,
    save_ventebot_order,
    update_ventebot_order_status,
)

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


# ==================== VENTEBOT CLIENT ====================
class VenteBotClient:
    """
    VenteBot Reseller API bilan xavfsiz va keshlangan integratsiya xizmati.
    """
    def __init__(self):
        self.base_url = VENTEBOT_BASE_URL.rstrip("/")
        self.api_key = VENTEBOT_API_KEY
        self.cache = TTLCache()
        self.rate_limiter = VenteBotRateLimiter(max_tokens=55, refill_period=60.0)
        self._order_locks: Dict[int, asyncio.Lock] = {}

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

    def convert_usd_to_uzs(self, price_usd: float) -> int:
        """
        Tiered Smart Pricing Formula (Foydalanuvchi talabi):
        - $0.10 - $0.50 (masalan $0.30) -> 10x ko'paytirish (chakana ~$3.00 -> ~39,000 so'm, min 35,000 so'm)
        - $0.51 - $1.00 (masalan $1.00) -> 4x (chakana ~$4.00 -> ~51,000 so'm)
        - $1.01 - $3.00 (masalan $2.00) -> 2.5x (chakana ~$5.00 -> ~64,000 so'm)
        - $3.01 - $7.00 (masalan $5.00) -> 1.6x (chakana ~$8.00 -> ~103,000 so'm)
        - $7.01 - $12.00 (masalan $10.00) -> 1.5x (chakana ~$15.00 -> ~193,000 so'm)
        - $12.01 - $25.00 -> 1.35x
        - $25.01+ -> 1.25x
        - Minimal narx: 15,000 so'm.
        - Yaxlitlash: 1,000 so'mgacha yaxlitlanadi.
        """
        if not price_usd or price_usd <= 0:
            return 15000
        if price_usd <= 0.50:
            retail_usd = max(2.5, price_usd * 10.0)
        elif price_usd <= 1.00:
            retail_usd = max(3.5, price_usd * 4.0)
        elif price_usd <= 3.00:
            retail_usd = max(5.0, price_usd * 2.5)
        elif price_usd <= 7.00:
            retail_usd = max(8.0, price_usd * 1.6)
        elif price_usd <= 12.00:
            retail_usd = max(12.0, price_usd * 1.5)
        elif price_usd <= 25.00:
            retail_usd = price_usd * 1.35
        else:
            retail_usd = price_usd * 1.25
        rate = USD_TO_UZS_RATE or 12850.0
        uzs = int(round(retail_usd * rate, -3))
        return max(15000, uzs)

    @staticmethod
    def categorize_product(p: Dict[str, Any]) -> str:
        """88 ta tovarning har birini 6 ta qulay toifaga ajratadi"""
        name = (p.get("name") or "").lower()
        desc = (p.get("description") or "").lower()
        combined = name + " " + desc

        if "test product" in name:
            return "test"

        # 1. AI & LLM modellar
        if any(k in combined for k in [
            "chatgpt", "chat gpt", "openai", "gpt", "claude", "gemini", "grok", "xai",
            "cursor", "manus", "factory", "lovable", "lovalbe", "replit", "kiro",
            "codex", "openrouter", "groq", "flux", "midjourney"
        ]):
            return "ai"

        # 2. Video, Ovoz & Dizayn
        if any(k in combined for k in [
            "capcut", "supercut", "descript", "elevenlabs", "eleven labs", "brain.fm",
            "wispr", "gamma", "figma", "framer", "canva", "adobe", "magic patterns",
            "mobbin", "miro"
        ]):
            return "design_video"

        # 3. Kino, Musiqa & Striming
        if any(k in combined for k in [
            "spotify", "netflix", "amazon", "prime video", "hbo", "peacock", "apple tv", "wink"
        ]):
            return "media_streaming"

        # 4. Developer & Server vositalari
        if any(k in combined for k in [
            "railway", "warp", "n8n", "linear", "jetbrains", "autodesk", "ilovepdf",
            "wordwall", "quizlet", "quillbot"
        ]):
            return "dev_tools"

        # 5. VPN, Proxy & Xavfsiz Tarmoq
        if any(k in combined for k in [
            "nord", "proton", "hma", "proxy", "vpn", "zoom", "snapchat"
        ]):
            return "vpn_security"

        # 6. Ofis, Ta'lim & Dasturlar
        if any(k in combined for k in [
            "microsoft", "office", "windows", "gmail", "google drive", "notion",
            "duolingo", "coursera", "cousera", "trading view", "tradingview", "scribd"
        ]):
            return "office_edu"

        return "other"

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
        url = f"{self.base_url}/api/reseller/me"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("success"):
                        self.cache.set(cache_key, data, ttl_seconds=60)
                        return data
                    return {
                        "success": False,
                        "code": data.get("code", f"HTTP_{resp.status}"),
                        "message": data.get("message", "Do'kon hisob ma'lumotlarini olib bo'lmadi"),
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
    async def get_products(self, lang: str = "uz", force_refresh: bool = False) -> Dict[str, Any]:
        """
        Faol tovarlar katalogini olish.
        Kesh muddati: 10 daqiqa (600 soniya).
        Barcha 88 ta mahsulot 6 toifaga ajratiladi va so'mdagi marjali narxi hisoblanadi.
        """
        cache_key = f"vb_products_{lang}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        await self.rate_limiter.acquire()
        url = f"{self.base_url}/api/reseller/products?lang={lang}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    if resp.status == 200:
                        raw_data = await resp.json()
                        raw_products = raw_data if isinstance(raw_data, list) else raw_data.get("products", raw_data.get("items", []))
                        processed_products = []
                        for p in raw_products:
                            cat = self.categorize_product(p)
                            if cat == "test":
                                continue  # Vendor test tovarini mijozlarga ko'rsatmaslik
                            p_copy = dict(p)
                            price_usd = float(p.get("price_usd") or p.get("price") or 0)
                            p_copy["category"] = cat
                            p_copy["price_uzs"] = self.convert_usd_to_uzs(price_usd)
                            processed_products.append(p_copy)

                        res = {"success": True, "products": processed_products}
                        # 10 daqiqa keshda saqlash
                        self.cache.set(cache_key, res, ttl_seconds=600)
                        return res
                    else:
                        err_data = await resp.json() if resp.content_type == 'application/json' else {}
                        return {
                            "success": False,
                            "code": err_data.get("code", f"HTTP_{resp.status}"),
                            "message": err_data.get("message", "Mahsulotlar katalogini olib bo'lmadi"),
                            "products": [],
                        }
        except Exception as e:
            logger.error(f"get_products xatolik: {e}")
            return {
                "success": False,
                "code": "NETWORK_ERROR",
                "message": f"Katalog so'rovida xatolik: {str(e)}",
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
        url = f"{self.base_url}/api/reseller/quote"
        payload = {"product_id": int(product_id), "quantity": int(quantity)}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("success"):
                        quote = data.get("quote", {})
                        unit_usd = float(quote.get("unit_price") or 0)
                        total_usd = float(quote.get("total") or 0)
                        quote["unit_price_uzs"] = self.convert_usd_to_uzs(unit_usd)
                        quote["total_uzs"] = self.convert_usd_to_uzs(total_usd)
                        data["quote"] = quote
                        self.cache.set(cache_key, data, ttl_seconds=300)
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

            if delivery_type == "stock" and stock is not None and stock < quantity:
                return {"success": False, "message": f"Kechirasiz, mahsulot zaxirada yetarli emas (Mavjud: {stock} ta)"}

            # Aktivatsiya tovarlari uchun identifikator tekshiruvi
            clean_ident = (activation_identifier or "").strip()
            if delivery_type == "activation" and not clean_ident:
                return {
                    "success": False,
                    "code": "IDENTIFIER_REQUIRED",
                    "message": "Ushbu xizmat uchun faollashtirish ma'lumoti (Telegram username, ID yoki email) kiritilishi shart",
                }

            total_usd = round(price_usd * quantity, 2)
            total_uzs = self.convert_usd_to_uzs(price_usd) * quantity

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
            url = f"{self.base_url}/api/reseller/orders"
            payload = {
                "product_id": int(product_id),
                "quantity": int(quantity),
                "activation_identifier": clean_ident or None,
                "customer_reference": f"tg_user_{tg_user_id}",
                "idempotency_key": idempotency_key,
            }

            order_success = False
            ventebot_order_data = {}
            error_reason = ""

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        resp_data = await resp.json()
                        if resp.status in (200, 201) and resp_data.get("id"):
                            order_success = True
                            ventebot_order_data = resp_data
                        else:
                            error_reason = resp_data.get("message") or f"VenteBot xatosi: HTTP {resp.status}"
            except Exception as e:
                logger.error(f"VenteBot order HTTP so'rov xatosi: {e}")
                error_reason = f"Tarmoq uzilishi: {str(e)}"

            # 6. Muvaffaqiyatsiz bo'lsa — AVTOMATIK REFUND
            if not order_success:
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

            delivered_items = ventebot_order_data.get("items", [])
            delivered_text = ""
            if delivered_items:
                delivered_text = "\n".join([str(item.get("account_data", "")) for item in delivered_items if item.get("account_data")])
            elif ventebot_order_data.get("status") == "AWAITING_ACTIVATION":
                delivered_text = "Faollashtirish jarayonda (AWAITING_ACTIVATION)"

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
    # 5. ORDER DETAILS (/api/reseller/orders/{id})
    # -------------------------------------------------------------
    async def get_order_details(self, ventebot_order_id: int) -> Dict[str, Any]:
        """Buyurtma holatini VenteBot'dan qayta tekshirish"""
        await self.rate_limiter.acquire()
        url = f"{self.base_url}/api/reseller/orders/{ventebot_order_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return await resp.json()
        except Exception as e:
            return {"success": False, "message": str(e)}


# Global singleton instance
ventebot_service = VenteBotClient()
