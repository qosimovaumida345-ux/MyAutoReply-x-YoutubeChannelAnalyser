import asyncio
import os
import yt_dlp
from urllib.parse import urlencode, parse_qs, urlparse
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from database import get_yt_connection, update_autopost_task, add_autopost_history, update_autopost_history, save_yt_connection, get_config, get_user_cookies, has_video_been_posted
from config import get_youtube_key, build_youtube_api, YT_CLIENT_ID, YT_CLIENT_SECRET, APP_BASE_URL

# Google qo'shimcha scope qaytarishini qabul qilish (scope mismatch xatosini oldini olish)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# OAuth callback URL (centralized via config.APP_BASE_URL)
RENDER_URL = APP_BASE_URL
REDIRECT_URI = f"{APP_BASE_URL}/oauth/callback"

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


def get_auth_url(tg_user_id=0):
    """OAuth URL yaratish (Web Application uchun callback bilan)"""
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        hl='en',
    )
    # State ni Telegram user ID bilan bog'lab saqlash
    if tg_user_id:
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
    r = youtube.channels().list(part="snippet,statistics", mine=True).execute()

    channel_title = "Unknown"
    channel_id = "unknown"
    channel_username = ""
    channel_thumbnail = ""
    subscriber_count = 0
    if r.get("items"):
        item = r["items"][0]
        snippet = item.get("snippet", {})
        channel_title = snippet.get("title", "Unknown")
        channel_id = item.get("id", "unknown")
        channel_username = snippet.get("customUrl", "")
        thumbs = snippet.get("thumbnails", {})
        channel_thumbnail = thumbs.get("medium", {}).get("url") or thumbs.get("default", {}).get("url", "")
        stats = item.get("statistics", {})
        subscriber_count = int(stats.get("subscriberCount", 0))

    # Telegram user ID ni state orqali topish
    tg_user_id = pending_oauth.pop(state, None) if state else None

    return {
        "tg_user_id": tg_user_id,
        "channel_title": channel_title,
        "channel_username": channel_username,
        "channel_id": channel_id,
        "channel_thumbnail": channel_thumbnail,
        "subscriber_count": subscriber_count,
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
    cookies_text = get_user_cookies(user_id)
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
                'player_client': ['android_vr', 'android', 'tv_embedded'],
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

    # PO Token Provider (bgutil HTTP server 127.0.0.1:4416)
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:4416/ping", timeout=0.8) as pot_resp:
            if pot_resp.status == 200:
                ydl_opts.setdefault('extractor_args', {}).setdefault('youtubepot-bgutilhttp', {})['base_url'] = "http://127.0.0.1:4416"
    except Exception:
        pass

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "format" in error_msg or "not available" in error_msg or "sign in" in error_msg or "429" in error_msg:
            print(f"[AUTOPOST] Primary clients failed for {video_id}, trying android/ios fallback...")

            fallback_opts = dict(ydl_opts)
            fallback_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android_vr', 'android', 'tv_embedded'],
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
            try: os.remove(cookie_path)
            except: pass

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
    
    # Kengaytirilgan video qayta ishlash (Watermark, Captions, Branding)
    from video_processor import process_video_advanced
    try:
        processed_mp4 = process_video_advanced(raw_mp4, channel_title, channel_pfp)
        
        # Agar fayl o'zgargan bo'lsa uni final nomiga ko'chiramiz
        if processed_mp4 != raw_mp4 and os.path.exists(processed_mp4):
            os.rename(processed_mp4, final_mp4)
            try: os.remove(raw_mp4)
            except: pass
            return final_mp4
        else:
            # Agar o'zgarmagan bo'lsa, xom faylni qaytaramiz
            os.rename(raw_mp4, final_mp4)
            return final_mp4
    except Exception as e:
        print(f"[AUTOPOST] Video ishlash xatosi: {e}")
        os.rename(raw_mp4, final_mp4)
        return final_mp4

# ==================== VIDEO UPLOAD ====================

def upload_to_youtube(file_path, title, description, credentials_dict):
    """OAuth orqali videoni YouTube ga yuklash (eskirgan access_token ni avtomatik yangilaydi)."""
    from google.auth.transport.requests import Request
    from database import update_yt_tokens

    creds = Credentials(
        token=credentials_dict.get('access_token'),
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET
    )

    def _refresh_creds_if_needed(force: bool = False):
        if creds.refresh_token and (force or not creds.token or creds.expired):
            creds.refresh(Request())
            credentials_dict['access_token'] = creds.token
            tg_uid = credentials_dict.get('tg_user_id')
            yt_chid = credentials_dict.get('yt_channel_id')
            if tg_uid and yt_chid:
                try:
                    update_yt_tokens(tg_uid, yt_chid, creds.token, creds.refresh_token)
                except Exception:
                    pass

    _refresh_creds_if_needed(force=False)

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

    def _execute_upload():
        youtube = build("youtube", "v3", credentials=creds)
        media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=False)
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        return request.execute()

    try:
        response = _execute_upload()
    except Exception as exc:
        err_low = str(exc).lower()
        is_auth_err = any(k in err_low for k in ("401", "invalid_credentials", "unauthorized", "token has been expired", "autherror"))
        if is_auth_err and creds.refresh_token:
            _refresh_creds_if_needed(force=True)
            response = _execute_upload()
        else:
            raise
    return response.get("id")


