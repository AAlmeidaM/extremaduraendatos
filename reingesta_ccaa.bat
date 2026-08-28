@echo off
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\reingesta.txt" (
  echo === INICIO %date% %time% ===
)
".venv\Scripts\python.exe" -m extremadura_datos.ingest --modo historico >> "_ejecucion_claude\reingesta.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\reingesta_estado.txt"
".venv\Scripts\python.exe" scripts\verificar_carga.py >> "_ejecucion_claude\reingesta.txt" 2>&1
echo === FIN === >> "_ejecucion_claude\reingesta.txt"
