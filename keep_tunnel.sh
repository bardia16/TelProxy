#!/bin/bash

# Check and load config from .env
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with REMOTE_USER and REMOTE_HOST variables."
    echo "Example:"
    echo "REMOTE_USER=your_username"
    echo "REMOTE_HOST=your_host"
    exit 1
fi

# Load config from .env
source .env

# Check required variables
if [ -z "$REMOTE_USER" ]; then
    echo "Error: REMOTE_USER must be set in .env file!"
    exit 1
fi
if [ -z "$REMOTE_HOST" ]; then
    echo "Error: REMOTE_HOST must be set in .env file!"
    exit 1
fi

# Function to cleanup ports and processes
cleanup_ports() {
    echo "[$(date)] Starting cleanup..."
    
    # Show current processes using port 9100
    echo "Current processes using port 9100:"
    lsof -i:9100 || netstat -anp 2>/dev/null | grep ":9100"
    
    # Kill processes using port 9100
    if command -v lsof >/dev/null 2>&1; then
        PIDS=$(lsof -ti:9100)
        if [ ! -z "$PIDS" ]; then
            echo "Killing processes with PIDs: $PIDS"
            kill -9 $PIDS
        else
            echo "No processes found using lsof"
        fi
    else
        echo "Using fuser to kill processes..."
        fuser -k 9100/tcp >/dev/null 2>&1
    fi
    
    # Kill any existing SSH processes for this tunnel
    SSH_PIDS=$(ps aux | grep "ssh.*9100" | grep -v grep | awk '{print $2}')
    if [ ! -z "$SSH_PIDS" ]; then
        echo "Killing SSH processes with PIDs: $SSH_PIDS"
        kill -9 $SSH_PIDS >/dev/null 2>&1
    else
        echo "No SSH processes found"
    fi
    
    sleep 2
    
    # Verify port status
    if lsof -i:9100 >/dev/null 2>&1 || netstat -an | grep -q ":9100"; then
        echo "WARNING: Port 9100 is still in use after cleanup!"
        echo "Current port status:"
        lsof -i:9100 || netstat -an | grep ":9100"
    else
        echo "Port 9100 is now free"
    fi
}

# Function to start tunnel
start_tunnel() {
    echo "[$(date)] Starting new tunnel..."
    $SSH_CMD &
    
    # Wait for tunnel to establish
    echo "Waiting for tunnel to establish..."
    sleep 5
    
    # Check if tunnel started successfully
    if netstat -an | grep -q ":9100.*ESTABLISHED"; then
        echo "Tunnel established successfully"
    else
        echo "Failed to establish tunnel"
    fi
}

# SSH tunnel command with connection persistence options
SSH_CMD="ssh -v -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes -o ConnectTimeout=30 -R localhost:9100:127.0.0.1:9100 $REMOTE_USER@$REMOTE_HOST -p 22"

echo "Starting SSH tunnel monitor..."
echo "Command: $SSH_CMD"
echo
echo "Press Ctrl+C to stop the monitor"
echo

# Initial cleanup
cleanup_ports

while true; do
    # Check for ESTABLISHED connections
    if ! netstat -an | grep -q ":9100.*ESTABLISHED"; then
        echo "[$(date)] Tunnel appears to be down. Cleaning up and restarting..."
        cleanup_ports
        start_tunnel
    else
        echo -n "."
        sleep 5
    fi
done 