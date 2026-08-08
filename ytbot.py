import re
import asyncio
import math
import json
from datetime import datetime, timedelta
from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message
)
from googleapiclient.discovery import build

from config import (
    BOT_TOKEN, API_ID, API_HASH, YOUTUBE_API_KEY, get_youtube_key,
    ADMIN_USERNAME, DEFAULT_PROXY, DAILY_LIMIT_USER, DAILY_LIMIT_ADMIN, get_gemini_key
)
from database import (
    add_tracked_channel, remove_tracked_channel, get_tracked_channels,
    save_channel_snapshot, save_video_snapshot,
    get_channel_history, get_channel_growth,
    add_bot_admin, is_bot_admin, get_all_admins,
    create_autopost_task,
    set_user_proxy, get_user_proxy, get_daily_usage, increment_usage, set_config
)
from autopost import autopost_worker, get_auth_url
from custom_emojis import e
import google.generativeai as genai

# ==================== YOUTUBE API ====================

def get_yt():
    try:
        key = get_youtube_key()
        return build("youtube", "v3", developerKey=key)
    except Exception:
        if YOUTUBE_API_KEY:
            return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        return None

# ==================== YORDAMCHI FUNKSIYALAR ====================

def fmt(num):
    """Raqamni chiroyli formatda"""
    if num is None: return "N/A"
    num = int(num)
    if num >= 1_000_000_000: return f"{num/1_000_000_000:.1f}B"
    if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
    if num >= 1_000: return f"{num/1_000:.1f}K"
    return str(num)

def fmt_full(num):
    """To'liq formatda"""
    if num is None: return "N/A"
    return f"{int(num):,}"

def growth_icon(val):
    if val > 0: return f"+{fmt(val)}"
    elif val < 0: return f"{fmt(val)}"
    return "0"

def parse_duration(dur):
    """ISO 8601 duration ni o'qiladigan formatga"""
    if not dur: return "N/A"
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', dur)
    if not match: return dur
    h, m, s = match.groups()
    parts = []
    if h: parts.append(f"{h}s")
    if m: parts.append(f"{m}d")
    if s: parts.append(f"{s}s")
    return ":".join(parts) if parts else "0:00"

def parse_duration_seconds(dur):
    """ISO 8601 ni soniyalarga"""
    if not dur: return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', dur)
    if not match: return 0
    h, m, s = match.groups()
    return int(h or 0)*3600 + int(m or 0)*60 + int(s or 0)

def time_ago(date_str):
    """Vaqtni 'X kun oldin' formatida"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        if diff.days > 365: return f"{diff.days // 365} yil oldin"
        if diff.days > 30: return f"{diff.days // 30} oy oldin"
        if diff.days > 0: return f"{diff.days} kun oldin"
        if diff.seconds > 3600: return f"{diff.seconds // 3600} soat oldin"
        if diff.seconds > 60: return f"{diff.seconds // 60} daqiqa oldin"
        return "hozirgina"
    except: return "N/A"

def estimate_earnings(views, cpm_low=0.5, cpm_high=5.0):
    """Taxminiy daromadni hisoblash"""
    low = (views / 1000) * cpm_low
    high = (views / 1000) * cpm_high
    return low, high

def engagement_rate(views, likes, comments):
    """Engagement foizini hisoblash"""
    if views == 0: return 0
    return ((likes + comments) / views) * 100

def extract_channel_id(text):
    """URL/username dan kanal identifikatorini olish"""
    if text.startswith("@"):
        return {"type": "username", "value": text[1:]}
    m = re.search(r'youtube\.com/channel/(UC[\w-]+)', text)
    if m: return {"type": "id", "value": m.group(1)}
    m = re.search(r'youtube\.com/@([\w.-]+)', text)
    if m: return {"type": "username", "value": m.group(1)}
    m = re.search(r'youtube\.com/(?:c|user)/([\w.-]+)', text)
    if m: return {"type": "username", "value": m.group(1)}
    return {"type": "username", "value": text.strip()}

def extract_video_id(text):
    """URL dan video ID"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{11})',
        r'youtube\.com/shorts/([\w-]{11})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m: return m.group(1)
    return text.strip() if len(text.strip()) == 11 else None

def extract_playlist_id(text):
    """URL dan playlist ID"""
    m = re.search(r'[?&]list=([\w-]+)', text)
    if m: return m.group(1)
    return text.strip()

# ==================== YOUTUBE API FUNKSIYALARI ====================

def get_channel(identifier):
    yt = get_yt()
    if not yt: return None
    try:
        if identifier["type"] == "id":
            r = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings,topicDetails,status", id=identifier["value"]).execute()
        else:
            r = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings,topicDetails,status", forUsername=identifier["value"]).execute()
        if not r.get("items"):
            sr = yt.search().list(part="snippet", q=identifier["value"], type="channel", maxResults=1).execute()
            if sr.get("items"):
                cid = sr["items"][0]["snippet"]["channelId"]
                r = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings,topicDetails,status", id=cid).execute()
        return r["items"][0] if r.get("items") else None
    except Exception as e:
        print(f"Channel API xato: {e}")
        return None

def get_video(video_id):
    yt = get_yt()
    if not yt: return None
    try:
        r = yt.videos().list(part="snippet,statistics,contentDetails,topicDetails,status", id=video_id).execute()
        return r["items"][0] if r.get("items") else None
    except Exception as e:
        print(f"Video API xato: {e}")
        return None

def get_videos_by_channel(channel_id, max_results=10, order="date"):
    yt = get_yt()
    if not yt: return []
    try:
        sr = yt.search().list(part="snippet", channelId=channel_id, order=order, type="video", maxResults=max_results).execute()
        if not sr.get("items"): return []
        ids = [i["id"]["videoId"] for i in sr["items"]]
        vr = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()
        return vr.get("items", [])
    except Exception as e:
        print(f"Videos API xato: {e}")
        return []

def get_playlists(channel_id, max_results=10):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.playlists().list(part="snippet,contentDetails", channelId=channel_id, maxResults=max_results).execute()
        return r.get("items", [])
    except: return []

def get_playlist_items(playlist_id, max_results=20):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.playlistItems().list(part="snippet,contentDetails", playlistId=playlist_id, maxResults=max_results).execute()
        return r.get("items", [])
    except: return []

def get_comments(video_id, max_results=10):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.commentThreads().list(part="snippet", videoId=video_id, maxResults=max_results, order="relevance", textFormat="plainText").execute()
        return r.get("items", [])
    except: return []

def search_youtube(query, search_type="video", max_results=10):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.search().list(part="snippet", q=query, type=search_type, maxResults=max_results).execute()
        items = r.get("items", [])
        if search_type == "video" and items:
            ids = [i["id"]["videoId"] for i in items if i["id"].get("videoId")]
            if ids:
                vr = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()
                return vr.get("items", [])
        return items
    except: return []

def get_trending(region="US", max_results=10, category_id="0"):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.videos().list(part="snippet,statistics,contentDetails", chart="mostPopular", regionCode=region, maxResults=max_results, videoCategoryId=category_id).execute()
        return r.get("items", [])
    except: return []

def get_categories(region="US"):
    yt = get_yt()
    if not yt: return []
    try:
        r = yt.videoCategories().list(part="snippet", regionCode=region).execute()
        return r.get("items", [])
    except: return []

# ==================== INLINE KEYBOARD BUILDERS ====================

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanal tahlili", callback_data="menu_channel"),
         InlineKeyboardButton("🎬 Video tahlili", callback_data="menu_video")],
        [InlineKeyboardButton("📊 Analitika", callback_data="menu_analytics"),
         InlineKeyboardButton("🔍 Qidiruv", callback_data="menu_search")],
        [InlineKeyboardButton("📌 Kuzatuv", callback_data="menu_tracking"),
         InlineKeyboardButton("⚙️ Asboblar", callback_data="menu_tools")],
        [InlineKeyboardButton("🔥 Trending", callback_data="menu_trending"),
         InlineKeyboardButton("📖 Yordam", callback_data="menu_help")],
    ])

