# بررسی منابع اخبار — ۲۰۲۶-۱۰-۰۵

| منبع | سند رسمی و دسترسی | هزینه و مجوز | تصمیم نسخه فعلی |
|---|---|---|---|
| CoinDesk | [معرفی رسمی RSS](https://www.coindesk.com/coindesk-news/2021/09/17/coindesk-rss) آدرس https://www.coindesk.com/arc/outboundfeeds/rss/ را اعلام می‌کند؛ دریافت feed در برنامه فعال نشده | [Terms](https://www.coindesk.com/terms) استفاده شخصی/غیرتجاری را از بازنشر/تغییر جدا می‌کند؛ مجوز برنامه/ترجمه و قیمت licensing معلوم نیست | تا مجوز کتبی برای عنوان/خلاصه/ترجمه و شرایط attribution، غیرفعال؛ تصویر و متن کامل استفاده نمی‌شوند |
| Cointelegraph | صفحه https://cointelegraph.com/rss-feeds در ابزار مرور قابل دریافت نبود؛ feed حدسی ساخته نشد | [Terms](https://cointelegraph.com/terms-and-privacy) pipeline خودکار/بازنشر و استفاده AI بدون رضایت کتبی را محدود می‌کند؛ هزینه مجوز معلوم نیست | غیرفعال؛ مجوز کتبی و feed رسمی قابل تأیید لازم است |

وجود RSS یا درج منبع به‌تنهایی اجازه بازنشر و ترجمه نیست. [Translation Statement](https://www.coindesk.com/translation-statement) درباره ترجمه خود CoinDesk است و مجوز اپ ثالث محسوب نمی‌شود. این نتیجه محافظه‌کارانه بررسی منابع است، نه ادعای دریافت مجوز.

RssProvider پس از تنظیم allowlist و license_confirmed=True قابل استفاده است؛ timeout، سقف ۱MiB، pin کردن DNS عمومی، TLS اصلی و عدم redirect دارد. تصاویر دریافت نمی‌شوند. feed فقط عنوان و خلاصه موجود را می‌گیرد، scraping مقاله وجود ندارد.

ترجمه دمو فقط یک fixture فارسی مشخص را پشتیبانی می‌کند. provider اختیاری OpenAI Responses همراه صف مدل/نسخه prompt و سقف پولی microUSD اضافه و با mock آزموده شده است؛ اتصال و کیفیت واقعی تأیید نشده‌اند. بدون مجوز منبع، کلید، مدل و قیمت صریح provider فعال نمی‌شود. [تنظیمات ترجمه](TRANSLATION.md). کلید ترجمه در اپ قرار نمی‌گیرد.
