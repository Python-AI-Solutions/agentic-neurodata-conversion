# Research Findings: MCP Server Architecture

**Date**: 2025-10-10
**Phase**: 0 - Technical Research
**Feature**: MCP Server Architecture

---

## 1. Hexagonal Architecture Patterns for Python

**Decision**: Use Python Abstract Base Classes (ABC) with Protocol for interface definition, combined with FastAPI's dependency injection system for port implementations.

**Rationale**:
- ABC provides compile-time interface enforcement with runtime checking via `@abstractmethod`
- Protocol (PEP 544) enables structural subtyping for flexible adapter implementations
- FastAPI's `Depends()` provides clean dependency injection without heavyweight frameworks
- Pattern naturally enforces business logic isolation in core service layer
- Testing is simplified through interface-based mocking

**Alternatives Considered**:
- **Pure Protocol (no ABC)**: More flexible but loses explicit interface contracts and IDE support for required methods
- **Runtime checking only (duck typing)**: Pythonic but sacrifices type safety and early error detection in complex multi-agent workflows
- **Dependency Injector library**: Adds dependency and configuration complexity for minimal benefit over FastAPI's native DI
- **Netflix Dispatch approach**: Over-engineered for single-service architecture, designed for microservices ecosystem

**Implementation Notes**:
- Define ports as ABC in `src/core/ports/` directory:
  - `agent_port.py` for agent coordination
  - `storage_port.py` for state persistence
  - `validator_port.py` for validation coordination
  - `tracing_port.py` for observability
- Adapters implement ports in `src/adapters/` with transport-specific logic
- Core service layer in `src/core/services/` depends only on port interfaces
- FastAPI dependency injection wires concrete implementations at startup

**References**:
- Python ABC documentation: https://docs.python.org/3/library/abc.html
- PEP 544 Protocols: https://peps.python.org/pep-0544/
- FastAPI dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- Hexagonal Architecture guide: https://alistair.cockburn.us/hexagonal-architecture/

---

## 2. FastAPI + MCP Protocol Integration

**Decision**: Run MCP server (stdio transport) and FastAPI HTTP server in separate async event loops using Python's asyncio subprocess management for MCP and uvicorn for HTTP. Use shared Redis/in-memory session store for state synchronization.

**Rationale**:
- MCP stdio transport requires dedicated stdin/stdout, incompatible with HTTP server logging
- Subprocess isolation prevents event loop conflicts between MCP and HTTP servers
- Shared session store enables protocol-agnostic state access (FR-010 parity requirement)
- asyncio subprocess management maintains async patterns throughout stack
- Production deployments can run MCP and HTTP as separate processes for scaling

**Alternatives Considered**:
- **Single event loop with MCP socket transport**: Requires TCP for MCP instead of stdio, complicates client configuration and violates Claude Agent SDK's default stdio mode
- **Threading for MCP server**: Introduces thread-safety complexity and blocks async benefits for agent coordination
- **Embedded MCP in FastAPI routes**: Violates adapter isolation principle (FR-006), mixes transport logic with business logic
- **Separate processes with IPC**: Production-ready but adds deployment complexity for development/testing

**Implementation Notes**:
- MCP server entry point: `cli/mcp_server.py` using `mcp.server.stdio.stdio_server()`
- HTTP server entry point: `cli/http_server.py` using `uvicorn.run()`
- Shared session store interface in `src/core/ports/storage_port.py`
- In-memory implementation for testing, Redis adapter for production
- Use asyncio context managers for lifecycle management

**References**:
- Claude Agent SDK: https://github.com/anthropics/anthropic-sdk-python (mcp module)
- FastAPI async support: https://fastapi.tiangolo.com/async/
- Python asyncio subprocess: https://docs.python.org/3/library/asyncio-subprocess.html
- Redis async client: https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html

---

## 3. DAG Workflow Engines

**Decision**: Custom lightweight DAG implementation using networkx for graph algorithms, asyncio for parallel execution, and Pydantic models for workflow definition.

**Rationale**:
- networkx provides battle-tested topological sort and cycle detection (FR-016)
- Custom implementation keeps codebase simple (~300 LOC vs 10K+ LOC for Airflow/Prefect)
- No external dependencies or cloud services required (constitutional requirement)
- Full control over checkpoint/recovery semantics (FR-027)
- Async execution maps naturally to agent invocation patterns

