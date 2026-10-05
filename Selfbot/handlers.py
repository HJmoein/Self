"""Telethon event handlers and command routing."""

import asyncio
import tempfile
import time

from telethon import events

from . import core, services, ui


@core.client.on(events.NewMessage)
async def cache_messages(event):
    if event.is_private and event.chat_id is not None and event.message is not None:
        sender = getattr(event.message, "sender", None)
        if sender is None and event.message.sender_id is not None:
            try:
                sender = await event.get_sender()
            except Exception:
                sender = None

        core.message_cache[event.chat_id].append(
            services.message_snapshot(event.message, sender)
        )
        core.message_index[event.message.id].add(event.chat_id)

        if core.timed_save_enabled and services.is_timed_message(event.message):
            asyncio.create_task(services.save_timed_message(event.message))


@core.client.on(events.NewMessage)
async def enemy_auto_reply_handler(event):
    """هنگام پیام دادن کاربر مشخص شده به عنوان دشمن، پاسخ خودکار ارسال می‌شود"""
    if not core.self_enabled or event.out or event.chat_id is None:
        return

    chat_id = event.chat_id
    sender_id = event.sender_id

    if chat_id in core.enemy_targets and sender_id in core.enemy_targets[chat_id]:
        idx = core.enemy_counters[chat_id] % len(core.ENEMY_INSULTS)
        insult = core.ENEMY_INSULTS[idx]
        core.enemy_counters[chat_id] += 1

        try:
            await core.run_with_floodwait(
                lambda: core.client.send_message(
                    chat_id,
                    insult,
                    reply_to=event.id
                )
            )
        except Exception:
            pass


@core.client.on(events.MessageDeleted)
async def deleted_message_handler(event):
    if not core.deleted_save_enabled:
        return

    chat_ids = set()

    if event.chat_id is not None:
        chat_ids.add(event.chat_id)
    else:
        for message_id in event.deleted_ids:
            chat_ids.update(core.message_index.get(message_id, set()))

    for chat_id in chat_ids:
        cached = {item["id"]: item for item in core.message_cache[chat_id]}
        removed = [
            cached[message_id]
            for message_id in event.deleted_ids
            if message_id in cached
        ]

        if not removed:
            continue

        core.deleted_messages[chat_id].extend(removed)

        for item in removed:
            await services.save_deleted_message(item)

        if len(core.deleted_messages[chat_id]) > 10:
            await services.send_deleted_messages_report(chat_id)


