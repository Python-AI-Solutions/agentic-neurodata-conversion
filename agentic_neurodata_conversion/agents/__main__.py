"""CLI entry point for starting agents as separate processes."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING, Literal

from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env file
load_dotenv()

from agentic_neurodata_conversion.config import (  # noqa: E402
    AgentConfig,
    get_conversation_agent_config,
    get_conversion_agent_config,
    get_evaluation_agent_config,
)

if TYPE_CHECKING:
    from agentic_neurodata_conversion.agents.base_agent import BaseAgent

AgentType = Literal["conversation", "conversion", "evaluation"]


def get_agent_config(agent_type: AgentType) -> AgentConfig:
    """
    Get configuration for specified agent type.

    Args:
        agent_type: Type of agent to configure

    Returns:
        Agent configuration

    Raises:
        ValueError: If agent type is invalid
    """
    if agent_type == "conversation":
        return get_conversation_agent_config()
    elif agent_type == "conversion":
        return get_conversion_agent_config()
    elif agent_type == "evaluation":
        return get_evaluation_agent_config()
    else:
        raise ValueError(
            f"Invalid agent type: {agent_type}. "
            "Must be one of: conversation, conversion, evaluation"
        )


def start_agent(agent_type: AgentType) -> None:
    """
    Start agent and register with MCP server.

    Args:
        agent_type: Type of agent to start

    Raises:
        SystemExit: If registration fails or agent cannot be started
    """
    print(f"Starting {agent_type} agent...")

    # Get configuration
    config = get_agent_config(agent_type)

    # Import and instantiate agent
    # Note: Specialized agents will be implemented in later phases
    # For now, we'll use placeholder implementations
    agent: BaseAgent
    if agent_type == "conversation":
        from agentic_neurodata_conversion.agents.conversation_agent import (
            ConversationAgent,
        )

        agent = ConversationAgent(config)
    elif agent_type == "conversion":
        from agentic_neurodata_conversion.agents.conversion_agent import (
            ConversionAgent,
        )

        agent = ConversionAgent(config)
    elif agent_type == "evaluation":
        from agentic_neurodata_conversion.agents.evaluation_agent import (
            EvaluationAgent,
        )

        agent = EvaluationAgent(config)
    else:
        # This should never happen due to validation above, but satisfies mypy
        raise ValueError(f"Unexpected agent type: {agent_type}")

    # Register with MCP server (handle async registration)
    print(f"Registering {agent_type} agent with MCP server...")
    try:
        # Try to get or create event loop for registration
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Loop is running - create a task and wait for it
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, agent.register_with_server())
                    response = future.result()
            else:
                # Loop exists but not running - use it
                response = loop.run_until_complete(agent.register_with_server())
        except RuntimeError:
            # No loop exists - create one with asyncio.run (normal case)
            response = asyncio.run(agent.register_with_server())

        print(f"Registration successful: {response}")
    except Exception as e:
        print(f"Registration failed: {e}")
        print(f"  Note: MCP server must be running at {config.mcp_server_url}")
        sys.exit(1)

    # Create FastAPI HTTP server
    print(f"Creating HTTP server on port {config.agent_port}...")
    app = agent.create_agent_server()

    # Start server
    print(f"{agent_type.capitalize()} agent ready")
    print(f"  - Listening on http://0.0.0.0:{config.agent_port}")
    print(f"  - MCP server: {config.mcp_server_url}")
    print(f"  - LLM provider: {config.llm_provider}")
    print(f"  - Capabilities: {', '.join(agent.get_capabilities())}")

    # Run uvicorn server
    # Note: Using single worker with async timeouts to prevent blocking
    # Multi-worker mode requires app factory pattern which conflicts with agent registration
    uvicorn.run(app, host="0.0.0.0", port=config.agent_port, log_level="info")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python -m agentic_neurodata_conversion.agents <agent_type>")
        print("Agent types: conversation, conversion, evaluation")
        sys.exit(1)

    agent_type = sys.argv[1]

    # Validate agent type
    valid_types: list[AgentType] = ["conversation", "conversion", "evaluation"]
    if agent_type not in valid_types:
        print(f"Error: Invalid agent type '{agent_type}'")
        print(f"Valid types: {', '.join(valid_types)}")
        sys.exit(1)

    # Start agent (synchronous function that handles async registration internally)
    try:
        start_agent(agent_type)  # type: ignore
    except KeyboardInterrupt:
        print(f"\n{agent_type.capitalize()} agent stopped")
    except Exception as e:
        print(f"\nError starting agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
