# Technical Architecture: As-Built Documentation

**Document Type**: Implementation architecture documentation
**Date**: October 27, 2025
**Purpose**: Document the actual implemented architecture, including patterns, decisions, and rationale discovered during development

---

## Executive Summary

This document describes the **actual implemented system architecture**, including design patterns, integration points, and technical decisions that emerged during iterative development. It complements the requirements specification by explaining **how** the system was built and **why** specific architectural choices were made.

### Key Architectural Innovations

1. **Schema-Driven LLM Prompting** - Using metadata schemas as structured context for AI
2. **Confidence-Tiered Automation** - Different strategies based on AI certainty
3. **Graceful LLM Degradation** - Full functionality with fallback to rule-based approaches
4. **Conversation-Aware State Management** - Adaptive behavior based on user interaction patterns
5. **Message-Driven Agent Communication** - MCP protocol for loose coupling

---

## System Architecture Overview

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Chat UI      │  │ File Upload  │  │ WebSocket    │          │
│  │ (HTML/JS)    │  │ Component    │  │ Client       │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼───────────────────┘
          │ WebSocket        │ HTTP POST        │ WS Connection
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼───────────────────┐
│                      FastAPI Backend Server                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  REST Endpoints (/api/upload, /api/status, /api/health)  │    │
│  └────────────────────────┬─────────────────────────────────┘    │
│  ┌────────────────────────▼─────────────────────────────────┐    │
│  │  WebSocket Handler (/ws)                                  │    │
│  │  - Connection management                                  │    │
│  │  - Message routing                                         │    │
│  │  - Session state tracking                                 │    │
│  └────────────────────────┬─────────────────────────────────┘    │
└───────────────────────────┼────────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────────┐
│                      MCP Server (Message Bus)                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Agent Registry                                           │    │
│  │  - conversation_agent → ConversationAgent                │    │
│  │  - conversion_agent → ConversionAgent                    │    │
│  │  - evaluation_agent → EvaluationAgent                    │    │
│  └────────────────────────┬─────────────────────────────────┘    │
│  ┌────────────────────────▼─────────────────────────────────┐    │
│  │  Message Router                                           │    │
│  │  route_message(to_agent, message, context, state)        │    │
│  └────────────────────────┬─────────────────────────────────┘    │
│  ┌────────────────────────▼─────────────────────────────────┐    │
│  │  Global State Manager                                     │    │
│  │  - Conversion status, metadata, paths, logs              │    │
│  │  - Conversation history                                   │    │
│  │  - Workflow state machine                                 │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────┬────────────────────┬────────────────────┬─────────────────┘
      │                    │                    │
┌─────▼────────┐  ┌───────▼────────┐  ┌───────▼─────────┐
│ Conversation │  │   Conversion    │  │   Evaluation    │
│    Agent     │  │     Agent       │  │     Agent       │
└──────┬───────┘  └────────┬────────┘  └────────┬────────┘
       │                   │                     │
┌──────▼──────────────────▼────────────────────▼─────────────┐
│              Supporting Services Layer                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ LLM Service (Claude AI Integration)                 │  │
│  │ - Structured output generation                      │  │
│  │ - Prompt templating                                 │  │
│  │ - Response parsing                                  │  │
│  └─────────────────���───────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Intelligent Metadata Parser                         │  │
│  │ - Natural language understanding                    │  │
│  │ - Batch and sequential parsing                      │  │
│  │ - Confidence scoring                                │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Metadata Inference Engine                           │  │
│  │ - Filename analysis                                 │  │
│  │ - File header parsing                               │  │
│  │ - Pattern recognition                               │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Smart Auto-Correction System                        │  │
│  │ - Validation error analysis                         │  │
│  │ - Fix generation                                    │  │
│  │ - Dependency resolution                             │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Report Service                                      │  │
│  │ - PDF generation (ReportLab)                        │  │
│  │ - JSON serialization                                │  │
│  │ - Text formatting                                   │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ NWB/DANDI Schema Registry                           │  │
│  │ - Field definitions                                 │  │
│  │ - Normalization rules                               │  │
│  │ - Validation patterns                               │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│              External Libraries Layer                        │
│  - NeuroConv (conversion framework)                         │
│  - SpikeInterface (data reading)                            │
│  - PyNWB (NWB file I/O)                                     │
│  - NWBInspector (validation)                                │
│  - Neo (electrophysiology data structures)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture Deep Dive

### Agent Communication Pattern: MCP Protocol

**Design Decision**: Custom Message Context Protocol (MCP) for inter-agent communication

**Why Not Direct Function Calls?**
- Agents should be loosely coupled
- Messages enable async processing
- Easier to add tracing/logging
- Future: Distribute agents across processes/machines

**Message Structure**:
```python
@dataclass
class MCPMessage:
    """Message sent between agents via MCP server."""
    action: str              # e.g., "detect_format", "run_conversion"
    context: Dict[str, Any]  # Message-specific data
    sender: Optional[str]    # Originating agent
    request_id: Optional[str]  # For tracking

@dataclass
class MCPResponse:
    """Response from agent message handler."""
    success: bool
    message: str             # User-facing message
    data: Dict[str, Any]     # Structured response data
    error: Optional[str]
```

**Message Flow Example**:
```python
# Conversation Agent → Conversion Agent
message = MCPMessage(
    action="run_conversion",
    context={
        "input_path": "/tmp/uploads/recording.bin",
        "metadata": {"experimenter": "Smith, Jane", ...}
    },
    sender="conversation_agent"
)

response = await mcp_server.route_message(
    to_agent="conversion_agent",
    message=message,
    state=global_state
)

if response.success:
    output_path = response.data["output_path"]
    # Proceed to validation...
```

### Conversation Agent: Orchestration Logic

**Responsibility**: Workflow orchestration and user interaction

**Key Implementation Pattern**: Message Handler Registry

```python
class ConversationAgent:
    def __init__(self, mcp_server, llm_service):
        self._mcp_server = mcp_server
        self._llm_service = llm_service

        # Handler registry maps actions to methods
        self._handlers = {
            "start_conversion": self.handle_start_conversion,
            "conversational_response": self.handle_conversational_response,
            "retry_decision": self.handle_retry_decision,
            "edit_metadata": self.handle_edit_metadata,
        }

    async def handle_message(self, message: MCPMessage, state: GlobalState):
        """Route message to appropriate handler."""
        handler = self._handlers.get(message.action)
        if not handler:
            return MCPResponse(
                success=False,
                message=f"Unknown action: {message.action}",
                error="UNKNOWN_ACTION"
            )

        return await handler(message, state)
```

