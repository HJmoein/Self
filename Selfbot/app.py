"""Single-account application startup."""

import asyncio
import os

from telethon.errors import RPCError
from telegram.error import Conflict

from . import core


def _inline_polling_error_handler(updater, error):
    if not isinstance(error, Conflict):
        core.logger.error(
            "Inline bot polling failed: %s",
            type(error).__name__,
            exc_info=(type(error), error, error.__traceback__),
        )
        return

    core.logger.error(
        "Inline bot polling stopped because another process is using "
        "getUpdates for the same BOT_TOKEN. Stop the other bot instance "
        "or webhook before restarting this Selfbot."
    )
    asyncio.create_task(
        updater.stop(),
        name="stop-conflicting-inline-polling",
    )


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

        inline_application = build_inline_application(token)
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
                ],
                error_callback=lambda error: _inline_polling_error_handler(
                    inline_application.updater,
                    error,
                ),
            )
            polling_started = True
            core.logger.info("Inline bot is running.")

        print("SelfBot is running...")
        await core.client.run_until_disconnected()
    finally:
        if inline_application is not None:
            if polling_started and inline_application.updater.running:
                await inline_application.updater.stop()
            if started:
                await inline_application.stop()
            if initialized:
                await inline_application.shutdown()
