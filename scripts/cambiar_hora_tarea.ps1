<#
.SYNOPSIS
    Cambia la hora de la tarea programada diaria (por defecto, a las 13:00).

.DESCRIPTION
    Vuelve a registrar la tarea con el mismo contenido que scripts\setup.ps1
    pero con otra hora. No pide contrasena: la tarea se registra para el
    usuario que la lanza y se ejecuta con la sesion iniciada.
#>
[CmdletBinding()]
param([string]$HoraTarea = '13:00')

$ErrorActionPreference = 'Stop'
$proyectoDir = Split-Path -Parent $PSScriptRoot
$nombreTarea = 'OfficeLab - extremadura-en-datos - ingesta diaria'
$scriptIngesta = Join-Path $proyectoDir 'scripts\run_ingesta.ps1'

$accion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptIngesta`""
$disparador = New-ScheduledTaskTrigger -Daily -At $HoraTarea
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Unregister-ScheduledTask -TaskName $nombreTarea -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombreTarea -Action $accion -Trigger $disparador `
    -Settings $ajustes -Description "Ingesta diaria de extremadura-en-datos ($HoraTarea)" | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $nombreTarea
Write-Output "[OK ] Tarea '$nombreTarea' registrada a las $HoraTarea"
Write-Output ("Proxima ejecucion: " + $info.NextRunTime)
Write-Output ("Ultima ejecucion:  " + $info.LastRunTime + "  resultado " + $info.LastTaskResult)
