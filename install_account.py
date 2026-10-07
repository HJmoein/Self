"""Start an isolated Selfbot session and prompt for login in this terminal."""

import os
import re
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
ACCOUNT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def main():
    account_name = input(
        "Account label (letters, numbers, _ or -, max 64 characters): "
    ).strip()
    if not ACCOUNT_NAME_PATTERN.fullmatch(account_name):
        raise SystemExit("Invalid account label.")

    accounts_dir = PROJECT_DIR / "accounts"
    accounts_dir.mkdir(exist_ok=True)
    session_path = accounts_dir / account_name
    environment = os.environ.copy()
    environment["SESSION_NAME"] = str(session_path)
    environment["BOT_TOKEN"] = ""

    print(
        f"Starting isolated session '{account_name}'. "
        "Enter your Telegram phone and login code only in this terminal."
    )
    print(
        "Inline help uses the configured BOT_USERNAME; "
        "this session won't poll BOT_TOKEN."
    )
    result = subprocess.run(
        [sys.executable, str(PROJECT_DIR / "Bot.py")],
        cwd=PROJECT_DIR,
        env=environment,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
