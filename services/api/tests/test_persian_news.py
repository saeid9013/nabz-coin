from nabz.news import PersianNewsProvider
import pytest


def test_persian_source_preserves_title_numbers_and_summary():
    result = PersianNewsProvider().translate('خبر BTC با قیمت 100 دلار', 'تغییر 2% گزارش شد.')
    assert result.title_fa == 'خبر BTC با قیمت 100 دلار'
    assert result.summary_fa == 'تغییر 2% گزارش شد.'


def test_persian_source_does_not_publish_english_as_persian():
    with pytest.raises(ValueError):
        PersianNewsProvider().translate('Bitcoin news', 'English only')

def test_persian_news_api_marks_original_and_preserves_attribution(tmp_path):
    from fastapi.testclient import TestClient
    from nabz.config import Settings
    from nabz.store import Store
    from nabz.news import ingest, translate_one
    from nabz.main import create_app
    settings = Settings(mode='live', database=str(tmp_path / 'news.sqlite3'), cmc_key='test-only')
    store = Store(settings)
    provider = PersianNewsProvider()
    ingest(store, [dict(title='خبر بیت‌کوین 100', summary='گزارش فارسی', url='https://mihansignal.com/test-news/', publisher='میهن سیگنال', published_at='2026-10-06T00:00:00+00:00', demo=False)], model=provider.model)
    assert translate_one(store, provider)
    with TestClient(create_app(settings)) as client:
        item = client.get('/api/v1/news').json()['items'][0]
        assert item['original_fa'] is True
        assert item['publisher'] == 'میهن سیگنال'
        assert client.get('/api/v1/news/' + item['id']).json()['original_fa'] is True
