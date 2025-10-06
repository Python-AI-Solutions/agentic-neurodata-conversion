# Phase 0: Technology Research and Decisions

**Feature**: MCP Server Architecture
**Date**: 2025-10-06
**Status**: Research Complete

## Overview

This document captures the technology research and decisions made for implementing the MCP Server Architecture feature. Each decision includes the chosen technology, rationale, and alternatives considered.

---

## 1. MCP SDK Selection

### Decision Made
**Python MCP SDK** from Anthropic's `modelcontextprotocol` package

### Rationale
- Official SDK with full protocol specification compliance
- Native Python implementation aligned with existing codebase (Python 3.9-3.11)
- Supports multiple transport mechanisms (stdio, SSE, WebSocket)
- Built-in tool registration system with type validation
- Active development and community support from Anthropic
- Provides both server and client implementations for testing
- Strong typing support with Pydantic integration
- Asynchronous by default, compatible with FastAPI and SQLAlchemy async

### Alternatives Considered
1. **Custom MCP Protocol Implementation**
   - Rejected: Unnecessary development overhead, potential spec drift, no ecosystem benefits

2. **TypeScript MCP SDK with Python bindings**
   - Rejected: Additional runtime complexity, worse Python ergonomics, harder debugging

3. **langchain-mcp adapter**
   - Rejected: Adds unnecessary LangChain dependency, focused on client-side usage

### Server Pattern Decisions

**Tool Registration Pattern**:
- Use decorators for tool registration (`@server.tool()`)
- Centralized tool registry in core service layer
- Transport adapters expose tools through thin wrapper

**Request Handling Pattern**:
- Adapter receives MCP request → Maps to service method → Returns MCP response
- Service layer remains protocol-agnostic
- Use dependency injection for service access

---

## 2. Async Database Patterns

### Decision Made
**SQLAlchemy 2.0+ with AsyncSession** and async engine

### Rationale
- SQLAlchemy 2.0 provides mature async support with asyncio
- AsyncSession integrates seamlessly with FastAPI and MCP SDK async patterns
- Supports transactional workflow state persistence
- Connection pooling for concurrent workflow management
- Declarative models with async ORM operations
- Migration support via Alembic with async drivers
- Compatible with SQLite (dev) and PostgreSQL (prod) as specified

### Implementation Patterns

**Transaction Management**:
```python
async with async_session() as session:
    async with session.begin():
        # Workflow state operations
        # Automatic rollback on exception
```

**Workflow State Persistence**:
- Use optimistic locking (version column) for concurrent updates
- JSON columns for flexible metadata and step data storage
- Separate tables for Workflow and WorkflowStep entities
- Index on workflow state and created_at for querying

**Session Lifecycle**:
- Scoped sessions per request/workflow operation
- Dependency injection of session in service layer
- Automatic session cleanup via context managers

### Alternatives Considered

1. **Synchronous SQLAlchemy with thread pools**
   - Rejected: Blocks event loop, poor performance with async MCP/FastAPI

2. **Asyncpg directly without ORM**
   - Rejected: Loss of ORM benefits, more boilerplate, PostgreSQL-only

3. **TinyDB or file-based storage**
   - Rejected: No production scalability, weak concurrency support

4. **MongoDB with motor**
   - Rejected: Overkill for relational workflow data, weaker transaction semantics

---

## 3. Circuit Breaker and Retry Logic

### Decision Made
**Tenacity library** for retry/backoff with custom circuit breaker pattern

### Rationale
- Tenacity provides declarative retry configuration with exponential backoff
- Supports async operations natively
- Flexible stop conditions (max attempts, time limits)
- Wait strategies (exponential, random jitter)
- Retry predicates based on exception type or return value
- Built-in logging and statistics
- Lightweight with no heavy dependencies

### Circuit Breaker Implementation
- Implement custom circuit breaker on top of tenacity
- States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
- Track failure rate per agent type
- Configurable failure threshold and timeout duration
- Redis-backed state for distributed deployments

### Retry Strategy
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TransientAgentError),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def invoke_agent(...):
    # Agent invocation logic
