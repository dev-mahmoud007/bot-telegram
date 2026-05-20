from datetime import datetime, timezone

TARGET_CODE = "EYYY"

async def fetch_from_specific_post():
    print("Searching smart (date + code)...")

    media_buffer = []
    messages = []
    found = False

    start_date = datetime(2026, 5, 18, tzinfo=timezone.utc)
    end_date = datetime(2026, 5, 20, tzinfo=timezone.utc)

    async for msg in client.iter_messages(source_channel):

        # ⛔ وقف إذا طلعنا برا النطاق
        if msg.date < start_date:
            break

        # تجاهل إذا أكبر من النطاق
        if msg.date > end_date:
            continue

        if msg.text and TARGET_CODE in msg.text:
            print("✅ Found exact post")
            found = True
            start_id = msg.id
            break

    if not found:
        print("❌ Not found in date range")
        return

    # 🔥 سحب من النقطة
    async for msg in client.iter_messages(source_channel, min_id=start_id):
        messages.append(msg)

    messages.reverse()

    for msg in messages:

        if msg.media:
            media_buffer.append(msg.media)
            continue

        if msg.text and media_buffer:
            text = format_post(msg.text)

            await send_post(media_buffer, text)

            print(f"Sent: {len(media_buffer)}")

            media_buffer = []

    print("Done ✅")