**Workflow State Machine Integration**:

```python
async def handle_start_conversion(self, message: MCPMessage, state: GlobalState):
    """
    Initiate conversion workflow.

    Flow:
    1. Validate files are uploaded
    2. Detect format (via Conversion Agent)
    3. Infer metadata from files
    4. Request missing metadata from user
    5. Wait for user response
    """

    # Update conversation phase
    state.conversation_phase = ConversationPhase.FORMAT_DETECTION

    # Send format detection request to Conversion Agent
    format_msg = MCPMessage(
        action="detect_format",
        context={"input_path": state.input_path}
    )

    format_response = await self._mcp_server.route_message(
        to_agent="conversion_agent",
        message=format_msg,
        state=state
    )

    if not format_response.success:
        return MCPResponse(
            success=False,
            message="Failed to detect format",
            error=format_response.error
        )

    # Format detected, move to metadata collection
    state.detected_format = format_response.data["format"]
    state.format_confidence = format_response.data["confidence"]
    state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Infer metadata from file analysis
    inference_result = await self._metadata_inference_engine.infer_metadata(
        state.input_path, state
    )

    # Generate dynamic metadata request
    missing_fields = self._identify_missing_fields(
        inference_result, state.metadata
    )

    request_message = await self._generate_dynamic_metadata_request(
        missing_fields, inference_result, state
    )

    state.conversation_phase = ConversationPhase.AWAITING_USER_INPUT

    return MCPResponse(
        success=True,
        message=request_message,
        data={"needs_user_input": True}
    )
```

### Conversion Agent: Format Detection & Conversion

**Responsibility**: Data format detection and NWB conversion

**Two-Stage Format Detection**:

**Stage 1: AI-Powered Analysis**
```python
async def _detect_format_with_ai(
    self,
    input_path: str,
    state: GlobalState
) -> Tuple[str, float]:
    """
    Use LLM to analyze file characteristics and predict format.

    Advantages:
    - Handles ambiguous cases
    - Learns from naming patterns
    - Provides reasoning

    Returns:
        (format_name, confidence_score)
    """

    # Gather file characteristics
    file_info = {
        "filename": Path(input_path).name,
        "extension": Path(input_path).suffix,
        "companion_files": self._find_companion_files(input_path),
        "file_size": Path(input_path).stat().st_size,
    }

    # If binary file, read header bytes
    if file_info["extension"] in [".bin", ".dat"]:
        with open(input_path, "rb") as f:
            header_bytes = f.read(1024)
            file_info["header_hex"] = header_bytes.hex()[:200]

    system_prompt = """You are an expert at identifying neuroscience data formats.
Analyze file characteristics and determine the most likely format."""

    user_prompt = f"""Identify the data format:

File: {file_info['filename']}
Extension: {file_info['extension']}
Companion files: {file_info['companion_files']}
Size: {file_info['file_size'] / 1024 / 1024:.1f} MB
Header (hex): {file_info.get('header_hex', 'N/A')}

Known formats:
- SpikeGLX: *.ap.bin, *.lf.bin with .meta companion
- OpenEphys: *.continuous or structure.oebin
- Neuropixels: *.imec*.bin with .meta

Return format name and confidence (0-100)."""

    output_schema = {
        "type": "object",
        "properties": {
            "format": {"type": "string"},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"}
        }
    }

    response = await self._llm_service.generate_structured_output(
        prompt=user_prompt,
        output_schema=output_schema,
        system_prompt=system_prompt
    )

    return response["format"], response["confidence"]
```

**Stage 2: Rule-Based Fallback**
```python
def _detect_format_with_rules(self, input_path: str) -> Tuple[str, float]:
    """
    Fallback format detection using regex patterns and file structure.

    Returns:
        (format_name, confidence_score)
    """

    filename = Path(input_path).name
    companion_files = self._find_companion_files(input_path)

    # SpikeGLX detection
    if re.match(r".*\.imec\d+\.(ap|lf)\.bin$", filename):
        meta_file = filename.replace(".bin", ".meta")
        if meta_file in companion_files:
            return "SpikeGLX", 95  # High confidence with .meta

    # OpenEphys detection
    if "structure.oebin" in companion_files:
        return "OpenEphys", 90

    # Generic binary with .meta → likely SpikeGLX
    if filename.endswith(".bin"):
        meta_file = filename.replace(".bin", ".meta")
        if meta_file in companion_files:
            return "SpikeGLX", 70  # Medium confidence

    return "unknown", 0
```

**Format-Specific Conversion Flow**:

```python
async def handle_run_conversion(self, message: MCPMessage, state: GlobalState):
    """
    Execute NWB conversion using detected format.

    Architecture:
    1. Select appropriate NeuroConv interface
    2. Detect available data streams
    3. Map metadata to NWB schema
    4. Run conversion
    5. Calculate checksum
    """

    # Select interface based on detected format
    if state.detected_format == "SpikeGLX":
        from neuroconv.datainterfaces import SpikeGLXRecordingInterface
        interface_class = SpikeGLXRecordingInterface

    elif state.detected_format == "OpenEphys":
        from neuroconv.datainterfaces import OpenEphysRecordingInterface
        interface_class = OpenEphysRecordingInterface

    else:
        return MCPResponse(
            success=False,
            message=f"Unsupported format: {state.detected_format}",
            error="UNSUPPORTED_FORMAT"
        )

    # Detect available data streams
    streams = await self._detect_available_streams(state.input_path)

    # Select optimal stream (prefer AP over LF, exclude SYNC)
    selected_stream = self._select_optimal_stream(streams)

    # Create interface
    interface = interface_class(
        file_path=state.input_path,
        stream_name=selected_stream
    )

    # Map flat metadata to nested NWB structure
    nwb_metadata = await self._map_flat_to_nested_metadata(
        state.metadata
    )

    # Run conversion
    conversion_start = datetime.now()

    output_path = Path(state.output_dir) / "output.nwb"
    interface.run_conversion(
        nwbfile_path=str(output_path),
        metadata=nwb_metadata,
        overwrite=True
    )

    conversion_duration = (datetime.now() - conversion_start).total_seconds()

    # Calculate checksum for integrity verification
    checksum = self._calculate_sha256(output_path)

    # Update state
    state.output_path = str(output_path)
    state.conversion_status = ConversionStatus.COMPLETED
    state.conversion_duration = conversion_duration

    return MCPResponse(
        success=True,
        message=f"✓ Conversion completed in {conversion_duration:.1f}s",
        data={
            "output_path": str(output_path),
            "checksum": checksum,
            "duration_seconds": conversion_duration
        }
    )
```

