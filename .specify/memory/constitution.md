<!--
Sync Impact Report:
Version Change: 2.0.1 → 3.0.0 (MAJOR)
Regeneration Type: Complete rebuild from all 10 requirements.md files (1389 lines)
Source Files:
  - agent-implementations/requirements.md (161 lines)
  - client-libraries-integrations/requirements.md (105 lines)
  - core-project-organization/requirements.md (164 lines)
  - data-management-provenance/requirements.md (121 lines)
  - evaluation-reporting/requirements.md (67 lines)
  - knowledge-graph-systems/requirements.md (103 lines)
  - mcp-server-architecture/requirements.md (150 lines)
  - test-verbosity-optimization/requirements.md (duplicate)
  - testing-quality-assurance/requirements.md (151 lines)
  - validation-quality-assurance/requirements.md (246 lines)
Modified Principles:
  - Expanded all 8 principles with complete requirement details
  - Added detailed agent specifications (8 requirements per agent)
  - Added comprehensive MCP server architecture (8 requirements)
  - Added complete testing infrastructure (8 requirements)
  - Expanded validation system details (21 requirements across 8 modules)
  - Added knowledge graph requirements (9 requirements)
  - Added data management requirements (7 requirements)
  - Added evaluation/reporting requirements (6 requirements)
  - Added client library requirements (6 requirements)
Added Sections:
  - Detailed Agent Requirements per principle
  - MCP Server Orchestration Details
  - Knowledge Graph Integration Specifics
  - Complete Testing Strategy Requirements
  - All Technical Standard Details from requirements
Removed Sections:
  - Generic/compressed summaries
  - Placeholder content
Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md - Constitution Check aligns
  ✅ .specify/templates/spec-template.md - No changes needed
  ✅ .specify/templates/tasks-template.md - TDD ordering preserved
Follow-up TODOs: None - all requirements incorporated
-->

# Agentic Neurodata Conversion Constitution

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

All functionality MUST be exposed through standardized MCP (Model Context Protocol) tools. The MCP server serves as the single orchestration layer coordinating all specialized agents and managing the complete conversion workflow from dataset analysis to NWB file generation and evaluation.

**Architecture Requirements:**

- **Transport-Agnostic Core Service**: All business logic MUST reside in a transport-agnostic core service layer with zero dependencies on MCP, HTTP, or other transport protocols. The core contains domain entities and value objects, use case implementations, business rule enforcement, workflow orchestration logic, state management, persistence abstractions, and external service interfaces.

- **Thin Adapter Layers**: Each transport protocol (stdin/stdout, HTTP/REST, WebSocket, gRPC, GraphQL) MUST be implemented as a thin adapter layer (<500 lines of code, <5% of total codebase) that performs protocol-specific deserialization only, maps requests to service method calls, handles protocol-specific errors, manages connection lifecycle, implements protocol authentication, provides protocol metrics, and contains ZERO business logic.

- **Functional Parity**: All transport adapters MUST provide identical functionality. Contract tests SHALL verify all adapters invoke identical service methods, produce equivalent results for same inputs, handle errors consistently, maintain state coherence, support the same feature set, provide comparable performance, generate compatible audit logs, and preserve semantic equivalence across protocols.

- **Direct Agent Invocation Prohibited**: External clients MUST NOT invoke agents directly. All agent coordination MUST flow through the MCP server's core service layer.

**MCP Server Orchestration Capabilities:**

- **Multi-Agent Workflows**: Orchestrate conversation, conversion, evaluation, and metadata questioner agents in coordinated workflows with proper sequencing (analysis → metadata collection → conversion → validation), parallel execution where appropriate, dependency resolution between steps, state management across agent interactions, error propagation and handling, retry logic with exponential backoff, timeout management per agent and overall, and workflow cancellation with cleanup.

- **Format Detection**: Automatically detect 25+ neuroscience formats through file extension analysis with confidence scoring, magic byte detection for binary formats, header parsing for structured formats, directory structure pattern matching, metadata file detection and parsing, sampling-based content analysis, format version identification, and multi-format dataset recognition.

- **Interface Selection**: Map formats to NeuroConv interfaces using confidence-weighted matching, interface capability matrices, performance characteristics, resource requirements, quality scores from past conversions, user preference learning, cost optimization for cloud resources, and fallback interface chains with explainable selection logic.

- **Validation Coordination**: Coordinate with NWB Inspector (configurable rule sets), PyNWB validator (schema compliance), DANDI validator (repository readiness), custom validators via plugin system, format-specific validators for source fidelity, cross-validation between multiple tools, ensemble validation with voting, and progressive validation during conversion.

- **State Management**: Coordinate multi-step workflows with checkpoint recovery, maintain conversion context across agent interactions with versioning, track provenance information throughout the pipeline, persist intermediate results for debugging and audit, handle concurrent workflows with isolation, manage resource allocation across agents, implement transaction-like semantics for multi-agent operations, and provide state querying and manipulation APIs.

**Rationale**: Centralizing operations through MCP tools creates a unified API surface, simplifies client integration, enables horizontal scaling, and maintains clean separation between business logic and transport protocols. This hexagonal architecture ensures the system can evolve transport mechanisms without affecting core functionality, supporting evolutionary architecture with fitness functions and maintaining architectural integrity over time.

### II. Agent Specialization & Coordination

Each internal agent MUST handle a single domain of responsibility with no cross-domain operations except through MCP server coordination.

**Agent Specifications:**

**Conversation Agent Requirements (8 requirements):**
1. Analyze dataset contents and identify data formats, experimental context, and missing metadata fields
2. Generate natural language questions understandable to non-expert users for missing essential metadata
3. Validate user responses against domain knowledge and suggest corrections for inconsistencies
4. Provide structured summaries with clear provenance marking (user-provided vs. auto-detected)
5. Avoid repeated questions and only ask what cannot be inferred from data or domain knowledge
6. Record reasoning and data sources used for each decision
7. Mark which fields were auto-generated vs. user-provided vs. externally enriched
8. Provide comprehensive audit trails of all operations and transformations

**Conversion Agent Requirements (8 requirements):**
1. Select appropriate NeuroConv DataInterface classes based on detected formats
2. Generate valid Python code handling specific data formats and experimental setups
3. Populate NWB metadata fields and mark which are auto-generated vs. user-provided
4. Provide clear error messages and suggest corrective actions on failure
5. Record complete provenance information for successful conversions
6. Handle timeouts, retries, and service failures gracefully
7. Support mock modes that don't require external LLM services for testing
8. Provide deterministic test modes for consistent testing

**Evaluation Agent Requirements (4 requirements):**
1. Coordinate with validation systems to assess file quality and compliance
2. Coordinate with evaluation systems to generate comprehensive reports and visualizations
3. Coordinate with knowledge graph systems to generate semantic representations
4. Integrate results from validation, evaluation, and knowledge graph systems into cohesive outputs

**Metadata Questioner Requirements (4 requirements):**
1. Generate contextually appropriate questions based on experimental type and data format
2. Provide clear explanations of why information is needed and how it will be used
3. Validate answers against domain constraints and suggest alternatives for invalid responses
4. Integrate responses into structured metadata with proper provenance tracking

