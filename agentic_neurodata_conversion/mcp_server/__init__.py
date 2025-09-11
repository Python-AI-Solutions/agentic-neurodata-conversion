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
MCP Server module for agentic neurodata conversion.

This module provides the Model Context Protocol (MCP) server implementation
that serves as the primary orchestration layer for the conversion pipeline.
"""

from .server import MCPRegistry, MCPServer, mcp

__all__ = ["MCPServer", "MCPRegistry", "mcp"]
