import asyncio
import os
import yt_dlp
from urllib.parse import urlencode, parse_qs, urlparse
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from database import get_yt_connection, update_autopost_task, add_autopost_history, update_autopost_history, save_yt_connection, get_config, get_user_cookies, has_video_been_posted
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
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
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
    channel_username = ""
    if r.get("items"):
        channel_title = r["items"][0]["snippet"]["title"]
        channel_id = r["items"][0]["id"]
        channel_username = r["items"][0]["snippet"].get("customUrl", "")

    # Telegram user ID ni state orqali topish
    tg_user_id = pending_oauth.pop(state, None) if state else None

    return {
        "tg_user_id": tg_user_id,
        "channel_title": channel_title,
        "channel_username": channel_username,
        "channel_id": channel_id,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_expiry": creds.expiry
    }


# ==================== VIDEO DOWNLOAD ====================

def test_available_formats(video_id="dQw4w9WgXcQ"):
    """
    Bulut serverda qaysi formatlar mavjudligini tekshirish uchun.
    Bot loglarida ko'rinadi (Render Dashboard > Logs).
    Usage: call this from ytbot.py with a /testformats command.
    """
    import json
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    results = {}
    clients_to_test = ['tv_embedded', 'ios', 'web', 'android', 'mweb']
    
    print(f"\n{'='*60}")
    print(f"[FORMAT TEST] Testing video: {video_id}")
    print(f"[FORMAT TEST] URL: {url}")
    print(f"{'='*60}")
    
    for client in clients_to_test:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': False,
                'skip_download': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': [client],
                    }
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                http_formats = [f for f in formats if f.get('protocol') in ('https', 'http')]
                results[client] = {
                    'total': len(formats),
                    'http_only': len(http_formats),
                    'best': max((f.get('height', 0) for f in http_formats if f.get('height')), default=0)
                }
                print(f"[FORMAT TEST] {client:15} → total={len(formats):3d} | http={len(http_formats):3d} | best_height={results[client]['best']}p")
        except Exception as e:
            results[client] = {'error': str(e)[:100]}
            print(f"[FORMAT TEST] {client:15} → ERROR: {str(e)[:80]}")
    
    print(f"{'='*60}\n")
    return results

