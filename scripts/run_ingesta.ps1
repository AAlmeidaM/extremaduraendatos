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
    & $py -m extremadura_datos.ingest *>&1 | Tee-Object -FilePath $logFile
    $codigoSalida = $LASTEXITCODE
} finally {
    Pop-Location
}

# Copia siempre legible del ultimo log, sin tener que buscar por fecha.
Copy-Item $logFile (Join-Path $logDir 'latest.log') -Force

exit $codigoSalida
