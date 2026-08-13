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

async def run_mass_engagement(action_type, target_id, users, chat_id, client):
    success = 0
    await client.send_message(chat_id, f"⚙️ {action_type.capitalize()} started for {len(users)} accounts...")
    
    for u in users:
        try:
            creds = Credentials(
                token=u['access_token'],
                refresh_token=u['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=YT_CLIENT_ID,
                client_secret=YT_CLIENT_SECRET
            )
            youtube = build("youtube", "v3", credentials=creds)
            
            if action_type == "like":
                youtube.videos().rate(id=target_id, rating="like").execute()
                
            elif action_type == "comment":
                comment_text = random.choice(COMMENTS_POOL)
                body = {
                    "snippet": {
                        "videoId": target_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": comment_text
                            }
                        }
                    }
                }
                youtube.commentThreads().insert(part="snippet", body=body).execute()
                
            elif action_type == "subscribe":
                sub_body = {
                    "snippet": {
                        "resourceId": {
                            "kind": "youtube#channel",
                            "channelId": target_id
                        }
                    }
                }
                youtube.subscriptions().insert(part="snippet", body=sub_body).execute()
                
            success += 1
            
        except Exception as e:
            print(f"{action_type} failed for {u['tg_user_id']}: {e}")
            
        # RANDOM DELAY to avoid spam detection
        delay = random.randint(30, 120)
        await asyncio.sleep(delay)
        
    await client.send_message(chat_id, f"✅ {action_type.capitalize()} finished! Successfully executed on {success} accounts.")
