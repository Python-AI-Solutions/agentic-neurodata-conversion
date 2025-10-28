# Pipeline Testing Guide

**Complete step-by-step guide to test the Multi-Agent NWB Conversion Pipeline**

---

## Prerequisites

### 1. Verify Redis is Running

```bash
# Test Redis connectivity
pixi run python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis Status:', r.ping())"
```

**Expected output**:
```
Redis Status: True
```

**If Redis is not running**:
- You need Redis for Windows running on `localhost:6379`
- Start `redis-server.exe` from wherever you installed it
- Or download from: https://github.com/tporadowski/redis/releases

### 2. Verify Test Dataset Exists

```bash
# Check if test dataset exists
ls tests/data/synthetic_openephys
```

**Expected**: Should show dataset files (settings.xml, .continuous files, etc.)

### 3. Verify Environment Variables (Optional)

```bash
# Check if .env file exists with API keys
cat .env
```

**Should contain** (if using LLM features):
```
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-...
```

---

## Testing Method 1: Automated Script (Easiest)

### Step 1: Start All Services

```bash
pixi run python scripts/start_all_services.py
```

**What you'll see**:
```
================================================================================
Multi-Agent NWB Conversion Pipeline - Service Orchestrator
================================================================================

[CHECK] Checking prerequisites...
  ✓ Python: 3.x.x
  ✓ Redis: Connected
  ✓ Ports available: 8000, 3001, 3002, 3003

[STEP] Starting MCP Server
  ✓ MCP Server started (PID: xxxxx)
  ✓ MCP Server is ready

[STEP] Starting conversation_agent
  ✓ conversation_agent started (PID: xxxxx)
  ✓ conversation_agent is ready

[STEP] Starting conversion_agent
  ✓ conversion_agent started (PID: xxxxx)
  ✓ conversion_agent is ready

[STEP] Starting evaluation_agent
  ✓ evaluation_agent started (PID: xxxxx)
  ✓ evaluation_agent is ready

System is ready!
You can now run: python scripts/run_full_demo.py

Press Ctrl+C to stop all services
```

**Let it run** - Keep this window open!

### Step 2: Run Tests (In New Terminal)

Open a **new terminal window** and run:

```bash
# Navigate to project directory
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2

# Test 1: Check system health
curl http://localhost:8000/health

# Test 2: Initialize a session
curl -X POST http://localhost:8000/api/v1/sessions/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_path":"./tests/data/synthetic_openephys"}'

# Test 3: Check session status (replace SESSION_ID with ID from above)
curl http://localhost:8000/api/v1/sessions/SESSION_ID/status
```

### Step 3: Stop Services

In the first terminal window where services are running:
- Press `Ctrl+C`

**You'll see**:
```
[STEP] Stopping All Services
  Stopping mcp_server...
  ✓ mcp_server stopped
  Stopping conversation_agent...
  ✓ conversation_agent stopped
  ...
```

---

## Testing Method 2: Manual (More Control)

This method gives you more visibility into each service's logs.

### Step 1: Start Services Manually

**Terminal 1 - MCP Server**:
```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
pixi run uvicorn agentic_neurodata_conversion.mcp_server.main:app --host 0.0.0.0 --port 8000 --log-level info
```

Wait until you see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 - Conversation Agent**:
```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
pixi run python -m agentic_neurodata_conversion.agents conversation
```

Wait until you see:
```
Conversation agent ready
  - Listening on http://0.0.0.0:3001
```

**Terminal 3 - Conversion Agent**:
```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
pixi run python -m agentic_neurodata_conversion.agents conversion
```

Wait until you see:
```
Conversion agent ready
  - Listening on http://0.0.0.0:3002
```

**Terminal 4 - Evaluation Agent**:
```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
pixi run python -m agentic_neurodata_conversion.agents evaluation
```

Wait until you see:
```
Evaluation agent ready
  - Listening on http://0.0.0.0:3003
```

### Step 2: Verify All Services Are Healthy

**Terminal 5 - Testing Terminal**:
```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2

# Check health
curl http://localhost:8000/health
```

**Expected output**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "agents_registered": [
    "conversation_agent",
    "conversion_agent",
    "evaluation_agent"
  ],
  "redis_connected": true
}
```

### Step 3: Test Session Initialization

```bash
# Initialize a new session
curl -X POST http://localhost:8000/api/v1/sessions/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_path":"./tests/data/synthetic_openephys"}' \
  -w "\n\nTime: %{time_total}s\nStatus: %{http_code}\n"
```

**Expected output** (~4 seconds):
```json
{
  "session_id": "abc123...",
  "workflow_stage": "initialized",
  "message": "Session abc123... initialized successfully. Starting metadata collection."
}

Time: 3.96s
Status: 200
```

**Watch the service terminals!** You'll see:
- **Terminal 1 (MCP)**: Session initialization requests
- **Terminal 2 (Conversation Agent)**: MCP message processing
- All with our enhanced logging showing timing!

### Step 4: Check Session Status

```bash
# Replace SESSION_ID with the ID from step 3
curl http://localhost:8000/api/v1/sessions/SESSION_ID/status
```

**Expected output**:
```json
{
  "session_id": "SESSION_ID",
  "workflow_stage": "collecting_metadata",
  "progress_percentage": 25,
  "status_message": "Collecting and extracting metadata from dataset.",
  "current_agent": "conversation_agent",
  "requires_clarification": false
}
```

### Step 5: Stop Services

In each terminal (1-4), press `Ctrl+C` to stop the service.

---

## Testing Method 3: Quick Health Check Only

If you just want to verify everything is working:

```bash
# Start all services (in background)
pixi run python scripts/start_all_services.py &

# Wait 30 seconds for startup
sleep 30

