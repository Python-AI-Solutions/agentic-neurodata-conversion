"""
Unit tests for AgentRegistry.

Tests cover:
- Agent registration with all metadata
- Agent retrieval (existing and non-existent)
- Listing all agents (empty and populated)
- Agent unregistration (existing and non-existent)
- Multiple agent registrations
- Agent overwrite on duplicate registration
"""

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry


class TestAgentRegistry:
    """Test AgentRegistry class."""

    def test_list_agents_returns_empty_list_initially(self) -> None:
        """Test list_agents returns empty list when no agents registered."""
        registry = AgentRegistry()
        agents = registry.list_agents()
        assert agents == []
        assert isinstance(agents, list)

    def test_register_agent_adds_agent_to_registry(self) -> None:
        """Test register_agent adds agent to registry."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["initialize_session", "handle_clarification"],
        )

        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_name"] == "conversation_agent"

    def test_register_agent_stores_all_metadata(self) -> None:
        """Test register_agent stores all agent metadata correctly."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversion_agent",
            agent_type="conversion",
            base_url="http://localhost:3002",
            capabilities=["detect_format", "convert_to_nwb"],
        )

        agent = registry.get_agent("conversion_agent")
        assert agent is not None
        assert agent["agent_name"] == "conversion_agent"
        assert agent["agent_type"] == "conversion"
        assert agent["base_url"] == "http://localhost:3002"
        assert agent["capabilities"] == ["detect_format", "convert_to_nwb"]

    def test_get_agent_returns_correct_agent_info(self) -> None:
        """Test get_agent returns correct agent information."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="evaluation_agent",
            agent_type="evaluation",
            base_url="http://localhost:3003",
            capabilities=["validate_nwb", "generate_report"],
        )

        agent = registry.get_agent("evaluation_agent")
        assert agent is not None
        assert isinstance(agent, dict)
        assert agent["agent_name"] == "evaluation_agent"
        assert agent["agent_type"] == "evaluation"
        assert agent["base_url"] == "http://localhost:3003"
        assert len(agent["capabilities"]) == 2
        assert "validate_nwb" in agent["capabilities"]
        assert "generate_report" in agent["capabilities"]

    def test_get_agent_returns_none_for_nonexistent_agent(self) -> None:
        """Test get_agent returns None for non-existent agent."""
        registry = AgentRegistry()
        agent = registry.get_agent("nonexistent_agent")
        assert agent is None

    def test_list_agents_returns_all_registered_agents(self) -> None:
        """Test list_agents returns all registered agents."""
        registry = AgentRegistry()

        # Register multiple agents
        registry.register_agent(
            agent_name="agent_1",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["cap1"],
        )
        registry.register_agent(
            agent_name="agent_2",
            agent_type="conversion",
            base_url="http://localhost:3002",
            capabilities=["cap2"],
        )
        registry.register_agent(
            agent_name="agent_3",
            agent_type="evaluation",
            base_url="http://localhost:3003",
            capabilities=["cap3"],
        )

        agents = registry.list_agents()
        assert len(agents) == 3
        agent_names = [agent["agent_name"] for agent in agents]
        assert "agent_1" in agent_names
        assert "agent_2" in agent_names
        assert "agent_3" in agent_names

    def test_unregister_agent_removes_agent(self) -> None:
        """Test unregister_agent removes agent from registry."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="temp_agent",
            agent_type="temporary",
            base_url="http://localhost:4000",
            capabilities=["temp_capability"],
        )

        # Verify agent exists
        assert registry.get_agent("temp_agent") is not None
        assert len(registry.list_agents()) == 1

        # Unregister agent
        registry.unregister_agent("temp_agent")

        # Verify agent is removed
        assert registry.get_agent("temp_agent") is None
        assert len(registry.list_agents()) == 0

    def test_unregister_agent_handles_nonexistent_agent_gracefully(self) -> None:
        """Test unregister_agent handles non-existent agent without error."""
        registry = AgentRegistry()

        # Should not raise error
        registry.unregister_agent("nonexistent_agent")

        # Registry should still be empty
        assert len(registry.list_agents()) == 0

    def test_multiple_agent_registrations(self) -> None:
        """Test multiple agent registrations with different types."""
        registry = AgentRegistry()

        # Register conversation agent
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["initialize_session", "handle_clarification"],
        )

        # Register conversion agent
        registry.register_agent(
            agent_name="conversion_agent",
            agent_type="conversion",
            base_url="http://localhost:3002",
            capabilities=["detect_format", "convert_to_nwb"],
        )

        # Register evaluation agent
        registry.register_agent(
            agent_name="evaluation_agent",
            agent_type="evaluation",
            base_url="http://localhost:3003",
            capabilities=["validate_nwb", "generate_report"],
        )

        # Verify all agents are registered
        assert len(registry.list_agents()) == 3

        # Verify each agent can be retrieved correctly
        conv_agent = registry.get_agent("conversation_agent")
        assert conv_agent is not None
        assert conv_agent["agent_type"] == "conversation"

        conversion_agent = registry.get_agent("conversion_agent")
        assert conversion_agent is not None
        assert conversion_agent["agent_type"] == "conversion"

        eval_agent = registry.get_agent("evaluation_agent")
        assert eval_agent is not None
        assert eval_agent["agent_type"] == "evaluation"

    def test_agent_overwrite_on_duplicate_registration(self) -> None:
        """Test agent gets overwritten on duplicate registration."""
        registry = AgentRegistry()

        # Register agent first time
        registry.register_agent(
            agent_name="test_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["capability_1"],
        )

        # Verify initial registration
        agent = registry.get_agent("test_agent")
        assert agent is not None
        assert agent["base_url"] == "http://localhost:3001"
        assert agent["capabilities"] == ["capability_1"]
        assert len(registry.list_agents()) == 1

        # Register same agent again with different metadata
        registry.register_agent(
            agent_name="test_agent",
            agent_type="conversion",
            base_url="http://localhost:4000",
            capabilities=["capability_2", "capability_3"],
        )

        # Verify agent was overwritten (not duplicated)
        agent = registry.get_agent("test_agent")
        assert agent is not None
        assert agent["agent_type"] == "conversion"  # Updated
        assert agent["base_url"] == "http://localhost:4000"  # Updated
        assert agent["capabilities"] == ["capability_2", "capability_3"]  # Updated
        assert len(registry.list_agents()) == 1  # Still only one agent

    def test_register_agent_with_empty_capabilities(self) -> None:
        """Test registering agent with empty capabilities list."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="minimal_agent",
            agent_type="minimal",
            base_url="http://localhost:5000",
            capabilities=[],
        )

        agent = registry.get_agent("minimal_agent")
        assert agent is not None
        assert agent["capabilities"] == []

    def test_list_agents_returns_copy_not_reference(self) -> None:
        """Test list_agents returns a new list, not internal reference."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="agent_1",
            agent_type="test",
            base_url="http://localhost:3001",
            capabilities=["cap1"],
        )

        # Get list of agents
        agents_list_1 = registry.list_agents()

        # Register another agent
        registry.register_agent(
            agent_name="agent_2",
            agent_type="test",
            base_url="http://localhost:3002",
            capabilities=["cap2"],
        )

        # Get list again
        agents_list_2 = registry.list_agents()

        # First list should not be affected by subsequent registration
        assert len(agents_list_1) == 1
        assert len(agents_list_2) == 2
