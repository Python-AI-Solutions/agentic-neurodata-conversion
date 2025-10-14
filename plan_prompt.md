# Plan Prompt: Multi-Agent NWB Conversion Pipeline

This prompt should be used with the `/plan` command to generate an implementation plan based on the `specify_prompt.md` requirements.

## Context for Planning

You are creating an implementation plan for a **model-agnostic, multi-agent NWB conversion system** that follows strict architectural constraints. Review the requirements in `specify_prompt.md` and the constitution at `.specify/memory/constitution.md`.

## Key Technical Decisions (Already Made)

### Architecture Decisions

**MCP Implementation:**
- Use **MCP Python package** (`mcp>=1.0.0`) for model-agnostic server
- **NOT using Claude Agent SDK** (it only works with Claude models)
- System must support ANY LLM provider (Claude, OpenAI, local models, etc.)

**Agent Deployment:**
- Agents run as **separate processes** (microservices architecture)
- Each agent is an independent Python process
- Communication via MCP protocol through central server
- Agents are **stateless** - all state in session context

**Communication Layer:**
- **REST API + HTTP** for user interaction and agent communication
- WebSockets are out of scope for MVP
- Port **3000** for MCP server (configurable)

**Context Storage:**
- **Redis** for fast access (primary cache)
- **Filesystem** (JSON files) for persistence (backup)
- Write-through strategy: write to both Redis and disk simultaneously
- PostgreSQL is out of scope for MVP

### Model Configuration

**Per-Agent LLM Configuration:**
```env
# Each agent can use a different model
CONVERSATION_AGENT_LLM_PROVIDER=anthropic
CONVERSATION_AGENT_MODEL=claude-3-5-sonnet-20250929
CONVERSATION_AGENT_API_KEY=sk-ant-...

CONVERSION_AGENT_LLM_PROVIDER=anthropic
CONVERSION_AGENT_MODEL=claude-3-5-sonnet-20250929
CONVERSION_AGENT_API_KEY=sk-ant-...

EVALUATION_AGENT_LLM_PROVIDER=anthropic
EVALUATION_AGENT_MODEL=claude-3-5-sonnet-20250929
EVALUATION_AGENT_API_KEY=sk-ant-...
```

**LLM Integration:**
- Direct API calls to provider SDKs (Anthropic SDK, OpenAI SDK)
- No abstraction layer (LiteLLM, LangChain) for MVP
- Each agent handles API calls directly based on configured provider

### Data Format Support

**MVP Scope:**
- **OpenEphys format ONLY**
- Other formats (Blackrock, Intan, SpikeGLX) are post-MVP

**Format Detection:**
- Hybrid approach:
  - File extension for binary data (.continuous)
  - Content inspection for metadata (settings.xml, channel maps)
- Validate OpenEphys structure:
  - Check for settings.xml presence
  - Validate continuous recording files exist
  - Verify channel configuration is readable

### Testing Strategy

**No Mock Services:**
- Test with REAL services we build
- Build components in dependency order so earlier components can be tested by later ones
- Unit tests use real NeuroConv and NWB Inspector libraries (no mocking)

**Coverage Requirements:**
- All agent message handlers: **≥90% coverage** (critical paths)
- Other components: **≥85% coverage**

**Test Data:**
- Create small synthetic OpenEphys datasets (~1MB) for testing
- DataLad is out of scope for MVP (no test dataset management via DataLad)

### User Interface

**REST API Endpoints:**
- FastAPI endpoints that return prompts for user interaction
- No CLI stdin/stdout interaction
- No WebSocket chat interface for MVP

**Example Flow:**
```
POST /api/v1/sessions/initialize
  → Returns: session_id + prompt for metadata

POST /api/v1/sessions/{id}/metadata
  → Returns: acknowledgment + next step

GET /api/v1/sessions/{id}/status
  → Returns: current workflow stage + progress

GET /api/v1/sessions/{id}/result
  → Returns: NWB file path + validation report
```

### Metadata Validation

**Basic validation for MVP:**
- Non-empty strings
- Valid date formats (ISO 8601)
- Basic type checking
- No domain-specific validation (taxonomy, ontologies) for MVP

### Performance Requirements

**Dataset Size:**
- Handle up to 10GB datasets
- **Warn users for files >10GB but allow processing**

**Concurrency:**
- **Single session only** for MVP
- Concurrent sessions are post-MVP feature

**Recovery:**
- **Session-level recovery**: system can restart from any agent failure point
- Context persisted to disk enables recovery after server restarts

### Error Handling

**Error Detail Level:**
- Include ALL details: error message, suggested fix, stack trace, session context snapshot
- Present concisely but completely
- Use LLM to generate user-friendly error messages with actionable remediation steps

### Logging

