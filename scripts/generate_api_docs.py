#!/usr/bin/env python
"""
Generate API documentation from MCP server tools and agents.

This script automatically generates documentation for:
- MCP tools and their parameters
- Agent interfaces and methods
- API endpoints and responses
- Configuration options
"""

from datetime import datetime
import importlib
import inspect
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_mcp_tools_docs() -> str:
    """Generate documentation for registered MCP tools."""
    try:
        from agentic_neurodata_conversion.mcp_server.server import mcp

        docs_lines = [
            "# MCP Tools API Reference",
            "",
            f"Generated on: {datetime.now().isoformat()}",
            "",
            "This document provides detailed information about all available MCP tools.",
            "",
            "## Available Tools",
            "",
        ]

        # Get all registered tools
        tools_metadata = mcp.list_tools()

        if not tools_metadata:
            docs_lines.extend(
                [
                    "No tools are currently registered.",
                    "",
                    "To register tools, ensure they are imported and use the `@mcp.tool` decorator.",
                ]
            )
            return "\n".join(docs_lines)

        # Generate documentation for each tool
        for tool_name, metadata in sorted(tools_metadata.items()):
            tool_func = mcp.get_tool(tool_name)

            docs_lines.extend(
                [
                    f"### {tool_name}",
                    "",
                    f"**Description:** {metadata.get('description', 'No description available')}",
                    "",
                    f"**Function:** `{metadata.get('function', 'unknown')}`",
                    "",
                    f"**Module:** `{metadata.get('module', 'unknown')}`",
                    "",
                ]
            )

            # Get function signature and parameters
            if tool_func:
                signature = inspect.signature(tool_func)

                docs_lines.extend(["**Parameters:**", ""])

                param_count = 0
                for param_name, param in signature.parameters.items():
                    if param_name == "server":  # Skip internal server parameter
                        continue

                    param_count += 1
                    param_type = _get_type_string(param.annotation)
                    default_str = ""

                    if param.default != inspect.Parameter.empty:
                        if isinstance(param.default, str):
                            default_str = f' = "{param.default}"'
                        else:
                            default_str = f" = {param.default}"

                    required = param.default == inspect.Parameter.empty
                    required_str = " (required)" if required else " (optional)"

                    docs_lines.append(
                        f"- `{param_name}`: {param_type}{default_str}{required_str}"
                    )

                if param_count == 0:
                    docs_lines.append("- No parameters")

                docs_lines.extend(["", "**Returns:**", ""])

                return_annotation = signature.return_annotation
                if return_annotation != inspect.Parameter.empty:
                    return_type = _get_type_string(return_annotation)
                    docs_lines.append(f"- {return_type}")
                else:
                    docs_lines.append("- Dict[str, Any] - Standard MCP tool response")

                # Add docstring if available
                if tool_func.__doc__:
                    docs_lines.extend(
                        [
                            "",
                            "**Documentation:**",
                            "",
                            "```",
                            tool_func.__doc__.strip(),
                            "```",
                        ]
                    )

                # Add usage example
                docs_lines.extend(
                    [
                        "",
                        "**Usage Example:**",
                        "",
                        "```python",
                        "# Via Python client",
                        f"result = client.call_tool('{tool_name}', param1='value1')",
                        "",
                        "# Via HTTP API",
                        f"POST /tool/{tool_name}",
                        "Content-Type: application/json",
                        "",
                        "{",
                        '  "param1": "value1"',
                        "}",
                        "```",
                        "",
                        "---",
                        "",
                    ]
                )

        return "\n".join(docs_lines)

    except ImportError as e:
        return f"# MCP Tools API Reference\n\nError importing MCP tools: {e}\n\nEnsure the project is properly installed."
    except Exception as e:
        return f"# MCP Tools API Reference\n\nError generating documentation: {e}"


