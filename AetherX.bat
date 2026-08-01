@echo off
title AetherX
cd /d "%~dp0"

:restart
echo [%time%] "Starting bot..."
python bot.py
set exit_code=%errorlevel%

if %exit_code% == 0 (
    echo [%time%] Bot exited with code 0. Waiting to see if it restarts itself...
    timeout /t 5 >nul

    rem
    tasklist /fi "imagename eq python.exe" /v | findstr /i "bot.py" >nul
    if %errorlevel%==0 (
        echo [%time%] "Bot is already running again. Not restarting."
        goto waitloop
    ) else (
        echo [%time%] "Bot not found. Restarting..."
    )
) else (
    echo [%time%] Crash detected (error %exit_code%) Restarting in 5 seconds.
    timeout /t 5 >nul
)

cls
goto restart

:waitloop
rem
timeout /t 10 >nul
tasklist /fi "imagename eq python.exe" /v | findstr /i "bot.py" >nul
if %errorlevel%==0 (
    goto waitloop
) else (
    echo [%time%] "Bot stopped. Restarting..."
    goto restart
)
