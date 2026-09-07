"""
Mega Features Hub for YouTube Automation & Analytics Bot.
9 ta Katta Mahsulot va Tizimli Yangilanishlarni Pyrogram botiga ulash:
1. Gemini AI Support Desk & Live Admin Hand-off (4 rol, 5 ta til, 2 tomonlama xabarlashuv)
2. P2P Conditional Cheklar (@wallet style) & Antifraud Sentinel
3. Instagram Account Auto-Cloner & 8-Layer Reposter
4. CapCut Desktop & Pro Tools Referral Hub
5. Admin Promo Codes (/newpromo) & User Redemption (/redeem)
6. 100% Free AI Video Generator Engine (Pollinations + Edge-TTS + FFmpeg)
7. YouTube Competitor Spy & SEO Stealer
8. Balance Cashout (Stars & TON)
9. Smart DeepLink & QR Generator
"""

import os
import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message
)
from config import OWNER_ID
from custom_emojis import e
from locales import t
import database as db

# Modullarni import qilish
from support_desk import (
    SUPPORT_ROLES, WAITING_MESSAGES,
    get_support_menu_keyboard, get_role_view_keyboard,
    generate_support_answer, forward_to_admin
)
from vouchers_engine import (
    RED_ANTIFRAUD_WARNING, create_p2p_check,
    get_check_claim_keyboard, process_check_claim
)
from instagram_cloner import (
    add_instagram_target, get_instagram_targets,
    remove_instagram_target, sync_instagram_account_now
)
from capcut_exchange import (
    CAPCUT_GUIDE_TEXT, submit_referral_link,
    get_next_invite_link, get_capcut_menu_keyboard
)
from promo_engine import admin_create_promo, user_redeem_promo
from pollinations_engine import build_ai_short_video
from competitor_spy import analyze_and_steal_seo
from cashout import (
    request_user_cashout, notify_admin_new_cashout,
    handle_admin_cashout_decision, MIN_CASHOUT_UZS
)
from deeplink_engine import generate_smart_deeplinks, generate_qr_code_image
from autopost import upload_to_youtube

logger = logging.getLogger(__name__)

# Foydalanuvchilarning suhbat holatlari (FSM)
USER_STATES = {}

def check_antifraud_or_blocked(user_id: int) -> bool:
    """Foydalanuvchi antifraud tizimida bloklanganmi?"""
    return db.is_user_antifraud_banned(user_id)

