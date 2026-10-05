import time
import httpx
from urllib.parse import urlsplit
from .models import Coin, Point
from datetime import datetime, timezone
import math


class CapabilityUnavailable(Exception):
    pass


class CmcProvider:
    BASE = 'https://pro-api.coinmarketcap.com'
    PATHS = {'market': '/v3/cryptocurrency/listings/latest',
             'overview': '/v1/global-metrics/quotes/latest',
             'metadata': '/v2/cryptocurrency/info',
             'history': '/v3/cryptocurrency/quotes/historical',
             'fear': '/v3/fear-and-greed/latest', 'altcoin': '/v1/altcoin-season-index/latest'}

    def __init__(self, settings, store, transport=None, sleep=time.sleep):
        self.store, self.sleep = store, sleep
        self.client = httpx.Client(base_url=self.BASE, timeout=15, follow_redirects=False,
            headers={'X-CMC_PRO_API_KEY': settings.cmc_key}, transport=transport)

    def fetch(self, category, ids=None, cmc_id=None, chart_range=None):
        params = {'limit': 100, 'convert': 'USD'} if category == 'market' else {'convert': 'USD'} if category == 'overview' else {}
        estimate = 1
        if category == 'metadata':
            if not ids or len(ids) > 100 or any(not isinstance(i, int) or i <= 0 for i in ids):
                raise ValueError('Metadata requires 1..100 CMC IDs')
            params = {'id': ','.join(map(str, ids)), 'aux': 'logo', 'skip_invalid': 'true'}
        if category == 'history':
            counts = {'1d': ('hourly', 24), '7d': ('hourly', 168), '30d': ('daily', 30)}
            if not isinstance(cmc_id, int) or cmc_id <= 0 or chart_range not in counts:
                raise ValueError('History ID/range invalid')
            interval, count = counts[chart_range]
            estimate = math.ceil(count / 100)
            params = {'id': str(cmc_id), 'convert': 'USD', 'interval': interval, 'count': count,
                      'time_end': datetime.now(timezone.utc).isoformat(), 'aux': 'price,quote_timestamp'}
        for attempt in range(3):
            token = self.store.reserve(category, estimate=estimate)
            try:
                response = self.client.get(self.PATHS[category], params=params)
            except (httpx.TimeoutException, httpx.NetworkError):
                # Unknown credit use remains reserved, including after crash/restart.
                if attempt == 2:
                    raise
                self.sleep(2 ** attempt)
                continue
            try:
                body = response.json()
            except ValueError:
                body = {}
            credit = body.get('status', {}).get('credit_count') if isinstance(body, dict) else None
            if isinstance(credit, int) and not isinstance(credit, bool) and credit >= 0:
                self.store.settle(token, credit)
            if response.status_code in (401, 403):
                raise CapabilityUnavailable('Upstream capability unavailable')
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    response.raise_for_status()
                self.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            if str(body.get('status', {}).get('error_code', 0)) != '0':
                raise CapabilityUnavailable('Upstream response rejected')
            data = body['data']
            if category == 'history':
                quotes = data.get(str(cmc_id), {}).get('quotes', [])
                if len(quotes) > params['count']:
                    raise ValueError('Upstream exceeded requested chart point cap')
                points = [Point(time=q['timestamp'], price=q['quote']['USD']['price']) for q in quotes]
                points.sort(key=lambda p: p.time)
                # Duplicate timestamps collapse; chart order stays chronological.
                return list({p.time.isoformat(): p.model_dump(mode='json') for p in points}.values())
            if category == 'metadata':
                result = {}
                for identity, metadata in data.items():
                    logo = metadata.get('logo')
                    p = urlsplit(logo or '')
                    if int(identity) in ids and p.scheme == 'https' and p.hostname == 's2.coinmarketcap.com' and p.port in {None, 443} and not p.username and not p.password:
                        result[int(identity)] = {'logo_url': logo}
                return result
            if category != 'market':
                return data
            items = []
            for row in data:
                quotes = row['quote']
                quote = next(q for q in quotes if q.get('symbol') == 'USD') if isinstance(quotes, list) else quotes['USD']
                coin = Coin(id=row['id'], rank=row['cmc_rank'], name=row['name'], symbol=row['symbol'],
                    price=quote['price'], change_24h=quote['percent_change_24h'],
                    volume_24h=quote['volume_24h'], market_cap=quote['market_cap'])
                items.append(coin.model_dump())
            return items


class DemoProvider:
    def fetch(self, category):
        if category != 'market':
            return {'demo': True, 'total_market_cap': 2500000000000, 'btc_dominance': 54.2}
        ids, names, symbols, prices = [1, 1027, 825, 1839, 5426], ['Bitcoin', 'Ethereum', 'Tether', 'BNB', 'Solana'], ['BTC', 'ETH', 'USDT', 'BNB', 'SOL'], [62450.25, 2480.6, 1, 580.4, 145.12]
        return [Coin(id=ids[i] if i < 5 else 900000 + i, rank=i + 1,
            name=names[i] if i < 5 else f'Demo Coin {i+1}', symbol=symbols[i] if i < 5 else f'DEMO{i+1}',
            price=prices[i] if i < 5 else 0.0000000000123 if i == 99 else 1000 / (i + 1),
            change_24h=2.4 + i/50 if i % 2 == 0 else -1.7 - i/80,
            volume_24h=250000000 / (i+1), market_cap=1200000000 / (i+1)).model_dump() for i in range(100)]