```

### Alternatives Considered

1. **pybreaker library**
   - Rejected: No native async support, last updated 2020, limited flexibility

2. **aiobreaker**
   - Rejected: Abandoned project (last commit 2019), no active maintenance

3. **resilience4j via py4j**
   - Rejected: Java dependency overhead, not Pythonic

4. **Custom implementation from scratch**
   - Rejected: Reinventing wheel, tenacity provides better testing and edge case handling

---

## 4. Distributed Tracing and Observability

### Decision Made
**OpenTelemetry** with OTLP export protocol

### Rationale
- Vendor-neutral standard for traces, metrics, and logs
- Python SDK with automatic instrumentation for FastAPI, SQLAlchemy, httpx
- Context propagation across async operations and service boundaries
- Supports multiple backends (Jaeger, Zipkin, Datadog, New Relic)
- Semantic conventions for HTTP, database, messaging
- Active CNCF project with strong industry adoption
- Integrates with Prometheus for metrics

### Implementation Details

**Span Creation Pattern**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_workflow(workflow_id: str):
    with tracer.start_as_current_span(
        "workflow.process",
        attributes={"workflow.id": workflow_id}
    ) as span:
        # Workflow operations
        span.add_event("format_detected", {"format": "Intan"})
```

**Context Propagation**:
- Automatic propagation in async contexts
- Manual propagation for agent invocations
- Trace ID injection into logs for correlation

**Export Strategy**:
- OTLP exporter to collector (production)
- Console exporter for development
- Batch span processor for performance

### Alternatives Considered

1. **Jaeger client directly**
   - Rejected: Vendor lock-in, no metrics/logs, manual instrumentation

2. **AWS X-Ray**
   - Rejected: Cloud vendor lock-in, poor local development experience

3. **Datadog APM directly**
   - Rejected: Expensive, vendor lock-in, OpenTelemetry can export to Datadog anyway

4. **Custom logging-based tracing**
   - Rejected: No distributed context, manual correlation, poor tooling

---

## 5. Format Detection and File Analysis

### Decision Made
**Multi-layered detection** using file signatures, magic bytes, and NeuroConv interface mapping

### Rationale
- Neuroscience formats (25+) have varying levels of structure
- No single detection method works for all formats
- Layered approach increases confidence and handles edge cases
- Leverages NeuroConv's existing interface definitions

### Detection Layers

**Layer 1: File Extension Analysis**
- Fast initial filter using pathlib
- Confidence scoring based on extension uniqueness
- Handles common formats (.nex, .nwb, .smrx)

**Layer 2: Magic Bytes Detection**
- Read first 512 bytes of binary files
- Compare against format signature database
- Handles HDF5-based formats (NWB, Allen Brain Observatory)

**Layer 3: Directory Structure Pattern Matching**
- Analyze file hierarchy for known patterns
- SpikeGLX (*.ap.bin + *.ap.meta), Intan (multiple .rhd files)
- Regex patterns for common structures

**Layer 4: Header Parsing**
- Parse format-specific headers for metadata
- Validate expected fields and structure
- Extract version information

**Layer 5: NeuroConv Interface Mapping**
- Map detected signatures to NeuroConv data interfaces
- Use confidence weights from previous layers
- Select optimal interface for conversion

### Format Signature Database
- JSON configuration file with format definitions
- Fields: name, extensions, magic_bytes, directory_patterns, neuroconv_interface
- Extensible for new formats via configuration

### Alternatives Considered

1. **python-magic library only**
   - Rejected: Generic format detection, lacks neuroscience-specific knowledge

2. **File extension only**
   - Rejected: Unreliable, files may lack extensions or have wrong ones

3. **Deep file content analysis**
   - Rejected: Too slow for initial detection, better as validation step

4. **Machine learning classifier**
   - Rejected: Overkill, requires training data, less explainable

---

## 6. Agent Communication Patterns

### Decision Made
**Async RPC pattern** with request/response queuing

### Rationale
- Agents may be remote processes or services
- Need timeout control and cancellation
- Async enables concurrent agent invocations
- Queue pattern handles backpressure

### Communication Architecture

