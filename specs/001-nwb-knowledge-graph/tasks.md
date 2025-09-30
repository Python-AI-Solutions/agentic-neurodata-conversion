# Tasks: NWB Knowledge Graph System

**Input**: Design documents from `/specs/001-nwb-knowledge-graph/`
**Prerequisites**: plan.md ✅, research.md ✅, spec.md ✅

## Execution Flow (main)
```
1. Load plan.md from feature directory ✅
   → Tech stack: Python 3.12+, 12 core dependencies
   → Structure: Single project (src/, tests/)
2. Load optional design documents:
   → research.md ✅: 6 technical decisions resolved
   → spec.md ✅: 69 functional requirements, 5 user scenarios
3. Generate tasks by category ✅
4. Apply task rules ✅
5. Number tasks sequentially ✅
6. Generate dependency graph ✅
7. Create parallel execution examples ✅
8. Validate task completeness ✅
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- All paths relative to `/Users/adityapatane/agentic-neurodata-conversion-3/`

---

## Phase 3.1: Setup & Infrastructure

- [X] **T001** Create project structure per implementation plan
  - Create `src/` directory for all modules
  - Create `tests/contract/`, `tests/integration/`, `tests/unit/` directories
  - Create `templates/` directory for HTML template
  - Create `examples/` directory for sample NWB files (optional)

- [X] **T002** Initialize Python project with dependencies
  - Create `pyproject.toml` or update `pixi.toml` with all dependencies from research.md
  - Core: pynwb>=2.5.0, h5py>=3.0, nwbinspector>=0.4.0, linkml-runtime>=1.5.0, linkml>=1.5.0, rdflib>=6.0, networkx>=3.0, jinja2>=3.0, pyyaml>=6.0, pydantic>=2.0, tqdm>=4.60, owlrl>=6.0
  - Dev: pytest>=7.0, pytest-cov, black, ruff, mypy
  - Run dependency installation and verify imports

- [X] **T003** [P] Configure code quality tools
  - Create `pyproject.toml` section for black, ruff, mypy
  - Create `.ruff.toml` with linting rules
  - Create `mypy.ini` with type checking configuration
  - Add pre-commit hooks (optional)

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (Module Interfaces)

- [X] **T004** [P] Contract test for nwb_loader module ✅ FAILING
  - File: `tests/contract/test_nwb_loader_contract.py`
  - Test: `load_nwb_file(path) -> NWBFile object`
  - Test: `validate_nwb_integrity(path) -> ValidationResult`
  - Assert: Returns correct object types, raises appropriate exceptions
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T005** [P] Contract test for inspector_runner module ✅ FAILING
  - File: `tests/contract/test_inspector_runner_contract.py`
  - Test: `run_inspection(nwbfile_path) -> InspectionResults`
  - Test: Results include severity categorization (critical, warning, info)
  - Assert: Returns structured results with all required fields
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T006** [P] Contract test for hierarchical_parser module ✅ FAILING
  - File: `tests/contract/test_hierarchical_parser_contract.py`
  - Test: `parse_hdf5_structure(nwbfile) -> HierarchyTree`
  - Test: Captures all metadata (groups, datasets, attributes, links)
  - Assert: Complete traversal, no data loss
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T007** [P] Contract test for linkml_schema_loader module ✅ FAILING
  - File: `tests/contract/test_linkml_schema_loader_contract.py`
  - Test: `load_official_schema(version) -> SchemaView`
  - Test: `validate_against_schema(instance, target_class) -> bool`
  - Assert: Schema loaded correctly, validation works
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T008** [P] Contract test for linkml_converter module ✅ FAILING
  - File: `tests/contract/test_linkml_converter_contract.py`
  - Test: `convert_nwb_to_linkml(nwbfile, schema) -> LinkMLInstances`
  - Test: Preserves all references and relationships
  - Assert: Output validates against official schema
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T009** [P] Contract test for ttl_generator module ✅ FAILING
  - File: `tests/contract/test_ttl_generator_contract.py`
  - Test: `generate_ttl(linkml_instances, schema) -> str (TTL content)`
  - Test: `generate_jsonld(ttl_content) -> str (JSON-LD content)`
  - Assert: Valid RDF/TTL, proper @context in JSON-LD
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T010** [P] Contract test for graph_constructor module ✅ FAILING
  - File: `tests/contract/test_graph_constructor_contract.py`
  - Test: `build_graph_from_ttl(ttl_content) -> KnowledgeGraph`
  - Test: `compute_graph_analytics(graph) -> GraphMetrics`
  - Assert: All triples preserved, analytics computed
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T011** [P] Contract test for report_generator module ✅ FAILING
  - File: `tests/contract/test_report_generator_contract.py`
  - Test: `generate_evaluation_report(inspection, hierarchy, metrics) -> Report`
  - Test: `export_report(report, format) -> file (JSON/HTML/TXT)`
  - Assert: All three formats generated correctly
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T012** [P] Contract test for html_generator module ✅ FAILING
  - File: `tests/contract/test_html_generator_contract.py`
  - Test: `generate_visualization(graph_jsonld, metadata) -> str (HTML)`
  - Test: HTML is self-contained, no external dependencies
  - Assert: Valid HTML5, embedded JSON parseable
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T013** [P] Contract test for visualization_engine module ✅ FAILING
  - File: `tests/contract/test_visualization_engine_contract.py`
  - Test: `compute_force_directed_layout(nodes, edges) -> LayoutData`
  - Test: `apply_visual_styling(graph, config) -> StyledGraph`
  - Assert: Layout converges, styling applied correctly
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T014** [P] Contract test for main CLI module ✅ FAILING
  - File: `tests/contract/test_main_cli_contract.py`
  - Test: CLI accepts NWB file path, outputs 10 files
  - Test: Exit codes (0=success, 1=error, 2=invalid input)
  - Assert: All outputs generated with correct naming
  - **VERIFIED FAILING** (no implementation yet)

### Integration Tests (End-to-End Workflows)

- [X] **T015** [P] Integration test: Valid NWB file processing ✅ FAILING
  - File: `tests/integration/test_complete_workflow.py`
  - Scenario: Process valid electrophysiology NWB file end-to-end
  - Assert: All 10 output files generated, evaluation report shows "PASS"
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T016** [P] Integration test: Knowledge graph generation ✅ FAILING
  - File: `tests/integration/test_knowledge_graph.py`
  - Scenario: Generate TTL and JSON-LD, validate with rdflib
  - Assert: Semantic fidelity maintained, SPARQL queries work
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T017** [P] Integration test: Interactive visualization ✅ FAILING
  - File: `tests/integration/test_visualization.py`
  - Scenario: Generate HTML, validate offline capability
  - Assert: HTML parses, no external resource requests, JSON embedded
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T018** [P] Integration test: Custom extensions handling ✅ FAILING
  - File: `tests/integration/test_custom_extensions.py`
  - Scenario: Process NWB file with custom extensions
  - Assert: Graceful degradation, extensions documented in report
  - **VERIFIED FAILING** (no implementation yet)

- [X] **T019** [P] Integration test: Large file performance ✅ FAILING
  - File: `tests/integration/test_performance.py`
  - Scenario: Process 1GB NWB file, measure time
  - Assert: Completes within 15 minutes, progress indicators work
  - **VERIFIED FAILING** (no implementation yet)

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Module Implementations (Priority Order)

- [ ] **T020** [P] Implement nwb_loader module
  - File: `src/nwb_loader.py`
  - Functions: `load_nwb_file()`, `validate_nwb_integrity()`
  - Use pynwb and h5py per research.md
  - Make T004 contract test PASS

- [ ] **T021** [P] Implement inspector_runner module
  - File: `src/inspector_runner.py`
  - Functions: `run_inspection()`, `categorize_results()`
  - Use nwbinspector programmatic API per research.md
  - Make T005 contract test PASS

- [ ] **T022** [P] Implement hierarchical_parser module
  - File: `src/hierarchical_parser.py`
  - Functions: `parse_hdf5_structure()`, `extract_metadata()`
  - Recursive HDF5 traversal with h5py
  - Make T006 contract test PASS

- [ ] **T023** Implement linkml_schema_loader module (blocks T024)
  - File: `src/linkml_schema_loader.py`
  - Functions: `load_official_schema()`, `validate_against_schema()`
  - Use linkml-runtime SchemaView per research.md
  - Make T007 contract test PASS

- [ ] **T024** Implement linkml_converter module (depends on T023)
  - File: `src/linkml_converter.py`
  - Functions: `convert_nwb_to_linkml()`, `preserve_references()`
  - Map NWB data to LinkML instances
  - Make T008 contract test PASS

- [ ] **T025** Implement ttl_generator module (depends on T024)
  - File: `src/ttl_generator.py`
  - Functions: `generate_ttl()`, `generate_jsonld()`
  - Use linkml RDFGenerator + rdflib per research.md
  - Make T009 contract test PASS

- [ ] **T026** Implement graph_constructor module (depends on T025)
  - File: `src/graph_constructor.py`
  - Functions: `build_graph_from_ttl()`, `compute_graph_analytics()`
  - Use rdflib for parsing, networkx for analytics
  - Make T010 contract test PASS

- [ ] **T027** [P] Implement visualization_engine module
  - File: `src/visualization_engine.py`
  - Functions: `compute_force_directed_layout()`, `apply_visual_styling()`
  - Implement Verlet integration force-directed layout per research.md
  - Make T013 contract test PASS

- [ ] **T028** Implement report_generator module (depends on T021, T022)
  - File: `src/report_generator.py`
  - Functions: `generate_evaluation_report()`, `export_report()`
  - Generate JSON, HTML, TXT formats
  - Make T011 contract test PASS

- [ ] **T029** Implement html_generator module (depends on T026, T027)
  - File: `src/html_generator.py`
  - Functions: `generate_visualization()`, `embed_graph_data()`
  - Use jinja2 templates per research.md
  - Make T012 contract test PASS

- [ ] **T030** Create HTML visualization template
  - File: `templates/visualization.html`
  - Vanilla JavaScript (ES6+), Canvas API
  - Implement pan/zoom, tooltips, search, filters
  - Self-contained, zero external dependencies

- [ ] **T031** Implement main CLI orchestration (depends on all modules)
  - File: `src/main.py`
  - Functions: CLI argument parsing, workflow orchestration
  - Use argparse, coordinate all modules, handle errors
  - Make T014 contract test PASS

---

## Phase 3.4: Integration & Configuration

- [ ] **T032** Implement configuration management
  - File: `src/config.py`
  - Use pydantic for validation per research.md
  - Support JSON/YAML config files
  - Handle all configuration options from FR-057 to FR-060

- [ ] **T033** Implement error severity handling
  - Update all modules with proper logging
  - Use Python logging module with custom severity levels per research.md
  - CRITICAL/ERROR/WARNING/INFO handling per FR-048

- [ ] **T034** Implement progress indicators
  - Add tqdm progress bars to all long-running operations
  - Per research.md: validation, inspection, conversion, graph generation
  - Update progress during processing per FR-045

- [ ] **T035** Add output file generation coordination
  - Ensure all 10 files generated per FR-050 to FR-056
  - Proper naming: `{filename}_evaluation_report.json`, etc.
  - Manual file management (no auto-cleanup) per FR-056a

---

## Phase 3.5: Polish & Validation

- [ ] **T036** [P] Unit tests for force-directed layout algorithm
  - File: `tests/unit/test_force_directed.py`
  - Test convergence, stability, performance
  - Verify layout quality for various graph sizes

- [ ] **T037** [P] Unit tests for LinkML to RDF conversion
  - File: `tests/unit/test_linkml_to_rdf.py`
  - Test namespace generation, triple correctness
  - Verify @context in JSON-LD

- [ ] **T038** [P] Unit tests for error handling
  - File: `tests/unit/test_error_handling.py`
  - Test all severity levels (CRITICAL, ERROR, WARNING, INFO)
  - Verify graceful degradation

- [ ] **T039** Run all integration tests
  - Execute T015-T019 integration test suite
  - Verify all scenarios pass
  - Check performance benchmarks (1GB in <15 min)

- [ ] **T040** Create quickstart.md validation guide
  - File: `specs/001-nwb-knowledge-graph/quickstart.md`
  - Step-by-step: Install → Process sample → Verify outputs
  - Include expected outputs and validation steps

- [ ] **T041** Performance optimization
  - Profile 1GB file processing
  - Optimize bottlenecks (likely: HDF5 reading, TTL generation)
  - Ensure 95% of 1GB files complete within 15 minutes

- [ ] **T042** [P] Documentation updates
  - Update `CLAUDE.md` with implementation details
  - Add docstrings to all public functions
  - Create usage examples

- [ ] **T043** Code quality review
  - Run black formatter on all Python files
  - Run ruff linter, fix all issues
  - Run mypy type checker, resolve type errors
  - Achieve ≥80% code coverage per NFR3.5

- [ ] **T044** Browser compatibility testing
  - Test HTML visualization in Chrome, Firefox, Safari, Edge
  - Verify offline capability (no network requests)
  - Test on desktop and tablet viewports

- [ ] **T045** Final validation with diverse NWB files
  - Test with ecephys, ophys, icephys, behavior file types
  - Test with files containing custom extensions
  - Test with 5GB file (max size limit)
  - Verify all 69 functional requirements met

---

## Dependencies

### Critical Path
```
T001-T003 (Setup)
  ↓
