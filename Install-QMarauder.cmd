@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Windows.ps1"
if errorlevel 1 echo Installation stopped. Read the error above and docs\GETTING-STARTED.md.
pause
