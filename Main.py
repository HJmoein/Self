import asyncio
import html
import re
import tempfile
import time
from collections import defaultdict, deque

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.functions.stories import GetStoriesByIDRequest
from config import API_ID, API_HASH, SESSION_NAME


client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

tasks = {}
self_enabled = True
current_language = "fa"
timed_save_enabled = False
deleted_save_enabled = False
message_cache = defaultdict(lambda: deque(maxlen=1000))
message_index = defaultdict(set)
deleted_messages = defaultdict(list)

STORY_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?P<username>[A-Za-z0-9_]+)/s/(?P<story_id>\d+)/?$"
)

CHANNEL_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?:(?P<username>[A-Za-z0-9_]+)|c/(?P<private_id>\d+))/(?P<message_id>\d+)/?$"
)

STORY_COMMAND = "دانلود استوری"
PERSIAN_HELP_COMMANDS = ("راهنما", "دستورات")
ARABIC_HELP_COMMANDS = ("مساعدة", "الأوامر")


def localized_text(text):
    if current_language != "ar":
        return text

    replacements = (
        ("ذخیره پیام‌های حذف‌شده روشن شد", "تم تشغيل حفظ الرسائل المحذوفة"),
        ("ذخیره پیام‌های حذف‌شده خاموش شد", "تم إيقاف حفظ الرسائل المحذوفة"),
        ("ذخیره پیام‌های زمان‌دار از قبل روشن است", "حفظ الرسائل المؤقتة مفعّل بالفعل"),
        ("ذخیره پیام‌های زمان‌دار روشن شد", "تم تشغيل حفظ الرسائل المؤقتة"),
        ("ذخیره پیام‌های زمان‌دار روشن نیست", "حفظ الرسائل المؤقتة غير مفعّل"),
        ("ذخیره پیام‌های زمان‌دار خاموش شد", "تم إيقاف حفظ الرسائل المؤقتة"),
        ("میو خودکار از قبل روشنه", "ميو مفعّل بالفعل"),
        ("میو خودکار روشن", "تم تشغيل ميو"),
        ("میو خودکار خاموش شد", "تم إيقاف ميو"),
        ("میو خودکار روشن نیست", "ميو غير مفعّل"),
        ("در حال بررسی...", "جارٍ الفحص..."),
        ("پینگ", "الاستجابة"),
        ("فرمت درست:", "الصيغة الصحيحة:"),
        ("در حال دانلود استوری...", "جارٍ تحميل القصة..."),
        ("دانلود استوری شروع شد", "بدأ تحميل القصة"),
        ("دانلود پست کانال شروع شد", "بدأ تحميل منشور القناة"),
        ("دانلود استوری انجام نشد", "فشل تحميل القصة"),
        ("دانلود پیام کانال انجام نشد", "فشل تحميل رسالة القناة"),
        ("دانلود این استوری ممکن نیست", "لا يمكن تحميل هذه القصة"),
        ("روی استوری یا پیام استوری ریپلای کن و دوباره بنویس", "قم بالرد على القصة أو رسالة القصة ثم أرسل مرة أخرى"),
        ("اطلاعات این کاربر پیدا نشد", "لم يتم العثور على معلومات هذا المستخدم"),
        ("برای گرفتن آیدی، روی پیام شخص ریپلای کن و بنویس", "للحصول على المعرف، قم بالرد على رسالة الشخص واكتب"),
        ("اطلاعات کاربر", "معلومات المستخدم"),
        ("اطلاعات مالک", "معلومات المالك"),
        ("نام:", "الاسم:"),
        ("یوزرنیم:", "اسم المستخدم:"),
        ("نداره", "لا يوجد"),
        ("آیدی عددی:", "المعرف الرقمي:"),
        ("فرمت درست لینک", "صيغة الرابط الصحيحة"),
        ("استوری دانلود شد", "تم تحميل القصة"),
        ("در حال دانلود...", "جارٍ التحميل..."),
    )

    for source, target in replacements:
        text = text.replace(source, target)
    return text


