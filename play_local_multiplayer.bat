
@echo off
echo [V92] MARIO BATTLE BO3 MASTER (CLICK & PLAY) 🏁💎🎵✨🚀
echo.
cd /d "%~dp0"

echo Launching Mario (P1)...
start "STABLE V92 - P1" py v92_mario_battle_pro.py

echo Waiting for Window 1...
timeout /t 6

echo Launching Luigi (P2)...
start "STABLE V92 - P2" py v92_mario_battle_pro.py

echo.
echo instructions:
echo - PICK PLAYER: Click the Red/Green buttons OR 1/2
echo - READY UP: [ENTER]
echo.
pause
