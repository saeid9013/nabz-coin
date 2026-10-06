# نبض کوین

بخش [کاوش](docs/DISCOVERY.md) شامل ترس و طمع، دیفای، جفت‌های DEX و اطلاعات پروژه‌هاست؛ برای دریافت واقعی `python scripts/run-live.py` را اجرا کنید و مسیر `#explore` را باز کنید.

اولویت فعلی نسخه وب فارسی است؛ کار APK برای مرحله بعد باقی می‌ماند. نسخه وب در حالت دمو و اتصال واقعی CoinMarketCap اجرا و در مرورگر بررسی شده است. راهنما و شواهد QA در [WEB](docs/WEB.md).

```powershell
cd F:\CoinMarketCap
python scripts/serve-web.py --port 8080
```

باز کردن http://127.0.0.1:8080. برای اتصال API: `python scripts/serve-web.py --port 8080 --api-url http://127.0.0.1:8000` و انتخاب حالت واقعی از تنظیمات (بک‌اند نیز live باشد). تست وب: `cd apps/web; npm run check; npm test`؛ تست HTTP: `python scripts/smoke-web.py`.

اپ اندروید فارسی Flutter و بک‌اند FastAPI برای بازار و اخبار. وضعیت واقعی و موانع در [PROGRESS](docs/PROGRESS.md) است. کد Flutter هنوز به‌دلیل نبود SDK اجرا/تحلیل نشده؛ APK فعلاً موجود نیست. داده دمو واقعی نیست.

## بک‌اند محلی

```powershell
cd F:\CoinMarketCap\services\api
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:APP_MODE = 'demo'
$env:DATABASE_PATH = 'nabz-demo.sqlite3'
.\.venv\Scripts\python -m nabz.scheduler --once
.\.venv\Scripts\python -m uvicorn nabz.main:create_app --factory --host 127.0.0.1 --port 8000
```

Store هنگام راه‌اندازی migration idempotent را اجرا می‌کند. scheduler در ترمینال مستقل با `python -m nabz.scheduler` اجرا می‌شود؛ API هیچ scheduler داخلی ندارد. تست: `python -m pytest -q` در services/api. بسته‌های مستقیم pin و closure وابستگی خود پروژه در requirements-lock.txt ثبت شده‌اند.

حالت live: APP_MODE=live، DATABASE_PATH=nabz-live.sqlite3 و CMC_API_KEY را فقط در environment سرور تنظیم کنید. `.env.example` نمونه است و خودکار خوانده نمی‌شود. بدون کلید startup خطای روشن دارد. API تا اجرای scheduler و دریافت اولین داده 503 می‌دهد. reset یا restart مصرف و cache را حذف نمی‌کند. استفاده از VPS/reverse proxy با TLS، trusted proxy و backup SQLite در [DEPLOYMENT](docs/DEPLOYMENT.md).

## اپ و APK

Android SDK در `E:\AndroidSdk` موجود است؛ Android 34/35 و AVD به نام Pixel_7 شناسایی شدند. Flutter/Dart پیدا نشده‌اند. ابتدا [Flutter stable رسمی](https://docs.flutter.dev/install/archive) و Android SDK سازگار را فراهم کنید و `flutter doctor -v` را اجرا کنید. Python دانلود manifest را در این محیط با HTTP 403 گزارش کرد. SDK سراسری نصب نشده است.

```powershell
cd F:\CoinMarketCap
 .\scripts\build-mobile.ps1 -Flutter PATH_TO_FLUTTER_BAT -AndroidSdk E:\AndroidSdk
# یا اجرای مراحل دستی:
.\scripts\bootstrap-mobile.ps1
cd apps\mobile
flutter pub get
flutter gen-l10n
flutter analyze
flutter test
flutter run --dart-define=DEMO_MODE=true
flutter build apk --debug --dart-define=DEMO_MODE=true
```

bootstrap تنها scaffold اندروید را در staging جدید تولید و کپی می‌کند؛ Dart، pubspec و fixtureهای پروژه حفظ می‌شوند. script هنوز با Flutter اجرا نشده است. `pubspec.lock` تنها پس از حل واقعی وابستگی‌ها ساخته و باید ثبت شود.

خروجی مورد انتظار پس از build موفق: `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`؛ این مسیر فعلاً فایل موجود نیست. debug امضای انتشار نیست.

اتصال live به API: `flutter run --dart-define=DEMO_MODE=false --dart-define=API_BASE_URL=http://10.0.2.2:8000` برای شبیه‌ساز Android. سرور را در توسعه به interface قابل دسترسی emulator bind کنید. برای دستگاه واقعی با USB می‌توان `adb reverse tcp:8000 tcp:8000` و آدرس localhost استفاده کرد. نسخه release فقط HTTPS. فقط API_BASE_URL عمومی در اپ؛ هیچ کلید CMC/ترجمه در dart-define قرار ندهید. اپ live پاسخ demo سرور را رد می‌کند.

واچ‌لیست و تم/اندازه متن/اعداد و ذخیره خبر محلی هستند؛ reset داده اپ آن‌ها را حذف می‌کند. اشتراک از share_plus و native share sheet استفاده می‌کند، اما هنوز روی دستگاه آزموده نشده. metadata لوگو و تاریخچه upstream به‌صورت opt-in پیاده‌سازی و با mock آزموده شده‌اند؛ history نیازمند تأیید صریح دسترسی حساب است. در حالت پیش‌فرض نمودار از snapshotهای scheduler یا کش است. اخبار و ترجمه live و تصاویر دستگاه هنوز تأیید نشده‌اند. provider ترجمه OpenAI با schema و سقف هزینه در [TRANSLATION](docs/TRANSLATION.md) توضیح داده شده است. مجوز خبر و هزینه مستقل میزبانی/ترجمه در docs ثبت‌اند.

نسخه‌های مستقیم Flutter از صفحات رسمی [Riverpod](https://pub.dev/packages/flutter_riverpod)، [go_router](https://pub.dev/packages/go_router)، [Dio](https://pub.dev/packages/dio)، [fl_chart](https://pub.dev/packages/fl_chart)، [shared_preferences](https://pub.dev/packages/shared_preferences)، [shamsi_date](https://pub.dev/packages/shamsi_date)، [url_launcher](https://pub.dev/packages/url_launcher) و [share_plus](https://pub.dev/packages/share_plus) بررسی شده‌اند؛ سازگاری resolver/build هنوز تأیید نشده. share_plus نیازمند Java 17، Kotlin 2.2.0، AGP حداقل 8.12.1 و Gradle حداقل 8.13 است؛ پس از bootstrap نسخه‌های scaffold بررسی شوند.

آخرین اجرای بک‌اند: ۴۳ تست موفق با ۳ warning deprecation. وضعیت واقعی build در docs/BUILD_STATUS.json و معیارهای باز در docs/QA.md ثبت شده‌اند.
