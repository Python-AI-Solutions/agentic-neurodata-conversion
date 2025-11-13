# Agentic Neurodata Conversion System

**AI-Powered NWB Conversion with Natural Language Interface**

Transform neuroscience electrophysiology data to standardized NWB format through intelligent conversation, automated format detection, and comprehensive validation.

---

## 🎯 Overview

The Agentic Neurodata Conversion System is a production-ready platform that revolutionizes how neuroscience researchers convert their electrophysiology data. Using a three-agent AI architecture and natural language processing, it reduces conversion time for NWB format compliance and DANDI archive readiness.

### Key Features

- **🤖 AI-Powered Intelligence**: Natural language metadata collection using Anthropic Claude
- **🎯 Automated Format Detection**: Improved accuracy for SpikeGLX, OpenEphys, Neuropixels
- **💬 Conversational Interface**: Modern chat UI similar to Claude.ai
- **✅ Smart Validation**: NWBInspector integration with AI-powered issue analysis
- **📊 Comprehensive Reports**: PDF, JSON, and text reports with workflow traceability
- **🔄 Adaptive Workflows**: Intelligent retry logic and error recovery
- **🎓 Learning System**: Metadata inference from filenames and history

---

## 🏗️ Architecture

### Three-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Server                     │
│  WebSocket + REST API + Session Management                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              MCP Server (Message Bus)                        │
│  Agent registration • Message routing • State management    │
└─────┬───────────────┬───────────────┬───────────────────────┘
      │               │               │
┌─────▼─────┐  ┌──────▼──────┐  ┌────▼──────┐
│Conversation│  │ Conversion  │  │Evaluation │
│   Agent    │  │   Agent     │  │  Agent    │
└────────────┘  └─────────────┘  └───────────┘
      │               │               │
┌─────▼───────────────▼───────────────▼───────────────────────┐
│                 Supporting Services                          │
│ • LLM Service (Claude AI)                                   │
│ • Intelligent Metadata Parser                               │
│ • Format Detector • Validation Analyzer                     │
│ • Report Generator • Schema Registry                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│          External Tools & Libraries                          │
│  NeuroConv • SpikeInterface • PyNWB • NWBInspector          │
└──────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

**1. Conversation Agent** (`conversation_agent.py`)

- Orchestrates entire workflow
- Manages user interactions
- Collects metadata through natural conversation
- Routes messages between agents
- Handles retry decisions and error recovery

**2. Conversion Agent** (`conversion_agent.py`)

- AI-powered format detection
- Stream detection and selection
- Metadata mapping to NWB schema
- Data conversion using NeuroConv
- Auto-correction application

**3. Evaluation Agent** (`evaluation_agent.py`)

- NWBInspector validation
- AI-powered issue analysis
- Multi-format report generation (PDF/JSON/text)
- DANDI compliance checking
- Correction suggestion generation

---

## 🚀 Quick Start

### Prerequisites