**Configuration:**
- Python standard logging
- JSON format for structured logs
- No advanced logging libraries (structlog) for MVP

### Out of Scope for MVP

**Explicitly NOT included:**
- ❌ DataLad integration (data management, provenance tracking)
- ❌ Knowledge graphs (RDF, LinkML, PROV-O)
- ❌ Claude Agent SDK (model-specific)
- ❌ LiteLLM, LangChain, LlamaIndex (abstraction layers)
- ❌ Multiple data format support (only OpenEphys)
- ❌ Concurrent session handling
- ❌ WebSocket communication
- ❌ PostgreSQL database
- ❌ DANDI archive upload

## Planning Instructions

Create an implementation plan that includes:

### 1. System Architecture
- High-level architecture diagram showing:
  - MCP Server (FastAPI + MCP package)
  - Three agent processes (Conversation, Conversion, Evaluation)
  - Redis + filesystem context storage
  - Communication flows
- Component responsibilities and boundaries
- Process deployment model

### 2. Technology Stack
- Core dependencies with versions (from pixi.toml)
- Required Python packages:
  - `mcp>=1.0.0` (MCP protocol)
  - `fastapi>=0.100.0` (REST API)
  - `redis>=5.0.0` (context cache)
  - `anthropic>=0.18.0` (Claude API)
  - `openai>=1.0.0` (OpenAI API)
  - `neuroconv>=0.4.0` (NWB conversion)
  - `nwbinspector>=0.4.0` (validation)
- Explicitly list excluded technologies

### 3. Data Models and Schemas
- Session context structure (SessionContext pydantic model)
- MCP message format (MCPMessage pydantic model)
- API request/response models
- Validation rules
- Context lifecycle management

### 4. Component Implementation Details

**MCP Server:**
- FastAPI application structure
- Message routing logic
- Agent registry for agent discovery
- Context manager (Redis + filesystem)
- REST API endpoints
- Health checks

**Base Agent Class:**
- Common agent functionality
- MCP client for server communication
- LLM provider abstraction (direct API calls)
- Message handling interface
- Agent registration with server

**Conversation Agent:**
- Session initialization
- OpenEphys format detection (hybrid: extension + content)
- Dataset validation (settings.xml, .continuous files)
- Metadata collection via LLM prompts
- Preprocessing results generation
- Handoff to conversion agent

**Conversion Agent:**
- NeuroConv OpenEphysRecordingInterface integration
- Metadata preparation for NWB format
- Conversion execution with progress monitoring
- Error capture with full details (message, trace, context)
- LLM-generated user-friendly error messages
- Handoff to evaluation agent

**Evaluation Agent:**
- NWB Inspector integration
- Comprehensive validation checks (schema, best practices, integrity)
- Report generation (JSON format)
- LLM-powered validation summaries
- Results return to conversation agent

### 5. Configuration Management
- Environment variable structure (per-agent model config)
- Settings module using pydantic-settings
- .env.example template
- Configuration validation

### 6. Testing Strategy
- Test structure (unit, integration, e2e)
- No mocks - test with real services
- Build order to enable testing without mocks:
  1. Context manager
  2. MCP server
  3. Base agent
  4. Individual agents
  5. Integration tests
- Test data creation (synthetic OpenEphys datasets)
- Coverage requirements per component

### 7. Deployment
- Development setup instructions
- Process management (starting server + 3 agent processes)
- Redis setup
- Environment configuration
- Health check endpoints

### 8. Implementation Roadmap
- Break down into phases (weeks)
- Dependency order for building components
- Milestones and checkpoints
- Ensure tests can be written for each phase

### 9. API Contract Examples
- Session initialization request/response
- Metadata submission request/response
- Status check response
- Result retrieval response

### 10. Risks and Mitigations
- Technical risks (LLM rate limits, large datasets, Redis failures)
- Process risks (scope creep, testing delays)
- Mitigation strategies

## Constitution Compliance Checklist

Ensure the plan adheres to:
- ✅ MCP-centric architecture (all communication through MCP server)
- ✅ TDD workflow (tests before implementation)
- ✅ Feature boundaries (no direct agent-to-agent calls)
- ✅ Quality gates (≥90% coverage for critical paths, ≥85% overall)
- ✅ Stateless agents with context management
- ✅ Logging requirements (structured, JSON format)
- ✅ Error handling (comprehensive error details)

## Expected Output

The plan should be:
- **Comprehensive**: Cover all aspects of implementation
- **Specific**: Include code examples, schemas, file structures
- **Testable**: Clear testing approach for each component
- **Pragmatic**: Focus on MVP scope, defer post-MVP features
- **Implementation-ready**: Developers can start building immediately after reading

The plan should be detailed enough that running `/tasks` afterward will generate a clear, dependency-ordered task breakdown.
