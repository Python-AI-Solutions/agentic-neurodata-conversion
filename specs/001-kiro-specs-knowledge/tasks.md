# Tasks: Knowledge Graph Systems for Agentic Neurodata Conversion

**Input**: Design documents from `/specs/001-kiro-specs-knowledge/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Found: Python 3.12+, rdflib, linkml, pynwb, fastapi, mcp
   → Structure: single project (knowledge graph service within MCP)
2. Load optional design documents:
   → data-model.md: Found 6 entities (KnowledgeGraph, Entity, EnrichmentSuggestion, etc.)
   → contracts/: Found knowledge_graph_api.yaml with 5 endpoints
   → research.md: Found technology decisions for RDF, SPARQL, ontology integration
3. Generate tasks by category:
   → Setup: 3 tasks (project structure, dependencies, linting)
   → Tests: 8 tasks (contract tests + integration scenarios)
   → Core: 12 tasks (models, services, MCP tools)
   → Integration: 4 tasks (RDF store, SPARQL engine, ontology loading)
   → Polish: 5 tasks (performance, validation, docs)
4. Apply task rules:
   → Different files marked [P] for parallel execution
   → Tests before implementation (TDD enforced)
   → Models before services dependency order
5. Number tasks sequentially (T001-T032)
6. Generate dependency graph and parallel execution examples
7. Validate task completeness: ✓ All contracts tested, all entities modeled
8. Return: SUCCESS (32 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
Single project structure at repository root:
- **Source**: `agentic_neurodata_conversion/knowledge_graph/`
- **Tests**: `tests/knowledge_graph/`

## Phase 3.1: Setup
- [ ] T001 Create knowledge graph module structure in `agentic_neurodata_conversion/knowledge_graph/`
- [ ] T002 Add knowledge graph dependencies to pixi.toml (rdflib>=7.1.4, owlready2, pyshacl)
- [ ] T003 [P] Configure knowledge graph linting rules in pyproject.toml

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (API Endpoints)
- [ ] T004 [P] Contract test POST /knowledge-graphs in `tests/knowledge_graph/contract/test_create_graph.py`
- [ ] T005 [P] Contract test GET /knowledge-graphs in `tests/knowledge_graph/contract/test_list_graphs.py`
- [ ] T006 [P] Contract test GET /knowledge-graphs/{id} in `tests/knowledge_graph/contract/test_get_graph.py`
- [ ] T007 [P] Contract test POST /knowledge-graphs/{id}/sparql in `tests/knowledge_graph/contract/test_sparql_query.py`
- [ ] T008 [P] Contract test POST /knowledge-graphs/{id}/enrich in `tests/knowledge_graph/contract/test_enrich_metadata.py`
- [ ] T009 [P] Contract test POST /knowledge-graphs/{id}/validate in `tests/knowledge_graph/contract/test_validate_graph.py`

### Integration Tests (User Scenarios)
- [ ] T010 [P] Integration test NWB to knowledge graph pipeline in `tests/knowledge_graph/integration/test_nwb_pipeline.py`
- [ ] T011 [P] Integration test metadata enrichment workflow in `tests/knowledge_graph/integration/test_enrichment_workflow.py`

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models
- [ ] T012 [P] KnowledgeGraph model in `agentic_neurodata_conversion/knowledge_graph/models/knowledge_graph.py`
- [ ] T013 [P] Entity model in `agentic_neurodata_conversion/knowledge_graph/models/entity.py`
- [ ] T014 [P] EnrichmentSuggestion model in `agentic_neurodata_conversion/knowledge_graph/models/enrichment.py`
- [ ] T015 [P] SemanticRelation model in `agentic_neurodata_conversion/knowledge_graph/models/relation.py`
- [ ] T016 [P] SchemaArtifact model in `agentic_neurodata_conversion/knowledge_graph/models/schema_artifact.py`
- [ ] T017 [P] Provenance model in `agentic_neurodata_conversion/knowledge_graph/models/provenance.py`

### Core Services
- [ ] T018 RDF store service in `agentic_neurodata_conversion/knowledge_graph/services/rdf_store.py`
- [ ] T019 NWB-LinkML schema processor in `agentic_neurodata_conversion/knowledge_graph/services/schema_processor.py`
- [ ] T020 SPARQL query engine in `agentic_neurodata_conversion/knowledge_graph/services/sparql_engine.py`
- [ ] T021 Metadata enrichment service in `agentic_neurodata_conversion/knowledge_graph/services/enrichment_service.py`
- [ ] T022 Ontology integration service in `agentic_neurodata_conversion/knowledge_graph/services/ontology_service.py`
- [ ] T023 SHACL validation service in `agentic_neurodata_conversion/knowledge_graph/services/validation_service.py`

### MCP Tool Integration
- [ ] T024 Knowledge graph MCP tools in `agentic_neurodata_conversion/knowledge_graph/mcp_tools.py`
- [ ] T025 Knowledge graph API endpoints in `agentic_neurodata_conversion/knowledge_graph/api.py`

## Phase 3.4: Integration
- [ ] T026 Connect RDF store to persistent backend (SQLite/PostgreSQL)
- [ ] T027 Integrate ontology cache with external APIs (NIFSTD, UBERON, CHEBI, NCBITaxon)
- [ ] T028 Add concurrent access control with read-write locks
- [ ] T029 Configure SPARQL query optimization and indexing

## Phase 3.5: Polish
- [ ] T030 [P] Unit tests for conflict resolution in `tests/knowledge_graph/unit/test_conflict_resolution.py`
- [ ] T031 Performance tests (sub-second query response, 5-10 concurrent users)
- [ ] T032 [P] Update knowledge graph documentation in `docs/knowledge_graph.md`

## Dependencies
- Setup (T001-T003) before everything
- Contract tests (T004-T009) before models (T012-T017)
- Integration tests (T010-T011) before services (T018-T023)
- Models (T012-T017) before services (T018-T023)
- Services (T018-T023) before MCP integration (T024-T025)
- Core implementation before integration (T026-T029)
- Everything before polish (T030-T032)

## Parallel Execution Examples

### Setup Phase (can run together)
```bash
# T001-T003 sequential due to dependency on project structure
```

### Contract Tests Phase (all parallel)
```bash
# Launch T004-T009 together:
Task: "Contract test POST /knowledge-graphs in tests/knowledge_graph/contract/test_create_graph.py"
Task: "Contract test GET /knowledge-graphs in tests/knowledge_graph/contract/test_list_graphs.py"
Task: "Contract test GET /knowledge-graphs/{id} in tests/knowledge_graph/contract/test_get_graph.py"
Task: "Contract test POST /knowledge-graphs/{id}/sparql in tests/knowledge_graph/contract/test_sparql_query.py"
Task: "Contract test POST /knowledge-graphs/{id}/enrich in tests/knowledge_graph/contract/test_enrich_metadata.py"
Task: "Contract test POST /knowledge-graphs/{id}/validate in tests/knowledge_graph/contract/test_validate_graph.py"
```

### Integration Tests Phase (parallel)
```bash
# Launch T010-T011 together:
Task: "Integration test NWB to knowledge graph pipeline in tests/knowledge_graph/integration/test_nwb_pipeline.py"
Task: "Integration test metadata enrichment workflow in tests/knowledge_graph/integration/test_enrichment_workflow.py"
```

### Models Phase (all parallel)
```bash
# Launch T012-T017 together:
Task: "KnowledgeGraph model in agentic_neurodata_conversion/knowledge_graph/models/knowledge_graph.py"
Task: "Entity model in agentic_neurodata_conversion/knowledge_graph/models/entity.py"
Task: "EnrichmentSuggestion model in agentic_neurodata_conversion/knowledge_graph/models/enrichment.py"
Task: "SemanticRelation model in agentic_neurodata_conversion/knowledge_graph/models/relation.py"
Task: "SchemaArtifact model in agentic_neurodata_conversion/knowledge_graph/models/schema_artifact.py"
Task: "Provenance model in agentic_neurodata_conversion/knowledge_graph/models/provenance.py"
```

## Notes
- [P] tasks = different files, no shared dependencies
- Verify all contract and integration tests FAIL before implementing models/services
- Commit after completing each task
- Run `pixi run test-unit` to validate unit tests
- Run `pixi run test-integration` to validate integration scenarios
- Use confidence-based conflict resolution (clarification from spec)
- Maintain backward schema compatibility (clarification from spec)

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts** (knowledge_graph_api.yaml):
   - 6 endpoints → 6 contract test tasks [P] (T004-T009)
   - 6 endpoints → API implementation tasks (T025)

2. **From Data Model** (data-model.md):
   - 6 entities → 6 model creation tasks [P] (T012-T017)
   - Services derived from entity relationships (T018-T023)

3. **From User Stories** (spec.md scenarios):
   - NWB processing scenario → pipeline integration test (T010)
   - Metadata enrichment scenario → enrichment workflow test (T011)

4. **Ordering**:
   - Setup → Tests → Models → Services → MCP Integration → Integration → Polish
   - TDD enforced: All tests must fail before implementation

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T004-T009 cover all 6 endpoints)
- [x] All entities have model tasks (T012-T017 cover all 6 entities)
- [x] All tests come before implementation (T004-T011 before T012+)
- [x] Parallel tasks truly independent (different files, no shared state)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task