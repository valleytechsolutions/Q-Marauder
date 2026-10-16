param(
    [string]$AdbPath,
    [ValidatePattern('^[A-Za-z0-9._:-]+$')][string]$Serial,
    [switch]$StartOnly,
    [switch]$ResetDisplay,
    [switch]$AppOnly,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($ResetDisplay -and -not $StartOnly) { throw '-ResetDisplay requires -StartOnly.' }
if (-not $AdbPath) {
    $bundled = Join-Path $root '.tools\platform-tools\adb.exe'
    if (Test-Path -LiteralPath $bundled) { $AdbPath = $bundled }
    elseif (Get-Command adb -ErrorAction SilentlyContinue) { $AdbPath = (Get-Command adb).Source }
    else {
        throw 'ADB is missing. Download Google Platform-Tools and extract platform-tools into .tools in this folder, or pass -AdbPath. See docs/GETTING-STARTED.md.'
    }
}
function Board {
    & $AdbPath -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "Board command failed (exit $LASTEXITCODE)." }
}
$connected = @(& $AdbPath devices)
if ($LASTEXITCODE -ne 0) { throw 'ADB could not start.' }
if (-not $Serial) {
    $boards = @()
    foreach ($line in $connected) {
        if ($line -match '^([A-Za-z0-9._:-]+)\s+device$') {
            $candidate = $Matches[1]
            $model = & $AdbPath -s $candidate shell cat /proc/device-tree/model 2>$null
            if ($LASTEXITCODE -eq 0 -and "$model" -match 'Arduino.*Imola') { $boards += $candidate }
        }
    }
    if ($boards.Count -ne 1) { throw 'Connect exactly one initialized UNO Q with a USB data cable, or pass -Serial. See docs/GETTING-STARTED.md.' }
    $Serial = $boards[0]
}
$model = Board shell cat /proc/device-tree/model
if ("$model" -notmatch 'Arduino.*Imola') { throw 'The selected USB device is not an Arduino UNO Q.' }
$who = Board shell id -un
if ("$who".Trim() -ne 'arduino') { throw 'This installer requires the standard arduino Linux account.' }
if ($StartOnly) {
    Board shell 'cd /home/arduino/q-marauder && python3 scripts/start.py'
    if ($ResetDisplay) {
        Board push (Join-Path $PSScriptRoot 'reset-display.sh') '/home/arduino/q-marauder/scripts/reset-display.sh'
        Board shell 'sh /home/arduino/q-marauder/scripts/reset-display.sh'
    }
} else {
    Write-Host 'Installing the Linux console. Your Debian image and saved surveys stay in place.'
    if (-not $AppOnly) {
        $core = Board shell 'arduino-cli core list'
        if ("$core" -notmatch 'arduino:zephyr\s+0\.11\.0-rc5(?:\s|$)') {
            throw 'Display upload supports factory Zephyr 0.11.0-rc5 only. Use -AppOnly for the console, or follow firmware/README.md. No firmware was flashed.'
        }
    }
    & (Join-Path $PSScriptRoot 'Deploy-UnoQ.ps1') -Serial $Serial -AdbPath $AdbPath
    if (-not $AppOnly) {
        Board shell 'mkdir -p /home/arduino/q-marauder/firmware'
        Board push (Join-Path $root 'firmware\uno_shield') '/home/arduino/q-marauder/firmware/'
        Write-Host 'Building and uploading the portrait TFT sketch. Keep USB connected.'
        Board shell 'cd /home/arduino/q-marauder && sh scripts/flash-display.sh'
    }
}
Board forward 'tcp:8788' 'tcp:8787'
Write-Host 'Ready: http://127.0.0.1:8788'
Write-Host 'Saved display settings restore through the console. If setup appears, select upright text and tap/release the three circles.'
Write-Host 'After a board reboot, double-click Start-QMarauder.cmd. Boot-service setup is optional; see docs/INSTALL.md.'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8788' }
