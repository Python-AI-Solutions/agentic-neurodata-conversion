"""
Generate toy SpikeGLX dataset for integration testing.

This script creates minimal but valid SpikeGLX files (.bin + .meta) for testing
format detection and conversion workflows without requiring real neural data.
"""

from pathlib import Path

import numpy as np


def generate_synthetic_neural_data(
    n_channels: int,
    n_samples: int,
    sample_rate: float,
    add_spikes: bool = True,
) -> np.ndarray:
    """
    Generate synthetic neural data with realistic characteristics.

    Args:
        n_channels: Number of recording channels
        n_samples: Number of time samples
        sample_rate: Sampling rate in Hz
        add_spikes: Whether to add synthetic spike waveforms

    Returns:
        Neural data array (channels × samples) as int16
    """
    # Generate baseline noise
    data = np.random.randn(n_channels, n_samples) * 10  # Low amplitude noise

    # Add low-frequency oscillations (8-12 Hz alpha band)
    time = np.arange(n_samples) / sample_rate
    for ch in range(n_channels):
        freq = 8 + np.random.rand() * 4  # Random freq in alpha range
        data[ch, :] += 20 * np.sin(2 * np.pi * freq * time)

    # Add synthetic spikes if requested
    if add_spikes:
        spike_rate = 5  # spikes per second per channel
        spike_duration = int(0.002 * sample_rate)  # 2ms spike

        for ch in range(n_channels):
            n_spikes = int(spike_rate * (n_samples / sample_rate))
            spike_times = np.random.choice(n_samples - spike_duration, size=n_spikes, replace=False)

            for spike_time in spike_times:
                # Simple spike waveform (negative then positive deflection)
                spike_waveform = np.zeros(spike_duration)
                half = spike_duration // 2
                spike_waveform[:half] = -np.exp(-np.linspace(0, 3, half)) * 100
                spike_waveform[half:] = np.exp(-np.linspace(0, 3, spike_duration - half)) * 50

                # Add to data
                end = spike_time + spike_duration
                data[ch, spike_time:end] += spike_waveform

    # Convert to int16 (SpikeGLX native format)
    data = np.clip(data, -32768, 32767).astype(np.int16)

    return data


def generate_spikeglx_meta(
    filename: str,
    sample_rate: float,
    n_channels: int,
    duration_sec: float,
    band_type: str,
) -> str:
    """
    Generate SpikeGLX .meta file content with all required fields for NeuroConv.

    Args:
        filename: Base filename
        sample_rate: Sampling rate in Hz
        n_channels: Number of channels
        duration_sec: Recording duration in seconds
        band_type: 'ap', 'lf', or 'nidq'

    Returns:
        Meta file content as string
    """
    # Generate channel mapping in Neo-compatible format
    # Format: (channelID;originalID:order) for each channel
    chan_map_entries = [f"(AP{i};{i}:{i})" for i in range(n_channels)]
    chan_map = f"({n_channels},{n_channels})" + "".join(chan_map_entries)

    # Generate IMRO table (simplified for Neuropixels 1.0)
    # Format: (channel bank refid apgain lfgain aphipass) - space separated
    imro_entries = [f"({i} 0 0 500 250 1)" for i in range(n_channels)]
    imro_table = f"({n_channels})" + "".join(imro_entries)

    # All required fields for NeuroConv's SpikeGLX interface
    meta_content = f"""appVersion=20190520
fileName={filename}
fileCreateTime=2025-01-08T12:00:00
fileSizeBytes={n_channels * int(duration_sec * sample_rate) * 2}
fileTimeSecs={duration_sec}
firstSample=0
gateMode=Immediate
imAiRangeMax=0.6
imAiRangeMin=-0.6
imDatApi=OpenEphys
imDatBs_fw=1
imDatBsc_pn=0,0,0,1,0,0
imDatBsc_type=0,0,0,0,0,0
imDatHs_fw=0.0.0.0
imDatLf_fw=0.0.0.0
imDatPrb_port=1
imDatPrb_slot=2
imDatPrb_type=0
imMaxInt=512
imRoFile=
imSampRate={sample_rate}
imTrigEnable=0
imTrgRising=T
imTrgSource=0
nSavedChans={n_channels}
niAiRangeMax=10
niAiRangeMin=-10
niDev1ProductName=PXI-6133
niMAGain=1
niMNChans1={n_channels}
niMNGain1=1
niMNGain=1
niSampRate=25000
snsApLfSy=384,384,1
snsGeomMap=
snsMnMaXaDw=384,384,1,0
snsShankMap=
snsSaveChanSubset=all
syncSourceIdx=0
syncSourcePeriod=1
~imroTbl={imro_table}
~snsChanMap={chan_map}
""".strip()

    return meta_content