# Quick health check
curl http://localhost:8000/health

# Quick session test
curl -X POST http://localhost:8000/api/v1/sessions/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_path":"./tests/data/synthetic_openephys"}'

# Stop services (find and kill the process)
pkill -f start_all_services
```

---

## Expected Performance Metrics

### ✅ Success Criteria

| Metric | Expected | Status |
|--------|----------|--------|
| Redis connection | <1s | ✅ |
| MCP server startup | <5s | ✅ |
| Agent registration | <3s each | ✅ |
| Health check response | <100ms | ✅ |
| Session initialization | 3-5s | ✅ |
| LLM metadata extraction | 2-60s | ✅ |
| No timeout errors | 0 errors | ✅ |

### 🔍 What to Watch For

**Good signs**:
- Services start without errors
- All 3 agents register successfully
- Health endpoint returns `"status": "healthy"`
- Session initialization completes in ~4s
- No `ReadTimeout` errors

**Problems to investigate**:
- `Connection refused` → Service not started
- `ReadTimeout` → Check timeout fixes are committed
- `500 Internal Server Error` → Check service logs
- `redis.exceptions.ConnectionError` → Redis not running

---

## Debugging Failed Tests

### Problem: Services won't start

**Solution**:
```bash
# Check if ports are already in use
netstat -ano | findstr :8000
netstat -ano | findstr :3001
netstat -ano | findstr :3002
netstat -ano | findstr :3003

# Kill processes using those ports if needed
taskkill /PID <PID> /F
```

### Problem: Redis connection refused

**Solution**:
```bash
# Start Redis for Windows
# Navigate to where you installed Redis and run:
redis-server.exe

# Or in another terminal:
cd C:\Tools\Redis  # or wherever you installed it
.\redis-server.exe
```

### Problem: Session initialization timeout

**Check**:
1. Are all commits applied? Run: `git log --oneline -2`
   - Should show: "Add comprehensive timeout debugging..." and "Fix timeout issue..."
2. Is the MCP server using the new timeout? Check `main.py:75`
   - Should have: `timeout=300`

### Problem: LLM errors (if using LLM features)

**Check**:
```bash
# Verify API key is set
cat .env | grep API_KEY

# Test API key manually
pixi run python -c "from anthropic import Anthropic; client = Anthropic(); print('API key valid')"
```

---

## Advanced Testing

### Run the Full Pipeline Test

```bash
# Ensure services are running, then:
pixi run python scripts/test_pipeline_wait_complete.py
```

This will:
1. Check health
2. Initialize session
3. Poll for completion (up to 10 minutes)
4. Display final results

### Check Logs with Enhanced Logging

If you want to see our detailed timing logs:

```bash
# The logs appear in the service terminal windows
# Look for messages like:
# - "MessageRouter initialized with timeout=300s"
# - "[initialize_session] Validating dataset path..."
# - "[conversation_agent] Calling LLM for metadata extraction..."
# - "LLM call completed in X.XXs"
```

### Test Redis Performance Independently

```bash
pixi run python scripts/debug_session_context.py
```

**Expected output**:
```
================================================================================
SESSION CONTEXT PERFORMANCE TEST
================================================================================

[1/4] Initializing ContextManager...
  [OK] Connected in 0.01s

[2/4] Creating test dataset info...
  [OK] Dataset info created: openephys, 10 files

[3/4] Creating session context in Redis...
  [OK] Session created in 0.00s

[4/4] Retrieving session context from Redis...
  [OK] Session retrieved in 0.00s

TEST COMPLETED SUCCESSFULLY
```

---

## Sample Test Session

Here's a complete test session from start to finish:

```bash
# 1. Start Redis (if not already running)
redis-server.exe &

# 2. Start all services
pixi run python scripts/start_all_services.py &

# 3. Wait for startup
sleep 30

# 4. Test health
curl http://localhost:8000/health
# ✅ {"status":"healthy"...}

# 5. Initialize session
curl -X POST http://localhost:8000/api/v1/sessions/initialize \
  -H "Content-Type: application/json" \
  -d '{"dataset_path":"./tests/data/synthetic_openephys"}'
# ✅ {"session_id":"abc123...","workflow_stage":"initialized"...}
# ✅ Completed in ~4 seconds

# 6. Check status
curl http://localhost:8000/api/v1/sessions/abc123.../status
# ✅ {"workflow_stage":"collecting_metadata","progress_percentage":25...}

# 7. Cleanup
# Press Ctrl+C in the start_all_services terminal
```

**Result**: ✅ All tests passed! Pipeline working perfectly!

---

## Quick Reference

### Service Ports
- MCP Server: http://localhost:8000
- Conversation Agent: http://localhost:3001
- Conversion Agent: http://localhost:3002
- Evaluation Agent: http://localhost:3003
- Redis: localhost:6379

### Key Endpoints
- Health: `GET /health`
- Initialize Session: `POST /api/v1/sessions/initialize`
- Session Status: `GET /api/v1/sessions/{session_id}/status`
- Session Result: `GET /api/v1/sessions/{session_id}/result`

### Test Dataset
- Path: `./tests/data/synthetic_openephys`
- Format: OpenEphys
- Contains: settings.xml, .continuous files, README.md

---

## Troubleshooting Quick Checklist

- [ ] Redis is running and accessible on localhost:6379
- [ ] All ports are available (8000, 3001, 3002, 3003)
- [ ] Latest commits are applied (timeout fix + logging)
- [ ] Test dataset exists at `./tests/data/synthetic_openephys`
- [ ] Environment variables set (if using LLM features)
- [ ] No firewall blocking localhost connections

---

**You're ready to test!** Start with **Method 1** (automated script) for the easiest experience, or use **Method 2** (manual) if you want to see detailed logs. 🚀
