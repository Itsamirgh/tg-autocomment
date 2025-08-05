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

ALLOWED_LINKS        = ["t.me/ironetbot", "akharinkhabar.ir", "t.me/nikotinn_text"]
ALLOWED_MENTIONS     = ["akhbartelfori"]
ALLOWED_PROXY_SUBSTR = ["proxy?server="]

client = TelegramClient(session_name, api_id, api_hash)
state  = {key: {"count": 0, "index": 0} for key in channels}

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    raw      = event.message.message or ""
    key      = event.chat.username or str(event.chat.id)
    cfg_val  = channels.get(key)
    if not cfg_val:
        return

    # URL filtering
    for ent in event.message.entities or []:
        if isinstance(ent, (MessageEntityTextUrl, MessageEntityUrl)):
            if isinstance(ent, MessageEntityTextUrl):
                url = ent.url
            else:
                url = raw[ent.offset : ent.offset + ent.length]
            ul = url.lower()
            if key in ul or any(a in ul for a in ALLOWED_LINKS) or any(p in ul for p in ALLOWED_PROXY_SUBSTR):
                continue
            return

    # @mention filtering
    for ent in event.message.entities or []:
        if isinstance(ent, MessageEntityMention):
            mention = raw[ent.offset + 1 : ent.offset + ent.length].lower()
            if mention == key or mention in ALLOWED_MENTIONS:
                continue
            return

    # hidden mention filtering
    for ent in event.message.entities or []:
        if isinstance(ent, MessageEntityMentionName):
            return

    # comment rotation
    if isinstance(cfg_val, dict):
        messages = cfg_val["messages"]
        freq     = cfg_val.get("frequency", 1)
    else:
        messages = [cfg_val]
        freq     = 1

    st = state[key]
    st["count"] += 1
    if st["count"] % freq != 0:
        return

    idx   = st["index"] % len(messages)
    reply = messages[idx]
    st["index"] += 1

    try:
        await asyncio.sleep(1)
        await client.send_message(
            entity=event.chat.username,
            message=reply,
            comment_to=event.message.id
        )
        print(f"✅ Commented on {key}:{event.message.id} -> {reply}")
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ Join the discussion group first.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

async def handle_health(request):
    return web.Response(text="OK")

async def main():
    port = int(os.environ.get("PORT", 8080))
    await client.start()
    print("✅ Bot is online")
    app  = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"🌐 Health on http://0.0.0.0:{port}/health")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