T004-T014 (Contract Tests) [ALL MUST BE WRITTEN FIRST]
  ↓
T015-T019 (Integration Tests) [ALL MUST BE WRITTEN FIRST]
  ↓
T020-T022 (Core Loaders) [P]
  ↓
T023 (Schema Loader)
  ↓
T024 (LinkML Converter)
  ↓
T025 (TTL Generator)
  ↓
T026 (Graph Constructor)
  ↓
T027 (Visualization Engine) [P with T028]
T028 (Report Generator)
  ↓
T029 (HTML Generator)
T030 (HTML Template)
  ↓
T031 (Main CLI)
  ↓
T032-T035 (Integration & Config)
  ↓
T036-T045 (Polish & Validation)
```

### Parallel Opportunities
- **T004-T014**: All contract tests (11 files, independent)
- **T015-T019**: All integration tests (5 files, independent)
- **T020-T022**: Core loaders (3 files, independent)
- **T027, T028**: Visualization engine + Report generator (independent)
- **T036-T038, T042**: Unit tests + docs (independent)

---

## Parallel Execution Examples

### Phase 3.2 - Write All Tests (Parallel)
```bash
# Launch contract tests together (T004-T014):
Task: "Contract test for nwb_loader in tests/contract/test_nwb_loader_contract.py"
Task: "Contract test for inspector_runner in tests/contract/test_inspector_runner_contract.py"
Task: "Contract test for hierarchical_parser in tests/contract/test_hierarchical_parser_contract.py"
# ... all 11 contract tests ...

