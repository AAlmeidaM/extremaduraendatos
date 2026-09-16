@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
".venv\Scripts\python.exe" scripts\notificar_telegram.py > "_ejecucion_claude\telegram_enviar.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\telegram_enviar_estado.txt"
