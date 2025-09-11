# Copyright (c) 2025 Agentic Neurodata Conversion Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Agent implementations for the agentic neurodata conversion system.

This module provides the base agent interface and concrete agent implementations
for different aspects of the neurodata conversion pipeline, including conversation,
conversion, evaluation, and knowledge graph agents.

The agents are designed to be orchestrated by the MCP server and provide
specialized functionality for dataset analysis, metadata extraction, conversion
script generation, and quality assurance.
"""

from .base import AgentConfig, AgentResult, AgentStatus, BaseAgent
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
    "KnowledgeGraphAgent",
]
