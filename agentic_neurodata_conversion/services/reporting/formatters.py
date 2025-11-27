"""Shared formatting utilities for reports.

Provides consistent formatting across all report types (PDF, HTML, JSON, Text).
"""

import re


class ReportFormatters:
    """Shared formatting utilities for NWB reports."""

    # Species common names for scientific quality
    SPECIES_COMMON_NAMES = {
        "Mus musculus": "House mouse",
        "Rattus norvegicus": "Norway rat",
        "Homo sapiens": "Human",
        "Macaca mulatta": "Rhesus macaque",
        "Danio rerio": "Zebrafish",
        "Drosophila melanogaster": "Fruit fly",
        "Caenorhabditis elegans": "Roundworm",
    }

    # Sex code expansion
    SEX_CODES = {
        "M": "Male",
        "F": "Female",
        "U": "Unknown",
        "O": "Other",
    }

    @staticmethod
    def format_species(species: str) -> str:
        """Format species with common name if known.

        Args:
            species: Scientific species name

        Returns:
            Formatted species string with common name if available
        """
        if species == "N/A" or not species:
            return "N/A"

        common_name = ReportFormatters.SPECIES_COMMON_NAMES.get(species)
        if common_name:
            return f"{species} ({common_name})"
        return species

    @staticmethod
    def format_sex(sex_code: str) -> str:
        """Expand sex code to full word.

        Args:
            sex_code: Single character sex code (M/F/U/O)

        Returns:
            Full word for sex
        """
        if not sex_code or sex_code == "N/A":
            return "N/A"
        return ReportFormatters.SEX_CODES.get(sex_code.upper(), sex_code)

    @staticmethod
    def format_age(iso_age: str) -> str:
        """Convert ISO 8601 duration to human-readable format.

        Args:
            iso_age: ISO 8601 duration (e.g., P90D for 90 days)

        Returns:
            Human-readable age string

        Examples:
            >>> ReportFormatters.format_age("P90D")
            'P90D (90 days)'
            >>> ReportFormatters.format_age("P8W")
            'P8W (8 weeks)'
        """
        if not iso_age or iso_age == "N/A":
            return "N/A"

        # Match P90D, P3M, P2Y formats
        match = re.match(r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?", iso_age)
        if match:
            years, months, weeks, days = match.groups()
            parts = []
            if years:
                parts.append(f"{years} year{'s' if int(years) != 1 else ''}")
            if months:
                parts.append(f"{months} month{'s' if int(months) != 1 else ''}")
            if weeks:
                parts.append(f"{weeks} week{'s' if int(weeks) != 1 else ''}")
            if days:
                parts.append(f"{days} day{'s' if int(days) != 1 else ''}")

            if parts:
                readable = ", ".join(parts)
                return f"{iso_age} ({readable})"
        return iso_age

    @staticmethod
    def format_filesize(size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: File size in bytes

        Returns:
            Human-readable file size (KB, MB, GB)

        Examples:
            >>> ReportFormatters.format_filesize(1024)
            '1.0 KB'
            >>> ReportFormatters.format_filesize(1048576)
            '1.0 MB'
        """
        if size_bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    @staticmethod
    def format_with_provenance(
        value: str,
        provenance: str,
        source_file: str | None = None,
        confidence: float | None = None,
        source_description: str | None = None,
    ) -> str:
        """Format a value with its provenance badge for display in reports.

        Args:
            value: The field value
            provenance: Provenance type (user-specified, ai-parsed, etc.)
            source_file: Source file path for file-extracted provenance
            confidence: Confidence score (0-100) for AI operations
            source_description: Description of where the value came from

        Returns:
            Formatted string with provenance badge and details
        """
        # Complete 6-tag provenance system with emoji badges
        provenance_badges = {
            "user-specified": "👤",  # User directly provided
            "file-extracted": "📄",  # From source file
            "ai-parsed": "🧠",  # AI parsed from unstructured text
            "ai-inferred": "🤖",  # AI inferred from context
            "schema-default": "📋",  # NWB schema default
            "system-default": "⚪",  # System fallback
            # Legacy mappings for backwards compatibility
            "user-provided": "👤",
            "default": "⚪",
        }

        badge = provenance_badges.get(provenance, "")
        if badge:
            result = f"{value} <b>{badge}</b>"

            # Build detailed provenance info
            details = []

            # Add provenance label
            provenance_labels = {
                "user-specified": "USER SPECIFIED",
                "file-extracted": "FILE EXTRACTED",
                "ai-parsed": "AI PARSED",
                "ai-inferred": "AI INFERRED",
                "schema-default": "SCHEMA DEFAULT",
                "system-default": "SYSTEM DEFAULT",
                "user-provided": "USER SPECIFIED",
                "default": "SYSTEM DEFAULT",
            }
            prov_label = provenance_labels.get(provenance, provenance.upper())
            details.append(prov_label)

            # Add confidence for AI operations
            if confidence is not None and provenance in ["ai-parsed", "ai-inferred"]:
                details.append(f"confidence: {confidence:.0f}%")

            # Add source description
            if source_description:
                # Truncate long source descriptions
                if len(source_description) > 50:
                    source_description = source_description[:47] + "..."
                details.append(source_description)

            # Add source file for file-extracted provenance
            elif provenance == "file-extracted" and source_file:
                # Truncate very long paths
                if len(source_file) > 60:
                    import os

                    source_file = f".../{os.path.basename(source_file)}"
                details.append(f"from: {source_file}")

            # Format details with smaller gray font
            if details:
                details_str = " | ".join(details)
                result += f' <font size="7" color="#666666">({details_str})</font>'

            return result
        return value
