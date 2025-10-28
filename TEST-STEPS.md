# Pipeline Testing Steps - Simple Guide

**Follow these exact steps to test your pipeline**

---

## Prerequisites (Do Once)

### ✅ Step 0: Verify Redis is Running

Open a **PowerShell/CMD** window and run:

```bash
pixi run python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis Status:', r.ping())"
```

**Expected output:**
```
Redis Status: True
```

**If you get an error**, start Redis:
- Navigate to where you installed Redis (e.g., `C:\Tools\Redis`)
- Run: `redis-server.exe`
- Keep that window open
- Try the test command above again

---

## Testing Method: Automated (Recommended - Easiest)

### Step 1: Start All Services

Open a **PowerShell/CMD** window in your project directory:

```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
pixi run python scripts/start_all_services.py
```

**Wait for this message:**
```
================================================================================
All Services Started Successfully
================================================================================
MCP Server: http://localhost:8000
conversation_agent: http://localhost:3001
conversion_agent: http://localhost:3002
evaluation_agent: http://localhost:3003

System is ready!
You can now run: python scripts/run_full_demo.py

Press Ctrl+C to stop all services
```

⏱️ **This takes about 10-15 seconds**

**Keep this window open!** Leave the services running.

---

### Step 2: Run Tests

Open a **NEW PowerShell/CMD** window in the same directory:

```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
```

#### Test 2a: Check System Health

```bash
curl http://localhost:8000/health
```

**Expected output:**
```json
{"status":"healthy","version":"0.1.0","agents_registered":["conversation_agent","conversion_agent","evaluation_agent"],"redis_connected":true}
```

✅ If you see this, **the system is healthy!**

---

#### Test 2b: Initialize a Session

```bash
curl -X POST http://localhost:8000/api/v1/sessions/initialize -H "Content-Type: application/json" -d "{\"dataset_path\":\"./tests/data/synthetic_openephys\"}"
```

**Expected output (in ~4 seconds):**
```json
{
  "session_id": "some-uuid-here",
  "workflow_stage": "initialized",
  "message": "Session some-uuid-here initialized successfully. Starting metadata collection."
}
```

✅ **Success criteria:**
- Response comes back in **3-5 seconds**
- Status is `"initialized"`
- You get a `session_id`

❌ **If you get a timeout after 60+ seconds**, something is wrong with the commits.

---

#### Test 2c: Check Session Status

**Copy the `session_id` from the previous test**, then run:

```bash
curl http://localhost:8000/api/v1/sessions/YOUR-SESSION-ID-HERE/status
```

**Example** (replace with your actual session_id):
```bash
curl http://localhost:8000/api/v1/sessions/aee15737-27f4-4985-ae73-97b654fc6aae/status
```

**Expected output:**
```json
{
  "session_id": "YOUR-SESSION-ID",
  "workflow_stage": "collecting_metadata",
  "progress_percentage": 25,
  "status_message": "Collecting and extracting metadata from dataset.",
  "current_agent": "conversation_agent",
  "requires_clarification": false
}
```

✅ If you see this, **the pipeline is working!**

---

### Step 3: Stop Services

Go back to the **first window** where services are running.

Press: **`Ctrl+C`**

**Expected output:**
```
Stopping All Services
  Stopping mcp_server...
  mcp_server stopped
  Stopping conversation_agent...
  conversation_agent stopped
  ...
All services stopped
```

---

## Alternative: Manual Testing (More Visibility)

If you want to see logs from each service individually:

### Step 1: Open 5 Terminal Windows

Navigate to project directory in each:
```bash
cd C:\Users\shahh\Projects\agentic-neurodata-conversion-2
```

---

### Step 2: Start Services (One Per Window)

**Window 1 - MCP Server:**
```bash
pixi run uvicorn agentic_neurodata_conversion.mcp_server.main:app --host 0.0.0.0 --port 8000 --log-level info
```

Wait for: `INFO:     Uvicorn running on http://0.0.0.0:8000`

---

**Window 2 - Conversation Agent:**
```bash
pixi run python -m agentic_neurodata_conversion.agents conversation
```

Wait for: `Conversation agent ready - Listening on http://0.0.0.0:3001`

---

**Window 3 - Conversion Agent:**
```bash
pixi run python -m agentic_neurodata_conversion.agents conversion
```

Wait for: `Conversion agent ready - Listening on http://0.0.0.0:3002`

---

**Window 4 - Evaluation Agent:**
```bash
pixi run python -m agentic_neurodata_conversion.agents evaluation
```

Wait for: `Evaluation agent ready - Listening on http://0.0.0.0:3003`

---

**Window 5 - Testing:**

Now run the same tests as in the automated method:

```bash
# Health check
curl http://localhost:8000/health

# Initialize session
curl -X POST http://localhost:8000/api/v1/sessions/initialize -H "Content-Type: application/json" -d "{\"dataset_path\":\"./tests/data/synthetic_openephys\"}"

# Check status (replace SESSION_ID)
curl http://localhost:8000/api/v1/sessions/SESSION_ID/status
```

**Benefit:** You'll see detailed logs in each window showing what's happening!

---

### Step 3: Stop Services

Press **`Ctrl+C`** in each of the first 4 windows to stop each service.

---

## Expected Results Summary

| Test | Expected Time | Expected Result |
|------|--------------|-----------------|
| Health check | <1 second | `"status": "healthy"` |
| Session init | 3-5 seconds | `"workflow_stage": "initialized"` |
| Session status | <1 second | `"workflow_stage": "collecting_metadata"` |

---

## Troubleshooting

### Problem: `Connection refused`

**Solution:** Services aren't running. Go back to Step 1.

---

### Problem: `Redis connection error`

**Solution:** Redis isn't running.
```bash
# Start Redis
redis-server.exe
```

---

### Problem: `ReadTimeout` or timeout after 60 seconds

**Solution:** Commits may not be applied. Verify:
```bash
git log --oneline -2
```

Should show:
```
5cfd373 Add comprehensive timeout debugging and performance logging
a934897 Fix timeout issue by increasing MCP server timeout to 300s
```

If not, pull latest changes:
```bash
git pull origin heet-full-specs
```

---

### Problem: Port already in use

**Solution:** Kill existing Python processes:
```bash
taskkill /F /IM python.exe
```

Wait 5 seconds, then try again.

---

### Problem: Services start but tests fail

**Check:**
1. Is Redis running? Test with Step 0
2. Did all agents register? Check health endpoint shows 3 agents
3. Does test dataset exist? Check: `ls tests/data/synthetic_openephys`

---

## Quick Verification Commands

```bash
# Check if services are running
curl http://localhost:8000/health
curl http://localhost:3001/health
curl http://localhost:3002/health
curl http://localhost:3003/health

# Check if Redis is running
pixi run python -c "import redis; r = redis.Redis(); print(r.ping())"

# Check latest commits
git log --oneline -2

# Check test dataset exists
ls tests/data/synthetic_openephys
```

---

## Success Criteria Checklist

- [ ] Redis responds to ping
- [ ] All 4 services start without errors
- [ ] Health endpoint shows 3 agents registered
- [ ] Session initialization completes in 3-5 seconds (not timeout!)
- [ ] Session status shows "collecting_metadata"
- [ ] No `ReadTimeout` errors

**If all checked: ✅ Pipeline is working!**

---

## That's It!

**Recommended:** Use the **Automated Method** for quickest testing.

**For debugging:** Use the **Manual Method** to see detailed logs.

**Questions?** Check the full guides:
- Quick start: `QUICKSTART.md`
- Detailed guide: `docs/TESTING-GUIDE.md`
