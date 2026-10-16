$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$adb = Join-Path $root '.tools\platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $adb)) { $adb = (Get-Command adb -ErrorAction Stop).Source }
$boards = @()
foreach ($line in @(& $adb devices)) {
    if ($line -match '^([A-Za-z0-9._:-]+)\s+device$') {
        $candidate = $Matches[1]
        $model = & $adb -s $candidate shell cat /proc/device-tree/model 2>$null
        if ($LASTEXITCODE -eq 0 -and "$model" -match 'Arduino.*Imola') { $boards += $candidate }
    }
}
if ($boards.Count -ne 1) { throw 'Connect exactly one initialized UNO Q.' }
$serial = $boards[0]
& $adb -s $serial push (Join-Path $PSScriptRoot 'install-ble-dependencies.sh') '/home/arduino/q-marauder/scripts/'
if ($LASTEXITCODE -ne 0) { throw 'Install Q-Marauder first, then retry BLE setup.' }
Write-Host 'Enter the Arduino Debian password when sudo asks. Typing stays invisible.'
& $adb -s $serial shell -t 'sh /home/arduino/q-marauder/scripts/install-ble-dependencies.sh'
if ($LASTEXITCODE -ne 0) { throw 'BLE dependency setup did not complete.' }
Write-Host 'Ready. Open Bluetooth in the Q-Marauder console.'
