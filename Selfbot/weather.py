"""Asynchronous weather lookup using the free Open-Meteo APIs."""

import asyncio
import json
import math
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10
MAX_CITY_NAME_LENGTH = 100


class WeatherError(Exception):
    """Base error for expected weather-service failures."""


class CityNotFoundError(WeatherError):
    """The geocoding service returned no matching city."""


class InvalidCityNameError(WeatherError):
    """The supplied city name is empty or longer than the supported limit."""


class WeatherServiceError(WeatherError):
    """The weather service could not return usable data."""


@dataclass(frozen=True)
class WeatherReport:
    city: str
    current: dict
    daily: dict


def match_command(text, commands):
    for command in sorted(commands, key=len, reverse=True):
        if text == command:
            return command, ""
        if text.startswith(command + " "):
            return command, text[len(command):].strip()
    return None


def _request_json(url):
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Selfbot/1.0"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.load(response)
    except HTTPError as error:
        raise WeatherServiceError("Weather API returned an HTTP error.") from error
    except (URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise WeatherServiceError("Weather API request failed.") from error

    if not isinstance(data, dict):
        raise WeatherServiceError("Weather API returned an invalid response.")
    return data


async def _get_json(url):
    return await asyncio.to_thread(_request_json, url)


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


async def fetch_weather(city, language="en"):
    city = city.strip()
    if not city or len(city) > MAX_CITY_NAME_LENGTH:
        raise InvalidCityNameError(city)

    language_order = [language] if language in {"fa", "ar", "en"} else ["en"]
    language_order.extend(
        item for item in ("fa", "ar", "en") if item not in language_order
    )
    results = None
    for geocoding_language in language_order:
        geocoding_parameters = {
            "name": city,
            "count": 5,
            "language": geocoding_language,
            "format": "json",
        }
        geocoding_url = f"{GEOCODING_URL}?{urlencode(geocoding_parameters)}"
        locations = await _get_json(geocoding_url)
        if locations.get("error"):
            raise WeatherServiceError("Geocoding API returned an error.")
        candidates = locations.get("results")
        if candidates is not None and not isinstance(candidates, list):
            raise WeatherServiceError("Geocoding API returned an invalid response.")
        if candidates:
            results = candidates
            break
    if not results:
        raise CityNotFoundError(city)

    location = results[0]
    if not isinstance(location, dict):
        raise WeatherServiceError("Geocoding API returned an invalid location.")
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if not _is_number(latitude) or not _is_number(longitude):
        raise WeatherServiceError("Geocoding API returned invalid coordinates.")

    forecast_parameters = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "is_day,precipitation,weather_code,cloud_cover,wind_speed_10m,"
            "wind_direction_10m,wind_gusts_10m"
        ),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "timezone": "auto",
        "forecast_days": 1,
    }
    forecast_url = f"{FORECAST_URL}?{urlencode(forecast_parameters)}"
    forecast = await _get_json(forecast_url)
    if forecast.get("error"):
        raise WeatherServiceError("Forecast API returned an error.")
    current = forecast.get("current")
    daily = forecast.get("daily")
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise WeatherServiceError("Forecast API returned incomplete weather data.")
    if not _is_number(current.get("temperature_2m")):
        raise WeatherServiceError("Forecast API returned no current temperature.")

    name_parts = (
        location.get("name"),
        location.get("admin1"),
        location.get("country"),
    )
    city_label = ", ".join(
        dict.fromkeys(part for part in name_parts if isinstance(part, str) and part)
    )
    if not city_label:
        city_label = city

    return WeatherReport(
        city=city_label,
        current=current,
        daily=daily,
    )


