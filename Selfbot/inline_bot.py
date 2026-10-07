"""Telegram inline bot for showing a localized, self-closing panel."""

import asyncio
import html
import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    ContextTypes,
    InlineQueryHandler,
)

from . import core


logger = logging.getLogger(__name__)
PANEL_CLOSE_DELAY_SECONDS = 5
CLOSE_CALLBACK_DATA = "close_inline_panel"
PAGE_CALLBACK_PREFIX = "panel_page"
PANEL_SETTINGS_QUERY_PREFIX = "__selfbot_settings__:"
PANEL_SETTING_NAMES = (
    "timed_save_enabled",
    "deleted_save_enabled",
    "edited_save_enabled",
)
_close_tasks = {}


def _query_user_settings(query_text):
    parts = query_text.split()
    if len(parts) < 2 or not parts[1].startswith(PANEL_SETTINGS_QUERY_PREFIX):
        return None

    encoded = parts[1][len(PANEL_SETTINGS_QUERY_PREFIX):]
    if len(encoded) != len(PANEL_SETTING_NAMES) or any(
        bit not in "01" for bit in encoded
    ):
        return None
    return dict(zip(PANEL_SETTING_NAMES, (bit == "1" for bit in encoded)))

PANEL_PAGES = {
    "fa": {
        "self": (
            "سلف",
            "<b>سلف و راهنما</b>\nروشن یا خاموش‌کردن سلف و بازکردن این راهنما.",
        ),
        "language": (
            "زبان",
            "<b>زبان</b>\nزبان فرمان‌های سلف را تغییر می‌دهد.",
        ),
        "meow": (
            "میو",
            "<b>میو</b>\nارسال خودکار «میو» در همین گفتگو.",
        ),
        "enemy": (
            "دشمن",
            "<b>دشمن (پاسخ خودکار)</b>\nبا ریپلای روی پیام کاربر فعال می‌شود.",
        ),
        "guardian": (
            "نگهبان چت",
            "<b>نگهبان چت</b>\nبرای تغییر وضعیت قابلیت‌ها فقط دکمه‌های زیر را بزن.",
        ),
        "tools": (
            "ابزارها",
            "<b>ابزارها</b>\nبررسی پاسخ، شناسه‌ها و ابزار تبدیل عکس به GIF.",
        ),
        "receive": (
            "مدیا",
            "<b>مدیا</b>\nپیام کانال/گروه را با ریپلای یا استوری را با لینک دریافت کن.",
        ),
        "weather": (
            "هواشناسی",
            "<b>هواشناسی</b>\nوضعیت یک شهر، مقایسهٔ دو شهر یا راهنمای هواشناسی.",
        ),
        "animation": (
            "انیمیشن",
            "<b>انیمیشن</b>\nنمایش قلب رنگی متحرک.",
        ),
    },
    "ar": {
        "self": (
            "السلف",
            "<b>السلف والمساعدة</b>\nتشغيل السلف أو إيقافه وفتح هذه المساعدة.",
        ),
        "language": (
            "اللغة",
            "<b>اللغة</b>\nتغيير لغة أوامر السلف.",
        ),
        "meow": (
            "ميو",
            "<b>ميو</b>\nإرسال ميو تلقائيًا في هذه المحادثة.",
        ),
        "enemy": (
            "العدو",
            "<b>العدو (الرد التلقائي)</b>\nيُفعّل بالرد على رسالة المستخدم.",
        ),
        "guardian": (
            "حارس الدردشة",
            "<b>حارس الدردشة</b>\nاستخدم الأزرار أدناه لتغيير حالة الميزات.",
        ),
        "tools": (
            "الأدوات",
            "<b>الأدوات</b>\nفحص الاستجابة والمعرّفات وتحويل الصور إلى GIF.",
        ),
        "receive": (
            "الوسائط",
            "<b>الوسائط</b>\nاستلام رسالة قناة/مجموعة بالرد أو قصة عبر رابطها.",
        ),
        "weather": (
            "الطقس",
            "<b>الطقس</b>\nحالة مدينة أو مقارنة مدينتين أو دليل الطقس.",
        ),
        "animation": (
            "الأنيميشن",
            "<b>الأنيميشن</b>\nعرض قلب متحرك بالألوان.",
        ),
    },
}

