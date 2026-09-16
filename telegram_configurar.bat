@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
".venv\Scripts\python.exe" scripts\telegram_configurar.py > "_ejecucion_claude\telegram_configurar.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\telegram_configurar_estado.txt"
