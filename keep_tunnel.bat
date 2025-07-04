@echo off
setlocal EnableDelayedExpansion

:: Check and load config from .env
if not exist .env (
    echo Error: .env file not found!
    echo Please create a .env file with REMOTE_USER and REMOTE_HOST variables.
    echo Example:
    echo REMOTE_USER=your_username
    echo REMOTE_HOST=your_host
    pause
    exit /b 1
)

:: Load config from .env
for /f "tokens=1,2 delims==" %%G in (.env) do (
    set "%%G=%%H"
)

:: Check required variables
if not defined REMOTE_USER (
    echo Error: REMOTE_USER must be set in .env file!
    pause
    exit /b 1
)
if not defined REMOTE_HOST (
    echo Error: REMOTE_HOST must be set in .env file!
    pause
    exit /b 1
)

:: SSH tunnel command
set "SSH_CMD=ssh -R 9100:127.0.0.1:9100 %REMOTE_USER%@%REMOTE_HOST% -p 22"

echo Starting SSH tunnel monitor...
echo Command: %SSH_CMD%
echo.
echo Press Ctrl+C to stop the monitor
echo.

:loop
:: Check if tunnel is running
netstat -an | find ":9100" > nul
if errorlevel 1 (
    echo Tunnel is down. Restarting...
    :: Kill any existing SSH processes
    taskkill /F /IM ssh.exe > nul 2>&1
    :: Start new tunnel
    %SSH_CMD%
    timeout /t 5 /nobreak > nul
) else (
    echo|set /p=".">nul
    timeout /t 5 /nobreak > nul
)
goto loop 