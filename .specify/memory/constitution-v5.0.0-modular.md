<!--
Constitution Version: 5.0.0
Format: Modular Constitution (Project-Wide + Module-Specific)
Ratified: 2025-10-08
Last Amended: 2025-10-08
Source: All 10 requirements.md files (1,389 lines total)
Change Type: MAJOR - New modular organizational structure

This constitution provides both project-wide governance (applicable to all modules) and
module-specific principles that govern individual system components while maintaining
consistency across the entire project.
-->

# Agentic Neurodata Conversion - Project-Wide Constitution

**Version**: 5.0.0
**Ratified**: 2025-10-08
**Last Amended**: 2025-10-08
**Scope**: All 10 system modules

---

## CORE PRINCIPLES (Apply to ALL modules)

These principles are **universally applicable** across all modules and components of the Agentic Neurodata Conversion project. No module may violate these core principles without explicit constitutional exception.

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

**Principle**: All system functionality MUST be exposed exclusively through Model Context Protocol (MCP) tools. The MCP server is the single orchestration point for all operations across all modules.

**Universal Requirements**:
- All business logic resides in transport-agnostic core service layers
- Transport adapters (stdin/stdout, HTTP, WebSocket, gRPC) are thin (<500 LOC, <5% of module codebase)
- Adapters contain ZERO business logic - only protocol translation
- Functional parity across all transports verified by contract tests
- Direct agent invocation, service-to-service calls, or module-to-module communication without MCP mediation is PROHIBITED

**Rationale**: Centralizing through MCP creates a unified API surface across all modules, enables horizontal scaling, simplifies client integration, and maintains clean separation between business logic and transport mechanisms. This hexagonal architecture allows transport evolution without affecting any module's core functionality.

**Verification**:
- Contract tests SHALL verify all adapters across all modules invoke identical service methods
- Architecture fitness functions SHALL detect business logic in adapters
- Integration tests SHALL verify all module operations flow through MCP server

**Applies To**: All 10 modules without exception

---

### II. Test-Driven Development (NON-NEGOTIABLE)

**Principle**: All features in all modules MUST follow strict TDD workflow. Contract tests MUST be written and approved before ANY implementation begins in ANY module.

