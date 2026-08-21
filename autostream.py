import os
import asyncio
import subprocess
import glob
from database import get_stream_key

# Memory dict to store ffmpeg process for each user
autostream_tasks = {}


async def download_videos(search_query, chat_id, tg_user_id=None, limit=4):
    """
    Search and download ONLY YouTube Shorts (duration <= 60s) using yt-dlp.
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

    # Filter: faqat 65 soniyadan qisqa (Shorts) videolarni olish
    def shorts_filter(info_dict, *, incomplete):
        dur = info_dict.get('duration')
        if dur and dur > 65:
            return "Video davomiyligi 60s dan ko'p (faqat shorts kerak)"
        return None

    ydl_opts = {
        # BUG FIX 1: format — webm ham qabul qilinsin (mp4 bo'lmasa fallback)
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'max_downloads': limit,
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,
        'match_filter': shorts_filter,
        'max_filesize': 50 * 1024 * 1024,  # 50MB (20MB juda kichik edi, ko'p short yuklanmay qolardi)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        # BUG FIX 2: compat_opts list emas SET bo'lishi kerak edi — o'chirildi (eski versiyalarda crash qilardi)
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'merge_output_format': 'mp4',
    }

    if has_cookies:
        ydl_opts['cookiefile'] = cookie_path

    if search_query.startswith("http"):
        url = search_query
    else:
        clean_q = search_query.replace("#shorts", "").replace("shorts", "").strip()
        url = f"ytsearch20:{clean_q} shorts #shorts"

    def _run_ydl():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # BUG FIX 3: info None bo'lishi mumkin edi — crash oldini olish
                if not info:
                    print("[autostream] yt-dlp extract_info None qaytardi")
                    return []

                if 'entries' in info:
                    res = []
                    for e in info.get('entries') or []:
                        if not e:
                            continue
                        try:
                            fn = ydl.prepare_filename(e)
                            # .mp4 ga o'zgartirish (merge bo'lgan bo'lsa)
                            fn_mp4 = os.path.splitext(fn)[0] + '.mp4'
                            if os.path.exists(fn_mp4):
                                res.append(fn_mp4)
                            elif os.path.exists(fn):
                                res.append(fn)
                            else:
                                # glob bilan qidirish
                                vid_id = e.get('id', '')
                                if vid_id:
                                    found = glob.glob(f"{download_dir}/{vid_id}.*")
                                    if found:
                                        res.append(found[0])
                        except Exception as ex:
                            print(f"[autostream] entry filename error: {ex}")
                    return res
                else:
                    fn = ydl.prepare_filename(info)
                    fn_mp4 = os.path.splitext(fn)[0] + '.mp4'
                    if os.path.exists(fn_mp4):
                        return [fn_mp4]
                    elif os.path.exists(fn):
                        return [fn]
                    else:
                        vid_id = info.get('id', '')
                        if vid_id:
                            found = glob.glob(f"{download_dir}/{vid_id}.*")
                            return found if found else []
                    return []

        except yt_dlp.utils.MaxDownloadsReached:
            # Bu normal — limit ga yetdi
            pass
        except Exception as e:
            print(f"[autostream] yt-dlp download error: {e}")
            return []

        # Agar MaxDownloadsReached bo'lsa, papkadagi fayllarni qaytarish
        try:
            all_files = glob.glob(f"{download_dir}/*.mp4") + glob.glob(f"{download_dir}/*.webm")
            return all_files[:limit]
        except Exception:
            return []

    try:
        paths = await asyncio.to_thread(_run_ydl)
    finally:
        if has_cookies and os.path.exists(cookie_path):
            try:
                os.remove(cookie_path)
            except:
                pass

    # Verify files exist va bo'sh emasligini tekshirish
    valid_paths = [p for p in (paths or []) if os.path.exists(p) and os.path.getsize(p) > 1000]
    print(f"[autostream] Topilgan valid fayllar: {len(valid_paths)} ta — {valid_paths}")
    return valid_paths


async def start_autostream(tg_user_id, search_query, client, chat_id):
    """
    1. Stream key tekshirish
    2. Shorts videolarni yuklab olish
    3. concat list yaratish
    4. FFmpeg ni 9:16 Vertical Shorts formatda ishga tushirish
    """
    if tg_user_id in autostream_tasks:
        proc = autostream_tasks[tg_user_id]
        # BUG FIX 4: o'lik process bo'lsa tozalash
        if proc.poll() is not None:
            del autostream_tasks[tg_user_id]
        else:
            await client.send_message(chat_id, "⚠️ Sizda allaqachon bitta translatsiya ketyapti! Avval uni to'xtating: `/autostream stop`")
            return

    stream_key = get_stream_key(tg_user_id)
    if not stream_key:
        await client.send_message(
            chat_id,
            "❌ Sizda Stream Key o'rnatilmagan!\n\n"
            "YouTube Studio → Go Live → Stream Settings dan Stream Key ni oling va:\n"
            "`/setstreamkey <key>` orqali kiriting."
        )
        return

    msg = await client.send_message(
        chat_id,
        f"🔍 Kuting, '{search_query}' bo'yicha **YouTube Shorts** videolari qidirilyapti va yuklanyapti..."
    )

    video_paths = await download_videos(search_query, chat_id, tg_user_id=tg_user_id, limit=4)

    if not video_paths:
        await msg.edit_text(
            "❌ Hech qanday mos Shorts video topilmadi yoki yuklashda xatolik yuz berdi.\n\n"
            "Maslahat: Boshqa qidiruv so'zi bilan urinib ko'ring yoki /setcookies orqali cookies qo'shing."
        )
        return

    await msg.edit_text(
        f"✅ {len(video_paths)} ta Shorts video tayyorlandi.\n"
        f"📱 **9:16 Vertical Shorts Live Stream** boshlanmoqda..."
    )

    # filelist.txt yaratish
    list_path = f"/tmp/autostream_{chat_id}/filelist.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in video_paths:
            # FFmpeg uchun path escape
            safe_path = p.replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe_path}'\n")

    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

    # BUG FIX 5: log fayl — FFmpeg xatolarini ko'rish uchun
    log_path = f"/tmp/autostream_{chat_id}/ffmpeg.log"

    cmd = [
        "ffmpeg", "-y", "-re",
        "-f", "concat",
        "-safe", "0",
        "-stream_loop", "-1",
        "-i", list_path,
        # 9:16 vertical format (YouTube Shorts)
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
        # BUG FIX 6: flv format RTMP uchun to'g'ri
        "-f", "flv",
        rtmp_url
    ]

    try:
        log_file = open(log_path, "w")
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file  # BUG FIX 7: DEVNULL emas — log faylga yozilsin
        )

        # BUG FIX 8: FFmpeg darhol o'lganini tekshirish (3 soniya kuting)
        await asyncio.sleep(3)
        if process.poll() is not None:
            log_file.close()
            # Log faylni o'qib xatoni ko'rish
            error_text = ""
            try:
                with open(log_path, "r") as lf:
                    lines = lf.readlines()
                    # Oxirgi 10 qator
                    error_text = "".join(lines[-10:])
            except:
                pass
            await msg.edit_text(
                f"❌ FFmpeg ishga tushmadi!\n\n"
                f"Xato:\n`{error_text[-300:] if error_text else 'Log topilmadi'}`\n\n"
                f"Stream Key to'g'riligini tekshiring."
            )
            return

        autostream_tasks[tg_user_id] = process
        await msg.edit_text(
            "📱 **YouTube Shorts Jonli efir muvaffaqiyatli boshlandi!**\n\n"
            "✅ 9:16 vertikal format\n"
            "✅ 24/7 davomli (loop)\n\n"
            "To'xtatish uchun: `/autostream stop`\n"
            "Holat tekshirish: `/autostream status`"
        )
    except FileNotFoundError:
        await msg.edit_text(
            "❌ FFmpeg topilmadi! Render serverida ffmpeg o'rnatilgan ekanligini tekshiring.\n"
            "Dockerfile ga `RUN apt-get install -y ffmpeg` qo'shing."
        )
    except Exception as e:
        await msg.edit_text(f"❌ Translatsiyani boshlashda xatolik: {e}")


async def stop_autostream(tg_user_id, client, chat_id):
    """FFmpeg jarayonini to'xtatish"""
    if tg_user_id not in autostream_tasks:
        await client.send_message(chat_id, "❌ Sizda hozir hech qanday translatsiya ketmayapti.")
        return

    process = autostream_tasks[tg_user_id]
    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    except Exception as e:
        print(f"[autostream] stop error: {e}")

    del autostream_tasks[tg_user_id]

    # Vaqtinchalik fayllarni tozalash
    import shutil
    try:
        shutil.rmtree(f"/tmp/autostream_{chat_id}", ignore_errors=True)
    except:
        pass

    await client.send_message(chat_id, "🛑 Translatsiya to'xtatildi va vaqtinchalik fayllar tozalandi.")


def get_autostream_status(tg_user_id):
    if tg_user_id not in autostream_tasks:
        return "To'xtagan 🔴"

    process = autostream_tasks[tg_user_id]
    ret = process.poll()
    if ret is None:
        return "Ketyapti 🟢"
    else:
        del autostream_tasks[tg_user_id]
        return f"To'xtagan 🔴 (Jarayon o'z-o'zidan yopilgan, exit code: {ret})"