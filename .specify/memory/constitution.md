<!--
Sync Impact Report:
Version change: NEW → 1.0.0
List of modified principles: Initial constitution creation
Added sections: Core Principles (5), Semantic Web Standards, Development Workflow, Governance
Removed sections: None (initial creation)
Templates requiring updates: ✅ updated (plan-template.md references verified)
Follow-up TODOs: None
-->

# Agentic Neurodata Conversion Constitution

## Core Principles

### I. Schema-First Development
Every feature MUST start with LinkML schema definition; All data structures MUST be validated against NWB-LinkML schema; Clear semantic mappings required between custom formats and NWB ontology; No implementation without prior schema validation and SHACL shape generation.

### II. Semantic Web Standards (NON-NEGOTIABLE)
All knowledge graph outputs MUST conform to W3C standards including RDF, OWL, and SPARQL; JSON-LD contexts MUST be generated from canonical NWB-LinkML schema; SHACL validation MUST be enforced for all graph data; Provenance tracking using PROV-O ontology is mandatory for all transformations.

### III. Test-First Development (NON-NEGOTIABLE)
TDD mandatory: Contract tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced; All SPARQL queries, schema validation, and MCP integrations MUST have failing tests before implementation; Integration tests required for knowledge graph enrichment workflows.

### IV. MCP Server Integration
All functionality MUST be exposed through Model Context Protocol interfaces; Clean separation between knowledge graph core logic and MCP tool layer; Concurrent access patterns MUST be handled safely; Structured responses compatible with agent and MCP server interfaces required.

### V. Data Quality Assurance
Quality scoring with configurable thresholds mandatory for all enrichment operations; Complete lineage tracking from raw NWB to final RDF required; Evidence trails MUST be maintained for all enrichment decisions; Confidence levels and reasoning chains required for metadata suggestions.

## Semantic Web Standards

### Ontology Integration Requirements
Core neuroscience ontologies (NIFSTD, UBERON, CHEBI, NCBITaxon) MUST be integrated with basic concept mapping; OWL equivalence and subsumption relationships with confidence scoring required; Schema version metadata MUST be recorded in PROV-O provenance for downstream triples.

### Knowledge Graph Output Standards
JSON-LD with schema-derived @context and TTL formats required; Standard semantic web protocols (SPARQL endpoints) for knowledge graph access; Efficient query execution with appropriate indexing and optimization; Runtime schema analysis for neurodata_type detection and structural pattern recognition.

## Development Workflow

### Validation Gates
All commits MUST pass LinkML schema validation; SHACL shape validation required before merge; Contract tests for all API endpoints MUST pass; Knowledge graph queries MUST execute within performance thresholds (<200ms for simple queries, <30 seconds for complex enrichment operations with human review).

### Code Quality Requirements
Python 3.12+ with type hints enforced via mypy; ruff for linting and formatting; pytest with coverage requirements for all knowledge graph operations; FastAPI for HTTP interfaces with proper async handling.

### Branch Protection
All PRs MUST verify constitutional compliance; Schema changes require regeneration of JSON-LD contexts, SHACL shapes, and RDF/OWL artifacts; Breaking changes to knowledge graph APIs require deprecation notice and migration path.

## Governance

Constitution supersedes all other development practices; Amendments require documentation, community review, and migration plan; All PRs and code reviews MUST verify compliance with semantic web standards and test-first principles; Complexity deviations MUST be justified with specific rationale and simpler alternatives analysis; Use CLAUDE.md for runtime development guidance and technology stack decisions.

**Version**: 1.1.0 | **Ratified**: 2025-09-29 | **Last Amended**: 2025-09-29