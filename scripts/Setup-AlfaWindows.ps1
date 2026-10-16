param([switch]$ShareOnly)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$usbipd = Join-Path $env:ProgramFiles 'usbipd-win\usbipd.exe'
if (-not (Test-Path -LiteralPath $usbipd)) {
    if ($ShareOnly) { throw 'usbipd is not installed.' }
    if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'This download helper supports x64 Windows only; install usbipd-win for your architecture manually.' }
    $cache = Join-Path $root '.tools\usbipd'
    New-Item -ItemType Directory -Force $cache | Out-Null
    $msi = Join-Path $cache 'usbipd-win_5.3.0_x64.msi'
    $expected = '1c984914aec944de19b64eff232421439629699f8138e3ddc29301175bc6d938'
    if (-not (Test-Path -LiteralPath $msi) -or (Get-FileHash -LiteralPath $msi).Hash -ne $expected) {
        Invoke-WebRequest -UseBasicParsing 'https://github.com/dorssel/usbipd-win/releases/download/v5.3.0/usbipd-win_5.3.0_x64.msi' -OutFile $msi
    }
    if ((Get-FileHash -LiteralPath $msi).Hash -ne $expected) { throw 'usbipd download checksum mismatch.' }
    if ((Get-AuthenticodeSignature -LiteralPath $msi).Status -ne 'Valid') { throw 'usbipd installer signature is not valid.' }
    $process = Start-Process msiexec.exe -Verb RunAs -WindowStyle Hidden -ArgumentList @('/i', ('"'+$msi+'"'), '/passive', '/norestart') -Wait -PassThru
    if ($process.ExitCode -notin @(0,3010)) { throw "usbipd installer returned $($process.ExitCode)." }
    if ($process.ExitCode -eq 3010) { throw 'Windows requires a restart. Restart, then run this helper again.' }
}
if (-not $ShareOnly) {
    $process = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File', ('"'+$PSCommandPath+'"'), '-ShareOnly') -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Sharing setup failed. See .local/usbip-setup.log.' }
    Write-Host 'Alfa shared. Continue with docs/USB-RADIO.md to prepare and attach it on the UNO Q.'
    exit 0
}
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'Sharing setup needs a Windows administrator.' }
New-Item -ItemType Directory -Force (Join-Path $root '.local') | Out-Null
Start-Transcript -Path (Join-Path $root '.local\usbip-setup.log') -Force
try {
    $state = (& $usbipd state | Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot query usbipd.' }
    $radios = @($state.Devices | Where-Object { $_.BusId -and $_.InstanceId -like 'USB\VID_0E8D&PID_7961\*' })
    if ($radios.Count -ne 1) { throw 'Connect exactly one 0e8d:7961 MediaTek Alfa adapter.' }
    # The local ADB tunnel does not need usbipd's installer-created LAN exception.
    Get-NetFirewallRule -DisplayName 'usbipd' -ErrorAction SilentlyContinue | Disable-NetFirewallRule
    & $usbipd bind --busid $radios[0].BusId
    if ($LASTEXITCODE -ne 0) { throw 'usbipd could not share the selected Alfa.' }
    Write-Host 'Only the selected Alfa is shared. Arduino USB and other adapters were not selected.'
} catch { Write-Output $_.Exception.Message; exit 1 }
finally { Stop-Transcript }
