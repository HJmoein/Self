"""Single-account application startup."""

import asyncio
import os

from telethon.errors import RPCError

from . import core


async def main():
    from . import handlers, services

    await core.client.start()
    try:
        await services.prepare_inline_help_bot(core.client)
    except (OSError, RPCError, TimeoutError, TypeError, ValueError) as error:
        core.logger.warning(
            "Could not pre-resolve the inline help bot; it will be resolved "
            "when the help panel is requested (%s).",
            type(error).__name__,
        )

    settings = core.get_settings()
    handlers.register_handlers(core.client)

    for chat_id in settings.meow_chats:
        settings.tasks[chat_id] = asyncio.create_task(services.meow_loop(chat_id))

    core.save_settings()
    token = os.getenv("BOT_TOKEN")
    inline_application = None
    initialized = False
    started = False
    polling_started = False

    if token:
        from .inline_bot import build_inline_application

        owner = await core.client.get_me()
        if owner is None or owner.id is None:
            raise RuntimeError("Could not determine the Selfbot owner account ID.")
        inline_application = build_inline_application(token, owner.id)
    else:
        core.logger.warning(
            "BOT_TOKEN is not set; inline mode is disabled. "
            "Add BOT_TOKEN to .env to enable it."
        )

    try:
        if inline_application is not None:
            await inline_application.initialize()
            initialized = True
            await inline_application.start()
            started = True
            if inline_application.updater is None:
                raise RuntimeError("Inline bot application has no updater.")
            await inline_application.updater.start_polling(
                allowed_updates=[
                    "inline_query",
                    "chosen_inline_result",
                    "callback_query",
                ]
            )
            polling_started = True
            core.logger.info("Inline bot is running.")

        print("SelfBot is running...")
        await core.client.run_until_disconnected()
    finally:
        if inline_application is not None:
            if polling_started:
                await inline_application.updater.stop()
            if started:
                await inline_application.stop()
            if initialized:
                await inline_application.shutdown()
