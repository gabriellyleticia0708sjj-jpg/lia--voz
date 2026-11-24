const $=id=>document.getElementById(id), canvas=$('orb'), ctx=canvas.getContext('2d');let mode='idle',busy=false,chat=localStorage.getItem("lia-chat")||crypto.randomUUID(), speaking=false, listening=false, rec=null, stream=null, audio=null, monitor=0, lastClap=0,lastPeak=0, armed=false, micEpoch=0;
localStorage.setItem("lia-chat",chat);
const particles=Array.from({length:430},()=>[Math.random()*Math.PI*2,Math.acos(2*Math.random()-1),Math.random()]);
function draw(ms){const t=ms/1000, active=mode!=='idle', speed=active?1.3:.22, r=155+(active?Math.sin(t*8)*7:Math.sin(t*2)*3);ctx.clearRect(0,0,520,520);ctx.save();ctx.translate(260,260);let g=ctx.createRadialGradient(0,0,0,0,0,225);g.addColorStop(0,'#c084fc55');g.addColorStop(.4,'#6d28d944');g.addColorStop(1,'#00000000');ctx.fillStyle=g;ctx.fillRect(-260,-260,520,520);ctx.globalCompositeOperation='lighter';for(let j=0;j<7;j++){ctx.save();ctx.rotate(t*speed*(j%2?-.3:.4)+j*.7);ctx.strokeStyle=j%2?'#a855f799':'#e9d5ff77';ctx.lineWidth=1.2;ctx.shadowColor='#a855f7';ctx.shadowBlur=12;for(let k=0;k<5;k++){ctx.beginPath();ctx.ellipse(0,0,r+j*7,40+j*19,0,k*1.25,k*1.25+.65);ctx.stroke()}ctx.restore()}for(const [a,b,p] of particles){let x=r*Math.sin(b)*Math.cos(a+t*speed),z=Math.sin(b)*Math.sin(a+t*speed),y=r*Math.cos(b);ctx.fillStyle=`rgba(190,110,255,${.18+.65*(z+1)/2})`;ctx.fillRect(x,y,1+p*2,1+p*2)}ctx.restore();if(!matchMedia('(prefers-reduced-motion: reduce)').matches)requestAnimationFrame(draw)}requestAnimationFrame(draw);
function status(s){$('status').textContent=s}function show(s){$('reply').textContent=s}function panel(open){$('panel').hidden=!open;$('menu').setAttribute('aria-expanded',String(open))}$('menu').onclick=()=>panel(true);$('close').onclick=()=>panel(false);
for(const id of ['backend','model','speak']){let v=localStorage.getItem('lia-'+id);if(v!==null){if(id==='speak')$(id).checked=v==='true';else $(id).value=v}$(id).onchange=()=>localStorage.setItem('lia-'+id,id==='speak'?$(id).checked:$(id).value)}
$('backend').addEventListener('change',()=>{$('model').value=$('backend').value==='ollama'?$('model').dataset.default:'default';localStorage.setItem('lia-model',$('model').value)});
const synth=window.speechSynthesis;
let currentSpeech=0, player=null, playerURL=null, voiceAbort=null;
function refreshVoices(){
  const wanted=localStorage.getItem('lia-voice')||'';
  const sel=$('voice'); sel.replaceChildren(new Option('Automática (português)',''));
  if(!synth)return;
  const voices=synth.getVoices().slice().sort((a,b)=>Number(!a.lang.toLowerCase().startsWith('pt'))-Number(!b.lang.toLowerCase().startsWith('pt')));
  for(const v of voices)sel.add(new Option(v.name+' ('+v.lang+')',v.voiceURI));
  if(voices.some(v=>v.voiceURI===wanted))sel.value=wanted;
}
for(const id of ['voice','rate','pitch','voice-engine']){
  if(id!=='voice'&&localStorage.getItem('lia-'+id)!==null)$(id).value=localStorage.getItem('lia-'+id);
  $(id).onchange=()=>localStorage.setItem('lia-'+id,$(id).value);
}
refreshVoices(); if(synth)synth.addEventListener('voiceschanged',refreshVoices);
function releaseAudio(){if(player){player.onended=player.onerror=null;player.pause();player=null}if(playerURL){URL.revokeObjectURL(playerURL);playerURL=null}}
function cancelSpeech(){++currentSpeech;if(voiceAbort)voiceAbort.abort();voiceAbort=null;releaseAudio();speaking=false;if(synth)synth.cancel()}
async function say(text){
  if(!text)return;
  cancelSpeech();const token=currentSpeech; speaking=true;mode='speaking';if(rec)rec.abort();
  let fallbackUsed=false;
  function done(error){if(token!==currentSpeech)return;releaseAudio();voiceAbort=null;speaking=false;mode=busy?'thinking':'idle';status(error?'Falha ao falar: '+error:'LIA pronta');startRecognition()}
  function fallback(error){
    if(token!==currentSpeech||fallbackUsed)return;fallbackUsed=true;releaseAudio();
    if(!synth||!window.SpeechSynthesisUtterance){done('Síntese de voz indisponível');return;}
    if(error)status('Voz neural indisponível; usando voz do navegador.');else status('LIA falando — navegador');
    const voices=synth.getVoices();const chosen=voices.find(v=>v.voiceURI===$('voice').value)||voices.find(v=>v.lang.toLowerCase()==='pt-br')||voices.find(v=>v.lang.toLowerCase().startsWith('pt'));
    const u=new SpeechSynthesisUtterance(text);u.lang=chosen?chosen.lang:'pt-BR';if(chosen)u.voice=chosen;
    u.rate=Number($('rate').value);u.pitch=Number($('pitch').value);
    u.onend=()=>done();u.onerror=e=>done(e.error);try{synth.speak(u)}catch(e){done(e.message)}
  }
  if($('voice-engine').value==='browser'||text.length>4000){fallback(text.length>4000?'texto longo':null);return}
  voiceAbort=new AbortController();
  try{
    status('Preparando voz Francisca...');
    const r=await fetch('/api/voz',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:text,rate:Number($('rate').value),pitch:Number($('pitch').value)}),signal:voiceAbort.signal});
    if(!r.ok)throw Error('HTTP '+r.status);const blob=await r.blob();if(token!==currentSpeech)return;if(!blob.size)throw Error('Áudio vazio');
    playerURL=URL.createObjectURL(blob);player=new Audio(playerURL);player.onended=()=>done();player.onerror=()=>fallback('áudio');
    status('LIA falando — Francisca Neural');await player.play();
  }catch(e){fallback(e.message)}
}
$('speak').addEventListener('change',()=>{if(!$('speak').checked){cancelSpeech();if(!busy){mode='idle';startRecognition()}}});
$('test-voice').onclick=()=>{if(busy)return;armed=false;say('Olá! Eu sou a LIA. Esta é a minha nova voz. Como posso ajudar você hoje?')};
$('test-ai').onclick=async()=>{
  const out=$('ai-status');out.textContent='Verificando servidor...';
  try{const r=await fetch('/api/status?backend='+encodeURIComponent($('backend').value)+'&model='+encodeURIComponent($('model').value));const d=await r.json();out.textContent=d.message||'Resposta inesperada.';}catch(e){out.textContent='Não foi possível consultar o diagnóstico. '+e.message}
};
async function send(text){if(busy||!text.trim())return;busy=true;armed=false;mode='thinking';show('LIA está pensando…');if(rec)rec.abort();cancelSpeech();try{let res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,chat,backend:$('backend').value,model:$('model').value})});let d=await res.json();if(!res.ok)throw Error(d.error||'Erro HTTP '+res.status);show(d.answer);if($('speak').checked)say(d.answer)}catch(e){show('Não consegui consultar a IA. '+e.message);$('ai-status').textContent=e.message}finally{busy=false;if(!speaking){mode='idle';startRecognition()}}}
$('chat').onsubmit=e=>{e.preventDefault();let v=$('message').value;if(!busy&&v.trim()){$('message').value='';send(v)}};
function newChat(){cancelSpeech();chat=crypto.randomUUID();localStorage.setItem('lia-chat',chat);show('');mode='idle';startRecognition()}
$('new').onclick=()=>{if(!busy){newChat();panel(false)}};
let historyCursor=null, historyText='';
async function loadHistory(older=false){try{let r=await fetch('/api/history'+(older&&historyCursor?'?before='+historyCursor:''));if(!r.ok)throw Error('Histórico indisponível');let d=await r.json();let page=d.map(x=>x.autor+': '+x.texto).join('\n\n');historyText=older?(page?page+'\n\n'+historyText:historyText):page;historyCursor=d.length?d[0].id:null;$('logs').textContent=historyText||'Nenhuma conversa.';$('older').hidden=d.length<100;}catch(e){status(e.message)}}
$('history').onclick=()=>loadHistory();$('older').onclick=()=>loadHistory(true);
async function postJSON(path,data={}){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const d=await r.json();if(!r.ok)throw Error(d.error||'Erro HTTP '+r.status);return d}
$('clear').onclick=async()=>{if(!busy&&confirm('Apagar todo o histórico web? A memória pessoal é separada.')){try{await postJSON('/api/clear');$('logs').textContent='';historyText='';historyCursor=null;$('older').hidden=true;newChat()}catch(e){status(e.message)}}};
async function loadMemory(){try{let r=await fetch('/api/memory');if(!r.ok)throw Error('Memória indisponível');const d=await r.json(), out=$('memory-list');out.replaceChildren();if(!d.length)out.textContent='Nenhuma informação pessoal salva.';for(const m of d){const box=document.createElement('div'), label=document.createElement('p'), edit=document.createElement('button'), del=document.createElement('button');label.textContent=(m.chave==='nome'?'Nome: ':'')+m.valor;edit.textContent='Editar';del.textContent='Apagar';edit.onclick=async()=>{const v=prompt('Atualize a informação:',m.valor);if(v===null)return;try{await postJSON('/api/memory/update',{chave:m.chave,valor:v});loadMemory()}catch(e){status(e.message)}};del.onclick=async()=>{if(!confirm('Apagar esta informação da memória pessoal?'))return;try{await postJSON('/api/memory/delete',{chave:m.chave});loadMemory()}catch(e){status(e.message)}};box.append(label,edit,del);out.append(box)}}catch(e){status(e.message)}}
$('memory').onclick=loadMemory;$('memory-clear').onclick=async()=>{if(!busy&&confirm('Apagar a memória pessoal? O histórico pode ainda conter essas informações.')){try{await postJSON('/api/memory/clear');loadMemory()}catch(e){status(e.message)}}};
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
function wakeMatch(s){return s.match(/^(?:(?:ol[áa]|oi|ei|hey)[,\s]+)?(?:lia|l[íi]a|l[íi]ah)(?=$|[,\s:!?\.\-])[,\s:!?\.\-]*(.*)$/i)}
function startRecognition(){
  if(!SR||rec||busy||speaking||(!armed&&!$('wake').checked))return;
  let r=new SR();rec=r;r.lang='pt-BR';r.continuous=false;r.interimResults=false;r.maxAlternatives=3;
  r.onstart=()=>{listening=true;mode=armed?'listening':'idle';status(armed?'Ouvindo pergunta…':'Microfone ativo: diga LIA ou Olá, LIA')};
  r.onresult=e=>{
    const alternatives=Array.from(e.results[e.resultIndex||0]).map(x=>x.transcript.trim());
    const s=alternatives[0]||'';$('heard').textContent='Última frase reconhecida: '+s;
    if(armed){armed=false;if(s)send(s);return;}
    for(const phrase of alternatives){let m=wakeMatch(phrase);if(m){if(m[1].trim())send(m[1].trim());else{armed=true;mode='listening';show('Estou ouvindo…');status('LIA ativada. Diga sua pergunta.')}return;}}
    status('Ouvi a frase, mas não reconheci a palavra LIA.');
  };
  r.onerror=e=>{
    if(['no-speech','aborted'].includes(e.error))return;
    const errors={'not-allowed':'Permissão do microfone negada. Abra a página em uma aba do Chrome e permita o microfone.','service-not-allowed':'Serviço de reconhecimento bloqueado pelo navegador.','audio-capture':'Microfone não encontrado ou indisponível.','network':'Serviço de reconhecimento de voz sem conexão. Isso é separado do Ollama.','language-not-supported':'Reconhecimento em português não suportado neste navegador.'};
    status(errors[e.error]||('Reconhecimento: '+e.error));$('wake').checked=false;armed=false;
  };
  r.onend=()=>{if(rec===r)rec=null;listening=false;if(!busy&&!speaking){mode=armed?'listening':'idle';if(armed||$('wake').checked)setTimeout(startRecognition,350)}};
  try{r.start()}catch(e){rec=null;armed=false;$('wake').checked=false;status('Não consegui iniciar o microfone: '+e.message)}
}
function activate(){if(busy||speaking)return;if(!SR){status('Reconhecimento indisponível. Abra a página em uma aba do Chrome compatível.');show('Reconhecimento de voz indisponível neste navegador.');return}armed=true;mode='listening';show('Estou ouvindo…');if(rec)rec.abort();else startRecognition()}
$('listen').onclick=()=>{panel(false);activate()};$('wake').onchange=()=>{if($('wake').checked){if(!SR){$('wake').checked=false;status('Navegador sem reconhecimento de voz');return}if(!window.isSecureContext){$('wake').checked=false;status('Abra a URL HTTPS privada da porta do Codespaces.');return}startRecognition()}else if(rec&&!armed)rec.abort()};
async function startClaps(){let epoch=++micEpoch;try{let s=await navigator.mediaDevices.getUserMedia({audio:true});if(epoch!==micEpoch||!$('claps').checked){s.getTracks().forEach(t=>t.stop());return}stream=s;audio=new AudioContext();await audio.resume();if(epoch!==micEpoch||!$('claps').checked)return;let a=audio.createAnalyser();a.fftSize=1024;audio.createMediaStreamSource(stream).connect(a);let b=new Float32Array(a.fftSize);status('Microfone ativo: detector de palmas');function tick(){if(epoch!==micEpoch)return;a.getFloatTimeDomainData(b);let peak=0,rms=0;for(let v of b){peak=Math.max(peak,Math.abs(v));rms+=v*v}rms=Math.sqrt(rms/b.length);let now=performance.now();if(!busy&&!speaking&&!armed&&peak>.55&&peak/(rms+.001)>4&&now-lastPeak>150){lastPeak=now;if(now-lastClap>180&&now-lastClap<850){lastClap=0;activate()}else lastClap=now}monitor=requestAnimationFrame(tick)}tick()}catch(e){$('claps').checked=false;status('Microfone: '+e.message)}}
function stopClaps(){micEpoch++;cancelAnimationFrame(monitor);if(stream)stream.getTracks().forEach(t=>t.stop());if(audio&&audio.state!=='closed')audio.close().catch(()=>{});stream=audio=null;lastClap=lastPeak=0} $('claps').onchange=()=>{$('claps').checked?startClaps():stopClaps()};function stopAll(){$('wake').checked=$('claps').checked=false;armed=false;if(rec)rec.abort();stopClaps();cancelSpeech();$('heard').textContent='';status('Microfone desligado.');if(!busy&&!speaking)mode='idle'}$('stop').onclick=stopAll;window.addEventListener('pagehide',stopAll);
