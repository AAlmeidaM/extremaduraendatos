@echo off
cd /d "%~dp0"
> "_ejecucion_claude\run_ingesta.txt" echo === INICIO %date% %time% ===
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Projects\extremadura-en-datos\scripts\run_ingesta.ps1" >> "_ejecucion_claude\run_ingesta.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\run_ingesta_estado.txt"
echo === FIN %date% %time% === >> "_ejecucion_claude\run_ingesta.txt"