**Universal Agent Requirements (All agents):**
- **Consistent Interfaces**: Follow consistent error handling patterns and return structured responses, provide clear logging and progress indicators for long-running operations, provide actionable error messages with suggested remediation steps, and return results in consistent formats processable by the MCP server.

- **Configuration & Monitoring**: Support configuration of LLM providers, model parameters, and operational settings; provide metrics on processing time, success rates, and resource usage; provide detailed logging of internal operations and decision-making processes; handle timeouts, retries, and service failures gracefully.

- **Provenance & Transparency**: Record reasoning and data sources for each decision; clearly mark auto-generated vs. user-provided vs. externally enriched fields; provide citations and/or confidence scores for external information; explain heuristics or logic used for inferences; provide comprehensive audit trails of all operations.

- **Testing Support**: Support mock modes that don't require external LLM services; provide deterministic test modes for consistent testing; handle edge cases and malformed inputs gracefully; work correctly when called by the MCP server in realistic scenarios.

**Rationale**: Single responsibility principle ensures maintainability, testability, independent evolution of agent capabilities, and prevents tight coupling. Complete provenance tracking enables scientific reproducibility and validation. Standardized interfaces across agents simplify integration, testing, and evolution.

### III. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow with contract tests written before ANY implementation begins.

**TDD Workflow (Mandatory):**

1. **Write Tests First**: Write tests that define expected behavior (contract, integration, unit) based on specifications
2. **User Approval**: Obtain user approval on test specifications before proceeding
3. **Verify RED Phase**: Verify tests fail appropriately demonstrating the feature doesn't exist yet
4. **Implement GREEN**: Implement minimum code to pass tests
5. **Refactor**: Refactor while maintaining green tests

**Quality Gates (Mandatory Thresholds):**

- **Critical Paths**: 90%+ code coverage for MCP server, agents, and validation systems
- **Client Libraries**: 85%+ code coverage minimum
- **Contract Tests**: 100% OpenAPI specification coverage - every endpoint has contract tests
- **Pre-Implementation**: ALL API endpoints have contract tests BEFORE implementation begins

**MCP Server Testing Infrastructure (6 requirements):**

1. **Endpoint Testing**: Unit tests for each HTTP endpoint covering successful requests with valid data, malformed request handling, authentication/authorization scenarios, rate limiting behavior, request size limits, timeout handling, concurrent request processing, and idempotency verification for applicable endpoints, with at least 90% code coverage for endpoint handlers.

2. **Agent Coordination Testing**: Integration tests verifying proper agent orchestration including sequential workflow execution, parallel agent invocation, dependency management between agents, state persistence across agent calls, error propagation from agents to server, retry logic with exponential backoff, circuit breaker activation, and graceful degradation when agents are unavailable, testing at least 20 different workflow scenarios.

3. **Contract Testing**: Validate all endpoints conform to OpenAPI specifications through automated contract testing, response schema validation, required field verification, data type checking, enum value validation, format string compliance (dates, UUIDs, etc.), pagination consistency, HATEOAS link validity, and versioning header correctness, with 100% specification coverage.

4. **Error Condition Testing**: Verify MCP server handles agent failures (timeout, crash, invalid response), network issues (connection loss, slow networks), resource exhaustion (memory, disk, file handles), concurrent modification conflicts, database connection failures, external service unavailability, malformed data from agents, and cascade failures, with specific error codes and messages for each scenario.

5. **State Management Testing**: Validate workflow state persistence, transaction consistency, rollback capabilities, state recovery after crashes, cleanup of orphaned resources, garbage collection of old states, state migration during upgrades, and distributed state coordination, ensuring ACID properties where applicable.

6. **Security Testing**: Verify input sanitization, SQL injection prevention, path traversal protection, XXE attack prevention, CSRF token validation, rate limiting effectiveness, authentication timeout, session management, and audit logging completeness, following OWASP testing guidelines.

**Individual Agent Testing (6 requirements):**

1. **Logic Testing**: Unit tests for core functionality with 50+ test cases per agent covering input validation, data transformation accuracy with property-based testing, decision-making algorithms with scenario coverage, error handling paths with forced error injection, edge case handling with boundary value analysis, performance characteristics with benchmark tests, memory usage patterns with leak detection, and configuration validation with invalid config tests.

2. **Interface Testing**: Verify agents conform to expected input/output contracts through schema validation tests, type checking with runtime verification, required field presence checks, optional field handling tests, null/undefined handling, encoding/decoding tests (UTF-8, base64), large payload handling (>10MB), and streaming data support tests, with contract tests for all agent methods.

3. **Mock Data Testing**: Support testing without external dependencies through mock LLM services with deterministic responses, fake file systems with in-memory operations, simulated network conditions, time manipulation for temporal testing, mock external APIs with various response patterns, stub data sources with controlled data, fake credentials and secrets, and deterministic random number generation, covering 100+ mock scenarios.

4. **Error Handling Testing**: Verify agents handle malformed inputs (missing fields, wrong types, invalid formats), service failures (LLM timeout, API errors, network issues), resource constraints (memory limits, disk space, CPU throttling), concurrent access issues, partial failures in multi-step operations, rollback scenarios, cleanup after failures, and error reporting accuracy, with at least 5 test cases per error type.

5. **State Machine Testing**: Validate state transitions, illegal state prevention, state persistence, concurrent state modifications, state recovery after restart, timeout handling in each state, event ordering requirements, and side effects of state changes, with full state diagram coverage.

6. **Performance Testing**: Measure response times under various loads, throughput for batch operations, resource usage patterns, scalability limits, degradation under stress, recovery after load spikes, cache effectiveness, and optimization opportunities, with performance regression detection.

**End-to-End Testing with Real Datasets (6 requirements):**

1. **DataLad-Managed Datasets**: Use DataLad-managed test datasets including Open Ephys recordings (multi-channel, multi-session), SpikeGLX datasets with different probe configurations, Neuralynx data with video synchronization, calcium imaging data (Suite2p, CaImAn processed), behavioral tracking data (DeepLabCut, SLEAP), multimodal recordings (ephys + imaging + behavior), datasets with missing/corrupted segments, and legacy format migrations, maintaining version control for reproducibility.

2. **Format Coverage**: Include test datasets representing major neuroscience data formats with binary formats (DAT, BIN, proprietary), HDF5-based formats (with various schemas), text-based formats (CSV, TSV, JSON), video formats (AVI, MP4, MOV), image stacks (TIFF, PNG sequences), time series data (continuous, event-based), metadata formats (JSON, XML, YAML), and mixed format datasets, covering at least 15 distinct format combinations.

3. **Quality Validation**: Verify test conversions produce valid NWB files passing NWB Inspector validation with zero critical issues, PyNWB schema compliance with all required fields, data integrity with checksum verification, temporal alignment across data streams (<1ms drift), spatial registration accuracy for imaging data, signal fidelity with SNR preservation, metadata completeness (>95% fields populated), and proper unit conversions, with automated quality scoring.

4. **Complete Pipeline Testing**: Verify full workflow including dataset discovery and format detection, metadata extraction and inference, user interaction simulation for missing metadata, conversion script generation and validation, parallel processing for large datasets, progress reporting and cancellation, error recovery and partial completion, and final evaluation with report generation, testing workflows up to 1TB in size.

5. **Scientific Validity**: Verify spike sorting results preservation, behavioral event alignment, stimulus timing accuracy, trial structure maintenance, experimental metadata fidelity, derived data linkage, provenance chain completeness, and reproducibility of analysis, with domain expert validation criteria.