PANEL_COMMANDS = {
    "fa": {
        "self": (
            (".سلف روشن", "روشن‌کردن سلف"),
            (".سلف خاموش", "خاموش‌کردن سلف"),
        ),
        "language": (
            (".زبان فارسی", "انتخاب زبان فارسی"),
            (".زبان عربی", "انتخاب زبان عربی"),
        ),
        "meow": (
            (".میو روشن", "روشن‌کردن میو خودکار در گفتگو"),
            (".میو خاموش", "خاموش‌کردن میو خودکار"),
        ),
        "enemy": (
            (".دشمن", "با ریپلای روی پیام کاربر، پاسخ خودکار را فعال کن"),
            (".دشمن خاموش", "خاموش‌کردن پاسخ خودکار در گفتگو"),
        ),
        "tools": (
            (".پینگ", "بررسی زمان پاسخ"),
            (".آیدی", "با ریپلای روی پیام کاربر"),
            (".ایدیم", "نمایش شناسهٔ حساب خودت"),
            (".گیف", "با ریپلای روی عکس؛ تبدیل به GIF"),
        ),
        "receive": (
            (".دریافت", "با ریپلای یا افزودن لینک پیام کانال/گروه"),
            (".دانلود استوری <لینک>", "دانلود استوری با لینک"),
        ),
        "weather": (
            (".هواشناسی <شهر>", "وضعیت آب‌وهوا"),
            (".مقایسه <شهر۱> با <شهر۲>", "مقایسهٔ آب‌وهوای دو شهر"),
            (".آموزش هواشناسی", "راهنمای دستورهای هواشناسی"),
        ),
        "animation": ((".قلب", "نمایش قلب رنگی متحرک"),),
    },
    "ar": {
        "self": (
            (".سلف تشغيل", "تشغيل السلف"),
            (".سلف إيقاف", "إيقاف السلف"),
        ),
        "language": (
            (".اللغة الفارسية", "اختيار اللغة الفارسية"),
            (".اللغة العربية", "اختيار اللغة العربية"),
        ),
        "meow": (
            (".ميو تشغيل", "تشغيل ميو تلقائيًا في المحادثة"),
            (".ميو إيقاف", "إيقاف ميو تلقائيًا"),
        ),
        "enemy": (
            (".عدو", "فعّل الرد التلقائي بالرد على رسالة المستخدم"),
            (".عدو إيقاف", "إيقاف الرد التلقائي في المحادثة"),
        ),
        "tools": (
            (".بنغ", "فحص زمن الاستجابة"),
            (".معرف", "بالرد على رسالة المستخدم"),
            (".معرفي", "عرض معرّف حسابك"),
            (".تحويل جيف", "بالرد على صورة؛ تحويلها إلى GIF"),
        ),
        "receive": (
            (".استلام", "بالرد أو بإضافة رابط رسالة القناة/المجموعة"),
            (".تحميل قصة <الرابط>", "تنزيل قصة باستخدام الرابط"),
        ),
        "weather": (
            (".طقس <مدينة>", "حالة الطقس"),
            (".مقارنة <مدينة١> و <مدينة٢>", "مقارنة الطقس في مدينتين"),
            (".تعليم الطقس", "دليل أوامر الطقس"),
        ),
        "animation": ((".الب", "عرض قلب متحرك بالألوان"),),
    },
}


def _closed_text(language):
    return "تم إغلاق اللوحة." if language == "ar" else "پنل بسته شد."


def _home_text(language):
    return (
        "<b>لوحة أوامر السلف</b>\nاختر القسم لعرض أوامره."
        if language == "ar"
        else "<b>پنل دستورهای سلف</b>\nبرای دیدن دستورها، یک بخش را انتخاب کن."
    )


