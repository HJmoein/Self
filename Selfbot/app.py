"""Application startup."""

import asyncio
import sys

from . import account_manager, core


async def main():
    if "--accounts" in sys.argv[1:]:
        await account_manager.main()
        return
    if "--list-accounts" in sys.argv[1:]:
        await account_manager.list_accounts(wait_for_back=False)
        return

    from . import handlers  # Register event handlers before starting the client.

    await core.client.start()
    print("SelfBot is running...")
    await core.client.run_until_disconnected()
