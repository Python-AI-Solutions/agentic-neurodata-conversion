"""
Factory for generating mock data files.

Provides programmatic generation of mock neuroscience data files
for testing without requiring real recordings.
"""
from pathlib import Path
from typing import Optional
import struct


class FileFactory:
    """Factory for generating mock data files."""

    @staticmethod
    def create_spikeglx_binary(
        output_path: Path,
        num_samples: int = 1000,
        num_channels: int = 384
    ) -> Path:
        """Create a mock SpikeGLX binary file.

        Args:
            output_path: Path where file should be created
            num_samples: Number of samples to generate
            num_channels: Number of channels

        Returns:
            Path to created file
        """
        # SpikeGLX files are binary with int16 samples
        # Format: samples are interleaved by channel
        data = bytearray()

        for sample in range(num_samples):
            for channel in range(num_channels):
                # Generate mock data (simple sawtooth wave)
                value = (sample + channel) % 32768
                data.extend(struct.pack('<h', value))  # Little-endian int16

        output_path.write_bytes(data)
        return output_path

    @staticmethod
    def create_spikeglx_meta(
        output_path: Path,
        num_channels: int = 384,
        sampling_rate: int = 30000
    ) -> Path:
        """Create a mock SpikeGLX .meta file.

        Args:
            output_path: Path where file should be created
            num_channels: Number of channels
            sampling_rate: Sampling rate in Hz

        Returns:
            Path to created file
        """
        meta_content = f"""~snsApLfSy=384,0,1
appVersion=3.0.0
fileTimeSecs=600
fileName=test_g0_t0.imec0.ap.bin
nSavedChans={num_channels}
sRateHz={sampling_rate}
snsSaveChanSubset=all
typeThis=imec
imDatPrb_type=0
imDatPrb_dock=0
imDatPrb_port=1
imDatPrb_slot=2
imRoFile=test_g0_t0.imec0.ap.imRoFile
"""
        output_path.write_text(meta_content)
        return output_path

    @staticmethod
    def create_nwb_file(
        output_path: Path,
        size_bytes: int = 1024
    ) -> Path:
        """Create a mock NWB file.

        Args:
            output_path: Path where file should be created
            size_bytes: Approximate size in bytes

        Returns:
            Path to created file
        """
        # NWB files are HDF5, but for testing we just create a placeholder
        # Real NWB validation would require pynwb, which is tested separately
        mock_nwb_header = b'\x89HDF\r\n\x1a\n'  # HDF5 magic number
        mock_data = b'x' * (size_bytes - len(mock_nwb_header))

        output_path.write_bytes(mock_nwb_header + mock_data)
        return output_path

    @staticmethod
    def create_axon_abf_file(output_path: Path) -> Path:
        """Create a mock Axon .abf file.

        Args:
            output_path: Path where file should be created

        Returns:
            Path to created file
        """
        # ABF files have specific header format
        # This is a minimal mock for testing detection
        abf_header = b'ABF2'  # ABF2 format identifier
        mock_data = b'\x00' * 1024

        output_path.write_bytes(abf_header + mock_data)
        return output_path

    @staticmethod
    def create_neuropixels_file(output_path: Path) -> Path:
        """Create a mock Neuropixels file.

        Args:
            output_path: Path where file should be created

        Returns:
            Path to created file
        """
        # Neuropixels uses SpikeGLX format
        # .nidq.bin extension is specific to Neuropixels NIDQ data
        return FileFactory.create_spikeglx_binary(output_path)

    @staticmethod
    def create_test_data_directory(
        base_path: Path,
        format_type: str = "spikeglx"
    ) -> Path:
        """Create a complete test data directory.

        Args:
            base_path: Base directory for test data
            format_type: Type of data to generate ("spikeglx", "neuropixels", "axon")

        Returns:
            Path to created directory
        """
        base_path.mkdir(parents=True, exist_ok=True)

        if format_type == "spikeglx":
            bin_file = base_path / "test_g0_t0.imec0.ap.bin"
            meta_file = base_path / "test_g0_t0.imec0.ap.meta"
            FileFactory.create_spikeglx_binary(bin_file)
            FileFactory.create_spikeglx_meta(meta_file)

        elif format_type == "neuropixels":
            nidq_file = base_path / "test_g0_t0.nidq.bin"
            meta_file = base_path / "test_g0_t0.nidq.meta"
            FileFactory.create_neuropixels_file(nidq_file)
            FileFactory.create_spikeglx_meta(meta_file)

        elif format_type == "axon":
            abf_file = base_path / "test_recording.abf"
            FileFactory.create_axon_abf_file(abf_file)

        return base_path

    @staticmethod
    def create_minimal_binary_file(
        output_path: Path,
        size_bytes: int = 100
    ) -> Path:
        """Create a minimal binary file for basic testing.

        Args:
            output_path: Path where file should be created
            size_bytes: Size in bytes

        Returns:
            Path to created file
        """
        output_path.write_bytes(b'test_data' * (size_bytes // 9))
        return output_path

    @staticmethod
    def create_corrupted_file(output_path: Path) -> Path:
        """Create a corrupted/invalid file for error testing.

        Args:
            output_path: Path where file should be created

        Returns:
            Path to created file
        """
        # Create file with invalid/corrupted data
        corrupted_data = b'\xff\xfe\xfd\xfc' * 256
        output_path.write_bytes(corrupted_data)
        return output_path

    @staticmethod
    def create_empty_file(output_path: Path) -> Path:
        """Create an empty file for edge case testing.

        Args:
            output_path: Path where file should be created

        Returns:
            Path to created file
        """
        output_path.touch()
        return output_path
