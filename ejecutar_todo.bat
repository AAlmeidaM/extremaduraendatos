@echo off
setlocal
cd /d "%~dp0"
if not exist _ejecucion_claude mkdir _ejecucion_claude
set LOG=_ejecucion_claude\log.txt

echo INICIO %date% %time% > "%LOG%"
echo. >> "%LOG%"

echo [1/3] Ejecutando scripts\setup.ps1 ... >> "%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\setup.ps1" >> "%LOG%" 2>&1
set RC1=%errorlevel%
echo [1/3] setup.ps1 termino con codigo %RC1% >> "%LOG%"
echo. >> "%LOG%"

if not %RC1%==0 (
  echo [FIN] setup.ps1 fallo ^(codigo %RC1%^), no se continua. >> "%LOG%"
  echo HECHO_CON_ERROR > _ejecucion_claude\estado.txt
  goto fin
)

echo [2/3] Cargando historico completo ^(esto puede tardar varios minutos^)... >> "%LOG%"
.venv\Scripts\python.exe -m extremadura_datos.ingest --modo historico >> "%LOG%" 2>&1
set RC2=%errorlevel%
echo [2/3] ingest --modo historico termino con codigo %RC2% >> "%LOG%"
echo. >> "%LOG%"

echo [3/3] Verificando filas cargadas en la base de datos... >> "%LOG%"
.venv\Scripts\python.exe scripts\verificar_carga.py >> "%LOG%" 2>&1
echo. >> "%LOG%"

if %RC2%==0 (
  echo HECHO_OK > _ejecucion_claude\estado.txt
) else (
  echo HECHO_CON_ERROR > _ejecucion_claude\estado.txt
)

:fin
echo FIN %date% %time% >> "%LOG%"
