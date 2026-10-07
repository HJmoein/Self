"""Telegram feature services: archival, media retrieval, and heart animation."""

import asyncio
import base64
import html
import math
import os
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageOps
from telethon.errors import RPCError
from telethon.tl.functions.stories import GetStoriesByIDRequest
from telethon.tl.types import Channel, Chat, User

from . import core


_inline_help_bot_entity = None
_inline_help_bot_client = None
_inline_help_bot_username = None
MAX_GIF_IMAGE_PIXELS = 40_000_000
MAX_GIF_DIMENSION = 720


async def _get_inline_help_bot_entity(client, bot_username):
    global _inline_help_bot_client
    global _inline_help_bot_entity
    global _inline_help_bot_username

    normalized_username = bot_username.casefold()
    if (
        _inline_help_bot_entity is not None
        and _inline_help_bot_client is client
        and _inline_help_bot_username == normalized_username
    ):
        return _inline_help_bot_entity

    entity = await client.get_input_entity(bot_username)
    _inline_help_bot_client = client
    _inline_help_bot_entity = entity
    _inline_help_bot_username = normalized_username
    return entity


async def prepare_inline_help_bot(client=None):
    bot_username = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
    if bot_username:
        await _get_inline_help_bot_entity(client or core.get_client(), bot_username)


def inline_help_bot_id():
    return getattr(_inline_help_bot_entity, "user_id", None)