async def edit_response(event, text, **kwargs):
    await event.edit(localized_text(text), **kwargs)


def message_snapshot(message, sender=None):
    sender = sender or getattr(message, "sender", None)
    first_name = getattr(sender, "first_name", None) or ""
    last_name = getattr(sender, "last_name", None) or ""
    sender_name = f"{first_name} {last_name}".strip()
    sender_name = sender_name or getattr(sender, "title", None) or "بدون نام"
    sender_username = getattr(sender, "username", None)

    return {
        "id": message.id,
        "date": message.date,
        "sender_id": message.sender_id,
        "sender_name": sender_name or str(message.sender_id or "نامشخص"),
        "sender_username": sender_username,
        "text": message.message or "",
        "has_media": bool(message.media),
        "message": message,
    }


def is_timed_message(message):
    media = getattr(message, "media", None)
    media_file = getattr(media, "document", None) or getattr(media, "photo", None)
    return bool(
        getattr(message, "ttl_period", None)
        or getattr(message, "ttl_seconds", None)
        or getattr(media, "ttl_seconds", None)
        or getattr(media_file, "ttl_seconds", None)
    )


async def save_timed_message(message):
    if not message.media:
        return

    try:
        with tempfile.TemporaryDirectory(prefix="timed_message_") as folder:
            file_path = await run_with_floodwait(
                lambda: client.download_media(message, file=folder)
            )

            if not file_path:
                return

            await run_with_floodwait(
                lambda: client.send_file(
                    "me",
                    file_path,
                    caption="پیام زمان‌دار ذخیره شد ✅",
                )
            )
    except Exception:
        pass


def deleted_message_caption(item):
    sender = item["sender_name"]
    if item["sender_username"]:
        sender += f" (@{item['sender_username']})"
    elif item["sender_id"]:
        sender += f" | آیدی عددی: {item['sender_id']}"

    return f"پیام حذف‌شده\nفرستنده: {sender}"


async def save_deleted_message(item):
    caption = deleted_message_caption(item)
    original_message = item["message"]

    try:
        if original_message.media:
            await run_with_floodwait(
                lambda: client.send_file(
                    "me",
                    original_message.media,
                    caption=caption + "\n\n" + (item["text"] or ""),
                )
            )
        else:
            await run_with_floodwait(
                lambda: client.send_message(
                    "me",
                    caption + "\n\n" + (item["text"] or "[بدون متن]"),
                )
            )
    except Exception:
        await run_with_floodwait(
            lambda: client.send_message(
                "me",
                caption + "\n\n" + (item["text"] or "[مدیا قابل بازیابی نبود]"),
            )
        )


async def send_deleted_messages_report(chat_id):
    messages = deleted_messages[chat_id]

    if len(messages) <= 10:
        return

    deleted_messages[chat_id] = []
    rows = []

    for item in messages:
        date_text = item["date"].strftime("%Y-%m-%d %H:%M:%S") if item["date"] else "نامشخص"
        content = item["text"] or "[پیام بدون متن]"
        if item["has_media"]:
            content += "\n[پیام دارای مدیا]"

        rows.append(
            "<article>"
            f"<h3>پیام {item['id']}</h3>"
            f"<p class=\"meta\">فرستنده: {html.escape(deleted_message_caption(item))} | "
            f"زمان: {html.escape(date_text)}</p>"
            f"<pre>{html.escape(content)}</pre>"
            "</article>"
        )

    report = (
        "<!doctype html><html lang=\"fa\" dir=\"rtl\"><head>"
        "<meta charset=\"utf-8\"><title>پیام‌های حذف‌شده</title>"
        "<style>body{font-family:Tahoma,sans-serif;max-width:900px;margin:32px auto;"
        "padding:0 16px;background:#f4f6f8;color:#17202a}article{background:#fff;"
        "border:1px solid #d9e0e7;border-radius:8px;padding:16px;margin:12px 0}"
        "h3{margin:0 0 8px}.meta{color:#637381;font-size:13px}pre{white-space:pre-wrap;"
        "font:inherit;line-height:1.8}</style></head><body>"
        f"<h1>پیام‌های حذف‌شده ({len(messages)})</h1>"
        + "".join(rows)
        + "</body></html>"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".html", prefix="deleted_messages_", delete=False
    ) as report_file:
        report_file.write(report)
        report_path = report_file.name

    try:
        await run_with_floodwait(
            lambda: client.send_file(
                "me",
                report_path,
                caption=f"گزارش {len(messages)} پیام حذف‌شده ✅",
            )
        )
    finally:
        try:
            import os
            os.remove(report_path)
        except OSError:
            pass


