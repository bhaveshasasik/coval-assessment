#!/bin/bash

# Workflow Verification System - Shutdown Script
# Stops both backend and frontend services

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping Workflow Verification System...${NC}\n"

# Function to stop a service by PID file
stop_service() {
    local service_name=$1
    local pid_file=$2

    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping $service_name (PID: $PID)...${NC}"
            kill $PID 2>/dev/null
            sleep 2

            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID 2>/dev/null
            fi

            echo -e "${GREEN}✓ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠️  No PID file for $service_name${NC}"
    fi
}

# Stop services
stop_service "Backend" "logs/backend.pid"
stop_service "Frontend" "logs/frontend.pid"

# Also stop by port (backup method)
echo -e "\n${YELLOW}Checking for any remaining processes on ports...${NC}"

# Kill any process on port 8000 (backend)
BACKEND_PORT_PID=$(lsof -ti :8000 2>/dev/null)
if [ ! -z "$BACKEND_PORT_PID" ]; then
    echo -e "${YELLOW}Stopping process on port 8000...${NC}"
    kill -9 $BACKEND_PORT_PID 2>/dev/null
    echo -e "${GREEN}✓ Port 8000 freed${NC}"
fi

# Kill any process on port 3000 (frontend)
FRONTEND_PORT_PID=$(lsof -ti :3000 2>/dev/null)
if [ ! -z "$FRONTEND_PORT_PID" ]; then
    echo -e "${YELLOW}Stopping process on port 3000...${NC}"
    kill -9 $FRONTEND_PORT_PID 2>/dev/null
    echo -e "${GREEN}✓ Port 3000 freed${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ All services stopped!${NC}"
echo -e "${GREEN}========================================${NC}\n"
