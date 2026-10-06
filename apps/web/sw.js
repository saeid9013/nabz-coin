const CACHE='nabz-web-shell-v12';
const FILES=['./','./index.html','./style.css','./app.js','./data.js','./ui.js','./content/encyclopedia.json','./manifest.webmanifest','./assets/icon.svg','./assets/Vazirmatn-Regular.ttf','./assets/Vazirmatn-Bold.ttf'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('nabz-web-shell-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
 if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match('./index.html')));
 else if(FILES.some(path=>new URL(path,self.registration.scope).pathname===url.pathname))event.respondWith(
  fetch(event.request).then(response=>{
   if(response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)));}
   return response;
  }).catch(()=>caches.match(event.request,{ignoreSearch:true})));
});
