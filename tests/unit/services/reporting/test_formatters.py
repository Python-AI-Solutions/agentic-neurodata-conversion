"""Unit tests for report formatting utilities.

Tests all formatting methods in ReportFormatters with focus on edge cases,
N/A handling, and provenance display logic.
"""

import pytest

from agentic_neurodata_conversion.services.reporting.formatters import ReportFormatters

# ============================================================================
# TestFormatSpecies
# ============================================================================


@pytest.mark.unit
class TestFormatSpecies:
    """Test format_species method with edge cases."""

    def test_format_species_na(self):
        """Test N/A handling."""
        assert ReportFormatters.format_species("N/A") == "N/A"

    def test_format_species_empty(self):
        """Test empty string handling."""
        assert ReportFormatters.format_species("") == "N/A"

    def test_format_species_none_like(self):
        """Test None-like handling."""
        assert ReportFormatters.format_species(None or "") == "N/A"

    def test_format_species_unknown(self):
        """Test unknown species fallback."""
        assert ReportFormatters.format_species("Unknown Species") == "Unknown Species"

    def test_format_species_known_with_common_name(self):
        """Test known species with common name."""
        result = ReportFormatters.format_species("Mus musculus")
        assert result == "Mus musculus (House mouse)"

    def test_format_species_all_known_species(self):
        """Test all predefined known species."""
        test_cases = [
            ("Mus musculus", "Mus musculus (House mouse)"),
            ("Rattus norvegicus", "Rattus norvegicus (Norway rat)"),
            ("Homo sapiens", "Homo sapiens (Human)"),
            ("Macaca mulatta", "Macaca mulatta (Rhesus macaque)"),
            ("Danio rerio", "Danio rerio (Zebrafish)"),
            ("Drosophila melanogaster", "Drosophila melanogaster (Fruit fly)"),
            ("Caenorhabditis elegans", "Caenorhabditis elegans (Roundworm)"),
        ]
        for species, expected in test_cases:
            assert ReportFormatters.format_species(species) == expected


# ============================================================================
# TestFormatSex
# ============================================================================


@pytest.mark.unit
class TestFormatSex:
    """Test format_sex method with edge cases."""

    def test_format_sex_na(self):
        """Test N/A handling."""
        assert ReportFormatters.format_sex("N/A") == "N/A"

    def test_format_sex_empty(self):
        """Test empty string handling."""
        assert ReportFormatters.format_sex("") == "N/A"

    def test_format_sex_none_like(self):
        """Test None-like handling."""
        assert ReportFormatters.format_sex(None or "") == "N/A"

    def test_format_sex_lowercase(self):
        """Test case insensitivity with lowercase."""
        assert ReportFormatters.format_sex("m") == "Male"
        assert ReportFormatters.format_sex("f") == "Female"

    def test_format_sex_uppercase(self):
        """Test uppercase sex codes."""
        assert ReportFormatters.format_sex("M") == "Male"
        assert ReportFormatters.format_sex("F") == "Female"
        assert ReportFormatters.format_sex("U") == "Unknown"
        assert ReportFormatters.format_sex("O") == "Other"

    def test_format_sex_unknown_code(self):
        """Test unknown sex code fallback."""
        assert ReportFormatters.format_sex("X") == "X"
        assert ReportFormatters.format_sex("UNKNOWN") == "UNKNOWN"


# ============================================================================
# TestFormatAge
# ============================================================================