def generate_agents_docs() -> str:
    """Generate documentation for agent interfaces."""
    docs_lines = [
        "# Agents API Reference",
        "",
        f"Generated on: {datetime.now().isoformat()}",
        "",
        "This document provides information about the internal agent interfaces.",
        "",
        "## Agent Architecture",
        "",
        "Agents are internal components that handle specific aspects of the conversion pipeline:",
        "",
        "- **ConversationAgent**: Handles dataset analysis and metadata extraction",
        "- **ConversionAgent**: Generates and executes NeuroConv scripts",
        "- **EvaluationAgent**: Validates and evaluates NWB files",
        "- **KnowledgeGraphAgent**: Manages knowledge graph operations",
        "",
        "## Base Agent Interface",
        "",
    ]

    try:
        from agentic_neurodata_conversion.agents.base import BaseAgent

        # Document base agent interface
        docs_lines.extend(
            [
                "### BaseAgent",
                "",
                "All agents inherit from the BaseAgent class which provides common functionality.",
                "",
                "**Methods:**",
                "",
            ]
        )

        # Get methods from BaseAgent
        for name, method in inspect.getmembers(BaseAgent, predicate=inspect.isfunction):
            if not name.startswith("_"):  # Skip private methods
                signature = inspect.signature(method)
                docs_lines.append(f"- `{name}{signature}`")

                if method.__doc__:
                    docs_lines.extend([f"  - {method.__doc__.strip().split('.')[0]}."])

        docs_lines.extend(["", "## Specific Agents", ""])

        # Document specific agents
        agent_modules = [
            ("ConversationAgent", "agentic_neurodata_conversion.agents.conversation"),
            ("ConversionAgent", "agentic_neurodata_conversion.agents.conversion"),
            ("EvaluationAgent", "agentic_neurodata_conversion.agents.evaluation"),
            (
                "KnowledgeGraphAgent",
                "agentic_neurodata_conversion.agents.knowledge_graph",
            ),
        ]

        for agent_name, module_path in agent_modules:
            try:
                module = importlib.import_module(module_path)
                agent_class = getattr(module, agent_name)

                docs_lines.extend(
                    [f"### {agent_name}", "", f"**Module:** `{module_path}`", ""]
                )

                if agent_class.__doc__:
                    docs_lines.extend(
                        ["**Description:**", "", agent_class.__doc__.strip(), ""]
                    )

                # Get public methods
                public_methods = []
                for name, method in inspect.getmembers(
                    agent_class, predicate=inspect.ismethod
                ):
                    if not name.startswith("_") and name not in ["__init__"]:
                        public_methods.append((name, method))

                if public_methods:
                    docs_lines.extend(["**Methods:**", ""])

                    for method_name, method in public_methods:
                        try:
                            signature = inspect.signature(method)
                            docs_lines.append(f"- `{method_name}{signature}`")

                            if method.__doc__:
                                docs_lines.append(
                                    f"  - {method.__doc__.strip().split('.')[0]}."
                                )
                        except Exception:
                            docs_lines.append(f"- `{method_name}(...)`")

                docs_lines.extend(["", "---", ""])

            except ImportError:
                docs_lines.extend(
                    [
                        f"### {agent_name}",
                        "",
                        f"*Module not available: {module_path}*",
                        "",
                        "---",
                        "",
                    ]
                )

        return "\n".join(docs_lines)

    except Exception as e:
        return f"# Agents API Reference\n\nError generating documentation: {e}"


def generate_api_endpoints_docs() -> str:
    """Generate documentation for HTTP API endpoints."""
    docs_lines = [
        "# HTTP API Reference",
        "",
        f"Generated on: {datetime.now().isoformat()}",
        "",
        "This document describes the HTTP API endpoints provided by the MCP server.",
        "",
        "## Base URL",
        "",
        "Default: `http://127.0.0.1:8000`",
        "",
        "## Authentication",
        "",
        "Currently, no authentication is required for local development.",
        "",
        "## Endpoints",
        "",
        "### GET /status",
        "",
        "Get server status and pipeline state.",
        "",
        "**Response:**",
        "```json",
        "{",
        '  "status": "running",',
        '  "pipeline_state": {},',
        '  "registered_tools": 5,',
        '  "agents": ["conversation", "conversion", "evaluation", "knowledge_graph"]',
        "}",
        "```",
        "",
        "### GET /tools",
        "",
        "List all registered MCP tools.",
        "",
        "**Response:**",
        "```json",
        "{",
        '  "tools": {',
        '    "dataset_analysis": {',
        '      "description": "Analyze dataset structure and extract metadata",',
        '      "function": "dataset_analysis",',
        '      "module": "agentic_neurodata_conversion.mcp_server.tools.dataset_analysis"',
        "    }",
        "  }",
        "}",
        "```",
        "",
        "### POST /tool/{tool_name}",
        "",
        "Execute a specific MCP tool.",
        "",
        "**Parameters:**",
        "- `tool_name` (path): Name of the tool to execute",
        "",
        "**Request Body:**",
        "```json",
        "{",
        '  "param1": "value1",',
        '  "param2": "value2"',
        "}",
        "```",
        "",
        "**Response (Success):**",
        "```json",
        "{",
        '  "status": "success",',
        '  "result": {',
        '    "data": "...",',
        '    "metadata": "..."',
        "  },",
        '  "state_updates": {',
        '    "key": "value"',
        "  }",
        "}",
        "```",
        "",
        "**Response (Error):**",
        "```json",
        "{",
        '  "status": "error",',
        '  "message": "Error description",',
        '  "error_type": "ValueError"',
        "}",
        "```",
        "",
        "### POST /reset",
        "",
        "Reset pipeline state.",
        "",
        "**Response:**",
        "```json",
        "{",
        '  "status": "reset",',
        '  "message": "Pipeline state cleared"',
        "}",
        "```",
        "",
        "## Error Codes",
        "",
        "- `200`: Success",
        "- `404`: Tool not found",
        "- `422`: Invalid parameters",
        "- `500`: Internal server error",
        "",
        "## Rate Limiting",
        "",
        "Currently no rate limiting is implemented.",
        "",
        "## CORS",
        "",
        "CORS is enabled for all origins in development mode.",
    ]

    return "\n".join(docs_lines)


