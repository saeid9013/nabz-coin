# بررسی API کریپتو — ۲۰۲۶-۱۰-۰۶

این بررسی انتخاب منبع است؛ provider جدید در محصول فعال نشده است.

| سرویس | داده مناسب | تصمیم |
|---|---|---|
| CoinMarketCap | قیمت، رتبه، حجم، عرضه، metadata و تاریخچه با توجه به حساب | حفظ منبع اصلی فعلی؛ گسترش ۵۰۰ ارز و دریافت تاریخچه پس از تست entitlement و محاسبه credits |
| Alternative.me | ترس و طمع بیت‌کوین و تاریخچه روزانه | اولویت اول تکمیل بازار؛ بدون کلید؛ درج attribution کنار شاخص الزامی |
| CoinPaprika | تیم، شرح، وب‌سایت، whitepaper | منبع مکمل تحریریه؛ team ترکیب سازندگان و توسعه‌دهندگان است؛ همه را founder فرض نکنید. قیمت‌گذاری Free استفاده شخصی/غیرتجاری را ذکر می‌کند؛ برای محصول تجاری نیازمند بررسی پلن |
| CoinGecko | metadata، نمودار، ATH، categories | گزینه جایگزین تاریخچه و metadata؛ کلید Demo، attribution و مجوز پلن بررسی شود |
| DefiLlama | TVL پروتکل و زنجیره، تاریخچه TVL | اولویت بعدی صفحه دیفای؛ منبع اصلی قیمت کل بازار نیست |
| DEX Screener | جفت معاملاتی، نقدینگی و حجم DEX | مرحله بعد؛ اتصال با chain و contract address، نه نماد |
| CryptoPanic | اخبار و sentiment | در این بررسی دسترسی/قیمت از صفحه رسمی قابل تأیید نبود؛ تا آزمون حساب انتخاب نشود |

## آزمون واقعی بدون کلید
- Alternative.me /fng/?limit=7: HTTP 200، هفت نقطه.
- DefiLlama /protocols: HTTP 200، ۸۴۹۴ رکورد؛ شمارش رکورد API به معنی شمارش کوین نیست.
- CoinPaprika /v1/coins/btc-bitcoin: HTTP 200، ساختار metadata دریافت شد.
- CoinGecko /api/v3/ping: HTTP 200؛ فقط اتصال، نه تضمین همه endpointها.
- DEX Screener search?q=SOL: HTTP 200، ۳۰ pair؛ این‌ها ۳۰ ارز مستقل نیستند.

## طرح اتصال
- scheduler سمت سرور، کش SQLite، زمان مشاهده و زمان دریافت و منبع مستقل برای هر داده.
- نگاشت بررسی‌شده cmc_id/coingecko_id/coinpaprika_id و chain/contract؛ تطبیق symbol به‌تنهایی ممنوع.
- قیمت منابع مختلف بدون اعلام منبع مخلوط نشود. TVL با market cap متفاوت است.
- تاریخچه به‌صورت دریافت گروهی/دوره‌ای و بودجه‌دار؛ کاربر هر صفحه درخواست upstream جدید نسازد.
- اطلاعات تیم و شرح انگلیسی وارد پیش‌نویس تحریریه شود؛ ترجمه و صحت پیش از انتشار بررسی گردد.

## منابع رسمی
https://coinmarketcap.com/api/pricing/
https://www.coingecko.com/en/api/pricing
https://docs.coingecko.com/reference/coins-id
https://coinpaprika.com/api/pricing/
https://coinpaprika.com/api-terms-of-use/
https://docs.coinpaprika.com/api-reference/coins/get-coin-by-id
https://alternative.me/crypto/fear-and-greed-index/#api
https://api-docs.defillama.com/
https://docs.dexscreener.com/api/reference
https://cryptopanic.com/developers/api/
