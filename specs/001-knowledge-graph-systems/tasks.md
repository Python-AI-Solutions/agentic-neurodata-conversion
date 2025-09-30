# Tasks: Knowledge Graph Systems

**Input**: Design documents from `/Users/adityapatane/agentic-neurodata-conversion-3/specs/001-knowledge-graph-systems/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)

```
1. Load plan.md from feature directory
   → ✅ Found implementation plan with Python 3.12+, semantic web stack
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

- [x] T001 Create knowledge graph project structure per implementation plan in src/knowledge_graph/
- [x] T002 Initialize Python 3.12+ project with semantic web dependencies (rdflib, linkml, pyshacl, fastapi, mcp)
- [x] T003 [P] Configure linting and formatting tools (ruff, mypy) for constitutional compliance
- [x] T004 [P] Set up LinkML schema processing pipeline in src/knowledge_graph/schema/
- [x] T005 [P] Configure SHACL validation framework with pyshacl in src/knowledge_graph/validation/

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (Parallel - Different Files)

- [ ] T006 [P] Contract test POST /sparql endpoint in tests/contract/test_sparql_endpoints.py
- [ ] T007 [P] Contract test POST /datasets endpoint in tests/contract/test_datasets_api.py
- [ ] T008 [P] Contract test POST /datasets/{id}/enrich endpoint in tests/contract/test_enrichment_api.py
- [ ] T009 [P] Contract test POST /validation/shacl endpoint in tests/contract/test_shacl_validation.py
- [ ] T010 [P] Contract test POST /validation/linkml endpoint in tests/contract/test_linkml_validation.py
- [ ] T011 [P] Contract test MCP tools in tests/contract/test_mcp_tools.py

### Integration Tests (Parallel - Different Scenarios)

- [ ] T012 [P] Integration test dataset creation and enrichment workflow in tests/integration/test_enrichment_workflow.py
- [ ] T013 [P] Integration test SPARQL query execution with 30-second timeout in tests/integration/test_sparql_execution.py
- [ ] T014 [P] Integration test schema validation and artifact regeneration in tests/integration/test_schema_validation.py
- [ ] T015 [P] Integration test ontology mapping with confidence scoring in tests/integration/test_ontology_mapping.py
- [ ] T016 [P] Integration test human review workflow for enrichment suggestions in tests/integration/test_human_review.py
- [ ] T017 [P] Integration test conflict resolution for competing suggestions in tests/integration/test_conflict_resolution.py
- [ ] T018 [P] Integration test provenance tracking using PROV-O in tests/integration/test_provenance_tracking.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### LinkML Schema and Models (Parallel - Different Entities)

- [ ] T019 [P] Dataset model with NWB file limit validation in src/knowledge_graph/models/dataset.py
- [ ] T020 [P] Session model with temporal boundaries in src/knowledge_graph/models/session.py
- [ ] T021 [P] Subject model with species mapping in src/knowledge_graph/models/subject.py
- [ ] T022 [P] Device model with calibration tracking in src/knowledge_graph/models/device.py
- [ ] T023 [P] Lab model with institutional affiliation in src/knowledge_graph/models/lab.py
- [ ] T024 [P] Protocol model with validation criteria in src/knowledge_graph/models/protocol.py
- [ ] T025 [P] KnowledgeGraph model with RDF compliance in src/knowledge_graph/models/knowledge_graph.py
- [ ] T026 [P] EnrichmentSuggestion model with confidence scoring in src/knowledge_graph/models/enrichment.py
- [ ] T027 [P] ValidationReport model with issue categorization in src/knowledge_graph/models/validation.py
- [ ] T028 [P] SchemaVersion model with artifact tracking in src/knowledge_graph/models/schema_version.py
- [ ] T029 [P] MCPTool model with protocol compliance in src/knowledge_graph/models/mcp_tool.py

### Semantic Web Services (Sequential - Shared Dependencies)

- [ ] T030 LinkML schema processor service in src/knowledge_graph/schema/processor.py
- [ ] T031 RDF triple store service with SPARQL endpoint in src/knowledge_graph/services/triple_store.py
- [ ] T032 SHACL validation service with shape generation in src/knowledge_graph/validation/shacl_validator.py
- [ ] T033 Metadata enrichment service with external sources in src/knowledge_graph/enrichment/enrichment_engine.py
- [ ] T034 Ontology mapping service with confidence scoring in src/knowledge_graph/ontology/mapper.py
- [ ] T035 SPARQL query optimization service in src/knowledge_graph/sparql/query_optimizer.py
- [ ] T035a Query indexing strategy implementation in src/knowledge_graph/sparql/indexing.py
- [ ] T035b Query plan analysis and optimization in src/knowledge_graph/sparql/planner.py
- [ ] T035c Query result caching service in src/knowledge_graph/sparql/cache.py

### API Endpoints (Sequential - Shared FastAPI App)

- [ ] T036 POST /sparql endpoint with tiered timeout per constitutional requirements (<200ms simple, <30s complex) in src/knowledge_graph/api/sparql.py
- [ ] T037 POST /datasets and GET /datasets endpoints in src/knowledge_graph/api/datasets.py
- [ ] T038 POST /datasets/{id}/enrich endpoint with human review in src/knowledge_graph/api/enrichment.py
- [ ] T039 POST /validation/shacl endpoint in src/knowledge_graph/api/validation.py
- [ ] T040 POST /validation/linkml endpoint in src/knowledge_graph/api/linkml.py

### CLI Commands (Parallel - Different Command Modules)

