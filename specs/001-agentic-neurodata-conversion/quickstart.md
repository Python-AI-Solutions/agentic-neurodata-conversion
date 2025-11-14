# Quick Start Guide: Agentic Neurodata Conversion System

**Audience**: Developers
**Time to Complete**: ~10 minutes
**Prerequisites**: macOS or Linux, basic Python/JavaScript knowledge

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Environment Setup](#environment-setup)
4. [Running the System](#running-the-system)
5. [Development Workflow](#development-workflow)
6. [Running Tests](#running-tests)
7. [Architecture Overview](#architecture-overview)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Required Software
- **Python**: 3.13 or higher
- **Pixi**: Python environment manager ([install](https://pixi.sh))
- **Git**: For version control
- **Web Browser**: Modern browser with JavaScript enabled (for frontend UI)

### Recommended Hardware
- **RAM**: 8 GB minimum (16 GB for large conversions)
- **Disk**: 10 GB free space (for uploads/outputs)
- **CPU**: Multi-core recommended (conversion is CPU-intensive)

### Operating System
- **macOS**: 12+ (Monterey or later)
- **Linux**: Ubuntu 20.04+ or equivalent
- **Windows**: Not supported in MVP (use WSL2)

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion
```

### Step 2: Install Pixi

**macOS/Linux**:
```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

**Verify installation**:
```bash
pixi --version
```

### Step 3: Install Dependencies

**Backend**:
```bash
# Pixi reads pixi.toml and installs all dependencies
pixi install
```

**Frontend**:
```bash
cd frontend
npm install
cd ..
```

---

## Environment Setup

### Step 1: Create `.env` File

Create `.env` in project root:

```bash
# Required: Anthropic Claude API key
ANTHROPIC_API_KEY=sk-ant-...  # Get from https://console.anthropic.com

# Optional: Customize paths
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
LOG_DIR=./logs

# Optional: Limits
MAX_UPLOAD_SIZE_GB=100
```

**Get your Anthropic API key**:
1. Visit [Anthropic Console](https://console.anthropic.com)
2. Create account or log in
3. Generate API key from Settings
4. Copy key to `.env` file

### Step 2: Create Required Directories

```bash
mkdir -p uploads outputs logs
```

### Step 3: Verify Environment

```bash
# Activate Pixi environment
pixi shell

# Verify Python packages
python -c "import neuroconv, pynwb, nwbinspector, fastapi, anthropic, pydantic; print('✅ All packages installed')"

# Exit Pixi shell
exit
```

---

## Running the System

### Option A: Run Everything (Recommended for First Time)

**Terminal 1** - Start Backend:
```bash
pixi shell
cd backend
python src/api/main.py
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080
```

**Terminal 2** - Start Frontend:
```bash
cd frontend
npm start
```

Expected output:
```
Compiled successfully!

You can now view the app in the browser.

  Local:            http://localhost:3000
```

**Open Browser**: Navigate to [http://localhost:3000](http://localhost:3000)

### Option B: Backend Only (API Development)

```bash
pixi run dev-backend
```

Test API:
```bash
curl http://localhost:8080/health
# Expected: {"status":"healthy","timestamp":"..."}
```

### Option C: Frontend Only (UI Development)

```bash
# Start frontend with mock backend
cd frontend
npm run start:mock
```

---

## Development Workflow

### Agent Development

Agents are independent modules in `backend/src/agents/`:

**Example: Modify Conversation Agent**

1. Open `backend/src/agents/conversation_agent.py`
2. Make changes (all agents use MCP for communication)
3. Restart backend
4. Test via API or UI

**Key Principle** (Constitution): No direct imports between agents!

```python
# ❌ WRONG: Direct import
from agents.conversion_agent import ConversionAgent

# ✅ CORRECT: Use MCP server
mcp_server.send_message(MCPMessage(
    target_agent="conversion_agent",
    action="convert_file",
    context={...}
))
```

### Adding New MCP Actions

**Example: Add new action to Conversion Agent**

1. Define handler in `backend/src/agents/conversion_agent.py`:
   ```python
   def handle_my_new_action(self, message: MCPMessage) -> Dict[str, Any]:
       # Implementation
       return {"result": "success"}
   ```

2. Register action in agent's `actions` dict:
   ```python
   self.actions = {
       "convert_file": self.handle_convert_file,
       "my_new_action": self.handle_my_new_action,  # New!
   }
   ```

3. Update `contracts/mcp-messages.json` with new action

4. Call from other agents:
   ```python
   response = mcp_server.send_message(MCPMessage(
       target_agent="conversion_agent",
       action="my_new_action",
       context={"param": "value"}
   ))
   ```

### Frontend Development

**MVP Implementation**: Static HTML in `frontend/public/chat-ui.html`

**Example: Modify Upload Form**

1. Open `frontend/public/chat-ui.html`
2. Make changes to HTML structure, CSS styles, or JavaScript
3. Refresh browser to see changes

**API Integration**:
```javascript
// Native fetch API for backend communication
const formData = new FormData();
formData.append('file', file);

const response = await fetch('http://localhost:8000/api/upload', {
    method: 'POST',
    body: formData
});
```

**Note**: Original plan called for React + TypeScript architecture. Static HTML was chosen for MVP speed. See [plan.md](plan.md#phase-8-frontend-ui) for migration considerations.

---

## Running Tests

### Backend Tests

**Unit Tests** (fast):
```bash
pixi run test-unit

# Specific agent
pixi run test-unit backend/tests/unit/test_conversation_agent.py
```

**Integration Tests** (slower, uses toy dataset):
```bash
pixi run test-integration

# Specific test
pixi run test-integration backend/tests/integration/test_end_to_end.py
```

**Coverage Report**:
```bash
pixi run test-coverage
# Opens HTML report in browser
```

**Target**: ≥80% code coverage (constitution requirement)

### Frontend Tests

```bash
cd frontend
npm test

# Coverage
npm run test:coverage
```

### Test Data

**Toy Dataset**: `backend/tests/fixtures/toy_spikeglx/`
- Size: ~5 MB
- Format: Synthetic SpikeGLX
- Purpose: Fast integration tests (<10 min requirement)
- See: Research Decision 7

**Generate New Test Data**:
```bash
python backend/tests/fixtures/generate_toy_dataset.py
```

---

## Architecture Overview

### Three-Agent System

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Conversation │◄──►│  Conversion  │◄──►│  Evaluation  │
│    Agent     │    │    Agent     │    │    Agent     │
└──────┬───────┘    └──────────────┘    └──────────────┘
       │
       │ All communication via MCP Server
       │
       ▼
┌─────────────────────────────────────────────┐
│         MCP Server (Message Routing)        │
│    - Agent registry                         │
│    - JSON-RPC 2.0 messages                  │
│    - Global state context injection         │
└─────────────────────────────────────────────┘
```

**Agent Responsibilities**:
- **Conversation Agent**: User interaction, retry approval, correction orchestration
- **Conversion Agent**: Format detection, NeuroConv execution, file versioning
- **Evaluation Agent**: NWB Inspector validation, report generation

**Key Files**:
- `backend/src/mcp/server.py` - MCP server implementation
- `backend/src/models/global_state.py` - Single session state
- `backend/src/api/main.py` - FastAPI REST API

### Data Flow

1. User uploads files via UI → **API**
2. API → **Conversation Agent** validates metadata
3. Conversation Agent → **Conversion Agent** converts to NWB
4. Conversion Agent → **Evaluation Agent** validates NWB
5. Evaluation Agent → **Conversation Agent** reports results
6. Conversation Agent → **User** (WebSocket updates + download links)

If validation fails/has warnings:
7. User approves retry → **Conversation Agent**
8. Conversation Agent → **Conversion Agent** applies corrections
9. Loop back to step 4

### File Structure

```
backend/src/
├── agents/              # Three independent agent modules
├── mcp/                 # MCP server and message routing
├── services/            # LLM, storage, logging services
├── models/              # Pydantic schemas (see data-model.md)
├── api/                 # FastAPI endpoints and WebSocket
└── utils/               # Logging, exceptions

frontend/public/
├── chat-ui.html         # Static HTML UI (MVP implementation)
└── assets/              # CSS and JavaScript files

specs/001-agentic-neurodata-conversion/
├── plan.md              # Implementation plan
├── research.md          # Technical decisions
├── data-model.md        # Pydantic schemas
├── contracts/           # API/MCP contracts
└── quickstart.md        # This file
```

---

## Troubleshooting

### Backend Issues

**Problem**: `ImportError: No module named 'neuroconv'`
**Solution**: Activate Pixi environment first
```bash
pixi shell
python src/api/main.py
```

**Problem**: `ANTHROPIC_API_KEY not set`
**Solution**: Create `.env` file with API key (see Environment Setup)

**Problem**: `Port 8080 already in use`
**Solution**: Kill existing process or use different port
```bash
# Find and kill process
lsof -ti:8080 | xargs kill -9

# Or use different port
uvicorn main:app --port 8081
```

**Problem**: Conversion fails with NeuroConv error
**Solution**: Check uploaded files are supported format
```bash
# Test with toy dataset
pixi run test-integration backend/tests/integration/test_end_to_end.py
```

### Frontend Issues

**Problem**: `npm install` fails
**Solution**: Clear cache and reinstall
```bash
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**Problem**: WebSocket connection refused
**Solution**: Verify backend is running on port 8080
```bash
curl http://localhost:8080/health
```

**Problem**: CORS errors in browser console
**Solution**: Verify FastAPI CORS middleware configured for `localhost:3000`

### Test Issues

**Problem**: Integration tests timeout
**Solution**: Increase timeout (currently 10 min) or use smaller toy dataset
```bash
# Check test dataset size
du -sh backend/tests/fixtures/toy_spikeglx/
```

**Problem**: Coverage below 80%
**Solution**: Add unit tests for uncovered code
```bash
# See coverage report
pixi run test-coverage
open htmlcov/index.html
```

### LLM Issues

**Problem**: `LLMAPIException: Rate limit exceeded`
**Solution**: Wait for rate limit reset (check `retry_after` header) or upgrade Anthropic plan

**Problem**: LLM responses don't match expected format
**Solution**: Check prompt templates in `backend/src/prompts/*.yaml` (Research Decision 6)

---

## Next Steps

1. **Read Architecture Docs**: [plan.md](plan.md), [data-model.md](data-model.md)
2. **Explore Contracts**: [contracts/openapi.yaml](contracts/openapi.yaml), [contracts/mcp-messages.json](contracts/mcp-messages.json)
3. **Run End-to-End Test**: `pixi run test-integration`
4. **Try Sample Conversion**: Upload toy dataset via UI
5. **Review Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)

## Getting Help

- **Issues**: Create GitHub issue with error logs
- **Questions**: Check `specs/` documentation first
- **Contributing**: Follow agent independence principle (no direct imports!)

---

**Version**: 1.0.0 | **Last Updated**: 2025-10-15
