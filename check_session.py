import asyncio
import base64
import html
import io
import os
import sys
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import User

# اطلاعات حساب تلگرام
API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

# آیدی عددی مالک سلف‌بات (شما)
OWNER_ID = 8870295777

# تنظیمات
MAX_CONCURRENT_DOWNLOADS = 3

client = TelegramClient("my_account", API_ID, API_HASH)


# ------------------ توابع دانلود عکس و ساخت HTML ------------------

async def download_single_photo(client, message, semaphore):
    """دانلود عکس پیام و تبدیل آن به Base64"""
    async with semaphore:
        while True:
            try:
                img_bytes = await client.download_media(message, file=io.BytesIO())
                if img_bytes:
                    b64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
                    return message.id, b64
                return message.id, None
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
            except Exception:
                return message.id, None


async def get_messages_safe(client, entity_id):
    """دریافت تمامی پیام‌های یک چت بدون قطعی"""
    while True:
        try:
            return await client.get_messages(entity_id, limit=None)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []


async def generate_chat_html(client, me, user):
    """تولید کدهای HTML برای چت انتخاب شده (از اولین پیام تا آخرین پیام به همراه عکس)"""
    chat_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown"
    username = user.username if user.username else "NoUsername"

    messages = await get_messages_safe(client, user.id)
    if not messages:
        return None, chat_name, username

    # مرتب‌سازی از اولین پیام به جدیدترین پیام
    messages.reverse()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    photo_messages = [m for m in messages if m.photo]
    photo_dict = {}

    if photo_messages:
        tasks = [download_single_photo(client, msg, semaphore) for msg in photo_messages]
        results = await asyncio.gather(*tasks)
        photo_dict = {msg_id: b64 for msg_id, b64 in results if b64 is not None}

    messages_html = []
    for message in messages:
        if not message.text and not message.photo:
            continue

        # تشخیص فرستنده پیام
        if message.sender_id == me.id:
            sender_display = f"{me.first_name or 'You'}"
            msg_class = "msg-card me"
        else:
            sender_display = chat_name
            msg_class = "msg-card target"

        clean_sender = html.escape(sender_display)
        clean_text = html.escape(message.text) if message.text else ""
        date_str = message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else ""

        img_tag = ""
        if message.id in photo_dict:
            img_tag = f'<br><img src="data:image/jpeg;base64,{photo_dict[message.id]}" class="chat-img" alt="Photo" />'

        messages_html.append(f"""
            <div class="{msg_class}">
                <div class="sender">{clean_sender}</div>
                <div class="date">{date_str}</div>
                <div class="text">{clean_text}{img_tag}</div>
            </div>
        """)

    if not messages_html:
        return None, chat_name, username

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
        .msg-card {{ border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }}
        .msg-card.target {{ background-color: #1e293b; border-right: 4px solid #3b82f6; }}
        .msg-card.me {{ background-color: #1e3a8a; border-right: 4px solid #10b981; }}
        .sender {{ font-weight: bold; color: #60a5fa; font-size: 14px; margin-bottom: 4px; }}
        .date {{ font-size: 11px; color: #64748b; margin-bottom: 8px; direction: ltr; text-align: left; }}
        .text {{ white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; font-size: 14px; }}
        .chat-img {{ max-width: 100%; max-height: 400px; border-radius: 8px; margin-top: 10px; display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="chat-header">
            <h2>گفتگو با: {html.escape(chat_name)}</h2>
            <p>یوزرنیم: @{html.escape(username)} | آیدی عددی: {user.id}</p>
        </div>
        {"".join(messages_html)}
    </div>
</body>
</html>"""
    return full_html, chat_name, username


# ------------------ پاسخ به دستورات مالک ------------------

@client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"^(?:لیست|\.chats)$"))
async def list_chats_handler(event):
    """پاسخ به دستور لیست یا .chats مالک"""
    status_msg = await event.reply("⏳ در حال استخراج لیست چت‌ها...")
    me = await client.get_me()

    contacts = []
    idx = 1

    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            if user.id == OWNER_ID:
                continue

            chat_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown"
            username = f"@{user.username}" if user.username else "بدون یوزرنیم"
            contacts.append((idx, chat_name, username, user.id))
            idx += 1

    if not contacts:
        await status_msg.edit("❌ هیچ چت شخصی یافت نشد.")
        return

    # ساخت پیام لیست چت‌ها
    response = f"👤 **اکانت:** {me.first_name} | `{me.id}`\n"
    response += f"📊 **تعداد چت‌های شخصی:** {len(contacts)}\n"
    response += "─" * 35 + "\n\n"
    response += "**ردیف | نام مخاطب | یوزرنیم | شناسه (ID)**\n"
    response += "─" * 35 + "\n"

    lines = []
    for c in contacts:
        lines.append(f"`{c[0]}` | **{c[1]}** | {c[2]} | `{c[3]}`")

    full_text = response + "\n".join(lines)
    full_text += "\n\n💡 *برای دریافت فایل HTML هر چت دستور زیر را بفرستید:*\n`.get <ردیف یا آیدی مخاطب>`"

    # پشتیبانی از پیام‌های طولانی
    if len(full_text) > 4000:
        await status_msg.delete()
        for chunk in [full_text[i:i + 4000] for i in range(0, len(full_text), 4000)]:
            await event.reply(chunk)
    else:
        await status_msg.edit(full_text)


@client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"^(?:\.get|گرفتن)\s+(.+)$"))
async def get_chat_handler(event):
    """پاسخ به دستور .get مالک برای استخراج یک چت مشخص"""
    query = event.pattern_match.group(1).strip()
    status_msg = await event.reply(f"⏳ در حال استخراج و ساخت فایل چت `{query}`...")
    
    me = await client.get_me()
    target_user = None

    # پیدا کردن کاربر بر اساس ردیف یا آیدی عددی یا یوزرنیم
    idx = 1
    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            if user.id == OWNER_ID:
                continue

            if query.isdigit():
                if int(query) == idx or int(query) == user.id:
                    target_user = user
                    break
            elif user.username and query.replace("@", "").lower() == user.username.lower():
                target_user = user
                break
            idx += 1

    if not target_user:
        await status_msg.edit(f"❌ مخاطبی با مشخصات `{query}` یافت نشد!")
        return

    # ساخت فایل HTML
    full_html, chat_name, username = await generate_chat_html(client, me, target_user)

    if not full_html:
        await status_msg.edit("❌ هیچ پیامی در این چت پیدا نشد.")
        return

    filename = f"Chat_{target_user.id}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_html)

    caption = (
        f"📄 **فایل چت دریافت شد**\n\n"
        f"👤 **اکانت:** {me.first_name} (`{me.id}`)\n"
        f"👥 **مخاطب:** {chat_name} (@{username})\n"
        f"🆔 **آیدی مخاطب:** `{target_user.id}`"
    )

    try:
        await event.reply(caption, file=filename)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit(f"❌ خطا در ارسال فایل: `{e}`")
    finally:
        if os.path.exists(filename):
            os.remove(filename)


# ------------------ تابع اصلی ------------------

async def main():
    await client.start()
    me = await client.get_me()

    print("\n" + "=" * 50)
    print(f"[INFO] Self-bot active on account: {me.first_name} (ID: {me.id})")
    print(f"[STATUS] Silent mode active. Listening for OWNER commands (OWNER_ID: {OWNER_ID})...")
    print("=" * 50 + "\n")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
