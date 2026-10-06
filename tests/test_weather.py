import asyncio
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from Selfbot import app, core, handlers, ui, weather


def _fake_logout_client(user_id):
    client = unittest.mock.Mock()
    client.connect = AsyncMock()
    client.is_user_authorized = AsyncMock(return_value=True)
    client.get_me = AsyncMock(
        return_value=type("User", (), {"id": user_id})()
    )
    client.log_out = AsyncMock()
    client.is_connected.return_value = False
    return client


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
        self.previous_language = core.get_settings().current_language

    async def asyncTearDown(self):
        core.get_settings().current_language = self.previous_language

    async def test_persian_help_has_readable_sections_and_examples(self):
        core.get_settings().current_language = "fa"
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
        core.get_settings().current_language = "ar"
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
        self.previous_language = core.get_settings().current_language

    async def asyncTearDown(self):
        core.get_settings().current_language = self.previous_language

    async def test_persian_main_help_groups_self_commands(self):
        core.get_settings().current_language = "fa"
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
        core.get_settings().current_language = "ar"
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


class SettingsPersistenceTests(unittest.IsolatedAsyncioTestCase):
    def test_settings_round_trip_restores_language_and_feature_flags(self):
        session_name = Path(core.SESSION_NAME).stem
        settings = core.get_settings()
        original_values = (
            settings.current_language,
            settings.self_enabled,
            settings.timed_save_enabled,
            settings.deleted_save_enabled,
            set(settings.meow_chats),
            {chat_id: set(targets) for chat_id, targets in settings.enemy_targets.items()},
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            settings_path = Path(temporary_directory) / ".selfbot_settings.json"
            with patch.object(core, "SETTINGS_PATH", settings_path):
                settings.current_language = "ar"
                settings.self_enabled = False
                settings.timed_save_enabled = True
                settings.deleted_save_enabled = True
                settings.meow_chats.clear()
                settings.meow_chats.add(-100123)
                settings.enemy_targets.clear()
                settings.enemy_targets[-100456].add(98765)
                core.save_settings()
                restored = core.AccountSettings(session_name)
                core.load_settings(restored)

        try:
            self.assertEqual(restored.current_language, "ar")
            self.assertFalse(restored.self_enabled)
            self.assertTrue(restored.timed_save_enabled)
            self.assertTrue(restored.deleted_save_enabled)
            self.assertEqual(restored.meow_chats, {-100123})
            self.assertEqual(restored.enemy_targets[-100456], {98765})
        finally:
            (
                settings.current_language,
                settings.self_enabled,
                settings.timed_save_enabled,
                settings.deleted_save_enabled,
                old_meow_chats,
                old_enemy_targets,
            ) = original_values
            settings.meow_chats.clear()
            settings.meow_chats.update(old_meow_chats)
            settings.enemy_targets.clear()
            settings.enemy_targets.update(old_enemy_targets)

    async def test_language_change_is_persisted(self):
        settings = core.get_settings()
        old_language = settings.current_language
        try:
            with tempfile.TemporaryDirectory() as temporary_directory:
                settings_path = Path(temporary_directory) / ".selfbot_settings.json"
                with patch.object(core, "SETTINGS_PATH", settings_path):
                    settings.current_language = "fa"
                    wrong_language_event = FakeEvent(".اللغة العربية")
                    await handlers.handler(wrong_language_event)
                    self.assertEqual(settings.current_language, "fa")
                    self.assertEqual(wrong_language_event.edits, [])

                    await handlers.handler(FakeEvent(".زبان عربی"))
                    self.assertEqual(settings.current_language, "ar")

                    wrong_language_event = FakeEvent(".زبان فارسی")
                    await handlers.handler(wrong_language_event)
                    self.assertEqual(settings.current_language, "ar")
                    self.assertEqual(wrong_language_event.edits, [])

                    await handlers.handler(FakeEvent(".اللغة الفارسية"))
                    restored = core.AccountSettings(Path(core.SESSION_NAME).stem)
                    core.load_settings(restored)
            self.assertEqual(restored.current_language, "fa")
        finally:
            settings.current_language = old_language


class ApplicationStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_runs_only_the_primary_selfbot_session(self):
        settings = core.get_settings()
        with (
            patch.object(core.client, "start", new=AsyncMock()) as start,
            patch.object(
                core.client,
                "run_until_disconnected",
                new=AsyncMock(),
            ) as run,
            patch.object(core, "save_settings") as save_settings,
            patch.object(handlers, "register_handlers") as register_handlers,
        ):
            await app.main()

        start.assert_awaited_once_with()
        run.assert_awaited_once_with()
        save_settings.assert_called_once_with()
        register_handlers.assert_called_once_with(core.client)


class WeatherHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_language = core.get_settings().current_language
        self.previous_enabled = core.get_settings().self_enabled
        core.get_settings().self_enabled = True

    async def asyncTearDown(self):
        core.get_settings().current_language = self.previous_language
        core.get_settings().self_enabled = self.previous_enabled

    async def test_weather_commands_are_limited_to_selected_language(self):
        core.get_settings().current_language = "fa"
        persian_event = FakeEvent(".هواشناسی تهران")
        with patch.object(
            weather, "fetch_weather", new=AsyncMock(return_value=make_report("Tehran", 20, 40, 3))
        ) as fetch:
            await handlers.handler(persian_event)
        fetch.assert_awaited_once_with("تهران", "fa")
        self.assertIn("دمای فعلی: 20.0°C", persian_event.edits[-1])

        core.get_settings().current_language = "ar"
        arabic_event = FakeEvent(".طقس طهران")
        with patch.object(
            weather, "fetch_weather", new=AsyncMock(return_value=make_report("Tehran", 20, 40, 3))
        ) as fetch:
            await handlers.handler(arabic_event)
        fetch.assert_awaited_once_with("طهران", "ar")
        self.assertIn("الحرارة الحالية: 20.0°C", arabic_event.edits[-1])

        with patch.object(weather, "fetch_weather", new=AsyncMock()) as fetch:
            core.get_settings().current_language = "fa"
            await handlers.handler(FakeEvent(".طقس Tehran"))
            core.get_settings().current_language = "ar"
            await handlers.handler(FakeEvent(".هواشناسی تهران"))
        fetch.assert_not_awaited()

    async def test_weather_without_city_uses_ahvaz_by_default(self):
        core.get_settings().current_language = "fa"
        persian_event = FakeEvent(".هواشناسی")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(return_value=make_report("Ahvaz", 35, 20, 4)),
        ) as fetch:
            await handlers.handler(persian_event)
        fetch.assert_awaited_once_with("اهواز", "fa")

        core.get_settings().current_language = "ar"
        arabic_event = FakeEvent(".طقس")
        with patch.object(
            weather,
            "fetch_weather",
            new=AsyncMock(return_value=make_report("Ahvaz", 35, 20, 4)),
        ) as fetch:
            await handlers.handler(arabic_event)
        fetch.assert_awaited_once_with("الأهواز", "ar")

    async def test_commands_from_other_language_are_ignored(self):
        settings = core.get_settings()
        old_language = settings.current_language
        old_self_enabled = settings.self_enabled
        old_timed_enabled = settings.timed_save_enabled
        old_deleted_enabled = settings.deleted_save_enabled
        try:
            language_commands = set(
                core.COMMAND_ALIASES["language_fa"]
                + core.COMMAND_ALIASES["language_ar"]
            )

            settings.current_language = "ar"
            settings.self_enabled = False
            event = FakeEvent(".سلف روشن")
            await handlers.handler(event)
            self.assertFalse(settings.self_enabled)
            self.assertEqual(event.edits, [])

            for command in core.PERSIAN_COMMAND_ALIASES - language_commands - {"سلف روشن"}:
                event = FakeEvent(f".{command}")
                await handlers.handler(event)
                self.assertEqual(event.edits, [], command)
            self.assertFalse(settings.timed_save_enabled)

            settings.current_language = "fa"
            event = FakeEvent(".سلف تشغيل")
            await handlers.handler(event)
            self.assertEqual(event.edits, [])

            for command in core.ARABIC_COMMAND_ALIASES - language_commands - {"سلف تشغيل"}:
                event = FakeEvent(f".{command}")
                await handlers.handler(event)
                self.assertEqual(event.edits, [], command)
            self.assertFalse(settings.deleted_save_enabled)

            with patch.object(core, "save_settings"):
                switch_to_arabic = FakeEvent(".زبان عربی")
                await handlers.handler(switch_to_arabic)
                self.assertEqual(settings.current_language, "ar")
                wrong_language_switch = FakeEvent(".زبان فارسی")
                await handlers.handler(wrong_language_switch)
                self.assertEqual(settings.current_language, "ar")
                self.assertEqual(wrong_language_switch.edits, [])
                switch_to_persian = FakeEvent(".اللغة الفارسية")
                await handlers.handler(switch_to_persian)
                self.assertEqual(settings.current_language, "fa")
        finally:
            settings.current_language = old_language
            settings.self_enabled = old_self_enabled
            settings.timed_save_enabled = old_timed_enabled
            settings.deleted_save_enabled = old_deleted_enabled

    async def test_comparison_fetches_both_cities_and_shows_localized_result(self):
        core.get_settings().current_language = "fa"
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
        core.get_settings().current_language = "fa"
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
        core.get_settings().current_language = "ar"
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
        core.get_settings().current_language = "fa"
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
        core.get_settings().current_language = "fa"
        persian_event = FakeEvent(".آموزش")
        await ui.show_weather_help(persian_event)
        self.assertIn(".هواشناسی اهواز", persian_event.edits[0])
        self.assertIn(".مقایسه اهواز با مشهد", persian_event.edits[0])

        core.get_settings().current_language = "ar"
        arabic_event = FakeEvent(".تعليم")
        await ui.show_weather_help(arabic_event)
        self.assertIn(".طقس الأهواز", arabic_event.edits[0])
        self.assertIn(".مقارنة الأهواز و مشهد", arabic_event.edits[0])
        self.assertNotIn(".آموزش", arabic_event.edits[0])


if __name__ == "__main__":
    unittest.main()
