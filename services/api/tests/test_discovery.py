import httpx
import pytest
from fastapi.testclient import TestClient
from nabz.discovery import collect, tick_discovery
from nabz.config import Settings
from nabz.store import Store
from nabz.main import create_app


def test_sentiment_rejects_out_of_range():
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'data':[{'value':'101','timestamp':'0','value_classification':'Fear'}]}))) as client:
        with pytest.raises(ValueError): collect('sentiment',client)


def test_scheduler_coalesces_and_retains_cache_on_failure(tmp_path,monkeypatch):
    monkeypatch.setenv('DISCOVERY_ENABLED','true')
    monkeypatch.setenv('COINPAPRIKA_ENABLED','false')
    settings=Settings(mode='live',database=str(tmp_path/'data.db'),cmc_key='test')
    store=Store(settings)
    calls=[]
    def request(r):
        calls.append(str(r.url))
        if r.url.host=='api.alternative.me':return httpx.Response(200,json={'data':[{'value':'30','timestamp':'1700000000','value_classification':'Fear'}]})
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        tick_discovery(settings,store,client)
        count=len(calls)
        tick_discovery(settings,store,client)
        assert len(calls)==count
    with TestClient(create_app(settings)) as api:
        result=api.get('/api/v1/discovery/sentiment').json()
        assert result['items'][0]['value']==30
        assert result['source']=='Alternative.me'
        assert api.get('/api/v1/discovery/defi').json()['freshness']=='unavailable'
        assert api.get('/api/v1/discovery/unknown').status_code==422
        assert len(calls)==count


def test_dex_pairs_are_separated_by_chain():
    def request(r):
        return httpx.Response(200,json={'pairs':[dict(chainId=chain,pairAddress='same',baseToken={'symbol':'X','address':'token'},quoteToken={'symbol':'USD'},priceUsd='NaN',liquidity={'usd':100}) for chain in ['a','b']]})
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        items=collect('dex',client)['items']
        assert len(items)==2
        assert all(p['price'] is None for p in items)

def test_commercial_mode_hides_free_paprika_cache(tmp_path,monkeypatch):
    settings=Settings(mode='live',database=str(tmp_path/'data.db'),cmc_key='test')
    store=Store(settings)
    store.put('discovery:projects',{'items':[{'name':'cached'}]})
    monkeypatch.setenv('APP_COMMERCIAL_MODE','true')
    with TestClient(create_app(settings)) as api:
        assert api.get('/api/v1/discovery/projects').json()['items']==[]


def test_defi_excludes_cex_and_nonfinite_tvl():
    def request(r):
        if r.url.path=='/protocols':return httpx.Response(200,json=[{'name':'Exchange','slug':'exchange','category':'CEX','tvl':100},{'name':'Lending','slug':'lending','category':'Lending','tvl':50},{'name':'Broken','tvl':'NaN'}])
        return httpx.Response(200,json=[{'name':'Chain','tvl':40}])
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        result=collect('defi',client)
        assert [p['name'] for p in result['items']]==['Lending']

def test_dex_analytics_preserve_missing_values():
    def request(r):
        return httpx.Response(200,json={'pairs':[dict(chainId='eth',pairAddress='pair',baseToken={'symbol':'X'},quoteToken={'symbol':'USD'},priceUsd='2',marketCap=40,fdv=80,priceNative='0.001',priceChange={'m5':-2.5},txns={'m5':{'buys':12,'sells':7}},volume={'m5':900})]})
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        item=collect('dex',client)['items'][0]
        assert item['periods']['m5']==dict(change=-2.5,volume=900,buys=12,sells=7)
        assert item['periods']['h24']['buys'] is None
        assert item['market_cap']==40 and item['price_native']==.001


def test_protocol_history_survives_missing_revenue(tmp_path):
    def request(r):
        if r.url.path=='/protocol/lido':
            return httpx.Response(200,json={'name':'Lido','tvl':[{'date':1700086400,'totalLiquidityUSD':20},{'date':1700000000,'totalLiquidityUSD':10},{'date':1699000000,'totalLiquidityUSD':'NaN'}]})
        if r.url.params.get('dataType')=='dailyFees':
            return httpx.Response(200,json={'total24h':5,'total7d':30,'total30d':100,'totalDataChart':[[1700000000,5]]})
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        body=collect('protocol:lido',client)
        with pytest.raises(ValueError):collect('protocol:unknown',client)
    item=body['items'][0]
    assert [p['price'] for p in item['history']]==[10,20]
    assert item['metrics']['dailyFees']['total_24h']==5
    assert item['metrics']['dailyFees']['total_30d']==100
    assert item['metrics']['dailyRevenue']['total_24h'] is None
    settings=Settings(mode='live',database=str(tmp_path/'live.db'),cmc_key='test')
    Store(settings).put('discovery:protocol:lido',body)
    with TestClient(create_app(settings)) as api:
        assert api.get('/api/v1/protocols/lido').json()['items'][0]['name']=='Lido'
        assert api.get('/api/v1/protocols/aave').json()['items']==[]
        assert api.get('/api/v1/protocols/unknown').status_code==422


