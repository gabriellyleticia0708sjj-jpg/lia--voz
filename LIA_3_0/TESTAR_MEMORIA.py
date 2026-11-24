"""Testes sem internet, sem Ollama e sem microfone. Não usa os dados pessoais reais."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from memoria import comando, recuperar_historico
from ia_local import MotorIA

SCHEMA='''CREATE TABLE messages(id INTEGER PRIMARY KEY,chat TEXT,autor TEXT,texto TEXT);
CREATE TABLE memories(chave TEXT PRIMARY KEY,valor TEXT NOT NULL);'''

class TesteLIA(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.sqlite3'
        self.db=sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def test_nome_apos_reabrir(self):
        self.assertIn('Ana',comando('Meu nome é Ana',self.db))
        self.db.commit();self.db.close();self.db=sqlite3.connect(self.path)
        self.assertEqual(comando('Qual é meu nome?',self.db),'Seu nome é Ana.')
        comando('Meu nome é Bia',self.db)
        self.assertEqual(comando('Qual é meu nome?',self.db),'Seu nome é Bia.')
        comando('Esqueça meu nome',self.db)
        self.assertIn('Ainda não',comando('Qual é meu nome?',self.db))
    def test_notas(self):
        comando('Lembre-se de que estudo Python',self.db)
        comando('Lembre-se de que estudo Python',self.db)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM memories').fetchone()[0],1)
        self.assertIn('estudo Python',comando('O que você sabe sobre mim?',self.db))
        self.assertIn('Não salve',comando('Lembre-se de que minha senha é teste',self.db))
    def test_busca_historica(self):
        self.db.executemany('INSERT INTO messages(chat,autor,texto) VALUES(?,?,?)',[('a','Você','Meu projeto de robótica usa Arduino'),('a','LIA','Podemos programar sensores.'),('b','Você','Estudo inglês'),('b','LIA','Ótimo.')])
        r=recuperar_historico(self.db,'O que conversamos sobre ROBOTICA?','b')
        self.assertIn('Arduino',r[0]['pergunta']);self.assertIn('sensores',r[0]['resposta'])
        # Uma conversa longa também pode recuperar um trecho antigo dela mesma.
        self.db.executemany('INSERT INTO messages(chat,autor,texto) VALUES(?,?,?)',[('a','Você','Outro assunto')]*12)
        r=recuperar_historico(self.db,'robótica','a')
        self.assertIn('Arduino',r[0]['pergunta'])
    def test_contexto_modelo(self):
        class Fake:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self):return b'{"message":{"content":"Resposta de teste"}}'
        with patch('ia_local.urllib.request.urlopen',return_value=Fake()) as call:
            m=MotorIA({'memorias':[{'chave':'nome','valor':'Ana'}],'historico_recuperado':[{'pergunta':'Arduino'}]})
            self.assertEqual(m.responder('Olá',[]),'Resposta de teste')
            payload=json.loads(call.call_args.args[0].data)
            self.assertIn('Ana',payload['messages'][0]['content'])
            self.assertIn('Arduino',payload['messages'][0]['content'])
            self.assertEqual(payload['keep_alive'],'15m')
if __name__=='__main__':unittest.main(verbosity=2)
