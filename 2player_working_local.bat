
echo [2-PLAYER LOCAL WORKING]
echo.
cd /d "%~dp0"

echo Launching Player 1...
start "MARIO P1" py 2player_working_local.py

echo Waiting 10 seconds for Player 2 slot to be safe...
timeout /t 10

echo Launching Player 2...
start "MARIO P2" py 2player_working_local.py

echo.
echo If window 2 still fails, press [SPACE] in window 1.
echo.
pause
