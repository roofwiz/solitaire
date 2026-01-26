
@echo off
echo [DEBUG] Running Mario Tetris in THIS window...
py v22_root\main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The game crashed. Please COPY the error above and send it to me.
)
pause
