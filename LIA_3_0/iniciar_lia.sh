#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
export LIA_MODEL="${1:-${LIA_MODEL:-llama3.2:1b}}"
export PORT="${PORT:-5000}"
mkdir -p dados
if ! command -v ollama >/dev/null; then
  echo 'Ollama não encontrado. Instale no Codespace: https://ollama.com/download/linux' >&2
  exit 1
fi
# Ambiente isolado, reaproveitado nas próximas inicializações.
if [ ! -x .venv-web/bin/python ]; then python3 -m venv .venv-web; fi
PY=.venv-web/bin/python
if ! "$PY" -c 'import flask, edge_tts, pypdf, PIL, ddgs, vosk' >/dev/null 2>&1; then
  "$PY" -m pip install -r requirements-web.txt
fi
OLLAMA_PID=''
cleanup(){ if [ -n "$OLLAMA_PID" ]; then kill "$OLLAMA_PID" 2>/dev/null || true; fi; }
trap cleanup EXIT
ready(){ curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; }
if ! ready; then
  echo 'Iniciando Ollama...'
  OLLAMA_HOST=127.0.0.1:11434 ollama serve >dados/ollama.log 2>&1 &
  OLLAMA_PID=$!
  for i in $(seq 1 30); do if ready; then break; fi; sleep 1; done
fi
if ! ready; then echo 'Ollama não iniciou. Veja dados/ollama.log.'; tail -n 15 dados/ollama.log 2>/dev/null || true; exit 1; fi
export OLLAMA_HOST=127.0.0.1:11434
if ! ollama show "$LIA_MODEL" >/dev/null 2>&1; then ollama pull "$LIA_MODEL"; fi
# Carregar o modelo já no início reduz a demora da primeira pergunta; falha não impede abrir a interface.
echo "Preparando $LIA_MODEL..."
"$PY" - <<'PY' || true
import json, os, urllib.request
try:
    req=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=json.dumps({'model':os.environ['LIA_MODEL'],'keep_alive':'15m','stream':False}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=90) as r:r.read()
except Exception as e: print('Pré-carregamento não concluído:',e)
PY
echo "LIA pronta para iniciar. Abra a porta $PORT PRIVADA."
"$PY" app.py
