"""
Unit tests for the format detector and metadata extractors.

Tests the FormatDetector functionality including format detection
and format-specific metadata extraction.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Import the actual components that should be implemented
try:
    from agentic_neurodata_conversion.interfaces.format_detector import FormatDetector
    COMPONENTS_AVAILABLE = True
except ImportError:
    # These should fail until implemented
    FormatDetector = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE, 
    reason="Format detector components not implemented yet"
)


class TestFormatDetector:
    """Test the FormatDetector functionality."""
    
    @pytest.fixture
    def format_detector(self):
        """Create a format detector instance."""
        return FormatDetector()
    
    @pytest.fixture
    def open_ephys_dataset(self):
        """Create a temporary Open Ephys dataset."""
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)
        
        # Create Open Ephys files
        (dataset_path / "100_CH1.continuous").write_text("continuous data")
        (dataset_path / "100_CH2.continuous").write_text("continuous data")
        (dataset_path / "all_channels.events").write_text("events data")
        (dataset_path / "Tetrode_1.spikes").write_text("spikes data")
        
        # Create settings.xml
        settings_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
    <PROCESSOR name="Sources/Rhythm FPGA" sampleRate="30000.0">
        <CHANNEL number="0" name="CH1" record="true"/>
        <CHANNEL number="1" name="CH2" record="true"/>
    </PROCESSOR>
</SETTINGS>'''
        (dataset_path / "settings.xml").write_text(settings_xml)
        
        yield str(dataset_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def spikeglx_dataset(self):
        """Create a temporary SpikeGLX dataset."""
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)
        
        # Create SpikeGLX files
        (dataset_path / "test_g0_t0.imec0.ap.bin").write_bytes(b"binary data")
        (dataset_path / "test_g0_t0.nidq.bin").write_bytes(b"nidq data")
        
        # Create meta file
        meta_content = """imSampRate=30000.0
