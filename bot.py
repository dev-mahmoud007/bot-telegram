from datetime import datetime

TARGET_CODE = "EYYY"

async def fetch_from_specific_post():
    print("Searching for target post (code + date)...")

    media_buffer = []
    messages = []
    found = False

    async for msg in client.iter_messages(source_channel):

        if msg.text and TARGET_CODE in msg.text:

            # 🎯 تحقق من التاريخ
            msg_date = msg.date.date()  # بدون وقت

            if msg_date == datetime(2026, 5, 19).date():
                print("✅ Found exact post (code + date)")
                found = True
                start_id = msg.id
                break

    if not found:
        print("❌ Target post not found")
        return

    # 🔥 سحب من هذه النقطة
    async for msg in client.iter_messages(source_channel, min_id=start_id):
        messages.append(msg)

    messages.reverse()

    for msg in messages:

        if msg.media:
            media_buffer.append(msg.media)
            continue

        if msg.text and media_buffer:
            text = format_post(msg.text)

            photos = []
            videos = []

            for m in media_buffer:
                if hasattr(m, 'photo') and m.photo:
                    photos.append(m)
                else:
                    videos.append(m)

            if photos:
                chunks = [photos[i:i+10] for i in range(0, len(photos), 10)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await client.send_file(target_channel, chunk, caption=text)
                    else:
                        await client.send_file(target_channel, chunk)
                    await asyncio.sleep(2)

            for v in videos:
                await client.send_file(target_channel, v)
                await asyncio.sleep(2)

            print(f"Sent batch: {len(media_buffer)}")

            media_buffer = []

    print("Done fetching from exact post ✅")