async def meow_loop(chat_id):
    try:
        while True:
            await asyncio.sleep(300)
            await client.send_message(chat_id, "میو")
    except asyncio.CancelledError:
        pass


async def show_help(event):
    if current_language == "ar":
        help_text = (
            "╭──────────────╮\n"
            "│ <b>أوامر السلف</b> │\n"
            "╰──────────────╯\n\n"
            "⚙ <b>السلف</b>\n"
            "├ <code>.سلف تشغيل</code> تشغيل السلف\n"
            "└ <code>.سلف إيقاف</code> إيقاف السلف\n\n"
            "🌐 <b>اللغة</b>\n"
            "├ <code>.اللغة الفارسية</code> الفارسية\n"
            "└ <code>.اللغة العربية</code> العربية\n\n"
            "🐾 <b>ميو</b>\n"
            "├ <code>.ميو تشغيل</code> تشغيل ميو\n"
            "└ <code>.ميو إيقاف</code> إيقاف ميو\n\n"
            "🗃 <b>حفظ الرسائل المحذوفة</b>\n"
            "├ <code>.حفظ تلقائي تشغيل</code> حفظ الوسائط المؤقتة\n"
            "├ <code>.حفظ تلقائي إيقاف</code> إيقاف حفظ الوسائط المؤقتة\n"
            "├ <code>.حفظ تلقائي المحذوفات تشغيل</code> حفظ المحذوفات\n"
            "└ <code>.حفظ تلقائي المحذوفات إيقاف</code> إيقاف حفظ المحذوفات\n\n"
            "🛠 <b>الأدوات</b>\n"
            "├ <code>.بنغ</code> فحص سرعة الاستجابة\n"
            "├ <code>.معرف</code> معرف المستخدم بالرد\n"
            "└ <code>.معرفي</code> معرف حسابي"
        )
    else:
        help_text = (
        "╭──────────────╮\n"
        "│ <b>دستورات سلف</b> │\n"
        "╰──────────────╯\n\n"
        "⚙ <b>سلف</b>\n"
        "├ <code>.سلف روشن</code> روشن‌کردن سلف\n"
        "└ <code>.سلف خاموش</code> خاموش‌کردن سلف\n\n"
        "🌐 <b>زبان</b>\n"
        "├ <code>.زبان فارسی</code> فارسی\n"
        "└ <code>.زبان عربی</code> عربی\n\n"
        "🐾 <b>میو</b>\n"
        "├ <code>.میو روشن</code>  روشن‌کردن میو\n"
        "└ <code>.میو خاموش</code> خاموش‌کردن میو\n\n"
        "🗃 <b>ذخیره پیام‌های حذف‌شده</b>\n"
        "├ <code>.سیو خودکار روشن</code> ذخیره پیام‌های زمان‌دار\n"
        "├ <code>.سیو خودکار خاموش</code> خاموش‌کردن ذخیره پیام‌های زمان‌دار\n"
        "├ <code>.سیو خودکار پیام حذف شده روشن</code> فعال‌سازی گزارش حذف\n"
        "└ <code>.سیو خودکار پیام حذف شده خاموش</code> غیرفعال‌سازی گزارش حذف\n\n"
        "🛠 <b>ابزارها</b>\n"
        "├ <code>.پینگ</code>  بررسی زمان پاسخ\n"
        "├ <code>.آیدی</code>  آیدی فرد با ریپلای\n"
        "└ <code>.ایدیم</code>  اطلاعات آیدی خودم\n\n"
        "📥 <b>دانلود</b>\n"
        "├ <code>.دانلود استوری لینک</code>\n"
        "└ <code>.دانلود چنل لینک</code>"
        )
    await event.edit(help_text, parse_mode="html")


