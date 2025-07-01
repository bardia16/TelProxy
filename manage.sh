#!/bin/bash

# Configuration
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PID_FILE="$APP_DIR/telproxy.pid"
LOG_FILE="$APP_DIR/telproxy.log"
PYTHON_MODULE="src.main"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if the process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null; then
            return 0 # Running
        else
            return 1 # Not running but PID file exists
        fi
    else
        return 2 # Not running
    fi
}

# Function to display usage
usage() {
    echo -e "${BLUE}Telegram Proxy Scraper Management Script${NC}"
    echo -e "Usage: $0 ${GREEN}command${NC}\n"
    echo -e "Commands:"
    echo -e "  ${GREEN}start${NC}    - Start the proxy scraper in the background"
    echo -e "  ${GREEN}stop${NC}     - Stop the running proxy scraper"
    echo -e "  ${GREEN}status${NC}   - Check if the proxy scraper is running"
    echo -e "  ${GREEN}restart${NC}  - Restart the proxy scraper"
    echo -e "  ${GREEN}logs${NC}     - Display the logs (use Ctrl+C to exit)"
    echo -e "  ${GREEN}once${NC}     - Run a single cycle and exit"
    echo -e "  ${GREEN}help${NC}     - Display this help message"
}

# Function to start the application
start_app() {
    echo -e "${BLUE}Starting Telegram Proxy Scraper...${NC}"
    
    # Check if already running
    is_running
    local status=$?
    
    if [ $status -eq 0 ]; then
        echo -e "${YELLOW}Telegram Proxy Scraper is already running with PID $(cat "$PID_FILE")${NC}"
        return 0
    fi
    
    # Activate virtual environment and start the application
    cd "$APP_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Start the application with nohup and redirect output to log file
    nohup python3 -u -m "$PYTHON_MODULE" schedule > "$LOG_FILE" 2>&1 &
    
    # Save the PID
    echo $! > "$PID_FILE"
    echo -e "${GREEN}Telegram Proxy Scraper started with PID $(cat "$PID_FILE")${NC}"
    echo -e "Logs are being written to ${BLUE}$LOG_FILE${NC}"
}

# Function to stop the application
stop_app() {
    echo -e "${BLUE}Stopping Telegram Proxy Scraper...${NC}"
    
    # Check if running
    is_running
    local status=$?
    
    if [ $status -eq 0 ]; then
        local pid=$(cat "$PID_FILE")
        kill -15 "$pid"  # Try graceful shutdown first
        sleep 2
        
        # Check if still running
        if ps -p "$pid" > /dev/null; then
            echo -e "${YELLOW}Process didn't terminate gracefully, forcing...${NC}"
            kill -9 "$pid"
        fi
        
        rm -f "$PID_FILE"
        echo -e "${GREEN}Telegram Proxy Scraper stopped${NC}"
    elif [ $status -eq 1 ]; then
        echo -e "${YELLOW}Telegram Proxy Scraper is not running but PID file exists. Cleaning up...${NC}"
        rm -f "$PID_FILE"
    else
        echo -e "${RED}Telegram Proxy Scraper is not running${NC}"
    fi
}

# Function to check status
check_status() {
    is_running
    local status=$?
    
    if [ $status -eq 0 ]; then
        local pid=$(cat "$PID_FILE")
        local uptime=$(ps -p "$pid" -o etime= | tr -d ' ')
        echo -e "${GREEN}Telegram Proxy Scraper is running with PID $pid (uptime: $uptime)${NC}"
        return 0
    elif [ $status -eq 1 ]; then
        echo -e "${YELLOW}Telegram Proxy Scraper is not running but PID file exists${NC}"
        return 1
    else
        echo -e "${RED}Telegram Proxy Scraper is not running${NC}"
        return 2
    fi
}

# Function to display logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}Showing logs (press Ctrl+C to exit):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}No log file found at $LOG_FILE${NC}"
    fi
}

# Function to run a single cycle
run_once() {
    echo -e "${BLUE}Running a single proxy extraction cycle...${NC}"
    cd "$APP_DIR"
    source "$VENV_DIR/bin/activate"
    python3 -u -m "$PYTHON_MODULE" once
}

# Main script logic
case "$1" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        stop_app
        sleep 2
        start_app
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    once)
        run_once
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac

exit 0 