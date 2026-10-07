import asyncio
import json
import logging
import os
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

from telethon import TelegramClient
from telethon.errors import FloodWaitError


env_path = Path(__file__).resolve().parent.parent / ".env"

for env_line in env_path.read_text(encoding="utf-8").splitlines():
    env_line = env_line.strip()
    if not env_line or env_line.startswith("#"):
        continue
    key, separator, value = env_line.partition("=")
    if not separator or not key.strip():
        raise ValueError("Each .env entry must use KEY=VALUE format.")
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    os.environ.setdefault(key.strip(), value)

_api_id = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "self")

if not _api_id or not API_HASH:
    raise RuntimeError("Set API_ID and API_HASH in the .env file before running Main.py.")

try:
    API_ID = int(_api_id)
except ValueError as error:
    raise RuntimeError("API_ID must be an integer.") from error

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
logger = logging.getLogger(__name__)
SETTINGS_PATH = Path(__file__).resolve().parent.parent / ".selfbot_settings.json"


def get_client():
    return client


@dataclass
class AccountSettings:
    session_name: str
    current_language: str = "fa"
    self_enabled: bool = True
    timed_save_enabled: bool = False
    deleted_save_enabled: bool = False
    edited_save_enabled: bool = False
    meow_chats: set = field(default_factory=set)
    enemy_targets: dict = field(default_factory=lambda: defaultdict(set))
    enemy_counters: dict = field(default_factory=lambda: defaultdict(int))
    tasks: dict = field(default_factory=dict)
    message_cache: dict = field(
        default_factory=lambda: defaultdict(lambda: deque(maxlen=1000))
    )
    message_index: dict = field(default_factory=lambda: defaultdict(set))
    deleted_messages: dict = field(default_factory=lambda: defaultdict(list))


def get_settings():
    return _settings


def settings_path_for(session_name):
    return SETTINGS_PATH


def load_settings(settings, path=None):
    settings_path = Path(path) if path is not None else settings_path_for(
        settings.session_name
    )
    try:
        with settings_path.open(encoding="utf-8") as settings_file:
            saved_values = json.load(settings_file)
    except FileNotFoundError:
        return
    except (OSError, json.JSONDecodeError) as error:
        logger.error(
            "Could not load Selfbot settings from %s: %s",
            settings_path,
            type(error).__name__,
            exc_info=True,
        )
        raise RuntimeError(
            f"Could not load saved settings from {settings_path}"
        ) from error

    if not isinstance(saved_values, dict):
        raise RuntimeError(f"Invalid settings format in {settings_path}")

    language = saved_values.get("current_language", "fa")
    boolean_settings = {
        "self_enabled": saved_values.get("self_enabled", True),
        "timed_save_enabled": saved_values.get("timed_save_enabled", False),
        "deleted_save_enabled": saved_values.get("deleted_save_enabled", False),
        "edited_save_enabled": saved_values.get("edited_save_enabled", False),
    }
    if not isinstance(language, str) or language not in {"fa", "ar"} or any(
        not isinstance(value, bool) for value in boolean_settings.values()
    ):
        raise RuntimeError(f"Invalid settings values in {settings_path}")

    raw_meow_chats = saved_values.get("meow_chats", [])
    raw_enemy_targets = saved_values.get("enemy_targets", {})
    if not isinstance(raw_meow_chats, list) or not isinstance(
        raw_enemy_targets, dict
    ):
        raise RuntimeError(f"Invalid chat settings in {settings_path}")

    def valid_id(value):
        return isinstance(value, int) and not isinstance(value, bool)

    if not all(valid_id(chat_id) for chat_id in raw_meow_chats):
        raise RuntimeError(f"Invalid meow chat IDs in {settings_path}")
    restored_enemies = {}
    for chat_id, target_ids in raw_enemy_targets.items():
        try:
            numeric_chat_id = int(chat_id)
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"Invalid enemy chat ID in {settings_path}"
            ) from error
        if (
            not isinstance(target_ids, list)
            or not all(valid_id(target_id) for target_id in target_ids)
        ):
            raise RuntimeError(f"Invalid enemy targets in {settings_path}")
        restored_enemies[numeric_chat_id] = set(target_ids)

    settings.current_language = language
    settings.self_enabled = boolean_settings["self_enabled"]
    settings.timed_save_enabled = boolean_settings["timed_save_enabled"]
    settings.deleted_save_enabled = boolean_settings["deleted_save_enabled"]
    settings.edited_save_enabled = boolean_settings["edited_save_enabled"]
    settings.meow_chats.clear()
    settings.meow_chats.update(raw_meow_chats)
    settings.enemy_targets.clear()
    settings.enemy_targets.update(restored_enemies)


