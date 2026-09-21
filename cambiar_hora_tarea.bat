@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\cambiar_hora_tarea.ps1" > "_ejecucion_claude\cambiar_hora2.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\cambiar_hora_estado.txt"