def download_video(video_id, proxy_url=None, user_id=None, apply_watermark=False, channel_title="", channel_pfp=""):
    """yt-dlp orqali videoni yuklab olish"""
    import os
    import glob
    import yt_dlp
    from database import get_user_cookies
    
    os.makedirs("downloads", exist_ok=True)
    raw_tmpl = f"downloads/{video_id}_raw.%(ext)s"
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Cookies
    cookies_text = get_user_cookies(user_id) if user_id else None
    cookie_path = f"downloads/cookies_{video_id}.txt"
    has_cookies = False
    if cookies_text:
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(cookies_text)
        has_cookies = True

    ydl_opts = {
        'format': 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': raw_tmpl,
        'quiet': False,
        'no_warnings': False,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'mweb'],
                'player_skip': ['webpage'],
            }
        },
        'source_address': '0.0.0.0',
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'sleep_interval': 1,
        'max_sleep_interval': 3,
    }

    if proxy_url:
        ydl_opts['proxy'] = proxy_url

    if has_cookies:
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "format" in error_msg or "not available" in error_msg or "sign in" in error_msg:
            print(f"[AUTOPOST] tv_embedded/mweb failed for {video_id}, trying fallback clients...")

            fallback_opts = dict(ydl_opts)
            fallback_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'mweb', 'web_creator'],
                    'player_skip': ['webpage'],
                }
            }
            fallback_opts['format'] = 'best[ext=mp4]/best'
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([url])
        else:
            raise
    finally:
        if os.path.exists(cookie_path):
            os.remove(cookie_path)

    # Fayl topish — glob bilan barcha mumkin bo'lgan extensionlarni tekshirish
    raw_mp4 = f"downloads/{video_id}_raw.mp4"
    if not os.path.exists(raw_mp4):
        candidates = glob.glob(f"downloads/{video_id}_raw.*")
        if candidates:
            raw_mp4 = candidates[0]
            print(f"[AUTOPOST] Fayl topildi (mp4 emas): {raw_mp4}")

    if not os.path.exists(raw_mp4):
        # Oxirgi tekshiruv — downloads papkasida bor narsalarni log qilish
        all_files = os.listdir("downloads")
        matching = [f for f in all_files if video_id in f]
        print(f"[AUTOPOST] downloads/ papkasida {video_id} ga tegishli fayllar: {matching}")
        if matching:
            raw_mp4 = os.path.join("downloads", matching[0])
        else:
            raise Exception(f"Video yuklab olinmadi: {video_id} — fayl topilmadi. downloads/ ichida: {all_files[:10]}")

    final_mp4 = f"downloads/{video_id}.mp4"
    
    # Watermark qo'shish (ixtiyoriy)
    if apply_watermark:
        print(f"[{video_id}] Watermark qo'shilmoqda ({channel_title})...")
        safe_title = channel_title.replace("'", "\\'")
        
        if channel_pfp and os.path.exists(channel_pfp):
            os.system(f'''ffmpeg -y -i "{raw_mp4}" -i "{channel_pfp}" -filter_complex "[0:v]crop=in_w:in_h*0.8:0:in_h*0.1[vid];[1:v]scale=h/10:-1[logo];[vid][logo]overlay=W-w-10:H-h-10, drawtext=text=\'{safe_title}\':fontcolor=white:fontsize=h/15:x=w-tw-10-main_h/10-10:y=h-th-10:box=1:boxcolor=black@0.5:boxborderw=5" -c:v libx264 -preset veryfast -crf 28 -c:a copy "{final_mp4}"''')
        else:
            os.system(f'''ffmpeg -y -i "{raw_mp4}" -vf "crop=in_w:in_h*0.8:0:in_h*0.1, drawtext=text=\'{safe_title}\':fontcolor=white:fontsize=h/15:x=w-tw-10:y=h-th-10:box=1:boxcolor=black@0.5:boxborderw=5" -c:v libx264 -preset veryfast -crf 28 -c:a copy "{final_mp4}"''')
            
        try: os.remove(raw_mp4)
        except: pass
        
        if os.path.exists(final_mp4):
            return final_mp4
    
    return raw_mp4

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

