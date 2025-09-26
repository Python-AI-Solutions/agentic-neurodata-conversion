# Tasks: Knowledge Graph Systems

**Input**: Design documents from `/specs/002-knowledge-graph-systems/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✓ COMPLETE: Tech stack: Python 3.12+, rdflib, linkml, pynwb, fastapi, mcp
2. Load optional design documents:
   → ✓ data-model.md: 11 core entities extracted
   → ✓ contracts/: 2 contract files found (knowledge-graph-api, mcp-integration)
   → ✓ research.md: Technical decisions extracted
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: MCP server, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. ✓ COMPLETE: All contracts have tests, all entities have models
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure per plan.md

## Phase 3.1: Setup
- [ ] T001 Create project structure with src/ and tests/ directories per implementation plan
- [ ] T002 [P] Initialize Python package structure in src/agentic_neurodata_conversion/knowledge_graph/
- [ ] T003 [P] Configure pytest with knowledge graph specific test configuration in tests/
- [ ] T004 [P] Set up ruff linting configuration for knowledge graph module

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests
- [ ] T005 [P] Contract test for POST /enrich/metadata in tests/contract/test_enrich_metadata.py
- [ ] T006 [P] Contract test for GET /enrich/suggestions in tests/contract/test_enrich_suggestions.py
- [ ] T007 [P] Contract test for POST /validate/schema in tests/contract/test_validate_schema.py
- [ ] T008 [P] Contract test for POST /validate/shacl in tests/contract/test_validate_shacl.py
- [ ] T009 [P] Contract test for POST /query/sparql in tests/contract/test_query_sparql.py
- [ ] T010 [P] Contract test for GET /query/templates in tests/contract/test_query_templates.py
- [ ] T011 [P] Contract test for POST /generate/jsonld in tests/contract/test_generate_jsonld.py
- [ ] T012 [P] Contract test for POST /generate/ttl in tests/contract/test_generate_ttl.py
- [ ] T013 [P] Contract test for GET /schema/versions in tests/contract/test_schema_versions.py
- [ ] T014 [P] Contract test for POST /schema/artifacts in tests/contract/test_schema_artifacts.py
- [ ] T015 [P] Contract test for POST /quality/assess in tests/contract/test_quality_assess.py
- [ ] T016 [P] Contract test for GET /quality/reports/{dataset_id} in tests/contract/test_quality_reports.py

### MCP Integration Tests
- [ ] T017 [P] Contract test for MCP enrich-metadata tool in tests/contract/test_mcp_enrich_metadata.py
- [ ] T018 [P] Contract test for MCP validate-schema tool in tests/contract/test_mcp_validate_schema.py
- [ ] T019 [P] Contract test for MCP query-knowledge-graph tool in tests/contract/test_mcp_query_kg.py
- [ ] T020 [P] Contract test for MCP generate-rdf tool in tests/contract/test_mcp_generate_rdf.py
- [ ] T021 [P] Contract test for MCP assess-quality tool in tests/contract/test_mcp_assess_quality.py

### Integration Tests from Quickstart Scenarios
- [ ] T022 [P] Integration test for Scenario 1: Metadata Enrichment Workflow in tests/integration/test_metadata_enrichment.py
- [ ] T023 [P] Integration test for Scenario 2: Schema Validation Workflow in tests/integration/test_schema_validation.py
- [ ] T024 [P] Integration test for Scenario 3: SPARQL Query Workflow in tests/integration/test_sparql_queries.py
- [ ] T025 [P] Integration test for Scenario 4: Schema Update and Artifact Generation in tests/integration/test_schema_updates.py
- [ ] T026 [P] Integration test for End-to-End Metadata Enrichment in tests/integration/test_e2e_enrichment.py
- [ ] T027 [P] Integration test for External Service Integration in tests/integration/test_external_services.py
- [ ] T028 [P] Integration test for MCP Server Integration in tests/integration/test_mcp_integration.py
- [ ] T029 [P] Integration test for Performance and Scalability in tests/integration/test_performance.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models
- [ ] T030 [P] Dataset entity model in src/agentic_neurodata_conversion/knowledge_graph/models/dataset.py
- [ ] T031 [P] Session entity model in src/agentic_neurodata_conversion/knowledge_graph/models/session.py
- [ ] T032 [P] Subject entity model in src/agentic_neurodata_conversion/knowledge_graph/models/subject.py
- [ ] T033 [P] Device entity model in src/agentic_neurodata_conversion/knowledge_graph/models/device.py
- [ ] T034 [P] Lab entity model in src/agentic_neurodata_conversion/knowledge_graph/models/lab.py
- [ ] T035 [P] Protocol entity model in src/agentic_neurodata_conversion/knowledge_graph/models/protocol.py
- [ ] T036 [P] OntologyMapping entity model in src/agentic_neurodata_conversion/knowledge_graph/models/ontology_mapping.py
- [ ] T037 [P] QualityAssessment entity model in src/agentic_neurodata_conversion/knowledge_graph/models/quality_assessment.py
- [ ] T038 [P] SchemaVersion entity model in src/agentic_neurodata_conversion/knowledge_graph/models/schema_version.py
- [ ] T039 [P] EnrichmentEvidence entity model in src/agentic_neurodata_conversion/knowledge_graph/models/enrichment_evidence.py
- [ ] T040 [P] ProjectContext entity model in src/agentic_neurodata_conversion/knowledge_graph/models/project_context.py

### Core Services
- [ ] T041 RDF store service with rdflib integration in src/agentic_neurodata_conversion/knowledge_graph/services/rdf_store.py
- [ ] T042 Metadata enrichment service in src/agentic_neurodata_conversion/knowledge_graph/services/enrichment_service.py
- [ ] T043 SPARQL query service in src/agentic_neurodata_conversion/knowledge_graph/services/query_service.py
- [ ] T044 Schema validation service in src/agentic_neurodata_conversion/knowledge_graph/services/validation_service.py
- [ ] T045 Knowledge graph generation service in src/agentic_neurodata_conversion/knowledge_graph/services/generation_service.py
- [ ] T046 Quality assessment service in src/agentic_neurodata_conversion/knowledge_graph/services/quality_service.py
- [ ] T047 Ontology integration service in src/agentic_neurodata_conversion/knowledge_graph/services/ontology_service.py
- [ ] T048 Schema management service in src/agentic_neurodata_conversion/knowledge_graph/services/schema_service.py

### API Endpoints (FastAPI)
- [ ] T049 POST /enrich/metadata endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/enrich.py
- [ ] T050 GET /enrich/suggestions endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/enrich.py
- [ ] T051 POST /validate/schema endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/validate.py
- [ ] T052 POST /validate/shacl endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/validate.py
- [ ] T053 POST /query/sparql endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/query.py
- [ ] T054 GET /query/templates endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/query.py
- [ ] T055 POST /generate/jsonld endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/generate.py
- [ ] T056 POST /generate/ttl endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/generate.py
- [ ] T057 GET /schema/versions endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/schema.py
- [ ] T058 POST /schema/artifacts endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/schema.py
- [ ] T059 POST /quality/assess endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/quality.py
- [ ] T060 GET /quality/reports/{dataset_id} endpoint in src/agentic_neurodata_conversion/knowledge_graph/api/quality.py

### CLI Commands
- [ ] T061 [P] CLI command for metadata enrichment in src/agentic_neurodata_conversion/knowledge_graph/cli/enrich.py
- [ ] T062 [P] CLI command for schema validation in src/agentic_neurodata_conversion/knowledge_graph/cli/validate.py
- [ ] T063 [P] CLI command for SPARQL queries in src/agentic_neurodata_conversion/knowledge_graph/cli/query.py
- [ ] T064 [P] CLI command for RDF generation in src/agentic_neurodata_conversion/knowledge_graph/cli/generate.py
- [ ] T065 [P] CLI command for quality assessment in src/agentic_neurodata_conversion/knowledge_graph/cli/quality.py

## Phase 3.4: Integration

### MCP Server Integration
- [ ] T066 MCP server setup and configuration in src/agentic_neurodata_conversion/knowledge_graph/mcp/server.py
- [ ] T067 MCP tool for enrich-metadata in src/agentic_neurodata_conversion/knowledge_graph/mcp/tools/enrich_metadata.py
- [ ] T068 MCP tool for validate-schema in src/agentic_neurodata_conversion/knowledge_graph/mcp/tools/validate_schema.py
- [ ] T069 MCP tool for query-knowledge-graph in src/agentic_neurodata_conversion/knowledge_graph/mcp/tools/query_kg.py
- [ ] T070 MCP tool for generate-rdf in src/agentic_neurodata_conversion/knowledge_graph/mcp/tools/generate_rdf.py
- [ ] T071 MCP tool for assess-quality in src/agentic_neurodata_conversion/knowledge_graph/mcp/tools/assess_quality.py
- [ ] T072 MCP resource handlers for ontologies, schemas, templates in src/agentic_neurodata_conversion/knowledge_graph/mcp/resources.py
- [ ] T073 MCP prompt templates for enrichment and validation in src/agentic_neurodata_conversion/knowledge_graph/mcp/prompts.py

### External Integrations
- [ ] T074 External ontology service integration (NCBITaxon, NIFSTD) in src/agentic_neurodata_conversion/knowledge_graph/external/ontology_clients.py
- [ ] T075 NWB-LinkML schema loader and processor in src/agentic_neurodata_conversion/knowledge_graph/external/linkml_processor.py
- [ ] T076 PROV-O provenance tracking in src/agentic_neurodata_conversion/knowledge_graph/external/provenance.py

### Middleware and Infrastructure
- [ ] T077 Error handling and logging middleware in src/agentic_neurodata_conversion/knowledge_graph/middleware/error_handler.py
- [ ] T078 Request/response logging middleware in src/agentic_neurodata_conversion/knowledge_graph/middleware/logging.py
- [ ] T079 Performance monitoring and metrics in src/agentic_neurodata_conversion/knowledge_graph/middleware/metrics.py
- [ ] T080 Configuration management in src/agentic_neurodata_conversion/knowledge_graph/config.py

## Phase 3.5: Polish

### Unit Tests
- [ ] T081 [P] Unit tests for Dataset model in tests/unit/models/test_dataset.py
- [ ] T082 [P] Unit tests for enrichment service in tests/unit/services/test_enrichment_service.py
- [ ] T083 [P] Unit tests for query service in tests/unit/services/test_query_service.py
- [ ] T084 [P] Unit tests for validation service in tests/unit/services/test_validation_service.py
- [ ] T085 [P] Unit tests for ontology service in tests/unit/services/test_ontology_service.py
- [ ] T086 [P] Unit tests for CLI commands in tests/unit/cli/test_commands.py

### Performance and Quality
- [ ] T087 Performance optimization for SPARQL queries (sub-second requirement) in src/agentic_neurodata_conversion/knowledge_graph/services/query_service.py
- [ ] T088 Concurrent access testing (5-20 users) in tests/performance/test_concurrent_access.py
- [ ] T089 Memory usage optimization for medium datasets (10K-100K triples) in src/agentic_neurodata_conversion/knowledge_graph/services/rdf_store.py
- [ ] T090 [P] API documentation generation from OpenAPI specs in docs/api/
- [ ] T091 [P] Update CLAUDE.md with final implementation details

### Validation and Cleanup
- [ ] T092 Run comprehensive test suite to ensure all requirements met
- [ ] T093 Validate external service integration with fail-fast behavior
- [ ] T094 Performance benchmarking against requirements (5-20 concurrent users, sub-second queries)
- [ ] T095 Final code review and refactoring for maintainability

## Dependencies

### Critical Path
- **Setup** (T001-T004) → **Tests** (T005-T029) → **Models** (T030-T040) → **Services** (T041-T048) → **API** (T049-T060) → **Integration** (T066-T080) → **Polish** (T081-T095)

### Parallel Dependencies
- T030-T040 (Models) can run in parallel - different entity files
- T005-T029 (Tests) can run in parallel - different test files
- T061-T065 (CLI) can run in parallel - different command files
- T067-T073 (MCP Tools) depend on T066 (MCP Server)
- T081-T086 (Unit Tests) can run in parallel - different test files

### Service Dependencies
- T042 (Enrichment) depends on T041 (RDF Store) and T047 (Ontology)
- T043 (Query) depends on T041 (RDF Store)
- T044 (Validation) depends on T048 (Schema Management)
- T045 (Generation) depends on T041 (RDF Store) and T048 (Schema)
- T046 (Quality) depends on T044 (Validation)

## Parallel Example
```bash
# Launch T005-T016 (Contract Tests) together:
Task: "Contract test for POST /enrich/metadata in tests/contract/test_enrich_metadata.py"
Task: "Contract test for GET /enrich/suggestions in tests/contract/test_enrich_suggestions.py"
Task: "Contract test for POST /validate/schema in tests/contract/test_validate_schema.py"
Task: "Contract test for POST /validate/shacl in tests/contract/test_validate_shacl.py"
Task: "Contract test for POST /query/sparql in tests/contract/test_query_sparql.py"
```

```bash
# Launch T030-T040 (Entity Models) together:
Task: "Dataset entity model in src/agentic_neurodata_conversion/knowledge_graph/models/dataset.py"
Task: "Session entity model in src/agentic_neurodata_conversion/knowledge_graph/models/session.py"
Task: "Subject entity model in src/agentic_neurodata_conversion/knowledge_graph/models/subject.py"
Task: "Device entity model in src/agentic_neurodata_conversion/knowledge_graph/models/device.py"
Task: "Lab entity model in src/agentic_neurodata_conversion/knowledge_graph/models/lab.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing (TDD requirement)
- Commit after each major task completion
- Focus on fail-fast behavior for external service failures
- Maintain confidence-based conflict resolution throughout
- Performance targets: Sub-second SPARQL queries, 5-20 concurrent users
- All API responses must include proper provenance information

