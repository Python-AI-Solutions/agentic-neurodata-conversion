"""
Real workflow tests for EvaluationAgent.

These tests use evaluation_agent_real fixture which has real internal logic,
testing actual validation workflows instead of mocking them away.
"""

import pytest


@pytest.mark.unit
class TestRealValidationWorkflows:
    """Integration-style unit tests using real dependencies."""

    @pytest.mark.asyncio
    async def test_real_agent_initialization(self, evaluation_agent_real):
        """Test that real agent is properly initialized."""
        # Should have LLM service (MockLLMService)
        assert evaluation_agent_real._llm_service is not None

    @pytest.mark.asyncio
    async def test_real_validation_analyzer_initialization(self, evaluation_agent_real):
        """Test that real validation analyzer is initialized."""
        if evaluation_agent_real._llm_service:
            assert evaluation_agent_real._validation_analyzer is not None
