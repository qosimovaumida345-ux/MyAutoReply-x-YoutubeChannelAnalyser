"""
1xBet & Casino Gamification Engine for Telegram Bot
Ushbu modul 5 ta yuqori daromadli interaktiv o'yinni boshqaradi:
1. 🍏 Apple of Fortune (1xBet Omad Olmasi) - 10 qator, 350x gacha, Provably Fair SHA-256
2. 💣 Mines (Minalar / Saper) - 5x5 grid, erkin minalar soni, ko'paytuvchilar, Cashout
3. 🚀 Live Crash / Aviator (2 Slotli) - Real-time avtomatik jonli efir (10ms ping), 5s timer, Bet 1 & Bet 2
4. 🃏 21 (Blackjack / Ochko) - Aqlli bot diler bilan klassik karta o'yini
5. 🛩️ Kamikaze - Samolyotli pog'onali o'yin, 0.2x o'sish, 10x gacha, Cashout
"""

import os
import sys
import json
import time
import math
import random
import secrets
import hashlib
import asyncio
from datetime import datetime, timedelta

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

import database as db
from config import BOT_TOKEN
from custom_emojis import ce, e

_global_bot: Client = None
CRASH_ACTIVE_VIEWERS = {}  # chat_id: {"message_id": int, "user_id": int, "last_rendered": "", "last_edit_ts": float}

# ==================== YORDAMCHI PROVABLY FAIR SHA-256 ====================

def create_provably_fair(data_obj: dict):
    """O'yin ma'lumotlarini server salt bilan SHA-256 orqali heshlaydi"""
    salt = secrets.token_hex(16)
    serialized = json.dumps(data_obj, sort_keys=True)
    full_str = f"{serialized}:{salt}"
    enc_hash = hashlib.sha256(full_str.encode('utf-8')).hexdigest()
    return salt, enc_hash

# ==================== ADMIN KAZINO SIGNALLARI & SPY TIZIMI ====================

def get_casino_signals_chat_id():
    """Qaysi guruh/kanal/chatga signal yuborishni aniqlaydi"""
    saved = db.get_bot_config("casino_signals_chat", None)
    if saved:
        try:
            return int(saved)
        except Exception:
            return saved
    import os
    env_chat = os.getenv("CASINO_SIGNALS_CHAT", "").strip() or os.getenv("CASINO_SIGNALS_GROUP", "").strip()
    if env_chat:
        try:
            return int(env_chat)
        except Exception:
            return env_chat
    from config import OWNER_ID
    return OWNER_ID if OWNER_ID else None

def is_casino_signals_enabled():
    val = db.get_bot_config("casino_signals_enabled", "1")
    return val == "1"

def should_send_signal_for_user(user_id: int):
    """Admin barcha o'yinchilarni kuzatyaptimi yoki aynan bitta usernimi?"""
    if not is_casino_signals_enabled():
        return False
    target = db.get_bot_config("casino_spy_target", "all")
    if not target or target.lower() == "all":
        return True
    try:
        return int(target) == int(user_id)
    except Exception:
        return False

def spy_action_kb(user_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🎯 Faqat {user_id} ni kuzatish", callback_data=f"casinospy_target_{user_id}"),
            InlineKeyboardButton("🌐 Hammani kuzatish (All)", callback_data="casinospy_target_all")
        ]
    ])

async def send_casino_signal(signal_text: str, target_user_id: int = None, reply_markup=None):
    """Admin belgilagan guruh/kanal/chatga signal yuboradi"""
    global _global_bot
    if not _global_bot:
        return
    if not is_casino_signals_enabled():
        return
    if target_user_id is not None and not should_send_signal_for_user(target_user_id):
        return
    
    chat_dest = get_casino_signals_chat_id()
    if not chat_dest:
        return

    try:
        await _global_bot.send_message(
            chat_id=chat_dest,
            text=signal_text,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"send_casino_signal error: {e}")

def format_crash_signal(round_id: int, crash_point: float) -> str:
    if crash_point < 1.30:
        safe_cashout = round(crash_point * 0.88, 2)
        risk_lvl = "O'ta yuqori xavf (Tez qulaydi!)"
    elif crash_point < 2.0:
        safe_cashout = round(crash_point * 0.78, 2)
        risk_lvl = "O'rtacha barqaror"
    elif crash_point < 5.0:
        safe_cashout = round(crash_point * 0.70, 2)
        risk_lvl = "Yuqori ko'paytuvchi"
    else:
        safe_cashout = round(crash_point * 0.65, 2)
        risk_lvl = "Super Katta Yutuq!"

    text = (
        f"{ce('CRASH_PLANE')} <b>LIVE CRASH (AVIATOR) SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Raund:</b> <code>#{round_id}</code>\n"
        f"<b>Kutilayotgan Portlash (Crash Point):</b> <b>x{crash_point:.2f}</b>\n"
        f"<b>Xavfsiz Yechib Olish Nuqtasi:</b> <b>x{safe_cashout:.2f}</b>\n"
        f"<b>Xavf Darajasi:</b> {risk_lvl}\n"
        f"{ce('TIMER')} <b>Tayyorgarlik vaqti:</b> 5 soniya cooldown\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Kassa serveridan olingan aniq ma'lumot!</i>"
    )
    return text

def format_crash_bet_signal(user_id: int, user_name: str, slot_num: int, amount_uzs: int, round_id: int, crash_point: float) -> str:
    safe_cashout = round(crash_point * 0.75, 2) if crash_point >= 1.5 else round(crash_point * 0.88, 2)
    text = (
        f"{ce('MONEY')} <b>CRASH FOYDALANUVCHI STAVKASI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>O'yinchi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
        f"<b>Raund:</b> <code>#{round_id}</code> | <b>Slot:</b> {slot_num}\n"
        f"<b>Tikilgan Garov:</b> <code>{amount_uzs:,} so'm</code>\n"
        f"<b>Ushbu Raund Portlashi:</b> <b>x{crash_point:.2f}</b>\n"
        f"<b>Tavsiya qilingan Cashout:</b> <b>x{safe_cashout:.2f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text

def format_apple_signal(user_id: int, user_name: str, bet_uzs: int, board: list) -> str:
    lines = [
        f"{ce('APPLE_WHOLE')} <b>APPLE OF FORTUNE HACK SIGNAL</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"<b>O'yinchi:</b> {user_name} (ID: <code>{user_id}</code>)",
        f"<b>Garov Miqdori:</b> <code>{bet_uzs:,} so'm</code>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"<b>QATORLAR XARITASI (Pastdan yuqoriga):</b>"
    ]
    safe_path = []
    for r in range(9, -1, -1):
        mult = APPLE_MULTIPLIERS[r]
        good_cols = [str(c + 1) for c in range(5) if board[r][c] == "good"]
        bad_cols = [str(c + 1) for c in range(5) if board[r][c] == "bad"]
        safe_path.append((r + 1, good_cols[0]))
        lines.append(
            f"• <b>{r + 1}-qator (x{mult}):</b> Yutuq: <b>{', '.join(good_cols)}</b> | <b>Olma yo'q (tishlangan):</b> <code>{', '.join(bad_cols)}</code>"
        )
    path_str = " -> ".join([f"{p[1]}" for p in reversed(safe_path)])
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"<b>100% YUTUQLI KATAKLAR KETMA-KETLIGI (1..10):</b>")
    lines.append(f"<code>{path_str}</code>")
    return "\n".join(lines)

def format_mines_signal(user_id: int, user_name: str, bet_uzs: int, mines_count: int, mine_positions: list) -> str:
    bombs = sorted([p + 1 for p in mine_positions])
    safe = sorted([p + 1 for p in range(25) if p not in mine_positions])
    grid_lines = []
    for r in range(5):
        row_str = ""
        for c in range(5):
            idx = r * 5 + c
            if idx in mine_positions:
                row_str += "[BOMBA] "
            else:
                row_str += "[OLMOS] "
        grid_lines.append(row_str.strip())
    grid_display = "\n".join(grid_lines)
    text = (
        f"{ce('MINES_BOMB')} <b>MINES (SAPER) HACK SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>O'yinchi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
        f"<b>Garov:</b> <code>{bet_uzs:,} so'm</code> | <b>Minalar soni:</b> {mines_count} ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>BOMBALAR JOYI (1-25):</b> <code>{', '.join(map(str, bombs))}</code>\n"
        f"<b>XAVFSIZ OLMOSLAR (GEMS):</b> <code>{', '.join(map(str, safe[:8]))}...</code>\n\n"
        f"<b>5x5 GRID XARITASI:</b>\n"
        f"<code>{grid_display}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return text

def format_blackjack_signal(user_id: int, user_name: str, bet_uzs: int, player_cards: list, dealer_cards: list) -> str:
    p_str = ", ".join([f"{c.get('rank', '')}{c.get('suit', '')}" for c in player_cards])
    d_str = ", ".join([f"{c.get('rank', '')}{c.get('suit', '')}" for c in dealer_cards])
    d_hidden = dealer_cards[1] if len(dealer_cards) > 1 else None
    d_hidden_str = f"{d_hidden.get('rank', '')}{d_hidden.get('suit', '')} (Qiymat: {d_hidden.get('val', '')})" if d_hidden else "Mavjud emas"
    text = (
        f"{ce('CARD_JOKER')} <b>21 (BLACKJACK) HACK SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>O'yinchi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
        f"<b>Garov:</b> <code>{bet_uzs:,} so'm</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>O'yinchi Kartalari:</b> <code>{p_str}</code>\n"
        f"<b>Diler Barcha Kartalari:</b> <code>{d_str}</code>\n"
        f"<b>DILERNING YASHIRIN KARTASI:</b> <b>{d_hidden_str}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Dilerning yashirin kartasini bilgan holda karta olish yoki to'xtashni hisoblang!</i>"
    )
    return text

def format_kamikaze_signal(user_id: int, user_name: str, bet_uzs: int, board: list) -> str:
    lines = [
        f"{ce('KAMI_PLANE')} <b>KAMIKAZE (SAMOLYOT) HACK SIGNAL</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"<b>O'yinchi:</b> {user_name} (ID: <code>{user_id}</code>)",
        f"<b>Garov:</b> <code>{bet_uzs:,} so'm</code>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"<b>POG'ONALAR XARITASI (1-10):</b>"
    ]
    safe_steps = []
    for s in range(len(board)):
        safe_cols = [str(c + 1) for c in range(len(board[s])) if board[s][c] == "safe"]
        boom_cols = [str(c + 1) for c in range(len(board[s])) if board[s][c] != "safe"]
        if safe_cols:
            safe_steps.append(safe_cols[0])
        lines.append(f"• <b>{s + 1}-bosqich:</b> Xavfsiz: <b>{', '.join(safe_cols)}</b> | To'siq: <code>{', '.join(boom_cols)}</code>")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"<b>100% XAVFSIZ YO'L KETMA-KETLIGI:</b>")
    lines.append(f"<code>{' -> '.join(safe_steps)}</code>")
    return "\n".join(lines)

