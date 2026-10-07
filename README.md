# Self

Run the default Selfbot session from the project directory:

```powershell
python Bot.py
```

The bot uses the Telegram session configured by `SESSION_NAME` in `.env`.
To run this Selfbot on another account, use the same project and run
`python Bot.py` with a different `SESSION_NAME`. Telethon will request that
account's phone and login code in the terminal. Never send the code to a
Telegram bot or paste it into chat.

Settings such as the selected language and enabled features are saved separately
for each session and restored after restarting the bot (`.selfbot_settings.json`
for the default `self` session; named sessions store settings beside their
session files). Each account has its own process and session; running many
accounts simultaneously is limited by the server's CPU, memory, and Telegram
limits.

Inline mode:

- Add your Telegram Bot API token as `BOT_TOKEN=...` in `.env` (keep it secret).
- Set `BOT_USERNAME=Moein_Helperbot` in `.env` to the inline bot username
  (without the `@`).
- When using two Selfbot accounts on separate servers, run inline polling on
  only one server: set `BOT_TOKEN` there. Leave `BOT_TOKEN` empty on the other
  server, but keep the same `BOT_USERNAME`; it can still query the central
  inline bot.
- The polling server automatically allows its logged-in Selfbot account. Add
  the numeric Telegram IDs of other installed Selfbot accounts to
  `BOT_ALLOWED_USER_IDS=id1,id2` in the central server's `.env`. These are
  allowed installations, not owner privileges. Other Telegram users cannot
  open the panel or use its buttons. Restart the central Selfbot after changes.
- Use a separate `SESSION_NAME` for each Telegram account. Settings files are
  stored with their sessions and must not be copied between accounts. Each Selfbot
  client only processes commands sent by its own logged-in account, and
  settings stay separate. The help command
  selects that account's panel language (`.راهنما`/`.دستورات` for Persian,
  `.مساعدة`/`.الأوامر` for Arabic).
- Start the inline bot in a private chat from each account once;
  guardian-button updates are sent privately to the account that pressed the
  button, applied only by its Selfbot, and deleted after processing.
- Enable inline feedback for the bot with BotFather (`/setinlinefeedback`) so
  Telegram returns the selected inline message ID to the bot.
- Run `python Bot.py`, then send `.راهنما` or `.مساعدة` in any chat. The Selfbot
  queries the inline bot and inserts its panel without requiring you to type
  the bot username. The command language selects the panel language; the
  current Selfbot language is used for other help aliases. The home panel
  closes after five seconds if left untouched. Choosing a section cancels the
  timer so the command pages remain open while navigating.
- Any account can query the inline help bot. Guardian changes are sent to the
  account that clicked and saved by that account's own Selfbot; account
  settings are not shared.
- Commands are displayed in monospace formatting so they are easy to select
  and copy from the message.
- The storage section is labeled "نگهبان چت" / "حارس الدردشة". Its inline
  buttons toggle timed-message, deleted-message, and private-message edit
  reports; enabled buttons are green and disabled buttons are red.
- Telegram does not let bots close the inline search/results picker itself;
  the five-second timer starts only after the panel result is selected and sent.

Weather commands:

- Persian: `.هواشناسی اهواز`, `.مقایسه اهواز با مشهد`, `.آموزش هواشناسی`
- Arabic: `.طقس الأهواز`, `.مقارنة الأهواز و مشهد`, `.تعليم الطقس`

Only commands in the selected language are handled. Use the language command
to switch languages.

Photo-to-GIF command (in the Tools section):

- Persian: reply to a photo and send `.گیف`.
- Arabic: reply to a photo and send `.تحويل جيف`.
- The photo is converted to a static GIF without adding artificial zoom or
  overlay text. The output is resized to fit a 720-pixel maximum dimension.
