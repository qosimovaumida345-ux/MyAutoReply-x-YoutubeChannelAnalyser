import os
import asyncio
import subprocess
from database import get_stream_key

# Memory dict to store ffmpeg process for each user
autostream_tasks = {}

async def download_videos(search_query, chat_id, tg_user_id=None, limit=5):
    """
    Search and download videos using yt-dlp.
    We download them to a temporary directory.
    Returns list of downloaded video paths.
    """
    import yt_dlp
    from database import get_user_cookies
    
    download_dir = f"/tmp/autostream_{chat_id}"
    os.makedirs(download_dir, exist_ok=True)
    
    cookies_text = get_user_cookies(tg_user_id)
    cookie_path = f"{download_dir}/cookies.txt"
    has_cookies = False
    if cookies_text:
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(cookies_text)
        has_cookies = True
    
    # We want to download the best mp4 format or anything that ffmpeg can easily concat
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'max_downloads': limit,
        'quiet': False,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb', 'web'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'compat_opts': ['no-youtube-unavailable-videos'],
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True
    }
    
    if has_cookies:
        ydl_opts['cookiefile'] = cookie_path
    
    # If the query is just a single URL, process it. Otherwise, ytsearch
    if search_query.startswith("http"):
        url = search_query
    else:
        url = f"ytsearch{limit}:{search_query}"
        
    def _run_ydl():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if 'entries' in info:
                    # It was a search
                    return [ydl.prepare_filename(e) for e in info['entries'] if e]
                else:
                    return [ydl.prepare_filename(info)]
        except Exception as e:
            print(f"yt-dlp autostream download error: {e}")
            return []
            
    try:
        paths = await asyncio.to_thread(_run_ydl)
    finally:
        if os.path.exists(cookie_path):
            try: os.remove(cookie_path)
            except: pass
    
    # Verify files exist
    valid_paths = [p for p in paths if os.path.exists(p)]
    return valid_paths

async def start_autostream(tg_user_id, search_query, client, chat_id):
    """
    1. Check stream key
    2. Download videos
    3. Create concat list
    4. Start FFmpeg
    """
    if tg_user_id in autostream_tasks:
        await client.send_message(chat_id, "Sizda allaqachon bitta translatsiya ketyapti! Avval uni to'xtating (/autostream stop).")
        return

    stream_key = get_stream_key(tg_user_id)
    if not stream_key:
        await client.send_message(chat_id, "❌ Sizda Stream Key o'rnatilmagan! Iltimos, `/setstreamkey <key>` orqali YouTube jonli efir kodingizni kiriting.")
        return

    msg = await client.send_message(chat_id, f"🔍 Kuting, '{search_query}' bo'yicha videolar qidirilyapti va yuklanyapti...")
    
    video_paths = await download_videos(search_query, chat_id, tg_user_id=tg_user_id, limit=5)
    
    if not video_paths:
        await msg.edit_text("❌ Hech qanday video topilmadi yoki yuklashda xatolik yuz berdi.")
        return
        
    await msg.edit_text(f"✅ {len(video_paths)} ta video yuklandi. Endi Live Stream boshlanmoqda...")
    
    # Create filelist.txt
    list_path = f"/tmp/autostream_{chat_id}/filelist.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in video_paths:
            # properly escape path for ffmpeg
            safe_path = p.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
            
    # Start FFmpeg subprocess
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    cmd = [
        "ffmpeg", "-re",
        "-f", "concat",
        "-safe", "0",
        "-stream_loop", "-1",
        "-i", list_path,
        "-vf", "scale=1280:720",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "2500k",
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "flv",
        rtmp_url
    ]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        autostream_tasks[tg_user_id] = process
        await msg.edit_text("📺 **Jonli efir muvaffaqiyatli boshlandi!**\n\nBu 24/7 ketaveradi. To'xtatish uchun: `/autostream stop`")
    except Exception as e:
        await msg.edit_text(f"❌ Translatsiyani boshlashda xatolik: {e}")

async def stop_autostream(tg_user_id, client, chat_id):
    """
    Stop the ffmpeg process
    """
    if tg_user_id not in autostream_tasks:
        await client.send_message(chat_id, "❌ Sizda hozir hech qanday translatsiya ketmayapti.")
        return
        
    process = autostream_tasks[tg_user_id]
    try:
        process.terminate()
        process.wait(timeout=5)
    except:
        process.kill()
        
    del autostream_tasks[tg_user_id]
    
    # Clean up files
    import shutil
    try:
        shutil.rmtree(f"/tmp/autostream_{chat_id}", ignore_errors=True)
    except: pass
    
    await client.send_message(chat_id, "🛑 Translatsiya to'xtatildi va vaqtinchalik fayllar tozalandi.")

def get_autostream_status(tg_user_id):
    if tg_user_id in autostream_tasks:
        process = autostream_tasks[tg_user_id]
        if process.poll() is None:
            return "Ketyapti 🟢"
        else:
            del autostream_tasks[tg_user_id]
            return "To'xtagan 🔴 (Jarayon o'z-o'zidan yopilgan)"
    return "To'xtagan 🔴"
