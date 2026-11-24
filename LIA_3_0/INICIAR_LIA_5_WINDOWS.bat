@echo off
cd /d "%~dp0"
if not exist .venv-web-win\Scripts\python.exe (
 echo Execute INSTALAR_LIA_5_WINDOWS.bat primeiro.
 pause
 exit /b 1
)
.venv-web-win\Scripts\python.exe iniciar_windows.py
pause
