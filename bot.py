import os
import sys
import asyncio
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

LOCK_FILE = "/tmp/bot.lock"
if os.path.exists(LOCK_FILE):
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write("running")

import atexit
atexit.register(lambda: os.remove(LOCK_FILE) if os.path.exists(LOCK_FILE) else None)

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

client = TelegramClient(StringSession(string_session), api_id, api_hash)
target_channel = "VeraFashionGaza"

LIVE_CHANNELS = ["mulhim00", "LaleFashion4", "toptanjorli2020", "totih1tr", "emirelatoptan"]
HISTORY_CHANNELS = ["LaleFashion4", "toptanjorli2020", "totih1tr", "emirelatoptan"]

def extract_price_with_dollar(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*\$|\$\s*(\d+(?:\.\d+)?)", text)
    if match: return float(match.group(1) or match.group(2))
    return None

def extract_price_with_word(text, word):
    match = re.search(fr"(\d+(?:\.\d+)?)\s*{word}|{word}\s*(\d+(?:\.\d+)?)", text)
    if match: return float(match.group(1) or match.group(2))
    return None

def contains_arabic(text):
    return bool(re.search(r"[\u0600-\u06FF]", text))

def format_post(text, source):
    if not text: return None
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines: return None

    title, price_val, size_val, code_val, color_val, fabric_val = "", None, "", "", "", ""
    source = source.lower()

    if source == "lalefashion4":
        title = lines[0]
        for line in lines:
            if "المودل" in line: code_val = line.replace("المودل", "").strip(" :")
            elif "Kumaş" in line: fabric_val = line.replace("Kumaş", "").strip(" :")
            elif "السايز" in line or "الحجم" in line: size_val = re.sub(r"(السايز|الحجم)", "", line).strip(" :")
        price_num = extract_price_with_dollar(text)
        price_val = f"{price_num + 4}$" if price_num else "على الخاص"

    elif source == "toptanjorli2020":
        for line in lines:
            if not title and not re.search(r"\d", line): title = line
            if re.fullmatch(r"[\d\-\s\,]+", line): size_val = line
        price_num = extract_price_with_dollar(text)
        price_val = f"{price_num + 5}$" if price_num else "على الخاص"

    elif source == "totih1tr":
        title = lines[0]
        for line in lines:
            if "مقاس" in line: size_val = line.replace("مقاس", "").strip(" :")
            elif "الوان" in line: color_val = line.replace("الوان", "").strip(" :")
            elif "قماش" in line: fabric_val = line.replace("قماش", "").strip(" :")
        price_num = extract_price_with_dollar(text)
        price_val = f"{price_num + 5}$" if price_num else "على الخاص"

    elif source == "emirelatoptan":
        for line in lines:
            if not title and contains_arabic(line): title = line
            if "كود الموديل" in line: code_val = line.replace("كود الموديل", "").strip(" :")
            elif "السيري" in line: size_val = line.replace("معلومات السيري", "").replace("السيري", "").strip(" :")
        price_num = extract_price_with_word(text, "دولار")
        price_val = f"{price_num + 5}$" if price_num else "على الخاص"

    elif source == "mulhim00":
        title = lines[0]
        for line in lines:
            if re.search(r"(?:السعر|سعر)\s*:", line):
                match = re.search(r"(\d+(?:\.\d+)?)", line)
                if match: price_val = f"{float(match.group(1)) + 4}$"
            elif re.search(r"(?:المقاس|المقاسات|القياسات)\s*:", line): size_val = re.sub(r".*?(?:المقاس|المقاسات|القياسات)\s*:\s*", "", line)
            elif re.search(r"(?:الكود|كود)\s*:", line): code_val = re.sub(r".*?(?:الكود|كود)\s*:\s*", "", line)
        fabric_val = "تركية مستوردة 🇹🇷"

    final_text = "✨ فيرا فاشون | Vera Fashion 👗\n\n"
    if title: final_text += f"{title}\n\n"
    final_text += "ـــــــــــــــــــــــــــــ\n"
    if fabric_val: final_text += f"🧵 الخامة: {fabric_val}\n"
    if size_val: final_text += f"📏 المقاسات: {size_val}\n"
    if color_val: final_text += f"🎨 الألوان: {color_val}\n"
    if code_val: final_text += f"🏷 الكود: {code_val}\n"
    if price_val: final_text += f"💲 السعر: {price_val}\n"
    final_text += "\n🛍 بيع جملة فقط\n📲 للتواصل والطلب:\n https://wa.me/970592417956"
    return final_text

send_queue = asyncio.Queue()

async def sender():
    while True:
        media, text = await send_queue.get()
        try:
            if media:
                chunks = [media[i:i+10] for i in range(0, len(media), 10)]
                for chunk in chunks:
                    files = [m.media for m in chunk]
                    await client.send_file(target_channel, files)
                    await asyncio.sleep(1.5)
            if text:
                await client.send_message(target_channel, text)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception as e:
            pass
        finally:
            send_queue.task_done()

# دالة سحب آخر أسبوع مع نظام التجميع الصارم الجديد
async def fetch_history_once():
    if os.path.exists("history_done.txt"): return

    print("⏳ Fetching last 7 days history with strict grouping...")
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    for channel in HISTORY_CHANNELS:
        try:
            messages = []
            async for msg in client.iter_messages(channel):
                if msg.date < seven_days_ago: break
                messages.append(msg)
            
            messages.reverse()
            final_posts = []
            current_post = {"media": [], "text": None, "grouped_id": None}
            
            for msg in messages:
                should_flush = False
                # شرط فك الاشتباك 1: اختلاف الألبوم
                if current_post["grouped_id"] and msg.grouped_id and current_post["grouped_id"] != msg.grouped_id:
                    should_flush = True
                # شرط فك الاشتباك 2: استلمنا نص والآن نستلم شيء جديد لا ينتمي لنفس الألبوم
                elif current_post["text"] and (msg.text or msg.media):
                    if not (msg.grouped_id and msg.grouped_id == current_post["grouped_id"]):
                        should_flush = True
                        
                # تفريغ وبدء موديل جديد
                if should_flush:
                    if current_post["media"] or current_post["text"]: final_posts.append(current_post.copy())
                    current_post = {"media": [], "text": None, "grouped_id": None}
                    
                if msg.grouped_id: current_post["grouped_id"] = msg.grouped_id
                if msg.media: current_post["media"].append(msg)
                if msg.text: current_post["text"] = msg.text
                    
            if current_post["media"] or current_post["text"]:
                final_posts.append(current_post)
                
            for post in final_posts:
                if post["text"]:
                    formatted = format_post(post["text"], channel)
                    if formatted:
                        await send_queue.put((post["media"], formatted))
                        await asyncio.sleep(1.5)
        except Exception as e:
            pass

    with open("history_done.txt", "w") as f: f.write("done")
    print("✅ History fetch complete!")

# ----------------- نظام الأمان الذكي للبث الحي -----------------
channel_state = {ch.lower(): {"media": [], "text": None, "grouped_id": None, "timer": None} for ch in LIVE_CHANNELS}

async def force_flush(source):
    state = channel_state[source]
    if not state["media"] and not state["text"]: return

    media_to_send = state["media"].copy()
    text_to_send = state["text"]
    
    # تصفير الموديل الحالي لاستقبال موديل جديد
    state["media"].clear()
    state["text"] = None
    state["grouped_id"] = None
    
    formatted = format_post(text_to_send, source) if text_to_send else None
    if media_to_send or formatted:
        await send_queue.put((media_to_send, formatted))

async def timer_flush(source):
    await asyncio.sleep(3) # فترة أمان أخيرة لو التاجر سكت تماماً
    await force_flush(source)

@client.on(events.NewMessage(chats=LIVE_CHANNELS))
async def handler(event):
    msg = event.message
    chat = await event.get_chat()
    source = chat.username.lower() if chat.username else str(chat.id)
    state = channel_state[source]

    # إيقاف المؤقت القديم
    if state["timer"] and not state["timer"].done():
        state["timer"].cancel()

    should_flush = False
    
    # فحص فك الاشتباك الفوري
    if state["grouped_id"] and msg.grouped_id and state["grouped_id"] != msg.grouped_id:
        should_flush = True
    elif state["text"] and (msg.text or msg.media):
        if not (msg.grouped_id and msg.grouped_id == state["grouped_id"]):
            should_flush = True

    # إرسال الموديل السابق فوراً لو بدأ التاجر بموديل جديد
    if should_flush:
        await force_flush(source)

    # إضافة البيانات للموديل الحالي
    if msg.grouped_id: state["grouped_id"] = msg.grouped_id
    if msg.media: state["media"].append(msg)
    if msg.text: state["text"] = msg.text

    # تشغيل مؤقت أمان جديد للحالة
    state["timer"] = asyncio.create_task(timer_flush(source))
# ----------------------------------------------------------------

async def main():
    asyncio.create_task(sender())
  #  await fetch_history_once()
    print("🔥 BULLETPROOF LIVE MODE STARTED")
    await client.run_until_disconnected()

client.start()
client.loop.run_until_complete(main())
