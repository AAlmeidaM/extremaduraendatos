@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\verificar_precios.py > "_ejecucion_claude\verificar_precios.txt" 2>&1
echo HECHO > "_ejecucion_claude\verificar_precios_estado.txt"
