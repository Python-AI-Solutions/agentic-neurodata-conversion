"""
Unit tests for metadata mapping functionality.

Tests the critical metadata transformation logic that converts flat
user input to NWB's nested metadata structure.
"""

import pytest

from backend.src.agents.conversion_agent import ConversionAgent


@pytest.mark.unit
class TestMetadataMapping:
    """Test suite for metadata structure mapping."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversionAgent(llm_service=None)

    def test_nwbfile_fields_mapping(self):
        """Test that NWBFile fields are correctly mapped."""
        flat_metadata = {
            "experimenter": "Dr. Jane Smith",
            "institution": "MIT",
            "session_description": "Test recording session",
            "keywords": "electrophysiology, mouse",
        }

        result = self.agent._map_flat_to_nested_metadata(flat_metadata)

        assert "NWBFile" in result
        assert result["NWBFile"]["experimenter"] == ["Dr. Jane Smith"]
        assert result["NWBFile"]["institution"] == "MIT"
        assert result["NWBFile"]["session_description"] == "Test recording session"
        assert result["NWBFile"]["keywords"] == ["electrophysiology, mouse"]

    def test_subject_fields_mapping(self):
        """Test that Subject fields are correctly mapped."""
        flat_metadata = {
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "age": "P90D",
            "sex": "M",
        }

        result = self.agent._map_flat_to_nested_metadata(flat_metadata)

        assert "Subject" in result
        assert result["Subject"]["subject_id"] == "mouse001"
        assert result["Subject"]["species"] == "Mus musculus"
        assert result["Subject"]["age"] == "P90D"
        assert result["Subject"]["sex"] == "M"

    def test_mixed_fields_mapping(self):
        """Test mapping of both NWBFile and Subject fields together."""
        flat_metadata = {
            "experimenter": "Dr. Smith",
            "institution": "Stanford",
            "subject_id": "rat042",
            "species": "Rattus norvegicus",
        }

        result = self.agent._map_flat_to_nested_metadata(flat_metadata)

        assert "NWBFile" in result
        assert "Subject" in result
        assert result["NWBFile"]["experimenter"] == ["Dr. Smith"]
        assert result["NWBFile"]["institution"] == "Stanford"
        assert result["Subject"]["subject_id"] == "rat042"
        assert result["Subject"]["species"] == "Rattus norvegicus"

    def test_list_field_string_conversion(self):
        """Test that string values for list fields are converted to lists."""
        flat_metadata = {
            "experimenter": "Single Experimenter",
            "keywords": "single keyword",
        }

        result = self.agent._map_flat_to_nested_metadata(flat_metadata)

        # Should convert strings to lists
        assert isinstance(result["NWBFile"]["experimenter"], list)
        assert result["NWBFile"]["experimenter"] == ["Single Experimenter"]
        assert isinstance(result["NWBFile"]["keywords"], list)
        assert result["NWBFile"]["keywords"] == ["single keyword"]

    def test_list_field_preserves_lists(self):
        """Test that list values for list fields are preserved."""
        flat_metadata = {
            "experimenter": ["Dr. Smith", "Dr. Jones"],
            "keywords": ["ephys", "behavior", "optogenetics"],
        }

        result = self.agent._map_flat_to_nested_metadata(flat_metadata)

        # Should preserve existing lists
        assert result["NWBFile"]["experimenter"] == ["Dr. Smith", "Dr. Jones"]
        assert result["NWBFile"]["keywords"] == ["ephys", "behavior", "optogenetics"]

    def test_empty_metadata(self):
        """Test handling of empty metadata dict."""
        result = self.agent._map_flat_to_nested_metadata({})

        # Should return empty dict, not fail
        assert result == {}

    def test_unknown_field_goes_to_nwbfile(self):
        """Test that unknown fields default to NWBFile section."""
        flat_metadata = {
            "custom_field": "custom value",
            "another_unknown": 42,
        }

        result = self.agent._map_flat_to_nested_metadata(flat_metadata)

        # Unknown fields should go to NWBFile as fallback
        assert "NWBFile" in result
        assert result["NWBFile"]["custom_field"] == "custom value"
        assert result["NWBFile"]["another_unknown"] == 42

    def test_all_nwbfile_fields_recognized(self):
        """Test that all standard NWBFile fields are correctly categorized."""
        nwbfile_fields = {
            "session_description": "test",
            "experiment_description": "test exp",
            "session_id": "session_001",
            "lab": "Neuroscience Lab",
            "protocol": "Protocol ABC",
            "notes": "Some notes",
            "related_publications": "DOI:10.1234/test",
        }

        result = self.agent._map_flat_to_nested_metadata(nwbfile_fields)

        assert "NWBFile" in result
        assert "Subject" not in result  # Should not create Subject section
        for key, value in nwbfile_fields.items():
            if key in ["related_publications"]:
                # List fields
                assert result["NWBFile"][key] == [value]
            else:
                assert result["NWBFile"][key] == value

    def test_all_subject_fields_recognized(self):
        """Test that all standard Subject fields are correctly categorized."""
        subject_fields = {
            "subject_id": "sub-001",
            "species": "Homo sapiens",
            "age": "25Y",
            "sex": "F",
            "description": "Healthy adult",
            "weight": "70kg",
            "strain": "Wild-type",
            "genotype": "WT",
        }

        result = self.agent._map_flat_to_nested_metadata(subject_fields)

        assert "Subject" in result
        assert "NWBFile" not in result  # Should not create NWBFile section
        for key, value in subject_fields.items():
            assert result["Subject"][key] == value

    def test_regression_metadata_persistence_bug(self):
        """
        Regression test for the metadata persistence bug.

        This test verifies the fix for the critical bug where user-provided
        metadata wasn't appearing in NWB files because of structure mismatch.
        """
        # Simulate what a user would provide through the chat interface
        user_input = {
            "experimenter": "Dr. Rodriguez",
            "institution": "UC Berkeley",
            "session_description": "Recording in mouse V1 during visual stimulation",
            "subject_id": "mouse_042",
            "species": "Mus musculus",
        }

        # Apply the transformation
        structured = self.agent._map_flat_to_nested_metadata(user_input)

        # Verify the structure matches what NeuroConv expects
        assert "NWBFile" in structured, "Missing NWBFile section"
        assert "Subject" in structured, "Missing Subject section"

        # Verify experimenter is a list (NeuroConv requirement)
        assert isinstance(structured["NWBFile"]["experimenter"], list)
        assert structured["NWBFile"]["experimenter"] == ["Dr. Rodriguez"]

        # Verify other NWBFile fields
        assert structured["NWBFile"]["institution"] == "UC Berkeley"
        assert structured["NWBFile"]["session_description"] == "Recording in mouse V1 during visual stimulation"

        # Verify Subject fields
        assert structured["Subject"]["subject_id"] == "mouse_042"
        assert structured["Subject"]["species"] == "Mus musculus"

        # This structure should now merge correctly with NeuroConv's metadata
        # without throwing KeyError or type mismatch errors