def search_youtube_candidates(query: str, max_results: int = 8, video_type: str = "shorts") -> list[dict]:
    """
    Qidiruv so'rovi bo'yicha YouTube videolarini topish.
    1-navbatda YouTube Data API v3 ishlatiladi; kvota tugasa yoki xato bersa
    avtomatik yt_dlp ytsearch fallback orqali namuna videolar ro'yxatini qaytaradi.
    """
    import re as _re
    import yt_dlp

    q = (query or "").strip()
    if not q:
        return []

    # Strip inline selected IDs tag if present in task query
    m_vids = _re.search(r"\[vids:([A-Za-z0-9_,-]+)\]", q)
    explicit_ids: list[str] = []
    if m_vids:
        explicit_ids = [v.strip() for v in m_vids.group(1).split(",") if v.strip()]
        q = _re.sub(r"\s*\[vids:[A-Za-z0-9_,-]+\]", "", q).strip()
    elif q.startswith("__IDS__:"):
        explicit_ids = [v.strip() for v in q.replace("__IDS__:", "").split(",") if v.strip()]

    # 1. Try YouTube Data API v3 first
    try:
        yt = build_youtube_api()
        if explicit_ids:
            res = yt.videos().list(part="snippet,contentDetails,statistics", id=",".join(explicit_ids[:20])).execute()
        else:
            search_q = f"{q} #shorts" if video_type in ("short", "shorts") and "short" not in q.lower() else q
            res = yt.search().list(
                q=search_q,
                part="snippet",
                maxResults=min(max(1, int(max_results)), 25),
                type="video",
            ).execute()
        items = res.get("items", [])
        out: list[dict] = []
        for item in items:
            vid_id = item["id"].get("videoId", "") if isinstance(item.get("id"), dict) else str(item.get("id", ""))
            if not vid_id:
                continue
            snip = item.get("snippet") or {}
            thumbs = snip.get("thumbnails") or {}
            thumb_url = (
                (thumbs.get("high") or {}).get("url")
                or (thumbs.get("medium") or {}).get("url")
                or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
            )
            stats = item.get("statistics") or {}
            out.append({
                "id": vid_id,
                "title": snip.get("title") or "Untitled",
                "description": snip.get("description") or "",
                "channel": snip.get("channelTitle") or "",
                "thumbnail": thumb_url,
                "published": snip.get("publishedAt") or "",
                "views": int(stats.get("viewCount", 0) or 0),
                "duration": 0,
            })
        if out:
            return out[:max_results]
    except Exception as e:
        print(f"[search_youtube_candidates] API fallback to yt_dlp: {e}")

    # 2. Fallback: yt_dlp ytsearch (zero YouTube API quota cost)
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
        }
        if explicit_ids:
            out = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for vid in explicit_ids[:max_results]:
                    try:
                        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                        if info:
                            out.append({
                                "id": vid,
                                "title": info.get("title") or f"Video {vid}",
                                "description": (info.get("description") or "")[:400],
                                "channel": info.get("uploader") or info.get("channel") or "",
                                "thumbnail": info.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                                "published": info.get("upload_date") or "",
                                "views": int(info.get("view_count") or 0),
                                "duration": int(info.get("duration") or 0),
                            })
                    except Exception:
                        out.append({
                            "id": vid,
                            "title": f"Video {vid}",
                            "description": "",
                            "channel": "",
                            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                            "published": "",
                            "views": 0,
                            "duration": 0,
                        })
            return out

        search_term = f"{q} shorts" if video_type in ("short", "shorts") and "short" not in q.lower() else q
        fetch_n = min(30, max(max_results * 2, 10))
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{fetch_n}:{search_term}", download=False)
        entries = (info or {}).get("entries") or []
        out = []
        for entry in entries:
            if not entry:
                continue
            vid = entry.get("id") or ""
            if not vid:
                continue
            dur = int(entry.get("duration") or 0)
            if video_type in ("short", "shorts") and dur > 120:
                continue
            out.append({
                "id": vid,
                "title": entry.get("title") or f"Video {vid}",
                "description": (entry.get("description") or "")[:400],
                "channel": entry.get("uploader") or entry.get("channel") or "",
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                "published": entry.get("upload_date") or "",
                "views": int(entry.get("view_count") or 0),
                "duration": dur,
            })
            if len(out) >= max_results:
                break
        return out
    except Exception as e2:
        print(f"[search_youtube_candidates] yt_dlp fallback error: {e2}")
        return []


