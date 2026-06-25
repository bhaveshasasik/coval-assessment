#!/bin/bash

# Workflow Verification System - Startup Script
# Runs both backend and frontend services

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Workflow Verification System${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create .env file with your ANTHROPIC_API_KEY${NC}"
    echo -e "Run: ${BLUE}cp .env.example .env${NC}"
    exit 1
fi

# Check if ANTHROPIC_API_KEY is set
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: ANTHROPIC_API_KEY may not be configured${NC}"
    echo -e "Please add your API key to .env file\n"
fi

# Check Node.js version
REQUIRED_NODE_VERSION="20.0.0"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    if [ "$(printf '%s\n' "$REQUIRED_NODE_VERSION" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_NODE_VERSION" ]; then
        echo -e "${RED}❌ Error: Node.js version $REQUIRED_NODE_VERSION or higher required${NC}"
        echo -e "${YELLOW}Current version: v$NODE_VERSION${NC}"
        echo -e "${YELLOW}Install Node.js from: https://nodejs.org/${NC}"
        echo -e "${YELLOW}Or use nvm: nvm install 18.18.0${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Error: Node.js is not installed${NC}"
    echo -e "${YELLOW}Install from: https://nodejs.org/${NC}"
    exit 1
fi

# Check if virtual environment exists, create if needed
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}\n"
fi

# Activate and install/update dependencies
source .venv/bin/activate
if [ ! -f ".venv/.dependencies_installed" ]; then
    echo -e "${YELLOW}⚠️  Installing backend dependencies...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    touch .venv/.dependencies_installed
    echo -e "${GREEN}✓ Backend dependencies installed${NC}\n"
fi

# Check if frontend node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}\n"
fi

# Create log directory
mkdir -p logs

echo -e "${GREEN}🚀 Starting services...${NC}\n"

# Start backend
echo -e "${BLUE}[Backend]${NC} Starting on http://localhost:8000"
source .venv/bin/activate
nohup uvicorn src.main:app --reload --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}\n"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start. Check logs/backend.log${NC}"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
done

# Start frontend
echo -e "${BLUE}[Frontend]${NC} Starting on http://localhost:3000"
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}\n"

# Wait for frontend to be ready
echo -e "${YELLOW}⏳ Waiting for frontend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is ready${NC}\n"
        break
    fi
    sleep 1
done

# Save PIDs for shutdown script
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ All services running!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}📍 Access Points:${NC}"
echo -e "  Frontend:    ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend API: ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs:    ${GREEN}http://localhost:8000/docs${NC}\n"

echo -e "${BLUE}📋 Logs:${NC}"
echo -e "  Backend:  ${YELLOW}tail -f logs/backend.log${NC}"
echo -e "  Frontend: ${YELLOW}tail -f logs/frontend.log${NC}\n"

echo -e "${BLUE}🛑 To stop:${NC}"
echo -e "  ${YELLOW}./stop.sh${NC}\n"

echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Trap Ctrl+C to clean up
trap "echo -e '\n${YELLOW}Stopping services...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f logs/*.pid; echo -e '${GREEN}✓ Services stopped${NC}'; exit 0" INT

# Keep script running
wait
