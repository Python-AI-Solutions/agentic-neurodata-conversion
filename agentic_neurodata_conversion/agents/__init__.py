"""
Agent implementations for the agentic neurodata conversion system.

This module provides the base agent interface and concrete agent implementations
for different aspects of the neurodata conversion pipeline, including conversation,
conversion, evaluation, and knowledge graph agents.

The agents are designed to be orchestrated by the MCP server and provide
specialized functionality for dataset analysis, metadata extraction, conversion
script generation, and quality assurance.
"""

from .base import BaseAgent, AgentStatus, AgentResult, AgentConfig
from .conversation import ConversationAgent
from .conversion import ConversionAgent
from .evaluation import EvaluationAgent
from .knowledge_graph import KnowledgeGraphAgent

__all__ = [
    "BaseAgent",
    "AgentStatus",
    "AgentResult",
    "AgentConfig",
    "ConversationAgent",
    "ConversionAgent", 
    "EvaluationAgent",
    "KnowledgeGraphAgent"
]