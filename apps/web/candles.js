import catalog from './content/candle-markets.json' with {type:'json'};
// Reviewed identities and exact TradingView resolved symbols; no guessed fallback.
const identities=new Map(catalog.items.map(entry=>[entry.id,entry]));
export function tradingMarkets(coin){const entry=identities.get(coin.id);return entry&&entry.symbol.toUpperCase()===coin.symbol.toUpperCase()?entry.markets:[];}
export function tradingSymbol(coin){return tradingMarkets(coin)[0]?.symbol??null;}
export function candleConfig(symbol,interval,theme){
 if(!/^(BINANCE|KRAKEN|COINBASE|OKX|BYBIT|KUCOIN|GATE|BITFINEX|MEXC):[A-Z0-9]+(?:USDT|USD)$/.test(symbol))throw Error('Invalid chart market');
 return {autosize:true,symbol,interval:['15','60','240','D'].includes(interval)?interval:'60',timezone:'Asia/Tehran',theme:theme==='light'?'light':'dark',style:'1',locale:'en',withdateranges:true,hide_side_toolbar:false,allow_symbol_change:false,save_image:false,calendar:false,support_host:'https://www.tradingview.com'};
}
export function renderCandles(container,coin,{e,theme,interval='60',selectedMarket=''}){
 const markets=tradingMarkets(coin),market=markets.find(m=>m.symbol===selectedMarket)||markets[0],symbol=market?.symbol;
 if(!symbol){container.innerHTML='<div class="empty"><h3>بازار کندلی این ارز هنوز تطبیق داده نشده است</h3><p>برای بررسی قیمت‌های گردآوری‌شده، نمایش خطی را انتخاب کنید.</p></div>';return;}
 const source=market.source_url;
 container.innerHTML=`<div class="candle-market-control"><label for="candle-market">صرافی و جفت نمودار</label><select id="candle-market">${markets.map(m=>`<option value="${e(m.symbol)}" ${m.symbol===symbol?'selected':''}>${e(m.exchange)} · ${e(m.base)}/${e(m.quote)}</option>`).join('')}</select><p class="muted">${markets.length>1?'منبع دیگر نیز قابل انتخاب است.':'این ارز فعلاً یک منبع تأییدشده دارد.'}</p></div><div class="candle-toolbar" role="group" aria-label="تایم‌فریم کندل">${Object.entries({'15':'۱۵ دقیقه','60':'۱ ساعت','240':'۴ ساعت',D:'۱ روز'}).map(([v,label])=>`<button data-candle-interval="${v}" aria-pressed="${v===interval}">${label}</button>`).join('')}</div><p class="muted">کندل‌های <bdi>${e(market.base)}/${e(market.quote)}</bdi> در ${e(market.exchange)} · زمان تهران · نمودار TradingView</p><div class="tradingview-widget-container candle-widget"><div class="tradingview-widget-container__widget"></div></div><p class="tradingview-widget-copyright"><a class="text-link" href="${e(source)}" target="_blank" rel="noopener noreferrer">${e(market.base)}/${e(market.quote)} chart by TradingView ↗</a></p><p class="hint">قیمت نمودار مربوط به این جفت در صرافی است؛ قیمت بالای صفحه از CoinMarketCap به دلار است. نمایش نمودار به اتصال TradingView نیاز دارد؛ اگر بارگذاری نشد، منبع دیگر یا لینک TradingView را انتخاب کنید.</p>`;
 const script=document.createElement('script');script.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';script.async=true;script.type='text/javascript';script.textContent=JSON.stringify(candleConfig(symbol,interval,theme));
 script.addEventListener('error',()=>{const host=container.querySelector('.candle-widget');if(host)host.innerHTML='<p class="error">اتصال به منبع نمودار برقرار نشد؛ لینک TradingView را باز کنید یا نمایش خطی را انتخاب کنید.</p>';});
 container.querySelector('.candle-widget').append(script);
}