6. **Performance Benchmarking**: Benchmark conversion speed (MB/sec by format), memory usage patterns (peak and average), disk I/O patterns (read/write ratios), CPU utilization (single vs multi-core), network usage for remote datasets, cache effectiveness, parallel scaling efficiency, and bottleneck identification, establishing performance baselines.

**Rationale**: Neuroscience data conversion is mission-critical. TDD ensures correctness, prevents regressions, provides living documentation of system behavior, and catches integration issues early. The scientific community depends on data integrity. Comprehensive testing across unit, integration, contract, and e2e levels with real datasets ensures production readiness.

### IV. Schema-First & Standards Compliance (NON-NEGOTIABLE)

Every data structure and feature MUST start with schema definition. NWB-LinkML schema is the canonical source for all NWB data structures, ontology mappings, and validation rules.

**Schema Workflow (Mandatory Sequence):**

1. Define or extend LinkML schema
2. Generate JSON-LD contexts, SHACL shapes, and Pydantic validators from schema
3. Implement validation logic using schema-derived validators
4. Create tests using schema-derived validators
5. ONLY THEN implement features

**Required Standards:**

- **NWB-LinkML Schema**: Canonical source for all NWB data structures with version metadata recorded in PROV-O provenance for downstream triples
- **LinkML Validation**: All data validated against schemas at runtime with Pydantic class generation and controlled vocabulary checking
- **Semantic Web Standards**: RDF, OWL, SPARQL, SHACL mandatory for knowledge graphs with W3C compliance
- **NWB Inspector**: Validation required for all converted files with configurable rule sets and importance-weighted scoring
- **FAIR Principles**: Findable, Accessible, Interoperable, Reusable compliance mandatory with automated checking

**Knowledge Graph Requirements (9 requirements):**

1. **Metadata Enrichment**: Use knowledge graph to suggest enrichments based on strain-to-species mappings, device specifications, and experimental protocols with evidence quality assessment and conflict detection; provide enhanced confidence levels, complete reasoning chains, evidence hierarchy, and support for iterative refinement workflows.

2. **Entity Relationships**: Use knowledge graph to maintain entities (Dataset, Session, Subject, Device, Lab, Protocol) with semantic relationships and complete provenance using PROV-O ontology and LinkML schema versioning metadata.

3. **SPARQL Query Engine**: Support SPARQL queries for complex metadata validation and enrichment rules; SHACL shapes generated from NWB-LinkML SHALL be used for structural validation; allow definition of custom validation rules and enrichment patterns; provide efficient query execution with appropriate indexing and optimization.

4. **Schema-Driven Validation**: Validate LinkML instances (YAML/JSON) against the NWB-LinkML schema; generate RDF using the reference from the NWB-LinkML schema to ensure consistent IRIs; run SHACL validation using shapes generated from the NWB-LinkML schema and produce detailed reports.

5. **RDF Generation**: Produce JSON-LD with schema-derived @context and TTL formats; expose knowledge graphs through standard semantic web protocols (SPARQL endpoints); provide APIs for programmatic access to knowledge graph data.

6. **Core Ontology Integration**: Integrate core neuroscience ontologies including NIFSTD (Neuroscience Information Framework), UBERON (anatomy), CHEBI (chemical entities), and NCBITaxon (species) with basic concept mapping and semantic bridging; establish basic relationships between NWB-LinkML classes/slots and ontology concepts using OWL equivalence and subsumption with confidence scoring.

7. **MCP Server Integration**: Provide clean APIs for metadata enrichment and validation, including schema/shape validation APIs; expose functionality through appropriate MCP tools; handle concurrent access and maintain consistency; return structured responses compatible with agent and MCP server interfaces.

8. **Schema & Artifact Management**: When updating NWB-LinkML schema, regenerate JSON-LD contexts, SHACL shapes, and RDF/OWL artifacts and store them with version metadata; pin the schema version used and record it in PROV-O provenance for downstream triples.

9. **Dynamic Content Handling**: When encountering unknown NWB data structures, automatically discover basic entity types and properties through runtime schema analysis including neurodata_type detection and structural pattern recognition; create adaptive RDF representations that preserve data types and maintain basic semantic relationships.

**Rationale**: Schema-first development ensures semantic consistency, enables automated validation, facilitates interoperability with the broader neuroscience ecosystem, and provides machine-readable contracts for all data structures. NWB-LinkML as canonical source ensures consistency across validation, knowledge graphs, and all system components. Semantic web standards enable integration with broader scientific infrastructure.

### V. Modular Architecture First

All systems MUST follow clear separation of concerns with granular modularity enabling parallel development, independent testing, easier debugging, and clear ownership boundaries.

**System-Level Modules (10 major components):**

1. **MCP Server Architecture** - Central orchestration hub with transport adapters
2. **Agent Implementations** - Conversation, Conversion, Evaluation, Metadata Questioner agents (4 specialized agents)
3. **Knowledge Graph Systems** - RDF/LinkML-based semantic enrichment and SPARQL queries
4. **Validation & Quality Assurance** - 8 sub-modules for comprehensive validation
5. **Evaluation & Reporting** - NWB Inspector integration, quality metrics, visualization
6. **Data Management & Provenance** - DataLad operations and provenance tracking
7. **Testing & Quality Assurance** - Comprehensive testing infrastructure
8. **Client Libraries & Integrations** - External interfaces and integration patterns
9. **Core Project Organization** - Project structure, tooling, development standards
10. **Test Verbosity Optimization** - Testing performance and optimization

**Validation System Sub-Modules (within module 4, 21 requirements across 8 modules):**

**Module 1: Core Validation Framework (3 requirements)**
- Implement `BaseValidator` abstract class with standardized interface
- Provide `ValidationResult` and `ValidationIssue` dataclasses with structured output
- Implement `ValidationConfig` class with profile-based settings and runtime updates
- Support comprehensive error handling and logging with structured formats

**Module 2: NWB Inspector Integration (3 requirements)**
- Integrate NWB Inspector for schema compliance checking
- Categorize validation issues by severity (critical, warning, info, best_practice)
- Validate against current NWB schema versions with required field checks
- Check FAIR principles compliance and provide improvement suggestions

**Module 3: LinkML Schema Validation (3 requirements)**
- Load and parse LinkML schema definitions, generate Pydantic validation classes
- Validate metadata against loaded schemas in real-time with detailed field-level errors
- Support controlled vocabulary validation with completion suggestions
- Handle nested object validation and cross-references

**Module 4: Quality Assessment Engine (2 requirements)**
- Implement quality metrics for completeness, consistency, accuracy, and compliance
- Provide weighted scoring algorithms with confidence intervals
- Analyze required and optional field completeness with prioritized recommendations

**Module 5: Domain Knowledge Validator (2 requirements)**
- Validate experimental parameter ranges against known scientific bounds
- Check biological plausibility and equipment/methodology consistency
- Implement electrophysiology, behavioral, and imaging experiment validation rules

**Module 6: Validation Orchestrator (2 requirements)**
- Coordinate execution of multiple validation engines with parallel/sequential workflows
- Manage validation dependencies and provide progress tracking
- Aggregate results from multiple validators with conflict resolution
- Prioritize and rank issues by severity and impact

