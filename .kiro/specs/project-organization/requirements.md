# Requirements Document

## Introduction

This project is a multi-agent AI pipeline for converting heterogeneous neuroscience data into the Neurodata Without Borders (NWB) format. The system integrates specialized agents (Conversation, Conversion, Evaluation, and TUIE), leveraging NeuroConv, Knowledge Graphs, LinkML schemas, and LLM-powered decision making to automate complex data standardization while maintaining transparency and human oversight. The current implementation in python modules has grown organically with significant functionality already developed, but now requires proper project organization, development patterns, testing infrastructure, documentation, and collaborative workflows to support the sophisticated multi-agent architecture and team collaboration.

## Requirements

### Requirement 1

**User Story:** As a developer, I want a well-organized project structure, so that I can easily navigate, understand, and contribute to the codebase.

#### Acceptance Criteria

1. WHEN examining the project structure THEN the system SHALL organize code into logical modules (etl for some one off or continuous data creation and a package with dependencies managed in pyproject.toml using pixi containing core, agents, interfaces, utils etc.)
2. WHEN looking for specific functionality THEN the system SHALL provide clear separation between data processing, agent logic, and infrastructure code
3. WHEN adding new features THEN the system SHALL have designated directories for different types of components
4. WHEN working with configuration THEN the system SHALL centralize configuration management in a dedicated location

### Requirement 2

**User Story:** As a developer, I want consistent development patterns and best practices, so that the codebase maintains quality and consistency across all modules.

#### Acceptance Criteria

1. WHEN writing new code THEN the system SHALL enforce consistent coding standards through automated tools (ruff SHALL be used)

2. WHEN committing changes THEN the system SHALL validate code quality through pre-commit hooks
3. WHEN developing features THEN the system SHALL follow established patterns for error handling, logging, and configuration
4. WHEN creating new modules THEN the system SHALL provide templates and examples for common patterns

### Requirement 3

**User Story:** As a developer, I want comprehensive testing infrastructure, so that I can ensure code quality and prevent regressions.

#### Acceptance Criteria

1. WHEN running tests THEN the system SHALL execute unit tests for all core functionality
2. WHEN testing integrations THEN the system SHALL provide integration tests for agent workflows
3. WHEN evaluating conversions THEN the system SHALL include evaluation tests for data conversion accuracy
4. WHEN making changes THEN the system SHALL provide test coverage reporting and quality metrics
5. WHEN considering testing THEN the system SHALL make use of datalad to keep track of datasets used and consider the ones suggested in documents/possible-datasets. 

### Requirement 4

**User Story:** As a developer, I want thorough documentation, so that I can understand the system architecture and contribute effectively.

#### Acceptance Criteria

1. WHEN exploring the project THEN the system SHALL provide comprehensive API documentation for all modules
2. WHEN learning the system THEN the system SHALL include architectural decision records and design documentation
3. WHEN using agents (note not the one used for the project itself) THEN the system SHALL document agent capabilities, interfaces, and usage patterns
4. WHEN contributing THEN the system SHALL provide clear contribution guidelines and development setup instructions

### Requirement 5

**User Story:** As a developer, I want robust development tooling, so that I can work efficiently with AI assistance and maintain code quality.

#### Acceptance Criteria

1. WHEN developing with AI THEN the system SHALL provide clear interfaces and documentation for AI-assisted workflows
2. WHEN managing dependencies THEN the system SHALL use modern package management with pixi with clear dependency specifications
3. WHEN debugging THEN the system SHALL provide comprehensive logging and debugging capabilities
4. WHEN deploying THEN the system SHALL include containerization and deployment configurations.

### Requirement 6

**User Story:** As a researcher, I want reliable multi-agent data conversion workflows, so that I can convert neuroscience data to NWB format with confidence through coordinated agent interactions.

#### Acceptance Criteria

1. WHEN converting data THEN the system SHALL orchestrate conversation, conversion, and evaluation agents in coordinated workflows with error handling
2. WHEN processing different formats THEN the system SHALL automatically detect formats (Open Ephys, SpikeGLX, etc.) and select appropriate NeuroConv interfaces
3. WHEN validating outputs THEN the system SHALL integrate NWB Inspector validation, knowledge graph generation, and comprehensive quality assessments
4. WHEN tracking provenance THEN the system SHALL maintain complete data lineage and conversion metadata with agent interaction logs
5. WHEN generating outputs THEN the system SHALL produce conversion logs, quality reports, knowledge graphs in multiple formats, and interactive visualizations

### Requirement 7

**User Story:** As a team member, I want collaborative development workflows, so that multiple developers can contribute effectively to the project.

#### Acceptance Criteria

1. WHEN collaborating THEN the system SHALL provide clear branching and merge strategies
2. WHEN reviewing code THEN the system SHALL include automated CI/CD pipelines for quality assurance
3. WHEN managing releases THEN the system SHALL provide versioning and release management processes
4. WHEN onboarding THEN the system SHALL include comprehensive setup and contribution documentation

### Requirement 8

**User Story:** As a maintainer, I want monitoring and observability, so that I can track system performance and identify issues.

#### Acceptance Criteria

1. WHEN running conversions THEN the system SHALL provide comprehensive logging and metrics
2. WHEN debugging issues THEN the system SHALL include error tracking and diagnostic capabilities
3. WHEN monitoring performance THEN the system SHALL track conversion success rates and processing times
4. WHEN analyzing usage THEN the system SHALL provide analytics on conversion patterns and agent interactions

### Requirement 9

**User Story:** As a neuroscience researcher, I want an intelligent conversation agent that can analyze my raw dataset and extract metadata, so that I can provide missing information through natural language interaction rather than complex technical forms.

#### Acceptance Criteria

