# Agentic Neurodata Conversion - Spec Organization

## Overview

This project has been organized into focused specifications that reflect the actual MCP-centric architecture revealed by examining the working implementation in `workflow.py`. Each spec addresses a specific aspect of the system while maintaining clear dependencies and interfaces.

## Spec Structure

### 1. [Core Project Organization](./core-project-organization/)
**Focus**: Foundational project structure, packaging, development tooling, and collaborative workflows  
**Key Concerns**: Directory structure, pyproject.toml, development environment, CI/CD, team collaboration  
**Dependencies**: None (foundation for all other specs)

### 2. [MCP Server Architecture](./mcp-server-architecture/)
**Focus**: The central MCP server that orchestrates all agent interactions  
**Key Concerns**: HTTP endpoints, agent coordination, workflow management, error handling  
**Dependencies**: Core Project Organization  
**Note**: This is the heart of the system - all other components interact through the MCP server

### 3. [Agent Implementations](./agent-implementations/)
**Focus**: Specialized agents called by the MCP server  
**Key Concerns**: ConversationAgent, ConversionAgent, EvaluationAgent, MetadataQuestioner interfaces  
**Dependencies**: Core Project Organization, MCP Server Architecture

### 4. [Knowledge Graph Systems](./knowledge-graph-systems/)
**Focus**: RDF generation, semantic relationships, metadata enrichment, SPARQL queries  
**Key Concerns**: Knowledge graph generation, semantic enrichment, domain ontologies, provenance tracking  
**Dependencies**: Core Project Organization

### 5. [Validation and Quality Assurance](./validation-quality-assurance/)
**Focus**: NWB Inspector validation, LinkML schemas, compliance checking, quality metrics  
**Key Concerns**: Schema validation, compliance checking, quality assessment, domain-specific validation  
**Dependencies**: Core Project Organization

### 6. [Evaluation and Reporting](./evaluation-reporting/)
**Focus**: Quality reports, interactive visualizations, human-readable summaries, comprehensive evaluation  
**Key Concerns**: Evaluation reports, interactive visualizations, context summaries, quality analytics  
**Dependencies**: Core Project Organization, Validation and Quality Assurance, Knowledge Graph Systems

### 7. [Data Management and Provenance](./data-management-provenance/)
**Focus**: DataLad integration, provenance tracking, data lifecycle management  
**Key Concerns**: Development datasets, conversion output tracking, version control, audit trails  
**Dependencies**: Core Project Organization

### 8. [Client Libraries and Integrations](./client-libraries-integrations/)
**Focus**: Python client libraries and external system integrations  
**Key Concerns**: workflow.py-style clients, HTTP communication, external tool integration  
**Dependencies**: MCP Server Architecture

### 9. [Testing and Quality Assurance](./testing-quality-assurance/)
**Focus**: Comprehensive testing strategy and quality assurance  
**Key Concerns**: Unit/integration tests, evaluation datasets, performance testing, CI/CD  
**Dependencies**: All other specs (tests the complete system)

## Architecture Insights

### MCP-Centric Design
The key architectural insight from examining `workflow.py` is that the **MCP server is the central orchestration hub**. The original design document incorrectly assumed we needed to build a separate orchestration layer, but the MCP server already fulfills this role effectively.

### Actual System Flow
```
Client Libraries (workflow.py) 
    ↓ HTTP/API calls
MCP Server (FastAPI)
    ↓ Direct Python calls  
Individual Agents (ConversationAgent, ConversionAgent, EvaluationAgent)
    ↓ Tool usage
External Tools (NeuroConv, NWB Inspector, Knowledge Graphs)
```

### Design Patterns
- **MCP Server as Facade**: Simplifies access to complex agent interactions
- **Agents as Strategies**: Different agents implement different domain strategies
- **Clients as Proxies**: Client libraries proxy remote MCP server operations
- **Pipeline as Template Method**: Standard workflow sequence with defined steps

## Development Approach

### Recommended Implementation Order
1. **Core Project Organization** - Foundation for everything else
2. **MCP Server Architecture** - Central orchestration hub (already largely implemented)
3. **Agent Implementations** - Refactor existing agents to clean interfaces
4. **Knowledge Graph Systems** - RDF generation and semantic enrichment (partially implemented)
5. **Validation and Quality Assurance** - NWB validation and quality checking (partially implemented)
6. **Evaluation and Reporting** - Quality reports and visualizations (partially implemented)
7. **Client Libraries and Integrations** - Refactor workflow.py into proper client library
8. **Data Management and Provenance** - DataLad integration for development and user data
9. **Testing and Quality Assurance** - Comprehensive testing across all components

### Parallel Development
- **MCP Server** and **Agent Implementations** can be developed in parallel
- **Knowledge Graph Systems**, **Validation and Quality Assurance**, and **Evaluation and Reporting** can be developed in parallel (they are related but independent)
- **Client Libraries** can be developed once MCP Server interfaces are stable
- **Data Management** can be developed independently and integrated later
- **Testing** should be developed alongside each component

## Key Benefits of This Organization

1. **Reflects Reality**: Specs match the actual working architecture
2. **Clear Separation**: Each spec has distinct responsibilities and interfaces
3. **Manageable Complexity**: Smaller, focused specs are easier to implement and maintain
4. **Parallel Development**: Multiple team members can work on different specs simultaneously
5. **Clear Dependencies**: Inter-spec dependencies are explicit and minimal
6. **Focused Testing**: Each spec can have its own targeted testing strategy

## Migration from Original Spec

The original `project-organization` spec has been refactored and split:
- Basic project structure → **Core Project Organization**
- Complex orchestration logic → **MCP Server Architecture** (simplified to match reality)
- Agent interfaces → **Agent Implementations** (simplified to focus on coordination)
- Knowledge graph functionality → **Knowledge Graph Systems** (dedicated spec for RDF, SPARQL, semantic enrichment)
- Validation functionality → **Validation and Quality Assurance** (dedicated spec for NWB validation, LinkML schemas)
- Evaluation functionality → **Evaluation and Reporting** (dedicated spec for reports, visualizations, summaries)
- DataLad integration → **Data Management and Provenance**
- External integrations → **Client Libraries and Integrations**
- Testing strategy → **Testing and Quality Assurance**

This reorganization properly separates the complex knowledge graph, validation, and evaluation systems into dedicated specs while reflecting the actual MCP-centric architecture.