def message_snapshot(message, sender=None):
    sender = sender or getattr(message, "sender", None)
    first_name = getattr(sender, "first_name", None) or ""
    last_name = getattr(sender, "last_name", None) or ""
    sender_name = f"{first_name} {last_name}".strip()
    sender_name = (
        sender_name
        or getattr(sender, "title", None)
        or str(message.sender_id or "بدون نام")
    )
    sender_username = getattr(sender, "username", None)

    return {
        "id": message.id,
        "date": message.date,
        "sender_id": message.sender_id,
        "sender_name": sender_name or str(message.sender_id or "نامشخص"),
        "sender_username": sender_username,
        "text": message.message or "",
        "has_media": bool(message.media),
        "media": message.media,
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


def _render_photo_gif(image_path, output_path):
    with Image.open(image_path) as source:
        if source.width * source.height > MAX_GIF_IMAGE_PIXELS:
            raise ValueError("Image resolution is too large.")
        image = ImageOps.exif_transpose(source).convert("RGB")

    image.thumbnail(
        (MAX_GIF_DIMENSION, MAX_GIF_DIMENSION),
        Image.Resampling.LANCZOS,
    )
    image.convert("P", palette=Image.Palette.ADAPTIVE).save(
        output_path,
        format="GIF",
        optimize=True,
    )


async def create_photo_gif(event, photo_message):
    language = core.get_settings().current_language

    media = getattr(photo_message, "media", None)
    document = getattr(media, "document", None)
    document_mime_type = getattr(document, "mime_type", None) or ""
    if getattr(media, "photo", None) is None and not document_mime_type.startswith(
        "image/"
    ):
        return (
            "روی یک عکس ریپلای کن و دستور .گیف را بفرست."
            if language == "fa"
            else "قم بالرد على صورة وأرسل الأمر .تحويل جيف."
        )

    await core.edit_response(
        event,
        "⏳ در حال ساخت GIF..." if language == "fa" else "⏳ جارٍ إنشاء GIF...",
    )
    try:
        with tempfile.TemporaryDirectory(prefix="photo_gif_") as folder:
            image_path = await core.run_with_floodwait(
                lambda: core.get_client().download_media(
                    photo_message,
                    file=folder,
                )
            )
            if not image_path:
                return (
                    "دانلود عکس انجام نشد؛ دوباره تلاش کن."
                    if language == "fa"
                    else "تعذّر تنزيل الصورة؛ حاول مرة أخرى."
                )

            output_path = os.path.join(folder, "photo.gif")
            try:
                await asyncio.to_thread(
                    _render_photo_gif,
                    image_path,
                    output_path,
                )
            except (
                OSError,
                Image.DecompressionBombError,
                ValueError,
            ) as error:
                core.logger.warning(
                    "Could not convert image to GIF: %s",
                    type(error).__name__,
                    exc_info=True,
                )
                return (
                    "ساخت GIF انجام نشد؛ عکس معتبر و کوچک‌تری را امتحان کن."
                    if language == "fa"
                    else "تعذّر إنشاء GIF؛ جرّب صورة صالحة وأصغر حجمًا."
                )

            await core.run_with_floodwait(
                lambda: core.get_client().send_file(
                    event.chat_id,
                    output_path,
                    caption=(
                        "GIF آماده شد ✅"
                        if language == "fa"
                        else "تم تجهيز GIF ✅"
                    ),
                )
            )
    except (OSError, RPCError) as error:
        core.logger.error(
            "Could not download or send photo GIF: %s",
            type(error).__name__,
            exc_info=True,
        )
        return (
            "دریافت یا ارسال GIF انجام نشد؛ دوباره تلاش کن."
            if language == "fa"
            else "تعذّر تنزيل GIF أو إرساله؛ حاول مرة أخرى."
        )

    return None


def timed_message_caption(message, sender=None):
    sender_info = message_snapshot(message, sender)
    caption = (
        f"{core.localized_text('پیام زمان‌دار ذخیره شد ✅')}\n"
        f"{core.localized_text('فرستنده:')} {sender_info['sender_name']}"
    )
    if sender_info["sender_username"]:
        caption += (
            f"\n{core.localized_text('یوزرنیم:')} "
            f"@{sender_info['sender_username']}"
        )
    if sender_info["sender_id"]:
        caption += (
            f"\n{core.localized_text('آیدی عددی:')} "
            f"{sender_info['sender_id']}"
        )
    return caption


async def save_timed_message(message, sender=None):
    if not message.media:
        return

    try:
        if sender is None and message.sender_id is not None:
            sender = await message.get_sender()

        with tempfile.TemporaryDirectory(prefix="timed_message_") as folder:
            file_path = await core.run_with_floodwait(
                lambda: core.get_client().download_media(message, file=folder)
            )

            if not file_path:
                core.logger.warning(
                    "Could not download timed media for message_id=%s",
                    message.id,
                )
                return

            await core.run_with_floodwait(
                lambda: core.get_client().send_file(
                    "me",
                    file_path,
                    caption=timed_message_caption(message, sender),
                )
            )
    except (OSError, RPCError) as error:
        core.logger.error(
            "Could not save timed message_id=%s: %s",
            message.id,
            type(error).__name__,
            exc_info=True,
        )


def deleted_message_caption(item):
    sender = item["sender_name"]
    if item["sender_username"]:
        sender += f" (@{item['sender_username']})"
    elif item["sender_id"]:
        sender += f" | {core.localized_text('آیدی عددی:')} {item['sender_id']}"

    label = core.localized_text("پیام حذف‌شده\nفرستنده:")
    return f"{label} {sender}"


async def save_deleted_message(item):
    caption = deleted_message_caption(item)
    original_message = item["message"]

    body = item["text"] or core.localized_text("[بدون متن]")
    report = f"{caption}\n\n{body}"
    if not original_message.media:
        await _send_report_text_to_saved_messages(report)
        return

    try:
        with tempfile.TemporaryDirectory(prefix="deleted_message_") as folder:
            file_path = await core.run_with_floodwait(
                lambda: core.get_client().download_media(
                    original_message,
                    file=folder,
                )
            )
            if not file_path:
                core.logger.warning(
                    "Could not download deleted media for message_id=%s",
                    item["id"],
                )
                await _send_report_text_to_saved_messages(
                    f"{caption}\n\n{body}\n\n"
                    f"{core.localized_text('[مدیا قابل بازیابی نبود]')}"
                )
                return
            await core.run_with_floodwait(
                lambda: core.get_client().send_file(
                    "me",
                    file_path,
                    caption=caption,
                )
            )
            await _send_report_text_to_saved_messages(body)
    except (OSError, RPCError) as error:
        core.logger.error(
            "Could not save deleted message_id=%s: %s",
            item["id"],
            type(error).__name__,
            exc_info=True,
        )
        await _send_report_text_to_saved_messages(
            f"{caption}\n\n{body}\n\n"
            f"{core.localized_text('[دانلود مدیا ناموفق بود]')}"
        )


async def _send_report_text_to_saved_messages(text):
    chunks = [
        text[index:index + 4096]
        for index in range(0, len(text), 4096)
    ] or [""]
    for chunk in chunks:
        await core.run_with_floodwait(
            lambda chunk=chunk: core.get_client().send_message("me", chunk)
        )


def edited_message_report(previous, updated):
    sender = updated["sender_name"]
    if updated["sender_username"]:
        sender += f" (@{updated['sender_username']})"
    if updated["sender_id"]:
        sender += f" | {core.localized_text('آیدی عددی:')} {updated['sender_id']}"

    old_text = (
        previous["text"]
        if previous is not None and previous["text"]
        else core.localized_text("[متن قبلی در دسترس نیست]")
    )
    new_text = updated["text"] or core.localized_text("[پیام بدون متن]")
    message = updated["message"]
    edited_at = getattr(message, "edit_date", None) or updated["date"]
    date_text = edited_at.strftime("%Y-%m-%d %H:%M:%S") if edited_at else "نامشخص"
    report = (
        f"{core.localized_text('پیام ویرایش شد')}\n"
        f"{core.localized_text('فرستنده:')} {sender}\n"
        f"{core.localized_text('آیدی پیام:')} {updated['id']}\n"
        f"{core.localized_text('زمان ویرایش:')} {date_text}\n\n"
        f"{core.localized_text('متن قبلی:')}\n{old_text}\n\n"
        f"{core.localized_text('متن جدید:')}\n{new_text}"
    )
    return report


def edited_message_report_text(previous, updated, max_length):
    report = edited_message_report(previous, updated)
    if len(report) <= max_length:
        return report

    header_lines = report.split("\n\n", 1)[0]
    old_text = (
        previous["text"]
        if previous is not None and previous["text"]
        else core.localized_text("[متن قبلی در دسترس نیست]")
    )
    new_text = updated["text"] or core.localized_text("[پیام بدون متن]")
    old_label = core.localized_text("متن قبلی:")
    new_label = core.localized_text("متن جدید:")
    prefix = f"{header_lines}\n\n{old_label}\n"
    separator = f"\n\n{new_label}\n"
    available = max_length - len(prefix) - len(separator)
    old_limit = available // 2
    new_limit = available - old_limit
    old_excerpt = old_text[:old_limit]
    new_excerpt = new_text[:new_limit]
    if len(old_text) > old_limit:
        old_excerpt = old_excerpt.rstrip() + "…"
    if len(new_text) > new_limit:
        new_excerpt = new_excerpt.rstrip() + "…"
    return f"{prefix}{old_excerpt}{separator}{new_excerpt}"


async def save_edited_message_report(previous, updated):
    message = updated["message"]

    if message.media:
        report = edited_message_report(previous, updated)
        try:
            with tempfile.TemporaryDirectory(prefix="edited_message_") as folder:
                file_path = await core.run_with_floodwait(
                    lambda: core.get_client().download_media(message, file=folder)
                )
                if not file_path:
                    core.logger.warning(
                        "Could not download edited media for message_id=%s",
                        updated["id"],
                    )
                    await _send_report_text_to_saved_messages(
                        edited_message_report_text(previous, updated, 4096)
                    )
                    return
                header = report.split("\n\n", 1)[0]
                details = report.split("\n\n", 1)[1] if "\n\n" in report else ""
                await core.run_with_floodwait(
                    lambda: core.get_client().send_file(
                        "me",
                        file_path,
                        caption=header[:1024],
                    )
                )
                if details:
                    await _send_report_text_to_saved_messages(details)
        except (OSError, RPCError) as error:
            core.logger.error(
                "Could not save edited media message_id=%s: %s",
                updated["id"],
                type(error).__name__,
                exc_info=True,
            )
            await _send_report_text_to_saved_messages(
                edited_message_report_text(previous, updated, 4096)
            )
    else:
        report = edited_message_report_text(previous, updated, 4096)
        await _send_report_text_to_saved_messages(report)


async def send_inline_help_panel(event, command):
    bot_username = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
    if not bot_username:
        message = (
            "نام کاربری ربات اینلاین را در BOT_USERNAME داخل فایل .env تنظیم کن."
            if core.get_settings().current_language != "ar"
            else "اضبط اسم مستخدم بوت Inline في BOT_USERNAME داخل ملف .env."
        )
        await core.edit_response(event, message)
        return

    bot_entity = await _get_inline_help_bot_entity(event.client, bot_username)

    destination = event.input_chat
    if destination is None:
        destination = await event.get_input_chat()
    if destination is None:
        message = (
            "شناسهٔ گفتگوی فعلی برای ارسال پنل راهنما پیدا نشد."
            if core.get_settings().current_language != "ar"
            else "تعذّر تحديد المحادثة الحالية لإرسال لوحة المساعدة."
        )
        await core.edit_response(event, message)
        return

    results = await event.client.inline_query(
        bot_entity,
        f"{command} __selfbot_settings__:"
        f"{int(core.get_settings().timed_save_enabled)}"
        f"{int(core.get_settings().deleted_save_enabled)}"
        f"{int(core.get_settings().edited_save_enabled)}",
        entity=destination,
    )
    if not results:
        message = (
            "ربات اینلاین نتیجه‌ای نداد؛ BOT_USERNAME را بررسی کن و مطمئن شو "
            "Inline Mode فعال است و ربات کمکی با BOT_TOKEN روشن است."
            if core.get_settings().current_language != "ar"
            else "لم يُرجع بوت Inline أي نتيجة؛ تحقق من BOT_USERNAME وتأكد من "
            "تفعيل Inline Mode وتشغيل البوت المساعد باستخدام BOT_TOKEN."
        )
        await core.edit_response(event, message)
        return

    await results[0].click(entity=destination)
    await event.delete()


async def deleted_media_preview(item, folder, index, remaining_size):
    if not item["has_media"]:
        return "", 0

    message = item["message"]
    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    photo = getattr(media, "photo", None)
    mime_type = (getattr(document, "mime_type", None) or "")
    mime_type = mime_type.split(";", 1)[0].strip().lower()
    unavailable_note = (
        '<p class="media-note">'
        f"{html.escape(core.localized_text('پیش‌نمایش این مدیا در HTML درج نشد؛ فایل جداگانه ذخیره شده است.'))}"
        "</p>"
    )
    if photo is not None:
        mime_type = "image/jpeg"

    supported_image_types = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    }
    supported_audio_types = {
        "audio/aac",
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
        "audio/x-wav",
    }
    supported_video_types = {"video/mp4"}
    if mime_type not in (
        supported_image_types | supported_audio_types | supported_video_types
    ):
        return unavailable_note, 0

    max_preview_size = min(10 * 1024 * 1024, remaining_size)
    if max_preview_size <= 0:
        return unavailable_note, 0

    known_size = getattr(document, "size", None)
    if photo is not None:
        photo_sizes = getattr(photo, "sizes", ())
        known_size = max(
            (
                getattr(size, "size", None)
                or max(getattr(size, "sizes", ()), default=0)
                for size in photo_sizes
            ),
            default=None,
        )
    if known_size is not None and known_size > max_preview_size:
        return unavailable_note, 0

    media_folder = os.path.join(folder, f"media_{item['id']}_{index}")
    os.makedirs(media_folder)
    try:
        file_path = await core.run_with_floodwait(
            lambda: core.get_client().download_media(message, file=media_folder)
        )
    except Exception as error:
        core.logger.warning(
            "Could not download media preview for deleted message_id=%s: %s",
            item["id"],
            type(error).__name__,
            exc_info=True,
        )
        return unavailable_note, 0

    if not file_path:
        return unavailable_note, 0

    with open(file_path, "rb") as media_file:
        media_bytes = media_file.read(max_preview_size + 1)
    if len(media_bytes) > max_preview_size:
        return unavailable_note, 0

    data_uri = (
        f"data:{mime_type};base64,"
        f"{base64.b64encode(media_bytes).decode('ascii')}"
    )
    if mime_type in supported_video_types:
        return (
            '<video controls preload="metadata" class="media-preview">'
            f'<source src="{data_uri}" type="video/mp4"></video>',
            len(media_bytes),
        )
    if mime_type in supported_audio_types:
        return (
            '<audio controls preload="metadata" class="media-preview">'
            f'<source src="{data_uri}" type="{mime_type}"></audio>',
            len(media_bytes),
        )
    return (
        f'<img class="media-preview" src="{data_uri}" '
        f'alt="{html.escape(core.localized_text("پیش‌نمایش عکس"))}">',
        len(media_bytes),
    )


