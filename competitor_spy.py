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
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return {
            "title": info.get("title", ""),
            "channel": info.get("uploader") or info.get("channel", ""),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "duration": info.get("duration", 0),
            "tags": info.get("tags") or [],
            "categories": info.get("categories") or [],
            "description": info.get("description", "")[:1000]
        }

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
