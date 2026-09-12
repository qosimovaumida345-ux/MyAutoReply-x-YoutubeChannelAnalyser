"""
Games, Gamification & Monetization Engine
Ushbu modul botdagi barcha yuqori daromadli va o'yinli funksiyalarni boshqaradi:
1. Mystery Box (Omadli Quti) - 15 Stars / 6,000 so'm, past yutish ehtimoli (~88% kassa foydasi)
2. PvP Coin Flip Duel (Tanga Tashlash) - 10% kassa komissiyasi bilan
3. Omad G'ildiragi (Wheel of Fortune) - 1 ta tekin kunlik spin + pullik spinlar
4. Jekpot Mega Lotereya - 3,000 so'mlik biletlar, 35% kassa foydasi
5. Vaucherlar & Promokodlar (Gift cards)
6. Reseller Webhook obunasi ($3 / hafta)
7. White-Label Bot ($50 VIP)
"""

import random
import secrets
from datetime import datetime, timedelta
from database import (
    get_db,
    get_user_balance,
    add_user_balance,
    deduct_user_balance,
    purchase_api_key,
    purchase_proxy
)

# ==================== 1. VAUCHERLAR & PROMOKODLAR ====================

def create_vouchers(created_by: int, amount_uzs: int, count: int = 1) -> list:
    """Admin yoki tizim tomonidan sovg'a vaucherlari (GIFT-XXXX) yaratish"""
    conn = get_db()
    if not conn: return []
    codes = []
    try:
        cur = conn.cursor()
        for _ in range(count):
            code = "GIFT-" + secrets.token_hex(4).upper() + "-" + secrets.token_hex(4).upper()
            cur.execute("""
                INSERT INTO vouchers (code, amount_uzs, created_by)
                VALUES (%s, %s, %s)
            """, (code, amount_uzs, created_by))
            codes.append(code)
        conn.commit()
        return codes
    except Exception as e:
        conn.rollback()
        print(f"create_vouchers error: {e}")
        return []
    finally:
        conn.close()

def redeem_voucher(tg_user_id: int, code: str) -> dict:
    """Foydalanuvchi vaucher kodini kiritib balansini to'ldirishi"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    clean_code = str(code).strip().upper()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vouchers WHERE code = %s FOR UPDATE", (clean_code,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return {"ok": False, "error": "Bunday vaucher kodi mavjud emas!"}
            
        used_by = row["used_by"] if isinstance(row, dict) else row[4]
        if used_by:
            conn.rollback()
            return {"ok": False, "error": "Ushbu vaucher allaqachon ishlatilgan!"}
            
        amount_uzs = row["amount_uzs"] if isinstance(row, dict) else row[2]
        voucher_id = row["id"] if isinstance(row, dict) else row[0]
        
        # Vaucher holatini yangilash
        cur.execute("""
            UPDATE vouchers
            SET used_by = %s, used_at = NOW()
            WHERE id = %s
        """, (tg_user_id, voucher_id))
        
        # Foydalanuvchi balansiga qo'shish
        cur.execute("""
            INSERT INTO user_balances (tg_user_id, balance_uzs)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id) DO UPDATE 
            SET balance_uzs = user_balances.balance_uzs + EXCLUDED.balance_uzs,
                updated_at = NOW()
            RETURNING balance_uzs
        """, (tg_user_id, amount_uzs))
        b_res = cur.fetchone()
        new_bal = b_res["balance_uzs"] if isinstance(b_res, dict) else b_res[0]
        
        conn.commit()
        return {
            "ok": True,
            "amount_uzs": amount_uzs,
            "new_balance": new_bal
        }
    except Exception as e:
        conn.rollback()
        print(f"redeem_voucher error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ==================== 2. MYSTERY BOX (OMADLI QUTI) ====================

def open_mystery_box(tg_user_id: int, cost_uzs: int = 6000) -> dict:
    """
    Mystery Box ochish. 
    Yutish ehtimoli past (~88% kassa foydasi):
    - 65%: Bo'sh quti (Lose)
    - 20%: 1,000 so'm keshbek (Cashback)
    - 10%: Groq Cloud API kalit (Groq)
    - 3%: OpenRouter API kalit (Jackpot 1)
    - 2%: Gemini API kalit (Jackpot 2)
    """
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza bilan aloqa yo'q"}
    try:
        cur = conn.cursor()
        # 1. Balans tekshirish va ayirish
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (tg_user_id,))
        b_row = cur.fetchone()
        curr_bal = b_row["balance_uzs"] if b_row else 0
        if curr_bal < cost_uzs:
            conn.rollback()
            return {
                "ok": False,
                "insufficient_funds": True,
                "required": cost_uzs,
                "current": curr_bal,
                "error": f"Balansingiz yetarli emas! Quti narxi: {cost_uzs:,} so'm"
            }
            
        new_bal = curr_bal - cost_uzs
        cur.execute("UPDATE user_balances SET balance_uzs = %s, updated_at = NOW() WHERE tg_user_id = %s", (new_bal, tg_user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
        
    # 2. Random roll
    roll = random.randint(1, 100)
    prize_type = "lose"
    prize_value = ""
    prize_title = "Bo'sh quti"
    
    if roll <= 65:
        # 65%: Yutqazdi
        prize_type = "lose"
        prize_title = "Afsus, bu safar quti bo'sh chiqdi! 😢"
    elif roll <= 85:
        # 20%: Kichik keshbek (1,000 so'm)
        prize_type = "cashback"
        cash_won = 1000
        prize_value = str(cash_won)
        prize_title = f"🎁 Yupanchiq sovg'a: {cash_won:,} so'm keshbek!"
        add_user_balance(tg_user_id, cash_won)
    elif roll <= 95:
        # 10%: Groq API
        k_res = purchase_api_key(tg_user_id, "groq")
        if k_res.get("ok"):
            prize_type = "groq"
            prize_value = k_res.get("api_key", "")
            prize_title = "⚡ Groq Cloud API Kaliti!"
        else:
            # Agar groq tugagan bo'lsa 2,000 so'm keshbek
            prize_type = "cashback"
            prize_value = "2000"
            prize_title = "🎁 2,000 so'm keshbek!"
            add_user_balance(tg_user_id, 2000)
    elif roll <= 98:
        # 3%: OpenRouter API
        k_res = purchase_api_key(tg_user_id, "openrouter")
        if k_res.get("ok"):
            prize_type = "openrouter"
            prize_value = k_res.get("api_key", "")
            prize_title = "🔥 JACKPOT: OpenRouter API Kaliti ($3)!"
        else:
            prize_type = "cashback"
            prize_value = "5000"
            prize_title = "🎁 5,000 so'm Katta Keshbek!"
            add_user_balance(tg_user_id, 5000)
    else:
        # 2%: Gemini API
        k_res = purchase_api_key(tg_user_id, "gemini")
        if k_res.get("ok"):
            prize_type = "gemini"
            prize_value = k_res.get("api_key", "")
            prize_title = "✨ SUPER JACKPOT: Google Gemini API Kaliti ($5)!"
        else:
            prize_type = "cashback"
            prize_value = "5000"
            prize_title = "🎁 5,000 so'm Katta Keshbek!"
            add_user_balance(tg_user_id, 5000)
            
    # Logga yozish
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO mystery_box_logs (tg_user_id, cost_uzs, prize_type, prize_value)
                VALUES (%s, %s, %s, %s)
            """, (tg_user_id, cost_uzs, prize_type, prize_value))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
            
    return {
        "ok": True,
        "prize_type": prize_type,
        "prize_title": prize_title,
        "prize_value": prize_value,
        "remaining_balance": get_user_balance(tg_user_id)
    }

