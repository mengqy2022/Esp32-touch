param([ValidateRange(0, [long]::MaxValue)][long]$CodexDailyGoal = 0)
$ErrorActionPreference = 'Stop'
$dashboardInstalled = Join-Path $env:LOCALAPPDATA 'ESP32TouchDashboard/ESP32TouchDashboard.exe'
if (-not (Test-Path -LiteralPath $dashboardInstalled)) {
    $dashboardPackage = Join-Path $PSScriptRoot 'dist/ESP32TouchDashboard.exe'
    if (-not (Test-Path -LiteralPath $dashboardPackage)) { throw 'Build or download ESP32TouchDashboard.exe first.' }
    $dashboardInstall = Start-Process -FilePath $dashboardPackage -ArgumentList @('--install','--quiet') -WindowStyle Hidden -PassThru
    if (-not $dashboardInstall.WaitForExit(30000) -or $dashboardInstall.ExitCode -ne 0) { throw 'Dashboard installation failed.' }
}
$dashboardConfig = Join-Path $env:LOCALAPPDATA 'ESP32TouchDashboard/config.json'
$dashboardSettings = Get-Content -LiteralPath $dashboardConfig -Raw | ConvertFrom-Json
$dashboardSettings.daily_goal = $CodexDailyGoal
$dashboardSettings | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $dashboardConfig -Encoding UTF8
$dashboardStart = Start-Process -FilePath $dashboardInstalled -ArgumentList '--resume' -WindowStyle Hidden -PassThru
if (-not $dashboardStart.WaitForExit(30000) -or $dashboardStart.ExitCode -ne 0) { throw 'Could not resume dashboard.' }
Write-Output 'Dashboard resumed. It will detect the device automatically.'
