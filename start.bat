@echo off
node other/note.js
timeout /t 5 /nobreak
:loop
echo Starting bot...

REM Start bot without opening a new window
node bot.js

REM Calculate time until the next restart (12 PM or 12 AM)
for /f "tokens=2 delims==" %%A in ('powershell -command "$now = Get-Date; $nextRestart = if ($now.Hour -lt 12) { $now.Date.AddHours(12) } else { $now.Date.AddDays(1) }; $nextRestart = $nextRestart.AddHours($now.Hour -lt 12 ? 0 : -12); ($nextRestart - $now).TotalSeconds"') do set /A waitSeconds=%%A

REM Wait until the next restart time
timeout /t %waitSeconds% /nobreak >nul 2>&1

REM Restart loop without opening a new CMD window
goto loop