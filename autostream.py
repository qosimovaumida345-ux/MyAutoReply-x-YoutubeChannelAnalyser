import os
import asyncio
import subprocess
import glob
import shutil
from database import get_stream_key

# Har bir user uchun ffmpeg process saqlanadi
autostream_tasks = {}


def resolve_url(query: str) -> str:
    """
    @username yoki kanal nomi → YouTube Shorts playlist URL ga aylantirish.
    Aks holda matn qidiruv URLi qaytaradi.
    """
    q = query.strip()

    # --- Kanal username yoki URL bo'lsa ---
    # /autostream start @HisYTStory  →  https://www.youtube.com/@HisYTStory/shorts
    # /autostream start HisYTStory   →  ytsearch20 orqali qidirish
    # /autostream start https://...  →  to'g'ridan-to'g'ri
    if q.startswith("http://") or q.startswith("https://"):
        # Kanal URL → /shorts qo'shamiz
        if "/shorts" not in q:
            q = q.rstrip("/") + "/shorts"
        return q

    if q.startswith("@"):
        # @Username → kanal Shorts sahifasi
        username = q  # @ belgisi saqlanadi
        return f"https://www.youtube.com/{username}/shorts"

    # Oddiy matn qidiruv
    clean_q = q.replace("#shorts", "").replace("shorts", "").strip()
    return f"ytsearch20:{clean_q} #shorts"


