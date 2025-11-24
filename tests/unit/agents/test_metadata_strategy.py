"""
Unit tests for MetadataRequestStrategy.

Tests priority-based metadata collection strategy, skip detection,
and sequential/batch request handling.
"""

from unittest.mock import AsyncMock

import pytest

from agentic_neurodata_conversion.agents.metadata.strategy import (
    METADATA_FIELDS,
    FieldPriority,
    MetadataField,
    MetadataRequestStrategy,
)
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFieldPriority:
    """Tests for FieldPriority enum."""

    def test_priority_values(self):
        """Test FieldPriority enum values."""
        assert FieldPriority.CRITICAL == "critical"
        assert FieldPriority.RECOMMENDED == "recommended"
        assert FieldPriority.OPTIONAL == "optional"


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataField:
    """Tests for MetadataField class."""

    def test_field_creation(self):
        """Test creating a metadata field."""
        field = MetadataField(
            name="experimenter",
            display_name="Experimenter Name",
            description="Person who performed the experiment",
            priority=FieldPriority.CRITICAL,
            why_needed="Required for DANDI",
            example='["Dr. Jane Smith"]',
            field_type="list",
        )

        assert field.name == "experimenter"
        assert field.display_name == "Experimenter Name"
        assert field.priority == FieldPriority.CRITICAL
        assert field.field_type == "list"

    def test_field_default_type(self):
        """Test default field type is text."""
        field = MetadataField(
            name="institution",
            display_name="Institution",
            description="Institution name",
            priority=FieldPriority.CRITICAL,
            why_needed="Required",
            example="MIT",
        )

        assert field.field_type == "text"


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataFieldsDefinitions:
    """Tests for METADATA_FIELDS dictionary."""

    def test_critical_fields_exist(self):
        """Test critical fields are defined."""
        critical_fields = [
            "experimenter",
            "institution",
            "experiment_description",
        ]

        for field_name in critical_fields:
            assert field_name in METADATA_FIELDS
            assert METADATA_FIELDS[field_name].priority == FieldPriority.CRITICAL

    def test_recommended_fields_exist(self):
        """Test recommended fields are defined."""
        recommended_fields = [
            "subject_id",
            "species",
            "session_description",
        ]

        for field_name in recommended_fields:
            assert field_name in METADATA_FIELDS
            assert METADATA_FIELDS[field_name].priority == FieldPriority.RECOMMENDED

    def test_optional_fields_exist(self):
        """Test optional fields are defined."""
        optional_fields = [
            "keywords",
            "related_publications",
            "session_id",
        ]

        for field_name in optional_fields:
            assert field_name in METADATA_FIELDS
            assert METADATA_FIELDS[field_name].priority == FieldPriority.OPTIONAL

    def test_all_fields_have_required_attributes(self):
        """Test all fields have required attributes."""
        for field_name, field in METADATA_FIELDS.items():
            assert field.name == field_name
            assert field.display_name is not None
            assert field.description is not None
            assert field.priority is not None
            assert field.why_needed is not None
            assert field.example is not None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataRequestStrategyInitialization:
    """Tests for MetadataRequestStrategy initialization."""

    def test_init_without_llm(self):
        """Test initialization without LLM service."""
        strategy = MetadataRequestStrategy()

        assert strategy.llm_service is None
        assert strategy.state is None
        assert strategy._current_phase is None
        assert strategy._current_field_index == 0

    def test_init_with_llm_and_state(self, global_state):
        """Test initialization with LLM service and state."""
        llm_service = MockLLMService()
        strategy = MetadataRequestStrategy(llm_service=llm_service, state=global_state)

        assert strategy.llm_service is llm_service
        assert strategy.state is global_state


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractMissingFields:
    """Tests for _extract_missing_fields method."""

    def test_extract_from_validation_issues(self):
        """Test extracting missing fields from validation issues."""
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing experimenter field"},
                {"message": "Missing institution information"},
                {"message": "experiment description not found"},
            ]
        }

        missing = strategy._extract_missing_fields(validation_result)

        assert "experimenter" in missing
        assert "institution" in missing
        assert "experiment_description" in missing

    def test_extract_no_duplicates(self):
        """Test that duplicate fields are not added twice."""
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing experimenter field"},
                {"message": "experimenter is required"},
            ]
        }

        missing = strategy._extract_missing_fields(validation_result)

        assert missing.count("experimenter") == 1

    def test_extract_empty_issues(self):
        """Test extraction from empty issues."""
        strategy = MetadataRequestStrategy()

        validation_result = {"issues": []}

        missing = strategy._extract_missing_fields(validation_result)

        assert missing == []

    def test_extract_handles_variations(self):
        """Test extraction handles field name variations."""
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing subject_id"},  # underscore
                {"message": "subject id not found"},  # space
                {"message": "Subject ID is required"},  # display name
            ]
        }

        missing = strategy._extract_missing_fields(validation_result)

        # Should match all variations to "subject_id"
        assert "subject_id" in missing


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFilterByPriority:
    """Tests for _filter_by_priority method."""

    def test_filter_critical_fields(self):
        """Test filtering for critical priority."""
        strategy = MetadataRequestStrategy()

        all_fields = ["experimenter", "institution", "species", "keywords"]
        critical = strategy._filter_by_priority(all_fields, FieldPriority.CRITICAL)

        assert "experimenter" in critical
        assert "institution" in critical
        assert "species" not in critical
        assert "keywords" not in critical

    def test_filter_recommended_fields(self):
        """Test filtering for recommended priority."""
        strategy = MetadataRequestStrategy()

        all_fields = ["experimenter", "species", "session_description", "keywords"]
        recommended = strategy._filter_by_priority(all_fields, FieldPriority.RECOMMENDED)

        assert "species" in recommended
        assert "session_description" in recommended
        assert "experimenter" not in recommended

    def test_filter_optional_fields(self):
        """Test filtering for optional priority."""
        strategy = MetadataRequestStrategy()

        all_fields = ["experimenter", "keywords", "related_publications"]
        optional = strategy._filter_by_priority(all_fields, FieldPriority.OPTIONAL)

        assert "keywords" in optional
        assert "related_publications" in optional
        assert "experimenter" not in optional

    def test_filter_unknown_fields(self):
        """Test filtering with unknown field names."""
        strategy = MetadataRequestStrategy()

        all_fields = ["experimenter", "unknown_field", "fake_field"]
        critical = strategy._filter_by_priority(all_fields, FieldPriority.CRITICAL)

        # Only known critical fields should be included
        assert "experimenter" in critical
        assert "unknown_field" not in critical
        assert "fake_field" not in critical


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestDetectSkipType:
    """Tests for detect_skip_type (keyword-based) method."""

    def test_detect_global_skip(self):
        """Test detecting global skip phrases."""
        strategy = MetadataRequestStrategy()

        global_phrases = [
            "skip all",
            "skip everything",
            "skip for now",
            "just proceed",
            "maybe later",
            "not right now",
        ]

        for phrase in global_phrases:
            result = strategy.detect_skip_type(phrase)
            assert result == "global", f"Failed for: {phrase}"

    def test_detect_field_skip(self):
        """Test detecting field-level skip."""
        strategy = MetadataRequestStrategy()

        field_phrases = [
            "skip",
            "skip it",
            "skip this",
            "no",
            "nope",
            "i don't have",
            "not available",
            "pass",
        ]

        for phrase in field_phrases:
            result = strategy.detect_skip_type(phrase)
            assert result == "field", f"Failed for: {phrase}"

    def test_detect_sequential_request(self):
        """Test detecting sequential mode request."""
        strategy = MetadataRequestStrategy()

        sequential_phrases = [
            "ask one by one",
            "one at a time",
            "ask separately",
            "ask individually",
            "one by one",
        ]

        for phrase in sequential_phrases:
            result = strategy.detect_skip_type(phrase)
            assert result == "sequential", f"Failed for: {phrase}"

    def test_detect_none_skip(self):
        """Test detecting non-skip messages."""
        strategy = MetadataRequestStrategy()

        non_skip_messages = [
            "Dr. Jane Smith, MIT, recording neural activity",
            "what is institution?",
            "can you explain?",
            "John Smith",
            "",
        ]

        for message in non_skip_messages:
            result = strategy.detect_skip_type(message)
            assert result == "none", f"Failed for: {message}"

    def test_detect_priority_order(self):
        """Test that global skip is detected before field skip."""
        strategy = MetadataRequestStrategy()

        # "skip all" contains both "skip all" and "skip"
        # Should return "global" not "field"
        result = strategy.detect_skip_type("skip all remaining")
        assert result == "global"


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestDetectSkipTypeWithLLM:
    """Tests for detect_skip_type_with_llm (LLM-based) method."""

    @pytest.mark.asyncio
    async def test_detect_with_llm_success(self, global_state):
        """Test LLM-based skip detection."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "intent": "global",
                "confidence": 95.0,
                "reasoning": "User wants to skip all questions",
            }
        )

        strategy = MetadataRequestStrategy(llm_service=llm_service, state=global_state)

        result = await strategy.detect_skip_type_with_llm("skip for now")

        assert result == "global"
        llm_service.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_with_llm_low_confidence_fallback(self, global_state):
        """Test fallback to keyword detection on low confidence."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "intent": "none",
                "confidence": 45.0,  # Below 60% threshold
                "reasoning": "Unclear intent",
            }
        )

        strategy = MetadataRequestStrategy(llm_service=llm_service, state=global_state)

        # "skip all" should be detected by keyword fallback as "global"
        result = await strategy.detect_skip_type_with_llm("skip all")

        assert result == "global"

    @pytest.mark.asyncio
    async def test_detect_without_llm_fallback(self):
        """Test fallback to keyword detection when no LLM."""
        strategy = MetadataRequestStrategy(llm_service=None)

        result = await strategy.detect_skip_type_with_llm("skip all")

        assert result == "global"

    @pytest.mark.asyncio
    async def test_detect_with_llm_failure_fallback(self, global_state):
        """Test fallback on LLM exception."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service unavailable"))

        strategy = MetadataRequestStrategy(llm_service=llm_service, state=global_state)

        result = await strategy.detect_skip_type_with_llm("skip")

        assert result == "field"  # Keyword fallback


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGetNextRequest:
    """Tests for get_next_request method."""

    def test_get_next_request_critical_batch(self, global_state):
        """Test requesting critical fields as batch."""
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing experimenter"},
                {"message": "Missing institution"},
            ]
        }

        result = strategy.get_next_request(global_state, validation_result)

        assert result["action"] == "ask_batch"
        assert result["phase"] == "critical"
        assert "experimenter" in result["fields"]
        assert "institution" in result["fields"]
        assert result["can_skip"] is False

    def test_get_next_request_critical_sequential(self, global_state):
        """Test requesting critical fields sequentially."""
        global_state.user_wants_sequential = True
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing experimenter"},
                {"message": "Missing institution"},
            ]
        }

        result = strategy.get_next_request(global_state, validation_result)

        assert result["action"] == "ask_field"
        assert result["phase"] == "critical"
        assert result["field"] in ["experimenter", "institution"]
        assert result["can_skip"] is False

    def test_get_next_request_recommended(self, global_state):
        """Test requesting recommended fields sequentially."""
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing species"},
                {"message": "Missing session_description"},
            ]
        }

        result = strategy.get_next_request(global_state, validation_result)

        assert result["action"] == "ask_field"
        assert result["phase"] == "recommended"
        assert result["field"] in ["species", "session_description"]
        assert result["can_skip"] is True

    def test_get_next_request_optional(self, global_state):
        """Test offering optional fields."""
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing keywords"},
                {"message": "Missing related_publications"},
            ]
        }

        result = strategy.get_next_request(global_state, validation_result)

        assert result["action"] == "offer_optional"
        assert result["phase"] == "optional"
        assert "keywords" in result["fields"]
        assert result["can_skip"] is True

    def test_get_next_request_respects_declined_fields(self, global_state):
        """Test that declined fields are filtered out."""
        global_state.user_declined_fields = ["experimenter"]
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing experimenter"},
                {"message": "Missing institution"},
            ]
        }

        result = strategy.get_next_request(global_state, validation_result)

        # Should only ask for institution, not experimenter
        if result["action"] == "ask_batch":
            assert "experimenter" not in result["fields"]
            assert "institution" in result["fields"]
        elif result["action"] == "ask_field":
            assert result["field"] != "experimenter"

    def test_get_next_request_all_declined(self, global_state):
        """Test when all fields are declined."""
        global_state.user_declined_fields = ["experimenter", "institution"]
        strategy = MetadataRequestStrategy()

        validation_result = {
            "issues": [
                {"message": "Missing experimenter"},
                {"message": "Missing institution"},
            ]
        }

        result = strategy.get_next_request(global_state, validation_result)

        assert result["action"] == "proceed"
        assert result["message"] is None

    def test_get_next_request_no_missing_fields(self, global_state):
        """Test when there are no missing fields."""
        strategy = MetadataRequestStrategy()

        validation_result = {"issues": []}

        result = strategy.get_next_request(global_state, validation_result)

        assert result["action"] == "proceed"
        assert result["message"] is None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestRequestCriticalBatch:
    """Tests for _request_critical_batch method."""

    def test_request_empty_critical_fields(self, global_state):
        """Test requesting with empty critical fields list."""
        strategy = MetadataRequestStrategy()

        result = strategy._request_critical_batch([], global_state)

        assert result["action"] == "proceed"
        assert result["message"] is None

    def test_request_critical_batch_message_format(self, global_state):
        """Test critical batch message format."""
        strategy = MetadataRequestStrategy()

        result = strategy._request_critical_batch(["experimenter", "institution"], global_state)

        assert "Critical Information Needed" in result["message"]
        assert "DANDI-compatible" in result["message"]
        assert result["can_skip"] is False


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestRequestNextRecommended:
    """Tests for _request_next_recommended method."""

    def test_request_empty_recommended_fields(self, global_state):
        """Test requesting with empty recommended fields list."""
        strategy = MetadataRequestStrategy()

        result = strategy._request_next_recommended([], global_state)

        assert result["action"] == "proceed"
        assert result["message"] is None

    def test_request_recommended_message_format(self, global_state):
        """Test recommended field message format."""
        strategy = MetadataRequestStrategy()

        result = strategy._request_next_recommended(["species"], global_state)

        assert result["action"] == "ask_field"
        assert result["field"] == "species"
        assert result["can_skip"] is True
        assert "💡" in result["message"]


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestOfferOptionalBatch:
    """Tests for _offer_optional_batch method."""

    def test_offer_optional_message_format(self, global_state):
        """Test optional fields offer message format."""
        strategy = MetadataRequestStrategy()

        result = strategy._offer_optional_batch(["keywords", "related_publications"], global_state)

        assert result["action"] == "offer_optional"
        assert result["phase"] == "optional"
        assert "Optional Enhancements" in result["message"]
        assert result["can_skip"] is True
        assert "keywords" in result["fields"]


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestRealMetadataStrategyWorkflows:
    """
    Integration-style unit tests using real MetadataStrategy logic.

    Tests real metadata strategy decisions instead of mocking.
    """

    @pytest.mark.asyncio
    async def test_real_strategy_initialization(self, mock_llm_api_only):
        """Test real metadata strategy initialization."""
        from agentic_neurodata_conversion.agents.metadata.strategy import MetadataRequestStrategy

        strategy = MetadataRequestStrategy(llm_service=mock_llm_api_only)

        # Verify real initialization
        assert strategy.llm_service is not None

    @pytest.mark.asyncio
    async def test_real_metadata_request_policy_decision(self, global_state):
        """Test real metadata strategy has get_next_request method."""
        from agentic_neurodata_conversion.agents.metadata.strategy import MetadataRequestStrategy

        strategy = MetadataRequestStrategy(llm_service=None, state=global_state)

        # Verify strategy has core methods
        assert hasattr(strategy, "get_next_request")
        assert hasattr(strategy, "detect_skip_type")

    @pytest.mark.asyncio
    async def test_real_strategy_with_llm(self, mock_llm_api_only, global_state):
        """Test real strategy with LLM for skip detection."""
        from agentic_neurodata_conversion.agents.metadata.strategy import MetadataRequestStrategy

        strategy = MetadataRequestStrategy(llm_service=mock_llm_api_only, state=global_state)

        # Verify can detect skip patterns
        result = strategy.detect_skip_type("skip this")
        assert isinstance(result, str)
