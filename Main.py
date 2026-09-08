import asyncio
import time

from telethon import TelegramClient, events
from config import API_ID, API_HASH, SESSION_NAME

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

tasks = {}


async def meow_loop(chat_id):
    try:
        while True:
            await asyncio.sleep(300)  # 5 دقیقه
            await client.send_message(chat_id, "میو")
    except asyncio.CancelledError:
        pass


@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    text = event.raw_text.strip()
    chat_id = event.chat_id

    # میو روشن
    if text == "میو روشن":
        if chat_id in tasks:
            await event.edit("میو خودکار از قبل روشنه")
            return

        tasks[chat_id] = asyncio.create_task(meow_loop(chat_id))
        await event.edit("میو خودکار روشن")

    # میو خاموش
    elif text == "میو خاموش":
        task = tasks.pop(chat_id, None)

        if task:
            task.cancel()
            await event.edit("میو خودکار خاموش شد")
        else:
            await event.edit("میو خودکار روشن نیست")

    # پینگ
    elif text == "پینگ":
        start = time.perf_counter()

        await event.edit("در حال بررسی...")

        ping = (time.perf_counter() - start) * 1000

        await event.edit(f"پینگ : {ping:.0f}ms")


async def main():
    await client.start()

    print("Meow SelfBot is running...")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
