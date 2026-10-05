# بررسی محیط — ۲۰۲۶-۱۰-۰۵

| ابزار | نتیجه واقعی |
|---|---|
| سیستم | Windows، PowerShell، workspace برابر F:/CoinMarketCap |
| Python | 3.14.6، C:/Python314/python.exe؛ pip 26.1.2 |
| Java | JDK 17.0.20، C:/Program Files/Java/jdk-17.0.20 |
| Android Studio | پوشه C:/Program Files/Android/Android Studio موجود است |
| Flutter / Dart | در PATH و مسیرهای متداول بررسی‌شده پیدا نشدند |
| adb | E:/AndroidSdk/platform-tools/adb.exe اجرا شد؛ دستگاه متصل ندارد |
| Android SDK | E:/AndroidSdk از تنظیمات Android Studio؛ platforms android-34 و android-35؛ AVD: Pixel_7 |
| دسترسی home | enumerate پوشه کاربر با Access denied مواجه شد؛ جست‌وجوی گسترده ادامه داده نشد |
| Git | اجراشدنی موجود؛ workspace مخزن نیست |
| Python packages | FastAPI 0.141.1، Uvicorn 0.52.4، HTTPX 0.28.1، Pydantic 2.13.5، pytest 8.4.2 قابل import |
| شبکه | manifest رسمی Flutter از storage.googleapis.com: HTTP 403، در sandbox و اجرای escalated؛ raw.githubusercontent.com: 200، فونت و مجوز دریافت شد |

SDK رسمی Flutter نصب نشده و PATH/تنظیمات سراسری تغییر نکرده‌اند. صفحه [آرشیو رسمی](https://docs.flutter.dev/install/archive) بررسی شد؛ پیشنهاد شاخه stable است. حداقل SDKهای وابستگی باید با pub resolver روی SDK واقعاً نصب‌شده تأیید شود؛ نسخه Flutter از جدول برنامه انتشار حدس زده نمی‌شود.

وابستگی مستقیم Python به نسخه‌های واقعاً نصب و تست‌شده pin شده‌اند؛ closure وابستگی پروژه (۲۲ بسته) در requirements-lock.txt ثبت شده، محیط مستقل از این فایل هنوز نصب نشده است. نسخه‌های Flutter از pub.dev بررسی شدند اما pubspec.lock، analyzer و build هنوز به علت SDK مفقود تولید/اجرا نشده‌اند.

تلاش مجدد دانلود manifest در مسیر صحیح releases/releases_windows.json: Google و CFUG و SJTU با HTTP 403؛ TUNA با HTTP 404. پاسخ Google محدودیت مکان جغرافیایی را اعلام کرد. [آینه‌های معرفی‌شده در مستندات Flutter](https://docs.flutter.dev/community/china) بررسی شدند؛ هیچ آرشیو SDK دریافت نشد.