### Evaluation Agent: Validation & Reporting

**Responsibility**: NWB validation and comprehensive report generation

**Validation Pipeline**:

```python
async def handle_run_validation(self, message: MCPMessage, state: GlobalState):
    """
    Run NWBInspector validation and categorize issues.

    Architecture:
    1. Load NWB file
    2. Run all NWBInspector checks
    3. Categorize by severity
    4. Extract issue details
    5. Analyze with LLM for user-friendly explanations
    """

    from nwbinspector import inspect_nwbfile, Importance

    # Run validation
    validation_start = datetime.now()

    issues = list(inspect_nwbfile(nwbfile_path=state.output_path))

    validation_duration = (datetime.now() - validation_start).total_seconds()

    # Categorize by severity
    critical = [iss for iss in issues if iss.importance == Importance.CRITICAL]
    violations = [iss for iss in issues if iss.importance == Importance.BEST_PRACTICE_VIOLATION]
    suggestions = [iss for iss in issues if iss.importance == Importance.BEST_PRACTICE_SUGGESTION]

    # Determine validation status
    if len(critical) > 0:
        status = ValidationStatus.FAILED
    elif len(violations) > 0:
        status = ValidationStatus.PASSED_WITH_WARNINGS
    else:
        status = ValidationStatus.PASSED

    # Generate detailed issue analysis with LLM
    if self._llm_service and len(issues) > 0:
        issue_analysis = await self._analyze_issues_with_ai(issues, state)
    else:
        issue_analysis = self._analyze_issues_with_rules(issues)

    # Update state
    state.validation_status = status
    state.validation_issues = issues
    state.validation_duration = validation_duration

    return MCPResponse(
        success=True,
        message=self._format_validation_summary(status, critical, violations, suggestions),
        data={
            "status": status.value,
            "total_issues": len(issues),
            "critical": len(critical),
            "violations": len(violations),
            "suggestions": len(suggestions),
            "issue_analysis": issue_analysis
        }
    )
```

**AI-Powered Issue Analysis**:

```python
async def _analyze_issues_with_ai(
    self,
    issues: List[ValidationIssue],
    state: GlobalState
) -> List[Dict[str, Any]]:
    """
    Use LLM to provide user-friendly explanations and fixes.

    For each issue:
    - Explain why it matters
    - Suggest specific fix
    - Provide example of correct format
    """

    analyzed_issues = []

    for issue in issues[:10]:  # Limit to top 10 for token efficiency
        system_prompt = """You are an NWB format expert helping users fix validation issues.
Provide clear, actionable guidance."""

        user_prompt = f"""Analyze this NWB validation issue:

Issue: {issue.message}
Location: {issue.location}
Severity: {issue.importance.name}
Check function: {issue.check_function_name}

Provide:
1. Why this matters for NWB/DANDI compliance
2. Specific fix with example
3. Priority (high/medium/low)
"""

        output_schema = {
            "type": "object",
            "properties": {
                "explanation": {"type": "string"},
                "suggested_fix": {"type": "string"},
                "example": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]}
            }
        }

        analysis = await self._llm_service.generate_structured_output(
            prompt=user_prompt,
            output_schema=output_schema,
            system_prompt=system_prompt
        )

        analyzed_issues.append({
            "issue": issue,
            "analysis": analysis
        })

    return analyzed_issues
```

**Report Generation Architecture**:

```python
async def handle_generate_report(self, message: MCPMessage, state: GlobalState):
    """
    Generate comprehensive reports in PDF, JSON, and text formats.

    Innovation: Workflow trace for scientific reproducibility
    """

    from services.report_service import ReportService

    report_service = ReportService()

    # Build workflow trace
    workflow_trace = await self._build_workflow_trace(state)

    # Generate reports in parallel
    report_paths = await asyncio.gather(
        report_service.generate_pdf_report(state, workflow_trace),
        report_service.generate_json_report(state, workflow_trace),
        report_service.generate_text_report(state, workflow_trace)
    )

    pdf_path, json_path, text_path = report_paths

    return MCPResponse(
        success=True,
        message="✓ Generated validation reports (PDF, JSON, text)",
        data={
            "pdf_report": str(pdf_path),
            "json_report": str(json_path),
            "text_report": str(text_path)
        }
    )

async def _build_workflow_trace(self, state: GlobalState) -> Dict[str, Any]:
    """
    Build complete workflow trace for reproducibility.

    Includes:
    - Input format and files
    - Conversion parameters
    - Technologies and versions
    - Processing steps
    - Metadata sources
    - Data provenance
    """

    import neuroconv
    import spikeinterface
    import pynwb
    import nwbinspector
    import sys

    trace = {
        "input": {
            "format": state.detected_format,
            "file_path": state.input_path,
            "file_size_bytes": Path(state.input_path).stat().st_size,
            "companion_files": self._find_companion_files(state.input_path)
        },
        "conversion": {
            "start_time": state.conversion_start_time.isoformat() if state.conversion_start_time else None,
            "duration_seconds": state.conversion_duration,
            "output_path": state.output_path,
            "output_size_bytes": Path(state.output_path).stat().st_size if state.output_path else None
        },
        "technologies": {
            "neuroconv": neuroconv.__version__,
            "spikeinterface": spikeinterface.__version__,
            "pynwb": pynwb.__version__,
            "nwbinspector": nwbinspector.__version__,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        },
        "processing_steps": [
            {"step": 1, "description": f"Detected {state.detected_format} format"},
            {"step": 2, "description": "Extracted metadata from file headers"},
            {"step": 3, "description": f"Created {state.detected_format}RecordingInterface"},
            {"step": 4, "description": "Mapped user metadata to NWB schema"},
            {"step": 5, "description": "Converted raw data to ElectricalSeries"},
            {"step": 6, "description": f"Added electrode table ({state.num_channels} channels)"},
            {"step": 7, "description": "Validated with NWBInspector"},
            {"step": 8, "description": "Generated comprehensive reports"}
        ],
        "metadata_sources": {
            "user_provided": list(state.metadata.keys()),
            "file_inferred": list(state.inferred_metadata.keys() if hasattr(state, 'inferred_metadata') else []),
            "auto_corrected": list(state.corrections.keys() if hasattr(state, 'corrections') else [])
        },
        "data_provenance": {
            "original_format": state.detected_format,
            "conversion_tool": "Agentic Neurodata Conversion v1.0",
            "conversion_date": datetime.now().isoformat(),
            "nwb_version": "2.x",
            "schema_version": "NWB 2.8.0"
        }
    }

    return trace
```