- [ ] T041 [P] CLI create-dataset command in src/cli/dataset_commands.py
- [ ] T042 [P] CLI validate-linkml command in src/cli/validation_commands.py
- [ ] T043 [P] CLI enrich-metadata command in src/cli/enrichment_commands.py
- [ ] T044 [P] CLI sparql-query command in src/cli/query_commands.py
- [ ] T045 [P] CLI review-suggestions command in src/cli/review_commands.py

## Phase 3.4: Integration

### MCP Server Integration (Sequential - Shared MCP App)

- [ ] T046 MCP server setup with FastAPI backend in src/mcp_server/knowledge_graph_server.py
- [ ] T047 MCP tool sparql_query implementation in src/knowledge_graph/mcp_tools/sparql_tool.py
- [ ] T048 MCP tool enrich_metadata implementation in src/knowledge_graph/mcp_tools/enrichment_tool.py
- [ ] T049 MCP tool validate_schema implementation in src/knowledge_graph/mcp_tools/validation_tool.py
- [ ] T050 MCP tool resolve_conflicts implementation in src/knowledge_graph/mcp_tools/conflict_tool.py
- [ ] T051 MCP tool generate_rdf implementation in src/knowledge_graph/mcp_tools/rdf_tool.py
- [ ] T052 MCP tool query_ontology implementation in src/knowledge_graph/mcp_tools/ontology_tool.py

### Ontology and Provenance Integration

- [ ] T053 NIFSTD ontology integration with concept mapping in src/knowledge_graph/ontology/nifstd.py
- [ ] T054 NCBITaxon species mapping with confidence scoring in src/knowledge_graph/ontology/ncbi_taxon.py
- [ ] T055 UBERON anatomy mapping integration in src/knowledge_graph/ontology/uberon.py
- [ ] T056 CHEBI chemical entity mapping in src/knowledge_graph/ontology/chebi.py
- [ ] T057 PROV-O provenance tracking implementation in src/knowledge_graph/provenance/prov_tracker.py

### Quality Assurance and Performance

- [ ] T058 Quality scoring service with configurable thresholds in src/knowledge_graph/quality/scorer.py
- [ ] T059 Evidence trail validation service in src/knowledge_graph/quality/evidence_validator.py
- [ ] T060 Query performance optimization with indexing in src/knowledge_graph/sparql/performance.py
- [ ] T060a Runtime schema discovery service in src/knowledge_graph/schema/discovery.py
- [ ] T060b Dynamic entity type detection in src/knowledge_graph/schema/entity_detector.py
- [ ] T060c Property analysis and inference engine in src/knowledge_graph/schema/property_inferrer.py
- [ ] T061 Concurrent access handling for 1-10 users in src/knowledge_graph/services/concurrency.py

## Phase 3.5: Polish

### Unit Tests (Parallel - Different Test Modules)

- [ ] T062 [P] Unit tests for LinkML schema processing in tests/unit/test_linkml_processing.py
- [ ] T063 [P] Unit tests for RDF generation and validation in tests/unit/test_rdf_generation.py
- [ ] T064 [P] Unit tests for SHACL shape generation in tests/unit/test_shacl_shapes.py
- [ ] T065 [P] Unit tests for ontology mapping confidence in tests/unit/test_ontology_mapping.py
- [ ] T066 [P] Unit tests for provenance tracking in tests/unit/test_provenance_tracking.py
- [ ] T067 [P] Unit tests for enrichment suggestion generation in tests/unit/test_enrichment_suggestions.py
- [ ] T068 [P] Unit tests for conflict detection and resolution in tests/unit/test_conflict_resolution.py

### Performance and Benchmarking

- [ ] T069 Performance tests for 30-second query timeout in tests/performance/test_query_timeout.py
- [ ] T070 Load testing for 1-10 concurrent users in tests/performance/test_concurrent_load.py
- [ ] T071 Scale testing for 100 NWB files per dataset in tests/performance/test_dataset_scale.py

### Documentation and Configuration

- [ ] T072 [P] Update API documentation with OpenAPI specs in docs/api.md
- [ ] T073 [P] Create deployment configuration for containerized environment in config/deployment.yaml
- [ ] T074 [P] Update constitutional compliance verification in docs/constitutional_compliance.md

### Final Validation

- [ ] T075 Run complete integration test suite from quickstart.md scenarios
- [ ] T076 Validate W3C semantic web standards compliance
- [ ] T077 Constitutional compliance audit for all components

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
Task: "Dataset model with NWB file limit validation in src/knowledge_graph/models/dataset.py"
Task: "Session model with temporal boundaries in src/knowledge_graph/models/session.py"
Task: "Subject model with species mapping in src/knowledge_graph/models/subject.py"
Task: "Device model with calibration tracking in src/knowledge_graph/models/device.py"
```

## Notes

- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task for constitutional compliance
- All tasks must maintain W3C semantic web standards
- Human review required for all enrichment suggestions (constitutional requirement)

## Task Generation Rules

*Applied during main() execution*

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

*GATE: Checked by main() before completion*

- [X] All contracts have corresponding tests
- [X] All entities have model tasks with LinkML compliance
- [X] All tests come before implementation (TDD)
- [X] Parallel tasks truly independent (different files)
- [X] Each task specifies exact file path
- [X] No task modifies same file as another [P] task
- [X] Constitutional compliance verified for semantic web standards
- [X] W3C RDF, SPARQL, SHACL standards maintained throughout
- [X] Human review workflow preserved for all enrichment operations
