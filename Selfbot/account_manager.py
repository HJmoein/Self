"""English terminal menu for managing Telegram accounts."""

import getpass
import logging
from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient

from . import core


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIRECTORY = PROJECT_ROOT


class AccountSetupCancelled(Exception):
    """The user chose to return to the account-manager menu."""


@dataclass(frozen=True)
class Account:
    session_path: Path
    user_id: int
    name: str


def _account_name(user):
    full_name = " ".join(
        part
        for part in (
            getattr(user, "first_name", None),
            getattr(user, "last_name", None),
        )
        if part
    ).strip()
    return full_name or getattr(user, "username", None) or "Unknown"


def _session_paths():
    return sorted(SESSION_DIRECTORY.glob("*.session"))


def _prompt_with_back(prompt, hidden=False):
    read_input = getpass.getpass if hidden else input
    value = read_input(prompt).strip()
    if value.casefold() in {"b", "back"}:
        raise AccountSetupCancelled
    return value


async def list_accounts(*, wait_for_back=True):
    accounts = []
    for session_path in _session_paths():
        client = TelegramClient(
            str(session_path.with_suffix("")),
            core.API_ID,
            core.API_HASH,
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                continue
            user = await client.get_me()
            if user is None:
                continue

            accounts.append(
                Account(
                    session_path=session_path,
                    user_id=user.id,
                    name=_account_name(user),
                )
            )
        except Exception as error:
            logger.warning(
                "Could not read Telegram account from %s: %s",
                session_path.name,
                type(error).__name__,
                exc_info=True,
            )
            print(
                f"Could not read an account: {type(error).__name__}"
            )
        finally:
            if client.is_connected():
                try:
                    await client.disconnect()
                except Exception as error:
                    logger.warning(
                        "Could not disconnect account session %s: %s",
                        session_path.name,
                        type(error).__name__,
                        exc_info=True,
                    )

    print(f"\nAccounts: {len(accounts)}")
    if not accounts:
        print("No authorized accounts found.")
    else:
        for index, account in enumerate(accounts, start=1):
            print(
                f"{index}. ID: {account.user_id} | "
                f"Name: {account.name}"
            )
    if wait_for_back:
        input("\nPress Enter or type B to go back: ")
    return accounts


def _next_session_path():
    existing = {path.stem.casefold() for path in _session_paths()}
    index = 1
    while f"account_{index}" in existing:
        index += 1
    return SESSION_DIRECTORY / f"account_{index}"


async def add_account():
    try:
        phone = _prompt_with_back(
            "Phone number (international format), or B to go back: "
        )
    except AccountSetupCancelled:
        return
    if not phone:
        print("Phone number cannot be empty.\n")
        return

    session_path = _next_session_path()
    client = TelegramClient(
        str(session_path),
        core.API_ID,
        core.API_HASH,
    )
    try:
        await client.start(
            phone=phone,
            code_callback=lambda: _prompt_with_back(
                "Telegram login code, or B to go back: "
            ),
            password=lambda: _prompt_with_back(
                "Two-step verification password, or B to go back: ",
                hidden=True,
            ),
        )
        user = await client.get_me()
        if user is None:
            raise RuntimeError("Telegram did not return the authorized account.")

        print("\nAccount added successfully.")
        print(f"ID: {user.id}")
        print(f"Name: {_account_name(user)}")
        print()
    except AccountSetupCancelled:
        print("Account setup cancelled.\n")
    except Exception as error:
        logger.warning(
            "Could not add Telegram account to %s: %s",
            session_path.name,
            type(error).__name__,
            exc_info=True,
        )
        print(f"Could not add account: {type(error).__name__}\n")
    finally:
        if client.is_connected():
            try:
                await client.disconnect()
            except Exception as error:
                logger.warning(
                    "Could not disconnect new account session %s: %s",
                    session_path.name,
                    type(error).__name__,
                    exc_info=True,
                )


async def main():
    actions = {
        "1": add_account,
        "2": list_accounts,
    }
    while True:
        print("=== SELFBOT ACCOUNT MANAGER ===")
        print("1. Add Account")
        print("2. List Accounts")
        print("3. Back")
        choice = input("Select an option: ").strip()

        if choice == "3":
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Choose 1, 2, or 3.\n")
            continue
        await action()
