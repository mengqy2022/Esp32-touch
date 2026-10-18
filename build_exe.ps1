param(
    [string]$PythonPath = (Get-Command python -ErrorAction Stop).Source,
    [string]$WorkRoot = 'F:\ESP32TouchDashboard-work\2026-10-17',
    [string]$RuntimeTemp = '',
    [switch]$PublishToRepository
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = ''
$dashboardTemp = Join-Path $WorkRoot 'temp'
$dashboardEnv = Join-Path $WorkRoot 'packaging-gui'
$dashboardBuild = Join-Path $WorkRoot 'build'
$dashboardOutput = Join-Path $WorkRoot 'output'
foreach ($dashboardDir in @($WorkRoot, $dashboardTemp, $dashboardBuild, $dashboardOutput)) {
    New-Item -ItemType Directory -Path $dashboardDir -Force | Out-Null
}
$env:TEMP = $dashboardTemp
$env:TMP = $dashboardTemp
$env:PIP_CACHE_DIR = Join-Path $WorkRoot 'pip-cache'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $WorkRoot 'pyinstaller-cache'
$env:CCACHE_DIR = Join-Path $WorkRoot 'ccache'
$dashboardPython = Join-Path $dashboardEnv 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $dashboardPython)) {
    & $PythonPath -c 'import tkinter'
    if ($LASTEXITCODE -ne 0) { throw 'Use -PythonPath with a Python installation that includes tkinter.' }
    & $PythonPath -m venv $dashboardEnv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create packaging environment.' }
}
& $dashboardPython -m pip install -r tools/requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Packaging dependency installation failed.' }
$dashboardRuntimeOptions = @()
if ($RuntimeTemp) {
    $dashboardRuntimeOptions = @('--runtime-tmpdir', $RuntimeTemp)
}
& $dashboardPython -m PyInstaller --noconfirm --clean --onefile --noconsole @dashboardRuntimeOptions `
  --name ESP32TouchDashboard --add-data "$PSScriptRoot/tools/codex_prices.json;." `
  --paths tools --distpath $dashboardOutput --workpath (Join-Path $dashboardBuild 'packaging') `
  --specpath $dashboardBuild tools/desktop_dashboard.py
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
$dashboardExe = Join-Path $dashboardOutput 'ESP32TouchDashboard.exe'
$dashboardChecksum = Join-Path $dashboardOutput 'SHA256SUMS.txt'
$dashboardHash = (Get-FileHash -LiteralPath $dashboardExe -Algorithm SHA256).Hash.ToLowerInvariant()
"$dashboardHash  ESP32TouchDashboard.exe" | Set-Content -LiteralPath $dashboardChecksum -Encoding ascii
if ($PublishToRepository) {
    Copy-Item -LiteralPath $dashboardExe, $dashboardChecksum -Destination (Join-Path $PSScriptRoot 'dist') -Force
}
Write-Output "EXE: $dashboardExe"
