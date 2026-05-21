import os
import sys
import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

print("🚀 COMMERCIAL BOT STARTED")

# 🛑 منع تعدد التشغيل
LOCK_FILE = "/tmp/bot.lock"
if os.path.exists(LOCK_FILE):
    print("Already running ❌")
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write("running")

import atexit
atexit.register(lambda: os.remove(LOCK_FILE) if os.path.exists(LOCK_FILE) else None)

# 🔐 بيانات
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

# 📁 تخزين ID
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

# 🧠 تنسيق النص
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

# 📦 إرسال احترافي
async def sender_worker():
    while True:
        media_buffer, text, msg_id = await send_queue.get()

        for attempt in range(3):
            try:
                await client.send_file(
                    target_channel,
                    [m.media for m in media_buffer],
                    caption=text
                )

                save_last_id(msg_id)
                print(f"✅ Sent: {len(media_buffer)} items")

                break

            except FloodWaitError as e:
                print(f"⏳ FloodWait {e.seconds}s")
                await asyncio.sleep(e.seconds)

            except Exception as e:
                print("Retry...", e)
                await asyncio.sleep(2)

        send_queue.task_done()

# 🧠 buffer ذكي
media_buffer = []

# 🔄 تعويض ذكي
async def smart_catchup():
    print("🔄 Catchup...")

    last_id = load_last_id()
    if last_id == 0:
        print("First run skip")
        return

    async for msg in client.iter_messages(source_channel, min_id=last_id):

        if msg.id <= last_id_cache:
            continue

        if msg.media:
            media_buffer.append(msg)
            continue

        if msg.text and media_buffer:
            text = format_post(msg.text)

            await send_queue.put((media_buffer.copy(), text, msg.id))
            media_buffer.clear()

    print("✅ Catchup done")

# ⚡ لايف
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    msg = event.message

    if msg.id <= last_id_cache:
        return

    global media_buffer

    if msg.media:
        media_buffer.append(msg)
        return

    if msg.text and media_buffer:
        await asyncio.sleep(2)

        text = format_post(msg.text)

        await send_queue.put((media_buffer.copy(), text, msg.id))

        media_buffer.clear()

# 🚀 تشغيل
async def main():
    print("ENTER MAIN")

    asyncio.create_task(sender_worker())

    await smart_catchup()

    print("LISTENING 🔥")

    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
