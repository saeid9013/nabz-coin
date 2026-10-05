from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from nabz.config import Settings
from nabz.main import create_app
from nabz.news import (DemoNewsProvider, DemoTranslationProvider, ingest, translate_one,
                       safe_url, clean, match_coins, RssProvider)
from nabz.providers import CmcProvider, DemoProvider, CapabilityUnavailable
from nabz.scheduler import tick
from nabz.store import Store, BudgetExceeded


@pytest.fixture
def settings(tmp_path):
    return Settings(database=str(tmp_path / 'test.sqlite3'))


def test_contract_demo_and_validation(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').json()['mode'] == 'demo'
        market = client.get('/api/v1/market').json()
        assert len(market['items']) == 100
        assert market['freshness'] == 'demo'
        assert client.get('/api/v1/market?q=BTC').json()['items'][0]['id'] == 1
        assert client.get('/api/v1/market?sort=losers').json()['items'][0]['change_24h'] < 0
        assert client.get('/api/v1/market?limit=1000').status_code == 422
        assert client.get('/api/v1/coins/999999').status_code == 404
        assert client.get('/api/v1/coins/1/chart?range=all').status_code == 422
        chart = client.get('/api/v1/coins/1/chart?range=7d').json()
        assert len(chart['points']) == 48
        assert chart['points'][0]['time'] < chart['points'][-1]['time']
        assert client.get('/api/v1/market/overview').json()['indices']['fear']['status'] == 'unavailable'
        assert client.get('/api/v1/news').json()['items'] == []


def test_live_configuration_and_database_separation(settings):
    with pytest.raises(ValueError, match='CMC_API_KEY'):
        create_app(replace(settings, mode='live'))
    Store(settings)
    with pytest.raises(ValueError, match='separate'):
        Store(replace(settings, mode='live', cmc_key='mock-key'))


def test_live_never_generates_fixtures_or_paid_refresh(settings):
    live = replace(settings, mode='live', cmc_key='mock-key')
    app = create_app(live)
    with TestClient(app) as client:
        assert client.get('/api/v1/market').status_code == 503
        items = DemoProvider().fetch('market')[:1]  # Test input representing a cached provider response.
        app.state.store.put('market', items, '2020-01-01T00:00:00+00:00')
        for _ in range(5):
            assert client.get('/api/v1/market').json()['freshness'] == 'stale'
        assert client.get('/api/v1/coins/1/chart').json()['points'] == []
        with app.state.store.connection() as db:
            assert db.execute('SELECT COUNT(*) FROM usage_records').fetchone()[0] == 0


def test_budget_survives_restart_and_concurrency(settings):
    settings = replace(settings, monthly_limit=4, external_credits=1)
    store = Store(settings)
    def reserve(_):
        try:
            return store.reserve('market')
        except BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(reserve, range(8)))
    assert len([t for t in tokens if t]) == 3
    restarted = Store(settings)
    with pytest.raises(BudgetExceeded):
        restarted.reserve('market')
    restarted.settle(next(t for t in tokens if t), 0)
    assert restarted.reserve('market')


def test_optional_budget(settings):
    store = Store(replace(settings, history_limit=1, metadata_limit=0))
    store.reserve('history')
    with pytest.raises(BudgetExceeded):
        store.reserve('history')
    with pytest.raises(BudgetExceeded):
        store.reserve('metadata')


def test_scheduler_shared_lease_and_restart(settings):
    store = Store(settings)
    class Provider:
        calls = 0
        def fetch(self, name):
            self.calls += 1
            return []
    provider = Provider()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: tick(settings, store, provider), range(4)))
    assert provider.calls == 2
    tick(settings, Store(settings), provider)
    assert provider.calls == 2
    assert store.get('market') is not None


def test_stale_lease_owner_cannot_release_new_lease(settings):
    store = Store(settings)
    old = store.acquire_job('market', 600, ttl=-1)
    new = store.acquire_job('market', 600)
    store.finish_job('market', old, 600)
    assert store.acquire_job('market', 600) is None
    store.finish_job('market', new, 600)


def test_cmc_retry_credit_count_and_403(settings):
    store = Store(settings)
    responses = [429, 200]
    def handler(request):
        code = responses.pop(0)
        return httpx.Response(code, json={'status': {'credit_count': 2, 'error_code': 0}, 'data': []})
    provider = CmcProvider(settings, store, httpx.MockTransport(handler), sleep=lambda _: None)
    assert provider.fetch('market') == []
    with store.connection() as db:
        assert db.execute('SELECT SUM(actual) FROM usage_records').fetchone()[0] == 4
    calls = []
    def denied(request):
        calls.append(request)
        return httpx.Response(403, json={'status': {'credit_count': 0}})
    provider = CmcProvider(settings, store, httpx.MockTransport(denied), sleep=lambda _: None)
    with pytest.raises(CapabilityUnavailable):
        provider.fetch('market')
    assert len(calls) == 1


def test_403_persistently_disables_job(settings):
    store = Store(settings)
    class Denied:
        calls = 0
        def fetch(self, category):
            self.calls += 1
            raise CapabilityUnavailable()
    provider = Denied()
    tick(settings, store, provider)
    with store.connection() as db:
        db.execute('UPDATE job_status SET next_due=0')
    tick(settings, Store(settings), provider)
    assert provider.calls == 2


