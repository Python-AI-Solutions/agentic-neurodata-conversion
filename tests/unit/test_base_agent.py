"""
Unit tests for the base agent framework.

Tests the BaseAgent abstract class, AgentStatus, AgentCapability, and AgentRegistry.
"""

from typing import Any

import pytest

# Import the actual components that should be implemented
from agentic_neurodata_conversion.agents.base import (
    AgentCapability,
    AgentRegistry,
    AgentStatus,
    BaseAgent,
)


class TestAgentStatus:
    """Test the AgentStatus enum."""

    @pytest.mark.unit
    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.INITIALIZING.value == "initializing"
        assert AgentStatus.READY.value == "ready"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.STOPPED.value == "stopped"


class TestAgentCapability:
    """Test the AgentCapability enum."""

    @pytest.mark.unit
    def test_agent_capability_values(self):
        """Test AgentCapability enum values."""
        assert AgentCapability.DATASET_ANALYSIS.value == "dataset_analysis"
        assert AgentCapability.METADATA_EXTRACTION.value == "metadata_extraction"
        assert AgentCapability.FORMAT_DETECTION.value == "format_detection"
        assert AgentCapability.CONVERSATION.value == "conversation"


class ConcreteTestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    def __init__(self, config=None, agent_id=None):
        self.process_called = False
        self.test_capabilities = {
            AgentCapability.DATASET_ANALYSIS,
            AgentCapability.CONVERSATION,
        }
        super().__init__(config, agent_id)

    def _initialize(self) -> None:
        """Initialize test agent capabilities."""
        for capability in self.test_capabilities:
            self.add_capability(capability)

    async def process(self, task: dict[str, Any]) -> dict[str, Any]:
        """Test implementation of task processing."""
        self.process_called = True

        task_type = task.get("type")
        if task.get("fail"):
            raise RuntimeError("Task processing failed")

        return {
            "result": "success",
            "task_type": task_type,
            "processed": True,
            "agent_id": self.agent_id,
        }

    def get_capabilities(self) -> set[AgentCapability]:
        """Return test agent capabilities."""
        return self.test_capabilities.copy()


class TestBaseAgent:
    """Test the BaseAgent abstract class."""

    @pytest.fixture
    def test_agent(self):
        """Create a test agent instance."""
        return ConcreteTestAgent(config={"test": True}, agent_id="test_agent_123")

    @pytest.mark.unit
    def test_agent_initialization(self, test_agent):
        """Test agent initialization."""
        assert test_agent.agent_id == "test_agent_123"
        assert test_agent.status == AgentStatus.READY
        assert test_agent.success_count == 0
        assert test_agent.error_count == 0
        assert len(test_agent.capabilities) == 2
        assert AgentCapability.DATASET_ANALYSIS in test_agent.capabilities
        assert AgentCapability.CONVERSATION in test_agent.capabilities

    @pytest.mark.unit
    def test_capability_management(self, test_agent):
        """Test capability management methods."""
        # Test has_capability
        assert test_agent.has_capability(AgentCapability.DATASET_ANALYSIS)
        assert test_agent.has_capability(AgentCapability.CONVERSATION)
        assert not test_agent.has_capability(AgentCapability.FORMAT_DETECTION)

        # Test add_capability
        test_agent.add_capability(AgentCapability.FORMAT_DETECTION)
        assert test_agent.has_capability(AgentCapability.FORMAT_DETECTION)

        # Test remove_capability
        test_agent.remove_capability(AgentCapability.CONVERSATION)
        assert not test_agent.has_capability(AgentCapability.CONVERSATION)

    @pytest.mark.unit
    def test_can_handle_task(self, test_agent):
        """Test task handling capability check."""
        # Should handle dataset analysis
        task1 = {"type": "dataset_analysis", "params": {}}
        assert test_agent.can_handle_task(task1)

        # Should handle conversation
        task2 = {"type": "conversation", "params": {}}
        assert test_agent.can_handle_task(task2)

        # Should not handle format detection (not in capabilities)
        task3 = {"type": "format_detection", "params": {}}
        assert not test_agent.can_handle_task(task3)

        # Should not handle unknown task type
        task4 = {"type": "unknown_task", "params": {}}
        assert not test_agent.can_handle_task(task4)

    @pytest.mark.unit
    async def test_successful_task_execution(self, test_agent):
        """Test successful task execution."""
        task = {"type": "dataset_analysis", "params": {"test": "value"}}

        result = await test_agent.execute_task(task)

        assert result["result"] == "success"
        assert result["task_type"] == "dataset_analysis"
        assert result["processed"] is True
        assert result["agent_id"] == test_agent.agent_id
        assert test_agent.process_called
        assert test_agent.status == AgentStatus.READY
        assert test_agent.success_count == 1
        assert test_agent.error_count == 0

    @pytest.mark.unit
    async def test_task_execution_failure(self, test_agent):
        """Test task execution failure."""
        # Use a supported task type that will fail in processing
        task = {"type": "dataset_analysis", "fail": True}

        with pytest.raises(RuntimeError, match="Task processing failed"):
            await test_agent.execute_task(task)

        assert test_agent.status == AgentStatus.ERROR
        assert test_agent.success_count == 0
        assert test_agent.error_count == 1

    @pytest.mark.unit
    async def test_unsupported_task_execution(self, test_agent):
        """Test execution of unsupported task."""
        task = {"type": "format_detection", "params": {}}

        with pytest.raises(ValueError, match="cannot handle task type"):
            await test_agent.execute_task(task)

    @pytest.mark.unit
    async def test_execution_when_not_ready(self, test_agent):
        """Test execution when agent is not ready."""
        test_agent.status = AgentStatus.BUSY
        task = {"type": "dataset_analysis", "params": {}}

        with pytest.raises(RuntimeError, match="is not ready"):
            await test_agent.execute_task(task)

    @pytest.mark.unit
    def test_get_status(self, test_agent):
        """Test getting agent status."""
        status = test_agent.get_status()

        assert status["agent_id"] == "test_agent_123"
        assert status["agent_type"] == "ConcreteTestAgent"
        assert status["status"] == "ready"
        assert len(status["capabilities"]) == 2
        assert "dataset_analysis" in status["capabilities"]
        assert "conversation" in status["capabilities"]
        assert status["success_count"] == 0
        assert status["error_count"] == 0
        assert "created_at" in status
        assert "last_activity" in status

    @pytest.mark.unit
    def test_metadata_management(self, test_agent):
        """Test metadata management."""
        # Update metadata
        test_agent.update_metadata({"test_key": "test_value", "number": 42})

        status = test_agent.get_status()
        assert status["metadata"]["test_key"] == "test_value"
        assert status["metadata"]["number"] == 42

    @pytest.mark.unit
    def test_metrics_reset(self, test_agent):
        """Test metrics reset."""
        # Set some metrics
        test_agent.success_count = 5
        test_agent.error_count = 2

        # Reset metrics
        test_agent.reset_metrics()

        assert test_agent.success_count == 0
        assert test_agent.error_count == 0

    @pytest.mark.unit
    async def test_agent_shutdown(self, test_agent):
        """Test agent shutdown."""
        await test_agent.shutdown()
        assert test_agent.status == AgentStatus.STOPPED


