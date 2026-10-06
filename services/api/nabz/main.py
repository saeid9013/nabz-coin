from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Literal
import json
import math
import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from .config import Settings
from .store import Store
from .models import MarketResponse, CoinResponse, ChartResponse, NewsResponse, ArticleResponse
from .providers import DemoProvider


def create_app(settings=None):
    settings = settings or Settings.from_env()
    settings.validate()
    store = Store(settings)

    @asynccontextmanager
    async def lifespan(app):
        if settings.mode == 'demo' and not store.get('market'):
            store.put('market', DemoProvider().fetch('market'))
            store.put('overview', DemoProvider().fetch('overview'))
        yield

    app = FastAPI(title='Nabz Coin API', version='0.1.0', lifespan=lifespan)
    app.state.store = store

    @app.middleware('http')
    async def public_limit(request: Request, call_next):
        # Do not trust user-supplied X-Forwarded-For. Configure trusted proxy explicitly in deployment.
        client = request.client.host if request.client else 'unknown'
        if not store.rate_allowed(client):
            return JSONResponse({'detail': 'Rate limit exceeded'}, status_code=429, headers={'Retry-After': '60'})
        return await call_next(request)

    @app.exception_handler(Exception)
    async def unexpected(request, exception):
        return JSONResponse({'detail': 'Service temporarily unavailable'}, status_code=503)

    def cached(key):
        value = store.get(key)
        if value is None:
            raise HTTPException(503, 'Cache not ready; scheduler must run')
        return value

    def freshness(fetched):
        if settings.mode == 'demo':
            return 'demo'
        age = datetime.now(timezone.utc) - datetime.fromisoformat(fetched)
        return 'stale' if age.total_seconds() >= 1200 else 'fresh'

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': settings.mode, 'market_ready': store.get('market') is not None}

    @app.get('/api/v1/market', response_model=MarketResponse)
    def market(q: str = Query('', max_length=100), sort: Literal['rank', 'gainers', 'losers'] = 'rank',
               limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0, le=100)):
        items, fetched = cached('market')
        items = store.enrich_coins(items)
        items = [i for i in items if q.casefold() in f"{i['name']} {i['symbol']}".casefold()]
        items.sort(key=lambda c: c['rank'] if sort == 'rank' else c['change_24h'], reverse=sort == 'gainers')
        return dict(mode=settings.mode, fetched_at=fetched, freshness=freshness(fetched),
                    items=items[offset:offset+limit], total=len(items))

    @app.get('/api/v1/market/overview')
    def overview():
        payload, fetched = cached('overview')
        indices = {key: store.get(key) for key in ['fear', 'altcoin']}
        return dict(mode=settings.mode, fetched_at=fetched, freshness=freshness(fetched), data=payload,
                    indices={k: {'data': v[0], 'fetched_at': v[1]} if v else {'status': 'unavailable'} for k, v in indices.items()})

    def get_coin(cmc_id):
        items, _ = cached('market')
        items = store.enrich_coins(items)
        for item in items:
            if item['id'] == cmc_id:
                return item
        raise HTTPException(404, 'Coin not in cached top 100')

    @app.get('/api/v1/coins/{cmc_id}', response_model=CoinResponse)
    def coin(cmc_id: int):
        item = get_coin(cmc_id)
        _, fetched = cached('market')
        return dict(mode=settings.mode, fetched_at=fetched, freshness=freshness(fetched), coin=item)

    @app.get('/api/v1/coins/{cmc_id}/chart', response_model=ChartResponse)
    def chart(cmc_id: int, range: Literal['1d', '7d', '30d'] = '7d'):
        coin = get_coin(cmc_id)
        if settings.mode == 'demo':
            _, fetched = cached('market')
            last = datetime.fromisoformat(fetched)
            days = {'1d': 1, '7d': 7, '30d': 30}[range]
            points = [{'time': last - timedelta(minutes=(47-i)*days*1440/47),
                'price': coin['price']*(0.97+i/1600+math.sin(i*0.5)*0.008)} for i in __import__('builtins').range(48)]
            return dict(mode='demo', fetched_at=fetched, freshness='demo', range=range, points=points, source='demo')
        entry = store.get(f'chart:{cmc_id}:{range}')
        if entry is None:
            # No paid history request is triggered by a public request.
            points = store.price_history(cmc_id, {'1d': 1, '7d': 7, '30d': 30}[range])
            fetched = points[-1]['time'] if points else None
            return dict(mode='live', fetched_at=fetched, freshness=freshness(fetched) if fetched else 'unavailable',
                range=range, points=points)
        points, fetched = entry
        points.sort(key=lambda p: p['time'])
        return dict(mode='live', fetched_at=fetched, freshness=freshness(fetched), range=range, points=points[:250], source='cmc_history')

    def article_rows(coin_id, cursor, limit):
        where, params = ['1=1'], []
        if cursor:
            with store.connection() as db:
                anchor = db.execute('SELECT published_at,id FROM articles WHERE id=?', (cursor,)).fetchone()
            if not anchor:
                raise HTTPException(400, 'Invalid news cursor')
            where.append('(a.published_at<? OR (a.published_at=? AND a.id<?))')
            params += [anchor['published_at'], anchor['published_at'], anchor['id']]
        if coin_id is not None:
            where.append('EXISTS(SELECT 1 FROM json_each(a.coin_ids) WHERE value=?)')
            params.append(coin_id)
        params.append(limit+1)
        with store.connection() as db:
            rows = db.execute('SELECT a.*,t.title_fa,t.summary_fa,t.status AS translation_status,t.model AS translation_model FROM articles a '
                'LEFT JOIN translations t ON t.rowid=(SELECT rowid FROM translations WHERE article_id=a.id '
                "AND input_hash=a.input_hash ORDER BY (status='ready') DESC,rowid DESC LIMIT 1) "
                'WHERE ' + ' AND '.join(where) + ' ORDER BY a.published_at DESC,a.id DESC LIMIT ?', params).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item['original_fa'] = item.get('translation_model') == 'persian-source-v1'
            item['coin_ids'] = json.loads(item['coin_ids'])
            item['demo'] = bool(item['demo'])
            item['translation_status'] = item['translation_status'] or 'pending'
            if coin_id is None or coin_id in item['coin_ids']:
                items.append(item)
        return items[:limit], (items[limit-1]['id'] if len(items) > limit else None)

    @app.get('/api/v1/news', response_model=NewsResponse)
    def news(coin_id: int | None = Query(None, gt=0), cursor: str | None = Query(None, max_length=64),
             limit: int = Query(20, ge=1, le=50)):
        items, next_cursor = article_rows(coin_id, cursor, limit)
        refreshed = store.get('news_refresh')
        fetched = refreshed[1] if refreshed else None
        return dict(mode=settings.mode, items=items, next_cursor=next_cursor, fetched_at=fetched,
            freshness=freshness(fetched) if fetched else 'unavailable')

    @app.get('/api/v1/news/{article_id}', response_model=ArticleResponse)
    def article(article_id: str):
        with store.connection() as db:
            row = db.execute('SELECT a.*,t.title_fa,t.summary_fa,t.status AS translation_status,t.model AS translation_model FROM articles a '
                'LEFT JOIN translations t ON t.rowid=(SELECT rowid FROM translations WHERE article_id=a.id '
                "AND input_hash=a.input_hash ORDER BY (status='ready') DESC,rowid DESC LIMIT 1) WHERE a.id=?", (article_id,)).fetchone()
        if row:
            item = dict(row)
            item['original_fa'] = item.get('translation_model') == 'persian-source-v1'
            item.update(coin_ids=json.loads(item['coin_ids']), demo=bool(item['demo']),
                translation_status=item['translation_status'] or 'pending')
            return item
        raise HTTPException(404, 'Article not found')

    @app.get('/api/v1/protocols/{slug}')
    def protocol_details(slug: Literal['lido', 'aave', 'uniswap']):
        result = store.get('discovery:protocol:' + slug)
        if not result:
            return dict(mode=settings.mode, items=[], fetched_at=None, freshness='unavailable')
        body, fetched = result
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(fetched)).total_seconds()
        return dict(**body, mode=settings.mode, fetched_at=fetched, freshness='stale' if age > 43200 else 'fresh')

    @app.get('/api/v1/discovery/{category}')
    def discovery(category: Literal['sentiment', 'defi', 'dex', 'projects']):
        if category == 'projects' and os.getenv('APP_COMMERCIAL_MODE', 'false') == 'true':
            return dict(mode=settings.mode, items=[], fetched_at=None, freshness='unavailable')
        result = store.get('discovery:' + category)
        if not result:
            return dict(mode=settings.mode, items=[], fetched_at=None, freshness='unavailable')
        body, fetched = result
        intervals = {'sentiment': 21600, 'defi': 3600, 'dex': 900, 'projects': 604800}
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(fetched)).total_seconds()
        return dict(**body, mode=settings.mode, fetched_at=fetched, freshness='stale' if age > intervals[category] * 2 else 'fresh')

    return app


# Factory avoids reading credentials / opening a database merely by importing module in tests.
