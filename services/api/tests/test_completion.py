from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from nabz.config import Settings
from nabz.store import Store, BudgetExceeded
from nabz.main import create_app
from nabz.providers import CmcProvider
from nabz.news import ingest, translate_one, validate_translation, Translation
from nabz.translation import OpenAITranslationProvider


@pytest.fixture
def settings(tmp_path):
    return Settings(mode='live', cmc_key='test-placeholder', database=str(tmp_path / 'live.sqlite3'))


@pytest.mark.parametrize('code', [0, '0'])
def test_cmc_success_code_numeric_or_string(settings, code):
    store = Store(settings)
    provider = CmcProvider(settings, store, httpx.MockTransport(lambda request:
        httpx.Response(200, json={'status': {'error_code': code, 'credit_count': 1}, 'data': []})))
    assert provider.fetch('market') == []
    provider.client.close()


def test_cmc_v3_list_quotes(settings):
    store = Store(settings)
    row = dict(id=1, cmc_rank=1, name='Bitcoin', symbol='BTC', quote=[dict(symbol='USD',
        price=10, percent_change_24h=-1, volume_24h=100, market_cap=1000)])
    provider = CmcProvider(settings, store, httpx.MockTransport(lambda request:
        httpx.Response(200, json={'status': {'error_code': '0', 'credit_count': 1}, 'data': [row]})))
    assert provider.fetch('market')[0]['price'] == 10
    provider.client.close()


def article(index=0, title='BTC rose +2.4%', summary=''):
    return dict(title=title, summary=summary, url=f'https://example.com/news/{index}', publisher='Licensed fixture',
                published_at=f'2026-10-05T{index:02d}:00:00+00:00', demo=False)


def translator(store, handler, budget='1'):
    # Prices and model are deliberately synthetic for deterministic mock tests; not real pricing advice.
    return OpenAITranslationProvider(store, api_key='mock-only', model='mock-model',
        input_usd_per_million='1', output_usd_per_million='2', daily_limit_usd=budget,
        transport=httpx.MockTransport(handler))


def completed(title='بیت‌کوین BTC با رشد +2.4% همراه شد', summary=''):
    return {'status': 'completed', 'usage': {'input_tokens': 100, 'output_tokens': 200},
        'output': [{'type': 'message', 'content': [{'type': 'output_text',
            'text': json.dumps({'title_fa': title, 'summary_fa': summary}, ensure_ascii=False)}]}]}


def test_news_newest_first_filtered_pagination_and_direct_detail(settings):
    app = create_app(settings)
    app.state.store.put('market', [{'id': 1, 'name': 'Bitcoin'}])
    ingest(app.state.store, [article(i, title='Bitcoin news') for i in range(6)])
    with TestClient(app) as client:
        first = client.get('/api/v1/news?coin_id=1&limit=2').json()
        assert first['items'][0]['published_at'] > first['items'][1]['published_at']
        seen = {a['id'] for a in first['items']}
        cursor = first['next_cursor']
        while cursor:
            page = client.get('/api/v1/news', params={'coin_id': 1, 'limit': 2, 'cursor': cursor}).json()
            assert not seen.intersection(a['id'] for a in page['items'])
            seen.update(a['id'] for a in page['items'])
            cursor = page['next_cursor']
        assert len(seen) == 6
        assert client.get('/api/v1/news/'+next(iter(seen))).status_code == 200
        assert client.get('/api/v1/news?cursor=invalid').status_code == 400


def test_metadata_bulk_id_budget_allowlist_and_persistent_enrichment(settings):
    store = Store(settings)
    def handle(request):
        assert request.url.path == '/v2/cryptocurrency/info'
        assert request.url.params['id'] == '1,1027'
        return httpx.Response(200, json={'status': {'credit_count': 1}, 'data': {
            '1': {'logo': 'https://s2.coinmarketcap.com/static/img/coins/64x64/1.png'},
            '1027': {'logo': 'https://localhost/secret.png'}}})
    provider = CmcProvider(settings, store, httpx.MockTransport(handle))
    data = provider.fetch('metadata', ids=[1, 1027])
    assert set(data) == {1}
    store.put_metadata(data, '2026-10-05T00:00:00+00:00')
    assert Store(settings).enrich_coins([{'id': 1}])[0]['logo_url'].startswith('https://s2.coinmarketcap.com/')
    with store.connection() as db:
        assert db.execute("SELECT SUM(actual) FROM usage_records WHERE category='metadata'").fetchone()[0] == 1


def test_live_structured_translation_no_tools_cost_and_dedup(settings):
    store = Store(settings)
    calls = []
    def handle(request):
        payload = json.loads(request.content)
        assert request.url.path == '/v1/responses'
        assert payload['tools'] == [] and payload['store'] is False
        assert payload['text']['format']['strict'] is True
        assert payload['input'][1]['role'] == 'user'
        calls.append(payload)
        return httpx.Response(200, json=completed())
    provider = translator(store, handle)
    ingest(store, [article()], model=provider.model, prompt_version=provider.prompt_version)
    assert translate_one(store, provider)
    assert not translate_one(Store(settings), provider)
    assert len(calls) == 1
    with store.connection() as db:
        row = db.execute('SELECT * FROM translations').fetchone()
        assert row['status'] == 'ready' and row['model'] == 'openai:mock-model'
        cost = db.execute('SELECT * FROM translation_costs').fetchone()
        assert cost['actual_microusd'] == 500
        assert cost['input_tokens'] == 100 and cost['output_tokens'] == 200


