param(
    [string]$AdbPath = (Join-Path $PSScriptRoot '..\.tools\platform-tools\adb.exe'),
    [ValidatePattern('^[A-Za-z0-9._:-]+$')][string]$Serial
)
$ErrorActionPreference = 'Stop'
$usbipd = Join-Path $env:ProgramFiles 'usbipd-win\usbipd.exe'
if (-not (Test-Path -LiteralPath $usbipd)) { throw 'Run Setup-AlfaWindows.cmd first.' }
if (-not (Test-Path -LiteralPath $AdbPath)) {
    if (Get-Command adb -ErrorAction SilentlyContinue) { $AdbPath = (Get-Command adb).Source }
    else { throw 'Install Google Platform-Tools; see docs/GETTING-STARTED.md.' }
}
if (-not $Serial) {
    $boards = @()
    foreach ($line in (& $AdbPath devices)) {
        if ($line -match '^([A-Za-z0-9._:-]+)\s+device$') {
            $candidate = $Matches[1]
            $model = & $AdbPath -s $candidate shell cat /proc/device-tree/model 2>$null
            if ($LASTEXITCODE -eq 0 -and "$model" -match 'Arduino.*Imola') { $boards += $candidate }
        }
    }
    if ($boards.Count -ne 1) { throw 'Connect exactly one initialized UNO Q or pass -Serial.' }
    $Serial = $boards[0]
}
$model = & $AdbPath -s $Serial shell cat /proc/device-tree/model
if ($LASTEXITCODE -ne 0 -or "$model" -notmatch 'Arduino.*Imola') { throw 'Selected device is not a UNO Q.' }
$state = (& $usbipd state | Out-String) | ConvertFrom-Json
$radios = @($state.Devices | Where-Object { $_.BusId -and $_.InstanceId -like 'USB\VID_0E8D&PID_7961\*' })
if ($radios.Count -ne 1 -or -not $radios[0].PersistedGuid) { throw 'Run Setup-AlfaWindows.cmd with exactly one Alfa attached first.' }
& $AdbPath -s $Serial reverse 'tcp:3240' 'tcp:3240'
if ($LASTEXITCODE -ne 0) { throw 'USB reverse tunnel failed.' }
& $AdbPath -s $Serial push (Join-Path $PSScriptRoot 'attach-usb-radio.py') '/home/arduino/q-marauder/scripts/'
if ($LASTEXITCODE -ne 0) { throw 'Install Q-Marauder before attaching the radio.' }
Write-Host 'Enter the Arduino Debian password if prompted. It stays on your computer; typing is invisible.'
& $AdbPath -s $Serial shell -t sudo python3 /home/arduino/q-marauder/scripts/attach-usb-radio.py $radios[0].BusId
if ($LASTEXITCODE -ne 0) { throw 'Radio attach failed. See docs/USB-RADIO.md.' }
Write-Host 'Keep this PC, the Alfa, and UNO Q connected. Re-run this launcher after reconnecting or rebooting.'
