# Agentic Neurodata Conversion - Complete Project Requirements & Specifications

**Version**: 2.0
**Date**: October 2025
**Status**: Production-Ready with Advanced Intelligence Features

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Vision & Goals](#project-vision--goals)
3. [System Architecture](#system-architecture)
4. [Core Features & Requirements](#core-features--requirements)
5. [Technical Stack](#technical-stack)
6. [Agent System Design](#agent-system-design)
7. [Intelligent Metadata Parser](#intelligent-metadata-parser)
8. [User Experience Requirements](#user-experience-requirements)
9. [Report Generation System](#report-generation-system)
10. [Validation & Quality Assurance](#validation--quality-assurance)
11. [API Specifications](#api-specifications)
12. [Security & Performance](#security--performance)
13. [Deployment Requirements](#deployment-requirements)
14. [Future Enhancements & Innovation](#future-enhancements--innovation)
15. [Development Guidelines](#development-guidelines)

---

## 1. Executive Summary

### Project Overview

The **Agentic Neurodata Conversion** system is an AI-powered platform that converts neuroscience electrophysiology data from proprietary formats (SpikeGLX, OpenEphys, Neuropixels) to the standardized NWB (Neurodata Without Borders) format, with automatic validation and DANDI archive compliance checking.

### Key Differentiators

- **AI-Powered Intelligence**: Uses Claude AI for natural language metadata parsing, intelligent format detection, and conversational user guidance
- **Three-Agent Architecture**: Specialized agents for conversion, evaluation, and conversation orchestration
- **Natural Language Interface**: Users can provide metadata in plain English without memorizing format specifications
- **Confidence-Based Auto-Application**: Smart metadata handling with three-tier confidence scoring
- **Complete Workflow Transparency**: Full process documentation for scientific reproducibility
- **DANDI-Ready Output**: Automated compliance checking and submission readiness assessment

### Success Metrics

- ✅ 100% accurate format detection for SpikeGLX, OpenEphys, Neuropixels
- ✅ 95%+ natural language metadata parsing accuracy
- ✅ <5 minutes conversion time for typical datasets
- ✅ Zero data loss during conversion
- ✅ Full NWB 2.x schema compliance
- ✅ DANDI archive submission-ready output

---

## 2. Project Vision & Goals

### Vision Statement

*"Democratize neuroscience data sharing by making NWB conversion as simple as having a conversation, while maintaining scientific rigor and reproducibility."*

### Primary Goals

1. **Accessibility**: Enable researchers without programming expertise to convert their data
2. **Intelligence**: Use AI to understand natural language input and guide users through the process
3. **Quality**: Ensure data integrity, format compliance, and scientific reproducibility
4. **Transparency**: Document every step for scientific validity and debugging
5. **Efficiency**: Minimize user time and cognitive load during conversion

### Target Users

- **Neuroscience Researchers**: Primary users with electrophysiology data
- **Lab Managers**: Managing data submission to DANDI archive
- **Data Scientists**: Programmatic access for batch conversions
- **Students**: Learning about NWB format and data standardization

---

## 3. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│  (Chat-based Web UI + REST API + WebSocket for real-time)      │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────┴────────────────────────────────┐
│                    FastAPI Backend Server                        │
│  - REST API endpoints                                            │
│  - WebSocket connection management                               │
│  - Session state management                                      │
│  - File upload handling                                          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────┴────────────────────────────────┐
│                      MCP Server (Message Bus)                    │
│  - Agent registration & discovery                                │
│  - Message routing between agents                                │
│  - Global state management                                       │
│  - Event broadcasting                                            │
└─────┬────────────────────┬────────────────────┬─────────────────┘
      │                    │                    │
┌─────▼────────┐  ┌───────▼────────┐  ┌───────▼─────────┐
│ Conversation │  │   Conversion    │  │   Evaluation    │
│    Agent     │  │     Agent       │  │     Agent       │
│              │  │                 │  │                 │
│ - Orchestrate│  │ - Format detect │  │ - NWB validate  │
│ - User chat  │  │ - Data convert  │  │ - Report gen    │
│ - Metadata   │  │ - Stream handle │  │ - DANDI check   │
│   collection │  │ - NWB write     │  │ - Issue analyze │
└──────────────┘  └─────────────────┘  └─────────────────┘
      │                    │                    │
┌─────▼────────────────────▼────────────────────▼─────────────────┐
│                    Supporting Services                           │
│  - Intelligent Metadata Parser (Natural Language)                │
│  - LLM Service (Claude AI integration)                           │
│  - Report Service (PDF/JSON/Text generation)                     │
│  - Validation History Tracker                                    │
│  - Workflow State Manager                                        │
└──────────────────────────────────────────────────────────────────┘
      │
┌─────▼────────────────────────────────────────────────────────────┐
│                  External Libraries & Tools                       │
│  - NeuroConv (conversion framework)                              │
│  - SpikeInterface (data reading)                                 │
│  - PyNWB (NWB file I/O)                                          │
│  - NWBInspector (validation)                                     │
│  - ReportLab (PDF generation)                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Agent-Based Architecture**: Specialized, loosely-coupled agents for separation of concerns
2. **Message-Driven Communication**: MCP protocol for inter-agent messaging
3. **State Management**: Centralized global state with agent-specific contexts
4. **AI-First Design**: LLM integration at every decision point
5. **Fail-Safe Fallbacks**: Pattern matching and rule-based backups when AI unavailable
6. **Asynchronous Processing**: Non-blocking I/O for large file handling

---

## 4. Core Features & Requirements

### 4.1 File Upload & Format Detection

#### Requirements

**FR-4.1.1**: Support multiple file upload (drag & drop or file picker)
**FR-4.1.2**: Accept binary data files: `.bin`, `.meta`, `.continuous`, `.dat`, `.oebin`
**FR-4.1.3**: Validate file pairs (e.g., SpikeGLX requires both `.bin` and `.meta`)
**FR-4.1.4**: Detect format automatically using:
  - AI-based analysis (filename patterns, file structure)
  - Fallback to regex pattern matching
  - File extension and companion file presence

#### Format Support

| Format | File Types | Detection Criteria |
|--------|------------|-------------------|
| SpikeGLX | `.ap.bin`, `.lf.bin`, `.nidq.bin` + `.meta` | Requires matching `.meta` file |
| OpenEphys | `structure.oebin`, `.continuous`, `.dat` | Presence of `structure.oebin` |
| Neuropixels | `*.imec*.bin` + `.meta` | Neuropixels-specific naming |

**FR-4.1.5**: Return confidence score for format detection (0-100%)
**FR-4.1.6**: Allow manual format selection if ambiguous (<70% confidence)

### 4.2 Intelligent Metadata Collection

#### Natural Language Understanding

**FR-4.2.1**: Accept metadata in natural language:
```
User: "I'm Dr. Jane Smith from MIT studying 8 week old male mice"
System: Parses → experimenter, institution, age, sex, species
```

**FR-4.2.2**: Support two input modes:
- **Batch Mode**: All metadata at once
- **Sequential Mode**: One field at a time with guidance

**FR-4.2.3**: Parse and normalize metadata to NWB/DANDI standards:
- Experimenter: "LastName, FirstName" format
- Institution: Full official name (expand abbreviations)
- Age: ISO 8601 duration (e.g., "P90D" for 90 days)
- Sex: Single letter code (M/F/U/O)
- Species: Scientific name (e.g., "Mus musculus")

#### Confidence-Based Auto-Application

**FR-4.2.4**: Three-tier confidence system:
- **HIGH (≥80%)**: Auto-apply silently with INFO log
- **MEDIUM (50-79%)**: Auto-apply with WARNING log + note
- **LOW (<50%)**: Auto-apply with WARNING + flag for review

**FR-4.2.5**: User confirmation workflow:
1. Show parsed metadata with confidence scores
2. Wait for user response:
   - **Confirm**: "yes", "correct", "ok", Enter key
   - **Edit**: "no", "change" + provide correction
   - **Skip**: "skip", "do it on your own", empty input
3. Apply based on response type

**FR-4.2.6**: Low-confidence field handling:
- Flag field in `state.metadata_warnings`
- Include warning in validation report
- Mark for user review before DANDI submission

### 4.3 NWB Conversion Engine

#### Data Processing Requirements

**FR-4.3.1**: Extract complete data streams:
- SpikeGLX: AP (action potentials), LF (local field), NIDQ (DAQ)
- OpenEphys: All continuous channels
- Neuropixels: All probe channels with correct geometry

**FR-4.3.2**: Preserve all metadata from source files:
- Sampling rate
- Channel count and configuration
- Probe geometry
- Recording device information
- Session timestamps

**FR-4.3.3**: Convert to NWB 2.x format with:
- ElectricalSeries for raw data
- Electrode table with positions
- Device and electrode group information
- Complete session metadata

**FR-4.3.4**: Optimize for DANDI submission:
- gzip compression (level 4)
- Chunked HDF5 storage
- Proper data types
- Complete metadata fields

#### Conversion Process

```
1. Format Detection → Confidence score
2. Select Interface (SpikeGLXRecordingInterface, etc.)
3. Detect Available Streams (using Neo library)
4. Map User Metadata → NWB Schema
5. Run NeuroConv Conversion
6. Calculate SHA256 Checksum
7. Validate Output
8. Generate Reports
```

**FR-4.3.5**: Track and log every conversion step for reproducibility
**FR-4.3.6**: Store intermediate results for debugging
**FR-4.3.7**: Support version control (output_v1.nwb, output_v2.nwb for retries)

### 4.4 Validation & Quality Assurance

#### NWB Validation

**FR-4.4.1**: Run NWBInspector validation on generated file
**FR-4.4.2**: Categorize issues by severity:
- **CRITICAL**: Must fix for valid NWB
- **BEST_PRACTICE_VIOLATION**: Should fix for DANDI
- **BEST_PRACTICE_SUGGESTION**: Recommended improvements

**FR-4.4.3**: Provide detailed issue information:
- Error message
- HDF5 location in file
- Check function that detected it
- Suggested fix (if available)

#### DANDI Compliance

**FR-4.4.4**: Check DANDI-required fields:
- experimenter
- institution
- experiment_description
- session_description
- subject information (ID, species, age, sex)

**FR-4.4.5**: Calculate DANDI readiness score (0-100%)
**FR-4.4.6**: List blocking issues preventing submission
**FR-4.4.7**: Estimate time to fix remaining issues

### 4.5 Report Generation

#### Three Report Formats

**FR-4.5.1**: Generate PDF report with:
- Professional formatting (ReportLab)
- Color-coded severity levels
- Complete metadata summary
- Issue tables with locations
- Workflow trace section
- DANDI readiness assessment
- Recommendations prioritized by importance

**FR-4.5.2**: Generate JSON report with:
- Machine-readable structure
- Complete validation results
- Metadata (experiment + subject)
- Workflow trace (technologies, steps, provenance)
- Statistics (file size, compression ratio, timing)
- DANDI compliance score

**FR-4.5.3**: Generate text report with:
- Plain-text summary
- Quick terminal viewing
- All sections in readable format

#### Workflow Trace

**FR-4.5.4**: Document complete conversion process:
- Input format detected
- Conversion start/end time and duration
- Technologies used (with exact versions)
- Processing steps (detailed 8-step breakdown)
- Data streams processed
- Conversion parameters (compression, chunking)
- Metadata sources
- Data provenance information

**Purpose**: Enable scientific reproducibility and transparency

---

## 5. Technical Stack

### Backend Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.13+ | Primary language |
| **Framework** | FastAPI | 0.100+ | REST API & WebSocket |
| **Agent Communication** | Custom MCP | 1.0 | Message protocol |
| **AI/LLM** | Anthropic Claude | Sonnet 3.5+ | Natural language processing |
| **NWB Conversion** | NeuroConv | 0.6.3+ | High-level conversion |
| **Data Reading** | SpikeInterface | 0.101.0+ | Electrophysiology I/O |
| **NWB I/O** | PyNWB | 2.8.2+ | NWB file operations |
| **Validation** | NWBInspector | 0.4.36+ | NWB compliance checking |
| **PDF Generation** | ReportLab | 4.4.4+ | PDF reports |
| **Package Manager** | Pixi | Latest | Dependency management |
| **Server** | Uvicorn | Latest | ASGI server |

### Frontend Technologies

| Category | Technology | Purpose |
|----------|-----------|---------|
| **UI** | HTML5/CSS3/JavaScript | Chat interface |
| **Communication** | WebSocket | Real-time messaging |
| **HTTP** | Fetch API | File upload, REST calls |

### Data Science Libraries

- **NumPy**: Numerical operations
- **H5py**: HDF5 file handling
- **Neo**: Neurophysiology file reading
- **Pydantic**: Data validation

### Development Tools

- **Git**: Version control
- **pytest**: Testing framework
- **Black**: Code formatting
- **Ruff**: Linting

---

## 6. Agent System Design

### 6.1 Conversation Agent

**Responsibility**: Orchestrate the entire workflow and manage user interaction

#### Capabilities

1. **Workflow Orchestration**
   - Start conversion process
   - Coordinate between conversion and evaluation agents
   - Manage retry logic after validation failures
   - Handle user decisions (proceed, edit, cancel)

2. **User Interaction**
   - Process conversational responses
   - Detect user intent (skip, edit, confirm)
   - Generate dynamic, context-aware questions
   - Provide helpful guidance and explanations

3. **Metadata Management**
   - Request missing metadata intelligently
   - Use adaptive strategy (batch vs. sequential)
   - Track user-provided vs. auto-extracted metadata
   - Merge metadata from multiple sources

4. **State Management**
   - Track conversation phase
   - Manage metadata request policy
   - Store conversation history
   - Handle session lifecycle

#### Key Methods

```python
async def handle_start_conversion(message, state)
async def handle_conversational_response(message, state)
async def handle_retry_decision(message, state)
async def _generate_dynamic_metadata_request(missing_fields, inference_result, file_info, state)
```

### 6.2 Conversion Agent

**Responsibility**: Detect format and perform NWB conversion

#### Capabilities

1. **Format Detection**
   - AI-based pattern recognition
   - Fallback to regex matching
   - Confidence scoring
   - Manual override support

2. **Stream Detection**
   - Use Neo library to parse headers
   - Identify available data streams
   - Prioritize non-SYNC streams
   - Select optimal stream for conversion

3. **Metadata Mapping**
   - Transform flat user metadata to nested NWB structure
   - Convert strings to lists where required (experimenter, keywords)
   - Apply normalization rules
   - Validate against NWB schema

4. **Conversion Execution**
   - Create appropriate NeuroConv interface
   - Configure conversion parameters
   - Run conversion with error handling
   - Calculate checksum for integrity

5. **Auto-Correction**
   - Apply validation fixes
   - Retry conversion with corrected metadata
   - Version output files (v1, v2, etc.)
   - Track correction history

#### Key Methods

```python
async def handle_detect_format(message, state)
async def handle_run_conversion(message, state)
async def handle_apply_corrections(message, state)
async def _detect_format(input_path, state)
async def _map_flat_to_nested_metadata(flat_metadata)
```

### 6.3 Evaluation Agent

**Responsibility**: Validate NWB files and generate reports

#### Capabilities

1. **NWB Validation**
   - Run NWBInspector checks
   - Categorize issues by severity
   - Extract issue locations and details
   - Calculate validation status

2. **AI-Powered Analysis**
   - Generate user-friendly explanations
   - Suggest specific fixes
   - Prioritize issues by importance
   - Estimate fix complexity

3. **Report Generation**
   - Create PDF report with professional formatting
   - Generate JSON for programmatic access
   - Produce text summary for quick viewing
   - Include workflow trace for reproducibility

4. **DANDI Compliance**
   - Check required fields
   - Calculate readiness score
   - List blocking issues
   - Provide submission guidance

#### Key Methods

```python
async def handle_run_validation(message, state)
async def handle_analyze_corrections(message, state)
async def handle_generate_report(message, state)
async def _build_workflow_trace(state)
```

---

## 7. Intelligent Metadata Parser

### 7.1 Architecture

```python
class IntelligentMetadataParser:
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.schema = NWBDANDISchema()
        self.field_schemas = {field.name: field for field in self.schema.get_all_fields()}
```

### 7.2 Core Functionality

#### Natural Language Batch Parsing

**Requirement**: Parse multiple metadata fields from free-form text

**Input Example**:
```
"I'm Dr. Jane Smith from MIT studying 8 week old male mice in visual cortex"
```

**Output**:
```python
[
    ParsedField(
        field_name="experimenter",
        raw_input="Dr. Jane Smith",
        parsed_value="Smith, Jane",
        confidence=95,
        reasoning="Clear name format",
        nwb_compliant=True
    ),
    ParsedField(
        field_name="institution",
        raw_input="MIT",
        parsed_value="Massachusetts Institute of Technology",
        confidence=98,
        reasoning="Standard abbreviation",
        nwb_compliant=True
    ),
    ParsedField(
        field_name="age",
        raw_input="8 week old",
        parsed_value="P56D",
        confidence=92,
        reasoning="Clear age statement",
        nwb_compliant=True
    ),
    # ... more fields
]
```

#### Single Field Parsing

**Requirement**: Parse and normalize individual metadata fields

**Use Cases**:
- Sequential metadata collection
- Field-by-field user guidance
- Correction of specific fields

#### Confidence Calculation

**Factors**:
1. **Clarity**: How explicitly the field is stated
2. **Format Match**: How well it matches expected patterns
3. **Context**: How much inference is required
4. **Ambiguity**: Whether there are alternative interpretations

**Scoring**:
- 80-100%: Explicit, unambiguous, matches expected format
- 50-79%: Requires interpretation, minor assumptions
- 0-49%: Vague, ambiguous, requires significant guessing

#### Normalization Rules

| Field | Normalization Rules |
|-------|-------------------|
| Experimenter | "Dr. Jane Smith" → "Smith, Jane"<br>"J. Smith" → "Smith, J." |
| Institution | "MIT" → "Massachusetts Institute of Technology"<br>"Stanford" → "Stanford University" |
| Age | "8 weeks" → "P56D"<br>"3 months" → "P90D" |
| Sex | "male" → "M"<br>"female" → "F" |
| Species | "mouse" → "Mus musculus"<br>"rat" → "Rattus norvegicus" |

### 7.3 User Confirmation Flow

```
User provides input (natural or structured)
    ↓
Parse and normalize with LLM
    ↓
Generate ParsedField objects with confidence
    ↓
Check user message type:
    ├─ Confirmation keywords ("yes", "ok", Enter) → Apply values
    ├─ Edit keywords ("no", "change") → Request correction
    ├─ Skip keywords ("skip", "do it on your own") → Auto-apply
    └─ Default → Show confirmation message and wait
```

### 7.4 Auto-Application Strategy

**High Confidence (≥80%)**:
```python
state.add_log(LogLevel.INFO, f"✓ Auto-applied {field}={value} (high confidence: {confidence}%)")
```

**Medium Confidence (50-79%)**:
```python
state.add_log(LogLevel.WARNING, f"⚠️ Auto-applied {field}={value} (medium confidence: {confidence}% - best guess)")
```

**Low Confidence (<50%)**:
```python
state.add_log(LogLevel.WARNING, f"❓ Auto-applied {field}={value} (LOW confidence: {confidence}% - NEEDS REVIEW)")
state.metadata_warnings[field] = {
    "value": value,
    "confidence": confidence,
    "warning": "Low confidence parsing - please review before DANDI submission"
}
```

---

## 8. User Experience Requirements

### 8.1 Chat Interface

**UI-8.1.1**: Conversational chat UI similar to ChatGPT
**UI-8.1.2**: Auto-expanding text input (min: 44px, max: 200px)
**UI-8.1.3**: Real-time message streaming via WebSocket
**UI-8.1.4**: Status indicators: "Connecting...", "Processing...", "Complete"
**UI-8.1.5**: File upload drag & drop support

### 8.2 User Guidance

**UX-8.2.1**: Context-aware help messages
**UX-8.2.2**: Example inputs for metadata fields
**UX-8.2.3**: Progress indicators for long operations
**UX-8.2.4**: Clear error messages with suggested fixes
**UX-8.2.5**: Ability to skip optional fields

### 8.3 Feedback & Transparency

**UX-8.3.1**: Show confidence scores for parsed metadata
**UX-8.3.2**: Display workflow steps as they happen
**UX-8.3.3**: Provide detailed logs for debugging
**UX-8.3.4**: Allow download of all reports (PDF, JSON, text)
**UX-8.3.5**: Show DANDI readiness score prominently

### 8.4 Accessibility

**UX-8.4.1**: Keyboard navigation support
**UX-8.4.2**: Screen reader compatibility
**UX-8.4.3**: High contrast mode
**UX-8.4.4**: Responsive design for mobile/tablet

---

## 9. Report Generation System

### 9.1 PDF Report Structure

```
┌─────────────────────────────────────────┐
│     NWB File Validation Report          │
│     Generated: 2025-10-27 14:30:15      │
└─────────────────────────────────────────┘

EXECUTIVE SUMMARY
═════════════════
✅ Status: PASSED WITH WARNINGS
Total Issues: 8 (0 critical, 2 violations, 6 suggestions)

FILE INFORMATION
════════════════
NWB File: /path/to/output.nwb
Size: 45.67 MB
Input: Noise4Sam_g0_t0.imec0.ap.bin
Format: SpikeGLX

METADATA
════════
Experiment:
  Experimenter(s): Smith, Jane; Doe, John
  Institution: Massachusetts Institute of Technology
  Lab: Neuroscience Lab
  Description: Extracellular electrophysiology...

Subject:
  ID: mouse001
  Species: Mus musculus (House mouse)
  Sex: Male
  Age: P90D (90 days)

VALIDATION RESULTS
══════════════════
Critical Issues (0):
  (None)

Best Practice Violations (2):
  1. [HIGH] Subject age should be specified
     Location: /general/subject
     Fix: Add age field in ISO 8601 format

  2. [MEDIUM] Missing experimenter information
     Location: /general/experimenter

Best Practice Suggestions (6):
  ...

WORKFLOW TRACE
══════════════
Input Format: SpikeGLX
Conversion Duration: 23.45 seconds

Technologies Used:
  - NeuroConv v0.6.3
  - SpikeInterface v0.101.0
  - PyNWB v2.8.2
  - NWBInspector v0.4.36
  - Python 3.13.0

Processing Steps:
  1. Detected SpikeGLX format
  2. Extracted metadata from .meta file
  3. Created SpikeGLXRecordingInterface
  4. Mapped metadata to NWB schema
  5. Converted raw data
  6. Added electrode table (384 channels)
  7. Validated with NWBInspector
  8. Generated reports

Data Provenance:
  Original Format: SpikeGLX
  Device: Neuropixels 2.0
  Software: SpikeGLX v20231019
  Conversion Tool: Agentic Neurodata Conversion v1.0

RECOMMENDATIONS
═══════════════
Priority: HIGH
  → Add subject age for DANDI compliance
  → Provide experimenter information

Priority: MEDIUM
  → Include keywords for discoverability
  → Add lab information

DANDI SUBMISSION
════════════════
Ready: NO ❌
Blocking Issues: 2
Compliance Score: 75%
Estimated Fixes: ~10 minutes

────────────────────────────────────────
Generated by: Agentic Neurodata Conversion
Report Version: 1.0
Contact: support@example.com
```

### 9.2 JSON Report Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["report_metadata", "validation_status", "summary", "issues"],
  "properties": {
    "report_metadata": {
      "type": "object",
      "properties": {
        "generated_at": {"type": "string", "format": "date-time"},
        "report_version": {"type": "string"},
        "tool": {"type": "string"},
        "nwbinspector_version": {"type": "string"}
      }
    },
    "nwb_file": {"type": "string"},
    "validation_status": {"type": "string", "enum": ["PASSED", "PASSED_WITH_WARNINGS", "FAILED"]},
    "summary": {
      "type": "object",
      "properties": {
        "total_issues": {"type": "integer"},
        "critical": {"type": "integer"},
        "best_practice_violation": {"type": "integer"},
        "best_practice_suggestion": {"type": "integer"}
      }
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "message": {"type": "string"},
          "severity": {"type": "string"},
          "location": {"type": "string"},
          "check_function_name": {"type": "string"},
          "importance": {"type": "string"},
          "suggested_fix": {"type": "string"}
        }
      }
    },
    "metadata": {"type": "object"},
    "workflow_trace": {"type": "object"},
    "dandi_readiness": {"type": "object"}
  }
}
```

---

## 10. Validation & Quality Assurance

### 10.1 Unit Testing

**TEST-10.1.1**: Test each agent independently
**TEST-10.1.2**: Mock MCP server for agent testing
**TEST-10.1.3**: Test metadata parser with various inputs
**TEST-10.1.4**: Test format detection accuracy
**TEST-10.1.5**: 80%+ code coverage target

### 10.2 Integration Testing

**TEST-10.2.1**: Test agent communication via MCP
**TEST-10.2.2**: Test complete conversion workflow
**TEST-10.2.3**: Test WebSocket message flow
**TEST-10.2.4**: Test file upload and storage

### 10.3 End-to-End Testing

**TEST-10.3.1**: Test with real SpikeGLX data
**TEST-10.3.2**: Test with real OpenEphys data
**TEST-10.3.3**: Test with real Neuropixels data
**TEST-10.3.4**: Validate output with NWBInspector
**TEST-10.3.5**: Verify DANDI submission readiness

### 10.4 Performance Testing

**PERF-10.4.1**: Conversion completes in <5 minutes for typical datasets
**PERF-10.4.2**: Handle files up to 10GB
**PERF-10.4.3**: WebSocket maintains connection during long operations
**PERF-10.4.4**: Memory usage stays below 2GB

---

## 11. API Specifications

### 11.1 REST Endpoints

#### POST /api/upload
Upload data files and optional metadata

**Request**:
```
Content-Type: multipart/form-data

file: binary (multiple allowed)
metadata: JSON object (optional)
```

**Response**:
```json
{
  "session_id": "session-123",
  "message": "Files uploaded successfully",
  "input_path": "/tmp/uploads/...",
  "uploaded_files": ["file1.bin", "file2.meta"],
  "status": "upload_acknowledged"
}
```

#### GET /api/status
Get current conversion status

**Response**:
```json
{
  "status": "completed",
  "detected_format": "SpikeGLX",
  "output_path": "/tmp/outputs/output.nwb",
  "validation_status": "PASSED_WITH_WARNINGS",
  "metadata": {...},
  "reports": {
    "pdf": "/tmp/outputs/report.pdf",
    "json": "/tmp/outputs/report.json",
    "text": "/tmp/outputs/report.txt"
  }
}
```

#### GET /api/health
Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "agents": ["conversation", "conversion", "evaluation"],
  "handlers": {...}
}
```

#### POST /api/reset
Reset session state

**Response**:
```json
{
  "status": "reset",
  "message": "Session state cleared"
}
```

#### GET /api/logs
Get conversion logs

**Query Params**: `?limit=100`

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2025-10-27T14:30:15",
      "level": "INFO",
      "message": "Starting conversion...",
      "context": {...}
    }
  ]
}
```

### 11.2 WebSocket Protocol

**Connection**: `ws://localhost:8000/ws`

**Client → Server Messages**:
```json
{
  "type": "user_message",
  "message": "I'm Dr. Jane Smith from MIT"
}
```

**Server → Client Messages**:
```json
{
  "type": "assistant_message",
  "message": "Thanks! I've noted your information...",
  "needs_user_input": false,
  "status": "awaiting_user_input"
}
```

---

## 12. Security & Performance

### 12.1 Security Requirements

**SEC-12.1.1**: Validate all uploaded files (size, type, content)
**SEC-12.1.2**: Sanitize user input to prevent injection attacks
**SEC-12.1.3**: Use secure WebSocket (WSS) in production
**SEC-12.1.4**: Implement rate limiting on API endpoints
**SEC-12.1.5**: Store API keys securely (environment variables)
**SEC-12.1.6**: Use HTTPS only in production
**SEC-12.1.7**: Implement session timeout (30 minutes inactivity)
**SEC-12.1.8**: Scan uploaded files for malware

### 12.2 Performance Requirements

**PERF-12.2.1**: API response time <200ms (excluding LLM calls)
**PERF-12.2.2**: File upload progress tracking
**PERF-12.2.3**: Streaming response for large LLM outputs
**PERF-12.2.4**: Background processing for conversion
**PERF-12.2.5**: Efficient HDF5 chunking and compression
**PERF-12.2.6**: Memory-mapped file reading for large datasets

### 12.3 Scalability

**SCALE-12.3.1**: Support concurrent user sessions
**SCALE-12.3.2**: Horizontal scaling via load balancer
**SCALE-12.3.3**: Separate worker processes for conversion
**SCALE-12.3.4**: Database for session persistence (future)
**SCALE-12.3.5**: Queue system for batch processing (future)

---

## 13. Deployment Requirements

### 13.1 Environment Setup

**DEP-13.1.1**: Use Pixi for dependency management
**DEP-13.1.2**: Python 3.13+ required
**DEP-13.1.3**: Environment variables:
```bash
ANTHROPIC_API_KEY=sk-...
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 13.1.4: Install dependencies:
```bash
pixi install
```

### 13.2 Server Deployment

**DEP-13.2.1**: Use Uvicorn with multiple workers:
```bash
pixi run dev  # Development
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4  # Production
```

**DEP-13.2.2**: Reverse proxy with Nginx
**DEP-13.2.3**: SSL/TLS certificate setup
**DEP-13.2.4**: Logging to file + stdout
**DEP-13.2.5**: Process manager (systemd, supervisor, or PM2)

### 13.3 Monitoring

**MON-13.3.1**: Health check endpoint monitoring
**MON-13.3.2**: Log aggregation (ELK stack or similar)
**MON-13.3.3**: Error tracking (Sentry or similar)
**MON-13.3.4**: Performance metrics (Prometheus + Grafana)
**MON-13.3.5**: Uptime monitoring

### 13.4 Backup & Recovery

**BACK-13.4.1**: Regular database backups (if using DB)
**BACK-13.4.2**: Uploaded file retention policy
**BACK-13.4.3**: Disaster recovery plan
**BACK-13.4.4**: Configuration version control

---

## 14. Future Enhancements & Innovation

### 14.1 Advanced Intelligence Features

#### 14.1.1 Learning from User Corrections
**Innovation**: Track user edits to improve parsing accuracy over time

**Implementation**:
```python
class AdaptiveMetadataParser:
    def __init__(self):
        self.correction_history = CorrectionTracker()

    async def learn_from_correction(self, original, corrected, field):
        """Store correction patterns for future use"""
        self.correction_history.add(
            field=field,
            original=original,
            corrected=corrected,
            timestamp=datetime.now()
        )

        # Update normalization rules
        if self.correction_history.get_frequency(original, corrected) > 5:
            self.schema.add_normalization_rule(field, original, corrected)
```

**Benefits**:
- Personalized to institution/lab conventions
- Improves accuracy over time
- Reduces user correction burden

#### 14.1.2 Predictive Metadata Suggestions
**Innovation**: Predict metadata based on file characteristics and history

**Example**:
```
System analyzes file: "smith_lab_mouse042_20251027.ap.bin"
↓
Predicts:
- Lab: "Smith Lab" (from filename)
- Subject ID: "mouse042" (from filename)
- Date: 2025-10-27 (from filename)
- Species: "Mus musculus" (common in this lab based on history)
↓
User confirms or corrects
```

#### 14.1.3 Smart Issue Resolution
**Innovation**: AI suggests specific fixes for validation issues

**Implementation**:
```python
async def analyze_issue_and_suggest_fix(issue):
    """Use LLM to generate specific fix for validation issue"""

    prompt = f"""
    NWB validation issue: {issue.message}
    Location: {issue.location}
    Current value: {issue.current_value}

    Suggest specific fix with example code/value.
    """

    fix = await llm.generate(prompt)
    return {
        "issue": issue,
        "suggested_fix": fix.code,
        "explanation": fix.reasoning,
        "confidence": fix.confidence
    }
```

#### 14.1.4 Intelligent Format Detection v2.0
**Innovation**: Deep learning model for format detection

**Approach**:
- Train CNN on binary file headers
- Use file structure patterns
- Combine with metadata analysis
- Achieve >99% accuracy

#### 14.1.5 Context-Aware Help System
**Innovation**: Provide help based on current user context

**Example**:
```
User stuck at: "Provide age of subject"
System detects: User hesitating, no input for 30 seconds
↓
Proactive help:
"Need help? Age should be in ISO 8601 format. Examples:
- 'P90D' for 90 days
- 'P8W' for 8 weeks
- '8 weeks old' (I can convert this for you!)
Type 'help age' for more info."
```

### 14.2 User Experience Enhancements

#### 14.2.1 Visual Data Preview
**Innovation**: Show visual preview of converted data

**Features**:
- Raster plot of spike times
- Waveform previews
- Channel map visualization
- Time series plots
- Interactive zooming

#### 14.2.2 Batch Processing Interface
**Innovation**: Upload and convert multiple sessions at once

**UI**:
```
┌─────────────────────────────────────┐
│ Batch Conversion                    │
├─────────────────────────────────────┤
│ Session 1: mouse001_day1 [✓ Done]  │
│ Session 2: mouse001_day2 [⏳ 45%]  │
│ Session 3: mouse001_day3 [⏸ Queue] │
│ Session 4: mouse002_day1 [⏸ Queue] │
│                                     │
│ [Pause All] [Resume All] [Cancel]  │
└─────────────────────────────────────┘
```

#### 14.2.3 Collaborative Editing
**Innovation**: Multiple users can work on same conversion

**Use Case**: PI provides high-level metadata, student adds details

#### 14.2.4 Mobile App
**Innovation**: Convert data from phone/tablet

**Features**:
- Simplified mobile UI
- Voice input for metadata
- Upload from cloud storage
- Push notifications when complete

#### 14.2.5 Progress Persistence
**Innovation**: Resume interrupted conversions

**Implementation**:
- Save state checkpoints
- Resume from last successful step
- Handle network interruptions gracefully

### 14.3 Integration Features

#### 14.3.1 DANDI Direct Upload
**Innovation**: Upload to DANDI archive directly from UI

**Flow**:
```
Convert to NWB → Validate → Fix Issues → Upload to DANDI
                                           ↓
                                    Create dandiset
                                    Add metadata
                                    Upload file
                                    Publish
```

#### 14.3.2 Cloud Storage Integration
**Innovation**: Read from and write to S3, Google Cloud, Azure

**Benefits**:
- No local storage needed
- Work with large datasets
- Institutional storage integration

#### 14.3.3 Git Integration
**Innovation**: Version control for NWB files

**Features**:
- Track changes to metadata
- Diff between versions
- Rollback to previous state
- Collaboration via branches

#### 14.3.4 Lab Management System Integration
**Innovation**: Import metadata from LIMS

**Supported Systems**:
- LabKey
- SampleDB
- OpenBIS
- Custom REST APIs

#### 14.3.5 Analysis Pipeline Integration
**Innovation**: Connect to downstream analysis tools

**Integrations**:
- SpikeInterface for spike sorting
- Suite2p for calcium imaging
- DeepLabCut for behavior
- Custom pipelines via API

### 14.4 Advanced Validation Features

#### 14.4.1 Semantic Validation
**Innovation**: Check metadata makes scientific sense

**Examples**:
- Age reasonable for species? (P1000D for mouse = 2.7 years → unusual)
- Sampling rate appropriate for recording type? (30kHz for LFP → too high)
- Channel count matches probe? (385 channels for Neuropixels 1.0 → wrong)

#### 14.4.2 Cross-File Validation
**Innovation**: Validate consistency across multiple files

**Checks**:
- Same subject ID used consistently
- Session times don't overlap
- Experimental conditions match expected protocol

#### 14.4.3 Literature-Based Validation
**Innovation**: Compare to published standards

**Example**:
```
Your metadata: "Anesthesia: isoflurane 5%"
Warning: Literature suggests isoflurane >3% may affect neural activity
Reference: Smith et al., 2020 (PMID: 12345678)
```

#### 14.4.4 Automated Fix Suggestions
**Innovation**: Propose specific metadata corrections

**Example**:
```
Issue: "Subject species should use binomial nomenclature"
Current: "mouse"
Suggestion: "Mus musculus"
Apply? [Yes] [No] [Edit]
```

### 14.5 Enterprise Features

#### 14.5.1 Multi-Tenancy
**Innovation**: Support multiple organizations/labs

**Features**:
- Separate data storage per tenant
- Custom branding
- Role-based access control
- Usage analytics per tenant

#### 14.5.2 Audit Trail
**Innovation**: Complete history of all actions

**Tracked Events**:
- Who uploaded files
- What metadata was provided
- When conversions ran
- Which validations failed
- Who approved submissions

#### 14.5.3 Compliance Reporting
**Innovation**: Generate reports for grants/institutions

**Reports**:
- Data sharing metrics
- FAIR principles compliance
- DANDI submission statistics
- User activity summaries

#### 14.5.4 Custom Workflows
**Innovation**: Define institution-specific workflows

**Example**:
```yaml
workflow:
  - stage: upload
    require: two_factor_auth
  - stage: metadata
    require: pi_approval
  - stage: validation
    require: min_score_80
  - stage: submission
    require: final_review
```

#### 14.5.5 API Rate Limiting & Quotas
**Innovation**: Fair usage policies for shared resources

**Features**:
- Per-user conversion limits
- Priority queue for paid tiers
- Resource usage dashboards

### 14.6 Research Features

#### 14.6.1 Experiment Template Library
**Innovation**: Pre-configured templates for common experiments

**Templates**:
- Neuropixels visual cortex recording
- Patch-clamp electrophysiology
- Two-photon calcium imaging
- Optogenetics + ephys
- Behavioral tracking + neural

#### 14.6.2 Metadata Ontology Integration
**Innovation**: Link to established ontologies

**Ontologies**:
- UBERON for anatomy
- NCBI Taxonomy for species
- BAO for assays
- OBI for instruments

#### 14.6.3 Citation Generation
**Innovation**: Generate citations for methods sections

**Output**:
```
Data was converted to NWB format using the Agentic Neurodata
Conversion tool (v1.0, https://...) with NeuroConv (v0.6.3),
SpikeInterface (v0.101.0), and PyNWB (v2.8.2). Validation was
performed using NWBInspector (v0.4.36).
```

#### 14.6.4 Data DOI Assignment
**Innovation**: Assign DOIs to converted datasets

**Integration**: Zenodo, Figshare, institutional repositories

#### 14.6.5 Provenance Tracking
**Innovation**: Complete data lineage from raw to NWB

**W3C PROV Format**:
```turtle
:nwb_file a prov:Entity ;
  prov:wasGeneratedBy :conversion_activity ;
  prov:wasDerivedFrom :raw_spikeglx_file .

:conversion_activity a prov:Activity ;
  prov:used :raw_spikeglx_file ;
  prov:wasAssociatedWith :user_jane_smith ;
  prov:startedAtTime "2025-10-27T14:29:45"^^xsd:dateTime .
```

---

## 15. Development Guidelines

### 15.1 Code Organization

```
project_root/
├── backend/
│   ├── src/
│   │   ├── agents/          # Agent implementations
│   │   ├── api/             # FastAPI routes
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Supporting services
│   │   └── outputs/         # Generated files
│   └── tests/               # Unit & integration tests
├── frontend/
│   └── public/
│       └── chat-ui.html     # Single-page app
├── test_data/               # Sample datasets
├── test scripts/            # Test & demo scripts
├── md docs/                 # All documentation
└── pixi.toml                # Dependencies
```

### 15.2 Coding Standards

**STYLE-15.2.1**: Follow PEP 8 style guide
**STYLE-15.2.2**: Use type hints for all functions
**STYLE-15.2.3**: Maximum line length: 100 characters
**STYLE-15.2.4**: Use Black for formatting
**STYLE-15.2.5**: Use Ruff for linting

**Example**:
```python
async def handle_user_response(
    self,
    message: str,
    context: Dict[str, Any],
    state: GlobalState,
) -> MCPResponse:
    """
    Process user's conversational response.

    Args:
        message: User's message text
        context: Conversation context
        state: Global state

    Returns:
        MCP response with extracted information
    """
    # Implementation...
```

### 15.3 Documentation Standards

**DOC-15.3.1**: Every module has a docstring
**DOC-15.3.2**: Every public function has a docstring
**DOC-15.3.3**: Use Google-style docstrings
**DOC-15.3.4**: Include usage examples in docstrings
**DOC-15.3.5**: Keep README up to date

### 15.4 Testing Standards

**TEST-15.4.1**: Every new feature has tests
**TEST-15.4.2**: Maintain 80%+ code coverage
**TEST-15.4.3**: Use pytest fixtures for common setup
**TEST-15.4.4**: Mock external services (LLM, file I/O)
**TEST-15.4.5**: Test error conditions explicitly

### 15.5 Git Workflow

**GIT-15.5.1**: Use feature branches
**GIT-15.5.2**: Write descriptive commit messages
**GIT-15.5.3**: Squash commits before merging
**GIT-15.5.4**: Tag releases with semantic versioning
**GIT-15.5.5**: Keep main branch deployable

### 15.6 Code Review Checklist

- [ ] Code follows style guide
- [ ] All functions have docstrings
- [ ] Tests pass and coverage maintained
- [ ] No hardcoded values (use config)
- [ ] Error handling comprehensive
- [ ] Logging appropriate
- [ ] Security considerations addressed
- [ ] Performance acceptable
- [ ] Documentation updated

---

## 16. Success Criteria

### 16.1 Functional Criteria

✅ **FC-16.1.1**: Convert SpikeGLX data with 100% accuracy
✅ **FC-16.1.2**: Convert OpenEphys data with 100% accuracy
✅ **FC-16.1.3**: Convert Neuropixels data with 100% accuracy
✅ **FC-16.1.4**: Parse natural language metadata with >95% accuracy
✅ **FC-16.1.5**: Generate valid NWB files passing NWBInspector
✅ **FC-16.1.6**: Produce DANDI-compliant outputs
✅ **FC-16.1.7**: Create comprehensive validation reports

### 16.2 Non-Functional Criteria

✅ **NFC-16.2.1**: Conversion completes in <5 minutes (typical dataset)
✅ **NFC-16.2.2**: System handles 10+ concurrent users
✅ **NFC-16.2.3**: 99.9% uptime (excluding maintenance)
✅ **NFC-16.2.4**: Zero data corruption incidents
✅ **NFC-16.2.5**: User satisfaction >4.5/5

### 16.3 Adoption Criteria

✅ **AC-16.3.1**: 100+ successful conversions in first 6 months
✅ **AC-16.3.2**: Used by 10+ research institutions
✅ **AC-16.3.3**: 50+ datasets uploaded to DANDI
✅ **AC-16.3.4**: Positive feedback from DANDI archive maintainers
✅ **AC-16.3.5**: Academic publication citing the tool

---

## 17. Glossary

**Agent**: Specialized component responsible for specific workflow tasks
**DANDI**: Distributed Archives for Neurophysiology Data Integration
**ElectricalSeries**: NWB container for voltage trace recordings
**MCP**: Model Context Protocol - custom inter-agent messaging system
**NeuroConv**: High-level Python library for neurodata format conversion
**NWB**: Neurodata Without Borders - standardized neurophysiology data format
**Neuropixels**: High-density silicon probe for neural recordings
**OpenEphys**: Open-source platform for extracellular electrophysiology
**PyNWB**: Python API for reading and writing NWB files
**SpikeGLX**: Data acquisition system for Neuropixels probes
**SpikeInterface**: Python framework for spike sorting and analysis

---

## 18. References

### 18.1 Standards & Specifications

- NWB Format Specification: https://nwb-schema.readthedocs.io/
- DANDI Archive Standards: https://www.dandiarchive.org/
- ISO 8601 Duration Format: https://en.wikipedia.org/wiki/ISO_8601#Durations
- HDF5 Specification: https://www.hdfgroup.org/

### 18.2 Key Libraries

- NeuroConv Documentation: https://neuroconv.readthedocs.io/
- SpikeInterface Documentation: https://spikeinterface.readthedocs.io/
- PyNWB Documentation: https://pynwb.readthedocs.io/
- NWBInspector Documentation: https://nwbinspector.readthedocs.io/

### 18.3 Related Projects

- NWB Explorer: https://nwbexplorer.opensourcebrain.org/
- DANDI CLI: https://github.com/dandi/dandi-cli
- NWB Widgets: https://github.com/NeurodataWithoutBorders/nwb-jupyter-widgets

---

## Appendix A: Example Workflows

### A.1 Basic Conversion

```
1. User uploads: Noise4Sam_g0_t0.imec0.ap.bin + .meta
2. System detects: SpikeGLX format (confidence: 98%)
3. System asks: "Who is the experimenter?"
4. User responds: "Dr. Jane Smith"
5. System parses: "Smith, Jane" (confidence: 95%)
6. System shows: "I understood: experimenter = 'Smith, Jane'. Correct?"
7. User: [presses Enter]
8. System: Auto-applies (high confidence)
9. System asks for remaining metadata...
10. User provides all metadata
11. System converts to NWB
12. System validates with NWBInspector
13. System generates reports (PDF, JSON, text)
14. User downloads NWB + reports
```

### A.2 Natural Language Batch Input

```
1. User uploads files
2. System asks: "Please provide metadata"
3. User: "I'm Dr. Jane Smith from MIT studying 8 week old male mice in visual cortex"
4. System parses:
   - experimenter: "Smith, Jane" (95%)
   - institution: "Massachusetts Institute of Technology" (98%)
   - age: "P56D" (92%)
   - sex: "M" (100%)
   - species: "Mus musculus" (100%)
   - experiment_description: "Visual cortex recording..." (65%)
5. System shows confirmation with confidence scores
6. User confirms
7. Conversion proceeds...
```

### A.3 Error Correction Flow

```
1. Conversion completes
2. Validation finds 5 issues (2 critical)
3. System analyzes issues with AI
4. System: "I found 2 critical issues that need fixing:
   1. Missing subject age
   2. Invalid session start time
   Would you like me to try fixing these automatically?"
5. User: "yes"
6. System proposes fixes with explanations
7. User reviews and approves
8. System re-runs conversion with fixes
9. Validation passes
10. Reports generated
```

---

## Appendix B: Deployment Checklist

### B.1 Pre-Deployment

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Security audit completed
- [ ] Performance testing done
- [ ] Backup strategy in place

### B.2 Deployment Steps

- [ ] Set environment variables
- [ ] Install dependencies with Pixi
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up SSL certificates
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Test health endpoint
- [ ] Verify API functionality
- [ ] Test WebSocket connection
- [ ] Perform smoke tests

### B.3 Post-Deployment

- [ ] Monitor error logs
- [ ] Check performance metrics
- [ ] Verify user conversions succeed
- [ ] Collect user feedback
- [ ] Document any issues
- [ ] Plan next iteration

---

## Document Control

**Version History**:
- v2.0 (2025-10-27): Complete project requirements based on production system
- v1.0 (2025-01-15): Initial requirements document

**Approved By**: Project Team
**Next Review**: 2026-01-27

**Maintainers**:
- Technical Lead: [Name]
- Product Owner: [Name]
- Documentation: [Name]

---

**END OF DOCUMENT**

*This requirements document serves as the complete specification for building the Agentic Neurodata Conversion system from scratch, including all current features and future innovation opportunities.*