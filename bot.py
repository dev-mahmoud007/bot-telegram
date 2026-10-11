import os
import re
import time
import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from telethon import TelegramClient, events, utils
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaWebPage

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("vera")

# =====================  الإعدادات  =====================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
STRING_SESSION = os.environ["STRING_SESSION"]
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "VeraFashionGaza")
NOTIFY_TO = os.getenv("NOTIFY_TO", "me")   # وين توصلك إشعارات التعديل/الحذف ("me" = الرسائل المحفوظة، فاضي = تعطيل)

CAPTION_WAIT = 3          # ثواني انتظار بعد آخر وسائط فيها كابشن (نص ضمن الألبوم)
MEDIA_WAIT = 120          # كم ثانية نستنى النص بعد وسائط بدون نص؛ إذا ما إجا نتجاهل الوسائط (ما بتنشر أبداً بدون نص)
MERGE_WINDOW = 15         # وسائط جديدة بعد هالمدة من آخر وسائط بدون نص = موديل جديد، والقديم بنتجاهله
REPLACE_WINDOW = 180      # المدة اللي نستنى فيها نص بديل بعد ما المصدر يحذف النص
POST_TEXT_ONLY = True     # نشر الرسائل النصية اللي مالها وسائط
DELETE_TEXT_IF_NOT_REPLACED = False  # لو انحذف النص ولم يأتِ بديل: احذف نصي أنا كمان؟
MAX_HISTORY = 3000
POLL_SECONDS = 20         # كل قديش يفحص القنوات مباشرة (شبكة أمان لو فاتت تحديثات حية)
POLL_MIN_AGE = 8          # ما يلتقط رسالة إلا إذا مر عليها هالعدد من الثواني (يعطي التحديثات الحية فرصة)
ON_REQUEST = "على الخاص"
WA_LINK = "https://wa.me/970592417956"

SOURCES = {
    "mulhim00":        dict(markup=4, title="first", fabric_default="تركية مستوردة 🇹🇷"),
    "lalefashion4":    dict(markup=4, title="first"),
    "toptanjorli2020": dict(markup=5, title="nodigit"),
    "totih1tr":        dict(markup=5, title="arabic"),
    "modalolvatoptan": dict(markup=4, title="first", multi_size=True),
    "cvbnmlj":         dict(markup=4, mode="literal"),
}

# =====================  التحليل (Parsing)  =====================
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def norm(t):
    return t.translate(_DIGITS)  # نفس الطول تماماً، فالمواقع تبقى صحيحة


NUM = r"\d+(?:[.,]\d+)?"
PRICE_PATTERNS = [
    re.compile(rf"(?:السعر|سعر|f[iİı]yat\w*|price)\s*[:：\-–=]?\s*\$?\s*({NUM})", re.I),
    re.compile(rf"({NUM})\s*(?:\$|دولار|دولارات|usd|dollars?)", re.I),
    re.compile(rf"\$\s*({NUM})"),
]


def find_price(text):
    n = norm(text)
    for pat in PRICE_PATTERNS:
        m = pat.search(n)
        if m:
            return float(m.group(1).replace(",", ".")), m.span(1)
    return None, None


def fmt_num(v):
    return f"{v:g}"


SIZE_KW = ["مقاس", "قياس", "beden", "size", "ölçü", "olcu"]
CODE_KW = ["كود", "kod", "model", "code"]
FABRIC_KW = ["قماش", "خامة", "خام", "kuma[sş]", "fabric"]
COLOR_KW = ["الوان", "ألوان", "لون", "renk", "colou?r"]
PRICE_KW = ["السعر", "سعر", "f[iİı]yat", "price"]
SIRI_KW = ["siri", "seri", "سيري", "سيرى"]


def _rx(words):
    return re.compile(rf"^\W*(?:ال)?(?:{'|'.join(words)})\w*[\s:：\-–—=_•·|]*(.*)$", re.I)


SIZE_RE, CODE_RE, FABRIC_RE, COLOR_RE = _rx(SIZE_KW), _rx(CODE_KW), _rx(FABRIC_KW), _rx(COLOR_KW)
FIELD_LINE = _rx(SIZE_KW + CODE_KW + FABRIC_KW + COLOR_KW + PRICE_KW + SIRI_KW)
SIZE_SUFFIX = re.compile(r"^([\d\s\-–_.,،/]+?)\s*(?:مقاس\w*|قياس\w*|beden)\s*$", re.I)
SIZE_NUMERIC = re.compile(r"^[\d\s\-–_.,،/]+$")


