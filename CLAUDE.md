# agentic-neurodata-conversion-5 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-03

## Active Technologies

- Python 3.11+ + pixi (environment), pydantic-settings (config), FastAPI (MCP
  server), structlog (logging), pytest (testing), ruff (linting), mypy (type
  checking), DataLad (data management) (001-core-project-organization)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE
TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR
ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 001-core-project-organization: Added Python 3.11+ + pixi (environment),
  pydantic-settings (config), FastAPI (MCP server), structlog (logging), pytest
  (testing), ruff (linting), mypy (type checking), DataLad (data management)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

=== CLAUDE.MD FROM PR #29 (specfile_1_knowledge_graph_systems) ===

# agentic-neurodata-conversion-3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-29

## Active Technologies

- Python 3.12+ (based on existing pixi.toml configuration) + rdflib, linkml,
  pynwb, fastapi, mcp, SHACL validation libraries (001-knowledge-graph-systems)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE
TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR
ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+ (based on existing pixi.toml configuration): Follow standard
conventions

## Recent Changes

- 001-knowledge-graph-systems: Added Python 3.12+ (based on existing pixi.toml
  configuration) + rdflib, linkml, pynwb, fastapi, mcp, SHACL validation
  libraries

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

=== CLAUDE.MD FROM PR #30 (try1_speckit_eval_reporting) ===

# agentic-neurodata-conversion-6 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-03

## Active Technologies

- Python 3.11+ + nwb-inspector, pydantic, asyncio, Chart.js (for HTML reports),
  MCP SDK (001-eval-report)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE
TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR
ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 001-eval-report: Added Python 3.11+ + nwb-inspector, pydantic, asyncio,
  Chart.js (for HTML reports), MCP SDK

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

=== CLAUDE.MD FROM PR #32 (004-implement-an-agent) ===

# agentic-neurodata-conversion-3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-29

## Active Technologies

- Python 3.12+ (based on existing pixi.toml configuration) + rdflib, linkml,
  pynwb, fastapi, mcp, SHACL validation libraries (001-knowledge-graph-systems)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE
TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR
ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+ (based on existing pixi.toml configuration): Follow standard
conventions

## Recent Changes

- 001-knowledge-graph-systems: Added Python 3.12+ (based on existing pixi.toml
  configuration) + rdflib, linkml, pynwb, fastapi, mcp, SHACL validation
  libraries

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

=== CLAUDE.MD FROM PR #33 (006-mcp-server-architecture) ===

# agentic-neurodata-conversion-3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-29

## Active Technologies

- Python 3.12+ (based on existing pixi.toml configuration) + rdflib, linkml,
  pynwb, fastapi, mcp, SHACL validation libraries (001-knowledge-graph-systems)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE
TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR
ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+ (based on existing pixi.toml configuration): Follow standard
conventions

## Recent Changes

- 001-knowledge-graph-systems: Added Python 3.12+ (based on existing pixi.toml
  configuration) + rdflib, linkml, pynwb, fastapi, mcp, SHACL validation
  libraries

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

=== CLAUDE.MD FROM PR #34 (005-testing-quality-assurance) ===

# agentic-neurodata-conversion-3 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-29

## Active Technologies

- Python 3.12+ (based on existing pixi.toml configuration) + rdflib, linkml,
  pynwb, fastapi, mcp, SHACL validation libraries (001-knowledge-graph-systems)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE
TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR
ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+ (based on existing pixi.toml configuration): Follow standard
conventions

## Recent Changes

- 001-knowledge-graph-systems: Added Python 3.12+ (based on existing pixi.toml
  configuration) + rdflib, linkml, pynwb, fastapi, mcp, SHACL validation
  libraries

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

=== CLAUDE.MD FROM PR #35 (try1_speckit_validation_quality_assurance) ===

# Project Context for Claude

**Project**: Agentic Neurodata Conversion - Validation & QA System **Last
Updated**: 2025-10-06

## Project Overview

An agentic tool for converting neuroscience data to standardized NWB (Neurodata
Without Borders) format, leveraging LLMs and agentic workflows. This document
focuses on the Validation and Quality Assurance System currently under
development.

## Current Feature: Validation and Quality Assurance System

**Branch**: `001-validation-quality-assurance` **Spec Location**:
`specs/001-validation-quality-assurance/` **Status**: Specification complete,
ready for implementation

### Feature Summary

Comprehensive, modular validation and quality assurance system for NWB file
conversions with 8 core modules:

1. Core Validation Framework - Base infrastructure
2. NWB Inspector Integration - NWB-specific validation
3. LinkML Schema Validation - Metadata validation
4. Quality Assessment Engine - Multi-dimensional quality metrics
5. Domain Knowledge Validator - Neuroscience-specific rules
6. Validation Orchestrator - Workflow coordination
7. Reporting and Analytics - Result visualization
8. MCP Integration Layer - API and service integration

## Technology Stack

**Language**: Python 3.9-3.13 **Package Manager**: pixi **Testing**: pytest

**Core Dependencies**:

- nwbinspector >= 0.4.0 (NWB validation)
- linkml-runtime >= 1.7.0 (schema validation)
- pydantic >= 2.0.0 (data validation)
- pynwb (NWB file I/O)
- plotly >= 5.0.0 (visualizations)
- jinja2 >= 3.1.0 (report templates)
- FastMCP (MCP server integration)

**Data Management**:

