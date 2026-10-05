# معماری

Flutter / Dart + Material 3، Riverpod، go_router، Dio، fl_chart، flutter_localizations/ARB. ساختار feature-based؛ مدل و repository مشترک از نمایش جدا هستند. تنظیمات/واچ‌لیست/اخبار ذخیره‌شده و آخرین پاسخ API با shared_preferences؛ داده مالی حساب کاربر ذخیره نمی‌شود.

FastAPI → repository SQLite → provider. API صرفاً کش را می‌خواند؛ refresh کاربر upstream را صدا نمی‌زند. scheduler فرآیند مستقل و قفل اجاره‌ای SQLite دارد؛ هر job وضعیت، موعد بعدی و خطا را پایدار ثبت می‌کند. API worker بیشتر دریافت پولی بیشتر ایجاد نمی‌کند.

CMC فقط سرور؛ مصرف واقعی credit_count با رزرو قبل از درخواست و شمارنده ماهانه ذخیره می‌شود. داده live و demo در فایل SQLite و namespace موبایل جدا هستند. range نمودار allowlist و داده حداکثر ۲۵۰ نقطه؛ تاریخچه پیش‌فرض غیرفعال تا entitlement تأیید شود. metadata و تاریخچه بودجه مستقل دارند.

اخبار: provider مستقل، URL allowlist، اندازه محدود، redirect غیرفعال، بررسی IP عمومی، پاک‌سازی HTML، dedup نسخه متن و صف ترجمه پایدار. مجوز روشن‌نشده مساوی با فعال‌نشدن منبع است. ترجمه دمو فقط fixture فارسی شناخته‌شده است؛ live بدون provider تأییدشده pending می‌ماند.

ذخیره زمان UTC؛ نمایش تهران و شمسی. API public بدون اسرار/trace؛ rate limit تک‌نمونه‌ای در SQLite. استقرار چند میزبان نیاز به PostgreSQL و rate limiter توزیع‌شده دارد.
