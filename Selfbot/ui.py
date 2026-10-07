"""User-facing help and identity views."""

from telethon.tl.types import User

from . import core


def help_text(language=None):
    language = language or core.get_settings().current_language
    if language == "ar":
        help_text = (
            "╭──────────────╮\n"
            "│ <b>أوامر السلف</b> │\n"
            "╰──────────────╯\n\n"
            "⚙ <b>السلف</b>\n"
            "├ <code>.سلف تشغيل</code> تشغيل السلف\n"
            "└ <code>.سلف إيقاف</code> إيقاف السلف\n\n"
            "🌐 <b>اللغة</b>\n"
            "├ <code>.اللغة الفارسية</code> الفارسية\n"
            "└ <code>.اللغة العربية</code> العربية\n\n"
            "🐾 <b>ميو</b>\n"
            "├ <code>.ميو تشغيل</code> تشغيل ميو\n"
            "└ <code>.ميو إيقاف</code> إيقاف ميو\n\n"
            "⚔ <b>العدو (الرد التلقائي)</b>\n"
            "├ <code>.عدو</code> بالرد على رسالة المستخدم للتفعيل\n"
            "└ <code>.عدو إيقاف</code> إيقافه\n\n"
            "🗃 <b>حفظ الرسائل المحذوفة</b>\n"
            "├ <code>.حفظ تلقائي تشغيل</code> حفظ الوسائط المؤقتة\n"
            "├ <code>.حفظ تلقائي إيقاف</code> إيقاف حفظ الوسائط المؤقتة\n"
            "├ <code>.حفظ تلقائي المحذوفات تشغيل</code> حفظ المحذوفات\n"
            "├ <code>.حفظ تلقائي المحذوفات إيقاف</code> إيقاف حفظ المحذوفات\n"
            "├ <code>.حفظ تلقائي التعديلات تشغيل</code> تقرير التعديلات في الخاص\n"
            "└ <code>.حفظ تلقائي التعديلات إيقاف</code> إيقاف تقرير التعديلات\n\n"
            "🛠 <b>الأدوات</b>\n"
            "├ <code>.بنغ</code> فحص سرعة الاستجابة\n"
            "├ <code>.معرف</code> معرف المستخدم بالرد\n"
            "└ <code>.معرفي</code> معرف حسابي\n\n"
            "📥 <b>الاستلام</b>\n"
            "├ <code>.تحميل قصة رابط</code> استلام قصة\n"
            "└ <code>.استلام</code> بالرد على رسالة من قناة أو مجموعة\n\n"
            "🌦 <b>الطقس</b>\n"
            "├ <code>.طقس الأهواز</code>\n"
            "├ <code>.مقارنة الأهواز و مشهد</code> مقارنة مدينتين\n"
            "└ <code>.تعليم</code> شرح استخدام الطقس\n\n"
            "💗 <b>الأنيميشن</b>\n"
            "└ <code>.الب</code> عرض قلب متحرك بالألوان"
        )
    else:
        help_text = (
            "╭──────────────╮\n"
            "│ <b>دستورات سلف</b> │\n"
            "╰──────────────╯\n\n"
            "⚙ <b>سلف</b>\n"
            "├ <code>.سلف روشن</code> روشن‌کردن سلف\n"
            "└ <code>.سلف خاموش</code> خاموش‌کردن سلف\n\n"
            "🌐 <b>زبان</b>\n"
            "├ <code>.زبان فارسی</code> فارسی\n"
            "└ <code>.زبان عربی</code> عربی\n\n"
            "🐾 <b>میو</b>\n"
            "├ <code>.میو روشن</code>  روشن‌کردن میو\n"
            "└ <code>.میو خاموش</code> خاموش‌کردن میو\n\n"
            "⚔ <b>دشمن (پاسخ خودکار)</b>\n"
            "├ <code>.دشمن</code> با ریپلای روی کاربر\n"
            "└ <code>.دشمن خاموش</code> غیرفعال‌سازی در چت\n\n"
            "🗃 <b>ذخیره پیام‌های حذف‌شده</b>\n"
            "├ <code>.سیو خودکار روشن</code> ذخیره پیام‌های زمان‌دار\n"
            "├ <code>.سیو خودکار خاموش</code> خاموش‌‌کردن ذخیره پیام‌های زمان‌دار\n"
            "├ <code>.سیو خودکار پیام حذف شده روشن</code> فعال‌سازی گزارش حذف\n"
            "├ <code>.سیو خودکار پیام حذف شده خاموش</code> غیرفعال‌سازی گزارش حذف\n"
            "├ <code>.سیو خودکار ویرایش روشن</code> گزارش ویرایش پیام‌های خصوصی\n"
            "└ <code>.سیو خودکار ویرایش خاموش</code> خاموش‌کردن گزارش ویرایش\n\n"
            "🛠 <b>ابزارها</b>\n"
            "├ <code>.پینگ</code>  بررسی زمان پاسخ\n"
            "├ <code>.آیدی</code>  آیدی فرد با ریپلای\n"
            "└ <code>.ایدیم</code>  اطلاعات آیدی خودم\n\n"
            "📥 <b>دریافت</b>\n"
            "├ <code>.دانلود استوری لینک</code>\n"
            "└ <code>.دریافت</code> دریافت پیام از کانال/گروه با ریپلای\n\n"
            "🌦 <b>هواشناسی</b>\n"
            "├ <code>.هواشناسی اهواز</code>\n"
            "├ <code>.مقایسه اهواز با مشهد</code> مقایسه دو شهر\n"
            "└ <code>.آموزش</code> راهنمای کامل هواشناسی\n\n"
            "💗 <b>انیمیشن</b>\n"
            "└ <code>.قلب</code> نمایش قلب رنگی متحرک"
        )

    return help_text


async def show_help(event):
    await event.edit(help_text(), parse_mode="html")


def weather_comparison_usage(language):
    if language == "ar":
        return (
            "اكتب اسمي المدينتين وافصل بينهما بكلمة «و»، مثال:\n"
            ".مقارنة الأهواز و مشهد"
        )
    return (
        "نام دو شهر را با «و» یا «با» جدا کنید؛ مثال:\n"
        ".مقایسه اهواز با مشهد"
    )


def parse_weather_comparison(arguments, language):
    arguments = arguments.strip()
    if not arguments:
        return None

    for separator in (" با ", " و ", " مع ", " مقابل ", " vs ", " versus "):
        if separator in arguments:
            first, second = arguments.split(separator, 1)
            cities = (first.strip(), second.strip())
            return cities if all(cities) else None

    parts = arguments.split(maxsplit=1)
    if len(parts) != 2:
        return None

    first, second = parts
    if language == "ar" and second.startswith("و") and len(second) > 1:
        second = second[1:].strip()
    return (first, second) if first and second else None


async def show_weather_help(event):
    if core.get_settings().current_language == "ar":
        help_text = (
            "🌦 <b>دليل الطقس</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>الطقس والمقارنة، بخطوات بسيطة</i>\n\n"
            "1️⃣ <b>طقس مدينة واحدة</b>\n"
            "أرسل الأمر متبوعاً باسم المدينة:\n"
            "┌ <code>.طقس الأهواز</code>\n"
            "└ <code>.الطقس London</code>\n"
            "ستظهر الحرارة الحالية وحالة الجو والرطوبة والرياح وغيرها.\n\n"
            "2️⃣ <b>قارن بين مدينتين</b>\n"
            "استخدم «و» أو «مع» للفصل بين الاسمين:\n"
            "┌ <code>.مقارنة الأهواز و مشهد</code>\n"
            "└ <code>.مقارنة الطقس London مع Paris</code>\n"
            "ستظهر حالة المدينتين، ثم فرق الحرارة وأيّهما أحرّ.\n\n"
            "3️⃣ <b>الأوامر والبدائل</b>\n"
            "🌤 الطقس: <code>.طقس</code> · <code>.الطقس</code>\n"
            "⚖️ المقارنة: <code>.مقارنة</code> · <code>.مقارنة الطقس</code>\n"
            "📖 الدليل: <code>.تعليم</code> · <code>.تعليم الطقس</code>\n\n"
            "💡 <b>نصيحة</b>\n"
            "اكتب اسم المدينة بالعربية أو الإنجليزية. للأسماء متعددة الكلمات، "
            "افصل المدينتين بكلمة «و» أو «مع». إذا لم تظهر المدينة، جرّب "
            "كتابتها بالإنجليزية."
        )
    else:
        help_text = (
            "🌦 <b>راهنمای هواشناسی</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>هواشناسی و مقایسهٔ شهرها، ساده و سریع</i>\n\n"
            "1️⃣ <b>آب‌وهوای یک شهر</b>\n"
            "دستور را همراه نام شهر بفرست:\n"
            "┌ <code>.هواشناسی اهواز</code>\n"
            "└ <code>.هوا London</code>\n"
            "دمای فعلی، وضعیت هوا، رطوبت، باد و اطلاعات دیگر نمایش داده می‌شود.\n\n"
            "2️⃣ <b>مقایسهٔ دو شهر</b>\n"
            "نام دو شهر را با «با» یا «و» جدا کن:\n"
            "┌ <code>.مقایسه اهواز با مشهد</code>\n"
            "└ <code>.مقایسه هوا New York و London</code>\n"
            "اطلاعات هر دو شهر و اختلاف دما و شهر گرم‌تر نمایش داده می‌شود.\n\n"
            "3️⃣ <b>دستورها و نام‌های جایگزین</b>\n"
            "🌤 هواشناسی: <code>.هواشناسی</code> · <code>.هوا</code>\n"
            "⚖️ مقایسه: <code>.مقایسه</code> · <code>.مقایسه هوا</code>\n"
            "📖 راهنما: <code>.آموزش</code> · <code>.آموزش هواشناسی</code>\n\n"
            "💡 <b>نکته</b>\n"
            "نام شهر را فارسی یا انگلیسی بنویس. برای نام‌های چندبخشی، بین دو "
            "شهر جداکنندهٔ «با» یا «و» بگذار. اگر شهری پیدا نشد، املای آن را "
            "بررسی کن یا نام انگلیسی‌اش را امتحان کن."
        )
    await event.edit(help_text, parse_mode="html")


async def show_user_id(event):
    reply = await event.get_reply_message()

    if reply is None:
        await core.edit_response(
            event,
            "برای گرفتن آیدی، روی پیام شخص ریپلای کن و بنویس: .آیدی"
        )
        return

    user = await reply.get_sender()

    if user is None:
        await core.edit_response(event, "اطلاعات این کاربر پیدا نشد.")
        return

    first_name = getattr(user, "first_name", None) or "بدون نام"
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    username = getattr(user, "username", None)
    username_text = f"@{username}" if username else "نداره"

    await core.edit_response(
        event,
        "🆔 <b>اطلاعات کاربر</b>\n\n"
        f"👤 نام: {full_name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🔢 آیدی عددی: <code>{user.id}</code>",
        parse_mode="html",
    )


async def show_my_id(event):
    user = await core.get_client().get_me()

    first_name = getattr(user, "first_name", None) or "بدون نام"
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    username = getattr(user, "username", None)
    username_text = f"@{username}" if username else "نداره"

    if core.get_settings().current_language == "ar":
        await event.edit(
            "🆔 <b>معلومات المالك</b>\n\n"
            f"👤 الاسم: {full_name}\n"
            f"🔗 اسم المستخدم: {username_text}\n"
            f"🔢 المعرف الرقمي: <code>{user.id}</code>",
            parse_mode="html",
        )
    else:
        await event.edit(
            "🆔 <b>اطلاعات مالک</b>\n\n"
            f"👤 نام: {full_name}\n"
            f"🔗 یوزرنیم: {username_text}\n"
            f"🔢 آیدی عددی: <code>{user.id}</code>",
            parse_mode="html",
        )