def save_settings(path=None):
    settings = get_settings()
    settings_path = Path(path) if path is not None else settings_path_for(
        settings.session_name
    )
    saved_values = {
        "current_language": get_settings().current_language,
        "self_enabled": get_settings().self_enabled,
        "timed_save_enabled": get_settings().timed_save_enabled,
        "deleted_save_enabled": get_settings().deleted_save_enabled,
        "edited_save_enabled": get_settings().edited_save_enabled,
        "meow_chats": sorted(get_settings().meow_chats),
        "enemy_targets": {
            str(chat_id): sorted(target_ids)
            for chat_id, target_ids in get_settings().enemy_targets.items()
            if target_ids
        },
    }
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=settings_path.parent,
            prefix=f"{settings_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as settings_file:
            temporary_path = Path(settings_file.name)
            json.dump(saved_values, settings_file, ensure_ascii=False, indent=2)
            settings_file.write("\n")
        os.replace(temporary_path, settings_path)
        if os.name == "posix":
            settings_path.chmod(0o600)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


_settings = AccountSettings(session_name=Path(SESSION_NAME).stem)
load_settings(_settings)

ENEMY_INSULTS = [
    "منیوچ الخرا",
    "الزربا",
    "عیر بیک",
    "عیر ابعزک",
    "گواد",
    "ابو عنیص",
    "ابو عز",
    "روح نیچ",
    "اینجوین بیک",
]
STORY_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?P<username>[A-Za-z0-9_]+)/s/(?P<story_id>\d+)/?$"
)
CHANNEL_LINK_PATTERN = re.compile(
    r"^(?:https?://)?t\.me/(?:(?P<username>[A-Za-z0-9_]+)|c/(?P<private_id>\d+))/(?P<message_id>\d+)/?$"
)
STORY_COMMAND = "دانلود استوری"
ARABIC_STORY_COMMAND = "تحميل قصة"
PERSIAN_HELP_COMMANDS = ("راهنما", "دستورات")
ARABIC_HELP_COMMANDS = ("مساعدة", "الأوامر")
PERSIAN_WEATHER_COMMANDS = ("هواشناسی", "هوا")
PERSIAN_WEATHER_COMPARE_COMMANDS = ("مقایسه هوا", "مقایسه")
PERSIAN_WEATHER_HELP_COMMANDS = ("آموزش هواشناسی", "آموزش")
ARABIC_WEATHER_COMMANDS = ("الطقس", "طقس")
ARABIC_WEATHER_COMPARE_COMMANDS = ("مقارنة الطقس", "مقارنة")
ARABIC_WEATHER_HELP_COMMANDS = ("تعليم الطقس", "تعليم")
COMMAND_ALIASES = {
    "self_on": ("سلف روشن", "سلف تشغيل", "السلف تشغيل"),
    "self_off": ("سلف خاموش", "سلف إيقاف", "السلف إيقاف"),
    "language_fa": ("زبان فارسی", "اللغة الفارسية", "اللغة فارسی"),
    "language_ar": ("زبان عربی", "اللغة العربية", "اللغة عربی"),
    "enemy_on": ("دشمن", "دشمن روشن", "عدو", "عدو تشغيل"),
    "enemy_off": ("دشمن خاموش", "عدو إيقاف"),
    "deleted_on": (
        "سیو خودکار پیام حذف شده روشن",
        "سیو خودکار پیام های حذف شده روشن",
        "سیو خودکار پیام‌های حذف‌شده روشن",
        "حفظ تلقائي المحذوفات تشغيل",
        "حفظ تلقائي للمحذوفات تشغيل",
    ),
    "deleted_off": (
        "سیو خودکار پیام حذف شده خاموش",
        "سیو خودکار پیام های حذف شده خاموش",
        "سیو خودکار پیام‌های حذف‌شده خاموش",
        "حفظ تلقائي المحذوفات إيقاف",
        "حفظ تلقائي للمحذوفات إيقاف",
    ),
    "edited_on": (
        "سیو خودکار ویرایش روشن",
        "سیو خودکار پیام ویرایش شده روشن",
        "ذخیره خودکار ویرایش روشن",
        "حفظ تلقائي التعديلات تشغيل",
    ),
    "edited_off": (
        "سیو خودکار ویرایش خاموش",
        "سیو خودکار پیام ویرایش شده خاموش",
        "ذخیره خودکار ویرایش خاموش",
        "حفظ تلقائي التعديلات إيقاف",
    ),
    "timed_on": (
        "سیو خودکار روشن",
        "سیو خودکار تایم دار روشن",
        "حفظ تلقائي تشغيل",
    ),
    "timed_off": (
        "سیو خودکار خاموش",
        "سیو خودکار تایم دار خاموش",
        "حفظ تلقائي إيقاف",
    ),
    "help": PERSIAN_HELP_COMMANDS + ARABIC_HELP_COMMANDS,
    "user_id": ("آیدی", "ایدی", "معرف", "معرّف"),
    "my_id": ("ایدیم", "آیدی من", "ایدی من", "معرفی", "معرفي", "معرّفي"),
    "receive": ("دریافت", "استلام"),
    "story_link": (STORY_COMMAND, ARABIC_STORY_COMMAND),
    "meow_on": ("میو روشن", "ميو تشغيل"),
    "meow_off": ("میو خاموش", "ميو إيقاف"),
    "ping": ("پینگ", "بنغ"),
    "story_reply": ("استوری دانلود", "دانلود استوری", "تحميل قصة", "تنزيل قصة"),
    "animation": ("انیمیشن", "قلب", "الب", "القلب", "الانيميشن", "الأنيميشن"),
}
PERSIAN_COMMAND_ALIASES = frozenset(
    (
        *COMMAND_ALIASES["self_on"][:1],
        *COMMAND_ALIASES["self_off"][:1],
        *COMMAND_ALIASES["language_fa"][:1],
        *COMMAND_ALIASES["language_ar"][:1],
        *COMMAND_ALIASES["enemy_on"][:2],
        *COMMAND_ALIASES["enemy_off"][:1],
        *COMMAND_ALIASES["deleted_on"][:3],
        *COMMAND_ALIASES["deleted_off"][:3],
        *COMMAND_ALIASES["edited_on"][:3],
        *COMMAND_ALIASES["edited_off"][:3],
        *COMMAND_ALIASES["timed_on"][:2],
        *COMMAND_ALIASES["timed_off"][:2],
        *PERSIAN_HELP_COMMANDS,
        "آیدی",
        "ایدی",
        "ایدیم",
        "آیدی من",
        "ایدی من",
        "معرفی",
        "دریافت",
        STORY_COMMAND,
        "استوری دانلود",
        *COMMAND_ALIASES["meow_on"][:1],
        *COMMAND_ALIASES["meow_off"][:1],
        *COMMAND_ALIASES["ping"][:1],
        "دانلود استوری",
        "انیمیشن",
        "قلب",
        *PERSIAN_WEATHER_COMMANDS,
        *PERSIAN_WEATHER_COMPARE_COMMANDS,
        *PERSIAN_WEATHER_HELP_COMMANDS,
    )
)
ARABIC_COMMAND_ALIASES = frozenset(
    (
        *COMMAND_ALIASES["self_on"][1:],
        *COMMAND_ALIASES["self_off"][1:],
        *COMMAND_ALIASES["language_fa"][1:],
        *COMMAND_ALIASES["language_ar"][1:],
        *COMMAND_ALIASES["enemy_on"][2:],
        *COMMAND_ALIASES["enemy_off"][1:],
        *COMMAND_ALIASES["deleted_on"][3:],
        *COMMAND_ALIASES["deleted_off"][3:],
        *COMMAND_ALIASES["edited_on"][3:],
        *COMMAND_ALIASES["edited_off"][3:],
        *COMMAND_ALIASES["timed_on"][2:],
        *COMMAND_ALIASES["timed_off"][2:],
        *ARABIC_HELP_COMMANDS,
        "معرف",
        "معرّف",
        "معرفي",
        "معرّفي",
        "استلام",
        ARABIC_STORY_COMMAND,
        *COMMAND_ALIASES["meow_on"][1:],
        *COMMAND_ALIASES["meow_off"][1:],
        *COMMAND_ALIASES["ping"][1:],
        "تنزيل قصة",
        "تحميل قصة",
        "الب",
        "القلب",
        "الانيميشن",
        "الأنيميشن",
        *ARABIC_WEATHER_COMMANDS,
        *ARABIC_WEATHER_COMPARE_COMMANDS,
        *ARABIC_WEATHER_HELP_COMMANDS,
    )
)


