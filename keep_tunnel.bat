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

:cleanup_ports
:: Kill any processes using port 9100
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9100.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
:: Kill any existing SSH processes
taskkill /F /IM ssh.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:loop
:: Check both LISTENING and ESTABLISHED connections
set "TUNNEL_ACTIVE=0"
for /f "tokens=4" %%a in ('netstat -an ^| findstr ":9100.*ESTABLISHED"') do (
    set "TUNNEL_ACTIVE=1"
)

if "!TUNNEL_ACTIVE!"=="0" (
    echo [%date% %time%] Tunnel appears to be down. Cleaning up and restarting...
    goto cleanup_ports
    :: Start new tunnel
    %SSH_CMD%
    :: Give it time to establish
    timeout /t 10 /nobreak >nul
) else (
    echo|set /p="."
    timeout /t 5 /nobreak >nul
)
goto loop 