"""
Unit tests for MetadataInferenceEngine.

Tests intelligent metadata extraction from files.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from agents.metadata_inference import MetadataInferenceEngine
from models.state import GlobalState


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    service = Mock()
    service.generate_structured_output = AsyncMock()
    return service


@pytest.fixture
def inference_engine(mock_llm_service):
    """Create inference engine with mock LLM."""
    return MetadataInferenceEngine(llm_service=mock_llm_service)


@pytest.fixture
def state():
    """Create mock global state."""
    state = GlobalState()
    state.metadata = {"format": "SpikeGLX"}
    return state


class TestMetadataInferenceEngine:
    """Test suite for MetadataInferenceEngine."""

    def test_initialization(self, mock_llm_service):
        """Test engine initialization."""
        engine = MetadataInferenceEngine(llm_service=mock_llm_service)
        assert engine.llm_service == mock_llm_service

    def test_initialization_without_llm(self):
        """Test engine works without LLM."""
        engine = MetadataInferenceEngine(llm_service=None)
        assert engine.llm_service is None

    def test_spikeglx_metadata_extraction(self, inference_engine):
        """Test SpikeGLX-specific metadata extraction."""
        metadata = inference_engine._extract_spikeglx_metadata(
            "test_data/Noise4Sam_g0_t0.imec0.ap.bin"
        )

        assert metadata["recording_type"] == "electrophysiology"
        assert metadata["system"] == "SpikeGLX"
        assert metadata["probe_type"] == "Neuropixels"
        assert metadata["data_stream"] == "action potentials (AP)"

    def test_spikeglx_lf_stream_detection(self, inference_engine):
        """Test LF stream detection in SpikeGLX files."""
        metadata = inference_engine._extract_spikeglx_metadata(
            "test_data/recording.imec0.lf.bin"
        )

        assert metadata["data_stream"] == "local field potentials (LF)"

    def test_species_inference_from_filename(self, inference_engine, state):
        """Test species inference from filename patterns."""
        file_meta = {"file_name": "mouse_recording_v1.bin"}

        heuristic = inference_engine._apply_heuristic_rules(file_meta, state)

        assert heuristic["species"] == "Mus musculus"
        assert heuristic["species_common_name"] == "house mouse"

    def test_brain_region_inference_from_filename(self, inference_engine, state):
        """Test brain region inference from filename."""
        file_meta = {"file_name": "recording_v1_experiment.bin"}

        heuristic = inference_engine._apply_heuristic_rules(file_meta, state)

        assert heuristic["brain_region"] == "V1"
        assert heuristic["brain_region_full"] == "primary visual cortex"

    def test_keywords_generation(self, inference_engine, state):
        """Test automatic keyword generation."""
        file_meta = {
            "file_name": "mouse_v1_neuropixels.bin",
            "probe_type": "Neuropixels",
        }

        heuristic = inference_engine._apply_heuristic_rules(file_meta, state)

        assert "keywords" in heuristic
        keywords = heuristic["keywords"]
        assert "Neuropixels" in keywords
        assert "V1" in keywords

    @pytest.mark.asyncio
    async def test_full_inference_with_llm(
        self, inference_engine, mock_llm_service, state
    ):
        """Test full inference pipeline with LLM."""
        # Mock file existence
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024  # 1 MB

                # Mock LLM response
                mock_llm_service.generate_structured_output.return_value = {
                    "inferred_metadata": {
                        "recording_modality": "electrophysiology",
                        "experiment_description": "Neural recording in visual cortex",
                    },
                    "confidence_scores": {
                        "recording_modality": 90,
                        "experiment_description": 75,
                    },
                    "reasoning": {
                        "recording_modality": "SpikeGLX format indicates electrophysiology",
                    },
                }

                result = await inference_engine.infer_metadata(
                    input_path="test_data/mouse_v1.bin",
                    state=state,
                )

        assert "inferred_metadata" in result
        assert "confidence_scores" in result
        assert "reasoning" in result
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_llm(self, state):
        """Test inference without LLM (heuristics only)."""
        engine = MetadataInferenceEngine(llm_service=None)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024

                result = await engine.infer_metadata(
                    input_path="test_data/mouse_v1_neuropixels.bin",
                    state=state,
                )

        # Should still have heuristic inferences
        assert "inferred_metadata" in result
        metadata = result["inferred_metadata"]

        # Heuristic rules should work
        assert metadata.get("species") == "Mus musculus"
        assert metadata.get("brain_region") == "V1"

    @pytest.mark.asyncio
    async def test_confidence_scoring(
        self, inference_engine, mock_llm_service, state
    ):
        """Test confidence score priority system."""
        mock_llm_service.generate_structured_output.return_value = {
            "inferred_metadata": {
                "recording_modality": "electrophysiology",
            },
            "confidence_scores": {
                "recording_modality": 75,
            },
            "reasoning": {},
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024

                result = await inference_engine.infer_metadata(
                    input_path="test_data/mouse_neuropixels.bin",
                    state=state,
                )

        scores = result["confidence_scores"]

        # Direct extraction should have highest confidence (95)
        # Heuristic rules should have 85
        # LLM inference should have specified confidence (75)
        assert all(0 <= score <= 100 for score in scores.values())

    @pytest.mark.asyncio
    async def test_error_handling(self, inference_engine, state):
        """Test error handling in inference."""
        # Non-existent file should not crash
        result = await inference_engine.infer_metadata(
            input_path="/nonexistent/file.bin",
            state=state,
        )

        # Should return empty result with suggestions
        assert result["inferred_metadata"] == {}
        assert result["confidence_scores"] == {}
        assert len(result["suggestions"]) > 0

    def test_rat_species_detection(self, inference_engine, state):
        """Test rat species detection."""
        file_meta = {"file_name": "rat_hippocampus_recording.bin"}

        heuristic = inference_engine._apply_heuristic_rules(file_meta, state)

        assert heuristic["species"] == "Rattus norvegicus"
        assert heuristic["species_common_name"] == "Norway rat"

    def test_hippocampus_brain_region(self, inference_engine, state):
        """Test hippocampus brain region detection."""
        file_meta = {"file_name": "rat_hpc_recording.bin"}

        heuristic = inference_engine._apply_heuristic_rules(file_meta, state)

        assert heuristic["brain_region"] == "HPC"
        assert heuristic["brain_region_full"] == "hippocampus"

    def test_openephys_metadata_extraction(self, inference_engine):
        """Test OpenEphys-specific metadata."""
        metadata = inference_engine._extract_openephys_metadata("test.dat")

        assert metadata["recording_type"] == "electrophysiology"
        assert metadata["system"] == "Open Ephys"

    def test_intan_metadata_extraction(self, inference_engine):
        """Test Intan-specific metadata."""
        metadata = inference_engine._extract_intan_metadata("test.rhd")

        assert metadata["recording_type"] == "electrophysiology"
        assert metadata["system"] == "Intan"

    @pytest.mark.asyncio
    async def test_low_confidence_warnings(
        self, inference_engine, mock_llm_service, state
    ):
        """Test that low confidence inferences generate warnings."""
        mock_llm_service.generate_structured_output.return_value = {
            "inferred_metadata": {
                "experiment_description": "Some description",
            },
            "confidence_scores": {
                "experiment_description": 50,  # Low confidence
            },
            "reasoning": {},
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024

                result = await inference_engine.infer_metadata(
                    input_path="test.bin",
                    state=state,
                )

        # Should have warning about low confidence
        suggestions = result["suggestions"]
        assert any("Low confidence" in s or "review" in s.lower() for s in suggestions)
