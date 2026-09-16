@echo off
rem Carga historica de la poblacion trimestral del INE (ECP) - 2026-09-16
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\poblacion.txt" echo === INICIO %date% %time% ===
for %%I in (ine_ecp_poblacion_ccaa_historico ine_ecp_poblacion_ccaa ine_ecp_poblacion_provincia_historico ine_ecp_poblacion_provincia) do ".venv\Scripts\python.exe" -m extremadura_datos.ingest --modo historico --solo %%I >> "_ejecucion_claude\poblacion.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\poblacion_estado.txt"
".venv\Scripts\python.exe" scripts\verificar_naturaleza.py >> "_ejecucion_claude\poblacion.txt" 2>&1
echo === FIN %date% %time% === >> "_ejecucion_claude\poblacion.txt"
