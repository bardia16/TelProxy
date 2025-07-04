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

# SSH tunnel command - modified to use localhost explicitly
SSH_CMD="ssh -v -R localhost:9100:127.0.0.1:9100 $REMOTE_USER@$REMOTE_HOST -p 22"

echo "Starting SSH tunnel monitor..."
echo "Command: $SSH_CMD"
echo
echo "Press Ctrl+C to stop the monitor"
echo

while true; do
    # Check if tunnel is running
    if ! netstat -an | grep -q ":9100"; then
        echo "Tunnel is down. Restarting..."
        # Kill any existing SSH processes
        pkill -f "ssh.*9100" > /dev/null 2>&1
        # Start new tunnel
        $SSH_CMD
        sleep 5
    else
        echo -n "."
        sleep 5
    fi
done 