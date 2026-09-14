import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعداداتك (نفسها اللي بتستخدمها بالبوت الأساسي)
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)
target_channel = "VeraFashionGaza"

OLD_NUMBER = "970595127374"
NEW_NUMBER = "970592417956"  # حط الرقم الجديد هنا

async def edit_old_messages():
    print("⏳ جاري البحث عن الرسائل وتعديل الرقم...")
    
    count = 0
    # limit=200 يعني رح يفحص آخر 200 رسالة نزلت بقناتك، بتقدر تزود الرقم لو بدك
    async for msg in client.iter_messages(target_channel, limit=200):
        if msg.text and OLD_NUMBER in msg.text:
            try:
                # استبدال الرقم القديم بالجديد
                new_text = msg.text.replace(OLD_NUMBER, NEW_NUMBER)
                
                # تعديل الرسالة في القناة
                await client.edit_message(target_channel, msg.id, new_text)
                count += 1
                print(f"✅ تم تعديل الرسالة رقم: {msg.id}")
                
                # استراحة بسيطة عشان تليجرام ما يحظر البوت (FloodWait)
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"❌ خطأ في تعديل الرسالة {msg.id}: {e}")

    print(f"🎉 تم الانتهاء! عدد الرسائل اللي تم تعديلها: {count}")

async def main():
    await edit_old_messages()

client.start()
client.loop.run_until_complete(main())
