import asyncio
import os
import yt_dlp
from urllib.parse import urlencode, parse_qs, urlparse
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from database import get_yt_connection, update_autopost_task, add_autopost_history, update_autopost_history, save_yt_connection, get_config
from config import get_youtube_key, YT_CLIENT_ID, YT_CLIENT_SECRET

# Google qo'shimcha scope qaytarishini qabul qilish (scope mismatch xatosini oldini olish)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Render service URL (callback uchun)
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://botclient-d1jn.onrender.com")
REDIRECT_URI = f"{RENDER_URL}/oauth/callback"

CLIENT_CONFIG = {
    "web": {
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI]
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

# Vaqtinchalik OAuth state saqlash (tg_user_id -> state)
pending_oauth = {}


def get_auth_url(tg_user_id):
    """OAuth URL yaratish (Web Application uchun callback bilan)"""
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    # State ni Telegram user ID bilan bog'lab saqlash
    pending_oauth[state] = tg_user_id
    return auth_url


def exchange_code_with_redirect(code, state=None):
    """Callback orqali kelgan kodni tokenlarga almashtirish"""
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Kanalingiz nomini aniqlash
    youtube = build("youtube", "v3", credentials=creds)
    r = youtube.channels().list(part="snippet", mine=True).execute()

    channel_title = "Unknown"
    channel_id = "unknown"
    if r.get("items"):
        channel_title = r["items"][0]["snippet"]["title"]
        channel_id = r["items"][0]["id"]

    # Telegram user ID ni state orqali topish
    tg_user_id = pending_oauth.pop(state, None) if state else None

    return {
        "tg_user_id": tg_user_id,
        "channel_title": channel_title,
        "channel_id": channel_id,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_expiry": creds.expiry,
    }


# ==================== VIDEO DOWNLOAD ====================

def download_video(video_id, proxy_url=None):
    """yt-dlp orqali videoni yuklab olish (proxy va cookies bilan)"""
    os.makedirs("downloads", exist_ok=True)
    outtmpl = f"downloads/{video_id}.mp4"
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'best',  # Eng oddiy va har doim ishlaydi
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # ====== YouTube Bot Detection Bypass ======
        'source_address': '0.0.0.0',  # Force IPv4
        # Brauzer kabi ko'rinish (YouTube bot larni filter qiladi)
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        },
        # iOS va web player orqali urinish (bot bloklarini aylanib o'tish)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web'],
            }
        },
        # So'rovlar orasida kechikish (bot kabi ko'rinmaslik uchun)
        'sleep_interval': 2,
        'max_sleep_interval': 5,
        'sleep_interval_requests': 1,
        # Xato bo'lsa qayta urinish
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
    }
    
    # Proxy qo'shish (foydalanuvchi yoki default)
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
    
    # Bazadan cookies ni olish
    cookies_text = get_config("yt_cookies")
    cookie_path = "downloads/cookies.txt"
    if cookies_text:
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(cookies_text)
        ydl_opts['cookiefile'] = cookie_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        # Faylni xavfsizlik uchun o'chirish (agar yaratilgan bo'lsa)
        if os.path.exists(cookie_path):
            os.remove(cookie_path)
    
    # Haqiqiy fayl nomini topish
    final_path = f"downloads/{video_id}.mp4"
    if os.path.exists(final_path):
        return final_path
    for f in os.listdir("downloads"):
        if f.startswith(video_id):
            return os.path.join("downloads", f)
    return final_path


# ==================== VIDEO UPLOAD ====================

def upload_to_youtube(file_path, title, description, credentials_dict):
    """OAuth orqali videoni YouTube ga yuklash"""
    creds = Credentials(
        token=credentials_dict['access_token'],
        refresh_token=credentials_dict['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET
    )

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],  # YouTube max 100 belgi
            "description": description,
            "tags": ["autopost"],
            "categoryId": "22"  # People & Blogs (umumiy)
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


# ==================== AUTO-POST WORKER ====================

async def autopost_worker(task_id, tg_user_id, search_query, count, client, chat_id, proxy_url=None):
    """Background task: videolarni qidiradi, yuklab oladi va kanalga post qiladi"""
    try:
        await client.send_message(chat_id, f"🔄 `Auto-post boshlandi: {count} ta video '{search_query}' bo'yicha...`")

        # 1. Credentials tekshirish
        conn_data = get_yt_connection(tg_user_id)
        if not conn_data or not conn_data.get("access_token"):
            await client.send_message(chat_id, "❌ `Kanalingiz ulanmagan! Avval /ytlogin orqali kanalingizni ulang.`")
            update_autopost_task(task_id, status="failed")
            return

        # 2. Videolarni qidirish (YouTube API orqali)
        yt = build("youtube", "v3", developerKey=get_youtube_key())
        search_res = yt.search().list(
            q=search_query,
            part="snippet",
            maxResults=min(count, 50),  # YouTube API max 50
            type="video"
        ).execute()

        videos = search_res.get("items", [])
        if not videos:
            await client.send_message(chat_id, "❌ `Videolar topilmadi.`")
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

            msg = await client.send_message(chat_id, f"⏳ `[{idx}/{len(videos)}] Yuklab olinmoqda: {title[:50]}...`")

            try:
                # Yuklab olish (proxy bilan)
                file_path = await asyncio.to_thread(download_video, vid_id, proxy_url)

                await msg.edit_text(f"⏳ `[{idx}/{len(videos)}] Kanalingizga yuklanmoqda: {title[:50]}...`")

                # Haqiqiy yuklash
                new_vid_id = await asyncio.to_thread(upload_to_youtube, file_path, title, desc, conn_data)

                update_autopost_history(hist_id, status="uploaded", uploaded_video_id=new_vid_id, uploaded_title=title)
                success_count += 1

                # Faylni tozalash
                if os.path.exists(file_path):
                    os.remove(file_path)

                await msg.edit_text(f"✅ `[{idx}/{len(videos)}] Yuklandi: {title[:50]}`")

            except Exception as e:
                update_autopost_history(hist_id, status="failed", error_msg=str(e))
                await msg.edit_text(f"❌ `[{idx}/{len(videos)}] Xatolik: {str(e)[:100]}`")
                # Xatolikda ham faylni tozalash
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass

            update_autopost_task(task_id, completed_count=success_count)

            # Rate limiting — har bir video orasida 10 soniya kutish
            await asyncio.sleep(10)

        update_autopost_task(task_id, status="completed")
        await client.send_message(chat_id, f"🎉 `Auto-post yakunlandi! {success_count}/{len(videos)} video yuklandi.`")

    except Exception as e:
        update_autopost_task(task_id, status="failed")
        await client.send_message(chat_id, f"❌ `Dastur xatosi: {str(e)[:100]}`")