def test_translation_auth_failure_is_persistently_disabled(settings):
    store = Store(settings)
    calls = []
    def denied(request):
        calls.append(request)
        return httpx.Response(403, json={'error': {'message': 'denied'}})
    provider = translator(store, denied)
    ingest(store, [article(), article(1)], model=provider.model, prompt_version=provider.prompt_version)
    assert not translate_one(store, provider)
    assert not translate_one(Store(settings), provider)
    assert len(calls) == 1
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM translations WHERE status='unavailable'").fetchone()[0] == 1


def test_translation_budget_blocks_before_request_and_preserves_attempt(settings):
    store = Store(settings)
    calls = []
    provider = translator(store, lambda request: calls.append(request), budget='0.000001')
    ingest(store, [article()], model=provider.model, prompt_version=provider.prompt_version)
    assert not translate_one(store, provider)
    assert calls == []
    with store.connection() as db:
        assert db.execute('SELECT attempts FROM translations').fetchone()[0] == 0
        assert db.execute('SELECT count FROM translation_usage').fetchone()[0] == 0


def test_cost_reservations_are_concurrent_and_survive_restart(settings):
    store = Store(settings)
    def attempt(_):
        try:
            return store.reserve_translation_cost('mock', 1000, 3000)
        except BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(attempt, range(8)))
    assert sum(t is not None for t in tokens) == 3
    with pytest.raises(BudgetExceeded):
        Store(settings).reserve_translation_cost('mock', 1000, 3000)


@pytest.mark.parametrize('body', [
    {'status': 'incomplete', 'output': []},
    {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal'}]}]},
    completed(title='BTC rose +2.4%'),
    completed(title='بیت‌کوین با رشد +2.4% همراه شد'),
    completed(title='بیت‌کوین BTC با رشد 2.4% همراه شد'),
    completed(summary='خلاصه اختراعی')])
def test_translation_rejects_partial_english_changed_values_or_fabricated_summary(settings, body):
    store = Store(settings)
    provider = translator(store, lambda request: httpx.Response(200, json=body))
    ingest(store, [article()], model=provider.model, prompt_version=provider.prompt_version)
    translate_one(store, provider)
    with store.connection() as db:
        assert db.execute('SELECT status FROM translations').fetchone()[0] == 'pending'


def test_translation_requires_explicit_prices(settings):
    with pytest.raises(ValueError, match='prices'):
        OpenAITranslationProvider(Store(settings), api_key='mock', model='mock', input_usd_per_million=0,
            output_usd_per_million=0, daily_limit_usd=1)


def test_history_estimates_budget_before_call_and_shared_scheduler(settings):
    from nabz.scheduler import tick_history
    settings = replace(settings, history_ids=(1,), history_access_confirmed=True)
    store = Store(settings)
    store.put('market', [{'id': 1}])
    calls = []
    def handle(request):
        assert request.url.path == '/v3/cryptocurrency/quotes/historical'
        count = int(request.url.params['count'])
        assert count <= 250 and request.url.params['id'] == '1'
        calls.append(count)
        return httpx.Response(200, json={'status': {'credit_count': 1}, 'data': {'1': {'quotes': [
            {'timestamp': '2026-10-05T02:00:00Z', 'quote': {'USD': {'price': 20}}},
            {'timestamp': '2026-10-05T01:00:00Z', 'quote': {'USD': {'price': 10}}}]}}})
    provider = CmcProvider(settings, store, httpx.MockTransport(handle))
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: tick_history(settings, store, provider), range(3)))
    assert sorted(calls) == [24, 30, 168]
    assert store.get('chart:1:7d')[0][0]['price'] == 10
    tick_history(settings, Store(settings), provider)
    assert len(calls) == 3
    with store.connection() as db:
        reserved = [r[0] for r in db.execute("SELECT reserved FROM usage_records WHERE category='history'")]
    assert sorted(reserved) == [1, 1, 2]
    blocked = Store(replace(settings, database=settings.database + '-blocked', history_limit=1))
    blocked_provider = CmcProvider(settings, blocked, httpx.MockTransport(handle))
    with pytest.raises(BudgetExceeded):
        blocked_provider.fetch('history', cmc_id=1, chart_range='7d')
    assert len(calls) == 3


def test_history_requires_entitlement_confirmation(settings):
    with pytest.raises(ValueError, match='entitlement'):
        replace(settings, history_ids=(1,)).validate()


def test_original_article_versions_are_retained_and_migration_idempotent(settings):
    store = Store(settings)
    first = article(title='BTC first title +2.4%')
    ingest(store, [first])
    changed = {**first, 'title': 'BTC changed title +2.4%'}
    ingest(store, [changed])
    restarted = Store(settings)
    with restarted.connection() as db:
        assert db.execute('SELECT COUNT(*) FROM article_versions').fetchone()[0] == 2
        originals = [row[0] for row in db.execute('SELECT title_original FROM article_versions')]
        assert first['title'] in originals and changed['title'] in originals
        assert [row[0] for row in db.execute('SELECT version FROM schema_version ORDER BY version')] == [1, 2, 3]
