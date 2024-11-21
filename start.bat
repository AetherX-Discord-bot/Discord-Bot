@echo off

:: Run other script
node other\note.js

:: Wait for 5 seconds
timeout /t 5

:loop
echo Starting bot...

:: Start bot in the background
start /b node bot.js
set BOT_PID=%ERRORLEVEL%

:: Get current time
for /f "tokens=1-4 delims=/: " %%a in ("%time%") do (
    set hour=%%a
    set minute=%%b
    set second=%%c
)

:: Calculate time until the next restart (12 PM or 12 AM)
set /a "now=%hour%*3600+%minute%*60+%second%"
set /a "next_noon=12*3600"
set /a "next_midnight=24*3600"

:: Determine the wait time
if %now% lss %next_noon% (
    set /a wait_seconds=%next_noon% - %now%
) else (
    set /a wait_seconds=%next_midnight% - %now%
)

:: Watch for bot process termination and override timer if necessary
:wait
tasklist | findstr /i "node.exe" >nul
if errorlevel 1 (
    echo Bot process ended. Restarting immediately.
    goto loop
)

:: If less than 20 seconds remain, start countdown
if %wait_seconds% leq 20 (
    echo Restart time is near! Countdown: 20 seconds remaining.
    for /L %%i in (20,-1,0) do (
        echo Restarting in %%i seconds...
        timeout /t 1 >nul
    )
    goto loop
)

:: Sleep until 20 seconds before restart time
timeout /t %wait_seconds% >nul
echo Restart time is near! Countdown: 20 seconds remaining.
for /L %%i in (20,-1,0) do (
    echo Restarting in %%i seconds...
    timeout /t 1 >nul
)

goto loop
