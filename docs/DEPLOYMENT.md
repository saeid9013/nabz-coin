# استقرار و تحویل محلی

خرید، انتشار عمومی یا ارسال به فروشگاه انجام نشده است. نصب پیشنهادی تک‌نمونه‌ای: API و یک scheduler مستقل با environment مشترک و DB مشترک؛ SQLite روی دیسک محلی پایدار، backup و permission فقط برای حساب سرویس. چند API worker scheduler را داخل فرآیند شروع نمی‌کنند. برای چند میزبان repository به PostgreSQL و rate-limit توزیع‌شده منتقل شود.

پشت reverse proxy دارای TLS اجرا شود؛ uvicorn با forwarded headers تنها از proxy شناخته‌شده اعتماد کند. rate limit فعلی ۶۰ درخواست در دقیقه بر اساس IP مستقیم است و quota چند کاربر پشت یک NAT مشترک می‌شود. اسرار در environment یا secret manager، بدون print/log. فایل .env در Git ممنوع. افزایش EXTERNAL_CREDITS برای مصرف بیرون سرویس لازم است.

news providerهای واقعی پیش‌فرض غیرفعال‌اند؛ scheduler فقط با NEWS_FEED_URLS، NEWS_ALLOWED_DOMAINS و NEWS_LICENSE_CONFIRMED=true دریافت RSS را فعال می‌کند. ترجمه اختیاری طبق TRANSLATION.md فعال می‌شود؛ تا آن زمان خبر live pending است. History/metadata نیز opt-in طبق DATA_SOURCES هستند و با mock آزموده شدند، نه حساب واقعی. ابزار build هنوز مسدود است؛ docs/BUILD_STATUS.json نتیجه واقعی آخرین تلاش و checks انجام‌شده را ثبت می‌کند.

## signing
پس از تولید scaffold و موفقیت تست/build، keystore انتشار واقعی خود را طبق [راهنمای رسمی Android Flutter](https://docs.flutter.dev/deployment/android) بسازید و خارج از مخزن نگه دارید. android/key.properties و keystore از Git خارج‌اند. signingConfig release را به کلید واقعی متصل کنید؛ تنظیم پیش‌فرض debug در template تولیدشده برای انتشار کافی نیست.

پس از تنظیم signing، `flutter build appbundle --release --dart-define=DEMO_MODE=false --dart-define=API_BASE_URL=https://your-backend.example`؛ placeholder آدرس را با سرور واقعی جایگزین کنید. secrets فقط server-side. debug APK هدف آزمایش محلی است؛ خروجی build فعلی موجود نیست.

## QA روی دستگاه
دستگاه/شبیه‌ساز واقعی، ۳۶۰/۴۱۲dp، scale ۱ و ۲، هر دو تم، landscape، TalkBack، reduced motion، restart و قطع شبکه را بررسی کنید. screenshot واقعی با `adb exec-out screencap -p` به فایل PNG باینری (بدون تبدیل متنی PowerShell) ذخیره شود. widget test جای QA واقعی دستگاه نیست. هیچ screenshot ساختگی تحویل نمی‌شود.
