# Tasks: Data Management and Provenance

**Input**: Design documents from `/specs/data-management-and-provenance/`
**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ research.md, ✅ data-model.md, ✅
contracts/, ✅ quickstart.md

**Tests**: TDD approach required per Constitution Principle V (Non-Negotiable).
Tests MUST be written and approved before implementation.

**Organization**: Tasks grouped by user story to enable independent
implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/data_management/`, `tests/`
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] **T001** Create project structure per plan.md
      (src/data_management/{datalad,provenance,reporting},
      tests/{unit,integration,fixtures})
- [ ] **T002** Add dependencies to pyproject.toml: datalad, pyoxigraph>=0.4.0,
      oxrdflib>=0.3.0, jinja2>=3.1.0, plotly>=6.0.0, pyyaml
- [ ] **T003** [P] Create enumerations in
      src/data_management/provenance/confidence.py (ConfidenceLevel, SourceType,
      ResolutionMethod, ArtifactType, Severity enums)
- [ ] **T004** [P] Create conversions/ output directory with .gitkeep
- [ ] **T005** [P] Setup pytest configuration with DataLad fixtures support

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] **T006** Create base Pydantic models for all entities in
      src/data_management/models.py (DataLadDataset, ConversionRepository,
      ProvenanceRecord, EvidenceSource, etc. per data-model.md)
- [ ] **T007** Create .gitattributes template for DataLad annexing configuration
      (>10MB threshold, development files in git)
- [ ] **T008** [P] Create Jinja2 template directory structure:
      src/data_management/reporting/templates/ with base_report.html.j2
- [ ] **T009** [P] Create performance configuration schema in
      src/data_management/config.py (Pydantic models for PerformanceThresholds,
      PerformanceConfig per research.md)
- [ ] **T010** Initialize Oxigraph RDF store wrapper in
      src/data_management/provenance/rdf_store.py (implement connection, basic
      CRUD)

**Checkpoint**: Foundation ready - user story implementation can now begin in
parallel

---

## Phase 3: User Story 1 - Development Dataset Management (Priority: P1) 🎯 MVP

**Goal**: Developers can create, configure, and manage versioned test datasets
with DataLad, supporting selective file downloading and proper annexing (>10MB
threshold)

**Independent Test**: Set up a test dataset, selectively download files, run
conversion test, verify dataset is versioned and reproducible across
environments

### Tests for User Story 1 (TDD - Write First)

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] **T011** [P] [US1] Unit test for DatasetManager.create_dataset() in
      tests/unit/test_dataset_manager.py
- [ ] **T012** [P] [US1] Unit test for DatasetManager.configure_annex() in
      tests/unit/test_dataset_manager.py
- [ ] **T013** [P] [US1] Unit test for DatasetManager.install_subdataset() in
      tests/unit/test_dataset_manager.py
- [ ] **T014** [P] [US1] Unit test for DatasetManager.get_files() with selective
      downloading in tests/unit/test_dataset_manager.py
- [ ] **T015** [P] [US1] Integration test for complete dataset workflow in
      tests/integration/test_datalad_workflow.py (create → configure → add files
      → save)
- [ ] **T016** [P] [US1] Fixture: Create sample test dataset in
      tests/fixtures/datasets/sample_ephys/

### Implementation for User Story 1

- [ ] **T017** [US1] Implement DatasetManager class skeleton per contract in
      src/data_management/datalad/dataset_manager.py
- [ ] **T018** [US1] Implement create_dataset() method using DataLad Python API
      (datalad.api.create)
- [ ] **T019** [US1] Implement configure_annex() method to write .gitattributes
      with 10MB threshold and file type rules
- [ ] **T020** [US1] Implement install_subdataset() method using
      datalad.api.install with recursive and get_data parameters
- [ ] **T021** [US1] Implement get_files() method using datalad.api.get with
      selective file paths
- [ ] **T022** [US1] Implement get_status() method using datalad.api.status
- [ ] **T023** [US1] Implement save_changes() method using datalad.api.save with
      descriptive commit messages
- [ ] **T024** [US1] Implement unlock_files() method using datalad.api.unlock
      for file modification
- [ ] **T025** [US1] Add exception handling for common DataLad errors (missing
      subdatasets, locked files) per data-model.md

**Checkpoint**: User Story 1 complete - Developers can manage test datasets with
DataLad

---

## Phase 4: User Story 2 - Comprehensive Provenance Tracking (Priority: P1)

**Goal**: Researchers get complete transparency into metadata derivation with
confidence levels, sources, reasoning chains stored as RDF/PROV-O with SPARQL
queries

**Independent Test**: Run conversion, examine provenance for any metadata field,
verify confidence levels, sources, derivation methods, and reasoning chains are
documented in RDF format

### Tests for User Story 2 (TDD - Write First)

- [ ] **T026** [P] [US2] Unit test for ProvenanceTracker.start_activity() in
      tests/unit/test_provenance_tracker.py
- [ ] **T027** [P] [US2] Unit test for ProvenanceTracker.record_entity() in
      tests/unit/test_provenance_tracker.py
- [ ] **T028** [P] [US2] Unit test for ProvenanceTracker.record_agent() in
      tests/unit/test_provenance_tracker.py
- [ ] **T029** [P] [US2] Unit test for PROV-O relationship linking
      (wasGeneratedBy, used, wasAssociatedWith) in
      tests/unit/test_provenance_tracker.py
- [ ] **T030** [P] [US2] Unit test for record_metadata_provenance() convenience
      method in tests/unit/test_provenance_tracker.py
- [ ] **T031** [P] [US2] Unit test for query_sparql() in
      tests/unit/test_provenance_tracker.py
- [ ] **T032** [P] [US2] Unit test for RDFStore operations (save_graph, export)
      in tests/unit/test_rdf_store.py
- [ ] **T033** [P] [US2] Integration test for complete provenance workflow in
      tests/integration/test_provenance_workflow.py

### Implementation for User Story 2

- [ ] **T034** [P] [US2] Complete RDFStore implementation in
      src/data_management/provenance/rdf_store.py (Oxigraph persistence, SPARQL
      execution)
- [ ] **T035** [US2] Implement ProvenanceTracker class skeleton per contract in
      src/data_management/provenance/tracker.py
- [ ] **T036** [US2] Implement start_activity() and end_activity() methods (PROV
      Activity recording)
- [ ] **T037** [US2] Implement record_entity() method (PROV Entity recording)
- [ ] **T038** [US2] Implement record_agent() method (PROV Agent recording)
- [ ] **T039** [US2] Implement link_generation() method (prov:wasGeneratedBy)
- [ ] **T040** [US2] Implement link_usage() method (prov:used)
- [ ] **T041** [US2] Implement link_association() method
      (prov:wasAssociatedWith)
- [ ] **T042** [US2] Implement link_attribution() method (prov:wasAttributedTo)
- [ ] **T043** [US2] Implement link_derivation() method (prov:wasDerivedFrom)
- [ ] **T044** [US2] Implement record_metadata_provenance() convenience method
      combining entity/activity/agent recording
- [ ] **T045** [US2] Implement query_sparql() method delegating to RDFStore
- [ ] **T046** [US2] Implement get_entity_provenance() method with depth
      traversal
- [ ] **T047** [US2] Implement get_activity_provenance() method
- [ ] **T048** [US2] Implement export_graph() method (Turtle/RDF-XML/JSON-LD
      formats)
- [ ] **T049** [US2] Implement get_confidence_distribution() aggregation query

**Checkpoint**: User Story 2 complete - Provenance tracking with RDF/PROV-O and
SPARQL

---

## Phase 5: User Story 3 - Conversion Output Repository (Priority: P2)

**Goal**: Data managers get per-conversion DataLad repositories tracking
iterations, outputs, and history with tags for successful conversions

**Independent Test**: Run conversion, make iterative improvements, verify each
iteration committed with messages, successful conversions tagged, all artifacts
accessible

### Tests for User Story 3 (TDD - Write First)

- [ ] **T050** [P] [US3] Unit test for ConversionRepository.create() in
      tests/unit/test_conversion_repo.py
- [ ] **T051** [P] [US3] Unit test for ConversionRepository.save_iteration() in
      tests/unit/test_conversion_repo.py
- [ ] **T052** [P] [US3] Unit test for ConversionRepository.tag_success() in
      tests/unit/test_conversion_repo.py
- [ ] **T053** [P] [US3] Integration test for multi-iteration conversion
      workflow in tests/integration/test_conversion_iterations.py

### Implementation for User Story 3

- [ ] **T054** [US3] Implement ConversionRepository class in
      src/data_management/datalad/conversion_repo.py
- [ ] **T055** [US3] Implement create() class method to initialize DataLad repo
      in conversions/ directory with structured subdirectories (outputs/nwb/,
      scripts/, reports/, provenance/)
- [ ] **T056** [US3] Implement save_iteration() method using
      DatasetManager.save_changes() with iteration numbering
- [ ] **T057** [US3] Implement tag_success() method using
      DatasetManager.tag_version()
- [ ] **T058** [US3] Implement get_history() method to retrieve commit log
- [ ] **T059** [US3] Add artifact organization logic per data-model.md structure

**Checkpoint**: User Story 3 complete - Per-conversion repositories with version
control

---

## Phase 6: User Story 4 - Organized Output Structure (Priority: P2)

**Goal**: Researchers get organized conversion outputs with metadata,
validation/evaluation reports in structured directories, properly versioned

**Independent Test**: Complete conversion, verify outputs organized into clear
directories (NWB, scripts, reports, graphs) with proper versioning

### Tests for User Story 4 (TDD - Write First)

- [ ] **T060** [P] [US4] Unit test for artifact organization in
      ConversionRepository in tests/unit/test_conversion_repo.py
- [ ] **T061** [P] [US4] Integration test verifying output structure after
      conversion in tests/integration/test_output_organization.py

### Implementation for User Story 4

- [ ] **T062** [US4] Implement ConversionArtifact model tracking in
      src/data_management/models.py
- [ ] **T063** [US4] Add register_artifact() method to ConversionRepository for
      tracking artifacts by type
- [ ] **T064** [US4] Implement get_artifacts_by_type() method for artifact
      retrieval
- [ ] **T065** [US4] Add checksum verification for artifact integrity

**Checkpoint**: User Story 4 complete - Organized, versioned conversion outputs

---

## Phase 7: User Story 5 - Agent Integration Provenance (Priority: P3)

**Goal**: Researchers can track agent interactions, tool usage, and decision
points throughout MCP workflow in provenance

**Independent Test**: Run conversion with agent interactions, examine provenance
to verify agent decisions, tool calls, reasoning captured

### Tests for User Story 5 (TDD - Write First)

- [ ] **T066** [P] [US5] Unit test for agent interaction recording in
      tests/unit/test_provenance_tracker.py
- [ ] **T067** [P] [US5] Integration test for MCP workflow provenance in
      tests/integration/test_agent_provenance.py

### Implementation for User Story 5

- [ ] **T068** [US5] Extend ProvenanceTracker to record agent-specific metadata
      (tool_usage, decision_points)
- [ ] **T069** [US5] Implement record_tool_usage() method for capturing agent
      tool calls
- [ ] **T070** [US5] Implement record_decision_point() method for agent
      reasoning capture
- [ ] **T071** [US5] Add SPARQL queries for agent activity analysis

**Checkpoint**: User Story 5 complete - Agent interaction provenance

---

## Phase 8: User Story 6 - Performance Monitoring (Priority: P3)

**Goal**: System administrators can monitor conversion performance with
configurable thresholds, automated cleanup, and metrics logging

**Independent Test**: Run conversions, verify metrics logged, temporary files
cleaned up, large datasets handled with memory optimization

### Tests for User Story 6 (TDD - Write First)

- [ ] **T072** [P] [US6] Unit test for PerformanceMonitor.track_metric() in
      tests/unit/test_performance.py
- [ ] **T073** [P] [US6] Unit test for threshold checking and alert generation
      in tests/unit/test_performance.py
- [ ] **T074** [P] [US6] Unit test for configuration loading (YAML) in
      tests/unit/test_performance.py
- [ ] **T075** [P] [US6] Integration test for performance monitoring workflow in
      tests/integration/test_performance_monitoring.py

### Implementation for User Story 6

- [ ] **T076** [US6] Implement PerformanceMonitor class in
      src/utils/performance.py
- [ ] **T077** [US6] Implement track_metric() method recording throughput,
      storage, response times
- [ ] **T078** [US6] Implement check_thresholds() method comparing metrics
      against config
- [ ] **T079** [US6] Implement alert generation logic (PerformanceAlert
      creation)
- [ ] **T080** [US6] Add automated cleanup functionality for temporary files
- [ ] **T081** [US6] Implement basic duplicate detection for storage
      optimization
- [ ] **T082** [US6] Add chunked operation support for large dataset handling
- [ ] **T083** [US6] Create default performance.yaml configuration template

**Checkpoint**: User Story 6 complete - Performance monitoring and optimization

---

## Phase 9: HTML Report Generation (Cross-Cutting)

**Purpose**: Interactive HTML reports with Plotly visualizations for all user
stories

### Tests for Report Generation (TDD - Write First)

- [ ] **T084** [P] Unit test for ReportGenerator.initialize_report() in
      tests/unit/test_report_generator.py
- [ ] **T085** [P] Unit test for add_visualization() with Plotly in
      tests/unit/test_report_generator.py
- [ ] **T086** [P] Unit test for add_confidence_chart() in
      tests/unit/test_report_generator.py
- [ ] **T087** [P] Unit test for add_timeline_chart() in
      tests/unit/test_report_generator.py
- [ ] **T088** [P] Unit test for generate_html() with embedded assets in
      tests/unit/test_report_generator.py
- [ ] **T089** [P] Integration test for complete report generation in
      tests/integration/test_end_to_end.py

### Implementation for Report Generation

- [ ] **T090** [P] Create Jinja2 base template in
      src/data_management/reporting/templates/base_report.html.j2
- [ ] **T091** [P] Create provenance report template in
      src/data_management/reporting/templates/provenance_report.html.j2
- [ ] **T092** [P] Create CSS styles for accessibility (ARIA support) in
      src/data_management/reporting/templates/styles.css
- [ ] **T093** Implement ReportGenerator class skeleton per contract in
      src/data_management/reporting/html_generator.py
- [ ] **T094** Implement initialize_report() method with Jinja2 environment
      setup
- [ ] **T095** Implement add_section() method for section management
- [ ] **T096** Implement add_visualization() method wrapping Plotly chart
      generation
- [ ] **T097** Implement add_confidence_chart() convenience method using Plotly
      bar chart
- [ ] **T098** Implement add_timeline_chart() convenience method using Plotly
      timeline
- [ ] **T099** Implement add_decision_chain() method for reasoning chain
      visualization
- [ ] **T100** Implement add_evidence_summary() method with evidence table
      rendering
- [ ] **T101** Implement set_executive_summary() method
- [ ] **T102** Implement generate_html() method with asset embedding for offline
      use
- [ ] **T103** Implement validate_report() method checking completeness

**Checkpoint**: HTML report generation complete for all features

---

## Phase 10: Integration & Polish

**Purpose**: End-to-end testing and cross-cutting concerns

- [ ] **T104** [P] End-to-end test: Complete conversion workflow (US1 dataset →
      US2 provenance → US3 repo �� US4 organization → US6 monitoring → Report)
- [ ] **T105** [P] Create quickstart examples as executable scripts in examples/
      directory
- [ ] **T106** [P] Add docstrings to all public methods following Google style
- [ ] **T107** [P] Configure pre-commit hooks for linting (ruff/black)
- [ ] **T108** Create CHANGELOG.md documenting feature completion
- [ ] **T109** Update main README.md with data management section
- [ ] **T110** Review constitution compliance and document any deviations

**Final Checkpoint**: Data Management and Provenance feature complete

---

## Task Dependencies

### Critical Path (Sequential)

1. Phase 1 (Setup) → Phase 2 (Foundation) → **BLOCKING**
2. Phase 2 complete → Phase 3-8 (User Stories) can start in parallel
3. Phase 3-8 → Phase 9 (Reports) → Phase 10 (Integration)

### User Story Completion Order

- **MVP (Phase 3)**: US1 (Dataset Management) - Foundational for all testing
- **High Priority**: US2 (Provenance) - Core value proposition
- **Medium Priority**: US3 (Conversion Repos), US4 (Output Organization)
- **Low Priority**: US5 (Agent Integration), US6 (Performance Monitoring)

### Parallelization Opportunities

**Within Phase 2 (Foundation)**:

- T008 (Templates) || T009 (Config) || T010 (RDF Store)

**Within Phase 3 (US1)**:

- All test tasks T011-T016 can run in parallel
- After tests: T017-T025 are sequential (implement DatasetManager)

**Within Phase 4 (US2)**:

- All test tasks T026-T033 in parallel
- T034 (RDF Store) before T035-T049
- T035-T049 sequential (ProvenanceTracker methods)

**Within Phase 9 (Reports)**:

- T090-T092 (Templates/CSS) in parallel
- T084-T089 (Tests) in parallel
- T093-T103 sequential (ReportGenerator implementation)

**Within Phase 10 (Polish)**:

- T104-T108 all parallelizable

---

## Implementation Strategy

### MVP Delivery (Minimum Viable Product)

**Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1)

- **Value**: Developers can manage test datasets with DataLad
- **Estimate**: ~15-20 tasks (T001-T025)
- **Deliverable**: Working dataset management with tests

### Incremental Delivery

1. **Sprint 1**: MVP (US1) - Dataset management
2. **Sprint 2**: US2 (Provenance) - Core feature
3. **Sprint 3**: US3+US4 (Repos + Organization)
4. **Sprint 4**: US5+US6+Reports (Agent integration, monitoring, reports)
5. **Sprint 5**: Integration & Polish

### Testing Approach

- **TDD Required**: Per Constitution Principle V
- **Test Order**: Write tests → Approve → Watch fail → Implement → Pass
- **Coverage Target**: 90%+ for core functionality (US1, US2)
- **Integration Tests**: After each user story completion

---

## Summary

**Total Tasks**: 110

- Setup: 5 tasks
- Foundation: 5 tasks (blocking)
- US1 (P1): 15 tasks (9 tests + 9 implementation)
- US2 (P1): 24 tasks (8 tests + 16 implementation)
- US3 (P2): 10 tasks (4 tests + 6 implementation)
- US4 (P2): 6 tasks (2 tests + 4 implementation)
- US5 (P3): 6 tasks (2 tests + 4 implementation)
- US6 (P3): 12 tasks (4 tests + 8 implementation)
- Reports: 20 tasks (6 tests + 14 implementation)
- Polish: 7 tasks

**Parallel Opportunities**: 45+ tasks marked [P] **Test Tasks**: 39 (35% of
total - TDD approach) **MVP Tasks**: 25 (Phase 1 + Phase 2 + Phase 3)

**Independent Test Criteria Met**: ✅ Each user story has specific acceptance
tests and can be verified independently