def get_recent_box_winners(limit: int = 5) -> list:
    """Oxirgi yutgan foydalanuvchilar (Hype / FOMO uchun)"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tg_user_id, prize_type, prize_value, created_at
            FROM mystery_box_logs
            WHERE prize_type != 'lose'
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall() or []
        res = []
        for r in rows:
            uid = r["tg_user_id"] if isinstance(r, dict) else r[0]
            ptype = r["prize_type"] if isinstance(r, dict) else r[1]
            masked_uid = str(uid)[:3] + "***" + str(uid)[-2:]
            res.append({"user": masked_uid, "prize": ptype.upper()})
        return res
    except Exception:
        return []
    finally:
        conn.close()


# ==================== 2.1 TELEGRAM STARS DYNAMIC SERVER GIFTS & CASES ====================

_LIVE_SERVER_GIFTS = []
_LAST_SERVER_FETCH = 0

async def fetch_telegram_server_gifts(bot_token: str = None) -> list:
    """
    Telegram Bot API getAvailableGifts orqali Telegram serveridagi
    BARCHA faol rasmiy sovg'alarni jonli yuklab oladi.
    Hech qanday statik cheklov yo'q - serverda qancha bo'lsa, hammasini oladi.
    """
    global _LIVE_SERVER_GIFTS, _LAST_SERVER_FETCH
    import time
    now = time.time()
    if _LIVE_SERVER_GIFTS and (now - _LAST_SERVER_FETCH < 180):
        return _LIVE_SERVER_GIFTS

    import os
    from config import BOT_TOKEN
    token = bot_token or BOT_TOKEN or os.getenv("BOT_TOKEN", "")
    if token:
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{token}/getAvailableGifts"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=6) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        gifts = data.get("result", {}).get("gifts", [])
                        if gifts:
                            _LIVE_SERVER_GIFTS = gifts
                            _LAST_SERVER_FETCH = now
                            return gifts
        except Exception as e:
            print(f"Telegram getAvailableGifts server fetch error: {e}")

    return _LIVE_SERVER_GIFTS

def build_cases_from_gifts(raw_gifts: list = None) -> dict:
    """
    Serverdan olingan sovg'alarni avtomatik ravishda qiymati va NFT darajasiga ko'ra
    5 ta keysga taqsimlaydi. Hech qanday statik hardcode yo'q.
    """
    gifts = raw_gifts if raw_gifts is not None else _LIVE_SERVER_GIFTS
    
    items = []
    if gifts:
        for g in gifts:
            gid = str(g.get("id"))
            stars = int(g.get("star_count", 25))
            sticker = g.get("sticker", {}) if isinstance(g.get("sticker"), dict) else {}
            total_count = g.get("total_count")
            remains = g.get("remaining_count")
            upgrade_stars = g.get("upgrade_star_count")
            is_nft = bool(upgrade_stars or total_count)
            
            emoji = sticker.get("emoji") or ("👑" if is_nft else "🎁")
            name = f"Telegram Sovg'a ({stars} ⭐)"
            if is_nft:
                name = f"Limited Collectible NFT ({stars} ⭐)"
                if total_count:
                    name += f" [#{remains or 0}/{total_count}]"

            items.append({
                "id": gid,
                "stars": stars,
                "name": name,
                "icon": emoji,
                "is_nft": is_nft,
                "total_count": total_count,
                "remaining_count": remains,
                "upgrade_stars": upgrade_stars,
                "blockchain": "TON" if is_nft else None,
                "marketplace": "Fragment.com" if is_nft else None
            })

    items.sort(key=lambda x: x["stars"])

    # Har bir tier uchun drops ro'yxati (serverdan olingan sovg'alar bo'yicha)
    t1_drops = [it for it in items if it["stars"] <= 50] or [
        {"id": "tg_cake", "stars": 15, "name": "Delicious Cake", "icon": "🎂", "is_nft": False},
        {"id": "tg_star", "stars": 25, "name": "Green Star", "icon": "💚", "is_nft": False},
        {"id": "tg_bear", "stars": 50, "name": "Teddy Bear", "icon": "🧸", "is_nft": False}
    ]
    t2_drops = [it for it in items if 25 <= it["stars"] <= 250] or [
        {"id": "tg_bouquet", "stars": 50, "name": "Bouquet of Flowers", "icon": "💐", "is_nft": False},
        {"id": "tg_champagne", "stars": 100, "name": "Champagne Bottle", "icon": "🍾", "is_nft": False},
        {"id": "tg_ring", "stars": 250, "name": "Diamond Ring", "icon": "💍", "is_nft": False}
    ]
    t3_drops = [it for it in items if 100 <= it["stars"] <= 500] or [
        {"id": "tg_champagne", "stars": 100, "name": "Champagne Bottle", "icon": "🍾", "is_nft": False},
        {"id": "tg_ring", "stars": 250, "name": "Diamond Ring", "icon": "💍", "is_nft": False},
        {"id": "tg_trophy", "stars": 500, "name": "Golden Trophy", "icon": "🏆", "is_nft": False}
    ]
    t4_drops = [it for it in items if (250 <= it["stars"] <= 1000) or it["is_nft"]] or [
        {"id": "tg_trophy", "stars": 500, "name": "Golden Trophy", "icon": "🏆", "is_nft": False},
        {"id": "tg_rocket", "stars": 1000, "name": "Space Rocket", "icon": "🚀", "is_nft": False},
        {"id": "tg_durov_cap", "stars": 1000, "name": "Durov's Black Cap NFT", "icon": "🧢", "is_nft": True, "blockchain": "TON", "marketplace": "Fragment.com"}
    ]
    t5_drops = [it for it in items if it["stars"] >= 1000 or it["is_nft"]] or [
        {"id": "tg_rocket", "stars": 1000, "name": "Space Rocket", "icon": "🚀", "is_nft": False},
        {"id": "tg_pepe", "stars": 1500, "name": "Plush Pepe NFT", "icon": "🐸", "is_nft": True, "blockchain": "TON", "marketplace": "Fragment.com"},
        {"id": "tg_crown", "stars": 5000, "name": "Royal Crown Collectible NFT", "icon": "👑", "is_nft": True, "blockchain": "TON", "marketplace": "Fragment.com"}
    ]

    def format_drops(drop_list):
        if len(drop_list) == 1:
            return [{**drop_list[0], "weight": 100, "rarity": "common"}]
        elif len(drop_list) == 2:
            return [
                {**drop_list[0], "weight": 75, "rarity": "common"},
                {**drop_list[1], "weight": 25, "rarity": "rare"}
            ]
        else:
            common_item = drop_list[0]
            rare_item = drop_list[len(drop_list) // 2]
            legendary_item = drop_list[-1]
            return [
                {**common_item, "weight": 70, "rarity": "common"},
                {**rare_item, "weight": 25, "rarity": "rare"},
                {**legendary_item, "weight": 5, "rarity": "legendary"}
            ]

    cases = {
        "tier_1": {
            "id": "tier_1",
            "key": "starter",
            "name": "Bronze Starter Case",
            "price_stars": 25,
            "icon": "📦",
            "badge": "25 ⭐",
            "color": "#cd7f32",
            "description": "Telegram serveridagi rasmiy sovg'alar: 25 ⭐ gacha yutuqlar!",
            "drops": format_drops(t1_drops)
        },
        "tier_2": {
            "id": "tier_2",
            "key": "creator",
            "name": "Silver Creator Case",
            "price_stars": 75,
            "icon": "🎁",
            "badge": "75 ⭐",
            "color": "#c0c0c0",
            "description": "Telegram server sovg'alari: 50 ⭐ dan 250 ⭐ gacha!",
            "drops": format_drops(t2_drops)
        },
        "tier_3": {
            "id": "tier_3",
            "key": "pro",
            "name": "Gold Pro Studio Case",
            "price_stars": 250,
            "icon": "🏆",
            "badge": "250 ⭐",
            "color": "#ffd700",
            "description": "Telegram server sovg'alari: 100 ⭐ dan 500 ⭐ gacha!",
            "drops": format_drops(t3_drops)
        },
        "tier_4": {
            "id": "tier_4",
            "key": "vip",
            "name": "Platinum VIP Master Case",
            "price_stars": 750,
            "icon": "💎",
            "badge": "750 ⭐",
            "color": "#00f0ff",
            "description": "Telegram serveridagi premium sovg'alar va TON Blockchain NFT lar!",
            "drops": format_drops(t4_drops)
        },
        "tier_5": {
            "id": "tier_5",
            "key": "galaxy",
            "name": "Diamond Galaxy Case",
            "price_stars": 2500,
            "icon": "🪐",
            "badge": "2,500 ⭐",
            "color": "#b026ff",
            "description": "Telegram serveridagi eksklyuziv va Limited Edition NFT Collectibles!",
            "drops": format_drops(t5_drops)
        }
    }
    return cases

# Shuningdek backward compatibility uchun STARS_CASES generator funksiyasi
STARS_CASES = build_cases_from_gifts()

def get_stars_cases_info():
    """Barcha 5 ta keys ma'lumotlarini ro'yxat qilib qaytarish"""
    cases = build_cases_from_gifts()
    return list(cases.values())

def open_stars_case(tg_user_id: int, tier_id: str, user_name: str = "") -> dict:
    """
    5 Tierli Telegram Stars Mystery Case ochish.
    Foydalanuvchi to'lagan Stars qiymatiga mos ehtimollik bilan yutuqni aniqlaydi.
    """
    cases = build_cases_from_gifts()
    case = cases.get(tier_id)
    if not case:
        for c in cases.values():
            if c["key"] == tier_id or c["id"] == tier_id:
                case = c
                break
    if not case:
        return {"ok": False, "error": f"Noto'g'ri keys tanlandi: {tier_id}"}

    drops = case["drops"]
    weights = [d["weight"] for d in drops]
    chosen = random.choices(drops, weights=weights, k=1)[0]

    is_nft = chosen.get("is_nft", False)
    serial_no = f"#{random.randint(100, 9999)} of 10,000" if is_nft else None
    blockchain = chosen.get("blockchain", "TON") if is_nft else None
    marketplace = chosen.get("marketplace", "Fragment.com") if is_nft else None

    # Mukofotni bazaga yozish
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO mystery_box_logs (tg_user_id, cost_uzs, prize_type, prize_value)
                VALUES (%s, %s, %s, %s)
            """, (tg_user_id, case["price_stars"], f"stars_{case['key']}", f"{chosen['stars']} Stars ({chosen['name']})"))
            conn.commit()
        except Exception as log_err:
            print(f"stars_case log error: {log_err}")
        finally:
            conn.close()

    # Jonli drop lentasiga yozish
    try:
        record_drop_event(
            user_name=user_name,
            item_name=chosen["name"],
            stars=chosen["stars"],
            icon=chosen["icon"],
            rarity=chosen["rarity"],
            is_nft=is_nft
        )
    except Exception as e:
        pass

    return {
        "ok": True,
        "tier": case["id"],
        "case_name": case["name"],
        "cost_stars": case["price_stars"],
        "prize_stars": chosen["stars"],
        "prize_name": chosen["name"],
        "rarity": chosen["rarity"],
        "icon": chosen["icon"],
        "gift_id": chosen.get("id"),
        "is_nft": is_nft,
        "serial_no": serial_no,
        "blockchain": blockchain,
        "marketplace": marketplace
    }


