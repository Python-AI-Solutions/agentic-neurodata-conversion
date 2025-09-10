"""
Basic MCP tools for demonstration and testing.

This module provides simple tools to demonstrate the MCP tool registration
system and provide basic server functionality.
"""

from typing import Dict, Any
from ..server import mcp
import logging

logger = logging.getLogger(__name__)


@mcp.tool(
    name="server_status",
    description="Get MCP server status and information"
)
async def get_server_status(server=None) -> Dict[str, Any]:
    """
    Get comprehensive server status information.
    
    Returns:
        Dictionary containing server status, tools, and pipeline state.
    """
    if server is None:
        return {
            'status': 'error',
            'message': 'Server context not available'
        }
    
    try:
        status = server.get_server_status()
        return {
            'status': 'success',
            'result': status
        }
    except Exception as e:
        logger.error(f"Failed to get server status: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


@mcp.tool(
    name="list_tools",
    description="List all registered MCP tools with their metadata"
)
async def list_registered_tools(server=None) -> Dict[str, Any]:
    """
    List all registered tools with their metadata.
    
    Returns:
        Dictionary containing all registered tools and their information.
    """
    if server is None:
        return {
            'status': 'error',
            'message': 'Server context not available'
        }
    
    try:
        tools = server.registry.list_tools()
        return {
            'status': 'success',
            'result': {
                'tool_count': len(tools),
                'tools': tools
            }
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


@mcp.tool(
    name="pipeline_state",
    description="Get or update pipeline state information"
)
async def manage_pipeline_state(
    action: str = "get",
    updates: Dict[str, Any] = None,
    server=None
) -> Dict[str, Any]:
    """
    Manage pipeline state - get current state or update with new values.
    
    Args:
        action: Action to perform ("get", "update", "clear")
        updates: Dictionary of updates to apply (for "update" action)
        server: Server context (injected automatically)
        
    Returns:
        Dictionary containing pipeline state or operation result.
    """
    if server is None:
        return {
            'status': 'error',
            'message': 'Server context not available'
        }
    
    try:
        if action == "get":
            state = server.get_pipeline_state()
            return {
                'status': 'success',
                'result': {
                    'pipeline_state': state,
                    'state_keys': list(state.keys())
                }
            }
        
        elif action == "update":
            if updates is None:
                return {
                    'status': 'error',
                    'message': 'Updates dictionary required for update action'
                }
            
            server.update_pipeline_state(updates)
            return {
                'status': 'success',
                'result': {
                    'message': f'Updated {len(updates)} pipeline state items',
                    'updated_keys': list(updates.keys())
                }
            }
        
        elif action == "clear":
            server.clear_pipeline_state()
            return {
                'status': 'success',
                'result': {
                    'message': 'Pipeline state cleared'
                }
            }
        
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}. Use "get", "update", or "clear"'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage pipeline state: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


@mcp.tool(
    name="echo",
    description="Echo back input data for testing tool execution"
)
async def echo_tool(
    message: str,
    metadata: Dict[str, Any] = None,
    server=None
) -> Dict[str, Any]:
    """
    Simple echo tool for testing MCP tool execution.
    
    Args:
        message: Message to echo back
        metadata: Optional metadata to include in response
        server: Server context (injected automatically)
        
    Returns:
        Dictionary containing echoed message and metadata.
    """
    try:
        result = {
            'echoed_message': message,
            'timestamp': None,  # Would use datetime if imported
            'server_available': server is not None
        }
        
        if metadata:
            result['metadata'] = metadata
            
        if server:
            result['server_status'] = server.is_running()
        
        return {
            'status': 'success',
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Echo tool failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }