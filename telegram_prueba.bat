@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
".venv\Scripts\python.exe" scripts\notificar_telegram.py --prueba > "_ejecucion_claude\telegram_prueba.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\telegram_prueba_estado.txt"