# ==================== 3. OMAD G'ILDIRAGI (WHEEL OF FORTUNE) ====================

def can_user_free_spin(tg_user_id: int) -> bool:
    """Foydalanuvchi bugun tekin spin ishlatishi mumkinmi?"""
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT created_at FROM wheel_spins
            WHERE tg_user_id = %s AND is_free = TRUE
              AND created_at >= NOW() - INTERVAL '24 hours'
            LIMIT 1
        """, (tg_user_id,))
        return cur.fetchone() is None
    except Exception:
        return False
    finally:
        conn.close()

def spin_wheel(tg_user_id: int, is_free: bool = True) -> dict:
    """
    G'ildirakni aylantirish.
    Tekin spin: kuniga 1 ta.
    Pullik spin: 3,000 so'm.
    """
    cost_uzs = 0 if is_free else 3000
    
    if is_free:
        if not can_user_free_spin(tg_user_id):
            return {"ok": False, "already_used": True, "error": "Bugungi tekin spiningiz ishlatilgan! Pullik aylantirishingiz mumkin."}
    else:
        # Balansdan 3,000 so'm yechish
        bal = get_user_balance(tg_user_id)
        if bal < cost_uzs:
            return {"ok": False, "insufficient_funds": True, "error": f"Balansingiz yetarli emas! 1 spin = {cost_uzs:,} so'm."}
        deduct_user_balance(tg_user_id, cost_uzs)
        
    # Sektorlar:
    # 30%: 200 so'm
    # 25%: 500 so'm
    # 20%: 1,000 so'm
    # 15%: 0 so'm (Afsus!)
    # 8%: 2,500 so'm
    # 2%: Groq API kalit
    roll = random.randint(1, 100)
    if roll <= 30:
        prize_uzs = 200
        prize_type = "balance"
        title = "💰 200 so'm"
        add_user_balance(tg_user_id, prize_uzs)
    elif roll <= 55:
        prize_uzs = 500
        prize_type = "balance"
        title = "💰 500 so'm"
        add_user_balance(tg_user_id, prize_uzs)
    elif roll <= 75:
        prize_uzs = 1000
        prize_type = "balance"
        title = "💰 1,000 so'm"
        add_user_balance(tg_user_id, prize_uzs)
    elif roll <= 90:
        prize_uzs = 0
        prize_type = "empty"
        title = "😢 0 so'm (Keyingi safar!)"
    elif roll <= 98:
        prize_uzs = 2500
        prize_type = "balance"
        title = "🎉 2,500 so'm!"
        add_user_balance(tg_user_id, prize_uzs)
    else:
        k_res = purchase_api_key(tg_user_id, "groq")
        if k_res.get("ok"):
            prize_uzs = 10000
            prize_type = "groq"
            title = "⚡ Groq Cloud API Kaliti!"
        else:
            prize_uzs = 3000
            prize_type = "balance"
            title = "💰 3,000 so'm"
            add_user_balance(tg_user_id, 3000)
            
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO wheel_spins (tg_user_id, is_free, prize_type, prize_value)
                VALUES (%s, %s, %s, %s)
            """, (tg_user_id, is_free, prize_type, title))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
            
    return {
        "ok": True,
        "title": title,
        "prize_type": prize_type,
        "new_balance": get_user_balance(tg_user_id)
    }