async def show_user_id(event):
    reply = await event.get_reply_message()

    if reply is None:
        await edit_response(
            event,
            "برای گرفتن آیدی، روی پیام شخص ریپلای کن و بنویس: .آیدی"
        )
        return

    user = await reply.get_sender()

    if user is None:
        await edit_response(event, "اطلاعات این کاربر پیدا نشد.")
        return

    first_name = getattr(user, "first_name", None) or "بدون نام"
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    username = getattr(user, "username", None)
    username_text = f"@{username}" if username else "نداره"

    await edit_response(
        event,
        "🆔 <b>اطلاعات کاربر</b>\n\n"
        f"👤 نام: {full_name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🔢 آیدی عددی: <code>{user.id}</code>",
        parse_mode="html",
    )


async def show_my_id(event):
    user = await client.get_me()

    first_name = getattr(user, "first_name", None) or "بدون نام"
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    username = getattr(user, "username", None)
    username_text = f"@{username}" if username else "نداره"

    if current_language == "ar":
        await event.edit(
            "🆔 <b>معلومات المالك</b>\n\n"
            f"👤 الاسم: {full_name}\n"
            f"🔗 اسم المستخدم: {username_text}\n"
            f"🔢 المعرف الرقمي: <code>{user.id}</code>",
            parse_mode="html",
        )
    else:
        await event.edit(
            "🆔 <b>اطلاعات مالک</b>\n\n"
            f"👤 نام: {full_name}\n"
            f"🔗 یوزرنیم: {username_text}\n"
            f"🔢 آیدی عددی: <code>{user.id}</code>",
            parse_mode="html",
        )


async def run_with_floodwait(operation):
    while True:
        try:
            return await operation()
        except FloodWaitError as error:
            await asyncio.sleep(error.seconds)


def progress_text(downloaded, total, frame, title="دانلود"):
    percent = int(downloaded * 100 / total) if total else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)
    return f"{frame} {localized_text(title)}\n[{bar}] {percent}%"


# =========================================================
# بهینه‌شده
# =========================================================

async def download_story_link(chat_id, link, status_message=None):
    match = STORY_LINK_PATTERN.match(link.strip())

    if match is None:
        return "لینک معتبر استوری نیست. نمونه: https://t.me/username/s/123"

    username = match.group("username")
    story_id = int(match.group("story_id"))

    try:
        peer = await client.get_input_entity(username)

        result = await run_with_floodwait(
            lambda: client(
                GetStoriesByIDRequest(
                    peer=peer,
                    id=[story_id]
                )
            )
        )

        if not result.stories:
            return "این استوری پیدا نشد یا دیگر در دسترس نیست."

        story = result.stories[0]

        if not story.media:
            return "این استوری فایل قابل دانلود ندارد."

        last_update = 0.0
        frames = ("⏳", "⌛", "🔄", "✨")
        frame_index = 0

        def show_progress(downloaded, total):
            nonlocal last_update, frame_index

            if status_message is None or not total:
                return

            now = time.monotonic()

            # جلوگیری از ویرایش بیش از حد پیام
            if now - last_update < 2:
                return

            last_update = now

            message = progress_text(
                downloaded,
                total,
                frames[frame_index % len(frames)],
                title="دانلود استوری",
            )

            frame_index += 1

            asyncio.create_task(
                status_message.edit(message)
            )

        with tempfile.TemporaryDirectory(
            prefix="meow_story_"
        ) as folder:

            # دانلود استوری
            file_path = await run_with_floodwait(
                lambda: client.download_media(
                    story.media,
                    file=folder,
                    progress_callback=show_progress,
                )
            )

            if not file_path:
                return "دانلود استوری انجام نشد."

            # آپلود به تلگرام
            await run_with_floodwait(
                lambda: client.send_file(
                    chat_id,
                    file_path,
                    caption="استوری دانلود شد ✅",
                    part_size_kb=512,
                    supports_streaming=True,
                )
            )

        return None

    except Exception as error:
        return f"دانلود استوری انجام نشد: {type(error).__name__}"


