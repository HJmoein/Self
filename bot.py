import asyncio

from telethon import TelegramClient, events, functions


api_id = 29834234
api_hash = "552c01d21d127def060f2915aedeebf9"
client = TelegramClient("my_account", api_id, api_hash)
reply_tasks = {}
last_replied_message = {}
about_moein = (
    "سلام، من معین هستم 👋\n"
    "برنامه‌نویس و فعال در حوزه توسعه ربات‌ها 🤖\n\n"
    "رشته تحصیلی من ریاضی هست و در زمینه برنامه‌نویسی و ساخت پروژه‌های مختلف فعالیت می‌کنم \n\n"
    "اگر سؤالی داشتید یا کمکی از دستم برمیاد با کمال میل در خدمتم"
)


async def reply_after_delay(event):
    try:
        await asyncio.sleep(10)
        chat = await event.get_input_chat()
        result = await client(functions.messages.GetPeerDialogsRequest(peers=[chat]))
        dialog = result.dialogs[0] if result.dialogs else None
        if not dialog or event.message.id <= dialog.read_inbox_max_id:
            return

        last_message_id = last_replied_message.get(event.chat_id)
        if last_message_id and dialog.read_inbox_max_id < last_message_id:
            return

        await event.respond(
            "شرمنده فک کنم آقای مهندس معین نیستن\n"
            "دوست داری درباره آقا مهندس بدونی؟\n"
            "بنویس: درباره معین"
        )
        last_replied_message[event.chat_id] = event.message.id
    except asyncio.CancelledError:
        pass


@client.on(events.NewMessage(incoming=True))
async def auto_reply(event):
    if not event.is_private:
        return

    if "درباره معین" in event.raw_text:
        await event.respond(about_moein)
        return

    old_task = reply_tasks.get(event.chat_id)
    if old_task and not old_task.done():
        old_task.cancel()
    reply_tasks[event.chat_id] = asyncio.create_task(reply_after_delay(event))


client.start()
print("Bot started")
client.run_until_disconnected()