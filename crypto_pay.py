import os
import json
import hmac
import hashlib
from typing import Optional
import aiohttp
import logging
from config import CRYPTO_PAY_TOKEN
from database import complete_payment_transaction, get_user_balance

logger = logging.getLogger(__name__)

# CryptoPay API Base URL
BASE_URL = "https://pay.crypt.bot/api"


def _get_crypto_pay_token() -> str:
    """Resolve @CryptoBot token dynamically from .env / os.environ or config fallback."""
    env_tok = os.getenv("CRYPTO_PAY_TOKEN", "").strip()
    if env_tok:
        return env_tok
    return (CRYPTO_PAY_TOKEN or "").strip()

# Faqat TON paketlari (Foydalanuvchi qoidasi: Faqat TON va Stars)
CRYPTO_PACKAGES = [
    {"asset": "TON", "amount": 0.5, "amount_uzs": 10000, "label": "💎 0.5 TON — 10,000 so'm (Minimal)"},
    {"asset": "TON", "amount": 1.0, "amount_uzs": 20000, "label": "💎 1 TON — 20,000 so'm"},
    {"asset": "TON", "amount": 2.0, "amount_uzs": 40000, "label": "💎 2 TON — 40,000 so'm"},
    {"asset": "TON", "amount": 3.0, "amount_uzs": 60000, "label": "💎 3 TON — 60,000 so'm"},
    {"asset": "TON", "amount": 5.0, "amount_uzs": 100000, "label": "💎 5 TON — 100,000 so'm"},
    {"asset": "TON", "amount": 10.0, "amount_uzs": 200000, "label": "💎 10 TON — 200,000 so'm"},
]

async def get_exchange_rates() -> list:
    """CryptoPay API dan real vaqtdagi valyuta kurslarini olish"""
    token = _get_crypto_pay_token()
    if not token:
        return []
    headers = {"Crypto-Pay-API-Token": token}
    url = f"{BASE_URL}/getExchangeRates"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                res = await resp.json()
                if resp.status == 200 and res.get("ok"):
                    return res.get("result", [])
    except Exception as e:
        logger.warning(f"getExchangeRates error: {e}")
    return []


def verify_crypto_pay_signature(raw_body: bytes, signature: str) -> bool:
    """CryptoPay webhook imzosini tekshirish"""
    token = _get_crypto_pay_token()
    if not token or not signature:
        return False
    try:
        secret = hashlib.sha256(token.encode()).digest()
        calc_sig = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(calc_sig, signature)
    except Exception as e:
        logger.error(f"Signature verify error: {e}")
        return False


async def create_crypto_pay_invoice(
    tg_user_id: int,
    asset: str,
    amount: float,
    amount_uzs: int,
    tx_id: int,
    currency_type: str = "crypto",
    accepted_assets: str = "USDT,TON,BTC,ETH,LTC,BNB,TRX,USDC",
) -> dict:
    """CryptoPay (@CryptoBot) orqali crypto yoki ko'p koinli fiat-USD to'lov fakturasini yaratadi"""
    token = _get_crypto_pay_token()
    if not token:
        raise ValueError("CRYPTO_PAY_TOKEN sozlanmagan! .env faylni tekshiring.")

    headers = {
        "Crypto-Pay-API-Token": token
    }

    payload_data = json.dumps({
        "tg_user_id": tg_user_id,
        "amount_uzs": amount_uzs,
        "tx_id": tx_id,
        "asset": asset,
        "currency_type": currency_type,
    })

    ctype = str(currency_type or "crypto").strip().lower()
    if ctype == "fiat":
        data = {
            "currency_type": "fiat",
            "fiat": (asset or "USD").upper(),
            "accepted_assets": accepted_assets,
            "amount": str(amount),
            "description": f"Mono Deck Studio hisobini to'ldirish ({amount_uzs:,} so'm)",
            "hidden_message": "To'lovingiz qabul qilindi! Balansingiz muvaffaqiyatli to'ldirildi.",
            "payload": payload_data,
            "expires_in": 3600,
        }
    else:
        data = {
            "currency_type": "crypto",
            "asset": asset,
            "amount": str(amount),
            "description": f"Mono Deck Studio hisobini to'ldirish ({amount_uzs:,} so'm)",
            "hidden_message": "To'lovingiz qabul qilindi! Balansingiz muvaffaqiyatli to'ldirildi.",
            "payload": payload_data,
            "expires_in": 3600,
        }

    url = f"{BASE_URL}/createInvoice"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            res = await resp.json()
            if resp.status == 200 and res.get("ok"):
                result = res["result"]
                return {
                    "ok": True,
                    "invoice_id": str(result["invoice_id"]),
                    "pay_url": result.get("bot_invoice_url") or result.get("pay_url") or result.get("mini_app_invoice_url"),
                    "amount": result.get("amount"),
                    "asset": result.get("asset") or result.get("fiat") or asset,
                    "currency_type": result.get("currency_type") or ctype,
                }
            else:
                logger.error(f"CryptoPay error {resp.status}: {res}")
                return {"ok": False, "error": res.get("error", "Noma'lum xatolik")}


