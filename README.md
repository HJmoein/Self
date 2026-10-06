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

To open the English account manager for adding accounts, run:

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
session filenames are not shown in account listings.

Selfbot settings (selected language and enabled features) are saved locally
when changed and restored on the next start. Per-chat meow and enemy settings
are also restored; meow tasks resume after the bot connects.

## Tests

Run the automated test suite from the project root:

```powershell
python -B -m unittest discover
```

The weather tests use mocked API responses and do not require an internet
connection.