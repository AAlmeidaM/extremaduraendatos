@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
".venv\Scripts\python.exe" scripts\inventario_web.py > "_ejecucion_claude\inventario.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\inventario_estado.txt"