def generate_toy_spikeglx_dataset(output_dir: Path):
    """
    Generate complete toy SpikeGLX dataset.

    Creates:
    - toy_recording_g0_t0.imec0.ap.bin (Action Potential band)
    - toy_recording_g0_t0.imec0.ap.meta
    - toy_recording_g0_t0.imec0.lf.bin (Local Field Potential band)
    - toy_recording_g0_t0.imec0.lf.meta
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configuration
    base_name = "toy_recording_g0_t0.imec0"
    n_channels = 16  # Reduced from real 384 for faster testing
    duration_sec = 10  # 10 second recording

    # AP band parameters
    ap_sample_rate = 30000  # 30 kHz
    ap_n_samples = int(duration_sec * ap_sample_rate)

    # LF band parameters
    lf_sample_rate = 2500  # 2.5 kHz
    lf_n_samples = int(duration_sec * lf_sample_rate)

    print(f"Generating toy SpikeGLX dataset in: {output_dir}")
    print(f"  Channels: {n_channels}")
    print(f"  Duration: {duration_sec} seconds")

    # Generate AP band data
    print(f"  Generating AP band ({ap_sample_rate} Hz)...")
    ap_data = generate_synthetic_neural_data(n_channels, ap_n_samples, ap_sample_rate, add_spikes=True)

    # Save AP binary file (channels interleaved)
    ap_bin_path = output_dir / f"{base_name}.ap.bin"
    ap_data.T.tofile(ap_bin_path)  # Transpose for sample-major order
    print(f"    Created: {ap_bin_path} ({ap_bin_path.stat().st_size / 1024 / 1024:.2f} MB)")

    # Save AP meta file
    ap_meta_path = output_dir / f"{base_name}.ap.meta"
    ap_meta_content = generate_spikeglx_meta(
        f"{base_name}.ap.bin",
        ap_sample_rate,
        n_channels,
        duration_sec,
        "ap",
    )
    ap_meta_path.write_text(ap_meta_content)
    print(f"    Created: {ap_meta_path}")

    # Generate LF band data
    print(f"  Generating LF band ({lf_sample_rate} Hz)...")
    lf_data = generate_synthetic_neural_data(n_channels, lf_n_samples, lf_sample_rate, add_spikes=False)

    # Save LF binary file
    lf_bin_path = output_dir / f"{base_name}.lf.bin"
    lf_data.T.tofile(lf_bin_path)
    print(f"    Created: {lf_bin_path} ({lf_bin_path.stat().st_size / 1024 / 1024:.2f} MB)")

    # Save LF meta file
    lf_meta_path = output_dir / f"{base_name}.lf.meta"
    lf_meta_content = generate_spikeglx_meta(
        f"{base_name}.lf.bin",
        lf_sample_rate,
        n_channels,
        duration_sec,
        "lf",
    )
    lf_meta_path.write_text(lf_meta_content)
    print(f"    Created: {lf_meta_path}")

    print("\n✓ Toy SpikeGLX dataset generated successfully!")
    print(f"  Total size: {sum(f.stat().st_size for f in output_dir.glob('*')) / 1024 / 1024:.2f} MB")
    print("\nFiles created:")
    for file in sorted(output_dir.glob("*")):
        print(f"  - {file.name}")


def generate_toy_neuropixels_dataset(output_dir: Path):
    """
    Generate toy Neuropixels dataset.

    Neuropixels uses SpikeGLX for acquisition, so this creates:
    - imec probe files (.ap.bin/.meta)
    - NIDQ (National Instruments DAQ) sync files (.nidq.bin/.meta)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configuration
    base_name = "neuropixels_recording_g0_t0"
    n_channels_imec = 16  # Reduced from real 384
    n_channels_nidq = 4  # Analog/digital sync channels
    duration_sec = 10

    print(f"Generating toy Neuropixels dataset in: {output_dir}")
    print(f"  IMEC channels: {n_channels_imec}")
    print(f"  NIDQ channels: {n_channels_nidq}")
    print(f"  Duration: {duration_sec} seconds")

    # Generate IMEC probe data (AP band)
    ap_sample_rate = 30000
    ap_n_samples = int(duration_sec * ap_sample_rate)
    print(f"  Generating IMEC probe data ({ap_sample_rate} Hz)...")

    imec_data = generate_synthetic_neural_data(n_channels_imec, ap_n_samples, ap_sample_rate, add_spikes=True)

    # Save IMEC binary file
    imec_bin_path = output_dir / f"{base_name}.imec0.ap.bin"
    imec_data.T.tofile(imec_bin_path)
    print(f"    Created: {imec_bin_path} ({imec_bin_path.stat().st_size / 1024 / 1024:.2f} MB)")

    # Save IMEC meta file
    imec_meta_path = output_dir / f"{base_name}.imec0.ap.meta"
    imec_meta_content = generate_spikeglx_meta(
        f"{base_name}.imec0.ap.bin",
        ap_sample_rate,
        n_channels_imec,
        duration_sec,
        "ap",
    )
    imec_meta_path.write_text(imec_meta_content)
    print(f"    Created: {imec_meta_path}")

    # Generate NIDQ (sync) data
    nidq_sample_rate = 25000
    nidq_n_samples = int(duration_sec * nidq_sample_rate)
    print(f"  Generating NIDQ sync data ({nidq_sample_rate} Hz)...")

    nidq_data = generate_synthetic_neural_data(n_channels_nidq, nidq_n_samples, nidq_sample_rate, add_spikes=False)

    # Save NIDQ binary file
    nidq_bin_path = output_dir / f"{base_name}.nidq.bin"
    nidq_data.T.tofile(nidq_bin_path)
    print(f"    Created: {nidq_bin_path} ({nidq_bin_path.stat().st_size / 1024 / 1024:.2f} MB)")

    # Save NIDQ meta file
    nidq_meta_path = output_dir / f"{base_name}.nidq.meta"
    nidq_meta_content = generate_spikeglx_meta(
        f"{base_name}.nidq.bin",
        nidq_sample_rate,
        n_channels_nidq,
        duration_sec,
        "nidq",
    )
    nidq_meta_path.write_text(nidq_meta_content)
    print(f"    Created: {nidq_meta_path}")

    print("\n✓ Toy Neuropixels dataset generated successfully!")
    print(f"  Total size: {sum(f.stat().st_size for f in output_dir.glob('*')) / 1024 / 1024:.2f} MB")
    print("\nFiles created:")
    for file in sorted(output_dir.glob("*")):
        print(f"  - {file.name}")


if __name__ == "__main__":
    # Output directories
    fixtures_parent = Path(__file__).parent
    spikeglx_dir = fixtures_parent / "toy_spikeglx"
    neuropixels_dir = Path(__file__).parent.parent.parent / "test_data" / "neuropixels"

    # Generate SpikeGLX dataset
    print("=" * 60)
    print("Generating SpikeGLX fixtures...")
    print("=" * 60)
    generate_toy_spikeglx_dataset(spikeglx_dir)

    print("\n" + "=" * 60)
    print("Generating Neuropixels fixtures...")
    print("=" * 60)
    generate_toy_neuropixels_dataset(neuropixels_dir)
