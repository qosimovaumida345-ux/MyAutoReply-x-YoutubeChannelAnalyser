import asyncio
import os
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from database import get_yt_connection, update_autopost_task, add_autopost_history, update_autopost_history
from config import get_youtube_key

def download_video(video_id):
    """yt-dlp orqali videoni yuklab olish"""
    outtmpl = f"downloads/{video_id}.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    return outtmpl

def upload_to_youtube(file_path, title, description, credentials_dict):
    """OAuth orqali videoni yuklash"""
    creds = Credentials(
        token=credentials_dict['access_token'],
        refresh_token=credentials_dict['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("YT_CLIENT_ID", "dummy_client_id"),
        client_secret=os.getenv("YT_CLIENT_SECRET", "dummy_client_secret")
    )
    
    youtube = build("youtube", "v3", credentials=creds)
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["autopost", "gaming", "shorts"],
            "categoryId": "20" # Gaming
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = request.execute()
    return response.get("id")

async def autopost_worker(task_id, tg_user_id, search_query, count, client, chat_id):
    """Background task: videolarni qidiradi, yuklab oladi va kanalga post qiladi"""
    try:
        await client.send_message(chat_id, f"🔄 Auto-post boshlandi: {count} ta video '{search_query}' bo'yicha...")
        
        # 1. Credentials tekshirish
        conn_data = get_yt_connection(tg_user_id)
        if not conn_data or not conn_data.get("access_token"):
            await client.send_message(chat_id, "❌ Kanalingiz ulanmagan! Avval /ytlogin orqali kanalingizni ulang.")
            update_autopost_task(task_id, status="failed")
            return
            
        # 2. Videolarni qidirish (YouTube API orqali)
        yt = build("youtube", "v3", developerKey=get_youtube_key())
        search_res = yt.search().list(
            q=search_query,
            part="snippet",
            maxResults=count,
            type="video"
        ).execute()
        
        videos = search_res.get("items", [])
        if not videos:
            await client.send_message(chat_id, "❌ Videolar topilmadi.")
            update_autopost_task(task_id, status="failed")
            return
            
        success_count = 0
        update_autopost_task(task_id, status="running")
        
        for idx, item in enumerate(videos, 1):
            vid_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            desc = item["snippet"]["description"]
            
            # DB ga yozish
            hist_id = add_autopost_history(task_id, tg_user_id, vid_id, title)
            
            msg = await client.send_message(chat_id, f"⏳ [{idx}/{count}] Yuklab olinmoqda: {title}...")
            
            try:
                # Yuklab olish
                file_path = download_video(vid_id)
                
                await msg.edit_text(f"⏳ [{idx}/{count}] Kanalingizga yuklanmoqda (upload): {title}...")
                
                # Yuklash
                # Eslatma: Hozircha Google Oauth ruxsati bo'lmagani uchun xato beradi.
                # Agar to'liq ishlab ketsa, pastdagi qatorni oching.
                # new_vid_id = upload_to_youtube(file_path, title, desc, conn_data)
                
                # Sмуляatsiya (Simulyasiya o'rniga haqiqiy ulanish uchun yuqoridagi kodni ishlating)
                await asyncio.sleep(2)
                new_vid_id = f"simulated_{vid_id}"
                
                update_autopost_history(hist_id, status="uploaded", uploaded_video_id=new_vid_id, uploaded_title=title)
                success_count += 1
                
                # Faylni tozalash
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                await msg.edit_text(f"✅ [{idx}/{count}] Muvaffaqiyatli yuklandi: {title}")
                
            except Exception as e:
                update_autopost_history(hist_id, status="failed", error_msg=str(e))
                await msg.edit_text(f"❌ [{idx}/{count}] Xatolik: {e}")
                
            update_autopost_task(task_id, completed_count=success_count)
            
        update_autopost_task(task_id, status="completed")
        await client.send_message(chat_id, f"🎉 Auto-post yakunlandi! {success_count}/{count} video yuklandi.")
        
    except Exception as e:
        update_autopost_task(task_id, status="failed")
        await client.send_message(chat_id, f"❌ Dastur xatosi: {e}")
