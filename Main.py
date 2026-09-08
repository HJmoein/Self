# main.py

import asyncio
from telethon import TelegramClient, events
from config import API_ID, API_HASH, SESSION_NAME

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

tasks = {}


async def meow_loop(chat_id):
    while True:
        await asyncio.sleep(300)  # 5 دقیقه
        await client.send_message(chat_id, "میو")


@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    if event.raw_text.strip() != "میو":
        return

    chat_id = event.chat_id

    if chat_id in tasks:
        await event.edit("میو خودکار از قبل روشنه 🐱")
        return

    tasks[chat_id] = asyncio.create_task(meow_loop(chat_id))
    await event.edit("میو خودکار روشن 🐱")


async def main():
    await client.start()
    print("Meow SelfBot is running...")
    await client.run_until_disconnected()


asyncio.run(main())
