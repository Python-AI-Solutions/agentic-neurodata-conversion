"""Unit tests for ConversionHelpers.

Tests metadata mapping, checksum calculation, and progress narration with
focus on uncovered lines 93, 107, 124-157.
"""

from unittest.mock import AsyncMock

import pytest

from agentic_neurodata_conversion.agents.conversion.conversion_helpers import ConversionHelpers

# ============================================================================
# TestMapFlatToNestedMetadata
# ============================================================================


@pytest.mark.unit
class TestMapFlatToNestedMetadata:
    """Test map_flat_to_nested_metadata with edge cases."""

    def test_skip_internal_fields(self):
        """Test line 93: Skip fields starting with underscore."""
        flat_metadata = {
            "experimenter": "Dr. Smith",
            "_internal_id": "12345",
            "_debug_flag": True,
            "institution": "MIT",
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Internal fields should be skipped
        assert "_internal_id" not in str(result)
        assert "_debug_flag" not in str(result)
        # Regular fields should be present
        assert result["NWBFile"]["experimenter"] == ["Dr. Smith"]
        assert result["NWBFile"]["institution"] == "MIT"

    def test_non_list_experimenter_value_int(self):
        """Test line 107: Convert non-list/non-string (int) to list."""
        flat_metadata = {
            "experimenter": 12345,  # Non-string, non-list value
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Should convert to string and wrap in list (line 107)
        assert result["NWBFile"]["experimenter"] == ["12345"]

    def test_non_list_experimenter_value_dict(self):
        """Test line 107: Convert non-list/non-string (dict) to list."""
        flat_metadata = {
            "experimenter": {"name": "Dr. Smith", "id": 123},
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Should convert to string representation and wrap in list
        assert isinstance(result["NWBFile"]["experimenter"], list)
        assert len(result["NWBFile"]["experimenter"]) == 1
        assert "name" in result["NWBFile"]["experimenter"][0]

    def test_non_list_keywords_value(self):
        """Test line 107: Convert non-list keywords to list."""
        flat_metadata = {
            "keywords": 42,  # Non-string, non-list value
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Should convert to string and wrap in list
        assert result["NWBFile"]["keywords"] == ["42"]

    def test_non_list_related_publications_value(self):
        """Test line 107: Convert non-list related_publications to list."""
        flat_metadata = {
            "related_publications": 3.14,  # Float value
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Should convert to string and wrap in list
        assert result["NWBFile"]["related_publications"] == ["3.14"]

    def test_custom_fields_processing(self):
        """Test lines 124-157: Custom field handling."""
        flat_metadata = {
            "experimenter": "Dr. Smith",
            "_custom_fields": {
                "Lab Equipment": "Nikon microscope",
                "Protocol Version": "2.1",
            },
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Custom fields should be added with cleaned keys (lines 134-135)
        assert "lab_equipment" in result["NWBFile"]
        assert result["NWBFile"]["lab_equipment"] == "Nikon microscope"
        assert "protocol_version" in result["NWBFile"]
        assert result["NWBFile"]["protocol_version"] == "2.1"

        # Custom fields summary should be added to notes (lines 148-157)
        assert "notes" in result["NWBFile"]
        assert "Custom metadata fields:" in result["NWBFile"]["notes"]
        assert "Lab Equipment: Nikon microscope" in result["NWBFile"]["notes"]
        assert "Protocol Version: 2.1" in result["NWBFile"]["notes"]

    def test_custom_fields_subject_related(self):
        """Test lines 138-142: Subject-related custom fields."""
        flat_metadata = {
            "_custom_fields": {
                "mouse_strain": "C57BL/6",
                "subject_condition": "healthy",
                "animal_id": "M123",
            },
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Subject-related custom fields should go to Subject (lines 138-142)
        assert "Subject" in result
        assert "mouse_strain" in result["Subject"]
        assert result["Subject"]["mouse_strain"] == "C57BL/6"
        assert "subject_condition" in result["Subject"]
        assert result["Subject"]["subject_condition"] == "healthy"
        assert "animal_id" in result["Subject"]
        assert result["Subject"]["animal_id"] == "M123"

        # Notes summary should still be created (lines 148-157)
        assert "notes" in result["NWBFile"]
        assert "Custom metadata fields:" in result["NWBFile"]["notes"]

    def test_custom_fields_with_existing_notes(self):
        """Test lines 153-155: Append custom fields to existing notes."""
        flat_metadata = {
            "notes": "Existing notes about the experiment",
            "_custom_fields": {
                "equipment": "Special device",
            },
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Existing notes should be preserved and custom summary appended
        assert "Existing notes about the experiment" in result["NWBFile"]["notes"]
        assert "Custom metadata fields:" in result["NWBFile"]["notes"]
        assert "equipment: Special device" in result["NWBFile"]["notes"]
        # Should have both parts separated by newlines (line 155)
        assert "\n\n" in result["NWBFile"]["notes"]

    def test_custom_fields_empty_dict(self):
        """Test lines 127-157: Empty custom fields dict."""
        flat_metadata = {
            "experimenter": "Dr. Smith",
            "_custom_fields": {},
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Empty custom fields should not add notes (line 148 check)
        # Only experimenter should be present
        assert "experimenter" in result["NWBFile"]
        # Notes should not be added for empty custom fields
        assert "notes" not in result["NWBFile"] or result["NWBFile"]["notes"] == ""

    def test_custom_fields_multiple_subject_keywords(self):
        """Test line 138: Multiple subject-related keywords detection."""
        flat_metadata = {
            "_custom_fields": {
                "rat_behavior": "exploratory",
                "animal_weight_kg": "0.3",
                "subject_genotype_detail": "wild-type",
                "mouse_age_weeks": "8",
            },
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # All should be placed in Subject due to keywords (lines 138-142)
        assert "Subject" in result
        assert "rat_behavior" in result["Subject"]
        assert "animal_weight_kg" in result["Subject"]
        assert "subject_genotype_detail" in result["Subject"]
        assert "mouse_age_weeks" in result["Subject"]

    def test_custom_fields_mixed_placement(self):
        """Test lines 138-145: Mixed subject and general custom fields."""
        flat_metadata = {
            "_custom_fields": {
                "subject_id_extra": "ABC123",  # Should go to Subject
                "equipment_type": "microscope",  # Should go to NWBFile
                "mouse_notes": "Special handling",  # Should go to Subject
                "data_quality": "excellent",  # Should go to NWBFile
            },
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Subject-related fields in Subject (lines 138-142)
        assert "Subject" in result
        assert "subject_id_extra" in result["Subject"]
        assert "mouse_notes" in result["Subject"]

        # General fields in NWBFile (lines 144-145)
        assert "data_quality" in result["NWBFile"]

        # All custom fields should be documented in notes (lines 148-157)
        assert "notes" in result["NWBFile"]
        assert "Custom metadata fields:" in result["NWBFile"]["notes"]
        assert "subject_id_extra: ABC123" in result["NWBFile"]["notes"]
        assert "equipment_type: microscope" in result["NWBFile"]["notes"]
        assert "mouse_notes: Special handling" in result["NWBFile"]["notes"]
        assert "data_quality: excellent" in result["NWBFile"]["notes"]


# ============================================================================
# TestCalculateChecksum
# ============================================================================


@pytest.mark.unit
class TestCalculateChecksum:
    """Test calculate_checksum method."""

    def test_calculate_checksum_valid_file(self, tmp_path):
        """Test checksum calculation for valid file."""
        # Create a test file
        test_file = tmp_path / "test_data.txt"
        test_file.write_text("Test data content")

        result = ConversionHelpers.calculate_checksum(str(test_file))

        # Should return a SHA256 hex digest (64 characters)
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculate_checksum_empty_file(self, tmp_path):
        """Test checksum calculation for empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = ConversionHelpers.calculate_checksum(str(test_file))

        # Should still return a valid SHA256 hash
        assert isinstance(result, str)
        assert len(result) == 64

    def test_calculate_checksum_binary_file(self, tmp_path):
        """Test checksum calculation for binary file."""
        test_file = tmp_path / "binary.dat"
        test_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        result = ConversionHelpers.calculate_checksum(str(test_file))

        # Should return a valid SHA256 hash
        assert isinstance(result, str)
        assert len(result) == 64


# ============================================================================
# TestNarrateProgress
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestNarrateProgress:
    """Test narrate_progress method with and without LLM."""

    async def test_narrate_progress_without_llm(self, global_state):
        """Test progress narration fallback without LLM."""
        helpers = ConversionHelpers(llm_service=None)

        result = await helpers.narrate_progress(
            stage="starting",
            format_name="Calcium Imaging",
            context={},
            state=global_state,
        )

        # Should return fallback message
        assert "Starting conversion" in result
        assert "Calcium Imaging" in result

    async def test_narrate_progress_processing_stage(self, global_state):
        """Test processing stage fallback."""
        helpers = ConversionHelpers(llm_service=None)

        result = await helpers.narrate_progress(
            stage="processing",
            format_name="Electrophysiology",
            context={"progress_percent": 45},
            state=global_state,
        )

        # Should include progress percentage
        assert "Processing" in result
        assert "Electrophysiology" in result
        assert "45%" in result

    async def test_narrate_progress_finalizing_stage(self, global_state):
        """Test finalizing stage fallback."""
        helpers = ConversionHelpers(llm_service=None)

        result = await helpers.narrate_progress(
            stage="finalizing",
            format_name="Any Format",
            context={},
            state=global_state,
        )

        # Should return finalizing message
        assert "Finalizing" in result

    async def test_narrate_progress_complete_stage(self, global_state):
        """Test complete stage fallback."""
        helpers = ConversionHelpers(llm_service=None)

        result = await helpers.narrate_progress(
            stage="complete",
            format_name="Any Format",
            context={},
            state=global_state,
        )

        # Should return complete message
        assert "complete" in result.lower()

    async def test_narrate_progress_unknown_stage(self, global_state):
        """Test unknown stage fallback."""
        helpers = ConversionHelpers(llm_service=None)

        result = await helpers.narrate_progress(
            stage="unknown_stage",
            format_name="Any Format",
            context={},
            state=global_state,
        )

        # Should return generic processing message
        assert "Processing" in result

    async def test_narrate_progress_with_llm_success(self, mock_llm_service, global_state):
        """Test progress narration with LLM service."""
        # Mock LLM response
        mock_llm_service.generate_completion = AsyncMock(
            return_value="Great! We're converting your calcium imaging data now."
        )

        helpers = ConversionHelpers(llm_service=mock_llm_service)

        result = await helpers.narrate_progress(
            stage="processing",
            format_name="Calcium Imaging",
            context={"progress_percent": 50},
            state=global_state,
        )

        # Should return LLM-generated narration
        assert "calcium imaging" in result.lower()
        mock_llm_service.generate_completion.assert_called_once()

        # Should log the narration
        assert any("Progress:" in log.message for log in global_state.logs)

    async def test_narrate_progress_with_llm_failure(self, mock_llm_service, global_state):
        """Test progress narration when LLM fails."""
        # Mock LLM to raise exception
        mock_llm_service.generate_completion = AsyncMock(side_effect=Exception("LLM service error"))

        helpers = ConversionHelpers(llm_service=mock_llm_service)

        result = await helpers.narrate_progress(
            stage="starting",
            format_name="Electrophysiology",
            context={},
            state=global_state,
        )

        # Should fall back to generic message
        assert "Processing" in result
        assert "Electrophysiology" in result
        assert "starting" in result

        # Should log the failure
        assert any("Progress narration failed" in log.message for log in global_state.logs)

    async def test_narrate_progress_with_complex_context(self, mock_llm_service, global_state):
        """Test progress narration with complex context."""
        mock_llm_service.generate_completion = AsyncMock(return_value="Processing your large dataset with 1000 trials.")

        helpers = ConversionHelpers(llm_service=mock_llm_service)

        context = {
            "progress_percent": 75,
            "files_processed": 5,
            "total_files": 10,
            "current_file": "trial_005.dat",
        }

        result = await helpers.narrate_progress(
            stage="processing",
            format_name="Behavioral Data",
            context=context,
            state=global_state,
        )

        # Should return LLM narration
        assert isinstance(result, str)
        assert len(result) > 0

        # Check that context was passed to LLM
        call_args = mock_llm_service.generate_completion.call_args
        assert "Context:" in call_args.kwargs["prompt"]


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestConversionHelpersIntegration:
    """Integration tests for ConversionHelpers."""

    def test_full_metadata_mapping_workflow(self):
        """Test complete metadata mapping with all features."""
        flat_metadata = {
            "experimenter": "Dr. Jane Smith",
            "institution": "Stanford University",
            "subject_id": "M001",
            "species": "Mus musculus",
            "age": "P90D",
            "keywords": "calcium imaging",
            "notes": "Initial experiment notes",
            "_internal_flag": "skip_me",
            "_custom_fields": {
                "Lab Equipment": "Two-photon microscope",
                "Protocol Version": "3.1",
                "mouse_strain": "C57BL/6",
                "subject_weight": "25g",
                "imaging_depth": "200um",
            },
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # NWBFile fields
        assert result["NWBFile"]["experimenter"] == ["Dr. Jane Smith"]
        assert result["NWBFile"]["institution"] == "Stanford University"
        assert result["NWBFile"]["keywords"] == ["calcium imaging"]

        # Subject fields
        assert result["Subject"]["subject_id"] == "M001"
        assert result["Subject"]["species"] == "Mus musculus"
        assert result["Subject"]["age"] == "P90D"

        # Custom fields - subject-related in Subject
        assert result["Subject"]["mouse_strain"] == "C57BL/6"
        assert result["Subject"]["subject_weight"] == "25g"

        # Custom fields - general in NWBFile
        assert result["NWBFile"]["lab_equipment"] == "Two-photon microscope"
        assert result["NWBFile"]["protocol_version"] == "3.1"
        assert result["NWBFile"]["imaging_depth"] == "200um"

        # Notes should combine existing + custom summary
        assert "Initial experiment notes" in result["NWBFile"]["notes"]
        assert "Custom metadata fields:" in result["NWBFile"]["notes"]
        assert "Lab Equipment: Two-photon microscope" in result["NWBFile"]["notes"]

        # Internal fields should be skipped
        assert "_internal_flag" not in str(result)

    def test_minimal_metadata(self):
        """Test minimal metadata without custom fields."""
        flat_metadata = {
            "session_description": "Test session",
        }

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Should only have NWBFile with session_description
        assert "NWBFile" in result
        assert result["NWBFile"]["session_description"] == "Test session"
        assert "Subject" not in result

    def test_empty_metadata(self):
        """Test empty metadata dictionary."""
        flat_metadata = {}

        result = ConversionHelpers.map_flat_to_nested_metadata(flat_metadata)

        # Should return empty nested structure
        assert result == {}
