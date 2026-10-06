"""Bounded scheduled snapshot of all documented public DEX API families."""
from urllib.parse import quote

ORIGIN = 'https://api.dexscreener.com'
FEEDS = {
    'profiles': '/token-profiles/latest/v1',
    'updates': '/token-profiles/recent-updates/v1',
    'community': '/community-takeovers/latest/v1',
    'ads': '/ads/latest/v1',
    'boosts': '/token-boosts/latest/v1',
    'top_boosts': '/token-boosts/top/v1',
    'metas': '/metas/trending/v1',
}

def collect_dex(client):
    from .discovery import number
    feeds, statuses, raw, pairs, orders = {}, {}, {}, {}, []
    def get(path):
        response = client.get(ORIGIN + path)
        response.raise_for_status()
        if len(response.content) > 20_000_000:
            raise ValueError('DEX response too large')
        result = response.json()
        raw[path] = result
        return result
    def add(rows, origin):
        if not isinstance(rows, list):
            return
        for p in rows:
            identity = (p.get('chainId'), p.get('pairAddress'))
            if not all(identity):
                continue
            if identity in pairs:
                if origin not in pairs[identity]['origins']:
                    pairs[identity]['origins'].append(origin)
                continue
            pairs[identity] = dict(chain=p['chainId'], address=p['pairAddress'], dex=p.get('dexId'),
                base=p.get('baseToken', {}).get('symbol'), quote=p.get('quoteToken', {}).get('symbol'),
                name=p.get('baseToken', {}).get('name'), quote_name=p.get('quoteToken', {}).get('name'),
                token_address=p.get('baseToken', {}).get('address'), quote_address=p.get('quoteToken', {}).get('address'), url=p.get('url'),
                labels=p.get('labels') or [], info=p.get('info') or {}, boosts=p.get('boosts') or {}, origins=[origin],
                price=number(p.get('priceUsd')), liquidity=number((p.get('liquidity') or {}).get('usd')),
                liquidity_base=number((p.get('liquidity') or {}).get('base')),liquidity_quote=number((p.get('liquidity') or {}).get('quote')),
                volume_24h=number((p.get('volume') or {}).get('h24')), price_native=number(p.get('priceNative')),
                fdv=number(p.get('fdv')), market_cap=number(p.get('marketCap')), created_at=number(p.get('pairCreatedAt')),
                periods={period: dict(change=number((p.get('priceChange') or {}).get(period)),volume=number((p.get('volume') or {}).get(period)),
                    buys=number(((p.get('txns') or {}).get(period) or {}).get('buys')),sells=number(((p.get('txns') or {}).get(period) or {}).get('sells')))
                    for period in ['m5','h1','h6','h24']})
    for query in ['BTC','ETH','SOL']:
        try:
            add(get('/latest/dex/search?q='+query).get('pairs'), 'search:'+query)
        except Exception:
            statuses['search:'+query] = 'unavailable'
    for key,path in FEEDS.items():
        try:
            result=get(path)
            if not isinstance(result,list):
                raise ValueError('Expected feed array')
            feeds[key]=result[:100]
            statuses[key]='ready'
        except Exception:
            feeds[key]=[]
            statuses[key]='unavailable'
    tokens={}
    for key in ['profiles','updates','community','ads','boosts','top_boosts']:
        for token in feeds[key]:
            chain,address=token.get('chainId'),token.get('tokenAddress')
            if chain and address:
                tokens.setdefault(chain,{})[address]=True
    # Up to 300 token identities, in batches of at most 30 per official contract.
    remaining=300
    for chain,addresses in list(tokens.items())[:20]:
        addresses=list(addresses)[:remaining]; remaining-=len(addresses)
        for i in range(0,len(addresses),30):
            try:
                add(get('/tokens/v1/'+quote(chain,safe='')+'/'+','.join(quote(a,safe='') for a in addresses[i:i+30])), 'token-feed')
            except Exception:
                statuses['token_pairs']='partial'
    for meta in feeds['metas'][:20]:
        slug=meta.get('slug')
        if not slug:
            continue
        try:
            result=get('/metas/meta/v1/'+quote(slug,safe=''))
            add(result.get('pairs'), 'meta:'+slug)
        except Exception:
            statuses['meta_pairs']='partial'
    for token in feeds['top_boosts'][:10]:
        chain,address=token.get('chainId'),token.get('tokenAddress')
        if not chain or not address:
            continue
        try:
            result=get('/orders/v1/'+quote(chain,safe='')+'/'+quote(address,safe=''))
            orders.append(dict(chain=chain,address=address,data=result))
        except Exception:
            statuses['orders']='partial'
    # Exercise exact-token and exact-pair lookups for the leading observed pair.
    first=next(iter(pairs.values()),None)
    if first:
        for key,path in [('exact_token','/token-pairs/v1/'+quote(first['chain'],safe='')+'/'+quote(first['token_address'] or '',safe='')),
                         ('exact_pair','/latest/dex/pairs/'+quote(first['chain'],safe='')+'/'+quote(first['address'],safe=''))]:
            try:
                result=get(path); add(result if isinstance(result,list) else result.get('pairs'),key)
                statuses[key]='ready'
            except Exception:
                statuses[key]='unavailable'
    if not pairs and not any(feeds.values()):
        raise ValueError('DEX unavailable')
    return dict(source='DEX Screener',source_url='https://dexscreener.com/',
        items=sorted(pairs.values(),key=lambda p:p['volume_24h'] or 0,reverse=True),feeds=feeds,orders=orders,statuses=statuses,raw=raw,
        scope=dict(token_limit=300,meta_limit=20,order_limit=10,searches=['BTC','ETH','SOL']),
        endpoint_catalog=[*FEEDS.values(),'/orders/v1/{chainId}/{tokenAddress}','/latest/dex/pairs/{chainId}/{pairId}',
            '/latest/dex/search?q={query}','/token-pairs/v1/{chainId}/{tokenAddress}','/tokens/v1/{chainId}/{tokenAddresses}','/metas/meta/v1/{slug}'])
