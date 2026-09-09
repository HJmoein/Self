from telethon import TelegramClient

API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

client = TelegramClient("my_account", API_ID, API_HASH)

async def main():
    me = await client.get_me()
    print("ID:", me.id)
    print("Username:", me.username)
    print("Name:", me.first_name)

with client:
    client.loop.run_until_complete(main())
