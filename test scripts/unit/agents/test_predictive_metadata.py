"""
Unit tests for PredictiveMetadataSystem.

Tests intelligent metadata prediction using LLM and pattern recognition.
"""

from unittest.mock import AsyncMock

import pytest
from agents.predictive_metadata import PredictiveMetadataSystem
from services.llm_service import MockLLMService

# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - mock_llm_service: from root conftest.py (Mock LLM service)
# - tmp_path: from pytest (temporary directory)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestPredictiveMetadataSystemInitialization:
    """Tests for PredictiveMetadataSystem initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        system = PredictiveMetadataSystem(llm_service=llm_service)

        assert system.llm_service is llm_service
        assert isinstance(system.prediction_history, list)
        assert len(system.prediction_history) == 0

    def test_init_without_llm_service(self):
        """Test initialization without LLM service (fallback mode)."""
        system = PredictiveMetadataSystem()

        assert system.llm_service is None
        assert isinstance(system.prediction_history, list)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFilenameParsing:
    """Tests for filename parsing and pattern extraction."""

    @pytest.fixture
    def system(self):
        """Create system without LLM for testing pure methods."""
        return PredictiveMetadataSystem()

    def test_parse_filename_with_date_yyyymmdd(self, system):
        """Test parsing filename with YYYYMMDD date format."""
        filename = "recording_20240117_mouse1.bin"

        parts = system._parse_filename(filename)

        assert parts["has_date"] is True
        assert "20240117" in parts["date_string"]

    def test_parse_filename_with_date_dash_format(self, system):
        """Test parsing filename with YYYY-MM-DD date format."""
        filename = "experiment_2024-01-17_session1.nwb"

        parts = system._parse_filename(filename)

        assert parts["has_date"] is True
        assert "2024-01-17" in parts["date_string"]

    def test_parse_filename_with_date_underscore_format(self, system):
        """Test parsing filename with YYYY_MM_DD date format."""
        filename = "data_2024_01_17.bin"

        parts = system._parse_filename(filename)

        assert parts["has_date"] is True
        assert "2024_01_17" in parts["date_string"]

    def test_parse_filename_with_mouse_subject_id(self, system):
        """Test parsing filename with mouse subject ID."""
        filename = "mouse_123_recording.bin"

        parts = system._parse_filename(filename)

        assert parts["has_subject_id"] is True
        assert "mouse" in parts["subject_id_hint"].lower()

    def test_parse_filename_with_rat_subject_id(self, system):
        """Test parsing filename with rat subject ID."""
        filename = "rat-456_experiment.bin"

        parts = system._parse_filename(filename)

        assert parts["has_subject_id"] is True
        assert "rat" in parts["subject_id_hint"].lower()

    def test_parse_filename_with_session_id(self, system):
        """Test parsing filename with session ID patterns."""
        filename = "mouse1_session_42.bin"

        parts = system._parse_filename(filename)

        assert parts["has_session_id"] is True
        assert "session" in parts["session_id_hint"].lower() or "42" in parts["session_id_hint"]

    def test_parse_filename_with_experimenter_hint(self, system):
        """Test parsing filename with experimenter name hint."""
        filename = "Doe_20240117_mouse1.bin"

        parts = system._parse_filename(filename)

        assert parts["has_experimenter_hint"] is True
        assert parts["experimenter_hint"] == "Doe"

    def test_parse_filename_comprehensive(self, system):
        """Test parsing filename with multiple patterns."""
        filename = "Smith_2024-01-17_mouse_123_session_05.bin"

        parts = system._parse_filename(filename)

        # Should detect multiple patterns
        assert parts["has_date"] is True
        assert parts["has_subject_id"] is True
        assert parts["has_session_id"] is True
        assert parts["has_experimenter_hint"] is True

    def test_parse_filename_no_patterns(self, system):
        """Test parsing filename with no recognizable patterns."""
        filename = "data.bin"

        parts = system._parse_filename(filename)

        assert parts["has_date"] is False
        assert parts["has_subject_id"] is False
        assert parts["has_session_id"] is False
        assert parts["has_experimenter_hint"] is False


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestBasicPredictions:
    """Tests for basic prediction fallback (no LLM)."""

    @pytest.fixture
    def system(self):
        """Create system without LLM."""
        return PredictiveMetadataSystem()

    def test_basic_predictions_with_inference(self, system):
        """Test basic predictions from inference results."""
        basic_inference = {
            "inferred_metadata": {
                "subject_id": "mouse_001",
                "species": "Mus musculus",
            },
            "confidence_scores": {
                "subject_id": 80,
                "species": 90,
            },
            "reasoning": {
                "subject_id": "Extracted from filename",
                "species": "Detected from file format",
            },
        }

        result = system._basic_predictions(basic_inference)

        assert result["predicted_metadata"] == basic_inference["inferred_metadata"]
        assert result["confidence_scores"] == basic_inference["confidence_scores"]
        assert result["reasoning"] == basic_inference["reasoning"]
        assert "smart_defaults" in result
        assert "fill_suggestions" in result
        assert len(result["fill_suggestions"]) > 0

    def test_basic_predictions_empty_inference(self, system):
        """Test basic predictions with empty inference."""
        basic_inference = {}

        result = system._basic_predictions(basic_inference)

        assert result["predicted_metadata"] == {}
        assert result["confidence_scores"] == {}
        assert result["reasoning"] == {}
        assert isinstance(result["fill_suggestions"], list)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestPredictionStorage:
    """Tests for prediction history storage and pattern learning."""

    @pytest.fixture
    def system(self):
        """Create system for storage tests."""
        return PredictiveMetadataSystem()

    def test_store_prediction_adds_to_history(self, system):
        """Test storing prediction adds to history."""
        predictions = {
            "predicted_metadata": {"experimenter": "Jane Doe"},
            "confidence_scores": {"experimenter": 85},
        }

        system._store_prediction("/path/to/file.nwb", predictions)

        assert len(system.prediction_history) == 1
        assert system.prediction_history[0]["path"] == "/path/to/file.nwb"
        assert system.prediction_history[0]["metadata"] == predictions["predicted_metadata"]

    def test_store_prediction_maintains_max_history(self, system):
        """Test prediction history maintains maximum size of 20."""
        # Add 25 predictions
        for i in range(25):
            predictions = {
                "predicted_metadata": {"experimenter": f"Person {i}"},
                "confidence_scores": {"experimenter": 80 + i},
            }
            system._store_prediction(f"/path/file{i}.nwb", predictions)

        # Should keep only last 20
        assert len(system.prediction_history) == 20
        # Should have the most recent ones (5-24)
        assert "Person 24" in str(system.prediction_history[-1]["metadata"])


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestPatternMatching:
    """Tests for finding similar file patterns."""

    @pytest.fixture
    def system_with_history(self):
        """Create system with prediction history."""
        system = PredictiveMetadataSystem()

        # Add some predictions to history
        system.prediction_history = [
            {
                "path": "/data/spikeglx/mouse_123.bin",
                "format": "SpikeGLX",
                "filename_parts": {
                    "has_subject_id": True,
                    "has_date": True,
                },
                "metadata": {"experimenter": "John Doe", "institution": "MIT"},
            },
            {
                "path": "/data/openephys/rat_456.bin",
                "format": "OpenEphys",
                "filename_parts": {
                    "has_subject_id": True,
                    "has_date": False,
                },
                "metadata": {"experimenter": "Jane Smith", "institution": "Harvard"},
            },
        ]

        return system

    def test_find_similar_patterns_same_format(self, system_with_history):
        """Test finding similar patterns with same format."""
        file_analysis = {
            "format": "SpikeGLX",
            "filename_parts": {
                "has_subject_id": True,
                "has_date": True,
            },
        }

        similar = system_with_history._find_similar_patterns(file_analysis)

        # Should find the SpikeGLX file as similar
        assert len(similar) > 0
        assert similar[0]["similarity"] > 40

    def test_find_similar_patterns_no_match(self, system_with_history):
        """Test finding similar patterns with no matches."""
        file_analysis = {
            "format": "Unknown",
            "filename_parts": {
                "has_subject_id": False,
                "has_date": False,
            },
        }

        similar = system_with_history._find_similar_patterns(file_analysis)

        # Should not find similar files (similarity <= 40)
        assert len(similar) == 0

    def test_find_similar_patterns_empty_history(self):
        """Test finding similar patterns with empty history."""
        system = PredictiveMetadataSystem()

        file_analysis = {
            "format": "SpikeGLX",
            "filename_parts": {"has_subject_id": True},
        }

        similar = system._find_similar_patterns(file_analysis)

        assert len(similar) == 0


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestSpikeGLXAnalysis:
    """Tests for SpikeGLX deep file analysis."""

    @pytest.mark.asyncio
    async def test_analyze_spikeglx_with_meta_file(self, tmp_path, global_state):
        """Test SpikeGLX analysis with .meta file present."""
        system = PredictiveMetadataSystem()

        # Create mock .bin and .meta files
        bin_file = tmp_path / "recording.imec0.ap.bin"
        meta_file = tmp_path / "recording.imec0.ap.meta"

        bin_file.write_bytes(b"mock binary data")
        meta_file.write_text("imSampRate=30000\nnSavedChans=385\nfileTimeSecs=600\nimProbeOpt=4\n")

        analysis = await system._analyze_spikeglx_deep(bin_file, global_state)

        assert "spikeglx_details" in analysis
        assert analysis["spikeglx_details"]["has_meta_file"] is True
        assert analysis["spikeglx_details"]["sampling_rate"] == "30000"
        assert analysis["spikeglx_details"]["channel_count"] == "385"

    @pytest.mark.asyncio
    async def test_analyze_spikeglx_without_meta_file(self, tmp_path, global_state):
        """Test SpikeGLX analysis without .meta file."""
        system = PredictiveMetadataSystem()

        bin_file = tmp_path / "recording.imec0.ap.bin"
        bin_file.write_bytes(b"mock binary data")

        analysis = await system._analyze_spikeglx_deep(bin_file, global_state)

        assert "spikeglx_details" in analysis
        # Should not have meta file details
        assert not analysis["spikeglx_details"].get("has_meta_file")

    @pytest.mark.asyncio
    async def test_analyze_spikeglx_corrupted_meta_file(self, tmp_path, global_state):
        """Test SpikeGLX analysis with corrupted .meta file."""
        system = PredictiveMetadataSystem()

        bin_file = tmp_path / "recording.imec0.ap.bin"
        meta_file = tmp_path / "recording.imec0.ap.meta"

        bin_file.write_bytes(b"mock binary data")
        # Lines without '=' are skipped, so this should result in empty metadata
        meta_file.write_text("corrupted data without equals signs\n")

        # Should handle gracefully
        analysis = await system._analyze_spikeglx_deep(bin_file, global_state)

        assert "spikeglx_details" in analysis
        # Meta file exists but has no parseable content
        assert analysis["spikeglx_details"]["has_meta_file"] is True
        assert analysis["spikeglx_details"]["sampling_rate"] is None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestOpenEphysAnalysis:
    """Tests for OpenEphys file analysis."""

    @pytest.mark.asyncio
    async def test_analyze_openephys(self, tmp_path, global_state):
        """Test OpenEphys analysis."""
        system = PredictiveMetadataSystem()

        data_file = tmp_path / "recording.continuous"
        data_file.write_bytes(b"mock openephys data")

        analysis = await system._analyze_openephys_deep(data_file, global_state)

        assert "openephys_details" in analysis
        assert isinstance(analysis["openephys_details"], dict)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestDeepFileAnalysis:
    """Tests for deep file analysis dispatcher."""

    @pytest.mark.asyncio
    async def test_deep_file_analysis_spikeglx(self, tmp_path, global_state):
        """Test deep analysis dispatches to SpikeGLX handler."""
        system = PredictiveMetadataSystem()

        file_path = tmp_path / "mouse_123_20240117.imec0.ap.bin"
        file_path.write_bytes(b"mock data")

        analysis = await system._deep_file_analysis(str(file_path), "SpikeGLX", global_state)

        assert analysis["path"] == str(file_path)
        assert analysis["format"] == "SpikeGLX"
        assert "filename_parts" in analysis
        assert "spikeglx_details" in analysis

    @pytest.mark.asyncio
    async def test_deep_file_analysis_openephys(self, tmp_path, global_state):
        """Test deep analysis dispatches to OpenEphys handler."""
        system = PredictiveMetadataSystem()

        file_path = tmp_path / "recording.continuous"
        file_path.write_bytes(b"mock data")

        analysis = await system._deep_file_analysis(str(file_path), "OpenEphys", global_state)

        assert analysis["format"] == "OpenEphys"
        assert "openephys_details" in analysis

    @pytest.mark.asyncio
    async def test_deep_file_analysis_unknown_format(self, tmp_path, global_state):
        """Test deep analysis with unknown format."""
        system = PredictiveMetadataSystem()

        file_path = tmp_path / "data.unknown"
        file_path.write_bytes(b"mock data")

        analysis = await system._deep_file_analysis(str(file_path), "Unknown", global_state)

        # Should still return basic analysis
        assert analysis["format"] == "Unknown"
        assert "filename_parts" in analysis


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestPredictMetadata:
    """Tests for main predict_metadata method."""

    @pytest.mark.asyncio
    async def test_predict_metadata_with_llm(self, tmp_path, global_state):
        """Test prediction with LLM service."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "predicted_metadata": {
                    "experimenter": "Jane Doe",
                    "institution": "MIT",
                    "subject_id": "mouse_123",
                },
                "confidence_scores": {
                    "experimenter": 85,
                    "institution": 90,
                    "subject_id": 95,
                },
                "reasoning": {
                    "experimenter": "Extracted from filename pattern",
                    "institution": "Common lab associated with this data type",
                    "subject_id": "Parsed from filename",
                },
                "smart_defaults": {},
                "fill_suggestions": ["Review and confirm metadata"],
            }
        )

        system = PredictiveMetadataSystem(llm_service=llm_service)

        file_path = tmp_path / "Doe_2024-01-17_mouse_123.bin"
        file_path.write_bytes(b"mock data")

        basic_inference = {
            "inferred_metadata": {"subject_id": "mouse_123"},
            "confidence_scores": {"subject_id": 80},
            "reasoning": {"subject_id": "From filename"},
        }

        result = await system.predict_metadata(str(file_path), "SpikeGLX", basic_inference, global_state)

        assert "predicted_metadata" in result
        assert "experimenter" in result["predicted_metadata"]
        assert result["confidence_scores"]["experimenter"] == 85
        # Should have called LLM
        llm_service.generate_structured_output.assert_called_once()
        # Should have stored prediction
        assert len(system.prediction_history) == 1

    @pytest.mark.asyncio
    async def test_predict_metadata_without_llm_fallback(self, tmp_path, global_state):
        """Test prediction without LLM falls back to basic."""
        system = PredictiveMetadataSystem()  # No LLM

        file_path = tmp_path / "recording.bin"
        file_path.write_bytes(b"mock data")

        basic_inference = {
            "inferred_metadata": {"subject_id": "mouse_001"},
            "confidence_scores": {"subject_id": 75},
            "reasoning": {"subject_id": "Filename pattern"},
        }

        result = await system.predict_metadata(str(file_path), "SpikeGLX", basic_inference, global_state)

        # Should use basic predictions
        assert result["predicted_metadata"] == basic_inference["inferred_metadata"]

    @pytest.mark.asyncio
    async def test_predict_metadata_llm_failure_fallback(self, tmp_path, global_state):
        """Test prediction falls back to basic when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM API error"))

        system = PredictiveMetadataSystem(llm_service=llm_service)

        file_path = tmp_path / "recording.bin"
        file_path.write_bytes(b"mock data")

        basic_inference = {
            "inferred_metadata": {"subject_id": "mouse_001"},
        }

        result = await system.predict_metadata(str(file_path), "SpikeGLX", basic_inference, global_state)

        # Should fall back to basic predictions
        assert result["predicted_metadata"] == basic_inference["inferred_metadata"]
        # Should have logged warning
        assert any("Predictive metadata failed" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_predict_metadata_logs_success(self, tmp_path, global_state):
        """Test prediction logs success with field count."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "predicted_metadata": {
                    "experimenter": "Jane Doe",
                    "institution": "MIT",
                },
                "confidence_scores": {
                    "experimenter": 85,
                    "institution": 90,
                },
                "reasoning": {},
            }
        )

        system = PredictiveMetadataSystem(llm_service=llm_service)

        file_path = tmp_path / "data.bin"
        file_path.write_bytes(b"mock data")

        await system.predict_metadata(str(file_path), "SpikeGLX", {}, global_state)

        # Should have logged success
        assert any(
            "Predictive metadata generated" in log.message and "2 fields" in log.message for log in global_state.logs
        )


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestLLMPredictMetadata:
    """Tests for LLM-based metadata prediction."""

    @pytest.mark.asyncio
    async def test_llm_predict_metadata_calls_llm_correctly(self, global_state):
        """Test LLM prediction calls service with correct parameters."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "predicted_metadata": {},
                "confidence_scores": {},
                "reasoning": {},
            }
        )

        system = PredictiveMetadataSystem(llm_service=llm_service)

        await system._llm_predict_metadata(
            file_path="/test/file.bin",
            file_format="SpikeGLX",
            file_analysis={"format": "SpikeGLX"},
            basic_inference={"inferred_metadata": {}},
            similar_patterns=[],
            state=global_state,
        )

        # Verify LLM was called
        llm_service.generate_structured_output.assert_called_once()
        call_args = llm_service.generate_structured_output.call_args

        # Check prompt contains file path and format
        assert "/test/file.bin" in call_args[1]["prompt"]
        assert "SpikeGLX" in call_args[1]["prompt"]
        # Check schema was provided
        assert "output_schema" in call_args[1]
        assert "predicted_metadata" in call_args[1]["output_schema"]["properties"]