**Module 7: Reporting and Analytics (2 requirements)**
- Generate detailed validation reports in multiple formats (JSON, HTML, PDF)
- Provide executive summaries with visualizations
- Track validation metrics over time for trend analysis
- Generate quality improvement recommendations

**Module 8: MCP Integration Layer (2 requirements)**
- Provide MCP tools for all major validation functions
- Support asynchronous validation operations
- Integrate with MCP server infrastructure with health checks
- Implement standardized input/output formats

**Module Requirements (All modules):**

- **Self-Contained**: Each module MUST have defined interfaces (abstract base classes), independent testability and deployability, well-documented purpose and responsibilities
- **No Cross-Dependencies**: Modules communicate ONLY through defined contracts, no direct imports between modules except through interfaces
- **Versioned Interfaces**: All module interfaces are versioned, backward compatible, with clear deprecation strategies
- **Contract Testing**: Each module has comprehensive contract tests verifying interfaces

**Rationale**: Modular architecture enables parallel development, independent testing, easier debugging, clear ownership boundaries, and system evolution without cascading changes. The 10 major modules align with the project's requirements specifications, with the validation system demonstrating deep modularity through 8 internal sub-modules. This structure supports evolutionary architecture and allows component replacement without system-wide impact.

### VI. Data Integrity & Provenance

All data operations MUST ensure complete traceability from raw data through conversion to final NWB files, enabling scientific reproducibility and validation.

**DataLad Requirements (7 requirements):**

1. **Python API Exclusively**: Use DataLad Python API (`import datalad.api as dl`) for ALL operations - NEVER use CLI commands in production code. This ensures programmatic control, error handling, and integration with Python workflows.

2. **Development Dataset Management**: Use DataLad to manage test datasets, evaluation data, and conversion examples; properly configure DataLad annexing to keep development files in git and only annex large data files; make use of datasets suggested in documents/possible-datasets with proper DataLad subdataset management; ensure test datasets are available and properly versioned through DataLad.

3. **Conversion Repository Creation**: When starting a conversion, create a new DataLad repository for tracking the conversion outputs and history; save each iteration with descriptive commit messages and proper versioning; tag successful conversions and summarize the conversion history; provide easy access to all conversion artifacts, scripts, and evaluation results.

4. **Output Organization**: Organize conversion outputs including NWB files, conversion scripts, validation reports, evaluation reports, and knowledge graph outputs; properly organize outputs from validation, evaluation, and knowledge graph systems; record the complete pipeline including validation, evaluation, and knowledge graph generation steps; ensure all outputs from specialized systems are properly versioned and accessible.

5. **File Annexing Configuration**: Configure .gitattributes to keep development files in git and only annex large data files (>10MB); handle conversion example repositories as subdatasets with proper installation and updates; handle common DataLad problems (missing subdatasets, locked files) gracefully.

6. **MCP Workflow Integration**: Record all agent interactions, tool usage, and decision points in provenance system; track the complete pipeline from dataset analysis through final evaluation; record error conditions, recovery attempts, and final outcomes; provide complete audit trails that can be used for reproducibility.

7. **Performance Monitoring**: Track conversion throughput, storage usage, and basic response times; provide automated cleanup of temporary files and basic duplicate detection; implement basic memory optimization through chunked operations; log DataLad operation status, performance metrics, and error conditions.

**Provenance Tracking Requirements:**

- **Confidence Levels**: Record confidence level for every metadata field: `definitive` (verified facts), `high_evidence` (strong automated inference), `human_confirmed` (user validated), `human_override` (user corrected automated value), `medium_evidence` (reasonable inference), `heuristic` (pattern-based guess), `low_evidence` (weak inference), `placeholder` (temporary value), `unknown` (no confidence info). Also record source type, derivation method, and complete reasoning chain.

- **Audit Trails**: Maintain complete audit trails of all modifications, decisions, data transformations, and evidence conflicts with resolution methods. Clearly distinguish between evidence-based decisions and human overrides, presenting evidence summaries for human review when conflicts exist.

- **Transparency Reports**: Generate reports with detailed provenance summaries including decision chains, evidence quality assessment, and confidence distributions allowing users to verify and validate all automated decisions.

**Repository Structure:**
- Code and configuration: GitHub repository
- Large data files: GIN (G-Node Infrastructure) via git-annex
- Conversion outputs: Annexed in output directories
- Test fixtures: Small samples (<10MB) in git, large datasets annexed

**Rationale**: Scientific reproducibility requires complete traceability from raw data through conversion to final NWB files. DataLad provides version control for data, enabling bit-for-bit reproduction of conversions. Provenance tracking with confidence levels enables validation, debugging, and scientific credibility. Complete audit trails support scientific integrity and allow researchers to understand and validate all automated decisions.

### VII. Quality-First Development

Quality assessment MUST be multi-dimensional and comprehensive, recognizing that valid structure without quality is scientifically useless.

**Multi-Dimensional Quality Requirements (6 requirements):**

1. **NWB Validation Foundation**: When nwb-inspector is available, execute with configurable parameters and parse JSON output into structured results with timeout handling and error recovery; when circuit breaker protection is active, immediately use fallback validation without attempting nwb-inspector and provide clear error messages with recovery guidance.

2. **Technical Quality Assessment**: Evaluate schema compliance, data integrity, structure quality, and performance characteristics with detailed scoring and specific remediation recommendations.

3. **Scientific Quality Assessment**: Assess experimental completeness against domain standards, validate experimental design consistency, and evaluate documentation adequacy with domain-specific improvement suggestions.

4. **Usability Quality Assessment**: Assess documentation clarity, evaluate searchability and metadata richness, check accessibility compliance, and suggest user experience improvements using natural language processing metrics.

5. **Quality Orchestration**: Coordinate all evaluator modules with proper dependency management and support parallel execution of independent evaluators; apply configurable weights, combine scores appropriately, and produce actionable recommendations; provide graceful degradation with partial results, maintain evaluation audit trails for traceability, and provide real-time progress reporting.

6. **Comprehensive Reporting**: Create executive summaries suitable for non-technical audiences and detailed technical reports with metrics, validation results, and recommendations; support multiple formats (Markdown, HTML, PDF, JSON) with custom report templates, variable substitution, and consistent formatting; generate simple HTML reports with embedded charts using lightweight JavaScript libraries; ensure HTML files work offline without external dependencies.

**Quality Dimensions:**

- **Completeness**: Required fields present, optional fields populated, metadata richness assessed, completion recommendations prioritized by importance
- **Consistency**: Cross-field validation, temporal continuity verified, spatial registration accurate
- **Accuracy**: Scientific plausibility checks, unit conversions correct, numerical precision verified
- **Compliance**: NWB schema conformance, FAIR principles adherence, DANDI requirements met, domain standards followed

**Quality Workflow:**
- Weighted scoring algorithms with configurable thresholds
- Scientific plausibility checks for neuroscience data
- Remediation guidance mandatory for all validation issues
- Performance benchmarks with regression detection
- Continuous quality improvement through analytics

**MCP Integration Requirements:**
- Provide clean APIs for evaluation services through standard MCP protocol with input validation and structured responses
- Expose functionality through appropriate MCP tools and handle concurrent evaluation requests with proper isolation
- Coordinate with all dependent modules efficiently, respond to health checks within 1 second, and provide request/response logging for monitoring

