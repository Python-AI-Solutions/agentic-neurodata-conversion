"""Integration tests for status router endpoints.

Tests GET /api/status, /api/metadata-provenance, and /api/logs endpoints
with focus on uncovered lines 80-96 in status.py (metadata provenance).
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    LogLevel,
    MetadataProvenance,
    ProvenanceInfo,
    ValidationOutcome,
    ValidationStatus,
)


@pytest.mark.integration
@pytest.mark.api
class TestStatusEndpoint:
    """Test GET /api/status endpoint for current conversion status."""

    def test_get_status_basic(self, api_test_client):
        """Test basic status retrieval."""
        response = api_test_client.get("/api/status")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "validation_status" in data
        assert "progress" in data
        assert "message" in data

    def test_get_status_idle_state(self, api_test_client_with_state):
        """Test status endpoint when system is idle."""
        response = api_test_client_with_state.get("/api/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "idle"
        assert data["progress"] == 0

    def test_get_status_during_conversion(self, api_test_client):
        """Test status endpoint during active conversion."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()
            mock_state.status = ConversionStatus.CONVERTING
            mock_state.validation_status = ValidationStatus.PASSED  # Use valid enum value
            mock_state.overall_status = None
            mock_state.progress_percent = 45
            mock_state.progress_message = "Converting data..."
            mock_state.current_stage = "conversion"
            mock_state.llm_message = "Processing your file"
            mock_state.input_path = "/test/input.dat"
            mock_state.output_path = None
            mock_state.correction_attempt = 0
            mock_state.can_retry = True
            mock_state.conversation_type = None

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "converting"
            assert data["progress"] == 45
            assert data["progress_message"] == "Converting data..."
            assert data["current_stage"] == "conversion"

    def test_get_status_completed(self, api_test_client):
        """Test status endpoint after successful completion."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_state.overall_status = ValidationOutcome.PASSED
            mock_state.progress_percent = 100
            mock_state.progress_message = "Conversion completed"
            mock_state.current_stage = "completed"
            mock_state.llm_message = "Success!"
            mock_state.input_path = "/test/input.dat"
            mock_state.output_path = "/test/output.nwb"
            mock_state.correction_attempt = 0
            mock_state.can_retry = False
            mock_state.conversation_type = None

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "completed"
            assert data["validation_status"] == "passed"
            assert data["progress"] == 100
            assert data["output_path"] == "/test/output.nwb"


@pytest.mark.integration
@pytest.mark.api
class TestMetadataProvenanceEndpoint:
    """Test GET /api/metadata-provenance endpoint (lines 80-96).

    This is the primary target for coverage improvement.
    Tests the metadata provenance tracking endpoint which provides
    audit trail for all metadata fields.
    """

    def test_metadata_provenance_empty(self, api_test_client):
        """Test metadata provenance with no tracked fields (lines 84-100)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()
            mock_state.metadata_provenance = {}  # Empty provenance

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify structure (lines 96-100)
            assert "provenance" in data
            assert "total_fields" in data
            assert "needs_review_count" in data

            # Empty provenance
            assert data["provenance"] == {}
            assert data["total_fields"] == 0
            assert data["needs_review_count"] == 0

    def test_metadata_provenance_single_field(self, api_test_client):
        """Test metadata provenance with single field (lines 84-94)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create single provenance entry (lines 85-94)
            prov_info = ProvenanceInfo(
                value="Dr. Jane Smith",
                provenance=MetadataProvenance.USER_SPECIFIED,
                confidence=1.0,
                source="Direct user input",
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
                needs_review=False,
                raw_input="experimenter: Dr. Jane Smith",
            )
            mock_state.metadata_provenance = {"experimenter": prov_info}

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify conversion to dict (lines 86-94)
            assert len(data["provenance"]) == 1
            assert "experimenter" in data["provenance"]

            field_data = data["provenance"]["experimenter"]
            assert field_data["value"] == "Dr. Jane Smith"
            assert field_data["provenance"] == "user-specified"  # Enum value
            assert field_data["confidence"] == 1.0
            assert field_data["source"] == "Direct user input"
            assert field_data["timestamp"] == "2024-01-15T10:30:00"
            assert field_data["needs_review"] is False
            assert field_data["raw_input"] == "experimenter: Dr. Jane Smith"

            # Verify counts (lines 98-99)
            assert data["total_fields"] == 1
            assert data["needs_review_count"] == 0

    def test_metadata_provenance_multiple_fields_different_types(self, api_test_client):
        """Test metadata provenance with multiple provenance types (lines 84-94)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create multiple provenance entries with different types
            provenance_data = {
                "experimenter": ProvenanceInfo(
                    value="Dr. Smith",
                    provenance=MetadataProvenance.USER_SPECIFIED,
                    confidence=1.0,
                    source="User input",
                    timestamp=datetime(2024, 1, 15, 10, 0, 0),
                    needs_review=False,
                ),
                "institution": ProvenanceInfo(
                    value="MIT",
                    provenance=MetadataProvenance.AI_PARSED,
                    confidence=0.95,
                    source="LLM extraction",
                    timestamp=datetime(2024, 1, 15, 10, 5, 0),
                    needs_review=True,  # AI-parsed may need review
                ),
                "session_start_time": ProvenanceInfo(
                    value="2024-01-01T00:00:00",
                    provenance=MetadataProvenance.AUTO_EXTRACTED,
                    confidence=1.0,
                    source="File metadata",
                    timestamp=datetime(2024, 1, 15, 10, 10, 0),
                    needs_review=False,
                ),
                "subject_id": ProvenanceInfo(
                    value="mouse-001",
                    provenance=MetadataProvenance.AI_INFERRED,
                    confidence=0.8,
                    source="Filename pattern",
                    timestamp=datetime(2024, 1, 15, 10, 15, 0),
                    needs_review=True,  # Inferred may need review
                ),
            }
            mock_state.metadata_provenance = provenance_data

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify all fields converted (lines 86-94)
            assert len(data["provenance"]) == 4
            assert "experimenter" in data["provenance"]
            assert "institution" in data["provenance"]
            assert "session_start_time" in data["provenance"]
            assert "subject_id" in data["provenance"]

            # Verify provenance types
            assert data["provenance"]["experimenter"]["provenance"] == "user-specified"
            assert data["provenance"]["institution"]["provenance"] == "ai-parsed"
            assert data["provenance"]["session_start_time"]["provenance"] == "auto-extracted"
            assert data["provenance"]["subject_id"]["provenance"] == "ai-inferred"

            # Verify needs_review count (line 99)
            assert data["total_fields"] == 4
            assert data["needs_review_count"] == 2  # institution and subject_id

    def test_metadata_provenance_all_provenance_types(self, api_test_client):
        """Test all provenance types are handled correctly (lines 86-94)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Test all provenance types
            provenance_data = {
                "field1": ProvenanceInfo(
                    value="value1",
                    provenance=MetadataProvenance.USER_SPECIFIED,
                    confidence=1.0,
                    source="User",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "field2": ProvenanceInfo(
                    value="value2",
                    provenance=MetadataProvenance.AI_PARSED,
                    confidence=0.9,
                    source="LLM",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "field3": ProvenanceInfo(
                    value="value3",
                    provenance=MetadataProvenance.AUTO_EXTRACTED,
                    confidence=1.0,
                    source="File",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "field4": ProvenanceInfo(
                    value="value4",
                    provenance=MetadataProvenance.AI_INFERRED,
                    confidence=0.8,
                    source="Filename",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "field5": ProvenanceInfo(
                    value="value5",
                    provenance=MetadataProvenance.AUTO_CORRECTED,
                    confidence=0.85,
                    source="Validation",
                    timestamp=datetime.now(),
                    needs_review=True,
                ),
                "field6": ProvenanceInfo(
                    value="value6",
                    provenance=MetadataProvenance.DEFAULT,
                    confidence=1.0,
                    source="System",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
            }
            mock_state.metadata_provenance = provenance_data

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify all types converted (line 88: prov_info.provenance.value)
            assert data["provenance"]["field1"]["provenance"] == "user-specified"
            assert data["provenance"]["field2"]["provenance"] == "ai-parsed"
            assert data["provenance"]["field3"]["provenance"] == "auto-extracted"
            assert data["provenance"]["field4"]["provenance"] == "ai-inferred"
            assert data["provenance"]["field5"]["provenance"] == "auto-corrected"
            assert data["provenance"]["field6"]["provenance"] == "default"

            assert data["total_fields"] == 6
            assert data["needs_review_count"] == 1  # Only field5

    def test_metadata_provenance_needs_review_count(self, api_test_client):
        """Test needs_review_count calculation (line 99)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create mix of fields needing and not needing review
            provenance_data = {
                "field_ok_1": ProvenanceInfo(
                    value="ok1",
                    provenance=MetadataProvenance.USER_SPECIFIED,
                    confidence=1.0,
                    source="User",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "field_review_1": ProvenanceInfo(
                    value="review1",
                    provenance=MetadataProvenance.AI_PARSED,
                    confidence=0.7,
                    source="LLM",
                    timestamp=datetime.now(),
                    needs_review=True,
                ),
                "field_ok_2": ProvenanceInfo(
                    value="ok2",
                    provenance=MetadataProvenance.AUTO_EXTRACTED,
                    confidence=1.0,
                    source="File",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "field_review_2": ProvenanceInfo(
                    value="review2",
                    provenance=MetadataProvenance.AI_INFERRED,
                    confidence=0.6,
                    source="Filename",
                    timestamp=datetime.now(),
                    needs_review=True,
                ),
                "field_review_3": ProvenanceInfo(
                    value="review3",
                    provenance=MetadataProvenance.AUTO_CORRECTED,
                    confidence=0.75,
                    source="Validation",
                    timestamp=datetime.now(),
                    needs_review=True,
                ),
            }
            mock_state.metadata_provenance = provenance_data

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify needs_review_count (line 99)
            assert data["total_fields"] == 5
            assert data["needs_review_count"] == 3  # field_review_1, 2, 3

    def test_metadata_provenance_timestamp_serialization(self, api_test_client):
        """Test timestamp ISO format serialization (line 91)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Test timestamp with microseconds
            timestamp = datetime(2024, 3, 15, 14, 30, 45, 123456)
            prov_info = ProvenanceInfo(
                value="test",
                provenance=MetadataProvenance.USER_SPECIFIED,
                confidence=1.0,
                source="Test",
                timestamp=timestamp,
                needs_review=False,
            )
            mock_state.metadata_provenance = {"test_field": prov_info}

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify ISO format (line 91: timestamp.isoformat())
            assert data["provenance"]["test_field"]["timestamp"] == "2024-03-15T14:30:45.123456"

    def test_metadata_provenance_raw_input_preservation(self, api_test_client):
        """Test raw_input field preservation (line 93)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Test with raw input
            prov_info = ProvenanceInfo(
                value="Dr. Jane Smith",
                provenance=MetadataProvenance.AI_PARSED,
                confidence=0.95,
                source="LLM",
                timestamp=datetime.now(),
                needs_review=False,
                raw_input="The experimenter's name is Dr. Jane Smith from MIT",
            )
            mock_state.metadata_provenance = {"experimenter": prov_info}

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify raw_input preserved (line 93)
            assert (
                data["provenance"]["experimenter"]["raw_input"] == "The experimenter's name is Dr. Jane Smith from MIT"
            )

    def test_metadata_provenance_confidence_values(self, api_test_client):
        """Test confidence value serialization (line 89)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Test different confidence values
            provenance_data = {
                "high_confidence": ProvenanceInfo(
                    value="high",
                    provenance=MetadataProvenance.USER_SPECIFIED,
                    confidence=1.0,
                    source="User",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "medium_confidence": ProvenanceInfo(
                    value="medium",
                    provenance=MetadataProvenance.AI_PARSED,
                    confidence=0.75,
                    source="LLM",
                    timestamp=datetime.now(),
                    needs_review=False,
                ),
                "low_confidence": ProvenanceInfo(
                    value="low",
                    provenance=MetadataProvenance.AI_INFERRED,
                    confidence=0.3,
                    source="Filename",
                    timestamp=datetime.now(),
                    needs_review=True,
                ),
            }
            mock_state.metadata_provenance = provenance_data

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/metadata-provenance")

            assert response.status_code == 200
            data = response.json()

            # Verify confidence values (line 89)
            assert data["provenance"]["high_confidence"]["confidence"] == 1.0
            assert data["provenance"]["medium_confidence"]["confidence"] == 0.75
            assert data["provenance"]["low_confidence"]["confidence"] == 0.3


@pytest.mark.integration
@pytest.mark.api
class TestLogsEndpoint:
    """Test GET /api/logs endpoint for log retrieval with pagination."""

    def test_get_logs_empty(self, api_test_client):
        """Test logs endpoint with no logs."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()
            mock_state.logs = []  # Empty logs

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/logs")

            assert response.status_code == 200
            data = response.json()

            assert "logs" in data
            assert "total_count" in data
            assert data["logs"] == []
            assert data["total_count"] == 0

    def test_get_logs_with_data(self, api_test_client):
        """Test logs endpoint with log entries."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create mock log entries
            from agentic_neurodata_conversion.models import LogEntry

            logs = [
                LogEntry(
                    level=LogLevel.INFO,
                    message="System started",
                    timestamp=datetime(2024, 1, 1, 10, 0, 0),
                    context={},
                ),
                LogEntry(
                    level=LogLevel.INFO,
                    message="File uploaded",
                    timestamp=datetime(2024, 1, 1, 10, 1, 0),
                    context={"filename": "test.nwb"},
                ),
                LogEntry(
                    level=LogLevel.WARNING,
                    message="Missing metadata",
                    timestamp=datetime(2024, 1, 1, 10, 2, 0),
                    context={"field": "experimenter"},
                ),
            ]
            mock_state.logs = logs

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/logs")

            assert response.status_code == 200
            data = response.json()

            assert len(data["logs"]) == 3
            assert data["total_count"] == 3
            assert data["logs"][0]["message"] == "System started"
            assert data["logs"][2]["level"] == "warning"

    def test_get_logs_pagination_limit(self, api_test_client):
        """Test logs endpoint with pagination limit."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create 10 log entries
            from agentic_neurodata_conversion.models import LogEntry

            logs = [
                LogEntry(
                    level=LogLevel.INFO,
                    message=f"Log entry {i}",
                    timestamp=datetime(2024, 1, 1, 10, i, 0),
                    context={},
                )
                for i in range(10)
            ]
            mock_state.logs = logs

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Request with limit=5
            response = api_test_client.get("/api/logs?limit=5")

            assert response.status_code == 200
            data = response.json()

            assert len(data["logs"]) == 5
            assert data["total_count"] == 10

    def test_get_logs_pagination_offset(self, api_test_client):
        """Test logs endpoint with pagination offset."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create 10 log entries
            from agentic_neurodata_conversion.models import LogEntry

            logs = [
                LogEntry(
                    level=LogLevel.INFO,
                    message=f"Log entry {i}",
                    timestamp=datetime(2024, 1, 1, 10, i, 0),
                    context={},
                )
                for i in range(10)
            ]
            mock_state.logs = logs

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Request with offset=5, limit=3
            response = api_test_client.get("/api/logs?offset=5&limit=3")

            assert response.status_code == 200
            data = response.json()

            assert len(data["logs"]) == 3
            assert data["total_count"] == 10
            assert data["logs"][0]["message"] == "Log entry 5"
            assert data["logs"][2]["message"] == "Log entry 7"

    def test_get_logs_default_pagination(self, api_test_client):
        """Test logs endpoint with default pagination (limit=100)."""
        with patch("agentic_neurodata_conversion.api.routers.status.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = Mock()

            # Create 150 log entries (more than default limit)
            from agentic_neurodata_conversion.models import LogEntry

            logs = [
                LogEntry(
                    level=LogLevel.INFO,
                    message=f"Log {i}",
                    timestamp=datetime.now(),
                    context={},
                )
                for i in range(150)
            ]
            mock_state.logs = logs

            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/logs")

            assert response.status_code == 200
            data = response.json()

            # Default limit is 100
            assert len(data["logs"]) == 100
            assert data["total_count"] == 150
