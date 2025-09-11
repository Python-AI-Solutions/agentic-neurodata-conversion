"""
Unit tests for the conversation agent.

Tests the ConversationAgent functionality including dataset analysis,
metadata extraction, and question generation.
"""

from pathlib import Path
import shutil
import tempfile
from unittest.mock import AsyncMock, Mock

import pytest

# Import the actual components that should be implemented
try:
    from agentic_neurodata_conversion.agents.base import (
        AgentConfig,
        AgentResult,
        AgentStatus,
    )
    from agentic_neurodata_conversion.agents.conversation import ConversationAgent

    COMPONENTS_AVAILABLE = True
except ImportError:
    # These should fail until implemented
    ConversationAgent = None
    AgentConfig = None
    AgentResult = None
    AgentStatus = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE, reason="Conversation agent components not implemented yet"
)


class TestConversationAgent:
    """Test the ConversationAgent functionality."""

    @pytest.fixture
    def agent_config(self):
        """Create a test agent configuration."""
        return AgentConfig(
            version="test", use_llm=False, llm_config={"model": "test-model"}
        )

    @pytest.fixture
    def conversation_agent(self, agent_config):
        """Create a conversation agent instance."""
        return ConversationAgent(agent_config)

    @pytest.fixture
    def test_dataset_dir(self):
        """Create a temporary test dataset directory."""
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)

        # Create some test files
        (dataset_path / "data.continuous").write_text("test data")
        (dataset_path / "events.events").write_text("test events")
        (dataset_path / "metadata.json").write_text('{"test": "metadata"}')

        yield str(dataset_path)

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.mark.unit
    def test_agent_initialization(self, conversation_agent):
        """Test conversation agent initialization."""
        assert conversation_agent.agent_type == "conversation"
        assert conversation_agent.agent_id.startswith("conversation_")
        assert conversation_agent.status == AgentStatus.IDLE
        assert conversation_agent.format_detector is not None
        assert conversation_agent.domain_knowledge is not None

    @pytest.mark.unit
    async def test_input_validation_success(self, conversation_agent, test_dataset_dir):
        """Test successful input validation."""
        validated = await conversation_agent._validate_inputs(
            dataset_dir=test_dataset_dir, use_llm=False, session_id="test_session"
        )

        assert validated["dataset_dir"] == str(Path(test_dataset_dir).absolute())
        assert validated["use_llm"] is False
        assert validated["session_id"] == "test_session"
        assert validated["existing_metadata"] == {}

    @pytest.mark.unit
    async def test_input_validation_missing_dataset_dir(self, conversation_agent):
        """Test input validation with missing dataset_dir."""
        with pytest.raises(ValueError, match="dataset_dir is required"):
            await conversation_agent._validate_inputs()

    @pytest.mark.unit
    async def test_input_validation_nonexistent_directory(self, conversation_agent):
        """Test input validation with nonexistent directory."""
        with pytest.raises(ValueError, match="Dataset directory does not exist"):
            await conversation_agent._validate_inputs(dataset_dir="/nonexistent/path")

    @pytest.mark.unit
    async def test_dataset_analysis_execution(
        self, conversation_agent, test_dataset_dir
    ):
        """Test dataset analysis execution."""
        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=False, session_id="test_session"
        )

        assert isinstance(result, AgentResult)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_id == conversation_agent.agent_id
        assert result.error is None

        # Check result data structure
        data = result.data
        assert "format_analysis" in data
        assert "basic_metadata" in data
        assert "enriched_metadata" in data
        assert "missing_metadata" in data
        assert "questions" in data
        assert "session_id" in data
        assert "requires_user_input" in data

        assert data["session_id"] == "test_session"

    @pytest.mark.unit
    async def test_format_detection(self, conversation_agent, test_dataset_dir):
        """Test format detection functionality."""
        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=False
        )

        format_analysis = result.data["format_analysis"]
        assert "formats" in format_analysis
        assert "file_count" in format_analysis
        assert "total_size" in format_analysis

        # Should detect Open Ephys format from .continuous and .events files
        formats = format_analysis["formats"]
        if formats:
            assert any(f["format"] == "open_ephys" for f in formats)

    @pytest.mark.unit
    async def test_basic_metadata_extraction(
        self, conversation_agent, test_dataset_dir
    ):
        """Test basic metadata extraction."""
        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=False
        )

        basic_metadata = result.data["basic_metadata"]
        assert "dataset_path" in basic_metadata
        assert "detected_formats" in basic_metadata
        assert "file_count" in basic_metadata
        assert "total_size" in basic_metadata
        assert "timestamps" in basic_metadata

        assert basic_metadata["dataset_path"] == str(Path(test_dataset_dir).absolute())
        assert basic_metadata["file_count"] > 0

    @pytest.mark.unit
    async def test_domain_knowledge_application(
        self, conversation_agent, test_dataset_dir
    ):
        """Test domain knowledge application."""
        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=False
        )

        enriched_metadata = result.data["enriched_metadata"]

        # Should have all basic metadata
        assert "dataset_path" in enriched_metadata
        assert "detected_formats" in enriched_metadata

        # May have inferred experimental type
        if "experimental_type" in enriched_metadata:
            assert enriched_metadata["experimental_type"] in [
                "electrophysiology",
                "calcium_imaging",
                "behavior",
            ]

    @pytest.mark.unit
    async def test_missing_metadata_identification(
        self, conversation_agent, test_dataset_dir
    ):
        """Test missing metadata identification."""
        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=False
        )

        missing_metadata = result.data["missing_metadata"]
        assert isinstance(missing_metadata, list)

        # Should identify missing required NWB fields
        missing_fields = [item["field"] for item in missing_metadata]
        required_fields = [
            "session_description",
            "identifier",
            "experimenter",
            "lab",
            "institution",
        ]

        for field in required_fields:
            assert field in missing_fields

    @pytest.mark.unit
    async def test_question_generation_without_llm(
        self, conversation_agent, test_dataset_dir
    ):
        """Test question generation without LLM."""
        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=False
        )

        questions = result.data["questions"]
        assert isinstance(questions, list)
        # Without LLM, questions should be empty
        assert len(questions) == 0

    @pytest.mark.unit
    async def test_question_generation_with_llm(
        self, conversation_agent, test_dataset_dir
    ):
        """Test question generation with LLM enabled."""
        # Enable LLM for this test
        conversation_agent.config.use_llm = True
        conversation_agent.llm_client = Mock()
        conversation_agent.llm_client.generate_completion = AsyncMock(
            return_value='[{"field": "session_description", "question": "What happened in this session?", "explanation": "Required for NWB", "priority": "high"}]'
        )

        result = await conversation_agent.execute(
            dataset_dir=test_dataset_dir, use_llm=True
        )

        questions = result.data["questions"]
        assert isinstance(questions, list)
        # With LLM, should generate questions
        if len(result.data["missing_metadata"]) > 0:
            assert len(questions) > 0

    @pytest.mark.unit
    async def test_template_question_generation(self, conversation_agent):
        """Test template-based question generation."""
        context = {
            "category": "session_info",
            "missing_fields": [
                {
                    "field": "session_description",
                    "description": "A description of the experimental session",
                    "required": True,
                }
            ],
        }

        questions = conversation_agent._generate_template_questions(context)

        assert len(questions) == 1
        assert questions[0]["field"] == "session_description"
        assert questions[0]["category"] == "session_info"
        assert questions[0]["priority"] == "high"

    @pytest.mark.unit
    def test_processing_steps(self, conversation_agent):
        """Test processing steps for provenance."""
        steps = conversation_agent._get_processing_steps()

        expected_steps = [
            "format_detection",
            "basic_metadata_extraction",
            "domain_knowledge_application",
            "missing_metadata_identification",
            "question_generation",
        ]

        assert steps == expected_steps

    @pytest.mark.unit
    def test_external_services_without_llm(self, conversation_agent):
        """Test external services identification without LLM."""
        services = conversation_agent._get_external_services_used()
        assert services == []

    @pytest.mark.unit
    def test_external_services_with_llm(self, conversation_agent):
        """Test external services identification with LLM."""
        conversation_agent.llm_client = Mock()
        services = conversation_agent._get_external_services_used()
        assert "llm_service" in services

    @pytest.mark.unit
    async def test_process_user_responses_valid(self, conversation_agent):
        """Test processing valid user responses."""
        responses = {
            "session_description": "Test recording session",
            "experimenter": "John Doe",
            "age": "30",
            "sex": "M",
            "sampling_rate": "30000",
        }

        result = await conversation_agent.process_user_responses(
            responses, "test_session"
        )

        assert "processed_responses" in result
        assert "validation_errors" in result
        assert "warnings" in result
        assert result["session_id"] == "test_session"

        processed = result["processed_responses"]
        assert processed["session_description"] == "Test recording session"
        assert processed["experimenter"] == "John Doe"
        assert processed["age"] == "30"
        assert processed["sex"] == "M"
        assert processed["sampling_rate"] == 30000.0

        assert len(result["validation_errors"]) == 0

    @pytest.mark.unit
    async def test_process_user_responses_with_errors(self, conversation_agent):
        """Test processing user responses with validation errors."""
        responses = {
            "session_description": "",  # Empty string should cause error
            "age": "-5",  # Negative age should cause error
            "sex": "invalid",  # Invalid sex value
            "sampling_rate": "not_a_number",  # Invalid sampling rate
        }

        result = await conversation_agent.process_user_responses(responses)

        assert len(result["validation_errors"]) == 4

        error_fields = [error["field"] for error in result["validation_errors"]]
        assert "session_description" in error_fields
        assert "age" in error_fields
        assert "sex" in error_fields
        assert "sampling_rate" in error_fields

    @pytest.mark.unit
    async def test_validate_datetime_response(self, conversation_agent):
        """Test datetime validation."""
        # Valid formats
        assert await conversation_agent._validate_response(
            "session_start_time", "2023-01-01 10:00:00"
        )
        assert await conversation_agent._validate_response(
            "session_start_time", "2023-01-01"
        )
        assert await conversation_agent._validate_response(
            "session_start_time", "01/01/2023"
        )

        # Invalid format should raise error
        with pytest.raises(ValueError):
            await conversation_agent._validate_response(
                "session_start_time", "invalid_date"
            )

    @pytest.mark.unit
    async def test_validate_age_response(self, conversation_agent):
        """Test age validation."""
        # Valid ages
        assert await conversation_agent._validate_response("age", "30") == "30"
        assert await conversation_agent._validate_response("age", 25) == "25"
        assert (
            await conversation_agent._validate_response("age", "P30") == "P30"
        )  # Descriptive age

        # Invalid age should raise error
        with pytest.raises(ValueError):
            await conversation_agent._validate_response("age", "-5")

    @pytest.mark.unit
    async def test_validate_sex_response(self, conversation_agent):
        """Test sex validation."""
        # Valid values
        assert await conversation_agent._validate_response("sex", "M") == "M"
        assert await conversation_agent._validate_response("sex", "male") == "M"
        assert await conversation_agent._validate_response("sex", "F") == "F"
        assert await conversation_agent._validate_response("sex", "female") == "F"
        assert await conversation_agent._validate_response("sex", "unknown") == "U"

        # Invalid value should raise error
        with pytest.raises(ValueError):
            await conversation_agent._validate_response("sex", "invalid")

    @pytest.mark.unit
    async def test_validate_sampling_rate_response(self, conversation_agent):
        """Test sampling rate validation."""
        # Valid rates
        assert (
            await conversation_agent._validate_response("sampling_rate", "30000")
            == 30000.0
        )
        assert (
            await conversation_agent._validate_response("sampling_rate", 25000.5)
            == 25000.5
        )

        # Invalid rates should raise error
        with pytest.raises(ValueError):
            await conversation_agent._validate_response("sampling_rate", "0")
        with pytest.raises(ValueError):
            await conversation_agent._validate_response("sampling_rate", "not_a_number")

    @pytest.mark.unit
    async def test_validate_channel_count_response(self, conversation_agent):
        """Test channel count validation."""
        # Valid counts
        assert await conversation_agent._validate_response("channel_count", "64") == 64
        assert await conversation_agent._validate_response("channel_count", 128) == 128

        # Invalid counts should raise error
        with pytest.raises(ValueError):
            await conversation_agent._validate_response("channel_count", "0")
        with pytest.raises(ValueError):
            await conversation_agent._validate_response("channel_count", "not_a_number")

    @pytest.mark.unit
    async def test_domain_knowledge_warnings(self, conversation_agent):
        """Test domain knowledge validation warnings."""
        responses = {
            "experimental_type": "electrophysiology",
            "sampling_rate": 500.0,  # Low for electrophysiology
            "species": "mouse",
            "age": "2 years",  # Unusual for mouse
        }

        warnings = await conversation_agent._validate_responses_with_domain_knowledge(
            responses
        )

        assert len(warnings) == 2
        warning_fields = [w["field"] for w in warnings]
        assert "sampling_rate" in warning_fields
        assert "age" in warning_fields

    @pytest.mark.unit
    async def test_generate_follow_up_questions(self, conversation_agent):
        """Test follow-up question generation."""
        current_responses = {
            "experimental_type": "electrophysiology",
            "recording_system": "Open Ephys",
        }
        missing_metadata = []

        follow_up = await conversation_agent.generate_follow_up_questions(
            current_responses, missing_metadata
        )

        assert len(follow_up) > 0
        question_fields = [q["field"] for q in follow_up]
        assert (
            "electrode_config" in question_fields
            or "open_ephys_version" in question_fields
        )
