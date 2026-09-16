<#
.SYNOPSIS
    Ejecuta la ingesta diaria y guarda el log en E:\Lab\logs\extremadura-en-datos.

.DESCRIPTION
    Este es el script que llama el Programador de tareas de Windows (lo
    registra scripts\setup.ps1). Tambien se puede ejecutar a mano para forzar
    una ingesta fuera de horario.
#>

$ErrorActionPreference = 'Stop'
$proyectoDir = Split-Path -Parent $PSScriptRoot
$logDir = 'E:\Lab\logs\extremadura-en-datos'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$marca = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$logFile = Join-Path $logDir "ingesta_$marca.log"
$py = Join-Path $proyectoDir '.venv\Scripts\python.exe'

Push-Location $proyectoDir
try {
    # CORREGIDO 2026-09-16: con $ErrorActionPreference = 'Stop', Windows
    # PowerShell 5.1 convierte cada linea que Python escribe en stderr (todo el
    # logging va a stderr) en un error terminante (NativeCommandError). La
    # tarea programada moria en la primera linea de log, sin llegar a ingerir
    # nada ni a copiar el log, y terminaba con codigo 1 cada dia desde el
    # 2026-08-28. Durante la llamada a Python se relaja a 'Continue' y cada
    # linea se pasa a texto plano antes de escribirla al log.
    $ErrorActionPreference = 'Continue'
    & $py -m extremadura_datos.ingest 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logFile
    $codigoSalida = $LASTEXITCODE
} finally {
    $ErrorActionPreference = 'Stop'
    Pop-Location
}

# Web publica (2026-09-16, paso 3 de docs/web-extremaduraendatos.md):
# regenera web/datos/*.json y, si han cambiado, los sube a GitHub; Vercel
# despliega solo. Un fallo aqui no cambia el codigo de salida de la ingesta.
Push-Location $proyectoDir
try {
    $ErrorActionPreference = 'Continue'
    & $py scripts\exportar_web.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -eq 0) {
        git add web/datos 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logFile -Append
        git diff --cached --quiet -- web/datos
        if ($LASTEXITCODE -ne 0) {
            git commit -m "Datos de la web: $(Get-Date -Format 'yyyy-MM-dd')" -- web/datos 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logFile -Append
            git push origin main 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logFile -Append
        } else {
            "Web: sin cambios en web/datos" | Tee-Object -FilePath $logFile -Append
        }
    } else {
        "AVISO: exportar_web.py termino con error; la web conserva los datos anteriores" | Tee-Object -FilePath $logFile -Append
    }
} finally {
    $ErrorActionPreference = 'Stop'
    Pop-Location
}

# Copia siempre legible del ultimo log, sin tener que buscar por fecha.
Copy-Item $logFile (Join-Path $logDir 'latest.log') -Force

exit $codigoSalida
