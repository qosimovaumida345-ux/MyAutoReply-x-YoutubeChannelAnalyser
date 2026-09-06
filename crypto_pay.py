import json
import hmac
import hashlib
import aiohttp
import logging
from config import CRYPTO_PAY_TOKEN
from database import complete_payment_transaction, get_user_balance

logger = logging.getLogger(__name__)

# CryptoPay API Base URL
BASE_URL = "https://pay.crypt.bot/api"

# USDT va GRAM (sobiq TON) kurslari (UZS ga nisbatan)
# 2026-yil holatiga: 1 GRAM (TON) ≈ $1.41 - $1.42 ≈ 18,000 so'm
CRYPTO_PACKAGES = [
    {"asset": "USDT", "amount": 1.0, "amount_uzs": 12800, "label": "1 USDT — 12,800 so'm"},
    {"asset": "USDT", "amount": 3.0, "amount_uzs": 38400, "label": "3 USDT — 38,400 so'm"},
    {"asset": "USDT", "amount": 5.0, "amount_uzs": 64000, "label": "5 USDT — 64,000 so'm"},
    {"asset": "USDT", "amount": 10.0, "amount_uzs": 128000, "label": "10 USDT — 128,000 so'm"},
    {"asset": "USDT", "amount": 25.0, "amount_uzs": 320000, "label": "25 USDT — 320,000 so'm"},
    {"asset": "TON", "amount": 1.0, "amount_uzs": 18000, "label": "1 GRAM (TON) — 18,000 so'm"},
    {"asset": "TON", "amount": 3.0, "amount_uzs": 54000, "label": "3 GRAM (TON) — 54,000 so'm"},
    {"asset": "TON", "amount": 5.0, "amount_uzs": 90000, "label": "5 GRAM (TON) — 90,000 so'm"},
    {"asset": "TON", "amount": 10.0, "amount_uzs": 180000, "label": "10 GRAM (TON) — 180,000 so'm"},
]

async def get_exchange_rates() -> list:
    """CryptoPay API dan real vaqtdagi valyuta kurslarini olish"""
    if not CRYPTO_PAY_TOKEN:
        return []
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
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
    if not CRYPTO_PAY_TOKEN or not signature:
        return False
    try:
        secret = hashlib.sha256(CRYPTO_PAY_TOKEN.encode()).digest()
        calc_sig = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(calc_sig, signature)
    except Exception as e:
        logger.error(f"Signature verify error: {e}")
        return False


async def create_crypto_pay_invoice(tg_user_id: int, asset: str, amount: float, amount_uzs: int, tx_id: int) -> dict:
    """CryptoPay orqali to'lov fakturasi (invoice) yaratadi"""
    if not CRYPTO_PAY_TOKEN:
        raise ValueError("CRYPTO_PAY_TOKEN sozlanmagan! .env faylni tekshiring.")

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
    }
    
    payload_data = json.dumps({
        "tg_user_id": tg_user_id,
        "amount_uzs": amount_uzs,
        "tx_id": tx_id,
        "asset": asset
    })

    data = {
        "asset": asset,
        "amount": str(amount),
        "description": f"YouTube Bot hisobini to'ldirish ({amount_uzs:,} so'm)",
        "hidden_message": "To'lovingiz qabul qilindi! Balansingiz muvaffaqiyatli to'ldirildi.",
        "payload": payload_data,
        "expires_in": 3600 # 1 soat
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
                    "asset": result.get("asset"),
                }
            else:
                logger.error(f"CryptoPay error {resp.status}: {res}")
                return {"ok": False, "error": res.get("error", "Noma'lum xatolik")}


async def transfer_crypto_pay(user_id: int, asset: str, amount: float, spend_id: str, comment: str = "") -> dict:
    """CryptoPay orqali bot hisobidan Telegram foydalanuvchiga (masalan bot egasiga) to'g'ridan-to'g'ri o'tkazish"""
    if not CRYPTO_PAY_TOKEN:
        return {"ok": False, "error": "CRYPTO_PAY_TOKEN sozlanmagan"}
        
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
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
    if not CRYPTO_PAY_TOKEN:
        return {"ok": False, "error": "CRYPTO_PAY_TOKEN sozlanmagan"}
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
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
    if not CRYPTO_PAY_TOKEN:
        return {"ok": False, "error": "CRYPTO_PAY_TOKEN sozlanmagan"}
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
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

