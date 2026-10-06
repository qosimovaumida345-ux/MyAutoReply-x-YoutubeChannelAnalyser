import time
import logging
import asyncio
from typing import Optional, Dict, Any
import aiohttp

from config import USD_TO_UZS_RATE

logger = logging.getLogger("currency_service")

class CurrencyService:
    """
    Real-time USD/UZS valyuta kursi xizmati.
    Manbalar:
    1. O'zbekiston Markaziy Banki (CBU.uz) rasmiy ochiq API
    2. Open Exchange Rates (open.er-api.com)
    3. ExchangeRate-API (api.exchangerate-api.com)
    4. Fallback: config.py (USD_TO_UZS_RATE)
    
    Kesh va fon yangilanishi:
    - 30 daqiqa kesh muddati.
    - Tezkor hisob-kitoblar uchun sinxron get_cached_rate() metodi mavjud.
    """

    def __init__(self, cache_ttl_seconds: int = 1800):
        self._cache_ttl = cache_ttl_seconds
        self._cached_rate: float = float(USD_TO_UZS_RATE or 12850.0)
        self._last_updated: float = 0.0
        self._last_source: str = "config_fallback"
        self._lock = asyncio.Lock()

    @property
    def current_rate(self) -> float:
        """Sinxron o'qish (keshdan yoki oxirgi olingan kursdan)"""
        return self._cached_rate

    def get_cached_usd_rate(self) -> float:
        """Sinxron metod: bot ichidagi tezkor hisob-kitoblar uchun darhol float qaytaradi"""
        return self._cached_rate

    async def get_usd_to_uzs_rate(self, force_refresh: bool = False) -> float:
        """
        Asinxron ravishda real-time USD -> UZS kursini oladi.
        Kesh muddati o'tmagan bo'lsa, keshdagi kurs qaytariladi.
        """
        now = time.time()
        if not force_refresh and (now - self._last_updated < self._cache_ttl) and self._last_updated > 0:
            return self._cached_rate

        async with self._lock:
            # Re-check after lock
            if not force_refresh and (time.time() - self._last_updated < self._cache_ttl) and self._last_updated > 0:
                return self._cached_rate

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            # 1-Manba: CBU.uz (O'zbekiston Markaziy Banki rasmiy kursi)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, list) and len(data) > 0:
                                rate_str = data[0].get("Rate")
                                if rate_str:
                                    rate_val = float(rate_str)
                                    if rate_val > 5000:
                                        self._cached_rate = rate_val
                                        self._last_updated = time.time()
                                        self._last_source = f"CBU.uz ({data[0].get('Date', 'today')})"
                                        logger.info(f"💵 Real-time USD kursi CBU.uz dan yangilandi: 1 USD = {rate_val:,.2f} UZS")
                                        return self._cached_rate
            except Exception as e:
                logger.warning(f"CBU.uz dan kurs olishda xatolik: {e}")

            # 2-Manba: Open Exchange Rates (open.er-api.com)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://open.er-api.com/v6/latest/USD",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            rates = data.get("rates", {})
                            uzs_rate = rates.get("UZS")
                            if uzs_rate and float(uzs_rate) > 5000:
                                self._cached_rate = float(uzs_rate)
                                self._last_updated = time.time()
                                self._last_source = "open.er-api.com"
                                logger.info(f"💵 Real-time USD kursi OpenER dan yangilandi: 1 USD = {self._cached_rate:,.2f} UZS")
                                return self._cached_rate
            except Exception as e:
                logger.warning(f"OpenER dan kurs olishda xatolik: {e}")

            # 3-Manba: ExchangeRate-API (api.exchangerate-api.com)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.exchangerate-api.com/v4/latest/USD",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            rates = data.get("rates", {})
                            uzs_rate = rates.get("UZS")
                            if uzs_rate and float(uzs_rate) > 5000:
                                self._cached_rate = float(uzs_rate)
                                self._last_updated = time.time()
                                self._last_source = "exchangerate-api.com"
                                logger.info(f"💵 Real-time USD kursi ExchangeRate-API dan yangilandi: 1 USD = {self._cached_rate:,.2f} UZS")
                                return self._cached_rate
            except Exception as e:
                logger.warning(f"ExchangeRate-API dan kurs olishda xatolik: {e}")

            # 4-Fallback: config.py
            if self._cached_rate <= 0:
                self._cached_rate = float(USD_TO_UZS_RATE or 12850.0)
            self._last_updated = time.time()
            logger.info(f"💵 Standart fallback USD kursi ishlatilmoqda: 1 USD = {self._cached_rate:,.2f} UZS")
            return self._cached_rate

    def get_info(self) -> Dict[str, Any]:
        """Kurs haqidagi to'liq metama'lumot"""
        return {
            "rate": self._cached_rate,
            "source": self._last_source,
            "last_updated": self._last_updated,
            "age_seconds": round(time.time() - self._last_updated, 1) if self._last_updated > 0 else None,
        }

# Global singleton
currency_service = CurrencyService()