## Task Generation Rules Applied
*Applied during main() execution*

1. **From Contracts**:
   - knowledge-graph-api.yaml → 12 contract test tasks (T005-T016) [P]
   - mcp-integration.yaml → 5 MCP contract tests (T017-T021) [P]

2. **From Data Model**:
   - 11 core entities → 11 model creation tasks (T030-T040) [P]
   - Semantic relationships → service layer tasks (T041-T048)

3. **From Quickstart Scenarios**:
   - 4 main scenarios → 4 integration tests (T022-T025) [P]
   - 4 test suites → 4 additional integration tests (T026-T029) [P]

4. **From Technical Context**:
   - Python 3.12+ → Setup tasks (T001-T004)
   - FastAPI → API endpoint tasks (T049-T060)
   - MCP integration → MCP tool tasks (T066-T073)
   - CLI requirement → CLI command tasks (T061-T065)

## Validation Checklist
*GATE: Checked before task list completion*

- [x] All contracts have corresponding tests (T005-T021)
- [x] All entities have model tasks (T030-T040)
- [x] All tests come before implementation (T005-T029 before T030+)
- [x] Parallel tasks truly independent (different files, marked [P])
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Dependencies clearly documented
- [x] Performance requirements addressed (T087-T089)
- [x] TDD workflow enforced (tests before implementation)
- [x] All quickstart scenarios have integration tests