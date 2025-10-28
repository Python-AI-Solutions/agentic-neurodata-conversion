"""Base agent abstract class for MCP conversion pipeline."""

from abc import ABC, abstractmethod
import asyncio
import logging
import time
from typing import Any, Optional

from anthropic import APIError as AnthropicAPIError
from anthropic import AsyncAnthropic
from anthropic import RateLimitError as AnthropicRateLimitError
from fastapi import FastAPI
import httpx
from httpx import AsyncClient
from openai import APIError as OpenAIAPIError
from openai import AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import SessionContext

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the MCP conversion pipeline.

    Provides common functionality:
    - LLM integration (Anthropic and OpenAI)
    - MCP server communication
    - HTTP server creation for receiving messages
    - Session context management
    - Retry logic with exponential backoff
    """

    def __init__(self, config: AgentConfig) -> None:
        """
        Initialize base agent with configuration.

        Args:
            config: Agent configuration including LLM settings
        """
        self.config = config
        self.agent_name = config.agent_name
        self.agent_type = config.agent_type
        self.mcp_server_url = config.mcp_server_url
        # HTTP client with timeout for agent communication (5 min for long LLM responses)
        self.http_client = AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
        self.llm_client = self._initialize_llm_client()

    def _initialize_llm_client(self) -> Any:
        """
        Initialize LLM client based on provider (Anthropic or OpenAI).

        Returns:
            LLM client instance (AsyncAnthropic or AsyncOpenAI)

        Raises:
            ValueError: If LLM provider is not supported
        """
        if self.config.llm_provider == "anthropic":
            # 3 minute timeout for LLM API calls (metadata extraction can be slow)
            return AsyncAnthropic(
                api_key=self.config.llm_api_key,
                timeout=httpx.Timeout(180.0, connect=10.0)
            )
        elif self.config.llm_provider == "openai":
            return AsyncOpenAI(
                api_key=self.config.llm_api_key,
                timeout=httpx.Timeout(180.0, connect=10.0)
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

    async def register_with_server(self) -> dict[str, Any]:
        """
        Register agent with MCP server.

        Sends agent metadata including name, type, base URL, and capabilities
        to the MCP server's internal registration endpoint.

        Returns:
            Registration response from MCP server

        Raises:
            httpx.HTTPError: If registration request fails
        """
        registration_data = {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "base_url": f"http://localhost:{self.config.agent_port}",  # Use localhost not 0.0.0.0 for cross-platform compatibility
            "capabilities": self.get_capabilities(),
        }

        response = await self.http_client.post(
            f"{self.mcp_server_url}/internal/register_agent",
            json=registration_data,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_session_context(self, session_id: str) -> SessionContext:
        """
        Get session context from MCP server.

        Args:
            session_id: Session identifier

        Returns:
            Session context model

        Raises:
            httpx.HTTPError: If request fails
        """
        response = await self.http_client.get(
            f"{self.mcp_server_url}/internal/sessions/{session_id}/context"
        )
        response.raise_for_status()
        return SessionContext(**response.json())

    async def update_session_context(
        self, session_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update session context on MCP server.

        Args:
            session_id: Session identifier
            updates: Dictionary of fields to update

        Returns:
            Update response from MCP server

        Raises:
            httpx.HTTPError: If update request fails
        """
        response = await self.http_client.patch(
            f"{self.mcp_server_url}/internal/sessions/{session_id}/context",
            json=updates,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def call_llm(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_retries: int = 5,
    ) -> str:
        """
        Call LLM with retry logic and exponential backoff.

        Handles both Anthropic and OpenAI providers with appropriate retry logic:
        - Rate limit errors: Exponential backoff (2^attempt seconds)
        - API errors: Linear backoff (1 + attempt seconds)
        - Max retries: 5 by default

        Args:
            prompt: User prompt to send to LLM
            system_message: Optional system message for context
            max_retries: Maximum number of retry attempts

        Returns:
            LLM response text

        Raises:
            AnthropicRateLimitError: If max retries exceeded for Anthropic
            OpenAIRateLimitError: If max retries exceeded for OpenAI
            AnthropicAPIError: If API error persists after retries for Anthropic
            OpenAIAPIError: If API error persists after retries for OpenAI
        """
        for attempt in range(max_retries):
            try:
                if self.config.llm_provider == "anthropic":
                    logger.info(f"[{self.agent_name}] Calling Anthropic LLM (attempt {attempt + 1}/{max_retries})...")
                    call_start = time.time()
                    # Wrap with asyncio.wait_for for absolute timeout (3 minutes)
                    response = await asyncio.wait_for(
                        self.llm_client.messages.create(
                            model=self.config.llm_model,
                            max_tokens=self.config.max_tokens,
                            temperature=self.config.temperature,
                            system=system_message if system_message else "",
                            messages=[{"role": "user", "content": prompt}],
                        ),
                        timeout=180.0
                    )
                    call_elapsed = time.time() - call_start
                    text: str = response.content[0].text
                    logger.info(f"[{self.agent_name}] Anthropic LLM call successful in {call_elapsed:.2f}s (response: {len(text)} chars)")
                    return text

                elif self.config.llm_provider == "openai":
                    logger.info(f"[{self.agent_name}] Calling OpenAI LLM (attempt {attempt + 1}/{max_retries})...")
                    call_start = time.time()
                    messages = []
                    if system_message:
                        messages.append({"role": "system", "content": system_message})
                    messages.append({"role": "user", "content": prompt})

                    # Wrap with asyncio.wait_for for absolute timeout (3 minutes)
                    response = await asyncio.wait_for(
                        self.llm_client.chat.completions.create(
                            model=self.config.llm_model,
                            max_tokens=self.config.max_tokens,
                            temperature=self.config.temperature,
                            messages=messages,
                        ),
                        timeout=180.0
                    )
                    call_elapsed = time.time() - call_start
                    content: Optional[str] = response.choices[0].message.content
                    logger.info(f"[{self.agent_name}] OpenAI LLM call successful in {call_elapsed:.2f}s (response: {len(content or '')} chars)")
                    return content or ""

            except asyncio.TimeoutError as e:
                # Timeout after 180s - treat as temporary failure and retry
                logger.warning(f"[{self.agent_name}] LLM call timed out after 180s (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"LLM call timed out after {max_retries} attempts (180s each)") from e
                wait_time = 2 + attempt  # 2s, 3s, 4s, 5s, 6s
                logger.info(f"[{self.agent_name}] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

            except (AnthropicRateLimitError, OpenAIRateLimitError) as e:
                # Exponential backoff for rate limits: 2^attempt
                logger.warning(f"[{self.agent_name}] Rate limit error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                wait_time = 2**attempt  # 1s, 2s, 4s, 8s, 16s
                logger.info(f"[{self.agent_name}] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

            except (AnthropicAPIError, OpenAIAPIError) as e:
                # Linear backoff for API errors: 1 + attempt
                logger.warning(f"[{self.agent_name}] API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                wait_time = 1 + attempt  # 1s, 2s, 3s, 4s, 5s
                logger.info(f"[{self.agent_name}] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # This should never be reached due to raises above, but for type safety
        raise RuntimeError("Unexpected: max retries reached without exception")

    def create_agent_server(self) -> FastAPI:
        """
        Create FastAPI server for receiving MCP messages.

        The server provides:
        - POST /mcp/message: Endpoint for receiving MCP messages
        - GET /health: Health check endpoint

        Returns:
            FastAPI application instance
        """
        app = FastAPI(
            title=f"{self.agent_name} HTTP Server",
            version="0.1.0",
        )

        @app.post("/mcp/message")
        async def receive_mcp_message(message: MCPMessage) -> dict[str, Any]:
            """
            Endpoint to receive MCP messages from MCP server.

            Args:
                message: MCP message to process

            Returns:
                Processing result dictionary
            """
            logger.info(f"[{self.agent_name}] Received MCP message: type={message.message_type.value}, session_id={message.session_id}, message_id={message.message_id}")
            start_time = time.time()
            result = await self.handle_message(message)
            elapsed = time.time() - start_time
            logger.info(f"[{self.agent_name}] Message processed in {elapsed:.2f}s, result_status={result.get('status')}")
            return result

        @app.get("/health")
        async def health_check() -> dict[str, str]:
            """
            Health check endpoint.

            Returns:
                Health status dictionary
            """
            return {
                "status": "healthy",
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
            }

        return app

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        Return list of capabilities this agent provides.

        Must be implemented by subclasses.

        Returns:
            List of capability strings
        """
        pass

    @abstractmethod
    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """
        Handle incoming MCP message.

        Must be implemented by subclasses to process specific message types
        and execute agent-specific tasks.

        Args:
            message: MCP message to handle

        Returns:
            Result dictionary with status and any relevant data
        """
        pass
