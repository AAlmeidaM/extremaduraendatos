@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\exportar.txt" (
  echo === INICIO %date% %time% ===
)
".venv\Scripts\python.exe" scripts\exportar_analisis.py >> "_ejecucion_claude\exportar.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\exportar_estado.txt"
echo === FIN === >> "_ejecucion_claude\exportar.txt"
