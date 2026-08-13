import asyncio
import random
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import YT_CLIENT_ID, YT_CLIENT_SECRET

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


async def run_mass_engagement(action_type, target_id, users, chat_id, client):
    """
    Mass engagement: like / comment / subscribe
    action_type: "like" | "comment" | "subscribe"
    target_id:   video ID (like/comment uchun) yoki channel ID (subscribe uchun)
    users:       [{"tg_user_id":..., "access_token":..., "refresh_token":...}, ...]
    """
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
            youtube = build("youtube", "v3", credentials=creds)

            # ✅ FIX: Google API sync → asyncio.to_thread orqali chaqirish
            if action_type == "like":
                await asyncio.to_thread(_do_like, youtube, target_id)

            elif action_type == "comment":
                comment_text = random.choice(COMMENTS_POOL)
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