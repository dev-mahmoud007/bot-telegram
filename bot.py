import os
import sys
import asyncio
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

print("🚀 FINAL BOT (1H + LIVE + SAFE)")

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
                files = [m.media for m in media] if media else None

                if files:
                    await client.send_file(target_channel, files, caption=text)
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

# 🧠 buffer
media_buffer = []
last_media_time = 0



# ⚡ لايف ذكي
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
        print(f"📦 Media ({len(media_buffer)})")
        return

    if msg.text:
        print("📝 Text detected")

        # إذا ما في وسائط
        if not media_buffer:
            text = format_post(msg.text)
            await send_queue.put(([], text, msg.id))
            return

        print("⏳ Waiting media...")

        start = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(1)
            now = asyncio.get_event_loop().time()

            if now - last_media_time > 2:
                break

            if now - start > 5:
                print("⚠️ Timeout")
                break

        text = format_post(msg.text)

        await send_queue.put((media_buffer.copy(), text, msg.id))
        print(f"🚀 Sent batch ({len(media_buffer)})")

        media_buffer.clear()
async def check_last_msg():
    async for msg in client.iter_messages(source_channel, limit=1):
        print("SOURCE LAST MSG ID:", msg.id)

# 🚀 تشغيل
async def main():
    print("ENTER MAIN")
    print("LAST_ID:", load_last_id())
    await check_last_msg()

    asyncio.create_task(sender())



    print("🔥 LIVE MODE")

    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
