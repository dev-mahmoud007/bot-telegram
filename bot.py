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

def increase_prices(text):
    if not text:
        return text

    return re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

media_buffer = []
collecting = False

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer, collecting

    msg = event.message

    try:
        # 📸 تجميع الوسائط
        if msg.media:
            media_buffer.append(msg.media)
            collecting = True
            print("Collected:", len(media_buffer))
            return

        # 📝 لما يوصل النص
        if msg.text and collecting:
            text = increase_prices(msg.text)

            # ⏳ ننتظر تجميع كامل
            await asyncio.sleep(2)

            # 🔥 تقسيم (حد 10)
            chunks = [media_buffer[i:i+10] for i in range(0, len(media_buffer), 10)]

            for i, chunk in enumerate(chunks):
                if i == 0:
                    await client.send_file(
                        target_channel,
                        chunk,
                        caption=text
                    )
                else:
                    await client.send_file(target_channel, chunk)

                await asyncio.sleep(2)

            print(f"Sent {len(media_buffer)} media")

            media_buffer = []
            collecting = False
            return

        # نص بدون وسائط
        if msg.text:
            await client.send_message(target_channel, increase_prices(msg.text))

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
