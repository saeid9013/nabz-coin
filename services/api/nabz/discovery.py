"""Fixed-origin, scheduled complementary data. Public requests only read cache."""
from datetime import datetime, timezone, timedelta
import math
import os
import httpx
from concurrent.futures import ThreadPoolExecutor
from .dex import collect_dex


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def collect(category, client):
    def get(url):
        response = client.get(url)
        response.raise_for_status()
        if len(response.content) > 20_000_000:
            raise ValueError('Response too large')
        return response.json()
    if category == 'sentiment':
        data = get('https://api.alternative.me/fng/?limit=31')
        if data.get('metadata', {}).get('error'):
            raise ValueError('Sentiment unavailable')
        items = []
        for item in data['data']:
            value = int(item['value'])
            if not 0 <= value <= 100:
                raise ValueError('Invalid sentiment value')
            items.append(dict(value=value, classification=item['value_classification'],
                              time=datetime.fromtimestamp(int(item['timestamp']), timezone.utc).isoformat()))
        remaining = number(data['data'][0].get('time_until_update'))
        if remaining is None:
            try:
                remaining = number(get('https://api.alternative.me/fng/?limit=1')['data'][0].get('time_until_update'))
            except Exception:
                remaining = None
        next_update = (datetime.now(timezone.utc) + timedelta(seconds=remaining)).isoformat() if remaining is not None and remaining >= 0 else None
        return dict(source='Alternative.me', source_url='https://alternative.me/crypto/fear-and-greed-index/', items=items, next_update=next_update)
    if category == 'defi':
        protocols = get('https://api.llama.fi/protocols')
        chains = get('https://api.llama.fi/v2/chains')
        protocols = sorted((p for p in protocols if number(p.get('tvl')) is not None and p.get('category') != 'CEX'), key=lambda p: number(p['tvl']), reverse=True)
        return dict(source='DefiLlama', source_url='https://defillama.com/',
            items=[dict(name=p['name'], slug=p['slug'], category=p.get('category'), chains=p.get('chains', []),
                        tvl=number(p['tvl']), change_1d=number(p.get('change_1d'))) for p in protocols[:100]],
            chains=sorted([dict(name=p['name'], tvl=number(p.get('tvl'))) for p in chains if number(p.get('tvl')) is not None], key=lambda p:p['tvl'], reverse=True)[:30])
    if category == 'dex':
        return collect_dex(client)
    if category == 'defi-growth':
        protocols = get('https://api.llama.fi/protocols')
        ranked = sorted((p for p in protocols if number(p.get('tvl')) is not None and p.get('category') != 'CEX'), key=lambda p: number(p['tvl']), reverse=True)[:100]
        now = datetime.now(timezone.utc)
        target = now - timedelta(days=30)
        def growth(p):
            result = dict(slug=p['slug'], change_30d=None, tvl_30d=None, delta_30d=None, baseline_at=None, status='unavailable')
            try:
                rows = get('https://api.llama.fi/protocol/' + p['slug']).get('tvl', [])
                candidates = [(int(x['date']), number(x.get('totalLiquidityUSD'))) for x in rows if number(x.get('date')) is not None and int(x['date']) <= target.timestamp() and number(x.get('totalLiquidityUSD')) is not None]
                timestamp, baseline = max(candidates, default=(0, None))
                if baseline is not None and baseline > 0 and target.timestamp() - timestamp <= 172800:
                    result.update(change_30d=(number(p['tvl']) / baseline - 1) * 100, tvl_30d=baseline, delta_30d=number(p['tvl'])-baseline, baseline_at=datetime.fromtimestamp(timestamp,timezone.utc).isoformat(),status='ready')
            except Exception:
                pass
            return result
        with ThreadPoolExecutor(max_workers=4) as pool:
            items = list(pool.map(growth, ranked))
        if not any(p['status']=='ready' for p in items):
            raise ValueError('Monthly history unavailable')
        return dict(source='DefiLlama', source_url='https://defillama.com/', items=items, calculated_at=now.isoformat(), scope='top_100_by_current_tvl', methodology='Current TVL / daily TVL at or before 30 days ago, maximum baseline gap 48 hours; positive baseline required.')
    if category.startswith('protocol:'):
        slug = category.split(':', 1)[1]
        if slug not in ['lido', 'aave', 'uniswap']:
            raise ValueError('Unsupported protocol')
        p = get('https://api.llama.fi/protocol/' + slug)
        history = sorted([dict(time=datetime.fromtimestamp(int(x['date']), timezone.utc).isoformat(),
                               price=number(x.get('totalLiquidityUSD'))) for x in p.get('tvl', [])
                          if number(x.get('totalLiquidityUSD')) is not None], key=lambda x: x['time'])
        metrics = {}
        for kind in ['dailyFees', 'dailyRevenue']:
            try:
                result = get('https://api.llama.fi/summary/fees/' + slug + '?dataType=' + kind)
                rows = sorted([dict(time=datetime.fromtimestamp(int(x[0]), timezone.utc).isoformat(), price=number(x[1]))
                               for x in result.get('totalDataChart', []) if len(x) == 2 and number(x[1]) is not None], key=lambda x:x['time'])
                metrics[kind] = dict(total_24h=number(result.get('total24h')), total_7d=number(result.get('total7d')), total_30d=number(result.get('total30d')),
                    points=rows, methodology=result.get('methodology'))
            except Exception:
                metrics[kind] = dict(total_24h=None, total_7d=None, total_30d=None, points=[], methodology=None)
        return dict(source='DefiLlama', source_url='https://defillama.com/protocol/' + slug,
                    items=[dict(slug=slug, name=p['name'], symbol=p.get('symbol'), description=p.get('description'),
                                chains=p.get('chains', []), history=history, metrics=metrics)])
    if category == 'projects':
        items = []
        for identity in ['btc-bitcoin', 'eth-ethereum', 'sol-solana', 'ada-cardano', 'xrp-xrp']:
            p = get('https://api.coinpaprika.com/v1/coins/' + identity)
            items.append(dict(id=p['id'], name=p['name'], symbol=p['symbol'], description=p.get('description'),
                              team=p.get('team', []), links=p.get('links', {}),
                              source_url='https://coinpaprika.com/coin/' + p['id'] + '/'))
        return dict(source='CoinPaprika', source_url='https://coinpaprika.com/', items=items)
    raise ValueError('Unknown category')


def tick_discovery(settings, store, client=None):
    if settings.mode != 'live' or os.getenv('DISCOVERY_ENABLED', 'false') != 'true':
        return
    own_client = client is None
    client = client or httpx.Client(timeout=20, follow_redirects=False)
    try:
        for category, interval in [('sentiment', 21600), ('defi', 3600), ('dex', 900), ('projects', 604800), ('protocol:lido', 21600), ('protocol:aave', 21600), ('protocol:uniswap', 21600), ('defi-growth', 21600)]:
            if category == 'projects' and (os.getenv('COINPAPRIKA_ENABLED', 'false') != 'true' or os.getenv('APP_COMMERCIAL_MODE', 'false') == 'true'):
                continue
            name = 'discovery:' + category
            owner = store.acquire_job(name, interval, ttl=600)
            if not owner:
                continue
            status = 'ready'
            try:
                body = collect(category, client)
                if not body['items']:
                    raise ValueError('Empty provider response')
                store.put(name, body)
            except Exception:
                status = 'retry_pending'
            finally:
                store.finish_job(name, owner, interval if status == 'ready' else 300, status)
    finally:
        if own_client:
            client.close()
