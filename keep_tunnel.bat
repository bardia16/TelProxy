@echo off
setlocal EnableDelayedExpansion

:: Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please create a .env file with REMOTE_USER and REMOTE_HOST variables.
    echo Example .env contents:
    echo REMOTE_USER=your_username
    echo REMOTE_HOST=your_host
    pause
    exit /b 1
)

:: Read configuration from .env file
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

:: Port configuration
set LOCAL_PORT=9100
set REMOTE_PORT=9100

:: Colors for Windows console
set GREEN=[32m
set RED=[31m
set BLUE=[34m
set NC=[0m

title SSH Tunnel Monitor

echo %BLUE%Starting SSH tunnel monitor%NC%
echo Local port: %GREEN%%LOCAL_PORT%%NC%
echo Remote port: %GREEN%%REMOTE_PORT%%NC%
echo Remote host: %GREEN%%REMOTE_HOST%%NC%
echo Remote user: %GREEN%%REMOTE_USER%%NC%
echo.

:loop
:: Check if port is in use (indicates tunnel might be running)
netstat -an | find ":%LOCAL_PORT%" > nul
if errorlevel 1 (
    echo %RED%Tunnel is down. Restarting...%NC%
    
    :: Kill any existing SSH processes that might be stuck
    taskkill /F /IM ssh.exe > nul 2>&1
    
    :: Start SSH tunnel
    start /B ssh -o ServerAliveInterval=30 ^
              -o ServerAliveCountMax=3 ^
              -o ExitOnForwardFailure=yes ^
              -o StrictHostKeyChecking=accept-new ^
              -R %REMOTE_PORT%:127.0.0.1:%LOCAL_PORT% ^
              %REMOTE_USER%@%REMOTE_HOST%
    
    :: Wait a bit for tunnel to establish
    timeout /t 5 /nobreak > nul
    
    :: Check if tunnel is now up
    netstat -an | find ":%LOCAL_PORT%" > nul
    if errorlevel 1 (
        echo %RED%Failed to establish tunnel. Will retry...%NC%
    ) else (
        echo %GREEN%Tunnel established successfully!%NC%
    )
) else (
    :: Just output a dot to show we're still monitoring
    echo|set /p=".">nul
)

:: Wait before checking again
timeout /t 5 /nobreak > nul
goto loop 