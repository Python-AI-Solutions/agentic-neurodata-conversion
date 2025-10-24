# Diagnostic Methods for "Can't Send POST Requests" Issue

**Issue**: MCP server reports "All connection attempts failed" when trying to send messages to agents, even though agents are registered and responding to direct health checks.

---

## Method 1: Test Direct Agent Connectivity

**Purpose**: Verify agents are actually reachable via HTTP

### Test 1A: Health Check (GET)
```bash
# Test each agent's health endpoint
curl -v http://localhost:3001/health
curl -v http://localhost:3002/health
curl -v http://localhost:3003/health

# Expected: {"status":"healthy","agent_name":"conversation_agent",...}
```

### Test 1B: MCP Message Endpoint (POST)
```bash
# Test the actual endpoint MCP server uses
curl -v -X POST http://localhost:3001/mcp/message \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test-123",
    "source_agent": "mcp_server",
    "target_agent": "conversation_agent",
    "message_type": "agent_execute",
    "session_id": "test-session",
    "payload": {
      "action": "initialize_session",
      "dataset_path": "./tests/data/synthetic_openephys"
    },
    "timestamp": "2025-10-24T00:00:00"
  }'

# Expected: {"status":"success","result":{...}} or {"status":"error",...}
# If 404: endpoint doesn't exist
# If 500: agent error processing message
# If connection refused: agent not listening
```

**How to Run:**
```bash
# Run in separate terminal while orchestrator is running
pixi run python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            'http://localhost:3001/mcp/message',
            json={
                'message_id': 'test-123',
                'source_agent': 'mcp_server',
                'target_agent': 'conversation_agent',
                'message_type': 'agent_execute',
                'session_id': 'test-session',
                'payload': {
                    'action': 'initialize_session',
                    'dataset_path': './tests/data/synthetic_openephys'
                },
                'timestamp': '2025-10-24T00:00:00'
            }
        )
        print(f'Status: {response.status_code}')
        print(f'Response: {response.text}')

asyncio.run(test())
"
```

---

## Method 2: Check Agent Server Binding and Ports

**Purpose**: Verify agents are binding to correct addresses and ports are actually open

### Test 2A: Check Port Bindings
```bash
# Windows - Check what's actually listening on agent ports
netstat -ano | findstr ":3001"
netstat -ano | findstr ":3002"
netstat -ano | findstr ":3003"
netstat -ano | findstr ":8000"

# Expected output for each:
# TCP    0.0.0.0:3001    0.0.0.0:0    LISTENING    <PID>
# or
# TCP    127.0.0.1:3001  0.0.0.0:0    LISTENING    <PID>

# Check if it's 0.0.0.0 (all interfaces) or 127.0.0.1 (localhost only)
```

### Test 2B: Test Different Addresses
```bash
# If bound to 0.0.0.0, test all these should work:
curl http://localhost:3001/health
curl http://127.0.0.1:3001/health
curl http://0.0.0.0:3001/health

# If only one works, that's a binding issue
```

### Test 2C: Check Agent Startup Logs
```bash
# Look for uvicorn startup messages
# Should see: "Uvicorn running on http://0.0.0.0:3001"

# Check orchestrator output
pixi run python scripts/start_all_services.py
# Look for agent startup confirmation
```

---

## Method 3: Verify Agent Registration URLs

**Purpose**: Check if MCP server has correct URLs for agents

### Test 3A: Inspect Agent Registry
```python
# Add this to scripts/test_pipeline_with_running_services.py

# After checking health, add:
import httpx

async with httpx.AsyncClient() as client:
    # Try to get agent info from registry
    # (May need to add debug endpoint to mcp_server)
    response = await client.get("http://localhost:8000/internal/agents/conversation_agent")
    print(f"Agent registration info: {response.json()}")
```

### Test 3B: Check Registration Payload
```bash
# Read agent registration code in base_agent.py
# Verify registration data includes correct base_url

# Expected registration:
# {
#   "agent_name": "conversation_agent",
#   "agent_type": "conversation",
#   "base_url": "http://0.0.0.0:3001",  # <-- CHECK THIS
#   "capabilities": [...]
# }
```

### Test 3C: Test URL from Registry
```bash
# If base_url is http://0.0.0.0:3001, test if that works:
curl http://0.0.0.0:3001/health

# Windows might not like 0.0.0.0 in URLs
# Should be http://localhost:3001 or http://127.0.0.1:3001
```

