import test from 'node:test';
import assert from 'node:assert/strict';
import {sortProtocols,selectPairs} from '../discovery-ui.js';
test('Monthly TVL ranking keeps zero and losses ahead of missing history',()=>{
 const rows=[{slug:'missing',tvl:999,change_30d:null},{slug:'loss',tvl:1,change_30d:-2},{slug:'zero',tvl:2,change_30d:0},{slug:'gain',tvl:3,change_30d:120}];
 assert.deepEqual(sortProtocols(rows).map(p=>p.slug),['gain','zero','loss','missing']);
 assert.equal(rows[0].slug,'missing');
});
test('DEX discovery matches exact contract text with chain filter and metadata scope',()=>{
 const rows=[{chain:'a',token_address:'AbC',base:'X',volume_24h:5,origins:['meta:cats']},{chain:'b',token_address:'AbC',base:'X',volume_24h:9,origins:['token-feed']}];
 assert.equal(selectPairs(rows,{query:'abc',chain:'a'})[0].chain,'a');
 assert.equal(selectPairs(rows,{origin:'meta:cats'}).length,1);
 assert.equal(selectPairs(rows)[0].chain,'b');
});