def test_sentiment_next_update_from_provider():
    def request(r):
        return httpx.Response(200,json={'data':[{'value':'73','timestamp':'1791244800','value_classification':'Greed','time_until_update':'600'}]})
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        result=collect('sentiment',client)
    from datetime import datetime, timezone
    seconds=(datetime.fromisoformat(result['next_update'])-datetime.now(timezone.utc)).total_seconds()
    assert 590<seconds<=600


def test_monthly_growth_uses_30_day_baseline_and_missing_is_not_zero():
    from datetime import datetime, timezone, timedelta
    baseline=int((datetime.now(timezone.utc)-timedelta(days=30,hours=1)).timestamp())
    def request(r):
        if r.url.path=='/protocols':
            return httpx.Response(200,json=[dict(name=s,slug=s,tvl=100,category='Lending') for s in ['growing','zero','young']])
        slug=r.url.path.split('/')[-1]
        return httpx.Response(200,json={'tvl':[{'date':baseline if slug!='young' else baseline+86400,'totalLiquidityUSD':50 if slug!='zero' else 0}]})
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        items={x['slug']:x for x in collect('defi-growth',client)['items']}
    assert items['growing']['change_30d']==100
    assert items['growing']['delta_30d']==50
    assert items['zero']['change_30d'] is None
    assert items['young']['change_30d'] is None


def test_dex_feeds_retain_raw_fields_and_survive_one_feed_failure():
    pair=dict(chainId='solana',pairAddress='pool',baseToken={'symbol':'X','address':'token'},quoteToken={'symbol':'SOL','address':'sol'},priceUsd='2',liquidity={'usd':4,'base':2,'quote':1},boosts={'active':5},info={'websites':[{'url':'https://example.com'}]})
    def request(r):
        path=r.url.path
        if path=='/ads/latest/v1':return httpx.Response(503)
        if '/metas/' in path:return httpx.Response(200,json=[])
        if '/latest/dex/' in path:return httpx.Response(200,json={'pairs':[pair]})
        if '/tokens/' in path or '/token-pairs/' in path:return httpx.Response(200,json=[pair])
        if '/orders/' in path:return httpx.Response(200,json=[{'type':'tokenAd','status':'approved'}])
        return httpx.Response(200,json=[{'chainId':'solana','tokenAddress':'token','description':'<unsafe>','totalAmount':5,'customField':'preserved'}])
    with httpx.Client(transport=httpx.MockTransport(request)) as client:
        body=collect('dex',client)
    assert len(body['items'])==1
    assert body['items'][0]['liquidity_base']==2
    assert body['items'][0]['boosts']['active']==5
    assert body['statuses']['ads']=='unavailable'
    assert body['feeds']['profiles'][0]['customField']=='preserved'
    assert body['orders'][0]['data'][0]['status']=='approved'
    assert len(body['endpoint_catalog'])==13


def test_defi_api_merges_monthly_history_without_external_requests(tmp_path):
    settings=Settings(mode='live',database=str(tmp_path/'data.db'),cmc_key='test')
    store=Store(settings)
    store.put('discovery:defi',dict(items=[dict(slug='a',tvl=100)],chains=[]))
    store.put('discovery:defi-growth',dict(items=[dict(slug='a',change_30d=50,delta_30d=30)],calculated_at='2026-10-06T00:00:00+00:00',scope='top_100_by_current_tvl'))
    with TestClient(create_app(settings)) as api:
        body=api.get('/api/v1/discovery/defi').json()
    assert body['items'][0]['change_30d']==50
    assert body['items'][0]['tvl']==100


def test_dex_raw_export_is_opt_in_and_only_reads_cache(tmp_path):
    settings=Settings(mode='live',database=str(tmp_path/'data.db'),cmc_key='test')
    Store(settings).put('discovery:dex',dict(items=[],feeds={'profiles':[{'tokenAddress':'x'}]},raw={'/feed':[{'extra':'kept'}]}))
    with TestClient(create_app(settings)) as api:
        normal=api.get('/api/v1/discovery/dex').json()
        raw=api.get('/api/v1/discovery/dex?include_raw=true').json()
    assert 'raw' not in normal
    assert normal['feeds']['profiles'][0]['tokenAddress']=='x'
    assert raw['raw']['/feed'][0]['extra']=='kept'
