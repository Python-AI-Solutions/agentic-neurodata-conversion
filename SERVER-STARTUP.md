# 🚀 Server Startup Guide

## Quick Start (Recommended)

Use the startup script that automatically handles server management:

```bash
./start-backend.sh
```

This script will:
1. ✅ Kill any existing servers on port 8000
2. ✅ Reset the backend state
3. ✅ Start a fresh uvicorn server
4. ✅ Prevent multiple servers from running

---

## Manual Startup

If you prefer to start manually:

### 1. Kill Existing Servers (if any)

```bash
# Kill processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Or kill all Python uvicorn processes
pkill -9 -f "python.*uvicorn"
```

### 2. Start the Backend

```bash
cd backend/src
pixi run python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Verify Server is Running

```bash
curl http://localhost:8000/api/health
```

---

## Server Status

### Check if Server is Running

```bash
# Check process
ps aux | grep uvicorn

# Check port
lsof -i:8000

# Check health
curl http://localhost:8000/api/health | python -m json.tool
```

### Check Server State

```bash
curl http://localhost:8000/api/status | python -m json.tool
```

### Reset Server State

```bash
curl -X POST http://localhost:8000/api/reset
```

---

## Troubleshooting

### Problem: "Address already in use" Error

**Cause**: Another server is already running on port 8000

**Solution**:
```bash
# Kill the process and restart
lsof -ti:8000 | xargs kill -9
./start-backend.sh
```

### Problem: "Another conversion is in progress"

**Cause**: Server state is stuck from previous session

**Solution**:
```bash
# Reset the state
curl -X POST http://localhost:8000/api/reset

# Then refresh your browser
# Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

### Problem: Multiple Zombie Servers

**Cause**: Multiple uvicorn processes running simultaneously

**Solution**:
```bash
# Kill ALL Python uvicorn processes
pkill -9 -f "python.*uvicorn"

# Then use the startup script
./start-backend.sh
```

---

## Application URLs

| Component | URL |
|-----------|-----|
| **Frontend (Chat UI)** | http://localhost:3000/chat-ui.html |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/api/health |
| **Status Endpoint** | http://localhost:8000/api/status |

---

## Server PID Tracking

Current running server PID: **69510** (as of last startup)

To check: `ps aux | grep 69510`

To kill: `kill -9 69510`

---

## Best Practices

1. ✅ **Always use `./start-backend.sh`** to start the server
2. ✅ **Only run ONE server at a time**
3. ✅ **Reset state when switching sessions**: `curl -X POST http://localhost:8000/api/reset`
4. ✅ **Hard refresh browser after code changes**: `Cmd+Shift+R` or `Ctrl+Shift+R`
5. ✅ **Check server health before starting work**: `curl http://localhost:8000/api/health`

---

## Development Workflow

### Starting a New Session

```bash
# 1. Start the backend
./start-backend.sh

# 2. Open the frontend
open http://localhost:3000/chat-ui.html

# 3. Hard refresh browser
# Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

# 4. Click "+ New Conversion"
```

### After Making Code Changes

```bash
# Backend changes: uvicorn auto-reloads
# Just wait 1-2 seconds for the reload

# Frontend changes: hard refresh browser
# Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

---

## Environment Variables

Required in `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

The server automatically loads this file on startup (via `python-dotenv`).

---

## Notes

- **System Reminders**: Claude Code may show "stale" background bash process reminders even after killing servers. These are false positives - verify actual server status with `ps aux | grep uvicorn` or `lsof -i:8000`.

- **Port Conflicts**: If port 8000 is already in use by another application, you'll need to either kill that application or change the port in `start-backend.sh`.

- **Auto-reload**: The `--reload` flag makes uvicorn automatically restart when Python files change. This is helpful during development but should be disabled in production.
