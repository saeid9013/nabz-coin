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
