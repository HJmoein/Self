import asyncio
import base64
import html
import io
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import User


API_ID = 
API_HASH = "552c01d21d127def060f2915aedeebf9"


TARGET_USER = ""

# تنظیمات درخواستی شما
SEND_DELAY = 1.0  
MAX_CONCURRENT_DOWNLOADS = 3

client = TelegramClient("my_account", API_ID, API_HASH)


async def download_single_photo(client, message, semaphore):
    # دانلود ایمن عکس با مدیریت هوشمند FloodWait
    async with semaphore:
        while True:
            try:
                img_bytes = await client.download_media(
                    message, file=io.BytesIO()
                )
                if img_bytes:
                    b64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
                    return message.id, b64
                return message.id, None
            except FloodWaitError as e:
                print(
                    f"[Limit] Photo download limited. Waiting for {e.seconds} seconds..."
                )
                await asyncio.sleep(e.seconds + 1)
            except Exception:
                return message.id, None


async def get_messages_safe(client, entity_id):
    # دریافت پیام‌های چت به همراه کنترل FloodWait
    while True:
        try:
            messages = await client.get_messages(entity_id, limit=None)
            return messages
        except FloodWaitError as e:
            print(
                f"[Limit] Get messages limited. Waiting for {e.seconds} seconds..."
            )
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print(f"[Error] Failed to fetch messages: {e}")
            return []


async def main():
    await client.start()
    me = await client.get_me()

    my_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    print(f"Logged in as: {my_name} (@{me.username})")
    print(
        f"\nExport started | Delay: {SEND_DELAY}s | Concurrent photos: {MAX_CONCURRENT_DOWNLOADS}\n"
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    async for dialog in client.iter_dialogs():
        # بررسی شخصی بودن چت (عدم پردازش ربات‌ها و گروه‌ها)
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            username = user.username if user.username else "NoUsername"
            chat_name = (
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            )

            # دریافت پیام‌ها
            messages = await get_messages_safe(client, dialog.id)
            if not messages:
                continue

            # چیدمان: پیام‌های قدیمی در بالای فایل، جدیدترین در پایین
            messages.reverse()

            # دانلود هم‌زمان ۳ عکس
            photo_messages = [m for m in messages if m.photo]
            photo_dict = {}

            if photo_messages:
                tasks = [
                    download_single_photo(client, msg, semaphore)
                    for msg in photo_messages
                ]
                results = await asyncio.gather(*tasks)
                photo_dict = {
                    msg_id: b64 for msg_id, b64 in results if b64 is not None
                }

            # ساخت ساختار پیام‌ها در HTML
            messages_html = []
            for message in messages:
                if not message.text and not message.photo:
                    continue

                if message.sender_id == me.id:
                    sender_name = my_name
                    is_me = True
                else:
                    sender = await message.get_sender()
                    is_me = False
                    sender_name = (
                        f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                        if sender
                        else "Unknown"
                    )
                    if not sender_name:
                        sender_name = "Unknown"

                clean_sender = html.escape(sender_name)
                clean_text = (
                    html.escape(message.text) if message.text else ""
                )
                date_str = (
                    message.date.strftime("%Y-%m-%d %H:%M:%S")
                    if message.date
                    else ""
                )

                img_tag = ""
                if message.id in photo_dict:
                    img_tag = f'<br><img src="data:image/jpeg;base64,{photo_dict[message.id]}" class="chat-img" alt="Photo" />'

                card_class = "msg-card me" if is_me else "msg-card"

                messages_html.append(
                    f"""
                    <div class="{card_class}">
                        <div class="sender">{clean_sender}</div>
                        <div class="date">{date_str}</div>
                        <div class="text">{clean_text}{img_tag}</div>
                    </div>
                """
                )

            if not messages_html:
                continue

            # قالب کامل فایل HTML
            full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat with {html.escape(chat_name)}</title>
    <style>
        body {{ font-family: Tahoma, 'Segoe UI', Arial, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; direction: rtl; }}
        .container {{ max-width: 750px; margin: 0 auto; }}
        .chat-header {{ background-color: #1e293b; padding: 15px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #334155; }}
        .chat-header h2 {{ margin: 0 0 8px 0; color: #38bdf8; font-size: 18px; }}
        .chat-header p {{ margin: 0; color: #94a3b8; font-size: 13px; }}
        .msg-card {{ background-color: #1e293b; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; border-right: 4px solid #3b82f6; }}
        .msg-card.me {{ border-right-color: #10b981; background-color: #162438; }}
        .sender {{ font-weight: bold; color: #60a5fa; font-size: 14px; margin-bottom: 4px; }}
        .msg-card.me .sender {{ color: #34d399; }}
        .date {{ font-size: 11px; color: #64748b; margin-bottom: 8px; direction: ltr; text-align: left; }}
        .text {{ white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; font-size: 14px; }}
        .chat-img {{ max-width: 100%; max-height: 400px; border-radius: 8px; margin-top: 10px; display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="chat-header">
            <h2>Chat with: {html.escape(chat_name)}</h2>
            <p>Username: @{html.escape(username)} | User ID: {user.id}</p>
        </div>
        {"".join(messages_html)}
    </div>
</body>
</html>"""

            file_data = full_html.encode("utf-8")
            file_stream = io.BytesIO(file_data)
            file_stream.name = f"{user.id}_{username}.html"

            # ارسال فایل به کاربر مقصد
            sent = False
            while not sent:
                try:
                    await client.send_file(
                        TARGET_USER,
                        file_stream,
                        caption=f"📂 Exported chat: {chat_name} (@{username})",
                    )
                    print(
                        f"[Success] Sent HTML to @{TARGET_USER}: {file_stream.name}"
                    )
                    sent = True
                except FloodWaitError as e:
                    print(
                        f"[Limit] Send file limited. Waiting for {e.seconds} seconds..."
                    )
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    print(f"[Error] Failed sending {file_stream.name}: {e}")
                    break

            # تاخیر ۱ ثانیه‌ای بین ارسال هر فایل چت
            await asyncio.sleep(SEND_DELAY)

    print("\nAll chats exported successfully!")


with client:
    client.loop.run_until_complete(main())
