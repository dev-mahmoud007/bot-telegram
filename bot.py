import os
import sys
import asyncio
import re
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

print("🚀 RESET + REBUILD BOT")

# 🛑 منع التكرار
LOCK_FILE = "/tmp/bot.lock"
if os.path.exists(LOCK_FILE):
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write("running")

import atexit
atexit.register(lambda: os.remove(LOCK_FILE) if os.path.exists(LOCK_FILE) else None)

# 🔐
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

# 🧠 تنسيق
def format_post(text):
    if not text:
        return None

    first_line = text.strip().split("\n")[0]

    price = re.search(r"السعر\s*:\s*(\d+(?:\.\d+)?)", text)
    price = float(price.group(1)) + 4 if price else ""

    size = re.search(r"(?:المقاس|المقاسات|القياسات)\s*:\s*(.+)", text)
    size = size.group(1).strip() if size else ""

    code = re.search(r"الكود\s*:\s*(.+)", text)
    code = code.group(1).strip() if code else ""

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{first_line}

الخامة: تركية مستوردة 🇹🇷

📏 المقاس: {size}
💲 السعر: {price}$
🏷 الكود: {code}

🛍 بيع جملة فقط

📲 https://wa.me/970595127374
"""

# 🧠 Queue
send_queue = asyncio.Queue()

async def sender():
    while True:
        media, text = await send_queue.get()

        try:
            files = [m.media for m in media] if media else None

            if files:
                await client.send_file(target_channel, files, caption=text)
            else:
                await client.send_message(target_channel, text)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print("Send error:", e)

        send_queue.task_done()

# 🔥 1. حذف منشورات 21 مايو
async def delete_target_day():
    print("🗑 Deleting May 21 posts...")

    start = datetime(2026, 5, 21, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 5, 21, 23, 59, tzinfo=timezone.utc)

    async for msg in client.iter_messages(target_channel):
        if msg.date < start:
            break

        if start <= msg.date <= end:
            try:
                await client.delete_messages(target_channel, msg.id)
                print("Deleted:", msg.id)
                await asyncio.sleep(0.3)
            except Exception as e:
                print("Delete error:", e)

    print("✅ Delete done")

# 🔥 2. إعادة النشر من المصدر
media_buffer = []

async def rebuild_from_source():
    print("♻️ Rebuilding from May 21...")

    start = datetime(2026, 5, 21, 0, 0, tzinfo=timezone.utc)

    temp = []

    async for msg in client.iter_messages(source_channel):
        if msg.date < start:
            break
        temp.append(msg)

    temp.reverse()

    for msg in temp:
        if msg.media:
            media_buffer.append(msg)
            continue

        if msg.text:
            text = format_post(msg.text)

            if media_buffer:
                await send_queue.put((media_buffer.copy(), text))
                media_buffer.clear()
            else:
                await send_queue.put(([], text))

    print("✅ Rebuild done")

# ⚡ لايف
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    msg = event.message

    global media_buffer

    if msg.media:
        media_buffer.append(msg)
        return

    if msg.text:
        await asyncio.sleep(2)

        text = format_post(msg.text)

        if media_buffer:
            await send_queue.put((media_buffer.copy(), text))
            media_buffer.clear()
        else:
            await send_queue.put(([], text))

# 🚀 تشغيل
async def main():
    asyncio.create_task(sender())

    # 👇 تنفيذ مرة واحدة
    await delete_target_day()
    await rebuild_from_source()

    print("🔥 LIVE MODE")

    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
