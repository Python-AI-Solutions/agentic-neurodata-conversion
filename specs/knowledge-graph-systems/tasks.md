# Tasks: Knowledge Graph Systems

**Input**: Design documents from
`/Users/adityapatane/agentic-neurodata-conversion-3/specs/001-knowledge-graph-systems/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)

```
1. Load plan.md from feature directory
   → ✅ Found implementation plan with Python 3.12-3.13, semantic web stack
   → ✅ Extract: rdflib, linkml, pynwb, fastapi, mcp, SHACL validation libraries
2. Load optional design documents:
   → ✅ data-model.md: Extract 11 entities → model tasks
   → ✅ contracts/: 2 contract files → contract test tasks
   → ✅ research.md: Extract technical decisions → setup tasks
3. Generate tasks by category:
   → ✅ Setup: LinkML schema, dependencies, constitutional compliance
   → ✅ Tests: SPARQL contract tests, MCP integration tests, enrichment workflow tests
   → ✅ Core: knowledge graph models, semantic services, CLI commands
   → ✅ Integration: RDF triple store, SHACL validation, ontology mapping
   → ✅ Polish: unit tests, performance benchmarks, documentation
4. Apply task rules:
   → ✅ Different files = mark [P] for parallel execution
   → ✅ Same file = sequential (no [P]) to avoid conflicts
   → ✅ Tests before implementation (TDD constitutional requirement)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph with constitutional compliance
7. Create parallel execution examples for semantic web components
8. Validate task completeness:
   → ✅ All contracts have tests
   → ✅ All entities have models with LinkML schema compliance
   → ✅ All endpoints implemented with W3C standards
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Knowledge graph components organized by semantic function
- Tests follow constitutional TDD requirements

## Phase 3.1: Setup

- [ ] T001 Create knowledge graph project structure per implementation plan in
      agentic_neurodata_conversion/knowledge_graph/
- [ ] T002 Add semantic web dependencies to pixi.toml (rdflib>=7.1.4, linkml>=1.5.0, pyshacl, fastapi>=0.100.0, mcp>=1.0.0) and run pixi install
      Note: Python 3.12-3.13 environment managed via pixi (per pixi.toml: ">=3.12,<3.14")
- [ ] T003 [P] Configure linting and formatting tools (ruff, mypy) for
      constitutional compliance
- [ ] T004 [P] Set up LinkML schema processing pipeline in
      agentic_neurodata_conversion/knowledge_graph/schema/
- [ ] T005 [P] Configure SHACL validation framework with pyshacl in
      agentic_neurodata_conversion/knowledge_graph/validation/

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CONSTITUTIONAL TDD WORKFLOW** (Constitution Principle II):
1. ✅ **RED**: Write test and verify it FAILS with expected error
2. ✅ **GREEN**: Implement minimum code to make test pass
3. ✅ **REFACTOR**: Improve code while maintaining green tests

**CRITICAL VERIFICATION STEPS**:
- [ ] After writing each test: Run `pixi run test-quick [test-file]`
- [ ] Confirm test FAILS with clear, expected error message
- [ ] Document expected failure behavior in test docstring
- [ ] Take screenshot or copy failure output for verification
- [ ] Only after RED verification → proceed to implementation (GREEN)
- [ ] After GREEN → refactor for quality while maintaining pass state

**CRITICAL: These tests MUST be written and MUST FAIL before ANY
implementation**

### Contract Tests (Parallel - Different Files)

- [ ] T006 [P] Contract test POST /sparql endpoint in
      tests/contract/test_sparql_endpoints.py
- [ ] T007 [P] Contract test POST /datasets endpoint in
      tests/contract/test_datasets_api.py
- [ ] T008 [P] Contract test POST /datasets/{id}/enrich endpoint in
      tests/contract/test_enrichment_api.py
- [ ] T009 [P] Contract test POST /validation/shacl endpoint in
      tests/contract/test_shacl_validation.py
- [ ] T010 [P] Contract test POST /validation/linkml endpoint in
      tests/contract/test_linkml_validation.py
- [ ] T011 [P] Contract test MCP tools in tests/contract/test_mcp_tools.py

### Integration Tests (Parallel - Different Scenarios)

- [ ] T012 [P] Integration test dataset creation and enrichment workflow in
      tests/integration/test_enrichment_workflow.py
- [ ] T013 [P] Integration test SPARQL query execution with 30-second timeout in
      tests/integration/test_sparql_execution.py
- [ ] T014 [P] Integration test schema validation and artifact regeneration in
      tests/integration/test_schema_validation.py
- [ ] T015 [P] Integration test ontology mapping with confidence scoring in
      tests/integration/test_ontology_mapping.py
- [ ] T016 [P] Integration test human review workflow for enrichment suggestions
      in tests/integration/test_human_review.py
