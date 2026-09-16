@echo off
rem Carga historica de precios agrarios (fase 3): FAO, portal Agri-food, Observatorio Junta
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\precios.txt" echo === INICIO %date% %time% ===
for %%F in (fao agrifood junta_observatorio) do (
  >> "_ejecucion_claude\precios.txt" echo === FUENTE %%F %time% ===
  ".venv\Scripts\python.exe" -m extremadura_datos.ingest --modo historico --fuente %%F >> "_ejecucion_claude\precios.txt" 2>&1
  >> "_ejecucion_claude\precios.txt" echo === FIN FUENTE %%F codigo !errorlevel! ===
)
".venv\Scripts\python.exe" scripts\verificar_carga.py >> "_ejecucion_claude\precios.txt" 2>&1
echo HECHO > "_ejecucion_claude\precios_estado.txt"
>> "_ejecucion_claude\precios.txt" echo === FIN %date% %time% ===