**Alternatives Considered**:
- **Apache Airflow**: Heavyweight (requires PostgreSQL, scheduler daemon, web server), designed for batch ETL not real-time agent orchestration
- **Prefect 2.x**: Cloud-focused with commercial features, excessive abstractions for simple agent DAGs
- **Temporal**: Excellent reliability but heavyweight (requires Temporal server cluster), over-engineered for single-server deployment
- **Celery**: Task queue not DAG engine, requires message broker (RabbitMQ/Redis), adds operational complexity

**Implementation Notes**:
- Workflow DAG representation: `networkx.DiGraph` with agent steps as nodes, dependencies as edges
- Topological sort for execution order: `networkx.topological_sort()`
- Cycle detection: `networkx.is_directed_acyclic_graph()`
- Parallel execution: `asyncio.gather()` for independent nodes at same DAG level
- Workflow persistence: Serialize DAG to JSON with Pydantic `WorkflowDefinition` model
- Execution state: Track completed/failed nodes in `ConversionSession` checkpoint

**References**:
- networkx documentation: https://networkx.org/documentation/stable/
- networkx DAG algorithms: https://networkx.org/documentation/stable/reference/algorithms/dag.html
- asyncio.gather: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather

---

## 4. State Management Patterns

**Decision**: Snapshot-based state persistence using JSON serialization with atomic writes via tempfile, optimistic locking with version numbers, and incremental checkpointing.

**Rationale**:
- JSON serialization is human-readable for debugging, widely supported for audit exports
- Atomic writes (write to temp → fsync → rename) prevent corruption during crashes (FR-027)
- Optimistic locking with version numbers prevents concurrent modification conflicts (FR-028)
- Snapshot approach simpler than event sourcing for workflow state (no replay complexity)
- Pydantic models provide automatic JSON serialization/deserialization with validation

**Alternatives Considered**:
- **Pickle serialization**: Faster but opaque binary format, version fragility across Python versions, security concerns with untrusted data
- **MessagePack**: Compact binary format but loses human readability for debugging, minimal compression benefit for workflow state (<100KB typical)
- **Event sourcing**: Provides complete history but adds complexity for state reconstruction, overkill for checkpoint/recovery requirements
- **Database transactions**: Requires external database dependency, adds operational complexity for file-based checkpoints

**Implementation Notes**:
- State model: Pydantic `ConversionSession` with `.json()` serialization
- Atomic write pattern:
  ```python
  with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=checkpoint_dir) as tmp:
      tmp.write(session.json(indent=2))
      tmp.flush()
      os.fsync(tmp.fileno())
  os.replace(tmp.name, checkpoint_path)  # Atomic rename
  ```
- Optimistic locking: Include `version: int` field in `ConversionSession`, increment on each update, check before writes
- Checkpoint naming: `checkpoint_{session_id}_{version}.json`
- Checkpoint pruning: Retain last N checkpoints (configurable, default 10)

**References**:
- Python tempfile: https://docs.python.org/3/library/tempfile.html
- os.replace atomic rename: https://docs.python.org/3/library/os.html#os.replace
- Pydantic JSON serialization: https://docs.pydantic.dev/latest/usage/serialization/

---

## 5. Distributed Tracing with OpenTelemetry

**Decision**: Use opentelemetry-api for instrumentation with contextvars for async context propagation, opentelemetry-sdk for span management, and stdout exporter for development with Jaeger support for production.

**Rationale**:
- OpenTelemetry is CNCF standard with wide ecosystem support (FR-047)
- contextvars provides thread-safe async context propagation across agent calls
- opentelemetry-api separates instrumentation from backend (vendor-neutral)
- Automatic instrumentation available for FastAPI, aiohttp, httpx
- Lightweight in development (stdout), production-ready with Jaeger/Zipkin exporters

**Alternatives Considered**:
- **Custom tracing**: Reinventing correlation ID propagation is error-prone, loses ecosystem tooling
- **Datadog APM**: Proprietary vendor lock-in, requires Datadog agent and commercial license
- **Zipkin client directly**: Less mature Python support than OpenTelemetry, narrower ecosystem
- **AWS X-Ray**: Cloud-specific, not suitable for on-premise deployments

