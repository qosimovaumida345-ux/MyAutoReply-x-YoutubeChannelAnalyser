import asyncio
import random
import re
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from config import YT_CLIENT_ID, YT_CLIENT_SECRET, get_gemini_key
from database import update_yt_tokens

COMMENTS_POOL = [
    "This is absolutely amazing! Keep up the great work 🔥",
    "Wow, I didn't expect this. Mind blown! 🤯",
    "Great content as always!",
    "This is exactly what I was looking for, thanks!",
    "So helpful and well explained. Loved it!",
    "Can't wait to see more videos like this. 👏",
    "The editing on this is top notch!",
    "Really interesting perspective, never thought of it this way.",
    "This made my day, thank you! 😊",
    "Subscribed! Looking forward to your next upload.",
    "Brilliant video! Super informative.",
    "I've shared this with all my friends. Great job!",
    "Quality content right here.",
    "I appreciate the effort you put into this.",
    "This is so underrated! Deserves way more views.",
    "Legendary video right here.",
    "I learned so much from this, thanks for sharing.",
    "Honestly, one of the best channels on this platform.",
    "Keep grinding! Your content is getting better and better.",
    "This deserves a million likes! ❤️"
]

for i in range(80):
    COMMENTS_POOL.append(f"Amazing stuff! Really enjoyed it. {'🔥' * random.randint(1,3)}")


def _do_like(youtube, video_id):
    """Sync: video layk qilish"""
    youtube.videos().rate(id=video_id, rating="like").execute()


def _do_comment(youtube, video_id, text):
    """Sync: comment yozish"""
    youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {"textOriginal": text}
                }
            }
        }
    ).execute()


def _do_subscribe(youtube, channel_id):
    """Sync: kanalga obuna bo'lish"""
    youtube.subscriptions().insert(
        part="snippet",
        body={
            "snippet": {
                "resourceId": {
                    "kind": "youtube#channel",
                    "channelId": channel_id
                }
            }
        }
    ).execute()


async def generate_gemini_comment(video_title):
    try:
        genai.configure(api_key=get_gemini_key())
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Write a short, engaging, and highly relevant YouTube comment for a video titled '{video_title}'. Do not use quotes or introductory text, just return the comment itself. Include a relevant emoji."
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        # Clean up any surrounding quotes if generated
        text = text.strip('"\'')
        if text:
            return text
    except Exception as e:
        print(f"Gemini comment error: {e}")
    return random.choice(COMMENTS_POOL)

def extract_video_id(url_or_id):
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url_or_id)
        if match:
            return match.group(1)
    return url_or_id

async def run_mass_engagement(action_type, target_url_or_id, users, chat_id, client):
    """
    Mass engagement: like / comment / subscribe
    action_type: "like" | "comment" | "subscribe"
    target_url_or_id:   video ID/URL (like/comment uchun) yoki channel ID (subscribe uchun)
    users:       [{"tg_user_id":..., "yt_channel_id":..., "access_token":..., "refresh_token":...}, ...]
    """
    target_id = extract_video_id(target_url_or_id)
    success = 0
    failed  = 0
    total   = len(users)

    await client.send_message(
        chat_id,
        f"⚙️ `{action_type.upper()} boshlandi — {total} ta account...`"
    )

    for i, u in enumerate(users, 1):
        try:
            # ✅ FIX: Credentials to'g'ri tuzildi
            creds = Credentials(
                token=u['access_token'],
                refresh_token=u['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=YT_CLIENT_ID,
                client_secret=YT_CLIENT_SECRET
            )
            # Token expired or close to expiry check
            if creds.expired or creds.expiry is None:
                try:
                    await asyncio.to_thread(creds.refresh, Request())
                    update_yt_tokens(u['tg_user_id'], u['yt_channel_id'], creds.token)
                except Exception as e:
                    print(f"[mass_engagement] Token refresh failed for {u.get('tg_user_id')}: {e}")

            youtube = build("youtube", "v3", credentials=creds)

            # ✅ FIX: Google API sync → asyncio.to_thread orqali chaqirish
            if action_type == "like":
                await asyncio.to_thread(_do_like, youtube, target_id)

            elif action_type == "comment":
                # Fetch video title to generate relevant comment
                video_title = "awesome video"
                try:
                    res = await asyncio.to_thread(youtube.videos().list, part="snippet", id=target_id)
                    res_data = res.execute()
                    if res_data.get("items"):
                        video_title = res_data["items"][0]["snippet"]["title"]
                except Exception as e:
                    pass
                
                comment_text = await generate_gemini_comment(video_title)
                await asyncio.to_thread(_do_comment, youtube, target_id, comment_text)

            elif action_type == "subscribe":
                await asyncio.to_thread(_do_subscribe, youtube, target_id)

            success += 1
            print(f"[mass_engagement] ✅ [{i}/{total}] {action_type} — tg={u.get('tg_user_id')}")

        except Exception as e:
            failed += 1
            err = str(e)
            # ✅ FIX: quota exceeded ni alohida ushlash
            if "quotaExceeded" in err:
                print(f"[mass_engagement] ⚠️ Quota tugadi — {u.get('tg_user_id')}")
                await client.send_message(chat_id, f"⚠️ `Quota tugadi, keyingi accountga o'tildi`")
            elif "forbidden" in err.lower():
                print(f"[mass_engagement] 🚫 Ruxsat yo'q — {u.get('tg_user_id')}: {err[:80]}")
            else:
                print(f"[mass_engagement] ❌ {action_type} xato — {u.get('tg_user_id')}: {err[:100]}")

        # ✅ Random delay — spam detection dan saqlanish
        delay = random.randint(25, 90)
        await asyncio.sleep(delay)

    # Yakuniy natija
    emoji = "✅" if failed == 0 else "⚠️"
    await client.send_message(
        chat_id,
        f"{emoji} `{action_type.upper()} tugadi!`\n\n"
        f"✅ Muvaffaqiyatli: `{success}/{total}`\n"
        f"❌ Xato: `{failed}/{total}`"
    )
    return {"success": success, "failed": failed, "total": total}