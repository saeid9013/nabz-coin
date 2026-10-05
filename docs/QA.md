# وضعیت کنترل کیفیت

بک‌اند: ۴۰ تست pytest موفق با ۳ warning deprecation محیط؛ HTTP smoke با Uvicorn واقعی، compileall و scheduler دمو اجرا شده‌اند. منابع زنده و کیفیت واقعی ترجمه هنوز آزموده نشده‌اند.

Flutter: تست‌های formatters، persistence، layout، contrast، repository و chart race نوشته شده‌اند ولی به علت SDK مفقود اجرا نشده‌اند. بررسی تعادل delimiter و ARB JSON فقط sanity check است؛ جای analyzer یا compiler نیست. اسکریپت build-mobile.ps1 قبل از اجرای pub/analyze/test در Get-Command flutter شکست خورد؛ شاهد docs/BUILD_STATUS.json با checks خالی.

| جریان / حالت | شواهد فعلی | پذیرش باقی‌مانده |
|---|---|---|
| بازار→جزئیات→واچ‌لیست، خبر→جزئیات | integration test دمو نوشته شده | flutter test integration_test -d DEVICE و restart واقعی |
| آفلاین بازار/خبر/جزئیات/نمودار | تست repository با mock Dio نوشته شده | اجرای تست و قطع شبکه روی دستگاه |
| range دیررس | FutureProvider family و chart_race_test | اجرای تست و انتخاب سریع range روی دستگاه |
| RTL/LTR، قیمت کوچک، تاریخ شمسی | unit/widget tests نوشته شده | اجرای Flutter و TalkBack |
| روشن/تیره و ۳۶۰/۴۱۲dp با متن ۲× | layout tests و contrast tests نوشته شده | اجرای تست و screenshots واقعی، landscape |
| اعتبار و ترجمه روزانه، restart/concurrency | تست‌های واقعی pytest با پاسخ upstream mock | اتصال حداقلی مجاز live پس از تنظیم سرور |
| APK | build script با گزارش و SHA-256 آماده | Flutter SDK، build موفق، نصب واقعی |

Screenshot واقعی پس از اجرای اپ: `python scripts/capture-device.py --adb PATH_TO_ADB --device DEVICE_ID --name market-dark-360-text2`. اسکریپت خروجی باینری دستگاه را اعتبارسنجی و در docs/screenshots ذخیره می‌کند؛ فایل قبلی را overwrite نمی‌کند. هنوز هیچ تصویر دستگاه ایجاد نشده است. QA باید تم و اندازه متن را در خود برنامه تغییر دهد؛ تصویر طراحی یا widget rendering به عنوان screenshot دستگاه معرفی نمی‌شود.

تست رگرسیون جدید news_pagination_test برای refresh هنگام دریافت صفحه بعد نوشته شده، اما اجرا نشده است. گزارش build اکنون timestamp_utc و android_sdk دارد. بررسی encoding/ARB و parser PowerShell موفق و HTTP smoke مجدد موفق بودند.

## وب
نسخه وب اولویت فعلی است؛ ۶ تست Node و check موفق و smoke-web موفق هستند. QA واقعی مرورگر، ابعاد و پوسته آفلاین در docs/WEB.md و تصاویر web-*.jpg ثبت شدند. داده live واقعی همچنان تأیید نشده است.