# ==================== AUTO-POST WORKER ====================

async def autopost_worker(task_id, tg_user_id, search_query, count, client, chat_id, proxy_url=None, apply_watermark=False, channel_id=None, selected_video_ids=None):
    """Background task: videolarni qidiradi, watermarkni tozalaydi, yuklab oladi va kanalga post qiladi"""
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

        # 1. Credentials tekshirish (kerakli kanalni tanlash)
        if not channel_id:
            try:
                from database import get_autopost_task_by_id
                trow = get_autopost_task_by_id(task_id)
                if trow:
                    channel_id = trow.get("yt_channel_id")
            except Exception:
                pass
        conn_data = get_yt_connection(tg_user_id, channel_id=channel_id)
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
                yt_info = build_youtube_api()
                res = yt_info.channels().list(part="snippet", id=conn_data['yt_channel_id']).execute()
                pfp_url = res['items'][0]['snippet']['thumbnails']['default']['url']
                os.makedirs("downloads", exist_ok=True)
                channel_pfp = f"downloads/pfp_{conn_data['yt_channel_id']}.jpg"
                urllib.request.urlretrieve(pfp_url, channel_pfp)
            except Exception as e:
                print(f"PFP Error: {e}")

        # 2. Videolarni qidirish (API + yt_dlp fallback)
        if selected_video_ids and isinstance(selected_video_ids, (list, tuple)):
            query_for_search = "__IDS__:" + ",".join(str(v).strip() for v in selected_video_ids if str(v).strip())
        else:
            query_for_search = search_query

        candidate_items = await asyncio.to_thread(
            search_youtube_candidates,
            query_for_search,
            max(int(count) * 4, 10),
            "shorts",
        )
        if not candidate_items:
            await safe_send("❌ `Videolar topilmadi.`")
            update_autopost_task(task_id, status="failed")
            return

        success_count = 0
        process_idx = 0
        update_autopost_task(task_id, status="running")
        for item in candidate_items:
            if success_count >= int(count):
                break
            vid_id = item.get("id", "")
            if not vid_id:
                continue

            title = item.get("title") or f"Short #{vid_id}"
            desc = item.get("description") or ""

            # Avval yuklangan videoni skip qilish
            if has_video_been_posted(tg_user_id, vid_id):
                print(f"[autopost] Skip (allaqachon yuklangan): {vid_id}")
                continue

            process_idx += 1

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
        await safe_send(f"🎉 `Auto-post yakunlandi! {success_count}/{count} video yuklandi.`")

    except Exception as e:
        update_autopost_task(task_id, status="failed")
        await safe_send(f"❌ `Dastur xatosi: {str(e)[:300].replace('`', '')}`")
        