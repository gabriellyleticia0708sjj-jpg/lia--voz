"""Memória explícita, local e editável para uma instalação pessoal."""
import re
import unicodedata
import uuid


def comando(texto, c):
    texto = re.sub(r'^\s*lia\s*[,!:]\s*', '', texto, flags=re.I).strip()
    nome = re.fullmatch(r'(?:meu nome (?:é|e)|me chamo|lembre-se de que meu nome (?:é|e))\s+([^\n.!?;]{1,80})[.!]?', texto, re.I)
    if nome:
        valor = nome[1].strip()
        if not valor or any(ch.isdigit() for ch in valor):
            return 'Digite apenas o nome pelo qual deseja ser chamada ou chamado.'
        c.execute('INSERT OR REPLACE INTO memories(chave,valor) VALUES(?,?)', ('nome', valor))
        return f'Vou lembrar que seu nome é {valor}. Você pode apagar essa informação no menu.'
    if re.fullmatch(r'(?:qual (?:é|e) (?:o )?meu nome|como (?:eu )?me chamo|voc[eê] (?:lembra|sabe) (?:do |o )?meu nome)[?!.]?', texto, re.I):
        row = c.execute("SELECT valor FROM memories WHERE chave='nome'").fetchone()
        return f'Seu nome é {row[0]}.' if row else 'Ainda não tenho seu nome salvo. Diga: Meu nome é Ana (usando seu nome ou apelido).'
    if re.fullmatch(r'esque[çc]a (?:o )?meu nome[.!]?', texto, re.I):
        c.execute("DELETE FROM memories WHERE chave='nome'")
        return 'Removi seu nome da memória pessoal. O histórico pode ainda conter essa informação.'
    if re.fullmatch(r'(?:o que voc[eê] sabe sobre mim|o que voc[eê] lembra de mim|listar mem[oó]rias)[?!.]?', texto, re.I):
        rows = c.execute('SELECT chave,valor FROM memories ORDER BY chave').fetchall()
        return 'Memória pessoal:\n'+'\n'.join(f'{k}: {v}' for k,v in rows) if rows else 'Ainda não há informações na memória pessoal.'
    m = re.fullmatch(r'(?:lembre-se|lembre|memorize|guarde)\s+(?:que |de que )?(.{1,500})', texto, re.I|re.S)
    if m:
        valor = m[1].strip()
        if not valor or sensivel(valor):
            return 'Não salve senhas, chaves ou dados sensíveis na memória. Use apenas informações de interesse e preferências.'
        if c.execute('SELECT COUNT(*) FROM memories').fetchone()[0]>=50:
            return 'Memória cheia. Apague alguma informação pelo menu antes de adicionar outra.'
        if not c.execute('SELECT 1 FROM memories WHERE valor=?',(valor,)).fetchone():
            c.execute('INSERT INTO memories(chave,valor) VALUES(?,?)', ('nota:'+uuid.uuid4().hex,valor))
        return 'Informação guardada na memória pessoal.'
    return None


def sensivel(valor):
    return bool(re.search(r'\b(senha|password|token|chave de api|cpf|cart[aã]o|endere[çc]o|telefone)\b',valor,re.I))

def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD',texto.casefold()) if not unicodedata.combining(c))

def recuperar_historico(c, texto, chat):
    """Busca lexical em todo o histórico; limita somente o contexto enviado ao modelo."""
    stop=set('qual quais como quando onde porque sobre voce lembra lembro quero pode podeis saber tenho tinha fale fala diga minha minhas meus meu seus suas sua nosso nossa para esta esse essa este isso aquilo uma umas uns dos das com sem que por nao sim mais muito tudo todas todos foram seria estou estava agora anterior conversa conversas lia nome'.split())
    termos=list(dict.fromkeys(t for t in re.findall(r'[^\W_]+',normalizar(texto)) if len(t)>=3 and t not in stop))[:8]
    c.create_function('normalizar',1,normalizar)
    recentes=c.execute('SELECT id FROM messages WHERE chat=? ORDER BY id DESC LIMIT 8',(chat,)).fetchall()
    limite=min((r[0] for r in recentes),default=0)
    if termos:
        expr=' + '.join('(instr(normalizar(texto),?)>0)' for _ in termos)
        rows=c.execute(f'SELECT id,autor,texto,({expr}) AS relevancia FROM messages WHERE (chat<>? OR id<?) AND autor=? AND relevancia>0 ORDER BY relevancia DESC,id DESC LIMIT 5',(*termos,chat,limite,'Você')).fetchall()
    else:
        rows=[]
    # Mantém os pares pergunta/resposta. Para perguntas genéricas, usa também o último assunto.
    if not rows:
        rows=c.execute('SELECT id,autor,texto,0 FROM messages WHERE chat<>? AND autor=? ORDER BY id DESC LIMIT 2',(chat,'Você')).fetchall()
    resultado=[]
    for mid,autor,msg,_ in reversed(rows):
        resposta=c.execute('SELECT texto FROM messages WHERE id=? AND autor=? AND chat=(SELECT chat FROM messages WHERE id=?)',(mid+1,'LIA',mid)).fetchone()
        resultado.append({'pergunta':msg[:350], 'resposta':resposta[0][:350] if resposta else ''})
    return resultado
