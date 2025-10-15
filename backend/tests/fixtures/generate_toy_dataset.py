"""
Generate a toy SpikeGLX dataset for testing.

This script creates a minimal but valid SpikeGLX dataset with:
- .ap.bin file (neural data) - ~3MB
- .ap.meta file (metadata)
- .lf.bin file (LFP data) - ~1MB
- .lf.meta file (metadata)

Total size: ~5MB
"""
import struct
from pathlib import Path
from typing import Dict

import numpy as np


def generate_spikeglx_meta(
    sample_rate: float,
    num_channels: int,
    file_type: str,
    duration_seconds: float,
) -> str:
    """
    Generate SpikeGLX metadata file content.

    Args:
        sample_rate: Sampling rate in Hz
        num_channels: Number of channels
        file_type: Either 'ap' (action potential) or 'lf' (local field potential)
        duration_seconds: Duration of recording

    Returns:
        Metadata file content as string
    """
    num_samples = int(sample_rate * duration_seconds)

    # Generate imroTbl - each channel with default settings
    # Format: (type,num_channels)(ch bank ref APgain LFgain APfilt)...
    imro_entries = "".join([f"({i} 0 0 500 250 1)" for i in range(num_channels)])
    imro_tbl = f"(0,{num_channels}){imro_entries}"

    # Generate snsChanMap - channel mapping with labels
    # Format: (num_channels,num_channels,1)(label;acq:usr)...
    # For simplicity, acq and usr order are the same
    chan_map_entries = "".join([f"(AP{i};{i}:{i})" for i in range(num_channels)])
    sns_chan_map = f"({num_channels},{num_channels},1){chan_map_entries}"

    # For snsSaveChanSubset, list all saved channels (0-indexed)
    # Format: 0,1,2,3...  or use "all" for all channels
    save_chan_subset = ",".join(str(i) for i in range(num_channels))

    meta = f"""~snsShankMap=0:0:1:1
~snsGeomMap=(0,0)
~snsChanMap={sns_chan_map}
~snsSaveChanSubset={save_chan_subset}
~imroTbl={imro_tbl}
acqApLfSy=384,384,1
fileCreateTime=2025-10-15T10:00:00
fileName=toy_recording_g0_t0.imec0.{file_type}.bin
fileTimeSecs={duration_seconds}
firstSample=0
imAiRangeMax=0.6
imAiRangeMin=-0.6
imDatApi=2.0
imDatPrb_type=1022
imDatPrb_pn=NP1022
imMaxInt=512
imSampRate={sample_rate}
nSavedChans={num_channels}
niSampRate={sample_rate}
snsApLfSy=384,384,1
typeEnabled=1
typeThis={file_type}
"""
    return meta


