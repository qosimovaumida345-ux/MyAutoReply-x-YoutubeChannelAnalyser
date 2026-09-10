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
import time
import asyncio
import logging
from pyrogram import Client, filters, StopPropagation, ContinuePropagation
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message, WebAppInfo
)
from config import OWNER_ID
from custom_emojis import e, ce
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
    get_capcut_menu_text, get_capcut_pro_keyboard,
    purchase_capcut_pro, CAPCUT_PRICES, LEGAL_DISCLAIMER_WARNING
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
from ton_nft_deployer import generate_nft_deploy_link

logger = logging.getLogger(__name__)

# Foydalanuvchilarning suhbat holatlari (FSM)
USER_STATES = {}

def check_antifraud_or_blocked(user_id: int) -> bool:
    """Foydalanuvchi antifraud tizimida bloklanganmi?"""
    return db.is_user_antifraud_banned(user_id)

def seed_premade_nfts():
    """Tayyor 3D NFT modellarini downloads/ papkasidan bazaga seed qilish (agar mavjud bo'lmasa)"""
    try:
        from config import OWNER_ID
        admin_id = OWNER_ID if OWNER_ID != 0 else 6735799833
        base_dir = os.path.dirname(os.path.abspath(__file__))
        downloads_dir = os.path.join(base_dir, "downloads")

        premade_nfts = [
            {
                "name": "NFT",
                "title": "Exclusive 3D NFT Collectible",
                "description": "Noyob va eksklyuziv 3D NFT artefakti. Telegram botida yaratilgan birinchi to'plam kolleksiyasi.",
                "price_ton": 15.0,
            },
            {
                "name": "HEART",
                "title": "Crystal Heart",
                "description": "Yaltiroq kristall yurak — sevgi va sadoqat ramzi. 3D animatsiyali Telegram Gift.",
                "price_ton": 12.0,
            },
            {
                "name": "TG_PREMIUM",
                "title": "Telegram Premium Star",
                "description": "Telegram Premium yulduzi — eksklyuziv VIP foydalanuvchilar uchun maxsus 3D artefakt.",
                "price_ton": 10.0,
            },
        ]

        conn = db.get_db()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT title FROM nft_items;")
        rows = cur.fetchall() or []
        existing_titles = set(r["title"] if isinstance(r, dict) else r[0] for r in rows)
        cur.close()
        conn.close()

        for nft in premade_nfts:
            if nft["title"] in existing_titles:
                continue
            glb_path = os.path.join(downloads_dir, f"{nft['name']}.glb")
            mp4_path = os.path.join(downloads_dir, f"{nft['name']}.mp4")
            token_id = int(time.time() * 1000) % 1000000000 + abs(hash(nft["name"])) % 1000
            item_id = db.create_nft_item(
                tg_user_id=admin_id,
                title=nft["title"],
                description=nft["description"],
                glb_file_id="",
                preview_image_id="",
                ipfs_metadata_uri="",
                polygon_token_id=abs(token_id),
                voucher_data="",
                price_uzs=0,
                price_matic=nft["price_ton"],
                video_file_path=mp4_path if os.path.exists(mp4_path) else "",
                glb_file_path=glb_path if os.path.exists(glb_path) else "",
                status="listed"
            )
            if item_id:
                logger.info(f"NFT Seeding: {nft['title']} ({nft['price_ton']} TON) -> ID #{item_id}")
    except Exception as e:
        logger.error(f"seed_premade_nfts error: {e}")