# =========================================================
# دانلود پیام کانال
# =========================================================

async def download_channel_message(chat_id, link, status_message=None):
    match = CHANNEL_LINK_PATTERN.match(link.strip())

    if match is None:
        return "لینک معتبر پیام کانال نیست."

    username = match.group("username")
    private_id = match.group("private_id")
    message_id = int(match.group("message_id"))

    try:
        if private_id:
            entity = int(f"-100{private_id}")
        else:
            entity = username

        message = await run_with_floodwait(
            lambda: client.get_messages(
                entity,
                ids=message_id
            )
        )

        if message is None:
            return "این پیام پیدا نشد یا دسترسی به آن وجود ندارد."

        channel_entity = await run_with_floodwait(
            lambda: client.get_entity(entity)
        )

        channel_name = (
            getattr(channel_entity, "title", None)
            or getattr(channel_entity, "username", None)
            or str(entity)
        )

        author_name = getattr(
            message,
            "post_author",
            None
        )

        if not author_name:
            try:
                sender = await message.get_sender()

                author_name = (
                    getattr(sender, "title", None)
                    or getattr(sender, "first_name", None)
                    or getattr(sender, "username", None)
                )
            except Exception:
                author_name = None

        author_name = author_name or channel_name

        message_info = (
            f"📣 کانال: {channel_name}\n"
            f"👤 منتشرکننده: {author_name}\n\n"
        )

        caption = message_info + (message.message or "")

        if message.media:
            last_update = 0.0
            frames = ("⏳", "⌛", "🔄", "✨")
            frame_index = 0

            def show_progress(downloaded, total):
                nonlocal last_update, frame_index

                now = time.monotonic()

                if status_message is None or now - last_update < 2:
                    return

                last_update = now

                progress = progress_text(
                    downloaded,
                    total,
                    frames[frame_index % len(frames)],
                    title="دانلود پست کانال",
                )

                frame_index += 1

                asyncio.create_task(
                    status_message.edit(progress)
                )

            with tempfile.TemporaryDirectory(
                prefix="channel_download_"
            ) as folder:

                file_path = await run_with_floodwait(
                    lambda: client.download_media(
                        message,
                        file=folder,
                        progress_callback=show_progress,
                    )
                )

                if not file_path:
                    return "دانلود مدیا انجام نشد."

                await run_with_floodwait(
                    lambda: client.send_file(
                        chat_id,
                        file_path,
                        caption=caption,
                    )
                )

        elif message.message:
            await run_with_floodwait(
                lambda: client.send_message(
                    chat_id,
                    message_info + message.message
                )
            )

        else:
            return "این پیام متن یا مدیای قابل دانلود ندارد."

        return None

    except Exception as error:
        return f"دانلود پیام کانال انجام نشد: {type(error).__name__}"


# =========================================================
# Handler
# =========================================================

