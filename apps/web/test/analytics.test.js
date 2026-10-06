import {test} from 'node:test';
import assert from 'node:assert/strict';
import {dexEmbedURL,sentimentOverview} from '../analytics.js';

test('DEX embed uses only fixed origin and safe pair identity',()=>{
 const url=new URL(dexEmbedURL({chain:'solana',address:'AbC123'},'light'));
 assert.equal(url.origin,'https://dexscreener.com');
 assert.equal(url.searchParams.get('embed'),'1');
 assert.equal(url.searchParams.get('theme'),'light');
 assert.equal(dexEmbedURL({chain:'https://evil.test',address:'token'}),null);
 assert.equal(dexEmbedURL({chain:'eth',address:'../token'}),null);
});

test('Sentiment comparison matches exact day and marks missing dates',()=>{
 const data={source_url:'https://alternative.me',items:[{value:73,classification:'Greed',time:'2026-10-06T00:00:00Z'},{value:70,classification:'Greed',time:'2026-10-05T00:00:00Z'},{value:50,classification:'Neutral',time:'2026-09-06T00:00:00Z'}]};
 const html=sentimentOverview(data,{e:s=>String(s),num:s=>String(s),date:s=>s,link:()=>''});
 assert.match(html,/<strong>70<\/strong>/);
 assert.match(html,/<strong>50<\/strong>/);
 assert.match(html,/در دسترس نیست/);

});
