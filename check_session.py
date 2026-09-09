import asyncio
import base64
import html
import io
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import User

# اطلاعات حساب تلگرام
API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

# آیدی عددی مالک جدید سلف‌بات
OWNER_ID = 8870295777

# تنظیمات نرخ ارسال و دانلود هم‌زمان
SEND_DELAY = 1.0
MAX_CONCURRENT_DOWNLOADS = 3

client = TelegramClient("my_account", API_ID, API_HASH)


async def download_single_photo(client, message, semaphore):
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
                await asyncio.sleep(e.seconds + 1)
            except Exception:
                return message.id, None


async def get_messages_safe(client, entity_id):
    while True:
        try:
            messages = await client.get_messages(entity_id, limit=None)
            return messages
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []


@client.on(
    events.NewMessage(from_users=OWNER_ID, pattern=r"^(?:لیست|\.chats)$")
)
async def list_chats_handler(event):
    status_msg = await event.reply("🔄 در حال استخراج لیست چت‌ها...")

    dialog_list = []
    index = 1

    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            chat_name = (
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            )
            username = f"@{user.username}" if user.username else "بدون آیدی"
            dialog_list.append(
                f"`{index}` | **{chat_name}** | {username} | `{user.id}`"
            )
            index += 1

    if not dialog_list:
        await status_msg.edit("❌ هیچ چت شخصی یافت نشد.")
        return

    table_header = "📊 **لیست چت‌های شخصی شما:**\n\n"
    table_header += "**ردیف | نام مخاطب | آیدی | شناسه (ID)**\n"
    table_header += "─" * 35 + "\n"

    full_response = (
        table_header
        + "\n".join(dialog_list)
        + "\n\n💡 *برای دریافت خروجی چت دستور زیر را بفرستید:*\n`.get <شناسه یا آیدی>`"
    )

    if len(full_response) > 4000:
        await status_msg.delete()
        for chunk in [
            full_response[i : i + 4000]
            for i in range(0, len(full_response), 4000)
        ]:
            await event.reply(chunk)
    else:
        await status_msg.edit(full_response)


@client.on(
    events.NewMessage(
        from_users=OWNER_ID, pattern=r"^(?:\.get|گرفتن)\s+(.+)$"
    )
)
async def export_chat_handler(event):
    target_input = event.pattern_match.group(1).strip()
    status_msg = await event.reply(
        f"⏳ در حال استخراج و ساخت HTML برای: `{target_input}`..."
    )

    try:
        if target_input.isdigit() or (
            target_input.startswith("-") and target_input[1:].isdigit()
        ):
            target_entity = int(target_input)
        else:
            target_entity = target_input.replace("@", "")

        user = await client.get_entity(target_entity)
    except Exception as e:
        await status_msg.edit(f"❌ کاربر یافت نشد یا آیدی اشتباه است: {e}")
        return

    me = await client.get_me()
    chat_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username if user.username else "NoUsername"

    messages = await get_messages_safe(client, user.id)
    if not messages:
        await status_msg.edit("❌ هیچ پیامی در این چت یافت نشد.")
        return

    messages.reverse()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    photo_messages = [
        m for m in messages if m.photo and m.sender_id != me.id
    ]
    photo_dict = {}

    if photo_messages:
        await status_msg.edit(
            f"📥 در حال دانلود {len(photo_messages)} تصویر ارسال شده توسط مخاطب..."
        )
        tasks = [
            download_single_photo(client, msg, semaphore)
            for msg in photo_messages
        ]
        results = await asyncio.gather(*tasks)
        photo_dict = {
            msg_id: b64 for msg_id, b64 in results if b64 is not None
        }

    messages_html = []
    for message in messages:
        if message.sender_id == me.id:
            continue

        if not message.text and not message.photo:
            continue

        sender_name = chat_name if chat_name else "Unknown"
        clean_sender = html.escape(sender_name)
        clean_text = html.escape(message.text) if message.text else ""
        date_str = (
            message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else ""
        )

        img_tag = ""
        if message.id in photo_dict:
            img_tag = f'<br><img src="data:image/jpeg;base64,{photo_dict[message.id]}" class="chat-img" alt="Photo" />'

        messages_html.append(
            f"""
            <div class="msg-card">
                <div class="sender">{clean_sender}</div>
                <div class="date">{date_str}</div>
                <div class="text">{clean_text}{img_tag}</div>
            </div>
        """
        )

    if not messages_html:
        await status_msg.edit("❌ هیچ پیامی از سمت طرف مقابل در این چت یافت نشد.")
        return

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
        .sender {{ font-weight: bold; color: #60a5fa; font-size: 14px; margin-bottom: 4px; }}
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

    try:
        await status_msg.edit("📤 در حال ارسال فایل چت...")
        await event.reply(
            f"📂 فایل چت کاربر: {chat_name} (@{username})", file=file_stream
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit(f"❌ خطا در ارسال فایل: {e}")


async def main():
    await client.start()
    me = await client.get_me()

    print("\n" + "=" * 50)
    if me.id == OWNER_ID:
        print(f"[INFO] Logged in as OWNER: {me.first_name} (ID: {me.id})")
        print("[STATUS] Full administrative access granted.")
        print("[STATUS] Self-bot is running and waiting for commands...")
    else:
        print(f"[WARNING] Logged in user: {me.first_name} (ID: {me.id})")
        print(f"[WARNING] You are NOT registered as the owner (Owner ID: {OWNER_ID}).")
        print("[STATUS] Bot running in non-owner mode. Commands restricted.")
    print("=" * 50 + "\n")

    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())
