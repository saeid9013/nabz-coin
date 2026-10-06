import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chartCoordinate,icon} from '../ui.js';

function luminance(hex){if(hex.length===4)hex='#'+[...hex.slice(1)].map(c=>c+c).join('');const rgb=hex.slice(1).match(/../g).map(c=>parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;}
function contrast(a,b){const values=[luminance(a),luminance(b)].sort((a,b)=>b-a);return (values[0]+.05)/(values[1]+.05);}
test('Both themes preserve AA text contrast across data surfaces',()=>{
 for(const file of ['style.css','design.css']){
 const css=readFileSync(new URL('../'+file,import.meta.url),'utf8');
 let inherited={};
 for(const selector of [':root','html[data-theme=light]']){
  const block=css.slice(css.indexOf(selector)).split('}')[0];
  const tokens={...inherited,...Object.fromEntries([...block.matchAll(/--([\w-]+):(#[\da-f]{6}|#[\da-f]{3})\b/gi)].map(m=>[m[1],m[2]]))};
  inherited=tokens;
  for(const foreground of ['text','muted','accent','positive','negative'])for(const background of ['bg','surface','raised'])assert.ok(contrast(tokens[foreground],tokens[background])>=4.5,`${selector} ${foreground}/${background}`);
  assert.ok(contrast('#ffffff',tokens.primary)>=4.5,'Primary button text');
 }
 }
});
test('Point inspector handles non-uniform time gaps and constant prices',()=>{
 const points=[{time:'2026-01-01T00:00:00Z',price:10},{time:'2026-01-01T00:00:01Z',price:10},{time:'2026-01-01T00:00:10Z',price:10}];
 assert.equal(chartCoordinate(points,0).x,12);assert.equal(chartCoordinate(points,1).x,99.60000000000001);assert.equal(chartCoordinate(points,2).x,888);assert.equal(chartCoordinate(points,1).y,125);
 assert.deepEqual(chartCoordinate(points.slice(0,1),0),{x:450,y:125});
});
test('Control icons expose no duplicate screen-reader names',()=>{assert.ok(icon('market').includes('aria-hidden="true"'));assert.ok(icon('watchlist',true).includes('fill="currentColor"'));});