async def send_deleted_messages_report(chat_id, deleted_messages):
    settings = core.get_settings()
    messages = list(deleted_messages)
    if len(messages) <= 10:
        return

    messages.sort(key=lambda item: item.get("id") or 0)
    rows = []
    remaining_preview_size = 25 * 1024 * 1024

    with tempfile.TemporaryDirectory(prefix="deleted_messages_") as folder:
        for index, item in enumerate(messages):
            date_text = item["date"].strftime("%Y-%m-%d %H:%M:%S") if item["date"] else "نامشخص"
            content = item["text"] or core.localized_text("[پیام بدون متن]")
            if item["has_media"]:
                content += f"\n{core.localized_text('[پیام دارای مدیا]')}"
            media_preview, preview_size = await deleted_media_preview(
                item, folder, index, remaining_preview_size
            )
            remaining_preview_size -= preview_size

            rows.append(
                "<article>"
                f"<h3>پیام {item['id']}</h3>"
                f"<p class=\"meta\">{html.escape(core.localized_text('فرستنده:'))} "
                f"{html.escape(deleted_message_caption(item))} | "
                f"{html.escape(core.localized_text('زمان:'))} {html.escape(date_text)}</p>"
                f"<pre>{html.escape(content)}</pre>"
                f"{media_preview}"
                "</article>"
            )

        report = (
            f"<!doctype html><html lang=\"{'ar' if settings.current_language == 'ar' else 'fa'}\" dir=\"rtl\"><head>"
            f"<meta charset=\"utf-8\"><title>{core.localized_text('پیام‌های حذف‌شده')}</title>"
            "<style>body{font-family:Tahoma,sans-serif;max-width:900px;margin:32px auto;"
            "padding:0 16px;background:#f4f6f8;color:#17202a}article{background:#fff;"
            "border:1px solid #d9e0e7;border-radius:8px;padding:16px;margin:12px 0}"
            "h3{margin:0 0 8px}.meta{color:#637381;font-size:13px}pre{white-space:pre-wrap;"
            "font:inherit;line-height:1.8}.media-preview{display:block;max-width:100%;"
            "max-height:600px;margin:12px auto;border-radius:6px}"
            ".media-note{color:#637381;font-size:13px}</style></head><body>"
            f"<h1>{core.localized_text('پیام‌های حذف‌شده')} ({len(messages)})</h1>"
            + "".join(rows)
            + "</body></html>"
        )

        report_path = os.path.join(folder, "deleted_messages.html")
        with open(report_path, "w", encoding="utf-8") as report_file:
            report_file.write(report)

        await core.run_with_floodwait(
            lambda: core.get_client().send_file(
                "me",
                report_path,
                caption=core.localized_text(
                    f"گزارش {len(messages)} پیام حذف‌شده ✅"
                ),
            )
        )

