<!--
Sync Impact Report:
Version: 3.0.0 (Alternative Format - Hierarchical)
Source: Same requirements as detailed version (1389 lines from 10 requirements.md files)
Format Differences:
  - Hierarchical organization with clear requirement numbering
  - Cross-references between related requirements
  - Quick navigation with ToC-friendly structure
  - Grouped requirements by theme
  - Maintains all content from detailed version
-->

# Agentic Neurodata Conversion Constitution
**Version 3.0.0 - Hierarchical Format**

## Table of Contents

- [Core Principles](#core-principles) (8 principles)
  - [I. MCP-Centric Architecture](#i-mcp-centric-architecture-non-negotiable)
  - [II. Agent Specialization](#ii-agent-specialization--coordination)
  - [III. Test-Driven Development](#iii-test-driven-development-non-negotiable)
  - [IV. Schema-First & Standards](#iv-schema-first--standards-compliance-non-negotiable)
  - [V. Modular Architecture](#v-modular-architecture-first)
  - [VI. Data Integrity & Provenance](#vi-data-integrity--provenance)
  - [VII. Quality-First Development](#vii-quality-first-development)
  - [VIII. Observability & Traceability](#viii-observability--traceability)
- [Technical Standards](#technical-standards) (6 domains)
- [Development Workflow](#development-workflow) (4 areas)
- [Governance](#governance) (4 sections)

---

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

**Principle**: All functionality MUST be exposed through standardized MCP (Model Context Protocol) tools. The MCP server is the single orchestration layer.

#### 1.1 Transport-Agnostic Core Service

**REQ-MCP-001**: All business logic MUST reside in a transport-agnostic core service layer
- Zero dependencies on MCP, HTTP, or other transport protocols
- Contains: domain entities, use cases, business rules, workflow orchestration, state management
- Enables testing without transport dependencies

**REQ-MCP-002**: Adapter layers MUST be thin (<500 lines of code, <5% of total codebase)
- Protocol-specific deserialization only
- Maps requests to service method calls
- Handles protocol-specific errors and connection lifecycle
- Implements protocol authentication and metrics
- **ZERO business logic in adapters**

**REQ-MCP-003**: Functional parity across all transport protocols (stdin/stdout, HTTP, WebSocket, gRPC, GraphQL)
- Contract tests verify identical service method invocations
- Equivalent results for same inputs
- Consistent error handling across protocols
- State coherence maintained
- Comparable performance characteristics

**REQ-MCP-004**: Direct agent invocation from external clients is PROHIBITED
- All agent coordination flows through MCP server core service layer
- Clients interact ONLY through MCP tools

#### 1.2 MCP Server Orchestration Capabilities

**REQ-MCP-005**: Multi-Agent Workflow Orchestration
- Sequential workflow execution: analysis → metadata collection → conversion → validation
- Parallel execution where appropriate
- Dependency resolution between steps
- State management across agent interactions
- Error propagation and retry logic with exponential backoff
- Timeout management per agent and overall workflow
- Workflow cancellation with cleanup

**REQ-MCP-006**: Format Detection (25+ neuroscience formats)
- File extension analysis with confidence scoring
- Magic byte detection for binary formats
- Header parsing for structured formats
- Directory structure pattern matching
- Metadata file detection and parsing
- Sampling-based content analysis
- Format version identification
- Multi-format dataset recognition

**REQ-MCP-007**: Interface Selection
- Confidence-weighted matching to NeuroConv interfaces
- Interface capability matrices
- Performance characteristics and resource requirements
- Quality scores from past conversions
- User preference learning
- Cost optimization for cloud resources
- Fallback interface chains with explainable selection logic

**REQ-MCP-008**: Validation Coordination
- NWB Inspector with configurable rule sets
- PyNWB validator for schema compliance
- DANDI validator for repository readiness
- Custom validators via plugin system
- Format-specific validators for source fidelity
- Cross-validation between multiple tools
- Ensemble validation with voting
- Progressive validation during conversion

**REQ-MCP-009**: State Management
- Checkpoint recovery for multi-step workflows
- Conversion context versioning across agent interactions
- Provenance tracking throughout pipeline
- Intermediate results persistence for debugging and audit
- Concurrent workflow isolation
- Resource allocation across agents
- Transaction-like semantics for multi-agent operations
- State querying and manipulation APIs

**Rationale**: Hexagonal architecture ensures system can evolve transport mechanisms without affecting core functionality. Supports evolutionary architecture with fitness functions and maintains architectural integrity over time.

**Cross-References**: See [Principle V](#v-modular-architecture-first) for module structure, [Technical Standards - Integration](#integration-standards) for protocol details.

---

### II. Agent Specialization & Coordination

**Principle**: Each agent handles single domain of responsibility. Cross-domain operations ONLY through MCP server.

#### 2.1 Conversation Agent

**REQ-AGENT-CONV-001**: Analyze dataset contents
- Identify data formats and experimental context
- Detect missing metadata fields

**REQ-AGENT-CONV-002**: Generate natural language questions
- Understandable to non-expert users
- Target essential missing metadata

**REQ-AGENT-CONV-003**: Validate user responses
- Against domain knowledge
- Suggest corrections for inconsistencies

**REQ-AGENT-CONV-004**: Provide structured summaries
- Clear provenance marking (user-provided vs. auto-detected)

**REQ-AGENT-CONV-005**: Avoid repeated questions
- Only ask what cannot be inferred from data or domain knowledge

**REQ-AGENT-CONV-006**: Record reasoning and data sources
- For each decision

**REQ-AGENT-CONV-007**: Mark field origins
- Auto-generated vs. user-provided vs. externally enriched

**REQ-AGENT-CONV-008**: Provide comprehensive audit trails
- All operations and transformations

#### 2.2 Conversion Agent

**REQ-AGENT-CONVERT-001**: Select appropriate NeuroConv DataInterface classes
- Based on detected formats

**REQ-AGENT-CONVERT-002**: Generate valid Python code
- Handle specific data formats and experimental setups

**REQ-AGENT-CONVERT-003**: Populate NWB metadata fields
- Mark auto-generated vs. user-provided

**REQ-AGENT-CONVERT-004**: Provide clear error messages
- Suggest corrective actions on failure

**REQ-AGENT-CONVERT-005**: Record complete provenance
- For successful conversions

**REQ-AGENT-CONVERT-006**: Handle failures gracefully
- Timeouts, retries, service failures

**REQ-AGENT-CONVERT-007**: Support mock modes
- Don't require external LLM services for testing

**REQ-AGENT-CONVERT-008**: Provide deterministic test modes
- For consistent testing

#### 2.3 Evaluation Agent

**REQ-AGENT-EVAL-001**: Coordinate with validation systems
- Assess file quality and compliance

**REQ-AGENT-EVAL-002**: Generate comprehensive reports
- With visualizations

**REQ-AGENT-EVAL-003**: Coordinate with knowledge graph systems
- Generate semantic representations

**REQ-AGENT-EVAL-004**: Integrate results
- From validation, evaluation, and knowledge graph systems

#### 2.4 Metadata Questioner Agent

**REQ-AGENT-META-001**: Generate contextually appropriate questions
- Based on experimental type and data format

**REQ-AGENT-META-002**: Provide clear explanations
- Why information is needed
- How it will be used

**REQ-AGENT-META-003**: Validate answers
- Against domain constraints
- Suggest alternatives for invalid responses

**REQ-AGENT-META-004**: Integrate responses into structured metadata
- With proper provenance tracking

#### 2.5 Universal Agent Requirements

**REQ-AGENT-ALL-001**: Consistent interfaces
- Error handling patterns
- Structured responses
- Clear logging and progress indicators
- Actionable error messages with remediation steps
- Results in formats processable by MCP server

**REQ-AGENT-ALL-002**: Configuration & monitoring
- LLM provider and model parameter configuration
- Metrics on processing time, success rates, resource usage
- Detailed logging of operations and decision-making
- Graceful handling of timeouts, retries, failures

**REQ-AGENT-ALL-003**: Provenance & transparency
- Record reasoning and data sources
- Mark field origins (auto vs. user vs. enriched)
- Citations and/or confidence scores
- Explain heuristics and logic
- Comprehensive audit trails

**REQ-AGENT-ALL-004**: Testing support
- Mock modes without external LLM services
- Deterministic test modes
- Edge case and malformed input handling
- Correct operation when called by MCP server

**Rationale**: Single responsibility ensures maintainability, testability, independent evolution. Standardized interfaces simplify integration.

**Cross-References**: See [Principle III](#iii-test-driven-development-non-negotiable) for agent testing requirements, [Principle VIII](#viii-observability--traceability) for logging.

---

### III. Test-Driven Development (NON-NEGOTIABLE)

**Principle**: Contract tests written BEFORE any implementation. Strict RED-GREEN-REFACTOR workflow.

#### 3.1 TDD Workflow (Mandatory)

**REQ-TDD-001**: Write tests first
- Define expected behavior (contract, integration, unit)
- Based on specifications

**REQ-TDD-002**: Obtain user approval
- On test specifications before proceeding

**REQ-TDD-003**: Verify RED phase
- Tests fail appropriately
- Demonstrates feature doesn't exist yet

**REQ-TDD-004**: Implement GREEN phase
- Minimum code to pass tests

**REQ-TDD-005**: Refactor phase
- While maintaining green tests

#### 3.2 Quality Gates (Mandatory Thresholds)

**REQ-TDD-006**: Critical path coverage ≥90%
- MCP server, agents, validation systems

**REQ-TDD-007**: Client library coverage ≥85%

**REQ-TDD-008**: Contract test coverage = 100%
- OpenAPI specification coverage
- Every endpoint has contract tests

**REQ-TDD-009**: Pre-implementation requirement
- ALL API endpoints have contract tests BEFORE implementation begins

#### 3.3 MCP Server Testing Infrastructure

**REQ-TEST-MCP-001**: Endpoint testing (≥90% coverage)
- Successful requests with valid data
- Malformed request handling
- Authentication/authorization scenarios
- Rate limiting behavior
- Request size limits and timeout handling
- Concurrent request processing
- Idempotency verification

**REQ-TEST-MCP-002**: Agent coordination testing (≥20 workflow scenarios)
- Sequential workflow execution
- Parallel agent invocation
- Dependency management between agents
- State persistence across agent calls
- Error propagation from agents to server
- Retry logic with exponential backoff
- Circuit breaker activation
- Graceful degradation when agents unavailable

**REQ-TEST-MCP-003**: Contract testing (100% specification coverage)
- All endpoints conform to OpenAPI specifications
- Response schema validation
- Required field verification
- Data type checking and enum value validation
- Format string compliance (dates, UUIDs)
- Pagination consistency
- HATEOAS link validity
- Versioning header correctness

**REQ-TEST-MCP-004**: Error condition testing
- Agent failures (timeout, crash, invalid response)
- Network issues (connection loss, slow networks)
- Resource exhaustion (memory, disk, file handles)
- Concurrent modification conflicts
- Database connection failures
- External service unavailability
- Malformed data from agents
- Cascade failures
- Specific error codes and messages for each scenario

**REQ-TEST-MCP-005**: State management testing
- Workflow state persistence
- Transaction consistency and rollback
- State recovery after crashes
- Cleanup of orphaned resources
- Garbage collection of old states
- State migration during upgrades
- Distributed state coordination
- ACID properties where applicable

**REQ-TEST-MCP-006**: Security testing (OWASP guidelines)
- Input sanitization verification
- SQL injection prevention
- Path traversal protection
- XXE attack prevention
- CSRF token validation
- Rate limiting effectiveness
- Authentication timeout
- Session management
- Audit logging completeness

#### 3.4 Individual Agent Testing

**REQ-TEST-AGENT-001**: Logic testing (50+ test cases per agent)
- Input validation
- Data transformation accuracy with property-based testing
- Decision-making algorithms with scenario coverage
- Error handling paths with forced error injection
- Edge case handling with boundary value analysis
- Performance characteristics with benchmark tests
- Memory usage patterns with leak detection
- Configuration validation with invalid configs

**REQ-TEST-AGENT-002**: Interface testing (contract tests for all methods)
- Schema validation tests
- Type checking with runtime verification
- Required field presence checks
- Optional field handling
- Null/undefined handling
- Encoding/decoding tests (UTF-8, base64)
- Large payload handling (>10MB)
- Streaming data support

**REQ-TEST-AGENT-003**: Mock data testing (100+ mock scenarios)
- Mock LLM services with deterministic responses
- Fake file systems with in-memory operations
- Simulated network conditions
- Time manipulation for temporal testing
- Mock external APIs with various response patterns
- Stub data sources with controlled data
- Fake credentials and secrets
- Deterministic random number generation

**REQ-TEST-AGENT-004**: Error handling testing (≥5 tests per error type)
- Malformed inputs (missing fields, wrong types, invalid formats)
- Service failures (LLM timeout, API errors, network issues)
- Resource constraints (memory limits, disk space, CPU throttling)
- Concurrent access issues
- Partial failures in multi-step operations
- Rollback scenarios
- Cleanup after failures
- Error reporting accuracy

**REQ-TEST-AGENT-005**: State machine testing (full state diagram coverage)
- State transitions
- Illegal state prevention
- State persistence
- Concurrent state modifications
- State recovery after restart
- Timeout handling in each state
- Event ordering requirements
- Side effects of state changes

**REQ-TEST-AGENT-006**: Performance testing (with regression detection)
- Response times under various loads
- Throughput for batch operations
- Resource usage patterns
- Scalability limits
- Degradation under stress
- Recovery after load spikes
- Cache effectiveness
- Optimization opportunities

#### 3.5 End-to-End Testing with Real Datasets

**REQ-TEST-E2E-001**: DataLad-managed test datasets
- Open Ephys recordings (multi-channel, multi-session)
- SpikeGLX datasets with different probe configurations
- Neuralynx data with video synchronization
- Calcium imaging data (Suite2p, CaImAn processed)
- Behavioral tracking data (DeepLabCut, SLEAP)
- Multimodal recordings (ephys + imaging + behavior)
- Datasets with missing/corrupted segments
- Legacy format migrations
- Version control for reproducibility

**REQ-TEST-E2E-002**: Format coverage (≥15 distinct format combinations)
- Binary formats (DAT, BIN, proprietary)
- HDF5-based formats (various schemas)
- Text-based formats (CSV, TSV, JSON)
- Video formats (AVI, MP4, MOV)
- Image stacks (TIFF, PNG sequences)
- Time series data (continuous, event-based)
- Metadata formats (JSON, XML, YAML)
- Mixed format datasets

**REQ-TEST-E2E-003**: Quality validation
- Valid NWB files passing NWB Inspector (zero critical issues)
- PyNWB schema compliance (all required fields)
- Data integrity with checksum verification
- Temporal alignment across data streams (<1ms drift)
- Spatial registration accuracy for imaging data
- Signal fidelity with SNR preservation
- Metadata completeness (>95% fields populated)
- Proper unit conversions
- Automated quality scoring

**REQ-TEST-E2E-004**: Complete pipeline testing (workflows up to 1TB)
- Dataset discovery and format detection
- Metadata extraction and inference
- User interaction simulation for missing metadata
- Conversion script generation and validation
- Parallel processing for large datasets
- Progress reporting and cancellation
- Error recovery and partial completion
- Final evaluation with report generation

**REQ-TEST-E2E-005**: Scientific validity (domain expert criteria)
- Spike sorting results preservation
- Behavioral event alignment
- Stimulus timing accuracy
- Trial structure maintenance
- Experimental metadata fidelity
- Derived data linkage
- Provenance chain completeness
- Reproducibility of analysis

**REQ-TEST-E2E-006**: Performance benchmarking (baseline establishment)
- Conversion speed (MB/sec by format)
- Memory usage patterns (peak and average)
- Disk I/O patterns (read/write ratios)
- CPU utilization (single vs multi-core)
- Network usage for remote datasets
- Cache effectiveness
- Parallel scaling efficiency
- Bottleneck identification

**Rationale**: TDD ensures correctness, prevents regressions, provides living documentation. Scientific community depends on data integrity.

**Cross-References**: See [Development Workflow - Testing](#testing-requirements) for additional testing standards.

---

### IV. Schema-First & Standards Compliance (NON-NEGOTIABLE)

**Principle**: NWB-LinkML schema is canonical source. Every data structure starts with schema definition.

#### 4.1 Schema Workflow (Mandatory Sequence)

**REQ-SCHEMA-001**: Define or extend LinkML schema FIRST

**REQ-SCHEMA-002**: Generate artifacts from schema
- JSON-LD contexts
- SHACL shapes
- Pydantic validators

**REQ-SCHEMA-003**: Implement validation logic using schema-derived validators

**REQ-SCHEMA-004**: Create tests using schema-derived validators

**REQ-SCHEMA-005**: ONLY THEN implement features

#### 4.2 Required Standards

**REQ-STD-001**: NWB-LinkML Schema as canonical source
- Version metadata recorded in PROV-O provenance

**REQ-STD-002**: LinkML validation at runtime
- Pydantic class generation
- Controlled vocabulary checking

**REQ-STD-003**: Semantic Web Standards (W3C compliance)
- RDF, OWL, SPARQL, SHACL mandatory for knowledge graphs

**REQ-STD-004**: NWB Inspector validation required
- Configurable rule sets
- Importance-weighted scoring

**REQ-STD-005**: FAIR Principles compliance mandatory
- Findable, Accessible, Interoperable, Reusable
- Automated checking

#### 4.3 Knowledge Graph Requirements

**REQ-KG-001**: Metadata enrichment
- Strain-to-species mappings
- Device specifications
- Experimental protocols
- Evidence quality assessment and conflict detection
- Enhanced confidence levels
- Complete reasoning chains
- Evidence hierarchy
- Iterative refinement workflows

**REQ-KG-002**: Entity relationship management
- Entities: Dataset, Session, Subject, Device, Lab, Protocol
- Semantic relationships
- Complete provenance using PROV-O ontology
- LinkML schema versioning metadata

**REQ-KG-003**: SPARQL query engine
- Complex metadata validation and enrichment rules
- SHACL shapes from NWB-LinkML for structural validation
- Custom validation rules and enrichment patterns
- Efficient query execution with indexing and optimization

**REQ-KG-004**: Schema-driven validation
- Validate LinkML instances (YAML/JSON) against NWB-LinkML schema
- Generate RDF using schema reference for consistent IRIs
- Run SHACL validation with schema-generated shapes
- Produce detailed reports

**REQ-KG-005**: RDF generation
- JSON-LD with schema-derived @context
- TTL (Turtle) formats
- Expose via standard semantic web protocols (SPARQL endpoints)
- Programmatic access APIs

**REQ-KG-006**: Core ontology integration
- NIFSTD (Neuroscience Information Framework)
- UBERON (anatomy)
- CHEBI (chemical entities)
- NCBITaxon (species)
- Basic concept mapping and semantic bridging
- OWL equivalence and subsumption with confidence scoring

**REQ-KG-007**: MCP server integration
- Clean APIs for metadata enrichment and validation
- Schema/shape validation APIs
- MCP tool exposure
- Concurrent access handling with consistency
- Structured responses compatible with agents and MCP server

**REQ-KG-008**: Schema & artifact management
- Regenerate JSON-LD contexts, SHACL shapes, RDF/OWL on schema updates
- Store with version metadata
- Pin schema version in PROV-O provenance

**REQ-KG-009**: Dynamic content handling
- Auto-discover unknown NWB data structures
- Runtime schema analysis (neurodata_type detection, pattern recognition)
- Adaptive RDF representations
- Preserve data types and semantic relationships

**Rationale**: Schema-first ensures semantic consistency, enables automated validation, facilitates interoperability with neuroscience ecosystem.

**Cross-References**: See [Technical Standards - Knowledge Graphs](#knowledge-graph-standards) for implementation details.

---

### V. Modular Architecture First

**Principle**: Clear separation of concerns with granular modularity. Independent testing and deployment.

#### 5.1 System-Level Modules (10 Major Components)

**REQ-MOD-001**: MCP Server Architecture
- Central orchestration hub with transport adapters

**REQ-MOD-002**: Agent Implementations
- 4 specialized agents: Conversation, Conversion, Evaluation, Metadata Questioner

**REQ-MOD-003**: Knowledge Graph Systems
- RDF/LinkML-based semantic enrichment and SPARQL queries

**REQ-MOD-004**: Validation & Quality Assurance
- 8 sub-modules (see 5.2)

**REQ-MOD-005**: Evaluation & Reporting
- NWB Inspector integration, quality metrics, visualization

**REQ-MOD-006**: Data Management & Provenance
- DataLad operations and provenance tracking

**REQ-MOD-007**: Testing & Quality Assurance
- Comprehensive testing infrastructure

**REQ-MOD-008**: Client Libraries & Integrations
- External interfaces and integration patterns

**REQ-MOD-009**: Core Project Organization
- Project structure, tooling, development standards

**REQ-MOD-010**: Test Verbosity Optimization
- Testing performance and optimization

#### 5.2 Validation System Sub-Modules (8 Components, 21 Requirements)

**Module 1: Core Validation Framework**

**REQ-VAL-001**: Implement `BaseValidator` abstract class
- Standardized interface

**REQ-VAL-002**: Provide `ValidationResult` and `ValidationIssue` dataclasses
- Structured output

**REQ-VAL-003**: Implement `ValidationConfig` class
- Profile-based settings
- Runtime updates
- Comprehensive error handling and logging

**Module 2: NWB Inspector Integration**

**REQ-VAL-004**: Integrate NWB Inspector
- Schema compliance checking

**REQ-VAL-005**: Categorize validation issues by severity
- Critical, warning, info, best_practice

**REQ-VAL-006**: Validate against current NWB schema versions
- Required field checks
- FAIR principles compliance
- Improvement suggestions

**Module 3: LinkML Schema Validation**

**REQ-VAL-007**: Load and parse LinkML schema definitions
- Generate Pydantic validation classes

**REQ-VAL-008**: Validate metadata in real-time
- Detailed field-level errors
- Controlled vocabulary with completion suggestions

**REQ-VAL-009**: Handle nested objects and cross-references

**Module 4: Quality Assessment Engine**

**REQ-VAL-010**: Implement quality metrics
- Completeness, consistency, accuracy, compliance

**REQ-VAL-011**: Provide weighted scoring algorithms
- Confidence intervals
- Required/optional field completeness analysis
- Prioritized recommendations

**Module 5: Domain Knowledge Validator**

**REQ-VAL-012**: Validate experimental parameter ranges
- Against known scientific bounds

**REQ-VAL-013**: Check biological plausibility
- Equipment/methodology consistency
- Electrophysiology, behavioral, imaging experiment-specific rules

**Module 6: Validation Orchestrator**

**REQ-VAL-014**: Coordinate execution of multiple validation engines
- Parallel/sequential workflows
- Validation dependency management
- Progress tracking

**REQ-VAL-015**: Aggregate results
- From multiple validators
- Conflict resolution
- Prioritize and rank issues by severity and impact

**Module 7: Reporting and Analytics**

**REQ-VAL-016**: Generate detailed validation reports
- Multiple formats (JSON, HTML, PDF)
- Executive summaries with visualizations

**REQ-VAL-017**: Track validation metrics over time
- Trend analysis
- Quality improvement recommendations

**Module 8: MCP Integration Layer**

**REQ-VAL-018**: Provide MCP tools for all major validation functions

**REQ-VAL-019**: Support asynchronous validation operations
- Integrate with MCP server infrastructure
- Health checks
- Standardized input/output formats

#### 5.3 Module Requirements (All Modules)

**REQ-MOD-ALL-001**: Self-contained modules
- Defined interfaces (abstract base classes)
- Independent testability and deployability
- Well-documented purpose and responsibilities

**REQ-MOD-ALL-002**: No cross-dependencies
- Communicate ONLY through defined contracts
- No direct imports between modules except through interfaces

**REQ-MOD-ALL-003**: Versioned interfaces
- Backward compatible
- Clear deprecation strategies

**REQ-MOD-ALL-004**: Contract testing
- Comprehensive contract tests verifying interfaces

**Rationale**: Enables parallel development, independent testing, easier debugging, clear ownership boundaries, system evolution without cascading changes.

**Cross-References**: See [Principle I](#i-mcp-centric-architecture-non-negotiable) for MCP module details.

---

### VI. Data Integrity & Provenance

**Principle**: Complete traceability from raw data through conversion to final NWB files. DataLad Python API exclusively.

#### 6.1 DataLad Requirements

**REQ-DL-001**: Python API exclusively (NEVER CLI)
- Use `import datalad.api as dl` for ALL operations
- Programmatic control, error handling, workflow integration

**REQ-DL-002**: Development dataset management
- Test datasets, evaluation data, conversion examples
- Configure DataLad annexing (dev files in git, large files annexed)
- DataLad subdataset management
- Ensure datasets available and properly versioned

**REQ-DL-003**: Conversion repository creation
- Create new DataLad repository for each conversion
- Track outputs and history
- Descriptive commit messages and proper versioning
- Tag successful conversions
- Summarize conversion history
- Easy access to all artifacts, scripts, evaluation results

**REQ-DL-004**: Output organization
- NWB files, conversion scripts, validation reports, evaluation reports, knowledge graph outputs
- Properly organize outputs from all specialized systems
- Record complete pipeline including validation, evaluation, knowledge graph steps
- All outputs versioned and accessible

**REQ-DL-005**: File annexing configuration
- .gitattributes: keep dev files in git, annex large files (>10MB)
- Handle conversion examples as subdatasets
- Handle common DataLad problems gracefully (missing subdatasets, locked files)

**REQ-DL-006**: MCP workflow integration
- Record all agent interactions, tool usage, decision points
- Track complete pipeline from analysis through evaluation
- Record error conditions, recovery attempts, final outcomes
- Complete audit trails for reproducibility

**REQ-DL-007**: Performance monitoring
- Track conversion throughput, storage usage, response times
- Automated cleanup of temporary files
- Basic duplicate detection
- Basic memory optimization through chunked operations
- Log DataLad operation status, performance, errors

#### 6.2 Provenance Tracking Requirements

**REQ-PROV-001**: Confidence levels for every metadata field
- `definitive` (verified facts)
- `high_evidence` (strong automated inference)
- `human_confirmed` (user validated)
- `human_override` (user corrected automated value)
- `medium_evidence` (reasonable inference)
- `heuristic` (pattern-based guess)
- `low_evidence` (weak inference)
- `placeholder` (temporary value)
- `unknown` (no confidence info)
- Also record: source type, derivation method, complete reasoning chain

**REQ-PROV-002**: Audit trails
- All modifications, decisions, transformations
- Evidence conflicts with resolution methods
- Distinguish evidence-based decisions from human overrides
- Present evidence summaries for human review when conflicts exist

**REQ-PROV-003**: Transparency reports
- Detailed provenance summaries
- Decision chains
- Evidence quality assessment
- Confidence distributions
- Allow users to verify and validate all automated decisions

#### 6.3 Repository Structure

**REQ-REPO-001**: GitHub repository structure
```
GitHub (code, config)
├── src/
├── tests/
├── docs/
└── .datalad/
```

**REQ-REPO-002**: GIN storage structure
```
GIN (large files via git-annex)
├── test-datasets/
├── evaluation-data/
└── conversion-examples/
```

**REQ-REPO-003**: Conversion outputs structure
```
Conversion Outputs (annexed)
├── nwb-files/
├── scripts/
├── validation-reports/
└── knowledge-graphs/
```

**Rationale**: Scientific reproducibility requires complete traceability. DataLad provides version control for data, enabling bit-for-bit reproduction.

**Cross-References**: See [Technical Standards - Data Management](#data-management-standards) for detailed operations.

---

### VII. Quality-First Development

**Principle**: Multi-dimensional comprehensive quality assessment. Valid structure without quality is scientifically useless.

#### 7.1 Multi-Dimensional Quality Requirements

**REQ-QUAL-001**: NWB validation foundation
- When nwb-inspector available: execute with configurable parameters, parse JSON output into structured results, timeout handling and error recovery
- When circuit breaker active: immediately use fallback validation, provide clear error messages with recovery guidance

**REQ-QUAL-002**: Technical quality assessment
- Schema compliance
- Data integrity
- Structure quality
- Performance characteristics
- Detailed scoring with specific remediation recommendations

**REQ-QUAL-003**: Scientific quality assessment
- Experimental completeness against domain standards
- Experimental design consistency validation
- Documentation adequacy evaluation
- Domain-specific improvement suggestions

**REQ-QUAL-004**: Usability quality assessment
- Documentation clarity
- Searchability and metadata richness evaluation
- Accessibility compliance checking
- User experience improvements using NLP metrics

**REQ-QUAL-005**: Quality orchestration
- Coordinate all evaluator modules with dependency management
- Support parallel execution of independent evaluators
- Apply configurable weights, combine scores appropriately
- Produce actionable recommendations
- Graceful degradation with partial results
- Maintain evaluation audit trails for traceability
- Real-time progress reporting

**REQ-QUAL-006**: Comprehensive reporting
- Executive summaries for non-technical audiences
- Detailed technical reports with metrics, validation results, recommendations
- Multiple formats (Markdown, HTML, PDF, JSON)
- Custom report templates with variable substitution
- Consistent formatting
- Simple HTML reports with embedded charts (lightweight JavaScript)
- HTML files work offline without external dependencies

#### 7.2 Quality Dimensions

**REQ-DIM-001**: Completeness
- Required fields present
- Optional fields populated
- Metadata richness assessed
- Completion recommendations prioritized by importance

**REQ-DIM-002**: Consistency
- Cross-field validation
- Temporal continuity verified
- Spatial registration accurate

**REQ-DIM-003**: Accuracy
- Scientific plausibility checks
- Unit conversions correct
- Numerical precision verified

**REQ-DIM-004**: Compliance
- NWB schema conformance
- FAIR principles adherence
- DANDI requirements met
- Domain standards followed

#### 7.3 Quality Workflow

**REQ-FLOW-001**: Weighted scoring algorithms
- Configurable thresholds

**REQ-FLOW-002**: Scientific plausibility checks
- For neuroscience data

**REQ-FLOW-003**: Remediation guidance mandatory
- For all validation issues

**REQ-FLOW-004**: Performance benchmarks
- With regression detection

**REQ-FLOW-005**: Continuous quality improvement
- Through analytics

#### 7.4 MCP Integration

**REQ-QUAL-MCP-001**: Clean APIs for evaluation services
- Standard MCP protocol
- Input validation and structured responses
- Expose functionality through MCP tools
- Handle concurrent evaluation requests with isolation

**REQ-QUAL-MCP-002**: Coordinate with dependent modules efficiently
- Respond to health checks within 1 second
- Provide request/response logging for monitoring

**Rationale**: Multi-dimensional assessment ensures converted data meets both technical and scientific standards. Protects scientific integrity.

**Cross-References**: See [Technical Standards - Validation](#validation--quality-assurance) for detailed metrics.

---

### VIII. Observability & Traceability

**Principle**: Comprehensive visibility into system operation for debugging, performance optimization, operational reliability.

#### 8.1 Logging Requirements

**REQ-LOG-001**: Structured logging (OpenTelemetry standards)
- JSON format
- Correlation IDs for distributed tracing across services
- Log levels per module (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Contextual information embedding
- Performance metrics in logs
- Security event logging
- Error fingerprinting for grouping
- Log sampling for high-volume operations

**REQ-LOG-002**: Error tracking
- Full stack traces
- Request/response recording
- State snapshots at failure
- Distributed tracing visualization
- Flame graphs for performance analysis
- Memory dump capabilities
- Goroutine/thread analysis
- Time-travel debugging support
- Configurable detail levels

**REQ-LOG-003**: Component logging verification (100% error path coverage)
- Appropriate log messages at correct severity levels
- Structured logging format (JSON)
- Correlation IDs for request tracing
- Performance metrics in logs
- Security event logging
- Error stack traces with context
- Rate limiting for log floods
- Log sanitization for sensitive data
- Log aggregation compatibility

**REQ-LOG-004**: Log levels per module
- Configurable per module
- Fine-grained control over verbosity
- No system restart required

**REQ-LOG-005**: Log aggregation support
- ELK/Fluentd compatibility
- Structured output easily parsed and indexed

**REQ-LOG-006**: Debug mode toggles
- Runtime toggles for debug mode
- Detailed logging without code changes or restarts

**REQ-LOG-007**: Remote debugging support
- Production troubleshooting capabilities
- Appropriate security controls

**REQ-LOG-008**: Interactive debugging tools
- For MCP server operations and agent interactions
- Step-through debugging of complex workflows

#### 8.2 Monitoring Requirements

**REQ-MON-001**: Conversion metrics (real-time dashboards)
- Throughput (files/hour, GB/hour)
- Latency percentiles (p50, p90, p99, p99.9)
- Error rates by category
- Resource utilization trends
- Queue depths and wait times
- Cache effectiveness metrics
- Agent performance scores
- Cost per conversion

**REQ-MON-002**: Performance metrics (Prometheus/OpenMetrics format)
- Response times (p50, p90, p99, max)
- Throughput (requests/sec, bytes/sec)
- Error rates by category
- Resource utilization (CPU, memory, disk, network)
- Queue depths and wait times
- Cache hit rates
- Database query performance
- Custom business metrics

**REQ-MON-003**: Usage analytics (predictive insights)
- Data format distribution
- Conversion success patterns
- Common failure modes
- User behavior patterns
- Resource usage patterns
- Peak usage times
- Geographic distribution
- Feature utilization rates

#### 8.3 Distributed Tracing Requirements

**REQ-TRACE-001**: OpenTelemetry standards
- Jaeger/Zipkin integration
- Cross-service visibility

**REQ-TRACE-002**: Trace propagation
- Across services
- Span relationship accuracy
- Timing information precision
- Baggage data preservation
- Sampling strategies
- Trace storage and retrieval
- Query capabilities
- Visualization accuracy

**REQ-TRACE-003**: Correlation IDs
- In all logs and traces
- End-to-end request tracking across distributed components

#### 8.4 Diagnostics Requirements

**REQ-DIAG-001**: Health checks (sub-second response)
- Liveness and readiness status
- Dependency status checks
- Configuration validation
- Resource availability
- Performance profiling data
- Thread dumps on demand
- Memory heap analysis
- Debugging endpoints

**REQ-DIAG-002**: Error capture (100% critical error capture)
- Full context
- Categorized by type and severity
- Deduplicated for similar issues
- Enriched with system state
- Tracked across services
- Aggregated for trends
- Alerted based on thresholds
- Integrated with incident management

#### 8.5 Observability Integration

**REQ-OBS-001**: Tool integration (full system visibility)
- Distributed tracing: Jaeger/Zipkin
- Metrics: Prometheus/OpenMetrics
- Logging: ELK/Fluentd
- APM: Datadog/New Relic
- Custom dashboards: Grafana
- Alerting: PagerDuty/Opsgenie
- Anomaly detection: ML models
- Capacity planning tools

**REQ-OBS-002**: Proactive monitoring (reduce MTTD)
- Anomaly detection algorithms
- Threshold-based alerting
- Trend analysis for degradation
- Predictive failure analysis
- Automatic issue correlation
- Root cause suggestion
- Impact assessment
- Automated remediation triggers

**Rationale**: Complex multi-agent systems require comprehensive observability. Structured logging enables automated analysis. Distributed tracing provides end-to-end visibility.

**Cross-References**: See [Development Workflow - Testing](#testing-requirements) for testing observability.

---

## Technical Standards

### Validation & Quality Assurance

**Standard Summary**: NWB Inspector integration, LinkML schema validation, domain knowledge validation, quality metrics, FAIR compliance.

**Key Requirements**:
- NWB Inspector: Configurable rule sets, timeout handling (30s for <1GB), fallback validation, JSON parsing, remediation guidance
- LinkML: Runtime validation, Pydantic generation, vocabulary checking, partial validation, nested objects
- Domain: Scientific plausibility checks, biological plausibility, equipment consistency, experiment-specific rules
- Quality: Weighted scoring, multi-dimensional (technical, scientific, usability), completeness (required 100%, optional >90%), consistency (cross-field, temporal, spatial), accuracy (units, precision, coordinates)
- FAIR: Automated Findable, Accessible, Interoperable, Reusable checking, metadata completeness, anti-pattern detection

**Cross-References**: See [Principle VII](#vii-quality-first-development) for quality requirements.

---

### Knowledge Graph Standards

**Standard Summary**: NWB-LinkML canonical source, RDF/OWL/SPARQL/SHACL, ontology integration, PROV-O provenance.

**Key Requirements**:
- Schema: NWB-LinkML canonical, version metadata in PROV-O, auto-regenerate JSON-LD/SHACL/RDF on schema updates
- Formats: JSON-LD (@context), Turtle (TTL), RDF/XML
- Validation: SHACL from NWB-LinkML, detailed reports, round-trip conversion
- Query: SPARQL endpoint, efficient indexing, complex rules, custom enrichment patterns, performance (<200ms simple, <30s complex)
- Ontologies: NIFSTD (neuroscience), UBERON (anatomy), CHEBI (chemicals), NCBITaxon (species), OWL equivalence/subsumption with confidence
- Provenance: PROV-O for transformations/enrichments, complete lineage raw NWB→RDF, evidence trails

**Cross-References**: See [Principle IV](#iv-schema-first--standards-compliance-non-negotiable) for schema requirements.

---

### Data Management Standards

**Standard Summary**: DataLad Python API exclusively, file annexing >10MB to GIN, Conventional Commits, repository structure.

**Key Requirements**:
- Operations: `import datalad.api as dl` ONLY, methods: `status()`, `save()`, `get()`, `create()`, `install()`, `add()`, `drop()`, proper exception handling
- Annexing: Files >10MB auto-annexed, GIN storage, `.gitattributes`: `* annex.largefiles=(largerthan=10MB)`, dev files <10MB in git
- Subdatasets: `datalad install` before use, version pinning, recursive operations `recursive=True`
- Commits: Conventional Commits format `type(scope): description`, types: feat/fix/docs/test/refactor/perf/ci/chore, include conversion details
- Structure: GitHub (src/, tests/, docs/, .datalad/), GIN (test-datasets/, evaluation-data/, conversion-examples/), Conversion Outputs (nwb-files/, scripts/, validation-reports/, knowledge-graphs/)

**Cross-References**: See [Principle VI](#vi-data-integrity--provenance) for DataLad requirements.

---

### Performance & Scale Standards

**Standard Summary**: Conversion, validation, API, query performance targets. Concurrent operations support.

**Key Requirements**:
- Conversion: Variable by format, baseline benchmarks required, memory <2GB standard workflows, chunked operations for large files, parallel processing with isolation
- Validation: <30s for <1GB files, streaming for >10GB, progressive validation during conversion
- API: <200ms p95 standard endpoints, <1s health checks, WebSocket/SSE for long-running ops
- Query: <200ms simple SPARQL, <30s complex enrichment with human review, <500ms metadata validation for real-time
- Concurrent: Parallel workflows with isolation, resource allocation per workflow, backpressure handling, fair scheduling

**Cross-References**: See [Principle III](#iii-test-driven-development-non-negotiable) for performance testing.

---

### Integration Standards

**Standard Summary**: MCP Protocol, HTTP/REST, WebSocket, GraphQL, Event-Driven messaging.

**Key Requirements**:
- MCP: Full spec compliance, stdin/stdout/Unix socket/TCP transports, tool discovery, structured errors
- HTTP/REST: OpenAPI 3.0, HATEOAS, content negotiation (JSON, MessagePack), compression (gzip, brotli)
- WebSocket: Real-time bidirectional, Socket.IO compatibility, auto-reconnect exponential backoff, message queuing during disconnects
- GraphQL: Optional query interface, subscription support, schema introspection, query complexity limits
- Event-Driven: RabbitMQ/Kafka for async processing, event sourcing for audit trails, saga pattern for distributed transactions, dead letter queues

**Cross-References**: See [Principle I](#i-mcp-centric-architecture-non-negotiable) for MCP architecture.

---

### Security Standards

**Standard Summary**: Input validation, injection prevention, authentication, authorization, audit logging, secrets management, OWASP compliance.

**Key Requirements**:
- Input: All inputs sanitized, schema validation (Pydantic), whitelist-based validation, size limits (<100MB default)
- Injection Prevention: SQL (parameterized queries only, no string interpolation), Path traversal (validate/sanitize paths, restrict to allowed dirs), XXE (disable external entities in XML parsers), Command (never pass user input to shell)
- Authentication: Token-based with JWT, refresh mechanisms with sliding expiration, timeout (30min default configurable), MFA support for high-security
- Authorization: RBAC where applicable, least privilege principle, resource-level permissions, audit logging of decisions
- Audit: Security events with full context, auth attempts (success/failure), auth failures, config changes, data access patterns
- Secrets: NO secrets in code/config, env vars for dev, Vault integration for prod (HashiCorp/AWS Secrets Manager), encrypted transit/rest, rotation policies
- OWASP: Top 10 mitigation, regular scanning (SAST, DAST), penetration testing for critical deployments, security training

**Cross-References**: See [Principle III](#iii-test-driven-development-non-negotiable) for security testing.

---

## Development Workflow

### Code Quality Requirements

**Language & Environment**: Python 3.11+ (prod), 3.8-3.12 compatible (clients), pixi, pyproject.toml

**Configuration**: pydantic-settings, nested classes, env var support with prefixes, validation at startup, feature flags

**Linting & Formatting**: ruff (lint, format, import org), line length 100, isort-compatible, automated by pre-commit hooks

**Type Checking**: mypy strict mode, type hints required all functions/methods, type stubs for external libs, generic types for collections/callables

**Code Quality Checks**: pylint, bandit (security), vulture (dead code), complexity (cyclomatic ≤10, maintainability index tracking)

**Pre-Commit Hooks** (bypass only for emergencies with justification):
- ruff format --check, ruff check, mypy
- Test execution for changed files
- Documentation generation
- Commit message format (Conventional Commits)
- Branch naming (feat/*, fix/*, docs/*)
- File size limits (<5MB without justification)
- Secret scanning (no API keys, passwords, tokens)

**Cross-References**: See [Principle III](#iii-test-driven-development-non-negotiable) for TDD workflow.

---

### Testing Requirements

**Test Categories**:
- **Unit**: Individual component isolation, 50+ cases per complex component, property-based (Hypothesis), boundary value analysis, forced error injection, benchmarks, memory leak detection, config validation
- **Integration**: Component interaction, 20+ agent coordination scenarios, state persistence, error propagation, retry logic, circuit breaker, graceful degradation, multi-step workflows
- **Contract**: OpenAPI conformance, 100% spec coverage mandatory, schema validation, field verification, type/enum checking, format compliance, pagination, HATEOAS links
- **E2E**: Real DataLad datasets, discovery/detection/extraction/conversion/validation, parallel processing, progress/cancellation, error recovery, workflows up to 1TB
- **Performance**: Baselines, regression detection (alert >10% slower), load/stress/scalability testing, cache effectiveness

**Test Data Management**: DataLad integration, 100+ fixtures, synthetic data, anonymization, test isolation

**Testing Standards**: Tests BEFORE implementation, property-based (Hypothesis), mutation testing for critical validation, snapshot testing, golden file testing, chaos engineering, cross-platform (Ubuntu 20.04+, macOS 11+, Windows 10+)

**Test Utilities**: Mock services, test data generation, fixture factories, assertion helpers, custom matchers, test decorators, cleanup utilities

**Cross-References**: See [Principle III](#iii-test-driven-development-non-negotiable) for complete testing requirements.

---

### CI/CD Requirements

**Automated Testing Triggers**:
- **Every Commit**: Unit tests (<5min), linting/formatting, type checking, secret detection
- **Every PR**: All unit tests, integration tests (<15min), contract tests (100% spec), code quality, security (SAST, dependencies), docs build, license compliance, commit validation, performance comparison
- **Nightly**: Comprehensive suite, E2E with real datasets, performance tests, full security (SAST, DAST), stability tests (24+ hours)
- **Weekly**: Dependency updates, license audit, full security scanning

**Testing Matrix**: Python 3.8-3.12, platforms (linux-64, osx-arm64, osx-64 if needed, windows for clients), dependencies (min, latest, dev)

**Quality Gates** (mandatory for merge):
- All tests passing
- Coverage: critical ≥90%, clients ≥85%, overall ≥80%
- No new vulnerabilities
- Performance within ±10% baseline
- Docs updated for user-facing changes
- Contract tests 100%
- Breaking changes documented with migration guide
- Architectural constraints verified

**Deployment**: Docker/OCI (multi-stage builds), Kubernetes (operators, CRDs, Helm charts), cloud-native (AWS/GCP/Azure, IaC with Terraform/Pulumi), blue-green deployments, deployment previews for PRs

**Cross-References**: See [Principle III](#iii-test-driven-development-non-negotiable) for testing details.

---

### Documentation Requirements

**API Documentation**: OpenAPI 3.0/AsyncAPI auto-generated, interactive (Swagger UI, ReDoc), code examples, auth guides, rate limiting, webhooks, SDK docs (Python primary), error code reference with remediation

**Code Documentation**: Google-style docstrings all public APIs, type hints all functions/methods, inline comments for complex logic (when, why, gotchas), module-level docstrings with overview/examples, example usage in docstrings, performance considerations, deprecation warnings with migration paths

**Architecture Documentation**: C4 diagrams (System Context, Container, Component, Code), sequence diagrams for key workflows, component interaction maps, data flow visualizations, deployment diagrams, ADRs (Architecture Decision Records), decision log with rationale/alternatives/consequences

**User Guides**: Quickstart (<10min to first conversion), tutorials for common scenarios (10+ examples), how-to guides, troubleshooting with common issues/solutions, FAQ

**Contribution Guides**: Dev setup (step-by-step <30min), testing strategies, code review process/checklists, coding standards/style guide, Git workflow (branching, commits, PRs), first good issues for newcomers

**Changelog**: Keep a Changelog format, versioned releases with semver, categorized (Added, Changed, Deprecated, Removed, Fixed, Security), migration guides for breaking changes, release notes with highlights

---

## Governance

### Amendment Process

**6-Step Process**:

1. **Documented Proposal**: Written proposal with specific wording changes, clear rationale why change is needed, examples how it improves project

2. **Impact Analysis**: Effects on specifications (which specs need updates?), implementations (what code changes?), development workflows (what processes change?), team processes (training needs, timeline)

3. **Community Review**: Discussion period (min 1 week MINOR, 2 weeks MAJOR), feedback and iteration opportunity, consensus-building

4. **Approval**: Consensus among maintainers where possible, maintainer decision per governance if no consensus, documented reasoning for approval/rejection

5. **Migration Plan**: Concrete steps for transitioning code/docs, timeline with milestones, backward compatibility or deprecation period, communication plan, rollback plan

6. **Version Increment**: Per semver rules, update version in constitution, update Sync Impact Report, notify stakeholders

---

### Versioning Policy

**Semantic Versioning (MAJOR.MINOR.PATCH)**:

**MAJOR (X.0.0)** - Breaking changes:
- Core principles removed or fundamentally redefined
- Governance structure changes invalidating processes
- Architectural changes requiring code rewrites
- Removal of mandatory compliance requirements
- Changes making existing implementations non-compliant
- Examples: Remove TDD requirement (breaks workflow), change from MCP-centric (requires rewrite), remove DataLad Python API requirement (allows CLI)

**MINOR (x.Y.0)** - Backward-compatible additions:
- New principles added (additional constraints)
- New sections or subsections (expanded guidance)
- Materially expanded guidance on existing principles
- Additional non-breaking constraints/requirements
- New quality gates not invalidating existing work
- Examples: Add AI ethics principle (expands requirements), add security standards section (new guidance), expand testing with new types (additions)

**PATCH (x.y.Z)** - Non-semantic changes:
- Clarifications of existing principles (no new requirements)
- Wording improvements for clarity
- Typo fixes and grammar corrections
- Formatting improvements
- Example additions or improvements
- Reorganization without content changes
- Examples: Clarify "DataLad Python API" meaning (no new req), fix typos (cosmetic), add examples (helpful not required)

**Version Increment Decision Tree**:
1. Does it break existing implementations or make them non-compliant? → MAJOR
2. Does it add new requirements or principles? → MINOR
3. Does it only clarify or fix without adding requirements? → PATCH

---

### Compliance Verification

**7-Point Checklist** (all PRs must verify):

1. **TDD Workflow Evidence**: Tests committed before implementation, test file timestamps earlier, git history shows test commits first, PR references test specs, tests demonstrated failing (RED phase)

2. **MCP Interface Consistency**: All functionality via MCP tools, no direct agent invocation, business logic in transport-agnostic core, adapters thin (<500 lines, <5% per adapter), zero business logic in adapters, functional parity verified by contract tests

3. **DataLad API Usage**: All operations use Python API (`import datalad.api as dl`), no CLI commands in production, proper exception handling, file annexing configured correctly (>10MB threshold)

4. **Schema Compliance**: All data structures in LinkML schemas first, schema-derived validators generated before implementation, runtime validation against schemas, tests use schema-derived validators, NWB-LinkML referenced for all NWB structures

5. **Modular Architecture**: Clear module boundaries, no cross-module dependencies except through interfaces, modules independently testable, contract tests for all module interfaces, new modules follow standard structure

6. **Quality Standards**: Multi-dimensional quality assessment implemented, completeness/consistency/accuracy/compliance checked, remediation guidance for all issues, scientific plausibility checks for domain data

7. **Observability**: Structured logging (JSON) with correlation IDs, error tracking with full stack traces, metrics collection for performance monitoring, audit trails for significant operations, OpenTelemetry standards for distributed tracing

**PR Review Checklist Template**:
```markdown
## Constitutional Compliance
- [ ] TDD: Tests before implementation (evidence in commit history)
- [ ] Contract Tests: New API endpoints have contract tests
- [ ] Schema-First: Data structures defined in schemas before code
- [ ] MCP Tools: Functionality via MCP tools (no direct agent access)
- [ ] DataLad API: Python API only (no CLI in production)
- [ ] Modular: Clear boundaries, contracts verified
- [ ] Quality: Multi-dimensional assessment implemented
- [ ] Observability: Structured logging, metrics, tracing present
- [ ] Documentation: Updated for user-facing changes
- [ ] Performance: Impact assessed, benchmarks within bounds
- [ ] Security: Implications considered, no new vulnerabilities
- [ ] Breaking Changes: Documented with migration guide (if applicable)

## Additional Checks
- [ ] Code coverage maintained or improved
- [ ] All tests passing (unit, integration, contract)
- [ ] No security vulnerabilities introduced
- [ ] Commit messages follow Conventional Commits
- [ ] PR linked to issue/feature request
```

---

### Constitutional Authority

**Hierarchy of Authority** (highest to lowest):
1. This Constitution (supreme governing document)
2. Architecture Decision Records (ADRs) - design decisions within constitutional bounds
3. Technical specifications and requirements
4. Implementation guidelines and best practices
5. Code comments and documentation

**Conflict Resolution**: When conflicts arise between constitution and other documentation, **constitutional principles take precedence**. Conflicting documentation MUST be updated to align.

**Exception Process** (6 requirements):

1. **Written Justification**: Why simpler constitutional-compliant alternatives insufficient, specific benefits of exception, risks introduced, mitigation strategies

2. **Maintainer Approval**: Explicit approval from ≥1 project maintainer, documented in PR comments or ADR, reasoning recorded

3. **ADR Documentation**: Create ADR documenting exception, rationale, alternatives considered, risks and mitigations, review and approval record

4. **Complexity Tracking**: Track in relevant spec's "Complexity Tracking" section, link to ADR and approval, explain why simpler alternatives rejected

5. **Time-Bound (if temporary)**: Exceptions SHOULD have sunset dates, plan for migration to constitutional compliance, timeline for removing exception

6. **Regular Review**: All exceptions reviewed quarterly, assessed for continued necessity, migration path updated if still needed

**Enforcement Mechanisms**:
- **Code Reviews**: All PRs reviewed for compliance using checklist, violations block merge until resolved or exception approved, reviewer comments reference specific principles
- **Automated Linters**: Pre-commit hooks enforce standards/tests/security, CI/CD verifies quality gates, automated checks for DataLad API usage/schema validation/test coverage
- **Architectural Fitness Functions**: Automated tests verifying constraints, contract tests ensuring adapter thin-ness (<500 lines, <5%), dependency analysis preventing cross-module violations, cyclic dependency detection
- **Violations**: PRs with violations cannot merge until fixed or exception approved, repeated violations trigger discussion if principle needs clarification, intentional violations without exception process are rejected

---

**Version**: 3.0.0
**Ratified**: 2025-10-08
**Last Amended**: 2025-10-08
**Supersedes**: All prior constitution versions (1.0.0, 1.1.0, 2.0.0, 2.0.1, and all PR-specific versions)

**Source**: Generated from comprehensive requirements across 10 specification files (1389 lines total) covering Agent Implementations, Client Libraries & Integrations, Core Project Organization, Data Management & Provenance, Evaluation & Reporting, Knowledge Graph Systems, MCP Server Architecture, Test Verbosity Optimization, Testing & Quality Assurance, and Validation & Quality Assurance.

**Format Note**: This is the hierarchical format optimized for navigation with requirement numbering and cross-references. A detailed format with expanded explanations is available as `constitution-v3.0.0-detailed.md`.
