import asyncio
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from Selfbot import account_manager, app, core, handlers, ui, weather


class FakeEvent:
    def __init__(self, raw_text):
        self.raw_text = raw_text
        self.chat_id = 123
        self.edits = []
        self.edit_kwargs = []

    async def edit(self, text, **kwargs):
        self.edits.append(text)
        self.edit_kwargs.append(kwargs)


def make_report(city, temperature, humidity, wind):
    return weather.WeatherReport(
        city=city,
        current={
            "temperature_2m": temperature,
            "relative_humidity_2m": humidity,
            "weather_code": 0,
            "wind_speed_10m": wind,
        },
        daily={
            "temperature_2m_min": [temperature - 3],
            "temperature_2m_max": [temperature + 4],
        },
    )


class WeatherServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_weather_accepts_persian_city_name(self):
        geocoding = {
            "results": [
                {
                    "name": "Tehran",
                    "admin1": "Tehran",
                    "country": "Iran",
                    "latitude": 35.7,
                    "longitude": 51.4,
                    "timezone": "Asia/Tehran",
                }
            ]
        }
        forecast = {
            "timezone": "Asia/Tehran",
            "current": {"temperature_2m": 20, "weather_code": 0},
            "daily": {"temperature_2m_min": [10], "temperature_2m_max": [25]},
        }

        with patch.object(
            weather, "_get_json", new=AsyncMock(side_effect=[geocoding, forecast])
        ) as get_json:
            report = await weather.fetch_weather("تهران", "fa")

        self.assertEqual(report.city, "Tehran, Iran")
        self.assertIn("کمینه / بیشینه: 10.0°C / 25.0°C", weather.format_weather(report, "fa"))
        formatted_report = weather.format_weather(report, "fa")
        self.assertNotIn("منطقه زمانی", formatted_report)
        self.assertNotIn("Open-Meteo", formatted_report)
        geocoding_query = parse_qs(urlparse(get_json.await_args_list[0].args[0]).query)
        self.assertEqual(geocoding_query["name"], ["تهران"])
        self.assertEqual(geocoding_query["language"], ["fa"])

    async def test_geocoding_falls_back_to_other_languages(self):
        geocoding = {
            "results": [
                {
                    "name": "تهران",
                    "country": "ایران",
                    "latitude": 35.7,
                    "longitude": 51.4,
                }
            ]
        }
        forecast = {
            "current": {"temperature_2m": 20},
            "daily": {},
        }
        with patch.object(
            weather,
            "_get_json",
            new=AsyncMock(side_effect=[{}, geocoding, forecast]),
        ) as get_json:
            await weather.fetch_weather("تهران", "en")

        geocoding_languages = [
            parse_qs(urlparse(call.args[0]).query)["language"][0]
            for call in get_json.await_args_list[:2]
        ]
        self.assertEqual(geocoding_languages, ["en", "fa"])

    async def test_fetch_weather_reports_missing_city(self):
        with patch.object(weather, "_get_json", new=AsyncMock(return_value={})):
            with self.assertRaises(weather.CityNotFoundError):
                await weather.fetch_weather("NoSuchCity")

    async def test_fetch_weather_reports_api_failure(self):
        with patch.object(
            weather,
            "_get_json",
            new=AsyncMock(side_effect=weather.WeatherServiceError("offline")),
        ):
            with self.assertRaises(weather.WeatherServiceError):
                await weather.fetch_weather("Tehran")

    def test_command_matching_prefers_longer_alias(self):
        matched = weather.match_command(
            "مقایسه هوا تهران و مشهد",
            core.PERSIAN_WEATHER_COMPARE_COMMANDS,
        )
        self.assertEqual(matched, ("مقایسه هوا", "تهران و مشهد"))

    def test_comparison_summary_and_arabic_format(self):
        first = make_report("Tehran", 30, 20, 12)
        second = make_report("Mashhad", 15, 70, 5)

        persian = weather.format_comparison(first, second, "fa")
        arabic = weather.format_comparison(first, second, "ar")

        self.assertIn("اختلاف دما: 15.0°C (Tehran گرم‌تر است)", persian)
        self.assertIn("فرق درجة الحرارة: 15.0°C (Tehran أعلى حرارة)", arabic)
        self.assertIn("الحرارة الحالية", arabic)
        self.assertNotIn("اختلاف رطوبت", persian)
        self.assertNotIn("اختلاف سرعت باد", persian)
        self.assertNotIn("فرق الرطوبة", arabic)
        self.assertNotIn("فرق سرعة الرياح", arabic)


class WeatherHelpUiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_language = core.current_language

    async def asyncTearDown(self):
        core.current_language = self.previous_language

    async def test_persian_help_has_readable_sections_and_examples(self):
        core.current_language = "fa"
        event = FakeEvent(".آموزش")

        await ui.show_weather_help(event)
        help_text = event.edits[0]

        self.assertEqual(event.edit_kwargs[0]["parse_mode"], "html")
        self.assertIn("🌦 <b>راهنمای هواشناسی</b>", help_text)
        self.assertIn("1️⃣ <b>آب‌وهوای یک شهر</b>", help_text)
        self.assertIn("<code>.هواشناسی اهواز</code>", help_text)
        self.assertNotIn("پیش‌فرض", help_text)
        self.assertIn("2️⃣ <b>مقایسهٔ دو شهر</b>", help_text)
        self.assertIn("<code>.مقایسه اهواز با مشهد</code>", help_text)
        self.assertIn("دمای فعلی", help_text)
        self.assertNotIn("دلیل الطقس", help_text)

    async def test_arabic_help_is_localized_and_lists_arabic_aliases(self):
        core.current_language = "ar"
        event = FakeEvent(".تعليم")

        await ui.show_weather_help(event)
        help_text = event.edits[0]

        self.assertEqual(event.edit_kwargs[0]["parse_mode"], "html")
        self.assertIn("🌦 <b>دليل الطقس</b>", help_text)
        self.assertIn("1️⃣ <b>طقس مدينة واحدة</b>", help_text)
        self.assertIn("<code>.طقس الأهواز</code>", help_text)
        self.assertNotIn("الافتراضي", help_text)
        self.assertNotIn("افتراضياً", help_text)
        self.assertIn("<code>.مقارنة الأهواز و مشهد</code>", help_text)
        self.assertIn("<code>.تعليم الطقس</code>", help_text)
        self.assertNotIn("راهنمای هواشناسی", help_text)


class MainHelpUiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_language = core.current_language

    async def asyncTearDown(self):
        core.current_language = self.previous_language

    async def test_persian_main_help_groups_self_commands(self):
        core.current_language = "fa"
        event = FakeEvent(".راهنما")

        await ui.show_help(event)
        help_text = event.edits[0]

        self.assertEqual(event.edit_kwargs[0]["parse_mode"], "html")
        self.assertTrue(help_text.startswith("╭──────────────╮"))
        self.assertIn("│ <b>دستورات سلف</b> │", help_text)
        self.assertIn("⚙ <b>سلف</b>", help_text)
        self.assertIn("<code>.سلف روشن</code>", help_text)
        self.assertIn("<b>ذخیره پیام‌های حذف‌شده</b>", help_text)
        self.assertIn("<code>.دریافت</code>", help_text)
        self.assertIn("<code>.قلب</code>", help_text)
        self.assertIn("<code>.هواشناسی اهواز</code>", help_text)
        self.assertNotIn("<b>راهنما</b>:", help_text)
        self.assertNotIn("لوحة أوامر السلف", help_text)

    async def test_arabic_main_help_groups_self_commands(self):
        core.current_language = "ar"
        event = FakeEvent(".مساعدة")

        await ui.show_help(event)
        help_text = event.edits[0]

        self.assertEqual(event.edit_kwargs[0]["parse_mode"], "html")
        self.assertTrue(help_text.startswith("╭──────────────╮"))
        self.assertIn("│ <b>أوامر السلف</b> │", help_text)
        self.assertIn("⚙ <b>السلف</b>", help_text)
        self.assertIn("<code>.سلف تشغيل</code>", help_text)
        self.assertIn("<b>حفظ الرسائل المحذوفة</b>", help_text)
        self.assertIn("<code>.استلام</code>", help_text)
        self.assertIn("<code>.الب</code>", help_text)
        self.assertIn("<code>.طقس الأهواز</code>", help_text)
        self.assertNotIn("<b>المساعدة</b>:", help_text)
        self.assertNotIn("پنل دستورات سلف", help_text)


class AccountManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_menu_uses_english_labels(self):
        output = io.StringIO()
        with patch("builtins.input", return_value="3"), redirect_stdout(output):
            await account_manager.main()

        self.assertIn("Add Account", output.getvalue())
        self.assertIn("List Accounts", output.getvalue())
        self.assertIn("Back", output.getvalue())
        self.assertNotIn("Run Account", output.getvalue())

    async def test_account_list_shows_cached_phone_ids_and_names_without_opening_sessions(self):
        paths = [Path("self.session"), Path("account_1.session")]
        cached_profiles = {
            "self": {
                "phone": "+123456789",
                "id": 12345,
                "name": "Test Account",
            }
        }
        output = io.StringIO()
        with (
            patch.object(account_manager, "_session_paths", return_value=paths),
            patch.object(
                account_manager,
                "_read_account_profiles",
                return_value=cached_profiles,
            ),
            patch.object(account_manager, "TelegramClient") as telegram_client,
            patch("builtins.input", return_value="") as prompt,
            redirect_stdout(output),
        ):
            accounts = await account_manager.list_accounts()

        self.assertEqual(len(accounts), 1)
        self.assertIn("Accounts: 1", output.getvalue())
        self.assertIn("Phone: +123456789", output.getvalue())
        self.assertIn("ID: 12345", output.getvalue())
        self.assertIn("Name: Test Account", output.getvalue())
        telegram_client.assert_not_called()
        self.assertNotIn("Session:", output.getvalue())
        self.assertNotIn("self.session", output.getvalue())
        self.assertNotIn("account_1.session", output.getvalue())
        prompt.assert_called_once_with("\nPress Enter or type B to go back: ")

    async def test_add_account_prompts_and_reports_english_success(self):
        user = type(
            "User",
            (),
            {"id": 67890, "first_name": "New", "last_name": "User"},
        )()

        class FakeClient:
            def __init__(self, *args):
                self.connected = False
                self.start_arguments = None

            async def start(self, **kwargs):
                self.connected = True
                self.start_arguments = kwargs

            async def get_me(self):
                return user

            def is_connected(self):
                return self.connected

            async def disconnect(self):
                self.connected = False

        output = io.StringIO()
        with (
            patch("builtins.input", return_value="+123456789"),
            patch.object(account_manager, "_next_session_path", return_value=Path("account_2")),
            patch.object(account_manager, "TelegramClient", FakeClient),
            tempfile.TemporaryDirectory() as temporary_directory,
            patch.object(
                account_manager,
                "ACCOUNT_METADATA_PATH",
                Path(temporary_directory) / ".account_profiles.json",
            ),
            redirect_stdout(output),
        ):
            await account_manager.add_account()
            saved_profiles = json.loads(
                (Path(temporary_directory) / ".account_profiles.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertIn("Account added successfully.", output.getvalue())
        self.assertIn("Phone: +123456789", output.getvalue())
        self.assertIn("ID: 67890", output.getvalue())
        self.assertIn("Name: New User", output.getvalue())
        self.assertNotIn("Session:", output.getvalue())
        self.assertEqual(
            saved_profiles["account_2"],
            {"id": 67890, "name": "New User", "phone": "+123456789"},
        )

    async def test_back_cancels_account_add_flow(self):
        output = io.StringIO()
        with (
            patch("builtins.input", return_value="B"),
            patch.object(account_manager, "TelegramClient") as telegram_client,
            redirect_stdout(output),
        ):
            await account_manager.add_account()

        telegram_client.assert_not_called()

    async def test_back_during_login_code_returns_to_account_menu(self):
        class FakeClient:
            def __init__(self, *args):
                self.connected = False

            async def start(self, **kwargs):
                self.connected = True
                kwargs["code_callback"]()

            def is_connected(self):
                return self.connected

            async def disconnect(self):
                self.connected = False

        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=["+123456789", "B"]),
            patch.object(
                account_manager,
                "_next_session_path",
                return_value=Path("account_2"),
            ),
            patch.object(account_manager, "TelegramClient", FakeClient),
            redirect_stdout(output),
        ):
            await account_manager.add_account()

        self.assertIn("Account setup cancelled.", output.getvalue())

    async def test_account_manager_lists_then_back_returns_to_menu(self):
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=["2", "", "3"]),
            patch.object(account_manager, "list_accounts", new=AsyncMock()) as listing,
            redirect_stdout(output),
        ):
            await account_manager.main()

        listing.assert_awaited_once()
        self.assertGreaterEqual(output.getvalue().count("=== SELFBOT ACCOUNT MANAGER ==="), 2)


