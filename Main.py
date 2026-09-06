import asyncio
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel
from telethon.errors import FloodWaitError

api_id = 29834234
api_hash = "552c01d21d127def060f2915aedeebf9"

client = TelegramClient("cleanup_session", api_id, api_hash)


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


async def main():
    await client.start()

    me = await client.get_me()
    print(f"Logged in as: {me.first_name}")

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
                exists = any(d.id == dialog.id for d in current)

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


with client:
    client.loop.run_until_complete(main())
