"""English terminal menu for managing Telegram accounts."""

import getpass
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from telethon import TelegramClient

from . import core


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIRECTORY = PROJECT_ROOT
ACCOUNT_METADATA_PATH = PROJECT_ROOT / ".account_profiles.json"


class AccountSetupCancelled(Exception):
    """The user chose to return to the account-manager menu."""


@dataclass(frozen=True)
class Account:
    session_path: Path
    user_id: int
    name: str
    phone: str | None = None


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


def save_account_profile(user, session_name=core.SESSION_NAME, phone=None):
    session_name = Path(session_name).stem
    profiles = _read_account_profiles()
    profiles[session_name] = {
        "id": user.id,
        "name": _account_name(user),
        "phone": phone or getattr(user, "phone", None),
    }

    ACCOUNT_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ACCOUNT_METADATA_PATH.parent,
            prefix=f"{ACCOUNT_METADATA_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as metadata_file:
            temporary_path = Path(metadata_file.name)
            json.dump(profiles, metadata_file, ensure_ascii=False, indent=2)
            metadata_file.write("\n")
        os.replace(temporary_path, ACCOUNT_METADATA_PATH)
        if os.name == "posix":
            ACCOUNT_METADATA_PATH.chmod(0o600)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _read_account_profiles():
    try:
        with ACCOUNT_METADATA_PATH.open(encoding="utf-8") as metadata_file:
            profiles = json.load(metadata_file)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as error:
        logger.error(
            "Could not read local account metadata: %s",
            type(error).__name__,
            exc_info=True,
        )
        print(f"Could not read saved account information: {type(error).__name__}")
        return {}

    if not isinstance(profiles, dict):
        logger.error("Local account metadata must contain a JSON object.")
        print("Could not read saved account information: invalid file format.")
        return {}
    return profiles


def _prompt_with_back(prompt, hidden=False):
    read_input = getpass.getpass if hidden else input
    value = read_input(prompt).strip()
    if value.casefold() in {"b", "back"}:
        raise AccountSetupCancelled
    return value


async def list_accounts(*, wait_for_back=True):
    profiles = _read_account_profiles()
    accounts = []
    for session_name, profile in profiles.items():
        if not isinstance(profile, dict):
            logger.warning("Ignoring invalid saved account profile.")
            continue
        user_id = profile.get("id")
        name = profile.get("name")
        if not isinstance(user_id, int) or not isinstance(name, str):
            logger.warning("Ignoring incomplete saved account profile.")
            continue
        accounts.append(
            Account(
                session_path=SESSION_DIRECTORY / f"{session_name}.session",
                user_id=user_id,
                name=name,
                phone=profile.get("phone")
                if isinstance(profile.get("phone"), str)
                else None,
            )
        )

    print(f"\nAccounts: {len(accounts)}")
    if not accounts:
        print(
            "No saved account information found. Restart the bot once after "
            "updating it, or add the account from the account manager."
        )
    else:
        for index, account in enumerate(accounts, start=1):
            print(
                f"{index}. Phone: {account.phone or 'Not available'} | "
                f"ID: {account.user_id} | "
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

        try:
            save_account_profile(user, session_path.name, phone=phone)
        except OSError as error:
            logger.error(
                "Account was authorized but its local profile could not be saved: %s",
                type(error).__name__,
                exc_info=True,
            )
            print(
                "Account was added, but its local account information "
                f"could not be saved: {type(error).__name__}"
            )
        print("\nAccount added successfully.")
        print(f"Phone: {phone}")
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
