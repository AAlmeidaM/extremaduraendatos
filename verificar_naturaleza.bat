@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
".venv\Scripts\python.exe" scripts\verificar_naturaleza.py > "_ejecucion_claude\naturaleza.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\naturaleza_estado.txt"
