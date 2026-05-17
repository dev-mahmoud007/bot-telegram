import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import re
from datetime import datetime, timedelta, timezone

# متغيرات Railway
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)

# القنوات
source_channel = "mulhim00"
target_channel = "VeraFashionGaza"

print("User Bot running...")

# 🔥 تعديل السعر (السعر:43$)
def increase_prices(text):
    if not text:
        return text

    text = re.sub(
        r"(السعر\s*:\s*)(\d+)\$",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 4}$",
        text
    )

    return text

# 🟡 سحب آخر 7 أيام فقط
async def first_run():
    print("Fetching last 7 days posts...")

    since_date = datetime.now(timezone.utc) - timedelta(days=7)
    count = 0

    async for msg in client.iter_messages(source_channel):
        if not msg.date:
            continue

        if msg.date < since_date:
            break

        text = msg.message or ""
        new_text = increase_prices(text)

        try:
            if msg.media:
                await client.send_file(
                    target_channel,
                    msg.media,
                    caption=new_text
                )
            else:
                if new_text:
                    await client.send_message(
                        target_channel,
                        new_text
                    )

            count += 1
            print(f"Sent old post {count}")

        except Exception as e:
            print("Error sending old:", e)

    print(f"Done. Sent {count} old posts.")

# 🔵 لايف
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

        print("Live sent:", new_text)

    except Exception as e:
        print("Live error:", e)

# التشغيل
async def main():
    await first_run()  # 👈 يسحب أسبوع فقط
    print("Now listening for new posts...")
    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
