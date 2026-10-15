param(
    [string]$AdbPath = (Join-Path $PSScriptRoot '..\.tools\platform-tools\adb.exe'),
    [ValidatePattern('^[A-Za-z0-9._:-]+$')][string]$Serial
)
# Read-only preflight. Does not install drivers, attach USB devices, or change networks.
$ErrorActionPreference = 'Stop'
$devices = @(Get-PnpDevice -PresentOnly | Where-Object {
    $_.InstanceId -like 'USB\VID_0E8D&PID_7961*'
} | ForEach-Object {
    [pscustomobject]@{ Name=$_.FriendlyName; Class=$_.Class; Status=$_.Status; HardwareId=($_.InstanceId -split '\\')[1] }
})
$report = [ordered]@{
    adapterFamily = 'MediaTek MT7921 USB (ALFA AXM/AXML family; verify model label)'
    adapterDetected = $devices.Count -gt 0
    devices = $devices
    usbipdInstalled = [bool](Get-Command usbipd -ErrorAction SilentlyContinue)
    administrator = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    board = $null
    note = 'A PC-connected adapter is not automatically available to the UNO Q. See docs/USB-RADIO.md.'
}
if (Test-Path -LiteralPath $AdbPath) {
    $boardArgs = @()
    if ($Serial) { $boardArgs += @('-s', $Serial) }
    $state = & $AdbPath @boardArgs get-state 2>$null
    if ($LASTEXITCODE -eq 0 -and $state -eq 'device') {
        $raw = & $AdbPath @boardArgs shell '/home/arduino/.local/bin/q-marauder doctor'
        if ($LASTEXITCODE -eq 0) {
            $diagnostics = ($raw -join "`n") | ConvertFrom-Json
            $report.board = @{kernel=$diagnostics.kernel; interfaces=$diagnostics.interfaces}
        }
    }
}
$report | ConvertTo-Json -Depth 6
