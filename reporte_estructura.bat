@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\reporte.txt" (
  echo === INICIO %date% %time% ===
)
".venv\Scripts\python.exe" scripts\reporte_estructura.py >> "_ejecucion_claude\reporte.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\reporte_estado.txt"
echo === FIN === >> "_ejecucion_claude\reporte.txt"