async def get_crypto_pay_invoice(invoice_id: str) -> Optional[dict]:
    """CryptoPay (@CryptoBot) API orqali aniq invoice holatini (status/asset/amount) tekshirish."""
    token = _get_crypto_pay_token()
    clean_id = str(invoice_id or "").strip()
    if not token or not clean_id:
        return None
    headers = {"Crypto-Pay-API-Token": token}
    url = f"{BASE_URL}/getInvoices?invoice_ids={clean_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                res = await resp.json()
                if resp.status == 200 and res.get("ok"):
                    result = res.get("result")
                    items = result.get("items", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
                    for item in items:
                        if str(item.get("invoice_id") or "") == clean_id:
                            return item
                    return items[0] if items else None
    except Exception as e:
        logger.warning(f"get_crypto_pay_invoice error: {e}")
    return None


async def transfer_crypto_pay(user_id: int, asset: str, amount: float, spend_id: str, comment: str = "") -> dict:
    """CryptoPay orqali bot hisobidan Telegram foydalanuvchiga (masalan bot egasiga) to'g'ridan-to'g'ri o'tkazish"""
    token = _get_crypto_pay_token()
    if not token:
        return {"ok": False, "error": "CRYPTO_PAY_TOKEN sozlanmagan"}
        
    headers = {
        "Crypto-Pay-API-Token": token
    }
    
    data = {
        "user_id": int(user_id),
        "asset": asset,
        "amount": str(amount),
        "spend_id": str(spend_id),
        "comment": comment or f"Transfer #{spend_id}"
    }
    
    url = f"{BASE_URL}/transfer"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                res = await resp.json()
                if resp.status == 200 and res.get("ok"):
                    logger.info(f"CryptoPay transfer muvaffaqiyatli: {amount} {asset} -> {user_id}")
                    return {"ok": True, "result": res.get("result")}
                else:
                    logger.warning(f"CryptoPay transfer xatoligi {resp.status}: {res}")
                    return {"ok": False, "error": res.get("error", "Transfer xatoligi")}
    except Exception as e:
        logger.error(f"CryptoPay transfer request error: {e}")
        return {"ok": False, "error": str(e)}


async def get_crypto_pay_balance() -> dict:
    """CryptoPay bot hisobidagi qoldiqlarni olish"""
    token = _get_crypto_pay_token()
    if not token:
        return {"ok": False, "error": "CRYPTO_PAY_TOKEN sozlanmagan"}
    headers = {"Crypto-Pay-API-Token": token}
    url = f"{BASE_URL}/getBalance"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                res = await resp.json()
                if resp.status == 200 and res.get("ok"):
                    return {"ok": True, "result": res.get("result", [])}
                return {"ok": False, "error": res.get("error")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def get_crypto_pay_me() -> dict:
    """CryptoPay ilova ma'lumotlarini tekshirish"""
    token = _get_crypto_pay_token()
    if not token:
        return {"ok": False, "error": "CRYPTO_PAY_TOKEN sozlanmagan"}
    headers = {"Crypto-Pay-API-Token": token}
    url = f"{BASE_URL}/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                res = await resp.json()
                if resp.status == 200 and res.get("ok"):
                    return {"ok": True, "result": res.get("result")}
                return {"ok": False, "error": res.get("error")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