**Implementation Notes**:
- Install: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-jaeger`
- Initialize tracer in `src/observability/tracing.py`:
  ```python
  from opentelemetry import trace
  from opentelemetry.sdk.trace import TracerProvider
  from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

  provider = TracerProvider()
  provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
  trace.set_tracer_provider(provider)
  tracer = trace.get_tracer(__name__)
  ```
- Instrument agent calls:
  ```python
  with tracer.start_as_current_span("agent_invocation") as span:
      span.set_attribute("agent_type", agent_type)
      span.set_attribute("session_id", session_id)
      result = await invoke_agent(...)
  ```
- Context propagation: OpenTelemetry automatically uses contextvars for async context
- Correlation IDs: Extract trace_id from span context for logging

**References**:
- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
- OpenTelemetry API: https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html
- FastAPI instrumentation: https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
- Jaeger: https://www.jaegertracing.io/docs/

---

## 6. Agent Coordination Patterns

**Decision**: Use tenacity library for retry logic with exponential backoff and jitter, aiobreaker library for async circuit breakers, and custom health check implementation.

**Rationale**:
- tenacity provides declarative retry configuration with decorators (FR-018)
- aiobreaker is async-native (asyncio compatible) for agent coordination
- Exponential backoff with full jitter prevents thundering herd during failures
- Circuit breaker prevents cascading failures when agents are unhealthy (FR-005)
- Libraries are lightweight, well-maintained, and widely adopted in Python ecosystem

**Alternatives Considered**:
- **pybreaker (sync)**: Not async-compatible, requires thread pool for async code
- **Custom retry implementation**: Reimplementing exponential backoff with jitter is error-prone, loses declarative configuration
- **resilience4j (Java port)**: No mature Python port, adding JVM dependency is excessive
- **Polly (C# library)**: No Python equivalent, only available for .NET

**Implementation Notes**:
- Install: `tenacity>=8.2.0`, `aiobreaker>=1.3.0`
- Retry configuration per agent type in `src/config/agent_config.py`:
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential_jitter

  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential_jitter(initial=1, max=10, jitter=5),
      reraise=True
  )
  async def invoke_agent_with_retry(agent, request):
      return await agent.invoke(request)
  ```
- Circuit breaker per agent instance:
  ```python
  from aiobreaker import CircuitBreaker, CircuitBreakerError

  agent_breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

  try:
      async with agent_breaker:
          result = await invoke_agent_with_retry(agent, request)
  except CircuitBreakerError:
      # Failover to backup agent or degrade gracefully
  ```
- Health checks: Lightweight HTTP GET to agent `/health` endpoint every 30 seconds
- Timeout management: `asyncio.wait_for()` per agent invocation, configurable per agent type

**References**:
- tenacity documentation: https://tenacity.readthedocs.io/en/latest/
- aiobreaker: https://github.com/abulimov/aiobreaker
- Full jitter algorithm: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

---

## 7. WebSocket Streaming with FastAPI

**Decision**: Use FastAPI's built-in WebSocket support with JSON Lines framing protocol, client-side reconnection with exponential backoff, and server-side heartbeat for connection health.

**Rationale**:
- FastAPI WebSocket support is native and well-integrated with async patterns (FR-009)
- JSON Lines (newline-delimited JSON) provides simple framing with human-readable messages
- Client-side reconnection logic keeps server stateless, simplifies horizontal scaling
- Server heartbeat (ping/pong) detects broken connections quickly
- No external WebSocket library needed, reduces dependency footprint

**Alternatives Considered**:
- **Socket.IO**: Heavyweight with fallback transports (long polling, polling), unnecessary complexity for modern browsers with native WebSocket support
- **Custom binary protocol**: More efficient but loses human readability, premature optimization for progress updates (low bandwidth)
- **Server-side reconnection**: Requires maintaining client registry, complicates server scaling and failover
- **GraphQL subscriptions**: Over-engineered for simple progress streaming, adds GraphQL dependency

**Implementation Notes**:
- WebSocket endpoint in `src/adapters/http/websocket_adapter.py`:
  ```python
  from fastapi import WebSocket, WebSocketDisconnect

  @app.websocket("/api/v1/ws/conversions/{session_id}")
  async def websocket_endpoint(websocket: WebSocket, session_id: str):
      await websocket.accept()
      try:
          while True:
              # Send progress updates as JSON Lines
              update = await get_progress_update(session_id)
              await websocket.send_text(update.json() + "\n")
              await asyncio.sleep(1)  # Rate limiting
      except WebSocketDisconnect:
          # Client disconnected, cleanup
  ```
- Message protocol (contracts/websocket-protocol.md):
  - Client → Server: `{"type": "subscribe", "session_id": "..."}`
  - Server → Client: `{"type": "progress_update", "step": "...", "percentage": 75}`
