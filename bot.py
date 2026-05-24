import os
import sys
import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

print("🚀 STABLE FINAL BOT")

# 🛑 منع تشغيل نسختين
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

# 🔥 إصلاح تلقائي
async def fix_last_id():
    global last_id_cache

    load_last_id()

    async for msg in client.iter_messages(source_channel, limit=1):
        real_last = msg.id

    print("LAST_ID:", last_id_cache)
    print("REAL_LAST:", real_last)

    # ❗ إذا last_id غلط (أكبر من الحقيقي)
    if last_id_cache > real_last:
        print("⚠️ FIXING LAST_ID...")
        save_last_id(real_last - 10)

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

# 📦 إرسال
async def sender():
    while True:
        media, text, msg_id = await send_queue.get()

        for _ in range(3):
            try:
                if media:
                    # 🔥 تقسيم الوسائط
                    chunks = [media[i:i+10] for i in range(0, len(media), 10)]

                    for i, chunk in enumerate(chunks):
                        files = [m.media for m in chunk]

                        # ✨ النص فقط مع أول مجموعة
                        if i == 0:
                            await client.send_file(target_channel, files, caption=text)
                        else:
                            await client.send_file(target_channel, files)

                        await asyncio.sleep(1)  # مهم لتجنب flood

                else:
                    await client.send_message(target_channel, text)

                save_last_id(msg_id)
                print(f"✅ Sent: {msg_id}")

                break

            except FloodWaitError as e:
                print(f"⏳ FloodWait {e.seconds}")
                await asyncio.sleep(e.seconds)

            except Exception as e:
                print("Retry:", e)
                await asyncio.sleep(2)

        send_queue.task_done()

# 🧠 buffer ذكي
media_buffer = []
last_media_time = 0

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer, last_media_time

    msg = event.message

    if msg.id <= last_id_cache:
        return

    now = asyncio.get_event_loop().time()

    if msg.media:
        media_buffer.append(msg)
        last_media_time = now
        return

    if msg.text:
        if not media_buffer:
            text = format_post(msg.text)
            await send_queue.put(([], text, msg.id))
            return

        start = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(1)
            now = asyncio.get_event_loop().time()

            if now - last_media_time > 2:
                break

            if now - start > 5:
                break

        text = format_post(msg.text)

        await send_queue.put((media_buffer.copy(), text, msg.id))
        media_buffer.clear()

# 🚀 تشغيل
async def main():
    print("ENTER MAIN")

    await fix_last_id()  # 🔥 أهم سطر

    asyncio.create_task(sender())

    print("🔥 LIVE MODE")

    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
