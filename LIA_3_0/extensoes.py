import io,json,os,sqlite3
from contextlib import closing
from flask import request,jsonify,send_file
from ia_local import MotorIA
import recursos as r

PERSONALIDADES={'equilibrada':'Clara e amigável.','tecnica':'Precisa, técnica, com exemplos de código.','professora':'Didática, ensine em etapas e incentive a prática.','objetiva':'Respostas curtas e diretas.'}

def preferences(c):
    d=dict(c.execute('SELECT key,value FROM preferences'))
    return {'personalidade':d.get('personalidade','equilibrada'),'semantica':d.get('semantica','0')=='1'}

def register(app,db,lock):
    @app.get('/api/preferences')
    def prefs():
        with closing(db()) as c:return jsonify(preferences(c))
    @app.post('/api/preferences')
    def setprefs():
        d=request.get_json(); p=d.get('personalidade','equilibrada')
        if p not in PERSONALIDADES:return jsonify(error='Personalidade inválida'),400
        with lock,closing(db()) as c,c:
            c.executemany('INSERT OR REPLACE INTO preferences VALUES(?,?)',[('personalidade',p),('semantica','1' if d.get('semantica') is True else '0')])
        return jsonify(ok=True)
    @app.post('/api/index')
    def index():
        try:
            with lock,closing(db()) as c: n=r.index_batch(c)
            return jsonify(indexados=n)
        except Exception:return jsonify(error='Instale nomic-embed-text no Ollama e mantenha o servidor ativo.'),503
    @app.get('/api/conversations')
    def conversations():
        with closing(db()) as c:
            rows=c.execute('SELECT chat,MIN(id),MAX(id),COUNT(*) FROM messages GROUP BY chat ORDER BY MAX(id) DESC LIMIT 200').fetchall()
            return jsonify([dict(chat=a,title=c.execute('SELECT texto FROM messages WHERE id=?',(b,)).fetchone()[0][:90],count=d) for a,b,_,d in rows])
    @app.get('/api/conversation')
    def conversation():
        chat=request.args.get('chat','')[:80]; before=request.args.get('before',type=int)
        with closing(db()) as c: rows=c.execute('SELECT id,autor,texto FROM messages WHERE chat=? AND (? IS NULL OR id<?) ORDER BY id DESC LIMIT 100',(chat,before,before)).fetchall()
        return jsonify([dict(id=a,autor=b,texto=d) for a,b,d in reversed(rows)])
    @app.get('/api/agenda')
    def agenda():
        with closing(db()) as c: rows=c.execute('SELECT id,title,at,kind,done FROM agenda ORDER BY at').fetchall()
        return jsonify([dict(id=a,title=b,at=d,kind=e,done=bool(f)) for a,b,d,e,f in rows])
    @app.post('/api/agenda')
    def add_agenda():
        d=request.get_json(); title=d.get('title',''); kind=d.get('kind')
        try:
            if not isinstance(title,str) or not title.strip() or len(title)>200 or kind not in ('evento','lembrete'):raise ValueError('Preencha título e tipo.')
            at=r.iso_utc(d.get('at',''))
        except (ValueError,TypeError,AttributeError) as e:return jsonify(error=str(e)),400
        with lock,closing(db()) as c,c: c.execute('INSERT INTO agenda(title,at,kind) VALUES(?,?,?)',(title.strip(),at,kind))
        return jsonify(ok=True)
    @app.post('/api/agenda/change')
    def change_agenda():
        d=request.get_json(); i=d.get('id'); action=d.get('action')
        if not isinstance(i,int) or action not in ('done','delete'):return jsonify(error='Pedido inválido'),400
        with lock,closing(db()) as c,c:
            c.execute('DELETE FROM agenda WHERE id=?' if action=='delete' else 'UPDATE agenda SET done=1 WHERE id=?',(i,))
        return jsonify(ok=True)
    @app.get('/api/agenda/ics')
    def export_agenda():
        from datetime import datetime,timezone
        now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        def escape(s):return s.replace('\\','\\\\').replace('\n','\\n').replace('\r','').replace(',','\\,').replace(';','\\;')
        with closing(db()) as c: rows=c.execute('SELECT id,title,at FROM agenda WHERE done=0').fetchall()
        lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//LIA//Agenda//PT-BR']
        for i,t,a in rows: lines+=['BEGIN:VEVENT',f'UID:{i}@lia.local','DTSTAMP:'+now,'DTSTART:'+datetime.fromisoformat(a).strftime('%Y%m%dT%H%M%SZ'),'SUMMARY:'+escape(t),'END:VEVENT']
        return send_file(io.BytesIO(('\r\n'.join(lines+['END:VCALENDAR',''])).encode()),mimetype='text/calendar',as_attachment=True,download_name='lia-agenda.ics')
    @app.post('/api/search')
    def search():
        d=request.get_json(); q=d.get('query','')
        if not isinstance(q,str) or not q.strip() or len(q)>300:return jsonify(error='Consulta inválida'),400
        try:return jsonify(results=r.search(q.strip()))
        except ValueError as e:return jsonify(error=str(e)),400
        except Exception:return jsonify(error='Pesquisa indisponível. Verifique a conexão e tente novamente.'),503
    @app.post('/api/analyze')
    def analyze():
        d=request.get_json(); kind=d.get('kind'); q=d.get('question',''); name=d.get('name','')
        if kind not in ('pdf','image','code') or not isinstance(q,str) or len(q)>1000 or not isinstance(name,str):return jsonify(error='Pedido inválido'),400
        try:
            b=r.decode(d.get('data'))
            if kind=='image':
                out=r.ollama('/api/chat',{'model':os.getenv('LIA_VISION_MODEL','qwen2.5vl:3b'),'messages':[{'role':'system','content':'Responda em português, descreva apenas conteúdo visível. Não identifique pessoas nem infira dados sensíveis. Respostas seguras e apropriadas à idade.'},{'role':'user','content':q or 'Descreva a imagem e explique o que é possível observar.','images':[r.image_data(b)]}],'stream':False,'options':{'num_predict':512,'num_ctx':4096}},180)
                answer=out['message']['content']
            else:
                text=r.pdf_text(b) if kind=='pdf' else r.code_text(b,name)
                model=str(d.get('model','llama3.2:1b'))[:120]
                answer=MotorIA({'modelo':model,'contexto_extra':text,'num_ctx':8192}).responder((q or ('Resuma os trechos e indique páginas.' if kind=='pdf' else 'Explique a estrutura, possíveis erros e melhorias.'))+' Responda apenas sobre os trechos fornecidos; indique lacunas.',[])
            return jsonify(answer=answer)
        except (ValueError,TypeError) as e:return jsonify(error=str(e)),400
        except Exception:
            app.logger.exception('Análise indisponível')
            return jsonify(error='Não foi possível analisar. Confira o arquivo, dependências e modelo Ollama. Para imagens instale qwen2.5vl:3b.'),503
    @app.post('/api/transcribe')
    def transcribe():
        try:return jsonify(text=r.transcribe(r.decode(request.get_json().get('data'),2*1024*1024)))
        except ValueError as e:return jsonify(error=str(e)),400
        except Exception:return jsonify(error='Reconhecimento offline indisponível. Confira a instalação do Vosk.'),503