- Heartbeat: Server sends `{"type": "ping"}` every 30 seconds, expects `{"type": "pong"}` within 10 seconds
- Client reconnection: Exponential backoff starting at 1 second, max 60 seconds
- Backpressure handling: Drop updates if client send buffer is full (prefer latest state over history)

**References**:
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
- JSON Lines format: https://jsonlines.org/
- WebSocket protocol: https://datatracker.ietf.org/doc/html/rfc6455

---

## 8. Plugin Architecture in Python

**Decision**: Use entry_points (setuptools) for plugin discovery, importlib for dynamic loading, and versioned plugin API with Protocol contracts.

**Rationale**:
- entry_points is standard Python plugin mechanism, widely supported by packaging tools
- importlib.metadata provides clean discovery without filesystem scanning
- Protocol contracts enable structural subtyping for plugin compatibility (FR-053)
- Version checking prevents incompatible plugins from loading
- In-process plugins keep architecture simple, separate processes for untrusted code if needed later

**Alternatives Considered**:
- **Namespace packages**: More complex configuration, harder to discover installed plugins
- **Filesystem scanning**: Fragile (depends on installation paths), misses installed packages
- **Separate processes (subprocess)**: Adds IPC overhead and complexity, premature for trusted custom validators
- **importlib.metadata alternatives (pkg_resources)**: Deprecated in favor of importlib.metadata

**Implementation Notes**:
- Plugin interface in `src/core/ports/plugin_port.py`:
  ```python
  from typing import Protocol

  class ValidatorPlugin(Protocol):
      plugin_api_version: str  # "1.0"
      plugin_name: str

      async def validate(self, nwb_file_path: str) -> ValidationResult:
          ...
  ```
- Plugin discovery in `src/core/services/plugin_registry.py`:
  ```python
  from importlib.metadata import entry_points

  def discover_validator_plugins():
      validators = []
      for ep in entry_points(group="mcp_server.validators"):
          plugin_cls = ep.load()
          if plugin_cls.plugin_api_version == "1.0":
              validators.append(plugin_cls())
      return validators
  ```
- Plugin registration in custom package's `setup.py`:
  ```python
  setup(
      name="my-custom-validator",
      entry_points={
          "mcp_server.validators": [
              "my_validator = my_package.validator:MyValidator"
          ]
      }
  )
  ```
- Plugin lifecycle: Load on server startup, validate API version, cache instances

**References**:
- Entry points: https://packaging.python.org/en/latest/specifications/entry-points/
- importlib.metadata: https://docs.python.org/3/library/importlib.metadata.html
- PEP 544 Protocols: https://peps.python.org/pep-0544/

---

## 9. Format Detection Strategies

**Decision**: Use python-magic (libmagic wrapper) for binary format detection, combined with custom heuristics for neuroscience formats, multi-factor weighted confidence scoring, and file sampling for large datasets.

**Rationale**:
- python-magic leverages libmagic's extensive format database for binary formats
- Custom heuristics needed for neuroscience formats not in libmagic (SpikeGLX, Open Ephys, etc.)
- Multi-factor scoring (extension, magic bytes, header structure, metadata) provides explainable confidence (FR-022)
- File sampling (first 10MB + random samples) keeps detection fast for TB-scale datasets
- Fallback to extension-based detection for text formats (CSV, JSON)

**Alternatives Considered**:
- **filetype (pure Python)**: Limited format database compared to libmagic, misses binary neuroscience formats
- **Extension-only detection**: Unreliable with misleading extensions (FR-020 edge case)
- **Full file parsing**: Too slow for large datasets, unnecessary for format identification
- **Machine learning classifier**: Over-engineered for rule-based detection, requires training data

**Implementation Notes**:
- Install: `python-magic>=0.4.27` (requires libmagic system library)
- Detector interface in `src/core/ports/format_detector_port.py`:
  ```python
  class FormatDetector(Protocol):
      format_name: str

      async def detect(self, dataset_path: Path) -> FormatDetectionResult:
          ...
  ```
- Detection pipeline in `src/formats/detection/detector_orchestrator.py`:
  1. Inventory files in dataset (skip files >10GB initially)
  2. Run parallel detection: magic bytes, extension, header parsing
  3. Calculate confidence scores per detector:
     - Magic bytes match: 90% confidence
     - Extension match: 50% confidence
     - Header structure match: 80% confidence
     - Metadata file match: 70% confidence
  4. Aggregate scores: `confidence = max(detector_scores) + 0.1 * sum(other_scores)`
  5. Return ranked formats with explanations