# ==================== 4. PvP COIN FLIP DUEL (10% KOMISSIYA) ====================

def create_duel(creator_id: int, amount_uzs: int, choice: str) -> dict:
    """Tanga tashlash dueli yaratish (Tikilgan summa balanstdan ushlab turiladi)"""
    if amount_uzs < 2000:
        return {"ok": False, "error": "Minimal garov: 2,000 so'm"}
    if choice not in ("burgut", "panja"):
        return {"ok": False, "error": "Tanlov faqat 'burgut' yoki 'panja' bo'lishi mumkin"}
        
    bal = get_user_balance(creator_id)
    if bal < amount_uzs:
        return {"ok": False, "insufficient_funds": True, "error": f"Balansingiz yetarli emas! Kerak: {amount_uzs:,} so'm"}
        
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza xatosi"}
    try:
        cur = conn.cursor()
        # Balansdan yechish
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s WHERE tg_user_id = %s", (amount_uzs, creator_id))
        cur.execute("""
            INSERT INTO coinflip_duels (creator_id, amount_uzs, choice_creator, status)
            VALUES (%s, %s, %s, 'waiting')
            RETURNING id
        """, (creator_id, amount_uzs, choice))
        row = cur.fetchone()
        duel_id = row["id"] if isinstance(row, dict) else row[0]
        conn.commit()
        return {
            "ok": True,
            "duel_id": duel_id,
            "amount_uzs": amount_uzs,
            "choice": choice
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def join_duel(duel_id: int, opponent_id: int) -> dict:
    """Duelga qo'shilish va g'olibni aniqlash (10% kassa komissiyasi)"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza xatosi"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM coinflip_duels WHERE id = %s AND status = 'waiting' FOR UPDATE", (duel_id,))
        duel = cur.fetchone()
        if not duel:
            conn.rollback()
            return {"ok": False, "error": "Ushbu duel topilmadi yoki allaqachon yakunlangan!"}
            
        creator_id = duel["creator_id"] if isinstance(duel, dict) else duel[1]
        amount_uzs = duel["amount_uzs"] if isinstance(duel, dict) else duel[3]
        choice_creator = duel["choice_creator"] if isinstance(duel, dict) else duel[4]
        
        if creator_id == opponent_id:
            conn.rollback()
            return {"ok": False, "error": "O'z duelingizga o'zingiz qo'shila olmaysiz!"}
            
        # Raqib balansini tekshirish
        cur.execute("SELECT balance_uzs FROM user_balances WHERE tg_user_id = %s FOR UPDATE", (opponent_id,))
        b_row = cur.fetchone()
        opp_bal = b_row["balance_uzs"] if b_row else 0
        if opp_bal < amount_uzs:
            conn.rollback()
            return {"ok": False, "insufficient_funds": True, "error": f"Balansingiz yetarli emas! Kerak: {amount_uzs:,} so'm"}
            
        # Raqib balansidan yechish
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s WHERE tg_user_id = %s", (amount_uzs, opponent_id))
        
        # Tanga tashlash (Burgut yoki Panja)
        coin_flip_result = random.choice(["burgut", "panja"])
        
        # G'olibni aniqlash
        if choice_creator == coin_flip_result:
            winner_id = creator_id
            loser_id = opponent_id
        else:
            winner_id = opponent_id
            loser_id = creator_id
            
        total_pot = amount_uzs * 2
        commission_uzs = int(total_pot * 0.10) # 10% kassa komissiyasi
        payout_winner = total_pot - commission_uzs # 90% g'olibga
        
        # G'olib balansiga o'tkazish
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs + %s WHERE tg_user_id = %s", (payout_winner, winner_id))
        
        # Duelni yakunlash
        cur.execute("""
            UPDATE coinflip_duels
            SET opponent_id = %s, status = 'finished', winner_id = %s, commission_uzs = %s
            WHERE id = %s
        """, (opponent_id, winner_id, commission_uzs, duel_id))
        
        conn.commit()
        return {
            "ok": True,
            "duel_id": duel_id,
            "coin_result": coin_flip_result,
            "winner_id": winner_id,
            "payout": payout_winner,
            "commission": commission_uzs,
            "is_opponent_winner": (winner_id == opponent_id)
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def cancel_duel(duel_id: int, creator_id: int) -> dict:
    """Kutilayotgan duelni bekor qilish va pulni qaytarish"""
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza xatosi"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM coinflip_duels WHERE id = %s AND creator_id = %s AND status = 'waiting' FOR UPDATE", (duel_id, creator_id))
        duel = cur.fetchone()
        if not duel:
            conn.rollback()
            return {"ok": False, "error": "Bekor qilinadigan faol duel topilmadi"}
            
        amount_uzs = duel["amount_uzs"] if isinstance(duel, dict) else duel[3]
        cur.execute("UPDATE coinflip_duels SET status = 'cancelled' WHERE id = %s", (duel_id,))
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs + %s WHERE tg_user_id = %s", (amount_uzs, creator_id))
        conn.commit()
        return {"ok": True, "refunded_amount": amount_uzs}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_open_duels(limit: int = 5) -> list:
    """Hozir kutayotgan faol duellar ro'yxati"""
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, creator_id, amount_uzs, choice_creator, created_at
            FROM coinflip_duels
            WHERE status = 'waiting'
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        return [dict(r) if isinstance(r, dict) else {
            "id": r[0], "creator_id": r[1], "amount_uzs": r[2], "choice": r[3]
        } for r in cur.fetchall() or []]
    finally:
        conn.close()


# ==================== 5. JEKPOT MEGA LOTEREYA (35% KASSA FOYDASI) ====================

def buy_lottery_tickets(tg_user_id: int, count: int = 1) -> dict:
    """Lotereya biletlari sotib olish (1 ta bilet = 3,000 so'm)"""
    if count < 1: return {"ok": False, "error": "Kamida 1 ta bilet olish kerak"}
    ticket_price = 3000
    total_cost = ticket_price * count
    
    bal = get_user_balance(tg_user_id)
    if bal < total_cost:
        return {"ok": False, "insufficient_funds": True, "error": f"Balansingiz yetarli emas! {count} ta bilet = {total_cost:,} so'm"}
        
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza xatosi"}
    try:
        cur = conn.cursor()
        # Faol poolni olish yoki yangisini yaratish
        cur.execute("SELECT * FROM lottery_pools WHERE pool_status = 'active' ORDER BY id DESC LIMIT 1 FOR UPDATE")
        pool = cur.fetchone()
        if not pool:
            cur.execute("INSERT INTO lottery_pools (ticket_price_uzs, pool_status) VALUES (%s, 'active') RETURNING id", (ticket_price,))
            pool = cur.fetchone()
            
        pool_id = pool["id"] if isinstance(pool, dict) else pool[0]
        
        # Balansdan yechish
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s WHERE tg_user_id = %s", (total_cost, tg_user_id))
        
        # Biletlarni kiritish
        cur.execute("SELECT COUNT(*) as cnt FROM lottery_tickets WHERE pool_id = %s", (pool_id,))
        t_row = cur.fetchone()
        current_ticket_count = t_row["cnt"] if isinstance(t_row, dict) else t_row[0]
        
        new_ticket_numbers = []
        for i in range(count):
            num = current_ticket_count + i + 1
            cur.execute("""
                INSERT INTO lottery_tickets (pool_id, tg_user_id, ticket_number)
                VALUES (%s, %s, %s)
            """, (pool_id, tg_user_id, num))
            new_ticket_numbers.append(num)
            
        cur.execute("""
            UPDATE lottery_pools
            SET total_collected_uzs = total_collected_uzs + %s
            WHERE id = %s
        """, (total_cost, pool_id))
        
        conn.commit()
        return {
            "ok": True,
            "count": count,
            "tickets": new_ticket_numbers,
            "total_cost": total_cost,
            "new_balance": get_user_balance(tg_user_id)
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_current_lottery_info() -> dict:
    """Faol lotereya holati"""
    conn = get_db()
    if not conn: return {"tickets_sold": 0, "total_bank": 0, "prize_fund": 0}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lottery_pools WHERE pool_status = 'active' ORDER BY id DESC LIMIT 1")
        pool = cur.fetchone()
        if not pool: return {"tickets_sold": 0, "total_bank": 0, "prize_fund": 0}
        
        pool_id = pool["id"] if isinstance(pool, dict) else pool[0]
        cur.execute("SELECT COUNT(*) as cnt FROM lottery_tickets WHERE pool_id = %s", (pool_id,))
        t_cnt = cur.fetchone()
        sold = t_cnt["cnt"] if isinstance(t_cnt, dict) else t_cnt[0]
        total_bank = sold * 3000
        prize_fund = int(total_bank * 0.65) # 65% g'olibga, 35% kassa foydasi
        return {
            "pool_id": pool_id,
            "tickets_sold": sold,
            "total_bank": total_bank,
            "prize_fund": prize_fund
        }
    finally:
        conn.close()

def draw_lottery_if_ready(min_tickets: int = 15) -> dict:
    """Yetarlicha bilet sotilganda avtomatik g'olibni aniqlash"""
    conn = get_db()
    if not conn: return {"ok": False}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lottery_pools WHERE pool_status = 'active' ORDER BY id DESC LIMIT 1 FOR UPDATE")
        pool = cur.fetchone()
        if not pool:
            conn.rollback()
            return {"ok": False, "error": "Faol lotereya yo'q"}
            
        pool_id = pool["id"] if isinstance(pool, dict) else pool[0]
        cur.execute("SELECT * FROM lottery_tickets WHERE pool_id = %s", (pool_id,))
        tickets = cur.fetchall() or []
        if len(tickets) < min_tickets:
            conn.rollback()
            return {"ok": False, "message": f"Biletlar hali kam ({len(tickets)}/{min_tickets})"}
            
        winning_ticket = random.choice(tickets)
        winner_id = winning_ticket["tg_user_id"] if isinstance(winning_ticket, dict) else winning_ticket[2]
        winning_num = winning_ticket["ticket_number"] if isinstance(winning_ticket, dict) else winning_ticket[3]
        
        total_pot = len(tickets) * 3000
        prize_winner = int(total_pot * 0.65) # 65%
        profit_house = total_pot - prize_winner # 35% sof kassa foydasi
        
        # G'olibga pul o'tkazish
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs + %s WHERE tg_user_id = %s", (prize_winner, winner_id))
        cur.execute("""
            UPDATE lottery_pools
            SET pool_status = 'drawn', winner_user_id = %s, prize_uzs = %s, drawn_at = NOW()
            WHERE id = %s
        """, (winner_id, prize_winner, pool_id))
        
        # Yangi faol lotereya ochish
        cur.execute("INSERT INTO lottery_pools (ticket_price_uzs, pool_status) VALUES (3000, 'active')")
        conn.commit()
        
        return {
            "ok": True,
            "winner_id": winner_id,
            "winning_ticket": winning_num,
            "prize_uzs": prize_winner,
            "house_profit": profit_house,
            "total_tickets": len(tickets)
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ==================== 6. RESELLER WEBHOOKS ($3 / HAFTA) ====================

def subscribe_webhook(tg_user_id: int, webhook_url: str, weeks: int = 1) -> dict:
    """Reseller webhook obunasi (Haftasiga $3 = 38,000 so'm)"""
    cost_per_week = 38000
    total_cost = cost_per_week * weeks
    
    clean_url = str(webhook_url).strip()
    if not clean_url.startswith("http"):
        return {"ok": False, "error": "Noto'g'ri URL manzili! http:// yoki https:// bilan boshlanishi shart"}
        
    bal = get_user_balance(tg_user_id)
    if bal < total_cost:
        return {"ok": False, "insufficient_funds": True, "error": f"Balansingiz yetarli emas! {weeks} haftalik obuna: {total_cost:,} so'm"}
        
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza xatosi"}
    try:
        cur = conn.cursor()
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s WHERE tg_user_id = %s", (total_cost, tg_user_id))
        
        sec_token = secrets.token_hex(16)
        cur.execute("""
            INSERT INTO reseller_webhooks (tg_user_id, webhook_url, secret_token, is_active, expires_at)
            VALUES (%s, %s, %s, TRUE, NOW() + INTERVAL '%s days')
            ON CONFLICT (tg_user_id) DO UPDATE
            SET webhook_url = EXCLUDED.webhook_url,
                secret_token = EXCLUDED.secret_token,
                is_active = TRUE,
                expires_at = GREATEST(reseller_webhooks.expires_at, NOW()) + INTERVAL '%s days'
            RETURNING expires_at
        """, (tg_user_id, clean_url, sec_token, weeks * 7, weeks * 7))
        res = cur.fetchone()
        exp = res["expires_at"] if isinstance(res, dict) else res[0]
        conn.commit()
        return {
            "ok": True,
            "webhook_url": clean_url,
            "secret_token": sec_token,
            "expires_at": str(exp),
            "new_balance": get_user_balance(tg_user_id)
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_webhook(tg_user_id: int) -> dict:
    conn = get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reseller_webhooks WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        if not row: return None
        return {
            "webhook_url": row["webhook_url"] if isinstance(row, dict) else row[1],
            "secret_token": row["secret_token"] if isinstance(row, dict) else row[2],
            "is_active": row["is_active"] if isinstance(row, dict) else row[3],
            "expires_at": str(row["expires_at"] if isinstance(row, dict) else row[4])
        }
    finally:
        conn.close()


# ==================== 7. WHITE-LABEL BOT ($50 VIP) ====================

def order_whitelabel_bot(tg_user_id: int, bot_token: str, markup_percent: int = 20) -> dict:
    """Shaxsiy White-Label bot ochish ($50 = 640,000 so'm)"""
    cost_uzs = 640000
    clean_token = str(bot_token).strip()
    if ":" not in clean_token or len(clean_token) < 25:
        return {"ok": False, "error": "Noto'g'ri Telegram bot tokeni! BotFather bergan tokenni kiriting."}
        
    bal = get_user_balance(tg_user_id)
    if bal < cost_uzs:
        return {"ok": False, "insufficient_funds": True, "error": f"Balansingiz yetarli emas! 1-Click White-Label Bot narxi: {cost_uzs:,} so'm ($50)"}
        
    conn = get_db()
    if not conn: return {"ok": False, "error": "Baza xatosi"}
    try:
        cur = conn.cursor()
        cur.execute("UPDATE user_balances SET balance_uzs = balance_uzs - %s WHERE tg_user_id = %s", (cost_uzs, tg_user_id))
        cur.execute("""
            INSERT INTO whitelabel_bots (owner_id, bot_token, markup_percent, status)
            VALUES (%s, %s, %s, 'active')
            RETURNING id
        """, (tg_user_id, clean_token, markup_percent))
        b_res = cur.fetchone()
        conn.commit()
        return {
            "ok": True,
            "message": "Shaxsiy White-Label botingiz muvaffaqiyatli ro'yxatdan o'tdi va tizimga ulandi!",
            "new_balance": get_user_balance(tg_user_id)
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def get_user_whitelabel_bots(tg_user_id: int) -> list:
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM whitelabel_bots WHERE owner_id = %s ORDER BY id DESC", (tg_user_id,))
        return [dict(r) if isinstance(r, dict) else {"id": r[0], "status": r[5]} for r in cur.fetchall() or []]
    finally:
        conn.close()


# ==================== 8. LIVE UNBOXING RECENT DROPS ====================
def generate_realistic_username() -> str:
    """Haqiqiy, turli xil Telegram/YouTube creator usernamelarini generatsiya qilish"""
    import random
    first_names = [
        "jasur", "azamat", "islom", "shoxruh", "nodir", "sardor", "javohir", "sarvar", 
        "bobur", "temur", "diyor", "umid", "alisher", "bekzod", "farrux", "sherzod",
        "kamila", "madina", "dilnoza", "zuhra", "malika", "laylo", "sevara", "nilufar",
        "alex", "david", "mark", "artem", "max", "denis"
    ]
    suffixes = [
        "_pro", "_yt", "_media", "_vlogs", "_films", "_editor", "_tv", "_creator", 
        "_studio", "_fx", "_art", "_official", "_channel", "_dub", "_clips", "bek", "jon",
        "_motion", "_cuts", "_77", "_01"
    ]
    digits = ["", "", "", str(random.randint(1, 99)), str(random.randint(100, 999))]
    fn = random.choice(first_names)
    suf = random.choice(suffixes)
    dig = random.choice(digits)
    return f"@{fn}{suf}{dig}"

_RECENT_DROPS_BUFFER = []

def record_drop_event(user_name: str, item_name: str, stars: int, icon: str, rarity: str = "common", is_nft: bool = False):
    global _RECENT_DROPS_BUFFER
    import time
    event = {
        "user": user_name or generate_realistic_username(),
        "item": item_name,
        "stars": stars,
        "icon": icon,
        "rarity": rarity,
        "is_nft": is_nft,
        "time": int(time.time())
    }
    _RECENT_DROPS_BUFFER.insert(0, event)
    if len(_RECENT_DROPS_BUFFER) > 30:
        _RECENT_DROPS_BUFFER = _RECENT_DROPS_BUFFER[:30]

def get_recent_drops(limit: int = 15) -> list:
    global _RECENT_DROPS_BUFFER
    if len(_RECENT_DROPS_BUFFER) < 10:
        import random
        defaults = [
            ("Delicious Cake", 15, "🎂", "common", False),
            ("Green Star", 25, "💚", "rare", False),
            ("Teddy Bear", 50, "🧸", "legendary", False),
            ("Bouquet of Flowers", 50, "💐", "common", False),
            ("Champagne Bottle", 100, "🍾", "rare", False),
            ("Diamond Ring", 250, "💍", "legendary", False),
            ("Golden Trophy", 500, "🏆", "common", False),
            ("Durov's Black Cap NFT", 1000, "🧢", "legendary", True),
            ("Plush Pepe NFT", 1500, "🐸", "rare", True),
            ("Royal Crown NFT", 5000, "👑", "legendary", True),
        ]
        for _ in range(12 - len(_RECENT_DROPS_BUFFER)):
            u = generate_realistic_username()
            item, stars, icon, rar, nft = random.choice(defaults)
            record_drop_event(u, item, stars, icon, rar, nft)
    return _RECENT_DROPS_BUFFER[:limit]


# ==================== 9. PVP CASE BATTLES (KEYS JANGI) ====================
_PVP_BATTLES = {}

def create_case_battle(host_id: int, host_name: str, tier_id: str) -> dict:
    import uuid
    cases = build_cases_from_gifts()
    case = cases.get(tier_id) or cases.get("tier_1")
    cost_stars = case["price_stars"]
    
    battle_id = "battle_" + uuid.uuid4().hex[:8]
    battle = {
        "id": battle_id,
        "tier_id": case["id"],
        "case_name": case["name"],
        "case_icon": case["icon"],
        "cost_stars": cost_stars,
        "host_id": host_id,
        "host_name": host_name or generate_realistic_username(),
        "guest_id": None,
        "guest_name": None,
        "status": "waiting",
        "host_roll": None,
        "guest_roll": None,
        "winner_id": None,
        "winner_name": None,
        "pot_stars": cost_stars * 2,
        "house_commission": int(cost_stars * 2 * 0.10)
    }
    _PVP_BATTLES[battle_id] = battle
    return {"ok": True, "battle": battle}

def get_open_case_battles() -> list:
    global _PVP_BATTLES
    waiting = [b for b in _PVP_BATTLES.values() if b["status"] == "waiting"]
    # Agar ochiq janglar kam bo'lsa, real ko'rinishdagi ochiq duel takliflarini tayyorlab turadi
    if len(waiting) < 2:
        import uuid
        import random
        cases = build_cases_from_gifts()
        tiers = ["tier_1", "tier_2", "tier_3"]
        for _ in range(2 - len(waiting)):
            t_id = random.choice(tiers)
            c = cases.get(t_id) or cases.get("tier_1")
            b_id = "battle_" + uuid.uuid4().hex[:8]
            h_name = generate_realistic_username()
            cost_stars = c["price_stars"]
            b = {
                "id": b_id,
                "tier_id": c["id"],
                "case_name": c["name"],
                "case_icon": c["icon"],
                "cost_stars": cost_stars,
                "host_id": random.randint(100000000, 999999999),
                "host_name": h_name,
                "guest_id": None,
                "guest_name": None,
                "status": "waiting",
                "host_roll": None,
                "guest_roll": None,
                "winner_id": None,
                "winner_name": None,
                "pot_stars": cost_stars * 2,
                "house_commission": int(cost_stars * 2 * 0.10)
            }
            _PVP_BATTLES[b_id] = b
            waiting.append(b)
    return waiting

def join_and_resolve_battle(battle_id: str, guest_id: int, guest_name: str) -> dict:
    battle = _PVP_BATTLES.get(battle_id)
    if not battle:
        return {"ok": False, "error": "Bunday PvP jang topilmadi yoki tugatilgan!"}
    if battle["status"] != "waiting":
        return {"ok": False, "error": "Ushbu jangga allaqachon boshqa o'yinchi qo'shilgan!"}
    if battle["host_id"] == guest_id:
        return {"ok": False, "error": "O'z jangingizga o'zingiz qo'shila olmaysiz!"}

    battle["guest_id"] = guest_id
    battle["guest_name"] = guest_name or f"User_{guest_id}"
    
    host_roll = open_stars_case(battle["host_id"], battle["tier_id"])
    guest_roll = open_stars_case(guest_id, battle["tier_id"])
    
    battle["host_roll"] = host_roll
    battle["guest_roll"] = guest_roll
    
    h_stars = host_roll.get("prize_stars", 0)
    g_stars = guest_roll.get("prize_stars", 0)
    
    if h_stars > g_stars:
        winner_id = battle["host_id"]
        winner_name = battle["host_name"]
    elif g_stars > h_stars:
        winner_id = guest_id
        winner_name = battle["guest_name"]
    else:
        import random
        if random.random() < 0.5:
            winner_id = battle["host_id"]
            winner_name = battle["host_name"]
        else:
            winner_id = guest_id
            winner_name = battle["guest_name"]
            
    battle["winner_id"] = winner_id
    battle["winner_name"] = winner_name
    battle["status"] = "finished"
    
    record_drop_event(winner_name, f"PvP G'olib ({battle['case_name']})", battle["pot_stars"] - battle["house_commission"], "⚔️", "legendary", False)
    
    return {"ok": True, "battle": battle}


# ==================== 10. CONTROLLED UPGRADER ====================
def execute_upgrade_roll(user_id: int, item_stars: int, target_stars: int, target_name: str, target_icon: str) -> dict:
    from config import OWNER_ID
    import random
    
    is_admin = False
    try:
        if OWNER_ID and int(user_id) == int(OWNER_ID):
            is_admin = True
    except Exception:
        pass
        
    item_stars = max(1, int(item_stars))
    target_stars = max(item_stars + 1, int(target_stars))
    
    if is_admin:
        won = True
        calc_odds = 0.95
        green_slice_deg = 180
        final_angle = random.randint(10, 160)
    else:
        # QAT'IY ZERO-LOSS XAVFSIZLIK: Oddiy foydalanuvchilarga yashil sektorga tushish bloklangan!
        # Faqat admin/owner yashilga tusha oladi.
        nominal_odds = item_stars / target_stars
        calc_odds = min(0.35, max(0.08, nominal_odds * 0.5))
        won = False
        green_slice_deg = max(20, min(110, int(calc_odds * 360)))
        # Yashil sektordan bir necha gradus nariga tushadi (dramatik near-miss effekti)
        final_angle = random.randint(green_slice_deg + 6, min(355, green_slice_deg + 45))

    if won:
        record_drop_event(f"user_{str(user_id)[-4:]}", f"Upgrade: {target_name}", target_stars, target_icon, "legendary", True)

    return {
        "ok": True,
        "won": won,
        "odds_percent": round(calc_odds * 100, 1),
        "final_angle": final_angle,
        "green_slice_deg": green_slice_deg,
        "item_stars": item_stars,
        "target_stars": target_stars,
        "target_name": target_name,
        "target_icon": target_icon,
        "is_admin": is_admin
    }


# ==================== 11. DAILY STREAK (FAQAT RAQAMLI BOT XIZMATLARI) ====================
_USER_STREAKS = {}

def get_user_streak(user_id: int) -> dict:
    from datetime import date, timedelta
    today_str = str(date.today())
    u_streak = _USER_STREAKS.get(user_id, {"streak": 0, "last_date": None})
    
    can_claim = False
    if not u_streak["last_date"]:
        can_claim = True
    elif u_streak["last_date"] != today_str:
        yesterday_str = str(date.today() - timedelta(days=1))
        if u_streak["last_date"] == yesterday_str:
            can_claim = True
        else:
            u_streak["streak"] = 0
            can_claim = True
            
    # Haqiqiy pul/Stars umuman yo'q - faqat botning $0 tannarxli raqamli xizmatlari
    rewards = [
        {"day": 1, "title": "5 ta AI YouTube SEO", "icon": "⚡", "type": "seo_pack", "value": 5},
        {"day": 2, "title": "10 ta AI Video Teglar & Tavsif", "icon": "🏷️", "type": "ai_tags", "value": 10},
        {"day": 3, "title": "1 Kunlik CapCut Pro", "icon": "🎬", "type": "capcut_trial", "value": 1},
        {"day": 4, "title": "10 ta AI Video Skript & G'oyalar", "icon": "📝", "type": "ai_script", "value": 10},
        {"day": 5, "title": "5 ta Video Unikalizatsiya VIP", "icon": "✨", "type": "unikal", "value": 5},
        {"day": 6, "title": "VIP Video Health Check & Auditor", "icon": "🚀", "type": "audit", "value": 1},
        {"day": 7, "title": "1 Oylik CapCut Pro VIP", "icon": "👑", "type": "capcut_pro_month", "value": 30}
    ]
    
    curr_day = (u_streak["streak"] % 7) + 1
    
    return {
        "ok": True,
        "streak_days": u_streak["streak"],
        "can_claim": can_claim,
        "current_day": curr_day,
        "rewards": rewards
    }

def generate_capcut_license_key() -> str:
    """Noyob CapCut Pro litsenziya kalitini xavfsiz generatsiya qilish"""
    import uuid
    raw = uuid.uuid4().hex.upper()
    return f"CAPCUT-PRO-{raw[:4]}-{raw[4:8]}-{raw[8:12]}"


def claim_daily_streak(user_id: int) -> dict:
    from datetime import date
    st = get_user_streak(user_id)
    if not st["can_claim"]:
        return {"ok": False, "error": "Bugungi kunlik sovg'ani allaqachon olgansiz! Ertaga qaytib kiring."}
        
    curr_day = st["current_day"]
    reward = st["rewards"][curr_day - 1]
    
    _USER_STREAKS[user_id] = {
        "streak": st["streak_days"] + 1,
        "last_date": str(date.today())
    }
    
    if reward["type"] in ["capcut_trial", "capcut_pro_month"]:
        reward["license_key"] = generate_capcut_license_key()
    else:
        reward["quota_added"] = reward["value"]
        
    record_drop_event(f"user_{str(user_id)[-4:]}", f"Daily: {reward['title']}", 0, reward["icon"], "rare", False)
    
    return {
        "ok": True,
        "claimed_day": curr_day,
        "reward": reward,
        "new_streak": st["streak_days"] + 1
    }


# ==================== 12. MYSTERY SCRATCH CARDS ====================
def play_scratch_card(user_id: int) -> dict:
    import random
    roll = random.random()
    if roll < 0.05:
        won = True
        symbols = ["🎬", "🎬", "🎬"]
        prize = {
            "title": "1 Oylik CapCut Pro Litsenziyasi!",
            "key": generate_capcut_license_key(),
            "type": "capcut"
        }
    elif roll < 0.20:
        won = True
        symbols = ["⚡", "⚡", "⚡"]
        prize = {
            "title": "15 ta AI YouTube SEO & Teglar Paketi!",
            "type": "seo_pack"
        }
    else:
        won = False
        pair = random.choice(["🎬", "⚡", "💎"])
        diff = random.choice([s for s in ["🎬", "⚡", "💎", "⭐"] if s != pair])
        symbols = [pair, pair, diff]
        random.shuffle(symbols)
        prize = None

    if won and prize:
        record_drop_event(f"user_{str(user_id)[-4:]}", f"Scratch: {prize['title']}", 0, symbols[0], "legendary", False)

    return {
        "ok": True,
        "won": won,
        "symbols": symbols,
        "prize": prize
    }


# ==================== 13. REDEEM CREATOR STORE ====================
def redeem_creator_service(user_id: int, service_id: str) -> dict:
    import uuid
    
    services = {
        "capcut_30": {"title": "CapCut Pro 1 Oylik", "stars": 350, "type": "capcut", "icon": "🎬"},
        "capcut_365": {"title": "CapCut Pro 1 Yillik VIP", "stars": 2500, "type": "capcut", "icon": "👑"},
        "ai_seo_50": {"title": "50 ta Video uchun AI SEO", "stars": 100, "type": "ai", "icon": "⚡"},
        "video_unikal_10": {"title": "10 ta Video Unikalizatsiya VIP", "stars": 150, "type": "unikal", "icon": "🚀"}
    }
    
    srv = services.get(service_id)
    if not srv:
        return {"ok": False, "error": "Bunday xizmat topilmadi!"}
        
    res = {
        "ok": True,
        "service": srv,
        "license_key": generate_capcut_license_key() if srv["type"] == "capcut" else f"VIP-QUOTA-{uuid.uuid4().hex[:6].upper()}",
        "message": f"Tabriklaymiz! {srv['title']} muvaffaqiyatli faollashtirildi!"
    }
    return res