def get_all(lines, rx):
    out = []
    for l in lines:
        m = rx.match(l)
        if m and m.group(1).strip():
            out.append(m.group(1).strip())
    return out


def clean_size(v):
    return re.sub(r"\.{3,}|…+", " - ", v).strip()


def find_sizes(lines, multi=False):
    vals = get_all(lines, SIZE_RE)
    if not vals:
        for l in lines:
            m = SIZE_SUFFIX.match(norm(l))
            if m:
                vals = [m.group(1).strip()]
                break
    if not vals:
        for l in lines:
            n = norm(l).strip()
            if SIZE_NUMERIC.match(n) and re.search(r"[\-–_.,،/]", n):
                vals = [n]
                break
    if not vals:
        return ""
    vals = [clean_size(v) for v in vals]
    return " و ".join(vals) if multi else vals[0]


def find_siri(lines):
    for l in lines:
        n = norm(l)
        if re.search("|".join(SIRI_KW), n, re.I):
            m = re.search(r"\d+", n)
            if m:
                return m.group(0)
    return ""


def pick_title(lines, mode):
    if mode == "nodigit":
        out = []
        for l in lines:
            if re.search(r"\d", norm(l)) or FIELD_LINE.match(l):
                break
            out.append(l)
            if len(out) == 2:
                break
        return "\n".join(out)
    if mode == "arabic":
        for l in lines:
            if re.search(r"[\u0600-\u06FF]", l) and not FIELD_LINE.match(l):
                return l
    return lines[0]


def build(title, f):
    out = "✨ فيرا فاشون | Vera Fashion 👗\n\n"
    if title:
        out += f"{title}\n\n"
    out += "ـــــــــــــــــــــــــــــ\n"
    if f.get("fabric"): out += f"🧵 الخامة: {f['fabric']}\n"
    if f.get("size"):   out += f"📏 المقاسات: {f['size']}\n"
    if f.get("siri"):   out += f"🔢 السيري: {f['siri']} قطع\n"
    if f.get("color"):  out += f"🎨 الألوان: {f['color']}\n"
    if f.get("code"):   out += f"🏷 الكود: {f['code']}\n"
    if f.get("price"):  out += f"💲 السعر: {f['price']}\n"
    out += f"\n🛍 بيع جملة فقط\n📲 للتواصل والطلب:\n{WA_LINK}"
    return rtl(out)


RLM = "\u200f"  # علامة اتجاه يمين-ليسار: بتخلي السطر RTL بدون ما تقلب ترتيب الإنجليزي والأرقام


def rtl(text):
    lines = []
    for l in text.split("\n"):
        if l.strip() and not l.lstrip().startswith("http"):
            l = RLM + l
        lines.append(l)
    return "\n".join(lines)


def format_post(text, source):
    if not text or not text.strip():
        return None
    cfg = SOURCES.get(source.lower())
    if not cfg:
        return None
    markup = cfg["markup"]

    if cfg.get("mode") == "literal":
        body = text.strip()
        v, span = find_price(body)
        if v is not None:
            body = body[:span[0]] + fmt_num(v + markup) + body[span[1]:]
        return build(body, {})

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None
    v, _ = find_price(text)
    f = {
        "size": find_sizes(lines, cfg.get("multi_size", False)),
        "code": (get_all(lines, CODE_RE) or [""])[0],
        "fabric": (get_all(lines, FABRIC_RE) or [cfg.get("fabric_default", "")])[0],
        "color": (get_all(lines, COLOR_RE) or [""])[0],
        "siri": find_siri(lines),
        "price": f"{fmt_num(v + markup)}$" if v is not None else ON_REQUEST,
    }
    return build(pick_title(lines, cfg.get("title", "first")), f)


def safe_format(text, source):
    try:
        return format_post(text, source)
    except Exception:
        log.exception("format_post failed for %s", source)
        return text  # أسلم من ضياع النص


