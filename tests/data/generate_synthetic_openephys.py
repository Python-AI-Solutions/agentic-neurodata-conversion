"""
Generate synthetic OpenEphys dataset for testing.

Creates a minimal valid OpenEphys dataset with:
- settings.xml configuration file
- Two .continuous files (CH1, CH2) with 10 seconds of synthetic data
- README.md with metadata for LLM extraction testing

Total size: ~1MB for fast testing.

OpenEphys .continuous format:
- Header (1024 bytes)
- Data blocks (2070 bytes each):
  - Timestamp (8 bytes, int64)
  - N samples (2 bytes, uint16)
  - Recording number (2 bytes, uint16)
  - Sample data (N × 2 bytes, int16)
  - Markers (10 bytes)

Usage:
    python tests/data/generate_synthetic_openephys.py
"""

from pathlib import Path
import struct

import numpy as np


def generate_continuous_file(
    filepath: Path, duration_seconds: int = 10, sampling_rate: int = 30000
) -> None:
    """
    Generate synthetic .continuous file in OpenEphys format.

    Creates a binary file with synthetic sine wave data that follows the OpenEphys
    .continuous format specification. The data represents a 10 Hz sine wave sampled
    at 30 kHz.

    Args:
        filepath: Output path for .continuous file
        duration_seconds: Duration of recording in seconds (default: 10)
        sampling_rate: Sampling rate in Hz (default: 30000)
    """
    # Create header (1024 bytes)
    header = b"header\n"
    header += b"sampleRate = 30000.0\n"
    header += b"bufferSize = 1024\n"
    header += b"bitVolts = 0.195\n"
    # Pad to 1024 bytes
    header += b"\x00" * (1024 - len(header))

    # Generate synthetic data (sine wave)
    total_samples = duration_seconds * sampling_rate
    samples_per_block = 1024

    with open(filepath, "wb") as f:
        f.write(header)

        for block_idx in range(total_samples // samples_per_block):
            # Block structure
            timestamp = block_idx * samples_per_block
            n_samples = samples_per_block
            rec_num = 0

            # Generate sine wave samples (10 Hz signal)
            t = np.arange(samples_per_block) / sampling_rate
            t += block_idx * samples_per_block / sampling_rate
            samples = (np.sin(2 * np.pi * 10 * t) * 1000).astype(np.int16)

            # Write block
            f.write(struct.pack("<q", timestamp))  # 8 bytes, int64, little-endian
            f.write(struct.pack("<H", n_samples))  # 2 bytes, uint16
            f.write(struct.pack("<H", rec_num))  # 2 bytes, uint16
            f.write(samples.tobytes())  # n_samples * 2 bytes
            f.write(b"\x00" * 10)  # 10 bytes markers

    print(f"Generated {filepath.name}: {filepath.stat().st_size / 1024:.1f} KB")


def generate_settings_xml(filepath: Path) -> None:
    """
    Generate settings.xml file with OpenEphys configuration.

    Creates an XML configuration file that describes the recording setup
    including version, date, and channel configuration.

    Args:
        filepath: Output path for settings.xml
    """
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <INFO>
    <VERSION>0.4.4</VERSION>
    <DATE>15 Jan 2024 12:00:00</DATE>
  </INFO>
  <SIGNALCHAIN>
    <PROCESSOR name="Sources/Rhythm FPGA">
      <CHANNEL name="CH1" number="0">
        <SELECTIONSTATE param="1"/>
      </CHANNEL>
      <CHANNEL name="CH2" number="1">
        <SELECTIONSTATE param="1"/>
      </CHANNEL>
    </PROCESSOR>
    <PROCESSOR name="Record Node">
      <EDITOR>
        <NWB>
          <EXPERIMENT_DESCRIPTION value="Synthetic test recording"/>
          <SESSION_ID value="test-session-001"/>
        </NWB>
      </EDITOR>
    </PROCESSOR>
  </SIGNALCHAIN>
</SETTINGS>
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"Generated {filepath.name}: {filepath.stat().st_size / 1024:.1f} KB")


def generate_readme(filepath: Path) -> None:
    """
    Generate README.md with metadata for LLM extraction.

    Creates a markdown file with subject information, experimental details,
    and recording metadata that can be extracted by the LLM-based metadata
    extraction agent.

    Args:
        filepath: Output path for README.md
    """
    readme_content = """# Synthetic OpenEphys Dataset

This is a synthetic dataset generated for testing the agentic-neurodata-conversion pipeline.

## Subject Information

**Subject ID**: Test Mouse 001
**Species**: Mus musculus
**Age**: P56 (8 weeks)
**Sex**: Male
**Weight**: 25g

## Experiment Details

**Experiment**: Synthetic test recording for pipeline validation
**Session Date**: 2024-01-15
**Session Start Time**: 12:00:00
**Experimenter**: Test User
**Lab**: Computational Neuroscience Lab
**Institution**: Test University

## Recording Details

**Recording Device**: Open Ephys Acquisition Board
**Device Manufacturer**: Open Ephys
**Recording Location**: CA1 (Hippocampus)
**Number of Channels**: 2
**Sampling Rate**: 30000 Hz
**Duration**: 10 seconds
**Recording Type**: Extracellular electrophysiology

## Signal Information

**Signal Type**: Synthetic sine wave (10 Hz)
**Signal Amplitude**: ~1000 arbitrary units
**Purpose**: Test dataset for conversion pipeline validation

## Notes

This dataset contains synthetic data and should only be used for testing purposes.
The data represents a simple 10 Hz sine wave and does not contain real neural recordings.

## Session Description

Test session for validating the multi-agent NWB conversion pipeline. This synthetic
dataset allows testing of format detection, metadata extraction, conversion, and
validation without requiring large real datasets.
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"Generated {filepath.name}: {filepath.stat().st_size / 1024:.1f} KB")


def main() -> None:
    """
    Generate synthetic OpenEphys dataset.

    Creates output directory and generates all required files:
    - settings.xml
    - 100_CH1.continuous
    - 100_CH2.continuous
    - README.md
    """
    # Determine output directory relative to this script
    output_dir = Path(__file__).parent / "synthetic_openephys"
    output_dir.mkdir(exist_ok=True)

    print(f"Generating synthetic OpenEphys dataset in: {output_dir}")
    print("-" * 70)

    # Generate all files
    generate_settings_xml(output_dir / "settings.xml")
    generate_continuous_file(output_dir / "100_CH1.continuous")
    generate_continuous_file(output_dir / "100_CH2.continuous")
    generate_readme(output_dir / "README.md")

    print("-" * 70)

    # Calculate total size
    total_size = sum(f.stat().st_size for f in output_dir.iterdir())
    file_count = len(list(output_dir.iterdir()))

    print("\nDataset summary:")
    print(f"  Location: {output_dir}")
    print(
        f"  Total size: {total_size / 1024:.1f} KB ({total_size / (1024 * 1024):.2f} MB)"
    )
    print(f"  File count: {file_count}")
    print("\nDataset ready for testing!")


if __name__ == "__main__":
    main()