---

## Supporting Services Architecture

### LLM Service: Anthropic Claude Integration

**Design Pattern**: Structured output generation with schema enforcement

```python
class LLMService:
    """
    Wrapper for Anthropic Claude API with structured output support.

    Key Innovation: JSON schema-based output enforcement
    """

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Generate LLM response conforming to JSON schema.

        Architecture:
        1. Augment prompt with schema requirements
        2. Request JSON output
        3. Parse and validate against schema
        4. Retry if validation fails

        Args:
            prompt: User prompt
            output_schema: JSON schema for output structure
            system_prompt: System instructions
            max_tokens: Maximum response tokens

        Returns:
            Parsed JSON conforming to schema
        """

        # Augment prompt with schema
        full_prompt = f"""{prompt}

IMPORTANT: Respond with valid JSON matching this exact schema:

{json.dumps(output_schema, indent=2)}

Your response must be ONLY the JSON object, no additional text."""

        messages = [{"role": "user", "content": full_prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt or "You are a helpful assistant.",
            messages=messages
        )

        # Extract JSON from response
        content = response.content[0].text

        # Parse JSON
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                raise ValueError(f"LLM did not return valid JSON: {content}")

        # Validate against schema (basic validation)
        self._validate_schema(parsed, output_schema)

        return parsed

    def _validate_schema(self, data: Dict, schema: Dict):
        """Basic schema validation - could use jsonschema library for complete validation."""
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Type checking for properties
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get("type")
                # Basic type validation...
```

**Prompt Template System**:

```python
class PromptTemplates:
    """
    Centralized prompt templates with variable interpolation.

    Design Decision: Keep prompts in code for version control
    """

    @staticmethod
    def metadata_parsing_prompt(field_name: str, field_schema: MetadataFieldSchema) -> str:
        """Generate prompt for parsing a specific metadata field."""
        return f"""Parse and normalize this metadata field for NWB format.

Field: {field_name}
Description: {field_schema.description}
Expected format: {field_schema.format or field_schema.field_type.value}
Example: {field_schema.example}

Normalization rules:
{chr(10).join(f"  '{k}' → '{v}'" for k, v in field_schema.normalization_rules.items())}

Provide the normalized value and confidence score (0-100)."""

    @staticmethod
    def format_detection_prompt(file_info: Dict[str, Any]) -> str:
        """Generate prompt for format detection."""
        return f"""Identify the neuroscience data format from these file characteristics.

Filename: {file_info['filename']}
Extension: {file_info['extension']}
Companion files: {', '.join(file_info['companion_files'])}
File size: {file_info['size_mb']:.1f} MB

Known formats:
- SpikeGLX: *.ap.bin or *.lf.bin with matching .meta file
- OpenEphys: *.continuous or structure.oebin present
- Neuropixels: *.imec*.bin with .meta

Provide format name and confidence (0-100)."""
```

### Schema Registry: Single Source of Truth

**Design Pattern**: Centralized metadata schema with rich field definitions

```python
class NWBDANDISchema:
    """
    Complete schema definition for NWB/DANDI metadata.

    Architecture:
    - Single source of truth for all metadata rules
    - Used by parser, validator, documentation, UI
    - Extensible for future fields
    """

    def __init__(self):
        self._fields = self._initialize_fields()

    def _initialize_fields(self) -> List[MetadataFieldSchema]:
        """Define all metadata fields with complete specifications."""

        return [
            MetadataFieldSchema(
                name="experimenter",
                description="Person(s) who conducted the experiment",
                field_type=FieldType.STRING_LIST,
                requirement_level=RequirementLevel.RECOMMENDED,
                format="LastName, FirstName",
                example="Smith, Jane",
                normalization_rules={
                    "Dr. Jane Smith": "Smith, Jane",
                    "Jane Smith": "Smith, Jane",
                    "J. Smith": "Smith, J."
                },
                validation_regex=r"^[A-Z][a-z]+,\s[A-Z]\.?.*$",
                nwb_path="/general/experimenter"
            ),

            MetadataFieldSchema(
                name="institution",
                description="Institution where experiment was performed",
                field_type=FieldType.STRING,
                requirement_level=RequirementLevel.RECOMMENDED,
                format="Full official name",
                example="Massachusetts Institute of Technology",
                normalization_rules={
                    "MIT": "Massachusetts Institute of Technology",
                    "Stanford": "Stanford University",
                    "Harvard": "Harvard University",
                    "Berkeley": "University of California, Berkeley"
                },
                nwb_path="/general/institution"
            ),

            MetadataFieldSchema(
                name="age",
                description="Subject age at time of experiment",
                field_type=FieldType.STRING,
                requirement_level=RequirementLevel.REQUIRED,
                format="ISO 8601 duration (e.g., 'P90D' for 90 days)",
                example="P56D",
                normalization_rules={
                    "8 weeks": "P56D",
                    "2 months": "P60D",
                    "3 months": "P90D",
                    "adult": "P90D"  # Guessed - needs review
                },
                validation_regex=r"^P\d+[DWMY]$",
                nwb_path="/general/subject/age"
            ),

            # ... more fields
        ]

    def get_field(self, field_name: str) -> Optional[MetadataFieldSchema]:
        """Get schema for specific field."""
        return next((f for f in self._fields if f.name == field_name), None)

    def get_required_fields(self) -> List[MetadataFieldSchema]:
        """Get all required fields."""
        return [
            f for f in self._fields
            if f.requirement_level == RequirementLevel.REQUIRED
        ]

    def get_all_fields(self) -> List[MetadataFieldSchema]:
        """Get all defined fields."""
        return self._fields

    def normalize_value(self, field_name: str, value: str) -> str:
        """Apply normalization rules to a value."""
        field = self.get_field(field_name)
        if not field:
            return value

        return field.normalization_rules.get(value, value)
```

