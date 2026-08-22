import os
import sys
import json
import re
import asyncio
import atexit
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError


# ============================================================
# VERA FASHION MULTI SOURCE BOT
# ============================================================

print("🚀 VERA FASHION MULTI SOURCE BOT")


# ============================================================
# منع تشغيل أكثر من نسخة
# ============================================================

LOCK_FILE = "/tmp/vera_fashion_bot.lock"
STATE_FILE = "bot_state.json"

if os.path.exists(LOCK_FILE):
    print("❌ Bot is already running.")
    sys.exit()

with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))

atexit.register(
    lambda: os.remove(LOCK_FILE)
    if os.path.exists(LOCK_FILE)
    else None
)


# ============================================================
# بيانات Telegram
# ============================================================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

if not api_hash:
    raise ValueError("API_HASH is missing")

if not string_session:
    raise ValueError("STRING_SESSION is missing")


client = TelegramClient(
    StringSession(string_session),
    api_id,
    api_hash
)


# ============================================================
# القناة الهدف
# ============================================================

TARGET_CHANNEL = "VeraFashionGaza"


# ============================================================
# القنوات المصدر
# ============================================================

SOURCES = {

    # القناة القديمة
    "mulhim00": {
        "parser": "mulhim",
        "price_add": 4,
        "history_hours": None,
    },

    # القنوات الجديدة
    "LaleFashion4": {
        "parser": "lale",
        "price_add": 4,
        "history_hours": 24,
    },

    "toptanjorli2020": {
        "parser": "toptan",
        "price_add": 5,
        "history_hours": 24,
    },

    "totih1tr": {
        "parser": "toti",
        "price_add": 5,
        "history_hours": 24,
    },

    "emirelatoptan": {
        "parser": "emirela",
        "price_add": 5,
        "history_hours": 24,
    },
}


# ============================================================
# توحيد أسماء القنوات
# ============================================================

SOURCE_LOOKUP = {
    name.lower(): name
    for name in SOURCES
}


# ============================================================
# حفظ آخر منشور لكل قناة
# ============================================================

def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

            if isinstance(data, dict):
                return data

    except Exception:
        pass

    return {}


state = load_state()


def save_state():
    temp_file = STATE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        STATE_FILE
    )


def get_last_id(channel):
    return int(
        state
        .get(channel, {})
        .get("last_id", 0)
    )


def save_last_id(channel, msg_id):
    if channel not in state:
        state[channel] = {}

    state[channel]["last_id"] = msg_id

    save_state()


# ============================================================
# تنظيف النص
# ============================================================

def clean_value(value):
    if not value:
        return ""

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def get_lines(text):
    if not text:
        return []

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def first_line(text):
    lines = get_lines(text)

    return lines[0] if lines else ""


# ============================================================
# استخراج السعر
#
# يدعم:
# 30$
# $30
# 30.5$
# $30.5
# 30 دولار
# 30.5 دولار
# السعر: 30
# السعر 30.5
#
# إذا لم يجد سعرًا يرجع None
# ============================================================