async def meow_loop(chat_id):
    try:
        while True:
            await asyncio.sleep(300)
            meow_text = "ميو" if core.get_settings().current_language == "ar" else "میو"
            await core.get_client().send_message(chat_id, meow_text)
    except asyncio.CancelledError:
        pass

HEART_COLORS = ("❤️", "🧡", "💛", "💚", "💙", "💜", "🩷")
HEARTS_PER_LINE = 7
HEART_ANIMATION_LINES = 3
HEART_ANIMATION_FRAMES = 4
HEART_ANIMATION_INTERVAL = 0.75


def build_heart_frame(frame_index):
    rows = []
    for row_index in range(HEART_ANIMATION_LINES):
        hearts = (
            HEART_COLORS[
                (frame_index + row_index * 2 + heart_index) % len(HEART_COLORS)
            ]
            for heart_index in range(HEARTS_PER_LINE)
        )
        rows.append("".join(hearts))
    return "\n".join(rows)


async def handle_animation_command(event):
    try:
        for frame_index in range(HEART_ANIMATION_FRAMES):
            frame = build_heart_frame(frame_index)
            await event.edit(frame, parse_mode=None)
            await asyncio.sleep(HEART_ANIMATION_INTERVAL)
    except Exception as error:
        core.logger.error(
            "Heart animation failed in chat_id=%s: %s",
            event.chat_id,
            type(error).__name__,
            exc_info=True,
        )
        await core.edit_response(
            event,
            f"اجرای انیمیشن قلب انجام نشد: {type(error).__name__}",
        )


