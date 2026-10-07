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
- Enable inline feedback for the bot with BotFather (`/setinlinefeedback`) so
  Telegram returns the selected inline message ID to the bot.
- Run `python Bot.py`, then send `.راهنما` or `.مساعدة` in any chat. The Selfbot
  queries the inline bot and inserts its panel without requiring you to type
  the bot username. The command language selects the panel language; the
  current Selfbot language is used for other help aliases. The home panel
  closes after five seconds if left untouched. Choosing a section cancels the
  timer so the command pages remain open while navigating.
- Only the Telegram account running the Selfbot can open or use the inline
  panel; other accounts receive no panel and cannot navigate its buttons.
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
