param(
  [int]$BackendPort = 9003,
  [int]$FrontendPort = 8082
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverDir = Join-Path $root 'server'
$webDir = Join-Path $root 'web'

Write-Host "Workspace: $root"
Write-Host "Backend:  http://127.0.0.1:$BackendPort (Django)"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort (Vue)"

# Backend (pixi)
$backendCmd = "Set-Location -Path `"$serverDir`"; pixi run python manage.py runserver 0.0.0.0:$BackendPort"
Start-Process -FilePath "pwsh" -ArgumentList @("-NoExit", "-Command", $backendCmd) | Out-Null

# Frontend (yarn)
$frontendCmd = "Set-Location -Path `"$webDir`"; yarn serve --port $FrontendPort"
Start-Process -FilePath "pwsh" -ArgumentList @("-NoExit", "-Command", $frontendCmd) | Out-Null

Write-Host "\nStarted. Close the two opened terminals to stop services."