async def autopost_worker(task_id, tg_user_id, search_query, count, client, chat_id, proxy_url=None, apply_watermark=False):
    """Background task: videolarni qidiradi, yuklab oladi va kanalga post qiladi"""
    try:
        async def safe_send(text):
            if client:
                try: return await client.send_message(chat_id, text)
                except: pass
            return None

        async def safe_edit(msg_obj, text):
            if msg_obj:
                try: await msg_obj.edit_text(text)
                except: pass

        await safe_send(f"🔄 `Auto-post boshlandi: {count} ta video '{search_query}' bo'yicha...`")

        # 1. Credentials tekshirish
        conn_data = get_yt_connection(tg_user_id)
        if not conn_data or not conn_data.get("access_token"):
            await safe_send("❌ `Kanalingiz ulanmagan! Avval /ytlogin orqali kanalingizni ulang.`")
            update_autopost_task(task_id, status="failed")
            return
            
        # Get channel details
        channel_title = conn_data.get("yt_channel_title", "AutoPost")
        channel_pfp = ""
        if apply_watermark:
            try:
                import urllib.request
                yt_info = build("youtube", "v3", developerKey=get_youtube_key())
                res = yt_info.channels().list(part="snippet", id=conn_data['yt_channel_id']).execute()
                pfp_url = res['items'][0]['snippet']['thumbnails']['default']['url']
                os.makedirs("downloads", exist_ok=True)
                channel_pfp = f"downloads/pfp_{conn_data['yt_channel_id']}.jpg"
                urllib.request.urlretrieve(pfp_url, channel_pfp)
            except Exception as e:
                print(f"PFP Error: {e}")

        # 2. Videolarni qidirish (YouTube API orqali)
        yt = build("youtube", "v3", developerKey=get_youtube_key())
        
        if search_query.startswith("__IDS__:"):
            vid_ids = search_query.replace("__IDS__:", "").split(",")
            search_res = yt.videos().list(
                part="snippet",
                id=",".join(vid_ids)
            ).execute()
        else:
            search_res = yt.search().list(
                q=search_query,
                part="snippet",
                maxResults=min(count, 50),  # YouTube API max 50
                type="video"
            ).execute()

        videos = search_res.get("items", [])
        if not videos:
            await safe_send("❌ `Videolar topilmadi.`")
            update_autopost_task(task_id, status="failed")
            return

        success_count = 0
        process_idx = 0  # FIX: process_idx aniqlanmagan edi → NameError crash bo'lardi
        update_autopost_task(task_id, status="running")
        for idx, item in enumerate(videos, 1):
            if isinstance(item["id"], dict):
                vid_id = item["id"].get("videoId", "")
            else:
                vid_id = item["id"]
                
            if not vid_id: continue
                
            title = item["snippet"]["title"]
            desc = item["snippet"]["description"]

            # Avval yuklangan videoni skip qilish
            if has_video_been_posted(tg_user_id, vid_id):
                print(f"[autopost] Skip (allaqachon yuklangan): {vid_id}")
                continue

            process_idx += 1  # FIX: faqat haqiqiy yuklanadigan videolar uchun oshirish

            # DB ga yozish
            hist_id = add_autopost_history(task_id, tg_user_id, vid_id, title)

            msg = await safe_send(f"⏳ `[{process_idx}/{count}] Yuklab olinmoqda: {title[:50].replace('`', '')}...`")

            file_path = None
            try:
                # Yuklab olish (proxy bilan)
                file_path = await asyncio.to_thread(
                    download_video, vid_id, proxy_url, tg_user_id,
                    apply_watermark, channel_title, channel_pfp
                )

                safe_title = title[:50].replace('`', "'")
                await safe_edit(msg, f"⏳ `[{process_idx}/{count}] Kanalingizga yuklanmoqda: {safe_title}...`")
                # Haqiqiy yuklash
                await safe_edit(msg, f"⏳ `[{process_idx}/{count}] YouTube'ga yuklanmoqda...`")
                new_vid_id = await asyncio.to_thread(upload_to_youtube, file_path, title, desc, conn_data)
                
                update_autopost_history(hist_id, status="uploaded", uploaded_video_id=new_vid_id, uploaded_title=title)
                success_count += 1

                # Faylni tozalash
                if os.path.exists(file_path):
                    os.remove(file_path)

                await safe_edit(msg, f"✅ `[{process_idx}/{count}] Yuklandi: {safe_title}`\nYouTube ID: `{new_vid_id}`")




            except Exception as e:
                err_msg = str(e).replace('`', "'")
                if "Sign in to confirm" in err_msg:
                    err_msg = "YouTube cookie lari yaroqsiz! Iltimos, ularni yangilang yoki qayta /setcookies qiling."
                update_autopost_history(hist_id, status="failed", error_msg=err_msg)
                await safe_edit(msg, f"❌ `[{process_idx}/{count}] Xatolik: {err_msg[:300]}`")
                # Xatolikda ham faylni tozalash
                try:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass

            update_autopost_task(task_id, completed_count=success_count)

            # Rate limiting — har bir video orasida 10 soniya kutish
            await asyncio.sleep(10)

        update_autopost_task(task_id, status="completed")
        await safe_send(f"🎉 `Auto-post yakunlandi! {success_count}/{len(videos)} video yuklandi.`")

    except Exception as e:
        update_autopost_task(task_id, status="failed")
        await safe_send(f"❌ `Dastur xatosi: {str(e)[:300].replace('`', '')}`")
        