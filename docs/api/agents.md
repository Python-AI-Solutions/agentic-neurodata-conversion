# Agents API Reference

Generated on: 2025-09-12T10:29:52.246466

This document provides information about the internal agent interfaces.

## Agent Architecture

Agents are internal components that handle specific aspects of the conversion pipeline:

- **ConversationAgent**: Handles dataset analysis and metadata extraction
- **ConversionAgent**: Generates and executes NeuroConv scripts
- **EvaluationAgent**: Validates and evaluates NWB files
- **KnowledgeGraphAgent**: Manages knowledge graph operations

## Base Agent Interface

### BaseAgent

All agents inherit from the BaseAgent class which provides common functionality.

**Methods:**

- `add_capability(self, capability: agentic_neurodata_conversion.agents.base.AgentCapability) -> None`
  - Add a capability to this agent.
- `add_error_handler(self, handler: Callable[[Exception], NoneType]) -> None`
  - Add an error event handler.
- `add_status_change_handler(self, handler: Callable[[agentic_neurodata_conversion.agents.base.AgentStatus, agentic_neurodata_conversion.agents.base.AgentStatus], NoneType]) -> None`
  - Add a status change event handler.
- `can_handle_task(self, task: dict[str, typing.Any]) -> bool`
  - Check if this agent can handle a specific task.
- `execute_task(self, task: dict[str, typing.Any]) -> dict[str, typing.Any]`
  - Execute a task with proper error handling and status management.
- `get_capabilities(self) -> set[agentic_neurodata_conversion.agents.base.AgentCapability]`
  - Get the set of capabilities this agent provides.
- `get_status(self) -> dict[str, typing.Any]`
  - Get comprehensive agent status information.
- `has_capability(self, capability: agentic_neurodata_conversion.agents.base.AgentCapability) -> bool`
  - Check if this agent has a specific capability.
- `process(self, task: dict[str, typing.Any]) -> dict[str, typing.Any]`
  - Process a task assigned to this agent.
- `remove_capability(self, capability: agentic_neurodata_conversion.agents.base.AgentCapability) -> None`
  - Remove a capability from this agent.
- `reset_metrics(self) -> None`
  - Reset agent performance metrics.
- `shutdown(self) -> None`
  - Gracefully shutdown the agent.
- `update_metadata(self, updates: dict[str, typing.Any]) -> None`
  - Update agent metadata.

## Specific Agents

### ConversationAgent

**Module:** `agentic_neurodata_conversion.agents.conversation`

**Description:**

Agent responsible for dataset analysis and conversational metadata extraction.

    This agent analyzes dataset structures, extracts available metadata,
    detects data formats, and can generate questions to gather missing
    information required for NWB conversion.


---

### ConversionAgent

**Module:** `agentic_neurodata_conversion.agents.conversion`

**Description:**

Agent responsible for generating and executing NeuroConv conversion scripts.

    This agent takes normalized metadata and file mappings to generate
    appropriate NeuroConv conversion scripts and can execute the conversion
    process to produce NWB files.


---

### EvaluationAgent

**Module:** `agentic_neurodata_conversion.agents.evaluation`

**Description:**

Agent responsible for evaluating and validating NWB files.

    This agent uses NWB Inspector and other validation tools to assess
    the quality, compliance, and completeness of generated NWB files,
    providing detailed reports and recommendations.


---

### KnowledgeGraphAgent

**Module:** `agentic_neurodata_conversion.agents.knowledge_graph`

**Description:**

Agent responsible for knowledge graph creation and management.

    This agent creates semantic representations of NWB data and metadata,
    builds knowledge graphs, and provides querying capabilities for
    relationship discovery and semantic search.


---