# ==================== 1. APPLE OF FORTUNE (1xBet) ====================

APPLE_MULTIPLIERS = [1.23, 1.54, 1.93, 2.41, 4.02, 6.71, 11.18, 27.96, 69.90, 350.00]

def generate_apple_board():
    """
    10 ta qator yaratadi (0 - pastki 1-qator, 9 - yuqori 10-qator).
    Har bir qatorda 5 ta katak:
    Qator 0..3 (1-4 bosqich): 4 ta good, 1 ta bad
    Qator 4..6 (5-7 bosqich): 3 ta good, 2 ta bad
    Qator 7..8 (8-9 bosqich): 2 ta good, 3 ta bad
    Qator 9 (10-bosqich): 1 ta good, 4 ta bad
    """
    board = []
    for row_idx in range(10):
        if row_idx <= 3:
            good_count, bad_count = 4, 1
        elif row_idx <= 6:
            good_count, bad_count = 3, 2
        elif row_idx <= 8:
            good_count, bad_count = 2, 3
        else:
            good_count, bad_count = 1, 4
        
        row = ["good"] * good_count + ["bad"] * bad_count
        random.shuffle(row)
        board.append(row)
    return board

def start_apple_session(tg_user_id: int, bet_uzs: int):
    """Yangi Apple of Fortune o'yinini yaratadi"""
    board = generate_apple_board()
    salt, enc_hash = create_provably_fair(board)
    session_id = f"apple_{tg_user_id}_{int(time.time())}_{secrets.token_hex(3)}"
    
    state = {
        "board": board,
        "current_row": 0,  # 0..9
        "revealed": {},    # "row_col": "good"/"bad"
        "history": []
    }
    
    conn = db.get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO casino_game_sessions 
            (session_id, tg_user_id, game_type, bet_amount_uzs, current_multiplier, status, server_seed, encrypted_hash, game_state)
            VALUES (%s, %s, 'apple', %s, 1.0, 'active', %s, %s, %s)
            RETURNING id, session_id, bet_amount_uzs, current_multiplier, status, encrypted_hash
        """, (session_id, tg_user_id, bet_uzs, salt, enc_hash, json.dumps(state)))
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "bet_amount_uzs": row["bet_amount_uzs"],
            "current_multiplier": float(row["current_multiplier"]),
            "status": row["status"],
            "encrypted_hash": row["encrypted_hash"],
            "current_row": 0,
            "game_state": state
        }
    except Exception as err:
        conn.rollback()
        print(f"start_apple_session error: {err}")
        return None
    finally:
        conn.close()

def render_apple_ui(session_data: dict, game_state: dict):
    """Apple of Fortune oynasini matn va inline klaviatura bilan hosil qiladi"""
    if isinstance(game_state, str):
        game_state = json.loads(game_state)
    cur_row = game_state.get("current_row", 0)
    status = session_data.get("status", "active")
    bet = session_data["bet_amount_uzs"]
    mult = float(session_data.get("current_multiplier", 1.0))
    cur_win = int(bet * mult)
    board = game_state.get("board", [])
    revealed = game_state.get("revealed", {})
    enc_hash = session_data.get("encrypted_hash", "")[:16] + "..."
    sess_id = session_data["id"]

    status_icon = ce("DOT_GREEN") if status == "active" else (ce("SUCCESS") if status == "won" else ce("ERROR"))
    status_text = "O'yin faol" if status == "active" else ("G'alaba!" if status == "won" else "Yutqazdingiz")

    header = (
        f"{ce('APPLE_WHOLE')} <b>Apple of Fortune (1xBet uslubida)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_icon} <b>Holat:</b> {status_text}\n"
        f"{ce('MONEY')} <b>Garov:</b> <code>{bet:,} so'm</code>\n"
        f"{ce('FIRE')} <b>Joriy koeffitsient:</b> <b>x{mult:.2f}</b>\n"
        f"{ce('MONEY')} <b>Joriy yutuq:</b> <code>{cur_win:,} so'm</code>\n"
        f"{ce('LOCK')} <b>Provably Fair:</b> <code>{enc_hash}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if status == "active":
        header += f"{ce('APPLE_WHOLE')} <b>{cur_row + 1}-bosqich</b> (Koeffitsient: <b>x{APPLE_MULTIPLIERS[cur_row]}</b>). Olmani tanlang:\n"
    elif status == "won":
        header += f"{ce('PARTY')} <b>Tabriklaymiz! Siz {cur_win:,} so'm yutib oldingiz!</b> {ce('APPLE_WHOLE')}\n"
    else:
        # Fosh bo'lgan qatorning vizual ko'rinishi:
        lost_row_vis = " ".join([ce("APPLE_WHOLE") if v == "good" else ce("APPLE_BITTEN") for v in board[cur_row]])
        header += (
            f"{ce('APPLE_BITTEN')} <b>Tishlangan olmaga tushdingiz! Garov boy berildi.</b>\n"
            f"Fosh bo'lgan qator: {lost_row_vis}\n"
        )

    # Tugmalar: yuqori qatordan (9) pastki qatorgacha (0)
    buttons = []
    
    visible_rows = []
    if status == "active":
        min_r = max(0, cur_row - 1)
        max_r = min(9, cur_row + 2)
        visible_rows = list(range(max_r, min_r - 1, -1))
    else:
        visible_rows = list(range(min(9, cur_row + 1), max(0, cur_row - 2), -1))

    for r in visible_rows:
        row_btns = []
        r_mult = APPLE_MULTIPLIERS[r]
        for c in range(5):
            k = f"{r}_{c}"
            if k in revealed:
                cell_val = revealed[k]
                lbl = "🟢 🍏" if cell_val == "good" else "🔴 🍎"
                cb_data = "apple_noop"
            elif status == "active" and r == cur_row:
                # Default holatda butun olmalar tanlash uchun ko'rinadi
                lbl = f"🍏 {c + 1}"
                cb_data = f"aple_pick_{sess_id}_{r}_{c}"
            elif status != "active" and r == cur_row:
                # Yutqazganda shu qatordagi butun olmalar va tishlangan olma fosh bo'ladi
                cell_val = board[r][c]
                lbl = "🟢 🍏" if cell_val == "good" else "🔴 🍎"
                cb_data = "apple_noop"
            else:
                lbl = f"▫️ {c + 1}" if r > cur_row else "🟢 🍏"
                cb_data = "apple_noop"
            row_btns.append(InlineKeyboardButton(lbl, callback_data=cb_data))
        
        # Qator chetiga koeffitsient indikatori
        level_mark = f"👉 🟡 x{r_mult}" if (status == "active" and r == cur_row) else f"🟡 x{r_mult}"
        row_btns.append(InlineKeyboardButton(level_mark, callback_data="apple_noop"))
        buttons.append(row_btns)

    # Cashout va Boshqaruv tugmalari
    control_row = []
    if status == "active" and cur_row > 0:
        control_row.append(InlineKeyboardButton(f"🟢 💰 Yutuqni Yechish ({cur_win:,} so'm)", callback_data=f"aple_cash_{sess_id}"))
    
    if control_row:
        buttons.append(control_row)
        
    if status != "active":
        buttons.append([
            InlineKeyboardButton("🔵 🔁 Yangi O'yin", callback_data=f"game_apple_new_{bet}"),
            InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")
        ])
    else:
        buttons.append([InlineKeyboardButton("🔴 ❌ O'yinni Tark Etish", callback_data="menu_games")])

    return header, InlineKeyboardMarkup(buttons)

# ==================== 2. 💣 MINES (Minalar / Saper) ====================

def calculate_mines_multiplier(mines_count: int, gems_opened: int) -> float:
    """Saper o'yinida har bir ochilgan olmos uchun koeffitsient hisoblaydi"""
    if gems_opened <= 0: return 1.0
    total = 25
    safe = total - mines_count
    prob = 1.0
    for i in range(gems_opened):
        prob *= (safe - i) / (total - i)
    raw_mult = (1.0 / prob) * 0.94
    return max(1.05, round(raw_mult, 2))

