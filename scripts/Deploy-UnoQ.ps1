param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._:-]+$')][string]$Serial,
    [string]$AdbPath = 'adb',
    [ValidateRange(1024,65535)][int]$LocalPort = 8788
)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
function Invoke-BoardAdb {
    & $AdbPath -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed with exit code $LASTEXITCODE" }
}
$state = & $AdbPath -s $Serial get-state
if ($LASTEXITCODE -ne 0 -or $state -ne 'device') { throw 'Select an authorized UNO Q from adb devices.' }
$model = & $AdbPath -s $Serial shell cat /proc/device-tree/model
if ($model -notmatch 'Arduino.*Imola') { throw "Unexpected board model: $model" }
Invoke-BoardAdb shell 'mkdir -p /home/arduino/q-marauder/scripts /home/arduino/q-marauder/licenses /home/arduino/q-marauder/packaging'
foreach ($name in @('qmarauder','scripts','licenses','packaging','LICENSE','THIRD_PARTY_NOTICES.md')) {
    Invoke-BoardAdb push (Join-Path $taskRoot $name) '/home/arduino/q-marauder/'
}
Invoke-BoardAdb shell 'cd /home/arduino/q-marauder && sh scripts/install.sh && python3 scripts/start.py'
Invoke-BoardAdb forward "tcp:$LocalPort" 'tcp:8787'
Write-Host "Open http://127.0.0.1:$LocalPort"
Write-Host 'Application installed. Existing running previews must be restarted to load updates. OS and MCU are not flashed.'
