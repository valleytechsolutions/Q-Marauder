@echo off
setlocal
title Q-Marauder - Enable lab radio
set "QM_ADB=%~dp0..\.tools\platform-tools\adb.exe"
if not exist "%QM_ADB%" set "QM_ADB=adb.exe"
echo This enables the prepared lab radio profile on your Arduino UNO Q.
echo The password prompt is for the Arduino's Debian account, not Windows.
echo Password characters will not appear while you type.
echo.
"%QM_ADB%" shell -t sudo python3 /home/arduino/q-marauder/scripts/install-radio-helper.py --profile /home/arduino/.local/share/q-marauder/lab-profile.json
if errorlevel 1 (
  echo.
  echo Setup did not finish. Keep this window open and share the error, not your password.
) else (
  echo.
  echo Radio helper installed. Return to the chat so hardware tests can continue.
)
pause