- [ ] T017 [P] Integration test conflict resolution for competing suggestions in
      tests/integration/test_conflict_resolution.py
- [ ] T018 [P] Integration test provenance tracking using PROV-O in
      tests/integration/test_provenance_tracking.py
- [ ] T018a [P] Integration test unknown NWB structure handling with runtime
      schema discovery in tests/integration/test_unknown_structures.py (covers
      spec.md Edge Case 1)

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### LinkML Schema and Models (Parallel - Different Entities)

- [ ] T019 [P] Dataset model with NWB file limit validation in
      agentic_neurodata_conversion/knowledge_graph/models/dataset.py
- [ ] T020 [P] Session model with temporal boundaries in
      agentic_neurodata_conversion/knowledge_graph/models/session.py
- [ ] T021 [P] Subject model with species mapping in
      agentic_neurodata_conversion/knowledge_graph/models/subject.py
- [ ] T022 [P] Device model with calibration tracking in
      agentic_neurodata_conversion/knowledge_graph/models/device.py
- [ ] T023 [P] Lab model with institutional affiliation in
      agentic_neurodata_conversion/knowledge_graph/models/lab.py
- [ ] T024 [P] Protocol model with validation criteria in
      agentic_neurodata_conversion/knowledge_graph/models/protocol.py
- [ ] T025 [P] KnowledgeGraph model with RDF compliance in
      agentic_neurodata_conversion/knowledge_graph/models/knowledge_graph.py
- [ ] T026 [P] EnrichmentSuggestion model with confidence scoring in
      agentic_neurodata_conversion/knowledge_graph/models/enrichment.py
- [ ] T027 [P] ValidationReport model with issue categorization in
      agentic_neurodata_conversion/knowledge_graph/models/validation.py
- [ ] T028 [P] SchemaVersion model with artifact tracking in
      agentic_neurodata_conversion/knowledge_graph/models/schema_version.py
- [ ] T029 [P] MCPTool model with protocol compliance in
      agentic_neurodata_conversion/knowledge_graph/models/mcp_tool.py

### Semantic Web Services (Sequential - Shared Dependencies)

- [ ] T030 LinkML schema processor service in
      agentic_neurodata_conversion/knowledge_graph/schema/processor.py
- [ ] T031 RDF triple store service with SPARQL endpoint in
      agentic_neurodata_conversion/knowledge_graph/services/triple_store.py
- [ ] T032 SHACL validation service with shape generation in
      agentic_neurodata_conversion/knowledge_graph/validation/shacl_validator.py
- [ ] T033 Metadata enrichment service with external sources in
      agentic_neurodata_conversion/knowledge_graph/enrichment/enrichment_engine.py
- [ ] T034 Ontology mapping service with confidence scoring in
      agentic_neurodata_conversion/knowledge_graph/ontology/mapper.py
- [ ] T035 SPARQL query optimization service in
      agentic_neurodata_conversion/knowledge_graph/sparql/query_optimizer.py
- [ ] T035a Query indexing strategy implementation in
      agentic_neurodata_conversion/knowledge_graph/sparql/indexing.py
- [ ] T035b Query plan analysis and optimization in
      agentic_neurodata_conversion/knowledge_graph/sparql/planner.py
- [ ] T035c Query result caching service in
      agentic_neurodata_conversion/knowledge_graph/sparql/cache.py

### Service Layer (Sequential - Core Business Logic)

**NOTE**: No direct API endpoints - all access through MCP tools per
constitutional requirement. Services provide business logic for MCP adapter.

- [ ] T036 SPARQL query service with tiered timeout (<200ms simple, <30s
      complex) in agentic_neurodata_conversion/knowledge_graph/sparql/query_service.py
- [ ] T037 Dataset management service in
      agentic_neurodata_conversion/knowledge_graph/services/dataset_service.py
- [ ] T038 Metadata enrichment service with human review workflow in
      agentic_neurodata_conversion/knowledge_graph/enrichment/enrichment_service.py
- [ ] T039 SHACL validation service in
      agentic_neurodata_conversion/knowledge_graph/validation/shacl_service.py
- [ ] T040 LinkML validation service in
      agentic_neurodata_conversion/knowledge_graph/validation/linkml_service.py

### CLI Commands (Parallel - Different Command Modules)

**NOTE**: CLI commands call MCP tools via local server instance, maintaining
constitutional MCP-centric architecture.

- [ ] T041 [P] CLI create-dataset command in
      agentic_neurodata_conversion/cli/dataset_commands.py (calls MCP tools
      locally)
- [ ] T042 [P] CLI validate-linkml command in
      agentic_neurodata_conversion/cli/validation_commands.py (calls MCP tools
      locally)
- [ ] T043 [P] CLI enrich-metadata command in
      agentic_neurodata_conversion/cli/enrichment_commands.py (calls MCP tools
      locally)
