import aiohttp
import asyncio
import base64
import logging
from database import (
    get_ton_wallet, get_payment_transaction,
    complete_payment_transaction, get_user_balance, get_db
)

logger = logging.getLogger(__name__)

def get_pending_ton_transactions():
    """Oxirgi 3 soat ichida yaratilgan va kutilayotgan TON to'lovlarini olish"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tg_user_id, amount_original, amount_uzs, created_at
            FROM payment_transactions
            WHERE currency = 'TON'
              AND status = 'pending'
              AND created_at >= NOW() - INTERVAL '3 hours'
            ORDER BY id ASC
        """)
        return cur.fetchall() or []
    except Exception as e:
        logger.error(f"get_pending_ton_transactions error: {e}")
        return []
    finally:
        conn.close()

def _extract_comment(in_msg: dict) -> str:
    """Toncenter tranzaksiyasidan izoh (memo) ni ajratib olish"""
    if not in_msg:
        return ""
    msg = in_msg.get("message", "")
    if not msg:
        msg_data = in_msg.get("msg_data", {})
        if isinstance(msg_data, dict):
            msg = msg_data.get("text") or msg_data.get("body") or ""
    if not msg:
        return ""
    # Base64 bo'lsa decode qilish
    if isinstance(msg, str):
        try:
            decoded = base64.b64decode(msg.strip()).decode("utf-8", errors="ignore")
            if any(c.isalnum() for c in decoded):
                return decoded.strip()
        except Exception:
            pass
    return str(msg).strip()

async def check_ton_payment_on_blockchain(wallet_address: str, tx_id: int, expected_ton: float) -> dict:
    """
    Toncenter va TonAPI orqali hamyonga tx_{tx_id} izohi bilan
    expected_ton miqdorida pul tushganini tekshirish
    """
    if not wallet_address:
        return {"found": False, "error": "Hamyon manzili sozlanmagan"}

    target_memo = f"tx_{tx_id}"
    expected_nanotons = int(expected_ton * 1e9)
    min_nanotons = int(expected_nanotons * 0.95) # 5% gacha tarmoq xarajati/farqini qamrab olish

    # 1. Toncenter API orqali tekshirish
    toncenter_url = f"https://toncenter.com/api/v2/getTransactions?address={wallet_address}&limit=25"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(toncenter_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok") and data.get("result"):
                        for tx in data["result"]:
                            in_msg = tx.get("in_msg", {})
                            if not in_msg:
                                continue
                            val = int(in_msg.get("value", 0))
                            comment = _extract_comment(in_msg)
                            
                            # Memo mos kelishini tekshirish
                            if target_memo.lower() in comment.lower() or str(tx_id) in comment:
                                if val >= min_nanotons:
                                    tx_hash = tx.get("transaction_id", {}).get("hash") or in_msg.get("hash") or f"tc_{tx_id}"
                                    sender = in_msg.get("source", "")
                                    return {
                                        "found": True,
                                        "tx_hash": tx_hash,
                                        "sender": sender,
                                        "amount_ton": val / 1e9,
                                        "comment": comment
                                    }
    except Exception as e:
        logger.warning(f"Toncenter check error for tx_{tx_id}: {e}")

    # 2. TonAPI orqali zaxira tekshirish (fallback)
    tonapi_url = f"https://tonapi.io/v2/blockchain/accounts/{wallet_address}/transactions?limit=25"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tonapi_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for tx in data.get("transactions", []):
                        in_msg = tx.get("in_msg", {})
                        if not in_msg:
                            continue
                        val = int(in_msg.get("value", 0))
                        comment = (
                            in_msg.get("decoded_body", {}).get("text")
                            or in_msg.get("message")
                            or _extract_comment(in_msg)
                        )
                        if target_memo.lower() in str(comment).lower() or str(tx_id) in str(comment):
                            if val >= min_nanotons:
                                tx_hash = tx.get("hash") or f"ta_{tx_id}"
                                sender = in_msg.get("source", {}).get("address", "") if isinstance(in_msg.get("source"), dict) else str(in_msg.get("source", ""))
                                return {
                                    "found": True,
                                    "tx_hash": tx_hash,
                                    "sender": sender,
                                    "amount_ton": val / 1e9,
                                    "comment": comment
                                }
    except Exception as e:
        logger.warning(f"TonAPI check error for tx_{tx_id}: {e}")

    return {"found": False}

async def verify_and_credit_ton_tx(tx_id: int) -> dict:
    """Tranzaksiyani tekshirib, agar to'langan bo'lsa balansga qo'shadi"""
    tx = get_payment_transaction(tx_id)
    if not tx:
        return {"ok": False, "error": "Tranzaksiya topilmadi"}

    if tx.get("status") == "completed":
        return {"ok": True, "already_completed": True, "tx": tx}

    wallet = get_ton_wallet()
    if not wallet:
        return {"ok": False, "error": "Botda TON hamyon o'rnatilmagan (/setton orqali o'rnating)"}

    expected_ton = float(tx.get("amount_original", 1.0))
    res = await check_ton_payment_on_blockchain(wallet, tx_id, expected_ton)

    if res.get("found"):
        tx_hash = res.get("tx_hash", f"ton_{tx_id}")
        updated_tx = complete_payment_transaction(tx_id, invoice_id=tx_hash)
        new_bal = get_user_balance(tx["tg_user_id"])
        return {
            "ok": True,
            "already_completed": False,
            "tx": updated_tx or tx,
            "new_balance": new_bal,
            "tx_hash": tx_hash,
            "sender": res.get("sender")
        }

    return {"ok": False, "not_found": True}


_ton_watcher_running = False

def start_ton_watcher_task(bot_client):
    """Orqa fonda TON blockchain tranzaksiyalarini kuzatishni boshlash"""
    global _ton_watcher_running
    if _ton_watcher_running:
        return
    _ton_watcher_running = True
    asyncio.create_task(_ton_watcher_loop(bot_client))


async def _ton_watcher_loop(bot_client):
    logger.info("TON Blockchain watcher ishga tushdi...")
    while True:
        try:
            await asyncio.sleep(12)
            wallet = get_ton_wallet()
            if not wallet:
                continue

            pending = get_pending_ton_transactions()
            if not pending:
                continue

            for p_tx in pending:
                tx_id = p_tx["id"]
                user_id = p_tx["tg_user_id"]
                amount_uzs = p_tx["amount_uzs"]
                amount_ton = p_tx["amount_original"]

                res = await verify_and_credit_ton_tx(tx_id)
                if res.get("ok") and not res.get("already_completed"):
                    new_bal = res.get("new_balance") or get_user_balance(user_id)
                    notify_text = (
                        f"✅ <b>To'lovingiz qabul qilindi!</b>\n\n"
                        f"🪙 <b>To'langan:</b> {amount_ton} GRAM (TON)\n"
                        f"💰 <b>Balansga qo'shildi:</b> +{amount_uzs:,} so'm\n"
                        f"⚖️ <b>Joriy balansingiz:</b> {new_bal:,} so'm\n\n"
                        f"🚀 Endi layk, obuna yoki izoh xizmatlaridan foydalanishingiz mumkin!"
                    )
                    try:
                        await bot_client.send_message(user_id, notify_text)
                    except Exception as send_err:
                        logger.warning(f"Error sending TON payment notification to {user_id}: {send_err}")
        except Exception as e:
            logger.error(f"ton_watcher_loop error: {e}")
            await asyncio.sleep(15)

