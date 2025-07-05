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

:: SSH tunnel command with connection persistence options
set "SSH_CMD=ssh -v -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes -o ConnectTimeout=30 -R localhost:9100:127.0.0.1:9100 %REMOTE_USER%@%REMOTE_HOST% -p 22"

echo Starting SSH tunnel monitor...
echo Command: %SSH_CMD%
echo.
echo Press Ctrl+C to stop the monitor
echo.

:loop
:: Check if tunnel is running
netstat -an | find ":9100" > nul
if errorlevel 1 (
    echo [%date% %time%] Tunnel is down. Restarting...
    :: Kill any existing SSH processes
    taskkill /F /IM ssh.exe > nul 2>&1
    :: Wait a moment for cleanup
    timeout /t 2 /nobreak > nul
    :: Start new tunnel
    %SSH_CMD%
    :: Give it time to establish
    timeout /t 10 /nobreak > nul
) else (
    echo|set /p="."
    timeout /t 5 /nobreak > nul
)
goto loop 