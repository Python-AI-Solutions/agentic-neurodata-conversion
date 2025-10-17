"""
Agent Registry for MCP Server.

Implements in-memory agent registry that maintains information about all active
agents in the system. Used by the message router and MCP server for agent discovery.

All operations are synchronous as this is an in-memory-only component.
"""

from typing import Optional, TypedDict


class AgentInfo(TypedDict):
    """Type definition for agent information dictionary."""

    agent_name: str
    agent_type: str
    base_url: str
    capabilities: list[str]


class AgentRegistry:
    """
    In-memory agent registry for tracking active agents.

    Maintains a simple dictionary mapping agent names to their metadata including
    agent type, base URL, and capabilities. All operations are synchronous and
    thread-safe for single-threaded async applications.

    Agent information structure:
    {
        "agent_name": str,
        "agent_type": str,      # e.g., "conversation", "conversion", "evaluation"
        "base_url": str,        # e.g., "http://localhost:3001"
        "capabilities": list[str]  # e.g., ["initialize_session", "detect_format"]
    }
    """

    def __init__(self) -> None:
        """Initialize AgentRegistry with empty agent dictionary."""
        self._agents: dict[str, AgentInfo] = {}

    def register_agent(
        self,
        agent_name: str,
        agent_type: str,
        base_url: str,
        capabilities: list[str],
    ) -> None:
        """
        Register an agent in the registry.

        If an agent with the same name already exists, it will be overwritten
        with the new metadata.

        Args:
            agent_name: Unique identifier for the agent
            agent_type: Type of agent (e.g., "conversation", "conversion", "evaluation")
            base_url: Base URL for agent communication (e.g., "http://localhost:3001")
            capabilities: List of capabilities the agent provides
        """
        self._agents[agent_name] = AgentInfo(
            agent_name=agent_name,
            agent_type=agent_type,
            base_url=base_url,
            capabilities=capabilities,
        )

    def get_agent(self, agent_name: str) -> Optional[AgentInfo]:
        """
        Retrieve agent information by name.

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            AgentInfo dictionary containing agent metadata if found, None otherwise
        """
        return self._agents.get(agent_name)

    def list_agents(self) -> list[AgentInfo]:
        """
        List all registered agents.

        Returns:
            List of all AgentInfo dictionaries. Returns empty list if
            no agents are registered. Returns a new list to prevent external
            modifications.
        """
        return list(self._agents.values())

    def unregister_agent(self, agent_name: str) -> None:
        """
        Remove an agent from the registry.

        This operation is idempotent - it will not raise an error if the agent
        does not exist.

        Args:
            agent_name: Name of the agent to remove
        """
        self._agents.pop(agent_name, None)