# Then launch integration tests together (T015-T019):
Task: "Integration test for complete workflow in tests/integration/test_complete_workflow.py"
Task: "Integration test for knowledge graph in tests/integration/test_knowledge_graph.py"
# ... all 5 integration tests ...
```

### Phase 3.3 - Core Implementations (Parallel Where Possible)
```bash
# Launch independent modules together (T020-T022):
Task: "Implement nwb_loader in src/nwb_loader.py"
Task: "Implement inspector_runner in src/inspector_runner.py"
Task: "Implement hierarchical_parser in src/hierarchical_parser.py"
```

---

## Notes
- **TDD Mandatory**: All tests (T004-T019) must be written and failing before implementation (T020+)
- **[P] Tasks**: Can run in parallel (different files, no dependencies)
- **Commit Strategy**: Commit after each task completion
- **Test First**: Verify all tests fail before implementing
- **Performance**: Monitor processing time throughout development
- **Standards**: Use official NWB LinkML schema (no custom schemas)
- **Offline**: HTML visualization must work without network

---

## Validation Checklist
*GATE: Verify before marking complete*

- [x] All 11 contract tests have corresponding tasks (T004-T014)
- [x] All 8 core modules have implementation tasks (T020-T031)
- [x] All tests come before implementation (T004-T019 before T020-T031)
- [x] Parallel tasks are truly independent (verified file conflicts)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Dependency graph is correct and complete
- [x] 69 functional requirements covered by tasks
- [x] All 5 user scenarios have integration tests

---

**Total Tasks**: 45
**Estimated Duration**: 8-10 weeks (1 developer)
**Parallelizable**: 24 tasks marked [P]

**Status**: Ready for execution. Begin with T001 (Setup).