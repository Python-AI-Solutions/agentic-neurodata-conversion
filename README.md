# Agentic Neurodata Conversion System

**AI-Powered NWB Conversion with Natural Language Interface**

[![CI/CD Pipeline](https://github.com/Python-AI-Solutions/agentic-neurodata-conversion/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Python-AI-Solutions/agentic-neurodata-conversion/actions/workflows/ci.yml)

Transform neuroscience electrophysiology data to standardized NWB format through intelligent conversation, automated format detection, and comprehensive validation.

---

## 🎯 Overview

The Agentic Neurodata Conversion System is a production-ready platform that revolutionizes how neuroscience researchers convert their electrophysiology data. Using a three-agent AI architecture and natural language processing, it reduces conversion time for NWB format compliance and DANDI archive readiness.

### Key Features

- **🤖 AI-Powered Intelligence**: Natural language metadata collection using Anthropic Claude
- **🎯 Automated Format Detection**: Automatic format detection of input data files
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

- **Pixi Package Manager**: [Install Pixi](https://pixi.sh/) (required)
- **Python 3.13+**: Managed automatically by Pixi
- **Anthropic API Key**: For AI features (required)

> **Note**: This project uses **Pixi for all dependency management**. pip/conda install is not supported. All dependencies are defined in `pixi.toml`.

### Installation

```bash
# Install Pixi if you don't have it
curl -fsSL https://pixi.sh/install.sh | bash

# Clone repository
cd agentic-neurodata-conversion

# Install all dependencies (Python, libraries, dev tools)
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
run python file inside scripts/startup/start_app.py
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



### 4. Adaptive Retry Logic

**Smart Error Recovery:**



### 5. Validation Intelligence

**NWBInspector + AI Analysis:**



### 6. Comprehensive Reporting



---




**Built with the spec-kit methodology** 📋

For complete specifications, see [`specs/001-agentic-neurodata-conversion`]
