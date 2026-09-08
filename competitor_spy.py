"""
YouTube Competitor Spy & SEO Stealer Engine.
Ixtiyoriy YouTube video havolasidan yashirin teglarni (tags/keywords), metama'lumotlarni
ko'chirib olish va Gemini AI orqali raqobatchidan o'zib ketuvchi CTR sarlavhalar va SEO tavsiyalar berish.
"""

import asyncio
import logging
import yt_dlp
from config import generate_with_fallback_async

logger = logging.getLogger(__name__)

def extract_competitor_metadata(video_url: str) -> dict:
    """
    yt-dlp orqali videoning barcha yashirin teglari va statistikasini olish.
    Agar kanal URL berilsa, kanalning eng so'nggi Shorts yoki videosini avtomatik tahlil qiladi.
    """
    clean_url = video_url.strip()
    
    # Agar kanal URL bo'lsa (@username yoki /channel/), eng oxirgi videoni olamiz
    if "/@" in clean_url or "/channel/" in clean_url or "/c/" in clean_url or clean_url.startswith("@"):
        if clean_url.startswith("@"):
            clean_url = f"https://www.youtube.com/{clean_url}"
        
        target_candidates = [
            f"{clean_url.rstrip('/')}/shorts",
            f"{clean_url.rstrip('/')}/videos",
            clean_url
        ]
        found_video_url = None
        for cand in target_candidates:
            try:
                ydl_channel_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": "in_playlist",
                    "playlist_items": "1-3",
                    "skip_download": True
                }
                with yt_dlp.YoutubeDL(ydl_channel_opts) as ydl:
                    info_ch = ydl.extract_info(cand, download=False)
                    entries = info_ch.get("entries") or []
                    for e in entries:
                        vid_id = e.get("id") or e.get("url")
                        if vid_id and len(str(vid_id)) == 11:
                            found_video_url = f"https://www.youtube.com/watch?v={vid_id}"
                            break
                        elif e.get("url") and ("watch" in e.get("url") or "shorts" in e.get("url")):
                            found_video_url = e["url"]
                            break
                if found_video_url:
                    clean_url = found_video_url
                    break
            except Exception:
                continue

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            if not info:
                raise ValueError("Video ma'lumotlarini yuklab bo'lmadi.")
            
            # Agar hali ham playlist bo'lsa, birinchi elementni olamiz
            if "entries" in info:
                entries = [e for e in info.get("entries", []) if e]
                if entries:
                    info = entries[0]

            return {
                "title": info.get("title", ""),
                "channel": info.get("uploader") or info.get("channel", ""),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "duration": info.get("duration", 0),
                "tags": info.get("tags") or [],
                "categories": info.get("categories") or [],
                "description": info.get("description", "")[:1000],
                "video_url": clean_url
            }
    except Exception as err:
        logger.error(f"extract_competitor_metadata error for {clean_url}: {err}")
        raise ValueError(
            "YouTube videosini aniqlab bo'lmadi! "
            "Iltimos, aniq video yoki Shorts havolasini yuboring (Masalan: https://youtube.com/watch?v=... yoki https://youtube.com/shorts/...)"
        )

async def analyze_and_steal_seo(video_url: str, lang: str = "uz") -> dict:
    """
    Raqobatchi videosini tahlil qilish va uni yengish uchun optimallashtirilgan
    3 ta yuqori CTR sarlavha, 20 ta kalit so'z va tavsiyalar generatsiya qilish.
    """
    meta = await asyncio.to_thread(extract_competitor_metadata, video_url)
    tags_str = ", ".join(meta["tags"]) if meta["tags"] else "Yashirin teglar topilmadi (umumiy SEO ishlatilgan)"

    prompt = f"""
Sen YouTube SEO va Algoritm bo'yicha eng kuchli mutaxassisisan.
Quyida raqobatchining muvaffaqiyatli videosi ma'lumotlari berilgan:

🎬 Sarlavha: {meta['title']}
👤 Kanal: {meta['channel']}
👁 Ko'rishlar: {meta['view_count']:,}
🏷 Raqobatchi ishlatgan yashirin teglar: {tags_str}
📝 Tavsifdan parcha: {meta['description'][:300]}

Vazifang foydalanuvchiga '{lang}' tilida ushbu raqobatchidan o'zib ketish uchun tayyor professional SEO to'plamini berish:
1. Ushbu video nima sababdan ko'p ko'rilgani bo'yicha qisqa tahlil (1-2 gap).
2. Raqobatchinikidan ancha kuchli, CTR yuqori 3 xil muqobil SARLAVHA.
3. YouTube qidiruvida 1-o'ringa chiqish uchun 20 ta eng sara TEG (virgul bilan ajratilgan tayyor nusxalash uchun).
4. Tavsif (description) uchun optimallashgan 3 ta hashtag va maslahat.
"""
    try:
        res = await generate_with_fallback_async(prompt)
        ai_analysis = res.text.strip()
    except Exception as e:
        ai_analysis = "AI tahlili vaqtida xatolik yuz berdi."

    return {
        "meta": meta,
        "ai_analysis": ai_analysis
    }