**Field Schema Definition**:

```python
@dataclass
class MetadataFieldSchema:
    """Complete specification for one metadata field."""

    name: str                                    # Field name (e.g., "experimenter")
    description: str                             # Human-readable description
    field_type: FieldType                        # Data type (string, number, list, etc.)
    requirement_level: RequirementLevel          # required, recommended, optional
    format: Optional[str]                        # Format specification
    example: str                                 # Example value
    normalization_rules: Dict[str, str]          # Input → normalized mapping
    validation_regex: Optional[str] = None       # Validation pattern
    nwb_path: Optional[str] = None               # Path in NWB file
    allowed_values: Optional[List[str]] = None   # Enum of allowed values
    units: Optional[str] = None                  # Units (for numeric fields)

class FieldType(str, Enum):
    """Data types for metadata fields."""
    STRING = "string"
    STRING_LIST = "string_list"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DURATION = "duration"

class RequirementLevel(str, Enum):
    """Requirement levels following DANDI standards."""
    REQUIRED = "required"           # Must be provided
    RECOMMENDED = "recommended"     # Should be provided for DANDI
    OPTIONAL = "optional"           # Nice to have
```

---

## State Management Architecture

### Global State: Centralized Workflow State

**Design Decision**: Single global state object passed to all agents

**Why Global State?**
- Simplifies inter-agent communication (no complex message passing for state)
- Enables atomic state transitions
- Facilitates debugging (single point to inspect)
- Easy to serialize for persistence

**Trade-offs**:
- Risk of tight coupling (mitigated by clear state contracts)
- Requires careful synchronization (currently single-threaded, OK)
- Future: Consider state immutability or copy-on-write

```python
@dataclass
class GlobalState:
    """
    Complete workflow state shared across all agents.

    Design: Organized by lifecycle phase
    """

    # File Management
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    output_dir: str = "/tmp/outputs"
    uploaded_files: List[str] = field(default_factory=list)

    # Format Detection
    detected_format: Optional[str] = None
    format_confidence: float = 0.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    inferred_metadata: Dict[str, Any] = field(default_factory=dict)
    metadata_warnings: Dict[str, Dict] = field(default_factory=dict)

    # Conversion
    conversion_status: ConversionStatus = ConversionStatus.PENDING
    conversion_start_time: Optional[datetime] = None
    conversion_duration: Optional[float] = None

    # Validation
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_issues: List[Any] = field(default_factory=list)
    validation_duration: Optional[float] = None

    # Conversation Management
    conversation_phase: ConversationPhase = ConversationPhase.INITIAL
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata_requests_count: int = 0
    user_skip_count: int = 0

    # Logging
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def add_log(self, level: LogLevel, message: str, context: Optional[Dict] = None):
        """Add timestamped log entry."""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
            "context": context or {}
        })

    def add_conversation_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_recent_user_messages(self, n: int = 5) -> List[str]:
        """Get last N user messages."""
        user_messages = [
            msg["content"] for msg in self.conversation_history
            if msg["role"] == "user"
        ]
        return user_messages[-n:]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for persistence or API responses."""
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "detected_format": self.detected_format,
            "format_confidence": self.format_confidence,
            "metadata": self.metadata,
            "conversion_status": self.conversion_status.value,
            "validation_status": self.validation_status.value,
            "conversation_phase": self.conversation_phase.value,
            "logs": self.logs[-100:],  # Last 100 logs
        }
```

### Workflow State Machine

**State Transitions**:

```python
class ConversationPhase(str, Enum):
    """Conversation workflow phases."""

    INITIAL = "initial"
    AWAITING_FILES = "awaiting_files"
    FILES_RECEIVED = "files_received"
    FORMAT_DETECTION = "format_detection"
    FORMAT_DETECTED = "format_detected"
    METADATA_COLLECTION = "metadata_collection"
    AWAITING_USER_INPUT = "awaiting_user_input"
    METADATA_COMPLETE = "metadata_complete"
    CONVERTING = "converting"
    CONVERSION_COMPLETE = "conversion_complete"
    VALIDATING = "validating"
    VALIDATION_COMPLETE = "validation_complete"
    AWAITING_RETRY_DECISION = "awaiting_retry_decision"
    GENERATING_REPORTS = "generating_reports"
    COMPLETE = "complete"
    ERROR = "error"

class WorkflowStateManager:
    """Manage valid state transitions and enforce workflow constraints."""

    VALID_TRANSITIONS = {
        ConversationPhase.INITIAL: [ConversationPhase.AWAITING_FILES],
        ConversationPhase.AWAITING_FILES: [ConversationPhase.FILES_RECEIVED],
        ConversationPhase.FILES_RECEIVED: [ConversationPhase.FORMAT_DETECTION],
        ConversationPhase.FORMAT_DETECTION: [
            ConversationPhase.FORMAT_DETECTED,
            ConversationPhase.ERROR
        ],
        ConversationPhase.FORMAT_DETECTED: [ConversationPhase.METADATA_COLLECTION],
        ConversationPhase.METADATA_COLLECTION: [
            ConversationPhase.AWAITING_USER_INPUT,
            ConversationPhase.METADATA_COMPLETE
        ],
        ConversationPhase.AWAITING_USER_INPUT: [
            ConversationPhase.METADATA_COLLECTION,  # More questions
            ConversationPhase.METADATA_COMPLETE     # Done collecting
        ],
        ConversationPhase.METADATA_COMPLETE: [ConversationPhase.CONVERTING],
        ConversationPhase.CONVERTING: [
            ConversationPhase.CONVERSION_COMPLETE,
            ConversationPhase.ERROR
        ],
        ConversationPhase.CONVERSION_COMPLETE: [ConversationPhase.VALIDATING],
        ConversationPhase.VALIDATING: [ConversationPhase.VALIDATION_COMPLETE],
        ConversationPhase.VALIDATION_COMPLETE: [
            ConversationPhase.AWAITING_RETRY_DECISION,  # Has issues
            ConversationPhase.GENERATING_REPORTS        # Passed
        ],
        ConversationPhase.AWAITING_RETRY_DECISION: [
            ConversationPhase.METADATA_COLLECTION,  # Fix metadata
            ConversationPhase.GENERATING_REPORTS    # Accept anyway
        ],
        ConversationPhase.GENERATING_REPORTS: [ConversationPhase.COMPLETE],
        ConversationPhase.ERROR: [
            ConversationPhase.AWAITING_FILES,  # Restart
            ConversationPhase.METADATA_COLLECTION  # Retry with fixes
        ]
    }

    @classmethod
    def can_transition(
        cls,
        current: ConversationPhase,
        next_phase: ConversationPhase
    ) -> bool:
        """Check if transition is valid."""
        valid_next = cls.VALID_TRANSITIONS.get(current, [])
        return next_phase in valid_next

    @classmethod
    def transition(
        cls,
        state: GlobalState,
        next_phase: ConversationPhase
    ) -> bool:
        """Attempt state transition with validation."""
        if not cls.can_transition(state.conversation_phase, next_phase):
            state.add_log(
                LogLevel.ERROR,
                f"Invalid state transition: {state.conversation_phase} → {next_phase}"
            )
            return False

        state.add_log(
            LogLevel.INFO,
            f"State transition: {state.conversation_phase} → {next_phase}"
        )

        state.conversation_phase = next_phase
        return True
```