def test_translation_dedup_change_and_retry(settings):
    store = Store(settings)
    store.put('market', DemoProvider().fetch('market'))
    fixture = DemoNewsProvider().fetch()
    assert ingest(store, fixture) == 1
    assert ingest(store, fixture) == 0
    assert translate_one(store, DemoTranslationProvider()) is True
    assert translate_one(store, DemoTranslationProvider()) is False
    with store.connection() as db:
        row = db.execute('SELECT * FROM translations').fetchone()
        assert row['status'] == 'ready'
        assert '62450.25' in row['summary_fa']
        assert json.loads(db.execute('SELECT coin_ids FROM articles').fetchone()[0]) == [1]
    fixture[0]['summary'] += ' Changed'
    assert ingest(store, fixture) == 1
    translate_one(store, DemoTranslationProvider())
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM translations WHERE status='pending'").fetchone()[0] == 1


def test_translation_single_flight(settings):
    store = Store(settings)
    ingest(store, DemoNewsProvider().fetch())
    class Counting(DemoTranslationProvider):
        calls = 0
        def translate(self, title, summary):
            self.calls += 1
            return super().translate(title, summary)
    provider = Counting()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: translate_one(store, provider), range(4)))
    assert provider.calls == 1


def test_news_api_status_and_source(settings):
    app = create_app(settings)
    ingest(app.state.store, DemoNewsProvider().fetch())
    with TestClient(app) as client:
        item = client.get('/api/v1/news').json()['items'][0]
        assert item['title_fa'] is None
        assert item['translation_status'] == 'pending'
        translate_one(app.state.store, DemoTranslationProvider())
        item = client.get('/api/v1/news').json()['items'][0]
        assert item['demo'] is True and item['translation_status'] == 'ready'
        assert client.get('/api/v1/news/'+item['id']).status_code == 200


@pytest.mark.parametrize('url', ['http://example.com/', 'https://127.0.0.1/', 'https://example.com@localhost/',
    'https://example.com:8080/', 'file:///etc/passwd', 'https://other.example/'])
def test_news_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        safe_url(url, {'example.com'})


def test_news_clean_matching_and_license():
    assert clean('<script>steal secret</script><b>Bitcoin</b> 10%') == 'Bitcoin 10%'
    assert match_coins('ONE grew', [{'id': 1, 'name': 'Bitcoin', 'symbol': 'ONE'}]) == []
    with pytest.raises(ValueError, match='license'):
        RssProvider(['https://example.com/rss'], {'example.com'})


def test_public_rate_limit(settings):
    with TestClient(create_app(settings)) as client:
        for _ in range(60):
            assert client.get('/health').status_code == 200
        assert client.get('/health').status_code == 429


def test_self_collected_charts_are_ordered_capped_and_persistent(settings):
    from datetime import datetime, timezone, timedelta
    store = Store(settings)
    now = datetime.now(timezone.utc)
    for i in range(300):
        store.snapshot_prices([{'id': 1, 'price': 100 + i}], (now - timedelta(minutes=300-i)).isoformat())
    points = Store(settings).price_history(1, 1)
    assert len(points) == 250
    assert points[0]['price'] == 100 and points[-1]['price'] == 399
    assert all(a['time'] < b['time'] for a, b in zip(points, points[1:]))


def test_news_scheduler_restart_does_not_retranslate(settings):
    from nabz.scheduler import tick_news
    store = Store(settings)
    tick_news(settings, store, DemoNewsProvider(), DemoTranslationProvider())
    tick_news(settings, Store(settings), DemoNewsProvider(), DemoTranslationProvider())
    with store.connection() as db:
        assert db.execute('SELECT SUM(count) FROM translation_usage').fetchone()[0] == 1


def test_rss_dns_private_redirect_size_and_xml(monkeypatch):
    import nabz.news as module
    provider = RssProvider(['https://example.com/rss'], {'example.com'}, license_confirmed=True)
    monkeypatch.setattr(module.socket, 'getaddrinfo', lambda *a, **k: [(None, None, None, None, ('127.0.0.1', 443))])
    with pytest.raises(ValueError, match='non-public'):
        provider.read('https://example.com/rss')
    monkeypatch.setattr(module.socket, 'getaddrinfo', lambda *a, **k: [(None, None, None, None, ('93.184.216.34', 443))])
    class Response:
        status = 302
        def getheader(self, key, default=None):
            return default
        def read(self, limit):
            return b'x' * limit
    class Connection:
        def __init__(self, *a, **k): pass
        def request(self, *a, **k): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(module.http.client, 'HTTPSConnection', Connection)
    with pytest.raises(ValueError, match='redirect'):
        provider.read('https://example.com/rss')
    Response.status = 200
    with pytest.raises(ValueError, match='too large'):
        provider.read('https://example.com/rss')
    monkeypatch.setattr(provider, 'read', lambda _: b'<!DOCTYPE rss [<!ENTITY x "danger">]><rss/>')
    with pytest.raises(ValueError, match='entities'):
        provider.fetch()


def test_timeouts_bounded_and_unknown_usage_reserved(settings):
    store = Store(settings)
    calls = []
    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout('mock timeout')
    provider = CmcProvider(settings, store, httpx.MockTransport(timeout), sleep=lambda _: None)
    with pytest.raises(httpx.ReadTimeout):
        provider.fetch('market')
    assert len(calls) == 3
    with store.connection() as db:
        assert db.execute('SELECT SUM(reserved) FROM usage_records WHERE actual IS NULL').fetchone()[0] == 3
