import asyncio
import json
import os
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageEntityUrl,
    MessageEntityTextUrl,
    MessageEntityMention,
    MessageEntityMentionName
)
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiohttp import web

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id       = cfg["api_id"]
api_hash     = cfg["api_hash"]
session_name = cfg["session_name"]
channels     = cfg["channels"]

ALLOWED_LINKS = [
    "t.me/ironetbot",
    "akharinkhabar.ir",
    "t.me/nikotinn_text",
]
ALLOWED_MENTIONS = [
    "akhbartelfori",
]
ALLOWED_PROXY_SUBSTR = [
    "proxy?server=",
]

client = TelegramClient(session_name, api_id, api_hash)
state = {username: {"count": 0, "index": 0} for username in channels}

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    username = event.chat.username.lower()
    msg      = event.message
    text     = (msg.message or "").lower()

    for ent in msg.entities or []:
        if isinstance(ent, (MessageEntityUrl, MessageEntityTextUrl)):
            url = ent.url if hasattr(ent, 'url') else text[ent.offset:ent.offset + ent.length]
            ul = url.lower()
            if username in ul or any(a in ul for a in ALLOWED_LINKS) or any(p in ul for p in ALLOWED_PROXY_SUBSTR):
                print(f"🔗 Allowed link: {url}")
                continue
            print(f"🚫 Skipping (external link {url})")
            return

    for ent in msg.entities or []:
        if isinstance(ent, MessageEntityMention):
            m = text[ent.offset+1:ent.offset+ent.length]
            if m.lower() == username or m.lower() in ALLOWED_MENTIONS:
                print(f"🔔 Allowed mention: @{m}")
                continue
            print(f"🚫 Skipping (mention @{m})")
            return

    for ent in msg.entities or []:
        if isinstance(ent, MessageEntityMentionName):
            print(f"🚫 Skipping (hidden mention user_id={ent.user_id})")
            return

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
    reply = messages[idx]
    st["index"] += 1

    try:
        await asyncio.sleep(1)
        await client.send_message(
            entity=event.chat.username,
            message=reply,
            comment_to=msg.id
        )
        print(f"✅ Commented on {username}:{msg.id} -> {reply}")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ Join the discussion group first.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

async def handle_health(request):
    return web.Response(text="OK")

async def main():
    port = int(os.environ.get("PORT", 8080))
    app  = web.Application()
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
