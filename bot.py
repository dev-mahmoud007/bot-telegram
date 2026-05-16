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

print("Bot is running (LIVE MODE)...")

# تعديل السعر
def increase_prices(text):
    return re.sub(r"\$(\d+)", lambda m: f"${int(m.group(1)) + 4}", text)

# استقبال المنشورات الجديدة فقط
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    print("New message detected!")

    text = event.message.message or ""
    new_text = increase_prices(text)

    try:
        if event.message.media:
            await client.send_file(
                target_channel,
                event.message.media,
                caption=new_text
            )
        else:
            if new_text:
                await client.send_message(
                    target_channel,
                    new_text
                )

        print("Sent:", new_text)

    except Exception as e:
        print("Error:", e)
print("TOKEN:", bot_token)
# تشغيل دائم
client.run_until_disconnected()
