"""
Mass Action Module — YouTube kanalga barcha ulangan akkauntlar orqali
Like, Comment, Subscribe qilish (kanal URL orqali).
"""
import asyncio
import random
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import get_youtube_key, build_youtube_api, YT_CLIENT_ID, YT_CLIENT_SECRET
from database import get_every_yt_connection


# ==================== YORDAMCHI FUNKSIYALAR ====================

def resolve_channel_from_url(url):
    """
    YouTube kanal URL dan channel_id ni aniqlash.
    Qo'llab-quvvatlanadigan formatlar:
      - https://www.youtube.com/@username
      - https://www.youtube.com/channel/UCxxxxxx
      - https://www.youtube.com/c/ChannelName
      - @username (faqat handle)
    """
    url = url.strip()
    
    # Agar faqat @username bo'lsa
    if url.startswith("@"):
        handle = url
    elif "/@" in url:
        handle = "@" + url.split("/@")[1].split("/")[0].split("?")[0]
    elif "/channel/" in url:
        # To'g'ridan-to'g'ri channel ID
        channel_id = url.split("/channel/")[1].split("/")[0].split("?")[0]
        return channel_id, None
    elif "/c/" in url:
        handle = "@" + url.split("/c/")[1].split("/")[0].split("?")[0]
    else:
        return None, "URL formatini tushunib bo'lmadi"
    
    # Handle orqali channel_id ni topish
    try:
        yt = build_youtube_api()
        # forHandle parametri bilan qidirish
        res = yt.channels().list(part="snippet", forHandle=handle.lstrip("@")).execute()
        items = res.get("items", [])
        if items:
            return items[0]["id"], items[0]["snippet"]["title"]
        
        # Agar forHandle ishlamasa, search orqali sinash
        search_res = yt.search().list(q=handle, type="channel", part="snippet", maxResults=1).execute()
        items = search_res.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"], items[0]["snippet"]["title"]
        
        return None, f"'{handle}' nomli kanal topilmadi"
    except Exception as e:
        return None, f"Kanal qidirishda xato: {str(e)[:200]}"


def get_channel_videos(channel_id):
    """Kanal ID orqali barcha videolarning ID va sarlavhalarini olish (limitsiz)"""
    try:
        yt = build_youtube_api()
        
        # Avval uploads playlist ID ni olish
        ch_res = yt.channels().list(part="contentDetails", id=channel_id).execute()
        items = ch_res.get("items", [])
        if not items:
            return [], "Kanal topilmadi"
        
        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Playlistdagi videolarni olish
        videos = []
        next_page = None
        while True:
            pl_res = yt.playlistItems().list(
                part="snippet",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=next_page
            ).execute()
            
            for item in pl_res.get("items", []):
                vid_id = item["snippet"]["resourceId"]["videoId"]
                title = item["snippet"]["title"]
                videos.append({"id": vid_id, "title": title})
            
            next_page = pl_res.get("nextPageToken")
            if not next_page:
                break
        
        return videos, None
    except Exception as e:
        return [], f"Videolarni olishda xato: {str(e)[:200]}"


def _build_user_youtube(conn_data):
    """Ulangan akkaunt uchun autentifikatsiyalangan YouTube client yaratish"""
    creds = Credentials(
        token=conn_data['access_token'],
        refresh_token=conn_data.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET
    )
    return build("youtube", "v3", credentials=creds)


# ==================== ASOSIY MASS ACTION WORKER ====================

