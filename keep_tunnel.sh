#!/bin/bash

# Load configuration from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found!"
    echo "Please create a .env file with REMOTE_USER and REMOTE_HOST variables."
    exit 1
fi

# Check required variables
if [ -z "$REMOTE_USER" ] || [ -z "$REMOTE_HOST" ]; then
    echo "Error: REMOTE_USER and REMOTE_HOST must be set in .env file!"
    echo "Example .env contents:"
    echo "REMOTE_USER=your_username"
    echo "REMOTE_HOST=your_host"
    exit 1
fi

# Port configuration
LOCAL_PORT=9100
REMOTE_PORT=9100

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting SSH tunnel monitor${NC}"
echo -e "Local port: ${GREEN}${LOCAL_PORT}${NC}"
echo -e "Remote port: ${GREEN}${REMOTE_PORT}${NC}"
echo -e "Remote host: ${GREEN}${REMOTE_HOST}${NC}"
echo -e "Remote user: ${GREEN}${REMOTE_USER}${NC}"

while true; do
    # Check if the tunnel is already running
    if ! nc -z localhost ${LOCAL_PORT} 2>/dev/null; then
        echo -e "\n${RED}Tunnel is down. Restarting...${NC}"
        
        # Start the SSH tunnel in the background
        ssh -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o StrictHostKeyChecking=accept-new \
            -R ${REMOTE_PORT}:127.0.0.1:${LOCAL_PORT} \
            ${REMOTE_USER}@${REMOTE_HOST} &
        
        # Store the SSH process ID
        SSH_PID=$!
        
        # Wait for tunnel to establish
        for i in {1..5}; do
            if nc -z localhost ${LOCAL_PORT} 2>/dev/null; then
                echo -e "${GREEN}Tunnel established successfully!${NC}"
                break
            fi
            echo -n "."
            sleep 1
        done
    else
        echo -n "."
    fi
    
    # Check every 5 seconds
    sleep 5
done 