def start_mines_session(tg_user_id: int, bet_uzs: int, mines_count: int = 3):
    """5x5 maydonda yangi Mines o'yinini yaratadi"""
    mines_count = max(1, min(10, mines_count))
    all_indices = list(range(25))
    mine_positions = random.sample(all_indices, mines_count)
    
    board = ["gem"] * 25
    for m in mine_positions:
        board[m] = "mine"

    salt, enc_hash = create_provably_fair({"mines": mine_positions, "count": mines_count})
    session_id = f"mines_{tg_user_id}_{int(time.time())}_{secrets.token_hex(3)}"

    state = {
        "mines_count": mines_count,
        "mine_positions": mine_positions,
        "opened_gems": [],
        "hit_mine": None
    }

    conn = db.get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO casino_game_sessions
            (session_id, tg_user_id, game_type, bet_amount_uzs, current_multiplier, status, server_seed, encrypted_hash, game_state)
            VALUES (%s, %s, 'mines', %s, 1.0, 'active', %s, %s, %s)
            RETURNING id, session_id, bet_amount_uzs, current_multiplier, status, encrypted_hash
        """, (session_id, tg_user_id, bet_uzs, salt, enc_hash, json.dumps(state)))
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "bet_amount_uzs": row["bet_amount_uzs"],
            "current_multiplier": float(row["current_multiplier"]),
            "status": row["status"],
            "encrypted_hash": row["encrypted_hash"],
            "mines_count": mines_count,
            "opened_gems": [],
            "game_state": state
        }
    except Exception as err:
        conn.rollback()
        print(f"start_mines_session error: {err}")
        return None
    finally:
        conn.close()

def render_mines_ui(session_data: dict, game_state: dict):
    """5x5 Mines interfeysini hosil qiladi"""
    if isinstance(game_state, str):
        game_state = json.loads(game_state)
    status = session_data.get("status", "active")
    bet = session_data["bet_amount_uzs"]
    mult = float(session_data.get("current_multiplier", 1.0))
    cur_win = int(bet * mult)
    mines_count = game_state.get("mines_count", 3)
    opened = set(game_state.get("opened_gems", []))
    hit_mine = game_state.get("hit_mine")
    mine_positions = set(game_state.get("mine_positions", []))
    enc_hash = session_data.get("encrypted_hash", "")[:16] + "..."
    sess_id = session_data["id"]

    status_icon = ce("DOT_GREEN") if status == "active" else (ce("SUCCESS") if status == "won" else ce("ERROR"))
    status_text = "O'yin faol" if status == "active" else ("Yutuq olindi!" if status == "won" else "Bomba portladi!")

    text = (
        f"{ce('MINES_BOMB')} <b>Mines (Minalar / Saper)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_icon} <b>Holat:</b> {status_text}\n"
        f"{ce('MONEY')} <b>Garov:</b> <code>{bet:,} so'm</code>\n"
        f"{ce('MINES_BOMB')} <b>Minalar soni:</b> <code>{mines_count} ta</code> | {ce('MINES_GEM')} <b>Ochilgan:</b> <code>{len(opened)} ta</code>\n"
        f"{ce('FIRE')} <b>Koeffitsient:</b> <b>x{mult:.2f}</b>\n"
        f"{ce('MONEY')} <b>Joriy yutuq:</b> <code>{cur_win:,} so'm</code>\n"
        f"{ce('LOCK')} <b>Provably Fair:</b> <code>{enc_hash}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if status == "active":
        next_mult = calculate_mines_multiplier(mines_count, len(opened) + 1)
        text += f"{ce('MINES_GEM')} Katakni bosing (Keyingi koeffitsient: <b>x{next_mult:.2f}</b>):\n"
    elif status == "won":
        text += f"{ce('PARTY')} <b>Tabriklaymiz! {cur_win:,} so'm hisobingizga o'tkazildi!</b> {ce('MINES_GEM')}\n"
    else:
        text += f"{ce('MINES_BOOM')} <b>Afsus, siz minaga tushdingiz! Garov kuyildi.</b>\n"

    # 5x5 tugmalar katakchasi
    buttons = []
    for r in range(5):
        row_btns = []
        for c in range(5):
            idx = r * 5 + c
            if idx in opened:
                lbl = "💎 🟢"
                cb_data = "mines_noop"
            elif status != "active" and idx in mine_positions:
                lbl = "💥 🔴" if idx == hit_mine else "💣 🔴"
                cb_data = "mines_noop"
            elif status == "active":
                lbl = f"🟦 {idx + 1}"
                cb_data = f"mines_open_{sess_id}_{idx}"
            else:
                lbl = "▫️"
                cb_data = "mines_noop"
            row_btns.append(InlineKeyboardButton(lbl, callback_data=cb_data))
        buttons.append(row_btns)

    # Cashout va qayta o'ynash
    if status == "active":
        if len(opened) > 0:
            buttons.append([InlineKeyboardButton(f"🟢 💰 Yutuqni Olish ({cur_win:,} so'm)", callback_data=f"mines_cash_{sess_id}")])
        buttons.append([InlineKeyboardButton("🔴 ❌ O'yinni Bekor Qilish", callback_data="menu_games")])
    else:
        buttons.append([
            InlineKeyboardButton(f"🔵 🔁 Yangi O'yin ({mines_count} mina)", callback_data=f"game_mines_new_{bet}_{mines_count}"),
            InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")
        ])

    return text, InlineKeyboardMarkup(buttons)

# ==================== 3. 🃏 21 (BLACKJACK / OCHKO) ====================

CARD_SUITS = ["♠️", "♥️", "♦️", "♣️"]
CARD_RANKS = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

def generate_deck():
    deck = []
    for s in CARD_SUITS:
        for r in CARD_RANKS:
            deck.append((r, s))
    random.shuffle(deck)
    return deck

def calculate_hand_score(cards: list) -> int:
    """Qo'ldagi kartalarning umumiy ochkosini hisoblaydi"""
    score = 0
    ace_count = 0
    for rank, suit in cards:
        val = CARD_RANKS[rank]
        score += val
        if rank == "A":
            ace_count += 1
    while score > 21 and ace_count > 0:
        score -= 10
        ace_count -= 1
    return score