def generate_configuration_docs() -> str:
    """Generate documentation for configuration options."""
    docs_lines = [
        "# Configuration Reference",
        "",
        f"Generated on: {datetime.now().isoformat()}",
        "",
        "This document describes all configuration options for the agentic neurodata conversion system.",
        "",
        "## Configuration System",
        "",
        "The system uses pydantic-settings for configuration management with support for:",
        "",
        "- Environment variables",
        "- Configuration files (.env)",
        "- Nested configuration structures",
        "- Type validation and conversion",
        "",
        "## Configuration Structure",
        "",
    ]

    try:
        from agentic_neurodata_conversion.core.config import Settings

        # Create a settings instance to get default values
        settings = Settings()

        # Document each configuration section
        config_sections = [
            ("server", "Server Configuration"),
            ("agents", "Agent Configuration"),
            ("data", "Data Processing Configuration"),
            ("database", "Database Configuration"),
        ]

        for section_name, section_title in config_sections:
            if hasattr(settings, section_name):
                section_config = getattr(settings, section_name)

                docs_lines.extend(
                    [
                        f"### {section_title}",
                        "",
                        f"**Section:** `{section_name}`",
                        "",
                        "**Options:**",
                        "",
                    ]
                )

                # Get all fields from the config section
                if hasattr(section_config, "__fields__"):
                    for field_name, field_info in section_config.__fields__.items():
                        field_value = getattr(section_config, field_name)
                        field_type = field_info.type_

                        # Get environment variable name
                        env_var = f"AGENTIC_CONVERTER_{section_name.upper()}__{field_name.upper()}"

                        docs_lines.extend(
                            [
                                f"- **{field_name}**",
                                f"  - Type: `{_get_type_string(field_type)}`",
                                f"  - Default: `{field_value}`",
                                f"  - Environment: `{env_var}`",
                            ]
                        )

                        if (
                            hasattr(field_info, "description")
                            and field_info.description
                        ):
                            docs_lines.append(
                                f"  - Description: {field_info.description}"
                            )

                        docs_lines.append("")

                docs_lines.extend(["", "---", ""])

        # Add environment variable examples
        docs_lines.extend(
            [
                "## Environment Variables",
                "",
                "Configuration can be set using environment variables with the following pattern:",
                "",
                "`AGENTIC_CONVERTER_<SECTION>__<FIELD>=<VALUE>`",
                "",
                "**Examples:**",
                "",
                "```bash",
                "# Server configuration",
                "export AGENTIC_CONVERTER_SERVER__HOST=0.0.0.0",
                "export AGENTIC_CONVERTER_SERVER__PORT=8080",
                "export AGENTIC_CONVERTER_SERVER__DEBUG=true",
                "",
                "# Agent configuration",
                "export AGENTIC_CONVERTER_AGENTS__CONVERSATION_MODEL=gpt-4",
                "export AGENTIC_CONVERTER_AGENTS__CONVERSION_TIMEOUT=600",
                "",
                "# Data configuration",
                "export AGENTIC_CONVERTER_DATA__OUTPUT_DIR=/custom/output",
                "export AGENTIC_CONVERTER_DATA__MAX_FILE_SIZE=2147483648",
                "```",
                "",
                "## Configuration Files",
                "",
                "Create a `.env` file in the project root:",
                "",
                "```env",
                "# .env file example",
                "AGENTIC_CONVERTER_SERVER__HOST=127.0.0.1",
                "AGENTIC_CONVERTER_SERVER__PORT=8000",
                "AGENTIC_CONVERTER_SERVER__DEBUG=false",
                "",
                "AGENTIC_CONVERTER_AGENTS__CONVERSATION_MODEL=gpt-3.5-turbo",
                "AGENTIC_CONVERTER_AGENTS__CONVERSION_TIMEOUT=300",
                "",
                "AGENTIC_CONVERTER_DATA__OUTPUT_DIR=outputs",
                "AGENTIC_CONVERTER_DATA__TEMP_DIR=temp",
                "```",
            ]
        )

        return "\n".join(docs_lines)

    except Exception as e:
        return f"# Configuration Reference\n\nError generating documentation: {e}"


