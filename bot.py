import os
import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

print("STRICT Smart Bot running...")

# تعديل السعر
def increase_prices(text):
    if not text:
        return text

    return re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

# 🧠 التخزين
media_buffer = []
waiting_for_text = False

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer, waiting_for_text

    msg = event.message

    try:
        # 📸 أي وسائط → خزّن فقط
        if msg.media:
            media_buffer.append(msg.media)
            waiting_for_text = True
            print(f"Collected media: {len(media_buffer)}")
            return

        # 📝 نص → فقط إذا عندنا وسائط
        if msg.text and waiting_for_text:
            text = increase_prices(msg.text)

            # ⏳ ننتظر شوي عشان نتأكد كل الوسائط وصلت
            await asyncio.sleep(2)

            # 🔥 تقسيم (حد Telegram = 10)
            chunks = [media_buffer[i:i+10] for i in range(0, len(media_buffer), 10)]

            for i, chunk in enumerate(chunks):
                if i == 0:
                    # أول دفعة مع النص (كابشن)
                    await client.send_file(
                        target_channel,
                        chunk,
                        caption=text
                    )
                else:
                    await client.send_file(
                        target_channel,
                        chunk
                    )

                await asyncio.sleep(2)

            print(f"✅ Sent {len(media_buffer)} media with text")

            # 🔄 reset
            media_buffer = []
            waiting_for_text = False
            return

        # ❌ نص بدون وسائط → تجاهل (حسب طلبك)
        if msg.text and not waiting_for_text:
            print("Ignored text بدون وسائط")
            return

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
