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

print("Smart Bot running...")

# 🔥 تعديل السعر
def increase_prices(text):
    if not text:
        return text

    return re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

# 🧠 تخزين الوسائط مؤقتًا
media_buffer = []

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer

    msg = event.message

    try:
        # 📸 إذا فيه وسائط → خزّن
        if msg.media:
            media_buffer.append(msg.media)
            print("Media added to buffer:", len(media_buffer))
            return

        # 📝 إذا فيه نص → انشر الوسائط + النص
        if msg.text:
            text = increase_prices(msg.text)

            if media_buffer:
                await client.send_file(
                    target_channel,
                    media_buffer,
                    caption=text
                )
                print("Sent media + text")

                media_buffer = []  # 🔥 تصفير

            else:
                # إذا نص لحاله
                await client.send_message(target_channel, text)
                print("Sent text only")

            await asyncio.sleep(5)

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
