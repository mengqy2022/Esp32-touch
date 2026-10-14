$ErrorActionPreference = 'Stop'
$dashboardRuntime = Join-Path $env:LOCALAPPDATA 'ESP32TouchDashboard'
if (Test-Path -LiteralPath (Join-Path $dashboardRuntime 'config.json')) {
    New-Item -ItemType File -Path (Join-Path $dashboardRuntime 'paused') -Force | Out-Null
    Write-Output 'Dashboard paused. The serial port will be released within a few seconds.'
}
# Also stop an older companion tool launched by this working copy.
$dashboardPidFile = Join-Path $PSScriptRoot 'build/dashboard-host.pid'
$dashboardScript = (Join-Path $PSScriptRoot 'tools/pc_monitor_host.py').Replace('/','\')
if (Test-Path -LiteralPath $dashboardPidFile) {
    $dashboardPid = [int](Get-Content -LiteralPath $dashboardPidFile -Raw)
    $dashboardProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
    if ($dashboardProcess -and $dashboardProcess.Name -like 'python*' -and
        $dashboardProcess.CommandLine.Replace('/','\').Contains($dashboardScript)) {
        Stop-Process -Id $dashboardPid
    }
    Remove-Item -LiteralPath $dashboardPidFile
}
