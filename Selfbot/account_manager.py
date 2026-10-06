"""English terminal menu for managing Telegram accounts."""

import getpass
import json
import logging
import os
import re
import uuid
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
    user_id: int | None
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


def _session_name_for_user(user, current_session_name):
    raw_name = getattr(user, "first_name", None) or getattr(user, "username", None)
    raw_name = " ".join(
        part
        for part in (
            getattr(user, "first_name", None),
            getattr(user, "last_name", None),
        )
        if part
    ).strip() or raw_name
    candidate = re.sub(r"[^\w-]+", "_", raw_name or "", flags=re.UNICODE).strip("_-")
    if not candidate:
        candidate = current_session_name
    candidate = candidate[:64].rstrip("_-")

    reserved = {Path(core.SESSION_NAME).stem.casefold()}
    reserved.update(name.casefold() for name in _read_account_profiles())
    reserved.update(path.stem.casefold() for path in _session_paths())
    reserved.discard(current_session_name.casefold())
    base = candidate
    suffix = 2
    while candidate.casefold() in reserved:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def rename_session(session_name, new_session_name):
    source = SESSION_DIRECTORY / f"{session_name}.session"
    destination = SESSION_DIRECTORY / f"{new_session_name}.session"
    if source == destination:
        return
    if destination.exists():
        raise FileExistsError(f"Session already exists: {destination.name}")

    renamed_paths = []
    try:
        for old_path, new_path in (
            (source, destination),
            (Path(f"{source}-journal"), Path(f"{destination}-journal")),
            (
                source.with_name(f"{source.stem}.session-journal"),
                destination.with_name(f"{destination.stem}.session-journal"),
            ),
        ):
            if old_path.exists():
                if new_path.exists():
                    raise FileExistsError(
                        f"Session data already exists: {new_path.name}"
                    )
                os.replace(old_path, new_path)
                renamed_paths.append((old_path, new_path))
    except OSError:
        for old_path, new_path in reversed(renamed_paths):
            if new_path.exists():
                os.replace(new_path, old_path)
        raise


def migrate_named_sessions(profiles):
    migrated = dict(profiles)
    used_names = {name.casefold() for name in migrated}
    changed = []
    try:
        for old_name, profile in list(migrated.items()):
            if (
                not re.fullmatch(r"account_\d+", old_name, flags=re.IGNORECASE)
                or not isinstance(profile, dict)
                or not isinstance(profile.get("name"), str)
            ):
                continue
            source = SESSION_DIRECTORY / f"{old_name}.session"
            if not source.is_file():
                continue
            base_name = re.sub(
                r"[^\w-]+",
                "_",
                profile["name"],
                flags=re.UNICODE,
            ).strip("_-")
            if not base_name:
                continue
            base_name = base_name[:64].rstrip("_-")
            target_name = base_name
            suffix = 2
            while (
                target_name.casefold() in used_names
                or (SESSION_DIRECTORY / f"{target_name}.session").exists()
            ):
                target_name = f"{base_name}_{suffix}"
                suffix += 1
            rename_session(old_name, target_name)
            migrated.pop(old_name)
            migrated[target_name] = profile
            used_names.discard(old_name.casefold())
            used_names.add(target_name.casefold())
            changed.append((old_name, target_name))
    except OSError:
        for old_name, new_name in reversed(changed):
            rename_session(new_name, old_name)
        raise

    if changed:
        try:
            _write_account_profiles(migrated)
        except OSError:
            for old_name, new_name in reversed(changed):
                rename_session(new_name, old_name)
            raise
    return migrated


def _write_account_profiles(profiles):
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


def rename_profile_key(old_name, new_name):
    profiles = _read_account_profiles()
    profile = profiles.pop(old_name, None)
    if profile is None:
        raise KeyError(f"Account profile not found: {old_name}")
    if new_name in profiles:
        profiles[old_name] = profile
        raise FileExistsError(f"Account profile already exists: {new_name}")
    profiles[new_name] = profile
    _write_account_profiles(profiles)


async def add_account():
    user = None
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
    if user is not None:
        session_name = session_path.name
        try:
            named_session = _session_name_for_user(user, session_name)
            rename_session(session_name, named_session)
            session_name = named_session
            save_account_profile(user, session_name, phone=phone)
        except Exception as error:
            logger.error(
                "Account was authorized but its named session or profile could "
                "not be saved: %s",
                type(error).__name__,
                exc_info=True,
            )
            print(
                "Account was authorized, but its named session or profile "
                f"could not be saved: {type(error).__name__}"
            )
            return
        print("\nAccount added successfully.")
        print(f"Phone: {phone}")
        print(f"ID: {user.id}")
        print(f"Name: {_account_name(user)}")
        print()


def _account_files_for_deletion(session_name):
    if (
        not session_name
        or Path(session_name).name != session_name
        or "\\" in session_name
        or "/" in session_name
        or session_name in {".", ".."}
    ):
        raise ValueError("Invalid account session name.")

    session_path = SESSION_DIRECTORY / f"{session_name}.session"
    return (
        session_path,
        Path(f"{session_path}-journal"),
        Path(f"{session_path}-wal"),
        Path(f"{session_path}-shm"),
        session_path.with_name(f"{session_path.stem}.session-journal"),
        core.settings_path_for(session_name),
    )