- Neuroscience format detectors in `src/formats/detection/neuro_detectors.py`:
  - SpikeGLX: `.bin` + `.meta` file pair, check meta header
  - Open Ephys: `structure.oebin` JSON file, validate schema
  - Blackrock: `.nev` + `.nsX` files, check NEV header magic bytes
  - etc. (FR-021 formats)

**References**:
- python-magic: https://github.com/ahupp/python-magic
- libmagic: https://www.darwinsys.com/file/
- NeuroConv format guide: https://neuroconv.readthedocs.io/en/main/user_guide/formats.html

---

## 10. RDF/PROV-O Libraries for Python

**Decision**: Use rdflib (pure Python) for RDF graph management and PROV-O modeling, with Turtle serialization format for human readability and JSON-LD for API responses.

**Rationale**:
- rdflib is mature (15+ years), pure Python (no C dependencies), stable API
- Built-in PROV-O namespace support via `rdflib.namespace.PROV`
- Turtle format is readable for debugging provenance graphs (FR-004)
- JSON-LD format provides web-compatible serialization for API responses
- In-memory graph operations are fast for workflow-scale provenance (<10K triples)
- Persistent storage via rdflib.plugins.stores (SQLite, PostgreSQL) for production

**Alternatives Considered**:
- **prov library**: PROV-specific but less flexible for custom extensions, smaller ecosystem
- **owlrl (reasoning)**: Adds reasoning capabilities but heavyweight and slow for simple provenance tracking
- **Allegro Graph / GraphDB**: Commercial triple stores are overkill for single-workflow provenance, add operational complexity
- **Custom JSON structure**: Loses standard PROV-O vocabulary, incompatible with provenance tools

**Implementation Notes**:
- Install: `rdflib>=7.0.0`
- Provenance tracker in `src/core/services/provenance_tracker.py`:
  ```python
  from rdflib import Graph, Namespace, Literal, URIRef
  from rdflib.namespace import RDF, PROV, XSD

  class ProvenanceTracker:
      def __init__(self):
          self.graph = Graph()
          self.ns = Namespace("http://mcp-server/provenance/")

      def record_agent_invocation(self, session_id, agent_type, input_data, output_data):
          activity = self.ns[f"activity_{session_id}_{agent_type}"]
          agent = self.ns[f"agent_{agent_type}"]

          self.graph.add((activity, RDF.type, PROV.Activity))
          self.graph.add((activity, PROV.wasAssociatedWith, agent))
          self.graph.add((activity, PROV.used, input_data))
          self.graph.add((output_data, PROV.wasGeneratedBy, activity))

      def export_turtle(self) -> str:
          return self.graph.serialize(format='turtle')

      def export_json_ld(self) -> str:
          return self.graph.serialize(format='json-ld')
  ```
- PROV-O entities (contracts/prov-schema.ttl):
  - `prov:Entity` subclasses: Dataset, NWBFile, IntermediateResult
  - `prov:Activity` subclasses: FormatDetection, MetadataCollection, Conversion, Validation
  - `prov:Agent` subclasses: ConversationAgent, MetadataQuestionerAgent, ConversionAgent, EvaluationAgent
- Storage: Serialize to Turtle files in `{checkpoint_dir}/provenance_{session_id}.ttl`

**References**:
- rdflib documentation: https://rdflib.readthedocs.io/en/stable/
- PROV-O ontology: https://www.w3.org/TR/prov-o/
- rdflib PROV namespace: https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.namespace.html#rdflib.namespace.PROV
- Turtle format: https://www.w3.org/TR/turtle/

---

## Research Completion Summary

**Status**: All 10 research tasks completed
**Date**: 2025-10-10
**Outcome**: All technical decisions made, ready for Phase 1 design artifacts

**Key Decisions**:
1. Hexagonal architecture with ABC/Protocol interfaces
2. Separate async event loops for MCP and HTTP servers
3. Custom DAG implementation with networkx
4. Snapshot-based state persistence with JSON
5. OpenTelemetry for distributed tracing
6. tenacity + aiobreaker for resilience patterns
7. FastAPI native WebSocket with JSON Lines
8. Entry points for plugin discovery
9. python-magic + custom heuristics for format detection
10. rdflib for PROV-O provenance tracking

**No Blockers**: All chosen technologies are mature, well-documented, and align with constitutional requirements (MCP-centric, test-driven, schema-first, quality-first).