@core.client.on(events.NewMessage(outgoing=True))
async def handler(event):

    text = event.raw_text.strip()
    chat_id = event.chat_id

    if not text.startswith("."):
        return

    text = text[1:].strip()

    if text in core.COMMAND_ALIASES["self_on"]:
        core.self_enabled = True
        await core.edit_response(event, "سلف روشن شد ✅")
        return

    if text in core.COMMAND_ALIASES["self_off"]:
        core.self_enabled = False
        await core.edit_response(event, "سلف خاموش شد")
        return

    if text in core.COMMAND_ALIASES["language_fa"]:
        core.current_language = "fa"
        await event.edit("زبان فارسی فعال شد ✅")
        return

    if text in core.COMMAND_ALIASES["language_ar"]:
        core.current_language = "ar"
        await event.edit("تم تفعيل اللغة العربية ✅")
        return

    if not core.self_enabled:
        return

    # دستور فعال‌سازی و غیرفعال‌سازی حالت دشمن
    if text in core.COMMAND_ALIASES["enemy_on"]:
        reply = await event.get_reply_message()
        if reply is None or not reply.sender_id:
            await core.edit_response(event, "برای فعال‌سازی حالت دشمن، روی پیام کاربر ریپلای کن!")
            return

        target_id = reply.sender_id
        core.enemy_targets[chat_id].add(target_id)
        await core.edit_response(event, "حالت دشمن روی کاربر فعال شد ✅")
        return

    if text in core.COMMAND_ALIASES["enemy_off"]:
        if chat_id in core.enemy_targets:
            core.enemy_targets.pop(chat_id, None)
            core.enemy_counters.pop(chat_id, None)
        await core.edit_response(event, "حالت دشمن غیرفعال شد ❌")
        return

    if text in core.COMMAND_ALIASES["deleted_on"]:
        core.deleted_save_enabled = True
        await core.edit_response(event, "ذخیره پیام‌های حذف‌شده روشن شد ✅")
        return

    if text in core.COMMAND_ALIASES["deleted_off"]:
        core.deleted_save_enabled = False
        await core.edit_response(event, "ذخیره پیام‌های حذف‌شده خاموش شد")
        return

    if text in core.COMMAND_ALIASES["timed_on"]:
        if core.timed_save_enabled:
            await core.edit_response(event, "ذخیره پیام‌های زمان‌دار از قبل روشن است.")
            return

        core.timed_save_enabled = True
        await core.edit_response(event, "ذخیره پیام‌های زمان‌دار روشن شد ✅")
        return

    if text in core.COMMAND_ALIASES["timed_off"]:
        if not core.timed_save_enabled:
            await core.edit_response(event, "ذخیره پیام‌های زمان‌دار روشن نیست")
            return

        core.timed_save_enabled = False
        await core.edit_response(event, "ذخیره پیام‌های زمان‌دار خاموش شد")
        return

    if text in core.COMMAND_ALIASES["help"]:
        await ui.show_help(event)
        return

    if text in core.COMMAND_ALIASES["user_id"]:
        await ui.show_user_id(event)
        return

    if text in core.COMMAND_ALIASES["my_id"]:
        await ui.show_my_id(event)
        return

    if text in core.COMMAND_ALIASES["animation"]:
        await services.handle_animation_command(event)
        return

    channel_command = next(
        (
            command
            for command in core.COMMAND_ALIASES["receive"]
            if text == command or text.startswith(command + " ")
        ),
        None,
    )
    if channel_command:
        link = text[len(channel_command):].strip()
        reply_message = await event.get_reply_message()

        if not link and reply_message is None:
            await core.edit_response(
                event,
                "برای دریافت پیام، روی پیام موردنظر ریپلای کن و سپس .دریافت را بنویس."
            )
            return

        await core.edit_response(
            event,
            "⏳ در حال دریافت پیام...\n"
            "[░░░░░░░░░░] 0%"
        )

        error_message = await services.download_channel_message(
            chat_id,
            message=reply_message,
            link=link or None,
            status_message=event,
        )

        if error_message:
            await core.edit_response(event, error_message)
        else:
            await event.delete()

        return

    story_command = next(
        (
            command
            for command in core.COMMAND_ALIASES["story_link"]
            if text.startswith(command + " ")
        ),
        None,
    )
    if story_command:
        link = text[len(story_command):].strip()

        if not core.STORY_LINK_PATTERN.match(link):
            command_example = (
                core.ARABIC_STORY_COMMAND
                if core.current_language == "ar"
                else core.STORY_COMMAND
            )
            await core.edit_response(
                event,
                f"فرمت درست:\n.{command_example} https://t.me/username/s/123"
            )
            return

        await core.edit_response(
            event,
            "⏳ دانلود استوری شروع شد...\n"
            "[░░░░░░░░░░] 0%"
        )

        error_message = await services.download_story_link(
            chat_id,
            link,
            event
        )

        if error_message:
            await core.edit_response(event, error_message)
        else:
            await event.delete()

        return

    if text in core.COMMAND_ALIASES["meow_on"]:
        if chat_id in core.tasks:
            await core.edit_response(event, "میو خودکار از قبل روشنه")
            return

        core.tasks[chat_id] = asyncio.create_task(
            services.meow_loop(chat_id)
        )

        await core.edit_response(event, "میو خودکار روشن")

    elif text in core.COMMAND_ALIASES["meow_off"]:
        task = core.tasks.pop(chat_id, None)

        if task:
            task.cancel()
            await core.edit_response(event, "میو خودکار خاموش شد")
        else:
            await core.edit_response(event, "میو خودکار روشن نیست")

    elif text in core.COMMAND_ALIASES["ping"]:
        start = time.perf_counter()

        await core.edit_response(event, "در حال بررسی...")

        ping = (time.perf_counter() - start) * 1000

        await core.edit_response(
            event,
            f"پینگ : {ping:.0f}ms"
        )

    elif text in core.COMMAND_ALIASES["story_reply"]:
        reply = await event.get_reply_message()

        if reply is None or not reply.media:
            await core.edit_response(
                event,
                "روی استوری یا پیام استوری ریپلای کن و دوباره بنویس: "
                ".استوری دانلود"
            )
            return

        await core.edit_response(
            event,
            "در حال دانلود استوری... ⏳"
        )

        try:
            with tempfile.TemporaryDirectory(
                prefix="meow_story_"
            ) as folder:

                file_path = await core.client.download_media(
                    reply,
                    file=folder
                )

                if not file_path:
                    await core.edit_response(
                        event,
                        "دانلود این استوری ممکن نیست."
                    )
                    return

                await core.client.send_file(
                    chat_id,
                    file_path,
                    caption=core.localized_text("استوری دانلود شد ✅")
                )

            await event.delete()

        except Exception as error:
            await core.edit_response(
                event,
                f"دانلود استوری انجام نشد: {type(error).__name__}"
            )
