import asyncio
import json
import os
import re
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiohttp import web

# Load settings
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id       = cfg["api_id"]
api_hash     = cfg["api_hash"]
session_name = cfg["session_name"]
# channels: username -> string or { "messages": [...], "frequency": N }
channels     = cfg["channels"]

client = TelegramClient(session_name, api_id, api_hash)
state = { u: {"count": 0, "index": 0} for u in channels }

# Domain‐like pattern (e.g. example.com, sub.domain.org)
DOMAIN_REGEX = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    username     = event.chat.username.lower()
    text_content = (event.message.message or "").lower()

    # 1) Mentions of other users
    for m in re.findall(r"@([A-Za-z0-9_]+)", text_content):
        if m.lower() != username:
            print(f"🚫 Skipping (mention @{m})")
            return

    # 2) URLs with http/https
    for url in re.findall(r"https?://\S+", text_content):
        if username not in url:
            print(f"🚫 Skipping (URL {url})")
            return

    # 3) Domain‐like tokens (e.g. example.com, instagram.com, t.me)
    for dom in DOMAIN_REGEX.findall(text_content):
        # if domain is exactly your channel’s username + .com etc, allow:
        if dom != f"{username}.com" and dom != f"{username}.ir":
            print(f"🚫 Skipping (domain {dom})")
            return

    # === comment logic ===
    cfg_val = channels[event.chat.username]
    if isinstance(cfg_val, dict):
        messages = cfg_val["messages"]
        freq     = cfg_val.get("frequency", 1)
    else:
        messages = [cfg_val]
        freq     = 1

    st = state[event.chat.username]
    st["count"] += 1
    if st["count"] % freq != 0:
        print(f"⏭ Skipping #{st['count']} (freq={freq})")
        return

    idx = st["index"] % len(messages)
    reply_text = messages[idx]
    st["index"] += 1

    try:
        await asyncio.sleep(1)
        await client.send_message(
            entity=event.chat.username,
            message=reply_text,
            comment_to=event.message.id
        )
        print(f"✅ Commented on {event.chat.username}:{event.message.id}")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ Join the Discussion Group first.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

async def handle_health(request):
    return web.Response(text="OK")

async def main():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"🌐 Health on http://0.0.0.0:{port}/health")

    print("🚀 Bot starting…")
    await client.start()
    print("✅ Bot is online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
