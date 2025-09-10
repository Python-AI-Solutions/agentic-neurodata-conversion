"""
MCP Server implementation with tool registry and execution framework.

This module provides the central MCP server that orchestrates all agent interactions
and exposes dataset analysis, conversion orchestration, and workflow handoff capabilities.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import inspect

logger = logging.getLogger(__name__)


class MCPRegistry:
    """
    Central registry for MCP tools with decorator-based registration.
    
    This registry manages tool registration, metadata, and provides
    a clean interface for tool discovery and execution.
    """
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized MCP tool registry")
    
    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Decorator for registering MCP tools.
        
        Args:
            name: Optional tool name. If not provided, uses function name.
            description: Optional tool description. If not provided, uses function docstring.
            
        Returns:
            Decorated function that is registered as an MCP tool.
            
        Example:
            @mcp.tool(name="dataset_analysis", description="Analyze dataset structure")
            async def analyze_dataset(dataset_dir: str, server=None) -> Dict[str, Any]:
                return {"status": "success", "result": "analysis_data"}
        """
        def decorator(func: Callable):
            tool_name = name or func.__name__
            
            # Validate function signature
            sig = inspect.signature(func)
            if 'server' not in sig.parameters:
                logger.warning(f"Tool {tool_name} does not have 'server' parameter. "
                             "This may limit access to server context.")
            
            # Register the tool
            self.tools[tool_name] = func
            self.tool_metadata[tool_name] = {
                'name': tool_name,
                'description': description or func.__doc__ or "No description available",
                'function': func.__name__,
                'module': func.__module__,
                'signature': str(sig),
                'parameters': {
                    param_name: {
                        'type': param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'Any',
                        'default': param.default if param.default != inspect.Parameter.empty else None,
                        'required': param.default == inspect.Parameter.empty and param_name != 'server'
                    }
                    for param_name, param in sig.parameters.items()
                    if param_name != 'server'  # Exclude internal server parameter
                }
            }
            
            logger.info(f"Registered MCP tool: {tool_name}")
            return func
        return decorator
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Get registered tool by name.
        
        Args:
            name: Tool name to retrieve.
            
        Returns:
            Tool function if found, None otherwise.
        """
        return self.tools.get(name)
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered tools with metadata.
        
        Returns:
            Dictionary mapping tool names to their metadata.
        """
        return self.tool_metadata.copy()
    
    def get_tool_names(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names.
        """
        return list(self.tools.keys())
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool by name.
        
        Args:
            name: Tool name to unregister.
            
        Returns:
            True if tool was found and removed, False otherwise.
        """
        if name in self.tools:
            del self.tools[name]
            del self.tool_metadata[name]
            logger.info(f"Unregistered MCP tool: {name}")
            return True
        return False


# Global registry instance
mcp = MCPRegistry()


class MCPServer:
    """
    Central MCP server that orchestrates all agent interactions.
    
    This server manages the execution of registered tools, maintains pipeline state,
    and coordinates between different agents in the conversion workflow.
    """
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize MCP server.
        
        Args:
            config: Server configuration object. If None, will use default settings.
        """
        self.config = config
        self.registry = mcp
        self.pipeline_state: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}
        self._running = False
        
        logger.info("Initialized MCP server")
        
        # Initialize agents when available
        try:
            self.agents = self._initialize_agents()
            logger.info(f"Initialized {len(self.agents)} agents")
        except ImportError as e:
            logger.warning(f"Could not initialize agents: {e}. "
                         "Agents will be available when implemented.")
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """
        Initialize internal agents.
        
        Returns:
            Dictionary of initialized agents.
            
        Note:
            This method will fail gracefully if agent modules are not yet implemented.
        """
        agents = {}
        
        try:
            # Import agents when they become available
            # For now, we'll use placeholder imports that will be implemented later
            from ..agents import (
                ConversationAgent, ConversionAgent, 
                EvaluationAgent, KnowledgeGraphAgent
            )
            
            agent_config = getattr(self.config, 'agent_config', None) if self.config else None
            
            agents = {
                'conversation': ConversationAgent(agent_config),
                'conversion': ConversionAgent(agent_config),
                'evaluation': EvaluationAgent(agent_config),
                'knowledge_graph': KnowledgeGraphAgent(agent_config)
            }
            
        except ImportError:
            # Agents not yet implemented - this is expected during development
            logger.debug("Agent modules not yet available")
            
        return agents
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a registered tool with error handling and state management.
        
        Args:
            tool_name: Name of the tool to execute.
            **kwargs: Arguments to pass to the tool.
            
        Returns:
            Dictionary containing execution result with status and data.
            
        Example:
            result = await server.execute_tool("dataset_analysis", 
                                             dataset_dir="/path/to/data")
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'tool': tool_name,
                'available_tools': self.registry.get_tool_names()
            }
        
        try:
            # Inject server context into tool execution
            kwargs['server'] = self
            
            logger.info(f"Executing tool: {tool_name}")
            
            # Execute tool (handle both sync and async functions)
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**kwargs)
            else:
                result = tool(**kwargs)
            
            # Update pipeline state if the tool provides state updates
            if isinstance(result, dict) and 'state_updates' in result:
                self.pipeline_state.update(result['state_updates'])
                logger.debug(f"Updated pipeline state with {len(result['state_updates'])} items")
            
            logger.info(f"Tool {tool_name} executed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {tool_name} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'tool': tool_name,
                'error_type': type(e).__name__
            }
    
    def get_pipeline_state(self) -> Dict[str, Any]:
        """
        Get current pipeline state.
        
        Returns:
            Copy of current pipeline state.
        """
        return self.pipeline_state.copy()
    
    def update_pipeline_state(self, updates: Dict[str, Any]) -> None:
        """
        Update pipeline state with new values.
        
        Args:
            updates: Dictionary of state updates to apply.
        """
        self.pipeline_state.update(updates)
        logger.debug(f"Pipeline state updated with {len(updates)} items")
    
    def clear_pipeline_state(self) -> None:
        """Clear all pipeline state."""
        self.pipeline_state.clear()
        logger.info("Pipeline state cleared")
    
    def get_server_status(self) -> Dict[str, Any]:
        """
        Get comprehensive server status information.
        
        Returns:
            Dictionary containing server status, registered tools, agents, and pipeline state.
        """
        return {
            'status': 'running' if self._running else 'stopped',
            'registered_tools': len(self.registry.tools),
            'tool_names': self.registry.get_tool_names(),
            'agents': list(self.agents.keys()),
            'pipeline_state_keys': list(self.pipeline_state.keys()),
            'config_available': self.config is not None
        }
    
    def start(self) -> None:
        """Start the MCP server."""
        self._running = True
        logger.info("MCP server started")
    
    def stop(self) -> None:
        """Stop the MCP server."""
        self._running = False
        logger.info("MCP server stopped")
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


# Convenience function for creating server instances
def create_mcp_server(config: Optional[Any] = None) -> MCPServer:
    """
    Create and return a new MCP server instance.
    
    Args:
        config: Optional server configuration.
        
    Returns:
        Configured MCP server instance.
    """
    return MCPServer(config)