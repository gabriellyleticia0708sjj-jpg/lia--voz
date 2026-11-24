"""Testes locais sem serviços externos; não acessa o banco real."""
import base64,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import app,recursos

class LIA5(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.patch=patch.object(app,'DB',Path(self.tmp.name)/'test.sqlite3');self.patch.start();self.client=app.app.test_client()
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def post(self,path,**d):return self.client.post(path,json=d)
    def test_home(self):
        self.assertIn(b'Ferramentas 5.0',self.client.get('/').data)
        self.assertEqual(self.client.get('/sw.js').status_code,200)
        self.assertEqual(self.client.get('/static/manifest.json').json['short_name'],'LIA')
    def test_memory_conversations(self):
        self.assertEqual(self.post('/api/chat',message='Meu nome é Ana',chat='a').status_code,200)
        self.assertEqual(self.post('/api/chat',message='Qual é meu nome?',chat='b').json['answer'],'Seu nome é Ana.')
        self.assertEqual(len(self.client.get('/api/conversations').json),2)
        self.assertEqual(len(self.client.get('/api/conversation?chat=a').json),2)
    def test_preferences(self):
        self.assertEqual(self.post('/api/preferences',personalidade='tecnica',semantica=True).status_code,200)
        self.assertEqual(self.client.get('/api/preferences').json,{'personalidade':'tecnica','semantica':True})
        self.assertEqual(self.post('/api/preferences',personalidade='x').status_code,400)
    def test_agenda(self):
        self.assertEqual(self.post('/api/agenda',title='Estudar',at='2027-01-01T10:00:00-03:00',kind='lembrete').status_code,200)
        item=self.client.get('/api/agenda').json[0];self.assertEqual(item['at'],'2027-01-01T13:00:00+00:00')
        self.assertIn(b'DTSTART:20270101T130000Z',self.client.get('/api/agenda/ics').data)
        self.post('/api/agenda/change',id=item['id'],action='done');self.assertTrue(self.client.get('/api/agenda').json[0]['done'])
    def test_semantics(self):
        self.post('/api/chat',message='Meu nome é Ana',chat='a')
        with patch('recursos.embeddings',side_effect=lambda x:[[1.,0.] for _ in x]):
            self.assertEqual(self.post('/api/index').json['indexados'],1)
            with app.db() as c:self.assertIn('Ana',recursos.semantic(c,'nome','b')[0]['pergunta'])
            self.post('/api/clear')
            with app.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM vectors').fetchone()[0],0)
    def test_code_zip(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('app.py','print("ola")\npassword="teste"');z.writestr('.env','SECRET=abc');z.writestr('node_modules/test.js','bad')
        out=recursos.code_text(b.getvalue(),'project.zip');self.assertIn('print',out);self.assertNotIn('teste',out);self.assertNotIn('SECRET',out)
        with patch('extensoes.MotorIA.responder',return_value='Análise de teste'):
            result=self.post('/api/analyze',kind='code',name='project.zip',data=base64.b64encode(b.getvalue()).decode(),question='Explique')
            self.assertEqual(result.json['answer'],'Análise de teste')
    def test_search_mock(self):
        with patch('recursos.search',return_value=[{'title':'Python','url':'https://python.org','snippet':'Docs'}]):
            self.assertEqual(self.post('/api/search',query='Python').json['results'][0]['title'],'Python')
    def test_image_mock(self):
        from PIL import Image
        f=io.BytesIO();Image.new('RGB',(20,20),'purple').save(f,format='PNG')
        with patch('recursos.ollama',return_value={'message':{'content':'Imagem roxa'}}) as call:
            result=self.post('/api/analyze',kind='image',name='test.png',data=base64.b64encode(f.getvalue()).decode(),question='Descreva')
            self.assertEqual(result.json['answer'],'Imagem roxa');self.assertTrue(call.call_args.args[1]['messages'][1]['images'])
    def test_audio_mock(self):
        with patch('recursos.transcribe',return_value='Olá'):
            self.assertEqual(self.post('/api/transcribe',data=base64.b64encode(b'test').decode()).json['text'],'Olá')
    def test_privacy(self):
        self.assertEqual(self.client.get('/api/history').headers['Cache-Control'],'no-store')
        self.assertEqual(self.client.post('/api/clear',data='x').status_code,415)
if __name__=='__main__':unittest.main(verbosity=2)
