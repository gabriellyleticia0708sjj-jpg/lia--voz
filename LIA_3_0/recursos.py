"""Recursos opcionais da LIA 5.0. Nenhum arquivo enviado é executado."""
import base64, io, json, math, re, sqlite3, threading, urllib.request, wave, zipfile
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
EMBED_MODEL = 'nomic-embed-text'

def ollama(path, payload, timeout=90):
    req=urllib.request.Request('http://127.0.0.1:11434'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def embeddings(texts):
    return ollama('/api/embed', {'model':EMBED_MODEL,'input':[t[:1800] for t in texts], 'keep_alive':'2m'},30)['embeddings']

def schema(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS agenda(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,at TEXT NOT NULL,kind TEXT NOT NULL,done INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS vectors(mid INTEGER PRIMARY KEY, model TEXT NOT NULL, source TEXT NOT NULL, vector TEXT NOT NULL);''')

def index_batch(c, limit=16):
    rows=c.execute("SELECT m.id,m.texto FROM messages m LEFT JOIN vectors v ON m.id=v.mid AND v.model=? AND v.source=m.texto WHERE m.autor='Você' AND v.mid IS NULL ORDER BY m.id DESC LIMIT ?",(EMBED_MODEL,limit)).fetchall()
    if rows:
        vecs=embeddings([r[1] for r in rows]); c.executemany('INSERT OR REPLACE INTO vectors VALUES(?,?,?,?)',[(mid,EMBED_MODEL,t,json.dumps(v)) for (mid,t),v in zip(rows,vecs)])
    c.commit(); return len(rows)

def semantic(c, query, chat):
    q=embeddings([query])[0]; norm=lambda v:math.sqrt(sum(x*x for x in v)) or 1
    n=norm(q); ranked=[]
    for mid,txt,raw in c.execute("SELECT m.id,m.texto,v.vector FROM vectors v JOIN messages m ON m.id=v.mid AND m.texto=v.source WHERE v.model=? AND m.chat<>?",(EMBED_MODEL,chat)):
        v=json.loads(raw)
        if len(v)!=len(q):continue
        score=sum(x*y for x,y in zip(q,v))/(n*norm(v))
        if score>.35:ranked.append((score,mid,txt))
    results=[]
    for _,mid,txt in sorted(ranked,reverse=True)[:3]:
        row=c.execute("SELECT texto FROM messages WHERE id=? AND autor='LIA' AND chat=(SELECT chat FROM messages WHERE id=?)",(mid+1,mid)).fetchone()
        results.append({'pergunta':txt[:350],'resposta':row[0][:350] if row else ''})
    return results

def decode(raw, limit=8*1024*1024):
    if not isinstance(raw,str) or len(raw)>limit*4//3+8:raise ValueError('Arquivo grande demais.')
    b=base64.b64decode(raw,validate=True)
    if not b or len(b)>limit:raise ValueError('Arquivo vazio ou grande demais.')
    return b

def pdf_text(b):
    from pypdf import PdfReader
    r=PdfReader(io.BytesIO(b));
    if r.is_encrypted:raise ValueError('PDF protegido por senha não é suportado.')
    parts=[]; remaining=18000
    for i,p in enumerate(r.pages[:30],1):
        if remaining<=0:break
        t=(p.extract_text() or '')[:remaining];remaining-=len(t)
        if t.strip():parts.append(f'Página {i}:\n'+t)
    if not parts:raise ValueError('Não há texto extraível. PDF digitalizado precisa de OCR, não incluído.')
    return '\n\n'.join(parts)

CODE_EXT={'.py','.js','.ts','.jsx','.tsx','.html','.css','.sql','.json','.md','.txt','.java','.c','.cpp','.cs','.go','.rs','.yaml','.yml','.toml','.vue','.php','.rb'}
BLOCK={'node_modules','.git','.venv','venv','__pycache__','dist','build','dados','secrets','credentials'}
def code_text(b,name):
    def allowed(n):
        p=Path(n); low=n.lower()
        return p.suffix.lower() in CODE_EXT and not any(x.startswith('.') or x.lower() in BLOCK for x in p.parts) and not any(x in low for x in ('secret','credential','password','token','private_key','api_key'))
    def redacted(s):
        return re.sub(r'(?im)^.*(?:api[_-]?key|password|senha|secret|token|private.key|credential)\s*[:=].*$', '[linha potencialmente sensível omitida]',s)
    if name.lower().endswith('.zip'):
        out=[]; total=0
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            for item in z.infolist()[:500]:
                if item.is_dir() or not allowed(item.filename) or item.file_size>160000 or item.flag_bits&1:continue
                s=redacted(z.read(item).decode('utf-8',errors='replace'))[:5000]; block=f'Arquivo {item.filename}:\n{s}'
                if total+len(block)>18000:break
                out.append(block);total+=len(block)
                if len(out)>=25:break
        if not out:raise ValueError('Nenhum arquivo de código compatível no ZIP.')
        return '\n\n'.join(out)
    if not allowed(name):raise ValueError('Tipo de código não suportado.')
    return redacted(b.decode('utf-8',errors='replace'))[:18000]

def image_data(b):
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS=16_000_000
    with Image.open(io.BytesIO(b)) as im:
        if im.width*im.height>16_000_000:raise ValueError('Imagem grande demais.')
        im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1024,1024));out=io.BytesIO();im.save(out,format='JPEG',quality=85)
    return base64.b64encode(out.getvalue()).decode()

_vosk=None; _vosk_lock=threading.Lock()
def transcribe(b):
    global _vosk
    from vosk import Model, KaldiRecognizer
    path=ROOT/'modelos'/'vosk-model-small-pt-0.3'
    if not path.is_dir():raise ValueError('Instale o modelo Vosk com INSTALAR_VOZ_OFFLINE.py.')
    with wave.open(io.BytesIO(b),'rb') as w:
        if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate()!=16000 or w.getnframes()>16000*30:raise ValueError('Gravação precisa ser WAV mono 16 kHz, até 30 segundos.')
        with _vosk_lock:
            if _vosk is None:_vosk=Model(str(path))
        r=KaldiRecognizer(_vosk,16000); parts=[]
        while True:
            chunk=w.readframes(4000)
            if not chunk:break
            if r.AcceptWaveform(chunk):parts.append(json.loads(r.Result()).get('text',''))
        parts.append(json.loads(r.FinalResult()).get('text',''))
    return ' '.join(p for p in parts if p).strip()

def search(query):
    from ddgs import DDGS
    # Pesquisa explícita, modo estrito; nenhum resultado é executado ou aberto pelo servidor.
    # Filtros são auxiliares, não substituem supervisão.
    if re.search(r'\b(porn[oô]\w*|nudes?|cassino|betting|apostas?|armas?|drogas?|suic[ií]dio|automutila\w*)\b',query,re.I):raise ValueError('Use a pesquisa para estudos, tecnologia e assuntos seguros.')
    rows=DDGS(timeout=12).text(query,region='br-pt',safesearch='on',max_results=5)
    return [{'title':str(r.get('title',''))[:200],'url':r['href'],'snippet':str(r.get('body',''))[:500]} for r in rows if urlparse(r.get('href','')).scheme in ('http','https')]

def iso_utc(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('Data precisa de fuso horário.')
    return dt.astimezone(timezone.utc).isoformat(timespec='seconds')
