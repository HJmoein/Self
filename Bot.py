"""Compatibility entry point; implementation lives in the Selfbot package."""

import asyncio

from Selfbot import app as _app
from Selfbot import core as _core
from Selfbot import handlers as _handlers
from Selfbot import services as _services
from Selfbot import ui as _ui

main = _app.main


def __getattr__(name):
    for module in (_core, _services, _ui, _handlers, _app):
        try:
            return getattr(module, name)
        except AttributeError:
            continue
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    asyncio.run(main())