WEATHER_CONDITIONS = {
    0: ("☀️", "آسمان صاف", "سماء صافية"),
    1: ("🌤️", "عمدتاً صاف", "صافٍ غالباً"),
    2: ("⛅", "نیمه‌ابری", "غائم جزئياً"),
    3: ("☁️", "ابری", "غائم"),
    45: ("🌫️", "مه", "ضباب"),
    48: ("🌫️", "مه یخ‌زده", "ضباب متجمّد"),
    51: ("🌦️", "نم‌نم باران خفیف", "رذاذ خفيف"),
    53: ("🌦️", "نم‌نم باران", "رذاذ"),
    55: ("🌧️", "نم‌نم باران شدید", "رذاذ كثيف"),
    56: ("🌧️", "نم‌نم باران یخ‌زده خفیف", "رذاذ متجمّد خفيف"),
    57: ("🌧️", "نم‌نم باران یخ‌زده شدید", "رذاذ متجمّد كثيف"),
    61: ("🌧️", "باران خفیف", "مطر خفيف"),
    63: ("🌧️", "باران", "مطر"),
    65: ("🌧️", "باران شدید", "مطر غزير"),
    66: ("🌧️", "باران یخ‌زده خفیف", "مطر متجمّد خفيف"),
    67: ("🌧️", "باران یخ‌زده شدید", "مطر متجمّد غزير"),
    71: ("🌨️", "برف خفیف", "ثلوج خفيفة"),
    73: ("🌨️", "برف", "ثلوج"),
    75: ("❄️", "برف شدید", "ثلوج كثيفة"),
    77: ("🌨️", "دانه‌های برف", "حبوب ثلجية"),
    80: ("🌦️", "رگبار خفیف", "زخات خفيفة"),
    81: ("🌧️", "رگبار", "زخات"),
    82: ("⛈️", "رگبار شدید", "زخات غزيرة"),
    85: ("🌨️", "رگبار برف خفیف", "زخات ثلجية خفيفة"),
    86: ("❄️", "رگبار برف شدید", "زخات ثلجية كثيفة"),
    95: ("⛈️", "رعدوبرق", "عاصفة رعدية"),
    96: ("⛈️", "رعدوبرق و تگرگ خفیف", "عاصفة رعدية وبَرَد خفيف"),
    99: ("⛈️", "رعدوبرق و تگرگ شدید", "عاصفة رعدية وبَرَد كثيف"),
}


def _number(value, suffix="", precision=1):
    if not _is_number(value):
        return "—"
    return f"{value:.{precision}f}{suffix}"


def _daily_value(daily, key):
    values = daily.get(key)
    if isinstance(values, list):
        return values[0] if values else None
    return values


def _condition(code, language):
    if not isinstance(code, int):
        return "نامشخص" if language == "fa" else "غير معروف"
    condition = WEATHER_CONDITIONS.get(code)
    if condition is None:
        return "نامشخص" if language == "fa" else "غير معروف"
    return f"{condition[0]} {condition[1 if language == 'fa' else 2]}"


def _compass_direction(degrees):
    if not _is_number(degrees):
        return "—"
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return directions[round(degrees / 45) % len(directions)]


