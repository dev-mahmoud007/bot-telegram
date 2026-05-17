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

# تعديل السعر
def increase_prices(text):
    if not text:
        return text

    return re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

# تخزين الوسائط
media_buffer = []
last_group_id = None

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global media_buffer, last_group_id

    msg = event.message

    try:
        # 📸 إذا ألبوم (grouped)
        if msg.grouped_id:
            if last_group_id != msg.grouped_id:
                media_buffer = []  # ألبوم جديد

            last_group_id = msg.grouped_id

            if msg.media:
                media_buffer.append(msg.media)

            print("Album media added:", len(media_buffer))
            return

        # 📸 إذا وسائط مفردة (بدون grouped)
        if msg.media:
            media_buffer.append(msg.media)
            print("Single media added:", len(media_buffer))
            return

        # 📝 إذا نص → انشر مع الوسائط
        if msg.text:
