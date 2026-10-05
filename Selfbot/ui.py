"""User-facing help and identity views."""

from telethon.tl.types import User

from . import core


async def show_help(event):
    if core.current_language == "ar":
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
            "└ <code>.حفظ تلقائي المحذوفات إيقاف</code> إيقاف حفظ المحذوفات\n\n"
            "🛠 <b>الأدوات</b>\n"
            "├ <code>.بنغ</code> فحص سرعة الاستجابة\n"
            "├ <code>.معرف</code> معرف المستخدم بالرد\n"
            "└ <code>.معرفي</code> معرف حسابي\n\n"
            "📥 <b>الاستلام</b>\n"
            "├ <code>.تحميل قصة رابط</code> استلام قصة\n"
            "└ <code>.استلام</code> بالرد على رسالة من قناة أو مجموعة\n\n"
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
            "└ <code>.سیو خودکار پیام حذف شده خاموش</code> غیرفعال‌سازی گزارش حذف\n\n"
            "🛠 <b>ابزارها</b>\n"
            "├ <code>.پینگ</code>  بررسی زمان پاسخ\n"
            "├ <code>.آیدی</code>  آیدی فرد با ریپلای\n"
            "└ <code>.ایدیم</code>  اطلاعات آیدی خودم\n\n"
            "📥 <b>دریافت</b>\n"
            "├ <code>.دانلود استوری لینک</code>\n"
            "└ <code>.دریافت</code> دریافت پیام از کانال/گروه با ریپلای\n\n"
            "💗 <b>انیمیشن</b>\n"
            "└ <code>.انیمیشن</code> نمایش قلب رنگی متحرک"
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
    user = await core.client.get_me()

    first_name = getattr(user, "first_name", None) or "بدون نام"
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    username = getattr(user, "username", None)
    username_text = f"@{username}" if username else "نداره"

    if core.current_language == "ar":
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
