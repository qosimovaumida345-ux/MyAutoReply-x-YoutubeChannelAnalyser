"""
Binance Pay & Custom-Amount On-Chain Crypto Deposit Verifier by TxID / Order ID.

Foydalanuvchi istalgan (custom) summada Binance Pay (UID), USDT (TRC20 / BEP20)
yoki TON orqali to'lov qilib, faqat Tranzaksiya ID (TxID / TxHash / Binance Order ID)
raqamini botga tashlaydi. Tizim Binance Read-Only API hamda ochiq blockchain
explorerlari orqali to'lovni tasdiqlab, UZS balansini bir zumda to'ldiradi.
"""
import base64
import hashlib
import hmac
import re
import time
from typing import Optional
from urllib.parse import urlencode

import aiohttp

from config import USD_TO_UZS_RATE

STABLECOINS = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI"})
FALLBACK_USD_PRICES = {
    "TON": 5.50,
    "GRAM": 5.50,
    "BNB": 620.0,
    "BTC": 92000.0,
    "ETH": 3200.0,
    "SOL": 180.0,
    "TRX": 0.20,
}


def normalize_tx_id(raw: str) -> str:
    """Explorer URL (tronscan/bscscan/tonviewer) yoki oddiy matndan toza TxID / Order ID ajratish."""
    s = str(raw or "").strip()
    if not s:
        return ""
    if "://" in s:
        # Extract last non-empty path/fragment token
        m = re.search(r"(?:transaction|tx)/([A-Za-z0-9_-]{6,128})", s)
        if m:
            return m.group(1)
        s = s.rstrip("/").split("/")[-1].split("?")[0]
    s = re.sub(r"[^A-Za-z0-9_+=/:-]", "", s)
    return s.strip()


def _ton_account_hex(addr: str) -> str:
    """Raw ('0:<64-hex>') yoki base64url ('UQ...'/'EQ...') TON manzilni 64 belgili hex ID ga normallashtirish."""
    s = str(addr or "").strip()
    if not s:
        return ""
    if ":" in s:
        _, _, h = s.partition(":")
        h = h.strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", h):
            return h
        return ""
    try:
        padded = s.replace("+", "-").replace("/", "_") + "=" * (-len(s) % 4)
        raw = base64.urlsafe_b64decode(padded)
        if len(raw) == 36:
            return raw[2:34].hex().lower()
    except Exception:
        pass
    return ""