def get_message_sender_name(sender, chat=None, post_author=None):
    if post_author and post_author.strip():
        return post_author.strip()

    if isinstance(sender, User):
        first_name = getattr(sender, "first_name", None) or ""
        last_name = getattr(sender, "last_name", None) or ""
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name

        return getattr(sender, "username", None) or "نامشخص"

    if isinstance(sender, Channel):
        if (
            isinstance(chat, Channel)
            and getattr(chat, "id", None) == getattr(sender, "id", None)
        ):
            return "خود گروه" if getattr(chat, "megagroup", False) else "خود کانال"
        return (
            getattr(sender, "title", None)
            or getattr(sender, "username", None)
            or "نامشخص"
        )

    if isinstance(sender, Chat):
        if isinstance(chat, Chat) and getattr(chat, "id", None) == getattr(sender, "id", None):
            return "خود گروه"
        return getattr(sender, "title", None) or "نامشخص"

    if sender is None:
        return "نامشخص"

    return "نامشخص"


async def resolve_message_chat(message):
    chat = getattr(message, "chat", None)
    if chat is not None:
        return chat

    try:
        chat = await core.run_with_floodwait(message.get_chat)
    except Exception as error:
        core.logger.warning(
            "Could not resolve chat for message id=%s: %s",
            getattr(message, "id", None),
            type(error).__name__,
            exc_info=True,
        )

    if chat is not None:
        return chat

    peer_id = getattr(message, "peer_id", None)
    if peer_id is None:
        return None

    try:
        return await core.run_with_floodwait(lambda: core.get_client().get_entity(peer_id))
    except Exception as error:
        core.logger.warning(
            "Could not fetch chat entity for message id=%s: %s",
            getattr(message, "id", None),
            type(error).__name__,
            exc_info=True,
        )
        return None


