@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Windows.ps1" -StartOnly -ResetDisplay
if errorlevel 1 echo Display recovery stopped. Read the error above and docs\GETTING-STARTED.md.
pause
