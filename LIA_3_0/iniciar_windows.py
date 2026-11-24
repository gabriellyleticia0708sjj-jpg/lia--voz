"""Inicializador local para Windows. Nenhum comando é escolhido pela IA."""
import os,sys,time,subprocess,urllib.request,shutil,webbrowser
from pathlib import Path
root=Path(__file__).resolve().parent;os.chdir(root)
os.environ.pop('CODESPACES',None);os.environ['PORT']='5000';os.environ['OLLAMA_HOST']='127.0.0.1:11434';os.environ.setdefault('LIA_MODEL','llama3.2:1b')
ollama=shutil.which('ollama'); local=Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Ollama'/'ollama.exe'
if not ollama and local.is_file():ollama=str(local)
if not ollama:raise SystemExit('Instale Ollama para Windows em https://ollama.com/download/windows')
def ready(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return r.status==200
    except Exception:return False
if ready('http://127.0.0.1:5000/api/preferences'):
    webbrowser.open('http://127.0.0.1:5000');raise SystemExit(0)
proc=None;flask=None
try:
    if not ready('http://127.0.0.1:11434/api/tags'):
        proc=subprocess.Popen([ollama,'serve'])
        for _ in range(30):
            if ready('http://127.0.0.1:11434/api/tags'):break
            time.sleep(1)
    if not ready('http://127.0.0.1:11434/api/tags'):raise RuntimeError('Ollama indisponível')
    model=os.environ['LIA_MODEL']
    if subprocess.run([ollama,'show',model],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:subprocess.run([ollama,'pull',model],check=True)
    flask=subprocess.Popen([sys.executable,'app.py'])
    for _ in range(30):
        if flask.poll() is not None:raise RuntimeError('Flask encerrou; confira a porta 5000.')
        if ready('http://127.0.0.1:5000/api/preferences'):
            webbrowser.open('http://127.0.0.1:5000');break
        time.sleep(1)
    flask.wait()
except KeyboardInterrupt:pass
finally:
    if flask and flask.poll() is None:flask.terminate()
    if proc and proc.poll() is None:proc.terminate()
