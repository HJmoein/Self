from telethon import TelegramClient

API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()

    async for dialog in client.iter_dialogs():
        try:
            name = dialog.name or str(dialog.id)

            await client.delete_dialog(dialog.entity)

            print(f"[OK] {name}")

        except Exception as e:
            print(f"[FAILED] {dialog.name or dialog.id}")
            print(f"Reason: {type(e).__name__}: {e}")

    print("\n--- Remaining dialogs ---")

    async for dialog in client.iter_dialogs():
        print(f"{dialog.name or dialog.id} | {dialog.id}")


with client:
    client.loop.run_until_complete(main())
