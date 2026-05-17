import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import re
import asyncio

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

print("User Bot running...")

def increase_prices(text):
    if not text:
        return text

    text = re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

    return text

# 🟡 سحب آخر 10 مع حماية من الحظر
async def first_run():
    print("Fetching last 10 posts safely...")

    count = 0

    async for msg in client.iter_messages(source_channel, limit=10):
        text = msg.message or ""
        new_text = increase_prices(text)

        try:
            if msg.media:
                await client.send_file(target_channel, msg.media, caption=new_text)
            else:
                if new_text:
                    await client.send_message(target_channel, new_text)

            count += 1
            print(f"Sent {count}")

            # 🔥 أهم سطر (تخفيف السرعة)
            await asyncio.sleep(5)

        except FloodWaitError as e:
            print(f"⏳ Flood wait: sleeping {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print("Error:", e)

    print(f"Done. Sent {count} posts.")

# 🔵 لايف
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    text = event.message.message or ""
    new_text = increase_prices(text)

    try:
        if event.message.media:
            await client.send_file(target_channel, event.message.media, caption=new_text)
        else:
            if new_text:
                await client.send_message(target_channel, new_text)

        print("Live sent")

    except FloodWaitError as e:
        print(f"⏳ Flood wait (live): {e.seconds}")
        await asyncio.sleep(e.seconds)

    except Exception as e:
        print("Live error:", e)

async def main():
    await first_run()
    print("Listening...")
    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
