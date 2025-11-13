"""
Agentic Neurodata Conversion - AI-powered NWB Converter
========================================================

Multi-agent system for converting neurophysiology data to NWB format using Claude Sonnet 4.5.

Main Components:
- agents: Conversation, Conversion, and Evaluation agents
- services: LLM service, MCP server, report generation
- models: Data models and state management
- api: FastAPI REST and WebSocket endpoints

Usage:
    from agentic_neurodata_conversion.agents import ConversationAgent, ConversionAgent, EvaluationAgent
    from agentic_neurodata_conversion.services import LLMService
    from agentic_neurodata_conversion.models import GlobalState
"""

__version__ = "0.1.0"
__author__ = "Aditya Patane"

# Import key components for easy access
try:
    from agentic_neurodata_conversion.models.mcp import MCPMessage
    from agentic_neurodata_conversion.models.state import GlobalState
    from agentic_neurodata_conversion.services.llm_service import LLMService

    __all__ = [
        "GlobalState",
        "MCPMessage",
        "LLMService",
        "__version__",
        "__author__",
    ]
except ImportError:
    # During installation or when dependencies aren't available
    __all__ = ["__version__", "__author__"]