def _get_type_string(type_annotation) -> str:
    """Convert type annotation to readable string."""
    if type_annotation == inspect.Parameter.empty:
        return "Any"

    if hasattr(type_annotation, "__name__"):
        return type_annotation.__name__

    # Handle typing module types
    type_str = str(type_annotation)

    # Clean up common typing patterns
    type_str = type_str.replace("typing.", "")
    type_str = type_str.replace("<class '", "").replace("'>", "")

    return type_str


def main():
    """Generate all API documentation."""
    docs_dir = Path("docs/api")
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("Generating API documentation...")

    # Generate MCP tools documentation
    print("- Generating MCP tools documentation...")
    tools_docs = generate_mcp_tools_docs()
    with open(docs_dir / "mcp_tools.md", "w") as f:
        f.write(tools_docs)

    # Generate agents documentation
    print("- Generating agents documentation...")
    agents_docs = generate_agents_docs()
    with open(docs_dir / "agents.md", "w") as f:
        f.write(agents_docs)

    # Generate HTTP API documentation
    print("- Generating HTTP API documentation...")
    api_docs = generate_api_endpoints_docs()
    with open(docs_dir / "http_api.md", "w") as f:
        f.write(api_docs)

    # Generate configuration documentation
    print("- Generating configuration documentation...")
    config_docs = generate_configuration_docs()
    with open(docs_dir / "configuration.md", "w") as f:
        f.write(config_docs)

    # Update main API README
    print("- Updating API README...")
    api_readme = f"""# API Documentation

Generated on: {datetime.now().isoformat()}

This directory contains comprehensive API documentation for the agentic neurodata conversion system.

## Documentation Files

- **[mcp_tools.md](mcp_tools.md)** - MCP tools and their parameters
- **[agents.md](agents.md)** - Internal agent interfaces and methods
- **[http_api.md](http_api.md)** - HTTP API endpoints and responses
- **[configuration.md](configuration.md)** - Configuration options and environment variables

## Quick Reference

### MCP Server
- Default URL: `http://127.0.0.1:8000`
- Status endpoint: `GET /status`
- Tools list: `GET /tools`
- Execute tool: `POST /tool/{{tool_name}}`

### Key Tools
- `dataset_analysis` - Analyze dataset structure and metadata
- `conversion_orchestration` - Generate and execute NeuroConv scripts
- `evaluate_nwb_file` - Validate and evaluate NWB files

### Configuration
- Environment variables: `AGENTIC_CONVERTER_<SECTION>__<FIELD>`
- Configuration file: `.env` in project root
- Nested structure: server, agents, data, database

## Regenerating Documentation

To regenerate this documentation:

```bash
pixi run python scripts/generate_api_docs.py
```

This will update all API documentation files with the latest information from the codebase.
"""

    with open(docs_dir / "README.md", "w") as f:
        f.write(api_readme)

    print("✅ API documentation generated successfully!")
    print(f"📁 Documentation saved to: {docs_dir}")
    print("📄 Files generated:")
    print("   - mcp_tools.md")
    print("   - agents.md")
    print("   - http_api.md")
    print("   - configuration.md")
    print("   - README.md")


if __name__ == "__main__":
    main()
