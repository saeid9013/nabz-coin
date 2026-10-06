import {test} from 'node:test';
import assert from 'node:assert/strict';
import {tradingSymbol,candleConfig} from '../candles.js';
test('Candles match verified coin identity and never arbitrary symbols',()=>{
 assert.equal(tradingSymbol({id:1,symbol:'BTC'}),'BINANCE:BTCUSDT');
 assert.equal(tradingSymbol({id:1027,symbol:'ETH'}),'BINANCE:ETHUSDT');
 assert.equal(tradingSymbol({id:1,symbol:'FAKE'}),null);
 assert.equal(tradingSymbol({id:999999,symbol:'BTC'}),null);
 assert.throws(()=>candleConfig('evil:script','60','dark'));
});
test('Candle settings select actual candlesticks, Tehran time and safe intervals',()=>{
 const config=candleConfig('BINANCE:BTCUSDT','240','light');
 assert.equal(config.style,'1');
 assert.equal(config.interval,'240');
 assert.equal(config.timezone,'Asia/Tehran');
 assert.equal(config.allow_symbol_change,false);
 assert.equal(candleConfig('BINANCE:BTCUSDT','bad','bad').interval,'60');
});

test('Catalog covers the current hundred coins, correct BCH identity and explicit aliases',()=>{
 assert.equal(tradingSymbol({id:1831,symbol:'BCH'}),'BINANCE:BCHUSDT');
 assert.equal(tradingSymbol({id:183,symbol:'BCH'}),null);
 assert.equal(tradingSymbol({id:328,symbol:'XMR'}),'KRAKEN:XMRUSD');
 assert.equal(tradingSymbol({id:825,symbol:'USDT'}),'KRAKEN:USDTUSD');
 assert.equal(tradingSymbol({id:38590,symbol:'币安人生'}),'BINANCE:BIANRENSHENGUSDT');
 assert.equal(tradingSymbol({id:38590,symbol:'FAKE'}),null);
});
