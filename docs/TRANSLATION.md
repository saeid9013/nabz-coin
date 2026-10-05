# ترجمه سمت سرور

Provider پیش‌فرض disabled است. demo-fixture-v1 تنها fixture آموزشی را ترجمه می‌کند؛ provider جدید openai با Responses API پیاده و صرفاً با httpx.MockTransport آزموده شد. درخواست پولی واقعی اجرا نشده است.

مبنای schema و پردازش refusal/incomplete: [OpenAI Docs: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). News در پیام user به‌عنوان JSON داده ارسال می‌شود؛ دستور ثابت developer، tools خالی، store=false و max_output_tokens=2048 هستند. خروجی تنها title_fa و summary_fa است و extra field رد می‌شود.

پیش از فعال‌سازی، مجوز منبع برای بازنشر عنوان/خلاصه و ترجمه با provider لازم است. NEWS_LICENSE_CONFIRMED=true فقط پس از گرفتن آن تنظیم شود. TRANSLATION_PROVIDER=openai، TRANSLATION_API_KEY، TRANSLATION_MODEL و دو نرخ TRANSLATION_INPUT_USD_PER_MILLION / TRANSLATION_OUTPUT_USD_PER_MILLION باید صریحاً از قیمت فعلی مدل انتخابی تنظیم شوند. مدل یا قیمت حدسی پیش‌فرض نداریم. TRANSLATION_DAILY_USD_LIMIT سقف روزانه USD و TRANSLATION_DAILY_LIMIT سقف تعداد است. هیچ کلید در موبایل، README یا گزارش نوشته نمی‌شود.

قفل/صف و هزینه در SQLite پایدارند. پیش از درخواست، هزینه سقف خروجی و برآورد محافظه‌کارانه UTF-8 ورودی به microUSD رزرو می‌شود؛ پس از پاسخ usage هزینه واقعی با قیمت تنظیم‌شده ثبت می‌شود. برای timeout یا crash با مصرف نامعلوم رزرو نگه داشته می‌شود؛ restart سقف را reset نمی‌کند. قیمت‌های تنظیم‌شده باید با صورتحساب سرویس هم‌خوان باشند؛ سقف محلی جای سقف هزینه حساب سرویس نیست.

اعداد و درصد signed، نمادهای uppercase، وجود فارسی و نبود خلاصه اختراعی اعتبارسنجی می‌شوند. این بررسی‌ها جای بازبینی کیفیت معنایی ترجمه واقعی را نمی‌گیرند؛ حفظ قطعیت/نام/محتوا باید با نمونه‌های مجاز live بررسی شود. ورودی اصل هر نسخه در article_versions و hash/مدل/نسخه prompt/attempt در translations نگه داشته می‌شود. source تغییر کند فقط همان نسخه صف جدید می‌سازد؛ خبرهای مختلف یک رویداد حذف نمی‌شوند.

429، timeout و پاسخ ناقص در صف pending با تأخیر و حداکثر سه تلاش می‌مانند؛ credential 401/403 provider را در DB unavailable می‌کند و برای خبرهای بعدی retry بی‌پایان نمی‌سازد. پس از اصلاح اعتبارنامه/دسترسی، مدیر باید disabled:<model> و وضعیت unavailable مربوطه را بررسی و صریح reset کند. سقف هزینه رسیدن، attempt را مصرف نمی‌کند؛ داده قبلی حفظ می‌شود.
