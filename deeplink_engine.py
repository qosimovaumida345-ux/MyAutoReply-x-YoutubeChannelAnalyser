"""
Smart YouTube DeepLink & QR Code Generator Engine.
Mobil ilovada to'g'ridan-to'g'ri ochiluvchi aqlli havolalar (DeepLink) va
yuqori aniqlikdagi skanerlanuvchi QR kodlar yaratish tizimi.
"""

import os
import re
import urllib.parse
import aiohttp
import logging

logger = logging.getLogger(__name__)

def extract_video_or_channel_id(url: str) -> tuple:
    """YouTube havola turini (video yoki kanal) va identifikatorini aniqlash"""
    clean_url = url.strip()
    # Video ID
    v_match = re.search(r"(?:v=|\/shorts\/|\/embed\/|youtu\.be\/|\/v\/)([A-Za-z0-9_-]{11})", clean_url)
    if v_match:
        return "video", v_match.group(1)

    # Channel ID or handle
    c_match = re.search(r"youtube\.com\/(?:channel\/([A-Za-z0-9_-]+)|@([A-Za-z0-9_.-]+))", clean_url)
    if c_match:
        ch_id = c_match.group(1) or f"@{c_match.group(2)}"
        return "channel", ch_id

    return "unknown", clean_url

def generate_smart_deeplinks(target_url: str) -> dict:
    """
    Standart YouTube havolasidan to'g'ridan-to'g'ri YouTube mobil ilovasida
    ochuvchi (in-app browser cheklovlarini aylanib o'tuvchi) DeepLinklar to'plami.
    """
    kind, ident = extract_video_or_channel_id(target_url)

    if kind == "video":
        android_intent = f"intent://www.youtube.com/watch?v={ident}#Intent;package=com.google.android.youtube;scheme=https;end"
        ios_deeplink = f"youtube://watch?v={ident}"
        universal_url = f"https://youtu.be/{ident}"
    elif kind == "channel":
        android_intent = f"intent://www.youtube.com/{ident}#Intent;package=com.google.android.youtube;scheme=https;end"
        ios_deeplink = f"youtube://{ident}"
        universal_url = f"https://www.youtube.com/{ident}"
    else:
        android_intent = target_url
        ios_deeplink = target_url
        universal_url = target_url

    return {
        "type": kind,
        "identifier": ident,
        "android_intent": android_intent,
        "ios_deeplink": ios_deeplink,
        "universal_url": universal_url
    }

async def generate_qr_code_image(data_url: str, output_path: str = "downloads/deeplink_qr.png") -> bool:
    """
    Har qanday URL uchun yuqori aniqlikdagi chiroyli QR kod tasvirini generatsiya qilish.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    encoded = urllib.parse.quote(data_url)
    qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=600x600&margin=15&format=png&data={encoded}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(qr_api_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if len(data) > 1000:
                        with open(output_path, "wb") as f:
                            f.write(data)
                        return True
        return False
    except Exception as e:
        logger.error(f"QR kod yaratishda xato: {e}")
        return False
