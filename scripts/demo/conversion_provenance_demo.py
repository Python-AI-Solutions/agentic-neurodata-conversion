#!/usr/bin/env python3
"""
Demonstration of conversion provenance tracking functionality.

This script shows how to use the ConversionProvenanceTracker to maintain
complete audit trails for neurodata conversions.
"""

import json
from pathlib import Path
import tempfile

from agentic_neurodata_conversion.data_management import (
    ConversionProvenanceTracker,
    ProvenanceSource,
)


def main():
    """Demonstrate conversion provenance tracking."""
    print("🔬 Conversion Provenance Tracking Demo")
    print("=" * 50)

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 Working directory: {temp_path}")

        # Initialize conversion provenance tracker
        print("\n1️⃣ Initializing conversion provenance tracker...")
        tracker = ConversionProvenanceTracker(
            conversion_id="demo_conversion_001",
            output_dir=str(temp_path / "conversions"),
            dataset_path="/demo/dataset/path",
        )

        print(f"   ✅ Created conversion repository: {tracker.conversion_repo_path}")
        print(f"   📊 Session ID: {tracker.session.session_id}")
        print(f"   ⏰ Started at: {tracker.session.start_time}")

        # Demonstrate recording different types of provenance
        print("\n2️⃣ Recording provenance entries...")

        # Auto-extracted metadata
        tracker.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="file_analyzer",
            operation="detect_file_format",
            input_data={"files": ["recording.dat", "events.csv", "metadata.json"]},
            output_data={
                "format": "custom_binary",
                "channels": 64,
                "sampling_rate": 30000,
            },
            confidence=0.95,
            metadata={"analysis_method": "file_signature_detection"},
        )
        print("   📄 Recorded auto-extracted file format detection")

        # User-provided metadata
        tracker.record_provenance(
            source=ProvenanceSource.USER_PROVIDED,
            agent="researcher",
            operation="provide_experimenter_info",
            input_data={"field": "experimenter"},
            output_data={"experimenter": "Dr. Jane Smith", "lab": "Neuroscience Lab"},
            confidence=1.0,
            metadata={"input_method": "web_form"},
        )
        print("   👤 Recorded user-provided experimenter information")

        # AI-generated content
        tracker.record_provenance(
            source=ProvenanceSource.AI_GENERATED,
            agent="conversation_agent",
            operation="generate_session_description",
            input_data={
                "context": "64-channel extracellular recording from mouse visual cortex"
            },
            output_data={
                "session_description": "Extracellular recording from mouse V1 during visual stimulation"
            },
            confidence=0.85,
            metadata={"model": "gpt-4", "temperature": 0.3},
        )
        print("   🤖 Recorded AI-generated session description")

        # External enrichment
        tracker.record_provenance(
            source=ProvenanceSource.EXTERNAL_ENRICHED,
            agent="knowledge_graph",
            operation="enrich_brain_region",
            input_data={"region": "V1"},
            output_data={
                "full_name": "Primary Visual Cortex",
                "ontology_id": "UBERON:0002436",
            },
            confidence=0.9,
            metadata={"source": "Allen Brain Atlas", "version": "2023.1"},
        )
        print("   🌐 Recorded external knowledge enrichment")

        # Update pipeline state
        print("\n3️⃣ Updating pipeline state...")
        tracker.update_pipeline_state(
            {
                "current_stage": "metadata_collection_complete",
                "files_processed": 3,
                "metadata_fields_populated": 8,
                "validation_status": "pending",
            }
        )
        print("   📈 Updated pipeline state with progress information")

        # Save conversion artifacts
        print("\n4️⃣ Saving conversion artifacts...")

        # Create demo conversion script
        conversion_script = '''
"""Auto-generated conversion script for demo_conversion_001."""

import numpy as np
from neuroconv import NWBConverter

def convert_session():
    """Convert demo session to NWB format."""
    print("Converting session with 64 channels...")

    # Simulated conversion logic
    metadata = {
        "experimenter": "Dr. Jane Smith",
        "lab": "Neuroscience Lab",
        "session_description": "Extracellular recording from mouse V1 during visual stimulation",
        "identifier": "demo_conversion_001"
    }

    print(f"Metadata: {metadata}")
    print("Conversion complete!")

if __name__ == "__main__":
    convert_session()
'''

        script_file = temp_path / "demo_conversion_script.py"
        script_file.write_text(conversion_script)

        tracker.save_conversion_artifact(
            artifact_path=str(script_file),
            artifact_type="conversion_script",
            description="Auto-generated conversion script for demo session",
            metadata={"generator": "demo_system", "version": "1.0"},
        )
        print("   💾 Saved conversion script")

        # Create demo metadata file
        final_metadata = {
            "identifier": "demo_conversion_001",
            "session_description": "Extracellular recording from mouse V1 during visual stimulation",
            "experimenter": "Dr. Jane Smith",
            "lab": "Neuroscience Lab",
            "institution": "Demo University",
            "session_start_time": "2024-01-15T14:30:00",
            "channels": 64,
            "sampling_rate": 30000,
            "brain_region": "Primary Visual Cortex",
        }

        metadata_file = temp_path / "final_metadata.json"
        metadata_file.write_text(json.dumps(final_metadata, indent=2))

        tracker.save_conversion_artifact(
            artifact_path=str(metadata_file),
            artifact_type="metadata_file",
            description="Final metadata for NWB conversion",
            metadata={"sources": ["user", "ai", "auto", "external"]},
        )
        print("   📋 Saved final metadata file")

        # Finalize conversion
        print("\n5️⃣ Finalizing conversion...")
        tracker.finalize_conversion("completed", final_metadata)
        print("   ✅ Conversion finalized successfully")

        # Display provenance summary
        print("\n6️⃣ Provenance Summary")
        print("-" * 30)

        summary = tracker.get_provenance_summary()

        print(f"Session ID: {summary['session_id']}")
        print(f"Status: {summary['status']}")
        print(f"Duration: {summary['duration']:.2f} seconds")
        print(f"Total Operations: {summary['total_operations']}")

        print("\nData Sources:")
        for source, count in summary["source_counts"].items():
            print(f"  • {source.replace('_', ' ').title()}: {count} operations")

        print("\nAgent Activity:")
        for agent, count in summary["agent_counts"].items():
            print(f"  • {agent}: {count} operations")

        confidence_stats = summary["confidence_stats"]
        if confidence_stats["count"] > 0:
            print("\nConfidence Statistics:")
            print(f"  • Average: {confidence_stats['average']:.2f}")
            print(
                f"  • Range: {confidence_stats['min']:.2f} - {confidence_stats['max']:.2f}"
            )
            print(f"  • Operations with confidence: {confidence_stats['count']}")

        # Show repository structure
        print("\n7️⃣ Repository Structure")
        print("-" * 30)
        print(f"Repository: {tracker.conversion_repo_path}")

        def show_tree(path, prefix="", max_depth=2, current_depth=0):
            if current_depth >= max_depth:
                return

            try:
                items = sorted(
                    [item for item in path.iterdir() if not item.name.startswith(".")],
                    key=lambda x: (x.is_file(), x.name),
                )
            except PermissionError:
                return

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "

                if item.is_file():
                    size = item.stat().st_size
                    size_str = f" ({size} bytes)"
                    print(f"{prefix}{current_prefix}{item.name}{size_str}")
                else:
                    print(f"{prefix}{current_prefix}{item.name}/")

                    if current_depth < max_depth - 1:
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        show_tree(item, next_prefix, max_depth, current_depth + 1)

        show_tree(tracker.conversion_repo_path)

        # Show key files
        print("\n8️⃣ Key Files Generated")
        print("-" * 30)

        key_files = [
            ("README.md", "Repository documentation"),
            ("CONVERSION_SUMMARY.md", "Human-readable conversion summary"),
            ("provenance/conversion_session.json", "Complete session data"),
            ("provenance/provenance_log.jsonl", "Detailed provenance log"),
            ("scripts/demo_conversion_script.py", "Generated conversion script"),
            ("inputs/final_metadata.json", "Final metadata for conversion"),
        ]

        for file_path, description in key_files:
            full_path = tracker.conversion_repo_path / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"  ✅ {file_path} ({size} bytes) - {description}")
            else:
                print(f"  ❌ {file_path} - {description}")

        print("\n🎉 Demo completed! Check the generated files at:")
        print(f"   {tracker.conversion_repo_path}")

        # Show a sample of the conversion summary
        summary_file = tracker.conversion_repo_path / "CONVERSION_SUMMARY.md"
        if summary_file.exists():
            print("\n📄 Sample from Conversion Summary:")
            print("-" * 40)
            lines = summary_file.read_text().split("\n")
            for line in lines[:15]:  # Show first 15 lines
                print(f"   {line}")
            if len(lines) > 15:
                print(f"   ... ({len(lines) - 15} more lines)")


if __name__ == "__main__":
    main()
