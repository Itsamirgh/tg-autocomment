import asyncio
import json
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError

# بارگذاری تنظیمات
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id = cfg["api_id"]
api_hash = cfg["api_hash"]
session_name = cfg["session_name"]
channels = cfg["channels"]  # dict: username -> comment text

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    comment_text = channels.get(event.chat.username, "🔥 ممنون از پستت!")
    try:
        await asyncio.sleep(1)  # جلوگیری از FloodWait
        await client.send_message(
            entity=event.chat,
            message=comment_text,
            comment_to=event.message.id  # کامنت توی Discussion
        )
        print(f"✅ کامنت ثبت شد زیر پست {event.message.id}")

    except FloodWaitError as e:
        print(f"⏰ FloodWait: لطفاً {e.seconds} ثانیه صبر کن…")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ خطا: باید عضو Discussion Group باشی.")
    except Exception as e:
        print(f"❌ خطای ناشناخته: {repr(e)}")

async def main():
    print("🚀 ربات داره لاگین می‌شه…")
    await client.start()
    print("✅ ربات آنلاین و آماده‌ست")
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("🛑 در حال قطع اتصال…")
        await client.disconnect()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
