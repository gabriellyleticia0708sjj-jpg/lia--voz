import os, sqlite3, threading, json, urllib.request, urllib.error, asyncio, io
from contextlib import closing
from memoria import comando, recuperar_historico
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from ia_local import MotorIA
import recursos
from extensoes import register, preferences, PERSONALIDADES
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=12*1024*1024
DATA=Path(__file__).parent/'dados'; DATA.mkdir(exist_ok=True)
DB=DATA/'web.sqlite3'; lock=threading.Lock()
DEFAULT_MODEL=os.getenv('LIA_MODEL','llama3.2:1b')
VOZ_LIA='pt-BR-FranciscaNeural'
def db():
    c=sqlite3.connect(DB,timeout=10); c.execute('PRAGMA busy_timeout=10000'); c.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, chat TEXT, autor TEXT, texto TEXT)'); c.execute('CREATE INDEX IF NOT EXISTS ix_chat_id ON messages(chat,id)'); c.execute('CREATE TABLE IF NOT EXISTS memories (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)'); c.commit(); recursos.schema(c); return c
@app.before_request
def protect():
    if request.method in ('POST','DELETE') and not request.is_json: return jsonify(error='JSON obrigatório'),415
    if request.method in ('POST','DELETE') and not isinstance(request.get_json(silent=True),dict): return jsonify(error='Objeto JSON obrigatório'),400
@app.get('/sw.js')
def service_worker(): return send_file(Path(__file__).parent/'static'/'sw.js',mimetype='application/javascript',max_age=0)
@app.get('/')
def home(): return render_template('index.html', default_model=DEFAULT_MODEL)
@app.get('/api/history')
def history():
    before=request.args.get('before',type=int)
    with closing(db()) as c:
        rows=c.execute('SELECT id,chat,autor,texto FROM messages WHERE (? IS NULL OR id<?) ORDER BY id DESC LIMIT 100',(before,before)).fetchall()
    return jsonify([dict(id=r[0],chat=r[1],autor=r[2],texto=r[3]) for r in reversed(rows)])
@app.post('/api/clear')
def clear():
    with lock, closing(db()) as c, c: c.execute('DELETE FROM messages'); c.execute('DELETE FROM vectors')
    return jsonify(ok=True)
@app.get('/api/status')
def ai_status():
    backend=request.args.get('backend','ollama')
    model=request.args.get('model',DEFAULT_MODEL)[:120]
    if backend not in ('ollama','openjarvis'):
        return jsonify(message='Motor inválido.'),400
    url=('http://127.0.0.1:11434/api/tags' if backend=='ollama' else os.getenv('OPENJARVIS_URL','http://127.0.0.1:8000').rstrip('/')+'/v1/models')
    try:
        with urllib.request.urlopen(url,timeout=5) as r: result=json.load(r)
        if backend=='ollama':
            names=[x.get('name') or x.get('model') for x in result.get('models',[])]
            if model not in names:
                return jsonify(ok=False,message='Ollama conectado, mas o modelo '+model+' não está instalado. Modelos: '+(', '.join(x for x in names if x) or 'nenhum'))
        return jsonify(ok=True,message='Servidor '+backend+' acessível. Envie uma pergunta para testar a geração.')
    except (OSError,ValueError,TypeError) as e:
        return jsonify(ok=False,message='Servidor '+backend+' indisponível ou diagnóstico não suportado. '+('Execute ollama serve em outro terminal e confira ollama list.' if backend=='ollama' else 'Confira a configuração do OpenJarvis.'))
@app.get('/api/memory')
def memory_list():
    with closing(db()) as c:
        rows=c.execute('SELECT chave,valor FROM memories ORDER BY chave').fetchall()
    return jsonify([dict(chave=k,valor=v) for k,v in rows])

@app.post('/api/memory/update')
def memory_update():
    d=request.get_json(); key=d.get('chave'); value=d.get('valor')
    if not isinstance(key,str) or not isinstance(value,str) or not value.strip() or len(value)>500:
        return jsonify(error='Informação inválida'),400
    from memoria import sensivel
    if sensivel(value): return jsonify(error='Não guarde senhas ou dados sensíveis.'),400
    with lock, closing(db()) as c, c:
        if key=='nome' and (len(value.strip())>80 or any(ch.isdigit() for ch in value)):
            return jsonify(error='Informe apenas o nome ou apelido.'),400
        if key.startswith('nota:'):
            import uuid
            c.execute('UPDATE memories SET chave=?,valor=? WHERE chave=?',('nota:'+uuid.uuid4().hex,value.strip(),key))
        else:
            c.execute('UPDATE memories SET valor=? WHERE chave=?',(value.strip(),key))
    return jsonify(ok=True)

