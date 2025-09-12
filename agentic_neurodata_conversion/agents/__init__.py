"""
Agent implementations for the agentic neurodata conversion system.

This module provides the base agent interface and concrete agent implementations
for different aspects of the neurodata conversion pipeline, including conversation,
conversion, evaluation, and knowledge graph agents.

The agents are designed to be orchestrated by the MCP server and provide
specialized functionality for dataset analysis, metadata extraction, conversion
script generation, and quality assurance.
"""

from .base import AgentCapability, AgentRegistry, AgentStatus, BaseAgent
from .conversation import ConversationAgent
from .conversion import ConversionAgent
from .evaluation import EvaluationAgent
from .knowledge_graph import KnowledgeGraphAgent

# Global agent registry instance
agent_registry = AgentRegistry()

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "AgentStatus",
    "AgentCapability",
    "ConversationAgent",
    "ConversionAgent",
    "EvaluationAgent",
    "KnowledgeGraphAgent",
    "agent_registry",
]
