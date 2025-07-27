import asyncio
import json
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError

# Load config
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id = cfg["api_id"]
api_hash = cfg["api_hash"]
session_name = cfg["session_name"]
channels = cfg["channels"]

# Init Telegram client
client = TelegramClient(session_name, api_id, api_hash)

# Create fake web server to keep Render service alive
app = Flask(__name__)

@app.route("/")
def index():
    return "🤖 Bot is running!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Handle new messages
@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    comment_text = channels.get(event.chat.username, "🔥 ممنون از پستت!")
    try:
        await asyncio.sleep(1)
        await client.send_message(
            entity=event.chat,
            message=comment_text,
            comment_to=event.message.id
        )
        print(f"✅ کامنت ثبت شد زیر پست {event.message.id}")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: لطفاً {e.seconds} ثانیه صبر کن…")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ خطا: باید عضو Discussion Group باشی.")
    except Exception as e:
        print(f"❌ خطای ناشناخته: {repr(e)}")

async def start_bot():
    print("🚀 ربات در حال استارت شدنه…")
    await client.start()
    print("✅ ربات متصل شد")
    await client.run_until_disconnected()

# Main entry
if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()
    asyncio.run(start_bot())