**Request/Response Model**:
```python
@dataclass
class AgentRequest:
    agent_type: str
    operation: str
    input_data: dict
    context: dict
    timeout_seconds: int
    correlation_id: str

@dataclass
class AgentResponse:
    agent_type: str
    success: bool
    output_data: dict | None
    error: dict | None
    execution_time_ms: int
    correlation_id: str
```

**Invocation Pattern**:
- Service layer creates AgentRequest
- Agent client sends request with timeout
- Polls/waits for response
- Handles timeout and failures gracefully

**Transport Options**:
1. In-process: Direct function calls (development)
2. HTTP: REST API calls to agent services
3. Message Queue: RabbitMQ/Redis for async workflows
4. MCP: Agent-to-agent via MCP protocol

### Alternatives Considered

1. **gRPC for agent communication**
   - Rejected: Adds complexity, HTTP sufficient for current scale

2. **GraphQL for agent queries**
   - Rejected: Overkill for simple request/response, less efficient

3. **WebSockets for all agents**
   - Rejected: Unnecessary persistent connections, state management overhead

---

## 7. Workflow State Machine

### Decision Made
**Explicit state enum** with transition validation

### Rationale
- Clear workflow lifecycle management
- Prevents invalid state transitions
- Enables proper error handling and recovery
- Supports checkpoint/resume functionality

### State Definitions

```python
class WorkflowState(str, Enum):
    PENDING = "pending"           # Created, not started
    ANALYZING = "analyzing"       # Format detection in progress
    COLLECTING = "collecting"     # Metadata collection
    CONVERTING = "converting"     # NWB conversion in progress
    VALIDATING = "validating"     # Validation checks running
    COMPLETED = "completed"       # Success
    FAILED = "failed"            # Unrecoverable error
    CANCELLED = "cancelled"       # User cancelled
```

### Transition Rules
- PENDING → ANALYZING (start workflow)
- ANALYZING → COLLECTING | FAILED (format detected or error)
- COLLECTING → CONVERTING | FAILED (metadata ready or error)
- CONVERTING → VALIDATING | FAILED (conversion done or error)
- VALIDATING → COMPLETED | FAILED (validation passed or failed)
- Any state → CANCELLED (user action)

### Checkpoint Strategy
- Persist state after each transition
- Store intermediate results in WorkflowStep records
- Enable resume from last successful checkpoint
- Implement idempotent step execution

### Alternatives Considered

1. **pytransitions library**
   - Rejected: Adds dependency, simple enum sufficient

2. **Implicit states via step completion**
   - Rejected: Less clear, harder to query and debug

3. **Complex workflow DAG**
   - Rejected: Overkill for linear pipeline with optional branches

---

## 8. Configuration Management

### Decision Made
**Pydantic Settings** with environment variable overrides

### Rationale
- Type-safe configuration with validation
- Environment variable support (12-factor app)
- Nested configuration models
- Automatic parsing of JSON, YAML via loaders
- Integration with FastAPI dependency injection
- Clear documentation via schema export

### Configuration Structure

```python
class DatabaseSettings(BaseSettings):
    url: str
    pool_size: int = 10
    echo: bool = False

class AgentSettings(BaseSettings):
    timeout_seconds: int = 300
    max_retries: int = 3
    circuit_breaker_threshold: float = 0.5

class ServerSettings(BaseSettings):
    database: DatabaseSettings
    agents: AgentSettings
    log_level: str = "INFO"

    class Config:
        env_prefix = "MCP_SERVER_"
        env_nested_delimiter = "__"
```

### Configuration Loading Order
1. Default values in Pydantic models
2. Configuration file (config.yaml)
3. Environment variables (override)
4. Runtime overrides (testing)

### Alternatives Considered

1. **python-decouple**
   - Rejected: Less type safety, no nested models

2. **dynaconf**
   - Rejected: More complex than needed, learning curve

3. **configparser (stdlib)**
   - Rejected: No validation, manual type conversion, dated

---

## 9. API Documentation and Contracts

### Decision Made
**OpenAPI 3.0** specification with code-first generation

### Rationale
- Industry standard for HTTP APIs
- FastAPI generates OpenAPI automatically
- Contract-first ensures adapter parity
- Supports code generation for clients
- Enables API testing tools (Postman, Insomnia)

### Contract Files

