@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
".venv\Scripts\python.exe" scripts\exportar_web.py > "_ejecucion_claude\exportar_web.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\exportar_web_estado.txt"
