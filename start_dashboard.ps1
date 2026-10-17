param([ValidateSet('codex', 'claude')][string]$AiSource)
$ErrorActionPreference = 'Stop'
$dashboardInstalled = Join-Path $env:LOCALAPPDATA 'ESP32TouchDashboard/ESP32TouchDashboard.exe'
if (-not (Test-Path -LiteralPath $dashboardInstalled)) {
    $dashboardPackage = Join-Path $PSScriptRoot 'dist/ESP32TouchDashboard.exe'
    if (-not (Test-Path -LiteralPath $dashboardPackage)) { throw 'Build or download ESP32TouchDashboard.exe first.' }
    $dashboardInstall = Start-Process -FilePath $dashboardPackage -ArgumentList @('--install','--quiet') -WindowStyle Hidden -PassThru
    if (-not $dashboardInstall.WaitForExit(30000) -or $dashboardInstall.ExitCode -ne 0) { throw 'Dashboard installation failed.' }
}
$dashboardStart = Start-Process -FilePath $dashboardInstalled -ArgumentList '--resume' -WindowStyle Hidden -PassThru
if (-not $dashboardStart.WaitForExit(30000) -or $dashboardStart.ExitCode -ne 0) { throw 'Could not resume dashboard.' }
if ($AiSource) {
    $dashboardSelect = Start-Process -FilePath $dashboardInstalled -ArgumentList @('--ai-source', $AiSource, '--quiet') -WindowStyle Hidden -PassThru
    if (-not $dashboardSelect.WaitForExit(30000) -or $dashboardSelect.ExitCode -ne 0) { throw 'Could not select device AI source.' }
}
Write-Output 'Dashboard resumed. It will detect the device automatically.'