def channel_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 To'liq statistika", callback_data="ch_full"),
         InlineKeyboardButton("👥 Obunachilar", callback_data="ch_subs")],
        [InlineKeyboardButton("🎬 So'nggi videolar", callback_data="ch_recent"),
         InlineKeyboardButton("🔥 Ommabop videolar", callback_data="ch_popular")],
        [InlineKeyboardButton("📂 Pleylistlar", callback_data="ch_playlists"),
         InlineKeyboardButton("ℹ️ Kanal haqida", callback_data="ch_about")],
        [InlineKeyboardButton("🖼 Banner/Avatar", callback_data="ch_banner"),
         InlineKeyboardButton("🔑 Kalit so'zlar", callback_data="ch_keywords")],
        [InlineKeyboardButton("⏱ Upload chastotasi", callback_data="ch_frequency"),
         InlineKeyboardButton("💰 Daromad taxmini", callback_data="ch_earnings")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def video_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 To'liq statistika", callback_data="vid_full"),
         InlineKeyboardButton("👍 Likelar", callback_data="vid_likes")],
        [InlineKeyboardButton("💬 Izohlar", callback_data="vid_comments"),
         InlineKeyboardButton("🏷 Teglar", callback_data="vid_tags")],
        [InlineKeyboardButton("🖼 Thumbnail", callback_data="vid_thumb"),
         InlineKeyboardButton("📝 Tavsif", callback_data="vid_desc")],
        [InlineKeyboardButton("⚡ Engagement", callback_data="vid_engage"),
         InlineKeyboardButton("⏱ Davomiyligi", callback_data="vid_duration")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def analytics_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 O'sish tahlili", callback_data="an_growth"),
         InlineKeyboardButton("⚖️ Solishtirish", callback_data="an_compare")],
        [InlineKeyboardButton("❤️ Engagement rate", callback_data="an_engage"),
         InlineKeyboardButton("📉 O'rtacha ko'rishlar", callback_data="an_avgviews")],
        [InlineKeyboardButton("🏆 Top videolar", callback_data="an_top"),
         InlineKeyboardButton("👎 Eng kam ko'rilgan", callback_data="an_bottom")],
        [InlineKeyboardButton("💸 Daromad taxmini", callback_data="an_earnings"),
         InlineKeyboardButton("🎯 Milestone", callback_data="an_milestone")],
        [InlineKeyboardButton("📄 To'liq hisobot", callback_data="an_report"),
         InlineKeyboardButton("🚀 Upload tezligi", callback_data="an_uploadrate")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def search_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Video qidirish", callback_data="sr_video"),
         InlineKeyboardButton("Kanal qidirish", callback_data="sr_channel")],
        [InlineKeyboardButton("Pleylist qidirish", callback_data="sr_playlist")],
        [InlineKeyboardButton("Orqaga", callback_data="back_main")],
    ])

def tracking_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="tr_add"),
         InlineKeyboardButton("➖ Kanal o'chirish", callback_data="tr_remove")],
        [InlineKeyboardButton("📋 Mening ro'yxatim", callback_data="tr_list"),
         InlineKeyboardButton("🔄 Barchasini tekshirish", callback_data="tr_checkall")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def tools_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 URL dan ID olish", callback_data="tl_id"),
         InlineKeyboardButton("🖼 Thumbnail olish", callback_data="tl_thumb")],
        [InlineKeyboardButton("⚔️ Kanal solishtirish", callback_data="tl_compare"),
         InlineKeyboardButton("🧮 Kalkulyator", callback_data="tl_calc")],
        [InlineKeyboardButton("📂 Kategoriyalar", callback_data="tl_categories"),
         InlineKeyboardButton("🌍 Davlat trending", callback_data="tl_region")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ])

def trending_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("US", callback_data="trend_US"),
         InlineKeyboardButton("UZ", callback_data="trend_UZ"),
         InlineKeyboardButton("RU", callback_data="trend_RU")],
        [InlineKeyboardButton("KR", callback_data="trend_KR"),
         InlineKeyboardButton("JP", callback_data="trend_JP"),
         InlineKeyboardButton("GB", callback_data="trend_GB")],
        [InlineKeyboardButton("TR", callback_data="trend_TR"),
         InlineKeyboardButton("IN", callback_data="trend_IN"),
         InlineKeyboardButton("DE", callback_data="trend_DE")],
        [InlineKeyboardButton("Orqaga", callback_data="back_main")],
    ])

def channel_action_kb(channel_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 So'nggi videolar", callback_data=f"cact_recent_{channel_id}"),
         InlineKeyboardButton("🔥 Ommabop", callback_data=f"cact_popular_{channel_id}")],
        [InlineKeyboardButton("📂 Pleylistlar", callback_data=f"cact_playlists_{channel_id}"),
         InlineKeyboardButton("📈 O'sish", callback_data=f"cact_growth_{channel_id}")],
        [InlineKeyboardButton("📄 To'liq hisobot", callback_data=f"cact_report_{channel_id}"),
         InlineKeyboardButton("💰 Daromad", callback_data=f"cact_earn_{channel_id}")],
        [InlineKeyboardButton("📌 Kuzatishga olish", callback_data=f"cact_track_{channel_id}"),
         InlineKeyboardButton("🔄 Yangilash", callback_data=f"cact_refresh_{channel_id}")],
    ])

def video_action_kb(video_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Izohlar", callback_data=f"vact_comments_{video_id}"),
         InlineKeyboardButton("🏷 Teglar", callback_data=f"vact_tags_{video_id}")],
        [InlineKeyboardButton("🖼 Thumbnail", callback_data=f"vact_thumb_{video_id}"),
         InlineKeyboardButton("⚡ Engagement", callback_data=f"vact_engage_{video_id}")],
        [InlineKeyboardButton("🔄 Yangilash", callback_data=f"vact_refresh_{video_id}")],
    ])

def back_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
    ])

def help_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanal buyruqlari", callback_data="help_channel"),
         InlineKeyboardButton("🎬 Video buyruqlari", callback_data="help_video")],
        [InlineKeyboardButton("📊 Analitika", callback_data="help_analytics"),
         InlineKeyboardButton("🔍 Qidiruv", callback_data="help_search")],
        [InlineKeyboardButton("📌 Kuzatuv", callback_data="help_tracking"),
         InlineKeyboardButton("⚙️ Asboblar", callback_data="help_tools")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
    ])

# ==================== BOT YARATISH ====================