nSavedChans=384
imProbeOpt=0
typeThis=imec
fileSizeBytes=1000000
~imroTbl=(0,384)
"""
        (dataset_path / "test_g0_t0.imec0.ap.meta").write_text(meta_content)
        
        yield str(dataset_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def neuralynx_dataset(self):
        """Create a temporary Neuralynx dataset."""
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)
        
        # Create Neuralynx files
        (dataset_path / "CSC1.ncs").write_bytes(b"neuralynx continuous data")
        (dataset_path / "Events.nev").write_bytes(b"neuralynx events")
        (dataset_path / "TT1.ntt").write_bytes(b"tetrode data")
        
        yield str(dataset_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.unit
    def test_format_detector_initialization(self, format_detector):
        """Test format detector initialization."""
        assert format_detector.supported_formats is not None
        assert 'open_ephys' in format_detector.supported_formats
        assert 'spikeglx' in format_detector.supported_formats
        assert 'neuralynx' in format_detector.supported_formats
        assert 'blackrock' in format_detector.supported_formats
        assert 'intan' in format_detector.supported_formats
    
    @pytest.mark.unit
    async def test_analyze_directory_open_ephys(self, format_detector, open_ephys_dataset):
        """Test directory analysis for Open Ephys format."""
        analysis = await format_detector.analyze_directory(open_ephys_dataset)
        
        assert 'formats' in analysis
        assert 'file_count' in analysis
        assert 'total_size' in analysis
        
        # Should detect Open Ephys format
        formats = analysis['formats']
        assert len(formats) > 0
        assert any(f['format'] == 'open_ephys' for f in formats)
        
        # Check file count
        assert analysis['file_count'] == 5  # 2 continuous + 1 events + 1 spikes + 1 settings
    
    @pytest.mark.unit
    async def test_analyze_directory_spikeglx(self, format_detector, spikeglx_dataset):
        """Test directory analysis for SpikeGLX format."""
        analysis = await format_detector.analyze_directory(spikeglx_dataset)
        
        # Should detect SpikeGLX format
        formats = analysis['formats']
        assert len(formats) > 0
        assert any(f['format'] == 'spikeglx' for f in formats)
    
    @pytest.mark.unit
    async def test_extract_open_ephys_metadata(self, format_detector, open_ephys_dataset):
        """Test Open Ephys metadata extraction."""
        metadata = await format_detector.extract_format_metadata(open_ephys_dataset, 'open_ephys')
        
        assert metadata['recording_system'] == 'Open Ephys'
        assert metadata['format'] == 'open_ephys'
        assert 'continuous_files' in metadata
        assert 'events_files' in metadata
        assert 'spikes_files' in metadata
        
        # Should extract from settings.xml
        assert 'sampling_rate' in metadata
        assert metadata['sampling_rate'] == 30000.0
        assert 'channel_count' in metadata
        assert metadata['channel_count'] == 2
    
    @pytest.mark.unit
    async def test_extract_spikeglx_metadata(self, format_detector, spikeglx_dataset):
        """Test SpikeGLX metadata extraction."""
        metadata = await format_detector.extract_format_metadata(spikeglx_dataset, 'spikeglx')
        
        assert metadata['recording_system'] == 'SpikeGLX'
        assert metadata['format'] == 'spikeglx'
        assert 'meta_files' in metadata
        assert 'bin_files' in metadata
        assert 'probe_types' in metadata
        
        # Should extract from meta file
        assert 'sampling_rate' in metadata
        assert metadata['sampling_rate'] == 30000.0
        assert 'channel_count' in metadata
        assert metadata['channel_count'] == 384
    
    @pytest.mark.unit
    async def test_extract_neuralynx_metadata(self, format_detector, neuralynx_dataset):
        """Test Neuralynx metadata extraction."""
        metadata = await format_detector.extract_format_metadata(neuralynx_dataset, 'neuralynx')
        
        assert metadata['recording_system'] == 'Neuralynx'
        assert metadata['format'] == 'neuralynx'
        assert 'ncs_files' in metadata
        assert 'nev_files' in metadata
        assert 'ntt_files' in metadata
        
        assert metadata['ncs_files'] == 1
        assert metadata['nev_files'] == 1
        assert metadata['ntt_files'] == 1
    
    @pytest.mark.unit
    async def test_extract_blackrock_metadata(self, format_detector):
        """Test Blackrock metadata extraction."""
        # Create temporary Blackrock dataset
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)
        
        try:
            # Create Blackrock files
            (dataset_path / "test.ns5").write_bytes(b"blackrock data")
            (dataset_path / "test.nev").write_bytes(b"blackrock events")
            
            metadata = await format_detector.extract_format_metadata(str(dataset_path), 'blackrock')
            
            assert metadata['recording_system'] == 'Blackrock'
            assert metadata['format'] == 'blackrock'
            assert 'ns_files' in metadata
            assert 'nev_files' in metadata
            
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.unit
    async def test_extract_intan_metadata(self, format_detector):
        """Test Intan metadata extraction."""
        # Create temporary Intan dataset
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)
        
        try:
            # Create Intan file with mock header
            intan_file = dataset_path / "test.rhd"
            with open(intan_file, 'wb') as f:
                # Write magic number for RHD2000
                f.write((0xC6912702).to_bytes(4, byteorder='little'))
                # Write version
                f.write(b'\x01\x02')  # Version 2.1
                # Write sampling rate at offset 8
                f.seek(8)
                f.write((30000).to_bytes(4, byteorder='little'))
            
            metadata = await format_detector.extract_format_metadata(str(dataset_path), 'intan')
            
            assert metadata['recording_system'] == 'Intan'
            assert metadata['format'] == 'intan'
            assert 'rhd_files' in metadata
            assert 'file_type' in metadata
            assert metadata['file_type'] == 'RHD2000'
            
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.unit
    async def test_extract_generic_metadata(self, format_detector):
        """Test generic metadata extraction for unknown formats."""
        # Create temporary dataset with unknown format
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)
        
        try:
            # Create files with unknown extensions
            (dataset_path / "data.unknown").write_text("unknown data")
            (dataset_path / "info.xyz").write_text("info file")
            
            metadata = await format_detector.extract_format_metadata(str(dataset_path), 'unknown')
            
            assert metadata['recording_system'] == 'Unknown'
            assert metadata['format'] == 'unknown'
            assert 'total_size_bytes' in metadata
            assert 'file_count' in metadata
            assert 'file_extensions' in metadata
            
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.unit
    def test_calculate_format_confidence(self, format_detector):
        """Test format confidence calculation."""
        format_info = {
            'extensions': ['.continuous', '.events'],
            'patterns': ['continuous', 'events']
        }
        
        extensions_found = {'.continuous', '.events', '.txt'}
        patterns_found = {'continuous', 'events', 'other'}
        
        confidence = format_detector._calculate_format_confidence(
            format_info, extensions_found, patterns_found
        )
        
        # Should have high confidence (all extensions + all patterns match)
        assert confidence == 1.0
    
    @pytest.mark.unit
    def test_calculate_format_confidence_partial(self, format_detector):
        """Test format confidence calculation with partial matches."""
        format_info = {
            'extensions': ['.continuous', '.events'],
            'patterns': ['continuous']
        }
        
        extensions_found = {'.continuous'}  # Only one extension matches
        patterns_found = {'continuous'}     # Pattern matches
        
        confidence = format_detector._calculate_format_confidence(
            format_info, extensions_found, patterns_found
        )
        
        # Should have partial confidence (0.6 * 0.5 + 0.4 * 1.0 = 0.7)
        assert confidence == 0.7
    
    @pytest.mark.unit
    async def test_parse_open_ephys_settings_error_handling(self, format_detector):
        """Test error handling in Open Ephys settings parsing."""
        # Create invalid XML file
        temp_dir = tempfile.mkdtemp()
        settings_file = Path(temp_dir) / "settings.xml"
        
        try:
            settings_file.write_text("invalid xml content")
            
            metadata = await format_detector._parse_open_ephys_settings(settings_file)
            
            # Should handle error gracefully
            assert 'settings_parse_error' in metadata
            
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.unit
    async def test_parse_spikeglx_meta_error_handling(self, format_detector):
        """Test error handling in SpikeGLX meta parsing."""
        # Create invalid meta file
        temp_dir = tempfile.mkdtemp()
        meta_file = Path(temp_dir) / "test.meta"
        
        try:
            # Create file that can't be read
            meta_file.write_bytes(b'\x00\x01\x02\x03')  # Binary content
            
            metadata = await format_detector._parse_spikeglx_meta(meta_file)
            
            # Should handle error gracefully and still return some metadata
            assert isinstance(metadata, dict)
            
        finally:
            shutil.rmtree(temp_dir)