@echo off
cd /d "%~dp0"
> "_ejecucion_claude\junta.txt" echo === INICIO %date% %time% ===
".venv\Scripts\python.exe" -m extremadura_datos.ingest --modo historico --fuente junta_observatorio >> "_ejecucion_claude\junta.txt" 2>&1
".venv\Scripts\python.exe" scripts\verificar_precios.py >> "_ejecucion_claude\junta.txt" 2>&1
echo HECHO > "_ejecucion_claude\junta_estado.txt"
>> "_ejecucion_claude\junta.txt" echo === FIN %date% %time% ===