async def resolve_message_sender(message):
    sender = getattr(message, "sender", None)
    if sender is not None and not getattr(sender, "min", False):
        return sender

    try:
        resolved_sender = await core.run_with_floodwait(message.get_sender)
        if resolved_sender is not None and not getattr(resolved_sender, "min", False):
            return resolved_sender
    except Exception as error:
        core.logger.warning(
            "Telethon get_sender failed for message id=%s sender_id=%s: %s",
            getattr(message, "id", None),
            getattr(message, "sender_id", None),
            type(error).__name__,
            exc_info=True,
        )

    sender_id = getattr(message, "sender_id", None)
    if sender_id is not None:
        try:
            resolved_sender = await core.run_with_floodwait(
                lambda: core.get_client().get_entity(sender_id)
            )
            if resolved_sender is not None:
                return resolved_sender
        except Exception as error:
            core.logger.warning(
                "Could not fetch sender entity for message id=%s sender_id=%s: %s",
                getattr(message, "id", None),
                sender_id,
                type(error).__name__,
                exc_info=True,
            )

    if sender is not None:
        core.logger.warning(
            "Using partial sender entity for message id=%s sender_id=%s",
            getattr(message, "id", None),
            sender_id,
        )
        return sender

    core.logger.warning(
        "Sender unavailable for message id=%s sender_id=%s",
        getattr(message, "id", None),
        sender_id,
    )
    return None


