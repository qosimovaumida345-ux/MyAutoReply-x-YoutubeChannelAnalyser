import os
import asyncio
import subprocess
from database import get_stream_key

# Memory dict to store ffmpeg process for each user
autostream_tasks = {}

async def download_videos(search_query, chat_id, tg_user_id=None, limit=4):
    """
    Search and download ONLY YouTube Shorts (duration <= 60s) using yt-dlp.
    We download them to a temporary directory with strict RAM/disk limits.
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
    
    # Filter function: faqat 65 soniyadan qisqa (Shorts) videolarni olish
    def shorts_filter(info_dict, *, incomplete):
        dur = info_dict.get('duration')
        if dur and dur > 65:
            return 'Video davomiyligi 60s dan ko\'p (faqat shorts kerak)'
        return None
    
    # Render RAM tejash uchun formatni 720p yoki undan past qilib cheklaymiz
    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'max_downloads': limit,
        'quiet': False,
        'noplaylist': True,
        'match_filter': shorts_filter,
        'max_filesize': 20 * 1024 * 1024, # Maksimal 20MB har bir video
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
    
    # Agar URL bo'lsa to'g'ridan-to'g'ri, aks holda #shorts qo'shib qidirish
    if search_query.startswith("http"):
        url = search_query
    else:
        # Shorts qidiruvini kuchaytirish
        clean_q = search_query.replace("#shorts", "").replace("shorts", "").strip()
        url = f"ytsearch20:{clean_q} shorts #shorts"
        
    def _run_ydl():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if 'entries' in info:
                    # Qidiruv natijalaridan faqat muvaffaqiyatli yuklanganlarini olish
                    res = []
                    for e in info['entries']:
                        if e:
                            fn = ydl.prepare_filename(e)
                            if os.path.exists(fn):
                                res.append(fn)
                    return res
                else:
                    fn = ydl.prepare_filename(info)
                    return [fn] if os.path.exists(fn) else []
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
    2. Download shorts videos
    3. Create concat list
    4. Start FFmpeg in 9:16 Vertical Shorts format
    """
    if tg_user_id in autostream_tasks:
        await client.send_message(chat_id, "Sizda allaqachon bitta translatsiya ketyapti! Avval uni to'xtating (/autostream stop).")
        return

    stream_key = get_stream_key(tg_user_id)
    if not stream_key:
        await client.send_message(chat_id, "❌ Sizda Stream Key o'rnatilmagan! Iltimos, `/setstreamkey <key>` orqali YouTube jonli efir kodingizni kiriting.")
        return

    msg = await client.send_message(chat_id, f"🔍 Kuting, '{search_query}' bo'yicha **YouTube Shorts** videolari qidirilyapti va yuklanyapti...")
    
    video_paths = await download_videos(search_query, chat_id, tg_user_id=tg_user_id, limit=4)
    
    if not video_paths:
        await msg.edit_text("❌ Hech qanday mos Shorts video topilmadi yoki yuklashda xatolik yuz berdi.")
        return
        
    await msg.edit_text(f"✅ {len(video_paths)} ta Shorts video tayyorlandi.\n📱 **9:16 Vertical Shorts Live Stream** boshlanmoqda...")
    
    # Create filelist.txt
    list_path = f"/tmp/autostream_{chat_id}/filelist.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in video_paths:
            # properly escape path for ffmpeg
            safe_path = p.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
            
    # Start FFmpeg subprocess in 9:16 Vertical format (YouTube Shorts Live)
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    cmd = [
        "ffmpeg", "-re",
        "-f", "concat",
        "-safe", "0",
        "-stream_loop", "-1",
        "-i", list_path,
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-b:v", "1500k",
        "-maxrate", "1800k",
        "-bufsize", "3000k",
        "-pix_fmt", "yuv420p",
        "-g", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        rtmp_url
    ]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        autostream_tasks[tg_user_id] = process
        await msg.edit_text("📱 **YouTube Shorts Jonli efir muvaffaqiyatli boshlandi!**\n\nBu 24/7 vertikal (9:16) formatda ketaveradi.\nTo'xtatish uchun: `/autostream stop`")
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
