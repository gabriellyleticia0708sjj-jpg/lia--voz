@echo off
cd /d "%~dp0"
py -3.13 -m venv .venv
if errorlevel 1 python -m venv .venv
if not exist ".venv\Scripts\python.exe" (echo Falha ao criar ambiente Python & pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
pause