@pytest.mark.unit
class TestFormatAge:
    """Test format_age method with ISO 8601 duration parsing."""

    def test_format_age_na(self):
        """Test N/A handling."""
        assert ReportFormatters.format_age("N/A") == "N/A"

    def test_format_age_empty(self):
        """Test empty string handling."""
        assert ReportFormatters.format_age("") == "N/A"

    def test_format_age_none_like(self):
        """Test None-like handling."""
        assert ReportFormatters.format_age(None or "") == "N/A"

    def test_format_age_single_year(self):
        """Test single year (no plural)."""
        result = ReportFormatters.format_age("P1Y")
        assert result == "P1Y (1 year)"

    def test_format_age_multiple_years(self):
        """Test multiple years (plural)."""
        result = ReportFormatters.format_age("P2Y")
        assert result == "P2Y (2 years)"

    def test_format_age_single_month(self):
        """Test single month (no plural)."""
        result = ReportFormatters.format_age("P1M")
        assert result == "P1M (1 month)"

    def test_format_age_multiple_months(self):
        """Test multiple months (plural)."""
        result = ReportFormatters.format_age("P3M")
        assert result == "P3M (3 months)"

    def test_format_age_single_week(self):
        """Test single week (no plural)."""
        result = ReportFormatters.format_age("P1W")
        assert result == "P1W (1 week)"

    def test_format_age_multiple_weeks(self):
        """Test multiple weeks (plural)."""
        result = ReportFormatters.format_age("P8W")
        assert result == "P8W (8 weeks)"

    def test_format_age_single_day(self):
        """Test single day (no plural)."""
        result = ReportFormatters.format_age("P1D")
        assert result == "P1D (1 day)"

    def test_format_age_multiple_days(self):
        """Test multiple days (plural)."""
        result = ReportFormatters.format_age("P90D")
        assert result == "P90D (90 days)"

    def test_format_age_combined_units(self):
        """Test combined units."""
        result = ReportFormatters.format_age("P1Y2M")
        assert result == "P1Y2M (1 year, 2 months)"

        result = ReportFormatters.format_age("P2Y3M5D")
        assert result == "P2Y3M5D (2 years, 3 months, 5 days)"

    def test_format_age_invalid_format(self):
        """Test invalid ISO format fallback."""
        result = ReportFormatters.format_age("invalid")
        assert result == "invalid"

    def test_format_age_zero_values(self):
        """Test edge case with zero values."""
        # P0Y matches the regex and formats as "0 years"
        result = ReportFormatters.format_age("P0Y")
        assert result == "P0Y (0 years)"


# ============================================================================
# TestFormatFilesize
# ============================================================================


@pytest.mark.unit
class TestFormatFilesize:
    """Test format_filesize method."""

    def test_format_filesize_zero(self):
        """Test zero bytes."""
        assert ReportFormatters.format_filesize(0) == "0 B"

    def test_format_filesize_bytes(self):
        """Test bytes."""
        assert ReportFormatters.format_filesize(512) == "512.0 B"

    def test_format_filesize_kilobytes(self):
        """Test kilobytes."""
        assert ReportFormatters.format_filesize(1024) == "1.0 KB"
        assert ReportFormatters.format_filesize(2048) == "2.0 KB"

    def test_format_filesize_megabytes(self):
        """Test megabytes."""
        assert ReportFormatters.format_filesize(1048576) == "1.0 MB"
        assert ReportFormatters.format_filesize(5242880) == "5.0 MB"

    def test_format_filesize_gigabytes(self):
        """Test gigabytes."""
        assert ReportFormatters.format_filesize(1073741824) == "1.0 GB"


# ============================================================================
# TestFormatWithProvenance
# ============================================================================


