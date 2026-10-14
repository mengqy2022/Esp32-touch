param([string]$PythonPath = (Get-Command python -ErrorAction Stop).Source)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = ''
if (-not (Test-Path -LiteralPath '.packaging/Scripts/python.exe')) {
    & $PythonPath -m venv .packaging
    if ($LASTEXITCODE -ne 0) { throw 'Could not create packaging environment.' }
}
& ./.packaging/Scripts/python.exe -m pip install -r tools/requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Packaging dependency installation failed.' }
& ./.packaging/Scripts/python.exe -m PyInstaller --noconfirm --clean --onefile --noconsole `
  --name ESP32TouchDashboard --add-data "$PSScriptRoot/tools/codex_prices.json;." `
  --paths tools --workpath build/packaging --specpath build tools/desktop_dashboard.py
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
Write-Output "EXE: $PSScriptRoot/dist/ESP32TouchDashboard.exe"
