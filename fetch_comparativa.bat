@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\fetch_comparativa.txt" (
  echo === INICIO %date% %time% ===
)
".venv\Scripts\python.exe" scripts\fetch_comparativa_nacional.py >> "_ejecucion_claude\fetch_comparativa.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\fetch_comparativa_estado.txt"
echo === FIN === >> "_ejecucion_claude\fetch_comparativa.txt"