async def get_message_metadata(message):
    chat = await resolve_message_chat(message)
    sender = await resolve_message_sender(message)
    return {
        "chat": chat,
        "chat_name": (
            getattr(chat, "title", None)
            or getattr(chat, "username", None)
            or getattr(chat, "first_name", None)
            or "نامشخص"
        ),
        "sender_name": get_message_sender_name(
            sender,
            chat,
            getattr(message, "post_author", None),
        ),
        "date": getattr(message, "date", None),
        "text": getattr(message, "message", None) or "",
    }


def format_message_metadata(metadata, language):
    chat = metadata["chat"]
    chat_name = metadata["chat_name"]
    sender_name = metadata["sender_name"]
    sent_at = metadata["date"]
    unknown_name = "غير معروف" if language == "ar" else "نامشخص"
    if sender_name == "نامشخص":
        sender_name = unknown_name
    elif language == "ar" and sender_name == "خود کانال":
        sender_name = "القناة نفسها"
    elif language == "ar" and sender_name == "خود گروه":
        sender_name = "المجموعة نفسها"

    if isinstance(chat, User):
        chat_label = "المحادثة" if language == "ar" else "گفتگو"
    elif isinstance(chat, Chat) or getattr(chat, "megagroup", False):
        chat_label = "المجموعة" if language == "ar" else "گروه"
    else:
        chat_label = "القناة" if language == "ar" else "کانال"

    time_text = sent_at.strftime("%Y/%m/%d - %H:%M") if sent_at else unknown_name
    if language == "ar":
        return (
            f"📢 {chat_label}: {chat_name}\n"
            f"👤 المرسل: {sender_name}\n"
            f"🕐 وقت الإرسال: {time_text}"
        )

    return (
        f"📢 {chat_label}: {chat_name}\n"
        f"👤 ارسال‌کننده: {sender_name}\n"
        f"🕐 زمان ارسال: {time_text}"
    )


def detect_media_type(message):
    if message is None or not message.media:
        return "متن"

    if getattr(message, "video_note", None) is not None:
        return "Video Message"
    if getattr(message, "photo", None) is not None:
        return "Photo"
    if getattr(message, "video", None) is not None:
        return "Video"
    if getattr(message, "document", None) is not None:
        return "File"
    if getattr(message, "audio", None) is not None:
        return "Audio"
    if getattr(message, "voice", None) is not None:
        return "Voice"
    if getattr(message, "sticker", None) is not None:
        return "Sticker"
    if getattr(message, "gif", None) is not None:
        return "GIF"
    return "Media"


