from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest

API_ID = 29834234‎
API_HASH = "552c01d21d127def060f2915aedeebf9"

client = TelegramClient("my_account", API_ID, API_HASH)

async def main():
    await client.start()

    async for d in client.iter_dialogs():
        try:
            await client(DeleteHistoryRequest(peer=d.entity, max_id=0, revoke=True))
        except Exception:
            pass
        await client.delete_dialog(d.entity)
        print(f"Deleted: {d.name or d.id}")

    print("Done.")

with client:
    client.loop.run_until_complete(main())