@pytest.mark.unit
class TestFormatWithProvenance:
    """Test format_with_provenance method with all provenance types."""

    def test_user_specified_provenance(self):
        """Test user-specified provenance badge."""
        result = ReportFormatters.format_with_provenance(
            "Test User",
            "user-specified",
        )
        assert "Test User <b>👤</b>" in result
        assert "USER SPECIFIED" in result

    def test_file_extracted_provenance(self):
        """Test file-extracted provenance badge."""
        result = ReportFormatters.format_with_provenance(
            "2023-01-01",
            "file-extracted",
        )
        assert "2023-01-01 <b>📄</b>" in result
        assert "FILE EXTRACTED" in result

    def test_ai_parsed_provenance(self):
        """Test AI-parsed provenance badge."""
        result = ReportFormatters.format_with_provenance(
            "University of California",
            "ai-parsed",
        )
        assert "University of California <b>🧠</b>" in result
        assert "AI PARSED" in result

    def test_ai_inferred_provenance(self):
        """Test AI-inferred provenance badge."""
        result = ReportFormatters.format_with_provenance(
            "cortex",
            "ai-inferred",
        )
        assert "cortex <b>🤖</b>" in result
        assert "AI INFERRED" in result

    def test_schema_default_provenance(self):
        """Test schema-default provenance badge."""
        result = ReportFormatters.format_with_provenance(
            "default_value",
            "schema-default",
        )
        assert "default_value <b>📋</b>" in result
        assert "SCHEMA DEFAULT" in result

    def test_system_default_provenance(self):
        """Test system-default provenance badge."""
        result = ReportFormatters.format_with_provenance(
            "fallback",
            "system-default",
        )
        assert "fallback <b>⚪</b>" in result
        assert "SYSTEM DEFAULT" in result

    def test_legacy_user_provided_mapping(self):
        """Test legacy user-provided maps to user-specified."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "user-provided",
        )
        assert "<b>👤</b>" in result
        assert "USER SPECIFIED" in result

    def test_legacy_default_mapping(self):
        """Test legacy default maps to system-default."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "default",
        )
        assert "<b>⚪</b>" in result
        assert "SYSTEM DEFAULT" in result

    def test_unknown_provenance_no_badge(self):
        """Test unknown provenance type has no badge."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "unknown-type",
        )
        # Should return value unchanged (no badge)
        assert result == "value"

    def test_ai_parsed_with_confidence(self):
        """Test AI-parsed with confidence score."""
        result = ReportFormatters.format_with_provenance(
            "Institution Name",
            "ai-parsed",
            confidence=85.5,
        )
        assert "Institution Name <b>🧠</b>" in result
        assert "confidence: 86%" in result

    def test_ai_inferred_with_confidence(self):
        """Test AI-inferred with confidence score."""
        result = ReportFormatters.format_with_provenance(
            "Location",
            "ai-inferred",
            confidence=72.3,
        )
        assert "Location <b>🤖</b>" in result
        assert "confidence: 72%" in result

    def test_non_ai_with_confidence_ignored(self):
        """Test confidence ignored for non-AI provenance."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "user-specified",
            confidence=95.0,
        )
        # Confidence should NOT appear for user-specified
        assert "confidence" not in result
        assert "95%" not in result

    def test_source_description(self):
        """Test source description display."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "ai-parsed",
            source_description="Extracted from metadata.yaml",
        )
        assert "Extracted from metadata.yaml" in result

    def test_source_description_truncation(self):
        """Test source description truncation at 50 chars."""
        long_desc = "This is a very long source description that exceeds fifty characters"
        result = ReportFormatters.format_with_provenance(
            "value",
            "ai-parsed",
            source_description=long_desc,
        )
        # Should truncate to 47 chars + "..." (total 50)
        assert "..." in result
        assert "This is a very long source description that" in result
        # The truncated portion should be in the result
        assert long_desc[:50] not in result  # Full text should not be present

    def test_file_extracted_with_source_file(self):
        """Test file-extracted with source file path."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "file-extracted",
            source_file="/path/to/data.txt",
        )
        assert "from: /path/to/data.txt" in result

    def test_file_extracted_source_file_truncation(self):
        """Test source file path truncation at 60 chars."""
        long_path = "/very/long/path/to/some/deeply/nested/directory/structure/file.txt"
        result = ReportFormatters.format_with_provenance(
            "value",
            "file-extracted",
            source_file=long_path,
        )
        # Should truncate to .../filename
        assert ".../file.txt" in result

    def test_source_description_overrides_source_file(self):
        """Test source_description takes precedence over source_file."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "file-extracted",
            source_file="/path/to/file.txt",
            source_description="Custom description",
        )
        # source_description should appear, not source_file
        assert "Custom description" in result
        assert "from:" not in result

    def test_html_formatting(self):
        """Test HTML tags are properly formatted."""
        result = ReportFormatters.format_with_provenance(
            "Test Value",
            "ai-parsed",
            confidence=90.0,
            source_description="Test source",
        )
        # Check HTML structure
        assert "<b>" in result and "</b>" in result
        assert 'font size="7"' in result
        assert 'color="#666666"' in result

    def test_details_separator(self):
        """Test multiple details separated by pipe."""
        result = ReportFormatters.format_with_provenance(
            "value",
            "ai-parsed",
            confidence=85.0,
            source_description="Source info",
        )
        # Should have "AI PARSED | confidence: 85% | Source info"
        assert "|" in result
        assert "AI PARSED" in result
        assert "confidence: 85%" in result
        assert "Source info" in result