async def download_story_link(chat_id, link):
    language = core.get_settings().current_language
    match = core.STORY_LINK_PATTERN.match(link.strip())
    if match is None:
        return (
            "لینک معتبر استوری نیست. نمونه: https://t.me/username/s/123"
            if language == "fa"
            else "رابط القصة غير صالح. مثال: https://t.me/username/s/123"
        )

    try:
        peer = await core.get_client().get_input_entity(match.group("username"))
        result = await core.run_with_floodwait(
            lambda: core.get_client()(
                GetStoriesByIDRequest(
                    peer=peer,
                    id=[int(match.group("story_id"))],
                )
            )
        )
        if not result.stories or not result.stories[0].media:
            return (
                "این استوری پیدا نشد یا فایل قابل دانلود ندارد."
                if language == "fa"
                else "لم يتم العثور على القصة أو لا تحتوي على وسائط قابلة للتنزيل."
            )

        with tempfile.TemporaryDirectory(prefix="story_download_") as folder:
            file_path = await core.run_with_floodwait(
                lambda: core.get_client().download_media(
                    result.stories[0].media,
                    file=folder,
                )
            )
            if not file_path:
                return (
                    "دانلود استوری انجام نشد."
                    if language == "fa"
                    else "تعذّر تنزيل القصة."
                )
            await core.run_with_floodwait(
                lambda: core.get_client().send_file(
                    chat_id,
                    file_path,
                    caption=(
                        "استوری دانلود شد ✅"
                        if language == "fa"
                        else "تم تنزيل القصة ✅"
                    ),
                    supports_streaming=True,
                )
            )
    except (OSError, RPCError, ValueError) as error:
        core.logger.warning(
            "Could not download story from link: %s",
            type(error).__name__,
            exc_info=True,
        )
        return (
            f"دانلود استوری انجام نشد: {type(error).__name__}"
            if language == "fa"
            else f"تعذّر تنزيل القصة: {type(error).__name__}"
        )

    return None


async def download_channel_message(chat_id, message=None, link=None, status_message=None):
    if message is None:
        if not link:
            return "برای دریافت پیام، روی پیام موردنظر ریپلای کن و سپس .دریافت را بنویس."

        match = core.CHANNEL_LINK_PATTERN.match(link.strip())
        if match is None:
            return "لینک معتبر پیام کانال/گروه نیست."

        username = match.group("username")
        private_id = match.group("private_id")
        message_id = int(match.group("message_id"))

        try:
            if private_id:
                entity = int(f"-100{private_id}")
            else:
                entity = username

            message = await core.run_with_floodwait(
                lambda: core.get_client().get_messages(entity, ids=message_id)
            )
        except Exception:
            return "این پیام پیدا نشد یا دسترسی به آن وجود ندارد."

    if message is None:
        return "این پیام پیدا نشد یا دسترسی به آن وجود ندارد."

    try:
        metadata = await get_message_metadata(message)
        info_text = format_message_metadata(metadata, core.get_settings().current_language)
        caption_text = metadata["text"]
        media_type = detect_media_type(message)
        caption_label = "📝 التعليق" if core.get_settings().current_language == "ar" else "📝 Caption"

        if message.media:
            media_caption = (
                f"{info_text}\n{caption_label}:\n{caption_text}"
                if caption_text
                else info_text
            )
            last_update = 0.0
            frames = ("⏳", "⌛", "🔄", "✨")
            frame_index = 0

            def show_progress(downloaded, total):
                nonlocal last_update, frame_index
                now = time.monotonic()

                if status_message is None or now - last_update < 2:
                    return

                last_update = now
                progress = core.progress_text(
                    downloaded,
                    total,
                    frames[frame_index % len(frames)],
                    title="دریافت پیام",
                )
                frame_index += 1
                asyncio.create_task(status_message.edit(core.localized_text(progress)))

            with tempfile.TemporaryDirectory(prefix="channel_receive_") as folder:
                file_path = await core.run_with_floodwait(
                    lambda: core.get_client().download_media(
                        message,
                        file=folder,
                        progress_callback=show_progress,
                    )
                )

                if not file_path:
                    return "دریافت مدیا انجام نشد."

                await core.run_with_floodwait(
                    lambda: core.get_client().send_file(
                        chat_id,
                        file_path,
                        caption=media_caption,
                        video_note=media_type == "Video Message",
                    )
                )

        elif caption_text.strip():
            text_with_info = f"{caption_text}\n\n━━━━━━━━━━━━\n{info_text}"
            await core.run_with_floodwait(
                lambda: core.get_client().send_message(chat_id, text_with_info)
            )

        else:
            return "این پیام متن یا مدیای قابل دریافت ندارد."

        return None

    except Exception as error:
        if "not found" in str(error).lower() or "access" in str(error).lower() or "forbidden" in str(error).lower():
            return "این پیام پیدا نشد یا دسترسی به آن وجود ندارد."
        return f"دریافت پیام انجام نشد: {type(error).__name__}"