class SettingsPersistenceTests(unittest.IsolatedAsyncioTestCase):
    def test_settings_round_trip_restores_global_and_per_chat_options(self):
        original_values = (
            core.current_language,
            core.self_enabled,
            core.timed_save_enabled,
            core.deleted_save_enabled,
            set(core.meow_chats),
            {chat_id: set(targets) for chat_id, targets in core.enemy_targets.items()},
        )
        try:
            core.current_language = "ar"
            core.self_enabled = False
            core.timed_save_enabled = True
            core.deleted_save_enabled = True
            core.meow_chats.clear()
            core.meow_chats.add(-100123)
            core.enemy_targets.clear()
            core.enemy_targets[-100456].add(98765)

            with tempfile.TemporaryDirectory() as temporary_directory:
                settings_path = Path(temporary_directory) / "settings.json"
                core.save_settings(settings_path)

                core.current_language = "fa"
                core.self_enabled = True
                core.timed_save_enabled = False
                core.deleted_save_enabled = False
                core.meow_chats.clear()
                core.enemy_targets.clear()
                core.load_settings(settings_path)

            self.assertEqual(core.current_language, "ar")
            self.assertFalse(core.self_enabled)
            self.assertTrue(core.timed_save_enabled)
            self.assertTrue(core.deleted_save_enabled)
            self.assertEqual(core.meow_chats, {-100123})
            self.assertEqual(core.enemy_targets[-100456], {98765})
        finally:
            (
                core.current_language,
                core.self_enabled,
                core.timed_save_enabled,
                core.deleted_save_enabled,
                saved_meow_chats,
                saved_enemy_targets,
            ) = original_values
            core.meow_chats.clear()
            core.meow_chats.update(saved_meow_chats)
            core.enemy_targets.clear()
            core.enemy_targets.update(saved_enemy_targets)

    async def test_language_command_saves_changed_setting(self):
        event = FakeEvent(".زبان عربی")
        previous_language = core.current_language
        try:
            with patch.object(core, "save_settings") as save_settings:
                await handlers.handler(event)

            self.assertEqual(core.current_language, "ar")
            save_settings.assert_called_once_with()
            self.assertIn("تم تفعيل اللغة العربية", event.edits[-1])
        finally:
            core.current_language = previous_language


class ApplicationStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_normal_startup_runs_selfbot_without_account_listing(self):
        startup_order = []
        with (
            patch.object(app.sys, "argv", ["Bot.py"]),
            patch.object(
                core.client,
                "start",
                new=AsyncMock(side_effect=lambda: startup_order.append("start")),
            ) as start,
            patch.object(
                core.client,
                "run_until_disconnected",
                new=AsyncMock(
                    side_effect=lambda: startup_order.append("run")
                ),
            ) as run,
            patch.object(
                core.client,
                "get_me",
                new=AsyncMock(
                    return_value=type(
                        "User",
                        (),
                        {
                            "id": 12345,
                            "first_name": "Test",
                            "last_name": "Account",
                            "phone": "+123456789",
                        },
                    )(),
                ),
            ),
            patch.object(account_manager, "save_account_profile") as save_profile,
            patch.object(account_manager, "_read_account_profiles", return_value={}),
            patch.object(handlers, "register_handlers") as register_handlers,
            patch.object(account_manager, "main", new=AsyncMock()) as manager,
            patch.object(
                account_manager,
                "list_accounts",
                new=AsyncMock(),
            ) as listing,
            patch("builtins.print") as terminal_print,
        ):
            await app.main()

        start.assert_awaited_once()
        run.assert_awaited_once()
        manager.assert_not_awaited()
        save_profile.assert_called_once()
        register_handlers.assert_called_once_with(core.client)
        terminal_print.assert_any_call("SelfBot is running...")
        self.assertEqual(startup_order, ["start", "run"])
        listing.assert_not_awaited()

    async def test_normal_startup_starts_and_registers_added_accounts(self):
        class AddedClient:
            def __init__(self, session_name, api_id, api_hash):
                self.session_name = Path(session_name).name
                self.connected = False

            async def connect(self):
                self.connected = True

            async def is_user_authorized(self):
                return True

            async def get_me(self):
                return type(
                    "User",
                    (),
                    {"id": 67890, "first_name": "Added", "last_name": "Account"},
                )()

            async def run_until_disconnected(self):
                return None

            def is_connected(self):
                return self.connected

        with tempfile.TemporaryDirectory() as temporary_directory:
            session_dir = Path(temporary_directory)
            (session_dir / "account_1.session").touch()
            with (
                patch.object(app.sys, "argv", ["Bot.py"]),
                patch.object(core.client, "start", new=AsyncMock()) as start,
                patch.object(
                    core.client,
                    "run_until_disconnected",
                    new=AsyncMock(),
                ) as run,
                patch.object(
                    core.client,
                    "get_me",
                    new=AsyncMock(
                        return_value=type(
                            "User",
                            (),
                            {"id": 12345, "first_name": "Main", "last_name": "Account"},
                        )(),
                    ),
                ),
                patch.object(
                    account_manager,
                    "_read_account_profiles",
                    return_value={"self": {}, "account_1": {}},
                ),
                patch.object(account_manager, "SESSION_DIRECTORY", session_dir),
                patch.object(app, "TelegramClient", AddedClient),
                patch.object(handlers, "register_handlers") as register_handlers,
                patch.object(account_manager, "save_account_profile") as save_profile,
                patch.object(core, "meow_chats", set()),
            ):
                await app.main()

        start.assert_awaited_once()
        run.assert_awaited_once()
        registered_clients = [
            call.args[0] for call in register_handlers.call_args_list
        ]
        self.assertIs(registered_clients[0], core.client)
        self.assertEqual(registered_clients[1].session_name, "account_1")
        self.assertEqual(save_profile.call_count, 2)

    async def test_registered_handler_uses_owning_telegram_client(self):
        client = type(
            "Client",
            (),
            {
                "add_event_handler": lambda self, callback, builder: self.handlers.append(
                    callback
                ),
                "handlers": [],
            },
        )()
        selected_clients = []

        async def verify_client(event):
            selected_clients.append(core.get_client())

        with patch.object(handlers, "cache_messages", verify_client):
            handlers.register_handlers(client)
            await client.handlers[0](object())

        self.assertEqual(selected_clients, [client])

    async def test_accounts_argument_opens_manager(self):
        with (
            patch.object(app.sys, "argv", ["Bot.py", "--accounts"]),
            patch.object(account_manager, "main", new=AsyncMock()) as manager,
            patch.object(core.client, "start", new=AsyncMock()) as start,
        ):
            await app.main()

        manager.assert_awaited_once()
        start.assert_not_awaited()

    async def test_list_accounts_argument_shows_list_without_starting_bot(self):
        with (
            patch.object(app.sys, "argv", ["Bot.py", "--list-accounts"]),
            patch.object(
                account_manager,
                "list_accounts",
                new=AsyncMock(),
            ) as listing,
            patch.object(core.client, "start", new=AsyncMock()) as start,
        ):
            await app.main()

        listing.assert_awaited_once_with(wait_for_back=False)
        start.assert_not_awaited()


class WeatherHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_language = core.current_language
        self.previous_enabled = core.self_enabled
        core.self_enabled = True

    async def asyncTearDown(self):
        core.current_language = self.previous_language
        core.self_enabled = self.previous_enabled

    async def test_weather_commands_are_limited_to_selected_language(self):
        core.current_language = "fa"
        persian_event = FakeEvent(".هواشناسی تهران")
        with patch.object(
            weather, "fetch_weather", new=AsyncMock(return_value=make_report("Tehran", 20, 40, 3))
        ) as fetch:
            await handlers.handler(persian_event)
        fetch.assert_awaited_once_with("تهران", "fa")
        self.assertIn("دمای فعلی: 20.0°C", persian_event.edits[-1])

        core.current_language = "ar"
        arabic_event = FakeEvent(".طقس طهران")
        with patch.object(
            weather, "fetch_weather", new=AsyncMock(return_value=make_report("Tehran", 20, 40, 3))
        ) as fetch:
            await handlers.handler(arabic_event)
        fetch.assert_awaited_once_with("طهران", "ar")
        self.assertIn("الحرارة الحالية: 20.0°C", arabic_event.edits[-1])

        with patch.object(weather, "fetch_weather", new=AsyncMock()) as fetch:
            core.current_language = "fa"
            await handlers.handler(FakeEvent(".طقس Tehran"))
            core.current_language = "ar"
            await handlers.handler(FakeEvent(".هواشناسی تهران"))
        fetch.assert_not_awaited()

    async def test_weather_without_city_uses_ahvaz_by_default(self):
        core.current_language = "fa"
        persian_event = FakeEvent(".هواشناسی")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(return_value=make_report("Ahvaz", 35, 20, 4)),
        ) as fetch:
            await handlers.handler(persian_event)
        fetch.assert_awaited_once_with("اهواز", "fa")

        core.current_language = "ar"
        arabic_event = FakeEvent(".طقس")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(return_value=make_report("Ahvaz", 35, 20, 4)),
        ) as fetch:
            await handlers.handler(arabic_event)
        fetch.assert_awaited_once_with("الأهواز", "ar")

    async def test_comparison_fetches_both_cities_and_shows_localized_result(self):
        core.current_language = "fa"
        event = FakeEvent(".مقایسه تهران با مشهد")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(
                side_effect=[
                    make_report("Tehran", 30, 20, 12),
                    make_report("Mashhad", 15, 70, 5),
                ]
            ),
        ) as fetch:
            await handlers.handler(event)

        self.assertEqual(
            fetch.await_args_list[0].args[0],
            "تهران",
        )
        self.assertEqual(fetch.await_args_list[1].args[0], "مشهد")
        self.assertEqual(fetch.await_args_list[0].args[1], "fa")
        self.assertEqual(fetch.await_args_list[1].args[1], "fa")
        self.assertIn("مقایسه آب‌وهوا", event.edits[-1])
        self.assertIn("اختلاف دما: 15.0°C", event.edits[-1])

    async def test_comparison_requests_cities_concurrently(self):
        core.current_language = "fa"
        event = FakeEvent(".مقایسه تهران با مشهد")
        started = 0
        both_started = asyncio.Event()

        async def fetch_concurrently(city, language):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=1)
            self.assertEqual(language, "fa")
            return make_report(city, 20, 50, 4)

        with patch.object(
            weather, "fetch_weather", new=AsyncMock(side_effect=fetch_concurrently)
        ):
            await handlers.handler(event)

        self.assertIn("تهران", event.edits[-1])
        self.assertIn("مشهد", event.edits[-1])

    async def test_api_error_is_reported_without_raising(self):
        core.current_language = "ar"
        event = FakeEvent(".طقس طهران")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(side_effect=weather.WeatherServiceError("offline")),
        ):
            with self.assertLogs(core.logger, level="WARNING"):
                await handlers.handler(event)

        self.assertIn("خدمة الطقس غير متاحة", event.edits[-1])

    async def test_missing_city_in_comparison_is_reported(self):
        core.current_language = "fa"
        event = FakeEvent(".مقایسه گاتهام با تهران")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(
                side_effect=[
                    weather.CityNotFoundError("گاتهام"),
                    make_report("Tehran", 20, 50, 4),
                ]
            ),
        ):
            await handlers.handler(event)

        self.assertIn("شهری با نام «گاتهام» پیدا نشد", event.edits[-1])

    async def test_weather_help_is_localized_and_lists_commands(self):
        core.current_language = "fa"
        persian_event = FakeEvent(".آموزش")
        await ui.show_weather_help(persian_event)
        self.assertIn(".هواشناسی اهواز", persian_event.edits[0])
        self.assertIn(".مقایسه اهواز با مشهد", persian_event.edits[0])

        core.current_language = "ar"
        arabic_event = FakeEvent(".تعليم")
        await ui.show_weather_help(arabic_event)
        self.assertIn(".طقس الأهواز", arabic_event.edits[0])
        self.assertIn(".مقارنة الأهواز و مشهد", arabic_event.edits[0])
        self.assertNotIn(".آموزش", arabic_event.edits[0])


if __name__ == "__main__":
    unittest.main()