**FIX**: If base_url has 0.0.0.0, change agent registration to use localhost:
```python
# In base_agent.py register_with_server():
registration_data = {
    "agent_name": self.agent_name,
    "agent_type": self.agent_type,
    "base_url": f"http://localhost:{self.config.agent_port}",  # NOT 0.0.0.0
    "capabilities": self.get_capabilities(),
}
```

---

## Method 4: Test MCP Server HTTP Client

**Purpose**: Verify MCP server's httpx client configuration

### Test 4A: Check Timeout Settings
```python
# In message_router.py __init__:
self.http_client = httpx.AsyncClient(timeout=60)

# Try shorter timeout to see if it's timing out:
self.http_client = httpx.AsyncClient(timeout=5.0)

# Or more verbose:
self.http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0, connect=2.0),
    follow_redirects=True,
    limits=httpx.Limits(max_connections=10)
)
```

### Test 4B: Add Debug Logging
```python
# In message_router.py send_message(), add before the POST:
print(f"[DEBUG] Sending to: {agent_info['base_url']}/mcp/message")
print(f"[DEBUG] Message: {message.model_dump()}")

# Then check MCP server logs
```

### Test 4C: Test with Raw Requests
```python
# Create standalone script to mimic what MCP server does:
import httpx
import asyncio

async def test_send():
    client = httpx.AsyncClient(timeout=30)

    url = "http://localhost:3001/mcp/message"
    payload = {
        "message_id": "test-456",
        "source_agent": "mcp_server",
        "target_agent": "conversation_agent",
        "message_type": "agent_execute",
        "session_id": "test",
        "payload": {"action": "initialize_session", "dataset_path": "."},
        "timestamp": "2025-10-24T00:00:00"
    }

    try:
        response = await client.post(url, json=payload)
        print(f"Success: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    await client.aclose()

asyncio.run(test_send())
```

---

## Method 5: Check Windows Firewall/Antivirus

**Purpose**: Verify no software is blocking local connections

### Test 5A: Temporarily Disable Windows Firewall
```powershell
# Run as Administrator
# Disable firewall temporarily
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Test if it works now
curl http://localhost:3001/health

# Re-enable firewall
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

### Test 5B: Check Antivirus Settings
- Check if antivirus (Windows Defender, Norton, McAfee, etc.) is blocking Python
- Add exception for Python or the project directory
- Temporarily disable antivirus and test

### Test 5C: Create Firewall Rule
```powershell
# Run as Administrator
# Allow inbound connections on agent ports
New-NetFirewallRule -DisplayName "NWB Pipeline Agents" `
  -Direction Inbound `
  -LocalPort 3001,3002,3003,8000 `
  -Protocol TCP `
  -Action Allow
```

---

## Method 6: Check Agent HTTP Endpoint Implementation

**Purpose**: Verify agent FastAPI app has /mcp/message endpoint

### Test 6A: Check base_agent.py create_agent_server()
```python
# Should have:
@app.post("/mcp/message")
async def handle_mcp_message(message: MCPMessage):
    result = await self.handle_message(message)
    return {"status": "success", "result": result}

# Verify this endpoint exists in all agents
```

### Test 6B: List All Agent Routes
```python
# Add to agent startup or create test script:
from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import get_conversation_agent_config

agent = ConversationAgent(get_conversation_agent_config())
app = agent.create_agent_server()

for route in app.routes:
    print(f"Route: {route.path} - Methods: {route.methods}")

# Should see: Route: /mcp/message - Methods: {'POST'}
```

---

## Method 7: Check Network Timing Issues

**Purpose**: Verify services are fully ready before being used

### Test 7A: Add Delays
```python
# In start_all_services.py, increase wait times:
def wait_for_agent(self, agent_name: str, max_wait: int = 60):  # Was 30
    # ...
    time.sleep(10)  # Add longer initial delay
```

### Test 7B: Use Health Check Endpoints
```python
# Verify agent is ACTUALLY responding before marking as ready:
async def wait_for_agent_ready(port: int, max_wait: int = 60):
    start = time.time()
    while time.time() - start < max_wait:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/health")
                if response.status_code == 200:
                    # Also test MCP endpoint
                    response = await client.post(
                        f"http://localhost:{port}/mcp/message",
                        json={"test": "ping"}
                    )
                    if response.status_code in [200, 422]:  # 422 = validation error is ok
                        return True
        except:
            pass
        await asyncio.sleep(2)
    return False
