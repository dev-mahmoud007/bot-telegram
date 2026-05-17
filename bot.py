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

print("Album Bot running...")

def increase_prices(text):
    if not text:
        return text

    return re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

albums = {}

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global albums

    msg = event.message

    try:
        # 📸 إذا ألبوم
        if msg.grouped_id:
            gid = msg.grouped_id

            if gid not in albums:
                albums[gid] = {
                    "media": [],
                    "text": None
                }

            albums[gid]["media"].append(msg)

            if msg.text:
                albums[gid]["text"] = msg.text

            # ⏳ انتظار اكتمال الألبوم
            await asyncio.sleep(2)

            if gid in albums:
                data = albums.pop(gid)

                media_files = [m.media for m in data["media"]]
                text = increase_prices(data["text"])

                # 📸 إرسال الألبوم بدون كابشن
                await client.send_file(
                    target_channel,
                    media_files
                )

                await asyncio.sleep(1)

                # 📝 إرسال النص تحت
                if text:
                    await client.send_message(
                        target_channel,
                        text
                    )

                print("Album + text sent ✅")

            return

        # 📝 نص عادي
        if msg.text:
            await client.send_message(
                target_channel,
                increase_prices(msg.text)
            )

    except FloodWaitError as e:
        print(f"Flood wait: {e.seconds}")
        await asyncio.sleep(e.seconds)

    except Exception as e:
        print("Error:", e)

async def main():
    print("Listening...")
    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
