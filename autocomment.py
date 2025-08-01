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
# channels: username -> either a string, or { "messages": [...], "frequency": N }
channels     = cfg["channels"]

# Initialize Telegram client
client = TelegramClient(session_name, api_id, api_hash)

# Maintain per-channel state: count of seen posts & current index in messages list
state = {}
for username in channels:
    state[username] = { "count": 0, "index": 0 }

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    username = event.chat.username
    cfg_val = channels[username]

    # determine messages list and frequency
    if isinstance(cfg_val, dict):
        messages = cfg_val.get("messages", [])
        freq     = cfg_val.get("frequency", 1)
    else:
        messages = [cfg_val]
        freq     = 1

    # increment seen counter
    st = state[username]
    st["count"] += 1

    # skip unless this is the Nth post
    if st["count"] % freq != 0:
        return

    # pick next message in rotation
    idx = st["index"] % len(messages)
    text = messages[idx]
    st["index"] += 1

    try:
        await asyncio.sleep(1)  # avoid FloodWait
        await client.send_message(
            entity=event.chat,
            message=text,
            comment_to=event.message.id
        )
        print(f"✅ Commented on {username}:{event.message.id} -> “{text}”")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ Error: join the discussion group first.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

# Health-check endpoint for Render.com / cron-job
async def handle_health(request):
    return web.Response(text="OK")

async def main():
    port = int(os.environ.get("PORT", 8080))
    # start HTTP server
    app = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health on http://0.0.0.0:{port}/health")

    # start Telegram bot
    print("🚀 Bot starting…")
    await client.start()
    print("✅ Bot is online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
