export function sortProtocols(items,field='change_30d'){
 return [...items].sort((a,b)=>{const x=a[field],y=b[field];const valid=v=>typeof v==='number'&&Number.isFinite(v);return valid(x)&&valid(y)?y-x:valid(x)?-1:valid(y)?1:(b.tvl||0)-(a.tvl||0);});
}
export function selectPairs(items,{query='',chain='',sort='volume_24h',origin=''}={}){
 const q=query.trim().toLowerCase();return items.filter(p=>(!chain||p.chain===chain)&&(!origin||p.origins?.some(x=>x.startsWith(origin)))&&[p.base,p.quote,p.name,p.chain,p.dex,p.token_address,p.address].join(' ').toLowerCase().includes(q)).sort((a,b)=>{
  const value=p=>sort==='change'?p.periods?.h24?.change:sort==='transactions'?(p.periods?.h24?.buys??0)+(p.periods?.h24?.sells??0):p[sort];
  const x=value(a),y=value(b);return Number.isFinite(x)&&Number.isFinite(y)?y-x:Number.isFinite(x)?-1:Number.isFinite(y)?1:0;
 });
}
