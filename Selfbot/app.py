"""Application startup."""

import asyncio

from . import core
from . import handlers  # Importing registers the Telethon event handlers.


async def main():
    await core.client.start()

    print("SelfBot is running...")

    await core.client.run_until_disconnected()
