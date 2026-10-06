"""Application startup."""

import asyncio
import logging
import sys
from pathlib import Path

from telethon import TelegramClient

from . import account_manager, core


logger = logging.getLogger(__name__)


def _additional_session_names(profiles):
    primary_name = Path(core.SESSION_NAME).stem
    return sorted(
        name
        for name in profiles
        if isinstance(name, str)
        and name
        and name not in {".", ".."}
        and Path(name).name == name
        and name != primary_name
    )


async def main():
    if "--accounts" in sys.argv[1:]:
        await account_manager.main()
        return
    if "--list-accounts" in sys.argv[1:]:
        await account_manager.list_accounts(wait_for_back=False)
        return

    from . import handlers, services  # Register handlers before client startup.

    await core.client.start()
    clients = [(Path(core.SESSION_NAME).stem, core.client)]
    profiles = account_manager._read_account_profiles()
    for session_name in _additional_session_names(profiles):
        session_path = account_manager.SESSION_DIRECTORY / f"{session_name}.session"
        if not session_path.is_file():
            logger.error("Saved account session is missing: %s", session_path)
            print(f"Could not start account {session_name}: session file is missing.")
            continue
        account_client = TelegramClient(
            str(session_path.with_suffix("")),
            core.API_ID,
            core.API_HASH,
        )
        try:
            await account_client.connect()
            if not await account_client.is_user_authorized():
                logger.error("Saved account session is not authorized: %s", session_name)
                print(f"Could not start account {session_name}: session is not authorized.")
                await account_client.disconnect()
                continue
            clients.append((session_name, account_client))
        except Exception as error:
            logger.error(
                "Could not connect saved account %s: %s",
                session_name,
                type(error).__name__,
                exc_info=True,
            )
            print(
                f"Could not start account {session_name}: "
                f"{type(error).__name__}"
            )
            if account_client.is_connected():
                await account_client.disconnect()

    for _, account_client in clients:
        handlers.register_handlers(account_client)

    for session_name, account_client in clients:
        try:
            user = await account_client.get_me()
            if user is None:
                raise RuntimeError("Telegram did not return the authorized account.")
            account_manager.save_account_profile(user, session_name)
        except Exception as error:
            logger.warning(
                "Account %s is connected but its profile could not be saved: %s",
                session_name,
                type(error).__name__,
                exc_info=True,
            )
            print(
                f"Account {session_name} is connected, but its profile "
                f"could not be saved: {type(error).__name__}"
            )

    for chat_id in core.meow_chats:
        token = core.set_active_client(core.client)
        try:
            core.tasks[chat_id] = asyncio.create_task(
                services.meow_loop(chat_id)
            )
        finally:
            core.reset_active_client(token)
    print(f"Connected accounts: {len(clients)}")
    print("SelfBot is running...")
    await asyncio.gather(
        *(account_client.run_until_disconnected() for _, account_client in clients)
    )