**Rationale**: Valid structure without quality is scientifically useless. Multi-dimensional assessment ensures converted data meets both technical and scientific standards. Comprehensive quality assessment protects scientific integrity, prevents publication of low-quality data, and maintains trust in the conversion pipeline. Automated quality scoring with human-readable explanations enables researchers to make informed decisions about data quality.

### VIII. Observability & Traceability

All operations MUST provide comprehensive visibility into system operation, enabling debugging, performance optimization, and operational reliability.

**Logging Requirements (8 requirements):**

1. **Structured Logging**: Implement structured logging with JSON format, correlation IDs for distributed tracing across services, log levels per module (DEBUG, INFO, WARNING, ERROR, CRITICAL), contextual information embedding, performance metrics in logs, security event logging, error fingerprinting for grouping, and log sampling for high-volume operations, following OpenTelemetry standards.

2. **Error Tracking**: Include full stack traces, request/response recording, state snapshots at failure, distributed tracing visualization, flame graphs for performance analysis, memory dump capabilities, goroutine/thread analysis, and time-travel debugging support, with configurable detail levels.

3. **Component Logging Verification**: Verify that all components produce appropriate log messages at correct severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL), with structured logging format (JSON), correlation IDs for request tracing, performance metrics in logs, security event logging, error stack traces with context, rate limiting for log floods, log sanitization for sensitive data, and log aggregation compatibility, covering 100% of error paths.

4. **Log Levels Per Module**: Support configurable log levels per module, enabling fine-grained control over logging verbosity without system restart.

5. **Log Aggregation Support**: Ensure compatibility with log aggregation systems (ELK/Fluentd), providing structured output that can be easily parsed and indexed.

6. **Debug Mode Toggles**: Provide runtime toggles for debug mode enabling detailed logging without requiring code changes or restarts.

7. **Remote Debugging Support**: Support remote debugging capabilities for production troubleshooting with appropriate security controls.

8. **Interactive Debugging Tools**: Provide interactive debugging tools for MCP server operations and agent interactions, enabling step-through debugging of complex workflows.

**Monitoring Requirements:**

- **Conversion Metrics**: Track throughput (files/hour, GB/hour), latency percentiles (p50, p90, p99, p99.9), error rates by category, resource utilization trends, queue depths and wait times, cache effectiveness metrics, agent performance scores, and cost per conversion, with real-time dashboards.

- **Performance Metrics**: Validate that performance metrics are collected including response times (p50, p90, p99, max), throughput (requests/sec, bytes/sec), error rates by category, resource utilization (CPU, memory, disk, network), queue depths and wait times, cache hit rates, database query performance, and custom business metrics, with Prometheus/OpenMetrics format support.

- **Usage Analytics**: Analyze data format distribution, conversion success patterns, common failure modes, user behavior patterns, resource usage patterns, peak usage times, geographic distribution, and feature utilization rates, with predictive insights.

**Distributed Tracing Requirements:**

- **OpenTelemetry Standards**: Support distributed tracing with Jaeger/Zipkin integration, following OpenTelemetry standards for cross-service visibility
- **Trace Propagation**: Verify trace propagation across services, span relationship accuracy, timing information precision, baggage data preservation, sampling strategies, trace storage and retrieval, query capabilities, and visualization accuracy
- **Correlation IDs**: Embed correlation IDs in all logs and traces enabling end-to-end request tracking across distributed components

**Diagnostics Requirements:**

- **Health Checks**: Ensure diagnostic endpoints provide health check status (liveness, readiness), dependency status checks, configuration validation, resource availability, performance profiling data, thread dumps on demand, memory heap analysis, and debugging endpoints, with sub-second response times.

- **Error Capture**: Verify errors are properly captured with full context, categorized by type and severity, deduplicated for similar issues, enriched with system state, tracked across services, aggregated for trends, alerted based on thresholds, and integrated with incident management, achieving 100% critical error capture.

**Observability Integration:**

- Support distributed tracing with Jaeger/Zipkin, metrics with Prometheus/OpenMetrics, logging with ELK/Fluentd, APM with Datadog/New Relic, custom dashboards with Grafana, alerting with PagerDuty/Opsgenie, anomaly detection with ML models, and capacity planning tools, ensuring full system visibility.

- Implement proactive monitoring with anomaly detection algorithms, threshold-based alerting, trend analysis for degradation, predictive failure analysis, automatic issue correlation, root cause suggestion, impact assessment, and automated remediation triggers, reducing mean time to detection.

**Rationale**: Complex multi-agent systems require comprehensive observability for debugging, performance optimization, and operational reliability. Structured logging enables automated analysis and alerting. Distributed tracing provides end-to-end visibility across microservices. Comprehensive monitoring enables proactive issue detection and resolution, reducing downtime and improving user experience.

## Technical Standards

### Validation & Quality Assurance

**NWB Inspector Integration:**
- Configurable rule sets with importance-weighted scoring
- Timeout handling (default 30s for <1GB files) with error recovery
- Fallback validation without nwb-inspector when circuit breaker active
- JSON output parsing into structured results with remediation guidance

**LinkML Schema Validation:**
- Runtime validation against NWB-LinkML schemas
- Pydantic class generation from schemas for type-safe validation
- Controlled vocabulary checking with completion suggestions
- Partial validation support for incomplete metadata
- Nested object validation and cross-reference handling

**Domain Knowledge Validation:**
- Scientific plausibility checks for experimental parameters
- Biological plausibility verification for measurements
- Equipment and methodology consistency validation
- Domain-specific guidance for questionable values
- Electrophysiology, behavioral, and imaging experiment-specific rules

**Quality Metrics:**
- Weighted scoring algorithms with configurable thresholds
- Multi-dimensional assessment: technical, scientific, usability
- Completeness scoring: required fields 100%, optional >90% when applicable
- Consistency validation: cross-field, temporal, spatial
- Accuracy verification: unit conversions, numerical precision, coordinate transformations

**FAIR Compliance:**
- Automated checking for Findable, Accessible, Interoperable, Reusable principles
- Metadata completeness assessment against best practices
- Anti-pattern detection and improvement suggestions

### Knowledge Graph Standards

**Schema Sources:**
- NWB-LinkML as canonical source for all ontology mappings
- Version metadata recorded in PROV-O provenance for downstream triples
- Automated regeneration of JSON-LD contexts, SHACL shapes, RDF/OWL artifacts on schema updates

**Output Formats:**
- JSON-LD with schema-derived @context
- Turtle (TTL) for human-readable RDF
- RDF/XML for tool interoperability

**Validation:**
- SHACL shapes generated from NWB-LinkML for structural validation
- Detailed validation reports with issue localization
- Round-trip conversion verification

**Query Engine:**
- SPARQL endpoint with efficient indexing and optimization
- Support for complex metadata validation rules
- Custom validation rules and enrichment patterns
- Query performance: <200ms for simple queries, <30s for complex enrichment

**Ontology Integration:**
- NIFSTD (Neuroscience Information Framework) - neuroscience concepts
- UBERON (anatomy) - anatomical structures
- CHEBI (chemical entities) - chemicals and drugs
- NCBITaxon (species) - organism taxonomy
- OWL equivalence and subsumption relationships with confidence scoring