```

---

## Method 8: Check for Port Conflicts

**Purpose**: Verify no other services are using the ports

### Test 8A: Kill All Python and Retry
```bash
taskkill //F //IM python.exe
sleep 5
pixi run python scripts/start_all_services.py
```

### Test 8B: Use Different Ports
```bash
# In .env file:
MCP_SERVER_PORT=8001
CONVERSATION_AGENT_PORT=3101
CONVERSION_AGENT_PORT=3102
EVALUATION_AGENT_PORT=3103

# Test if different ports work
```

---

## Quick Diagnosis Script

Create `scripts/diagnose_connection.py`:

```python
"""Quick diagnostic for agent connectivity issues."""

import asyncio
import httpx
import sys


async def diagnose():
    """Run all diagnostic checks."""

    print("="*80)
    print("AGENT CONNECTIVITY DIAGNOSTICS")
    print("="*80 + "\n")

    agents = {
        "conversation_agent": 3001,
        "conversion_agent": 3002,
        "evaluation_agent": 3003,
    }

    results = {}

    async with httpx.AsyncClient(timeout=10) as client:
        for agent_name, port in agents.items():
            print(f"Testing {agent_name} (port {port})...")
            results[agent_name] = {}

            # Test 1: Health endpoint
            try:
                response = await client.get(f"http://localhost:{port}/health")
                results[agent_name]["health_localhost"] = response.status_code
                print(f"  [OK] Health (localhost): {response.status_code}")
            except Exception as e:
                results[agent_name]["health_localhost"] = str(e)
                print(f"  [ERROR] Health (localhost): {e}")

            # Test 2: Health via 127.0.0.1
            try:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                results[agent_name]["health_127"] = response.status_code
                print(f"  [OK] Health (127.0.0.1): {response.status_code}")
            except Exception as e:
                results[agent_name]["health_127"] = str(e)
                print(f"  [ERROR] Health (127.0.0.1): {e}")

            # Test 3: MCP message endpoint
            try:
                response = await client.post(
                    f"http://localhost:{port}/mcp/message",
                    json={
                        "message_id": "diag-test",
                        "source_agent": "diagnostic",
                        "target_agent": agent_name,
                        "message_type": "agent_execute",
                        "session_id": "test",
                        "payload": {"action": "test"},
                        "timestamp": "2025-01-01T00:00:00"
                    }
                )
                results[agent_name]["mcp_endpoint"] = response.status_code
                print(f"  [OK] MCP endpoint: {response.status_code}")
            except Exception as e:
                results[agent_name]["mcp_endpoint"] = str(e)
                print(f"  [ERROR] MCP endpoint: {e}")

            print()

    # Test MCP server
    print("Testing MCP Server (port 8000)...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("http://localhost:8000/health")
            print(f"  [OK] MCP Server health: {response.status_code}")
            print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"  [ERROR] MCP Server: {e}")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    all_ok = True
    for agent_name, tests in results.items():
        print(f"\n{agent_name}:")
        for test_name, result in tests.items():
            status = "[OK]" if isinstance(result, int) and result < 400 else "[FAIL]"
            print(f"  {status} {test_name}: {result}")
            if status == "[FAIL]":
                all_ok = False

    if all_ok:
        print("\n[SUCCESS] All agents are reachable!")
    else:
        print("\n[ERROR] Some agents are not reachable. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(diagnose())
```

**Run it:**
```bash
pixi run python scripts/diagnose_connection.py
```

---

## Most Likely Issue: Base URL Registration

**HYPOTHESIS**: Agents register with `base_url: "http://0.0.0.0:3001"` but Windows can't connect to 0.0.0.0.

**CHECK**: Look at [base_agent.py:80](agentic_neurodata_conversion/agents/base_agent.py#L80)
```python
registration_data = {
    "agent_name": self.agent_name,
    "agent_type": self.agent_type,
    "base_url": f"http://0.0.0.0:{self.config.agent_port}",  # <-- PROBLEM?
    "capabilities": self.get_capabilities(),
}
```

**FIX**:
```python
"base_url": f"http://localhost:{self.config.agent_port}",  # Use localhost
```

This is the #1 most likely issue!
