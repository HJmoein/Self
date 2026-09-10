import asyncio
import os
import time

from telethon import TelegramClient
from config import API_ID, API_HASH, SESSION_NAME

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


async def main():
    await client.start()

    print("روی یک پیام تلگرامی که فایل/ویدیو دارد ریپلای کن.")
    print("بعد لینک یا ID آن پیام را به این اسکریپت بده.")

    msg_id = int(input("Message ID: "))

    # این بخش برای کانال/گروه عمومی است
    message = await client.get_messages(None, ids=msg_id)

    if not message or not message.media:
        print("❌ فایل پیدا نشد.")
        return

    start = time.perf_counter()
    downloaded = 0

    def progress(current, total):
        nonlocal downloaded
        downloaded = current

        elapsed = time.perf_counter() - start
        if elapsed > 0:
            speed = current / elapsed / 1024 / 1024
            percent = current * 100 / total if total else 0

            print(
                f"\r{percent:6.2f}% | "
                f"{speed:8.2f} MB/s",
                end="",
                flush=True
            )

    path = await client.download_media(
        message,
        file="./speed_test",
        progress_callback=progress,
    )

    elapsed = time.perf_counter() - start
    size_mb = os.path.getsize(path) / 1024 / 1024
    speed = size_mb / elapsed

    print("\n\n✅ تست تمام شد")
    print(f"📦 حجم: {size_mb:.2f} MB")
    print(f"⏱ زمان: {elapsed:.2f} ثانیه")
    print(f"🚀 سرعت واقعی: {speed:.2f} MB/s")
    print(f"🚀 سرعت تقریبی: {speed * 8:.2f} Mbps")

    os.remove(path)


asyncio.run(main())
