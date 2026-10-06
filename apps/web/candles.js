// Explicit CMC identity mapping; an arbitrary token symbol cannot select a market.
const markets={1:'BTC',1027:'ETH',5426:'SOL',52:'XRP',1839:'BNB',74:'DOGE',2010:'ADA',1958:'TRX',5805:'AVAX',1975:'LINK',6636:'DOT',183:'BCH',2:'LTC',7083:'UNI',6535:'NEAR',21794:'APT',8916:'ICP',20947:'SUI',512:'XLM',4642:'HBAR',1321:'ETC',3794:'ATOM',2280:'FIL',7226:'INJ',11840:'OP',11841:'ARB',5690:'RENDER',10603:'IMX',22861:'TIA',22974:'TAO',3773:'FET',23149:'SEI',11419:'TON',28752:'WIF',24478:'PEPE',5994:'SHIB'};
export function tradingSymbol(coin){const base=markets[coin.id];return base&&coin.symbol===base?'BINANCE:'+base+'USDT':null;}
export function candleConfig(symbol,interval,theme){
 if(!/^BINANCE:[A-Z0-9]+USDT$/.test(symbol))throw Error('Invalid chart market');
 return {autosize:true,symbol,interval:['15','60','240','D'].includes(interval)?interval:'60',timezone:'Asia/Tehran',theme:theme==='light'?'light':'dark',style:'1',locale:'en',withdateranges:true,hide_side_toolbar:false,allow_symbol_change:false,save_image:false,calendar:false,support_host:'https://www.tradingview.com'};
}
export function renderCandles(container,coin,{e,theme,interval='60'}){
 const symbol=tradingSymbol(coin);
 if(!symbol){container.innerHTML='<div class="empty"><h3>بازار کندلی این ارز هنوز تطبیق داده نشده است</h3><p>برای بررسی قیمت‌های گردآوری‌شده، نمایش خطی را انتخاب کنید.</p></div>';return;}
 const source='https://www.tradingview.com/symbols/'+symbol.replace(':','-')+'/';
 container.innerHTML=`<div class="candle-toolbar" role="group" aria-label="تایم‌فریم کندل">${Object.entries({'15':'۱۵ دقیقه','60':'۱ ساعت','240':'۴ ساعت',D:'۱ روز'}).map(([v,label])=>`<button data-candle-interval="${v}" aria-pressed="${v===interval}">${label}</button>`).join('')}</div><p class="muted">کندل‌های <bdi>${e(coin.symbol)}/USDT</bdi> در Binance · زمان تهران · نمودار TradingView</p><div class="tradingview-widget-container candle-widget"><div class="tradingview-widget-container__widget"></div></div><p class="tradingview-widget-copyright"><a class="text-link" href="${e(source)}" target="_blank" rel="noopener noreferrer">${e(coin.symbol)}/USDT chart by TradingView ↗</a></p><p class="hint">قیمت نمودار مربوط به این جفت در صرافی است؛ قیمت بالای صفحه از CoinMarketCap به دلار است. نمایش نمودار به اتصال TradingView نیاز دارد؛ اگر بارگذاری نشد، لینک منبع را باز کنید.</p>`;
 const script=document.createElement('script');script.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';script.async=true;script.type='text/javascript';script.textContent=JSON.stringify(candleConfig(symbol,interval,theme));
 script.addEventListener('error',()=>{const host=container.querySelector('.candle-widget');if(host)host.innerHTML='<p class="error">اتصال به منبع نمودار برقرار نشد؛ لینک TradingView را باز کنید یا نمایش خطی را انتخاب کنید.</p>';});
 container.querySelector('.candle-widget').append(script);
}
