@echo off
cd /d "%~dp0"
py -3.11 -m venv .venv-web-win
if errorlevel 1 goto erro
.venv-web-win\Scripts\python.exe -m pip install -r requirements-web.txt
if errorlevel 1 goto erro
echo Instalacao concluida. Abra INICIAR_LIA_5_WINDOWS.bat
pause
exit /b 0
:erro
echo Instale Python 3.11 e verifique o terminal.
pause
exit /b 1
