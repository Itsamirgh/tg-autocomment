import asyncio
import json
import os
import re
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiohttp import web

# Load and normalize config
with open("config.json", "r", encoding="utf-8") as f:
    raw_cfg = json.load(f)
api_id       = raw_cfg["api_id"]
api_hash     = raw_cfg["api_hash"]
session_name = raw_cfg["session_name"]
channels     = {k.lower(): v for k, v in raw_cfg["channels"].items()}

# Whitelisted external links (substrings)
ALLOWED_LINKS = [
    "t.me/ironetbot",
    "akharinkhabar.ir",
    "t.me/nikotinn_text",
    "proxy?server=",
    "proxy?",
]

client = TelegramClient(session_name, api_id, api_hash)
state  = {k: {"count": 0, "index": 0} for k in channels}

URL_PATTERN = re.compile(r'https?://\S+|\b[\w-]+\.[\w\.-]+\b')

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    msg  = event.message
    raw  = msg.raw_text or ""
    text = raw.lower()
    key  = (event.chat.username or "").lower() or str(event.chat.id)
    print(f"🛠️ Received in {key}: {raw}")

    cfg_val = channels.get(key)
    if not cfg_val:
        print(f"❌ No config for {key}, skipping")
        return

    # === promotional filter via regex ===
    for url in URL_PATTERN.findall(raw):
        ul = url.lower()
        print(f"🔍 Found URL-like text: {url}")
        if key in ul or any(a in ul for a in ALLOWED_LINKS):
            print("✅ URL allowed")
            continue
        print(f"🚫 Skipping due to external link: {url}")
        return

    # === rotation logic ===
    if isinstance(cfg_val, dict):
        messages = cfg_val["messages"]
        freq     = cfg_val.get("frequency", 1)
    else:
        messages = [cfg_val]
        freq     = 1

    st = state[key]
    st["count"] += 1
    print(f"ℹ️ Count={st['count']} (freq={freq})")
    if st["count"] % freq != 0:
        print("⏭ Skipped by frequency")
        return

    idx   = st["index"] % len(messages)
    reply = messages[idx]
    st["index"] += 1

    try:
        await asyncio.sleep(1)
        await client.send_message(
            entity=event.chat.username or event.chat.id,
            message=reply,
            comment_to=msg.id
        )
        print(f"✅ Commented on {key}:{msg.id} -> {reply}")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ Join the discussion group first.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

# Health-check endpoint
async def handle_health(request):
    return web.Response(text="OK")

async def main():
    print("🚀 Bot starting…")
    await client.start()
    print("✅ Bot is online")
    port = int(os.environ.get("PORT", 8080))
    app  = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"🌐 Health on http://0.0.0.0:{port}/health")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