---

## Data Flow Patterns

### Complete End-to-End Flow

```
1. USER UPLOADS FILE
   ↓
   Frontend: FormData with file
   ↓
   Backend: POST /api/upload
   ↓
   Save file to /tmp/uploads/{session_id}/{filename}
   ↓
   Update state.input_path, state.uploaded_files
   ↓
   Return session_id to frontend

2. USER INITIATES CONVERSION
   ↓
   Frontend: WebSocket message {type: "user_message", message: "start conversion"}
   ↓
   Backend: WebSocket handler → Conversation Agent
   ↓
   Conversation Agent: handle_start_conversion()
     ├─ Send "detect_format" → Conversion Agent
     │  ├─ AI format detection (if LLM available)
     │  ├─ Rule-based fallback
     │  └─ Return format + confidence
     ├─ Update state.detected_format
     ├─ Infer metadata from files (MetadataInferenceEngine)
     ├─ Identify missing required fields
     ├─ Generate dynamic metadata request (LLM)
     └─ Return request message to user

3. USER PROVIDES METADATA
   ↓
   Frontend: WebSocket {message: "I'm Dr. Jane Smith from MIT..."}
   ↓
   Conversation Agent: handle_conversational_response()
     ├─ Parse natural language (IntelligentMetadataParser)
     │  ├─ LLM batch parsing with confidence scores
     │  └─ Fallback to regex patterns
     ├─ Generate confirmation message
     └─ Return confirmation to user

4. USER CONFIRMS (or skips)
   ↓
   Frontend: WebSocket {message: "yes"} or {message: ""}
   ↓
   Conversation Agent: Detect confirmation
     ├─ Apply metadata with confidence tiers
     │  ├─ High (≥80%): Silent apply
     │  ├─ Medium (50-79%): Apply with note
     │  └─ Low (<50%): Apply with warning flag
     ├─ Update state.metadata
     ├─ Send "run_conversion" → Conversion Agent
     └─ Return "Converting..." status

5. CONVERSION AGENT CONVERTS
   ↓
   Conversion Agent: handle_run_conversion()
     ├─ Select NeuroConv interface (SpikeGLX, OpenEphys, etc.)
     ├─ Detect available streams
     ├─ Map flat metadata → nested NWB structure
     ├─ Run interface.run_conversion()
     ├─ Calculate SHA256 checksum
     ├─ Update state.output_path, state.conversion_status
     └─ Return output_path

6. CONVERSATION AGENT TRIGGERS VALIDATION
   ↓
   Send "run_validation" → Evaluation Agent

7. EVALUATION AGENT VALIDATES
   ↓
   Evaluation Agent: handle_run_validation()
     ├─ Run NWBInspector.inspect_nwbfile()
     ├─ Categorize issues (critical, violations, suggestions)
     ├─ AI analysis of issues (explanations, fixes)
     ├─ Determine validation_status
     ├─ Update state.validation_status, state.validation_issues
     └─ Return validation summary

8. CONVERSATION AGENT GENERATES REPORTS
   ↓
   Send "generate_report" → Evaluation Agent
   ↓
   Evaluation Agent: handle_generate_report()
     ├─ Build workflow trace
     ├─ Generate PDF report (ReportLab)
     ├─ Generate JSON report
     ├─ Generate text report
     └─ Return report paths

9. RETURN TO USER
   ↓
   Conversation Agent → WebSocket → Frontend
   ↓
   Display: Download links for NWB file + reports
```

### Message Flow Example: Metadata Parsing

```python
# Frontend sends user message
ws.send(JSON.stringify({
    type: "user_message",
    message: "I'm Dr. Jane Smith from MIT studying 8 week old mice"
}))

# Backend WebSocket handler
async def websocket_endpoint(websocket: WebSocket):
    data = await websocket.receive_json()

    # Route to Conversation Agent
    message = MCPMessage(
        action="conversational_response",
        context={"user_message": data["message"]}
    )

    response = await mcp_server.route_message(
        to_agent="conversation_agent",
        message=message,
        state=session_state
    )

    # Conversation Agent processes
    async def handle_conversational_response(self, message, state):
        user_msg = message.context["user_message"]

        # Parse with Intelligent Metadata Parser
        parsed_fields = await self._metadata_parser.parse_natural_language_batch(
            user_msg, state
        )

        # LLM Service called internally
        # Returns: [
        #   ParsedField(experimenter="Smith, Jane", confidence=95),
        #   ParsedField(institution="MIT → Massachusetts Institute of Technology", confidence=98),
        #   ParsedField(age="8 weeks → P56D", confidence=92),
        #   ParsedField(species="mice → Mus musculus", confidence=100)
        # ]

        # Generate confirmation
        confirmation_msg = self._metadata_parser.generate_confirmation_message(
            parsed_fields
        )

        # Store for later application
        state.pending_parsed_fields = parsed_fields

        return MCPResponse(
            success=True,
            message=confirmation_msg,
            data={"needs_confirmation": True}
        )

# Send response back to user
await websocket.send_json({
    "type": "assistant_message",
    "message": response.message,
    "needs_user_input": True
})
```

