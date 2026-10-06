"""Single-account application startup."""

import asyncio

from . import core


async def main():
    from . import handlers, services

    await core.client.start()
    settings = core.get_settings()
    handlers.register_handlers(core.client)

    for chat_id in settings.meow_chats:
        settings.tasks[chat_id] = asyncio.create_task(services.meow_loop(chat_id))

    core.save_settings()
    print("SelfBot is running...")
    await core.client.run_until_disconnected()