def _matches_command(text, commands):
    return any(
        text == command or text.startswith(command + " ")
        for command in commands
    )


def is_persian_command(text):
    return _matches_command(text, PERSIAN_COMMAND_ALIASES)


def is_arabic_command(text):
    return _matches_command(text, ARABIC_COMMAND_ALIASES)


def is_arabic_weather_command(text):
    return _matches_command(
        text,
        ARABIC_WEATHER_COMMANDS
        + ARABIC_WEATHER_COMPARE_COMMANDS
        + ARABIC_WEATHER_HELP_COMMANDS,
    )


def localized_text(text):
    if get_settings().current_language != "ar":
        return text

    replacements = (
        ("برای دریافت پیام، روی پیام موردنظر ریپلای کن و سپس .دریافت را بنویس.", "لاستلام رسالة، قم بالرد عليها ثم أرسل .استلام."),
        ("لینک معتبر پیام کانال/گروه نیست.", "رابط الرسالة غير صالح."),
        ("این پیام پیدا نشد یا دسترسی به آن وجود ندارد.", "تعذّر العثور على الرسالة أو ليس لديك صلاحية الوصول إليها."),
        ("دریافت مدیا انجام نشد.", "تعذّر استلام الوسائط."),
        ("این پیام متن یا مدیای قابل دریافت ندارد.", "لا تحتوي هذه الرسالة على نص أو وسائط قابلة للاستلام."),
        ("دریافت پیام انجام نشد:", "تعذّر استلام الرسالة:"),
        ("📢 کانال:", "📢 القناة:"),
        ("👤 ارسال‌کننده:", "👤 المرسل:"),
        ("🕐 زمان ارسال:", "🕐 وقت الإرسال:"),
        ("📝 Caption:", "📝 التعليق:"),
        ("برای گرفتن آیدی، روی پیام شخص ریپلای کن و بنویس: .آیدی", "للحصول على المعرّف، قم بالرد على رسالة الشخص واكتب .معرف."),
        ("اطلاعات این کاربر پیدا نشد.", "لم يتم العثور على معلومات هذا المستخدم."),
        ("نامشخص", "غير معروف"),
        ("بدون نام", "بلا اسم"),
        ("سیو خودکار پیام حذف شده روشن", "حفظ تلقائي للرسائل المحذوفة تشغيل"),
        ("سیو خودکار پیام حذف شده خاموش", "حفظ تلقائي للرسائل المحذوفة إيقاف"),
        ("سیو خودکار تایم دار روشن", "حفظ تلقائي للرسائل المؤقتة تشغيل"),
        ("سیو خودکار تایم دار خاموش", "حفظ تلقائي للرسائل المؤقتة إيقاف"),
        ("سلف روشن شد ✅", "تم تشغيل السلف ✅"),
        ("سلف خاموش شد", "تم إيقاف السلف"),
        ("ارسال قلب انجام نشد:", "تعذّر إرسال القلب:"),
        ("قلب ارسال شد، اما پاک‌کردن دستور انجام نشد:", "تم إرسال القلب، لكن تعذّر حذف الأمر:"),
        ("اجرای انیمیشن قلب انجام نشد:", "تعذّر تشغيل أنيميشن القلب:"),
        ("پیام زمان‌دار ذخیره شد ✅", "تم حفظ الرسالة المؤقتة ✅"),
        ("پیام حذف‌شده", "رسالة محذوفة"),
        ("فرستنده:", "المرسل:"),
        ("پیام ویرایش شد", "تم تعديل الرسالة"),
        ("آیدی پیام:", "معرّف الرسالة:"),
        ("زمان ویرایش:", "وقت التعديل:"),
        ("متن قبلی:", "النص السابق:"),
        ("متن جدید:", "النص الجديد:"),
        ("[متن قبلی در دسترس نیست]", "[النص السابق غير متاح]"),
        ("پیش‌نمایش این مدیا در HTML درج نشد؛ فایل جداگانه ذخیره شده است.", "لم يتم تضمين معاينة الوسائط في ملف HTML؛ تم حفظ الملف بشكل منفصل."),
        ("پیش‌نمایش عکس", "معاينة الصورة"),
        ("پیام‌های حذف‌شده", "الرسائل المحذوفة"),
        ("پیام بدون متن", "رسالة بلا نص"),
        ("پیام دارای مدیا", "رسالة تحتوي على وسائط"),
        ("[بدون متن]", "[رسالة بلا نص]"),
        ("[مدیا قابل بازیابی نبود]", "[تعذّر استعادة الوسائط]"),
        ("زمان:", "الوقت:"),
        ("گزارش ", "تقرير "),
        ("حالت دشمن روی کاربر فعال شد ✅", "تم تفعيل وضع العدو لهذا المستخدم ✅"),
        ("حالت دشمن غیرفعال شد ❌", "تم إيقاف وضع العدو ❌"),
        ("برای فعال‌سازی حالت دشمن، روی پیام کاربر ریپلای کن!", "لتفعيل وضع العدو، قم بالرد على رسالة المستخدم."),
        ("در حال دریافت پیام...", "جارٍ استلام الرسالة..."),
        ("پینگ :", "زمن الاستجابة:"),
        ("ذخیره پیام‌های حذف‌شده روشن شد", "تم تشغيل حفظ الرسائل المحذوفة"),
        ("ذخیره پیام‌های حذف‌شده خاموش شد", "تم إيقاف حفظ الرسائل المحذوفة"),
        ("گزارش پیام‌های ویرایش‌شده روشن شد ✅", "تم تشغيل تقارير الرسائل المعدّلة ✅"),
        ("گزارش پیام‌های ویرایش‌شده خاموش شد", "تم إيقاف تقارير الرسائل المعدّلة"),
        ("گزارش پیام‌های ویرایش‌شده از قبل روشن است.", "تقارير الرسائل المعدّلة مفعّلة بالفعل."),
        ("گزارش پیام‌های ویرایش‌شده روشن نیست", "تقارير الرسائل المعدّلة غير مفعّلة"),
        ("ذخیره پیام‌های زمان‌دار از قبل روشن است", "حفظ الرسائل المؤقتة مفعّل بالفعل"),
        ("ذخیره پیام‌های زمان‌دار روشن شد", "تم تشغيل حفظ الرسائل المؤقتة"),
        ("ذخیره پیام‌های زمان‌دار روشن نیست", "حفظ الرسائل المؤقتة غير مفعّل"),
        ("ذخیره پیام‌های زمان‌دار خاموش شد", "تم إيقاف حفظ الرسائل المؤقتة"),
        ("میو خودکار از قبل روشنه", "ميو مفعّل بالفعل"),
        ("میو خودکار روشن", "تم تشغيل ميو"),
        ("میو خودکار خاموش شد", "تم إيقاف ميو"),
        ("میو خودکار روشن نیست", "ميو غير مفعّل"),
        ("در حال بررسی...", "جارٍ الفحص..."),
        ("پینگ", "الاستجابة"),
        ("فرمت درست:", "الصيغة الصحيحة:"),
        ("در حال دانلود استوری...", "جارٍ تحميل القصة..."),
        ("دانلود استوری شروع شد", "بدأ تحميل القصة"),
        ("دانلود پست کانال شروع شد", "بدأ تحميل منشور القناة"),
        ("دانلود استوری انجام نشد", "فشل تحميل القصة"),
        ("دانلود پیام کانال انجام نشد", "فشل تحميل رسالة القناة"),
        ("دانلود این استوری ممکن نیست", "لا يمكن تحميل هذه القصة"),
        ("روی استوری یا پیام استوری ریپلای کن و دوباره بنویس", "قم بالرد على القصة أو رسالة القصة ثم أرسل مرة أخرى"),
        ("اطلاعات این کاربر پیدا نشد", "لم يتم العثور على معلومات هذا المستخدم"),
        ("برای گرفتن آیدی، روی پیام شخص ریپلای کن و بنویس", "للحصول على المعرف، قم بالرد على رسالة الشخص واكتب"),
        ("اطلاعات کاربر", "معلومات المستخدم"),
        ("اطلاعات مالک", "معلومات المالك"),
        ("نام:", "الاسم:"),
        ("یوزرنیم:", "اسم المستخدم:"),
        ("نداره", "لا يوجد"),
        ("آیدی عددی:", "المعرف الرقمي:"),
        ("فرمت درست لینک", "صيغة الرابط الصحيحة"),
        ("استوری دانلود شد", "تم تحميل القصة"),
        ("در حال دانلود...", "جارٍ التحميل..."),
        ("دانلود استوری انجام نشد:", "تعذّر تنزيل القصة:"),
        ("روی استوری یا پیام استوری ریپلای کن و دوباره بنویس:", "قم بالرد على القصة أو رسالتها ثم أرسل مرة أخرى:"),
        ("استوری دانلود", "تنزيل قصة"),
        ("دانلود استوری", "تنزيل قصة"),
        ("در حال دریافت پیام", "جارٍ استلام الرسالة"),
        ("دریافت پیام", "استلام الرسالة"),
        ("لینک معتبر استوری نیست. نمونه:", "رابط القصة غير صالح. مثال:"),
        ("این استوری پیدا نشد یا دیگر در دسترس نیست.", "لم يتم العثور على هذه القصة أو لم تعد متاحة."),
        ("این استوری فایل قابل دانلود ندارد.", "لا تحتوي هذه القصة على ملف قابل للتنزيل."),
        ("دانلود استوری انجام نشد.", "تعذر تنزيل القصة."),
        ("لینک معتبر پیام کانال نیست.", "رابط منشور القناة غير صالح."),
        ("کانال:", "القناة:"),
        ("منتشرکننده:", "الناشر:"),
    )

    for source, target in replacements:
        text = text.replace(source, target)
    return text


async def edit_response(event, text, **kwargs):
    await event.edit(localized_text(text), **kwargs)


async def run_with_floodwait(operation):
    while True:
        try:
            return await operation()
        except FloodWaitError as error:
            await asyncio.sleep(error.seconds)


def progress_text(downloaded, total, frame, title="دانلود"):
    percent = int(downloaded * 100 / total) if total else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)
    return f"{frame} {localized_text(title)}\n[{bar}] {percent}%"
