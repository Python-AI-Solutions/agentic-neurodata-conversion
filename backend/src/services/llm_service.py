"""
LLM service abstraction layer.

Provides a provider-agnostic interface for LLM interactions,
with concrete implementations for Anthropic Claude.

Features:
- Exponential backoff retry logic
- Graceful error recovery
- Performance monitoring
- Structured output support
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from anthropic import AsyncAnthropic

# Configure logger for LLM performance monitoring
logger = logging.getLogger(__name__)


async def call_with_retry(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    fallback: Optional[Callable] = None,
) -> Any:
    """
    Call async function with exponential backoff retry.

    Args:
        func: Async function to call
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        fallback: Optional fallback function if all retries fail

    Returns:
        Result from func or fallback

    Raises:
        Last exception if all retries fail and no fallback provided
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            result = await func()
            if attempt > 0:
                logger.info(f"Retry successful on attempt {attempt + 1}/{max_retries}")
            return result

        except Exception as e:
            last_exception = e
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)[:100]}"
            )

            # Don't sleep on last attempt
            if attempt < max_retries - 1:
                # Calculate exponential backoff
                delay = min(
                    base_delay * (exponential_base ** attempt),
                    max_delay
                )
                logger.info(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        f"All {max_retries} attempts failed. Last error: {str(last_exception)}"
    )

    # Try fallback if provided
    if fallback:
        try:
            logger.info("Attempting fallback function...")
            return await fallback()
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {str(fallback_error)}")
            raise LLMServiceError(
                f"All retries and fallback failed: {str(last_exception)}",
                provider="retry_mechanism",
                details={
                    "max_retries": max_retries,
                    "last_error": str(last_exception),
                    "fallback_error": str(fallback_error)
                }
            )

    # No fallback, raise last exception
    raise last_exception


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

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Anthropic LLM service.

        Args:
            api_key: Anthropic API key
            model: Model identifier (default: Claude Sonnet 4.5)

        Note: Claude Sonnet 4.5 is specifically designed for agentic systems,
        offering superior reasoning for multi-agent architectures, structured
        outputs, and domain-specific tasks like neuroscience data conversion.
        """
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        enable_retry: bool = True,
    ) -> str:
        """
        Generate a text completion using Claude with automatic retry.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            enable_retry: Enable automatic retry with exponential backoff

        Returns:
            Generated text completion

        Raises:
            LLMServiceError: If API call fails after all retries
        """
        async def _api_call():
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            # Start performance monitoring
            start_time = time.time()
            logger.info(
                f"LLM API call starting: model={self._model}, "
                f"max_tokens={max_tokens}, prompt_length={len(prompt)}"
            )

            try:
                response = await self._client.messages.create(**kwargs)

                # Log performance metrics
                duration = time.time() - start_time
                if duration > 10:
                    logger.error(
                        f"LLM API call VERY SLOW: {duration:.2f}s - "
                        f"model={self._model}, tokens={max_tokens}"
                    )
                elif duration > 5:
                    logger.warning(
                        f"LLM API call slow: {duration:.2f}s - "
                        f"model={self._model}, tokens={max_tokens}"
                    )
                else:
                    logger.info(f"LLM API call completed: {duration:.2f}s")

                # Extract text from response
                if response.content and len(response.content) > 0:
                    return response.content[0].text
                else:
                    raise LLMServiceError(
                        "Empty response from API",
                        provider="anthropic",
                        details={"model": self._model, "duration": duration},
                    )

            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                logger.error(
                    f"LLM API call failed after {duration:.2f}s: {str(e)} - "
                    f"model={self._model}"
                )
                raise LLMServiceError(
                    f"Failed to generate completion: {str(e)}",
                    provider="anthropic",
                    details={"model": self._model, "exception": str(e), "duration": duration},
                )

        # Use retry logic if enabled
        if enable_retry:
            return await call_with_retry(_api_call, max_retries=3)
        else:
            return await _api_call()

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

        # Start performance monitoring
        start_time = time.time()
        logger.info(
            f"LLM structured output call starting: model={self._model}, "
            f"prompt_length={len(prompt)}, schema_keys={list(output_schema.keys())}"
        )

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

            # Validate against output schema if provided
            if output_schema:
                try:
                    from jsonschema import validate, ValidationError as SchemaValidationError
                    validate(instance=result, schema=output_schema)
                except ImportError:
                    # jsonschema not installed - log warning but continue
                    logger.warning("jsonschema package not installed - skipping schema validation")
                except SchemaValidationError as e:
                    duration = time.time() - start_time
                    logger.error(
                        f"LLM output failed schema validation after {duration:.2f}s: {str(e)}"
                    )
                    raise LLMServiceError(
                        f"LLM response doesn't match expected schema: {str(e)}",
                        provider="anthropic",
                        details={
                            "model": self._model,
                            "validation_error": str(e),
                            "result": result,
                            "expected_schema": output_schema,
                            "duration": duration,
                        },
                    )

            # Log successful parsing
            duration = time.time() - start_time
            logger.info(
                f"LLM structured output completed and validated: {duration:.2f}s - "
                f"result_keys={list(result.keys())}"
            )

            return result

        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            logger.error(
                f"LLM structured output JSON parsing failed after {duration:.2f}s: {str(e)} - "
                f"model={self._model}, response_preview={completion[:100]}"
            )
            raise LLMServiceError(
                f"Failed to parse JSON from response: {str(e)}",
                provider="anthropic",
                details={
                    "model": self._model,
                    "response": completion[:500],  # First 500 chars
                    "duration": duration,
                },
            )
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(
                f"LLM structured output failed after {duration:.2f}s: {str(e)} - "
                f"model={self._model}"
            )
            raise LLMServiceError(
                f"Failed to generate structured output: {str(e)}",
                provider="anthropic",
                details={"model": self._model, "exception": str(e), "duration": duration},
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