async def mass_action_worker(channel_url, comment_text, action_type, client, chat_id):
    """
    Background task: Kanal URL bo'yicha barcha ulangan akkauntlardan mass action bajarish.
    
    action_type: "all" | "like" | "comment" | "subscribe"
    """
    async def safe_send(text):
        if client:
            try: return await client.send_message(chat_id, text)
            except: pass
        return None

    async def safe_edit(msg_obj, text):
        if msg_obj:
            try: await msg_obj.edit_text(text)
            except: pass

    # 1. Kanal URL ni hal qilish
    status_msg = await safe_send("🔍 `Kanal aniqlanmoqda...`")
    
    channel_id, channel_name = await asyncio.to_thread(resolve_channel_from_url, channel_url)
    if not channel_id:
        await safe_edit(status_msg, f"❌ `Xatolik: {channel_name}`")
        return
    
    if not channel_name:
        channel_name = channel_id
    
    await safe_edit(status_msg, f"✅ `Kanal topildi: {channel_name}`\n🔄 `Videolar yuklanmoqda...`")
    
    # 2. Videolarni olish
    videos, err = await asyncio.to_thread(get_channel_videos, channel_id)
    if err:
        await safe_edit(status_msg, f"❌ `{err}`")
        return
    
    if not videos:
        await safe_edit(status_msg, f"❌ `Kanalda videolar topilmadi`")
        return
    
    # 3. Barcha ulangan akkauntlarni olish
    all_connections = await asyncio.to_thread(get_every_yt_connection)
    if not all_connections:
        await safe_edit(status_msg, f"❌ `Hech qanday YouTube akkaunt ulanmagan! /ytlogin orqali ulaning.`")
        return
    
    # O'zining kanalini chiqarib tashlash (o'ziga o'zi like/sub qilib bo'lmaydi)
    connections = [c for c in all_connections if c.get('yt_channel_id') != channel_id]
    if not connections:
        connections = all_connections  # Agar faqat 1 ta akkaunt bo'lsa, baribir sinab ko'rish
    
    total_accounts = len(connections)
    total_videos = len(videos)
    
    do_like = action_type in ("all", "like")
    # Agar faqat like yoki sub bo'lmasa, doim comment yozadi (AI orqali)
    do_comment = action_type in ("all", "comment")
    do_subscribe = action_type in ("all", "subscribe")
    
    actions = []
    if do_subscribe: actions.append("Subscribe")
    if do_like: actions.append("Like")
    if do_comment: actions.append("Comment")
    
    await safe_edit(status_msg, 
        f"🚀 **Mass Action Boshlandi!**\n\n"
        f"📺 Kanal: `{channel_name}`\n"
        f"🎬 Videolar: `{total_videos}` ta\n"
        f"👥 Akkauntlar: `{total_accounts}` ta\n"
        f"⚡ Amallar: `{', '.join(actions)}`\n\n"
        f"⏳ `Jarayon boshlanmoqda... Bu biroz vaqt olishi mumkin.`"
    )
    
    # 4. Har bir akkaunt uchun amallarni bajarish
    total_likes = 0
    total_comments = 0
    total_subs = 0
    errors = 0
    
    for acc_idx, conn_data in enumerate(connections, 1):
        acc_name = conn_data.get('yt_channel_title', f'Akkaunt #{acc_idx}')
        
        try:
            yt = await asyncio.to_thread(_build_user_youtube, conn_data)
        except Exception as e:
            print(f"[mass] Akkaunt yaratishda xato ({acc_name}): {e}")
            errors += 1
            continue
        
        progress_msg = await safe_send(
            f"👤 `[{acc_idx}/{total_accounts}] {acc_name} bilan ishlamoqda...`"
        )
        
        # Subscribe
        if do_subscribe:
            try:
                def _check_and_subscribe():
                    # Obuna qilinganmi yo'qmi tekshirish
                    subs_res = yt.subscriptions().list(part="snippet", forChannelId=channel_id, mine=True).execute()
                    if subs_res.get("items"):
                        return False # Allaqachon obuna
                    
                    # Obuna bo'lmasa, qo'shamiz
                    yt.subscriptions().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "resourceId": {
                                    "kind": "youtube#channel",
                                    "channelId": channel_id
                                }
                            }
                        }
                    ).execute()
                    return True
                
                newly_subbed = await asyncio.to_thread(_check_and_subscribe)
                total_subs += 1
                if newly_subbed:
                    print(f"[mass] ✅ {acc_name} -> Subscribed to {channel_name}")
                else:
                    print(f"[mass] ℹ️ {acc_name} -> Already subscribed to {channel_name}")
            except Exception as e:
                err_str = str(e)
                print(f"[mass] ❌ Subscribe error ({acc_name}): {err_str[:100]}")
                errors += 1
            
            # Kichik pauza
            await asyncio.sleep(1)
        
        # Like + Comment har bir video uchun
        for vid_idx, video in enumerate(videos, 1):
            vid_id = video["id"]
            vid_title = video["title"][:40]
            
            # Like
            if do_like:
                try:
                    def _like(video_id=vid_id):
                        yt.videos().rate(id=video_id, rating="like").execute()
                    
                    await asyncio.to_thread(_like)
                    total_likes += 1
                    print(f"[mass] 👍 {acc_name} -> Liked: {vid_title}")
                except Exception as e:
                    print(f"[mass] ❌ Like error ({acc_name}, {vid_id}): {str(e)[:80]}")
                    errors += 1
                
                await asyncio.sleep(0.5)
            
            # Comment (AI orqali har xil gap)
            if do_comment:
                try:
                    from config import generate_with_fallback
                    
                    # AI ga prompt berish (user text bergan bo'lsa uni mavzu sifatida olish)
                    topic_hint = f" mavzu: {comment_text}" if comment_text else ""
                    prompt = f"Mana bu YouTube videoga: '{vid_title}'{topic_hint}. Faqat bitta qisqa, tabiiy, odamdek pozitiv (yoki mavzuga mos) izoh yoz. Hech qanday boshqa matn, qavslar qo'shma, to'g'ridan to'g'ri izohni qaytar."
                    
                    ai_res = await asyncio.to_thread(generate_with_fallback, prompt)
                    ai_text = ai_res.text.strip() if (ai_res and ai_res.text) else "Zo'r video!"
                    
                    def _comment(video_id=vid_id, text=ai_text):
                        yt.commentThreads().insert(
                            part="snippet",
                            body={
                                "snippet": {
                                    "videoId": video_id,
                                    "topLevelComment": {
                                        "snippet": {
                                            "textOriginal": text
                                        }
                                    }
                                }
                            }
                        ).execute()
                    
                    await asyncio.to_thread(_comment)
                    total_comments += 1
                    print(f"[mass] 💬 {acc_name} -> Commented on: {vid_title} (AI: {ai_text[:30]}...)")
                except Exception as e:
                    err_str = str(e)
                    if "commentsDisabled" in err_str:
                        print(f"[mass] ℹ️ Comments disabled: {vid_title}")
                    else:
                        print(f"[mass] ❌ Comment error ({acc_name}, {vid_id}): {err_str[:80]}")
                        errors += 1
                
                await asyncio.sleep(0.5)
            
            # Har 10 ta videodan keyin progress xabar
            if vid_idx % 10 == 0:
                await safe_edit(progress_msg,
                    f"👤 `[{acc_idx}/{total_accounts}] {acc_name}`\n"
                    f"📊 `Video: {vid_idx}/{total_videos} | 👍{total_likes} 💬{total_comments} 🔔{total_subs}`"
                )
        
        # Akkauntlar orasida pauza (Max 15 soniya)
        if acc_idx < total_accounts:
            await safe_edit(progress_msg,
                f"✅ `{acc_name} tugadi!`\n"
                f"⏳ `Keyingi akkauntga o'tilmoqda...`"
            )
            await asyncio.sleep(random.uniform(3, 5))
    
    # 5. Yakuniy hisobot
    await safe_send(
        f"🎉 **Mass Action Yakunlandi!**\n\n"
        f"📺 Kanal: `{channel_name}`\n"
        f"👥 Akkauntlar: `{total_accounts}` ta\n"
        f"🎬 Videolar: `{total_videos}` ta\n\n"
        f"📊 **Natijalar:**\n"
        f"   👍 Layklar: `{total_likes}`\n"
        f"   💬 Kommentlar: `{total_comments}`\n"
        f"   🔔 Obunalar: `{total_subs}`\n"
        f"   ❌ Xatoliklar: `{errors}`"
    )