- **Pixi Package Manager**: [Install Pixi](https://pixi.sh/)
- **Python 3.13+**: Managed by Pixi
- **Anthropic API Key**: For AI features (required)

### Installation

```bash
# Clone repository
cd agentic-neurodata-conversion-14

# Install all dependencies (Python, libraries, etc.)
pixi install

# Set up environment variables
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Or create .env file
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env
```

### Running the System

**Start Backend:**

```bash
pixi run dev
```

Server runs at http://localhost:8000

**Start Frontend (new terminal):**

```bash
cd frontend/public
python -m http.server 3000
```

Access at http://localhost:3000/chat-ui.html

**Alternative (All-in-one):**

```bash
python start_app.py
```

---

## 💡 Usage

### Web UI Workflow

1. **Open Browser**: Navigate to http://localhost:3000/chat-ui.html
2. **Upload Files**: Drag & drop your data files

   - SpikeGLX: `.ap.bin` + `.meta` files
   - OpenEphys: `structure.oebin` + data files
   - Neuropixels: `.imec*.bin` + `.meta` files
3. **Start Conversion**: Type "start conversion" in chat
4. **Provide Metadata**: Describe your experiment naturally

   ```
   "I'm Dr. Jane Smith from MIT studying 8 week old male mice
    in visual cortex during a visual stimulation experiment"
   ```
5. **Confirm Understanding**: System shows parsed metadata

   - Review values and confidence scores
   - Type "yes" to confirm or "edit [field]" to change
6. **Automatic Conversion**: System converts to NWB format

   - Real-time progress updates
   - Automatic validation
   - Issue detection and analysis
7. **Download Results**:

   - Converted NWB file
   - Validation reports (PDF, JSON, text)
   - All DANDI-ready

### API Usage

**Upload File:**

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@recording.bin" \
  -F "file=@recording.meta"
```

**Start Conversion:**

```bash
curl -X POST http://localhost:8000/api/start-conversion
```

**Check Status:**

```bash
curl http://localhost:8000/api/status
```

**Chat with System:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -F "message=I'm Dr. Smith from MIT, studying adult mice"
```

**Download NWB:**

```bash
curl http://localhost:8000/api/download/nwb -o output.nwb
```

**Download Report:**

```bash
curl http://localhost:8000/api/download/report -o report.pdf
```

---

## 🧠 Intelligent Features

### 1. Natural Language Metadata Parsing

**Input:**

```
"I'm Dr. Jane Smith from MIT studying 8 week old male mice"
```

**System Understanding:**

```json
{
  "experimenter": "Smith, Jane" (95% confidence),
  "institution": "Massachusetts Institute of Technology" (98%),
  "subject_age": "P56D" (92%),
  "subject_sex": "M" (100%),
  "subject_species": "Mus musculus" (100%)
}
```

**Features:**

- Batch or sequential metadata collection
- Automatic normalization to NWB/DANDI standards
- Confidence-based auto-application
- User confirmation workflow

### 2. Intelligent Format Detection

**Two-Stage Detection:**

1. **AI Analysis**: Claude AI analyzes filename, companion files, file headers
2. **Rule-Based Fallback**: Regex patterns and file structure analysis

**Supported Formats:**

- SpikeGLX (Neuropixels)
- OpenEphys (structure.oebin, settings.xml)
- Neuropixels probe recordings
- Generic formats via NeuroConv

### 3. Metadata Inference

**Automatic Extraction from:**

- Filenames (dates, subject IDs, experimenter names)
- File headers (sampling rates, channels, device info)
- Companion files (.meta, .xml, .json)
- Historical patterns

### 4. Adaptive Retry Logic

**Smart Error Recovery:**

- Automatic issue categorization
- AI-suggested corrections
- User-guided fixes for complex issues
- Maximum retry limits (3 attempts)
- Version tracking (output_v1.nwb, output_v2.nwb)

### 5. Validation Intelligence

**NWBInspector + AI Analysis:**

- Categorize by severity (Critical/Violation/Suggestion)
- User-friendly explanations
- Specific fix recommendations
- DANDI compliance scoring
- Prioritized issue lists

### 6. Comprehensive Reporting

**Three Report Formats:**

**PDF Report:**

- Professional formatting with color coding
- Executive summary
- Complete metadata display
- Issue tables with locations
- Workflow trace for reproducibility
- DANDI readiness assessment

**JSON Report:**

- Machine-readable structure
- Complete validation results
- Workflow provenance
- Statistics and metrics

**Text Report:**

- Quick terminal viewing
- All sections in plain text

---

## 📁 Project Structure

```
agentic-neurodata-conversion-14/
├── backend/
│   ├── src/
│   │   ├── agents/                      # Three-agent implementations
│   │   │   ├── conversation_agent.py    # Orchestration & chat
│   │   │   ├── conversion_agent.py      # Format detection & conversion
│   │   │   ├── evaluation_agent.py      # Validation & reporting
│   │   │   ├── intelligent_metadata_parser.py  # NLP metadata parsing
│   │   │   ├── intelligent_format_detector.py  # AI format detection
│   │   │   ├── metadata_inference.py    # Filename/header inference
│   │   │   ├── metadata_strategy.py     # Adaptive collection strategies
│   │   │   ├── nwb_dandi_schema.py      # Schema definitions
│   │   │   ├── smart_autocorrect.py     # Auto-fix logic
│   │   │   ├── smart_validation.py      # Validation intelligence
│   │   │   ├── adaptive_retry.py        # Retry strategies
│   │   │   └── validation_history_learning.py
│   │   ├── api/
│   │   │   └── main.py                  # FastAPI app (1700+ lines)
│   │   ├── models/
│   │   │   ├── state.py                 # Global state management
│   │   │   ├── mcp.py                   # MCP message protocol
│   │   │   ├── api.py                   # API models
│   │   │   ├── metadata.py              # Metadata schemas
│   │   │   ├── validation.py            # Validation models
│   │   │   └── workflow_state_manager.py
│   │   ├── services/
│   │   │   ├── llm_service.py           # Claude AI integration
│   │   │   ├── mcp_server.py            # Message routing
│   │   │   ├── report_service.py        # PDF/JSON/text reports
│   │   │   ├── metadata_cache.py        # Caching layer
│   │   │   └── prompt_service.py        # Prompt templates
│   │   └── utils/
│   │       └── file_versioning.py       # Output versioning
│   └── tests/
│       ├── unit/                         # Unit tests
│       ├── integration/                  # Integration tests
│       └── fixtures/                     # Test data generators
├── frontend/
│   └── public/
│       ├── chat-ui.html                  # Modern chat interface (114KB)
├── specs/                                # Spec-kit specifications
├── pixi.toml                             # Dependencies & tasks
├── pixi.lock                             # Locked dependencies
├── run_server.py                         # Server startup script
└── .env.example                          # Environment template
```

---

## 🔧 Technology Stack

### Backend

| Component                 | Technology       | Version    | Purpose                     |
| ------------------------- | ---------------- | ---------- | --------------------------- |
| **Language**        | Python           | 3.13+      | Core language               |
| **Framework**       | FastAPI          | 0.115.0+   | REST API & WebSocket        |
| **AI/LLM**          | Anthropic Claude | Sonnet 3.5 | Natural language processing |
| **Conversion**      | NeuroConv        | 0.6.3+     | Data conversion             |
| **Data Reading**    | SpikeInterface   | 0.101.0+   | Electrophysiology I/O       |
| **NWB I/O**         | PyNWB            | 2.8.2+     | NWB file operations         |
| **Validation**      | NWBInspector     | 0.4.36+    | NWB compliance checking     |
| **PDF Reports**     | ReportLab        | 4.2.5+     | PDF generation              |
| **Package Manager** | Pixi             | Latest     | Dependency management       |
| **Server**          | Uvicorn          | 0.32.0+    | ASGI server                 |
| **Validation**      | Pydantic         | 2.9.0+     | Data validation             |
| **Testing**         | pytest           | 8.3.3+     | Test framework              |

### Frontend

| Component               | Technology            | Purpose                 |
| ----------------------- | --------------------- | ----------------------- |
| **UI**            | HTML5/CSS3/JavaScript | Modern chat interface   |
| **Communication** | WebSocket             | Real-time updates       |
| **HTTP**          | Fetch API             | File upload, REST calls |

### Data Science

- **NumPy**: Numerical operations
- **H5py**: HDF5 file handling
- **Neo**: Neurophysiology formats
- **WebSockets**: Real-time communication

### Development

- **Ruff**: Linting
- **mypy**: Type checking
- **pytest-cov**: Code coverage
- **pytest-asyncio**: Async testing
- **httpx**: HTTP testing

---

## 📊 API Reference

### REST Endpoints

| Method         | Endpoint                      | Description                        |
| -------------- | ----------------------------- | ---------------------------------- |
| **GET**  | `/`                         | Root endpoint                      |
| **GET**  | `/api/health`               | Health check                       |
| **POST** | `/api/upload`               | Upload files (multipart/form-data) |
| **POST** | `/api/start-conversion`     | Start conversion workflow          |
| **POST** | `/api/chat`                 | Send conversational message        |
| **POST** | `/api/chat/smart`           | Context-aware chat (any state)     |
| **GET**  | `/api/status`               | Get current status                 |
| **POST** | `/api/improvement-decision` | Accept/improve validation results  |
| **POST** | `/api/retry-approval`       | Retry decision after failure       |
| **POST** | `/api/user-input`           | Submit user corrections            |
| **GET**  | `/api/validation`           | Get validation results             |
| **GET**  | `/api/correction-context`   | Get correction details             |
| **GET**  | `/api/logs`                 | Get system logs (paginated)        |
| **GET**  | `/api/metadata-provenance`  | Get metadata audit trail           |
| **GET**  | `/api/download/nwb`         | Download NWB file                  |
| **GET**  | `/api/download/report`      | Download validation report         |
| **POST** | `/api/reset`                | Reset session                      |
| **WS**   | `/ws`                       | WebSocket for real-time updates    |

### WebSocket Protocol

**Client → Server Messages:**

```json
{
  "type": "ping",
  "timestamp": 1234567890
}

{
  "type": "subscribe",
  "event_types": ["status", "progress"]
}
```

**Server → Client Messages:**

```json
{
  "event_type": "status_update",
  "data": {
    "status": "converting",
    "progress": 45,
    "message": "Converting stream 1/2..."
  }
}

{
  "event_type": "conversation",
  "data": {
    "message": "I understood your metadata...",
    "needs_user_input": true
  }
}
```

---

## 🧪 Testing

### Running Tests

```bash
# All tests with coverage
pixi run test

# Unit tests only
pixi run test-unit

# Integration tests only
pixi run test-integration

# With detailed coverage report
pytest backend/tests -v --cov=backend/src --cov-report=html
open htmlcov/index.html
```

### Test Structure

```
backend/tests/
├── unit/                    # Fast, isolated tests
│   ├── test_mcp_server.py
│   ├── test_metadata_parser.py
│   ├── test_format_detector.py
│   └── ...
├── integration/             # Multi-component tests
│   ├── test_conversion_workflow.py
│   ├── test_validation_workflow.py
│   └── ...
├── fixtures/                # Test data generators
│   └── generate_toy_dataset.py
└── conftest.py              # Shared fixtures
```

### Coverage

- **Target**: 60%+ code coverage
- **Current**: 15 unit tests, 7 integration tests
- **Areas**: Agents, services, API endpoints

---

## 🎓 Development

### Code Quality

```bash
# Linting
pixi run lint

# Auto-formatting
pixi run format

# Type checking
pixi run typecheck
```

### Configuration

**Environment Variables (.env):**

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional
CORS_ORIGINS=http://localhost:3000
DEBUG=false
LOG_LEVEL=INFO
```

### Available Pixi Tasks

```bash
pixi run dev              # Start development server
pixi run serve            # Alternative server start
pixi run test             # Run all tests
pixi run test-unit        # Unit tests only
pixi run test-integration # Integration tests only
pixi run lint             # Lint code
pixi run format           # Format code
pixi run typecheck        # Type checking
pixi run generate-fixtures # Generate test data
pixi run clean            # Clean cache files
```


---


## 🤝 Contributing

### Development Workflow

1. **Read Constitution**: `.specify/memory/constitution.md`
2. **Review Specifications**: `specs/001-agentic-neurodata-conversion/`
3. **Write Tests First**: TDD approach
4. **Follow Standards**: PEP 8, type hints, docstrings
5. **Run Quality Checks**: lint, format, typecheck
6. **Test Coverage**: Maintain 80%+

### Code Standards

- **Style Guide**: PEP 8
- **Line Length**: 100 characters
- **Type Hints**: Required for all functions
- **Docstrings**: Google style
- **Formatting**: Black/Ruff
- **Linting**: Ruff
- **Type Checking**: mypy

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

### Core Technologies

- **NeuroConv** - Format detection and conversion framework
- **NWBInspector** - NWB file validation
- **Anthropic Claude** - AI-powered natural language processing
- **FastAPI** - Modern web framework
- **SpikeInterface** - Electrophysiology data reading
- **PyNWB** - NWB file operations
- **ReportLab** - Professional PDF generation

---

## 🔄 Version History

**v0.1.0** (October 2025)

- Initial production release
- Three-agent architecture
- Natural language metadata collection
- AI-powered format detection
- Comprehensive validation and reporting
- Modern chat UI
- Complete documentation

---

## 🚦 Status

**Current Status**: Production-Ready ✅

**Active Branch**: `try2_full_prj_adi_v2`

**Main Features**:

- ✅ Three-agent architecture operational
- ✅ Natural language processing
- ✅ Format detection (SpikeGLX, OpenEphys, Neuropixels)
- ✅ NWB conversion with NeuroConv
- ✅ Validation with NWBInspector
- ✅ PDF/JSON/text reports
- ✅ Modern chat UI
- ✅ WebSocket real-time updates
- ✅ Comprehensive testing
- ✅ Full documentation

---

**Built with the spec-kit methodology** 📋

For complete specifications, see [`specs/001-agentic-neurodata-conversion/`](specs/001-agentic-neurodata-conversion/)