def _page_markup(language, page="home", owner_settings=None):
    pages = PANEL_PAGES[language]
    rows = []
    if page == "home":
        page_items = list(pages.items())
        buttons = []
        for index, (key, (title, _content)) in enumerate(page_items):
            if key == "guardian" or index >= len(page_items) - 4:
                style = "primary"
            elif index < 4:
                style = "success"
            else:
                style = "danger"
            buttons.append(
                InlineKeyboardButton(
                    title,
                    callback_data=f"{PAGE_CALLBACK_PREFIX}:{language}:{key}",
                    style=style,
                )
            )
        rows = [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    else:
        if page == "guardian":
            owner_settings = owner_settings or {
                name: getattr(core.get_settings(), name)
                for name in PANEL_SETTING_NAMES
            }
            labels = (
                (
                    "timed_save_enabled",
                    "ذخیرهٔ پیام زمان‌دار" if language == "fa" else "حفظ الرسائل المؤقتة",
                ),
                (
                    "deleted_save_enabled",
                    "ذخیرهٔ پیام حذف‌شده" if language == "fa" else "حفظ الرسائل المحذوفة",
                ),
                (
                    "edited_save_enabled",
                    "گزارش ویرایش پیوی" if language == "fa" else "تقارير تعديلات الخاص",
                ),
            )
            for setting_name, label in labels:
                enabled = owner_settings[setting_name]
                rows.append(
                    [
                        InlineKeyboardButton(
                            f"{'✓' if enabled else '✗'} {label}",
                            callback_data=f"panel_toggle:{language}:{setting_name}",
                            style="success" if enabled else "danger",
                        )
                    ]
                )
        rows.append(
            [
                InlineKeyboardButton(
                    "القائمة" if language == "ar" else "بازگشت به دستورات",
                    callback_data=f"{PAGE_CALLBACK_PREFIX}:{language}:home",
                    style="danger",
                )
            ]
        )
    if page == "home":
        rows.append(
            [
                InlineKeyboardButton(
                    "إغلاق اللوحة" if language == "ar" else "بستن پنل",
                    callback_data=CLOSE_CALLBACK_DATA,
                    style="danger",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def _page_text(language, page):
    if page == "home":
        return _home_text(language)
    description = PANEL_PAGES[language][page][1]
    commands = PANEL_COMMANDS.get(language, {}).get(page, ())
    if not commands:
        return description
    command_list = "\n".join(
        f"<code>{html.escape(command)}</code> — {html.escape(description)}"
        for command, description in commands
    )
    return f"{description}\n\n{command_list}"


def _query_language(query_text, default_language):
    parts = query_text.strip().lstrip(".").split(maxsplit=1)
    command = parts[0] if parts else ""
    if command in core.PERSIAN_HELP_COMMANDS:
        return "fa"
    if command in core.ARABIC_HELP_COMMANDS:
        return "ar"
    if default_language == "ar" and core.is_persian_command(command):
        return None
    if default_language == "fa" and core.is_arabic_command(command):
        return None
    return default_language


def _panel_settings_for(context, user_id):
    settings_by_user = context.application.bot_data["panel_settings"]
    return settings_by_user.setdefault(
        user_id,
        {
            name: getattr(core.get_settings(), name)
            for name in PANEL_SETTING_NAMES
        },
    )


def _is_panel_owner(query, context):
    return query.from_user.id == context.application.bot_data.get("owner_id")


async def inline_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.inline_query
    if query.from_user.id != context.application.bot_data.get("owner_id"):
        await query.answer([], cache_time=0, is_personal=True)
        return

    language = _query_language(
        query.query,
        core.get_settings().current_language,
    )
    if language is None:
        await query.answer([], cache_time=0, is_personal=True)
        return

    user_id = update.effective_user.id
    settings_by_user = context.application.bot_data["panel_settings"]
    query_settings = _query_user_settings(query.query)
    if query_settings is not None:
        settings_by_user[user_id] = query_settings
    user_settings = _panel_settings_for(context, user_id)
    panel = InlineQueryResultArticle(
        id=f"localized-panel:{language}",
        title="مساعدة" if language == "ar" else "راهنما",
        description=(
            "لوحة أوامر تفاعلية"
            if language == "ar"
            else "پنل تعاملی دستورهای ربات"
        ),
        input_message_content=InputTextMessageContent(
            message_text=_home_text(language),
            parse_mode="HTML",
        ),
        reply_markup=_page_markup(
            language,
            owner_settings=user_settings,
        ),
    )
    await query.answer([panel], cache_time=0, is_personal=True)


async def _close_inline_panel_after_delay(bot, inline_message_id, language):
    await asyncio.sleep(PANEL_CLOSE_DELAY_SECONDS)
    await bot.edit_message_text(
        inline_message_id=inline_message_id,
        text=_closed_text(language),
        reply_markup=None,
    )


def _close_task_done(inline_message_id, task):
    if _close_tasks.get(inline_message_id) is task:
        _close_tasks.pop(inline_message_id, None)
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error(
            "Could not auto-close inline panel: %s",
            type(error).__name__,
            exc_info=(type(error), error, error.__traceback__),
        )


def _schedule_panel_close(application, bot, inline_message_id, language):
    _cancel_panel_close(inline_message_id)

    task = application.create_task(
        _close_inline_panel_after_delay(
            bot, inline_message_id, language
        ),
        name="close-inline-panel",
    )
    _close_tasks[inline_message_id] = task
    task.add_done_callback(
        lambda completed: _close_task_done(
            inline_message_id, completed
        )
    )


def _cancel_panel_close(inline_message_id):
    old_task = _close_tasks.pop(inline_message_id, None)
    if old_task is not None:
        old_task.cancel()


async def chosen_inline_result_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chosen = update.chosen_inline_result
    if not chosen.inline_message_id:
        logger.warning(
            "Inline feedback did not include an inline message ID; "
            "enable inline feedback with BotFather to auto-close panels."
        )
        return

    language = "ar" if chosen.result_id.endswith(":ar") else "fa"
    _schedule_panel_close(
        context.application,
        context.bot,
        chosen.inline_message_id,
        language,
    )


async def panel_page_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not _is_panel_owner(query, context):
        await query.answer()
        return
    await query.answer()
    _prefix, language, page = query.data.split(":", 2)
    if language not in PANEL_PAGES or (
        page != "home" and page not in PANEL_PAGES[language]
    ):
        await query.edit_message_text(
            text=_closed_text(core.get_settings().current_language),
            reply_markup=None,
        )
        return

    await query.edit_message_text(
        text=_page_text(language, page),
        parse_mode="HTML",
        reply_markup=_page_markup(
            language,
            page,
            _panel_settings_for(context, query.from_user.id),
        ),
    )
    if query.inline_message_id and page != "home":
        _cancel_panel_close(query.inline_message_id)


async def panel_toggle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not _is_panel_owner(query, context):
        await query.answer()
        return

    _prefix, language, setting_name = query.data.split(":", 2)
    if language not in PANEL_PAGES or setting_name not in {
        "timed_save_enabled",
        "deleted_save_enabled",
        "edited_save_enabled",
    }:
        await query.answer()
        return

    user_id = query.from_user.id
    user_settings = _panel_settings_for(context, user_id)
    enabled = not user_settings[setting_name]
    try:
        setattr(core.get_settings(), setting_name, enabled)
        core.save_settings()
    except OSError as error:
        logger.warning(
            "Could not persist inline panel setting for user_id=%s: %s",
            user_id,
            type(error).__name__,
            exc_info=True,
        )
        await query.answer(
            "ذخیره تنظیم انجام نشد؛ گزارش برنامه را بررسی کن."
            if language == "fa"
            else "تعذّر حفظ الإعداد؛ راجع سجل البرنامج.",
            show_alert=True,
        )
        return

    user_settings[setting_name] = enabled
    try:
        await query.edit_message_reply_markup(
            reply_markup=_page_markup(
                language,
                "guardian",
                user_settings,
            )
        )
    except TelegramError as error:
        logger.warning(
            "Could not refresh inline panel for user_id=%s: %s",
            user_id,
            str(error).replace("\n", " ")[:100],
        )
        await query.answer(
            (
                "تنظیم ذخیره شد، اما نمایش پنل به‌روزرسانی نشد: "
                f"{str(error).replace(chr(10), ' ')[:100]}"
            )
            if language == "fa"
            else (
                "تم حفظ الإعداد لكن تعذّر تحديث اللوحة: "
                f"{str(error).replace(chr(10), ' ')[:100]}"
            ),
            show_alert=True,
        )
        return

    await query.answer()


async def close_inline_panel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not _is_panel_owner(query, context):
        await query.answer()
        return
    await query.answer()

    inline_message_id = query.inline_message_id
    if inline_message_id:
        _cancel_panel_close(inline_message_id)

    await query.edit_message_text(
        text=_closed_text(core.get_settings().current_language),
        reply_markup=None,
    )


def build_inline_application(token):
    application = Application.builder().token(token).build()
    application.bot_data["panel_settings"] = {}
    application.add_handler(InlineQueryHandler(inline_query_handler))
    application.add_handler(
        ChosenInlineResultHandler(chosen_inline_result_handler)
    )
    application.add_handler(
        CallbackQueryHandler(
            panel_toggle_callback,
            pattern=r"^panel_toggle:",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            panel_page_callback,
            pattern=f"^{PAGE_CALLBACK_PREFIX}:",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            close_inline_panel_callback,
            pattern=f"^{CLOSE_CALLBACK_DATA}$",
        )
    )
    return application
