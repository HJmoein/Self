# Self

## Run the bot

Running the entry point starts the Selfbot directly with the session configured
in `.env`:

```powershell
python Bot.py
```

To list accounts, their phone numbers, Telegram IDs, and names separately, run:

```powershell
python Bot.py --list-accounts
```

To open the English account manager for adding, listing, or deleting accounts,
run:

```powershell
python Bot.py --accounts
```

The manager can add an account or list saved account details, including phone
number, Telegram ID, and name. The list reads local metadata rather than opening
Telegram session files, so it can be used while the bot is running. If account
details are not available yet, restart the bot once to save them. Use `B` while
adding an account, or press Enter/`B` on
the list screen, to go back. The manager menu's `Back` option returns to the
terminal; it does not start the bot. Adding an account requires its phone
number, Telegram login code, and two-step verification password when enabled.
Account sessions and account metadata are stored locally and excluded from Git;
session filenames are not shown in account listings. The bot starts every saved
account session when it launches, so restart the bot after adding an account.
To log out a Selfbot account, stop the bot, select `Delete Account` in the
manager, enter the account's Telegram ID, and confirm with `Yes` (or `Y`).
Answer `No` (or `N`) to cancel. This logs out only the selected Selfbot session
and removes its local session/settings; it does not delete the Telegram account.
The primary account can also be selected by its Telegram ID.

Each account has its own session and settings file. Settings such as language,
enabled features, meow, and enemy targets are saved separately for each account
and restored on the next start. A separate settings file is created when each
account starts. Newly added sessions use the account's name; older `account_N`
sessions are renamed to the saved account name at startup.

## Tests

Run the automated test suite from the project root:

```powershell
python -B -m unittest discover
```

The weather tests use mocked API responses and do not require an internet
connection.