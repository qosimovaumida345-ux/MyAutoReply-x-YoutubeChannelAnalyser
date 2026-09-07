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
