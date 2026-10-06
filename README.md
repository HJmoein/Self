# Self

Run the Selfbot from the project directory:

```powershell
python Bot.py
```

The bot uses the single Telegram session configured by `SESSION_NAME` in
`.env`. Settings such as the selected language and enabled features are saved in
`.selfbot_settings.json` and restored after restarting the bot.

Weather commands:

- Persian: `.هواشناسی اهواز`, `.مقایسه اهواز با مشهد`, `.آموزش هواشناسی`
- Arabic: `.طقس الأهواز`, `.مقارنة الأهواز و مشهد`, `.تعليم الطقس`

Only commands in the selected language are handled. Use the language command
to switch languages.

Run tests:

```powershell
python -B -m unittest discover
```