- [ ] T044 [P] CLI sparql-query command in
      agentic_neurodata_conversion/cli/query_commands.py (calls MCP tools
      locally)
- [ ] T045 [P] CLI review-suggestions command in
      agentic_neurodata_conversion/cli/review_commands.py (calls MCP tools
      locally)

## Phase 3.4: Integration

### MCP Agent SDK Integration (Sequential - Constitutional Compliance)

**CONSTITUTIONAL REQUIREMENT**: All MCP integration MUST use Claude Agent SDK
(Constitution Principle I). Transport adapters MUST be thin (<500 LOC) with ZERO
business logic.

- [ ] T046 Register knowledge graph tools with Claude Agent SDK in
      agentic_neurodata_conversion/mcp_server/tools/kg_tools.py (thin adapter
      <500 LOC)
- [ ] T047 MCP tool registration: sparql_query using @mcp.tool decorator,
      delegates to knowledge_graph.sparql service
- [ ] T048 MCP tool registration: enrich_metadata using @mcp.tool decorator,
      delegates to knowledge_graph.enrichment service
- [ ] T049 MCP tool registration: validate_schema using @mcp.tool decorator,
      delegates to knowledge_graph.validation service
- [ ] T050 MCP tool registration: resolve_conflicts using @mcp.tool decorator,
      delegates to knowledge_graph.enrichment.conflict_resolver service
- [ ] T051 MCP tool registration: generate_rdf using @mcp.tool decorator,
      delegates to knowledge_graph.schema.rdf_generator service
- [ ] T052 MCP tool registration: query_ontology using @mcp.tool decorator,
      delegates to knowledge_graph.ontology service
- [ ] T052a Verify adapter LOC <500 and contains ZERO business logic (only
      parameter mapping and service delegation)

### Ontology and Provenance Integration

- [ ] T053 NIFSTD ontology integration with concept mapping in
      agentic_neurodata_conversion/knowledge_graph/ontology/nifstd.py
- [ ] T054 NCBITaxon species mapping with confidence scoring in
      agentic_neurodata_conversion/knowledge_graph/ontology/ncbi_taxon.py
- [ ] T055 UBERON anatomy mapping integration in
      agentic_neurodata_conversion/knowledge_graph/ontology/uberon.py
- [ ] T056 CHEBI chemical entity mapping in
      agentic_neurodata_conversion/knowledge_graph/ontology/chebi.py
- [ ] T057 PROV-O provenance tracking implementation in
      agentic_neurodata_conversion/knowledge_graph/provenance/prov_tracker.py

### Quality Assurance and Performance

- [ ] T058 Quality scoring service with configurable thresholds in
      agentic_neurodata_conversion/knowledge_graph/quality/scorer.py
- [ ] T059 Evidence trail validation service in
      agentic_neurodata_conversion/knowledge_graph/quality/evidence_validator.py
- [ ] T060 Query performance optimization with indexing in
      agentic_neurodata_conversion/knowledge_graph/sparql/performance.py
- [ ] T060a Runtime schema discovery service in
      agentic_neurodata_conversion/knowledge_graph/schema/discovery.py
- [ ] T060b Dynamic entity type detection in
      agentic_neurodata_conversion/knowledge_graph/schema/entity_detector.py
- [ ] T060c Property analysis and inference engine in
      agentic_neurodata_conversion/knowledge_graph/schema/property_inferrer.py
- [ ] T061 Concurrent access handling for 1-10 users in
      agentic_neurodata_conversion/knowledge_graph/services/concurrency.py

## Phase 3.5: Polish

### Unit Tests (Parallel - Different Test Modules)

- [ ] T062 [P] Unit tests for LinkML schema processing in
      tests/unit/test_linkml_processing.py
- [ ] T063 [P] Unit tests for RDF generation and validation in
      tests/unit/test_rdf_generation.py
- [ ] T064 [P] Unit tests for SHACL shape generation in
      tests/unit/test_shacl_shapes.py
- [ ] T065 [P] Unit tests for ontology mapping confidence in
      tests/unit/test_ontology_mapping.py
- [ ] T066 [P] Unit tests for provenance tracking in
      tests/unit/test_provenance_tracking.py
- [ ] T067 [P] Unit tests for enrichment suggestion generation in
      tests/unit/test_enrichment_suggestions.py
- [ ] T068 [P] Unit tests for conflict detection and resolution in
      tests/unit/test_conflict_resolution.py

### Performance and Benchmarking

- [ ] T069 Performance tests for 30-second query timeout in
      tests/performance/test_query_timeout.py
- [ ] T070 Load testing for 1-10 concurrent users in
      tests/performance/test_concurrent_load.py
