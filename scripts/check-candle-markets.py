"""Read-only TradingView symbol-page checks. Output is a review draft, not live config."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import httpx

EXCHANGES=[('BINANCE','USDT'),('KRAKEN','USD'),('COINBASE','USD'),('OKX','USDT'),('BYBIT','USDT'),('KUCOIN','USDT'),('GATE','USDT'),('BITFINEX','USD'),('MEXC','USDT')]
ALIASES={38590: ('币安人生', 'BIANRENSHENG')}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='.tools/candle-market-review.json')
    args=parser.parse_args()
    with httpx.Client(timeout=15,follow_redirects=True) as client:
        coins=client.get('http://127.0.0.1:8080/api/v1/market').json()['items']
        def check(coin):
            base=coin['symbol'].upper()
            alias=ALIASES.get(coin['id'])
            if alias and coin['symbol']==alias[0]:base=alias[1]
            result=dict(id=coin['id'],symbol=coin['symbol'],name=coin['name'],markets=[])
            if not re.fullmatch('[A-Z0-9]+',base):
                result['reason']='nonstandard_symbol';return result
            for exchange,quote in EXCHANGES:
                if base==quote:continue
                pair=base+quote
                symbol=exchange+':'+pair
                url='https://www.tradingview.com/symbols/'+pair+'/?exchange='+exchange
                try:
                    response=client.get(url)
                    if response.status_code!=200:continue
                    title=re.search(r'<title>(.*?)</title>',response.text,re.S)
                    if not title or ('"resolved_symbol":"'+symbol+'"' not in response.text):continue
                    result['markets'].append(dict(symbol=symbol,exchange=exchange,base=base,quote=quote,source_url=url,page_title=html.unescape(title.group(1)),checked_at=datetime.now(timezone.utc).isoformat()))
                    # One primary and one alternate, without polling every available exchange.
                    if len(result['markets'])>=2:break
                except httpx.HTTPError:
                    continue
            if not result['markets']:result['reason']='no_confirmed_market'
            print(str(coin['id'])+' '+base+' '+','.join(m['symbol'] for m in result['markets']),flush=True)
            return result
        rows=list(ThreadPoolExecutor(max_workers=4).map(check,coins))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(dict(checked_at=datetime.now(timezone.utc).isoformat(),items=rows),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Matched',sum(bool(row['markets']) for row in rows),'of',len(rows),flush=True)

if __name__=='__main__':main()
