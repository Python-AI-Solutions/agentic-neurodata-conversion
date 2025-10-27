# Agentic Neurodata Conversion 🧠

AI-assisted conversion of neurodata to NWB (Neurodata Without Borders) format using a three-agent architecture.

## Overview

This system uses specialized AI agents to automate the conversion of various neuroscience data formats to standardized NWB files:

- **Conversion Agent**: Detects formats and performs conversions using NeuroConv
- **Evaluation Agent**: Validates NWB files with NWB Inspector and analyzes issues
- **Conversation Agent**: Orchestrates workflows and manages user interactions

All agents communicate via MCP (Model Context Protocol) for clean separation of concerns.

## Quick Start

### Prerequisites

- [Pixi](https://pixi.sh/) package manager
- Python 3.13+ (managed by pixi)
- (Optional) Anthropic API key for LLM-powered correction analysis

### Installation

1. **Clone the repository**
   ```bash
   cd agentic-neurodata-conversion-14
   ```

2. **Install dependencies**
   ```bash
   pixi install
   ```

3. **Generate test dataset**
   ```bash
   pixi run generate-fixtures
   ```

4. **(Optional) Set up LLM service**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

### Running the Application

#### Start the Backend API

```bash
pixi run dev
```

The API will be available at http://localhost:8000

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

#### Open the Frontend UI

**🎨 NEW: Chat-Based Interface (Recommended)**

We now have a modern, conversational UI inspired by Claude.ai!

1. Open a new terminal and start a simple HTTP server:
   ```bash
   cd frontend/public
   python -m http.server 3000
   ```

2. Open your browser to:
   - **Chat UI (Recommended)**: http://localhost:3000/chat-ui.html
   - Classic UI: http://localhost:3000/index.html

The chat interface provides:
- 💬 Conversational interaction with AI assistant
- 🎨 Modern, clean design
- 🔄 Real-time WebSocket updates
- ⚡ Interactive action buttons
- 📊 Status-aware messaging
- ✨ Smooth animations

See [frontend/public/CHAT_UI_README.md](frontend/public/CHAT_UI_README.md) for details.

## Features

### ✅ Implemented (MVP)

- **Three-Agent Architecture**
  - Format detection (SpikeGLX, OpenEphys, Neuropixels)
  - NWB conversion via NeuroConv
  - NWB Inspector validation
  - LLM-powered correction analysis (optional)

- **REST API**
  - File upload with metadata
  - Status tracking
  - Retry approval workflow
  - Log access
  - NWB file download

- **WebSocket Support**
  - Real-time status updates

- **Web UI**
  - Drag-and-drop file upload
  - Live status monitoring
  - Retry approval dialog
  - Download converted files

- **Testing**
  - 15 unit tests for MCP server
  - 7 integration tests for workflows
  - API endpoint tests

### 📋 Architecture Principles

From `.specify/memory/constitution.md`:

1. **Three-Agent Architecture**: Strict separation of concerns
2. **Protocol-Based Communication**: MCP with JSON-RPC 2.0
3. **Defensive Error Handling**: Fail fast with full diagnostics
4. **User-Controlled Workflows**: Explicit approval for retries
5. **Provider-Agnostic Services**: Abstract interfaces for external services

## Usage Examples

### Using the Web UI

1. **Start both backend and frontend** (see above)
2. **Drag and drop** your neurodata file onto the upload area
3. **Click "Start Conversion"** to begin the workflow
4. **Monitor progress** in the status section
5. **Download** the converted NWB file when complete

### Using the REST API

#### Upload a file

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@path/to/your/data.bin" \
  -F 'metadata={"session_description": "Test session"}'
```

#### Check status

```bash
curl http://localhost:8000/api/status
```

#### Download converted file

```bash
curl http://localhost:8000/api/download/nwb -o output.nwb
```

#### View logs

```bash
curl http://localhost:8000/api/logs
```

### Using the Python API Directly

```python
from models import MCPMessage
from services import get_mcp_server
from agents import (
    register_conversation_agent,
    register_conversion_agent,
    register_evaluation_agent,
)

# Initialize
mcp_server = get_mcp_server()
register_conversion_agent(mcp_server)
register_evaluation_agent(mcp_server)
register_conversation_agent(mcp_server)

# Start conversion
message = MCPMessage(
    target_agent="conversation",
    action="start_conversion",
    context={
        "input_path": "/path/to/data",
        "metadata": {"session_description": "My session"}
    }
)

response = await mcp_server.send_message(message)
print(response.result)
```

## Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── agents/           # Three agent implementations
│   │   │   ├── conversion_agent.py
│   │   │   ├── evaluation_agent.py
│   │   │   └── conversation_agent.py
│   │   ├── api/              # FastAPI application
│   │   │   └── main.py
│   │   ├── models/           # Pydantic models
│   │   │   ├── state.py
│   │   │   ├── mcp.py
│   │   │   ├── validation.py
│   │   │   └── api.py
│   │   └── services/         # Core services
│   │       ├── mcp_server.py
│   │       └── llm_service.py
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/
│   └── public/
│       └── index.html        # Web UI
├── specs/                    # Spec-kit specifications
│   └── 001-agentic-neurodata-conversion/
│       ├── plan.md
│       ├── tasks.md
│       ├── research.md
│       ├── data-model.md
│       └── contracts/
└── pixi.toml                 # Dependencies
```

## Development

### Running Tests

```bash
# All tests
pixi run test

# Unit tests only
pixi run test-unit

# Integration tests only
pixi run test-integration

# With coverage
pixi run pytest backend/tests -v --cov=backend/src --cov-report=term-missing
```

### Code Quality

```bash
# Lint code
pixi run lint

# Format code
pixi run format

# Type checking
pixi run typecheck
```

### Development Server with Auto-Reload

```bash
pixi run dev
```

This starts the FastAPI server with auto-reload enabled.

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload file for conversion |
| GET | `/api/status` | Get conversion status |
| POST | `/api/retry-approval` | Submit retry decision |
| POST | `/api/user-input` | Submit user input |
| GET | `/api/validation` | Get validation results |
| GET | `/api/logs` | Get conversion logs |
| GET | `/api/download/nwb` | Download NWB file |
| POST | `/api/reset` | Reset session |
| WS | `/ws` | WebSocket for real-time updates |

### Status Flow

```
IDLE → UPLOADING → DETECTING_FORMAT → CONVERTING → VALIDATING
                                                        ↓
                    ←─────────────────────── AWAITING_RETRY_APPROVAL
                    │                                   ↓
                    └──────→ COMPLETED          or    FAILED
```

## Supported Data Formats

- **SpikeGLX** (.ap.bin, .lf.bin with .meta files)
- **OpenEphys** (structure.oebin or settings.xml)
- **Neuropixels** (.nidq files)
- Additional formats via NeuroConv (Blackrock, Axona, Neuralynx, Plexon, etc.)

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` - API key for Claude (optional, enables LLM correction analysis)

### LLM Service

The system supports multiple LLM providers through an abstract interface:

- **Anthropic** (default): Claude 3.5 Sonnet for correction analysis
- **Mock**: For testing without API calls

To use a different provider, modify the `create_llm_service()` call in `backend/src/api/main.py`.

## Troubleshooting

### "No candidates were found for neuroconv" error

This is expected - neuroconv is installed via PyPI. The error should be fixed in the pixi.toml configuration.

### Tests fail with "Toy dataset not generated"

Run the fixture generation:
```bash
pixi run generate-fixtures
```

### API returns 409 "Another conversion is in progress"

Reset the session:
```bash
curl -X POST http://localhost:8000/api/reset
```

Or use the "Reset Session" button in the web UI.

### CORS errors in browser

The API is configured to allow all origins for MVP. In production, update the CORS settings in `backend/src/api/main.py`.

## Contributing

This project follows the spec-kit methodology. See `specs/001-agentic-neurodata-conversion/` for complete specifications.

### Development Workflow

1. Read the constitution: `.specify/memory/constitution.md`
2. Review the plan: `specs/001-agentic-neurodata-conversion/plan.md`
3. Check tasks: `specs/001-agentic-neurodata-conversion/tasks.md`
4. Write tests first (TDD)
5. Implement following constitutional principles

## License

See LICENSE file for details.

## Acknowledgments

- **NeuroConv** - Format detection and conversion
- **NWB Inspector** - Validation
- **Anthropic Claude** - LLM-powered correction analysis
- **FastAPI** - Web framework
- **Spec-kit** - Specification-driven development

## Contact

For questions or issues, please open an issue on GitHub.

---

**Built with the spec-kit workflow** 📋

See the complete specifications in `specs/001-agentic-neurodata-conversion/`.
