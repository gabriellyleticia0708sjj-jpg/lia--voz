"""Baixa o modelo oficial português Vosk; executado apenas por solicitação do usuário."""
from pathlib import Path
import urllib.request,zipfile,tempfile,shutil
root=Path(__file__).resolve().parent/'modelos'; root.mkdir(exist_ok=True)
name='vosk-model-small-pt-0.3'; dest=root/name
if dest.is_dir(): print('Modelo já instalado.');raise SystemExit(0)
with tempfile.TemporaryDirectory() as tmp:
    archive=Path(tmp)/'modelo.zip'
    print('Baixando modelo português do Vosk...')
    with urllib.request.urlopen('https://alphacephei.com/vosk/models/'+name+'.zip',timeout=60) as r, archive.open('wb') as f:shutil.copyfileobj(r,f)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p=Path(item.filename)
            if not p.parts or p.parts[0]!=name or p.is_absolute() or '..' in p.parts or '\\' in item.filename:raise ValueError('Arquivo de modelo inválido')
        z.extractall(tmp)
    shutil.move(str(Path(tmp)/name),str(dest))
print('Modelo instalado. Abra Ferramentas > Voz offline.')