1. WHEN I provide a raw dataset directory THEN the conversation agent SHALL analyze contents and identify data formats, experimental context, and missing metadata fields
2. WHEN essential metadata is missing THEN the conversation agent SHALL generate natural language questions understandable to non-expert users
3. WHEN I respond to questions THEN the conversation agent SHALL validate responses against domain knowledge and suggest corrections for inconsistencies
4. WHEN metadata extraction is complete THEN the conversation agent SHALL provide structured summaries with clear provenance marking (user-provided vs. auto-detected)

### Requirement 10

**User Story:** As a researcher, I want a conversion agent that can automatically generate and execute NeuroConv scripts, so that my data is converted to NWB format with minimal input from me where I help to resolve ambiguities and provide any missing metadata.

#### Acceptance Criteria

1. WHEN provided with normalized metadata and file mappings THEN the conversion agent SHALL select appropriate NeuroConv DataInterface classes based on detected formats
2. WHEN generating conversion scripts THEN the conversion agent SHALL create valid Python code handling specific data formats and experimental setups
3. WHEN executing conversions THEN the conversion agent SHALL populate NWB metadata fields and mark which are auto-generated vs. user-provided
4. WHEN conversion fails THEN the conversion agent SHALL provide clear error messages and suggest corrective actions
5. WHEN conversion succeeds THEN the conversion agent SHALL record complete provenance information for every populated field

### Requirement 11

**User Story:** As a data quality manager, I want an evaluation agent that validates NWB outputs against standards and best practices, so that converted files meet community requirements before archival or sharing and maximise the value of the data shared given an arbitrary input dataset.

#### Acceptance Criteria

1. WHEN an NWB file is generated THEN the evaluation agent SHALL run NWB Inspector validation to check schema compliance and best practices
2. WHEN validation issues are found THEN the evaluation agent SHALL categorize errors by severity and provide specific remediation guidance
3. WHEN generating quality reports THEN the evaluation agent SHALL create comprehensive assessments including metadata completeness, data integrity, and structural compliance
4. WHEN validation passes THEN the evaluation agent SHALL generate knowledge graph representations in the most useful format (TTL, JSON-LD, N-Triples)
5. WHEN creating outputs THEN the evaluation agent SHALL produce human-readable context summaries and interactive visualizations

### Requirement 12

**User Story:** As a system integrator, I want MCP (Model Context Protocol) server capabilities, so that the conversion pipeline can be accessed programmatically by external tools and workflows.

#### Acceptance Criteria

1. WHEN external systems connect THEN the MCP server SHALL expose conversion tools through standardized FastAPI endpoints
2. WHEN processing requests THEN the MCP server SHALL handle dataset analysis, conversion script generation, and NWB evaluation as discrete services
3. WHEN managing state THEN the MCP server SHALL coordinate multi-step workflows and maintain conversion context across agent interactions
4. WHEN providing responses THEN the MCP server SHALL return structured results with complete metadata and error handling

### Requirement 13

**User Story:** As a researcher, I want a knowledge graph system that enriches my metadata using external references and domain knowledge, so that missing information can be automatically filled with high confidence.

#### Acceptance Criteria

1. WHEN metadata has gaps THEN the knowledge graph SHALL suggest enrichments based on strain-to-species mappings, device specifications, and experimental protocols
2. WHEN making suggestions THEN the knowledge graph SHALL provide confidence scores and clear provenance for all auto-filled values
3. WHEN storing relationships THEN the knowledge graph SHALL maintain entities (Dataset, Session, Subject, Device, Lab, Protocol) with semantic relationships
4. WHEN querying knowledge THEN the knowledge graph SHALL support SPARQL queries for complex metadata validation and enrichment rules
5. WHEN tracking provenance THEN the knowledge graph SHALL differentiate between User, AI, and External data sources with full audit trails

### Requirement 14

**User Story:** As a data manager, I want LinkML schema validation that ensures metadata follows structured formats, so that all conversions comply with NWB requirements and community standards.

#### Acceptance Criteria

1. WHEN processing metadata THEN LinkML schemas SHALL validate all fields against machine-readable specifications before ingestion
2. WHEN generating validation classes THEN LinkML SHALL produce Pydantic/JSON Schema classes for runtime validation
3. WHEN enforcing standards THEN LinkML schemas SHALL ensure consistency with NWB metadata requirements and controlled vocabularies
4. WHEN detecting violations THEN LinkML validation SHALL provide specific error messages indicating which fields violate which constraints

### Requirement 15

**User Story:** As a researcher, I want comprehensive provenance tracking throughout the conversion process, so that I can understand the origin and confidence level of every piece of metadata in my final NWB file.

#### Acceptance Criteria

1. WHEN any metadata field is populated THEN the system SHALL record whether it came from user input, automatic extraction, AI suggestion, or external enrichment
2. WHEN tracking changes THEN the system SHALL maintain complete audit trails of all modifications, decisions, and data transformations
3. WHEN providing transparency THEN the system SHALL clearly distinguish between high-confidence automatic extractions and AI-generated suggestions
4. WHEN generating reports THEN the system SHALL include provenance summaries allowing users to verify and validate all automated decisions

### Requirement 16

**User Story:** As a lab manager, I want a human-in-the-loop refinement process, so that domain experts can review, correct, and approve AI-generated suggestions before finalizing conversions.

#### Acceptance Criteria

1. WHEN AI suggestions are made THEN the system SHALL present them clearly marked as "AI-suggested" with confidence indicators
2. WHEN validation fails THEN the system SHALL route outputs through refinement loops with clear error descriptions and suggested corrections
3. WHEN human feedback is provided THEN the system SHALL incorporate corrections and learn from expert input for future improvements
4. WHEN finalizing conversions THEN the system SHALL require explicit approval for any AI-generated content affecting data interpretation

