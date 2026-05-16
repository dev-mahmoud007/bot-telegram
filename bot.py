import os
from telethon import TelegramClient, events
import re

# متغيرات Railway
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

# القنوات
source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

# تشغيل البوت
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# تعديل الأسعار
def increase_prices(text):
    return re.sub(r"\$(\d+)", lambda m: f"${int(m.group(1)) + 4}", text)

# أول تشغيل (آخر 50 منشور)
async def first_run():
    print("Fetching last messages...")

    async for msg in client.iter_messages(source_channel, limit=50):
        text = msg.message or ""
        new_text = increase_prices(text)

        if msg.media:
            await client.send_file(target_channel, msg.media, caption=new_text)
        else:
            if new_text:
                await client.send_message(target_channel, new_text)

    print("Done first run.")

# لايف
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    text = event.message.message or ""
    new_text = increase_prices(text)

    if event.message.media:
        await client.send_file(target_channel, event.message.media, caption=new_text)
    else:
        await client.send_message(target_channel, new_text)

# تشغيل
async def main():
    await first_run()
    print("Bot started...")
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
