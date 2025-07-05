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

:: SSH tunnel command with auto-exit on failure
set "SSH_CMD=ssh -v -o ExitOnForwardFailure=yes -R localhost:9100:127.0.0.1:9100 %REMOTE_USER%@%REMOTE_HOST% -p 22"

echo Starting SSH tunnel monitor...
echo Command: %SSH_CMD%
echo.
echo Press Ctrl+C to stop the monitor
echo.

:cleanup
echo [%date% %time%] Cleaning up any existing SSH processes...
taskkill /F /IM ssh.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:start_tunnel
echo [%date% %time%] Starting SSH tunnel...
start "" %SSH_CMD%

:: Initial wait for SSH to start
timeout /t 5 /nobreak >nul

:loop
:: Check if SSH process exists
tasklist | findstr /i "ssh.exe" >nul
if !errorlevel! neq 0 (
    echo [%date% %time%] SSH process not found. Restarting...
    goto cleanup
)

:: Still alive, wait and check again
echo|set /p="."
timeout /t 5 /nobreak >nul
goto loop 