def load_mega_features(bot: Client):

    # ==================== ANTIFRAUD TEKSHIRUVI (GLOBAL FILTER) ====================
    @bot.on_message(group=-1)
    async def global_antifraud_gate(client, message: Message):
        if not message.from_user:
            return
        uid = message.from_user.id
        if check_antifraud_or_blocked(uid):
            await message.reply_text(
                "🚫 **HISOBINGIZ BUTUNLAY BLOKLANGAN!**\n\n"
                "Siz shartli chek olganingizdan so'ng homiy kanaldan chiqib ketgansiz.\n"
                "Qat'iy xavfsizlik qoidalariga asosan siz uchun bot xizmatlari va balansingiz muzlatilgan."
            )
            message.stop_propagation()

    @bot.on_callback_query(group=-1)
    async def global_antifraud_cb_gate(client, cb: CallbackQuery):
        if not cb.from_user:
            return
        uid = cb.from_user.id
        try:
            if check_antifraud_or_blocked(uid):
                await cb.answer("🚫 Siz qoidabuzarlik sababli botdan bloklangansiz!", show_alert=True)
                cb.stop_propagation()
        except Exception as e:
            logger.error(f"global_antifraud_cb_gate error: {e}")

    # =========================================================================
    # 1. SUPPORT DESK & LIVE ADMIN BRIDGE
    # =========================================================================
    @bot.on_message(filters.command(["support", "yordam", "helpdesk"]) & filters.private)
    async def support_cmd(client, message: Message):
        uid = message.from_user.id
        lang = db.get_user_language(uid)
        kb = get_support_menu_keyboard(lang)
        text = (
            f"🤝 **Yordam & Qo'llab-quvvatlash Markazi**\n\n"
            f"Kerakli bo'limni tanlang. Sun'iy intellekt (Gemini AI) savollaringizga "
            f"24/7 rejimda javob beradi yoki to'g'ridan-to'g'ri admin bilan jonli bog'laydi:"
        )
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^menu_support_desk$"))
    async def cb_support_desk_root(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        lang = db.get_user_language(uid)
        kb = get_support_menu_keyboard(lang)
        try:
            await cb.message.edit_text(
                f"🤝 **Yordam & Qo'llab-quvvatlash Markazi**\n\n"
                f"Kerakli bo'limni tanlang. Sun'iy intellekt yoki Jonli Admin sizga xizmat ko'rsatadi:",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"cb_support_desk_root error: {e}")

    @bot.on_callback_query(filters.regex(r"^support_desk_root$"))
    async def cb_support_desk_back(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        lang = db.get_user_language(uid)
        try:
            await cb.message.edit_text(
                f"🤝 **Yordam & Qo'llab-quvvatlash Markazi**\n\nKerakli yo'nalishni tanlang:",
                reply_markup=get_support_menu_keyboard(lang)
            )
        except Exception as e:
            logger.error(f"cb_support_desk_back error: {e}")

    @bot.on_callback_query(filters.regex(r"^supp_role_([a-z_]+)$"))
    async def cb_support_role(client, cb: CallbackQuery):
        role_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        lang = db.get_user_language(uid)
        role_data = SUPPORT_ROLES.get(role_key, SUPPORT_ROLES["faq"])
        title = role_data["title"].get(lang, role_data["title"]["uz"])
        desc = role_data["desc"].get(lang, role_data["desc"]["uz"])

        text = (
            f"{title}\n\n"
            f"ℹ️ {desc}\n\n"
            f"Savolingizga zudlik bilan javob olish uchun **«Savol berish (AI)»** tugmasini bosing "
            f"yoki shaxsan adminga xat yo'llang:"
        )
        await cb.message.edit_text(text, reply_markup=get_role_view_keyboard(role_key, lang))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^supp_ask_([a-z_]+)$"))
    async def cb_support_ask_ai(client, cb: CallbackQuery):
        role_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        USER_STATES[uid] = {"action": "waiting_support_ai", "role": role_key}
        await cb.message.reply_text("✍️ **Savolingizni yozib yuboring:**\n(Gemini AI sizga professional javob tayyorlaydi)")
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^supp_live_([a-z_]+)$"))
    async def cb_support_live_admin(client, cb: CallbackQuery):
        role_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        USER_STATES[uid] = {"action": "waiting_support_live", "role": role_key}
        await cb.message.reply_text("👤 **Adminga yetkazilishi kerak bo'lgan xabaringizni yozing:**\n(Xabar bevosita bosh adminga yuboriladi)")
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^adm_rep_ticket_(\d+)_(\d+)$"))
    async def cb_admin_reply_ticket(client, cb: CallbackQuery):
        if cb.from_user.id != OWNER_ID:
            await cb.answer("Faqat bot egasi javob yozishi mumkin!", show_alert=True)
            return
        ticket_id = int(cb.matches[0].group(1))
        target_uid = int(cb.matches[0].group(2))
        USER_STATES[cb.from_user.id] = {
            "action": "admin_replying",
            "ticket_id": ticket_id,
            "target_user_id": target_uid
        }
        await cb.message.reply_text(f"✍️ **Foydalanuvchiga ({target_uid}) yuboriladigan javob xabaringizni yozing:**")
        await cb.answer()

    # =========================================================================
    # 2. P2P CONDITIONAL CHEKLAR & ANTIFRAUD
    # =========================================================================
    @bot.on_message(filters.command(["check", "chek"]) & filters.private)
    async def check_cmd(client, message: Message):
        uid = message.from_user.id
        parts = message.command
        if len(parts) < 3:
            await message.reply_text(
                "💸 **P2P Shartli Chek Yaratish:**\n\n"
                "Format: `/check <umumiy_summa> <odam_soni> [@homiy_kanal]`\n\n"
                "Misol: `/check 50000 5 @mening_kanalim`\n"
                "(50,000 so'm 5 kishiga 10,000 so'mdan tarqatiladi. Kanal obunachilari oladi)."
            )
            return

        try:
            total_amt = int(parts[1])
            claims_count = int(parts[2])
            req_channel = parts[3] if len(parts) > 3 else None
        except ValueError:
            await message.reply_text("❌ Summa va odam soni raqam bo'lishi kerak!")
            return

        ok, msg, code = create_p2p_check(uid, total_amt, claims_count, req_channel)
        if not ok:
            await message.reply_text(f"❌ Xatolik: {msg}")
            return

        share_kb = get_check_claim_keyboard(code, req_channel)
        ch_text = f"\n📢 **Shart:** @{req_channel.strip().lstrip('@')} kanaliga a'zo bo'lish" if req_channel else ""
        text = (
            f"💸 **Yangi Chek Yaratildi!**\n\n"
            f"💰 **Umumiy summa:** `{total_amt:,}` so'm\n"
            f"👥 **Qabul qiluvchilar soni:** `{claims_count}` ta\n"
            f"💵 **Har biriga:** `{int(total_amt/claims_count):,}` so'm{ch_text}\n\n"
            f"🔗 **Chek Kodi:** `{code}`\n\n"
            f"{RED_ANTIFRAUD_WARNING}"
        )
        await message.reply_text(text, reply_markup=share_kb)

    @bot.on_callback_query(filters.regex(r"^menu_vouchers$"))
    async def cb_menu_vouchers(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        bal = db.get_user_balance(uid)
        text = (
            f"💸 **P2P Shartli Cheklar Tizimi (@wallet uslubida)**\n\n"
            f"💰 **Balansingiz:** `<b>{bal:,} so'm</b>`\n\n"
            f"Siz o'z balansingizdan do'stlaringizga yoki kanalingiz auditoriyasiga chek tarqatishingiz mumkin.\n"
            f"Chekni olish uchun majburiy kanal a'zoligi shartini qo'yishingiz mumkin!\n\n"
            f"Yaratish uchun buyruq:\n"
            f"`/check <summa> <odam_soni> [@kanal]`\n\n"
            f"{RED_ANTIFRAUD_WARNING}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi Chek Yaratish Qo'llanmasi", callback_data="help_create_check")],
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception as e:
            logger.error(f"cb_menu_vouchers error: {e}")

    @bot.on_callback_query(filters.regex(r"^claim_chk_([A-Za-z0-9_-]+)$"))
    async def cb_claim_check(client, cb: CallbackQuery):
        check_code = cb.matches[0].group(1)
        uid = cb.from_user.id
        ok, res = await process_check_claim(client, uid, check_code)
        if not ok:
            await cb.answer(res, show_alert=True)
            return

        await cb.message.reply_text(res)
        await cb.answer("Chek qabul qilindi!", show_alert=False)

    # =========================================================================
    # 3. INSTAGRAM AUTO-KLONER & 8-LAYER REPOSTER
    # =========================================================================
    @bot.on_message(filters.command(["igcloner", "igsync"]) & filters.private)
    async def ig_cloner_cmd(client, message: Message):
        uid = message.from_user.id
        targets = get_instagram_targets(uid)
        ch_list = "\n".join([f"• @{t['ig_username']} (Interval: {t['check_interval_mins']} daqiqa)" for t in targets]) if targets else "Hozircha kuzatilayotgan profillar yo'q."

        text = (
            f"📸 **Instagram Account Auto-Cloner & Reposter**\n\n"
            f"Belgilangan Instagram profiliga yangi Reel yuklanganda, bot uni darhol "
            f"yuklab oladi, 8-qatlamli unikalizatsiya (anti-copyright) qiladi va "
            f"ulangan YouTube kanalingizga avtomatik Shorts qilib joylaydi!\n\n"
            f"📋 **Kuzatilayotgan profillaringiz:**\n{ch_list}\n\n"
            f"Yangi profil qo'shish uchun: `/igcloner add @username`\n"
            f"O'chirish uchun: `/igcloner del @username`\n"
            f"Hozir sinash uchun: `/igcloner sync @username`"
        )
        parts = message.command
        if len(parts) >= 3:
            action = parts[1].lower()
            target_username = parts[2].strip().lstrip("@")
            if action == "add":
                add_instagram_target(uid, target_username)
                await message.reply_text(f"✅ `@{target_username}` muvaffaqiyatli kuzatuvga qo'shildi!")
                return
            elif action == "del":
                remove_instagram_target(uid, target_username)
                await message.reply_text(f"🗑 `@{target_username}` kuzatuvdan olib tashlandi.")
                return
            elif action == "sync":
                res = await sync_instagram_account_now(uid, target_username, app=client, chat_id=message.chat.id)
                await message.reply_text(f"Natija: {res.get('message')}")
                return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")],
            [InlineKeyboardButton("🔄 Hozir Tekshirish & Yuklash", callback_data="ig_sync_now")],
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="main_menu")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^menu_ig_cloner$"))
    async def cb_menu_ig_cloner(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        targets = get_instagram_targets(uid)
        ch_list = "\n".join([f"• @{t['ig_username']}" for t in targets]) if targets else "Hozircha kuzatilayotgan profillar yo'q."
        text = (
            f"📸 **Instagram Account Auto-Cloner**\n\n"
            f"Siz kiritgan Instagram profilidagi Reels'lar 8-qatlamli unikalizatsiya bilan "
            f"to'g'ridan-to'g'ri YouTube Shorts ga nusxalanadi.\n\n"
            f"📋 **Profillar:**\n{ch_list}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")],
            [InlineKeyboardButton("🔄 Tekshirish & Yuklash", callback_data="ig_sync_now")],
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception as e:
            logger.error(f"cb_menu_ig_cloner error: {e}")

    @bot.on_callback_query(filters.regex(r"^ig_add_profile$"))
    async def cb_ig_add_profile(client, cb: CallbackQuery):
        await cb.answer()
        USER_STATES[cb.from_user.id] = {"action": "waiting_ig_profile"}
        await cb.message.reply_text("📸 **Instagram username yuboring:** (masalan: `@cristiano` yoki `selenagomez`)")

    @bot.on_callback_query(filters.regex(r"^ig_sync_now$"))
    async def cb_ig_sync_now(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        targets = get_instagram_targets(uid)
        if not targets:
            await cb.message.reply_text("⚠️ Avval kamida 1 ta Instagram profil qo'shing!")
            return
        await cb.message.reply_text("🔄 **Tekshiruv boshlanmoqda...** Yangi videolar avtomatik yuklanadi.")
        for t in targets:
            await sync_instagram_account_now(uid, t["ig_username"], app=client, chat_id=cb.message.chat.id)

    # =========================================================================
    # 4. CAPCUT DESKTOP & PRO TOOLS REFERRAL HUB
    # =========================================================================
    @bot.on_message(filters.command(["capcut", "capcutpro"]) & filters.private)
    async def capcut_cmd(client, message: Message):
        kb = get_capcut_menu_keyboard()
        await message.reply_text(CAPCUT_GUIDE_TEXT, reply_markup=kb, disable_web_page_preview=True)

    @bot.on_callback_query(filters.regex(r"^menu_capcut$"))
    async def cb_menu_capcut(client, cb: CallbackQuery):
        await cb.answer()
        try:
            await cb.message.edit_text(CAPCUT_GUIDE_TEXT, reply_markup=get_capcut_menu_keyboard(), disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"cb_menu_capcut error: {e}")

    @bot.on_callback_query(filters.regex(r"^capcut_get_pro$"))
    async def cb_capcut_get_pro(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        ref = get_next_invite_link(exclude_user_id=uid)
        fallback_link = "https://www.capcut.com/capcut_pc_web/fission_receive?code=AIIt3z29586914&lng=en"
        link = ref.get("invite_link") if ref else fallback_link
        text = (
            f"🎁 **CapCut Pro Bepul Havolangiz:**\n\n"
            f"🔗 [CapCut Desktop-ni Yuklab Olish (7 kun bepul Pro)]({link})\n\n"
            f"Kompyuteringizda ushbu havola orqali CapCut Desktop o'rnating va 7 kun bepul Pro oling!\n"
            f"O'z taklif havolangizni botga qo'shib muddatni 70 kungacha uzaytirishingiz mumkin."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ O'z Havolamni Qo'shish", callback_data="capcut_add_link")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_capcut")]
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb, disable_web_page_preview=False)
        except Exception as e:
            logger.error(f"cb_capcut_get_pro error: {e}")

    @bot.on_callback_query(filters.regex(r"^capcut_add_link$"))
    async def cb_capcut_add_link(client, cb: CallbackQuery):
        USER_STATES[cb.from_user.id] = {"action": "waiting_capcut_link"}
        await cb.message.reply_text(
            "➕ **CapCut Desktop taklif havolangizni yuboring:**\n\n"
            "(CapCut kompyuter dasturida 'Invite Friends' bo'limidan olingan havola)"
        )
        await cb.answer()

    # =========================================================================
    # 5. ADMIN PROMO CODES (/newpromo) & USER REDEMPTION (/redeem)
    # =========================================================================
    @bot.on_message(filters.command("newpromo") & filters.private)
    async def new_promo_cmd(client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("❌ Faqat bosh admin promokod yarata oladi.")
            return

        parts = message.command
        if len(parts) < 3:
            await message.reply_text("Format: `/newpromo <KOD> <BONUS_UZS> [MAKS_FOYDALANISH]`\nMasalan: `/newpromo MEGA2026 25000 100`")
            return

        code = parts[1]
        try:
            bonus = int(parts[2])
            limit = int(parts[3]) if len(parts) > 3 else 100
        except ValueError:
            await message.reply_text("❌ Bonus va limit raqam bo'lishi kerak!")
            return

        ok, res = admin_create_promo(code, bonus, limit)
        await message.reply_text(res)

    @bot.on_message(filters.command("redeem") & filters.private)
    async def redeem_cmd(client, message: Message):
        parts = message.command
        if len(parts) < 2:
            USER_STATES[message.from_user.id] = {"action": "waiting_promo_code"}
            await message.reply_text("🎟 **Promokodingizni kiriting:**")
            return

        code = parts[1]
        ok, res = user_redeem_promo(message.from_user.id, code)
        await message.reply_text(res)

    @bot.on_callback_query(filters.regex(r"^enter_promo_code$"))
    async def cb_enter_promo_code(client, cb: CallbackQuery):
        USER_STATES[cb.from_user.id] = {"action": "waiting_promo_code"}
        await cb.message.reply_text("🎟 **Iltimos, promokodingizni yozib yuboring:**")
        await cb.answer()

    # =========================================================================
    # 6. 100% BEPUL AI VIDEO GENERATOR (POLLINATIONS + EDGE-TTS)
    # =========================================================================
    @bot.on_message(filters.command(["aivideo", "genvideo"]) & filters.private)
    async def aivideo_cmd(client, message: Message):
        uid = message.from_user.id
        is_sub = db.is_user_ai_video_subscribed(uid)
        bal = db.get_user_balance(uid)
        if not is_sub and bal < 15000:
            text = (
                "🎬 **AI Video Studio ($20 / oy)**\n\n"
                "Ushbu xizmat pullik bo'lib, professional 9:16 vertikal Shorts/Reels tayyorlaydi:\n"
                "• 🎨 **Flux.1 Ultra AI** — 4K tasvirlar\n"
                "• 🎙 **Neural Edge-TTS** — 5 ta tilda tabiiy diktor ovozi\n"
                "• 🎬 **FFmpeg Ken Burns FX** — Dinamik animatsiya va audio montaj\n\n"
                "💎 **Tariflar:**\n"
                "• 👑 **Oylik Cheksiz Obuna:** <b>$20 / oy</b> (256,000 so'm)\n"
                "• ⭐ **Telegram Stars:** 1,000 ⭐\n"
                "• 🎞 **1 ta Video:** 15,000 so'm / video\n\n"
                f"💳 **Balansingiz:** <code>{bal:,} so'm</code>\n\n"
                "Tarifni tanlang:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Oylik Obuna ($20 - 256,000 so'm)", callback_data="aivid_buy_sub")],
                [InlineKeyboardButton("⭐ 1,000 Stars bilan Olish", callback_data="aivid_buy_stars")],
                [InlineKeyboardButton("🎞 1 ta Video (15,000 so'm)", callback_data="aivid_buy_single")],
                [InlineKeyboardButton("💰 Hisobni To'ldirish", callback_data="menu_wallet")],
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])
            await message.reply_text(text, reply_markup=kb)
            return

        parts = message.command
        if len(parts) < 2:
            USER_STATES[uid] = {"action": "waiting_aivideo_prompt" if is_sub else "waiting_aivideo_prompt_single"}
            note = "Faol $20/oy obuna (Cheksiz)" if is_sub else "1 ta video: 15,000 so'm (balansdan yechiladi)"
            await message.reply_text(
                f"🎬 **AI Video Studio ({note})**\n\n"
                "✍️ **Video mavzusini yozing:** (masalan: *Kosmos sirlari va qora tuynuklar*)"
            )
            return

        prompt = " ".join(parts[1:])
        if not is_sub:
            res_fee = db.deduct_single_ai_video_fee(uid)
            if not res_fee.get("ok"):
                await message.reply_text(f"❌ {res_fee.get('error', 'Balans yetarli emas')}")
                return

        wait_m = await message.reply_text("⏳ **AI video yaratilmoqda...**\n(Flux rasm + Diktor ovozi + FFmpeg montaj ~30-40 soniya)")
        try:
            lang = db.get_user_language(uid)
            video_data = await build_ai_short_video(prompt, lang=lang)
            v_path = video_data["video_path"]
            title = video_data["title"]

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 YouTube Kanalimga Yuklash", callback_data=f"pub_aivid_{os.path.basename(v_path)}")],
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])

            await client.send_video(
                chat_id=message.chat.id,
                video=v_path,
                caption=f"🎬 **{title}**\n\n{video_data['script']}",
                reply_markup=kb,
                supports_streaming=True
            )
            await wait_m.delete()
        except Exception as e:
            logger.error(f"AI Video xato: {e}")
            await wait_m.edit_text(f"❌ Xatolik yuz berdi: {e}")

    @bot.on_callback_query(filters.regex(r"^menu_ai_video$"))
    async def cb_menu_ai_video(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        is_sub = db.is_user_ai_video_subscribed(uid)
        if not is_sub:
            bal = db.get_user_balance(uid)
            text = (
                "🎬 **AI Video Studio ($20 / oy)**\n\n"
                "Ushbu xizmat professional sun'iy intellekt orqali to'liq avtomatlashtirilgan video tayyorlash studiyasidir:\n"
                "• 🎨 **Flux.1 Ultra AI** — 9:16 kinematografik 4K tasvirlar\n"
                "• 🎙 **Neural Edge-TTS** — 5 ta tilda tabiiy diktor ovozi\n"
                "• 🎬 **Ken Burns FX** — Dinamik kamera harakati va audio montaj\n"
                "• 🚀 **1-Click YouTube Shorts Yuklash**\n\n"
                f"💳 **Sizning balansingiz:** <code>{bal:,} so'm</code>\n\n"
                "💎 **Tariflar:**\n"
                "• 👑 **Oylik Cheksiz Obuna:** <b>$20 / oy</b> (256,000 so'm)\n"
                "• ⭐ **Telegram Stars:** 1,000 ⭐\n"
                "• 🎞 **1 ta Video:** 15,000 so'm / video\n\n"
                "Kerakli tarifni tanlang:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Oylik Obuna ($20 - 256,000 so'm)", callback_data="aivid_buy_sub")],
                [InlineKeyboardButton("⭐ 1,000 Stars bilan Olish", callback_data="aivid_buy_stars")],
                [InlineKeyboardButton("🎞 1 ta Video Yaratish (15,000 so'm)", callback_data="aivid_buy_single")],
                [InlineKeyboardButton("💰 Hisobni To'ldirish", callback_data="menu_wallet")],
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])
            try:
                await cb.message.edit_text(text, reply_markup=kb)
            except Exception as e:
                logger.error(f"cb_menu_ai_video error: {e}")
            return

        USER_STATES[uid] = {"action": "waiting_aivideo_prompt"}
        text = (
            "🎬 **AI Video Studio (Faol Obuna)**\n\n"
            "Sizda faol obuna mavjud! Cheksiz video yaratish rejimi yoqilgan.\n\n"
            "✍️ **Video yaratish uchun mavzuni yozib yuboring:**\n"
            "(Masalan: *Kosmos sirlari va qora tuynuklar* yoki *Qiziqarli faktlar*)"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception as e:
            logger.error(f"cb_menu_ai_video prompt error: {e}")

    @bot.on_callback_query(filters.regex(r"^aivid_buy_sub$"))
    async def cb_aivid_buy_sub(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        res = db.purchase_ai_video_subscription(uid)
        if not res.get("ok"):
            bal = db.get_user_balance(uid)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Balansni To'ldirish", callback_data="menu_wallet")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_ai_video")]
            ])
            await cb.message.edit_text(
                f"❌ <b>Mablag' yetarli emas!</b>\n\n"
                f"AI Video Studio $20/oy (256,000 so'm) obunasi uchun balansingiz yetarli emas.\n"
                f"• Kerak: <code>256,000 so'm</code>\n"
                f"• Balansingiz: <code>{bal:,} so'm</code>\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:",
                reply_markup=kb
            )
            return

        exp = res.get("expires_at", "")
        USER_STATES[uid] = {"action": "waiting_aivideo_prompt"}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Video Yaratish", callback_data="menu_ai_video")],
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(
            f"🎉 <b>Tabriklaymiz! AI Video Studio obunangiz faollashdi!</b>\n\n"
            f"• Amal qilish muddati: <code>{exp}</code> gacha (30 kun)\n"
            f"• Cheksiz video generatsiya faol!\n\n"
            f"Endi video mavzusini chatga yozib yuborishingiz mumkin:",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^aivid_buy_stars$"))
    async def cb_aivid_buy_stars(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        bot_token = os.getenv("BOT_TOKEN")
        from ytbot import _send_bot_api_invoice
        res = await _send_bot_api_invoice(
            bot_token=bot_token,
            chat_id=cb.message.chat.id,
            title="AI Video Studio — $20 / oy Obuna",
            description="30 kun davomida cheksiz 9:16 vertikal AI video generatsiyasi",
            payload=f"aivid_sub_{uid}",
            currency="XTR",
            prices=[{"label": "AI Video Studio ($20)", "amount": 1000}],
            provider_token=""
        )
        if not res:
            await cb.message.reply_text("❌ Stars hisobini ochishda xatolik yuz berdi. Iltimos, /balance orqali balansingizni to'ldiring.")

    @bot.on_callback_query(filters.regex(r"^aivid_buy_single$"))
    async def cb_aivid_buy_single(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        bal = db.get_user_balance(uid)
        if bal < 15000:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Balansni To'ldirish", callback_data="menu_wallet")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_ai_video")]
            ])
            await cb.message.edit_text(
                f"❌ <b>Mablag' yetarli emas!</b>\n\n"
                f"1 ta video yaratish narxi: <code>15,000 so'm</code>\n"
                f"Sizning balansingiz: <code>{bal:,} so'm</code>\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:",
                reply_markup=kb
            )
            return

        USER_STATES[uid] = {"action": "waiting_aivideo_prompt_single"}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Bekor qilish", callback_data="menu_ai_video")]
        ])
        await cb.message.edit_text(
            f"🎞 <b>1 ta AI Video Generatsiyasi (15,000 so'm)</b>\n\n"
            f"Mavzuni yuborganingizdan so'ng balansingizdan 15,000 so'm yechiladi va video tayyorlanadi.\n\n"
            f"✍️ <b>Video mavzusini yozib yuboring:</b>",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^pub_aivid_(.+)$"))
    async def cb_publish_ai_video(client, cb: CallbackQuery):
        await cb.answer("YouTube ga yuklash boshlandi...", show_alert=False)
        uid = cb.from_user.id
        v_name = cb.matches[0].group(1)
        v_path = os.path.join("downloads", v_name)
        if not os.path.exists(v_path):
            await cb.message.reply_text("❌ Video fayli topilmadi.")
            return

        yt_conn = db.get_yt_connection(uid)
        if not yt_conn or not yt_conn.get("access_token"):
            await cb.message.reply_text("⚠️ Avval /ytlogin orqali YouTube kanalingizni ulang!")
            return

        try:
            yt_id = await asyncio.to_thread(
                upload_to_youtube,
                v_path,
                "AI Viral Short #Shorts",
                "Generated with AI Video Studio ($20/mo)\n#shorts #ai #viral",
                yt_conn
            )
            await cb.message.reply_text(f"✅ **Muvaffaqiyatli yuklandi!**\n🔗 [YouTube da ko'rish](https://youtu.be/{yt_id})")
        except Exception as e:
            await cb.message.reply_text(f"❌ Yuklashda xato: {e}")

    # =========================================================================
    # 7. YOUTUBE COMPETITOR SPY & SEO STEALER
    # =========================================================================
    @bot.on_message(filters.command(["spy", "seosteal"]) & filters.private)
    async def spy_cmd(client, message: Message):
        parts = message.command
        if len(parts) < 2:
            USER_STATES[message.from_user.id] = {"action": "waiting_spy_url"}
            await message.reply_text(
                "🔍 **YouTube Competitor Spy & SEO Stealer**\n\n"
                "Raqobatchining videosidan yashirin teglarni va kalit so'zlarni ko'chirib olish "
                "hamda Gemini AI orqali uni ortda qoldiruvchi CTR sarlavhalar olish uchun "
                "video havolasini yuboring:\n\n"
                "Masalan: `/spy https://youtu.be/...`"
            )
            return

        video_url = parts[1]
        wait_m = await message.reply_text("🕵️‍♂️ **Raqobatchi metama'lumotlari va yashirin teglari tahlil qilinmoqda...**")
        try:
            lang = db.get_user_language(message.from_user.id)
            res = await analyze_and_steal_seo(video_url, lang=lang)
            meta = res["meta"]
            tags_str = ", ".join(meta["tags"]) if meta["tags"] else "Yashirin teglar topilmadi."

            report = (
                f"🎯 **RAQOBATCHI TAHLILI NATIJASI:**\n\n"
                f"🎬 **Sarlavha:** {meta['title']}\n"
                f"👤 **Kanal:** {meta['channel']}\n"
                f"👁 **Ko'rishlar:** `{meta['view_count']:,}` ta\n"
                f"👍 **Layklar:** `{meta['like_count']:,}` ta\n\n"
                f"🏷 **YASHIRIN TEGLAR (Keywords):**\n`{tags_str}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🧠 **GEMINI AI SEO TAVSIYALARI:**\n\n"
                f"{res['ai_analysis']}"
            )
            await wait_m.delete()
            await message.reply_text(report)
        except Exception as e:
            await wait_m.edit_text(f"❌ Tahlil xatosi: {e}")

    @bot.on_callback_query(filters.regex(r"^menu_spy$"))
    async def cb_menu_spy(client, cb: CallbackQuery):
        await cb.answer()
        USER_STATES[cb.from_user.id] = {"action": "waiting_spy_url"}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        try:
            await cb.message.edit_text(
                "🔍 **YouTube Competitor Spy & SEO Stealer**\n\n"
                "Tahlil qilmoqchi bo'lgan YouTube video yoki Shorts havolasini yuboring:",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"cb_menu_spy error: {e}")

    # =========================================================================
    # 8. CASHOUT ENGINE (STARS & TON PUL YECHISH)
    # =========================================================================
    @bot.on_message(filters.command(["cashout", "yechish"]) & filters.private)
    async def cashout_cmd(client, message: Message):
        uid = message.from_user.id
        bal = db.get_user_balance(uid)
        text = (
            f"💸 **Hisobdan Pul Yechish (Cashout)**\n\n"
            f"💰 **Mavjud balansingiz:** `{bal:,}` so'm\n"
            f"⚠️ **Minimal yechish summasi:** `{MIN_CASHOUT_UZS:,}` so'm\n\n"
            f"Pul yechish usulini tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Telegram Stars orqali", callback_data="co_method_stars")],
            [InlineKeyboardButton("💎 TON Hamyon (The Open Network)", callback_data="co_method_ton")],
            [InlineKeyboardButton("⬅️ Balans Menyusi", callback_data="menu_wallet")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^menu_cashout$"))
    async def cb_menu_cashout(client, cb: CallbackQuery):
        uid = cb.from_user.id
        bal = db.get_user_balance(uid)
        text = (
            f"💸 **Hisobdan Pul Yechish (Cashout)**\n\n"
            f"💰 **Mavjud balansingiz:** `{bal:,}` so'm\n"
            f"⚠️ **Minimal yechish:** `{MIN_CASHOUT_UZS:,}` so'm\n\n"
            f"Qaysi usulda yechib olmoqchisiz?"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Telegram Stars orqali", callback_data="co_method_stars")],
            [InlineKeyboardButton("💎 TON Hamyon orqali", callback_data="co_method_ton")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_wallet")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^co_method_(stars|ton)$"))
    async def cb_co_select_method(client, cb: CallbackQuery):
        method = cb.matches[0].group(1)
        uid = cb.from_user.id
        USER_STATES[uid] = {"action": "waiting_cashout_details", "method": method}
        prompt_txt = "Telegram @username va summani yozing (masalan: `@username 50000`):" if method == "stars" else "TON hamyon manzilingiz va summani yozing (masalan: `EQ... 100000`):"
        await cb.message.reply_text(f"💳 **{method.upper()} orqali yechish:**\n\n{prompt_txt}")
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^adm_co_(app|rej)_(\d+)$"))
    async def cb_admin_cashout_action(client, cb: CallbackQuery):
        if cb.from_user.id != OWNER_ID:
            await cb.answer("Faqat bot egasi bu amalni bajara oladi!", show_alert=True)
            return

        action = cb.matches[0].group(1)
        req_id = int(cb.matches[0].group(2))
        ok, res = await handle_admin_cashout_decision(client, req_id, action, cb.from_user.id)
        await cb.answer(res, show_alert=True)
        await cb.message.edit_text(f"{cb.message.text}\n\n👉 **Holat:** {res}")

    # =========================================================================
    # 9. SMART DEEPLINK & QR CODE GENERATOR
    # =========================================================================
    @bot.on_message(filters.command(["deeplink", "qr"]) & filters.private)
    async def deeplink_cmd(client, message: Message):
        parts = message.command
        if len(parts) < 2:
            USER_STATES[message.from_user.id] = {"action": "waiting_deeplink_url"}
            await message.reply_text(
                "📲 **Smart YouTube DeepLink & QR Generator**\n\n"
                "YouTube video yoki kanalingiz havolasini yuboring. Bot mobil ilovada "
                "to'g'ridan-to'g'ri ochiluvchi aqlli havola va yuqori sifatli QR kod yasab beradi:\n\n"
                "Masalan: `/deeplink https://youtu.be/...`"
            )
            return

        url = parts[1]
        dl_info = generate_smart_deeplinks(url)
        qr_file = f"downloads/qr_{message.from_user.id}.png"
        await generate_qr_code_image(dl_info["universal_url"], qr_file)

        caption = (
            f"📲 **Smart DeepLink Tayyor!**\n\n"
            f"🌐 **Universal:** `{dl_info['universal_url']}`\n"
            f"🤖 **Android Intent:** `{dl_info['android_intent']}`\n"
            f"🍏 **iOS DeepLink:** `{dl_info['ios_deeplink']}`\n\n"
            f"💡 *Ushbu QR kod yoki havolani Instagram Stories yoki Telegramda ulashing — foydalanuvchilar to'g'ridan-to'g'ri YouTube mobil ilovasida ochiladi!*"
        )
        if os.path.exists(qr_file):
            await client.send_photo(chat_id=message.chat.id, photo=qr_file, caption=caption)
            try: os.remove(qr_file)
            except: pass
        else:
            await message.reply_text(caption)

    @bot.on_callback_query(filters.regex(r"^mkt_view_deeplink$"))
    async def cb_mkt_view_deeplink(client, cb: CallbackQuery):
        USER_STATES[cb.from_user.id] = {"action": "waiting_deeplink_url"}
        await cb.message.reply_text(
            "📲 **Smart YouTube DeepLink & QR Generator**\n\n"
            "YouTube havolangizni yuboring, bot uni mobil ilovada to'g'ridan-to'g'ri ochiladigan formatga o'tkazadi:"
        )
        await cb.answer()

    # =========================================================================
    # UNIVERSAL FSM TEXT HANDLER (STATE INPUTS)
    # =========================================================================
    @bot.on_message(filters.text & filters.private, group=10)
    async def universal_state_listener(client, message: Message):
        uid = message.from_user.id
        state = USER_STATES.get(uid)
        if not state:
            return

        action = state.get("action")
        text = message.text.strip()

        # 1. AI Support savoli
        if action == "waiting_support_ai":
            USER_STATES.pop(uid, None)
            role = state.get("role", "faq")
            lang = db.get_user_language(uid)
            wait_m = await message.reply_text("⏳ `Gemini AI javob tayyorlamoqda...`")
            ans = await generate_support_answer(text, role, lang)
            await wait_m.delete()
            await message.reply_text(f"🤖 **AI Maslahatchi Javobi:**\n\n{ans}")
            message.stop_propagation()

        # 2. Live Admin xabari
        elif action == "waiting_support_live":
            USER_STATES.pop(uid, None)
            role = state.get("role", "general")
            lang = db.get_user_language(uid)
            ticket_id = await forward_to_admin(client, message.from_user, role, text, lang)
            wait_notice = WAITING_MESSAGES.get(lang, WAITING_MESSAGES["uz"])
            await message.reply_text(f"{wait_notice}\n\n🎫 Murojaat raqami: `#{ticket_id}`")
            message.stop_propagation()

        # 3. Admin javobi foydalanuvchiga
        elif action == "admin_replying" and uid == OWNER_ID:
            USER_STATES.pop(uid, None)
            ticket_id = state.get("ticket_id")
            target_uid = state.get("target_user_id")
            db.add_support_message(ticket_id, sender_type="admin", message_text=text)
            user_msg = (
                f"📩 **ADMIN JAVOBI (Murojaat #{ticket_id}):**\n\n"
                f"{text}\n\n"
                f"Qo'shimcha savollaringiz bo'lsa, /support orqali yozishingiz mumkin."
            )
            try:
                await client.send_message(chat_id=target_uid, text=user_msg)
                await message.reply_text(f"✅ Javobingiz foydalanuvchiga ({target_uid}) muvaffaqiyatli yetkazildi!")
            except Exception as err:
                await message.reply_text(f"❌ Foydalanuvchiga yuborishda xato: {err}")
            message.stop_propagation()

        # 4. CapCut taklif havolasi kiritish
        elif action == "waiting_capcut_link":
            USER_STATES.pop(uid, None)
            ok, res = submit_referral_link(uid, text)
            await message.reply_text(res)
            message.stop_propagation()

        # 5. Promokod kiritish
        elif action == "waiting_promo_code":
            USER_STATES.pop(uid, None)
            ok, res = user_redeem_promo(uid, text)
            await message.reply_text(res)
            message.stop_propagation()

        # 6. Instagram profil qo'shish
        elif action == "waiting_ig_profile":
            USER_STATES.pop(uid, None)
            clean_ig = text.lstrip("@").strip()
            add_instagram_target(uid, clean_ig)
            await message.reply_text(f"✅ `@{clean_ig}` Instagram profili kuzatuvga qo'shildi! Endi yangi videolar avtomat YouTube ga o'tkaziladi.")
            message.stop_propagation()

        # 7. AI Video Prompt
        elif action in ("waiting_aivideo_prompt", "waiting_aivideo_prompt_single"):
            USER_STATES.pop(uid, None)
            if action == "waiting_aivideo_prompt_single":
                res_fee = db.deduct_single_ai_video_fee(uid)
                if not res_fee.get("ok"):
                    await message.reply_text(f"❌ {res_fee.get('error', 'Balansingiz yetarli emas!')}")
                    message.stop_propagation()
                    return
            elif not db.is_user_ai_video_subscribed(uid):
                await message.reply_text("❌ Ushbu xizmatdan foydalanish uchun AI Video Studio obunasi ($20/oy) talab qilinadi. /aivideo orqali xarid qiling.")
                message.stop_propagation()
                return

            wait_m = await message.reply_text("⏳ **AI video yaratilmoqda...**\n(Flux rasm + Diktor ovozi + FFmpeg montaj ~30-40 soniya)")
            try:
                lang = db.get_user_language(uid)
                video_data = await build_ai_short_video(text, lang=lang)
                v_path = video_data["video_path"]
                title = video_data["title"]

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 YouTube Kanalimga Yuklash", callback_data=f"pub_aivid_{os.path.basename(v_path)}")],
                    [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
                ])

                await client.send_video(
                    chat_id=message.chat.id,
                    video=v_path,
                    caption=f"🎬 **{title}**\n\n{video_data['script']}",
                    reply_markup=kb,
                    supports_streaming=True
                )
                await wait_m.delete()
            except Exception as e:
                logger.error(f"AI Video xato: {e}")
                await wait_m.edit_text(f"❌ Xatolik yuz berdi: {e}")
            message.stop_propagation()

        # 8. Competitor Spy URL
        elif action == "waiting_spy_url":
            USER_STATES.pop(uid, None)
            wait_m = await message.reply_text("🕵️‍♂️ **Raqobatchi metama'lumotlari tahlil qilinmoqda...**")
            try:
                lang = db.get_user_language(uid)
                res = await analyze_and_steal_seo(text, lang=lang)
                meta = res["meta"]
                tags_str = ", ".join(meta["tags"]) if meta["tags"] else "Yashirin teglar topilmadi."

                report = (
                    f"🎯 **RAQOBATCHI TAHLILI NATIJASI:**\n\n"
                    f"🎬 **Sarlavha:** {meta['title']}\n"
                    f"👤 **Kanal:** {meta['channel']}\n"
                    f"👁 **Ko'rishlar:** `{meta['view_count']:,}` ta\n"
                    f"👍 **Layklar:** `{meta['like_count']:,}` ta\n\n"
                    f"🏷 **YASHIRIN TEGLAR (Keywords):**\n`{tags_str}`\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🧠 **GEMINI AI SEO TAVSIYALARI:**\n\n"
                    f"{res['ai_analysis']}"
                )
                await wait_m.delete()
                await message.reply_text(report)
            except Exception as e:
                await wait_m.edit_text(f"❌ Tahlil xatosi: {e}")
            message.stop_propagation()

        # 9. Cashout tafsilotlari
        elif action == "waiting_cashout_details":
            USER_STATES.pop(uid, None)
            method = state.get("method", "ton")
            tokens = text.split()
            if len(tokens) < 2:
                await message.reply_text("❌ Format xato! Masalan: `EQ... 50000` yoki `@username 50000`")
                message.stop_propagation()
                return
            target_addr = tokens[0]
            try:
                amt = int(tokens[1])
            except ValueError:
                await message.reply_text("❌ Summa raqam bo'lishi kerak!")
                message.stop_propagation()
                return

            ok, res, equiv = request_user_cashout(uid, method, target_addr, amt)
            if not ok:
                await message.reply_text(f"❌ Xatolik: {res}")
            else:
                await message.reply_text(f"✅ {res}\n💰 Ekvivalent: `{equiv}`")
                # Adminga xabar yuborish
                await notify_admin_new_cashout(client, 999, message.from_user, method, target_addr, amt, equiv)
            message.stop_propagation()

        # 10. DeepLink URL
        elif action == "waiting_deeplink_url":
            USER_STATES.pop(uid, None)
            dl_info = generate_smart_deeplinks(text)
            qr_file = f"downloads/qr_{uid}.png"
            await generate_qr_code_image(dl_info["universal_url"], qr_file)

            caption = (
                f"📲 **Smart DeepLink Tayyor!**\n\n"
                f"🌐 **Universal:** `{dl_info['universal_url']}`\n"
                f"🤖 **Android Intent:** `{dl_info['android_intent']}`\n"
                f"🍏 **iOS DeepLink:** `{dl_info['ios_deeplink']}`\n\n"
                f"💡 *QR kodni yuklab oling va istalgan joyda ulashing!*"
            )
            if os.path.exists(qr_file):
                await client.send_photo(chat_id=message.chat.id, photo=qr_file, caption=caption)
                try: os.remove(qr_file)
                except: pass
            else:
                await message.reply_text(caption)
            message.stop_propagation()
