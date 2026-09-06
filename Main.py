import asyncio
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel

API_ID =29834234‎
API_HASH ="552c01d21d127def060f2915aedeebf9"

client = TelegramClient("cleanup_session", API_ID, API_HASH)


async def main():
    await client.start()

    me = await client.get_me()
    print(f"Logged in as: {me.first_name}")

    dialogs = await client.get_dialogs()
    total = len(dialogs)
    done = 0

    for dialog in dialogs:
        try:
            entity = dialog.entity

            # Saved Messages
            if isinstance(entity, User) and entity.id == me.id:
                await client.delete_dialog(entity)
                name = "Saved Messages"

            # Private chats / bots
            elif isinstance(entity, User):
                await client.delete_dialog(entity)
                name = getattr(entity, "first_name", "Private chat")

            # Groups / channels
            elif isinstance(entity, (Chat, Channel)):
                await client.delete_dialog(entity)
                name = getattr(entity, "title", "Group/Channel")

            else:
                continue

            done += 1
            print(f"[{done}/{total}] Removed: {name}")
            await asyncio.sleep(0.3)

        except Exception as e:
            print(f"Failed: {dialog.name} -> {e}")

    print("\nFinished.")


with client:
    client.loop.run_until_complete(main())