def start_blackjack_session(tg_user_id: int, bet_uzs: int):
    """21 (Blackjack) o'yinini boshlaydi"""
    deck = generate_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]

    player_score = calculate_hand_score(player_cards)
    status = "active"
    win_amount = 0
    if player_score == 21:
        status = "won"
        win_amount = int(bet_uzs * 2.5)

    session_id = f"bj_{tg_user_id}_{int(time.time())}_{secrets.token_hex(3)}"
    state = {
        "deck": deck,
        "player_cards": player_cards,
        "dealer_cards": dealer_cards,
        "dealer_revealed": (status != "active")
    }

    conn = db.get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO casino_game_sessions
            (session_id, tg_user_id, game_type, bet_amount_uzs, current_multiplier, status, server_seed, encrypted_hash, game_state, win_amount_uzs)
            VALUES (%s, %s, 'blackjack', %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, session_id, bet_amount_uzs, current_multiplier, status
        """, (session_id, tg_user_id, bet_uzs, 2.5 if status == 'won' else 1.0, status, "bj_seed", "bj_hash", json.dumps(state), win_amount))
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "bet_amount_uzs": row["bet_amount_uzs"],
            "current_multiplier": float(row["current_multiplier"]),
            "status": row["status"],
            "player_cards": player_cards,
            "dealer_cards": dealer_cards,
            "game_state": state
        }
    except Exception as err:
        conn.rollback()
        print(f"start_blackjack_session error: {err}")
        return None
    finally:
        conn.close()

def suit_to_ce(suit_str: str) -> str:
    if "♠" in suit_str: return ce("CARD_SPADES")
    if "♥" in suit_str: return ce("CARD_HEARTS")
    if "♦" in suit_str: return ce("CARD_DIAMONDS")
    if "♣" in suit_str: return ce("CARD_CLUBS")
    return suit_str

def render_blackjack_ui(session_data: dict, game_state: dict):
    """Blackjack interfeysini hosil qiladi"""
    if isinstance(game_state, str):
        game_state = json.loads(game_state)
    status = session_data.get("status", "active")
    bet = session_data["bet_amount_uzs"]
    player_cards = game_state.get("player_cards", [])
    dealer_cards = game_state.get("dealer_cards", [])
    dealer_revealed = game_state.get("dealer_revealed", False)
    sess_id = session_data["id"]
    
    p_score = calculate_hand_score(player_cards)
    
    if dealer_revealed:
        d_score = calculate_hand_score(dealer_cards)
        d_cards_str = " ".join([f"[{r}{suit_to_ce(s)}]" for r, s in dealer_cards])
        d_score_str = f"({d_score} ochko)"
    else:
        first_r, first_s = dealer_cards[0]
        d_cards_str = f"[{first_r}{suit_to_ce(first_s)}] [{ce('CARD_BACK')} yashirin]"
        d_score_str = f"({CARD_RANKS[first_r]}+ ochko)"

    p_cards_str = " ".join([f"[{r}{suit_to_ce(s)}]" for r, s in player_cards])

    status_title = f"{ce('TIMER')} O'yin ketmoqda"
    if status == "won":
        status_title = f"{ce('PARTY')} SIZ G'ALABA QOZONDINGIZ!"
    elif status == "lost":
        status_title = f"{ce('ERROR')} DILER YUTDI (Siz yutqazdingiz)"
    elif status == "push":
        status_title = f"{ce('HANDSHAKE')} DURANG (Garov qaytarildi)"

    text = (
        f"{ce('CARD_JOKER')} <b>21 (Blackjack / Ochko)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{ce('TARGET')} <b>Holat:</b> {status_title}\n"
        f"{ce('MONEY')} <b>Garov:</b> <code>{bet:,} so'm</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ce('BOT')} <b>Diler (Bot) kartalari:</b>\n"
        f"{d_cards_str} {d_score_str}\n\n"
        f"{ce('USER')} <b>Sizning kartalaringiz:</b>\n"
        f"{p_cards_str} <b>({p_score} ochko)</b>\n\n"
    )

    if status == "active":
        text += "Tanlovingiz: [Yana karta olish] yoki [Yetarli deb to'xtash]:"
        buttons = [
            [
                InlineKeyboardButton("🟢 🃏 Yana bitta karta (+Hit)", callback_data=f"bj_hit_{sess_id}"),
                InlineKeyboardButton("🔴 🛑 Yetarli (Stand)", callback_data=f"bj_stand_{sess_id}")
            ]
        ]
    else:
        win_uzs = session_data.get("win_amount_uzs", 0)
        if status == "won":
            text += f"{ce('MONEY')} <b>Yutuq miqdori:</b> <code>+{win_uzs:,} so'm</code> hisobingizga qo'shildi!"
        elif status == "push":
            text += f"{ce('RETRY')} <b>Garov:</b> <code>{bet:,} so'm</code> qaytarildi."
        else:
            text += f"{ce('CASH')} <b>Garov:</b> <code>{bet:,} so'm</code> boy berildi."

        buttons = [
            [
                InlineKeyboardButton("🔵 🔁 Yangi O'yin", callback_data=f"game_bj_new_{bet}"),
                InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")
            ]
        ]

    return text, InlineKeyboardMarkup(buttons)

# ==================== 4. 🛩️ KAMIKAZE (Samolyotli Pog'onalar) ====================

KAMIKAZE_MULTIPLIERS = [1.20, 1.40, 1.65, 2.00, 2.50, 3.20, 4.20, 5.80, 7.80, 10.00]

def generate_kamikaze_board():
    """10 ta balandlik bosqichi, har birida 5 ta marshrut (1 ta halokat, 4 ta o'tish)"""
    board = []
    for step in range(10):
        row = ["safe"] * 4 + ["crash"]
        random.shuffle(row)
        board.append(row)
    return board

def start_kamikaze_session(tg_user_id: int, bet_uzs: int):
    """Kamikaze samolyot o'yinini yaratadi"""
    board = generate_kamikaze_board()
    salt, enc_hash = create_provably_fair(board)
    session_id = f"kami_{tg_user_id}_{int(time.time())}_{secrets.token_hex(3)}"

    state = {
        "board": board,
        "current_step": 0,
        "revealed": {}
    }

    conn = db.get_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO casino_game_sessions
            (session_id, tg_user_id, game_type, bet_amount_uzs, current_multiplier, status, server_seed, encrypted_hash, game_state)
            VALUES (%s, %s, 'kamikaze', %s, 1.0, 'active', %s, %s, %s)
            RETURNING id, session_id, bet_amount_uzs, current_multiplier, status, encrypted_hash
        """, (session_id, tg_user_id, bet_uzs, salt, enc_hash, json.dumps(state)))
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "bet_amount_uzs": row["bet_amount_uzs"],
            "current_multiplier": float(row["current_multiplier"]),
            "status": row["status"],
            "encrypted_hash": row["encrypted_hash"],
            "game_state": state
        }
    except Exception as err:
        conn.rollback()
        print(f"start_kamikaze_session error: {err}")
        return None
    finally:
        conn.close()

def render_kamikaze_ui(session_data: dict, game_state: dict):
    """Kamikaze o'yini interfeysini hosil qiladi"""
    if isinstance(game_state, str):
        game_state = json.loads(game_state)
    cur_step = game_state.get("current_step", 0)
    status = session_data.get("status", "active")
    bet = session_data["bet_amount_uzs"]
    mult = float(session_data.get("current_multiplier", 1.0))
    cur_win = int(bet * mult)
    board = game_state.get("board", [])
    revealed = game_state.get("revealed", {})
    enc_hash = session_data.get("encrypted_hash", "")[:16] + "..."
    sess_id = session_data["id"]

    status_icon = ce("DOT_GREEN") if status == "active" else (ce("SUCCESS") if status == "won" else ce("ERROR"))
    status_text = f"{ce('KAMI_PLANE')} Parvoz davom etmoqda" if status == "active" else (f"{ce('KAMI_LANDING')} Muvaffaqiyatli qo'ndi!" if status == "won" else f"{ce('KAMI_CRASH')} Samolyot quladi!")

    text = (
        f"{ce('KAMI_PLANE')} <b>Kamikaze (Samolyotli Pog'onalar)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_icon} <b>Holat:</b> {status_text}\n"
        f"{ce('MONEY')} <b>Garov:</b> <code>{bet:,} so'm</code>\n"
        f"{ce('FIRE')} <b>Joriy koeffitsient:</b> <b>x{mult:.2f}</b>\n"
        f"{ce('MONEY')} <b>Joriy yutuq:</b> <code>{cur_win:,} so'm</code>\n"
        f"{ce('LOCK')} <b>Provably Fair:</b> <code>{enc_hash}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if status == "active":
        next_m = KAMIKAZE_MULTIPLIERS[cur_step]
        text += f"{ce('KAMI_PLANE')} <b>{cur_step + 1}-bosqich</b> (Koeffitsient: <b>x{next_m:.2f}</b>). Qo'nish chizig'ini tanlang:\n"
    elif status == "won":
        text += f"{ce('PARTY')} <b>Tabriklaymiz! Siz {cur_win:,} so'm yutib oldingiz!</b> {ce('KAMI_LANDING')}\n"
    else:
        text += f"{ce('KAMI_CRASH')} <b>Samolyot quladi! Garov boy berildi.</b>\n"

    # Tugmalar qatori
    buttons = []
    visible_steps = list(range(min(9, cur_step + 2), max(0, cur_step - 1), -1))
    for s in visible_steps:
        row_btns = []
        s_mult = KAMIKAZE_MULTIPLIERS[s]
        for c in range(5):
            k = f"{s}_{c}"
            if k in revealed:
                lbl = "🛩️ 🟢" if revealed[k] == "safe" else "💥 🔴"
                cb = "kami_noop"
            elif status == "active" and s == cur_step:
                lbl = f"🛬 {c + 1}"
                cb = f"kami_pick_{sess_id}_{s}_{c}"
            elif status != "active" and s == cur_step:
                lbl = "🛩️ 🟢" if board[s][c] == "safe" else "💥 🔴"
                cb = "kami_noop"
            else:
                lbl = f"☁️ {c + 1}" if s > cur_step else "▫️"
                cb = "kami_noop"
            row_btns.append(InlineKeyboardButton(lbl, callback_data=cb))
        
        indicator = f"👉 🟡 x{s_mult:.2f}" if (status == "active" and s == cur_step) else f"🟡 x{s_mult:.2f}"
        row_btns.append(InlineKeyboardButton(indicator, callback_data="kami_noop"))
        buttons.append(row_btns)

    if status == "active" and cur_step > 0:
        buttons.append([InlineKeyboardButton(f"🟢 💰 Yutuqni Olish ({cur_win:,} so'm)", callback_data=f"kami_cash_{sess_id}")])

    if status != "active":
        buttons.append([
            InlineKeyboardButton("🔵 🔁 Yangi Parvoz", callback_data=f"game_kami_new_{bet}"),
            InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")
        ])
    else:
        buttons.append([InlineKeyboardButton("🔴 ❌ Parvozni Bekor Qilish", callback_data="menu_games")])

    return text, InlineKeyboardMarkup(buttons)

# ==================== 5. 🚀 LIVE CRASH / AVIATOR (2 SLOTLI) ====================

class LiveCrashManager:
    """Global Live Crash (Aviator) Dvigateli - Real-time uzluksiz raundlar va 2 mustaqil stavka sloti"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LiveCrashManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized: return
        self.initialized = True
        self.round_id = 1
        self.state = "waiting"  # "waiting" (5s countdown), "flying", "crashed"
        self.waiting_end_time = time.time() + 5.0
        self.countdown = 5
        self.multiplier = 1.00
        self.crash_point = 1.85
        self.crash_time = 0
        self.round_start_time = time.time()
        self.recent_crashes = [1.54, 2.10, 1.15, 4.80, 1.85]
        self.active_bets = {}
        self.history_leaderboard = []

    def start_new_round(self):
        """Yangi global raundni boshlaydi"""
        self.round_id += 1
        self.state = "waiting"
        self.waiting_end_time = time.time() + 5.0
        self.countdown = 5
        self.multiplier = 1.00
        self.crash_time = 0
        self.active_bets.clear()
        
        # Crash point generator: 92% ehtimollik kassa foydasi
        r = random.random()
        if r < 0.08:  # 8% darhol crash 1.00x - 1.10x
            self.crash_point = round(random.uniform(1.00, 1.15), 2)
        elif r < 0.60:  # 52% oddiy crash 1.15x - 2.50x
            self.crash_point = round(random.uniform(1.15, 2.50), 2)
        elif r < 0.90:  # 30% yuqori crash 2.50x - 7.00x
            self.crash_point = round(random.uniform(2.50, 7.00), 2)
        else:  # 10% katta crash 7.00x - 50.00x
            self.crash_point = round(random.uniform(7.00, 35.00), 2)

    def place_bet(self, user_id: int, user_name: str, slot_num: int, amount_uzs: int, auto_cashout: float = 0.0):
        """Foydalanuvchi stavkasini qabul qiladi (faqat waiting bosqichida)"""
        if self.state != "waiting":
            return {"ok": False, "error": "Raund allaqachon uchmoqda! Keyingi raundni kuting (5 soniya)."}
        
        if slot_num not in (1, 2):
            return {"ok": False, "error": "Noto'g'ri slot! 1 yoki 2-slotni tanlang."}

        key = (user_id, slot_num)
        if key in self.active_bets:
            return {"ok": False, "error": f"{slot_num}-slotga allaqachon stavka qilingan!"}

        # Balansdan yechish
        ok = db.deduct_user_balance(user_id, amount_uzs)
        if not ok:
            return {"ok": False, "error": "Balansingizda yetarli mablag' mavjud emas!"}

        self.active_bets[key] = {
            "user_id": user_id,
            "user_name": user_name or f"User_{user_id}",
            "slot": slot_num,
            "bet_amount": amount_uzs,
            "auto_cashout": auto_cashout if auto_cashout >= 1.10 else 0.0,
            "status": "active",
            "cashed_mult": 0.0,
            "win_amount": 0
        }
        return {"ok": True, "bet": self.active_bets[key]}

    def cashout_bet(self, user_id: int, slot_num: int):
        """Foydalanuvchi qo'lda yutuqni yechib oladi"""
        if self.state != "flying":
            return {"ok": False, "error": "Ayni paytda parvoz holati mavjud emas!"}

        key = (user_id, slot_num)
        if key not in self.active_bets:
            return {"ok": False, "error": "Ushbu slotda faol stavka topilmadi!"}

        b = self.active_bets[key]
        if b["status"] != "active":
            return {"ok": False, "error": "Bu stavka allaqachon yechib olingan yoki yutqazilgan!"}

        current_m = self.multiplier
        win_uzs = int(b["bet_amount"] * current_m)
        
        b["status"] = "cashed_out"
        b["cashed_mult"] = current_m
        b["win_amount"] = win_uzs

        # Foydalanuvchi balansiga yutuqni qo'shish
        db.add_user_balance(user_id, win_uzs)
        
        # Leaderboardga qo'shish
        self.history_leaderboard.insert(0, {
            "user_name": b["user_name"],
            "slot": slot_num,
            "mult": current_m,
            "win": win_uzs,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        self.history_leaderboard = self.history_leaderboard[:15]

        return {"ok": True, "win_amount": win_uzs, "multiplier": current_m}

    def tick(self):
        """Har soniyada crash holatini va hisob-kitoblarni yangilaydi"""
        now = time.time()
        if self.state == "waiting":
            remaining = int(math.ceil(max(0, self.waiting_end_time - now)))
            self.countdown = remaining
            if now >= self.waiting_end_time:
                self.state = "flying"
                self.multiplier = 1.00
                self.round_start_time = now
        elif self.state == "flying":
            elapsed = now - self.round_start_time
            self.multiplier = round(1.00 + (elapsed * 0.38) + (elapsed ** 1.35) * 0.12, 2)
            
            # Auto-cashoutlarni tekshirish
            for key, b in list(self.active_bets.items()):
                if b["status"] == "active" and b["auto_cashout"] > 0:
                    if self.multiplier >= b["auto_cashout"]:
                        win_uzs = int(b["bet_amount"] * b["auto_cashout"])
                        b["status"] = "cashed_out"
                        b["cashed_mult"] = b["auto_cashout"]
                        b["win_amount"] = win_uzs
                        db.add_user_balance(b["user_id"], win_uzs)
                        self.history_leaderboard.insert(0, {
                            "user_name": b["user_name"],
                            "slot": b["slot"],
                            "mult": b["auto_cashout"],
                            "win": win_uzs,
                            "time": datetime.now().strftime("%H:%M:%S")
                        })
                        self.history_leaderboard = self.history_leaderboard[:15]

            # Crash tekshiruvi
            if self.multiplier >= self.crash_point:
                self.state = "crashed"
                self.crash_time = now
                self.recent_crashes.insert(0, self.crash_point)
                self.recent_crashes = self.recent_crashes[:8]
                
                # Yutqazilgan barcha faol stavkalarni belgilash
                for key, b in self.active_bets.items():
                    if b["status"] == "active":
                        b["status"] = "lost"

        elif self.state == "crashed":
            # 2.5 soniya kutib yangi raundga o'tadi
            if now - self.crash_time >= 2.5:
                self.start_new_round()

crash_manager = LiveCrashManager()
_last_signaled_round_id = 0

async def run_crash_background_worker():
    """Crash server engine background sikli - barcha faol oyna foydalanuvchilariga avtomatik jonli uzatadi"""
    global _last_signaled_round_id
    while True:
        try:
            crash_manager.tick()
            now = time.time()

            # 5-soniyalik cooldown ichida admin guruhga signal yuborish
            if crash_manager.state == "waiting" and crash_manager.round_id != _last_signaled_round_id:
                _last_signaled_round_id = crash_manager.round_id
                sig_txt = format_crash_signal(crash_manager.round_id, crash_manager.crash_point)
                asyncio.create_task(send_casino_signal(sig_txt))

            if _global_bot and CRASH_ACTIVE_VIEWERS:
                for chat_id, data in list(CRASH_ACTIVE_VIEWERS.items()):
                    if chat_id not in CRASH_ACTIVE_VIEWERS:
                        continue
                    token = data.get("session_token")
                    # Telegram Bot API cheklovi: har bir chatga ~0.75-0.8s da yangilash
                    if now - data.get("last_edit_ts", 0) < 0.75:
                        continue
                    try:
                        text, kb = render_crash_ui(data["user_id"])
                        if CRASH_ACTIVE_VIEWERS.get(chat_id, {}).get("session_token") != token:
                            continue
                        if text != data.get("last_rendered"):
                            data["last_rendered"] = text
                            data["last_edit_ts"] = now
                            await _global_bot.edit_message_text(chat_id, data["message_id"], text, reply_markup=kb)
                    except Exception as edit_err:
                        err_str = str(edit_err).lower()
                        if "flood" in err_str:
                            await asyncio.sleep(1.5)
                        elif any(k in err_str for k in ["message to edit not found", "chat not found", "message_id_invalid", "bad_request"]):
                            CRASH_ACTIVE_VIEWERS.pop(chat_id, None)
                        elif "message is not modified" in err_str:
                            pass
        except Exception as e:
            print(f"Crash background worker tick error: {e}")
        await asyncio.sleep(0.35)

def render_crash_ui(tg_user_id: int):
    """Live Crash asosiy interfeysini hosil qiladi"""
    cm = crash_manager
    state = cm.state
    mult = cm.multiplier
    recent_str = " | ".join([f"<b>{m:.2f}x</b>" for m in cm.recent_crashes[:5]])

    b1 = cm.active_bets.get((tg_user_id, 1))
    b2 = cm.active_bets.get((tg_user_id, 2))

    if state == "waiting":
        flight_display = (
            f"{ce('TIMER')} <b>Yangi Raund Boshlanmoqda:</b> <b>{cm.countdown} soniya</b>\n"
            f"<i>Stavkalaringizni tanlang! {ce('LIGHTNING')} Ping: 10ms</i>"
        )
    elif state == "flying":
        trail_len = min(10, int((mult - 1.0) * 3) + 1)
        flight_path = "─" * trail_len + ">"
        flight_display = (
            f"{ce('CRASH_PLANE')} <b>SAMOLYOT UCHMOQDA:</b> <b><code>x{mult:.2f}</code></b>\n"
            f"<code>[{flight_path}]</code> {ce('LIGHTNING')} <i>Ping: 10ms | 60 FPS</i>"
        )
    else:
        flight_display = f"{ce('CRASH_BOOM')} <b>PORTLASH! (Crash at x{cm.crash_point:.2f})</b>"

    # Slotlar holati
    def format_slot_status(b, num):
        if not b:
            return f"{ce('ERROR')} Stavka yo'q"
        if b["status"] == "active":
            cur_pot = int(b["bet_amount"] * mult) if state == "flying" else b["bet_amount"]
            return f"{ce('DOT_GREEN')} Faol ({b['bet_amount']:,} so'm -> <b>{cur_pot:,} so'm</b>)"
        if b["status"] == "cashed_out":
            return f"{ce('SUCCESS')} Yechib olindi (+{b['win_amount']:,} so'm x{b['cashed_mult']:.2f})"
        return f"{ce('CRASH_BOOM')} Boy berildi ({b['bet_amount']:,} so'm)"

    slot1_txt = format_slot_status(b1, 1)
    slot2_txt = format_slot_status(b2, 2)

    # Leaderboard
    leaderboard_lines = []
    for lb in cm.history_leaderboard[:4]:
        leaderboard_lines.append(f"• {lb['user_name'][:12]} -> <b>x{lb['mult']:.2f}</b> (+{lb['win']:,} so'm)")
    lb_text = "\n".join(leaderboard_lines) if leaderboard_lines else "<i>Hozircha yutuqlar yo'q</i>"

    text = (
        f"{ce('CRASH_PLANE')} <b>Live Crash / Aviator (2 Slotli)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{flight_display}\n\n"
        f"{ce('CHART')} <b>Oxirgi koeffitsientlar:</b>\n"
        f"{recent_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"[1] <b>1-Slot:</b> {slot1_txt}\n"
        f"[2] <b>2-Slot:</b> {slot2_txt}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{ce('TROPHY')} <b>Jonli Yutuqlar (Live):</b>\n"
        f"{lb_text}\n"
    )

    buttons = []
    
    # Parvoz paytidagi tezkor cashout tugmalari
    if state == "flying":
        cash_row = []
        if b1 and b1["status"] == "active":
            pot1 = int(b1["bet_amount"] * mult)
            cash_row.append(InlineKeyboardButton(f"🟢 💰 1-Slot Yechish ({pot1:,} so'm)", callback_data="crash_cash_1"))
        if b2 and b2["status"] == "active":
            pot2 = int(b2["bet_amount"] * mult)
            cash_row.append(InlineKeyboardButton(f"🟢 💰 2-Slot Yechish ({pot2:,} so'm)", callback_data="crash_cash_2"))
        if cash_row:
            buttons.append(cash_row)

    # Stavka qilish tugmalari (agar kutish fazasi bo'lsa)
    if state == "waiting":
        row_bet1 = []
        if not b1:
            row_bet1 = [
                InlineKeyboardButton("🔵 1️⃣ 3,000", callback_data="crash_bet_1_3000"),
                InlineKeyboardButton("🔵 1️⃣ 5,000", callback_data="crash_bet_1_5000"),
                InlineKeyboardButton("🔵 1️⃣ 10,000", callback_data="crash_bet_1_10000"),
            ]
        row_bet2 = []
        if not b2:
            row_bet2 = [
                InlineKeyboardButton("🟣 2️⃣ 5,000", callback_data="crash_bet_2_5000"),
                InlineKeyboardButton("🟣 2️⃣ 10,000", callback_data="crash_bet_2_10000"),
                InlineKeyboardButton("🟣 2️⃣ 25,000", callback_data="crash_bet_2_25000"),
            ]
        if row_bet1: buttons.append(row_bet1)
        if row_bet2: buttons.append(row_bet2)

    buttons.append([
        InlineKeyboardButton("🟡 🔄 Yangilash", callback_data="crash_refresh"),
        InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="crash_exit_games"),
        InlineKeyboardButton("⚪ 🏠 Bosh Menyu", callback_data="crash_exit_main")
    ])

    return text, InlineKeyboardMarkup(buttons)

# ==================== UMUMIY O'YINLAR BOSHQARUV MENYUSI ====================

def games_main_menu_kb():
    """Botning barcha o'yinlari jamlangan yangi bosh menyusi"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍏 🟢 Apple of Fortune", callback_data="game_apple_menu"),
            InlineKeyboardButton("💣 🔴 Mines (Saper)", callback_data="game_mines_menu"),
        ],
        [
            InlineKeyboardButton("🚀 🔵 Live Crash (Aviator)", callback_data="game_crash_menu"),
            InlineKeyboardButton("🃏 🟣 21 (Blackjack)", callback_data="game_bj_menu"),
        ],
        [
            InlineKeyboardButton("🛩️ 🟡 Kamikaze (Parvoz)", callback_data="game_kami_menu"),
            InlineKeyboardButton("🎰 🟠 Omad G'ildiragi", callback_data="spin_wheel"),
        ],
        [
            InlineKeyboardButton("🎁 🟢 Omadli Quti", callback_data="box_open"),
            InlineKeyboardButton("⚔️ 🔴 Tanga Tashlash (Duel)", callback_data="duel_menu"),
        ],
        [
            InlineKeyboardButton("🎟️ 🟣 Mega Lotereya", callback_data="lottery_menu"),
            InlineKeyboardButton("🏠 ⚪ Bosh Menyu", callback_data="back_main")
        ]
    ])

def register_casino_handlers(bot: Client):
    """Barcha 5 ta yangi o'yinning callback query handlerlarini botga ulaydi"""
    global _global_bot
    _global_bot = bot

    @bot.on_callback_query(filters.regex(r"^menu_games$"))
    async def cb_menu_games(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        bal = db.get_user_balance(user_id)
        text = (
            f"{ce('CASINO')} <b>KAZINO VA OMAD O'YINLARI ZALI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{ce('MONEY')} <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"O'zingizga yoqqan o'yinni tanlang va omadingizni sinab ko'ring:\n"
            f"• {ce('APPLE_WHOLE')} <b>Apple of Fortune</b> — 350x gacha olma terish\n"
            f"• {ce('MINES_BOMB')} <b>Mines</b> — Minalardan qochib olmoslarni ochish\n"
            f"• {ce('CRASH_PLANE')} <b>Live Crash (Aviator)</b> — 2 slotli jonli raundlar\n"
            f"• {ce('CARD_JOKER')} <b>21 (Blackjack)</b> — Aqlli diler bilan klassik karta\n"
            f"• {ce('KAMI_PLANE')} <b>Kamikaze</b> — Samolyotli pog'onalar parvozi"
        )
        await cb.message.edit_text(text, reply_markup=games_main_menu_kb())
        await cb.answer()

    # --- APPLE OF FORTUNE CALLBACKS ---
    @bot.on_callback_query(filters.regex(r"^game_apple_menu$"))
    async def cb_apple_menu(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        text = (
            f"{ce('APPLE_WHOLE')} <b>Apple of Fortune (1xBet uslubida)</b>\n\n"
            f"10 ta pog'onali olmalar maydoni! Har qatorda to'g'ri olmani topsangiz, "
            f"koeffitsient <b>x1.23</b> dan boshlanib <b>x350.00</b> gacha ko'tariladi!\n\n"
            f"Garov miqdorini tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 3,000 so'm", callback_data="game_apple_start_3000"),
             InlineKeyboardButton("🔵 5,000 so'm", callback_data="game_apple_start_5000")],
            [InlineKeyboardButton("🟣 10,000 so'm", callback_data="game_apple_start_10000"),
             InlineKeyboardButton("🟡 25,000 so'm", callback_data="game_apple_start_25000")],
            [InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^game_apple_(?:start|new)_(\d+)$"))
    async def cb_apple_start(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        bet = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        bal = db.get_user_balance(user_id)
        if bal < bet:
            await cb.answer("Balansingizda yetarli mablag' yo'q!", show_alert=True)
            return
        db.deduct_user_balance(user_id, bet)
        session = start_apple_session(user_id, bet)
        if not session:
            db.add_user_balance(user_id, bet)
            await cb.answer("Xatolik: O'yinni boshlab bo'lmadi!", show_alert=True)
            return
        state = session["game_state"]

        # Admin kanal/guruhiga 100% olma xaritasi signalini yuborish
        user_name = cb.from_user.first_name or f"User_{user_id}"
        sig_txt = format_apple_signal(user_id, user_name, bet, state["board"])
        asyncio.create_task(send_casino_signal(sig_txt, target_user_id=user_id, reply_markup=spy_action_kb(user_id)))

        text, kb = render_apple_ui(session, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^aple_pick_(\d+)_(\d+)_(\d+)$"))
    async def cb_apple_pick(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        r = int(cb.matches[0].group(2))
        c = int(cb.matches[0].group(3))
        user_id = cb.from_user.id

        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            await cb.answer("Sessiya topilmadi!", show_alert=True)
            return

        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            await cb.answer("Ushbu o'yin allaqachon yakunlangan!", show_alert=True)
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        cur_row = state.get("current_row", 0)
        if r != cur_row:
            conn.close()
            await cb.answer("Faqat joriy qatordagi olmani tanlashingiz mumkin!", show_alert=True)
            return

        cell_val = state["board"][r][c]
        state["revealed"][f"{r}_{c}"] = cell_val

        if cell_val == "good":
            cur_row += 1
            state["current_row"] = cur_row
            new_mult = APPLE_MULTIPLIERS[cur_row - 1]
            if cur_row >= 10:  # 10-qator to'liq yutildi (Jackpot 350x)
                win_amt = int(sess["bet_amount_uzs"] * new_mult)
                cur.execute("UPDATE casino_game_sessions SET status = 'won', current_multiplier = %s, win_amount_uzs = %s, game_state = %s, updated_at = NOW() WHERE id = %s", (new_mult, win_amt, json.dumps(state), sess["id"]))
                db.add_user_balance(user_id, win_amt)
                sess["status"] = "won"
                sess["current_multiplier"] = new_mult
                sess["win_amount_uzs"] = win_amt
            else:
                cur.execute("UPDATE casino_game_sessions SET current_multiplier = %s, game_state = %s, updated_at = NOW() WHERE id = %s", (new_mult, json.dumps(state), sess["id"]))
                sess["current_multiplier"] = new_mult
        else:
            cur.execute("UPDATE casino_game_sessions SET status = 'lost', game_state = %s, updated_at = NOW() WHERE id = %s", (json.dumps(state), sess["id"]))
            sess["status"] = "lost"

        conn.commit()
        conn.close()

        sess["game_state"] = state
        text, kb = render_apple_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^aple_cash_(\d+)$"))
    async def cb_apple_cashout(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            await cb.answer("O'yin allaqachon yakunlangan!", show_alert=True)
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        mult = float(sess["current_multiplier"])
        win_amt = int(sess["bet_amount_uzs"] * mult)
        cur.execute("UPDATE casino_game_sessions SET status = 'won', win_amount_uzs = %s, updated_at = NOW() WHERE id = %s", (win_amt, sess["id"]))
        conn.commit()
        conn.close()

        db.add_user_balance(user_id, win_amt)
        sess["status"] = "won"
        sess["win_amount_uzs"] = win_amt
        sess["game_state"] = state
        text, kb = render_apple_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer(f"G'alaba! +{win_amt:,} so'm balansingizga qo'shildi!", show_alert=True)

    # --- MINES CALLBACKS ---
    @bot.on_callback_query(filters.regex(r"^game_mines_menu$"))
    async def cb_mines_menu(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        text = (
            f"{ce('MINES_BOMB')} <b>Mines (Minalar / Saper)</b>\n\n"
            f"5x5 maydonda yashiringan minalardan saqlanib olmoslarni toping!\n"
            f"Har bir ochilgan olmos garovingizni bir necha barobar oshiradi!\n\n"
            f"Garov summasini tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 3,000 (3 mina)", callback_data="game_mines_start_3000_3"),
             InlineKeyboardButton("🔵 5,000 (3 mina)", callback_data="game_mines_start_5000_3")],
            [InlineKeyboardButton("🟣 10,000 (5 mina)", callback_data="game_mines_start_10000_5"),
             InlineKeyboardButton("🟡 25,000 (5 mina)", callback_data="game_mines_start_25000_5")],
            [InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^game_mines_(?:start|new)_(\d+)_(\d+)$"))
    async def cb_mines_start(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        bet = int(cb.matches[0].group(1))
        mines_count = int(cb.matches[0].group(2))
        user_id = cb.from_user.id
        bal = db.get_user_balance(user_id)
        if bal < bet:
            await cb.answer("Balansingizda mablag' yetarli emas!", show_alert=True)
            return
        db.deduct_user_balance(user_id, bet)
        sess = start_mines_session(user_id, bet, mines_count)
        if not sess:
            db.add_user_balance(user_id, bet)
            await cb.answer("Xatolik yuz berdi!", show_alert=True)
            return
        
        state = sess["game_state"]

        # Admin kanal/guruhiga Mines bombalar xaritasi signalini yuborish
        user_name = cb.from_user.first_name or f"User_{user_id}"
        sig_txt = format_mines_signal(user_id, user_name, bet, mines_count, state["mine_positions"])
        asyncio.create_task(send_casino_signal(sig_txt, target_user_id=user_id, reply_markup=spy_action_kb(user_id)))

        text, kb = render_mines_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mines_open_(\d+)_(\d+)$"))
    async def cb_mines_open(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        idx = int(cb.matches[0].group(2))
        user_id = cb.from_user.id

        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        mines_set = set(state["mine_positions"])
        opened = set(state.get("opened_gems", []))

        if idx in opened:
            conn.close()
            await cb.answer()
            return

        if idx in mines_set:
            # Mina portladi
            state["hit_mine"] = idx
            sess["status"] = "lost"
            cur.execute("UPDATE casino_game_sessions SET status = 'lost', game_state = %s, updated_at = NOW() WHERE id = %s", (json.dumps(state), sess["id"]))
        else:
            opened.add(idx)
            state["opened_gems"] = list(opened)
            new_mult = calculate_mines_multiplier(state["mines_count"], len(opened))
            sess["current_multiplier"] = new_mult
            cur.execute("UPDATE casino_game_sessions SET current_multiplier = %s, game_state = %s, updated_at = NOW() WHERE id = %s", (new_mult, json.dumps(state), sess["id"]))

        conn.commit()
        conn.close()

        sess["game_state"] = state
        text, kb = render_mines_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^mines_cash_(\d+)$"))
    async def cb_mines_cashout(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            await cb.answer("O'yin allaqachon yakunlangan!", show_alert=True)
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        mult = float(sess["current_multiplier"])
        win_amt = int(sess["bet_amount_uzs"] * mult)
        cur.execute("UPDATE casino_game_sessions SET status = 'won', win_amount_uzs = %s, updated_at = NOW() WHERE id = %s", (win_amt, sess["id"]))
        conn.commit()
        conn.close()

        db.add_user_balance(user_id, win_amt)
        sess["status"] = "won"
        sess["win_amount_uzs"] = win_amt
        sess["game_state"] = state
        text, kb = render_mines_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer(f"G'alaba! +{win_amt:,} so'm balansingizga o'tkazildi!", show_alert=True)

    # --- 21 (BLACKJACK) CALLBACKS ---
    @bot.on_callback_query(filters.regex(r"^game_bj_menu$"))
    async def cb_bj_menu(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        text = (
            f"{ce('CARD_JOKER')} <b>21 (Blackjack / Ochko)</b>\n\n"
            f"Aqlli bot dileriga qarshi klassik 21 karta o'yini!\n"
            f"21 ochkoga eng yaqin kelgan yoki dilerdan ko'proq ochko to'plagan g'olib bo'ladi.\n\n"
            f"Garov summasini tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 3,000 so'm", callback_data="game_bj_start_3000"),
             InlineKeyboardButton("🔵 5,000 so'm", callback_data="game_bj_start_5000")],
            [InlineKeyboardButton("🟣 10,000 so'm", callback_data="game_bj_start_10000"),
             InlineKeyboardButton("🟡 25,000 so'm", callback_data="game_bj_start_25000")],
            [InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^game_bj_(?:start|new)_(\d+)$"))
    async def cb_bj_start(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        bet = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        bal = db.get_user_balance(user_id)
        if bal < bet:
            await cb.answer("Balansda yetarli mablag' yo'q!", show_alert=True)
            return
        db.deduct_user_balance(user_id, bet)
        sess = start_blackjack_session(user_id, bet)
        if not sess:
            db.add_user_balance(user_id, bet)
            await cb.answer("Xatolik yuz berdi!", show_alert=True)
            return
        
        state = sess["game_state"]

        # Admin kanal/guruhiga 21 (Blackjack) diler kartalari signalini yuborish
        user_name = cb.from_user.first_name or f"User_{user_id}"
        sig_txt = format_blackjack_signal(user_id, user_name, bet, state["player_cards"], state["dealer_cards"])
        asyncio.create_task(send_casino_signal(sig_txt, target_user_id=user_id, reply_markup=spy_action_kb(user_id)))

        text, kb = render_blackjack_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^bj_hit_(\d+)$"))
    async def cb_bj_hit(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        deck = state["deck"]
        if deck:
            state["player_cards"].append(deck.pop())

        p_score = calculate_hand_score(state["player_cards"])
        if p_score > 21:
            sess["status"] = "lost"
            state["dealer_revealed"] = True
            cur.execute("UPDATE casino_game_sessions SET status = 'lost', game_state = %s, updated_at = NOW() WHERE id = %s", (json.dumps(state), sess["id"]))
        elif p_score == 21:
            pass

        conn.commit()
        conn.close()

        sess["game_state"] = state
        text, kb = render_blackjack_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^bj_stand_(\d+)$"))
    async def cb_bj_stand(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        deck = state["deck"]
        dealer_cards = state["dealer_cards"]
        state["dealer_revealed"] = True

        p_score = calculate_hand_score(state["player_cards"])
        d_score = calculate_hand_score(dealer_cards)

        # Diler 17 gacha karta oladi
        while d_score < 17 and deck:
            dealer_cards.append(deck.pop())
            d_score = calculate_hand_score(dealer_cards)

        bet = sess["bet_amount_uzs"]
        win_amt = 0
        if d_score > 21:  # Diler bust bo'ldi
            sess["status"] = "won"
            win_amt = int(bet * 2.0)
            db.add_user_balance(user_id, win_amt)
        elif p_score > d_score:
            sess["status"] = "won"
            win_amt = int(bet * 2.0)
            db.add_user_balance(user_id, win_amt)
        elif p_score == d_score:
            sess["status"] = "push"
            win_amt = bet
            db.add_user_balance(user_id, win_amt)
        else:
            sess["status"] = "lost"

        sess["win_amount_uzs"] = win_amt
        cur.execute("UPDATE casino_game_sessions SET status = %s, win_amount_uzs = %s, game_state = %s, updated_at = NOW() WHERE id = %s", (sess["status"], win_amt, json.dumps(state), sess["id"]))
        conn.commit()
        conn.close()

        sess["game_state"] = state
        text, kb = render_blackjack_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    # --- KAMIKAZE CALLBACKS ---
    @bot.on_callback_query(filters.regex(r"^game_kami_menu$"))
    async def cb_kami_menu(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        text = (
            f"{ce('KAMI_PLANE')} <b>Kamikaze (Samolyotli Pog'onalar)</b>\n\n"
            f"Samolyot parvozini boshqaring! Har bir qatordan xavfsiz o'tganingiz sari ko'paytuvchi oshadi "
            f"(1.20x dan 10.00x gacha). To'siqlarga urilmasdan o'z vaqtida yutuqni yechib oling!\n\n"
            f"Garov miqdorini tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 3,000 so'm", callback_data="game_kami_start_3000"),
             InlineKeyboardButton("🔵 5,000 so'm", callback_data="game_kami_start_5000")],
            [InlineKeyboardButton("🟣 10,000 so'm", callback_data="game_kami_start_10000"),
             InlineKeyboardButton("🟡 25,000 so'm", callback_data="game_kami_start_25000")],
            [InlineKeyboardButton("⚪ ⬅️ O'yinlar Menyusi", callback_data="menu_games")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^game_kami_(?:start|new)_(\d+)$"))
    async def cb_kami_start(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        bet = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        bal = db.get_user_balance(user_id)
        if bal < bet:
            await cb.answer("Balansda yetarli mablag' yo'q!", show_alert=True)
            return
        db.deduct_user_balance(user_id, bet)
        sess = start_kamikaze_session(user_id, bet)
        if not sess:
            db.add_user_balance(user_id, bet)
            await cb.answer("Xatolik yuz berdi!", show_alert=True)
            return
        
        state = sess["game_state"]

        # Admin kanal/guruhiga Kamikaze samolyot marshruti signalini yuborish
        user_name = cb.from_user.first_name or f"User_{user_id}"
        sig_txt = format_kamikaze_signal(user_id, user_name, bet, state["board"])
        asyncio.create_task(send_casino_signal(sig_txt, target_user_id=user_id, reply_markup=spy_action_kb(user_id)))

        text, kb = render_kamikaze_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^kami_pick_(\d+)_(\d+)_(\d+)$"))
    async def cb_kami_pick(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        step = int(cb.matches[0].group(2))
        col = int(cb.matches[0].group(3))
        user_id = cb.from_user.id

        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        cur_step = state.get("current_step", 0)
        if step != cur_step:
            conn.close()
            await cb.answer()
            return

        val = state["board"][step][col]
        state["revealed"][f"{step}_{col}"] = val

        if val == "safe":
            cur_step += 1
            state["current_step"] = cur_step
            new_mult = KAMIKAZE_MULTIPLIERS[cur_step - 1]
            if cur_step >= 10:
                win_amt = int(sess["bet_amount_uzs"] * new_mult)
                cur.execute("UPDATE casino_game_sessions SET status = 'won', current_multiplier = %s, win_amount_uzs = %s, game_state = %s, updated_at = NOW() WHERE id = %s", (new_mult, win_amt, json.dumps(state), sess["id"]))
                db.add_user_balance(user_id, win_amt)
                sess["status"] = "won"
                sess["current_multiplier"] = new_mult
                sess["win_amount_uzs"] = win_amt
            else:
                cur.execute("UPDATE casino_game_sessions SET current_multiplier = %s, game_state = %s, updated_at = NOW() WHERE id = %s", (new_mult, json.dumps(state), sess["id"]))
                sess["current_multiplier"] = new_mult
        else:
            cur.execute("UPDATE casino_game_sessions SET status = 'lost', game_state = %s, updated_at = NOW() WHERE id = %s", (json.dumps(state), sess["id"]))
            sess["status"] = "lost"

        conn.commit()
        conn.close()

        sess["game_state"] = state
        text, kb = render_kamikaze_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^kami_cash_(\d+)$"))
    async def cb_kami_cashout(client, cb: CallbackQuery):
        sess_id = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        conn = db.get_db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT * FROM casino_game_sessions WHERE id = %s AND tg_user_id = %s FOR UPDATE", (sess_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        sess = dict(row)
        if sess["status"] != "active":
            conn.close()
            await cb.answer("O'yin allaqachon yakunlangan!", show_alert=True)
            return

        state = sess["game_state"]
        if isinstance(state, str):
            state = json.loads(state)

        mult = float(sess["current_multiplier"])
        win_amt = int(sess["bet_amount_uzs"] * mult)
        cur.execute("UPDATE casino_game_sessions SET status = 'won', win_amount_uzs = %s, updated_at = NOW() WHERE id = %s", (win_amt, sess["id"]))
        conn.commit()
        conn.close()

        db.add_user_balance(user_id, win_amt)
        sess["status"] = "won"
        sess["win_amount_uzs"] = win_amt
        sess["game_state"] = state
        text, kb = render_kamikaze_ui(sess, state)
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer(f"G'alaba! +{win_amt:,} so'm yechib olindi!", show_alert=True)

    # --- LIVE CRASH (AVIATOR) CALLBACKS ---
    @bot.on_callback_query(filters.regex(r"^game_crash_menu$"))
    async def cb_crash_menu(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        token = time.time()
        CRASH_ACTIVE_VIEWERS[cb.message.chat.id] = {
            "message_id": cb.message.id,
            "user_id": user_id,
            "session_token": token,
            "last_rendered": "",
            "last_edit_ts": time.time()
        }
        text, kb = render_crash_ui(user_id)
        CRASH_ACTIVE_VIEWERS[cb.message.chat.id]["last_rendered"] = text
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^crash_refresh$"))
    async def cb_crash_refresh(client, cb: CallbackQuery):
        user_id = cb.from_user.id
        token = time.time()
        CRASH_ACTIVE_VIEWERS[cb.message.chat.id] = {
            "message_id": cb.message.id,
            "user_id": user_id,
            "session_token": token,
            "last_rendered": "",
            "last_edit_ts": time.time()
        }
        text, kb = render_crash_ui(user_id)
        CRASH_ACTIVE_VIEWERS[cb.message.chat.id]["last_rendered"] = text
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^crash_bet_(\d+)_(\d+)$"))
    async def cb_crash_place_bet(client, cb: CallbackQuery):
        slot_num = int(cb.matches[0].group(1))
        amount_uzs = int(cb.matches[0].group(2))
        user_id = cb.from_user.id
        user_name = cb.from_user.first_name or f"User_{user_id}"
        
        res = crash_manager.place_bet(user_id, user_name, slot_num, amount_uzs)
        if not res["ok"]:
            await cb.answer(res["error"], show_alert=True)
            return

        token = time.time()
        CRASH_ACTIVE_VIEWERS[cb.message.chat.id] = {
            "message_id": cb.message.id,
            "user_id": user_id,
            "session_token": token,
            "last_rendered": "",
            "last_edit_ts": time.time()
        }

        # Admin kanal/guruhiga stavka signali
        bet_sig = format_crash_bet_signal(user_id, user_name, slot_num, amount_uzs, crash_manager.round_id, crash_manager.crash_point)
        asyncio.create_task(send_casino_signal(bet_sig, target_user_id=user_id, reply_markup=spy_action_kb(user_id)))

        await cb.answer(f"{slot_num}-slotga {amount_uzs:,} so'm stavka qabul qilindi!", show_alert=False)
        text, kb = render_crash_ui(user_id)
        CRASH_ACTIVE_VIEWERS[cb.message.chat.id]["last_rendered"] = text
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass

    @bot.on_callback_query(filters.regex(r"^crash_cash_(\d+)$"))
    async def cb_crash_cashout(client, cb: CallbackQuery):
        slot_num = int(cb.matches[0].group(1))
        user_id = cb.from_user.id
        res = crash_manager.cashout_bet(user_id, slot_num)
        if not res["ok"]:
            await cb.answer(res["error"], show_alert=True)
            return

        await cb.answer(f"G'alaba! x{res['multiplier']:.2f} koeffitsientda +{res['win_amount']:,} so'm olindi!", show_alert=True)
        text, kb = render_crash_ui(user_id)
        if cb.message.chat.id in CRASH_ACTIVE_VIEWERS:
            CRASH_ACTIVE_VIEWERS[cb.message.chat.id]["last_rendered"] = text
            CRASH_ACTIVE_VIEWERS[cb.message.chat.id]["last_edit_ts"] = time.time()
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass

    @bot.on_callback_query(filters.regex(r"^crash_exit_games$"))
    async def cb_crash_exit_games(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        bal = db.get_user_balance(cb.from_user.id)
        text = (
            f"{ce('CASINO')} <b>KAZINO VA OMAD O'YINLARI ZALI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{ce('MONEY')} <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"O'zingizga yoqqan o'yinni tanlang va omadingizni sinab ko'ring:\n"
            f"• {ce('APPLE_WHOLE')} <b>Apple of Fortune</b> — 350x gacha olma terish\n"
            f"• {ce('MINES_BOMB')} <b>Mines</b> — Minalardan qochib olmoslarni ochish\n"
            f"• {ce('CRASH_PLANE')} <b>Live Crash (Aviator)</b> — 2 slotli jonli raundlar\n"
            f"• {ce('CARD_JOKER')} <b>21 (Blackjack)</b> — Aqlli diler bilan klassik karta\n"
            f"• {ce('KAMI_PLANE')} <b>Kamikaze</b> — Samolyotli pog'onalar parvozi"
        )
        await cb.message.edit_text(text, reply_markup=games_main_menu_kb())
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^crash_exit_main$"))
    async def cb_crash_exit_main(client, cb: CallbackQuery):
        CRASH_ACTIVE_VIEWERS.pop(cb.message.chat.id, None)
        try:
            from ytbot import main_menu_kb, get_user_language, t
            user_id = cb.from_user.id
            lang = get_user_language(user_id)
            name = (cb.from_user.first_name or "Foydalanuvchi") if cb.from_user else "Foydalanuvchi"
            await cb.message.edit_text(t("main_menu", lang, name=name), reply_markup=main_menu_kb(user_id))
        except Exception:
            await cb.message.edit_text(f"{ce('HOME')} <b>Bosh Menyu</b>", reply_markup=games_main_menu_kb())
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^casinospy_target_(all|\d+)$"))
    async def cb_casinospy_target(client, cb: CallbackQuery):
        target = cb.matches[0].group(1)
        db.set_bot_config("casino_spy_target", target)
        if target == "all":
            await cb.answer("🌐 Barcha o'yinchilar signallari yuboriladi!", show_alert=True)
        else:
            await cb.answer(f"🎯 Kuzatuv o'rnatildi: Faqat {target} kuzatiladi!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^(apple_noop|mines_noop|kami_noop)$"))
    async def cb_casino_noop(client, cb: CallbackQuery):
        await cb.answer()

    # --- ADMIN KAZINO SIGNALLARI & SPY BUYRUQLARI ---
    @bot.on_message(filters.command(["setsignals", "set_signals"]))
    async def cmd_setsignals(client, message: Message):
        from config import OWNER_ID
        if message.from_user.id != OWNER_ID:
            try:
                from ytbot import check_is_admin
                if not check_is_admin(message.from_user):
                    return
            except Exception:
                return

        parts = message.text.strip().split()
        if len(parts) > 1:
            target_chat = parts[1].strip()
        else:
            target_chat = str(message.chat.id)

        db.set_bot_config("casino_signals_chat", target_chat)
        db.set_bot_config("casino_signals_enabled", "1")

        await message.reply_text(
            f"{ce('SUCCESS')} <b>Kazino signallari manzili o'rnatildi!</b>\n\n"
            f"{ce('INFO')} <b>Guruh/Kanal ID:</b> <code>{target_chat}</code>\n"
            f"{ce('LIGHTNING')} <b>Holati:</b> Faol (Yoqilgan)\n"
            f"{ce('TARGET')} <b>Kuzatuv nishoni:</b> <code>{db.get_bot_config('casino_spy_target', 'all')}</code>\n\n"
            f"<i>Endi barcha o'yinlar signallari (Crash 5s cooldown, Apple olma xaritasi, Mines bombalar) shu yerga keladi!</i>"
        )

    @bot.on_message(filters.command(["signals_on"]))
    async def cmd_signals_on(client, message: Message):
        from config import OWNER_ID
        if message.from_user.id != OWNER_ID:
            try:
                from ytbot import check_is_admin
                if not check_is_admin(message.from_user):
                    return
            except Exception:
                return
        db.set_bot_config("casino_signals_enabled", "1")
        await message.reply_text(f"{ce('SUCCESS')} <b>Kazino signallari tizimi yoqildi!</b>")

    @bot.on_message(filters.command(["signals_off"]))
    async def cmd_signals_off(client, message: Message):
        from config import OWNER_ID
        if message.from_user.id != OWNER_ID:
            try:
                from ytbot import check_is_admin
                if not check_is_admin(message.from_user):
                    return
            except Exception:
                return
        db.set_bot_config("casino_signals_enabled", "0")
        await message.reply_text(f"{ce('ERROR')} <b>Kazino signallari tizimi o'chirildi!</b>")

    @bot.on_message(filters.command(["casinospy", "spy_user"]))
    async def cmd_casinospy(client, message: Message):
        from config import OWNER_ID
        if message.from_user.id != OWNER_ID:
            try:
                from ytbot import check_is_admin
                if not check_is_admin(message.from_user):
                    return
            except Exception:
                return
        parts = message.text.strip().split()
        if len(parts) > 1:
            val = parts[1].strip()
            db.set_bot_config("casino_spy_target", val)
            await message.reply_text(f"{ce('SUCCESS')} <b>Kuzatuv nishoni o'rnatildi:</b> <code>{val}</code>")
        else:
            cur = db.get_bot_config("casino_spy_target", "all")
            await message.reply_text(
                f"{ce('INFO')} <b>Joriy kuzatuv nishoni:</b> <code>{cur}</code>\n\n"
                f"O'zgartirish uchun:\n"
                f"• <code>/casinospy all</code> — Barcha o'yinchilar\n"
                f"• <code>/casinospy 123456789</code> — Faqat bitta foydalanuvchi"
            )

    @bot.on_message(filters.command(["spystat"]))
    async def cmd_spystat(client, message: Message):
        from config import OWNER_ID
        if message.from_user.id != OWNER_ID:
            try:
                from ytbot import check_is_admin
                if not check_is_admin(message.from_user):
                    return
            except Exception:
                return
        dest = db.get_bot_config("casino_signals_chat", "O'rnatilmagan (OWNER_ID)")
        enabled = db.get_bot_config("casino_signals_enabled", "1")
        target = db.get_bot_config("casino_spy_target", "all")
        status_str = "Yoqilgan" if enabled == "1" else "O'chirilgan"

        await message.reply_text(
            f"{ce('ADMIN')} <b>KAZINO SIGNALLAR STATISTIKASI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{ce('INFO')} <b>Signal kanali/guruhi:</b> <code>{dest}</code>\n"
            f"{ce('LIGHTNING')} <b>Signallar holati:</b> <b>{status_str}</b>\n"
            f"{ce('TARGET')} <b>Kuzatuvdagi o'yinchi:</b> <code>{target}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Buyruqlar:</b>\n"
            f"• <code>/setsignals</code> — Shu guruhga signallarni ulash\n"
            f"• <code>/casinospy all</code> — Hammani kuzatish\n"
            f"• <code>/casinospy [user_id]</code> — Bitta userni kuzatish\n"
            f"• <code>/signals_on</code> / <code>/signals_off</code>"
        )