---

## Performance Optimizations

### Async/Await Architecture

**Design Decision**: Fully async architecture for non-blocking I/O

```python
# All agent handlers are async
async def handle_message(self, message: MCPMessage, state: GlobalState):
    # Can await multiple operations concurrently
    results = await asyncio.gather(
        self._detect_format(state.input_path),
        self._infer_metadata(state.input_path),
        self._analyze_file_structure(state.input_path)
    )
```

**Benefits**:
- Efficient LLM API calls (no blocking)
- Multiple file operations in parallel
- WebSocket connections don't block server

### Caching Strategies

**File Analysis Caching**:
```python
class ConversionAgent:
    def __init__(self):
        self._format_cache = {}  # file_path → (format, confidence)
        self._metadata_cache = {}  # file_path → inferred_metadata

    async def _detect_format(self, file_path: str):
        # Check cache first
        if file_path in self._format_cache:
            return self._format_cache[file_path]

        # Perform detection
        format, confidence = await self._detect_format_with_ai(file_path)

        # Cache result
        self._format_cache[file_path] = (format, confidence)

        return format, confidence
```

**LLM Response Caching** (Future):
```python
# For repeated prompts with same input
class LLMService:
    def __init__(self):
        self._response_cache = {}  # hash(prompt+schema) → response

    async def generate_structured_output(self, prompt, schema):
        cache_key = hashlib.sha256(f"{prompt}{json.dumps(schema)}".encode()).hexdigest()

        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        response = await self._call_llm(prompt, schema)
        self._response_cache[cache_key] = response
        return response
```

### Memory Management

**Conversation History Pruning**:
```python
class GlobalState:
    MAX_CONVERSATION_HISTORY = 50  # Last 50 messages

    def add_conversation_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Prune old messages
        if len(self.conversation_history) > self.MAX_CONVERSATION_HISTORY:
            # Keep first 5 (context) + last 45 (recent)
            self.conversation_history = (
                self.conversation_history[:5] +
                self.conversation_history[-45:]
            )
```

---

## Security & Error Handling

### Input Validation

**File Upload Security**:
```python
@app.post("/api/upload")
async def upload_file(file: UploadFile):
    # File size limit
    MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
    file_size = 0

    # Allowed extensions
    ALLOWED_EXTENSIONS = {".bin", ".meta", ".continuous", ".dat", ".oebin"}
    ext = Path(file.filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not allowed: {ext}")

    # Secure filename (prevent path traversal)
    safe_filename = secure_filename(file.filename)

    # Save with size checking
    save_path = Path(UPLOAD_DIR) / session_id / safe_filename

    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                f.close()
                save_path.unlink()
                raise HTTPException(413, "File too large")
            f.write(chunk)
```

**User Input Sanitization**:
```python
def sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    # Remove control characters
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

    # Limit length
    MAX_INPUT_LENGTH = 10000
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]

    return text.strip()
```

### Error Recovery Patterns

**Graceful Degradation**:
```python
async def parse_natural_language_batch(self, user_input: str, state: GlobalState):
    """Parse with LLM, fall back to regex on failure."""

    if not self.llm_service:
        state.add_log(LogLevel.WARNING, "LLM unavailable, using fallback parser")
        return self._fallback_parse_batch(user_input, state)

    try:
        # Try LLM parsing
        return await self._llm_parse_batch(user_input, state)

    except anthropic.APIError as e:
        state.add_log(LogLevel.ERROR, f"LLM API error: {e}, using fallback")
        return self._fallback_parse_batch(user_input, state)

    except Exception as e:
        state.add_log(LogLevel.ERROR, f"Unexpected error in LLM parsing: {e}")
        # Fall back to regex
        return self._fallback_parse_batch(user_input, state)
```

**Retry Logic with Exponential Backoff**:
```python
async def call_llm_with_retry(
    self,
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0
):
    """Call LLM with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            return await self._call_llm(prompt)

        except anthropic.RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            delay = base_delay * (2 ** attempt)
            logger.warning(f"Rate limited, retrying in {delay}s...")
            await asyncio.sleep(delay)

        except anthropic.APIConnectionError as e:
            if attempt == max_retries - 1:
                raise

            delay = base_delay * (2 ** attempt)
            logger.warning(f"Connection error, retrying in {delay}s...")
            await asyncio.sleep(delay)
```

---

## Testing Strategy

### Unit Testing Architecture

**Agent Testing with Mocked MCP**:
```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for agent testing."""
    server = Mock()
    server.route_message = AsyncMock()
    return server

@pytest.fixture
def mock_llm_service():
    """Mock LLM service for deterministic testing."""
    service = Mock()
    service.generate_structured_output = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_metadata_parsing_high_confidence(mock_llm_service):
    """Test metadata parsing with high confidence result."""

    # Setup mock LLM response
    mock_llm_service.generate_structured_output.return_value = {
        "fields": [
            {
                "field_name": "experimenter",
                "raw_value": "Dr. Jane Smith",
                "normalized_value": "Smith, Jane",
                "confidence": 95,
                "reasoning": "Clear name with title",
                "needs_review": False
            }
        ]
    }

    parser = IntelligentMetadataParser(mock_llm_service)
    state = GlobalState()

    # Test
    result = await parser.parse_natural_language_batch(
        "I'm Dr. Jane Smith",
        state
    )

    # Verify
    assert len(result) == 1
    assert result[0].field_name == "experimenter"
    assert result[0].parsed_value == "Smith, Jane"
    assert result[0].confidence == 95
    assert result[0].confidence_level == ConfidenceLevel.HIGH
```

### Integration Testing

