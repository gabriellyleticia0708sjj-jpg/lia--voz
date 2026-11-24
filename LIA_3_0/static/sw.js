// Sem cache de mensagens, anexos, páginas privadas ou dados pessoais.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{if(event.request.mode==='navigate'&&new URL(event.request.url).origin===self.location.origin)event.respondWith(fetch(event.request).catch(()=>new Response('LIA está desconectada. Inicie o servidor local ou retome seu Codespace.',{headers:{'Content-Type':'text/plain; charset=utf-8'}})))});
