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
Base agent interface and common functionality for the agentic neurodata conversion system.

This module defines the abstract base class for all agents, providing a consistent
interface for agent lifecycle management, capability registration, and integration
with the MCP server.
"""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Callable, Optional
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration."""

    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class AgentCapability(Enum):
    """Agent capability enumeration."""

    DATASET_ANALYSIS = "dataset_analysis"
    METADATA_EXTRACTION = "metadata_extraction"
    FORMAT_DETECTION = "format_detection"
    CONVERSATION = "conversation"
    SCRIPT_GENERATION = "script_generation"
    CONVERSION_EXECUTION = "conversion_execution"
    VALIDATION = "validation"
    EVALUATION = "evaluation"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    REPORTING = "reporting"


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    This class provides the common interface and functionality that all agents
    must implement, including lifecycle management, capability registration,
    and integration with the MCP server.
    """

    def __init__(self, config: Optional[Any] = None, agent_id: Optional[str] = None):
        """
        Initialize the base agent.

        Args:
            config: Agent configuration object.
            agent_id: Optional agent identifier. If not provided, generates a UUID.
        """
        self.agent_id = agent_id or str(uuid.uuid4())
        self.config = config
        self.status = AgentStatus.INITIALIZING
        self.capabilities: set[AgentCapability] = set()
        self.metadata: dict[str, Any] = {}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.error_count = 0
        self.success_count = 0

        # Event handlers
        self._status_change_handlers: list[
            Callable[[AgentStatus, AgentStatus], None]
        ] = []
        self._error_handlers: list[Callable[[Exception], None]] = []

        logger.info(
            f"Initializing agent {self.agent_id} of type {self.__class__.__name__}"
        )

        # Initialize agent-specific components
        try:
            self._initialize()
            self.status = AgentStatus.READY
            logger.info(f"Agent {self.agent_id} initialized successfully")
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.error_count += 1
            logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            self._handle_error(e)
            raise

    @abstractmethod
    def _initialize(self) -> None:
        """
        Initialize agent-specific components.

        This method should be implemented by concrete agent classes to set up
        their specific functionality, register capabilities, and prepare for operation.
        """
        pass

    @abstractmethod
    async def process(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Process a task assigned to this agent.

        Args:
            task: Task dictionary containing task type, parameters, and context.

        Returns:
            Dictionary containing the processing result.

        Raises:
            NotImplementedError: If the agent doesn't support the task type.
            Exception: If processing fails.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> set[AgentCapability]:
        """
        Get the set of capabilities this agent provides.

        Returns:
            Set of AgentCapability enums representing what this agent can do.
        """
        pass

    def add_capability(self, capability: AgentCapability) -> None:
        """
        Add a capability to this agent.

        Args:
            capability: The capability to add.
        """
        self.capabilities.add(capability)
        logger.debug(f"Added capability {capability.value} to agent {self.agent_id}")

    def remove_capability(self, capability: AgentCapability) -> None:
        """
        Remove a capability from this agent.

        Args:
            capability: The capability to remove.
        """
        self.capabilities.discard(capability)
        logger.debug(
            f"Removed capability {capability.value} from agent {self.agent_id}"
        )

    def has_capability(self, capability: AgentCapability) -> bool:
        """
        Check if this agent has a specific capability.

        Args:
            capability: The capability to check for.

        Returns:
            True if the agent has the capability, False otherwise.
        """
        return capability in self.capabilities

    def can_handle_task(self, task: dict[str, Any]) -> bool:
        """
        Check if this agent can handle a specific task.

        Args:
            task: Task dictionary to check.

        Returns:
            True if the agent can handle the task, False otherwise.
        """
        task_type = task.get("type")
        if not task_type:
            return False

        # Map task types to capabilities
        task_capability_map = {
            "dataset_analysis": AgentCapability.DATASET_ANALYSIS,
            "metadata_extraction": AgentCapability.METADATA_EXTRACTION,
            "format_detection": AgentCapability.FORMAT_DETECTION,
            "conversation": AgentCapability.CONVERSATION,
            "script_generation": AgentCapability.SCRIPT_GENERATION,
            "conversion_execution": AgentCapability.CONVERSION_EXECUTION,
            "validation": AgentCapability.VALIDATION,
            "evaluation": AgentCapability.EVALUATION,
            "knowledge_graph": AgentCapability.KNOWLEDGE_GRAPH,
            "reporting": AgentCapability.REPORTING,
        }

        required_capability = task_capability_map.get(task_type)
        return required_capability is not None and self.has_capability(
            required_capability
        )

    async def execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a task with proper error handling and status management.

        Args:
            task: Task dictionary to execute.

        Returns:
            Dictionary containing the execution result.
        """
        if not self.can_handle_task(task):
            raise ValueError(
                f"Agent {self.agent_id} cannot handle task type: {task.get('type')}"
            )

        if self.status != AgentStatus.READY:
            raise RuntimeError(
                f"Agent {self.agent_id} is not ready (status: {self.status.value})"
            )

        # Update status and activity
        old_status = self.status
        self.status = AgentStatus.BUSY
        self.last_activity = datetime.utcnow()
        self._notify_status_change(old_status, self.status)

        try:
            logger.info(f"Agent {self.agent_id} executing task: {task.get('type')}")
            result = await self.process(task)

            # Update success metrics
            self.success_count += 1
            self.status = AgentStatus.READY
            self._notify_status_change(AgentStatus.BUSY, self.status)

            logger.info(f"Agent {self.agent_id} completed task successfully")
            return result

        except Exception as e:
            # Update error metrics and status
            self.error_count += 1
            self.status = AgentStatus.ERROR
            self._notify_status_change(AgentStatus.BUSY, self.status)

            logger.error(f"Agent {self.agent_id} task execution failed: {e}")
            self._handle_error(e)
            raise

    def get_status(self) -> dict[str, Any]:
        """
        Get comprehensive agent status information.

        Returns:
            Dictionary containing agent status, capabilities, metrics, and metadata.
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.__class__.__name__,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "metadata": self.metadata.copy(),
        }

    def update_metadata(self, updates: dict[str, Any]) -> None:
        """
        Update agent metadata.

        Args:
            updates: Dictionary of metadata updates to apply.
        """
        self.metadata.update(updates)
        logger.debug(f"Updated metadata for agent {self.agent_id}")

    def reset_metrics(self) -> None:
        """Reset agent performance metrics."""
        self.success_count = 0
        self.error_count = 0
        logger.info(f"Reset metrics for agent {self.agent_id}")

    def add_status_change_handler(
        self, handler: Callable[[AgentStatus, AgentStatus], None]
    ) -> None:
        """
        Add a status change event handler.

        Args:
            handler: Function to call when status changes. Receives (old_status, new_status).
        """
        self._status_change_handlers.append(handler)

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """
        Add an error event handler.

        Args:
            handler: Function to call when errors occur. Receives the exception.
        """
        self._error_handlers.append(handler)

    def _notify_status_change(
        self, old_status: AgentStatus, new_status: AgentStatus
    ) -> None:
        """
        Notify registered handlers of status changes.

        Args:
            old_status: Previous agent status.
            new_status: New agent status.
        """
        for handler in self._status_change_handlers:
            try:
                handler(old_status, new_status)
            except Exception as e:
                logger.error(f"Status change handler failed: {e}")

    def _handle_error(self, error: Exception) -> None:
        """
        Handle errors by notifying registered error handlers.

        Args:
            error: The exception that occurred.
        """
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the agent.

        This method should be called when the agent is no longer needed.
        Concrete implementations can override this to perform cleanup.
        """
        old_status = self.status
        self.status = AgentStatus.STOPPED
        self._notify_status_change(old_status, self.status)
        logger.info(f"Agent {self.agent_id} shutdown completed")

    def __str__(self) -> str:
        """String representation of the agent."""
        return (
            f"{self.__class__.__name__}(id={self.agent_id}, status={self.status.value})"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (
            f"{self.__class__.__name__}(id={self.agent_id}, status={self.status.value}, "
            f"capabilities={len(self.capabilities)}, success={self.success_count}, "
            f"errors={self.error_count})"
        )


class AgentRegistry:
    """
    Registry for managing agent instances and their lifecycle.

    This class provides centralized management of agents, including registration,
    discovery, task routing, and lifecycle management.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self.agents: dict[str, BaseAgent] = {}
        self.agents_by_type: dict[str, list[BaseAgent]] = {}
        self.agents_by_capability: dict[AgentCapability, list[BaseAgent]] = {}

        logger.info("Initialized agent registry")

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the registry.

        Args:
            agent: The agent instance to register.

        Raises:
            ValueError: If an agent with the same ID is already registered.
        """
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent with ID {agent.agent_id} is already registered")

        # Register by ID
        self.agents[agent.agent_id] = agent

        # Register by type
        agent_type = agent.__class__.__name__
        if agent_type not in self.agents_by_type:
            self.agents_by_type[agent_type] = []
        self.agents_by_type[agent_type].append(agent)

        # Register by capabilities
        for capability in agent.get_capabilities():
            if capability not in self.agents_by_capability:
                self.agents_by_capability[capability] = []
            self.agents_by_capability[capability].append(agent)

        logger.info(f"Registered agent {agent.agent_id} of type {agent_type}")

    def unregister_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Unregister an agent from the registry.

        Args:
            agent_id: ID of the agent to unregister.

        Returns:
            The unregistered agent instance, or None if not found.
        """
        agent = self.agents.pop(agent_id, None)
        if not agent:
            return None

        # Remove from type registry
        agent_type = agent.__class__.__name__
        if agent_type in self.agents_by_type:
            self.agents_by_type[agent_type] = [
                a for a in self.agents_by_type[agent_type] if a.agent_id != agent_id
            ]
            if not self.agents_by_type[agent_type]:
                del self.agents_by_type[agent_type]

        # Remove from capability registry
        for capability in agent.get_capabilities():
            if capability in self.agents_by_capability:
                self.agents_by_capability[capability] = [
                    a
                    for a in self.agents_by_capability[capability]
                    if a.agent_id != agent_id
                ]
                if not self.agents_by_capability[capability]:
                    del self.agents_by_capability[capability]

        logger.info(f"Unregistered agent {agent_id}")
        return agent

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by ID.

        Args:
            agent_id: ID of the agent to retrieve.

        Returns:
            The agent instance, or None if not found.
        """
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> list[BaseAgent]:
        """
        Get all agents of a specific type.

        Args:
            agent_type: The agent class name to search for.

        Returns:
            List of agents of the specified type.
        """
        return self.agents_by_type.get(agent_type, []).copy()

    def get_agents_by_capability(self, capability: AgentCapability) -> list[BaseAgent]:
        """
        Get all agents that have a specific capability.

        Args:
            capability: The capability to search for.

        Returns:
            List of agents with the specified capability.
        """
        return self.agents_by_capability.get(capability, []).copy()

    def find_agent_for_task(self, task: dict[str, Any]) -> Optional[BaseAgent]:
        """
        Find the best agent to handle a specific task.

        Args:
            task: Task dictionary to find an agent for.

        Returns:
            The best available agent for the task, or None if no suitable agent found.
        """
        # Get task type and find agents with the required capability
        task_type = task.get("type")
        if not task_type:
            return None

        # Find agents that can handle this task
        suitable_agents = [
            agent
            for agent in self.agents.values()
            if agent.can_handle_task(task) and agent.status == AgentStatus.READY
        ]

        if not suitable_agents:
            return None

        # Simple selection strategy: return the agent with the lowest error rate
        return min(
            suitable_agents,
            key=lambda a: a.error_count / max(a.success_count + a.error_count, 1),
        )

    def get_registry_status(self) -> dict[str, Any]:
        """
        Get comprehensive registry status information.

        Returns:
            Dictionary containing registry statistics and agent information.
        """
        total_agents = len(self.agents)
        agents_by_status = {}

        for agent in self.agents.values():
            status = agent.status.value
            agents_by_status[status] = agents_by_status.get(status, 0) + 1

        return {
            "total_agents": total_agents,
            "agents_by_status": agents_by_status,
            "agents_by_type": {
                agent_type: len(agents)
                for agent_type, agents in self.agents_by_type.items()
            },
            "capabilities_available": list(self.agents_by_capability.keys()),
            "agent_ids": list(self.agents.keys()),
        }

    async def shutdown_all_agents(self) -> None:
        """
        Gracefully shutdown all registered agents.

        This method should be called during application shutdown.
        """
        logger.info(f"Shutting down {len(self.agents)} agents")

        # Shutdown all agents concurrently
        shutdown_tasks = [agent.shutdown() for agent in self.agents.values()]
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        # Clear all registries
        self.agents.clear()
        self.agents_by_type.clear()
        self.agents_by_capability.clear()

        logger.info("All agents shutdown completed")

    def __len__(self) -> int:
        """Return the number of registered agents."""
        return len(self.agents)

    def __contains__(self, agent_id: str) -> bool:
        """Check if an agent ID is registered."""
        return agent_id in self.agents

    def __iter__(self):
        """Iterate over all registered agents."""
        return iter(self.agents.values())