**Provenance:**
- PROV-O ontology for all transformations and enrichments
- Complete lineage tracking from raw NWB to final RDF
- Evidence trails for enrichment decisions

### Data Management Standards

**DataLad Operations:**
- Python API only (`import datalad.api as dl`) - NEVER CLI commands
- All operations use `datalad.api` methods: `status()`, `save()`, `get()`, `create()`, `install()`, `add()`, `drop()`
- Proper exception handling for DataLad operations
- Programmatic control enabling error recovery and workflow integration

**File Annexing:**
- Files >10MB automatically annexed
- Storage on GIN (G-Node Infrastructure) via git-annex
- .gitattributes configuration: `* annex.largefiles=(largerthan=10MB)`
- Development files (<10MB) kept in git for fast access

**Subdatasets:**
- Properly initialized before use with `datalad install`
- Version pinning for reproducibility
- Recursive operations when needed (`recursive=True`)

**Commit Messages:**
- Descriptive messages following Conventional Commits format
- Format: `type(scope): description` e.g., `feat(conversion): add Open Ephys support`
- Types: feat, fix, docs, test, refactor, perf, ci, chore
- Include conversion details: format, file count, data size

**Repository Structure:**
```
GitHub (code, config)
├── src/
├── tests/
├── docs/
└── .datalad/

GIN (large files via git-annex)
├── test-datasets/
├── evaluation-data/
└── conversion-examples/

Conversion Outputs (annexed)
├── nwb-files/
├── scripts/
├── validation-reports/
└── knowledge-graphs/
```

### Performance & Scale Standards

**Conversion Performance:**
- Speed: Variable by format, establish baseline benchmarks per format
- Memory: <2GB for standard workflows, chunked operations for large files
- Parallel processing: Support concurrent conversions with resource isolation

**Validation Performance:**
- Files <1GB: <30 seconds for complete validation
- Files >10GB: Streaming validation to avoid memory limits
- Progressive validation: Validate during conversion for early error detection

**API Response Times:**
- Standard endpoints: <200ms p95 latency
- Health checks: <1 second response time
- Long-running operations: Progress updates via WebSocket/SSE

**Query Performance:**
- Simple SPARQL queries: <200ms
- Complex enrichment operations: <30s with human review
- Metadata validation queries: <500ms for real-time feedback

**Concurrent Operations:**
- Support parallel workflows with proper isolation
- Resource allocation per workflow
- Backpressure handling for overwhelmed agents
- Fair scheduling across workflows

### Integration Standards

**MCP Protocol:**
- Full compliance with Model Context Protocol specification
- Support for stdin/stdout, Unix socket, TCP transports
- Tool discovery and capability querying
- Structured error responses with error codes

**HTTP/REST:**
- OpenAPI 3.0 specifications for all endpoints
- HATEOAS principles for discoverability
- Content negotiation (JSON, MessagePack)
- Compression support (gzip, brotli)

**WebSocket:**
- Real-time bidirectional communication for progress updates
- Socket.IO compatibility for client libraries
- Automatic reconnection with exponential backoff
- Message queuing during disconnections

**GraphQL:**
- Optional query interface for flexible data access
- Subscription support for real-time updates
- Schema introspection and documentation
- Query complexity limits to prevent DoS

**Event-Driven:**
- Message queues (RabbitMQ/Kafka) for asynchronous processing
- Event sourcing patterns for audit trails
- Saga pattern for distributed transactions
- Dead letter queues for failed operations

### Security Standards

**Input Validation:**
- All inputs sanitized before processing
- Schema validation required (Pydantic models)
- Whitelist-based validation where possible
- Size limits enforced (request body <100MB default)

**Injection Prevention:**
- SQL injection: Use parameterized queries exclusively, no string interpolation
- Path traversal: Validate and sanitize file paths, restrict to allowed directories
- XXE attack: Disable external entity processing in XML parsers
- Command injection: Never pass user input to shell commands

**Authentication:**
- Token-based authentication with JWT
- Token refresh mechanisms with sliding expiration
- Timeout management (30 minute default, configurable)
- Multi-factor authentication support for high-security deployments

**Authorization:**
- Role-based access control (RBAC) where applicable
- Principle of least privilege
- Resource-level permissions
- Audit logging of authorization decisions

**Audit Logging:**
- Security events logged with full context
- Authentication attempts (success/failure)
- Authorization failures
- Configuration changes
- Data access patterns

**Secrets Management:**
- NO secrets in code or configuration files
- Environment variables for development
- Vault integration for production (HashiCorp Vault, AWS Secrets Manager)
- Encrypted secrets in transit and at rest
- Secret rotation policies

**OWASP Compliance:**
- Follow OWASP Top 10 mitigation strategies
- Regular security scanning (SAST, DAST)
- Penetration testing for critical deployments
- Security training for developers

## Development Workflow

### Code Quality Requirements

**Language & Environment:**
- Python 3.11+ (production code)
- Python 3.8-3.12 compatibility (client libraries)
- pixi for reproducible environment management
- `pyproject.toml` for modern packaging standards

**Configuration:**
- pydantic-settings for type-safe configuration
- Nested classes for complex settings
- Environment variable support with prefixes (e.g., `NWB_CONVERTER_`)
- Configuration validation at startup
- Feature flag support for gradual rollout

**Linting & Formatting:**
- ruff for linting, formatting, and import organization
- Line length: 100 characters
- Import sorting: isort-compatible
- Automated fixes applied by pre-commit hooks

**Type Checking:**
- mypy in strict mode for static type checking
- Type hints required for all functions and methods
- Type stubs for external libraries without types
- Generic types for collections and callables

**Code Quality Checks:**
- pylint for additional code quality analysis
- bandit for security scanning
- vulture for dead code detection
- Complexity analysis: cyclomatic complexity ≤10, maintainability index tracking