@app.post('/api/memory/delete')
def memory_delete():
    key=request.get_json().get('chave')
    if not isinstance(key,str): return jsonify(error='Chave inválida'),400
    with lock, closing(db()) as c, c:
        c.execute('DELETE FROM memories WHERE chave=?',(key,))
    return jsonify(ok=True)

@app.post('/api/memory/clear')
def memory_clear():
    with lock, closing(db()) as c, c:
        c.execute('DELETE FROM memories')
    return jsonify(ok=True)

@app.post('/api/voz')
def voz():
    d=request.get_json(); text=d.get('texto','')
    if not isinstance(text,str) or not text.strip() or len(text)>4000:
        return jsonify(error='Texto deve ter entre 1 e 4000 caracteres'),400
    try:
        rate=max(0.7,min(1.3,float(d.get('rate',.95))))
        pitch=max(0.7,min(1.3,float(d.get('pitch',1))))
        import edge_tts
        async def gerar():
            buf=io.BytesIO()
            tts=edge_tts.Communicate(text,VOZ_LIA,rate=f'{round((rate-1)*100):+d}%',pitch=f'{round((pitch-1)*100):+d}Hz')
            async for part in tts.stream():
                if part['type']=='audio': buf.write(part['data'])
            if not buf.tell(): raise RuntimeError('Áudio vazio')
            buf.seek(0); return buf
        return send_file(asyncio.run(asyncio.wait_for(gerar(),timeout=25)),mimetype='audio/mpeg',max_age=0)
    except Exception:
        app.logger.exception('Voz neural indisponível')
        return jsonify(error='Voz neural indisponível; use voz do navegador.'),503

@app.post('/api/chat')
def chat():
    d=request.get_json(); msg=str(d.get('message','')).strip(); chat_id=str(d.get('chat',''))[:80]; model=str(d.get('model',DEFAULT_MODEL))[:120]; backend=d.get('backend','ollama')
    if not msg or len(msg)>12000 or not chat_id or backend not in ('ollama','openjarvis'): return jsonify(error='Pedido inválido'),400
    with lock:
        with closing(db()) as c, c:
            answer=comando(msg,c)
            rows=c.execute('SELECT autor,texto FROM messages WHERE chat=? ORDER BY id DESC LIMIT 8',(chat_id,)).fetchall()
            memories=c.execute('SELECT chave,valor FROM memories ORDER BY chave LIMIT 50').fetchall()
            antigos=recuperar_historico(c,msg,chat_id)
            prefs=preferences(c)
            if answer is None and prefs['semantica']:
                try: antigos=recursos.semantic(c,msg,chat_id)+antigos
                except Exception: pass
        if answer is None:
            try:
                answer=MotorIA(dict(backend=backend,modelo=model,openjarvis_model=model,openjarvis_url=os.getenv('OPENJARVIS_URL','http://127.0.0.1:8000'),memorias=[dict(chave=k,valor=v) for k,v in memories],historico_recuperado=antigos,personalidade=PERSONALIDADES.get(prefs['personalidade'],''))).responder(msg,[dict(autor=r[0],texto=r[1]) for r in reversed(rows)])
            except Exception as e:
                with closing(db()) as c, c:
                    c.execute('INSERT INTO messages(chat,autor,texto) VALUES(?,?,?)',(chat_id,'Você',msg))
                return jsonify(error=str(e)),503
        with closing(db()) as c, c:
            c.executemany('INSERT INTO messages(chat,autor,texto) VALUES(?,?,?)',[(chat_id,'Você',msg),(chat_id,'LIA',answer)])
    return jsonify(answer=answer)
register(app,db,lock)
@app.after_request
def privacy_headers(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response
if __name__=='__main__': app.run(host='0.0.0.0' if os.getenv('CODESPACES') else '127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