- [ ] T070a Load testing concurrent writes with consistency verification
      (detect race conditions, validate conflict detection per FR-003) in
      tests/performance/test_concurrent_consistency.py (covers spec.md Edge
      Case 4)
- [ ] T071 Scale testing for 100 NWB files per dataset in
      tests/performance/test_dataset_scale.py

### Coverage Gates and Quality Verification (Constitutional Requirement)

**CONSTITUTIONAL REQUIREMENT** (Principle II): Critical paths ≥90%, Standard features ≥85%

- [ ] T072 Identify critical path components (SPARQL engine, validation,
      enrichment core) in tests/critical_paths.md
- [ ] T073 Verify critical path coverage ≥90%: pixi run pytest --cov
      --cov-fail-under=90 tests/unit/test_sparql_*.py
      tests/unit/test_validation_*.py tests/unit/test_enrichment_core.py
- [ ] T074 Verify standard feature coverage ≥85%: pixi run pytest --cov
      --cov-fail-under=85 agentic_neurodata_conversion/knowledge_graph/
- [ ] T075 Generate comprehensive coverage report: pixi run test-cov
- [ ] T076 Review uncovered lines and add tests for gaps >85% threshold
- [ ] T077 Verify cyclomatic complexity <10 for all functions: pixi run ruff
      check --select C901

### Documentation and Configuration

- [ ] T078 [P] Update API documentation with OpenAPI specs in docs/api.md
- [ ] T079 [P] Create deployment configuration for containerized environment in
      config/deployment.yaml
- [ ] T080 [P] Update constitutional compliance verification in
      docs/constitutional_compliance.md

### Final Validation

- [ ] T081 Run complete integration test suite from quickstart.md scenarios
- [ ] T082 Validate W3C semantic web standards compliance (RDF, SPARQL, SHACL)
- [ ] T083 Constitutional compliance audit for all components (all 7 principles)
- [ ] T084 Verify MCP adapter LOC <500 with zero business logic
- [ ] T085 Run full pre-commit hooks: pixi run pre-commit run --all-files
- [ ] T086 Final coverage report verification with quality gates passing

## Dependencies

**Critical Path**:

- Setup (T001-T005) before everything
- Contract tests (T006-T011) before implementation (T019-T061)
- Models (T019-T029) before services (T030-T035)
- Services before endpoints (T036-T040)
- Core implementation before MCP integration (T046-T052)
- Integration before polish (T062-T077)

**Parallel Execution Blockers**:

- T030-T035: Sequential (shared service dependencies)
- T036-T040: Sequential (shared FastAPI app)
- T046-T052: Sequential (shared MCP server)

## Parallel Example

```bash
# Launch contract tests together (Phase 3.2):
Task: "Contract test POST /sparql endpoint in tests/contract/test_sparql_endpoints.py"
Task: "Contract test POST /datasets endpoint in tests/contract/test_datasets_api.py"
Task: "Contract test POST /datasets/{id}/enrich endpoint in tests/contract/test_enrichment_api.py"
Task: "Contract test POST /validation/shacl endpoint in tests/contract/test_shacl_validation.py"
Task: "Contract test POST /validation/linkml endpoint in tests/contract/test_linkml_validation.py"
Task: "Contract test MCP tools in tests/contract/test_mcp_tools.py"

# Launch model creation together (Phase 3.3):
Task: "Dataset model with NWB file limit validation in agentic_neurodata_conversion/knowledge_graph/models/dataset.py"
Task: "Session model with temporal boundaries in agentic_neurodata_conversion/knowledge_graph/models/session.py"
Task: "Subject model with species mapping in agentic_neurodata_conversion/knowledge_graph/models/subject.py"
Task: "Device model with calibration tracking in agentic_neurodata_conversion/knowledge_graph/models/device.py"
```

## Notes

- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task for constitutional compliance
- All tasks must maintain W3C semantic web standards
- Human review required for all enrichment suggestions (constitutional
  requirement)

## Task Generation Rules

_Applied during main() execution_

1. **From Contracts**:
   - knowledge-graph-api.yaml → 5 contract test tasks [P]
   - mcp-integration.yaml → 1 MCP contract test task [P]
   - Each endpoint → implementation task

2. **From Data Model**:
   - 11 entities → 11 model creation tasks [P]
   - Relationships → service layer tasks

3. **From User Stories**:
   - 5 quickstart scenarios → 5 integration tests [P]
   - Constitutional requirements → compliance validation tasks

4. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist

_GATE: Checked by main() before completion_

- [x] All contracts have corresponding tests
- [x] All entities have model tasks with LinkML compliance
- [x] All tests come before implementation (TDD)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Constitutional compliance verified for semantic web standards
- [x] W3C RDF, SPARQL, SHACL standards maintained throughout
- [x] Human review workflow preserved for all enrichment operations