async def download_videos(search_query, chat_id, tg_user_id=None, limit=6):
    """
    Berilgan query bo'yicha YouTube Shorts videolarini yuklab oladi.
    @username yoki kanal URL berilsa o'sha kanalning Shorts videolarini oladi.
    Live stream videolarni o'tkazib yuboradi.
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

    url = resolve_url(search_query)
    is_channel = search_query.strip().startswith("@") or \
                 "youtube.com/@" in search_query or \
                 "youtube.com/c/" in search_query or \
                 "youtube.com/channel/" in search_query

    print(f"[autostream] URL: {url} | is_channel: {is_channel}")

    # Shorts filter — live streamlarni va uzun videolarni bloklash
    def shorts_filter(info_dict, *, incomplete):
        # Live streamni bloklash
        if info_dict.get('is_live') or info_dict.get('live_status') in ('is_live', 'is_upcoming'):
            return "Bu live stream — o'tkazib yuborildi"
        dur = info_dict.get('duration')
        # Duration aniqlanmagan va live emas bo'lsa ham bloklash (ehtiyot uchun)
        if dur is None and not incomplete:
            return "Duration aniqlanmadi — o'tkazib yuborildi"
        if info_dict.get('is_live') or info_dict.get('live_status') == 'is_live':
            return "Live stream — skip"
        if dur and dur > 180:
            return "3 daqiqadan uzun — skip"    
        return None

    ydl_opts = {
        'format': (
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]'
            '/bestvideo[height<=720]+bestaudio'
            '/best[height<=720]'
            '/best'
        ),
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'max_downloads': limit,
        'quiet': False,
        'no_warnings': False,
        'noplaylist': False,       # kanal playlist uchun True emas
        'match_filter': shorts_filter,
        'max_filesize': 50 * 1024 * 1024,  # 50MB
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'merge_output_format': 'mp4',
        'ignoreerrors': True,       # bitta video xato bo'lsa davom etsin
    }

    # Kanal URL bo'lsa playlist sifatida yuklaymiz
    if is_channel:
        ydl_opts['playlistend'] = limit
        ydl_opts.pop('max_downloads', None)

    if has_cookies:
        ydl_opts['cookiefile'] = cookie_path

    def _run_ydl():
        collected = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    print("[autostream] extract_info None qaytardi")
                    return []

                entries = info.get('entries') if 'entries' in info else [info]

                for e in (entries or []):
                    if not e:
                        continue
                    vid_id = e.get('id', '')
                    if not vid_id:
                        continue
                    # Fayl izlash
                    try:
                        fn = ydl.prepare_filename(e)
                        fn_mp4 = os.path.splitext(fn)[0] + '.mp4'
                        if os.path.exists(fn_mp4) and os.path.getsize(fn_mp4) > 5000:
                            collected.append(fn_mp4)
                            continue
                        if os.path.exists(fn) and os.path.getsize(fn) > 5000:
                            collected.append(fn)
                            continue
                    except Exception:
                        pass
                    # glob bilan qidirish
                    found = glob.glob(f"{download_dir}/{vid_id}.*")
                    for f in found:
                        if os.path.getsize(f) > 5000:
                            collected.append(f)
                            break

        except yt_dlp.utils.MaxDownloadsReached:
            pass  # normal — limitga yetdi
        except Exception as ex:
            print(f"[autostream] yt-dlp error: {ex}")

        # Agar yuqorida hech narsa topilmasa — papkani skan qilamiz
        if not collected:
            all_files = glob.glob(f"{download_dir}/*.mp4") + \
                        glob.glob(f"{download_dir}/*.webm") + \
                        glob.glob(f"{download_dir}/*.mkv")
            collected = [f for f in all_files
                         if os.path.getsize(f) > 5000 and 'cookies' not in f]

        print(f"[autostream] Yuklangan fayllar: {len(collected)} ta")
        return collected[:limit]

    try:
        paths = await asyncio.to_thread(_run_ydl)
    finally:
        if has_cookies and os.path.exists(cookie_path):
            try:
                os.remove(cookie_path)
            except Exception:
                pass

    valid = [p for p in (paths or []) if os.path.exists(p) and os.path.getsize(p) > 5000]
    print(f"[autostream] Valid fayllar: {valid}")
    return valid


async def start_autostream(tg_user_id, search_query, client, chat_id):
    """
    1. Stream key tekshirish
    2. Shorts videolarni yuklab olish (@username yoki kanal URL yoki matn)
    3. FFmpeg loop stream → YouTube RTMP
    """
    # O'lik process ni tozalash
    if tg_user_id in autostream_tasks:
        proc = autostream_tasks[tg_user_id]
        if proc.poll() is not None:
            del autostream_tasks[tg_user_id]
        else:
            await client.send_message(
                chat_id,
                "⚠️ Sizda allaqachon bitta translatsiya ketyapti!\n"
                "Avval to'xtating: `/autostream stop`"
            )
            return

    stream_key = get_stream_key(tg_user_id)
    if not stream_key:
        await client.send_message(
            chat_id,
            "❌ Stream Key o'rnatilmagan!\n\n"
            "YouTube Studio → Go Live → Stream Settings → Stream Key\n"
            "Keyin: `/setstreamkey <key>`"
        )
        return

    q = search_query.strip()
    if q.startswith("@"):
        info_msg = f"🔍 **{q}** kanalining Shorts videolari yuklanmoqda..."
    else:
        info_msg = f"🔍 **'{q}'** bo'yicha Shorts videolari qidirilyapti..."

    msg = await client.send_message(chat_id, info_msg)

    video_paths = await download_videos(q, chat_id, tg_user_id=tg_user_id, limit=6)

    if not video_paths:
        await msg.edit_text(
            "❌ Hech qanday Shorts video topilmadi!\n\n"
            "Maslahatlar:\n"
            "• `@Username` to'g'riligini tekshiring\n"
            "• Kaналda Shorts videolar borligini tekshiring\n"
            "• `/setcookies` orqali cookie qo'shing"
        )
        return

    await msg.edit_text(
        f"✅ {len(video_paths)} ta Shorts video tayyorlandi.\n"
        f"📡 YouTube Live Stream boshlanmoqda..."
    )

    # filelist.txt yaratish (FFmpeg concat uchun)
    list_path = f"/tmp/autostream_{chat_id}/filelist.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in video_paths:
            safe = p.replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe}'\n")

    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    log_path = f"/tmp/autostream_{chat_id}/ffmpeg.log"

    cmd = [
        "ffmpeg", "-y", "-re",
        "-f", "concat",
        "-safe", "0",
        "-stream_loop", "-1",
        "-i", list_path,
        # 9:16 vertical (YouTube Shorts)
        "-vf", (
            "scale=720:1280:force_original_aspect_ratio=decrease,"
            "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,"
            "setsar=1"
        ),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-b:v", "1500k",
        "-maxrate", "1800k",
        "-bufsize", "3000k",
        "-pix_fmt", "yuv420p",
        "-g", "60",
        "-keyint_min", "60",
        "-sc_threshold", "0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-f", "flv",
        rtmp_url
    ]

    try:
        log_file = open(log_path, "w")
        process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)

        # 3 soniya kuting — FFmpeg darhol o'lganini bilish uchun
        await asyncio.sleep(3)
        if process.poll() is not None:
            log_file.close()
            err = ""
            try:
                with open(log_path, "r") as lf:
                    lines = lf.readlines()
                    err = "".join(lines[-15:])
            except Exception:
                pass
            await msg.edit_text(
                f"❌ FFmpeg ishga tushmadi!\n\n"
                f"```\n{err[-400:] if err else 'Log topilmadi'}\n```\n\n"
                f"Stream Key to'g'riligini tekshiring."
            )
            return

        autostream_tasks[tg_user_id] = process
        await msg.edit_text(
            "📱 **Jonli efir muvaffaqiyatli boshlandi!**\n\n"
            f"📺 Manba: `{q}`\n"
            f"🎬 {len(video_paths)} ta video loop qilinmoqda\n"
            f"📐 Format: 9:16 vertikal (Shorts)\n\n"
            "To'xtatish: `/autostream stop`\n"
            "Holat: `/autostream status`"
        )

    except FileNotFoundError:
        await msg.edit_text(
            "❌ FFmpeg topilmadi!\n"
            "Dockerfile ga qo'shing:\n"
            "`RUN apt-get install -y ffmpeg`"
        )
    except Exception as ex:
        await msg.edit_text(f"❌ Xatolik: {ex}")


async def stop_autostream(tg_user_id, client, chat_id):
    if tg_user_id not in autostream_tasks:
        await client.send_message(chat_id, "❌ Hozir hech qanday translatsiya ketmayapti.")
        return

    process = autostream_tasks[tg_user_id]
    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    except Exception as ex:
        print(f"[autostream] stop error: {ex}")

    del autostream_tasks[tg_user_id]

    try:
        shutil.rmtree(f"/tmp/autostream_{chat_id}", ignore_errors=True)
    except Exception:
        pass

    await client.send_message(chat_id, "🛑 Translatsiya to'xtatildi. Fayllar tozalandi.")


def get_autostream_status(tg_user_id):
    if tg_user_id not in autostream_tasks:
        return "To'xtagan 🔴"
    process = autostream_tasks[tg_user_id]
    if process.poll() is None:
        return "Ketyapti 🟢"
    del autostream_tasks[tg_user_id]
    return f"To'xtagan 🔴 (exit code: {process.returncode})"

# ==================== STREAMER WORKER LOOP ====================

async def run_streamer_queue(port=3000):
    """
    ROLE=streamer uchun:
    DB dagi 'pending' stream tasklerini oladi va bajaradi.
    Agar 2 ta odam bir vaqtda stream qilsa — 2 ta streamer instance
    har biri alohida task olib ishlaydi (SKIP LOCKED bilan).
    """
    import asyncio
    import os
    import subprocess
    from database import (
        claim_pending_stream_task, update_stream_task,
        cancel_user_stream_tasks, get_user_stream_status
    )

    worker_id = f"streamer_{os.getpid()}"
    print(f"📡 [{worker_id}] Stream queue worker poylamoqda...")

    # Bot client — foydalanuvchiga xabar yuborish uchun
    bot_client = None
    try:
        from pyrogram import Client
        from config import API_ID, API_HASH, BOT_TOKEN
        if BOT_TOKEN and API_ID and API_HASH:
            bot_client = Client(
                f"streamer_bot_{os.getpid()}",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True
            )
            await bot_client.start()
            print(f"✅ [{worker_id}] Bot client tayyor")
    except Exception as e:
        print(f"⚠️ [{worker_id}] Bot client ishga tushmadi: {e}")
        bot_client = None

    current_task_id = None
    current_proc    = None

    async def safe_msg(chat_id, text):
        if bot_client:
            try:
                await bot_client.send_message(chat_id, text)
            except Exception as ex:
                print(f"[{worker_id}] xabar yuborish xatosi: {ex}")

    while True:
        try:
            # Avval joriy task bekor qilinganmi — tekshir
            if current_task_id is not None and current_proc is not None:
                from database import get_db
                import psycopg2.extras
                conn_check = get_db()
                if conn_check:
                    try:
                        cur_check = conn_check.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                        cur_check.execute(
                            "SELECT status FROM stream_tasks WHERE id=%s",
                            (current_task_id,)
                        )
                        row = cur_check.fetchone()
                        if row and row['status'] == 'cancelled':
                            # Stop current ffmpeg
                            try:
                                current_proc.terminate()
                                current_proc.wait(timeout=5)
                            except Exception:
                                try: current_proc.kill()
                                except: pass
                            current_task_id = None
                            current_proc    = None
                            print(f"[{worker_id}] Joriy stream bekor qilindi")
                    except Exception as e:
                        print(f"[{worker_id}] cancel check xato: {e}")
                    finally:
                        conn_check.close()

            # Agar hozir band bo'lmasak — yangi task ol
            if current_task_id is None:
                task = claim_pending_stream_task(worker_id)
                if task:
                    task_id      = task['id']
                    tg_user_id   = task['tg_user_id']
                    chat_id      = task['chat_id']
                    search_query = task['search_query']
                    stream_key   = task['stream_key']

                    current_task_id = task_id
                    print(f"📥 [{worker_id}] Stream task #{task_id} olindi: '{search_query}'")

                    await safe_msg(
                        chat_id,
                        f"🔍 **'{search_query}'** bo'yicha Shorts videolari yuklanmoqda..."
                    )

                    try:
                        # 1. Videolarni yuklab olish
                        video_paths = await download_videos(
                            search_query, chat_id,
                            tg_user_id=tg_user_id, limit=6
                        )

                        if not video_paths:
                            await safe_msg(
                                chat_id,
                                "❌ Hech qanday Shorts video topilmadi!\n"
                                "• `@Username` to'g'riligini tekshiring\n"
                                "• `/setcookies` orqali cookie qo'shing"
                            )
                            update_stream_task(task_id, 'failed')
                            current_task_id = None
                            current_proc    = None
                        else:
                            # 2. filelist.txt yaratish
                            import tempfile
                            tmpdir = f"/tmp/autostream_{chat_id}"
                            os.makedirs(tmpdir, exist_ok=True)
                            list_path = f"{tmpdir}/filelist.txt"
                            with open(list_path, "w", encoding="utf-8") as f:
                                for p in video_paths:
                                    safe_p = p.replace("\\", "/").replace("'", "\\'")
                                    f.write(f"file '{safe_p}'\n")

                            rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
                            log_path = f"{tmpdir}/ffmpeg.log"

                            cmd = [
                                "ffmpeg", "-y", "-re",
                                "-f", "concat", "-safe", "0",
                                "-stream_loop", "-1", "-i", list_path,
                                "-vf", (
                                    "scale=720:1280:force_original_aspect_ratio=decrease,"
                                    "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
                                ),
                                "-c:v", "libx264", "-preset", "ultrafast",
                                "-tune", "zerolatency",
                                "-b:v", "1500k", "-maxrate", "1800k", "-bufsize", "3000k",
                                "-pix_fmt", "yuv420p", "-g", "60",
                                "-keyint_min", "60", "-sc_threshold", "0",
                                "-c:a", "aac", "-b:a", "128k",
                                "-ar", "44100", "-ac", "2",
                                "-f", "flv", rtmp_url
                            ]

                            log_file = open(log_path, "w")
                            proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)

                            # 3 soniya kut — FFmpeg darhol o'lganini bilish uchun
                            await asyncio.sleep(3)
                            if proc.poll() is not None:
                                log_file.close()
                                err = ""
                                try:
                                    with open(log_path, "r") as lf:
                                        err = "".join(lf.readlines()[-15:])
                                except Exception:
                                    pass
                                await safe_msg(
                                    chat_id,
                                    f"❌ FFmpeg ishga tushmadi!\n```\n{err[-300:]}\n```"
                                )
                                update_stream_task(task_id, 'failed')
                                current_task_id = None
                                current_proc    = None
                            else:
                                # Muvaffaqiyatli boshlandi
                                autostream_tasks[tg_user_id] = proc
                                current_proc = proc
                                update_stream_task(task_id, 'running')
                                await safe_msg(
                                    chat_id,
                                    f"📱 **Jonli efir muvaffaqiyatli boshlandi!**\n\n"
                                    f"📺 Manba: `{search_query}`\n"
                                    f"🎬 {len(video_paths)} ta video loop\n"
                                    f"📐 Format: 9:16 vertikal\n\n"
                                    "To'xtatish: `/autostream stop`"
                                )

                    except Exception as e:
                        await safe_msg(chat_id, f"❌ Stream xatosi: {e}")
                        update_stream_task(task_id, 'failed')
                        current_task_id = None
                        current_proc    = None

            else:
                # Hozir task bor — FFmpeg tirik ekanini tekshir
                if current_proc and current_proc.poll() is not None:
                    # FFmpeg o'chib qoldi
                    print(f"[{worker_id}] FFmpeg to'xtadi (task #{current_task_id})")
                    update_stream_task(current_task_id, 'completed')
                    # autostream_tasks dan o'chirish
                    keys_to_del = [k for k, v in autostream_tasks.items() if v == current_proc]
                    for k in keys_to_del:
                        del autostream_tasks[k]
                    current_task_id = None
                    current_proc    = None

            await asyncio.sleep(5)

        except Exception as e:
            print(f"❌ [{worker_id}] Streamer loop xatosi: {e}")
            await asyncio.sleep(10)