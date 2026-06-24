# Setup Guide

Quick setup for the Workflow Verification System.

---

## Quick Start (3 Steps)

### 1. Configure API Key
```bash
# Edit .env file (already exists)
# Add your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 2. Run
```bash
./start.sh
```

### 3. Access
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

**To stop:**
```bash
./stop.sh
```

---

## What `start.sh` Does

The startup script automatically handles:
- ✓ Validates `.env` file and API key
- ✓ Checks virtual environment exists
- ✓ Installs frontend dependencies if needed
- ✓ Starts backend on port 8000
- ✓ Waits for backend health check
- ✓ Starts frontend on port 3000
- ✓ Creates logs in `logs/` directory
- ✓ Displays access URLs

**View logs:**
```bash
tail -f logs/backend.log   # Backend logs
tail -f logs/frontend.log  # Frontend logs
```

---

## Troubleshooting

### "API key not configured" error
Edit `.env` file and add your key:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### "Virtual environment not found" error
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Port already in use
```bash
# Kill processes on ports 8000 or 3000
./stop.sh

# Or manually:
lsof -ti :8000 | xargs kill -9
lsof -ti :3000 | xargs kill -9
```

### Backend fails to start
Check logs for details:
```bash
tail -f logs/backend.log
```

### Frontend fails to start
Check logs or reinstall dependencies:
```bash
tail -f logs/frontend.log

# Or reinstall:
cd frontend
rm -rf node_modules
npm install
```

---

## Manual Setup (If Needed)

If `./start.sh` doesn't work, run manually:

```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Terminal 2 - Frontend  
cd frontend
npm run dev
```

---

## Development Commands

```bash
# Restart services
./stop.sh && ./start.sh

# View logs
tail -f logs/backend.log
tail -f logs/frontend.log

# Format code
ruff format .                    # Backend
cd frontend && npm run lint      # Frontend

# Type check
mypy src --ignore-missing-imports  # Backend
cd frontend && npx tsc --noEmit    # Frontend
```