@client.on(events.NewMessage)
async def cache_messages(event):
    if event.is_private and event.chat_id is not None and event.message is not None:
        sender = getattr(event.message, "sender", None)
        if sender is None and event.message.sender_id is not None:
            try:
                sender = await event.get_sender()
            except Exception:
                sender = None

        message_cache[event.chat_id].append(
            message_snapshot(event.message, sender)
        )
        message_index[event.message.id].add(event.chat_id)

        if timed_save_enabled and is_timed_message(event.message):
            asyncio.create_task(save_timed_message(event.message))


@client.on(events.MessageDeleted)
async def deleted_message_handler(event):
    if not deleted_save_enabled:
        return

    chat_ids = set()

    if event.chat_id is not None:
        chat_ids.add(event.chat_id)
    else:
        for message_id in event.deleted_ids:
            chat_ids.update(message_index.get(message_id, set()))

    for chat_id in chat_ids:
        cached = {item["id"]: item for item in message_cache[chat_id]}
        removed = [
            cached[message_id]
            for message_id in event.deleted_ids
            if message_id in cached
        ]

        if not removed:
            continue

        deleted_messages[chat_id].extend(removed)

        for item in removed:
            await save_deleted_message(item)

        if len(deleted_messages[chat_id]) > 10:
            await send_deleted_messages_report(chat_id)

