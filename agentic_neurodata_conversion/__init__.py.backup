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
    from backend.src.agents import ConversationAgent, ConversionAgent, EvaluationAgent
    from backend.src.services import LLMService
    from backend.src.models import GlobalState
"""

__version__ = "0.1.0"
__author__ = "Aditya Patane"

# Import key components for easy access
try:
    from backend.src.models.mcp import MCPMessage
    from backend.src.models.state import GlobalState
    from backend.src.services.llm_service import LLMService

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
