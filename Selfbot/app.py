"""Application startup."""

import asyncio
import logging
import sys

from . import account_manager, core


logger = logging.getLogger(__name__)


async def main():
    if "--accounts" in sys.argv[1:]:
        await account_manager.main()
        return
    if "--list-accounts" in sys.argv[1:]:
        await account_manager.list_accounts(wait_for_back=False)
        return

    from . import handlers, services  # Register handlers before client startup.

    await core.client.start()
    try:
        user = await core.client.get_me()
        if user is not None:
            account_manager.save_account_profile(user)
        else:
            raise RuntimeError("Telegram did not return the authorized account.")
    except Exception as error:
        logger.warning(
            "Bot started, but account information could not be saved: %s",
            type(error).__name__,
            exc_info=True,
        )
        print(
            "SelfBot is running, but account information could not be saved: "
            f"{type(error).__name__}"
        )
    for chat_id in core.meow_chats:
        core.tasks[chat_id] = asyncio.create_task(
            services.meow_loop(chat_id)
        )
    print("SelfBot is running...")
    await core.client.run_until_disconnected()
