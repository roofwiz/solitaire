
@echo off
echo [STABLE BATTLE PRO] WORKING LAUNCHER 🏁
echo.
cd /d "%~dp0"

echo Launching Mario (P1)...
start "STABLE BATTLE - P1" py 2player_mario_pro_working.py

echo Waiting for stabilization...
timeout /t 10

echo Launching Luigi (P2)...
start "STABLE BATTLE - P2" py 2player_mario_pro_working.py

echo.
echo If Luigi fails to show, press [SPACE] in Mario's window.
echo.
pause