def _sign_binance(query_params: dict, api_secret: str) -> str:
    qs = urlencode(query_params)
    sig = hmac.new(api_secret.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{qs}&signature={sig}"


async def get_live_usd_price(asset: str) -> float:
    """Binance public ticker orqali aktivning jonli USD narxini olish."""
    clean = str(asset or "USDT").strip().upper()
    if clean in STABLECOINS:
        return 1.0
    symbol = f"{clean}USDT"
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    p = float(data.get("price") or 0)
                    if p > 0:
                        return p
    except Exception:
        pass
    return FALLBACK_USD_PRICES.get(clean, 1.0)


async def verify_binance_pay_tx(api_key: str, api_secret: str, tx_id: str) -> Optional[dict]:
    """Binance Read-Only API orqali Binance Pay (Order ID / Transaction ID) ni tekshirish."""
    if not api_key or not api_secret or not tx_id:
        return None
    ts = int(time.time() * 1000)
    params = {
        "timestamp": ts,
        "recvWindow": 15000,
        "limit": 100,
    }
    signed_qs = _sign_binance(params, api_secret)
    url = f"https://api.binance.com/sapi/v1/pay/transactions?{signed_qs}"
    headers = {"X-MBX-APIKEY": api_key}
    target = tx_id.lower()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                for item in data.get("data") or []:
                    cand_ids = [
                        str(item.get("orderId") or "").lower(),
                        str(item.get("transactionId") or "").lower(),
                        str(item.get("prepayId") or "").lower(),
                    ]
                    if target not in cand_ids:
                        continue
                    amt = float(item.get("amount") or 0)
                    # Only incoming positive credits belong to receiver
                    if amt <= 0:
                        continue
                    asset = str(item.get("currency") or "USDT").upper()
                    return {
                        "found": True,
                        "source": "binance_pay",
                        "network": "BINANCE_PAY",
                        "asset": asset,
                        "amount_crypto": amt,
                        "tx_id": str(item.get("orderId") or item.get("transactionId") or tx_id),
                    }
    except Exception:
        pass
    return None


async def verify_binance_deposit_tx(api_key: str, api_secret: str, tx_id: str) -> Optional[dict]:
    """Binance Read-Only API orqali On-Chain Depozit (TRC20/BEP20/TON/SOL va h.k.) TxID ni tekshirish."""
    if not api_key or not api_secret or not tx_id:
        return None
    ts = int(time.time() * 1000)
    params = {
        "status": 1,  # 1 = Success (credited)
        "limit": 100,
        "timestamp": ts,
        "recvWindow": 15000,
    }
    signed_qs = _sign_binance(params, api_secret)
    url = f"https://api.binance.com/sapi/v1/capital/deposit/hisrec?{signed_qs}"
    headers = {"X-MBX-APIKEY": api_key}
    target = tx_id.lower()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                rows = await resp.json()
                if not isinstance(rows, list):
                    return None
                for item in rows:
                    dep_tx = str(item.get("txId") or "").strip().lower()
                    # Binance sometimes prefixes internal transfers (e.g. "internal transfer 1234567890")
                    if not dep_tx or not (
                        dep_tx == target
                        or (len(target) >= 12 and (dep_tx.endswith(target) or dep_tx.endswith(f" {target}")))
                    ):
                        continue
                    amt = float(item.get("amount") or 0)
                    if amt <= 0:
                        continue
                    return {
                        "found": True,
                        "source": "binance_deposit",
                        "network": str(item.get("network") or "ONCHAIN").upper(),
                        "asset": str(item.get("coin") or "USDT").upper(),
                        "amount_crypto": amt,
                        "tx_id": tx_id,
                    }
    except Exception:
        pass
    return None


async def verify_public_chain_tx(
    tx_id: str,
    ton_wallet: str = "",
    trc20_addr: str = "",
    bep20_addr: str = "",
    ton_memo: str = "",
) -> Optional[dict]:
    """Ochiq blockchain explorerlari (TonAPI / Tronscan) orqali to'lovni zaxira tekshirish."""
    clean_hex = tx_id.lower().removeprefix("0x")
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. TRON (TRC20 USDT) via Tronscan public API
    if trc20_addr and re.fullmatch(r"[0-9a-f]{64}", clean_hex):
        try:
            url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={clean_hex}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        d = await resp.json()
                        if d.get("confirmed") and d.get("contractRet") == "SUCCESS":
                            for tr in d.get("trc20TransferInfo") or []:
                                if str(tr.get("to_address") or "").strip() == trc20_addr.strip():
                                    sym = str(tr.get("symbol") or "USDT").upper()
                                    dec = int(tr.get("decimals") or 6)
                                    raw_amt = float(tr.get("amount_str") or 0)
                                    amt = raw_amt / (10 ** dec)
                                    if sym in STABLECOINS and amt > 0:
                                        return {
                                            "found": True,
                                            "source": "tronscan",
                                            "network": "TRC20",
                                            "asset": sym,
                                            "amount_crypto": amt,
                                            "tx_id": clean_hex,
                                        }
        except Exception:
            pass

    # 2. TON (Native TON transfer to configured ton_wallet) via TonAPI
    if ton_wallet:
        try:
            url = f"https://tonapi.io/v2/blockchain/transactions/{tx_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        d = await resp.json()
                        in_msg = d.get("in_msg") or {}
                        dest = (in_msg.get("destination") or {}).get("address") or ""
                        val_nano = int(in_msg.get("value") or 0)
                        # Check canonical account hex (handles UQ.../EQ... vs raw 0:<hex>) or substring fallback
                        if d.get("success") and val_nano > 0:
                            cfg_hex = _ton_account_hex(ton_wallet)
                            dest_hex = _ton_account_hex(dest)
                            acct_match = bool(cfg_hex and dest_hex and cfg_hex == dest_hex) or (
                                ton_wallet.strip().lower() in dest.lower()
                            )
                            if acct_match:
                                expected_memo = str(ton_memo or "").strip()
                                if expected_memo:
                                    dec_body = in_msg.get("decoded_body")
                                    if not isinstance(dec_body, dict):
                                        dec_body = {}
                                    tx_comment = str(
                                        dec_body.get("text")
                                        or dec_body.get("comment")
                                        or ""
                                    ).strip()
                                    if not tx_comment and str(in_msg.get("decoded_op_name") or "").strip().lower() == "text_comment":
                                        raw_msg_txt = dec_body.get("value") or in_msg.get("message") or ""
                                        tx_comment = str(raw_msg_txt).strip()
                                    if tx_comment != expected_memo:
                                        return None
                                return {
                                    "found": True,
                                    "source": "tonapi",
                                    "network": "TON",
                                    "asset": "TON",
                                    "amount_crypto": val_nano / 1e9,
                                    "tx_id": d.get("hash") or tx_id,
                                }
        except Exception:
            pass

    return None


async def verify_crypto_tx_by_id(raw_tx_id: str) -> dict:
    """
    Foydalanuvchi yuborgan TxID / Binance Order ID ni to'liq tekshiradi:
    1) Oldin ishlatilmaganligini tekshiradi
    2) Binance Pay, Binance On-Chain Depozit va Ochiq Blockchain API dan qidiradi
    3) Jonli kurs bo'yicha UZS ekvivalentini hisoblaydi
    """
    from database import get_binance_crypto_config, is_crypto_tx_claimed

    tx_id = normalize_tx_id(raw_tx_id)
    if len(tx_id) < 6:
        return {"ok": False, "error": "TxID yoki Order ID juda qisqa (kamida 6 ta belgi kiriting)."}

    if is_crypto_tx_claimed(tx_id):
        return {"ok": False, "error": "Ushbu tranzaksiya (TxID) allaqachon hisobga o'tkazilgan!"}

    cfg = get_binance_crypto_config()
    api_key = cfg.get("binance_api_key", "")
    api_secret = cfg.get("binance_api_secret", "")

    found = None
    if api_key and api_secret:
        found = await verify_binance_pay_tx(api_key, api_secret, tx_id)
        if not found:
            found = await verify_binance_deposit_tx(api_key, api_secret, tx_id)

    if not found:
        found = await verify_public_chain_tx(
            tx_id,
            ton_wallet=cfg.get("ton_wallet_address", ""),
            trc20_addr=cfg.get("usdt_trc20_address", ""),
            bep20_addr=cfg.get("usdt_bep20_address", ""),
            ton_memo=cfg.get("ton_wallet_memo", ""),
        )

    if not found:
        if not (api_key and api_secret or cfg.get("ton_wallet_address") or cfg.get("usdt_trc20_address")):
            return {
                "ok": False,
                "error": "Kripto to'lov tizimi hali sozlanmagan (.env da BINANCE_API_KEY / BINANCE_API_SECRET va hamyon manzillari kiritilmagan).",
            }
        return {
            "ok": False,
            "error": (
                "Tranzaksiya topilmadi yoki hali blockchain/Binance da tasdiqlanmadi.\n"
                "1–2 daqiqa kutib, TxID / Binance Order ID ni to'g'ri yuborganingizni tekshiring."
            ),
        }

    # Verify the canonical tx_id wasn't claimed under another alias
    canon_tx_id = str(found.get("tx_id") or tx_id)
    if canon_tx_id != tx_id and is_crypto_tx_claimed(canon_tx_id):
        return {"ok": False, "error": "Ushbu tranzaksiya (TxID) allaqachon ishlatilgan!"}

    asset = found["asset"]
    amt_crypto = float(found["amount_crypto"])
    usd_price = await get_live_usd_price(asset)
    amount_uzs = max(500, int(round(amt_crypto * usd_price * USD_TO_UZS_RATE)))

    return {
        "ok": True,
        "tx_id": canon_tx_id,
        "network": found["network"],
        "asset": asset,
        "amount_crypto": amt_crypto,
        "usd_value": round(amt_crypto * usd_price, 4),
        "amount_uzs": amount_uzs,
        "source": found["source"],
    }