**End-to-End Workflow Test**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_conversion_workflow():
    """Test complete workflow from upload to report generation."""

    # Setup
    mcp_server = MCPServer()
    llm_service = LLMService(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Register agents
    conversation_agent = ConversationAgent(mcp_server, llm_service)
    conversion_agent = ConversionAgent(mcp_server, llm_service)
    evaluation_agent = EvaluationAgent(mcp_server, llm_service)

    mcp_server.register_agent("conversation_agent", conversation_agent)
    mcp_server.register_agent("conversion_agent", conversion_agent)
    mcp_server.register_agent("evaluation_agent", evaluation_agent)

    state = GlobalState()

    # 1. Upload file
    test_file = "tests/data/Noise4Sam_g0_t0.imec0.ap.bin"
    state.input_path = test_file

    # 2. Start conversion
    msg = MCPMessage(action="start_conversion", context={})
    response = await conversation_agent.handle_message(msg, state)

    assert response.success
    assert state.detected_format == "SpikeGLX"

    # 3. Provide metadata
    msg = MCPMessage(
        action="conversational_response",
        context={"user_message": "Jane Smith at MIT, 8 week old male mouse"}
    )
    response = await conversation_agent.handle_message(msg, state)

    assert response.success
    assert state.metadata["experimenter"] == "Smith, Jane"

    # 4. Confirm and convert
    msg = MCPMessage(
        action="conversational_response",
        context={"user_message": "yes"}
    )
    response = await conversation_agent.handle_message(msg, state)

    assert state.conversion_status == ConversionStatus.COMPLETED
    assert Path(state.output_path).exists()

    # 5. Validate
    assert state.validation_status in [
        ValidationStatus.PASSED,
        ValidationStatus.PASSED_WITH_WARNINGS
    ]

    # 6. Verify reports generated
    assert state.pdf_report_path and Path(state.pdf_report_path).exists()
    assert state.json_report_path and Path(state.json_report_path).exists()
```

---

## Deployment Architecture

### Production Configuration

```python
# config/production.py

ENVIRONMENT = "production"

# Server
HOST = "0.0.0.0"
PORT = 8000
WORKERS = 4
LOG_LEVEL = "INFO"

# File Storage
UPLOAD_DIR = "/data/uploads"
OUTPUT_DIR = "/data/outputs"
MAX_FILE_SIZE_GB = 10

# LLM Service
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_MODEL = "claude-3-5-sonnet-20241022"
LLM_MAX_RETRIES = 3

# Session Management
SESSION_TIMEOUT_MINUTES = 30
CLEANUP_INTERVAL_HOURS = 24

# Rate Limiting
API_RATE_LIMIT = "100/minute"
WEBSOCKET_MESSAGE_LIMIT = "10/second"

# Security
ALLOWED_ORIGINS = ["https://nwb-converter.example.com"]
SSL_CERT_PATH = "/etc/ssl/certs/server.crt"
SSL_KEY_PATH = "/etc/ssl/private/server.key"
```

### Docker Deployment

```dockerfile
# Dockerfile

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pixi.toml pixi.lock ./
RUN pip install pixi && pixi install --frozen

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose ports
EXPOSE 8000

# Run server
CMD ["pixi", "run", "start-prod"]
```

---

## Future Architecture Enhancements

### Distributed Agent Processing

**Current**: All agents run in same process
**Future**: Distribute agents across workers

```python
# Redis-based message queue
class DistributedMCPServer:
    """MCP server using Redis for cross-process communication."""

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.agents = {}

    async def route_message(self, to_agent: str, message: MCPMessage, state: GlobalState):
        """Route message via Redis queue."""

        # Serialize message and state
        msg_data = {
            "message": message.to_dict(),
            "state": state.to_dict()
        }

        # Push to agent's queue
        queue_name = f"agent:{to_agent}:inbox"
        await self.redis.lpush(queue_name, json.dumps(msg_data))

        # Wait for response
        response_queue = f"agent:{to_agent}:outbox:{message.request_id}"
        response_data = await self.redis.brpop(response_queue, timeout=60)

        if not response_data:
            raise TimeoutError(f"Agent {to_agent} did not respond")

        return MCPResponse.from_dict(json.loads(response_data[1]))
```

### Machine Learning Enhancements

**Confidence Calibration Model**:
```python
class ConfidenceCalibrator:
    """ML model to calibrate LLM confidence scores."""

    def __init__(self):
        self.model = LogisticRegression()
        self.trained = False

    def train(self, training_data: List[Tuple[float, bool]]):
        """
        Train on (predicted_confidence, actual_correctness) pairs.

        Args:
            training_data: [(95, True), (60, False), (80, True), ...]
        """
        X = np.array([conf for conf, _ in training_data]).reshape(-1, 1)
        y = np.array([correct for _, correct in training_data])

        self.model.fit(X, y)
        self.trained = True

    def calibrate(self, llm_confidence: float) -> float:
        """
        Convert LLM's confidence to calibrated probability.

        Example:
            LLM says 80% → Calibrated 65% (based on actual success rate)
        """
        if not self.trained:
            return llm_confidence  # Return uncalibrated

        prob = self.model.predict_proba([[llm_confidence]])[0][1]
        return prob * 100
```

---

## Appendix: Key Files Reference

### Backend Structure
```
backend/
├── src/
│   ├── agents/
│   │   ├── conversation_agent.py          # Workflow orchestration
│   │   ├── conversion_agent.py            # Format detection & conversion
│   │   ├── evaluation_agent.py            # Validation & reporting
│   │   ├── intelligent_metadata_parser.py # Natural language parsing
│   │   ├── metadata_inference.py          # File-based inference
│   │   ├── smart_autocorrect.py           # Error fixing
│   │   ├── nwb_dandi_schema.py            # Schema definitions
│   │   └── conversational_handler.py      # Conversation logic
│   ├── api/
│   │   └── main.py                        # FastAPI application
│   ├── models/
│   │   ├── state.py                       # GlobalState & enums
│   │   ├── api.py                         # API request/response models
│   │   └── mcp.py                         # MCP message models
│   └── services/
│       ├── llm_service.py                 # LLM integration
│       ├── mcp_server.py                  # Message routing
│       └── report_service.py              # Report generation
└── tests/
    ├── unit/                               # Unit tests
    ├── integration/                        # Integration tests
    └── fixtures/                           # Test data
```

### Critical Integration Points

1. **LLM Service ↔ All Agents**: All intelligent features depend on LLM service
2. **MCP Server ↔ Agents**: Message routing enables loose coupling
3. **GlobalState ↔ All Components**: Shared state enables coordination
4. **Schema ↔ Parser/Validator**: Schema drives both parsing and validation
5. **WebSocket ↔ Conversation Agent**: Real-time user interaction

---

**END OF DOCUMENT**