"""
Comprehensive validation of all test_data files.

This test suite validates all data in the test_data/ directory:
- NWB files (converted outputs)
- SpikeGLX data (raw and samples)
- OpenEphys fixtures
- Neuropixels data
"""

from pathlib import Path

import pytest

from backend.src.agents.conversion_agent import ConversionAgent


@pytest.mark.integration
class TestAllNWBFiles:
    """Validate all NWB files in test_data."""

    def test_noise4sam_nwb(self):
        """Validate Noise4Sam_test.nwb (SpikeGLX conversion output)."""
        nwb_file = Path("test_data/Noise4Sam_test.nwb")

        if not nwb_file.exists():
            pytest.skip("Noise4Sam_test.nwb not found")

        try:
            from pynwb import NWBHDF5IO
        except ImportError:
            pytest.skip("pynwb not available")

        with NWBHDF5IO(str(nwb_file), "r") as io:
            nwbfile = io.read()

            # Verify basic structure
            assert nwbfile is not None, "NWB file could not be read"
            assert nwbfile.identifier is not None, "Missing identifier"

            # Verify acquisition data
            assert len(nwbfile.acquisition) > 0, "Should have acquisition data"

            # Check for electrical series (SpikeGLX data)
            has_electrical_series = any("ElectricalSeries" in str(type(acq)) for acq in nwbfile.acquisition.values())
            assert has_electrical_series, "Should have ElectricalSeries data"

            # Get the electrical series
            for key, acq in nwbfile.acquisition.items():
                if "ElectricalSeries" in str(type(acq)):
                    # Verify data dimensions
                    assert hasattr(acq, "data"), "ElectricalSeries should have data"
                    data_shape = acq.data.shape
                    print(f"  {key}: {data_shape[0]} samples × {data_shape[1]} channels")
                    assert data_shape[0] > 0, "Should have time samples"
                    assert data_shape[1] > 0, "Should have channels"

    def test_bad_example_nwb(self):
        """Validate bad_example.nwb (validation test file)."""
        nwb_file = Path("test_data/bad_example.nwb")

        if not nwb_file.exists():
            pytest.skip("bad_example.nwb not found")

        try:
            from pynwb import NWBHDF5IO
        except ImportError:
            pytest.skip("pynwb not available")

        # This file might be intentionally incomplete for validation testing
        # Just verify it can be read
        with NWBHDF5IO(str(nwb_file), "r") as io:
            nwbfile = io.read()
            assert nwbfile is not None, "NWB file could not be read"
            print(f"  File type: {type(nwbfile).__name__}")
            print(f"  Has acquisition: {len(nwbfile.acquisition) > 0}")

    def test_icephys_nwb(self):
        """Validate sub-18118024_icephys.nwb (intracellular electrophysiology)."""
        nwb_file = Path("test_data/dh/sub-18118024_icephys.nwb")

        if not nwb_file.exists():
            pytest.skip("sub-18118024_icephys.nwb not found")

        try:
            from pynwb import NWBHDF5IO
        except ImportError:
            pytest.skip("pynwb not available")

        with NWBHDF5IO(str(nwb_file), "r") as io:
            nwbfile = io.read()

            # Verify basic structure
            assert nwbfile is not None, "NWB file could not be read"
            assert nwbfile.identifier is not None, "Missing identifier"

            # This is intracellular ephys data
            print(f"  Session: {nwbfile.session_description if hasattr(nwbfile, 'session_description') else 'N/A'}")
            print(f"  Institution: {nwbfile.institution if hasattr(nwbfile, 'institution') else 'N/A'}")

            # Check for icephys data
            if hasattr(nwbfile, "icephys_electrodes"):
                print(f"  Intracellular electrodes: {len(nwbfile.icephys_electrodes)}")


