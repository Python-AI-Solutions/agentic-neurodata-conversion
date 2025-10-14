"""
LLM service abstraction layer.

Provides a provider-agnostic interface for LLM interactions,
with concrete implementations for Anthropic Claude.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


class LLMService(ABC):
    """
    Abstract interface for LLM services.

    Concrete implementations inject provider-specific clients.
    """

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate a text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text completion

        Raises:
            LLMServiceError: If generation fails
        """
        pass

    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema.

        Args:
            prompt: User prompt
            output_schema: JSON schema for output structure
            system_prompt: Optional system prompt

        Returns:
            Generated output as dictionary

        Raises:
            LLMServiceError: If generation fails or output doesn't match schema
        """
        pass


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    def __init__(self, message: str, provider: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class AnthropicLLMService(LLMService):
    """
    Anthropic Claude implementation of LLM service.

    Uses the Anthropic Python SDK for API communication.
    """

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic LLM service.

        Args:
            api_key: Anthropic API key
            model: Model identifier (default: Claude 3.5 Sonnet)
        """
        self._client = Anthropic(api_key=api_key)
        self._model = model

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate a text completion using Claude.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text completion

        Raises:
            LLMServiceError: If API call fails
        """
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self._client.messages.create(**kwargs)

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise LLMServiceError(
                    "Empty response from API",
                    provider="anthropic",
                    details={"model": self._model},
                )

        except Exception as e:
            raise LLMServiceError(
                f"Failed to generate completion: {str(e)}",
                provider="anthropic",
                details={"model": self._model, "exception": str(e)},
            )

    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured output using Claude with prompt engineering.

        Note: This implementation uses prompt engineering to encourage
        structured JSON output. For production use, consider using
        Claude's native structured output features if available.

        Args:
            prompt: User prompt
            output_schema: JSON schema for output structure
            system_prompt: Optional system prompt

        Returns:
            Generated output as dictionary

        Raises:
            LLMServiceError: If generation fails or output parsing fails
        """
        import json

        # Enhance prompt with schema
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{json.dumps(output_schema, indent=2)}

Respond ONLY with the JSON object, no additional text."""

        try:
            completion = await self.generate_completion(
                enhanced_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for structured output
            )

            # Parse JSON from response
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in completion:
                start = completion.find("```json") + 7
                end = completion.find("```", start)
                json_str = completion[start:end].strip()
            elif "```" in completion:
                start = completion.find("```") + 3
                end = completion.find("```", start)
                json_str = completion[start:end].strip()
            else:
                json_str = completion.strip()

            result = json.loads(json_str)
            return result

        except json.JSONDecodeError as e:
            raise LLMServiceError(
                f"Failed to parse JSON from response: {str(e)}",
                provider="anthropic",
                details={
                    "model": self._model,
                    "response": completion[:500],  # First 500 chars
                },
            )
        except Exception as e:
            raise LLMServiceError(
                f"Failed to generate structured output: {str(e)}",
                provider="anthropic",
                details={"model": self._model, "exception": str(e)},
            )


class MockLLMService(LLMService):
    """
    Mock LLM service for testing.

    Returns predefined responses without making API calls.
    """

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock LLM service.

        Args:
            responses: Optional dictionary mapping prompts to responses
        """
        self._responses = responses or {}
        self._default_response = "Mock LLM response"

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Return mock completion."""
        return self._responses.get(prompt, self._default_response)

    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return mock structured output."""
        # Return a minimal valid object based on schema
        return {"mock": True, "schema": output_schema}

    def set_response(self, prompt: str, response: str) -> None:
        """Set a mock response for a specific prompt."""
        self._responses[prompt] = response


# Factory function for creating LLM services
def create_llm_service(
    provider: str = "anthropic",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMService:
    """
    Factory function to create LLM service instances.

    Args:
        provider: LLM provider name ("anthropic" or "mock")
        api_key: API key (required for real providers)
        model: Model identifier (provider-specific)
        **kwargs: Additional provider-specific arguments

    Returns:
        LLM service instance

    Raises:
        ValueError: If provider is unknown or required args are missing
    """
    if provider == "anthropic":
        if not api_key:
            raise ValueError("api_key is required for Anthropic provider")
        if model:
            return AnthropicLLMService(api_key=api_key, model=model)
        return AnthropicLLMService(api_key=api_key)

    elif provider == "mock":
        return MockLLMService(responses=kwargs.get("responses"))

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