**Universal TDD Workflow**:
1. **Write Tests First**: Define expected behavior (contract, integration, unit)
2. **User Approval**: Obtain approval on test specifications
3. **Verify RED**: Tests fail appropriately (feature doesn't exist)
4. **Implement GREEN**: Minimum code to pass tests
5. **Refactor**: While maintaining green tests

**Universal Quality Gates**:
- **Critical Paths** (MCP server, agents, validation systems): ≥90% code coverage
- **Standard Modules** (knowledge graphs, data management, evaluation): ≥85% coverage
- **Client Libraries**: ≥85% coverage
- **Contract Tests**: 100% OpenAPI/AsyncAPI specification coverage
- **Pre-Implementation**: ALL API endpoints have contract tests before implementation

**Universal Test Categories**:
- **Unit Tests**: 50+ cases per complex component, property-based testing with Hypothesis
- **Integration Tests**: 20+ workflow scenarios per module, cross-module coordination
- **Contract Tests**: 100% API specification coverage, schema validation
- **E2E Tests**: Real DataLad-managed datasets, workflows up to 1TB
- **Performance Tests**: Benchmarks with regression detection (±10% baseline)

**Rationale**: Neuroscience data conversion is mission-critical. TDD ensures correctness, prevents regressions, provides living documentation, and catches integration issues early. The scientific community depends on data integrity across all system components.

**Verification**:
- Git history SHALL show tests committed before implementation in all modules
- CI pipelines SHALL enforce coverage thresholds for all modules
- Code reviews SHALL reject implementation without tests in any module
- Pre-commit hooks SHALL prevent commits that reduce coverage

**Applies To**: All 10 modules, all components, all features without exception

---

### III. Schema-First Development (NON-NEGOTIABLE)

**Principle**: NWB-LinkML schema is the canonical source for ALL modules. Every data structure and feature in every module MUST start with schema definition.

**Universal Schema Workflow** (Mandatory Sequence for ALL Modules):
1. **Define Schema**: Define or extend LinkML schema FIRST
2. **Generate Artifacts**: Generate JSON-LD contexts, SHACL shapes, Pydantic validators
3. **Implement Validation**: Implement validation logic using schema-derived validators
4. **Create Tests**: Create tests using schema-derived validators
5. **Implement Features**: ONLY THEN implement features

**Universal Standards** (Required for ALL Modules):
- **NWB-LinkML**: Canonical source with version metadata recorded in PROV-O provenance
- **LinkML Validation**: Runtime validation with Pydantic class generation
- **Semantic Web Standards**: RDF, OWL, SPARQL, SHACL (W3C compliance) mandatory
- **NWB Inspector**: Validation required for all converted files
- **FAIR Principles**: Findable, Accessible, Interoperable, Reusable compliance mandatory with automated checking

**Knowledge Graph Integration** (Applies to All Modules):
- Metadata enrichment with evidence quality assessment
- SPARQL query engine for validation rules
- Core ontology integration (NIFSTD, UBERON, CHEBI, NCBITaxon)
- Complete provenance using PROV-O ontology for all transformations
- Schema version pinning and recording in all outputs

**Rationale**: Schema-first ensures semantic consistency across all modules, enables automated validation, facilitates interoperability with the broader neuroscience ecosystem, and provides machine-readable contracts for all data structures.

**Verification**:
- Code reviews SHALL verify schema exists before implementation in all modules
- CI SHALL validate all data against schemas in all modules
- Integration tests SHALL verify schema-driven workflows across modules
- Schema drift detection SHALL alert on inconsistencies

**Applies To**: All 10 modules, all data structures, all interfaces

---

### IV. Modular Architecture & Clear Boundaries (NON-NEGOTIABLE)

**Principle**: All systems MUST follow clear separation of concerns with granular modularity. Modules MUST communicate ONLY through well-defined contracts.

**Universal Module Requirements**:
- **Self-Contained**: Each module is independently deployable
- **Defined Interfaces**: All interfaces documented with schemas (OpenAPI/AsyncAPI)
- **Contract-Based Communication**: Modules communicate ONLY through versioned contracts
- **Independent Testing**: Each module fully testable in isolation
- **Versioned APIs**: All module interfaces use semantic versioning
- **Backward Compatibility**: Breaking changes require MAJOR version bump

**10 System Modules** (Official Module List):
1. **MCP Server Architecture** - Central orchestration hub
2. **Agent Implementations** - Conversation, Conversion, Evaluation, Metadata Questioner (4 agents)
3. **Knowledge Graph Systems** - RDF/LinkML semantic enrichment
4. **Validation & Quality Assurance** - 8 sub-modules for comprehensive validation
5. **Evaluation & Reporting** - NWB Inspector integration, quality metrics
6. **Data Management & Provenance** - DataLad operations, provenance tracking
7. **Testing & Quality Assurance** - Testing infrastructure and frameworks
8. **Client Libraries & Integrations** - External interfaces and integration patterns
9. **Core Project Organization** - Project structure, tooling, standards
10. **Test Verbosity Optimization** - Testing performance optimization

**Universal Module Boundaries**:
- NO direct imports between modules (except through public APIs)
- NO shared mutable state between modules
- NO tight coupling or circular dependencies
- ALL inter-module communication through MCP server or defined contracts

**Rationale**: Modular architecture enables parallel development by independent teams, independent testing and deployment, easier debugging with clear ownership, and system evolution without cascading changes across modules.

**Verification**:
- Dependency analysis tools SHALL detect violations of module boundaries
- Architecture tests SHALL verify no forbidden dependencies
- Integration tests SHALL verify contract-based communication
- Build system SHALL enforce module independence

**Applies To**: All 10 modules with strict enforcement

---

### V. Data Integrity & Complete Provenance (NON-NEGOTIABLE)

**Principle**: Complete traceability MUST be maintained from raw data through all module operations to final NWB files. Every data transformation in every module MUST be recorded.

**Universal DataLad Requirements** (ALL Modules):
- **Python API Exclusively**: Use `import datalad.api as dl` - NEVER use CLI commands in ANY module
- **Repository Creation**: Each conversion creates its own DataLad repository
- **Complete History**: All transformations tracked with descriptive commits
- **File Annexing**: Files >10MB annexed to GIN (G-Node Infrastructure) storage
- **Subdataset Management**: Proper initialization and version pinning

**Universal Provenance Requirements** (ALL Modules):
- **Confidence Levels** (9 levels for ALL metadata fields in ALL modules):
  - `definitive`: Verified facts (highest confidence)
  - `high_evidence`: Strong automated inference with multiple sources
  - `human_confirmed`: User validated information
  - `human_override`: User corrected automated value
  - `medium_evidence`: Reasonable inference with single source
  - `heuristic`: Pattern-based inference
  - `low_evidence`: Weak inference or low confidence
  - `placeholder`: Temporary value requiring review
  - `unknown`: No confidence information available

- **Source Tracking**: Record data source for EVERY decision in EVERY module
- **Derivation Methods**: Document transformation methods used
- **Reasoning Chains**: Complete audit trail of automated decisions
- **Conflict Resolution**: Document how evidence conflicts were resolved

**Universal Repository Structure** (ALL Modules):
```
GitHub Repository:
  - Source code and configuration
  - Documentation and specs
  - Small test fixtures (<10MB)

GIN Storage (git-annex):
  - Large data files (>10MB)
  - Test datasets
  - Conversion outputs

Conversion Outputs (annexed):
  - NWB files with complete provenance
  - Conversion scripts with execution logs
  - Validation reports from all modules
  - Knowledge graph outputs
  - Complete audit trails
```

**Rationale**: Scientific reproducibility requires complete traceability. DataLad provides version control for data enabling bit-for-bit reproduction. Provenance tracking enables validation, debugging, and scientific credibility. Every module contributes to overall reproducibility.

**Verification**:
- ALL DataLad operations SHALL use Python API (automated checks in CI)
- Provenance SHALL be validated in E2E tests for all modules
- Audit trails SHALL be complete and verifiable
- Repository structure SHALL be enforced by CI

**Applies To**: All 10 modules, all data operations, all transformations

---

### VI. Quality-First Development & Observability (NON-NEGOTIABLE)

**Principle**: Quality assessment MUST be multi-dimensional across all modules. All operations in all modules MUST provide comprehensive visibility.

**Universal Quality Dimensions** (ALL Modules):
- **Completeness**: Required fields (100%), optional fields (>90% when applicable)
- **Consistency**: Cross-field validation, temporal continuity, spatial registration
- **Accuracy**: Scientific plausibility, unit conversions, numerical precision
- **Compliance**: NWB schema, FAIR principles, DANDI requirements, domain standards

**Universal Quality Workflow** (ALL Modules):
- NWB Inspector integration with configurable thresholds
- LinkML schema validation at runtime for all data
- Domain knowledge validation for neuroscience-specific data
- Weighted scoring with clear remediation guidance
- Progressive validation during processing (fail early)

**Universal Observability Requirements** (ALL Modules):
- **Structured Logging**: JSON format with correlation IDs (OpenTelemetry standards)
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL with appropriate use
- **Distributed Tracing**: Jaeger/Zipkin integration for cross-service visibility
- **Performance Metrics**: p50, p90, p99 latency; throughput; error rates by module
- **Health Checks**: <1 second response time with dependency status for all modules
- **Error Tracking**: Full stack traces, state snapshots, recovery suggestions
- **Correlation IDs**: Propagate across all module boundaries for request tracing

**Universal Monitoring** (ALL Modules):
- **Resource Utilization**: CPU, memory, disk, network per module
- **Error Rates**: Categorized by module, severity, and error type
- **Throughput**: Requests/sec, bytes/sec per module
- **Latency Distribution**: Percentiles tracked per module and operation
- **Queue Depths**: For asynchronous operations in all modules
- **Cache Effectiveness**: Hit rates, eviction rates per module

**Rationale**: Valid structure without quality is scientifically useless. Multi-dimensional assessment protects scientific integrity across all modules. Comprehensive observability enables debugging and performance optimization in complex multi-agent, multi-module systems.

**Verification**:
- Quality metrics SHALL be collected for all operations in all modules
- Logging SHALL use structured JSON format with correlation IDs
- Distributed tracing SHALL cover all modules and services
- Monitoring dashboards SHALL provide module-level visibility

**Applies To**: All 10 modules, all operations, all data outputs

---

## SHARED TECHNICAL STANDARDS

These technical standards apply across all modules to ensure consistency, interoperability, and maintainability.

### Language & Environment Standards

**Language Requirements**:
- **Python 3.11+**: Production code (all modules)
- **Python 3.8-3.12 Compatibility**: Client libraries and external interfaces
- **Type Hints**: Mandatory for all functions and methods in all modules
- **Docstrings**: Google-style for all public APIs in all modules

**Environment Management**:
- **pixi**: Reproducible environment management (all modules)
- **pyproject.toml**: Modern packaging standards (all modules)
- **Lock Files**: Committed to ensure reproducibility

**Configuration Management**:
- **pydantic-settings**: Type-safe configuration (all modules)
- **Environment Variables**: Prefixed by module (e.g., `MCP_`, `AGENT_`, `KG_`)
- **Configuration Validation**: At startup with clear error messages
- **Feature Flags**: Support for gradual rollout and A/B testing

### Code Quality Standards

**Linting & Formatting** (ALL Modules):
- **ruff**: Linting, formatting, import organization
- **Line Length**: 100 characters maximum
- **Import Sorting**: isort-compatible
- **Automated Fixes**: Applied by pre-commit hooks

**Type Checking** (ALL Modules):
- **mypy**: Strict mode mandatory
- **Type Stubs**: For external libraries without types
- **Generic Types**: For collections and callables
- **Type Aliases**: For complex type expressions

**Complexity Limits** (ALL Modules):
- **Cyclomatic Complexity**: ≤10 per function
- **Cognitive Complexity**: ≤15 per function
- **Function Length**: ≤50 lines (with justification for exceptions)
- **Class Length**: ≤300 lines (with justification for exceptions)

**Security Standards** (ALL Modules):
- **bandit**: Security scanning
- **Safety**: Dependency vulnerability checking
- **Secret Scanning**: No secrets in code or configuration
- **Input Sanitization**: All inputs validated and sanitized

### Testing Standards

**Test Organization** (ALL Modules):
```
tests/
├── unit/              # Module-specific unit tests
├── integration/       # Cross-module integration tests
├── contract/          # API contract tests
├── e2e/               # End-to-end workflow tests
├── performance/       # Performance and benchmarking tests
├── fixtures/          # Shared test fixtures and utilities
└── conftest.py        # pytest configuration and shared fixtures
```

**Test Data Management** (ALL Modules):
- **DataLad Integration**: Version-controlled test datasets
- **Lazy Loading**: For files >10MB
- **Synthetic Data**: Generation utilities for edge cases
- **Anonymization**: Utilities for sensitive data
- **Test Isolation**: Proper cleanup between tests

**Test Standards** (ALL Modules):
- **Tests Before Implementation**: TDD workflow enforced
- **Property-Based Testing**: Hypothesis for data transformations
- **Mutation Testing**: For critical validation logic
- **Snapshot Testing**: For complex outputs
- **Parametrized Tests**: For testing multiple scenarios

### CI/CD Standards

**Pipeline Stages** (ALL Modules):
```
Every Commit:
  - Unit tests (<5 minutes)
  - Linting and formatting checks
  - Type checking (mypy)
  - Secret scanning

Every Pull Request:
  - All unit tests
  - Integration tests (<15 minutes)
  - Contract tests (100% spec coverage)
  - Code quality analysis
  - Security scanning (SAST, dependency vulnerabilities)
  - Documentation build verification
  - Performance benchmark comparison

Nightly:
  - Comprehensive test suite
  - E2E tests with real datasets
  - Performance tests and profiling
  - Full security scanning (SAST, DAST)
  - Long-running stability tests

Weekly:
  - Dependency update checks
  - License compliance audit
  - Full security vulnerability scanning
```

**Quality Gates** (ALL Modules):
- All tests passing (100%)
- Code coverage thresholds maintained or improved
- No new security vulnerabilities
- Performance within ±10% of baseline
- Documentation updated for user-facing changes
- All contract tests passing (100% spec coverage)
- Breaking changes documented with migration guide

**Deployment Standards** (ALL Modules):
- **Containerization**: Docker/OCI compliance, multi-stage builds
- **Kubernetes**: Helm charts with customizable values
- **Blue-Green Deployments**: Zero-downtime updates
- **Rollback Capability**: Automated rollback on failure
- **Deployment Previews**: For pull requests

### Documentation Standards

**API Documentation** (ALL Modules):
- **OpenAPI 3.0**: For REST APIs (auto-generated from code)
- **AsyncAPI**: For message-based APIs
- **GraphQL Schema**: For GraphQL endpoints
- **Interactive Docs**: Swagger UI, ReDoc
- **Code Examples**: For common operations

**Code Documentation** (ALL Modules):
- **Google-Style Docstrings**: All public APIs
- **Type Hints**: All functions and methods
- **Inline Comments**: For complex logic (when, why, gotchas)
- **Module-Level Docstrings**: Overview and examples
- **Example Usage**: In docstrings for clarity

**Architecture Documentation** (ALL Modules):
- **C4 Diagrams**: System Context, Container, Component, Code levels
- **Sequence Diagrams**: For key workflows
- **Component Interaction Maps**: Module relationships
- **Data Flow Diagrams**: Data through system
- **ADRs**: Architecture Decision Records for significant decisions

**User Documentation** (ALL Modules):
- **Quickstart Guide**: <10 minutes to first result
- **Tutorials**: Step-by-step for common scenarios (10+ examples)
- **How-To Guides**: Specific tasks and recipes
- **Troubleshooting**: Common issues and solutions
- **FAQ**: Based on user questions

### Performance Standards

**Response Time Targets** (ALL Modules):
- **Standard API Endpoints**: <200ms p95 latency
- **Health Checks**: <1 second response time
- **Batch Operations**: Progress reporting every 10 seconds
- **Long-Running Operations**: WebSocket/SSE for progress updates

**Resource Constraints** (ALL Modules):
- **Memory**: <2GB for standard workflows per module
- **Disk I/O**: Chunked operations for large files
- **Network**: Efficient protocols (gRPC, msgpack)
- **CPU**: Multi-core utilization where applicable

**Scalability Targets** (ALL Modules):
- **Horizontal Scaling**: Support for load balancing
- **Vertical Scaling**: Efficient resource utilization
- **Concurrent Operations**: Thread-safe, process-safe
- **Backpressure Handling**: Graceful degradation under load

### Security Standards

**Authentication & Authorization** (ALL Modules):
- **Token-Based Authentication**: JWT with refresh tokens
- **Token Expiration**: 30 minutes default (configurable)
- **Refresh Mechanism**: Sliding expiration
- **RBAC**: Role-based access control where applicable
- **Principle of Least Privilege**: Minimum necessary permissions

**Input Validation** (ALL Modules):
- **Schema Validation**: All inputs validated against schemas
- **Whitelist Validation**: Preferred over blacklist
- **Size Limits**: Request body <100MB default
- **Rate Limiting**: Prevent abuse

**Injection Prevention** (ALL Modules):
- **SQL Injection**: Parameterized queries ONLY
- **Path Traversal**: Validate and sanitize file paths
- **XXE Attacks**: Disable external entity processing in XML
- **Command Injection**: Never pass user input to shell

**Secrets Management** (ALL Modules):
- **NO Secrets in Code**: Ever, no exceptions
- **Environment Variables**: Development only
- **Vault Integration**: Production (HashiCorp Vault, AWS Secrets Manager)
- **Encryption**: Transit and at rest
- **Rotation Policies**: Regular secret rotation

**OWASP Compliance** (ALL Modules):
- **OWASP Top 10**: Mitigation strategies for all
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **CORS**: Properly configured for APIs
- **Regular Audits**: Security scanning and penetration testing

---

## MODULE-SPECIFIC PRINCIPLES

Each module has specific governance principles derived from its unique requirements while adhering to all core principles above.

### Module 1: MCP Server Architecture

**Module Purpose**: Central orchestration hub coordinating all agents and managing the complete conversion workflow from dataset analysis to NWB file generation and evaluation.

#### 1.1 Transport-Agnostic Core Service (NON-NEGOTIABLE)

**Principle**: ALL business logic MUST reside in a transport-agnostic core service layer with ZERO dependencies on any transport protocol.

**Requirements**:
- Core service layer contains ALL business logic
- Domain entities and value objects (no transport-specific types)
- Use case implementations (independent of transport)
- Business rule enforcement (protocol-agnostic)
- Workflow orchestration logic (no protocol knowledge)
- State management (transport-independent)
- Persistence abstractions (no transport coupling)
- External service interfaces (clean boundaries)

**Verification**:
- Dependency analysis SHALL verify core has no transport imports
- Unit tests SHALL run core logic without any transport
- Architecture tests SHALL enforce clean architecture boundaries

#### 1.2 Thin Adapter Pattern (NON-NEGOTIABLE)

**Principle**: Each transport protocol MUST be implemented as a thin adapter layer with strict size and responsibility limits.

**Requirements**:
- **Size Limit**: <500 lines of code per adapter
- **Codebase Ratio**: <5% of total codebase per adapter
- **Responsibilities ONLY**:
  - Protocol-specific deserialization
  - Request mapping to service method calls
  - Protocol-specific errors and serialization
  - Connection lifecycle management
  - Protocol authentication/authorization
  - Protocol-specific metrics
- **ZERO Business Logic**: No domain logic, validation, or transformations

**Supported Transports**:
- **stdin/stdout**: For CLI and direct invocation
- **HTTP/REST**: OpenAPI 3.0 specification
- **WebSocket**: Real-time bidirectional communication
- **gRPC**: High-performance RPC
- **GraphQL**: (Optional) Flexible query interface

**Verification**:
- Line count checks SHALL fail builds exceeding 500 LOC per adapter
- Code coverage SHALL verify adapters have no untested business logic
- Code reviews SHALL reject business logic in adapters

#### 1.3 Functional Parity Verification (NON-NEGOTIABLE)

**Principle**: ALL transport adapters MUST provide identical functionality. Contract tests MUST verify equivalence.

**Requirements**:
- Contract tests verify all adapters:
  - Invoke identical service methods for same operations
  - Produce equivalent results for same inputs
  - Handle errors consistently across protocols
  - Maintain state coherence across transports
  - Support the same feature set
  - Provide comparable performance characteristics
  - Generate compatible audit logs
  - Preserve semantic equivalence

**Verification**:
- Contract test suite SHALL have 100% specification coverage
- Integration tests SHALL verify cross-transport compatibility
- Performance tests SHALL verify comparable latency

#### 1.4 Multi-Agent Workflow Orchestration

**Principle**: MCP server SHALL orchestrate all agent interactions with proper sequencing, error handling, and state management.

**Requirements**:
- **Sequential Workflows**: Proper ordering (analysis → metadata → conversion → validation)
- **Parallel Execution**: Where appropriate for independent operations
- **Dependency Resolution**: Manage dependencies between workflow steps
- **State Management**: Maintain context across agent interactions with versioning
- **Error Propagation**: Proper error handling from agents to clients
- **Retry Logic**: Exponential backoff with configurable limits
- **Timeout Management**: Per-agent and overall workflow timeouts
- **Workflow Cancellation**: Clean cancellation with resource cleanup

**Verification**:
- Integration tests SHALL verify all workflow patterns
- Chaos tests SHALL verify error handling and recovery
- Performance tests SHALL verify parallel execution benefits

#### 1.5 Format Detection & Interface Selection

**Principle**: MCP server SHALL automatically detect neuroscience data formats and select appropriate NeuroConv interfaces.

**Requirements**:
- **Format Detection** (25+ formats supported):
  - File extension analysis with confidence scoring
  - Magic byte detection for binary formats
  - Header parsing for structured formats
  - Directory structure pattern matching
  - Metadata file detection and parsing
  - Sampling-based content analysis
  - Format version identification
  - Multi-format dataset recognition

- **Interface Selection**:
  - Confidence-weighted matching to NeuroConv interfaces
  - Interface capability matrices (format support, features)
  - Performance characteristics consideration
  - Resource requirements assessment
  - Quality scores from past conversions
  - User preference learning
  - Cost optimization for cloud resources
  - Fallback interface chains with explainable selection logic

**Verification**:
- Unit tests SHALL verify format detection for all 25+ formats
- Integration tests SHALL verify interface selection accuracy
- E2E tests SHALL verify end-to-end format handling

#### 1.6 Validation Coordination

**Principle**: MCP server SHALL coordinate validation across multiple validation systems with ensemble techniques.

**Requirements**:
- **NWB Inspector Integration**: Configurable rule sets and thresholds
- **PyNWB Validator**: Schema compliance verification
- **DANDI Validator**: Repository readiness checking
- **Custom Validators**: Plugin system for extensibility
- **Format-Specific Validators**: Source fidelity verification
- **Cross-Validation**: Between multiple validation tools
- **Ensemble Validation**: Voting mechanisms for ambiguous results
- **Progressive Validation**: During conversion for early failure detection

**Verification**:
- Integration tests SHALL verify all validator integrations
- E2E tests SHALL verify validation coordination
- Contract tests SHALL verify validator plugin interface

#### 1.7 State Management & Recovery

**Principle**: MCP server SHALL manage workflow state with checkpoint recovery and transaction semantics.

**Requirements**:
- **Checkpoint Recovery**: Save state at key points for recovery after failure
- **Conversion Context**: Maintain and version context across agent interactions
- **Provenance Tracking**: Throughout entire pipeline with correlation IDs
- **Intermediate Results**: Persist for debugging and audit with retention policies
- **Concurrent Workflows**: Proper isolation between simultaneous conversions
- **Resource Allocation**: Manage resources across agents (CPU, memory, connections)
- **Transaction Semantics**: Atomic operations for multi-agent workflows
- **State Querying**: APIs for workflow state inspection
- **State Manipulation**: APIs for workflow control (pause, resume, cancel)

**Verification**:
- Integration tests SHALL verify checkpoint recovery
- Chaos tests SHALL verify recovery from various failure modes
- Performance tests SHALL verify concurrent workflow isolation

#### 1.8 Observability & Monitoring

**Principle**: MCP server SHALL provide comprehensive observability into all operations with structured logging and distributed tracing.

**Requirements**:
- **Structured Logging**: JSON format with correlation IDs for all operations
- **Distributed Tracing**: OpenTelemetry integration for cross-service visibility
- **Performance Metrics**: Response times (p50, p90, p99), throughput, error rates
- **Health Checks**: Dependency status, resource availability, service readiness
- **Error Tracking**: Full context, stack traces, state snapshots at failure
- **Audit Trails**: Complete operation logs for compliance and debugging
- **Analytics**: Trend tracking, pattern detection, anomaly detection
- **Alerting**: Proactive alerts for failures, degradation, resource exhaustion

**Verification**:
- All operations SHALL produce structured logs with correlation IDs
- Distributed traces SHALL cover all agent interactions
- Monitoring dashboards SHALL provide real-time visibility

---

### Module 2: Agent Implementations

**Module Purpose**: Specialized agents orchestrated by MCP server to perform specific aspects of neuroscience data conversion.

#### 2.1 Conversation Agent Principles

**2.1.1 Dataset Analysis & Metadata Extraction (REQ-1)**

**Principle**: Conversation agent SHALL analyze dataset contents and extract metadata while minimizing user burden.

**Requirements**:
- Analyze dataset contents and identify data formats
- Identify experimental context from file structure and metadata
- Detect missing essential metadata fields
- Generate natural language questions understandable to non-expert users
- Validate user responses against domain knowledge
- Suggest corrections for inconsistencies
- Provide structured summaries with clear provenance marking
- Avoid repeated questions by tracking previous interactions

**Acceptance Criteria**:
1. WHEN dataset directory provided THEN analyze contents, identify formats, context, missing fields
2. WHEN essential metadata missing THEN generate understandable questions with necessary details
3. WHEN user responds THEN validate against domain knowledge, suggest corrections
4. WHEN extraction complete THEN provide structured summary with provenance (user vs auto-detected)

**Verification**:
- Unit tests SHALL verify format detection accuracy (>95%)
- Integration tests SHALL verify question generation appropriateness
- E2E tests SHALL verify complete metadata extraction workflows

**2.1.2 Domain-Aware Interaction**

**Principle**: Conversation agent SHALL only ask questions that cannot be inferred from data or domain knowledge.

**Requirements**:
- Infer metadata from file structure, naming conventions, timestamps
- Apply domain knowledge to make reasonable assumptions
- Only ask for information that is essential and unambiguous
- Track conversation history to avoid repetition
- Provide context for why information is needed
- Offer suggestions based on similar datasets

**Verification**:
- Unit tests SHALL verify inference accuracy
- Integration tests SHALL verify question minimization
- User studies SHALL validate question appropriateness

#### 2.2 Conversion Agent Principles

**2.2.1 NeuroConv Script Generation (REQ-2)**

**Principle**: Conversion agent SHALL generate and execute valid NeuroConv scripts that handle specific data formats and experimental setups.

**Requirements**:
- Select appropriate NeuroConv DataInterface classes based on detected formats
- Generate valid Python code handling specific data formats
- Handle experimental setups with proper configuration
- Populate NWB metadata fields from extracted metadata
- Mark which fields are auto-generated vs. user-provided
- Execute generated scripts with proper error handling
- Provide clear error messages and corrective action suggestions on failure
- Record complete provenance information for successful conversions

**Acceptance Criteria**:
1. WHEN metadata and file mappings provided THEN select appropriate DataInterface classes
2. WHEN generating scripts THEN create valid Python code for specific formats and setups
3. WHEN executing THEN populate NWB metadata, mark origins (auto vs user)
4. WHEN conversion fails THEN provide clear error messages with corrective actions
5. WHEN conversion succeeds THEN record complete provenance

**Verification**:
- Unit tests SHALL verify DataInterface selection for all supported formats
- Integration tests SHALL verify script generation validity
- E2E tests SHALL verify end-to-end conversion success

**2.2.2 Error Handling & Recovery**

**Principle**: Conversion agent SHALL handle failures gracefully with clear guidance for recovery.

**Requirements**:
- Detect errors early in conversion process
- Provide actionable error messages with specific remediation steps
- Suggest alternative approaches when primary method fails
- Support partial conversions when possible
- Save intermediate results for debugging
- Provide detailed logs for troubleshooting

**Verification**:
- Unit tests SHALL verify error detection accuracy
- Integration tests SHALL verify error message quality
- E2E tests SHALL verify recovery procedures

#### 2.3 Evaluation Agent Principles

**2.3.1 Validation Coordination (REQ-3)**

**Principle**: Evaluation agent SHALL coordinate with validation, evaluation, and knowledge graph systems to produce comprehensive assessments.

**Requirements**:
- Coordinate with validation systems to assess file quality and compliance
- Coordinate with evaluation systems to generate reports and visualizations
- Coordinate with knowledge graph systems to generate semantic representations
- Integrate results from all systems into cohesive outputs
- Handle failures in individual systems gracefully
- Provide unified error reporting across systems

**Acceptance Criteria**:
1. WHEN NWB file generated THEN coordinate with validation systems for quality assessment
2. WHEN validation complete THEN coordinate with evaluation systems for reports
3. WHEN knowledge graphs needed THEN coordinate with KG systems for semantic representations
4. WHEN providing results THEN integrate all results into cohesive outputs

**Verification**:
- Integration tests SHALL verify coordination with all systems
- Contract tests SHALL verify interfaces to validation/evaluation/KG systems
- E2E tests SHALL verify end-to-end evaluation workflows

#### 2.4 Metadata Questioner Principles

**2.4.1 Dynamic Question Generation (REQ-4)**

**Principle**: Metadata questioner SHALL dynamically generate contextually appropriate questions based on experimental type and data format.

**Requirements**:
- Generate questions based on experimental type (electrophysiology, imaging, behavior)
- Adapt questions to data format specifics
- Provide clear explanations of why information is needed
- Explain how information will be used in conversion
- Validate answers against domain constraints
- Suggest alternatives for invalid responses
- Integrate responses into structured metadata with provenance tracking

**Acceptance Criteria**:
1. WHEN metadata gaps identified THEN generate contextually appropriate questions
2. WHEN asking questions THEN provide clear explanations of need and use
3. WHEN receiving responses THEN validate against domain constraints, suggest alternatives
4. WHEN questions complete THEN integrate responses with proper provenance

**Verification**:
- Unit tests SHALL verify question appropriateness for different experiment types
- Integration tests SHALL verify answer validation
- E2E tests SHALL verify metadata integration

#### 2.5 Universal Agent Requirements (REQ-5, REQ-6, REQ-7, REQ-8)

**2.5.1 Consistent Interfaces**

**Principle**: ALL agents SHALL follow consistent patterns for error handling, logging, and responses.

**Requirements**:
- Consistent error handling patterns across all agents
- Structured responses in standardized format
- Clear logging with correlation IDs
- Progress indicators for long-running operations (>10 seconds)
- Actionable error messages with remediation steps
- Results in formats easily processed by MCP server

**Verification**:
- Contract tests SHALL verify interface consistency
- Integration tests SHALL verify error handling uniformity

**2.5.2 Configuration & Monitoring**

**Principle**: ALL agents SHALL be configurable and provide comprehensive monitoring.

**Requirements**:
- Configuration of LLM providers (OpenAI, Anthropic, etc.)
- Configuration of model parameters (temperature, max tokens, etc.)
- Configuration of operational settings (timeouts, retries, etc.)
- Metrics on processing time, success rates, resource usage
- Detailed logging of internal operations and decision-making
- Graceful handling of timeouts, retries, and service failures

**Verification**:
- Unit tests SHALL verify all configuration options
- Integration tests SHALL verify monitoring metrics accuracy

**2.5.3 Provenance & Transparency**

**Principle**: ALL agents SHALL maintain complete provenance and provide transparent decision-making.

**Requirements**:
- Record reasoning and data sources for each decision
- Clearly mark field origins (auto-generated vs. user-provided vs. externally enriched)
- Provide citations and/or confidence scores for external information
- Explain heuristics or logic used for inferences
- Provide comprehensive audit trails of all operations and transformations

**Verification**:
- Unit tests SHALL verify provenance recording
- Integration tests SHALL verify audit trail completeness
- E2E tests SHALL verify end-to-end transparency

**2.5.4 Testing Support**

**Principle**: ALL agents SHALL support comprehensive testing without external dependencies.

**Requirements**:
- Mock modes that don't require external LLM services
- Deterministic test modes for consistent testing
- Graceful handling of edge cases and malformed inputs
- Correct operation when called by MCP server in realistic scenarios

**Verification**:
- Unit tests SHALL use mock modes exclusively
- Integration tests SHALL verify realistic MCP server interactions
- E2E tests SHALL use real LLM services

---

### Module 3: Client Libraries & Integrations

**Module Purpose**: Provide robust, user-friendly client libraries and integration patterns for external systems.

#### 3.1 Python Client Library (REQ-1, REQ-2)

**Principle**: Provide a comprehensive Python client that simplifies MCP server interaction.

**Requirements**:
- **Simple API**: Intuitive methods for common operations
- **Type Safety**: Complete type hints with mypy validation
- **Error Handling**: Comprehensive error handling with recovery strategies
- **Authentication**: Support for all authentication methods
- **Session Management**: Connection pooling, keepalive, reconnection
- **Async Support**: Both synchronous and asynchronous APIs
- **Progress Tracking**: Real-time progress updates via callbacks
- **Batch Operations**: Efficient batch processing support
- **Retry Logic**: Configurable retry with exponential backoff
- **Timeout Management**: Per-operation and global timeouts

**Verification**:
- Unit tests SHALL verify all API methods
- Integration tests SHALL verify MCP server communication
- E2E tests SHALL verify complete workflows

#### 3.2 Error Handling & Recovery (REQ-3)

**Principle**: Client libraries SHALL provide robust error handling with automatic recovery where possible.

**Requirements**:
- **Network Errors**: Automatic retry with exponential backoff
- **Timeout Errors**: Configurable timeout policies
- **Authentication Errors**: Token refresh and re-authentication
- **Server Errors**: Graceful degradation and fallback strategies
- **Data Errors**: Clear error messages with remediation guidance
- **Circuit Breaker**: Prevent cascading failures
- **Fallback Mechanisms**: Alternative strategies when primary fails

**Verification**:
- Unit tests SHALL verify all error handling paths
- Chaos tests SHALL verify recovery mechanisms
- Integration tests SHALL verify circuit breaker behavior

#### 3.3 AI-Powered Assistance (REQ-4)

**Principle**: Client libraries SHALL provide AI-powered assistance for common tasks.

**Requirements**:
- **Code Generation**: Generate boilerplate conversion code
- **Parameter Suggestions**: Suggest optimal parameters based on data
- **Error Diagnosis**: AI-powered error analysis and suggestions
- **Best Practices**: Suggest best practices for common scenarios
- **Documentation**: Context-aware documentation and examples

**Verification**:
- Unit tests SHALL verify AI assistance accuracy
- Integration tests SHALL verify suggestion quality
- User studies SHALL validate usefulness

#### 3.4 Integration Patterns (REQ-5)

**Principle**: Provide well-documented integration patterns for common scenarios.

**Requirements**:
- **Jupyter Notebooks**: Interactive analysis and conversion
- **Workflow Systems**: Integration with Airflow, Prefect, etc.
- **Cloud Platforms**: AWS, GCP, Azure integration guides
- **CI/CD Pipelines**: Automated conversion in CI/CD
- **Data Lakes**: Integration with data lake architectures
- **Monitoring Systems**: Integration with observability tools

**Verification**:
- Integration examples SHALL be tested in CI
- Documentation SHALL include working examples
- User feedback SHALL validate pattern effectiveness

#### 3.5 Testing Infrastructure (REQ-6)

**Principle**: Client libraries SHALL provide comprehensive testing utilities.

**Requirements**:
- **Mock Server**: In-memory mock MCP server for testing
- **Test Fixtures**: Common test data and scenarios
- **Assertion Helpers**: Specialized assertions for NWB data
- **Test Utilities**: Helpers for common test patterns
- **Performance Testing**: Benchmarking utilities

**Verification**:
- All testing utilities SHALL be tested
- Examples SHALL demonstrate test utility usage
- Documentation SHALL cover testing best practices

---

### Module 4: Core Project Organization

**Module Purpose**: Establish project structure, development standards, and tooling infrastructure.

#### 4.1 Project Structure (REQ-1)

**Principle**: Maintain clear, consistent project structure across all modules.

**Requirements**:
- **Monorepo Structure**: All modules in single repository with clear boundaries
- **Module Organization**: Consistent structure within each module
- **Configuration Files**: Centralized configuration with module overrides
- **Documentation**: Co-located with code, up-to-date
- **Build System**: Consistent build and packaging across modules

**Verification**:
- CI SHALL verify project structure consistency
- Linters SHALL enforce structural rules
- Documentation SHALL reflect actual structure

#### 4.2 Development Standards (REQ-2)

**Principle**: Enforce consistent development standards across all modules.

**Requirements**:
- **Coding Standards**: Python style guide adherence (PEP 8, PEP 257)
- **Code Review**: Mandatory reviews for all changes
- **Branch Strategy**: Clear branching and merging strategy
- **Commit Messages**: Conventional commits format
- **Pull Request Templates**: Standardized PR descriptions
- **Issue Templates**: Standardized issue reporting

**Verification**:
- Pre-commit hooks SHALL enforce standards
- CI SHALL verify compliance
- Code reviews SHALL check adherence

#### 4.3 Tooling Infrastructure (REQ-3, REQ-4)

**Principle**: Provide consistent tooling across all modules.

**Requirements**:
- **Environment Management**: pixi for reproducible environments
- **Dependency Management**: Lock files for reproducibility
- **Build Tools**: Consistent build process
- **Testing Framework**: pytest with consistent configuration
- **Linting Tools**: ruff, bandit, mypy
- **Documentation Tools**: Sphinx, MkDocs
- **CI/CD Platform**: GitHub Actions with reusable workflows

**Verification**:
- All tools SHALL have configuration in repository
- CI SHALL use same tools as local development
- Documentation SHALL cover tool usage

#### 4.4 Quality Gates (REQ-5)

**Principle**: Enforce quality gates at multiple levels.

**Requirements**:
- **Pre-Commit**: Local quality checks before commit
- **Pre-Push**: Additional checks before push
- **Pull Request**: Comprehensive checks before merge
- **Release**: Additional validation before release

**Verification**:
- CI SHALL enforce all quality gates
- Failed gates SHALL block progression
- Override mechanism SHALL require approval

---

### Module 5: Data Management & Provenance

**Module Purpose**: Manage data lifecycle and provenance tracking using DataLad.

#### 5.1 DataLad Python API (REQ-1) (NON-NEGOTIABLE)

**Principle**: ALL DataLad operations MUST use Python API exclusively - CLI commands are PROHIBITED in production code.

**Requirements**:
- `import datalad.api as dl` for ALL operations
- Use `dl.status()`, `dl.save()`, `dl.get()`, `dl.create()`, `dl.install()`, `dl.add()`, `dl.drop()`
- Proper exception handling for all DataLad operations
- Programmatic control enabling error recovery
- Integration with Python workflows

**Verification**:
- Static analysis SHALL detect CLI command usage
- CI SHALL fail on CLI command detection
- Code reviews SHALL reject CLI commands

#### 5.2 Development Dataset Management (REQ-2)

**Principle**: Use DataLad to manage all development datasets with proper versioning.

**Requirements**:
- Test datasets managed with DataLad
- Evaluation data versioned with DataLad
- Conversion examples tracked with DataLad
- Proper DataLad annexing configuration (dev files in git, large files annexed)
- Subdataset management for modular datasets
- Datasets available and properly versioned

**Verification**:
- CI SHALL verify dataset availability
- Tests SHALL use DataLad-managed datasets
- Documentation SHALL reference dataset versions

#### 5.3 Conversion Repository Creation (REQ-3)

**Principle**: Each conversion SHALL create its own DataLad repository for complete tracking.

**Requirements**:
- New DataLad repository for each conversion
- Track all conversion outputs and history
- Descriptive commit messages with metadata
- Proper versioning of conversion iterations
- Tag successful conversions with meaningful tags
- Summarize conversion history
- Easy access to all artifacts, scripts, and results

**Verification**:
- E2E tests SHALL verify repository creation
- Conversion outputs SHALL be in DataLad repositories
- Repositories SHALL have complete history

#### 5.4 Output Organization (REQ-4)

**Principle**: Organize all conversion outputs systematically within DataLad repositories.

**Requirements**:
- NWB files with complete metadata
- Conversion scripts with execution parameters
- Validation reports from all validators
- Evaluation reports with visualizations
- Knowledge graph outputs in multiple formats
- Complete pipeline documentation
- Proper versioning of all outputs
- Accessible organization structure

**Verification**:
- E2E tests SHALL verify output organization
- Documentation SHALL specify output structure
- Tools SHALL expect consistent organization

#### 5.5 File Annexing Configuration (REQ-5)

**Principle**: Configure git-annex properly to keep development files in git and only annex large data files.

**Requirements**:
- `.gitattributes` configuration: `* annex.largefiles=(largerthan=10MB)`
- Development files (<10MB) in git for fast access
- Large files (>10MB) annexed to GIN storage
- Conversion examples as subdatasets with proper management
- Handle common DataLad problems (missing subdatasets, locked files) gracefully

**Verification**:
- CI SHALL verify annexing configuration
- Tests SHALL verify correct file storage
- Documentation SHALL explain annexing strategy

#### 5.6 MCP Workflow Integration (REQ-6)

**Principle**: Record complete provenance of all MCP workflow operations.

**Requirements**:
- Record all agent interactions with timestamps
- Record all tool usage with parameters
- Record all decision points with reasoning
- Track complete pipeline from analysis through evaluation
- Record error conditions, recovery attempts, and outcomes
- Provide complete audit trails for reproducibility

**Verification**:
- Integration tests SHALL verify provenance recording
- E2E tests SHALL verify complete audit trails
- Audit trails SHALL be queryable and analyzable

#### 5.7 Performance Monitoring (REQ-7)

**Principle**: Track DataLad operation performance and optimize for efficiency.

**Requirements**:
- Track conversion throughput (files/hour, GB/hour)
- Track storage usage and growth
- Track basic response times for DataLad operations
- Automated cleanup of temporary files
- Basic duplicate detection
- Basic memory optimization through chunked operations
- Log DataLad operation status, performance metrics, error conditions

**Verification**:
- Monitoring SHALL track DataLad metrics
- Performance tests SHALL benchmark operations
- Alerts SHALL trigger on performance degradation

---

### Module 6: Evaluation & Reporting

**Module Purpose**: Validate NWB files and generate comprehensive quality reports.

#### 6.1 NWB Inspector Integration (REQ-1)

**Principle**: Integrate NWB Inspector with fallback capabilities for robust validation.

**Requirements**:
- Execute nwb-inspector with configurable parameters
- Parse JSON output into structured results
- Timeout handling (30s default for <1GB files)
- Error recovery and retry logic
- Circuit breaker protection for persistent failures
- Fallback validation when circuit breaker active
- Clear error messages with recovery guidance

**Verification**:
- Unit tests SHALL verify inspector integration
- Integration tests SHALL verify fallback behavior
- E2E tests SHALL verify end-to-end validation

#### 6.2 Multi-Dimensional Quality Assessment (REQ-2, REQ-3, REQ-4)

**Principle**: Assess quality across multiple dimensions with actionable feedback.

**Requirements**:
- **Technical Quality**: Schema compliance, data integrity, structure quality, performance
- **Scientific Quality**: Experimental completeness, design consistency, documentation adequacy
- **Usability Quality**: Documentation clarity, searchability, metadata richness, accessibility
- Detailed scoring with specific remediation recommendations
- Domain-specific improvement suggestions
- Priority ranking of issues by impact

**Verification**:
- Unit tests SHALL verify all quality dimensions
- Integration tests SHALL verify scoring accuracy
- User studies SHALL validate recommendation quality

#### 6.3 Quality Orchestration (REQ-5)

**Principle**: Coordinate all evaluator modules with proper dependency management.

**Requirements**:
- Coordinate all evaluator modules
- Proper dependency management between evaluators
- Support parallel execution of independent evaluators
- Apply configurable weights to different quality dimensions
- Combine scores appropriately into overall quality score
- Produce actionable recommendations prioritized by impact
- Graceful degradation with partial results
- Maintain evaluation audit trails for traceability
- Real-time progress reporting

**Verification**:
- Integration tests SHALL verify orchestration
- Performance tests SHALL verify parallel execution benefits
- Audit trails SHALL be complete and queryable

#### 6.4 Comprehensive Reporting (REQ-6)

**Principle**: Generate reports in multiple formats suitable for different audiences.

**Requirements**:
- **Executive Summaries**: For non-technical audiences, high-level overview
- **Detailed Technical Reports**: With metrics, validation results, recommendations
- **Multiple Formats**: Markdown, HTML, PDF, JSON with consistent information
- **Custom Templates**: Variable substitution, consistent formatting
- **Simple HTML Reports**: With embedded charts using lightweight JavaScript
- **Offline Support**: HTML files work without external dependencies

**Verification**:
- Unit tests SHALL verify report generation for all formats
- Integration tests SHALL verify report content accuracy
- User studies SHALL validate report usefulness

#### 6.5 MCP Integration (REQ-7)

**Principle**: Provide clean APIs for evaluation services through MCP protocol.

**Requirements**:
- Standard MCP protocol compliance
- Input validation and structured responses
- Expose functionality through appropriate MCP tools
- Handle concurrent evaluation requests with isolation
- Coordinate with dependent modules efficiently
- Respond to health checks within 1 second
- Provide request/response logging for monitoring

**Verification**:
- Contract tests SHALL verify MCP interface
- Integration tests SHALL verify concurrent request handling
- Performance tests SHALL verify response time targets

---

### Module 7: Knowledge Graph Systems

**Module Purpose**: Provide RDF/LinkML-based semantic enrichment and SPARQL querying.

#### 7.1 Metadata Enrichment (REQ-1)

**Principle**: Use knowledge graph to suggest enrichments with evidence quality assessment.

**Requirements**:
- Strain-to-species mappings with confidence scores
- Device specifications from knowledge base
- Experimental protocols with versioning
- Evidence quality assessment for all enrichments
- Conflict detection between sources
- Enhanced confidence levels (9 levels)
- Complete reasoning chains for decisions
- Evidence hierarchy (primary sources prioritized)
- Iterative refinement workflows

**Verification**:
- Unit tests SHALL verify enrichment accuracy
- Integration tests SHALL verify evidence assessment
- E2E tests SHALL verify complete enrichment workflows

#### 7.2 Entity Relationship Management (REQ-2)

**Principle**: Maintain entities with semantic relationships and complete provenance.

**Requirements**:
- **Entities**: Dataset, Session, Subject, Device, Lab, Protocol with all attributes
- **Relationships**: Semantic relationships between entities (part-of, derives-from, uses, etc.)
- **Provenance**: Complete provenance using PROV-O ontology
- **Versioning**: LinkML schema versioning metadata
- **Lifecycle**: Entity creation, updates, deprecation

**Verification**:
- Unit tests SHALL verify entity management
- Integration tests SHALL verify relationship integrity
- Provenance SHALL be complete and traceable

#### 7.3 SPARQL Query Engine (REQ-3)

**Principle**: Provide efficient SPARQL query engine for validation and enrichment rules.

**Requirements**:
- Complex metadata validation rules in SPARQL
- Enrichment patterns in SPARQL
- Custom validation rules definable by users
- Efficient query execution with indexing
- Query optimization for common patterns
- Performance targets: <200ms simple queries, <30s complex enrichment

**Verification**:
- Unit tests SHALL verify query correctness
- Performance tests SHALL verify latency targets
- Integration tests SHALL verify rule execution

#### 7.4 Schema-Driven Validation (REQ-4)

**Principle**: Validate all LinkML instances against NWB-LinkML schema with SHACL shapes.

**Requirements**:
- Validate LinkML instances (YAML/JSON) against NWB-LinkML schema
- Generate RDF using reference from NWB-LinkML for consistent IRIs
- Run SHACL validation using shapes generated from NWB-LinkML
- Produce detailed validation reports with issue localization
- Provide remediation suggestions for validation failures

**Verification**:
- Unit tests SHALL verify validation accuracy
- Integration tests SHALL verify SHACL shape generation
- E2E tests SHALL verify end-to-end validation

#### 7.5 RDF Generation (REQ-5)

**Principle**: Produce RDF in multiple formats with schema-derived contexts.

**Requirements**:
- **JSON-LD**: With schema-derived @context for interoperability
- **Turtle (TTL)**: Human-readable RDF format
- **RDF/XML**: For tool compatibility
- **SPARQL Endpoints**: Expose knowledge graphs via standard protocols
- **Programmatic APIs**: For accessing knowledge graph data
- **Round-Trip Conversion**: Verify data integrity through conversion cycles

**Verification**:
- Unit tests SHALL verify RDF generation for all formats
- Integration tests SHALL verify round-trip conversion
- Contract tests SHALL verify SPARQL endpoint compliance

#### 7.6 Core Ontology Integration (REQ-6)

**Principle**: Integrate core neuroscience ontologies with semantic bridging.

**Requirements**:
- **NIFSTD**: Neuroscience Information Framework ontology
- **UBERON**: Anatomy ontology for anatomical structures
- **CHEBI**: Chemical entities for drugs and compounds
- **NCBITaxon**: Species taxonomy for organism identification
- Basic concept mapping between ontologies
- Semantic bridging across ontologies
- OWL equivalence and subsumption relationships
- Confidence scoring for mappings

**Verification**:
- Unit tests SHALL verify ontology integration
- Integration tests SHALL verify concept mapping accuracy
- E2E tests SHALL verify cross-ontology queries

#### 7.7 MCP Server Integration (REQ-7)

**Principle**: Provide clean APIs for knowledge graph services through MCP.

**Requirements**:
- Clean APIs for metadata enrichment
- Clean APIs for validation services
- Schema/shape validation APIs
- Expose functionality through appropriate MCP tools
- Handle concurrent access with consistency
- Return structured responses compatible with agents and MCP server

**Verification**:
- Contract tests SHALL verify MCP interface
- Integration tests SHALL verify concurrent access handling
- Performance tests SHALL verify response times

#### 7.8 Schema & Artifact Management (REQ-8)

**Principle**: Manage NWB-LinkML schema versions and regenerate artifacts on updates.

**Requirements**:
- When updating NWB-LinkML schema:
  - Regenerate JSON-LD contexts
  - Regenerate SHACL shapes
  - Regenerate RDF/OWL artifacts
  - Store with version metadata
- Pin schema version used in each conversion
- Record schema version in PROV-O provenance for downstream triples
- Maintain compatibility matrix across schema versions

**Verification**:
- CI SHALL verify artifact generation on schema updates
- Version pinning SHALL be enforced
- Provenance SHALL include schema versions

#### 7.9 Dynamic Content Handling (REQ-9)

**Principle**: Handle unknown NWB data structures gracefully with adaptive RDF generation.

**Requirements**:
- Automatically discover basic entity types and properties
- Runtime schema analysis including neurodata_type detection
- Structural pattern recognition for unknown structures
- Create adaptive RDF representations preserving data types
- Maintain basic semantic relationships even for unknown types
- Provide warnings for unknown structures with suggestions

**Verification**:
- Unit tests SHALL verify handling of unknown structures
- Integration tests SHALL verify adaptive RDF generation
- E2E tests SHALL verify complete unknown data handling

---

### Module 8: Test Verbosity Optimization

**Module Purpose**: Optimize testing performance without compromising quality.

#### 8.1 Test Output Management (REQ-1)

**Principle**: Provide configurable test output verbosity for different scenarios.

**Requirements**:
- Configurable verbosity levels (minimal, normal, verbose, debug)
- Context-aware output (more detail on failures)
- Structured output for CI/CD parsing
- Performance impact minimization of logging
- Real-time progress indicators for long tests
- Summary statistics at test completion

**Verification**:
- Unit tests SHALL verify verbosity configuration
- Performance tests SHALL verify minimal overhead
- CI SHALL use appropriate verbosity levels

#### 8.2 Test Parallelization (REQ-2)

**Principle**: Execute tests in parallel while maintaining isolation and correctness.

**Requirements**:
- Parallel execution with pytest-xdist
- Proper test isolation (no shared state)
- Resource management (file handles, network connections)
- Deterministic test ordering when needed
- Failure isolation (one test failure doesn't affect others)
- Load balancing across workers

**Verification**:
- Parallel tests SHALL produce same results as sequential
- Performance tests SHALL verify speedup with parallelization
- Integration tests SHALL verify proper isolation

#### 8.3 Test Selection & Filtering (REQ-3)

**Principle**: Intelligently select tests based on changes to minimize execution time.

**Requirements**:
- Change-based test selection (run tests affected by code changes)
- Marker-based filtering (run specific test categories)
- Failed test re-execution (prioritize recently failed tests)
- Test dependency tracking (run dependent tests when base changes)
- Configurable test suites for different scenarios (smoke, regression, full)

**Verification**:
- Test selection SHALL identify affected tests accurately
- Performance SHALL improve with intelligent selection
- CI SHALL use test selection for fast feedback

#### 8.4 Performance Optimization (REQ-4)

**Principle**: Optimize test execution performance without compromising coverage.

**Requirements**:
- Fixture caching and reuse
- Database fixture optimization (in-memory when possible)
- Network mock optimization (avoid real network calls in unit tests)
- File I/O optimization (in-memory file systems for unit tests)
- Lazy loading of test data
- Profile-guided optimization (identify and optimize slow tests)

**Verification**:
- Performance tests SHALL track test execution time trends
- Slow tests SHALL be identified and optimized
- Regression tests SHALL prevent performance degradation

---

### Module 9: Testing & Quality Assurance

**Module Purpose**: Comprehensive testing strategies and quality assurance infrastructure.

#### 9.1 MCP Server Testing Infrastructure (REQ-1-REQ-6)

**9.1.1 Endpoint Testing (REQ-1)**

**Principle**: Test all HTTP endpoints comprehensively with ≥90% coverage.

**Requirements**:
- Successful requests with valid data (happy paths)
- Malformed request handling (invalid JSON, missing fields, wrong types)
- Authentication/authorization scenarios (valid/invalid tokens, expired tokens, insufficient permissions)
- Rate limiting behavior (verify limits enforced)
- Request size limits (verify large request handling)
- Timeout handling (verify timeout behavior)
- Concurrent request processing (verify thread safety)
- Idempotency verification for applicable endpoints (POST vs PUT)
- At least 90% code coverage for endpoint handlers

**Verification**:
- Contract tests SHALL verify all endpoints
- Coverage reports SHALL show ≥90% endpoint coverage
- Performance tests SHALL verify concurrent handling

**9.1.2 Agent Coordination Testing (REQ-2)**

**Principle**: Verify proper agent orchestration with ≥20 workflow scenarios.

**Requirements**:
- Sequential workflow execution (verify ordering)
- Parallel agent invocation (verify concurrency)
- Dependency management between agents (verify coordination)
- State persistence across agent calls (verify context maintenance)
- Error propagation from agents to server (verify error handling)
- Retry logic with exponential backoff (verify retry behavior)
- Circuit breaker activation (verify protection from cascading failures)
- Graceful degradation when agents unavailable (verify fallback behavior)
- Test at least 20 different workflow scenarios covering common and edge cases

**Verification**:
- Integration tests SHALL cover all 20+ scenarios
- Chaos tests SHALL verify error handling
- Performance tests SHALL verify orchestration efficiency

**9.1.3 Contract Testing (REQ-3)**

**Principle**: Validate 100% OpenAPI specification conformance.

**Requirements**:
- Automated contract testing framework
- Response schema validation (verify all responses match schemas)
- Required field verification (verify all required fields present)
- Data type checking (verify correct types)
- Enum value validation (verify values in allowed sets)
- Format string compliance (dates, UUIDs, etc. match formats)
- Pagination consistency (verify pagination links correct)
- HATEOAS link validity (verify all links functional)
- Versioning header correctness (verify API version headers)
- 100% OpenAPI specification coverage

**Verification**:
- Contract test suite SHALL have 100% spec coverage
- CI SHALL fail on specification violations
- Documentation SHALL match implementation

**9.1.4 Error Condition Testing (REQ-4)**

**Principle**: Verify comprehensive error handling with specific codes and messages.

**Requirements**:
- Agent failures: timeout, crash, invalid response
- Network issues: connection loss, slow networks, intermittent failures
- Resource exhaustion: memory, disk, file handles, connections
- Concurrent modification conflicts (optimistic locking)
- Database connection failures (connection pool exhaustion)
- External service unavailability (third-party API failures)
- Malformed data from agents (invalid JSON, schema violations)
- Cascade failures (multiple failures in sequence)
- Specific error codes and messages for each scenario
- Recovery strategies for each error type

**Verification**:
- Chaos tests SHALL inject all error types
- Error handling SHALL provide recovery guidance
- Monitoring SHALL track error rates by type

**9.1.5 State Management Testing (REQ-5)**

**Principle**: Validate state persistence and ACID properties.

**Requirements**:
- Workflow state persistence (verify state saved correctly)
- Transaction consistency (verify atomic operations)
- Rollback capabilities (verify rollback on errors)
- State recovery after crashes (verify recovery mechanisms)
- Cleanup of orphaned resources (verify garbage collection)
- Garbage collection of old states (verify retention policies)
- State migration during upgrades (verify version compatibility)
- Distributed state coordination (verify consistency in distributed setup)
- ACID properties where applicable (Atomicity, Consistency, Isolation, Durability)

**Verification**:
- Integration tests SHALL verify state management
- Chaos tests SHALL verify recovery from crashes
- Performance tests SHALL verify state operation efficiency

**9.1.6 Security Testing (REQ-6)**

**Principle**: Follow OWASP testing guidelines for all security aspects.

**Requirements**:
- Input sanitization verification (SQL injection, XSS, etc.)
- SQL injection prevention (parameterized queries only)
- Path traversal protection (validate file paths)
- XXE attack prevention (disable external entities)
- CSRF token validation (verify token presence and validity)
- Rate limiting effectiveness (verify limits prevent abuse)
- Authentication timeout (verify session expiration)
- Session management (verify secure session handling)
- Audit logging completeness (verify all security events logged)
- Follow OWASP testing guidelines for all aspects

**Verification**:
- Security tests SHALL cover all OWASP Top 10
- Penetration testing SHALL be performed regularly
- Security scanning SHALL be automated in CI

#### 9.2 Individual Agent Testing (REQ-7-REQ-12)

**9.2.1 Logic Testing (REQ-7)**

**Principle**: Test core functionality comprehensively with ≥50 test cases per agent.

**Requirements**:
- Input validation (verify all validation rules)
- Data transformation accuracy with property-based testing (Hypothesis)
- Decision-making algorithms with scenario coverage (all paths tested)
- Error handling paths with forced error injection
- Edge case handling with boundary value analysis
- Performance characteristics with benchmark tests
- Memory usage patterns with leak detection
- Configuration validation with invalid configs
- At least 50 test cases per complex agent

**Verification**:
- Unit tests SHALL achieve ≥90% coverage
- Property-based tests SHALL find edge cases
- Performance tests SHALL establish baselines

**9.2.2 Interface Testing (REQ-8)**

**Principle**: Verify agents conform to contracts with schema validation.

**Requirements**:
- Schema validation tests (verify responses match schemas)
- Type checking with runtime verification (pydantic)
- Required field presence checks (verify all required fields)
- Optional field handling tests (verify proper handling)
- Null/undefined handling (verify null safety)
- Encoding/decoding tests (UTF-8, base64, etc.)
- Large payload handling (>10MB payloads)
- Streaming data support tests (chunked data)
- Contract tests for all agent methods

**Verification**:
- Contract tests SHALL verify all methods
- Integration tests SHALL verify MCP interaction
- E2E tests SHALL verify complete workflows

**9.2.3 Mock Data Testing (REQ-9)**

**Principle**: Support testing without external dependencies with 100+ mock scenarios.

**Requirements**:
- Mock LLM services with deterministic responses
- Fake file systems with in-memory operations (memfs)
- Simulated network conditions (latency, drops, errors)
- Time manipulation for temporal testing (freezegun)
- Mock external APIs with various response patterns
- Stub data sources with controlled data
- Fake credentials and secrets (no real credentials)
- Deterministic random number generation (seeded RNG)
- Cover 100+ mock scenarios for comprehensive testing

**Verification**:
- Unit tests SHALL use mock services exclusively
- Mock scenarios SHALL cover all agent operations
- Integration tests SHALL verify realistic behavior

**9.2.4 Error Handling Testing (REQ-10)**

**Principle**: Verify agents handle all error types with ≥5 test cases per type.

**Requirements**:
- Malformed inputs: missing fields, wrong types, invalid formats
- Service failures: LLM timeout, API errors, network issues
- Resource constraints: memory limits, disk space, CPU throttling
- Concurrent access issues (race conditions, deadlocks)
- Partial failures in multi-step operations (atomicity)
- Rollback scenarios (verify rollback correctness)
- Cleanup after failures (verify resource cleanup)
- Error reporting accuracy (verify error messages)
- At least 5 test cases per error type

**Verification**:
- Error injection tests SHALL cover all error types
- Recovery tests SHALL verify recovery mechanisms
- Error messages SHALL be actionable

**9.2.5 State Machine Testing (REQ-11)**

**Principle**: Validate state transitions with full state diagram coverage.

**Requirements**:
- State transitions (verify all valid transitions)
- Illegal state prevention (verify invalid transitions blocked)
- State persistence (verify state saved correctly)
- Concurrent state modifications (verify thread safety)
- State recovery after restart (verify recovery mechanisms)
- Timeout handling in each state (verify timeout behavior)
- Event ordering requirements (verify event handling order)
- Side effects of state changes (verify expected side effects)
- Full state diagram coverage (all states and transitions tested)

**Verification**:
- State tests SHALL cover all states and transitions
- Property-based tests SHALL find invalid sequences
- Integration tests SHALL verify state persistence

**9.2.6 Performance Testing (REQ-12)**

**Principle**: Measure and optimize agent performance with regression detection.

**Requirements**:
- Response times under various loads (baseline establishment)
- Throughput for batch operations (items/sec)
- Resource usage patterns (CPU, memory, I/O)
- Scalability limits (maximum throughput)
- Degradation under stress (graceful degradation)
- Recovery after load spikes (verify recovery time)
- Cache effectiveness (hit rates, eviction rates)
- Optimization opportunities (identify bottlenecks)
- Performance regression detection (alert on >10% degradation)

**Verification**:
- Benchmarks SHALL establish baselines
- Performance tests SHALL run in CI
- Regression alerts SHALL trigger on degradation

#### 9.3 End-to-End Testing (REQ-13-REQ-18)

**9.3.1 DataLad-Managed Test Datasets (REQ-13)**

**Principle**: Use DataLad-managed datasets covering diverse neuroscience data formats.

**Requirements**:
- Open Ephys recordings (multi-channel, multi-session)
- SpikeGLX datasets with different probe configurations
- Neuralynx data with video synchronization
- Calcium imaging data (Suite2p, CaImAn processed)
- Behavioral tracking data (DeepLabCut, SLEAP)
- Multimodal recordings (ephys + imaging + behavior)
- Datasets with missing/corrupted segments (robustness testing)
- Legacy format migrations (backward compatibility)
- Version control for reproducibility (DataLad)

**Verification**:
- Datasets SHALL be available in CI
- Datasets SHALL cover all supported formats
- Datasets SHALL be properly versioned

**9.3.2 Format Coverage (REQ-14)**

**Principle**: Include test datasets representing ≥15 distinct format combinations.

**Requirements**:
- Binary formats (DAT, BIN, proprietary formats)
- HDF5-based formats (with various schemas)
- Text-based formats (CSV, TSV, JSON, YAML)
- Video formats (AVI, MP4, MOV, H264)
- Image stacks (TIFF sequences, PNG sequences)
- Time series data (continuous, event-based)
- Metadata formats (JSON, XML, YAML, custom)
- Mixed format datasets (multiple formats in one dataset)
- Cover at least 15 distinct format combinations

**Verification**:
- E2E tests SHALL use all 15+ format combinations
- Format detection SHALL correctly identify all formats
- Conversions SHALL succeed for all formats

**9.3.3 Quality Validation (REQ-15)**

**Principle**: Verify test conversions meet strict quality criteria with automated scoring.

**Requirements**:
- Valid NWB files passing NWB Inspector with zero critical issues
- PyNWB schema compliance with all required fields
- Data integrity with checksum verification (SHA256)
- Temporal alignment across data streams (<1ms drift tolerance)
- Spatial registration accuracy for imaging data (subpixel accuracy)
- Signal fidelity with SNR preservation (within 5%)
- Metadata completeness (>95% fields populated)
- Proper unit conversions (verify correctness)
- Automated quality scoring (objective metrics)

**Verification**:
- E2E tests SHALL verify all quality criteria
- Quality scores SHALL meet thresholds
- Failed conversions SHALL be investigated

**9.3.4 Complete Pipeline Testing (REQ-16)**

**Principle**: Verify full workflow including dataset discovery through report generation for workflows up to 1TB.

**Requirements**:
- Dataset discovery and format detection
- Metadata extraction and inference
- User interaction simulation for missing metadata
- Conversion script generation and validation
- Parallel processing for large datasets
- Progress reporting and cancellation support
- Error recovery and partial completion
- Final evaluation with comprehensive report generation
- Test workflows up to 1TB in size

**Verification**:
- E2E tests SHALL cover complete pipeline
- Large dataset tests SHALL verify scalability
- Pipeline tests SHALL verify all stages

**9.3.5 Scientific Validity (REQ-17)**

**Principle**: Verify conversions preserve scientific validity with domain expert criteria.

**Requirements**:
- Spike sorting results preservation (cluster IDs, timestamps)
- Behavioral event alignment (event timing accuracy <1ms)
- Stimulus timing accuracy (within hardware precision)
- Trial structure maintenance (all trials present, correct order)
- Experimental metadata fidelity (all metadata preserved)
- Derived data linkage (links to source data intact)
- Provenance chain completeness (full audit trail)
- Reproducibility of analysis (same analysis produces same results)
- Domain expert validation criteria (neuroscience experts review)

**Verification**:
- Scientific validity tests SHALL verify preservation
- Domain experts SHALL review test results
- Analysis reproducibility SHALL be verified

**9.3.6 Performance Benchmarking (REQ-18)**

**Principle**: Establish performance baselines for all operations.

**Requirements**:
- Conversion speed (MB/sec by format) benchmarks
- Memory usage patterns (peak and average) tracking
- Disk I/O patterns (read/write ratios) analysis
- CPU utilization (single vs multi-core) profiling
- Network usage for remote datasets measurement
- Cache effectiveness evaluation
- Parallel scaling efficiency assessment
- Bottleneck identification (CPU, I/O, memory, network)
- Establish performance baselines for regression detection

**Verification**:
- Benchmarks SHALL run in CI (nightly)
- Baselines SHALL be established and tracked
- Regressions SHALL trigger alerts

#### 9.4 Client Library Testing (REQ-19-REQ-24)

**9.4.1 API Method Testing (REQ-19)**

**Principle**: Test all client library methods comprehensively with ≥85% coverage.

**Requirements**:
- Test all API methods with valid inputs (happy paths)
- Test error cases for each method (invalid inputs, timeouts, errors)
- Test edge cases (boundary values, empty inputs, large inputs)
- Test async and sync versions where both provided
- Test retry logic and exponential backoff
- Test timeout handling and cancellation
- Achieve ≥85% code coverage for client libraries

**Verification**:
- Unit tests SHALL cover all API methods
- Integration tests SHALL verify server interaction
- Coverage reports SHALL show ≥85% coverage

**9.4.2 Connection Management Testing (REQ-20)**

**Principle**: Verify robust connection management with automatic recovery.

**Requirements**:
- Connection establishment (verify initial connection)
- Connection pooling (verify pool management)
- Keepalive mechanisms (verify connection maintenance)
- Automatic reconnection on disconnect (verify recovery)
- Connection timeout handling (verify timeout behavior)
- TLS/SSL verification (verify secure connections)
- Connection failure scenarios (network loss, server restart)

**Verification**:
- Integration tests SHALL verify connection management
- Chaos tests SHALL verify recovery mechanisms
- Security tests SHALL verify TLS handling

**9.4.3 Error Handling Resilience (REQ-21)**

**Principle**: Verify comprehensive error handling with graceful degradation.

**Requirements**:
- Network errors with retry logic (exponential backoff)
- Timeout errors with configurable policies
- Authentication errors with token refresh
- Server errors with fallback strategies
- Data errors with remediation guidance
- Circuit breaker functionality (prevent cascading failures)
- Fallback mechanisms when primary strategy fails

**Verification**:
- Error injection tests SHALL cover all error types
- Recovery tests SHALL verify mechanisms
- Circuit breaker tests SHALL verify protection

**9.4.4 Authentication Testing (REQ-22)**

**Principle**: Test all authentication methods with token management.

**Requirements**:
- Token-based authentication (JWT, OAuth2)
- API key authentication
- Certificate-based authentication (mTLS)
- Token refresh mechanisms (automatic refresh)
- Token expiration handling (re-authentication)
- Multi-factor authentication support
- Session management (session creation, renewal, termination)

**Verification**:
- Auth tests SHALL cover all methods
- Integration tests SHALL verify token refresh
- Security tests SHALL verify token security

**9.4.5 Integration Example Testing (REQ-23)**

**Principle**: Verify all integration examples work as documented.

**Requirements**:
- Jupyter notebook examples (execute in CI)
- Workflow system examples (Airflow, Prefect, etc.)
- Cloud platform examples (AWS, GCP, Azure)
- CI/CD pipeline examples (GitHub Actions, GitLab CI)
- All examples execute successfully
- All examples produce expected outputs
- Documentation matches implementation

**Verification**:
- CI SHALL execute all integration examples
- Examples SHALL produce expected outputs
- Documentation SHALL be up to date

**9.4.6 Cross-Platform Testing (REQ-24)**

**Principle**: Verify client libraries work across platforms and Python versions.

**Requirements**:
- Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
- Operating systems: Ubuntu 20.04+, macOS 11+, Windows 10+
- Architecture: x86_64, ARM64 (M1/M2)
- Test on all combinations in CI matrix
- Handle platform-specific differences gracefully

**Verification**:
- CI matrix SHALL cover all combinations
- Platform-specific tests SHALL verify differences
- Documentation SHALL note platform requirements

---

### Module 10: Validation & Quality Assurance

**Module Purpose**: Comprehensive, modular validation and quality assurance system for NWB file conversions with 8 core sub-modules.

#### 10.1 Core Validation Framework (Sub-Module 1)

**Principle**: Provide base infrastructure for all validation operations.

**10.1.1 Base Validator Implementation (REQ-1)**

**Requirements**:
- Implement `BaseValidator` abstract class with standardized interface
- All validators inherit from BaseValidator
- Common validation lifecycle: initialize, validate, report
- Plugin architecture for extensibility

**Verification**:
- Unit tests SHALL verify BaseValidator interface
- All validators SHALL inherit from BaseValidator
- Plugin system SHALL support third-party validators

**10.1.2 Validation Result Structures (REQ-2)**

**Requirements**:
- Provide `ValidationResult` dataclass with structured output
- Provide `ValidationIssue` dataclass for individual issues
- Standardized severity levels: CRITICAL, ERROR, WARNING, INFO
- Structured metadata for each issue (location, remediation, evidence)

**Verification**:
- All validators SHALL use standard result structures
- Result serialization SHALL be consistent
- Documentation SHALL explain result structure

**10.1.3 Configuration Management (REQ-3)**

**Requirements**:
- Implement `ValidationConfig` class with profile-based settings
- Runtime configuration updates without restart
- Configuration validation at load time
- Support for environment-specific configs (dev, staging, prod)
- Comprehensive error handling and logging with structured formats

**Verification**:
- Config tests SHALL verify all settings
- Runtime update tests SHALL verify hot reload
- Profile tests SHALL verify environment handling

#### 10.2 NWB Inspector Integration (Sub-Module 2)

**Principle**: Integrate NWB Inspector for schema compliance checking.

**10.2.1 Inspector Integration (REQ-4)**

**Requirements**:
- Integrate NWB Inspector for schema compliance checking
- Execute with configurable parameters (timeout, verbosity)
- Parse and structure output for downstream consumption
- Handle inspector version compatibility

**Verification**:
- Unit tests SHALL verify inspector integration
- Integration tests SHALL verify output parsing
- Version tests SHALL verify compatibility

**10.2.2 Issue Categorization (REQ-5)**

**Requirements**:
- Categorize validation issues by severity
- **Severity Levels**: critical, warning, info, best_practice
- Map inspector output to standardized severity levels
- Provide severity-based filtering and reporting

**Verification**:
- Categorization tests SHALL verify mapping
- Filtering tests SHALL verify severity filtering
- Reports SHALL group by severity

**10.2.3 Schema Validation (REQ-6)**

**Requirements**:
- Validate against current NWB schema versions (2.x, 3.x)
- Required field checks (all required fields present)
- Optional field checks (optional fields valid if present)
- FAIR principles compliance checking
- Provide improvement suggestions for FAIR compliance

**Verification**:
- Schema tests SHALL verify all schema versions
- FAIR tests SHALL verify compliance checking
- Suggestion tests SHALL verify recommendations

#### 10.3 LinkML Schema Validation (Sub-Module 3)

**Principle**: Validate metadata against LinkML schemas.

**10.3.1 Schema Loading (REQ-7)**

**Requirements**:
- Load and parse LinkML schema definitions
- Generate Pydantic validation classes from schemas
- Cache generated classes for performance
- Support schema versioning and migrations

**Verification**:
- Schema loading tests SHALL verify all schemas
- Generation tests SHALL verify Pydantic classes
- Cache tests SHALL verify performance improvement

**10.3.2 Runtime Validation (REQ-8)**

**Requirements**:
- Validate metadata against loaded schemas in real-time
- Detailed field-level errors with location information
- Controlled vocabulary validation with completion suggestions
- Type checking and format validation
- Partial validation support for incomplete metadata

**Verification**:
- Validation tests SHALL verify all field types
- Error tests SHALL verify detailed error messages
- Performance tests SHALL verify real-time capability

**10.3.3 Nested Object Handling (REQ-9)**

**Requirements**:
- Handle nested object validation recursively
- Cross-reference validation (verify references valid)
- Circular reference detection and handling
- Deep validation with path tracking

**Verification**:
- Nesting tests SHALL verify recursive validation
- Reference tests SHALL verify cross-reference checking
- Circular reference tests SHALL verify detection

#### 10.4 Quality Assessment Engine (Sub-Module 4)

**Principle**: Implement multi-dimensional quality metrics.

**10.4.1 Quality Metrics (REQ-10)**

**Requirements**:
- Implement quality metrics for:
  - **Completeness**: Required and optional field population
  - **Consistency**: Cross-field validation, temporal/spatial coherence
  - **Accuracy**: Scientific plausibility, unit correctness, numerical precision
  - **Compliance**: NWB schema, FAIR principles, DANDI requirements

**Verification**:
- Metric tests SHALL verify all quality dimensions
- Integration tests SHALL verify metric combination
- Documentation SHALL explain metric calculations

**10.4.2 Scoring Algorithms (REQ-11)**

**Requirements**:
- Provide weighted scoring algorithms with confidence intervals
- Configurable weights per quality dimension
- Aggregate scores with statistical confidence
- Analyze required and optional field completeness
- Prioritized recommendations for improvement
- Trend analysis across multiple conversions

**Verification**:
- Scoring tests SHALL verify algorithms
- Weight tests SHALL verify configurability
- Confidence tests SHALL verify intervals

#### 10.5 Domain Knowledge Validator (Sub-Module 5)

**Principle**: Validate scientific plausibility and domain constraints.

**10.5.1 Parameter Range Validation (REQ-12)**

**Requirements**:
- Validate experimental parameter ranges against known scientific bounds
- **Examples**: sampling rates (reasonable ranges), electrode counts (valid ranges), stimulus parameters (plausible values)
- Provide domain-specific guidance for questionable values

**Verification**:
- Range tests SHALL verify all parameter types
- Plausibility tests SHALL detect implausible values
- Guidance tests SHALL verify recommendations

**10.5.2 Consistency Validation (REQ-13)**

**Requirements**:
- Check biological plausibility of measurements
- Verify equipment and methodology consistency
- Cross-validate related parameters
- Implement experiment-specific validation rules:
  - **Electrophysiology**: spike waveforms, LFP bands, electrode impedances
  - **Behavioral**: trial structure, event timing, reward parameters
  - **Imaging**: frame rates, pixel sizes, fluorescence ranges

**Verification**:
- Plausibility tests SHALL detect implausible measurements
- Consistency tests SHALL verify related parameters
- Experiment-specific tests SHALL verify domain rules

#### 10.6 Validation Orchestrator (Sub-Module 6)

**Principle**: Coordinate execution of multiple validation engines.

**10.6.1 Orchestration (REQ-14)**

**Requirements**:
- Coordinate execution of multiple validation engines
- Support parallel/sequential workflow execution
- Validation dependency management (order constraints)
- Progress tracking and reporting
- Cancellation support for long-running validations

**Verification**:
- Orchestration tests SHALL verify coordination
- Parallel tests SHALL verify concurrent execution
- Dependency tests SHALL verify ordering

**10.6.2 Result Aggregation (REQ-15)**

**Requirements**:
- Aggregate results from multiple validators
- Conflict resolution between validators (voting, confidence-based)
- Prioritize and rank issues by severity and impact
- Deduplication of similar issues
- Generate unified validation report

**Verification**:
- Aggregation tests SHALL verify result combination
- Conflict tests SHALL verify resolution
- Prioritization tests SHALL verify ranking

#### 10.7 Reporting and Analytics (Sub-Module 7)

**Principle**: Generate comprehensive validation reports and analytics.

**10.7.1 Report Generation (REQ-16)**

**Requirements**:
- Generate detailed validation reports in multiple formats:
  - **JSON**: Machine-readable, structured
  - **HTML**: Human-readable with visualizations
  - **PDF**: Printable, shareable
- Provide executive summaries with visualizations
- Custom templates with variable substitution
- Consistent formatting across report types

**Verification**:
- Report tests SHALL verify all formats
- Template tests SHALL verify customization
- Visualization tests SHALL verify charts

**10.7.2 Analytics (REQ-17)**

**Requirements**:
- Track validation metrics over time for trend analysis
- Identify patterns in validation issues
- Quality improvement recommendations based on trends
- Historical comparison across conversions
- Predictive analytics for common issues

**Verification**:
- Analytics tests SHALL verify metric tracking
- Trend tests SHALL verify pattern detection
- Recommendation tests SHALL verify suggestions

#### 10.8 MCP Integration Layer (Sub-Module 8)

**Principle**: Expose validation functionality through MCP protocol.

**10.8.1 MCP Tools (REQ-18)**

**Requirements**:
- Provide MCP tools for all major validation functions
- Standardized tool interface following MCP specification
- Input validation for all tools
- Structured responses compatible with MCP server

**Verification**:
- Contract tests SHALL verify MCP tool interface
- Integration tests SHALL verify tool functionality
- Documentation SHALL cover all tools

**10.8.2 Asynchronous Operations (REQ-19)**

**Requirements**:
- Support asynchronous validation operations
- Progress reporting via callbacks or events
- Cancellation support for long-running operations
- Integrate with MCP server infrastructure
- Health checks (<1 second response time)
- Standardized input/output formats

**Verification**:
- Async tests SHALL verify operation handling
- Progress tests SHALL verify reporting
- Cancellation tests SHALL verify cleanup

---

## CROSS-MODULE INTEGRATION RULES

These rules govern how modules interact and integrate with each other to form a cohesive system.

### Integration Rule 1: MCP Server as Mediator (NON-NEGOTIABLE)

**Rule**: ALL inter-module communication MUST flow through the MCP server. Direct module-to-module communication is PROHIBITED.

**Requirements**:
- Modules expose functionality through MCP tools ONLY
- Modules make requests to other modules through MCP server
- MCP server maintains routing table for all module services
- MCP server handles request/response transformation between modules
- MCP server enforces authentication/authorization for cross-module requests

**Rationale**: Centralizing communication through MCP server provides observability, enables policy enforcement, simplifies debugging, and allows for future architectural evolution without changing module interfaces.

**Verification**:
- Dependency analysis SHALL detect direct module-to-module imports
- Architecture tests SHALL verify all communication flows through MCP
- Network monitoring SHALL show no direct module-to-module traffic

### Integration Rule 2: Contract-Based Interfaces (NON-NEGOTIABLE)

**Rule**: All module interfaces MUST be defined by versioned contracts (OpenAPI, AsyncAPI, Protobuf).

**Requirements**:
- Contracts defined BEFORE implementation
- Contracts version with semantic versioning
- Breaking changes require MAJOR version bump
- Backward compatibility maintained for MINOR/PATCH
- Contract tests verify conformance
- Contracts published to central registry

**Rationale**: Contract-based interfaces enable independent module development, provide clear expectations, enable automated testing, and facilitate API evolution without breaking clients.

**Verification**:
- Contract tests SHALL verify all module interfaces
- Version tests SHALL verify semantic versioning
- Registry SHALL contain all current contracts

### Integration Rule 3: DataLad for Data Exchange

**Rule**: When modules exchange data files, they MUST use DataLad repositories for versioning and provenance.

**Requirements**:
- Data files >10MB exchanged via DataLad repositories
- Each data exchange creates or updates DataLad repository
- Complete provenance recorded for all data transfers
- Data integrity verified with checksums
- Version pinning for reproducibility

**Rationale**: DataLad provides version control, integrity verification, and provenance tracking for data files, ensuring reproducibility and traceability across module boundaries.

**Verification**:
- Data transfer tests SHALL use DataLad
- Provenance SHALL be complete for all transfers
- Integrity SHALL be verified for all transfers

### Integration Rule 4: Unified Observability

**Rule**: All modules MUST participate in unified observability with correlation ID propagation.

**Requirements**:
- Structured logging in JSON format (all modules)
- Correlation IDs propagated across module boundaries
- Distributed tracing with OpenTelemetry (all modules)
- Performance metrics reported to central system
- Health checks expose dependency status
- Error tracking with full context

**Rationale**: Unified observability enables end-to-end request tracing, performance analysis, debugging across modules, and operational monitoring.

**Verification**:
- Log aggregation SHALL collect logs from all modules
- Traces SHALL span all modules in request path
- Monitoring dashboards SHALL show all modules

### Integration Rule 5: Consistent Error Handling

**Rule**: All modules MUST use consistent error codes, formats, and recovery strategies.

**Requirements**:
- Standardized error code taxonomy (e.g., AUTH_001, VALIDATION_042)
- Consistent error response format (status, code, message, details)
- Actionable error messages with remediation steps
- Graceful degradation when dependent modules fail
- Circuit breakers to prevent cascading failures
- Retry logic with exponential backoff for transient errors

**Rationale**: Consistent error handling enables automated error recovery, simplifies client implementation, improves user experience, and prevents cascading failures.

**Verification**:
- Error tests SHALL verify format consistency
- Integration tests SHALL verify cross-module error propagation
- Recovery tests SHALL verify graceful degradation

### Integration Rule 6: Schema Compatibility

**Rule**: All modules MUST use compatible schema versions with backward compatibility guarantees.

**Requirements**:
- Schema versions pinned and recorded in provenance
- Schema registry maintains compatibility matrix
- Backward compatibility maintained for MINOR/PATCH schema changes
- Breaking schema changes coordinated across modules
- Schema migration tools provided for version upgrades

**Rationale**: Schema compatibility ensures modules can evolve independently while maintaining interoperability, prevents breaking changes from cascading, and enables gradual migration to new schema versions.

**Verification**:
- Compatibility tests SHALL verify schema interoperability
- Registry SHALL enforce compatibility rules
- Migration tests SHALL verify version upgrades

### Integration Rule 7: Performance Budgets

**Rule**: Each module MUST meet performance budgets for operations affecting other modules.

**Requirements**:
- Response time budgets per operation (e.g., <200ms for standard endpoints)
- Throughput budgets per module (e.g., 100 requests/sec minimum)
- Resource usage budgets (CPU, memory, disk I/O)
- Performance testing in CI for all module boundaries
- Performance degradation alerts (<10% tolerance)

**Rationale**: Performance budgets prevent individual modules from degrading overall system performance, enable capacity planning, and ensure predictable user experience.

**Verification**:
- Performance tests SHALL verify budgets for all operations
- Monitoring SHALL track performance against budgets
- Alerts SHALL trigger on budget violations

### Integration Rule 8: Security Boundaries

**Rule**: Modules MUST treat each other as untrusted and validate all inter-module communication.

**Requirements**:
- Input validation at module boundaries (schema validation)
- Authentication required for all inter-module requests
- Authorization enforced based on least privilege principle
- Data sanitization at boundaries (prevent injection attacks)
- Audit logging of all cross-module operations
- Encryption for sensitive data in transit

**Rationale**: Security boundaries prevent compromised modules from affecting others, enforce defense in depth, enable security auditing, and comply with security best practices.

**Verification**:
- Security tests SHALL verify input validation
- Auth tests SHALL verify authentication enforcement
- Audit tests SHALL verify complete logging

### Integration Rule 9: Graceful Degradation

**Rule**: Modules MUST continue operating (with reduced functionality) when dependent modules are unavailable.

**Requirements**:
- Identify critical vs. optional dependencies
- Fallback strategies for optional dependencies
- Circuit breakers to prevent cascading failures
- Cached responses for frequently accessed data
- Degraded mode with reduced functionality clearly communicated
- Health checks distinguish between healthy, degraded, and failed states

**Rationale**: Graceful degradation improves system resilience, prevents total system failure, enables maintenance without downtime, and provides better user experience during partial outages.

**Verification**:
- Chaos tests SHALL verify degradation behavior
- Health checks SHALL expose degradation state
- Integration tests SHALL verify fallback strategies

### Integration Rule 10: Versioned Deployments

**Rule**: Modules MUST support independent deployment with version compatibility checks.

**Requirements**:
- Each module independently deployable
- Version compatibility matrix maintained and enforced
- Health checks verify compatible versions of dependencies
- Deployment order constraints documented
- Rollback plan for incompatible version deployments

**Rationale**: Independent deployment enables faster releases, reduces deployment risk, allows for gradual rollout, and supports continuous deployment practices.

**Verification**:
- Deployment tests SHALL verify independent deployment
- Compatibility tests SHALL verify version matrix
- Rollback tests SHALL verify recovery procedures

---

## GOVERNANCE

### Amendment Process

**Principle**: Constitution amendments follow a formal process ensuring stability while allowing evolution.

**Process**:
1. **Documented Proposal**: Written proposal with specific wording changes and clear rationale
2. **Impact Analysis**: Assessment of effects on all 10 modules, specifications, implementations, workflows
3. **Community Review**: 1 week for MINOR changes, 2 weeks for MAJOR changes, with stakeholder input
4. **Approval**: Consensus among maintainers or maintainer decision per project governance
5. **Migration Plan**: Concrete transition steps, timeline, communication plan for affected modules
6. **Version Increment**: Per semantic versioning policy (MAJOR/MINOR/PATCH)

**Applies To**: Amendments to any section of this constitution

### Versioning Policy

**Semantic Versioning (MAJOR.MINOR.PATCH)**:

**MAJOR**:
- Breaking changes to core principles affecting all modules
- Governance removal or fundamental redefinition
- Architectural changes requiring module rewrites
- Examples: Removing TDD requirement, changing from MCP-centric architecture

**MINOR**:
- New core principles added
- New technical standards sections
- Materially expanded guidance
- Additional non-breaking constraints
- Examples: Adding AI ethics principle, adding new security standards

**PATCH**:
- Clarifications of existing principles
- Wording improvements
- Typo fixes
- Non-semantic refinements
- Examples: Clarifying "DataLad Python API" meaning, fixing grammar

**Decision Tree**:
1. Does it break existing implementations in any module? → MAJOR
2. Does it add new requirements to any module? → MINOR
3. Does it only clarify or fix without adding requirements? → PATCH

### Compliance Verification

**All Pull Requests MUST Verify** (7-Point Checklist):

1. ✅ **TDD**: Tests committed before implementation (git history evidence)
2. ✅ **MCP Tools**: Functionality via MCP tools (no direct module-to-module communication)
3. ✅ **DataLad API**: Python API only (no CLI in production)
4. ✅ **Schema-First**: Data structures in schemas before code
5. ✅ **Modular**: Clear module boundaries, contracts verified
6. ✅ **Quality**: Multi-dimensional assessment implemented
7. ✅ **Observability**: Structured logging, metrics, tracing present

**PR Review Checklist**:
```markdown
## Constitutional Compliance
### Core Principles
- [ ] Tests written before implementation (TDD)
- [ ] Contract tests for new API endpoints (100% coverage)
- [ ] Schema definitions for new data structures
- [ ] MCP tool exposure (no direct agent/module access)
- [ ] DataLad Python API only (no CLI in production)
- [ ] Module boundaries clear and enforced
- [ ] Quality assessment implemented (multi-dimensional)
- [ ] Observability present (logging, metrics, tracing)

### Module-Specific
- [ ] Module-specific principles followed
- [ ] Module interface contracts updated
- [ ] Module dependencies documented

### Integration Rules
- [ ] MCP server mediation verified
- [ ] Contract-based interfaces used
- [ ] Observability integrated
- [ ] Error handling consistent

### General
- [ ] Documentation updated (user-facing changes)
- [ ] Performance impact assessed
- [ ] Security implications considered
- [ ] Breaking changes documented with migration guide
```

### Constitutional Authority

**Hierarchy** (highest to lowest):
1. **This Constitution** (supreme governing document for all 10 modules)
2. **Architecture Decision Records (ADRs)** (specific design decisions within constitutional bounds)
3. **Technical Specifications** (module-specific requirements)
4. **Implementation Guidelines** (best practices)
5. **Code Comments and Documentation** (implementation details)

**Conflict Resolution**: Constitutional principles take precedence over all other documentation. Conflicting documentation MUST be updated to align with constitutional requirements.

**Exception Process** (6 Requirements):
1. **Written Justification**: Why constitutional-compliant alternatives are insufficient, specific benefits, risks, mitigations
2. **Maintainer Approval**: Explicit approval from ≥1 project maintainer (documented in PR/ADR)
3. **ADR Documentation**: Create ADR documenting exception, rationale, alternatives, risks, mitigations, review
4. **Complexity Tracking**: Track in relevant specification's "Complexity Tracking" section, link to ADR
5. **Time-Bound**: Exceptions SHOULD have sunset dates, migration plan to constitutional compliance
6. **Regular Review**: All exceptions reviewed quarterly, assessed for continued necessity

**Enforcement**:
- **Code Reviews**: All PRs reviewed for compliance, violations block merge
- **Automated Linters**: Pre-commit hooks, CI/CD pipelines enforce rules
- **Architectural Fitness Functions**: Automated tests verify constraints
- **Violations**: Cannot merge until fixed or exception approved

---

**Version**: 5.0.0
**Ratified**: 2025-10-08
**Last Amended**: 2025-10-08
**Supersedes**: All prior constitution versions (1.0.0, 1.1.0, 2.0.0, 2.0.1, 3.0.0, 4.0.0)

**Source**: Comprehensive requirements from all 10 specification files (1,389 lines total) covering Agent Implementations, Client Libraries & Integrations, Core Project Organization, Data Management & Provenance, Evaluation & Reporting, Knowledge Graph Systems, MCP Server Architecture, Test Verbosity Optimization, Testing & Quality Assurance, and Validation & Quality Assurance.

**Format**: Modular constitution with project-wide core principles, shared technical standards, module-specific principles for all 10 modules, and cross-module integration rules.
