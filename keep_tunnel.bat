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

:: Check if curl is available
where curl >nul 2>&1
if !errorlevel! neq 0 (
    echo Warning: curl is not available. Remote port forwarding check will be disabled.
    set "CURL_AVAILABLE=0"
) else (
    set "CURL_AVAILABLE=1"
)

:: SSH tunnel command with connection persistence options
set "SSH_CMD=ssh -v -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes -o ConnectTimeout=30 -R localhost:9100:127.0.0.1:9100 %REMOTE_USER%@%REMOTE_HOST% -p 22"

echo Starting SSH tunnel monitor...
echo Command: %SSH_CMD%
echo.
echo Press Ctrl+C to stop the monitor
echo.

:cleanup_ports
echo [%date% %time%] Starting cleanup...

:: Show processes using port 9100
echo Current processes using port 9100:
netstat -ano | findstr ":9100"

:: Kill processes using port 9100
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9100"') do (
    echo Attempting to kill process with PID: %%a
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel! equ 0 (
        echo Successfully killed process %%a
    ) else (
        echo Failed to kill process %%a
    )
)

:: Kill any existing SSH processes
echo Killing any existing SSH processes...
taskkill /F /IM ssh.exe >nul 2>&1
if !errorlevel! equ 0 (
    echo Successfully killed SSH processes
) else (
    echo No SSH processes found
)

:: Double check if port is still in use
timeout /t 2 /nobreak >nul
netstat -ano | findstr ":9100" >nul
if !errorlevel! equ 0 (
    echo WARNING: Port 9100 is still in use after cleanup!
    echo Current port status:
    netstat -ano | findstr ":9100"
) else (
    echo Port 9100 is now free
)

:start_tunnel
echo [%date% %time%] Starting new tunnel...
start "" %SSH_CMD%

:: Progressive connection checks
echo Waiting for SSH process to start...
set "SSH_STARTED=0"
for /l %%i in (1,1,10) do (
    tasklist | findstr /i "ssh.exe" >nul
    if !errorlevel! equ 0 (
        set "SSH_STARTED=1"
        echo SSH process detected
        goto :wait_for_port
    )
    timeout /t 1 /nobreak >nul
)
if "!SSH_STARTED!"=="0" (
    echo Failed to start SSH process
    goto :cleanup_ports
)

:wait_for_port
echo Waiting for port to start listening...
set "PORT_LISTENING=0"
for /l %%i in (1,1,15) do (
    netstat -an | findstr ":9100.*LISTENING" >nul
    if !errorlevel! equ 0 (
        set "PORT_LISTENING=1"
        echo Port is now listening
        goto :wait_for_connection
    )
    timeout /t 1 /nobreak >nul
)
if "!PORT_LISTENING!"=="0" (
    echo Port failed to start listening
    goto :cleanup_ports
)

:wait_for_connection
echo Waiting for connection to establish...
set "CONNECTION_ESTABLISHED=0"
for /l %%i in (1,1,20) do (
    netstat -an | findstr ":9100.*ESTABLISHED" >nul
    if !errorlevel! equ 0 (
        set "CONNECTION_ESTABLISHED=1"
        echo Connection established
        goto :check_connection
    )
    timeout /t 1 /nobreak >nul
)
if "!CONNECTION_ESTABLISHED!"=="0" (
    echo Connection failed to establish
    goto :cleanup_ports
)

:check_connection
:: Function to check connection health
set "TUNNEL_HEALTHY=0"

:: 1. Check if SSH process exists
tasklist | findstr /i "ssh.exe" >nul
if !errorlevel! equ 0 (
    :: 2. Check if port is listening
    netstat -an | findstr ":9100.*LISTENING" >nul
    if !errorlevel! equ 0 (
        :: 3. Check if connection is established
        netstat -an | findstr ":9100.*ESTABLISHED" >nul
        if !errorlevel! equ 0 (
            :: 4. Check if remote port forwarding is working
            if "!CURL_AVAILABLE!"=="1" (
                :: Try to connect through SSH to the remote port
                :: First, establish a temporary SSH control socket
                set "CTRL_SOCKET=%TEMP%\ssh_ctrl_%RANDOM%"
                ssh -M -S "!CTRL_SOCKET!" -fnN %REMOTE_USER%@%REMOTE_HOST%
                
                :: Wait a bit for the control socket to be ready
                timeout /t 2 /nobreak >nul
                
                :: Use the control socket to check remote port
                ssh -S "!CTRL_SOCKET!" %REMOTE_USER%@%REMOTE_HOST% "curl -s -m 5 http://localhost:9100/health" >nul 2>&1
                if !errorlevel! equ 0 (
                    echo Remote port forwarding verified
                    set "TUNNEL_HEALTHY=1"
                ) else (
                    echo Remote port forwarding check failed
                )
                
                :: Clean up control socket
                ssh -S "!CTRL_SOCKET!" -O exit %REMOTE_USER%@%REMOTE_HOST% >nul 2>&1
                if exist "!CTRL_SOCKET!" del "!CTRL_SOCKET!"
            ) else (
                :: If curl isn't available, consider the connection healthy if we got this far
                set "TUNNEL_HEALTHY=1"
            )
        ) else (
            echo Connection not established
        )
    ) else (
        echo Port not listening
    )
) else (
    echo SSH process not found
)

:loop
call :check_connection

if "!TUNNEL_HEALTHY!"=="0" (
    echo [%date% %time%] Tunnel health check failed. Cleaning up and restarting...
    goto cleanup_ports
) else (
    echo|set /p="."
    timeout /t 5 /nobreak >nul
)
goto loop 