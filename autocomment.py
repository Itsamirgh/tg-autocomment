import asyncio
import json
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id = cfg["api_id"]
api_hash = cfg["api_hash"]
session_name = cfg["session_name"]
channels = cfg["channels"]

client = TelegramClient(session_name, api_id, api_hash)

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

def fake_web_server():
    app = Flask(__name__)

    @app.route('/')
    def index():
        return "🤖 Bot is alive", 200

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

async def run_bot():
    print("🚀 ربات داره لاگین می‌شه…")
    await client.start()
    print("✅ ربات آنلاین و آماده‌ست")
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("🛑 در حال قطع اتصال…")
        await client.disconnect()

if __name__ == "__main__":
    threading.Thread(target=fake_web_server).start()
    asyncio.run(run_bot())
