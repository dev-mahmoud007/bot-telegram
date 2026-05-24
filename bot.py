import os
import sys
import asyncio
import re
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

print("🚀 RESET 24 MAY + LIVE BOT")

# 🛑 منع تشغيل نسختين
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

# 📁 last_id
last_id_cache = 0

def load_last_id():
    global last_id_cache
    try:
        with open("last_id.txt", "r") as f:
            last_id_cache = int(f.read().strip())
    except:
        last_id_cache = 0
    return last_id_cache

def save_last_id(mid):
    global last_id_cache
    last_id_cache = mid
    with open("last_id.txt", "w") as f:
        f.write(str(mid))

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

# 📦 إرسال (مع تقسيم 10)
async def sender():
    while True:
        media, text, msg_id = await send_queue.get()

        try:
            if media:
                chunks = [media[i:i+10] for i in range(0, len(media), 10)]

                for i, chunk in enumerate(chunks):
                    files = [m.media for m in chunk]

                    if i == 0:
                        await client.send_file(target_channel, files, caption=text)
                    else:
                        await client.send_file(target_channel, files)

                    await asyncio.sleep(1)

            else:
                await client.send_message(target_channel, text)

            save_last_id(msg_id)
            print("✅ Sent:", msg_id)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print("Send error:", e)

        send_queue.task_done()

# 🔥 حذف + إعادة بناء (مرة واحدة فقط)
async def reset_24_may():
    if os.path.exists("reset_done.txt"):
        print("⏭ Reset already done")
        return

    print("🗑 Deleting 24 May...")

    start = datetime(2026, 5, 24, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 5, 24, 23, 59, tzinfo=timezone.utc)

    # حذف
    async for msg in client.iter_messages(target_channel):
        if msg.date < start:
            break

        if start <= msg.date <= end:
            await client.delete_messages(target_channel, msg.id)
            await asyncio.sleep(0.3)

    print("♻️ Reposting 24 May...")

    temp = []
    async for msg in client.iter_messages(source_channel):
        if msg.date < start:
            break
        if start <= msg.date <= end:
            temp.append(msg)

    temp.reverse()

    media_buffer = []

    for msg in temp:
        if msg.media:
            media_buffer.append(msg)
            continue

        if msg.text:
            text = format_post(msg.text)

            if media_buffer:
                await send_queue.put((media_buffer.copy(), text, msg.id))
                media_buffer.clear()
            else:
                await send_queue.put(([], text, msg.id))

    # علم إنه خلص
    with open("reset_done.txt", "w") as f:
        f.write("done")

    print("✅ RESET DONE")

# 🟢 لايف بسيط (صح)
media_buffer = []

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    msg = event.message

    if msg.id <= last_id_cache:
        return

    if msg.media:
        media_buffer.append(msg)
        return

    if msg.text:
        text = format_post(msg.text)

        if media_buffer:
            await send_queue.put((media_buffer.copy(), text, msg.id))
            media_buffer.clear()
        else:
            await send_queue.put(([], text, msg.id))

# 🚀 تشغيل
async def main():
    print("ENTER MAIN")

    load_last_id()

    asyncio.create_task(sender())

    await reset_24_may()  # 👈 مرة واحدة فقط

    print("🔥 LIVE MODE")

    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