# =====================  الحالة  =====================
@dataclass(eq=False)
class Post:
    source: str
    media: list = field(default_factory=list)       # رسائل المصدر (قبل الإرسال)
    text: Optional[str] = None
    text_id: Optional[int] = None
    last_group: Optional[int] = None
    version: int = 0
    last_ts: float = 0.0
    lock: Any = field(default_factory=asyncio.Lock)
    sent: bool = False
    cancelled: bool = False
    media_ids: set = field(default_factory=set)
    sent_media: dict = field(default_factory=dict)  # id في المصدر -> رسالتي المرسلة
    sent_text: Any = None
    shown: Optional[str] = None
    text_deleted: bool = False
    awaiting_until: float = 0.0
    keys: set = field(default_factory=set)


class Chan:
    def __init__(self, name):
        self.name = name
        self.lock = asyncio.Lock()
        self.pending: Optional[Post] = None
        self.recent = deque(maxlen=8)
        self.seen = set()      # ids الرسائل اللي عالجناها (حية أو من الفحص)
        self.baseline = 0      # آخر id وقت التشغيل: ما نعالج شي أقدم منه


client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
target = None
id_to_name = {}
entities = {}
channels = {}
queue = None
index = {}          # (source, msg_id) -> Post
history = deque()
bg_tasks = set()


def spawn(coro):
    t = asyncio.create_task(coro)
    bg_tasks.add(t)
    t.add_done_callback(bg_tasks.discard)


def is_media(msg):
    return bool(msg.media) and not isinstance(msg.media, MessageMediaWebPage)


async def retry(fn, *a, **k):
    for _ in range(6):
        try:
            return await fn(*a, **k)
        except FloodWaitError as e:
            log.warning("FloodWait %ss", e.seconds)
            await asyncio.sleep(e.seconds + 1)
    raise RuntimeError("too many flood waits")


async def notify(text):
    log.info(text.replace("\n", " | "))
    if NOTIFY_TO:
        try:
            await retry(client.send_message, NOTIFY_TO, text)
        except Exception:
            log.exception("notify failed")


def add_key(post, mid):
    k = (post.source, mid)
    index[k] = post
    post.keys.add(k)


def register(post):
    for mid in post.media_ids:
        add_key(post, mid)
    if post.text_id:
        add_key(post, post.text_id)
    history.append(post)
    while len(history) > MAX_HISTORY:
        old = history.popleft()
        for k in old.keys:
            index.pop(k, None)


def short(t, n=150):
    t = (t or "").replace("\n", " ")
    return t if len(t) <= n else t[:n] + "…"