def extract_price(text):
    if not text:
        return None

    patterns = [

        # 16.40$
        r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*\$",

        # $16.40
        r"\$\s*(\d+(?:[.,]\d+)?)",

        # 16.40 دولار
        r"(\d+(?:[.,]\d+)?)\s*(?:دولار|دولاراً|دولارًا)",

        # دولار 16.40
        r"(?:دولار|دولاراً|دولارًا)\s*(\d+(?:[.,]\d+)?)",

        # السعر: 16.40
        r"(?:السعر|سعر|السعرر+)\s*[:：\-]?\s*(\d+(?:[.,]\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        try:
            number = match.group(1)
            number = number.replace(",", ".")

            return float(number)

        except Exception:
            continue

    return None


def format_price(text, addition):
    price = extract_price(text)

    if price is None:
        return "على الخاص"

    final_price = price + addition

    if final_price.is_integer():
        return f"{int(final_price)}$"

    return f"{final_price:g}$"


# ============================================================
# استخراج النص الذي يأتي بعد كلمة معينة
# ============================================================

def value_after_keyword(text, keywords):
    if not text:
        return ""

    keyword_pattern = "|".join(
        re.escape(x)
        for x in keywords
    )

    pattern = (
        rf"(?:{keyword_pattern})"
        rf"\s*[:：\-]?\s*([^\n]+)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    return clean_value(
        match.group(1)
    )


# ============================================================
# MULHIM00
#
# أول سطر = اسم الموديل
# المقاس = المقاس / المقاسات / القياسات
# الكود = الكود
# السعر = السعر الأصلي + 4
# ============================================================

def parse_mulhim(text):
    name = first_line(text)

    size = value_after_keyword(
        text,
        [
            "المقاس",
            "المقاسات",
            "القياسات"
        ]
    )

    code = value_after_keyword(
        text,
        ["الكود"]
    )

    price = format_price(
        text,
        4
    )

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{name}

الخامة: تركية مستوردة 🇹🇷

📏 المقاس: {size}
💲 السعر: {price}
🏷 الكود: {code}

🛍 بيع جملة فقط

📲 https://wa.me/970592417956
"""


# ============================================================
# LALEFASHION4
#
# أول سطر = اسم الموديل
# الموديل نفسه = الكود
# Kumaş = القماش
# السايز / الحجم / المقاس = المقاس
# السعر الأصلي + 4
# ============================================================

def parse_lale(text):
    lines = get_lines(text)

    if not lines:
        return None

    name = lines[0]

    code = name

    fabric = value_after_keyword(
        text,
        ["Kumaş"]
    )

    size = value_after_keyword(
        text,
        [
            "السايز",
            "سايز",
            "الحجم",
            "المقاس",
            "المقاسات"
        ]
    )

    price = format_price(
        text,
        4
    )

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{name}

🧵 القماش: {fabric}
📏 المقاس: {size}
🏷 الكود: {code}
💲 السعر: {price}

🛍 بيع جملة فقط

📲 https://wa.me/970592417956
"""


# ============================================================
# TOPTANJORLI2020
#
# القناة فوضوية وغير منتظمة.
#
# الألوان لا تعتبر اسم موديل.
# القماش يوضع في خانة القماش.
# السيري = عدد القطع وليس المقاس.
# أرقام مثل 1.2.3 = المقاسات.
# الرقم بجانب الدولار = السعر.
# السعر بدون رقم = على الخاص.
# ============================================================

COLOR_WORDS = {
    "اسود",
    "أسود",
    "ابيض",
    "أبيض",
    "كحلي",
    "بيج",
    "بني",
    "احمر",
    "أحمر",
    "اخضر",
    "أخضر",
    "وردي",
    "زهري",
    "رمادي",
    "رصاصي",
    "موف",
    "بنفسجي",
    "برتقالي",
    "اصفر",
    "أصفر",
    "ازرق",
    "أزرق",
}


def is_color_only_line(line):
    clean = re.sub(
        r"[🖤🤍💙❤️💚💛🧡💜🤎🩷🩵🩶]+",
        "",
        line
    )

    clean = re.sub(
        r"[^\w\u0600-\u06FF ]+",
        " ",
        clean
    )

    words = [
        x.strip()
        for x in clean.split()
        if x.strip()
    ]

    if not words:
        return False

    return all(
        word in COLOR_WORDS
        for word in words
    )


def extract_colors_from_line(line):
    found = []

    for color in COLOR_WORDS:
        if re.search(
            rf"(?<!\w){re.escape(color)}(?!\w)",
            line,
            flags=re.IGNORECASE
        ):
            found.append(color)

    return list(
        dict.fromkeys(found)
    )


def parse_toptan(text):
    lines = get_lines(text)

    if not lines:
        return None

    model = ""
    fabric = ""
    colors = []
    sizes = []

    # --------------------------------------------------------
    # القماش
    # --------------------------------------------------------

    for line in lines:
        match = re.search(
            r"قماش\s*[:：\-]?\s*(.+)",
            line,
            flags=re.IGNORECASE
        )

        if match:
            fabric = clean_value(
                match.group(1)
            )
            break

    # --------------------------------------------------------
    # الألوان
    # --------------------------------------------------------

    for line in lines:
        if is_color_only_line(line):
            colors.extend(
                extract_colors_from_line(line)
            )

    colors = list(
        dict.fromkeys(colors)
    )

    # --------------------------------------------------------
    # المقاسات
    #
    # مثل:
    # 1.2.3
    # 1. 2. 3
    # --------------------------------------------------------

    for line in lines:

        if "$" in line:
            continue

        if re.search(
            r"السيري|سيري",
            line,
            flags=re.IGNORECASE
        ):
            continue

        if re.search(
            r"قماش",
            line,
            flags=re.IGNORECASE
        ):
            continue

        matches = re.findall(
            r"(?<![\d.])\d+(?![\d.])",
            line
        )

        if matches and len(matches) <= 10:
            for number in matches:
                if number not in sizes:
                    sizes.append(number)

    # --------------------------------------------------------
    # اسم الموديل
    # --------------------------------------------------------

    ignored_phrases = {
        "من جديد",
        "جديد",
        "متوفر",
        "متوفره",
        "متوفرة",
    }

    model_candidates = []

    for line in lines:

        clean = line.strip()

        # تجاهل السعر
        if "$" in clean:
            continue

        # تجاهل السيري
        if re.search(
            r"السيري|سيري",
            clean,
            flags=re.IGNORECASE
        ):
            continue

        # تجاهل القماش
        if re.search(
            r"قماش",
            clean,
            flags=re.IGNORECASE
        ):
            continue

        # تجاهل المقاسات
        if re.fullmatch(
            r"[\d.\s]+",
            clean
        ):
            continue

        # تجاهل الأسطر التي تحتوي أرقامًا
        if re.search(
            r"\d",
            clean
        ):
            continue

        # تجاهل الألوان فقط
        if is_color_only_line(clean):
            continue

        # تجاهل عبارات افتتاحية
        if clean in ignored_phrases:
            continue

        model_candidates.append(clean)

    # نأخذ آخر وصف مناسب للموديل
    if model_candidates:
        model = model_candidates[-1]
    else:
        model = lines[0]

    price = format_price(
        text,
        5
    )

    size_text = " ".join(sizes)

    color_text = " ".join(colors)

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{model}

🧵 القماش: {fabric}
🎨 الألوان: {color_text}
📏 المقاس: {size_text}
💲 السعر: {price}

🛍 بيع جملة فقط

📲 https://wa.me/970592417956
"""


# ============================================================
# TOTIH1TR
#
# السطر الأول = اسم الموديل
# مقاس = المقاس
# الوان = اللون
# قماش = نوع القماش
# السعر الذي بجانبه $ أو دولار أو كلمة السعر
# السعر الأصلي + 5
# إذا لم يوجد سعر = على الخاص
# ============================================================

def parse_toti(text):
    name = first_line(text)

    size = value_after_keyword(
        text,
        ["مقاس"]
    )

    colors = value_after_keyword(
        text,
        [
            "الوان",
            "ألوان"
        ]
    )

    fabric = value_after_keyword(
        text,
        ["قماش"]
    )

    price = format_price(
        text,
        5
    )

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{name}

📏 المقاس: {size}
🎨 الألوان: {colors}
🧵 القماش: {fabric}
💲 السعر: {price}

🛍 بيع جملة فقط

📲 https://wa.me/970592417956
"""


# ============================================================
# EMIRELATOPTAN
#
# أول سطر = اسم الموديل
# MODEL KODU / MODEL CODE / كود الموديل = الكود
# SERİ BİLGİSİ / SERIES INFORMATION / معلومات السيري = المقاس
# قماش = القماش
# السعر بالدولار هو المعتمد
# السعر الأصلي + 5
# ============================================================

def parse_emirela(text):
    lines = get_lines(text)

    if not lines:
        return None

    # اسم الموديل
    name = lines[0]

    # الكود
    code = value_after_keyword(
        text,
        [
            "MODEL KODU",
            "MODEL CODE",
            "كود الموديل",
            "كود المودل"
        ]
    )

    # المقاسات
    size = value_after_keyword(
        text,
        [
            "SERİ BİLGİSİ",
            "SERIES INFORMATION",
            "معلومات السيري"
        ]
    )

    # القماش
    fabric = value_after_keyword(
        text,
        ["قماش"]
    )

    # السعر
    # مثال:
    # FIYAT 750 TL 16.40 $
    #
    # سيتم اختيار 16.40 وليس 750
    price = format_price(
        text,
        5
    )

    return f"""✨ فيرا فاشون | Vera Fashion 👗

{name}

🧵 القماش: {fabric}
📏 المقاس: {size}
🏷 الكود: {code}
💲 السعر: {price}

🛍 بيع جملة فقط

📲 https://wa.me/970592417956
"""


# ============================================================
# اختيار Parser المناسب لكل قناة
# ============================================================

PARSERS = {
    "mulhim": parse_mulhim,
    "lale": parse_lale,
    "toptan": parse_toptan,
    "toti": parse_toti,
    "emirela": parse_emirela,
}


def parse_post(channel, text):
    config = SOURCES[channel]

    parser = PARSERS[
        config["parser"]
    ]

    try:
        return parser(text)

    except Exception as e:
        print(
            f"❌ Parser error {channel}: {e}"
        )

        return None


# ============================================================
# قائمة الانتظار
# ============================================================

send_queue = asyncio.Queue()


# ============================================================
# إرسال الموديل
#
# جميع الصور والفيديوهات أولًا.
# وبعد اكتمال جميع مجموعات Media يتم إرسال النص.
#
# مثال:
# 27 Media
# المجموعة الأولى = 10
# المجموعة الثانية = 10
# المجموعة الثالثة = 7
# ثم النص
# ============================================================

async def send_model(
    channel,
    media,
    text,
    msg_id
):

    while True:

        try:

            print(
                f"📤 Sending {channel} "
                f"ID={msg_id} "
                f"MEDIA={len(media)}"
            )

            # إرسال كل مجموعات Media
            for start in range(
                0,
                len(media),
                10
            ):

                chunk = media[
                    start:start + 10
                ]

                files = [
                    item.media
                    for item in chunk
                ]

                if not files:
                    continue

                await client.send_file(
                    TARGET_CHANNEL,
                    files
                )

                await asyncio.sleep(1)

            # إرسال النص بعد انتهاء كل Media
            if text:
                await client.send_message(
                    TARGET_CHANNEL,
                    text
                )

            # حفظ آخر منشور بعد نجاح الإرسال بالكامل
            save_last_id(
                channel,
                msg_id
            )

            print(
                f"✅ SENT {channel} {msg_id}"
            )

            return

        except FloodWaitError as e:

            print(
                f"⏳ FloodWait {channel}: "
                f"{e.seconds} seconds"
            )

            await asyncio.sleep(
                e.seconds + 2
            )

        except Exception as e:

            print(
                f"❌ Send error {channel} "
                f"{msg_id}: {e}"
            )

            await asyncio.sleep(10)


# ============================================================
# Worker الإرسال
# ============================================================

async def sender():

    while True:

        item = await send_queue.get()

        try:

            (
                channel,
                media,
                text,
                msg_id
            ) = item

            await send_model(
                channel,
                media,
                text,
                msg_id
            )

        finally:

            send_queue.task_done()


# ============================================================
# جلب آخر 24 ساعة للقنوات الجديدة
# ============================================================

async def process_history(channel):

    config = SOURCES[channel]

    hours = config["history_hours"]

    # القناة القديمة Live فقط
    if hours is None:

        print(
            f"🟢 {channel}: LIVE ONLY"
        )

        return

    # إذا سبق تشغيل القناة
    # لا نعيد آخر 24 ساعة
    if get_last_id(channel) > 0:

        print(
            f"⏭ {channel}: already initialized "
            f"last_id={get_last_id(channel)}"
        )

        return

    start_time = (
        datetime.now(timezone.utc)
        - timedelta(hours=hours)
    )

    print(
        f"📚 Loading last {hours} hours: "
        f"{channel}"
    )

    messages = []

    try:

        async for msg in client.iter_messages(
            channel
        ):

            if not msg.date:
                continue

            if msg.date < start_time:
                break

            messages.append(msg)

    except Exception as e:

        print(
            f"❌ History error {channel}: {e}"
        )

        return

    # ترتيب من الأقدم إلى الأحدث
    messages.reverse()

    print(
        f"📦 {channel}: "
        f"{len(messages)} messages"
    )

    media_buffer = []

    for msg in messages:

        # Media
        if msg.media:

            media_buffer.append(msg)

            continue

        # النص
        if msg.text:

            formatted = parse_post(
                channel,
                msg.text
            )

            if not formatted:
                continue

            await send_queue.put(
                (
                    channel,
                    media_buffer.copy(),
                    formatted,
                    msg.id
                )
            )

            media_buffer.clear()

    # Media بدون نص
    if media_buffer:

        print(
            f"⚠️ {channel}: "
            f"{len(media_buffer)} media "
            f"without text"
        )

    print(
        f"✅ History queued: {channel}"
    )


# ============================================================
# Buffer مستقل لكل قناة
# ============================================================

live_buffers = {
    channel: []
    for channel in SOURCES
}


# ============================================================
# استقبال المنشورات الجديدة Live
# ============================================================

@client.on(
    events.NewMessage(
        chats=list(SOURCES.keys())
    )
)
async def handler(event):

    msg = event.message

    username = getattr(
        event.chat,
        "username",
        None
    )

    if not username:
        return

    channel = SOURCE_LOOKUP.get(
        username.lower()
    )

    if not channel:
        return

    # منع التكرار
    if msg.id <= get_last_id(channel):
        return

    # Media
    if msg.media:

        live_buffers[
            channel
        ].append(msg)

        print(
            f"📸 {channel} MEDIA {msg.id}"
        )

        return

    # لا يوجد نص
    if not msg.text:
        return

    # تنسيق النص
    formatted = parse_post(
        channel,
        msg.text
    )

    if not formatted:
        return

    # أخذ كل Media التابعة لهذا الموديل
    media = live_buffers[
        channel
    ].copy()

    # تفريغ Buffer
    live_buffers[
        channel
    ].clear()

    print(
        f"📝 {channel} TEXT {msg.id} "
        f"MEDIA={len(media)}"
    )

    await send_queue.put(
        (
            channel,
            media,
            formatted,
            msg.id
        )
    )


# ============================================================
# التشغيل الرئيسي
# ============================================================

async def main():

    print("🚀 ENTER MAIN")

    # تشغيل Worker واحد للإرسال
    asyncio.create_task(
        sender()
    )

    # جلب التاريخ للقنوات الجديدة فقط
    for channel in SOURCES:

        if SOURCES[channel]["history_hours"] is not None:

            await process_history(
                channel
            )

    print("🔥 LIVE MODE")

    await client.run_until_disconnected()


# ============================================================
# START
# ============================================================

client.start()

client.loop.run_until_complete(
    main()
     )