def _removable_accounts(profiles):
    sessions = {path.stem: path for path in _session_paths()}
    session_names = set(sessions)
    session_names.update(
        name
        for name in profiles
        if isinstance(name, str)
        and name
        and Path(name).name == name
        and "/" not in name
        and "\\" not in name
        and name not in {".", ".."}
    )

    accounts = []
    for session_name in sorted(session_names, key=str.casefold):
        profile = profiles.get(session_name)
        if not isinstance(profile, dict):
            profile = {}
        user_id = profile.get("id")
        accounts.append(
            Account(
                session_path=sessions.get(
                    session_name,
                    SESSION_DIRECTORY / f"{session_name}.session",
                ),
                user_id=user_id if isinstance(user_id, int) else None,
                name=(
                    profile["name"]
                    if isinstance(profile.get("name"), str)
                    else session_name
                ),
                phone=(
                    profile["phone"]
                    if isinstance(profile.get("phone"), str)
                    else None
                ),
            )
        )
    return accounts


async def _resolve_account_id(account):
    if account.user_id is not None or not account.session_path.is_file():
        return account

    client = TelegramClient(
        str(account.session_path.with_suffix("")),
        core.API_ID,
        core.API_HASH,
    )
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("Session is not authorized.")
        user = await client.get_me()
        if user is None:
            raise RuntimeError("Telegram did not return the account.")
        save_account_profile(user, account.session_path.stem)
        return Account(
            session_path=account.session_path,
            user_id=user.id,
            name=_account_name(user),
            phone=getattr(user, "phone", None),
        )
    finally:
        if client.is_connected():
            await client.disconnect()


def _delete_account_files(session_name):
    staged_paths = []
    marker = uuid.uuid4().hex
    try:
        for source in _account_files_for_deletion(session_name):
            if not source.exists():
                continue
            staged = source.with_name(f"{source.name}.deleting-{marker}")
            os.replace(source, staged)
            staged_paths.append((source, staged))
    except OSError:
        for original, staged in reversed(staged_paths):
            if staged.exists():
                os.replace(staged, original)
        raise
    return staged_paths


async def delete_account():
    profiles = _read_account_profiles()
    accounts = []
    for account in _removable_accounts(profiles):
        try:
            accounts.append(await _resolve_account_id(account))
        except Exception as error:
            logger.error(
                "Could not read account ID from session %s: %s",
                account.session_path.name,
                type(error).__name__,
                exc_info=True,
            )
            accounts.append(account)

    profiles = _read_account_profiles()
    if not accounts:
        print("No account sessions or saved account profiles were found.")
        return

    print(f"\nAccounts available for deletion: {len(accounts)}")
    for index, account in enumerate(accounts, start=1):
        print(
            f"{index}. ID: {account.user_id or 'Not available'} | "
            f"Phone: {account.phone or 'Not available'} | Name: {account.name}"
        )
    selection = input(
        "Enter the Telegram account ID to remove, or B to go back: "
    ).strip()
    if selection.casefold() in {"b", "back"}:
        return
    if not selection.isdecimal():
        print("Enter a numeric Telegram account ID.\n")
        return

    selected_id = int(selection)
    matching_accounts = [
        account for account in accounts if account.user_id == selected_id
    ]
    if len(matching_accounts) != 1:
        if len(matching_accounts) > 1:
            print(
                "More than one session has this ID. Resolve duplicate account "
                "profiles first.\n"
            )
        else:
            print(f"No additional account found with Telegram ID {selected_id}.\n")
        return

    account = matching_accounts[0]
    session_name = account.session_path.stem
    print(
        f"Log out this Selfbot session for {account.name} "
        f"(ID: {account.user_id}, {account.phone or 'phone unavailable'})? "
        "This does not delete the Telegram account."
    )
    confirmation = input("Are you sure you want to delete this account? (Yes/No): ")
    if confirmation.strip().casefold() not in {"y", "yes"}:
        print("Account deletion cancelled.\n")
        return

    if account.session_path.is_file():
        client = TelegramClient(
            str(account.session_path.with_suffix("")),
            core.API_ID,
            core.API_HASH,
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError("Session is not authorized.")
            user = await client.get_me()
            if user is None or user.id != account.user_id:
                raise RuntimeError("Session account ID did not match the selection.")
            await client.log_out()
        except Exception as error:
            logger.error(
                "Could not log out account session %s: %s",
                session_name,
                type(error).__name__,
                exc_info=True,
            )
            print(
                "Could not log out this session. Stop the bot if it is running, "
                f"then try again ({type(error).__name__})."
            )
            return
        finally:
            if client.is_connected():
                await client.disconnect()

    staged_paths = _delete_account_files(session_name)
    updated_profiles = dict(profiles)
    updated_profiles.pop(session_name, None)
    try:
        _write_account_profiles(updated_profiles)
    except OSError:
        for original, staged in reversed(staged_paths):
            if staged.exists():
                os.replace(staged, original)
        raise

    cleanup_errors = []
    for _, staged in staged_paths:
        try:
            staged.unlink()
        except OSError as error:
            cleanup_errors.append(error)
            logger.error(
                "Could not remove staged account file %s: %s",
                staged.name,
                type(error).__name__,
                exc_info=True,
            )
    if cleanup_errors:
        print(
            "Account was removed, but some staged files could not be deleted. "
            "Check the application directory."
        )
        return
    print(f"Account {account.name} deleted. Restart the bot to apply the change.\n")


async def main():
    actions = {
        "1": add_account,
        "2": list_accounts,
        "3": delete_account,
    }
    while True:
        print("=== SELFBOT ACCOUNT MANAGER ===")
        print("1. Add Account")
        print("2. List Accounts")
        print("3. Delete Account")
        print("4. Back")
        choice = input("Select an option: ").strip()

        if choice == "4":
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Choose 1, 2, 3, or 4.\n")
            continue
        await action()