@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    global current_language, deleted_save_enabled, self_enabled, timed_save_enabled

    text = event.raw_text.strip()
    chat_id = event.chat_id

    if not text.startswith("."):
        return

    text = text[1:].strip()

    if text in (("سلف تشغيل", "السلف تشغيل") if current_language == "ar" else ("سلف روشن",)):
        self_enabled = True
        await event.edit(
            "السلف تم تشغيله ✅" if current_language == "ar" else "سلف روشن شد ✅"
        )
        return

    if text in (("سلف إيقاف", "السلف إيقاف") if current_language == "ar" else ("سلف خاموش",)):
        self_enabled = False
        await event.edit(
            "السلف تم إيقافه" if current_language == "ar" else "سلف خاموش شد"
        )
        return

    if text in ("زبان فارسی", "اللغة الفارسية", "اللغة فارسی"):
        current_language = "fa"
        await event.edit("زبان فارسی فعال شد ✅")
        return

    if text in ("زبان عربی", "اللغة العربية", "اللغة عربی"):
        current_language = "ar"
        await event.edit("تم تفعيل اللغة العربية ✅")
        return

    if not self_enabled:
        return

    if text in (
        (
            "حفظ تلقائي المحذوفات تشغيل",
        )
        if current_language == "ar"
        else (
            "سیو خودکار پیام حذف شده روشن",
            "سیو خودکار پیام های حذف شده روشن",
            "سیو خودکار پیام‌های حذف‌شده روشن",
        )
    ):
        deleted_save_enabled = True
        await edit_response(event, "ذخیره پیام‌های حذف‌شده روشن شد ✅")
        return

    if text in (
        (
            "حفظ تلقائي المحذوفات إيقاف",
        )
        if current_language == "ar"
        else (
            "سیو خودکار پیام حذف شده خاموش",
            "سیو خودکار پیام های حذف شده خاموش",
            "سیو خودکار پیام‌های حذف‌شده خاموش",
        )
    ):
        deleted_save_enabled = False
        await edit_response(event, "ذخیره پیام‌های حذف‌شده خاموش شد")
        return

    if text in (
        ("حفظ تلقائي تشغيل",)
        if current_language == "ar"
        else ("سیو خودکار روشن", "سیو خودکار تایم دار روشن")
    ):
        if timed_save_enabled:
            await edit_response(event, "ذخیره پیام‌های زمان‌دار از قبل روشن است.")
            return

        timed_save_enabled = True
        await edit_response(event, "ذخیره پیام‌های زمان‌دار روشن شد ✅")
        return

    if text in (
        ("حفظ تلقائي إيقاف",)
        if current_language == "ar"
        else ("سیو خودکار خاموش", "سیو خودکار تایم دار خاموش")
    ):
        if not timed_save_enabled:
            await edit_response(event, "ذخیره پیام‌های زمان‌دار روشن نیست")
            return

        timed_save_enabled = False
        await edit_response(event, "ذخیره پیام‌های زمان‌دار خاموش شد")
        return

    if text in (
        ARABIC_HELP_COMMANDS
        if current_language == "ar"
        else PERSIAN_HELP_COMMANDS
    ):
        await show_help(event)
        return

    if text in (("معرف",) if current_language == "ar" else ("آیدی", "ایدی")):
        await show_user_id(event)
        return

    if text in (
        ("معرفي",)
        if current_language == "ar"
        else ("ایدیم", "آیدی من", "ایدی من", "معرفی")
    ):
        await show_my_id(event)
        return

    if text.startswith("دانلود چنل "):
        link = text[len("دانلود چنل "):].strip()

        await edit_response(
            event,
            "⏳ دانلود پست کانال شروع شد...\n"
            "[░░░░░░░░░░] 0%"
        )

        error_message = await download_channel_message(
            chat_id,
            link,
            event
        )

        if error_message:
            await edit_response(event, error_message)
        else:
            await event.delete()

        return

    if text.startswith(STORY_COMMAND + " "):
        link = text[len(STORY_COMMAND):].strip()

        if not STORY_LINK_PATTERN.match(link):
            await edit_response(
                event,
                "فرمت درست:\n"
                ".دانلود استوری https://t.me/username/s/123"
            )
            return

        await edit_response(
            event,
            "⏳ دانلود استوری شروع شد...\n"
            "[░░░░░░░░░░] 0%"
        )

        error_message = await download_story_link(
            chat_id,
            link,
            event
        )

        if error_message:
            await edit_response(event, error_message)
        else:
            await event.delete()

        return

    if text in (("ميو تشغيل",) if current_language == "ar" else ("میو روشن",)):
        if chat_id in tasks:
            await edit_response(event, "میو خودکار از قبل روشنه")
            return

        tasks[chat_id] = asyncio.create_task(
            meow_loop(chat_id)
        )

        await edit_response(event, "میو خودکار روشن")

    elif text in (("ميو إيقاف",) if current_language == "ar" else ("میو خاموش",)):
        task = tasks.pop(chat_id, None)

        if task:
            task.cancel()
            await edit_response(event, "میو خودکار خاموش شد")
        else:
            await edit_response(event, "میو خودکار روشن نیست")

    elif text in (("بنغ",) if current_language == "ar" else ("پینگ",)):
        start = time.perf_counter()

        await edit_response(event, "در حال بررسی...")

        ping = (time.perf_counter() - start) * 1000

        await edit_response(
            event,
            f"پینگ : {ping:.0f}ms"
        )

    elif text in ("استوری دانلود", "دانلود استوری"):
        reply = await event.get_reply_message()

        if reply is None or not reply.media:
            await edit_response(
                event,
                "روی استوری یا پیام استوری ریپلای کن و دوباره بنویس: "
                ".استوری دانلود"
            )
            return

        await edit_response(
            event,
            "در حال دانلود استوری... ⏳"
        )

        try:
            with tempfile.TemporaryDirectory(
                prefix="meow_story_"
            ) as folder:

                file_path = await client.download_media(
                    reply,
                    file=folder
                )

                if not file_path:
                    await edit_response(
                        event,
                        "دانلود این استوری ممکن نیست."
                    )
                    return

                await client.send_file(
                    chat_id,
                    file_path,
                    caption="استوری دانلود شد ✅"
                )

            await event.delete()

        except Exception as error:
            await edit_response(
                event,
                f"دانلود استوری انجام نشد: {type(error).__name__}"
            )


# =========================================================
# Main
# =========================================================

async def main():
    await client.start()

    print("Meow SelfBot is running...")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
