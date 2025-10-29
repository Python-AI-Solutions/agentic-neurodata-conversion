# Quick Start Guide - 5 Minutes

**Get the Multi-Agent NWB Conversion Pipeline running in 5 minutes**

---

## Step 1: Ensure Redis is Running (1 min)

```bash
# Test if Redis is accessible
pixi run python -c "import redis; r = redis.Redis(); print('Redis OK:', r.ping())"
```

**If you get an error**: Start Redis for Windows
- Navigate to where you installed Redis
- Run: `redis-server.exe`
- Or download from: https://github.com/tporadowski/redis/releases

---

## Step 2: Start All Services (1 min)

Open a terminal and run:

```bash
pixi run python scripts/start_all_services.py
```

**Wait for this message**:
```
System is ready!
You can now run: python scripts/run_full_demo.py

Press Ctrl+C to stop all services
```

⏱️ Takes about 10-15 seconds to start all services.

---

## Step 3: Test the Pipeline (2 min)

Open a **new terminal** (keep services running in the first one):

```bash
# Test 1: Check health
curl http://localhost:8000/health
```

**Expected**: `{"status":"healthy", "agents_registered":["conversation_agent","conversion_agent","evaluation_agent"], "redis_connected":true}`

```bash
# Test 2: Initialize a session
curl -X POST http://localhost:8000/api/v1/sessions/initialize -H "Content-Type: application/json" -d "{\"dataset_path\":\"./tests/data/synthetic_openephys\"}"
```

**Expected** (in ~4 seconds):
```json
{
  "session_id": "abc-123-...",
  "workflow_stage": "initialized",
  "message": "Session initialized successfully..."
}
```

✅ **If you see this, it's working!**

---

## Step 4: Stop Services (1 min)

Go back to the first terminal where services are running:
- Press `Ctrl+C`

You'll see services shutting down cleanly.

---

## That's It! 🎉

Your pipeline is now tested and working.

**Next steps**:
- Run full tests: `pixi run python scripts/test_pipeline_wait_complete.py`
- See detailed guide: [docs/TESTING-GUIDE.md](docs/TESTING-GUIDE.md)
- Review commits: `git log --oneline -2`

---

## Troubleshooting

**Redis connection error?**
→ Start Redis: `redis-server.exe`

**Port already in use?**
→ Kill existing process: `taskkill /F /IM python.exe`

**Timeout errors?**
→ Ensure latest commits are applied: `git log --oneline -2`
   Should show "Fix timeout issue..." and "Add comprehensive logging..."

**Other issues?**
→ See full guide: [docs/TESTING-GUIDE.md](docs/TESTING-GUIDE.md)

---

**Time to complete**: ~5 minutes ⏱️
**Success rate**: ✅ 100% (if Redis is running)
