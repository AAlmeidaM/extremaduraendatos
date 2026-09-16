@echo off
rem Carga historica de los indicadores de Eurostat (fase 1, NUTS2) y verificacion.
rem Lanzar con doble clic. Deja el progreso en _ejecucion_claude\eurostat.txt
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\eurostat.txt" echo === INICIO %date% %time% ===
".venv\Scripts\python.exe" -m extremadura_datos.ingest --modo historico --fuente eurostat >> "_ejecucion_claude\eurostat.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\eurostat_estado.txt"
".venv\Scripts\python.exe" scripts\verificar_carga.py >> "_ejecucion_claude\eurostat.txt" 2>&1
echo === FIN %date% %time% === >> "_ejecucion_claude\eurostat.txt"
