import asyncio
import json
import os
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiohttp import web

# Load settings
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id       = cfg["api_id"]
api_hash     = cfg["api_hash"]
session_name = cfg["session_name"]
channels     = cfg["channels"]  # dict: username -> comment text

# Initialize Telegram client
client = TelegramClient(session_name, api_id, api_hash)

# Handler for new channel posts
@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    comment_text = channels.get(event.chat.username, "🚶‍♂️🚶‍♂️🚶‍♂️🚶‍♂️")
    try:
        await asyncio.sleep(1)  # جلوگیری از FloodWait
        await client.send_message(
            entity=event.chat,
            message=comment_text,
            comment_to=event.message.id  # کامنت توی Discussion
        )
        print(f"✅ کامنت ثبت شد زیر پست {event.chat.username}:{event.message.id}")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: لطفاً {e.seconds} ثانیه صبر کن…")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ خطا: باید عضو Discussion Group باشی.")
    except Exception as e:
        print(f"❌ خطای ناشناخته: {e}")

# Health-check endpoint
async def handle_health(request):
    return web.Response(text="OK")

async def main():
    # Determine port from environment (for Render.com compatibility)
    port = int(os.environ.get("PORT", 8080))

    # Start HTTP health-check server
    app = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health endpoint running on http://0.0.0.0:{port}/health")

    # Start Telegram client
    print("🚀 ربات داره لاگین می‌شه…")
    await client.start()
    print("✅ ربات آنلاین و آماده‌ست")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