def load_mega_features(bot: Client):
    # Premade 3D NFT kolleksiyasini bazaga seed qilish
    try:
        seed_premade_nfts()
    except Exception as se:
        logger.error(f"seed_premade_nfts error: {se}")

    # ==================== ANTIFRAUD TEKSHIRUVI (GLOBAL FILTER) ====================
    @bot.on_message(group=-2)
    async def global_antifraud_gate(client, message: Message):
        if not message.from_user:
            message.continue_propagation()
            return
        uid = message.from_user.id
        if check_antifraud_or_blocked(uid):
            await message.reply_text(
                f"{ce('LOCK')} **HISOBINGIZ BUTUNLAY BLOKLANGAN!**\n\n"
                "Siz shartli chek olganingizdan so'ng homiy kanaldan chiqib ketgansiz.\n"
                "Qat'iy xavfsizlik qoidalariga asosan siz uchun bot xizmatlari va balansingiz muzlatilgan."
            )
            message.stop_propagation()
        else:
            message.continue_propagation()

    @bot.on_callback_query(group=-2)
    async def global_antifraud_cb_gate(client, cb: CallbackQuery):
        if not cb.from_user:
            cb.continue_propagation()
            return
        try:
            uid = cb.from_user.id
            if check_antifraud_or_blocked(uid):
                await cb.answer("Siz qoidabuzarlik sababli botdan bloklangansiz!", show_alert=True)
                cb.stop_propagation()
            else:
                cb.continue_propagation()
        except (StopPropagation, ContinuePropagation):
            raise
        except Exception as e:
            import traceback
            logger.error(f"global_antifraud_cb_gate error: {e}\n{traceback.format_exc()}")
            cb.continue_propagation()

    # =========================================================================
    # 1. SUPPORT DESK & LIVE ADMIN BRIDGE
    # =========================================================================
    @bot.on_message(filters.command(["support", "yordam", "helpdesk"]) & filters.private)
    async def support_cmd(client, message: Message):
        uid = message.from_user.id
        lang = db.get_user_language(uid)
        kb = get_support_menu_keyboard(lang)
        text = (
            f"{ce('ADMIN')} **Yordam & Qo'llab-quvvatlash Markazi**\n\n"
            f"Kerakli bo'limni tanlang. Sun'iy intellekt (Gemini AI) savollaringizga "
            f"24/7 rejimda javob beradi yoki to'g'ridan-to'g'ri admin bilan jonli bog'laydi:"
        )
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^menu_support_desk$"))
    async def cb_support_desk_root(client, cb: CallbackQuery):
        await cb.answer()
        try:
            uid = cb.from_user.id
            lang = db.get_user_language(uid)
            kb = get_support_menu_keyboard(lang)
            msg_text = (
                f"{ce('ADMIN')} **Yordam & Qo'llab-quvvatlash Markazi**\n\n"
                f"Kerakli bo'limni tanlang. Sun'iy intellekt yoki Jonli Admin sizga xizmat ko'rsatadi:"
            )
            try:
                await cb.message.edit_text(msg_text, reply_markup=kb)
            except Exception as e:
                import traceback
                logger.error(f"cb_support_desk_root edit error: {e}\n{traceback.format_exc()}")
                try:
                    await cb.message.reply_text(msg_text, reply_markup=kb)
                except Exception:
                    pass
        except Exception as e:
            import traceback
            logger.error(f"cb_support_desk_root error: {e}\n{traceback.format_exc()}")
            try:
                await cb.message.reply_text(f"{ce('WARN')} Xatolik yuz berdi, admin xabardor qilindi. Iltimos qayta urinib ko'ring.")
            except: pass

    @bot.on_callback_query(filters.regex(r"^support_desk_root$"))
    async def cb_support_desk_back(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        lang = db.get_user_language(uid)
        try:
            await cb.message.edit_text(
                f"{ce('ADMIN')} <b>Yordam & Qo'llab-quvvatlash Markazi</b>\n\nKerakli yo'nalishni tanlang:",
                reply_markup=get_support_menu_keyboard(lang)
            )
        except Exception as e:
            import traceback
            logger.error(f"cb_support_desk_back error: {e}\n{traceback.format_exc()}")

    @bot.on_callback_query(filters.regex(r"^supp_role_([a-z_]+)$"))
    async def cb_support_role(client, cb: CallbackQuery):
        try:
            await cb.answer()
        except Exception:
            pass
        role_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        lang = db.get_user_language(uid)
        role_data = SUPPORT_ROLES.get(role_key, SUPPORT_ROLES["faq"])
        title = role_data["title"].get(lang, role_data["title"]["uz"])
        desc = role_data["desc"].get(lang, role_data["desc"]["uz"])

        text = (
            f"{title}\n\n"
            f"{ce('INFO')} {desc}\n\n"
            f"Savolingizga zudlik bilan javob olish uchun <b>«Savol berish (AI)»</b> tugmasini bosing "
            f"yoki shaxsan adminga xat yo'llang:"
        )
        try:
            await cb.message.edit_text(text, reply_markup=get_role_view_keyboard(role_key, lang))
        except Exception:
            await cb.message.reply_text(text, reply_markup=get_role_view_keyboard(role_key, lang))

    @bot.on_callback_query(filters.regex(r"^supp_ask_([a-z_]+)$"))
    async def cb_support_ask_ai(client, cb: CallbackQuery):
        role_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        USER_STATES[uid] = {"action": "waiting_support_ai", "role": role_key}
        await cb.message.reply_text(f"{ce('MEMO')} <b>Savolingizni yozib yuboring:</b>\n(Gemini AI sizga professional javob tayyorlaydi)")
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^supp_live_([a-z_]+)$"))
    async def cb_support_live_admin(client, cb: CallbackQuery):
        role_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        USER_STATES[uid] = {"action": "waiting_support_live", "role": role_key}
        await cb.message.reply_text(f"{ce('USER')} <b>Adminga yetkazilishi kerak bo'lgan xabaringizni yozing:</b>\n(Xabar bevosita bosh adminga yuboriladi)")
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
        await cb.message.reply_text(f"{ce('MEMO')} <b>Foydalanuvchiga ({target_uid}) yuboriladigan javob xabaringizni yozing:</b>")
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
                f"{ce('CASH')} <b>P2P Shartli Chek Yaratish:</b>\n\n"
                f"Format: <code>/check &lt;umumiy_summa&gt; &lt;odam_soni&gt; [@homiy_kanal]</code>\n\n"
                f"Misol: <code>/check 50000 5 @mening_kanalim</code>\n"
                f"(50,000 so'm 5 kishiga 10,000 so'mdan tarqatiladi. Kanal obunachilari oladi)."
            )
            return

        try:
            total_amt = int(parts[1])
            claims_count = int(parts[2])
            req_channel = parts[3] if len(parts) > 3 else None
        except ValueError:
            await message.reply_text(f"{ce('ERROR')} Summa va odam soni raqam bo'lishi kerak!")
            return

        ok, msg, code = create_p2p_check(uid, total_amt, claims_count, req_channel)
        if not ok:
            await message.reply_text(f"{ce('ERROR')} Xatolik: {msg}")
            return

        share_kb = get_check_claim_keyboard(code, req_channel)
        ch_text = f"\n{ce('CHANNEL')} <b>Shart:</b> @{req_channel.strip().lstrip('@')} kanaliga a'zo bo'lish" if req_channel else ""
        text = (
            f"{ce('CASH')} <b>Yangi Chek Yaratildi!</b>\n\n"
            f"{ce('MONEY')} <b>Umumiy summa:</b> <code>{total_amt:,}</code> so'm\n"
            f"{ce('FRIENDS')} <b>Qabul qiluvchilar soni:</b> <code>{claims_count}</code> ta\n"
            f"{ce('COIN')} <b>Har biriga:</b> <code>{int(total_amt/claims_count):,}</code> so'm{ch_text}\n\n"
            f"{ce('LINK')} <b>Chek Kodi:</b> <code>{code}</code>\n\n"
            f"{RED_ANTIFRAUD_WARNING}"
        )
        await message.reply_text(text, reply_markup=share_kb)

    @bot.on_callback_query(filters.regex(r"^menu_vouchers$"))
    async def cb_menu_vouchers(client, cb: CallbackQuery):
        await cb.answer()
        try:
            uid = cb.from_user.id
            bal = db.get_user_balance(uid)
            text = (
                f"{ce('CASH')} <b>P2P Shartli Cheklar Tizimi (@wallet uslubida)</b>\n\n"
                f"{ce('MONEY')} <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
                f"Do'stlaringiz yoki kanalingiz obunachilari uchun shartli chek yarating. "
                f"Mablag'ni faqat siz belgilagan homiy kanalga a'zo bo'lganlar qabul qila oladi!\n\n"
                f"{ce('LIGHTNING')} <b>Imkoniyatlar:</b>\n"
                f"• {ce('TARGET')} Homiy kanalga majburiy a'zolik sharti\n"
                f"• {ce('FRIENDS')} Bir nechta qabul qiluvchi o'rtasida teng taqsimlash\n"
                f"• {ce('SHIELD')} Kanaldan chiqqanlarni avtomatik aniqlash va qat'iy jazolash\n\n"
                f"{RED_ANTIFRAUD_WARNING}"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Yangi Chek Yaratish", callback_data="vouchers_create_wizard")],
                [InlineKeyboardButton("🎁 Chekni Faollashtirish (Kodni kiritish)", callback_data="vouchers_enter_code")],
                [InlineKeyboardButton("📖 Cheklar Qo'llanmasi", callback_data="help_create_check")],
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])
            try:
                await cb.message.edit_text(text, reply_markup=kb)
            except Exception as e:
                import traceback
                logger.error(f"cb_menu_vouchers edit error: {e}\n{traceback.format_exc()}")
                try:
                    await cb.message.reply_text(text, reply_markup=kb)
                except Exception:
                    pass
        except Exception as e:
            import traceback
            logger.error(f"cb_menu_vouchers error: {e}\n{traceback.format_exc()}")
            try:
                await cb.message.reply_text(f"{ce('WARN')} Xatolik yuz berdi, admin xabardor qilindi. Iltimos qayta urinib ko'ring.")
            except: pass

    @bot.on_callback_query(filters.regex(r"^vouchers_create_wizard$"))
    async def cb_vouchers_create_wizard(client, cb: CallbackQuery):
        await cb.answer()
        USER_STATES[cb.from_user.id] = {"action": "waiting_check_params"}
        bal = db.get_user_balance(cb.from_user.id)
        text = (
            f"{ce('PLUS')} <b>Yangi P2P Shartli Chek Yaratish:</b>\n\n"
            f"{ce('MONEY')} <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
            f"Iltimos, chek parametrlarini quyidagi formatda yuboring:\n"
            f"<code>&lt;summa&gt; &lt;odam_soni&gt; [@homiy_kanal]</code>\n\n"
            f"<b>Misollar:</b>\n"
            f"• <code>50000 5 @mening_kanalim</code> (50,000 so'm 5 kishiga, kanal obunachilariga)\n"
            f"• <code>20000 2</code> (20,000 so'm 2 kishiga, kanalsiz ochiq chek)\n\n"
            f"Chek summasi balansingizdan zudlik bilan yechiladi."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Bekor qilish", callback_data="menu_vouchers")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^vouchers_enter_code$"))
    async def cb_vouchers_enter_code(client, cb: CallbackQuery):
        await cb.answer()
        USER_STATES[cb.from_user.id] = {"action": "waiting_check_code"}
        text = (
            f"{ce('GIFT')} <b>P2P Chekni Faollashtirish:</b>\n\n"
            f"Sizga yuborilgan chek kodini yozib yuboring:\n"
            f"(Masalan: <code>CHK-A1B2C3D4</code>)"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Bekor qilish", callback_data="menu_vouchers")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^help_create_check$"))
    async def cb_help_create_check(client, cb: CallbackQuery):
        await cb.answer()
        text = (
            f"{ce('HELP')} <b>P2P Shartli Cheklar & Antifraud Qo'llanmasi:</b>\n\n"
            f"1. <b>Chek yaratish:</b> Siz o'z balansingizdan istalgan summani bir nechta odamga teng ulashib beruvchi chek yaratasiz.\n"
            f"2. <b>Homiy kanal sharti:</b> Agar homiy kanal ko'rsatsangiz, faqat o'sha kanalga obuna bo'lganlargina pulni ola oladi.\n"
            f"3. <b>Antifraud nazorati:</b> Tizim fon rejimida doimiy ravishda pul olgan foydalanuvchilarning kanaldan chiqib ketganligini tekshiradi.\n"
            f"4. <b>Jazo:</b> Pulni olib kanaldan chiqqan foydalanuvchi butunlay bloklanadi va hisobi muzlatiladi.\n\n"
            f"{RED_ANTIFRAUD_WARNING}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi Chek Yaratish", callback_data="vouchers_create_wizard")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_vouchers")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)

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
        ch_list = "\n".join([f"• @{t['ig_username']} (Interval: {t.get('check_interval_mins', 60)} daqiqa)" for t in targets]) if targets else "Hozircha kuzatilayotgan profillar yo'q."

        text = (
            f"{ce('INSTAGRAM_LOGO')} <b>Instagram Account Auto-Cloner & Reposter</b>\n\n"
            f"Belgilangan Instagram profiliga yangi Reel yuklanganda, bot uni darhol "
            f"yuklab oladi, 8-qatlamli unikalizatsiya (anti-copyright) qiladi va "
            f"ulangan YouTube kanalingizga avtomatik Shorts qilib joylaydi!\n\n"
            f"{ce('LIST')} <b>Kuzatilayotgan profillaringiz:</b>\n{ch_list}\n\n"
            f"Yangi profil qo'shish uchun: <code>/igcloner add @username</code>\n"
            f"O'chirish uchun: <code>/igcloner del @username</code>\n"
            f"Hozir sinash uchun: <code>/igcloner sync @username</code>"
        )
        parts = message.command
        if len(parts) >= 3:
            action = parts[1].lower()
            target_username = parts[2].strip().lstrip("@")
            if action == "add":
                add_instagram_target(uid, target_username)
                await message.reply_text(f"{ce('CHECK')} <code>@{target_username}</code> muvaffaqiyatli kuzatuvga qo'shildi!")
                return
            elif action == "del":
                remove_instagram_target(uid, target_username)
                await message.reply_text(f"{ce('CROSS')} <code>@{target_username}</code> kuzatuvdan olib tashlandi.")
                return
            elif action == "sync":
                res = await sync_instagram_account_now(uid, target_username, app=client, chat_id=message.chat.id)
                await message.reply_text(f"Natija: {res.get('message')}")
                return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")],
            [InlineKeyboardButton("🔄 Hozir Tekshirish & Yuklash", callback_data="ig_sync_now")],
            [InlineKeyboardButton("📋 Profillar Ro'yxati", callback_data="ig_manage_profiles")],
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        await message.reply_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^menu_ig_cloner$"))
    async def cb_menu_ig_cloner(client, cb: CallbackQuery):
        await cb.answer()
        try:
            uid = cb.from_user.id
            targets = get_instagram_targets(uid)
            ch_list = "\n".join([f"• @{t['ig_username']}" for t in targets]) if targets else "Hozircha kuzatilayotgan profillar yo'q."
            text = (
                f"{ce('INSTAGRAM_LOGO')} <b>Instagram Account Auto-Cloner</b>\n\n"
                f"Siz kiritgan Instagram profilidagi Reels'lar 8-qatlamli unikalizatsiya bilan "
                f"to'g'ridan-to'g'ri YouTube Shorts ga nusxalanadi.\n\n"
                f"{ce('LIST')} <b>Kuzatilayotgan profillar:</b>\n{ch_list}"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")],
                [InlineKeyboardButton("🔄 Tekshirish & Yuklash", callback_data="ig_sync_now")],
                [InlineKeyboardButton("📋 Profillarni Boshqarish", callback_data="ig_manage_profiles")],
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])
            try:
                await cb.message.edit_text(text, reply_markup=kb)
            except Exception as e:
                import traceback
                logger.error(f"cb_menu_ig_cloner edit error: {e}\n{traceback.format_exc()}")
                try:
                    await cb.message.reply_text(text, reply_markup=kb)
                except Exception:
                    pass
        except Exception as e:
            import traceback
            logger.error(f"cb_menu_ig_cloner error: {e}\n{traceback.format_exc()}")
            try:
                await cb.message.reply_text(f"{ce('WARN')} Xatolik yuz berdi, admin xabardor qilindi. Iltimos qayta urinib ko'ring.")
            except: pass

    @bot.on_callback_query(filters.regex(r"^ig_add_profile$"))
    async def cb_ig_add_profile(client, cb: CallbackQuery):
        await cb.answer()
        USER_STATES[cb.from_user.id] = {"action": "waiting_ig_profile"}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Bekor qilish", callback_data="menu_ig_cloner")]
        ])
        await cb.message.edit_text(
            f"{ce('INSTAGRAM_LOGO')} <b>Instagram username yuboring:</b>\n\n(Masalan: <code>@cristiano</code> yoki <code>selenagomez</code>)",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^ig_manage_profiles$"))
    async def cb_ig_manage_profiles(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        targets = get_instagram_targets(uid)
        if not targets:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_ig_cloner")]
            ])
            await cb.message.edit_text("Hozircha kuzatilayotgan profillar yo'q.", reply_markup=kb)
            return

        buttons = []
        for t in targets:
            u_name = t["ig_username"]
            buttons.append([
                InlineKeyboardButton(f"@{u_name}", callback_data=f"ig_view_{u_name}"),
                InlineKeyboardButton(f"🗑 O'chirish", callback_data=f"ig_del_{u_name}")
            ])
        buttons.append([InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")])
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_ig_cloner")])

        await cb.message.edit_text(
            f"{ce('LIST')} <b>Kuzatilayotgan Instagram profillaringiz:</b>\nO'chirmoqchi bo'lganingiz yonidagi 🗑 tugmasini bosing:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    @bot.on_callback_query(filters.regex(r"^ig_del_([A-Za-z0-9_.]+)$"))
    async def cb_ig_del_profile(client, cb: CallbackQuery):
        target_username = cb.matches[0].group(1)
        uid = cb.from_user.id
        remove_instagram_target(uid, target_username)
        await cb.answer(f"@{target_username} kuzatuvdan olib tashlandi!", show_alert=True)
        # Qayta ro'yxatni chiqarish
        targets = get_instagram_targets(uid)
        buttons = []
        for t in targets:
            u_name = t["ig_username"]
            buttons.append([
                InlineKeyboardButton(f"@{u_name}", callback_data=f"ig_view_{u_name}"),
                InlineKeyboardButton(f"🗑 O'chirish", callback_data=f"ig_del_{u_name}")
            ])
        buttons.append([InlineKeyboardButton("➕ Yangi Profil Qo'shish", callback_data="ig_add_profile")])
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_ig_cloner")])
        await cb.message.edit_text(
            f"{ce('LIST')} <b>Kuzatilayotgan Instagram profillaringiz:</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    @bot.on_callback_query(filters.regex(r"^ig_view_([A-Za-z0-9_.]+)$"))
    async def cb_ig_view_profile(client, cb: CallbackQuery):
        await cb.answer()
        target_username = cb.matches[0].group(1)
        uid = cb.from_user.id
        targets = get_instagram_targets(uid)
        matched = next((t for t in targets if t["ig_username"].lower() == target_username.lower()), None)
        interval = matched.get("check_interval_mins", 60) if matched else 60
        last_sync = matched.get("last_checked_at", "Hozirgacha tekshirilmadi") if matched else "Noma'lum"

        text = (
            f"{ce('INSTAGRAM_LOGO')} <b>Instagram Profil:</b> <code>@{target_username}</code>\n\n"
            f"• <b>Holat:</b> {ce('VERIFIED')} Faol kuzatuvda\n"
            f"• <b>Kuzatuv intervali:</b> Har {interval} daqiqada\n"
            f"• <b>Oxirgi tekshiruv:</b> <code>{last_sync}</code>\n\n"
            f"Tanlang:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Hozir Tekshirish & Yuklash", callback_data=f"ig_sync_{target_username}")],
            [InlineKeyboardButton("🗑 Kuzatuvdan O'chirish", callback_data=f"ig_del_{target_username}")],
            [InlineKeyboardButton("⬅️ Profillar Ro'yxati", callback_data="ig_manage_profiles")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^ig_sync_now$"))
    async def cb_ig_sync_now(client, cb: CallbackQuery):
        try:
            await cb.answer("Barcha profillar tekshirilmoqda...", show_alert=False)
        except Exception:
            pass
        uid = cb.from_user.id
        targets = get_instagram_targets(uid)
        if not targets:
            await cb.message.reply_text(f"{ce('WARN')} Avval kamida 1 ta Instagram profil qo'shing!")
            return
        await cb.message.reply_text(f"{ce('WAIT')} <b>Tekshiruv boshlanmoqda...</b> Yangi videolar avtomatik yuklanadi.")
        for t in targets:
            await sync_instagram_account_now(uid, t["ig_username"], app=client, chat_id=cb.message.chat.id)

    @bot.on_callback_query(filters.regex(r"^ig_sync_(?!now$)([A-Za-z0-9_.]+)$"))
    async def cb_ig_sync_single(client, cb: CallbackQuery):
        try:
            await cb.answer("Tekshiruv boshlanmoqda...", show_alert=False)
        except Exception:
            pass
        target_username = cb.matches[0].group(1)
        uid = cb.from_user.id
        wait_m = await cb.message.reply_text(f"{ce('WAIT')} <b>@{target_username} tekshirilmoqda...</b>")
        res = await sync_instagram_account_now(uid, target_username, app=client, chat_id=cb.message.chat.id)
        await wait_m.edit_text(f"{ce('INSTAGRAM_LOGO')} <b>@{target_username} natijasi:</b>\n{res.get('message', 'Tekshiruv yakunlandi.')}")

    # =========================================================================
    # 4. CAPCUT PRO — PULLIK SOTISH TIZIMI
    # =========================================================================
    @bot.on_message(filters.command(["capcut", "capcutpro"]) & filters.private)
    async def capcut_cmd(client, message: Message):
        uid = message.from_user.id
        lang = db.get_user_language(uid)
        text = get_capcut_menu_text(uid, lang)
        kb = get_capcut_pro_keyboard(uid, lang)
        await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)

    @bot.on_callback_query(filters.regex(r"^menu_capcut$"))
    async def cb_menu_capcut(client, cb: CallbackQuery):
        await cb.answer()
        try:
            uid = cb.from_user.id
            lang = db.get_user_language(uid)
            text = get_capcut_menu_text(uid, lang)
            kb = get_capcut_pro_keyboard(uid, lang)
            try:
                await cb.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
            except Exception as e:
                import traceback
                logger.error(f"cb_menu_capcut edit error: {e}\n{traceback.format_exc()}")
                try:
                    await cb.message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)
                except Exception:
                    pass
        except Exception as e:
            import traceback
            logger.error(f"cb_menu_capcut error: {e}\n{traceback.format_exc()}")
            try:
                await cb.message.reply_text(f"{ce('WARN')} Xatolik yuz berdi, admin xabardor qilindi. Iltimos qayta urinib ko'ring.")
            except: pass

    @bot.on_callback_query(filters.regex(r"^capcut_buy_(30|90|365)$"))
    async def cb_capcut_buy(client, cb: CallbackQuery):
        await cb.answer()
        plan_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        res = purchase_capcut_pro(uid, plan_key)

        if not res.get("ok"):
            bal = db.get_user_balance(uid)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Balansni To'ldirish", callback_data="menu_wallet")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_capcut")]
            ])
            await cb.message.edit_text(
                f"{ce('ERROR')} <b>Mablag' yetarli emas!</b>\n\n"
                f"{res.get('error')}\n"
                f"{ce('MONEY')} Sizning joriy balansingiz: <code>{bal:,} so'm</code>\n\n"
                f"Iltimos, avval hisobingizni to'ldiring:",
                reply_markup=kb
            )
            return

        plan_label = res["plan_label"]
        price_label = res["price_label"]
        lic_key = res["license_key"]
        expires_at = res["expires_at"]
        new_bal = res["new_balance"]

        text = (
            f"{ce('PARTY')} <b>Tabriklaymiz! CapCut Pro {plan_label} muvaffaqiyatli xarid qilindi!</b>\n\n"
            f"{ce('KEY')} <b>Sizning Litsenziya Kalitingiz:</b>\n"
            f"<code>{lic_key}</code>\n\n"
            f"{ce('CALENDAR')} <b>Amal qilish muddati:</b> <code>{expires_at}</code> gacha\n"
            f"{ce('MONEY')} <b>Yechilgan summa:</b> {price_label}\n"
            f"{ce('REPORT')} <b>Qolgan balansingiz:</b> <code>{new_bal:,} so'm</code>\n\n"
            f"{ce('LIST')} <b>Faollashtirish bo'yicha ko'rsatma:</b>\n"
            f"1. Kompyuter yoki telefoningizda CapCut dasturini oching\n"
            f"2. Profilingizga kiring va 'Pro' bo'limini tanlang\n"
            f"3. Yuqoridagi litsenziya kalitini kiriting\n"
            f"4. Barcha VIP filtrlar, 4K eksport va AI imkoniyatlaridan cheksiz foydalaning!\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Mening Obunam", callback_data="capcut_my_status")],
            [InlineKeyboardButton("🏠 Bosh Menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^capcut_stars_(30|90|365)$"))
    async def cb_capcut_stars(client, cb: CallbackQuery):
        await cb.answer()
        plan_key = cb.matches[0].group(1)
        uid = cb.from_user.id
        plan = CAPCUT_PRICES.get(plan_key)
        if not plan:
            return

        from config import BOT_TOKEN
        bot_token = BOT_TOKEN or os.getenv("BOT_TOKEN")
        from ytbot import _send_bot_api_invoice
        stars_amount = plan["stars"]
        res = await _send_bot_api_invoice(
            bot_token=bot_token,
            chat_id=cb.message.chat.id,
            title=f"CapCut Pro {plan['label']} Litsenziyasi",
            description=f"{plan['days']} kunlik CapCut Pro rasmiy litsenziyasi va VIP imkoniyatlar",
            payload=f"capcut_stars_{plan_key}_{uid}",
            currency="XTR",
            prices=[{"label": f"CapCut Pro {plan['label']}", "amount": stars_amount}],
            provider_token=""
        )
        if not res:
            await cb.message.reply_text(f"{ce('ERROR')} Stars hisobini ochishda xatolik yuz berdi. Iltimos, balans orqali xarid qiling.")

    @bot.on_callback_query(filters.regex(r"^capcut_my_status$"))
    async def cb_capcut_my_status(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        sub = db.get_user_capcut_subscription(uid)
        if not sub:
            text = (
                f"{ce('INFO')} <b>Sizda hali faol CapCut Pro obunasi mavjud emas.</b>\n\n"
                f"CapCut Pro xarid qilib barcha VIP vositalardan foydalanishingiz mumkin:"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Tariflarni Ko'rish", callback_data="menu_capcut")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_capcut")]
            ])
            await cb.message.edit_text(text, reply_markup=kb)
            return

        text = (
            f"{ce('CROWN')} <b>Sizning CapCut Pro Obunangiz:</b>\n\n"
            f"• <b>Holat:</b> {ce('VERIFIED')} Faol\n"
            f"• <b>Amal qilish muddati:</b> <code>{sub.get('expires_at')}</code> gacha\n"
            f"• <b>Litsenziya kaliti:</b> <code>{sub.get('license_key', 'Faol')}</code>\n\n"
            f"{ce('ROCKET')} Cheksiz foydalanishingiz mumkin!\n\n"
            f"{LEGAL_DISCLAIMER_WARNING}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Obunani Uzaytirish", callback_data="menu_capcut")],
            [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
        ])
        await cb.message.edit_text(text, reply_markup=kb)

    # =========================================================================
    # 5. ADMIN PROMO CODES (/newpromo) & USER REDEMPTION (/redeem)
    # =========================================================================
    @bot.on_message(filters.command("newpromo") & filters.private)
    async def new_promo_cmd(client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text(f"{ce('ERROR')} Faqat bosh admin promokod yarata oladi.")
            return

        parts = message.command
        if len(parts) < 3:
            await message.reply_text(f"Format: <code>/newpromo &lt;KOD&gt; &lt;BONUS_UZS&gt; [MAKS_FOYDALANISH]</code>\nMasalan: <code>/newpromo MEGA2026 25000 100</code>")
            return

        code = parts[1]
        try:
            bonus = int(parts[2])
            limit = int(parts[3]) if len(parts) > 3 else 100
        except ValueError:
            await message.reply_text(f"{ce('ERROR')} Bonus va limit raqam bo'lishi kerak!")
            return

        ok, res = admin_create_promo(code, bonus, limit)
        await message.reply_text(res)

    @bot.on_message(filters.command("redeem") & filters.private)
    async def redeem_cmd(client, message: Message):
        parts = message.command
        if len(parts) < 2:
            USER_STATES[message.from_user.id] = {"action": "waiting_promo_code"}
            await message.reply_text(f"{ce('TICKET')} <b>Promokodingizni kiriting:</b>")
            return

        code = parts[1]
        ok, res = user_redeem_promo(message.from_user.id, code)
        await message.reply_text(res)

    @bot.on_callback_query(filters.regex(r"^enter_promo_code$"))
    async def cb_enter_promo_code(client, cb: CallbackQuery):
        try:
            await cb.answer()
        except Exception:
            pass
        USER_STATES[cb.from_user.id] = {"action": "waiting_promo_code"}
        await cb.message.reply_text(f"{ce('TICKET')} <b>Iltimos, promokodingizni yozib yuboring:</b>")

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
                f"{ce('VIDEO')} <b>AI Video Studio ($20 / oy)</b>\n\n"
                f"Ushbu xizmat pullik bo'lib, professional 9:16 vertikal Shorts/Reels tayyorlaydi:\n"
                f"• {ce('FLUX')} <b>Flux.1 Ultra AI</b> — 4K tasvirlar\n"
                f"• {ce('VOICE')} <b>Neural Edge-TTS</b> — 5 ta tilda tabiiy diktor ovozi\n"
                f"• {ce('VIDEO')} <b>FFmpeg Ken Burns FX</b> — Dinamik animatsiya va audio montaj\n\n"
                f"{ce('TON')} <b>Tariflar:</b>\n"
                f"• {ce('CROWN')} <b>Oylik Cheksiz Obuna:</b> <b>$20 / oy</b> (256,000 so'm)\n"
                f"• {ce('STAR')} <b>Telegram Stars:</b> 1,000 ⭐\n"
                f"• {ce('CLIPPER')} <b>1 ta Video:</b> 15,000 so'm / video\n\n"
                f"{ce('MONEY')} <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
                f"{ce('WARN')} <i>OGOHLANTIRISH: Raqamli mahsulotlar uchun qaytarib berilmaydi (NO REFUNDS).</i>\n\n"
                f"Tarifni tanlang:"
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
                f"{ce('VIDEO')} <b>AI Video Studio ({note})</b>\n\n"
                f"{ce('MEMO')} <b>Video mavzusini yozing:</b> (masalan: <i>Kosmos sirlari va qora tuynuklar</i>)"
            )
            return

        prompt = " ".join(parts[1:])
        if not is_sub:
            res_fee = db.deduct_single_ai_video_fee(uid)
            if not res_fee.get("ok"):
                await message.reply_text(f"{ce('ERROR')} {res_fee.get('error', 'Balans yetarli emas')}")
                return

        wait_m = await message.reply_text(f"{ce('WAIT')} <b>AI video yaratilmoqda...</b>\n(Flux rasm + Diktor ovozi + FFmpeg montaj ~30-40 soniya)")
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
                caption=f"{ce('VIDEO')} <b>{title}</b>\n\n{video_data['script']}\n\n{ce('WARN')} <i>Qaytarib berilmaydi (NO REFUNDS).</i>",
                reply_markup=kb,
                supports_streaming=True
            )
            await wait_m.delete()
        except Exception as e:
            import traceback
            logger.error(f"AI Video xato: {e}\n{traceback.format_exc()}")
            await wait_m.edit_text(f"{ce('ERROR')} Xatolik yuz berdi: {e}")

    @bot.on_callback_query(filters.regex(r"^menu_ai_video$"))
    async def cb_menu_ai_video(client, cb: CallbackQuery):
        await cb.answer()
        try:
            uid = cb.from_user.id
            is_sub = db.is_user_ai_video_subscribed(uid)
            if not is_sub:
                bal = db.get_user_balance(uid)
                text = (
                    f"{ce('VIDEO')} <b>AI Video Studio ($20 / oy)</b>\n\n"
                    f"Ushbu xizmat professional sun'iy intellekt orqali to'liq avtomatlashtirilgan video tayyorlash studiyasidir:\n"
                    f"• {ce('FLUX')} <b>Flux.1 Ultra AI</b> — 9:16 kinematografik 4K tasvirlar\n"
                    f"• {ce('VOICE')} <b>Neural Edge-TTS</b> — 5 ta tilda tabiiy diktor ovozi\n"
                    f"• {ce('VIDEO')} <b>Ken Burns FX</b> — Dinamik kamera harakati va audio montaj\n"
                    f"• {ce('ROCKET')} <b>1-Click YouTube Shorts Yuklash</b>\n\n"
                    f"{ce('CARD')} <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>\n\n"
                    f"{ce('TON')} <b>Tariflar:</b>\n"
                    f"• {ce('CROWN')} <b>Oylik Cheksiz Obuna:</b> <b>$20 / oy</b> (256,000 so'm)\n"
                    f"• {ce('STAR')} <b>Telegram Stars:</b> 1,000 ⭐\n"
                    f"• {ce('CLIPPER')} <b>1 ta Video:</b> 15,000 so'm / video\n\n"
                    f"{ce('WARN')} <i>OGOHLANTIRISH: Raqamli mahsulotlar uchun to'lov qaytarilmaydi (NO REFUNDS).</i>\n\n"
                    f"Kerakli tarifni tanlang:"
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
                    import traceback
                    logger.error(f"cb_menu_ai_video error: {e}\n{traceback.format_exc()}")
                    try:
                        await cb.message.reply_text(text, reply_markup=kb)
                    except Exception:
                        pass
                return

            USER_STATES[uid] = {"action": "waiting_aivideo_prompt"}
            text = (
                f"{ce('VIDEO')} <b>AI Video Studio (Faol Obuna)</b>\n\n"
                f"Sizda faol obuna mavjud! Cheksiz video yaratish rejimi yoqilgan.\n\n"
                f"{ce('MEMO')} <b>Video yaratish uchun mavzuni yozib yuboring:</b>\n"
                f"(Masalan: <i>Kosmos sirlari va qora tuynuklar</i> yoki <i>Qiziqarli faktlar</i>)"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])
            try:
                await cb.message.edit_text(text, reply_markup=kb)
            except Exception as e:
                import traceback
                logger.error(f"cb_menu_ai_video prompt error: {e}\n{traceback.format_exc()}")
                try:
                    await cb.message.reply_text(text, reply_markup=kb)
                except Exception:
                    pass
        except Exception as e:
            import traceback
            logger.error(f"cb_menu_ai_video error: {e}\n{traceback.format_exc()}")
            try:
                await cb.message.reply_text(f"{ce('WARN')} Xatolik yuz berdi, admin xabardor qilindi. Iltimos qayta urinib ko'ring.")
            except: pass

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
                f"{ce('ERROR')} <b>Mablag' yetarli emas!</b>\n\n"
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
            f"{ce('PARTY')} <b>Tabriklaymiz! AI Video Studio obunangiz faollashdi!</b>\n\n"
            f"• Amal qilish muddati: <code>{exp}</code> gacha (30 kun)\n"
            f"• Cheksiz video generatsiya faol!\n\n"
            f"Endi video mavzusini chatga yozib yuborishingiz mumkin:\n\n"
            f"{ce('WARN')} <i>OGOHLANTIRISH: Raqamli xizmatlar uchun to'lov qaytarilmaydi (NO REFUNDS).</i>",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^aivid_buy_stars$"))
    async def cb_aivid_buy_stars(client, cb: CallbackQuery):
        await cb.answer()
        uid = cb.from_user.id
        from config import BOT_TOKEN
        bot_token = BOT_TOKEN or os.getenv("BOT_TOKEN")
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
            await cb.message.reply_text(f"{ce('ERROR')} Stars hisobini ochishda xatolik yuz berdi. Iltimos, /balance orqali balansingizni to'ldiring.")

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
                f"{ce('ERROR')} <b>Mablag' yetarli emas!</b>\n\n"
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
            f"{ce('VIDEO')} <b>1 ta AI Video Generatsiyasi (15,000 so'm)</b>\n\n"
            f"Mavzuni yuborganingizdan so'ng balansingizdan 15,000 so'm yechiladi va video tayyorlanadi.\n\n"
            f"{ce('MEMO')} <b>Video mavzusini yozib yuboring:</b>\n\n"
            f"{ce('WARN')} <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^pub_aivid_(.+)$"))
    async def cb_publish_ai_video(client, cb: CallbackQuery):
        await cb.answer("YouTube ga yuklash boshlandi...", show_alert=False)
        uid = cb.from_user.id
        v_name = cb.matches[0].group(1)
        v_path = os.path.join("downloads", v_name)
        if not os.path.exists(v_path):
            await cb.message.reply_text(f"{ce('ERROR')} Video fayli topilmadi.")
            return

        yt_conn = db.get_yt_connection(uid)
        if not yt_conn or not yt_conn.get("access_token"):
            await cb.message.reply_text(f"{ce('WARN')} Avval /ytlogin orqali YouTube kanalingizni ulang!")
            return

        try:
            yt_id = await asyncio.to_thread(
                upload_to_youtube,
                v_path,
                "AI Viral Short #Shorts",
                "Generated with AI Video Studio ($20/mo)\n#shorts #ai #viral",
                yt_conn
            )
            await cb.message.reply_text(f"{ce('CHECK')} <b>Muvaffaqiyatli yuklandi!</b>\n{ce('LINK')} <a href=\"https://youtu.be/{yt_id}\">YouTube da ko'rish</a>")
        except Exception as e:
            await cb.message.reply_text(f"{ce('ERROR')} Yuklashda xato: {e}")

    # =========================================================================
    # 7. YOUTUBE COMPETITOR SPY & SEO STEALER
    # =========================================================================
    @bot.on_message(filters.command(["spy", "seosteal"]) & filters.private)
    async def spy_cmd(client, message: Message):
        parts = message.command
        if len(parts) < 2:
            USER_STATES[message.from_user.id] = {"action": "waiting_spy_url"}
            await message.reply_text(
                f"{ce('SEARCH')} <b>YouTube Competitor Spy & SEO Stealer</b>\n\n"
                f"Raqobatchining videosidan yashirin teglarni va kalit so'zlarni ko'chirib olish "
                f"hamda Gemini AI orqali uni ortda qoldiruvchi CTR sarlavhalar olish uchun "
                f"video yoki kanal havolasini yuboring:\n\n"
                f"Masalan: <code>/spy https://youtu.be/...</code>"
            )
            return

        video_url = parts[1]
        wait_m = await message.reply_text(f"{ce('SPY_HAT')} <b>Raqobatchi metama'lumotlari va yashirin teglari tahlil qilinmoqda...</b>")
        try:
            lang = db.get_user_language(message.from_user.id)
            res = await analyze_and_steal_seo(video_url, lang=lang)
            meta = res["meta"]
            tags_str = ", ".join(meta["tags"]) if meta["tags"] else "Yashirin teglar topilmadi."

            report = (
                f"{ce('TARGET')} <b>RAQOBATCHI TAHLILI NATIJASI:</b>\n\n"
                f"{ce('VIDEO')} <b>Sarlavha:</b> {meta['title']}\n"
                f"{ce('USER')} <b>Kanal:</b> {meta['channel']}\n"
                f"{ce('VIEWS')} <b>Ko'rishlar:</b> <code>{meta['view_count']:,} ta</code>\n"
                f"{ce('LIKE')} <b>Layklar:</b> <code>{meta['like_count']:,} ta</code>\n\n"
                f"{ce('SEO_TAG')} <b>YASHIRIN TEGLAR (Keywords):</b>\n<code>{tags_str}</code>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{ce('BRAIN')} <b>GEMINI AI SEO TAVSIYALARI:</b>\n\n"
                f"{res['ai_analysis']}"
            )
            await wait_m.delete()
            await message.reply_text(report)
        except Exception as e:
            await wait_m.edit_text(f"{ce('ERROR')} Tahlil xatosi: {e}")

    @bot.on_callback_query(filters.regex(r"^menu_spy$"))
    async def cb_menu_spy(client, cb: CallbackQuery):
        await cb.answer()
        try:
            USER_STATES[cb.from_user.id] = {"action": "waiting_spy_url"}
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
            ])
            spy_text = (
                f"{ce('SEARCH')} <b>YouTube Competitor Spy & SEO Stealer</b>\n\n"
                f"Tahlil qilmoqchi bo'lgan YouTube video yoki Shorts havolasini yuboring:"
            )
            try:
                await cb.message.edit_text(spy_text, reply_markup=kb)
            except Exception as e:
                import traceback
                logger.error(f"cb_menu_spy edit error: {e}\n{traceback.format_exc()}")
                try:
                    await cb.message.reply_text(spy_text, reply_markup=kb)
                except Exception:
                    pass
        except Exception as e:
            import traceback
            logger.error(f"cb_menu_spy error: {e}\n{traceback.format_exc()}")
            try:
                await cb.message.reply_text(f"{ce('WARN')} Xatolik yuz berdi, admin xabardor qilindi. Iltimos qayta urinib ko'ring.")
            except: pass

    # =========================================================================
    # 8. CASHOUT ENGINE (STARS & TON PUL YECHISH)
    # =========================================================================
    @bot.on_message(filters.command(["cashout", "yechish"]) & filters.private)
    async def cashout_cmd(client, message: Message):
        uid = message.from_user.id
        bal = db.get_user_balance(uid)
        text = (
            f"{ce('CASH')} <b>Hisobdan Pul Yechish (Cashout)</b>\n\n"
            f"{ce('MONEY')} <b>Mavjud balansingiz:</b> <code>{bal:,}</code> so'm\n"
            f"{ce('WARN')} <b>Minimal yechish summasi:</b> <code>{MIN_CASHOUT_UZS:,}</code> so'm\n\n"
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
            f"{ce('CASH')} <b>Hisobdan Pul Yechish (Cashout)</b>\n\n"
            f"{ce('MONEY')} <b>Mavjud balansingiz:</b> <code>{bal:,}</code> so'm\n"
            f"{ce('WARN')} <b>Minimal yechish:</b> <code>{MIN_CASHOUT_UZS:,}</code> so'm\n\n"
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
        try:
            await cb.answer()
        except Exception:
            pass
        method = cb.matches[0].group(1)
        uid = cb.from_user.id
        USER_STATES[uid] = {"action": "waiting_cashout_details", "method": method}
        if method == "stars":
            prompt_txt = "Telegram @username va summani yozing (masalan: `@username 50000`):"
        else:
            w = db.get_user_ton_wallet(uid)
            if w and w.get("wallet_address"):
                saved_addr = w["wallet_address"]
                masked = f"{saved_addr[:6]}...{saved_addr[-6:]}"
                prompt_txt = (
                    f"💎 <b>Ulangan TON Hamyoningiz:</b> <code>{saved_addr}</code> ({masked})\n\n"
                    f"👉 Ushbu hamyonga yechish uchun <b>faqat summani</b> yozing (masalan: <code>100000</code>)\n"
                    f"Yoki boshqa hamyon manzilini ko'rsating (masalan: <code>EQ... 100000</code>):"
                )
            else:
                prompt_txt = "TON hamyon manzilingiz va summani yozing (masalan: `EQ... 100000`):"
        await cb.message.reply_text(f"{ce('CARD')} <b>{method.upper()} orqali yechish:</b>\n\n{prompt_txt}")

    @bot.on_callback_query(filters.regex(r"^adm_co_(app|rej)_(\d+)$"))
    async def cb_admin_cashout_action(client, cb: CallbackQuery):
        if cb.from_user.id != OWNER_ID:
            await cb.answer("Faqat bot egasi bu amalni bajara oladi!", show_alert=True)
            return

        action = cb.matches[0].group(1)
        req_id = int(cb.matches[0].group(2))
        ok, res = await handle_admin_cashout_decision(client, req_id, action, cb.from_user.id)
        await cb.answer(res, show_alert=True)
        await cb.message.edit_text(f"{cb.message.text}\n\n👉 <b>Holat:</b> {res}")

    # =========================================================================
    # 9. SMART DEEPLINK & QR CODE GENERATOR
    # =========================================================================
    @bot.on_message(filters.command(["deeplink", "qr"]) & filters.private)
    async def deeplink_cmd(client, message: Message):
        parts = message.command
        if len(parts) < 2:
            USER_STATES[message.from_user.id] = {"action": "waiting_deeplink_url"}
            await message.reply_text(
                f"{ce('DEEPLINK')} <b>Smart YouTube DeepLink & QR Generator</b>\n\n"
                f"YouTube video yoki kanalingiz havolasini yuboring. Bot mobil ilovada "
                f"to'g'ridan-to'g'ri ochiluvchi aqlli havola va yuqori sifatli QR kod yasab beradi:\n\n"
                f"Masalan: <code>/deeplink https://youtu.be/...</code>"
            )
            return

        url = parts[1]
        dl_info = generate_smart_deeplinks(url)
        qr_file = f"downloads/qr_{message.from_user.id}.png"
        await generate_qr_code_image(dl_info["universal_url"], qr_file)

        caption = (
            f"{ce('DEEPLINK')} <b>Smart DeepLink Tayyor!</b>\n\n"
            f"{ce('WEB')} <b>Universal:</b> <code>{dl_info['universal_url']}</code>\n"
            f"{ce('MOBILE')} <b>Android Intent:</b> <code>{dl_info['android_intent']}</code>\n"
            f"{ce('MOBILE')} <b>iOS DeepLink:</b> <code>{dl_info['ios_deeplink']}</code>\n\n"
            f"{ce('IDEA')} <i>Ushbu QR kod yoki havolani Instagram Stories yoki Telegramda ulashing — foydalanuvchilar to'g'ridan-to'g'ri YouTube mobil ilovasida ochiladi!</i>\n\n"
            f"{ce('WARN')} <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
        )
        if os.path.exists(qr_file):
            await client.send_photo(chat_id=message.chat.id, photo=qr_file, caption=caption)
            try: os.remove(qr_file)
            except: pass
        else:
            await message.reply_text(caption)

    @bot.on_callback_query(filters.regex(r"^mkt_view_deeplink$"))
    async def cb_mkt_view_deeplink(client, cb: CallbackQuery):
        try:
            await cb.answer()
        except Exception:
            pass
        USER_STATES[cb.from_user.id] = {"action": "waiting_deeplink_url"}
        await cb.message.reply_text(
            f"{ce('DEEPLINK')} <b>Smart YouTube DeepLink & QR Generator</b>\n\n"
            f"YouTube havolangizni yuboring, bot uni mobil ilovada to'g'ridan-to'g'ri ochiladigan formatga o'tkazadi:"
        )

    # =========================================================================
    # 13. 3D NFT MARKETPLACE (Tayyor Kolleksiya + TON Mint)
    # =========================================================================

    @bot.on_message(filters.command("nft") & filters.private)
    async def nft_cmd(client, message: Message):
        uid = message.from_user.id
        lang = db.get_user_language(uid) or "uz"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{e('GALLERY')} NFT Kolleksiya (Bozor)", callback_data="nft_market")],
            [InlineKeyboardButton(f"{e('NFT')} Mening NFT larim", callback_data="nft_my_items")],
            [InlineKeyboardButton(f"{e('HOME')} Bosh Menyu", callback_data="back_main")]
        ])
        await message.reply_text(
            f"{ce('NFT')} <b>3D NFT Marketplace</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{ce('GALLERY')} Eksklyuziv 3D NFT kolleksiyamizdan o'zingizga yoqqanini tanlang!\n\n"
            f"{ce('TONKEEPER')} Sotib olingan NFT haqiqiy <b>TON blockchain</b>ga mint qilinadi va "
            f"sizning hamyoningizga tushadi.\n\n"
            f"{ce('RENDER')} Har bir NFT 3D model (.glb) va animatsiyali video bilan birga keladi.",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^menu_nft$"))
    async def cb_menu_nft(client, cb: CallbackQuery):
        uid = cb.from_user.id
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{e('GALLERY')} NFT Kolleksiya (Bozor)", callback_data="nft_market")],
            [InlineKeyboardButton(f"{e('NFT')} Mening NFT larim", callback_data="nft_my_items")],
            [InlineKeyboardButton(f"{e('HOME')} Bosh Menyu", callback_data="back_main")]
        ])
        try:
            await cb.message.edit_text(
                f"{ce('NFT')} <b>3D NFT Marketplace</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"{ce('GALLERY')} Eksklyuziv 3D NFT kolleksiyamizdan tanlang!\n"
                f"{ce('TONKEEPER')} Xarid qilingan NFT TON blockchainga mint qilinadi.",
                reply_markup=kb
            )
        except Exception:
            try:
                await cb.message.delete()
            except Exception:
                pass
            await client.send_message(
                chat_id=cb.message.chat.id,
                text=(
                    f"{ce('NFT')} <b>3D NFT Marketplace</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"{ce('GALLERY')} Eksklyuziv 3D NFT kolleksiyamizdan tanlang!\n"
                    f"{ce('TONKEEPER')} Xarid qilingan NFT TON blockchainga mint qilinadi."
                ),
                reply_markup=kb
            )
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^nft_market$"))
    async def cb_nft_market(client, cb: CallbackQuery):
        items = db.get_listed_nfts(limit=20)
        if not items:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("\u2b05\ufe0f Orqaga", callback_data="menu_nft")]
            ])
            text = (
                f"{ce('GALLERY')} <b>3D NFT Bozori</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                "Hozircha sotuvda faol NFT lar yo'q."
            )
            try:
                await cb.message.edit_text(text, reply_markup=kb)
            except Exception:
                try:
                    await cb.message.delete()
                except Exception:
                    pass
                await client.send_message(cb.message.chat.id, text, reply_markup=kb)
            await cb.answer()
            return

        text = f"{ce('GALLERY')} <b>3D NFT Bozori ({len(items)} ta)</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        btns = []
        for it in items:
            price_ton = float(it.get('price_matic', 0))
            text += (
                f"{ce('NFT')} <b>{it.get('title')}</b>\n"
                f"{ce('TONKEEPER')} Narxi: <b>{price_ton} TON</b>\n"
                f"{ce('BLOCKCHAIN')} <i>{it.get('description', '')[:60]}</i>\n\n"
            )
            btns.append([InlineKeyboardButton(
                f"{e('NFT')} {it.get('title')} — {price_ton} TON",
                callback_data=f"nft_view_{it['id']}"
            )])

        btns.append([InlineKeyboardButton("\u2b05\ufe0f Orqaga", callback_data="menu_nft")])
        try:
            await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btns))
        except Exception:
            try:
                await cb.message.delete()
            except Exception:
                pass
            await client.send_message(cb.message.chat.id, text, reply_markup=InlineKeyboardMarkup(btns))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^nft_view_(\d+)$"))
    async def cb_nft_view(client, cb: CallbackQuery):
        """NFT ni ko'rish: Video preview + batafsil ma'lumot + Sotib olish tugmasi"""
        item_id = int(cb.matches[0].group(1))
        item = db.get_nft_item(item_id)
        if not item or item.get("status") != "listed":
            await cb.answer("Bu NFT mavjud emas yoki allaqachon sotilgan!", show_alert=True)
            return

        await cb.answer()
        price_ton = float(item.get('price_matic', 0))
        chat_id = cb.message.chat.id

        caption = (
            f"{ce('NFT')} <b>{item.get('title')}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ce('BLOCKCHAIN')} <i>{item.get('description', '')}</i>\n\n"
            f"{ce('TONKEEPER')} <b>Narxi:</b> <code>{price_ton} TON</code>\n"
            f"{ce('POLYGON')} <b>Token ID:</b> <code>#{item.get('polygon_token_id', 0)}</code>\n"
            f"{ce('RENDER')} <b>Format:</b> 3D GLTF (.glb) + Video (.mp4)\n\n"
            f"{ce('MINT')} Sotib olganingizdan keyin NFT haqiqiy TON blockchainga mint qilinadi "
            f"va sizning hamyoningizga tushadi!"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{e('TONKEEPER')} Sotib olish — {price_ton} TON", callback_data=f"nft_buy_{item_id}")],
            [InlineKeyboardButton(f"{e('GALLERY')} Bozorga qaytish", callback_data="nft_market")],
            [InlineKeyboardButton(f"{e('HOME')} Bosh Menyu", callback_data="back_main")]
        ])

        # Video preview yuborish (agar mavjud bo'lsa)
        video_path = item.get('video_file_path', '')
        if video_path and os.path.exists(video_path):
            try:
                await client.send_video(
                    chat_id=chat_id,
                    video=video_path,
                    caption=caption,
                    reply_markup=kb,
                    supports_streaming=True
                )
                try:
                    await cb.message.delete()
                except Exception:
                    pass
                return
            except Exception as ve:
                logger.warning(f"Video yuborishda xatolik: {ve}")

        # Video topilmasa matnli xabar
        try:
            await cb.message.edit_text(caption, reply_markup=kb)
        except Exception:
            await client.send_message(chat_id=chat_id, text=caption, reply_markup=kb)

    @bot.on_callback_query(filters.regex(r"^nft_my_items$"))
    async def cb_nft_my_items(client, cb: CallbackQuery):
        uid = cb.from_user.id
        items = db.get_user_nfts(uid)

        # Sotib olingan NFT-lar ham ko'rinishi uchun
        conn = db.get_db()
        bought_items = []
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM nft_items WHERE buyer_user_id = %s ORDER BY id DESC", (uid,))
                bought_items = [dict(r) for r in (cur.fetchall() or [])]
            except Exception:
                pass
            finally:
                conn.close()

        all_items = items + bought_items
        # Dublikatlarni olib tashlash
        seen = set()
        unique_items = []
        for it in all_items:
            if it['id'] not in seen:
                seen.add(it['id'])
                unique_items.append(it)

        if not unique_items:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{e('GALLERY')} NFT Bozorga o'tish", callback_data="nft_market")],
                [InlineKeyboardButton("\u2b05\ufe0f Orqaga", callback_data="menu_nft")]
            ])
            text = (
                f"{ce('NFT')} <b>Sizda hali NFT lar mavjud emas.</b>\n\n"
                f"NFT Bozordan eksklyuziv 3D kolleksiyalarni sotib oling!"
            )
            try:
                await cb.message.edit_text(text, reply_markup=kb)
            except Exception:
                try:
                    await cb.message.delete()
                except Exception:
                    pass
                await client.send_message(cb.message.chat.id, text, reply_markup=kb)
            await cb.answer()
            return

        text = f"{ce('NFT')} <b>Sizning NFT Kolleksiyangiz ({len(unique_items)} ta):</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        btns = []
        for it in unique_items[:10]:
            status = it.get('status', 'draft')
            if status == 'sold' and it.get('buyer_user_id') == uid:
                status_ico = f"{e('SUCCESS')}"
                status_txt = "Sizniki"
            elif status == 'listed':
                status_ico = f"{e('PRICE_TAG')}"
                status_txt = "Sotuvda"
            else:
                status_ico = f"{e('NFT')}"
                status_txt = status

            text += f"{status_ico} <b>{it.get('title', 'NFT')}</b> — {status_txt}\n"

            # Sotib olingan lekin hali mint qilinmagan NFT uchun TON mint tugmasi
            if status == 'sold' and it.get('buyer_user_id') == uid and not it.get('minted_tx_hash'):
                btns.append([InlineKeyboardButton(
                    f"{e('MINT')} TON da Mint: {it.get('title', 'NFT')[:18]}",
                    callback_data=f"nft_mint_{it['id']}"
                )])

            # Video ko'rish
            if it.get('video_file_path') and os.path.exists(it.get('video_file_path', '')):
                btns.append([InlineKeyboardButton(
                    f"{e('RENDER')} Ko'rish: {it.get('title', 'NFT')[:18]}",
                    callback_data=f"nft_show_{it['id']}"
                )])

        btns.append([InlineKeyboardButton(f"{e('GALLERY')} NFT Bozor", callback_data="nft_market")])
        btns.append([InlineKeyboardButton("\u2b05\ufe0f Orqaga", callback_data="menu_nft")])
        try:
            await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btns))
        except Exception:
            try:
                await cb.message.delete()
            except Exception:
                pass
            await client.send_message(cb.message.chat.id, text, reply_markup=InlineKeyboardMarkup(btns))
        await cb.answer()

    @bot.on_callback_query(filters.regex(r"^nft_show_(\d+)$"))
    async def cb_nft_show(client, cb: CallbackQuery):
        """Sotib olingan NFT ni ko'rish (video + glb)"""
        item_id = int(cb.matches[0].group(1))
        item = db.get_nft_item(item_id)
        if not item:
            await cb.answer("NFT topilmadi!", show_alert=True)
            return
        await cb.answer()
        chat_id = cb.message.chat.id

        caption = (
            f"{ce('NFT')} <b>{item.get('title')}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{ce('BLOCKCHAIN')} <i>{item.get('description', '')}</i>"
        )

        video_path = item.get('video_file_path', '')
        if video_path and os.path.exists(video_path):
            try:
                await client.send_video(chat_id=chat_id, video=video_path, caption=caption, supports_streaming=True)
            except Exception:
                await client.send_message(chat_id=chat_id, text=caption)

        glb_path = item.get('glb_file_path', '')
        if glb_path and os.path.exists(glb_path):
            try:
                await client.send_document(
                    chat_id=chat_id,
                    document=glb_path,
                    file_name=f"{item.get('title', 'NFT').replace(' ', '_')}.glb",
                    caption=f"{ce('RENDER')} <b>3D Model (.glb):</b> {item.get('title')}"
                )
            except Exception as ge:
                logger.warning(f"GLB yuborishda xatolik: {ge}")

    @bot.on_callback_query(filters.regex(r"^nft_buy_(\d+)$"))
    async def cb_nft_buy(client, cb: CallbackQuery):
        """NFT sotib olish — TON narx"""
        item_id = int(cb.matches[0].group(1))
        uid = cb.from_user.id
        item = db.get_nft_item(item_id)
        if not item or item.get("status") != "listed":
            await cb.answer("Bu NFT mavjud emas yoki allaqachon sotilgan!", show_alert=True)
            return

        if item.get("tg_user_id") == uid:
            await cb.answer("O'zingizning NFTingizni sotib ololmaysiz!", show_alert=True)
            return

        # TON narx tekshirish — foydalanuvchida TON hamyon ulangan bo'lishi kerak
        w = db.get_user_ton_wallet(uid)
        if not w or not w.get("wallet_address"):
            await cb.answer("Avval TON hamyoningizni ulang!", show_alert=True)
            from config import WEB_APP_URL
            import os
            web_url = os.environ.get("WEB_URL", WEB_APP_URL)
            wallet_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{e('TONKEEPER')} TON Hamyonni Ulash (Mini App)", web_app=WebAppInfo(url=f"{web_url}/tonconnect/page?user_id={uid}"))],
                [InlineKeyboardButton(f"{e('WALLET_CONNECT')} Hamyon Sozlamalari", callback_data="menu_wallet")],
                [InlineKeyboardButton("\u2b05\ufe0f Orqaga", callback_data=f"nft_view_{item_id}")]
            ])
            await client.send_message(
                chat_id=cb.message.chat.id,
                text=(
                    f"{ce('WARN')} <b>TON Hamyon topilmadi!</b>\n\n"
                    f"3D NFT ni sotib olish va uni to'g'ridan-to'g'ri o'z hamyoningizga mint qilish uchun, "
                    f"avval TON hamyoningizni (Tonkeeper, Telegram Wallet yoki boshqa) ulang:"
                ),
                reply_markup=wallet_kb
            )
            return

        price_ton = float(item.get('price_matic', 0))
        buyer_wallet = w["wallet_address"]

        # NFT holatini 'sold' ga o'zgartirish va buyer_user_id ni yozish
        db.update_nft_status(item_id, status="sold", buyer_user_id=uid)

        await cb.answer(f"NFT sizga biriktirildi! TON da mint qilish uchun pastdagi tugmani bosing.", show_alert=True)

        # TON Mint link generatsiya qilish
        amount_nano = int(price_ton * 1_000_000_000)  # TON nano ga o'girish
        try:
            deploy_data = generate_nft_deploy_link(buyer_wallet, f"nft://{item_id}", amount_nano=amount_nano)
            ton_link = deploy_data.get("ton_link", "")
        except Exception as te:
            logger.error(f"TON deploy link error: {te}")
            ton_link = ""

        caption = (
            f"{ce('SOLD')} <b>NFT Muvaffaqiyatli Xarid Qilindi!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ce('NFT')} <b>{item.get('title')}</b>\n"
            f"{ce('TONKEEPER')} <b>Narxi:</b> <code>{price_ton} TON</code>\n"
            f"{ce('WALLET_CONNECT')} <b>Hamyoningiz:</b> <code>{buyer_wallet[:8]}...{buyer_wallet[-6:]}</code>\n\n"
            f"{ce('MINT')} NFT ni TON blockchainga mint qilish uchun quyidagi tugmani bosing.\n"
            f"Tonkeeper yoki Telegram Wallet ochiladi va tasdiqlagach NFT hamyoningizga tushadi!"
        )

        kb_buttons = []
        if ton_link:
            kb_buttons.append([InlineKeyboardButton(
                f"{e('TONKEEPER')} TON da Mint qilish ({price_ton} TON)",
                url=ton_link
            )])
        kb_buttons.extend([
            [InlineKeyboardButton(f"{e('NFT')} Mening NFT larim", callback_data="nft_my_items")],
            [InlineKeyboardButton(f"{e('HOME')} Bosh Menyu", callback_data="back_main")]
        ])

        chat_id = cb.message.chat.id
        # Video yuborish
        video_path = item.get('video_file_path', '')
        if video_path and os.path.exists(video_path):
            try:
                await client.send_video(
                    chat_id=chat_id,
                    video=video_path,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(kb_buttons),
                    supports_streaming=True
                )
                return
            except Exception:
                pass

        await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=InlineKeyboardMarkup(kb_buttons)
        )

        # Sotuvchiga xabar
        seller_id = item.get("tg_user_id")
        if seller_id:
            try:
                await client.send_message(
                    seller_id,
                    f"{ce('SOLD')} <b>NFTingiz Sotildi!</b>\n\n"
                    f"Sizning <b>{item.get('title')}</b> 3D NFTingiz <code>{price_ton} TON</code> ga sotildi!"
                )
            except Exception:
                pass

    @bot.on_callback_query(filters.regex(r"^nft_mint_(\d+)$"))
    async def cb_nft_mint(client, cb: CallbackQuery):
        """Allaqachon sotib olingan NFT ni TON da mint qilish uchun link berish"""
        item_id = int(cb.matches[0].group(1))
        uid = cb.from_user.id
        item = db.get_nft_item(item_id)

        if not item or item.get('buyer_user_id') != uid:
            await cb.answer("Bu NFT sizga tegishli emas!", show_alert=True)
            return

        w = db.get_user_ton_wallet(uid)
        if not w or not w.get("wallet_address"):
            await cb.answer("Avval TON hamyoningizni ulang! /wallet buyrug'ini yuboring.", show_alert=True)
            return

        await cb.answer()
        buyer_wallet = w["wallet_address"]
        price_ton = float(item.get('price_matic', 0))
        amount_nano = int(price_ton * 1_000_000_000)

        try:
            deploy_data = generate_nft_deploy_link(buyer_wallet, f"nft://{item_id}", amount_nano=amount_nano)
            ton_link = deploy_data.get("ton_link", "")
        except Exception:
            ton_link = ""

        if ton_link:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{e('TONKEEPER')} TON da Mint qilish", url=ton_link)],
                [InlineKeyboardButton("\u2b05\ufe0f Orqaga", callback_data="nft_my_items")]
            ])
            await cb.message.reply_text(
                f"{ce('MINT')} <b>TON Mint</b>\n\n"
                f"{ce('NFT')} <b>{item.get('title')}</b>\n"
                f"Quyidagi tugmani bosing — Tonkeeper ochiladi va tasdiqlagach NFT hamyoningizga tushadi!",
                reply_markup=kb
            )
        else:
            await cb.message.reply_text(f"{ce('ERROR')} Mint link yaratishda xatolik yuz berdi. Qayta urinib ko'ring.")

    # =========================================================================
    # UNIVERSAL FSM TEXT HANDLER (STATE INPUTS)
    # =========================================================================
    @bot.on_message((filters.text | filters.photo | filters.document) & filters.private, group=-1)
    async def universal_state_listener(client, message: Message):
        if not message.from_user:
            message.continue_propagation()
            return
        uid = message.from_user.id
        state = USER_STATES.get(uid)
        if not state:
            message.continue_propagation()
            return

        action = state.get("action")
        text = message.text.strip() if message.text else (message.caption.strip() if message.caption else "")
        # Agar foydalanuvchi buyruq yuborsa (/start, /menu, /help va h.k.), holatdan chiqamiz
        if text.startswith("/"):
            USER_STATES.pop(uid, None)
            message.continue_propagation()
            return

        try:
            # 1. AI Support savoli
            if action == "waiting_support_ai":
                USER_STATES.pop(uid, None)
                role = state.get("role", "faq")
                lang = db.get_user_language(uid)
                wait_m = await message.reply_text(f"{ce('WAIT')} <code>Gemini AI javob tayyorlamoqda...</code>")
                try:
                    ans = await asyncio.wait_for(generate_support_answer(text, role, lang), timeout=15)
                except Exception as ai_err:
                    logger.error(f"Support AI timeout/error: {ai_err}")
                    ans = "Kechirasiz, sun'iy intellekt xizmati hozirda band. Iltimos, admin bilan to'g'ridan-to'g'ri bog'laning!"
                try:
                    await wait_m.delete()
                except Exception:
                    pass
                await message.reply_text(f"{ce('BOT')} <b>AI Maslahatchi Javobi:</b>\n\n{ans}")
                message.stop_propagation()

            # 2. Live Admin xabari
            elif action == "waiting_support_live":
                USER_STATES.pop(uid, None)
                role = state.get("role", "general")
                lang = db.get_user_language(uid)
                ticket_id = await forward_to_admin(client, message.from_user, role, text, lang)
                wait_notice = WAITING_MESSAGES.get(lang, WAITING_MESSAGES["uz"])
                await message.reply_text(f"{wait_notice}\n\n{ce('TICKET')} Murojaat raqami: <code>#{ticket_id}</code>")
                message.stop_propagation()

            # 3. Admin javobi foydalanuvchiga
            elif action == "admin_replying" and (uid == OWNER_ID or db.is_admin(uid)):
                USER_STATES.pop(uid, None)
                ticket_id = state.get("ticket_id")
                target_uid = state.get("target_user_id")
                db.add_support_message(ticket_id, sender_type="admin", message_text=text)
                user_msg = (
                    f"{ce('INVOICE')} <b>ADMIN JAVOBI (Murojaat #{ticket_id}):</b>\n\n"
                    f"{text}\n\n"
                    f"Qo'shimcha savollaringiz bo'lsa, /support orqali yozishingiz mumkin."
                )
                try:
                    await client.send_message(chat_id=target_uid, text=user_msg)
                    await message.reply_text(f"{ce('CHECK')} Javobingiz foydalanuvchiga ({target_uid}) muvaffaqiyatli yetkazildi!")
                except Exception as err:
                    await message.reply_text(f"{ce('ERROR')} Foydalanuvchiga yuborishda xato: {err}")
                message.stop_propagation()

            # 4. P2P Chek Yaratish (Wizard)
            elif action == "waiting_check_params":
                USER_STATES.pop(uid, None)
                parts = text.split()
                if len(parts) < 2:
                    await message.reply_text(f"{ce('ERROR')} Format xato! Masalan: <code>50000 5 @kanal</code> yoki <code>20000 2</code>")
                    message.stop_propagation()
                    return
                try:
                    total_amt = int(parts[0])
                    claims_cnt = int(parts[1])
                    req_ch = parts[2] if len(parts) > 2 else None
                except ValueError:
                    await message.reply_text(f"{ce('ERROR')} Summa va odam soni raqam bo'lishi kerak!")
                    message.stop_propagation()
                    return

                if total_amt < 1000 or claims_cnt < 1:
                    await message.reply_text(f"{ce('ERROR')} Minimal summa: 1,000 so'm, odam soni kamida 1 ta bo'lishi kerak!")
                    message.stop_propagation()
                    return

                ok, msg, code = create_p2p_check(uid, total_amt, claims_cnt, req_ch)
                if not ok:
                    await message.reply_text(f"{ce('ERROR')} Xatolik: {msg}")
                    message.stop_propagation()
                    return

                share_kb = get_check_claim_keyboard(code, req_ch)
                ch_text = f"\n{ce('CHANNEL')} <b>Shart:</b> @{req_ch.strip().lstrip('@')} kanaliga a'zo bo'lish" if req_ch else ""
                res_text = (
                    f"{ce('CASH')} <b>Yangi P2P Shartli Chek Yaratildi!</b>\n\n"
                    f"{ce('MONEY')} <b>Umumiy summa:</b> <code>{total_amt:,} so'm</code>\n"
                    f"{ce('FRIENDS')} <b>Qabul qiluvchilar:</b> <code>{claims_cnt} ta</code>\n"
                    f"{ce('COIN')} <b>Har biriga:</b> <code>{int(total_amt/claims_cnt):,} so'm</code>{ch_text}\n\n"
                    f"{ce('LINK')} <b>Chek Kodi:</b> <code>{code}</code>\n\n"
                    f"{RED_ANTIFRAUD_WARNING}"
                )
                await message.reply_text(res_text, reply_markup=share_kb)
                message.stop_propagation()

            # 5. P2P Chek Kodini kiritish
            elif action == "waiting_check_code":
                USER_STATES.pop(uid, None)
                clean_code = text.strip().upper()
                ok, res = await process_check_claim(client, uid, clean_code)
                if not ok:
                    await message.reply_text(f"{ce('ERROR')} {res}")
                else:
                    await message.reply_text(f"{ce('CHECK')} {res}")
                message.stop_propagation()

            # 6. Promokod kiritish
            elif action == "waiting_promo_code":
                USER_STATES.pop(uid, None)
                ok, res = user_redeem_promo(uid, text)
                await message.reply_text(res)
                message.stop_propagation()

            # 7. Instagram profil qo'shish
            elif action == "waiting_ig_profile":
                USER_STATES.pop(uid, None)
                clean_ig = text.lstrip("@").strip()
                add_instagram_target(uid, clean_ig)
                await message.reply_text(f"{ce('CHECK')} <code>@{clean_ig}</code> Instagram profili kuzatuvga qo'shildi! Endi yangi videolar avtomat YouTube ga o'tkaziladi.")
                message.stop_propagation()

            # 8. AI Video Prompt
            elif action in ("waiting_aivideo_prompt", "waiting_ai_prompt", "waiting_aivideo_prompt_single"):
                USER_STATES.pop(uid, None)
                is_sub = db.is_user_ai_video_subscribed(uid)
                if action == "waiting_aivideo_prompt_single" or not is_sub:
                    res_fee = db.deduct_single_ai_video_fee(uid)
                    if not res_fee.get("ok"):
                        await message.reply_text(
                            f"{ce('ERROR')} {res_fee.get('error', 'Balansingiz yetarli emas!')}\n\n"
                            f"1 ta AI video yaratish narxi: 15,000 so'm yoki /aivideo orqali oylik obuna xarid qiling."
                        )
                        message.stop_propagation()
                        return

                wait_m = await message.reply_text(f"{ce('WAIT')} <b>AI video yaratilmoqda...</b>\n(Flux rasm + Diktor ovozi + FFmpeg montaj ~30 soniya)")
                try:
                    lang = db.get_user_language(uid)
                    video_data = await build_ai_short_video(text, lang=lang)
                    v_path = video_data["video_path"]
                    title = video_data["title"]

                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 YouTube Kanalimga Yuklash", callback_data=f"pub_aivid_{os.path.basename(v_path)}")],
                        [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
                    ])

                    caption_text = (
                        f"{ce('VIDEO')} <b>{title}</b>\n\n"
                        f"{video_data['script']}\n\n"
                        f"{ce('WARN')} <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                    )

                    await client.send_video(
                        chat_id=message.chat.id,
                        video=v_path,
                        caption=caption_text,
                        reply_markup=kb,
                        supports_streaming=True
                    )
                    try:
                        await wait_m.delete()
                    except Exception:
                        pass
                except Exception as e:
                    import traceback
                    logger.error(f"AI Video xato: {e}\n{traceback.format_exc()}")
                    await wait_m.edit_text(f"{ce('ERROR')} Xatolik yuz berdi: {e}")
                message.stop_propagation()

            # 9. Competitor Spy URL
            elif action == "waiting_spy_url":
                USER_STATES.pop(uid, None)
                wait_m = await message.reply_text(f"{ce('SPY_HAT')} <b>Raqobatchi metama'lumotlari tahlil qilinmoqda...</b>")
                try:
                    lang = db.get_user_language(uid)
                    res = await analyze_and_steal_seo(text, lang=lang)
                    meta = res["meta"]
                    tags_str = ", ".join(meta["tags"]) if meta["tags"] else "Yashirin teglar topilmadi."

                    report = (
                        f"{ce('TARGET')} <b>RAQOBATCHI TAHLILI NATIJASI:</b>\n\n"
                        f"{ce('VIDEO')} <b>Sarlavha:</b> {meta['title']}\n"
                        f"{ce('USER')} <b>Kanal:</b> {meta['channel']}\n"
                        f"{ce('VIEWS')} <b>Ko'rishlar:</b> <code>{meta['view_count']:,} ta</code>\n"
                        f"{ce('LIKE')} <b>Layklar:</b> <code>{meta['like_count']:,} ta</code>\n\n"
                        f"{ce('SEO_TAG')} <b>YASHIRIN TEGLAR (Keywords):</b>\n<code>{tags_str}</code>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"{ce('BRAIN')} <b>GEMINI AI SEO TAVSIYALARI:</b>\n\n"
                        f"{res['ai_analysis']}\n\n"
                        f"{ce('WARN')} <i>Eslatma: Tahlil ommaviy ma'lumotlar asosida taqdim etiladi.</i>"
                    )
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Boshqa Video Tahlili", callback_data="menu_spy")],
                        [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
                    ])
                    try:
                        await wait_m.delete()
                    except Exception:
                        pass
                    await message.reply_text(report, reply_markup=kb)
                except Exception as e:
                    err_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Qayta urinish", callback_data="menu_spy")],
                        [InlineKeyboardButton("⬅️ Bosh Menyu", callback_data="back_main")]
                    ])
                    await wait_m.edit_text(f"{ce('ERROR')} Tahlil xatosi: {e}\n\nIltimos, to'g'ri YouTube video yoki Shorts havolasini yuboring.", reply_markup=err_kb)
                message.stop_propagation()

            # 10. Cashout tafsilotlari
            elif action == "waiting_cashout_details":
                USER_STATES.pop(uid, None)
                method = state.get("method", "ton")
                tokens = text.split()
                if len(tokens) == 1 and method == "ton" and tokens[0].isdigit():
                    # Foydalanuvchi ulangan hamyoni uchun faqat summani kiritdi
                    w = db.get_user_ton_wallet(uid)
                    if w and w.get("wallet_address"):
                        target_addr = w["wallet_address"]
                        amt = int(tokens[0])
                    else:
                        await message.reply_text(f"{ce('ERROR')} Hamyon manzili kiritilmadi! Masalan: <code>EQ... 100000</code>")
                        message.stop_propagation()
                        return
                elif len(tokens) < 2:
                    await message.reply_text(f"{ce('ERROR')} Format xato! Masalan: <code>EQ... 50000</code> yoki <code>@username 50000</code>")
                    message.stop_propagation()
                    return
                else:
                    target_addr = tokens[0]
                    try:
                        amt = int(tokens[1])
                    except ValueError:
                        await message.reply_text(f"{ce('ERROR')} Summa raqam bo'lishi kerak!")
                        message.stop_propagation()
                        return

                ok, res, equiv, req_id = request_user_cashout(uid, method, target_addr, amt)
                if not ok:
                    await message.reply_text(f"{ce('ERROR')} Xatolik: {res}")
                else:
                    await message.reply_text(f"{ce('CHECK')} {res}\n{ce('MONEY')} Ekvivalent: <code>{equiv}</code>")
                    # Adminga xabar yuborish (haqiqiy req_id bilan)
                    await notify_admin_new_cashout(client, req_id, message.from_user, method, target_addr, amt, equiv)
                message.stop_propagation()

            # 11. DeepLink URL
            elif action == "waiting_deeplink_url":
                USER_STATES.pop(uid, None)
                dl_info = generate_smart_deeplinks(text)
                qr_file = f"downloads/qr_{uid}.png"
                await generate_qr_code_image(dl_info["universal_url"], qr_file)

                caption = (
                    f"{ce('DEEPLINK')} <b>Smart DeepLink Tayyor!</b>\n\n"
                    f"{ce('WEB')} <b>Universal:</b> <code>{dl_info['universal_url']}</code>\n"
                    f"{ce('BOT')} <b>Android Intent:</b> <code>{dl_info['android_intent']}</code>\n"
                    f"{ce('MOBILE')} <b>iOS DeepLink:</b> <code>{dl_info['ios_deeplink']}</code>\n\n"
                    f"{ce('IDEA')} <i>QR kodni yuklab oling va istalgan joyda ulashing!</i>\n\n"
                    f"{ce('WARN')} <i>Eslatma: Qaytarib berilmaydi (NO REFUNDS).</i>"
                )
                if os.path.exists(qr_file):
                    await client.send_photo(chat_id=message.chat.id, photo=qr_file, caption=caption)
                    try: os.remove(qr_file)
                    except: pass
                else:
                    await message.reply_text(caption)
                message.stop_propagation()

            # 12. (O'chirildi — NFT endi tayyor kolleksiyadan sotib olinadi)
            # 13. NFT narxi (bozorga qo'yish)
            elif action == "waiting_nft_price":
                USER_STATES.pop(uid, None)
                item_id = state.get("item_id")
                clean_txt = text.replace(" ", "").replace(",", "").replace("so'm", "").strip()
                try:
                    price_val = int(clean_txt)
                    if price_val <= 0:
                        raise ValueError("0 dan katta bo'lishi kerak")
                except ValueError:
                    await message.reply_text(f"{ce('ERROR')} Narx noto'g'ri kiritildi! Ijobiy raqam kiriting (masalan: <code>50000</code>).")
                    message.stop_propagation()
                    return

                ok = db.update_nft_status(item_id, status="listed", price_uzs=price_val)
                if ok:
                    await message.reply_text(
                        f"✅ <b>3D NFT Bozorga Muvaffaqiyatli Chiqarildi!</b>\n\n"
                        f"💰 <b>Belgilangan narx:</b> <code>{price_val:,}</code> so'm\n"
                        f"Boshqa foydalanuvchilar /nft bo'limi orqali sotib olishlari mumkin.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🛒 NFT Bozorini Ko'rish", callback_data="nft_market")],
                            [InlineKeyboardButton("🏠 Bosh Menyu", callback_data="back_main")]
                        ])
                    )
                else:
                    await message.reply_text(f"{ce('ERROR')} NFT holatini yangilashda xatolik yuz berdi.")
                message.stop_propagation()
            else:
                message.continue_propagation()
        except (StopPropagation, ContinuePropagation):
            raise
        except Exception as state_err:
            import traceback
            logger.error(f"universal_state_listener exception for {uid}: {state_err}\n{traceback.format_exc()}")
            await message.reply_text(f"{ce('ERROR')} Xatolik yuz berdi: {state_err}\nIltimos, qaytadan urinib ko'ring yoki /support orqali yordam so'rang.")
            message.stop_propagation()