**Pre-Commit Hooks:**
All quality checks run automatically before commit:
- Code formatting verification (ruff format --check)
- Linting checks passing (ruff check)
- Type checking success (mypy)
- Test execution for changed files
- Documentation generation
- Commit message format validation (Conventional Commits)
- Branch naming conventions (feat/*, fix/*, docs/*, etc.)
- File size limits (<5MB without justification)
- Secret scanning (no API keys, passwords, tokens)

**Bypass**: Use `--no-verify` ONLY for emergencies with explicit justification in commit message.

### Testing Requirements

**Test Categories:**

**Unit Tests:**
- Individual component isolation testing
- 50+ test cases per complex component (agents, validators, converters)
- Property-based testing with Hypothesis for data transformations
- Boundary value analysis for edge cases
- Forced error injection for error handling paths
- Benchmark tests for performance characteristics
- Memory leak detection for long-running operations
- Configuration validation with invalid configs

**Integration Tests:**
- Component interaction testing
- Agent coordination: 20+ workflow scenarios minimum
- State persistence across agent calls
- Error propagation from agents to server
- Retry logic with exponential backoff verification
- Circuit breaker activation testing
- Graceful degradation when agents unavailable
- Multi-step workflow testing

**Contract Tests:**
- API endpoint conformance to OpenAPI specifications
- 100% specification coverage mandatory
- Response schema validation
- Required field verification
- Data type checking with runtime verification
- Enum value validation
- Format string compliance (dates, UUIDs, emails)
- Pagination consistency
- HATEOAS link validity

**End-to-End Tests:**
- Full pipeline with real DataLad-managed datasets
- Dataset discovery and format detection
- Metadata extraction and inference
- User interaction simulation
- Conversion script generation and validation
- Parallel processing for large datasets
- Progress reporting and cancellation
- Error recovery and partial completion
- Final evaluation with report generation
- Workflows up to 1TB in size

**Performance Tests:**
- Benchmarks with baseline establishment
- Regression detection (alert if >10% slower)
- Load testing (concurrent users/workflows)
- Stress testing (resource exhaustion scenarios)
- Scalability testing (horizontal/vertical scaling)
- Cache effectiveness measurement

**Test Data Management:**

- **DataLad Integration**: Version-controlled datasets with lazy loading for files >10MB
- **Test Fixtures**: 100+ predefined fixtures including minimal valid datasets, corrupted data edge cases, large-scale performance data, multi-modal combinations, time-series generators, metadata variations, format conversion cases, regression baselines
- **Synthetic Data**: Generation utilities for edge cases and boundary conditions
- **Data Anonymization**: Utilities for sensitive information removal
- **Test Isolation**: Proper cleanup between tests, parallel test isolation

**Testing Standards:**

- Tests written BEFORE implementation (RED-GREEN-REFACTOR)
- Property-based testing with Hypothesis for data transformations
- Mutation testing for critical validation logic
- Snapshot testing for complex outputs
- Golden file testing for regression prevention
- Chaos engineering tests for client resilience
- Cross-platform testing: Ubuntu 20.04+, macOS 11+, Windows 10+ where applicable

**Test Utilities:**

- Mock service instantiation with presets
- Test data generation with realistic patterns
- Fixture factories for common scenarios
- Assertion helpers for complex comparisons
- Custom matchers for domain objects
- Test decorators for common patterns (timeout, retry, parameterize)
- Cleanup utilities for automatic resource management

### CI/CD Requirements

**Automated Testing Triggers:**

**Every Commit:**
- Unit tests (<5 minutes total execution time)
- Linting and formatting checks
- Type checking (mypy)
- Security scanning basics (secret detection)

**Every Pull Request:**
- All unit tests
- Integration tests (<15 minutes total execution time)
- Contract tests (100% specification coverage)
- Code quality analysis
- Security scanning (SAST, dependency vulnerabilities)
- Documentation building verification
- License compliance checking
- Commit message validation
- Performance benchmark comparison

**Nightly:**
- Comprehensive test suite (all categories)
- E2E tests with real datasets
- Performance tests and benchmarking
- Security scanning (full SAST, DAST)
- Long-running stability tests (24+ hours)

**Weekly:**
- Dependency update checks
- License compliance audit
- Security vulnerability scanning (full)

**Testing Matrix:**

**Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
**Platforms**: linux-64, osx-arm64, osx-64 (if needed), windows (for client libraries)
**Dependency Versions**: minimum supported, latest stable, development (pre-release)

**Quality Gates (Mandatory for Merge):**

- All tests passing
- Code coverage thresholds maintained or improved
  - Critical paths: ≥90%
  - Client libraries: ≥85%
  - Overall: ≥80%
- No new security vulnerabilities (SAST, dependency scanning)
- Performance benchmarks within acceptable bounds (±10% of baseline)
- Documentation updated for user-facing changes
- All contract tests passing (100% specification coverage)
- Breaking changes documented with migration guide
- Architectural constraints verified

**Deployment:**

- Containerization: Docker/OCI compliance, multi-stage builds for size optimization
- Kubernetes: Operators and CRDs for complex deployments, Helm charts with values customization
- Cloud-native: Support for AWS/GCP/Azure with infrastructure as code (Terraform, Pulumi)
- Blue-green deployments: Zero-downtime updates with rollback capability
- Deployment previews: Automatic preview environments for pull requests

### Documentation Requirements

**API Documentation:**
- OpenAPI 3.0/AsyncAPI specifications (auto-generated from code)
- Interactive documentation (Swagger UI, ReDoc)
- Code examples for common operations
- Authentication guides with examples
- Rate limiting documentation
- Webhook integration guides
- SDK documentation per language (Python primary)
- Error code reference with remediation suggestions

**Code Documentation:**
- Google-style docstrings for all public APIs
- Type hints for all functions and methods
- Inline comments for complex logic (when, why, gotchas)
- Module-level docstrings with overview and examples
- Example usage in docstrings for clarity
- Performance considerations noted
- Deprecation warnings with migration paths

**Architecture Documentation:**
- C4 model diagrams (System Context, Container, Component, Code)
- Sequence diagrams for key workflows
- Component interaction maps
- Data flow visualizations
- Deployment diagrams for different environments
- Architecture Decision Records (ADRs) for significant decisions
- Decision log with rationale, alternatives, consequences

**User Guides:**
- Quickstart guide (<10 minutes to first conversion)
- Tutorials for common scenarios (10+ examples)
- How-to guides for specific tasks
- Troubleshooting guide with common issues/solutions
- FAQ based on user questions

**Contribution Guides:**
- Development setup (step-by-step, < 30 minutes)
- Testing strategies and best practices
- Code review process and checklists
- Coding standards and style guide
- Git workflow (branching, commits, PRs)
- First good issues labeled for newcomers

**Changelog:**
- Structured changelog following Keep a Changelog format
- Versioned releases with semver
- Categorized changes: Added, Changed, Deprecated, Removed, Fixed, Security
- Migration guides for breaking changes
- Release notes with highlights

## Governance

### Amendment Process

Constitution amendments require a formal process ensuring stability while allowing evolution:

1. **Documented Proposal**: Written proposal with specific wording changes, clear rationale explaining why the change is needed, and examples of how it will improve the project.

2. **Impact Analysis**: Assessment of effects on existing specifications (which specs need updates?), implementations (what code changes are required?), development workflows (what processes change?), and team processes (training needs, timeline).

3. **Community Review**: Discussion period for stakeholder input (minimum 1 week for MINOR, 2 weeks for MAJOR changes), opportunity for feedback and iteration, consensus-building among maintainers and contributors.

4. **Approval**: Consensus among maintainers where possible, maintainer decision per project governance if consensus not reached, documented reasoning for approval/rejection.

5. **Migration Plan**: Concrete steps for transitioning existing code and documentation, timeline for implementation with milestones, backward compatibility strategy or deprecation period, communication plan for affected parties, rollback plan if issues arise.

6. **Version Increment**: Per semantic versioning rules defined below, update version in constitution, update Sync Impact Report, notify stakeholders of changes.

### Versioning Policy

Constitution versions follow semantic versioning (MAJOR.MINOR.PATCH):

**MAJOR (X.0.0)** - Breaking changes:
- Core principles removed or fundamentally redefined (e.g., removing TDD requirement)
- Governance structure changes that invalidate existing processes
- Architectural changes requiring code rewrites (e.g., changing from MCP to different protocol)
- Removal of mandatory compliance requirements
- Changes that make existing implementations non-compliant

Examples:
- Removing TDD as mandatory → MAJOR (breaks development workflow)
- Changing from MCP-centric to different architecture → MAJOR (requires rewrite)
- Removing DataLad Python API requirement → MAJOR (allows CLI, changes implementations)

**MINOR (x.Y.0)** - Backward-compatible additions:
- New principles added (additional constraints)
- New sections or subsections (expanded guidance)
- Materially expanded guidance on existing principles
- Additional non-breaking constraints or requirements
- New quality gates that don't invalidate existing work

Examples:
- Adding new principle about AI ethics → MINOR (expands requirements)
- Adding security standards section → MINOR (new guidance)
- Expanding testing requirements with new test types → MINOR (additions, not breaking)

**PATCH (x.y.Z)** - Non-semantic changes:
- Clarifications of existing principles (no new requirements)
- Wording improvements for clarity
- Typo fixes and grammar corrections
- Formatting improvements
- Example additions or improvements
- Reorganization without content changes

Examples:
- Clarifying what "DataLad Python API" means → PATCH (no new requirement)
- Fixing typos in principle descriptions → PATCH (cosmetic)
- Adding examples to illustrate existing principles → PATCH (helpful but not required)

**Version Increment Decision Tree:**
1. Does it break existing implementations or make them non-compliant? → MAJOR
2. Does it add new requirements or principles? → MINOR
3. Does it only clarify or fix without adding requirements? → PATCH

### Compliance Verification

All pull requests MUST verify constitutional compliance before merge. Code reviews SHALL check:

**1. TDD Workflow Evidence**
- ✅ Tests committed before implementation
- ✅ Test file timestamps earlier than implementation files
- ✅ Git history shows test commits before feature commits
- ✅ PR description references test specifications
- ✅ Tests demonstrated failing (RED phase) before implementation

**2. MCP Interface Consistency**
- ✅ All functionality exposed through MCP tools
- ✅ No direct agent invocation from external clients
- ✅ Business logic in transport-agnostic core service layer
- ✅ Adapters are thin (<500 lines, <5% codebase per adapter)
- ✅ Adapters contain zero business logic
- ✅ Functional parity across all transports verified by contract tests

**3. DataLad API Usage**
- ✅ All DataLad operations use Python API (`import datalad.api as dl`)
- ✅ No CLI commands (`datalad save`, `datalad create`, etc.) in production code
- ✅ Proper exception handling for DataLad operations
- ✅ File annexing configuration correct (>10MB threshold)

**4. Schema Compliance**
- ✅ All data structures defined in LinkML schemas first
- ✅ Schema-derived validators generated before implementation
- ✅ Runtime validation against schemas implemented
- ✅ Tests use schema-derived validators
- ✅ NWB-LinkML referenced for all NWB data structures

**5. Modular Architecture**
- ✅ Clear module boundaries maintained
- ✅ No cross-module dependencies except through defined interfaces
- ✅ Modules independently testable
- ✅ Contract tests exist for all module interfaces
- ✅ New modules follow standard structure

**6. Quality Standards**
- ✅ Multi-dimensional quality assessment implemented
- ✅ Completeness, consistency, accuracy, compliance checked
- ✅ Remediation guidance provided for all issues
- ✅ Scientific plausibility checks for domain data

**7. Observability**
- ✅ Structured logging (JSON) with correlation IDs
- ✅ Error tracking with full stack traces
- ✅ Metrics collection for performance monitoring
- ✅ Audit trails for significant operations
- ✅ OpenTelemetry standards followed for distributed tracing

**Review Checklist for Pull Requests:**

```markdown
## Constitutional Compliance

- [ ] **TDD**: Tests written before implementation (evidence in commit history)
- [ ] **Contract Tests**: New API endpoints have contract tests
- [ ] **Schema-First**: Data structures defined in schemas before code
- [ ] **MCP Tools**: Functionality exposed through MCP tools (no direct agent access)
- [ ] **DataLad API**: Python API only (no CLI in production)
- [ ] **Modular**: Clear module boundaries, contracts verified
- [ ] **Quality**: Multi-dimensional assessment implemented
- [ ] **Observability**: Structured logging, metrics, tracing present
- [ ] **Documentation**: Updated for user-facing changes
- [ ] **Performance**: Impact assessed, benchmarks within bounds
- [ ] **Security**: Implications considered, no new vulnerabilities
- [ ] **Breaking Changes**: Documented with migration guide (if applicable)

## Additional Checks

- [ ] Code coverage maintained or improved
- [ ] All tests passing (unit, integration, contract)
- [ ] No security vulnerabilities introduced
- [ ] Commit messages follow Conventional Commits
- [ ] PR linked to issue/feature request
```

### Constitutional Authority

This constitution is the supreme governing document for the Agentic Neurodata Conversion project.

**Hierarchy of Authority:**

1. **This Constitution** (highest authority)
2. Architecture Decision Records (ADRs) - for specific design decisions within constitutional bounds
3. Technical specifications and requirements
4. Implementation guidelines and best practices
5. Code comments and documentation

**Conflict Resolution:**

When conflicts arise between this constitution and other documentation (specifications, ADRs, code comments, etc.), **constitutional principles take precedence**. The conflicting documentation MUST be updated to align with constitutional requirements.

**Exception Process:**

Deviations from constitutional principles require explicit approval and documentation:

1. **Written Justification**: Document why simpler constitutional-compliant alternatives are insufficient, specific benefits of the exception, risks introduced by the deviation, mitigation strategies for those risks.

2. **Maintainer Approval**: Explicit approval from at least one project maintainer, documented in PR comments or ADR, reasoning for approval recorded.

3. **ADR Documentation**: Create Architecture Decision Record documenting the exception, rationale, alternatives considered, risks and mitigations, review and approval record.

4. **Complexity Tracking**: Track in relevant specification's "Complexity Tracking" section, link to ADR and approval, explain why simpler alternatives rejected.

5. **Time-Bound (if temporary)**: Exceptions SHOULD have sunset dates when possible, plan for migration to constitutional compliance, timeline for removing exception.

6. **Regular Review**: All exceptions reviewed quarterly, assessed for continued necessity, migration path updated if still needed.

**Enforcement Mechanisms:**

**Code Reviews:**
- All PRs reviewed for constitutional compliance using checklist above
- Violations block merge until resolved or exception approved
- Reviewer comments reference specific constitutional principles

**Automated Linters:**
- Pre-commit hooks enforce coding standards, test requirements, security checks
- CI/CD pipelines verify compliance with quality gates
- Automated checks for DataLad API usage, schema validation, test coverage

**Architectural Fitness Functions:**
- Automated tests verifying architectural constraints
- Contract tests ensuring adapter thin-ness (<500 lines, <5% per adapter)
- Dependency analysis preventing cross-module violations
- Cyclic dependency detection and prevention

**Violations:**
- PRs with violations cannot merge until fixed or exception approved
- Repeated violations trigger discussion of whether principle needs clarification
- Intentional violations without exception process are rejected

---

**Version**: 3.0.0
**Ratified**: 2025-10-08
**Last Amended**: 2025-10-08
**Supersedes**: All prior constitution versions (1.0.0, 1.1.0, 2.0.0, 2.0.1, and all PR-specific versions)

**Source**: Generated from comprehensive requirements across 10 specification files (1389 lines total) covering Agent Implementations, Client Libraries & Integrations, Core Project Organization, Data Management & Provenance, Evaluation & Reporting, Knowledge Graph Systems, MCP Server Architecture, Test Verbosity Optimization, Testing & Quality Assurance, and Validation & Quality Assurance.
