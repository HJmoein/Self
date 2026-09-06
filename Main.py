import asyncio
from telethon import TelegramClient, functions
from telethon.tl.types import User, Chat, Channel

api_id = 29834234
api_hash = "552c01d21d127def060f2915aedeebf9"

client = TelegramClient("cleanup_session", api_id, api_hash)


async def main():
    await client.start()

    me = await client.get_me()
    print(f"Logged in as: {me.first_name}")

    dialogs = await client.get_dialogs()

    print(f"\nFound {len(dialogs)} dialogs.")

    done = 0

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

            await client.delete_dialog(entity)

            done += 1
            print(f"[{done}/{len(dialogs)}] Removed: {name}")

            await asyncio.sleep(0.3)

        except Exception as e:
            print(f"Failed: {dialog.name} -> {e}")

    # Change profile name after processing is finished
    try:
        await client(functions.account.UpdateProfileRequest(
            first_name="کیر شدم"
        ))
        print("Profile name changed to:کیر شدم")
    except Exception as e:
        print(f"Failed to change profile name: {e}")

    print(f"\nFinished. Removed: {done}")


with client:
    client.loop.run_until_complete(main())
