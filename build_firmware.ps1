param([string]$WorkRoot = 'F:\ESP32TouchDashboard-work\2026-10-17')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$dashboardTemp = Join-Path $WorkRoot 'temp'
New-Item -ItemType Directory -Path $dashboardTemp -Force | Out-Null
$env:TEMP = $dashboardTemp
$env:TMP = $dashboardTemp
$env:CCACHE_DIR = Join-Path $WorkRoot 'ccache'
$env:PIP_CACHE_DIR = Join-Path $WorkRoot 'pip-cache'
# Use an activated ESP-IDF 5.5.4 terminal. This command builds only; no flashing.
idf.py -B (Join-Path $WorkRoot 'build') build
if ($LASTEXITCODE -ne 0) { throw 'Firmware build failed.' }
