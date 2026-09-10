import asyncio
import re
import tempfile
import time

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.functions.stories import GetStoriesByIDRequest
from config import API_ID, API_HASH, SESSION_NAME


client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

tasks = {}

STORY_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?P<username>[A-Za-z0-9_]+)/s/(?P<story_id>\d+)/?$"
)

CHANNEL_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?:(?P<username>[A-Za-z0-9_]+)|c/(?P<private_id>\d+))/(?P<message_id>\d+)/?$"
)

STORY_COMMAND = "دانلود استوری"
HELP_COMMANDS = ("راهنما", "دستورات")


async def meow_loop(chat_id):
    try:
        while True:
            await asyncio.sleep(300)
            await client.send_message(chat_id, "میو")
    except asyncio.CancelledError:
        pass


async def show_help(event):
    help_text = (
        "╭──────────────╮\n"
        "│ <b>دستورات سلف</b> │\n"
        "╰──────────────╯\n\n"
        "🐾 <b>میو</b>\n"
        "├ <code>.میو روشن</code>  روشن‌کردن میو\n"
        "└ <code>.میو خاموش</code> خاموش‌کردن میو\n\n"
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
        await event.edit(
            "برای گرفتن آیدی، روی پیام شخص ریپلای کن و بنویس: .آیدی"
        )
        return

    user = await reply.get_sender()

    if user is None:
        await event.edit("اطلاعات این کاربر پیدا نشد.")
        return

    first_name = getattr(user, "first_name", None) or "بدون نام"
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    username = getattr(user, "username", None)
    username_text = f"@{username}" if username else "نداره"

    await event.edit(
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

    return f"{frame} {title}\n[{bar}] {percent}%"


def upload_progress_text(downloaded, total, speed):
    percent = int(downloaded * 100 / total) if total else 0

    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)

    if speed >= 1024 * 1024:
        speed_text = f"{speed / (1024 * 1024):.2f} MB/s"
    elif speed >= 1024:
        speed_text = f"{speed / 1024:.2f} KB/s"
    else:
        speed_text = f"{speed:.0f} B/s"

    return (
        "📤 <b>در حال ارسال استوری</b>\n"
        f"[{bar}] {percent}%\n"
        f"⚡ سرعت: {speed_text}"
    )


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

        # -------------------------
        # Download progress
        # -------------------------

        last_update = 0.0
        frames = ("⏳", "⌛", "🔄", "✨")
        frame_index = 0

        def download_progress(downloaded, total):
            nonlocal last_update, frame_index

            if status_message is None or not total:
                return

            now = time.monotonic()

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

            file_path = await run_with_floodwait(
                lambda: client.download_media(
                    story.media,
                    file=folder,
                    progress_callback=download_progress,
                )
            )

            if not file_path:
                return "دانلود استوری انجام نشد."

            # -------------------------
            # Download finished
            # -------------------------

            if status_message is not None:
                try:
                    await status_message.edit(
                        "📤 <b>در حال ارسال استوری...</b>\n"
                        "[░░░░░░░░░░] 0%\n"
                        "⚡ سرعت: محاسبه..."
                    )
                except Exception:
                    pass

            # -------------------------
            # Upload progress
            # -------------------------

            upload_start = time.monotonic()
            last_uploaded = 0
            last_upload_time = upload_start
            last_upload_update = 0.0

            def upload_progress(current, total):
                nonlocal last_upload_update
                nonlocal last_uploaded
                nonlocal last_upload_time

                if status_message is None or not total:
                    return

                now = time.monotonic()

                # آپدیت پیام هر 2 ثانیه
                if now - last_upload_update < 2:
                    return

                elapsed = now - upload_start

                if elapsed <= 0:
                    return

                # سرعت میانگین واقعی آپلود
                speed = current / elapsed

                last_upload_update = now
                last_uploaded = current
                last_upload_time = now

                message = upload_progress_text(
                    current,
                    total,
                    speed
                )

                asyncio.create_task(
                    status_message.edit(
                        message,
                        parse_mode="html"
                    )
                )

            # -------------------------
            # Upload
            # -------------------------

            await run_with_floodwait(
                lambda: client.send_file(
                    chat_id,
                    file_path,
                    caption="استوری دانلود شد ✅",
                    part_size_kb=512,
                    supports_streaming=True,
                    progress_callback=upload_progress,
                )
            )

        return None

    except Exception as error:
        return f"دانلود استوری انجام نشد: {type(error).__name__}"


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


@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    text = event.raw_text.strip()
    chat_id = event.chat_id

    if not text.startswith("."):
        return

    text = text[1:].strip()

    if text in HELP_COMMANDS:
        await show_help(event)
        return

    if text in ("آیدی", "ایدی"):
        await show_user_id(event)
        return

    if text in ("ایدیم", "آیدی من", "ایدی من"):
        await show_my_id(event)
        return

    if text.startswith("دانلود چنل "):
        link = text[len("دانلود چنل "):].strip()

        await event.edit(
            "⏳ دانلود پست کانال شروع شد...\n"
            "[░░░░░░░░░░] 0%"
        )

        error_message = await download_channel_message(
            chat_id,
            link,
            event
        )

        if error_message:
            await event.edit(error_message)
        else:
            await event.delete()

        return

    if text.startswith(STORY_COMMAND + " "):
        link = text[len(STORY_COMMAND):].strip()

        if not STORY_LINK_PATTERN.match(link):
            await event.edit(
                "فرمت درست:\n"
                ".دانلود استوری https://t.me/username/s/123"
            )
            return

        await event.edit(
            "⏳ دانلود استوری شروع شد...\n"
            "[░░░░░░░░░░] 0%"
        )

        error_message = await download_story_link(
            chat_id,
            link,
            event
        )

        if error_message:
            await event.edit(error_message)
        else:
            await event.delete()

        return

    if text == "میو روشن":
        if chat_id in tasks:
            await event.edit("میو خودکار از قبل روشنه")
            return

        tasks[chat_id] = asyncio.create_task(
            meow_loop(chat_id)
        )

        await event.edit("میو خودکار روشن")

    elif text == "میو خاموش":
        task = tasks.pop(chat_id, None)

        if task:
            task.cancel()
            await event.edit("میو خودکار خاموش شد")
        else:
            await event.edit("میو خودکار روشن نیست")

    elif text == "پینگ":
        start = time.perf_counter()

        await event.edit("در حال بررسی...")

        ping = (time.perf_counter() - start) * 1000

        await event.edit(
            f"پینگ : {ping:.0f}ms"
        )

    elif text in ("استوری دانلود", "دانلود استوری"):
        reply = await event.get_reply_message()

        if reply is None or not reply.media:
            await event.edit(
                "روی استوری یا پیام استوری ریپلای کن و دوباره بنویس: "
                ".استوری دانلود"
            )
            return

        await event.edit(
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
                    await event.edit(
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
            await event.edit(
                f"دانلود استوری انجام نشد: {type(error).__name__}"
            )


async def main():
    await client.start()

    print("Meow SelfBot is running...")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
