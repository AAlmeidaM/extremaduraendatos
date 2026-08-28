<#
.SYNOPSIS
    Deja el proyecto extremadura-en-datos listo para funcionar: entorno
    virtual, dependencias, base de datos, esquema, Git y tarea programada
    diaria.

.DESCRIPTION
    Pasos (todos re-ejecutables sin romper nada si ya se hicieron antes):
      1. Crea .venv y hace pip install -e . (dependencias de pyproject.toml)
      2. Copia .env.example a .env si no existe
      3. Si .env no tiene ya una DATABASE_URL real, llama a
         C:\OfficeLab\scripts\pg-new-database.ps1 -Slug extremadura-en-datos
         y escribe la cadena de conexion generada directamente en .env
      4. Aplica el esquema de base de datos (sql/001_schema.sql)
      5. git init + primer commit, si no hay ya un repositorio
      6. Registra la tarea programada diaria en el Programador de tareas
         de Windows (ejecuta scripts\run_ingesta.ps1)

.NOTES
    No requiere permisos de administrador.
    Requiere que officelab-postgres este en marcha
    (cd E:\Lab\services\_shared ; docker compose up -d).
#>

[CmdletBinding()]
param(
    [string]$HoraTarea = '08:00'
)

$ErrorActionPreference = 'Stop'
$proyectoDir = Split-Path -Parent $PSScriptRoot
Push-Location $proyectoDir

Write-Output ''
Write-Output '============================================================================'
Write-Output '  SETUP: extremadura-en-datos'
Write-Output '============================================================================'
Write-Output ''

# --- 1. Entorno virtual -------------------------------------------------------
if (-not (Test-Path '.venv')) {
    Write-Output '[1/6] Creando entorno virtual (.venv)...'
    python -m venv .venv
} else {
    Write-Output '[1/6] .venv ya existe, se reutiliza.'
}

$pip = '.venv\Scripts\pip.exe'
$py  = '.venv\Scripts\python.exe'

& $py -m pip install --upgrade pip --quiet
& $pip install -e . --quiet
Write-Output '[OK ] Dependencias instaladas (pip install -e .)'

# --- 2. .env -------------------------------------------------------------------
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Output '[2/6] .env creado a partir de .env.example'
} else {
    Write-Output '[2/6] .env ya existe, no se sobrescribe.'
}

# --- 3. Base de datos y rol -----------------------------------------------------
$envTexto = Get-Content '.env' -Raw
$tieneUrlReal = $envTexto -match 'DATABASE_URL=postgresql://[^\r\n]*' -and
                ($Matches[0] -notmatch 'CAMBIAR')

if (-not $tieneUrlReal) {
    Write-Output '[3/6] Creando base de datos y rol en PostgreSQL compartido...'
    $salida = & powershell -ExecutionPolicy Bypass -File `
        'C:\OfficeLab\scripts\pg-new-database.ps1' -Slug extremadura-en-datos 2>&1
    $salida | ForEach-Object { Write-Output "        $_" }

    $lineaUrl = $salida | Where-Object {
        $_ -match '^DATABASE_URL=postgresql://' -and $_ -notmatch 'CAMBIAR'
    } | Select-Object -First 1

    if (-not $lineaUrl) {
        Write-Output ''
        Write-Output '  [ERROR] No se pudo extraer DATABASE_URL de la salida de pg-new-database.ps1.'
        Write-Output '  Copiala a mano en .env y vuelve a ejecutar este script.'
        Pop-Location
        exit 1
    }

    ($envTexto -replace 'DATABASE_URL=postgresql://[^\r\n]*', $lineaUrl) |
        Set-Content '.env' -NoNewline
    Write-Output '[OK ] DATABASE_URL escrita en .env'
} else {
    Write-Output '[3/6] .env ya tiene una DATABASE_URL configurada, no se toca.'
}

# --- 4. Esquema ------------------------------------------------------------------
Write-Output '[4/6] Aplicando esquema de base de datos...'
& $py -m extremadura_datos.bootstrap_db

# --- 5. Git ------------------------------------------------------------------------
if (-not (Test-Path '.git')) {
    Write-Output '[5/6] Inicializando Git...'
    git init --quiet
    git add .
    git commit --quiet -m 'Estructura inicial de extremadura-en-datos'
    Write-Output '[OK ] Repositorio Git creado con el primer commit'
} else {
    Write-Output '[5/6] Ya existe repositorio Git, no se toca.'
}

# --- 6. Tarea programada -----------------------------------------------------------
Write-Output "[6/6] Registrando tarea programada diaria ($HoraTarea)..."
$nombreTarea = 'OfficeLab - extremadura-en-datos - ingesta diaria'
$scriptIngesta = Join-Path $proyectoDir 'scripts\run_ingesta.ps1'

$accion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptIngesta`""
$disparador = New-ScheduledTaskTrigger -Daily -At $HoraTarea
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Unregister-ScheduledTask -TaskName $nombreTarea -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombreTarea -Action $accion -Trigger $disparador `
    -Settings $ajustes -Description 'Ingesta diaria de extremadura-en-datos (INE)' | Out-Null
Write-Output "[OK ] Tarea '$nombreTarea' registrada (diaria, $HoraTarea, se ejecuta con la sesion iniciada)"

Write-Output ''
Write-Output '----------------------------------------------------------------------------'
Write-Output '  SIGUIENTE PASO RECOMENDADO'
Write-Output '----------------------------------------------------------------------------'
Write-Output ''
Write-Output '  Antes de fiarte de la ingesta automatica, comprueba el JSON real del INE:'
Write-Output ''
Write-Output '    .venv\Scripts\python -m extremadura_datos.inspect_table 75803'
Write-Output ''
Write-Output '  Y luego una ingesta manual de prueba:'
Write-Output ''
Write-Output '    .venv\Scripts\python -m extremadura_datos.ingest'
Write-Output ''
Write-Output '  Ver docs\fuentes-ine.md para el porque de este aviso.'
Write-Output '----------------------------------------------------------------------------'
Write-Output ''

Pop-Location