- DataLad for reproducible data management
- Git-annex for large files
- GIN (G-Node Infrastructure) for data storage

## Project Structure

```
src/validation_qa/
├── core/                   # Module 1: Base validation framework
├── nwb_inspector/          # Module 2: NWB Inspector integration
├── linkml/                 # Module 3: LinkML schema validation
├── quality/                # Module 4: Quality assessment
├── domain/                 # Module 5: Domain knowledge validation
├── orchestrator/           # Module 6: Workflow orchestration
├── reporting/              # Module 7: Reporting and analytics
└── mcp/                    # Module 8: MCP integration

tests/
├── contract/               # API contract tests
├── integration/            # Module integration tests
└── unit/                   # Unit tests by module

cli/                        # CLI entry points

specs/001-validation-quality-assurance/
├── spec.md                 # Feature specification (44 FRs)
├── clarify.md              # Clarification questions
├── plan.md                 # Implementation plan
├── research.md             # Technology research
├── tasks.md                # 100 implementation tasks
├── analyze.md              # Cross-artifact analysis
└── contracts/              # API contracts (OpenAPI)
```

## Constitution Principles

**Reference**: `.specify/memory/constitution.md`

1. **Modular Architecture First** - 8 self-contained modules with defined
   interfaces
2. **Standards Compliance** (NON-NEGOTIABLE) - NWB, FAIR, LinkML standards
3. **Quality-First Development** - TDD mandatory, multi-dimensional metrics
4. **Traceability & Observability** - Structured logging, analytics, audit
   trails
5. **Configuration & Flexibility** - Profile-based config, custom extensions

## Build & Test Commands

```bash
# Install dependencies
pixi install

# Run all tests
pixi run pytest

# Run specific test categories
pixi run pytest -m contract        # Contract tests
pixi run pytest -m integration     # Integration tests
pixi run pytest -m unit            # Unit tests
pixi run pytest -m "not slow"      # Skip slow tests

# Run validation CLI
pixi run python cli/validate.py --help

# Format and lint
pixi run black src/ tests/
pixi run ruff check src/ tests/
pixi run mypy src/
```

## Recent Changes

- **2025-10-06**: Completed spec-kit workflow (constitution → specify → clarify
  → plan → tasks → analyze)
- **2025-10-06**: Generated 100 implementation tasks with clear dependencies
- **2025-10-06**: Cross-artifact analysis completed - 91% confidence, approved
  for implementation

## Development Workflow

**Current Phase**: Pre-implementation (Phase 3.1-3.2)

**Next Steps**:

1. T001-T007: Project setup and structure
2. T008-T012: Design documents (data-model.md, contracts/, quickstart.md)
3. T013-T028: Contract tests (MUST FAIL before implementation)
4. T029-T036: Core Framework implementation
5. T037-T075: Module implementations (can parallelize)
6. T076-T080: CLI and integration
7. T081-T100: Polish and documentation

**TDD Workflow**:

1. Write contract test (must fail) ✗
2. Implement minimum code to pass ✓
3. Refactor for quality
4. Commit with format: `[T###] Task description`

## Key Constraints

- Memory usage <2GB for standard validation workflows
- Validate <1GB NWB files in <30 seconds
- Support streaming validation for files >10GB
- Zero network dependencies for core validation (ontology services optional)
- Backward compatible with NWB 2.x schemas

## Important Files

**Specification Documents**:

- `specs/001-validation-quality-assurance/spec.md` - 44 functional requirements
- `specs/001-validation-quality-assurance/tasks.md` - 100 implementation tasks
- `specs/001-validation-quality-assurance/plan.md` - Technical implementation
  plan
- `specs/001-validation-quality-assurance/research.md` - Technology research
  (1,673 lines)

**Project Documentation**:

- `README.md` - Project overview and quick start
- `.specify/memory/constitution.md` - Project governance principles
- `.kiro/specs/validation-quality-assurance/requirements.md` - Original
  requirements

## DataLad Notes

**IMPORTANT**: Always use DataLad Python API, not CLI commands

```python
import datalad.api as dl

# Check status
status = dl.status(dataset=".", return_type='list')

# Save changes
dl.save(dataset=".", message="Update files", recursive=True)

# Get large files
dl.get(path="path/to/file.nwb")
```

## Resources

**Documentation**:

- NWB: https://www.nwb.org/
- PyNWB: https://pynwb.readthedocs.io/
- NeuroConv: https://neuroconv.readthedocs.io/
- LinkML: https://linkml.io/
- DataLad: https://handbook.datalad.org/

**Community**:

- NWB Inspector: https://github.com/NeurodataWithoutBorders/nwbinspector
- CatalystNeuro: https://github.com/catalystneuro

## Spec-Kit Context

This project uses spec-kit for spec-driven development. All specification
documents are in `specs/001-validation-quality-assurance/`.

**Workflow completed**:

- ✅ /constitution - Project principles established
- ✅ /specify - Feature specification created
- ✅ /clarify - Ambiguities resolved
- ✅ /plan - Implementation plan generated
- ✅ /tasks - 100 tasks defined
- ✅ /analyze - Consistency verified (91% confidence)
- ⏳ /implement - Ready to begin

**Analysis Results**: 100% requirements coverage, complete traceability,
realistic scope (10-15 days estimated)

---

_This file is auto-maintained by spec-kit. Manual additions should be placed
between CUSTOM START/END markers._