class TestAgentRegistry:
    """Test the AgentRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create an agent registry."""
        return AgentRegistry()

    @pytest.fixture
    def test_agents(self):
        """Create test agents."""
        agent1 = ConcreteTestAgent(agent_id="agent_1")
        agent2 = ConcreteTestAgent(agent_id="agent_2")
        return agent1, agent2

    @pytest.mark.unit
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry) == 0
        assert len(registry.agents) == 0
        assert len(registry.agents_by_type) == 0
        assert len(registry.agents_by_capability) == 0

    @pytest.mark.unit
    def test_agent_registration(self, registry, test_agents):
        """Test agent registration."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        assert len(registry) == 2
        assert "agent_1" in registry
        assert "agent_2" in registry
        assert registry.get_agent("agent_1") == agent1
        assert registry.get_agent("agent_2") == agent2

    @pytest.mark.unit
    def test_duplicate_registration_error(self, registry, test_agents):
        """Test error on duplicate agent registration."""
        agent1, _ = test_agents

        registry.register_agent(agent1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register_agent(agent1)

    @pytest.mark.unit
    def test_agent_unregistration(self, registry, test_agents):
        """Test agent unregistration."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        unregistered = registry.unregister_agent("agent_1")

        assert unregistered == agent1
        assert len(registry) == 1
        assert "agent_1" not in registry
        assert "agent_2" in registry

    @pytest.mark.unit
    def test_get_agents_by_type(self, registry, test_agents):
        """Test getting agents by type."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        agents = registry.get_agents_by_type("ConcreteTestAgent")
        assert len(agents) == 2
        assert agent1 in agents
        assert agent2 in agents

    @pytest.mark.unit
    def test_get_agents_by_capability(self, registry, test_agents):
        """Test getting agents by capability."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        agents = registry.get_agents_by_capability(AgentCapability.DATASET_ANALYSIS)
        assert len(agents) == 2
        assert agent1 in agents
        assert agent2 in agents

    @pytest.mark.unit
    def test_find_agent_for_task(self, registry, test_agents):
        """Test finding agent for task."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        task = {"type": "dataset_analysis", "params": {}}
        found_agent = registry.find_agent_for_task(task)

        assert found_agent is not None
        assert found_agent in [agent1, agent2]

    @pytest.mark.unit
    def test_registry_status(self, registry, test_agents):
        """Test registry status reporting."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        status = registry.get_registry_status()

        assert status["total_agents"] == 2
        assert status["agents_by_status"]["ready"] == 2
        assert status["agents_by_type"]["ConcreteTestAgent"] == 2
        assert len(status["agent_ids"]) == 2

    @pytest.mark.unit
    async def test_shutdown_all_agents(self, registry, test_agents):
        """Test shutting down all agents."""
        agent1, agent2 = test_agents

        registry.register_agent(agent1)
        registry.register_agent(agent2)

        await registry.shutdown_all_agents()

        assert len(registry) == 0
        assert agent1.status == AgentStatus.STOPPED
        assert agent2.status == AgentStatus.STOPPED