**contracts/openapi.yaml**:
- Full OpenAPI 3.0 specification
- All endpoints with request/response schemas
- Error response definitions
- Examples for each operation
- Security schemes (API key, OAuth2)

**contracts/mcp-tools.json**:
- MCP tool definitions in JSON schema format
- Input/output schemas for each tool
- Tool descriptions and metadata
- Version information

### Validation Strategy
- Generate contracts from code during CI
- Validate actual responses match contract
- Use contract tests to ensure adapter parity
- Version contracts alongside code

### Alternatives Considered

1. **GraphQL schema**
   - Rejected: REST more widely adopted, simpler for this use case

2. **Protocol Buffers**
   - Rejected: Primarily for gRPC, less human-readable

3. **AsyncAPI**
   - Considered: Will add for WebSocket/event-driven aspects in future

---

## 10. Testing Strategy

### Decision Made
**Layered testing** with contract, integration, and unit tests

### Rationale
- Contract tests ensure adapter parity (critical for Requirement 8)
- Integration tests validate multi-agent workflows
- Unit tests for business logic in isolation
- pytest-asyncio for async test support

### Test Layers

**Contract Tests** (tests/contract/):
- Test each adapter against same service layer
- Verify equivalent behavior across transports
- JSON test cases with expected inputs/outputs
- Automated parity verification

**Integration Tests** (tests/integration/):
- Full workflow scenarios end-to-end
- Database state verification
- Agent coordination testing
- Performance benchmarks

**Unit Tests** (tests/unit/):
- Service layer business logic
- State machine transitions
- Format detection algorithms
- Error handling logic

### Test Tools
- pytest with pytest-asyncio for async tests
- pytest-mock for mocking agents
- httpx for HTTP client testing
- testcontainers for database testing

### Alternatives Considered

1. **unittest (stdlib)**
   - Rejected: Less ergonomic than pytest, weaker async support

2. **nose2**
   - Rejected: Less active development than pytest

3. **BDD with behave**
   - Rejected: Overkill for technical system, team prefers pytest

---

## Summary of Key Technology Decisions

| Component | Technology | Primary Rationale |
|-----------|-----------|-------------------|
| MCP SDK | Python MCP SDK (Anthropic) | Official implementation, native async, full spec compliance |
| Async Database | SQLAlchemy 2.0 AsyncSession | Mature async ORM, transaction support, migration tooling |
| Retry/Circuit Breaker | Tenacity + custom breaker | Declarative retries, async support, flexible configuration |
| Observability | OpenTelemetry | Vendor-neutral, comprehensive instrumentation, industry standard |
| Format Detection | Multi-layer detection | Handles diverse neuroscience formats, confidence scoring |
| Agent Communication | Async RPC pattern | Timeout control, backpressure handling, transport flexibility |
| Workflow State | Explicit state enum | Clear transitions, checkpoint/resume, query-friendly |
| Configuration | Pydantic Settings | Type-safe, env var support, validation, FastAPI integration |
| API Contracts | OpenAPI 3.0 + MCP tools | Industry standard, code generation, testing support |
| Testing | Layered pytest strategy | Contract parity, integration coverage, unit isolation |

---

## Risk Assessment

### Technical Risks

1. **Agent Communication Latency**: Mitigated by async patterns and timeout controls
2. **State Consistency**: Mitigated by SQLAlchemy transactions and optimistic locking
3. **Format Detection Accuracy**: Mitigated by multi-layer approach and confidence scoring
4. **Adapter Parity Drift**: Mitigated by contract tests in CI/CD

### Mitigation Strategies

- Comprehensive contract testing suite
- Performance benchmarking in CI
- Canary deployments for new features
- Feature flags for gradual rollout

---

## Open Questions for Phase 1

1. **Message Queue Selection**: RabbitMQ vs Redis Streams for async workflows?
2. **Caching Layer**: Redis for agent result caching?
3. **Authentication**: API key vs OAuth2 vs mutual TLS?
4. **Rate Limiting**: Token bucket vs sliding window algorithm?

These will be addressed during detailed design in Phase 1.

---

**Research Phase Complete**: Ready for Phase 1 (Design & Contracts)
