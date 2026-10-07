# Self

Run the Selfbot from the project directory:

```powershell
python Bot.py
```

The bot uses the single Telegram session configured by `SESSION_NAME` in
`.env`. Settings such as the selected language and enabled features are saved in
`.selfbot_settings.json` and restored after restarting the bot.

Inline mode:

- Add your Telegram Bot API token as `BOT_TOKEN=...` in `.env` (keep it secret).
- Set `BOT_USERNAME=Moein_Helperbot` in `.env` to the inline bot username
  (without the `@`).
- When using two Selfbot accounts on separate servers, run inline polling on
  only one server: set `BOT_TOKEN` there and list both Telegram account IDs in
  `BOT_OWNER_IDS=id1,id2`. Leave `BOT_TOKEN` empty on the other server, but
  keep the same `BOT_USERNAME`; it can still query the central inline bot.
- Use a separate `SESSION_NAME` and that server's own `.selfbot_settings.json`
  for each Telegram account; do not copy one account's settings file to the
  other server. Each Selfbot client only processes commands sent by its own
  logged-in account. The help command
  selects that account's panel language (`.راهنما`/`.دستورات` for Persian,
  `.مساعدة`/`.الأوامر` for Arabic).
- Add `BOT_OWNER_IDS=id1,id2` on the server running the inline bot, using both
  Telegram user IDs. Start the inline bot in a private chat from each account
  once; guardian-button updates are sent privately to the account that pressed
  the button, applied only by its Selfbot, and deleted after processing.
- Enable inline feedback for the bot with BotFather (`/setinlinefeedback`) so
  Telegram returns the selected inline message ID to the bot.
- Run `python Bot.py`, then send `.راهنما` or `.مساعدة` in any chat. The Selfbot
  queries the inline bot and inserts its panel without requiring you to type
  the bot username. The command language selects the panel language; the
  current Selfbot language is used for other help aliases. The home panel
  closes after five seconds if left untouched. Choosing a section cancels the
  timer so the command pages remain open while navigating.
- Only Telegram accounts listed in `BOT_OWNER_IDS` can open or use the inline
  panel. Guardian settings are read from and saved by that account's own
  Selfbot; the inline bot keeps no separate settings file.
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

Photo GIF command (in the Tools section):

- Persian: reply to a photo and send `.گیف متن دلخواه`.
- Arabic: reply to a photo and send `.تحويل جيف النص`.
- The text is rendered on a looping GIF. The output is resized to fit a
  720-pixel maximum dimension; text is limited to 160 characters.
