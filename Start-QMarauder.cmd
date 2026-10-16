@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Windows.ps1" -StartOnly
if errorlevel 1 echo Startup stopped. Read the error above and docs\GETTING-STARTED.md.
pause
