@echo off
setlocal
title Q-Marauder - Enable lab radio
set "QM_ADB=%~dp0..\.tools\platform-tools\adb.exe"
if not exist "%QM_ADB%" set "QM_ADB=adb.exe"
echo Choose BLE capture setup, or configure your own Wi-Fi lab profile.
echo The password prompt is for the Arduino's Debian account, not Windows.
echo Password characters will not appear while you type.
echo.
"%QM_ADB%" shell -t sh /home/arduino/q-marauder/scripts/setup-radio.sh
if errorlevel 1 (
  echo.
  echo Setup did not finish. Keep this window open and share the error, not your password.
) else (
  echo.
  echo Radio helper installed. Open Counter surveillance on the TFT or Detection modes in the browser Lab.
)
pause
