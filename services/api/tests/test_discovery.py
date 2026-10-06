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
