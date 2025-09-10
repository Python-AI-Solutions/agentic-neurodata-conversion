# Core Project Organization Requirements

## Introduction

This spec establishes the foundational project structure, packaging, development tooling, and collaborative workflows for the agentic neurodata conversion project. It provides the base infrastructure that other specialized specs build upon, including the MCP server architecture, agent implementations, validation systems, knowledge graphs, evaluation frameworks, data management, and testing infrastructure. The core organization supports a system built around a central MCP (Model Context Protocol) server that orchestrates multi-agent workflows for converting neuroscience data to NWB format. The MCP server exposes tools such as analyze_data, convert_to_nwb, and handoff, which delegate tasks to internal agent

## Requirements

### Requirement 1

**User Story:** As a developer, I want a well-organized project structure that reflects the MCP server as the primary orchestration layer, so that I can easily navigate, understand, and contribute to the codebase.

#### Acceptance Criteria

1. WHEN examining the project structure THEN the system SHALL organize code into logical modules (etl for data creation and a package with dependencies managed in pyproject.toml using pixi containing core, agents, interfaces, utils etc.)
2. WHEN looking for functionality THEN the system SHALL provide clear separation between MCP server (primary orchestration exposing tools like analyze_data, convert_to_nwb, and handoff), internal agent modules (conversation agent, conversion agent), client interface implementations, and external client libraries
3. WHEN adding new features THEN the system SHALL have designated directories for MCP tools, agent modules, and third-party client integrations
4. WHEN working with configuration THEN the system SHALL use pydantic-settings based configuration with nested classes and environment variable support

### Requirement 2

**User Story:** As a developer, I want consistent development patterns and best practices, so that the codebase maintains quality and consistency across MCP server, agents, and clients.

#### Acceptance Criteria

1. WHEN writing new code THEN the system SHALL enforce consistent coding standards through automated tools (ruff SHALL be used)
2. WHEN committing changes THEN the system SHALL validate code quality through pre-commit hooks
3. WHEN developing features THEN the system SHALL follow established patterns for MCP tool implementation (using @mcp.tool decorators with structured JSON in/out), agent interfaces, and error handling
4. WHEN creating new modules THEN the system SHALL provide templates for MCP tools, agents, and client libraries

### Requirement 3

**User Story:** As a developer, I want robust development tooling optimized for MCP server development, so that I can work efficiently with the multi-agent architecture.

#### Acceptance Criteria

1. WHEN developing MCP tools THEN the system SHALL provide decorator-based tool registration (@mcp.tool, as in the current server implementation using fastmcp) and testing utilities for MCP server development
2. WHEN managing dependencies THEN the system SHALL use modern package management with pixi with clear dependency specifications
3. WHEN debugging THEN the system SHALL provide comprehensive logging for MCP server operations, tool executions, and agent interactions, including end-to-end handoff flows (dataset analyzed → normalized metadata → conversion executed).
4. WHEN deploying THEN the system SHALL include containerization for the MCP server with configurable host/port settings via environment variables

### Requirement 4

**User Story:** As a team member, I want collaborative development workflows that support the MCP-centric architecture, so that multiple developers can contribute effectively.

#### Acceptance Criteria

1. WHEN collaborating THEN the system SHALL provide clear branching and merge strategies for MCP server and agent development
2. WHEN reviewing code THEN the system SHALL include automated CI/CD pipelines that test MCP server functionality
3. WHEN managing releases THEN the system SHALL provide versioning for MCP server API and agent interfaces
4. WHEN onboarding THEN the system SHALL include comprehensive setup documentation for MCP server development

### Requirement 5

**User Story:** As a developer, I want basic documentation infrastructure that explains the MCP-centric architecture, so that I can understand and contribute to the system effectively.

#### Acceptance Criteria

1. WHEN exploring the project THEN the system SHALL provide documentation explaining the MCP server's central role as the primary orchestration layer
2. WHEN contributing THEN the system SHALL provide clear guidelines for developing MCP tools and agents
3. WHEN setting up development THEN the system SHALL include comprehensive MCP server setup and testing instructions
4. WHEN understanding the architecture THEN the system SHALL provide clear documentation of the MCP server as central orchestrator with agents managed internally and multiple client interface options

### Requirement 6

**User Story:** As a developer, I want the core project structure to support the specialized system components, so that the MCP server, agents, validation systems, and other components can be developed and integrated effectively.

#### Acceptance Criteria

1. WHEN organizing components THEN the system SHALL provide clear structure for MCP server implementation (detailed in mcp-server-architecture spec)
2. WHEN implementing agents THEN the system SHALL provide foundation for agent development (detailed in agent-implementations spec)
3. WHEN adding validation THEN the system SHALL support validation and quality assurance systems (detailed in validation-quality-assurance spec)
4. WHEN managing data THEN the system SHALL provide foundation for data management and provenance tracking (detailed in data-management-provenance spec)

### Requirement 7

**User Story:** As a developer, I want the project structure to support documentation and examples for external developers, so that third-party integration is well-documented and accessible.

#### Acceptance Criteria

1. WHEN providing examples THEN the system SHALL include a dedicated examples directory with client integration patterns (detailed in client-libraries-integrations spec)
2. WHEN documenting integration THEN the system SHALL provide clear documentation structure for third-party developers
3. WHEN organizing examples THEN the system SHALL separate core system code from third-party integration examples
4. WHEN maintaining examples THEN the system SHALL ensure examples stay current with MCP server API changes

### Requirement 8

**User Story:** As a developer, I want basic testing infrastructure foundation, so that comprehensive testing can be built upon a solid base.

#### Acceptance Criteria

1. WHEN setting up testing THEN the system SHALL provide basic test directory structure and configuration for pytest
2. WHEN running tests THEN the system SHALL include basic CI/CD pipeline configuration that can be extended by comprehensive testing systems
3. WHEN organizing tests THEN the system SHALL provide clear separation between unit tests, integration tests, and end-to-end tests (comprehensive testing detailed in testing-quality-assurance spec)
4. WHEN managing test data THEN the system SHALL provide foundation for DataLad-based test data management (detailed in data-management-provenance spec)

### Requirement 9

**User Story:** As a system architect, I want the core project organization to establish the foundation that other specialized specs build upon, so that the overall system architecture is coherent and well-coordinated.

#### Acceptance Criteria

1. WHEN implementing specialized components THEN the core structure SHALL support the MCP server architecture (mcp-server-architecture spec), agent implementations (agent-implementations spec), and validation systems (validation-quality-assurance spec)
2. WHEN adding advanced features THEN the core structure SHALL accommodate knowledge graph systems (knowledge-graph-systems spec), evaluation and reporting (evaluation-reporting spec), and data management (data-management-provenance spec)
3. WHEN providing integration support THEN the core structure SHALL include foundation for client examples and third-party integrations (client-libraries-integrations spec)
4. WHEN ensuring quality THEN the core structure SHALL support comprehensive testing and quality assurance frameworks (testing-quality-assurance spec)