def create_ytbot():
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi!")
        return None
    
    bot = Client("yt_analytics_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    
    # Adminni username (@WebDev999) orqali aniqlash
    def check_is_admin(user):
        if not user or not user.username:
            return False
        return user.username.lower() == ADMIN_USERNAME.lower()

    # ==================== /start ====================
    @bot.on_message(filters.command("start"))
    async def start_cmd(client, message):
        text = (
            f"{e('BOT')} **YouTube Analytics Bot** ga xush kelibsiz!\n\n"
            f"{e('STAR')} Bu bot orqali istalgan YouTube kanal va videolarning "
            f"to'liq statistikasini ko'rishingiz mumkin.\n\n"
            f"{e('PIN')} Quyidagi menyudan kerakli bo'limni tanlang:"
        )
        await message.reply_text(text, reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)
    
    # ==================== /help ====================
    @bot.on_message(filters.command("help"))
    async def help_cmd(client, message):
        is_admin = check_is_admin(message.from_user)
        
        help_text = (
            "📖 `YouTube Analytics Bot Buyruqlari:`\n\n"
            "📌 `Asosiy buyruqlar:`\n"
            "`/start` - Botni boshlash\n"
            "`/help` - Yordam\n"
            "`/ytlogin` - YouTube kanalini ulash\n"
            "`/autopost <soni> <qidiruv>` - Auto-post (Kunlik limit: 3 ta)\n"
            "`/setproxy <ip:port>` - O'z proxy IP ingizni o'rnatish\n"
            "`/myproxy` - Hozirgi proxy sozlamasini ko'rish\n\n"
            "📊 `Analitika va Qidiruv:`\n"
            "`/channel <kanal>` - Kanal statistikasi\n"
            "`/video <url>` - Video statistikasi\n"
            "`/compare <kanal1> <kanal2>` - Kanallarni solishtirish\n"
            "`/search <so'z>` - Qidiruv\n"
            "`/trending` - Trendlar"
        )
        
        if is_admin:
            help_text += (
                "\n\n⚙️ `Admin buyruqlari:`\n"
                "`/setcookies` - YouTube cookies faylini yuklash (.txt)"
            )
            
        await message.reply_text(help_text, reply_markup=help_menu_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /menu ====================
    @bot.on_message(filters.command("menu"))
    async def menu_cmd(client, message):
        await message.reply_text(f"{e('STAR')} Asosiy menyu:", reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)
    
    # ==================== /ping ====================
    @bot.on_message(filters.command("ping"))
    async def ping_cmd(client, message):
        start = datetime.now()
        msg = await message.reply_text("Pong!")
        diff = (datetime.now() - start).microseconds / 1000
        await msg.edit_text(f"Pong! `{diff:.0f}ms`", parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /channel ====================
    @bot.on_message(filters.command("channel"))
    async def channel_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/channel <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        if not YOUTUBE_API_KEY:
            await message.reply_text("YouTube API kaliti sozlanmagan!")
            return
        
        wait = await message.reply_text("Qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        
        s, st = ch["snippet"], ch["statistics"]
        subs = int(st.get("subscriberCount", 0))
        views = int(st.get("viewCount", 0))
        vids = int(st.get("videoCount", 0))
        avg = views // vids if vids > 0 else 0
        created = s.get("publishedAt", "")[:10]
        country = s.get("country", "N/A")
        save_channel_snapshot(ch["id"], subs, views, vids)
        
        text = (
            f"**{s['title']}**\n\n"
            f"{'='*28}\n\n"
            f"Obunachilar: `{fmt(subs)}` ({fmt_full(subs)})\n"
            f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
            f"Videolar: `{fmt(vids)}` ({fmt_full(vids)})\n"
            f"O'rtacha ko'rish/video: `{fmt(avg)}`\n"
            f"Yaratilgan: `{created}`\n"
            f"Davlat: `{country}`\n"
            f"ID: `{ch['id']}`"
        )
        await wait.edit_text(text, reply_markup=channel_action_kb(ch["id"]), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /subs ====================
    @bot.on_message(filters.command("subs"))
    async def subs_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/subs <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        subs = int(ch["statistics"].get("subscriberCount", 0))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nObunachilar: **{fmt_full(subs)}**",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /totalviews ====================
    @bot.on_message(filters.command("totalviews"))
    async def totalviews_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/totalviews <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        views = int(ch["statistics"].get("viewCount", 0))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nUmumiy ko'rishlar: **{fmt_full(views)}**",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /videocount ====================
    @bot.on_message(filters.command("videocount"))
    async def videocount_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/videocount <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        vids = int(ch["statistics"].get("videoCount", 0))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nVideolar soni: **{fmt_full(vids)}**",
            parse_mode=ParseMode.MARKDOWN
        )

    # ==================== /ytlogin ====================
    
    @bot.on_message(filters.command("ytlogin"))
    async def ytlogin_cmd(client, message):
        try:
            url = get_auth_url(message.from_user.id)
            text = (
                "🔗 **YouTube kanalingizni ulash uchun quyidagi linkni bosing:**\n\n"
                f"[➡️ Google orqali ruxsat berish]({url})\n\n"
                "**Qadamlar:**\n"
                "1️⃣ Yuqoridagi linkni bosing\n"
                "2️⃣ YouTube kanalingiz bor Gmail akkauntni tanlang\n"
                "3️⃣ \"Allow\" (Ruxsat berish) tugmasini bosing\n"
                "4️⃣ Avtomatik ulanadi — bu yerga qaytib xabar keladi!\n\n"
                "_Ruxsat berganingizdan so'ng, bot avtomatik xabar yuboradi._"
            )
            await message.reply_text(text, disable_web_page_preview=True)
        except Exception as e:
            await message.reply_text(f"❌ Xatolik yuz berdi: {e}")
            
    # ==================== /setproxy & /myproxy ====================
    @bot.on_message(filters.command("setproxy"))
    async def setproxy_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("❌ `Noto'g'ri format! Foydalanish: /setproxy http://ip:port yoki /setproxy socks5://user:pass@ip:port`", parse_mode=ParseMode.MARKDOWN)
            return
        proxy = args[1].strip()
        user_id = message.from_user.id
        if set_user_proxy(user_id, proxy):
            await message.reply_text(f"✅ `Proxy muvaffaqiyatli saqlandi:` `{proxy}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("❌ `Bazaga saqlashda xatolik yuz berdi.`", parse_mode=ParseMode.MARKDOWN)

    @bot.on_message(filters.command("myproxy"))
    async def myproxy_cmd(client, message):
        user_id = message.from_user.id
        proxy = get_user_proxy(user_id)
        if proxy:
            await message.reply_text(f"🌐 `Sizning proxy sozlamangiz:` `{proxy}`", parse_mode=ParseMode.MARKDOWN)
        else:
            def_p = DEFAULT_PROXY or "o'rnatilmagan"
            await message.reply_text(f"🌐 `Sizda shaxsiy proxy yo'q. Default proxy:` `{def_p}`", parse_mode=ParseMode.MARKDOWN)

    # ==================== /autopost ====================
    
    @bot.on_message(filters.command("autopost"))
    async def autopost_cmd(client, message):
        user_id = message.from_user.id
        is_admin = check_is_admin(message.from_user)

        # Limit tekshirish
        daily_used = get_daily_usage(user_id)
        limit = DAILY_LIMIT_ADMIN if is_admin else DAILY_LIMIT_USER

        if daily_used >= limit:
            await message.reply_text(
                f"⏳ `Kunlik limitingiz ({limit} ta) tugadi! Ertaga qayta urinib ko'ring.`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.reply_text("`Buzilgan format!\nTo'g'ri foydalanish: /autopost <soni> <qidiruv so'zi>\nMasalan: /autopost 2 gaming shorts`", parse_mode=ParseMode.MARKDOWN)
            return
            
        try:
            count = int(args[1])
            query = args[2]

            remaining = limit - daily_used
            if count > remaining:
                await message.reply_text(
                    f"❌ `Siz bugun max {remaining} ta video yuklay olasiz! (Kunlik limit: {limit} ta)`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
                
            task_id = create_autopost_task(user_id, "my_channel", query, "video", count)
            if task_id:
                increment_usage(user_id, count)
                user_proxy = get_user_proxy(user_id) or DEFAULT_PROXY
                await message.reply_text(f"✅ `Vazifa qabul qilindi. {count} ta video '{query}' bo'yicha qidirilmoqda...`", parse_mode=ParseMode.MARKDOWN)
                asyncio.create_task(autopost_worker(task_id, user_id, query, count, client, message.chat.id, proxy_url=user_proxy))
            else:
                await message.reply_text("❌ `Xatolik yuz berdi. DB ni tekshiring.`", parse_mode=ParseMode.MARKDOWN)
                
        except ValueError:
            await message.reply_text("❌ `Soni raqam bo'lishi kerak!`", parse_mode=ParseMode.MARKDOWN)

    
    # ==================== /setcookies ====================
    
    @bot.on_message(filters.command("setcookies"))
    async def setcookies_cmd(client, message):
        # Admin check (@WebDev999)
        if not check_is_admin(message.from_user):
            await message.reply_text("❌ `Faqat adminlar cookies yuklay oladi!`", parse_mode=ParseMode.MARKDOWN)
            return
            
        doc = message.document
        if not doc:
            await message.reply_text("❌ `Siz fayl yubormadingiz!\n\nTo'g'ri usul: Faylni Telegramga yuklayotganda, izoh (caption) qismiga /setcookies deb yozing.`", parse_mode=ParseMode.MARKDOWN)
            return
            
        if not doc.file_name.endswith(".txt"):
            await message.reply_text("❌ `Iltimos, faqat .txt formatidagi fayl yuklang (masalan cookies.txt).`", parse_mode=ParseMode.MARKDOWN)
            return
            
        try:
            # Faylni xotiraga yuklash
            file_path = await client.download_media(message)
            with open(file_path, 'r', encoding='utf-8') as f:
                cookies_text = f.read()
            import os
            os.remove(file_path)
            
            # Bazaga saqlash
            if set_config("yt_cookies", cookies_text):
                await message.reply_text("✅ `Cookies muvaffaqiyatli saqlandi! Endi /autopost ishlab ketadi.`", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text("❌ `Bazaga saqlashda xatolik yuz berdi.`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await message.reply_text(f"❌ `Faylni o'qishda xatolik: {e}`", parse_mode=ParseMode.MARKDOWN)

    # ==================== /about ====================
    @bot.on_message(filters.command("about"))
    async def about_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/about <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        desc = ch["snippet"].get("description", "Tavsif mavjud emas")[:1000]
        country = ch["snippet"].get("country", "N/A")
        created = ch["snippet"].get("publishedAt", "")[:10]
        custom_url = ch["snippet"].get("customUrl", "N/A")
        text = (
            f"**{ch['snippet']['title']}** haqida\n\n"
            f"{'='*28}\n\n"
            f"Custom URL: `{custom_url}`\n"
            f"Davlat: `{country}`\n"
            f"Yaratilgan: `{created}`\n"
            f"ID: `{ch['id']}`\n\n"
            f"Tavsif:\n{desc}"
        )
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /country ====================
    @bot.on_message(filters.command("country"))
    async def country_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/country <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        country = ch["snippet"].get("country", "Noma'lum")
        await message.reply_text(f"**{ch['snippet']['title']}**\n\nDavlat: **{country}**", parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /created ====================
    @bot.on_message(filters.command("created"))
    async def created_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/created <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        created = ch["snippet"].get("publishedAt", "")[:10]
        age = time_ago(ch["snippet"].get("publishedAt", ""))
        await message.reply_text(
            f"**{ch['snippet']['title']}**\n\nYaratilgan: **{created}** ({age})",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /keywords ====================
    @bot.on_message(filters.command("keywords"))
    async def keywords_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/keywords <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        bs = ch.get("brandingSettings", {}).get("channel", {})
        kw = bs.get("keywords", "Kalit so'zlar topilmadi")
        await message.reply_text(
            f"**{ch['snippet']['title']}** kalit so'zlari:\n\n`{kw}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /banner ====================
    @bot.on_message(filters.command("banner"))
    async def banner_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/banner <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        bi = ch.get("brandingSettings", {}).get("image", {})
        banner = bi.get("bannerExternalUrl", "")
        if banner:
            await message.reply_photo(banner, caption=f"**{ch['snippet']['title']}** banner rasmi", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("Bu kanalda banner rasmi topilmadi.")
    
    # ==================== /avatar ====================
    @bot.on_message(filters.command("avatar"))
    async def avatar_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/avatar <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        thumbs = ch["snippet"].get("thumbnails", {})
        url = thumbs.get("high", thumbs.get("medium", thumbs.get("default", {}))).get("url", "")
        if url:
            await message.reply_photo(url, caption=f"**{ch['snippet']['title']}** profil rasmi", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("Profil rasmi topilmadi.")
    
    # ==================== /video ====================
    @bot.on_message(filters.command("video"))
    async def video_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/video <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        wait = await message.reply_text("Qidirilmoqda...")
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await wait.edit_text("Video topilmadi. URL ni tekshiring.")
            return
        v = get_video(vid_id)
        if not v:
            await wait.edit_text("Video ma'lumotlari topilmadi.")
            return
        
        sn, st = v["snippet"], v["statistics"]
        views = int(st.get("viewCount", 0))
        likes = int(st.get("likeCount", 0))
        comments = int(st.get("commentCount", 0))
        dur = parse_duration(v.get("contentDetails", {}).get("duration", ""))
        published = sn.get("publishedAt", "")[:10]
        ago = time_ago(sn.get("publishedAt", ""))
        eng = engagement_rate(views, likes, comments)
        lr = (likes / views * 100) if views > 0 else 0
        low, high = estimate_earnings(views)
        
        save_video_snapshot(vid_id, sn.get("channelId", ""), sn["title"], views, likes, comments)
        
        text = (
            f"**{sn['title']}**\n\n"
            f"{'='*28}\n\n"
            f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
            f"Likelar: `{fmt(likes)}` ({fmt_full(likes)})\n"
            f"Izohlar: `{fmt(comments)}` ({fmt_full(comments)})\n"
            f"Like/View: `{lr:.2f}%`\n"
            f"Engagement: `{eng:.2f}%`\n"
            f"Davomiyligi: `{dur}`\n"
            f"Chop etilgan: `{published}` ({ago})\n"
            f"Kanal: {sn.get('channelTitle', 'N/A')}\n"
            f"Taxminiy daromad: `${low:.0f} - ${high:.0f}`\n"
            f"ID: `{vid_id}`"
        )
        await wait.edit_text(text, reply_markup=video_action_kb(vid_id), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /recent ====================
    @bot.on_message(filters.command("recent"))
    async def recent_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/recent <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("So'nggi videolar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        text = f"**{ch['snippet']['title']}** - So'nggi videolar\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            likes = int(vs.get("likeCount", 0))
            ago = time_ago(v["snippet"].get("publishedAt", ""))
            text += f"**{i}.** {v['snippet']['title'][:45]}\n"
            text += f"   `{fmt(views)}` ko'rish | `{fmt(likes)}` like | {ago}\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /popular ====================
    @bot.on_message(filters.command("popular"))
    async def popular_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/popular <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Eng ommabop videolar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="viewCount")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        text = f"**{ch['snippet']['title']}** - Eng ommabop\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            likes = int(vs.get("likeCount", 0))
            text += f"**{i}.** {v['snippet']['title'][:45]}\n"
            text += f"   `{fmt(views)}` ko'rish | `{fmt(likes)}` like\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /playlists ====================
    @bot.on_message(filters.command("playlists"))
    async def playlists_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/playlists <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Pleylistlar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        pls = get_playlists(ch["id"], max_results=15)
        if not pls:
            await wait.edit_text("Pleylistlar topilmadi.")
            return
        text = f"**{ch['snippet']['title']}** - Pleylistlar\n\n{'='*28}\n\n"
        for i, p in enumerate(pls, 1):
            count = p.get("contentDetails", {}).get("itemCount", 0)
            text += f"**{i}.** {p['snippet']['title'][:45]}\n"
            text += f"   `{count}` ta video\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /compare ====================
    @bot.on_message(filters.command("compare"))
    async def compare_cmd(client, message):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.reply_text(
                "Foydalanish: `/compare <kanal1> <kanal2>`\n\n"
                "Misol: `/compare @mkbhd @linustechtips`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        wait = await message.reply_text("Kanallar solishtirilmoqda...")
        ch1 = get_channel(extract_channel_id(args[1]))
        ch2 = get_channel(extract_channel_id(args[2]))
        if not ch1 or not ch2:
            await wait.edit_text("Kanallardan biri topilmadi.")
            return
        
        s1, s2 = ch1["statistics"], ch2["statistics"]
        sub1, sub2 = int(s1.get("subscriberCount",0)), int(s2.get("subscriberCount",0))
        v1, v2 = int(s1.get("viewCount",0)), int(s2.get("viewCount",0))
        vc1, vc2 = int(s1.get("videoCount",0)), int(s2.get("videoCount",0))
        avg1 = v1//vc1 if vc1 else 0
        avg2 = v2//vc2 if vc2 else 0
        
        w_sub = ch1["snippet"]["title"] if sub1>sub2 else ch2["snippet"]["title"]
        w_view = ch1["snippet"]["title"] if v1>v2 else ch2["snippet"]["title"]
        w_avg = ch1["snippet"]["title"] if avg1>avg2 else ch2["snippet"]["title"]
        
        text = (
            f"**Solishtirish**\n\n{'='*28}\n\n"
            f"| | **{ch1['snippet']['title'][:15]}** | **{ch2['snippet']['title'][:15]}** |\n"
            f"|---|---|---|\n"
            f"| Obunachilar | `{fmt(sub1)}` | `{fmt(sub2)}` |\n"
            f"| Ko'rishlar | `{fmt(v1)}` | `{fmt(v2)}` |\n"
            f"| Videolar | `{fmt(vc1)}` | `{fmt(vc2)}` |\n"
            f"| O'rtacha | `{fmt(avg1)}` | `{fmt(avg2)}` |\n\n"
            f"{'='*28}\n\n"
            f"Obunachilar bo'yicha: **{w_sub}**\n"
            f"Ko'rishlar bo'yicha: **{w_view}**\n"
            f"O'rtacha bo'yicha: **{w_avg}**"
        )
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /growth ====================
    @bot.on_message(filters.command("growth"))
    async def growth_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/growth <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Tahlil qilinmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        st = ch["statistics"]
        subs = int(st.get("subscriberCount",0))
        views = int(st.get("viewCount",0))
        vids = int(st.get("videoCount",0))
        save_channel_snapshot(ch["id"], subs, views, vids)
        g = get_channel_growth(ch["id"])
        
        text = f"**{ch['snippet']['title']}** - O'sish\n\n{'='*28}\n\n"
        text += f"Obunachilar: `{fmt(subs)}` ({fmt_full(subs)})\n"
        text += f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
        text += f"Videolar: `{fmt(vids)}`\n\n"
        if g:
            text += f"{'='*28}\n\nOxirgi tekshiruvdan beri:\n\n"
            text += f"Obunachilar: {growth_icon(g['sub_growth'])}\n"
            text += f"Ko'rishlar: {growth_icon(g['view_growth'])}\n"
            text += f"Videolar: {growth_icon(g['video_growth'])}\n"
            text += f"\nOldingi: `{g['previous']['snapshot_at'][:19]}`"
        else:
            text += "\nO'sish ma'lumotlari hali yetarli emas."
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /engagement ====================
    @bot.on_message(filters.command("engagement"))
    async def engagement_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/engagement <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Engagement hisoblanmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        
        total_views, total_likes, total_comments = 0, 0, 0
        for v in videos:
            vs = v["statistics"]
            total_views += int(vs.get("viewCount", 0))
            total_likes += int(vs.get("likeCount", 0))
            total_comments += int(vs.get("commentCount", 0))
        
        eng = engagement_rate(total_views, total_likes, total_comments)
        lr = (total_likes / total_views * 100) if total_views else 0
        cr = (total_comments / total_views * 100) if total_views else 0
        
        level = "Juda yaxshi" if eng > 5 else "Yaxshi" if eng > 3 else "O'rtacha" if eng > 1 else "Past"
        
        text = (
            f"**{ch['snippet']['title']}** - Engagement\n\n{'='*28}\n\n"
            f"Oxirgi {len(videos)} ta video asosida:\n\n"
            f"Engagement Rate: **{eng:.2f}%** ({level})\n"
            f"Like Rate: `{lr:.2f}%`\n"
            f"Comment Rate: `{cr:.4f}%`\n\n"
            f"Umumiy ko'rishlar: `{fmt(total_views)}`\n"
            f"Umumiy likelar: `{fmt(total_likes)}`\n"
            f"Umumiy izohlar: `{fmt(total_comments)}`"
        )
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /earnings ====================
    @bot.on_message(filters.command("earnings"))
    async def earnings_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/earnings <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        views = int(ch["statistics"].get("viewCount", 0))
        low, high = estimate_earnings(views)
        
        videos = get_videos_by_channel(ch["id"], max_results=5, order="date")
        monthly_views = 0
        for v in videos:
            monthly_views += int(v["statistics"].get("viewCount", 0))
        m_low, m_high = estimate_earnings(monthly_views)
        
        text = (
            f"**{ch['snippet']['title']}** - Daromad taxmini\n\n{'='*28}\n\n"
            f"Umumiy taxminiy daromad:\n"
            f"  `${low:,.0f}` - `${high:,.0f}`\n\n"
            f"So'nggi videolar asosida (oylik taxmin):\n"
            f"  `${m_low:,.0f}` - `${m_high:,.0f}`\n\n"
            f"CPM oralig'i: $0.50 - $5.00\n\n"
            f"Bu faqat taxmin. Haqiqiy daromad niche, davlat va "
            f"reklama turlariga bog'liq."
        )
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /milestone ====================
    @bot.on_message(filters.command("milestone"))
    async def milestone_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/milestone <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        subs = int(ch["statistics"].get("subscriberCount", 0))
        milestones = [100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000, 100000000]
        next_m = None
        for m in milestones:
            if subs < m:
                next_m = m
                break
        
        text = f"**{ch['snippet']['title']}** - Milestone\n\n{'='*28}\n\n"
        text += f"Hozirgi obunachilar: **{fmt_full(subs)}**\n\n"
        if next_m:
            remaining = next_m - subs
            progress = (subs / next_m) * 100
            bar_len = 20
            filled = int(bar_len * progress / 100)
            bar = "|" * filled + "." * (bar_len - filled)
            text += f"Keyingi milestone: **{fmt(next_m)}**\n"
            text += f"Qoldi: **{fmt_full(remaining)}** obunachi\n"
            text += f"Progress: `[{bar}]` {progress:.1f}%\n"
        else:
            text += "Barcha asosiy milestonelarni qo'lga kiritgan!"
        
        # O'tilgan milestonlar
        passed = [m for m in milestones if subs >= m]
        if passed:
            text += f"\n\nO'tilgan milestonelar: "
            text += ", ".join([f"`{fmt(m)}`" for m in passed])
        
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /report ====================
    @bot.on_message(filters.command("report"))
    async def report_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/report <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("To'liq hisobot tayyorlanmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        
        sn, st = ch["snippet"], ch["statistics"]
        subs = int(st.get("subscriberCount",0))
        views = int(st.get("viewCount",0))
        vids = int(st.get("videoCount",0))
        avg = views//vids if vids else 0
        created = sn.get("publishedAt","")[:10]
        country = sn.get("country","N/A")
        low, high = estimate_earnings(views)
        
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        t_views, t_likes, t_comments = 0, 0, 0
        durations = []
        for v in videos:
            vs = v["statistics"]
            t_views += int(vs.get("viewCount",0))
            t_likes += int(vs.get("likeCount",0))
            t_comments += int(vs.get("commentCount",0))
            durations.append(parse_duration_seconds(v.get("contentDetails",{}).get("duration","")))
        
        eng = engagement_rate(t_views, t_likes, t_comments) if t_views else 0
        avg_dur = sum(durations)//len(durations) if durations else 0
        avg_dur_min = avg_dur // 60
        avg_dur_sec = avg_dur % 60
        
        save_channel_snapshot(ch["id"], subs, views, vids)
        
        text = (
            f"**{sn['title']}** - TO'LIQ HISOBOT\n\n"
            f"{'='*30}\n\n"
            f"**ASOSIY STATISTIKA**\n"
            f"Obunachilar: `{fmt_full(subs)}`\n"
            f"Ko'rishlar: `{fmt_full(views)}`\n"
            f"Videolar: `{fmt_full(vids)}`\n"
            f"O'rtacha/video: `{fmt(avg)}`\n"
            f"Davlat: `{country}`\n"
            f"Yaratilgan: `{created}`\n\n"
            f"**ENGAGEMENT (oxirgi {len(videos)} video)**\n"
            f"Engagement: `{eng:.2f}%`\n"
            f"O'rtacha ko'rish: `{fmt(t_views//len(videos) if videos else 0)}`\n"
            f"O'rtacha like: `{fmt(t_likes//len(videos) if videos else 0)}`\n"
            f"O'rtacha izoh: `{fmt(t_comments//len(videos) if videos else 0)}`\n"
            f"O'rtacha davomiylik: `{avg_dur_min}d {avg_dur_sec}s`\n\n"
            f"**DAROMAD TAXMINI**\n"
            f"Umumiy: `${low:,.0f}` - `${high:,.0f}`\n\n"
            f"{'='*30}\n"
            f"ID: `{ch['id']}`"
        )
        await wait.edit_text(text, reply_markup=channel_action_kb(ch["id"]), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /comments ====================
    @bot.on_message(filters.command("comments"))
    async def comments_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/comments <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        wait = await message.reply_text("Izohlar yuklanmoqda...")
        comments = get_comments(vid_id, max_results=10)
        if not comments:
            await wait.edit_text("Izohlar topilmadi yoki o'chirilgan.")
            return
        text = f"**Top izohlar**\n\n{'='*28}\n\n"
        for i, c in enumerate(comments, 1):
            sn = c["snippet"]["topLevelComment"]["snippet"]
            author = sn.get("authorDisplayName","")[:20]
            txt = sn.get("textDisplay","")[:100]
            likes = int(sn.get("likeCount",0))
            text += f"**{i}. {author}** ({fmt(likes)} like)\n{txt}\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /tags ====================
    @bot.on_message(filters.command("tags"))
    async def tags_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/tags <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        v = get_video(vid_id)
        if not v:
            await message.reply_text("Video ma'lumotlari topilmadi.")
            return
        tags = v["snippet"].get("tags", [])
        if not tags:
            await message.reply_text("Bu videoda teglar topilmadi.")
            return
        text = f"**{v['snippet']['title'][:40]}** - Teglar\n\n"
        text += f"Jami: **{len(tags)}** ta teg\n\n"
        text += " | ".join([f"`{t}`" for t in tags[:40]])
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /thumbnail ====================
    @bot.on_message(filters.command("thumbnail"))
    async def thumbnail_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/thumbnail <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        url = f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg"
        await message.reply_photo(url, caption=f"Video thumbnail\nID: `{vid_id}`", parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /search ====================
    @bot.on_message(filters.command("search"))
    async def search_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/search <so'z>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Qidirilmoqda...")
        results = search_youtube(args[1], "video", 10)
        if not results:
            await wait.edit_text("Natija topilmadi.")
            return
        text = f"**Qidiruv:** `{args[1]}`\n\n{'='*28}\n\n"
        for i, v in enumerate(results, 1):
            vs = v.get("statistics", {})
            views = int(vs.get("viewCount", 0))
            ago = time_ago(v["snippet"].get("publishedAt", ""))
            text += f"**{i}.** {v['snippet']['title'][:45]}\n"
            text += f"   {v['snippet'].get('channelTitle','')} | `{fmt(views)}` | {ago}\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /searchch ====================
    @bot.on_message(filters.command("searchch"))
    async def searchch_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/searchch <kanal nomi>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Kanallar qidirilmoqda...")
        results = search_youtube(args[1], "channel", 10)
        if not results:
            await wait.edit_text("Natija topilmadi.")
            return
        text = f"**Kanal qidiruvi:** `{args[1]}`\n\n{'='*28}\n\n"
        buttons = []
        for i, ch in enumerate(results, 1):
            sn = ch["snippet"]
            title = sn.get("title", sn.get("channelTitle", "N/A"))[:40]
            desc = sn.get("description", "")[:60]
            text += f"**{i}.** {title}\n   {desc}\n\n"
            cid = ch.get("id", {})
            if isinstance(cid, dict):
                cid = cid.get("channelId", "")
            if cid and len(buttons) < 5:
                buttons.append([InlineKeyboardButton(f"{i}. {title[:25]}", callback_data=f"cact_refresh_{cid}")])
        kb = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("Bosh menyu", callback_data="back_main")]]) if buttons else back_main_kb()
        await wait.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /trending ====================
    @bot.on_message(filters.command("trending"))
    async def trending_cmd(client, message):
        args = message.text.split()
        region = args[1].upper() if len(args) > 1 else "US"
        wait = await message.reply_text(f"Trending ({region}) yuklanmoqda...")
        videos = get_trending(region, max_results=10)
        if not videos:
            await wait.edit_text("Trending topilmadi.")
            return
        text = f"**Trending - {region}**\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            text += f"**{i}.** {v['snippet']['title'][:40]}\n"
            text += f"   {v['snippet'].get('channelTitle','')} | `{fmt(views)}`\n\n"
        await wait.edit_text(text, reply_markup=trending_menu_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /track ====================
    @bot.on_message(filters.command("track"))
    async def track_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/track <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        st = ch["statistics"]
        subs, views, vids = int(st.get("subscriberCount",0)), int(st.get("viewCount",0)), int(st.get("videoCount",0))
        add_tracked_channel(message.from_user.id, ch["id"], ch["snippet"]["title"])
        save_channel_snapshot(ch["id"], subs, views, vids)
        await message.reply_text(
            f"**{ch['snippet']['title']}** kuzatishga qo'shildi!\n\n"
            f"Obunachilar: `{fmt(subs)}`\n"
            f"O'sishni ko'rish: `/growth {ch['snippet']['title']}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== /untrack ====================
    @bot.on_message(filters.command("untrack"))
    async def untrack_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/untrack <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if ch:
            remove_tracked_channel(message.from_user.id, ch["id"])
            await message.reply_text(f"**{ch['snippet']['title']}** kuzatishdan olib tashlandi.", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("Kanal topilmadi.")
    
    # ==================== /mylist ====================
    @bot.on_message(filters.command("mylist"))
    async def mylist_cmd(client, message):
        channels = get_tracked_channels(message.from_user.id)
        if not channels:
            await message.reply_text("Hali hech qanday kanal kuzatilmayapti.\n\nQo'shish: `/track <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        text = "**Kuzatayotgan kanallarim**\n\n"
        buttons = []
        for i, ch in enumerate(channels, 1):
            text += f"**{i}.** {ch['channel_title']}\n"
            buttons.append([InlineKeyboardButton(f"{ch['channel_title'][:30]}", callback_data=f"cact_refresh_{ch['channel_id']}")])
        kb = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("Bosh menyu", callback_data="back_main")]])
        await message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /checkall ====================
    @bot.on_message(filters.command("checkall"))
    async def checkall_cmd(client, message):
        channels = get_tracked_channels(message.from_user.id)
        if not channels:
            await message.reply_text("Kuzatuvdagi kanallar yo'q.", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Barcha kanallar tekshirilmoqda...")
        text = "**Barcha kanallar holati**\n\n"
        for ch_data in channels:
            chinfo = get_channel({"type": "id", "value": ch_data["channel_id"]})
            if chinfo:
                st = chinfo["statistics"]
                subs = int(st.get("subscriberCount",0))
                views = int(st.get("viewCount",0))
                vids = int(st.get("videoCount",0))
                save_channel_snapshot(ch_data["channel_id"], subs, views, vids)
                g = get_channel_growth(ch_data["channel_id"])
                growth_text = ""
                if g:
                    growth_text = f" ({growth_icon(g['sub_growth'])})"
                text += f"**{chinfo['snippet']['title']}**\n"
                text += f"  `{fmt(subs)}`{growth_text} sub | `{fmt(views)}` views\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /topvideos ====================
    @bot.on_message(filters.command("topvideos"))
    async def topvideos_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/topvideos <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        wait = await message.reply_text("Top videolar qidirilmoqda...")
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await wait.edit_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="viewCount")
        if not videos:
            await wait.edit_text("Videolar topilmadi.")
            return
        videos.sort(key=lambda x: int(x["statistics"].get("viewCount",0)), reverse=True)
        text = f"**{ch['snippet']['title']}** - TOP 10\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            likes = int(vs.get("likeCount", 0))
            eng = engagement_rate(views, likes, int(vs.get("commentCount",0)))
            medal = ["1.", "2.", "3."][i-1] if i <= 3 else f"{i}."
            text += f"**{medal}** {v['snippet']['title'][:40]}\n"
            text += f"   `{fmt(views)}` ko'rish | `{fmt(likes)}` like | eng: `{eng:.1f}%`\n\n"
        await wait.edit_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /avgviews ====================
    @bot.on_message(filters.command("avgviews"))
    async def avgviews_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/avgviews <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if not videos:
            await message.reply_text("Videolar topilmadi.")
            return
        views_list = [int(v["statistics"].get("viewCount",0)) for v in videos]
        likes_list = [int(v["statistics"].get("likeCount",0)) for v in videos]
        avg_v = sum(views_list) // len(views_list)
        avg_l = sum(likes_list) // len(likes_list)
        max_v = max(views_list)
        min_v = min(views_list)
        text = (
            f"**{ch['snippet']['title']}** - O'rtacha\n\n{'='*28}\n\n"
            f"Oxirgi {len(videos)} ta video:\n\n"
            f"O'rtacha ko'rish: **{fmt_full(avg_v)}**\n"
            f"O'rtacha like: **{fmt_full(avg_l)}**\n"
            f"Eng ko'p: **{fmt_full(max_v)}**\n"
            f"Eng kam: **{fmt_full(min_v)}**\n"
            f"Farq: **{fmt_full(max_v - min_v)}**"
        )
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /uploadfreq ====================
    @bot.on_message(filters.command("uploadfreq"))
    async def uploadfreq_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/uploadfreq <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        ch = get_channel(extract_channel_id(args[1]))
        if not ch:
            await message.reply_text("Kanal topilmadi.")
            return
        videos = get_videos_by_channel(ch["id"], max_results=10, order="date")
        if len(videos) < 2:
            await message.reply_text("Yetarli ma'lumot yo'q.")
            return
        dates = []
        for v in videos:
            try:
                dt = datetime.fromisoformat(v["snippet"]["publishedAt"].replace('Z', '+00:00'))
                dates.append(dt)
            except: pass
        if len(dates) < 2:
            await message.reply_text("Sana ma'lumotlari topilmadi.")
            return
        dates.sort(reverse=True)
        diffs = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
        avg_days = sum(diffs) / len(diffs)
        per_week = 7 / avg_days if avg_days > 0 else 0
        per_month = 30 / avg_days if avg_days > 0 else 0
        
        text = (
            f"**{ch['snippet']['title']}** - Upload chastotasi\n\n{'='*28}\n\n"
            f"Oxirgi {len(videos)} ta video asosida:\n\n"
            f"O'rtacha interval: **{avg_days:.1f} kun**\n"
            f"Haftasiga: **{per_week:.1f}** ta video\n"
            f"Oyiga: **{per_month:.1f}** ta video\n"
        )
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /id ====================
    @bot.on_message(filters.command("id"))
    async def id_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/id <URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        url = args[1]
        vid_id = extract_video_id(url)
        ch_id = extract_channel_id(url)
        pl_id = extract_playlist_id(url) if "list=" in url else None
        
        text = "**URL dan ID**\n\n"
        if vid_id and len(vid_id) == 11:
            text += f"Video ID: `{vid_id}`\n"
        if ch_id:
            text += f"Kanal: `{ch_id['value']}` ({ch_id['type']})\n"
        if pl_id and pl_id != url.strip():
            text += f"Playlist ID: `{pl_id}`\n"
        if text == "**URL dan ID**\n\n":
            text += "ID aniqlab bo'lmadi. URL ni tekshiring."
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /categories ====================
    @bot.on_message(filters.command("categories"))
    async def categories_cmd(client, message):
        args = message.text.split()
        region = args[1].upper() if len(args) > 1 else "US"
        cats = get_categories(region)
        if not cats:
            await message.reply_text("Kategoriyalar topilmadi.")
            return
        text = f"**YouTube kategoriyalari ({region})**\n\n"
        for c in cats:
            text += f"`{c['id']}` - {c['snippet']['title']}\n"
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /playlist ====================
    @bot.on_message(filters.command("playlist"))
    async def playlist_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/playlist <URL yoki ID>`", parse_mode=ParseMode.MARKDOWN)
            return
        pl_id = extract_playlist_id(args[1])
        items = get_playlist_items(pl_id, max_results=15)
        if not items:
            await message.reply_text("Pleylist topilmadi yoki bo'sh.")
            return
        text = f"**Pleylist videolari** ({len(items)} ta)\n\n{'='*28}\n\n"
        for i, item in enumerate(items, 1):
            sn = item["snippet"]
            text += f"**{i}.** {sn['title'][:45]}\n"
            text += f"   {sn.get('videoOwnerChannelTitle','')[:30]}\n\n"
        await message.reply_text(text, reply_markup=back_main_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /desc ====================
    @bot.on_message(filters.command("desc"))
    async def desc_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Foydalanish: `/desc <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        vid_id = extract_video_id(args[1])
        if not vid_id:
            await message.reply_text("Video topilmadi.")
            return
        v = get_video(vid_id)
        if not v:
            await message.reply_text("Video ma'lumotlari topilmadi.")
            return
        desc = v["snippet"].get("description", "Tavsif yo'q")[:2000]
        await message.reply_text(f"**{v['snippet']['title'][:40]}**\n\n{desc}", parse_mode=ParseMode.MARKDOWN)
    
    # ==================== CALLBACK QUERY HANDLERS ====================
    
    @bot.on_callback_query(filters.regex("^back_main$"))
    async def cb_back_main(client, cb: CallbackQuery):
        await cb.message.edit_text("Asosiy menyu:", reply_markup=main_menu_kb())
        await cb.answer()
    
    @bot.on_callback_query(filters.regex("^menu_"))
    async def cb_menu(client, cb: CallbackQuery):
        menu = cb.data.replace("menu_", "")
        menus = {
            "channel": ("**Kanal tahlili**\n\nKanal nomini yoki URL ni buyruq bilan yuboring:", channel_menu_kb()),
            "video": ("**Video tahlili**\n\nVideo URL ni buyruq bilan yuboring:", video_menu_kb()),
            "analytics": ("**Analitika va O'sish**\n\nKanal nomini buyruq bilan yuboring:", analytics_menu_kb()),
            "search": ("**Qidiruv**\n\nQidiruv so'zini buyruq bilan yuboring:", search_menu_kb()),
            "tracking": ("**Kanal kuzatuvi**\n\nKanallarni kuzatib boring:", tracking_menu_kb()),
            "tools": ("**Asboblar**\n\nTurli foydali vositalar:", tools_menu_kb()),
            "trending": ("**Trending**\n\nDavlatni tanlang:", trending_menu_kb()),
            "help": ("**Yordam**\n\nKategoriyani tanlang:", help_menu_kb()),
        }
        if menu in menus:
            text, kb = menus[menu]
            await cb.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Channel menu callbacks
    @bot.on_callback_query(filters.regex("^ch_"))
    async def cb_channel_menu(client, cb: CallbackQuery):
        action = cb.data.replace("ch_", "")
        hints = {
            "full": "To'liq statistika olish uchun:\n`/channel <kanal nomi yoki URL>`",
            "subs": "Obunachilar soni:\n`/subs <kanal>`",
            "recent": "So'nggi videolar:\n`/recent <kanal>`",
            "popular": "Eng ommabop videolar:\n`/popular <kanal>`",
            "playlists": "Pleylistlar:\n`/playlists <kanal>`",
            "about": "Kanal haqida:\n`/about <kanal>`",
            "banner": "Banner rasmi:\n`/banner <kanal>`",
            "keywords": "Kalit so'zlar:\n`/keywords <kanal>`",
            "frequency": "Upload chastotasi:\n`/uploadfreq <kanal>`",
            "earnings": "Daromad taxmini:\n`/earnings <kanal>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_channel")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Video menu callbacks
    @bot.on_callback_query(filters.regex("^vid_"))
    async def cb_video_menu(client, cb: CallbackQuery):
        action = cb.data.replace("vid_", "")
        hints = {
            "full": "To'liq statistika:\n`/video <URL>`",
            "likes": "Video likelari:\n`/video <URL>`",
            "comments": "Izohlar:\n`/comments <URL>`",
            "tags": "Teglar:\n`/tags <URL>`",
            "thumb": "Thumbnail:\n`/thumbnail <URL>`",
            "desc": "Tavsif:\n`/desc <URL>`",
            "engage": "Engagement:\n`/video <URL>`",
            "duration": "Davomiyligi:\n`/video <URL>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_video")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Analytics menu callbacks
    @bot.on_callback_query(filters.regex("^an_"))
    async def cb_analytics_menu(client, cb: CallbackQuery):
        action = cb.data.replace("an_", "")
        hints = {
            "growth": "O'sish tahlili:\n`/growth <kanal>`",
            "compare": "Solishtirish:\n`/compare <kanal1> <kanal2>`",
            "engage": "Engagement:\n`/engagement <kanal>`",
            "avgviews": "O'rtacha ko'rishlar:\n`/avgviews <kanal>`",
            "top": "Top videolar:\n`/topvideos <kanal>`",
            "bottom": "Eng kam ko'rilgan:\n`/topvideos <kanal>`",
            "earnings": "Daromad taxmini:\n`/earnings <kanal>`",
            "milestone": "Milestone:\n`/milestone <kanal>`",
            "report": "To'liq hisobot:\n`/report <kanal>`",
            "uploadrate": "Upload tezligi:\n`/uploadfreq <kanal>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_analytics")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Search callbacks
    @bot.on_callback_query(filters.regex("^sr_"))
    async def cb_search_menu(client, cb: CallbackQuery):
        action = cb.data.replace("sr_", "")
        hints = {
            "video": "Video qidirish:\n`/search <so'z>`",
            "channel": "Kanal qidirish:\n`/searchch <nom>`",
            "playlist": "Pleylist:\n`/playlist <URL yoki ID>`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_search")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Tracking callbacks
    @bot.on_callback_query(filters.regex("^tr_"))
    async def cb_tracking_menu(client, cb: CallbackQuery):
        action = cb.data.replace("tr_", "")
        hints = {
            "add": "Kanal qo'shish:\n`/track <kanal>`",
            "remove": "Kanal o'chirish:\n`/untrack <kanal>`",
            "list": "Ro'yxat:\n`/mylist`",
            "checkall": "Barchasini tekshirish:\n`/checkall`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_tracking")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Tools callbacks
    @bot.on_callback_query(filters.regex("^tl_"))
    async def cb_tools_menu(client, cb: CallbackQuery):
        action = cb.data.replace("tl_", "")
        hints = {
            "id": "URL dan ID:\n`/id <URL>`",
            "thumb": "Thumbnail olish:\n`/thumbnail <URL>`",
            "compare": "Solishtirish:\n`/compare <kanal1> <kanal2>`",
            "calc": "Kalkulyator - ko'rishlar bo'yicha daromad:\n`/earnings <kanal>`",
            "categories": "Kategoriyalar:\n`/categories [davlat_kodi]`",
            "region": "Davlat trending:\n`/trending [davlat_kodi]`",
        }
        text = hints.get(action, "Buyruqni yozing")
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="menu_tools")]]), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Trending region callbacks
    @bot.on_callback_query(filters.regex("^trend_"))
    async def cb_trending(client, cb: CallbackQuery):
        region = cb.data.replace("trend_", "")
        await cb.answer(f"Trending {region} yuklanmoqda...")
        videos = get_trending(region, max_results=10)
        if not videos:
            await cb.message.edit_text(f"Trending ({region}) topilmadi.", reply_markup=trending_menu_kb())
            return
        text = f"**Trending - {region}**\n\n{'='*28}\n\n"
        for i, v in enumerate(videos, 1):
            vs = v["statistics"]
            views = int(vs.get("viewCount", 0))
            text += f"**{i}.** {v['snippet']['title'][:40]}\n"
            text += f"   {v['snippet'].get('channelTitle','')} | `{fmt(views)}`\n\n"
        await cb.message.edit_text(text, reply_markup=trending_menu_kb(), parse_mode=ParseMode.MARKDOWN)
    
    # Help category callbacks
    @bot.on_callback_query(filters.regex("^help_"))
    async def cb_help(client, cb: CallbackQuery):
        cat = cb.data.replace("help_", "")
        helps = {
            "channel": (
                "**Kanal buyruqlari:**\n\n"
                "`/channel` - To'liq statistika\n"
                "`/subs` - Obunachilar\n"
                "`/totalviews` - Umumiy ko'rishlar\n"
                "`/videocount` - Videolar soni\n"
                "`/about` - Kanal haqida\n"
                "`/country` - Davlat\n"
                "`/created` - Yaratilgan sana\n"
                "`/keywords` - Kalit so'zlar\n"
                "`/banner` - Banner rasmi\n"
                "`/avatar` - Profil rasmi\n"
                "`/playlists` - Pleylistlar"
            ),
            "video": (
                "**Video buyruqlari:**\n\n"
                "`/video` - To'liq statistika\n"
                "`/comments` - Izohlar\n"
                "`/tags` - Teglar\n"
                "`/thumbnail` - Thumbnail\n"
                "`/desc` - Tavsif\n"
                "`/playlist` - Pleylist videolari"
            ),
            "analytics": (
                "**Analitika buyruqlari:**\n\n"
                "`/growth` - O'sish tahlili\n"
                "`/engagement` - Engagement rate\n"
                "`/earnings` - Daromad taxmini\n"
                "`/milestone` - Milestone\n"
                "`/report` - To'liq hisobot\n"
                "`/compare` - Solishtirish\n"
                "`/topvideos` - Top videolar\n"
                "`/avgviews` - O'rtacha ko'rishlar\n"
                "`/uploadfreq` - Upload chastotasi"
            ),
            "search": (
                "**Qidiruv buyruqlari:**\n\n"
                "`/search` - Video qidirish\n"
                "`/searchch` - Kanal qidirish\n"
                "`/trending` - Trending videolar\n"
                "`/categories` - Kategoriyalar"
            ),
            "tracking": (
                "**Kuzatuv buyruqlari:**\n\n"
                "`/track` - Kanalni kuzatishga olish\n"
                "`/untrack` - Kuzatishdan olish\n"
                "`/mylist` - Kuzatuvdagi kanallar\n"
                "`/checkall` - Barchasini tekshirish"
            ),
            "tools": (
                "**Asboblar:**\n\n"
                "`/id` - URL dan ID ajratish\n"
                "`/thumbnail` - Thumbnail olish\n"
                "`/compare` - Kanallarni solishtirish\n"
                "`/categories` - Kategoriyalar\n"
                "`/ping` - Bot tezligini tekshirish"
            ),
        }
        text = helps.get(cat, "Yordam topilmadi")
        await cb.message.edit_text(text, reply_markup=help_menu_kb(), parse_mode=ParseMode.MARKDOWN)
        await cb.answer()
    
    # Channel action callbacks (kanal sahifasidagi tugmalar)
    @bot.on_callback_query(filters.regex("^cact_"))
    async def cb_channel_action(client, cb: CallbackQuery):
        parts = cb.data.split("_", 2)
        if len(parts) < 3:
            await cb.answer("Xato")
            return
        action = parts[1]
        channel_id = parts[2]
        
        await cb.answer(f"Yuklanmoqda...")
        
        if action == "recent":
            videos = get_videos_by_channel(channel_id, max_results=10, order="date")
            if not videos:
                await cb.message.edit_text("Videolar topilmadi.", reply_markup=back_main_kb())
                return
            ch = get_channel({"type": "id", "value": channel_id})
            title = ch["snippet"]["title"] if ch else channel_id
            text = f"**{title}** - So'nggi videolar\n\n{'='*28}\n\n"
            for i, v in enumerate(videos, 1):
                vs = v["statistics"]
                views = int(vs.get("viewCount", 0))
                ago = time_ago(v["snippet"].get("publishedAt", ""))
                text += f"**{i}.** {v['snippet']['title'][:45]}\n"
                text += f"   `{fmt(views)}` ko'rish | {ago}\n\n"
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "popular":
            videos = get_videos_by_channel(channel_id, max_results=10, order="viewCount")
            if not videos:
                await cb.message.edit_text("Videolar topilmadi.", reply_markup=back_main_kb())
                return
            ch = get_channel({"type": "id", "value": channel_id})
            title = ch["snippet"]["title"] if ch else channel_id
            text = f"**{title}** - Ommabop\n\n{'='*28}\n\n"
            for i, v in enumerate(videos, 1):
                vs = v["statistics"]
                views = int(vs.get("viewCount", 0))
                text += f"**{i}.** {v['snippet']['title'][:45]}\n   `{fmt(views)}`\n\n"
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "playlists":
            pls = get_playlists(channel_id, max_results=10)
            if not pls:
                await cb.message.edit_text("Pleylistlar topilmadi.", reply_markup=back_main_kb())
                return
            text = "**Pleylistlar**\n\n"
            for i, p in enumerate(pls, 1):
                count = p.get("contentDetails", {}).get("itemCount", 0)
                text += f"**{i}.** {p['snippet']['title'][:40]} (`{count}` video)\n\n"
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "growth":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            st = ch["statistics"]
            subs = int(st.get("subscriberCount",0))
            views = int(st.get("viewCount",0))
            vids = int(st.get("videoCount",0))
            save_channel_snapshot(channel_id, subs, views, vids)
            g = get_channel_growth(channel_id)
            text = f"**{ch['snippet']['title']}** - O'sish\n\n"
            text += f"Obunachilar: `{fmt(subs)}`\nKo'rishlar: `{fmt(views)}`\n\n"
            if g:
                text += f"Sub o'sish: {growth_icon(g['sub_growth'])}\n"
                text += f"View o'sish: {growth_icon(g['view_growth'])}\n"
            else:
                text += "O'sish ma'lumotlari hali yetarli emas."
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "report":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            sn, st = ch["snippet"], ch["statistics"]
            subs = int(st.get("subscriberCount",0))
            views = int(st.get("viewCount",0))
            vids = int(st.get("videoCount",0))
            avg = views//vids if vids else 0
            low, high = estimate_earnings(views)
            text = (
                f"**{sn['title']}** - HISOBOT\n\n{'='*28}\n\n"
                f"Obunachilar: `{fmt_full(subs)}`\n"
                f"Ko'rishlar: `{fmt_full(views)}`\n"
                f"Videolar: `{fmt_full(vids)}`\n"
                f"O'rtacha/video: `{fmt(avg)}`\n"
                f"Daromad: `${low:,.0f}` - `${high:,.0f}`"
            )
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "earn":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            views = int(ch["statistics"].get("viewCount", 0))
            low, high = estimate_earnings(views)
            text = (
                f"**{ch['snippet']['title']}** - Daromad\n\n"
                f"Umumiy: `${low:,.0f}` - `${high:,.0f}`\n"
                f"CPM: $0.50 - $5.00"
            )
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "track":
            add_tracked_channel(cb.from_user.id, channel_id, "")
            ch = get_channel({"type": "id", "value": channel_id})
            if ch:
                st = ch["statistics"]
                save_channel_snapshot(channel_id, int(st.get("subscriberCount",0)), int(st.get("viewCount",0)), int(st.get("videoCount",0)))
                add_tracked_channel(cb.from_user.id, channel_id, ch["snippet"]["title"])
            await cb.message.edit_text("Kanal kuzatishga qo'shildi!", reply_markup=channel_action_kb(channel_id))
        
        elif action == "refresh":
            ch = get_channel({"type": "id", "value": channel_id})
            if not ch:
                await cb.message.edit_text("Kanal topilmadi.", reply_markup=back_main_kb())
                return
            sn, st = ch["snippet"], ch["statistics"]
            subs = int(st.get("subscriberCount",0))
            views = int(st.get("viewCount",0))
            vids = int(st.get("videoCount",0))
            avg = views//vids if vids else 0
            save_channel_snapshot(channel_id, subs, views, vids)
            text = (
                f"**{sn['title']}** (yangilandi)\n\n{'='*28}\n\n"
                f"Obunachilar: `{fmt(subs)}` ({fmt_full(subs)})\n"
                f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
                f"Videolar: `{fmt(vids)}`\n"
                f"O'rtacha: `{fmt(avg)}`"
            )
            await cb.message.edit_text(text, reply_markup=channel_action_kb(channel_id), parse_mode=ParseMode.MARKDOWN)
    
    # Video action callbacks
    @bot.on_callback_query(filters.regex("^vact_"))
    async def cb_video_action(client, cb: CallbackQuery):
        parts = cb.data.split("_", 2)
        if len(parts) < 3:
            await cb.answer("Xato")
            return
        action = parts[1]
        video_id = parts[2]
        
        await cb.answer("Yuklanmoqda...")
        
        if action == "comments":
            comments = get_comments(video_id, max_results=10)
            if not comments:
                await cb.message.edit_text("Izohlar topilmadi.", reply_markup=video_action_kb(video_id))
                return
            text = "**Top izohlar**\n\n"
            for i, c in enumerate(comments, 1):
                sn = c["snippet"]["topLevelComment"]["snippet"]
                author = sn.get("authorDisplayName","")[:20]
                txt = sn.get("textDisplay","")[:80]
                likes = int(sn.get("likeCount",0))
                text += f"**{i}. {author}** ({fmt(likes)} like)\n{txt}\n\n"
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "tags":
            v = get_video(video_id)
            if not v:
                await cb.message.edit_text("Video topilmadi.", reply_markup=back_main_kb())
                return
            tags = v["snippet"].get("tags", [])
            text = f"**Teglar** ({len(tags)} ta)\n\n"
            text += " | ".join([f"`{t}`" for t in tags[:30]]) if tags else "Teglar topilmadi"
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "thumb":
            url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            await cb.message.reply_photo(url, caption=f"Thumbnail: `{video_id}`", parse_mode=ParseMode.MARKDOWN)
            await cb.answer()
        
        elif action == "engage":
            v = get_video(video_id)
            if not v:
                await cb.message.edit_text("Video topilmadi.", reply_markup=back_main_kb())
                return
            st = v["statistics"]
            views = int(st.get("viewCount",0))
            likes = int(st.get("likeCount",0))
            comments_count = int(st.get("commentCount",0))
            eng = engagement_rate(views, likes, comments_count)
            lr = (likes/views*100) if views else 0
            text = (
                f"**{v['snippet']['title'][:40]}** - Engagement\n\n"
                f"Engagement: `{eng:.2f}%`\n"
                f"Like rate: `{lr:.2f}%`\n"
                f"Ko'rishlar: `{fmt(views)}`\n"
                f"Likelar: `{fmt(likes)}`\n"
                f"Izohlar: `{fmt(comments_count)}`"
            )
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
        
        elif action == "refresh":
            v = get_video(video_id)
            if not v:
                await cb.message.edit_text("Video topilmadi.", reply_markup=back_main_kb())
                return
            sn, st = v["snippet"], v["statistics"]
            views = int(st.get("viewCount",0))
            likes = int(st.get("likeCount",0))
            comments_count = int(st.get("commentCount",0))
            eng = engagement_rate(views, likes, comments_count)
            text = (
                f"**{sn['title']}** (yangilandi)\n\n{'='*28}\n\n"
                f"Ko'rishlar: `{fmt(views)}` ({fmt_full(views)})\n"
                f"Likelar: `{fmt(likes)}`\n"
                f"Izohlar: `{fmt(comments_count)}`\n"
                f"Engagement: `{eng:.2f}%`"
            )
            await cb.message.edit_text(text, reply_markup=video_action_kb(video_id), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== AI ROUTER (Aqlli Yo'naltirish) ====================
    @bot.on_message(filters.text & ~filters.regex(r"^/") & filters.private)
    async def ai_routing_handler(client, message):
        user_text = message.text.strip()
        if not user_text:
            return
            
        try:
            api_key = get_gemini_key()
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""Foydalanuvchi Telegram botga quyidagi matnni yozdi:
"{user_text}"

Botda quyidagi buyruqlar bor:
1. /compare <kanal1> <kanal2> - ikki kanalni taqqoslash
2. /autopost <soni> <mavzu> - videolarni avto post qilish
3. /channel <kanal> - kanal statistikasini ko'rish
4. /video <url> - video statistikasini ko'rish
5. /trending - trenddagi videolarni ko'rish
6. /search <so'z> - videolar qidirish

Vazifang: Foydalanuvchi niyatini aniqla. 
Agar foydalanuvchi kanal taqqoslashni so'rasa yoki boshqa buyruqqa mos keladigan narsa so'rasa, mos Telegram buyrug'ini aniq qaytar.
Javobingni FAQAT JSON formatida ber:
{{
    "action": "command" yoki "text",
    "result": "buyruq matni (masalan /compare ch1 ch2) YOKI foydalanuvchiga do'stona javob"
}}"""
            res = model.generate_content(prompt)
            if res and res.text:
                json_match = re.search(r'\{[\s\S]*\}', res.text)
                if json_match:
                    data = json.loads(json_match.group())
                    act = data.get("action")
                    val = data.get("result", "")
                    if act == "command" and val.startswith("/"):
                        await message.reply_text(f"`🎯 AI yo'naltirishi: {val}`\n\nBuyruq ijro etilmoqda...", parse_mode=ParseMode.MARKDOWN)
                        message.text = val
                        cmd_name = val.split()[0][1:]
                        if cmd_name == "compare":
                            await compare_cmd(client, message)
                        elif cmd_name == "channel":
                            await channel_cmd(client, message)
                        elif cmd_name == "video":
                            await video_cmd(client, message)
                        elif cmd_name == "search":
                            await search_cmd(client, message)
                        elif cmd_name == "trending":
                            await trending_cmd(client, message)
                        elif cmd_name == "autopost":
                            await autopost_cmd(client, message)
                        return
                    else:
                        await message.reply_text(f"`{val}`", parse_mode=ParseMode.MARKDOWN)
                        return
        except Exception as e:
            print(f"AI routing xato: {e}")
        
        await message.reply_text("`Yordam uchun /help ni bosing.`", parse_mode=ParseMode.MARKDOWN)
    
    return bot


async def run_ytbot():
    bot = create_ytbot()
    if bot is None:
        print("YouTube Bot ishga tushmadi. BOT_TOKEN ni tekshiring.")
        return
    print("YouTube Analytics Bot ishga tushmoqda...")
    await bot.start()
    print("YouTube Analytics Bot muvaffaqiyatli ishga tushdi!")
    await asyncio.Event().wait()