def format_weather(report, language):
    fa = language == "fa"
    current = report.current
    daily = report.daily
    temperature_unit = "°C"
    wind_unit = "km/h"
    condition = _condition(current.get("weather_code"), language)
    minimum = _daily_value(daily, "temperature_2m_min")
    maximum = _daily_value(daily, "temperature_2m_max")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")
    labels = {
        "temperature": "دمای فعلی" if fa else "الحرارة الحالية",
        "condition": "وضعیت" if fa else "الحالة",
        "range": "کمینه / بیشینه" if fa else "الصغرى / العظمى",
        "humidity": "رطوبت" if fa else "الرطوبة",
        "wind": "سرعت باد" if fa else "سرعة الرياح",
        "direction": "جهت باد" if fa else "اتجاه الرياح",
        "gusts": "تندباد" if fa else "هبات الرياح",
        "feels_like": "دمای حسی" if fa else "الحرارة المحسوسة",
        "precipitation": "بارش فعلی" if fa else "الهطول الحالي",
        "precipitation_chance": (
            "احتمال بارش امروز" if fa else "احتمال الهطول اليوم"
        ),
        "clouds": "پوشش ابر" if fa else "الغطاء السحابي",
        "uv": (
            "شاخص فرابنفش امروز"
            if fa
            else "مؤشر الأشعة فوق البنفسجية اليوم"
        ),
    }
    lines = [
        f"📍 {report.city}",
        f"🌡️ {labels['temperature']}: "
        f"{_number(current.get('temperature_2m'), temperature_unit)}",
        f"🌤️ {labels['condition']}: {condition}",
        f"↕️ {labels['range']}: "
        f"{_number(minimum, temperature_unit)} / "
        f"{_number(maximum, temperature_unit)}",
        f"💧 {labels['humidity']}: {_number(humidity, '%', 0)}",
        f"💨 {labels['wind']}: {_number(wind, f' {wind_unit}')}",
        f"🧭 {labels['direction']}: "
        f"{_compass_direction(current.get('wind_direction_10m'))}",
        f"🌬️ {labels['gusts']}: "
        f"{_number(current.get('wind_gusts_10m'), f' {wind_unit}')}",
        f"🤔 {labels['feels_like']}: "
        f"{_number(current.get('apparent_temperature'), temperature_unit)}",
        f"☔ {labels['precipitation']}: "
        f"{_number(current.get('precipitation'), ' mm')}",
        f"🌧️ {labels['precipitation_chance']}: "
        f"{_number(_daily_value(daily, 'precipitation_probability_max'), '%', 0)}",
        f"☁️ {labels['clouds']}: {_number(current.get('cloud_cover'), '%', 0)}",
        f"🔆 {labels['uv']}: "
        f"{_number(_daily_value(daily, 'uv_index_max'))}",
    ]
    return "\n".join(lines)


def format_comparison(first, second, language):
    fa = language == "fa"
    summary = ["🔎 " + ("جمع‌بندی" if fa else "الخلاصة")]
    first_temperature = first.current.get("temperature_2m")
    second_temperature = second.current.get("temperature_2m")
    if _is_number(first_temperature) and _is_number(second_temperature):
        difference = abs(first_temperature - second_temperature)
        if first_temperature == second_temperature:
            summary.append(
                f"• {'اختلاف دما' if fa else 'فرق درجة الحرارة'}: "
                f"{_number(difference, '°C')} "
                f"({'دمای دو شهر برابر است' if fa else 'درجة الحرارة متساوية في المدينتين'})"
            )
        else:
            warmer = (
                first if first_temperature > second_temperature else second
            )
            summary.append(
                f"• {'اختلاف دما' if fa else 'فرق درجة الحرارة'}: "
                f"{_number(difference, '°C')} "
                f"({warmer.city} "
                f"{'گرم‌تر است' if fa else 'أعلى حرارة'})"
            )
    else:
        summary.append(
            "اطلاعات کافی نیست" if fa else "لا تتوفر بيانات كافية"
        )

    heading = "📊 مقایسه آب‌وهوا" if fa else "📊 مقارنة الطقس"
    return (
        f"{heading}\n\n"
        f"{format_weather(first, language)}\n\n"
        f"{format_weather(second, language)}\n\n"
        + "\n".join(summary)
    )


def error_message(error, language):
    fa = language == "fa"
    if isinstance(error, InvalidCityNameError):
        if fa:
            return "نام شهر معتبر نیست؛ لطفاً نامی کوتاه‌تر و معتبر وارد کنید."
        return "اسم المدينة غير صالح؛ أدخل اسماً أقصر وصحيحاً."
    if isinstance(error, CityNotFoundError):
        if fa:
            return f"شهری با نام «{error}» پیدا نشد. املای نام شهر را بررسی کنید یا نام انگلیسی آن را امتحان کنید."
        return f"لم يتم العثور على مدينة باسم «{error}». تحقق من كتابة الاسم أو جرّب الاسم بالإنجليزية."
    if fa:
        return "سرویس هواشناسی در دسترس نیست یا پاسخ معتبری نداد. اتصال اینترنت را بررسی کنید و کمی بعد دوباره تلاش کنید."
    return "خدمة الطقس غير متاحة أو لم تُرجع بيانات صالحة. تحقق من اتصال الإنترنت وحاول مجدداً بعد قليل."
