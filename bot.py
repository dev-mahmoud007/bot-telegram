import os
import sys
import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

print("BOT STARTED 🔥")

# 🛑 منع تشغيل أكثر من نسخة
LOCK_FILE = "/tmp/bot.lock"

if os.path.exists(LOCK_FILE):
    print("Bot already running. EXIT.")
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write("running")

import atexit
def cleanup():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
atexit.register(cleanup)

# 🔐 بيانات
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

print("CONFIG LOADED ✅")

# 🧠 ذاكرة مؤقتة (تحمي من التكرار لو الملف انمسح)
last_id_cache = 0

# 📁 تحميل ID
def load_last_id():
    global last_id_cache
    try:
        with open("last_id.txt", "r") as f:
            last_id_cache = int(f.read().strip())
            print(f"Loaded last_id: {last_id_cache}")
            return last_id_cache
    except:
        print("No last_id file → start fresh")
        return 0

# 💾 حفظ ID
def save_last_id(msg_id):
    global last_id_cache
    last_id_cache = msg_id

    with open("last_id.txt", "w") as f:
        f.write(str(msg_id))

    print(f"Saved last_id → {msg_id}")

# 🧠 تنسيق النص
def format_post(text):
    if not text:
        return None

    lines = text.strip().split("\n")
    first_line = lines[0].strip() if lines else ""

    price_match = re.search(r"السعر\s*:\s*(\d+(?:\.\d+)?)", text)
    price = float(price_match.group(1)) + 4 if price_match else ""

    size_match = re.search(r"(?:المقاس|المقاسات|القياسات)\s*:\s*(.+)", text)
    size = size_match.group(1).strip() if size_match else ""

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

# 📦 إرسال ذكي
async def send_post(media_buffer, text, last_msg_id):
    photos = []
    videos = []

    for m in media_buffer:
        if hasattr(m, 'photo') and m.photo:
            photos.append(m)
        else:
            videos.append(m)

    # صور (ألبوم)
    if photos:
        chunks = [photos[i:i+10] for i in range(0, len(photos), 10)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await client.send_file(target_channel, chunk, caption=text)
            else:
                await client.send_file(target_channel, chunk)
            await asyncio.sleep(2)

    # فيديو
    for v in videos:
        await client.send_file(target_channel, v)
        await asyncio.sleep(2)

    # حفظ ID
    save_last_id(last_msg_id)

# 🔄 تعويض ذكي
async def smart_catchup():
    print("SMART CATCHUP 🔄")

    last_id = load_last_id()

    if last_id == 0:
        print("First run → skip catchup")
        return

    media_buffer = []

    async for msg in client.iter_messages(source_channel, min_id=last_id):

        # حماية من التكرار
        if msg.id <= last_id_cache:
            continue

        if msg.media:
            media_buffer.append(msg)
            continue

        if msg.text and media_buffer:
            text = format_post(msg.text)

            await send_post(media_buffer, text, msg.id)

            print(f"Recovered: {len(media_buffer)}")

            media_buffer = []

    print("Catchup done ✅")

# 🧠 لايف
media_buffer = []
waiting = False
last_media_time = 0

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer, waiting, last_media_time

    msg = event.message

    if msg.media:
        media_buffer.append(msg)
        waiting = True
        last_media_time = asyncio.get_event_loop().time()
        return

    if msg.text and waiting:
        await asyncio.sleep(3)

        now = asyncio.get_event_loop().time()
        if now - last_media_time < 2:
            return

        text = format_post(msg.text)

        await send_post(media_buffer, text, msg.id)

        print(f"LIVE sent: {len(media_buffer)}")

        media_buffer = []
        waiting = False

# 🚀 تشغيل
async def main():
    print("ENTER MAIN")

    await smart_catchup()

    print("LISTENING 🔥")

    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