@pytest.mark.integration
class TestAllRawDataFormats:
    """Test format detection for all raw data in test_data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversionAgent(llm_service=None)

    def test_spikeglx_synthetic_detection(self):
        """Test detection of synthetic SpikeGLX data."""
        test_dir = Path("test_data/spikeglx")

        if not test_dir.exists():
            pytest.skip("test_data/spikeglx not found")

        # Check for required files
        ap_bin = test_dir / "Noise4Sam_g0_t0.imec0.ap.bin"
        ap_meta = test_dir / "Noise4Sam_g0_t0.imec0.ap.meta"
        lf_bin = test_dir / "Noise4Sam_g0_t0.imec0.lf.bin"
        lf_meta = test_dir / "Noise4Sam_g0_t0.imec0.lf.meta"

        assert ap_bin.exists(), "AP band binary file missing"
        assert ap_meta.exists(), "AP band meta file missing"
        assert lf_bin.exists(), "LF band binary file missing"
        assert lf_meta.exists(), "LF band meta file missing"

        # Verify format detection
        assert self.agent._is_spikeglx(test_dir), "Should detect as SpikeGLX"

        # Verify file sizes
        print(f"  AP band: {ap_bin.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"  LF band: {lf_bin.stat().st_size / 1024 / 1024:.1f} MB")

    def test_spikeglx_real_samples_detection(self):
        """Test detection of real SpikeGLX sample data."""
        test_dir = Path("test_data/spikeglx_samples")

        if not test_dir.exists():
            pytest.skip("test_data/spikeglx_samples not found")

        # Check for required files
        lf_bin = test_dir / "Noise4Sam_g0_t0.imec0.lf.bin"
        lf_meta = test_dir / "Noise4Sam_g0_t0.imec0.lf.meta"

        assert lf_bin.exists(), "LF band binary file missing"
        assert lf_meta.exists(), "LF band meta file missing"

        # Verify format detection
        assert self.agent._is_spikeglx(test_dir), "Should detect as SpikeGLX"

        # This is real hardware-recorded data
        print(f"  Real SpikeGLX sample: {lf_bin.stat().st_size / 1024 / 1024:.1f} MB")

        # Read meta file to verify it's real data
        meta_content = lf_meta.read_text()
        assert "appVersion" in meta_content, "Should have valid meta file"
        assert "imSampRate" in meta_content, "Should have sample rate"

    def test_neuropixels_detection(self):
        """Test detection of Neuropixels data."""
        test_dir = Path("test_data/neuropixels")

        if not test_dir.exists():
            pytest.skip("test_data/neuropixels not found")

        # Check for Neuropixels-specific files
        imec_bin = list(test_dir.glob("*.imec*.ap.bin"))
        nidq_bin = list(test_dir.glob("*.nidq.bin"))

        assert len(imec_bin) > 0, "Should have IMEC probe files"
        assert len(nidq_bin) > 0, "Should have NIDQ sync files"

        # Verify format detection
        assert self.agent._is_neuropixels(test_dir), "Should detect as Neuropixels"

        print(f"  IMEC files: {len(imec_bin)}")
        print(f"  NIDQ files: {len(nidq_bin)}")

    def test_openephys_new_format_detection(self):
        """Test detection of OpenEphys new format."""
        test_dir = Path("test_data/openephys/new_format")

        if not test_dir.exists():
            pytest.skip("test_data/openephys/new_format not found")

        # Check for structure.oebin
        oebin_file = test_dir / "structure.oebin"
        assert oebin_file.exists(), "structure.oebin file missing"

        # Verify format detection
        assert self.agent._is_openephys(test_dir), "Should detect as OpenEphys"

        # Verify JSON structure
        import json

        with open(oebin_file) as f:
            structure = json.load(f)

        assert "GUI version" in structure, "Should have GUI version"
        assert "continuous" in structure, "Should have continuous data info"
        print(f"  OpenEphys GUI version: {structure.get('GUI version')}")

    def test_openephys_old_format_detection(self):
        """Test detection of OpenEphys old format."""
        test_dir = Path("test_data/openephys/old_format")

        if not test_dir.exists():
            pytest.skip("test_data/openephys/old_format not found")

        # Check for settings.xml
        settings_file = test_dir / "settings.xml"
        assert settings_file.exists(), "settings.xml file missing"

        # Verify format detection
        assert self.agent._is_openephys(test_dir), "Should detect as OpenEphys"

        # Verify XML structure
        import xml.etree.ElementTree as ET

        tree = ET.parse(settings_file)
        root = tree.getroot()

        assert root.tag == "SETTINGS", "Should have SETTINGS root element"
        print("  OpenEphys old format detected")


@pytest.mark.integration
class TestDataIntegrity:
    """Verify integrity and consistency of test data."""

    def test_all_spikeglx_meta_files_parseable(self):
        """Ensure all .meta files can be parsed."""
        meta_files = list(Path("test_data").glob("**/*.meta"))

        if not meta_files:
            pytest.skip("No .meta files found")

        for meta_file in meta_files:
            content = meta_file.read_text()

            # Verify basic required fields
            assert "fileName" in content, f"{meta_file}: Missing fileName"
            assert "fileSizeBytes" in content, f"{meta_file}: Missing fileSizeBytes"

            print(f"  ✓ {meta_file.relative_to(Path('test_data'))}")

    def test_all_bin_files_have_meta(self):
        """Ensure all .bin files have corresponding .meta files."""
        bin_files = list(Path("test_data").glob("**/*.bin"))

        if not bin_files:
            pytest.skip("No .bin files found")

        for bin_file in bin_files:
            meta_file = bin_file.with_suffix(".meta")
            assert meta_file.exists(), f"{bin_file.name} missing corresponding .meta file"

            print(f"  ✓ {bin_file.relative_to(Path('test_data'))} ↔ {meta_file.name}")

    def test_nwb_files_size_reasonable(self):
        """Verify NWB files are within reasonable size ranges."""
        nwb_files = list(Path("test_data").glob("**/*.nwb"))

        if not nwb_files:
            pytest.skip("No NWB files found")

        for nwb_file in nwb_files:
            size_mb = nwb_file.stat().st_size / 1024 / 1024

            # NWB files should be > 0 and typically < 100MB for test data
            assert size_mb > 0, f"{nwb_file.name}: Empty file"

            # Very large files might indicate an issue
            if size_mb > 100:
                print(f"  ⚠ {nwb_file.name}: Large file ({size_mb:.1f} MB)")
            else:
                print(f"  ✓ {nwb_file.name}: {size_mb:.1f} MB")


# Summary marker
pytestmark = pytest.mark.integration
