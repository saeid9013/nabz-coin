# کاوش داده‌های کریپتو

مسیر وب #explore چهار بخش دارد. همه اطلاعات از کش بک‌اند /api/v1/discovery/{category} خوانده می‌شوند؛ مرورگر کلید یا URL دلخواه upstream نمی‌فرستد.

| بخش | داده | فاصله دریافت |
|---|---|---|
| sentiment | ۳۰ روز ترس و طمع بیت‌کوین از Alternative.me | ۶ ساعت |
| defi | ۱۰۰ پروتکل بر اساس TVL، بدون دسته CEX؛ ۳۰ زنجیره | ۱ ساعت |
| dex | حداکثر ۶۰ جفت از جست‌وجوی BTC/ETH/SOL؛ یکتا بر اساس chain و pair address، مرتب بر اساس حجم ۲۴ ساعت | ۱۵ دقیقه |
| projects | مشخصات و تیم BTC/ETH/SOL/ADA/XRP از CoinPaprika | هفت روز |

سرویس‌های انتخاب‌شده فعلاً بدون ثبت‌نام یا کلید کار می‌کنند؛ حساب یا اشتراک خریداری نشده است. DISCOVERY_ENABLED=true لازم است؛ run-live.py آن را فعال می‌کند. CoinPaprika از پلن عمومی رایگان برای توسعه غیرتجاری استفاده می‌کند: COINPAPRIKA_ENABLED=false آن را غیرفعال می‌کند و APP_COMMERCIAL_MODE=true نیز دریافت این سرویس را متوقف می‌کند. برای کاربرد درآمدزا باید پلن تجاری و اتصال احراز هویت آن جداگانه فراهم شود. در حالت تجاری، API کش پیشین این سرویس را نیز منتشر نمی‌کند.

قیمت اصلی همچنان CoinMarketCap است. اطلاعات DEX قیمت یک جفت خاص است و به کوین CMC وصل نشده؛ نماد تضمین اصالت یا هویت نیست. نتایج جست‌وجو توصیه خرید نیستند. TVL با market cap متفاوت است و جمع پروتکل‌ها ممکن است دوباره‌شماری داشته باشد. اطلاعات تیم و شرح CoinPaprika به زبان منبع است و وضعیت فعلی اعضای تیم جداگانه تأیید نشده است. عنوان founder برای همه اعضا تولید نمی‌شود.

منبع و دریافت در UI مشخص است. Alternative.me attribution کنار شاخص، CoinPaprika attribution و لینک پروژه، DefiLlama لینک پروتکل و DEX Screener لینک جفت دارد. خطای upstream کش سالم پیشین را حذف نمی‌کند؛ داده قدیمی مشخص می‌شود. قفل و زمان‌بندی در SQLite پایدارند. پاسخ عمومی هیچ دریافت خارجی ایجاد نمی‌کند. هر job ناموفق پنج دقیقه بعد دوباره بررسی می‌شود.

منابع رسمی: https://alternative.me/crypto/fear-and-greed-index/#api ، https://api-docs.defillama.com/llms-free.txt ، https://docs.dexscreener.com/api/reference ، https://coinpaprika.com/api-terms-of-use/
