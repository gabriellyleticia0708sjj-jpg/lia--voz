@echo off
powershell -NoProfile -Command "$p=Join-Path ([Environment]::GetFolderPath('Startup')) 'LIA 5.0.lnk'; if(Test-Path -LiteralPath $p){Remove-Item -LiteralPath $p}"
echo Inicio automatico desativado.
pause
