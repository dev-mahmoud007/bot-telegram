from telethon import TelegramClient, events
import re
from datetime import datetime, timedelta
import os

api_id = 123456
api_hash = "YOUR_API_HASH"
bot_token = "YOUR_BOT_TOKEN"

source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# تعديل الأسعار
def increase_prices(text):
    return re.sub(r"\$(\d+)", lambda m: f"${int(m.group(1)) + 4}", text)

# تحقق إذا أول تشغيل
FIRST_RUN_FILE = "first_run.txt"

async def first_run():
    if os.path.exists(FIRST_RUN_FILE):
        return

    print("First run: fetching last 30 days...")

    limit_date = datetime.now() - timedelta(days=30)

    async for msg in client.iter_messages(source_channel):
        if msg.date < limit_date:
            break

        text = msg.message or ""
        new_text = increase_prices(text)

        if msg.media:
            await client.send_file(target_channel, msg.media, caption=new_text)
        else:
            if new_text:
                await client.send_message(target_channel, new_text)

    # نحفظ إنه خلصنا
    with open(FIRST_RUN_FILE, "w") as f:
        f.write("done")

# استقبال الرسائل الجديدة
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    text = event.message.message or ""
    new_text = increase_prices(text)

    if event.message.media:
        await client.send_file(target_channel, event.message.media, caption=new_text)
    else:
        await client.send_message(target_channel, new_text)

async def main():
    await first_run()
    print("Now listening for new messages...")
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