def generate_binary_data(
    num_channels: int,
    num_samples: int,
    sample_rate: float,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate synthetic neural/LFP data.

    Args:
        num_channels: Number of channels
        num_samples: Number of time samples
        sample_rate: Sampling rate in Hz
        seed: Random seed for reproducibility

    Returns:
        2D array of shape (num_samples, num_channels) with int16 values
    """
    np.random.seed(seed)

    # Generate baseline noise
    data = np.random.randn(num_samples, num_channels).astype(np.float32)

    # Add some synthetic spikes (20% of channels have spikes)
    num_spike_channels = max(1, num_channels // 5)
    spike_channels = np.random.choice(num_channels, num_spike_channels, replace=False)

    # Add spikes at random times
    num_spikes_per_channel = 20
    spike_width_samples = int(0.002 * sample_rate)  # 2ms spike width

    for ch in spike_channels:
        spike_times = np.random.randint(
            spike_width_samples,
            num_samples - spike_width_samples,
            num_spikes_per_channel,
        )
        for spike_time in spike_times:
            # Simple Gaussian spike shape
            spike_samples = np.arange(
                spike_time - spike_width_samples,
                spike_time + spike_width_samples,
            )
            spike_shape = np.exp(
                -((spike_samples - spike_time) ** 2) / (2 * (spike_width_samples / 4) ** 2)
            )
            data[spike_samples, ch] += spike_shape * 5.0  # Spike amplitude

    # Add some low-frequency oscillations (simulate LFP)
    time = np.arange(num_samples) / sample_rate
    for ch in range(num_channels):
        # 8-12 Hz oscillation (alpha band)
        freq = 8 + 4 * np.random.rand()
        phase = 2 * np.pi * np.random.rand()
        data[:, ch] += 0.5 * np.sin(2 * np.pi * freq * time + phase)

    # Scale to int16 range (-32768 to 32767)
    # Use 50% of the dynamic range to avoid clipping
    data = data / np.abs(data).max() * 16384

    return data.astype(np.int16)


def write_binary_file(filepath: Path, data: np.ndarray) -> None:
    """
    Write data to binary file in SpikeGLX format.

    SpikeGLX format: interleaved int16 samples, channels x samples

    Args:
        filepath: Output file path
        data: 2D array of shape (num_samples, num_channels)
    """
    with open(filepath, "wb") as f:
        # Write data row by row (sample by sample)
        for sample in data:
            # Pack as little-endian int16
            packed = struct.pack(f"<{len(sample)}h", *sample)
            f.write(packed)


def generate_toy_spikeglx_dataset(
    output_dir: Path,
    ap_sample_rate: float = 30000.0,  # 30 kHz for AP band
    lf_sample_rate: float = 2500.0,   # 2.5 kHz for LF band
    num_channels: int = 16,            # Reduced from 384 for toy dataset
    duration_seconds: float = 10.0,   # 10 seconds
) -> Dict[str, Path]:
    """
    Generate a complete toy SpikeGLX dataset.

    Args:
        output_dir: Directory to write files
        ap_sample_rate: Action potential band sampling rate (Hz)
        lf_sample_rate: Local field potential sampling rate (Hz)
        num_channels: Number of channels
        duration_seconds: Duration of recording (seconds)

    Returns:
        Dictionary mapping file types to created file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = {}

    # Generate AP band files
    # Use proper SpikeGLX naming convention: name_g0_t0.imec0.ap.bin
    print(f"Generating AP band data ({ap_sample_rate} Hz, {duration_seconds}s)...")
    ap_num_samples = int(ap_sample_rate * duration_seconds)
    ap_data = generate_binary_data(num_channels, ap_num_samples, ap_sample_rate, seed=42)

    ap_bin_path = output_dir / "toy_recording_g0_t0.imec0.ap.bin"
    write_binary_file(ap_bin_path, ap_data)
    created_files["ap_bin"] = ap_bin_path
    print(f"  Created: {ap_bin_path} ({ap_bin_path.stat().st_size / 1024 / 1024:.2f} MB)")

    ap_meta_path = output_dir / "toy_recording_g0_t0.imec0.ap.meta"
    ap_meta_content = generate_spikeglx_meta(
        ap_sample_rate, num_channels, "ap", duration_seconds
    )
    ap_meta_path.write_text(ap_meta_content)
    created_files["ap_meta"] = ap_meta_path
    print(f"  Created: {ap_meta_path}")

    # Generate LF band files
    print(f"Generating LF band data ({lf_sample_rate} Hz, {duration_seconds}s)...")
    lf_num_samples = int(lf_sample_rate * duration_seconds)
    lf_data = generate_binary_data(num_channels, lf_num_samples, lf_sample_rate, seed=43)

    lf_bin_path = output_dir / "toy_recording_g0_t0.imec0.lf.bin"
    write_binary_file(lf_bin_path, lf_data)
    created_files["lf_bin"] = lf_bin_path
    print(f"  Created: {lf_bin_path} ({lf_bin_path.stat().st_size / 1024 / 1024:.2f} MB)")

    lf_meta_path = output_dir / "toy_recording_g0_t0.imec0.lf.meta"
    lf_meta_content = generate_spikeglx_meta(
        lf_sample_rate, num_channels, "lf", duration_seconds
    )
    lf_meta_path.write_text(lf_meta_content)
    created_files["lf_meta"] = lf_meta_path
    print(f"  Created: {lf_meta_path}")

    total_size = sum(p.stat().st_size for p in created_files.values())
    print(f"\nTotal dataset size: {total_size / 1024 / 1024:.2f} MB")

    return created_files


def main():
    """Main entry point."""
    # Default output directory
    script_dir = Path(__file__).parent
    output_dir = script_dir / "toy_spikeglx"

    print("=" * 60)
    print("Toy SpikeGLX Dataset Generator")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print()

    created_files = generate_toy_spikeglx_dataset(output_dir)

    print()
    print("=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)
    print("\nCreated files:")
    for file_type, filepath in created_files.items():
        print(f"  {file_type}: {filepath.name}")
    print()


if __name__ == "__main__":
    main()
