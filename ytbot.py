import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from googleapiclient.discovery import build

from config import BOT_TOKEN, API_ID, API_HASH, YOUTUBE_API_KEY
from database import (
    add_tracked_channel, remove_tracked_channel, get_tracked_channels,
    save_channel_snapshot, save_video_snapshot,
    get_channel_history, get_channel_growth
)


def get_youtube_service():
    """YouTube Data API v3 xizmatini yaratish"""
    if not YOUTUBE_API_KEY:
        return None
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def extract_channel_identifier(text: str):
    """URL yoki username dan kanal identifikatorini ajratib olish"""
    # @username formati
    if text.startswith("@"):
        return {"type": "username", "value": text[1:]}
    
    # youtube.com/channel/UC...
    match = re.search(r'youtube\.com/channel/(UC[\w-]+)', text)
    if match:
        return {"type": "id", "value": match.group(1)}
    
    # youtube.com/@username
    match = re.search(r'youtube\.com/@([\w.-]+)', text)
    if match:
        return {"type": "username", "value": match.group(1)}
    
    # youtube.com/c/username yoki youtube.com/user/username
    match = re.search(r'youtube\.com/(?:c|user)/([\w.-]+)', text)
    if match:
        return {"type": "username", "value": match.group(1)}
    
    # Oddiy matn (username deb hisoblaymiz)
    return {"type": "username", "value": text.strip()}


def extract_video_id(text: str):
    """Video URL dan video ID ni ajratib olish"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{11})',
        r'youtube\.com/shorts/([\w-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return text.strip() if len(text.strip()) == 11 else None


def format_number(num):
    """Raqamni chiroyli formatda ko'rsatish"""
    if num is None:
        return "N/A"
    num = int(num)
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def growth_emoji(value):
    """O'sish yoki pasayish emojiisi"""
    if value > 0:
        return f"📈 +{format_number(value)}"
    elif value < 0:
        return f"📉 {format_number(value)}"
    return "➡️ 0"


def get_channel_info(identifier):
    """YouTube API orqali kanal ma'lumotlarini olish"""
    yt = get_youtube_service()
    if not yt:
        return None
    
    try:
        if identifier["type"] == "id":
            request = yt.channels().list(
                part="snippet,statistics,contentDetails,brandingSettings",
                id=identifier["value"]
            )
        else:
            request = yt.channels().list(
                part="snippet,statistics,contentDetails,brandingSettings",
                forUsername=identifier["value"]
            )
        
        response = request.execute()
        
        # forUsername ishlamasa, search orqali izlaymiz
        if not response.get("items"):
            search_req = yt.search().list(
                part="snippet",
                q=identifier["value"],
                type="channel",
                maxResults=1
            )
            search_resp = search_req.execute()
            
            if search_resp.get("items"):
                channel_id = search_resp["items"][0]["snippet"]["channelId"]
                request = yt.channels().list(
                    part="snippet,statistics,contentDetails,brandingSettings",
                    id=channel_id
                )
                response = request.execute()
        
        if response.get("items"):
            return response["items"][0]
        return None
        
    except Exception as e:
        print(f"YouTube API xatosi: {e}")
        return None


def get_video_info(video_id: str):
    """YouTube API orqali video ma'lumotlarini olish"""
    yt = get_youtube_service()
    if not yt:
        return None
    
    try:
        request = yt.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        
        if response.get("items"):
            return response["items"][0]
        return None
        
    except Exception as e:
        print(f"YouTube API xatosi: {e}")
        return None


def get_recent_videos(channel_id: str, max_results: int = 5):
    """Kanalning so'nggi videolarini olish"""
    yt = get_youtube_service()
    if not yt:
        return []
    
    try:
        # So'nggi videolarni qidirish
        search_req = yt.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            type="video",
            maxResults=max_results
        )
        search_resp = search_req.execute()
        
        if not search_resp.get("items"):
            return []
        
        # Video ID larni yig'ish
        video_ids = [item["id"]["videoId"] for item in search_resp["items"]]
        
        # To'liq statistikalarni olish
        videos_req = yt.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        )
        videos_resp = videos_req.execute()
        
        return videos_resp.get("items", [])
        
    except Exception as e:
        print(f"YouTube API xatosi: {e}")
        return []


