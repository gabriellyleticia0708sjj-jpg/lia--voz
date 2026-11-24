@echo off
cd /d "%~dp0"
if not exist .venv-web-win\Scripts\python.exe (
 echo Instale a LIA 5.0 primeiro.
 pause
 exit /b 1
)
choice /C SN /M "Abrir a LIA automaticamente ao entrar no Windows"
if errorlevel 2 exit /b 0
set "LIA_START=%~dp0INICIAR_LIA_5_WINDOWS.bat"
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'LIA 5.0.lnk')); $s.TargetPath=$env:LIA_START; $s.Save()"
echo Para desativar execute DESATIVAR_INICIO_WINDOWS.bat.
pause
