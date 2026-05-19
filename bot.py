import os
import asyncio
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# 🔐 بيانات
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

FLAG_FILE = "first_run_done.txt"

print("FINAL PRO BOT 🔥")

# 🧠 تنسيق النص
def format_post(text):
    if not text:
        return None

    lines = text.strip().split("\n")

    # أول سطر من المصدر
    first_line = lines[0].strip() if lines else ""

    # السعر
    price_match = re.search(r"السعر\s*:\s*(\d+(?:\.\d+)?)", text)
    price = float(price_match.group(1)) + 4 if price_match else ""

    # المقاس
    size_match = re.search(r"(?:المقاس|المقاسات|القياسات)\s*:\s*(.+)", text)
    size = size_match.group(1).strip() if size_match else ""

    # الكود
    code_match = re.search(r"الكود\s*:\s*(.+)", text)
    code = code_match.group(1).strip() if code_match else ""

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{first_line}

الخامة: تركية مستوردة عالية الجودة 🇹🇷

📏 المقاس: {size}
💲 السعر: {price}$
🏷 الكود: {code}

🛍 لبيع الجملة فقط | Vera Fashion 🛒

📲 لطلب الموديل يرجى التواصل مباشرة:
https://wa.me/970595127374
"""

# 🟡 أول تشغيل (24 ساعة - ترتيب صحيح)
async def first_run():
    print("Fetching last 24 hours...")

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    media_buffer = []

    async for msg in client.iter_messages(source_channel, reverse=True):

        if msg.date < since:
            continue

        if msg.media:
            media_buffer.append(msg.media)
            continue

        if msg.text and media_buffer:
            text = format_post(msg.text)

            chunks = [media_buffer[i:i+10] for i in range(0, len(media_buffer), 10)]

            for i, chunk in enumerate(chunks):
                if i == 0:
                    await client.send_file(target_channel, chunk, caption=text)
                else:
                    await client.send_file(target_channel, chunk)

                await asyncio.sleep(2)

            media_buffer = []

    print("First run done ✅")


# 🧠 لايف
media_buffer = []
waiting = False

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer, waiting

    msg = event.message

    if msg.media:
        media_buffer.append(msg.media)
        waiting = True
        return

    if msg.text and waiting:
        text = format_post(msg.text)

        chunks = [media_buffer[i:i+10] for i in range(0, len(media_buffer), 10)]

        for i, chunk in enumerate(chunks):
            if i == 0:
                await client.send_file(target_channel, chunk, caption=text)
            else:
                await client.send_file(target_channel, chunk)

            await asyncio.sleep(2)

        media_buffer = []
        waiting = False


# 🚀 تشغيل (مرة واحدة فقط)
async def main():
    if not os.path.exists(FLAG_FILE):
        print("FIRST RUN 🔥")

        await first_run()

        with open(FLAG_FILE, "w") as f:
            f.write("done")

        print("Switching to LIVE...")

    else:
        print("Already ran before ✅")

    await client.run_until_disconnected()


client.start()
client.loop.run_until_complete(main())