def create_ytbot():
    """YouTube Analytics Telegram Bot yaratish"""
    if not BOT_TOKEN:
        print("⚠️  BOT_TOKEN topilmadi!")
        return None
    
    bot = Client(
        "yt_analytics_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )
    
    # ==================== /start ====================
    @bot.on_message(filters.command("start"))
    async def start_cmd(client, message):
        welcome = """
🎬 **YouTube Analytics Bot** ga xush kelibsiz!

Bu bot orqali istalgan YouTube kanalning to'liq statistikasini ko'rishingiz mumkin.

📋 **Buyruqlar:**

🔍 `/channel <nom yoki URL>` — Kanal statistikasi
🎥 `/video <URL>` — Video statistikasi  
📊 `/recent <nom yoki URL>` — So'nggi videolar tahlili
➕ `/track <nom yoki URL>` — Kanalni kuzatishga olish
📈 `/growth <nom yoki URL>` — O'sish dinamikasi
📋 `/mylist` — Kuzatayotgan kanallarim
❌ `/untrack <nom yoki URL>` — Kuzatishdan olib tashlash

💡 **Misol:** `/channel @mkbhd` yoki `/channel https://youtube.com/@mkbhd`
"""
        await message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /channel ====================
    @bot.on_message(filters.command("channel"))
    async def channel_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("ℹ️ Foydalanish: `/channel <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not YOUTUBE_API_KEY:
            await message.reply_text("❌ YouTube API kaliti sozlanmagan! Admin ga murojaat qiling.")
            return
        
        wait_msg = await message.reply_text("🔍 Qidirilmoqda...")
        
        identifier = extract_channel_identifier(args[1])
        channel = get_channel_info(identifier)
        
        if not channel:
            await wait_msg.edit_text("❌ Kanal topilmadi. Nom yoki URL ni tekshiring.")
            return
        
        snippet = channel["snippet"]
        stats = channel["statistics"]
        
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        videos = int(stats.get("videoCount", 0))
        
        # Snapshotni bazaga saqlash
        save_channel_snapshot(channel["id"], subs, views, videos)
        
        # O'rtacha ko'rishlar hisoblash
        avg_views = views // videos if videos > 0 else 0
        
        created = snippet.get("publishedAt", "N/A")[:10]
        
        text = f"""
📺 **{snippet['title']}**

{'━' * 28}

👥 **Obunachilar:** `{format_number(subs)}` ({subs:,})
👁 **Umumiy ko'rishlar:** `{format_number(views)}` ({views:,})
🎬 **Videolar soni:** `{format_number(videos)}` ({videos:,})
📊 **O'rtacha ko'rish/video:** `{format_number(avg_views)}`
📅 **Yaratilgan:** `{created}`

{'━' * 28}

🆔 **Channel ID:** `{channel['id']}`
📝 **Tavsif:** {snippet.get('description', 'Tavsif yo'q')[:200]}...
"""
        await wait_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /video ====================
    @bot.on_message(filters.command("video"))
    async def video_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("ℹ️ Foydalanish: `/video <video URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not YOUTUBE_API_KEY:
            await message.reply_text("❌ YouTube API kaliti sozlanmagan!")
            return
        
        wait_msg = await message.reply_text("🔍 Qidirilmoqda...")
        
        video_id = extract_video_id(args[1])
        if not video_id:
            await wait_msg.edit_text("❌ Video topilmadi. URL ni tekshiring.")
            return
        
        video = get_video_info(video_id)
        if not video:
            await wait_msg.edit_text("❌ Video ma'lumotlari topilmadi.")
            return
        
        snippet = video["snippet"]
        stats = video["statistics"]
        
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        
        # Bazaga saqlash
        save_video_snapshot(
            video_id, snippet.get("channelId", ""), snippet["title"],
            views, likes, comments
        )
        
        # Like/view nisbati
        like_ratio = (likes / views * 100) if views > 0 else 0
        
        published = snippet.get("publishedAt", "N/A")[:10]
        duration = video.get("contentDetails", {}).get("duration", "N/A")
        
        text = f"""
🎥 **{snippet['title']}**

{'━' * 28}

👁 **Ko'rishlar:** `{format_number(views)}` ({views:,})
👍 **Likelar:** `{format_number(likes)}` ({likes:,})
💬 **Izohlar:** `{format_number(comments)}` ({comments:,})
📊 **Like/View nisbati:** `{like_ratio:.2f}%`
⏱ **Davomiyligi:** `{duration}`
📅 **Chop etilgan:** `{published}`

{'━' * 28}

📺 **Kanal:** {snippet.get('channelTitle', 'N/A')}
🆔 **Video ID:** `{video_id}`
"""
        await wait_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /recent ====================
    @bot.on_message(filters.command("recent"))
    async def recent_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("ℹ️ Foydalanish: `/recent <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not YOUTUBE_API_KEY:
            await message.reply_text("❌ YouTube API kaliti sozlanmagan!")
            return
        
        wait_msg = await message.reply_text("🔍 So'nggi videolar qidirilmoqda...")
        
        identifier = extract_channel_identifier(args[1])
        channel = get_channel_info(identifier)
        
        if not channel:
            await wait_msg.edit_text("❌ Kanal topilmadi.")
            return
        
        videos = get_recent_videos(channel["id"], max_results=5)
        
        if not videos:
            await wait_msg.edit_text("❌ Videolar topilmadi.")
            return
        
        text = f"📺 **{channel['snippet']['title']}** — So'nggi videolar\n\n{'━' * 28}\n\n"
        
        for i, v in enumerate(videos, 1):
            s = v["statistics"]
            views = int(s.get("viewCount", 0))
            likes = int(s.get("likeCount", 0))
            comments = int(s.get("commentCount", 0))
            published = v["snippet"].get("publishedAt", "")[:10]
            
            text += f"""**{i}. {v['snippet']['title'][:50]}**
   👁 `{format_number(views)}` | 👍 `{format_number(likes)}` | 💬 `{format_number(comments)}`
   📅 `{published}`

"""
        
        await wait_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /track ====================
    @bot.on_message(filters.command("track"))
    async def track_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("ℹ️ Foydalanish: `/track <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not YOUTUBE_API_KEY:
            await message.reply_text("❌ YouTube API kaliti sozlanmagan!")
            return
        
        wait_msg = await message.reply_text("🔍 Kanal qidirilmoqda...")
        
        identifier = extract_channel_identifier(args[1])
        channel = get_channel_info(identifier)
        
        if not channel:
            await wait_msg.edit_text("❌ Kanal topilmadi.")
            return
        
        stats = channel["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        videos_count = int(stats.get("videoCount", 0))
        
        # Bazaga qo'shish
        added = add_tracked_channel(
            message.from_user.id,
            channel["id"],
            channel["snippet"]["title"]
        )
        
        # Birinchi snapshotni saqlash
        save_channel_snapshot(channel["id"], subs, views, videos_count)
        
        if added:
            await wait_msg.edit_text(
                f"✅ **{channel['snippet']['title']}** kuzatishga qo'shildi!\n\n"
                f"👥 Obunachilar: `{format_number(subs)}`\n"
                f"👁 Ko'rishlar: `{format_number(views)}`\n\n"
                f"📊 O'sishni ko'rish uchun: `/growth {channel['snippet']['title']}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await wait_msg.edit_text(f"ℹ️ **{channel['snippet']['title']}** allaqachon kuzatilmoqda.")
    
    # ==================== /growth ====================
    @bot.on_message(filters.command("growth"))
    async def growth_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("ℹ️ Foydalanish: `/growth <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not YOUTUBE_API_KEY:
            await message.reply_text("❌ YouTube API kaliti sozlanmagan!")
            return
        
        wait_msg = await message.reply_text("📊 Tahlil qilinmoqda...")
        
        identifier = extract_channel_identifier(args[1])
        channel = get_channel_info(identifier)
        
        if not channel:
            await wait_msg.edit_text("❌ Kanal topilmadi.")
            return
        
        # Yangi snapshot saqlash
        stats = channel["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        videos_count = int(stats.get("videoCount", 0))
        save_channel_snapshot(channel["id"], subs, views, videos_count)
        
        # O'sishni hisoblash
        growth = get_channel_growth(channel["id"])
        
        text = f"📊 **{channel['snippet']['title']}** — O'sish Tahlili\n\n{'━' * 28}\n\n"
        text += f"👥 **Obunachilar:** `{format_number(subs)}` ({subs:,})\n"
        text += f"👁 **Ko'rishlar:** `{format_number(views)}` ({views:,})\n"
        text += f"🎬 **Videolar:** `{format_number(videos_count)}`\n\n"
        
        if growth:
            text += f"{'━' * 28}\n\n"
            text += f"📈 **O'sish (oxirgi tekshiruvdan beri):**\n\n"
            text += f"👥 Obunachilar: {growth_emoji(growth['sub_growth'])}\n"
            text += f"👁 Ko'rishlar: {growth_emoji(growth['view_growth'])}\n"
            text += f"🎬 Videolar: {growth_emoji(growth['video_growth'])}\n"
            text += f"\n📅 Oldingi tekshiruv: `{growth['previous']['snapshot_at'][:19]}`\n"
        else:
            text += "\nℹ️ O'sish ma'lumotlari hali yetarli emas. Keyinroq qayta tekshiring."
        
        await wait_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /mylist ====================
    @bot.on_message(filters.command("mylist"))
    async def mylist_cmd(client, message):
        channels = get_tracked_channels(message.from_user.id)
        
        if not channels:
            await message.reply_text("📋 Siz hali hech qanday kanalni kuzatmayapsiz.\n\n➕ Qo'shish: `/track <kanal>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        text = "📋 **Kuzatayotgan kanallarim:**\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. **{ch['channel_title']}**\n   🆔 `{ch['channel_id']}`\n\n"
        
        text += f"\n📊 O'sishni ko'rish: `/growth <kanal nomi>`"
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== /untrack ====================
    @bot.on_message(filters.command("untrack"))
    async def untrack_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("ℹ️ Foydalanish: `/untrack <kanal nomi yoki URL>`", parse_mode=ParseMode.MARKDOWN)
            return
        
        identifier = extract_channel_identifier(args[1])
        
        if YOUTUBE_API_KEY:
            channel = get_channel_info(identifier)
            if channel:
                remove_tracked_channel(message.from_user.id, channel["id"])
                await message.reply_text(f"✅ **{channel['snippet']['title']}** kuzatishdan olib tashlandi.")
                return
        
        await message.reply_text("❌ Kanal topilmadi yoki kuzatilmayapti.")
    
    # ==================== /help ====================
    @bot.on_message(filters.command("help"))
    async def help_cmd(client, message):
        await start_cmd(client, message)
    
    return bot


async def run_ytbot():
    """YouTube Analytics Botni ishga tushirish"""
    bot = create_ytbot()
    if bot is None:
        print("❌ YouTube Bot ishga tushmadi. BOT_TOKEN ni tekshiring.")
        return
    
    print("🚀 YouTube Analytics Bot ishga tushmoqda...")
    await bot.start()
    print("✅ YouTube Analytics Bot muvaffaqiyatli ishga tushdi!")
    
    # Abadiy ishlash
    await asyncio.Event().wait()