# =====================  الإرسال (طابور واحد، كل منشور وحدة كاملة)  =====================
async def send_one(m):
    """يرسل وسائط وحدة؛ إذا فشل بالمرجع ينزّلها ويرفعها من جديد."""
    try:
        return await retry(client.send_file, target, m.media)
    except Exception as e:
        log.exception("send by reference failed (%s), trying download/upload", type(e).__name__)
        tmp = tempfile.mkdtemp()
        try:
            path = await client.download_media(m, file=tmp + os.sep)
            return await retry(client.send_file, target, path, supports_streaming=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


async def send_post(post):
    media = sorted(post.media, key=lambda m: m.id)
    try:
        for i in range(0, len(media), 10):
            chunk = media[i:i + 10]
            try:
                res = await retry(client.send_file, target, [m.media for m in chunk])
                res = res if isinstance(res, list) else [res]
                pairs = list(zip(chunk, res))
            except Exception:
                log.exception("album failed, sending one by one")
                pairs = []
                for m in chunk:
                    pairs.append((m, await send_one(m)))
            for m, s in pairs:
                post.sent_media[m.id] = s
            if i + 10 < len(media):
                await asyncio.sleep(1.5)
        if post.text:
            formatted = safe_format(post.text, post.source)
            if formatted:
                post.sent_text = await retry(client.send_message, target, formatted)
                post.shown = formatted
    finally:
        post.sent = True


async def sender():
    while True:
        post = await queue.get()
        try:
            async with post.lock:
                if not post.cancelled:
                    await send_post(post)
        except Exception as e:
            log.exception("send failed")
            await notify(f"⚠️ [{post.source}] فشل إرسال منشور: {type(e).__name__}: {short(str(e), 200)}")
        finally:
            queue.task_done()
        await asyncio.sleep(0.5)


# =====================  تجميع المنشورات لكل قناة  =====================
async def reconcile(p):
    """يجيب من سيرفر تليجرام الوسائط الناقصة (اللي ما وصلت بالتحديثات الحية)."""
    ent = entities.get(p.source)
    if not ent:
        return
    try:
        have = {m.id for m in p.media}
        found = []
        if p.text_id and p.text_id not in have:
            # نص منفصل: كل الوسائط قبله مباشرة اللي لسا ما اننشرت
            msgs = await retry(client.get_messages, ent, limit=30, max_id=p.text_id)
            for m in msgs:                      # من الأحدث للأقدم
                if (p.source, m.id) in index or not is_media(m) or (m.raw_text or "").strip():
                    break
                if m.id not in have:
                    found.append(m)
        elif p.media:
            # نص كابشن داخل الألبوم: كمّل باقي صور نفس الألبوم
            groups = {m.grouped_id for m in p.media if m.grouped_id}
            if groups:
                lo, hi = min(have), max(have)
                msgs = await retry(client.get_messages, ent, limit=40, min_id=lo - 11, max_id=hi + 11)
                found = [m for m in msgs if m.grouped_id in groups and m.id not in have
                         and (p.source, m.id) not in index]
        if found:
            p.media.extend(found)
            await notify(f"🧩 [{p.source}] لقيت {len(found)} وسائط ناقصة ما وصلت بالتحديثات وضفتها للموديل")
    except Exception:
        log.exception("reconcile failed for %s", p.source)


async def drop_pending(ch, why):
    """يتجاهل وسائط بدون نص (ما بتنشر، فما في شي يتحذف من قناتك)."""
    p = ch.pending
    ch.pending = None
    if p and p.media and not p.text:
        await notify(f"🧹 [{ch.name}] تجاهلت {len(p.media)} وسائط بدون نص ({why}) — ما نشرتها")


async def flush(ch):
    """يُستدعى والقفل ممسوك."""
    p = ch.pending
    ch.pending = None
    if not p or (not p.media and not p.text):
        return
    if p.media and not p.text:      # وسائط بدون نص: ممنوع تنشر
        log.info("flush skipped: media without text [%s]", p.source)
        return
    await reconcile(p)
    if not p.media and not POST_TEXT_ONLY:
        return
    p.media.sort(key=lambda m: m.id)
    p.media_ids = {m.id for m in p.media}
    register(p)
    ch.recent.append(p)
    await queue.put(p)


def arm_timer(ch, p, delay):
    v = p.version

    async def run():
        await asyncio.sleep(delay)
        async with ch.lock:
            if ch.pending is p and p.version == v:
                if p.text:
                    await flush(ch)
                else:
                    await drop_pending(ch, f"ما إجا نص خلال {MEDIA_WAIT} ثانية")

    spawn(run())


def find_replaceable(ch):
    now = time.time()
    for post in reversed(ch.recent):
        if post.text_deleted and now < post.awaiting_until:
            return post
    return None


async def apply_text(post, mid, text):
    """القفل الخاص بالمنشور ممسوك. يطبّق نصاً جديداً/معدلاً."""
    post.text_id, post.text, post.text_deleted = mid, text, False
    add_key(post, mid)
    if not post.sent:
        return
    formatted = safe_format(text, post.source)
    if not formatted:
        return
    if post.sent_text:
        if formatted != post.shown:
            await retry(client.edit_message, target, post.sent_text.id, formatted)
            post.shown = formatted
    else:
        post.sent_text = await retry(client.send_message, target, formatted)
        post.shown = formatted


async def on_new(event):
    src = id_to_name.get(event.chat_id)
    if src:
        await process_new(src, event.message)


async def process_new(src, msg):
    ch = channels[src]
    if msg.id in ch.seen:
        return
    ch.seen.add(msg.id)
    if len(ch.seen) > 1000:
        ch.seen = set(sorted(ch.seen)[-500:])
    text = msg.raw_text or ""
    log.info("IN  [%s] id=%s group=%s media=%s text=%s | pending=%s | %s",
             src, msg.id, msg.grouped_id, type(msg.media).__name__ if msg.media else "-",
             bool(text.strip()),
             (f"{len(ch.pending.media)}m/{'T' if ch.pending.text else '-'}" if ch.pending else "none"),
             short(text, 40))
    if (src, msg.id) in index:   # وصلت متأخرة وانضافت للموديل أصلاً
        log.info("SKIP [%s] id=%s already posted", src, msg.id)
        return
    async with ch.lock:
        p = ch.pending
        if is_media(msg):
            same_album = bool(msg.grouped_id) and msg.grouped_id == p.last_group if p else False
            if p and p.text and not same_album:
                await flush(ch)
                p = None
            if p and not p.text and not same_album and time.time() - p.last_ts > MERGE_WINDOW:
                await drop_pending(ch, "وصلت وسائط موديل جديد وما إجا نص للقديم")
                p = None
            if p is None:
                p = ch.pending = Post(src)
            p.media.append(msg)
            p.last_ts = time.time()
            p.last_group = msg.grouped_id
            if text.strip():
                p.text, p.text_id = text, msg.id
            p.version += 1
            arm_timer(ch, p, CAPTION_WAIT if p.text else MEDIA_WAIT)
            return

        if not text.strip():
            return

        # رسالة نصية بدون وسائط
        if p and p.media and not p.text:
            p.text, p.text_id = text, msg.id
            p.version += 1
            await flush(ch)                      # النص وصل: انشر الموديل فوراً
            return
        if p:
            await flush(ch)

        post = find_replaceable(ch)              # المصدر حذف النص وبعث نص جديد؟
        if post:
            async with post.lock:
                await apply_text(post, msg.id, text)
            await notify(f"🔁 [{src}] وصل نص بديل (msg {msg.id}) → عدّلت نص منشورك\n{short(text)}")
            return

        np = Post(src)
        np.text, np.text_id = text, msg.id
        ch.pending = np
        await flush(ch)


async def on_edit(event):
    msg = event.message
    src = id_to_name.get(event.chat_id)
    if not src:
        return
    ch = channels[src]
    new_text = msg.raw_text or ""

    async with ch.lock:
        p = ch.pending
        if p and (msg.id == p.text_id or any(m.id == msg.id for m in p.media)):
            if msg.id == p.text_id and new_text != p.text:
                old = p.text
                p.text, p.text_id = (new_text, msg.id) if new_text.strip() else (None, None)
                p.version += 1
                await notify(f"✏️ [{src}] تعديل نص (msg {msg.id}) قبل النشر\nقبل: {short(old)}\nبعد: {short(new_text)}")
            elif new_text.strip() and not p.text:
                p.text, p.text_id = new_text, msg.id
                p.version += 1
            for i, m in enumerate(p.media):
                if m.id == msg.id:
                    p.media[i] = msg
            return

    post = index.get((src, msg.id))
    if not post:
        return
    async with post.lock:
        if msg.id == post.text_id:
            if new_text == post.text:
                return
            old = post.text
            if not new_text.strip():
                await mark_text_removed(post, msg.id)
                return
            await apply_text(post, msg.id, new_text)
            await notify(f"✏️ [{src}] تعديل نص (msg {msg.id}) → عدّلت منشورك\nقبل: {short(old)}\nبعد: {short(new_text)}")
        elif post.text_id is None and new_text.strip() and msg.id in post.media_ids:
            await apply_text(post, msg.id, new_text)
            await notify(f"✏️ [{src}] انضاف نص لموديل منشور (msg {msg.id}) → نشرت النص\n{short(new_text)}")


async def mark_text_removed(post, mid):
    post.text_deleted = True
    post.awaiting_until = time.time() + REPLACE_WINDOW
    if not post.sent:
        post.text, post.text_id = None, None
    spawn(expiry_notice(post, mid))
    await notify(f"🗑 [{post.source}] انحذف النص (msg {mid}) → بستنى نص بديل {REPLACE_WINDOW} ثانية")


async def expiry_notice(post, mid):
    await asyncio.sleep(REPLACE_WINDOW + 1)
    if post.text_deleted and not post.cancelled:
        async with post.lock:
            if not post.text_deleted:
                return
            if DELETE_TEXT_IF_NOT_REPLACED and post.sent_text:
                await retry(client.delete_messages, target, [post.sent_text.id])
                post.sent_text = None
                await notify(f"🗑 [{post.source}] ما إجا نص بديل، حذفت النص من قناتك")
            else:
                await notify(f"ℹ️ [{post.source}] ما إجا نص بديل لـ msg {mid}، تركت النص الحالي")


async def on_delete(event):
    src = id_to_name.get(event.chat_id)
    if not src:
        return
    ch = channels[src]
    for mid in event.deleted_ids:
        touched = False
        async with ch.lock:
            p = ch.pending
            if p:
                if mid == p.text_id:
                    p.text, p.text_id = None, None
                    p.version += 1
                    touched = True
                    await notify(f"🗑 [{src}] انحذف النص (msg {mid}) قبل النشر")
                if any(m.id == mid for m in p.media):
                    p.media = [m for m in p.media if m.id != mid]
                    p.version += 1
                    touched = True
                    await notify(f"🗑 [{src}] انحذفت وسائط (msg {mid}) قبل النشر")
                    if not p.media and not p.text:
                        ch.pending = None
        if touched:
            continue
        post = index.get((src, mid))
        if post:
            async with post.lock:
                await handle_deleted(post, mid)


async def handle_deleted(post, mid):
    is_text = mid == post.text_id
    if mid in post.media_ids:
        post.media_ids.discard(mid)
        if post.sent:
            sent = post.sent_media.pop(mid, None)
            if sent:
                await retry(client.delete_messages, target, [sent.id])
        else:
            post.media = [m for m in post.media if m.id != mid]
        await notify(f"🗑 [{post.source}] انحذفت وسائط (msg {mid}) → حذفتها من قناتك")
    if is_text:
        post.text_deleted = True
        post.awaiting_until = time.time() + REPLACE_WINDOW
        if not post.sent:
            post.text, post.text_id = None, None

    gone = not post.media_ids and (post.text_deleted or post.text_id is None)
    if gone:
        post.cancelled = True
        if post.sent:
            ids = [s.id for s in post.sent_media.values()]
            if post.sent_text:
                ids.append(post.sent_text.id)
            if ids:
                await retry(client.delete_messages, target, ids)
        for k in post.keys:
            index.pop(k, None)
        await notify(f"🗑 [{post.source}] انحذف الموديل كاملاً من المصدر → حذفته من قناتك")
    elif is_text:
        spawn(expiry_notice(post, mid))
        await notify(f"🗑 [{post.source}] انحذف النص (msg {mid}) → بستنى نص بديل {REPLACE_WINDOW} ثانية")


async def poller():
    """شبكة أمان: كل فترة بيسأل تليجرام مباشرة عن آخر رسائل كل قناة، وبيعالج أي رسالة ما وصلت بالتحديثات الحية."""
    await asyncio.sleep(POLL_SECONDS)
    while True:
        for src, ch in channels.items():
            try:
                msgs = await retry(client.get_messages, entities[src], limit=30)
                now = datetime.now(timezone.utc)
                fresh = sorted(
                    (m for m in msgs if m.id > ch.baseline and m.id not in ch.seen
                     and (now - m.date).total_seconds() > POLL_MIN_AGE),
                    key=lambda m: m.id)
                for m in fresh:
                    await notify(f"🛟 [{src}] التقطت رسالة (id {m.id}) ما وصلت بالتحديثات الحية")
                    await process_new(src, m)
            except Exception:
                log.exception("poll failed for %s", src)
        await asyncio.sleep(POLL_SECONDS)


# =====================  التشغيل  =====================
async def main():
    global target, queue
    queue = asyncio.Queue()
    await client.start()
    target = await client.get_entity(TARGET_CHANNEL)

    for name in SOURCES:
        try:
            ent = await client.get_entity(name)
            id_to_name[utils.get_peer_id(ent)] = name
            entities[name] = ent
            channels[name] = Chan(name)
            last = await client.get_messages(ent, limit=1)
            channels[name].baseline = last[0].id if last else 0
        except Exception:
            log.exception("cannot resolve source %s", name)

    chats = list(id_to_name)
    client.add_event_handler(on_new, events.NewMessage(chats=chats))
    client.add_event_handler(on_edit, events.MessageEdited(chats=chats))
    client.add_event_handler(on_delete, events.MessageDeleted())

    spawn(sender())
    spawn(poller())
    log.info("🔥 BOT STARTED — watching: %s", ", ".join(id_to_name.values()))
    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())
