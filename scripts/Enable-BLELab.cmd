@echo off
setlocal
title Q-Marauder - BLE Lab setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable-BLELab.ps1"
pause
