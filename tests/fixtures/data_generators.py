"""
Test data generators and factories.

This module provides utilities for generating synthetic test data
for various neuroscience data formats and scenarios.
"""

import json
import random
import struct
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np


@dataclass
class DatasetSpec:
    """Specification for generating test datasets."""
    format_type: str
    file_count: int
    total_size_mb: float
    channels: int
    sampling_rate: float
    duration_seconds: float
    has_events: bool = True
    has_metadata: bool = True
    corruption_level: float = 0.0  # 0.0 = clean, 1.0 = heavily corrupted


class SyntheticDataGenerator:
    """Generates synthetic neuroscience data for testing."""
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        random.seed(seed)
    
    def generate_open_ephys_dataset(self, output_dir: Path, spec: DatasetSpec) -> Dict[str, Any]:
        """Generate synthetic Open Ephys dataset."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate continuous data
        continuous_dir = output_dir / "continuous"
        continuous_dir.mkdir(exist_ok=True)
        
        # Generate recording data
        samples = int(spec.sampling_rate * spec.duration_seconds)
        data = self.rng.randn(spec.channels, samples).astype(np.float32)
        
        # Add some corruption if specified
        if spec.corruption_level > 0:
            corruption_mask = self.rng.random((spec.channels, samples)) < spec.corruption_level
            data[corruption_mask] = np.nan
        
        # Save as binary file (simplified Open Ephys format)
        data_file = continuous_dir / "100_CH1.continuous"
        with open(data_file, "wb") as f:
            # Write header (simplified)
            header = {
                "format": "Open Ephys Data Format",
                "version": "0.4.0",
                "header_bytes": 1024,
                "description": "Synthetic test data",
                "date_created": datetime.now().isoformat(),
                "channel": 1,
                "channelType": "Continuous",
                "sampleRate": spec.sampling_rate,
                "blockLength": 1024,
                "bufferSize": 1024,
                "bitVolts": 0.195
            }
            
            # Write header as JSON padded to 1024 bytes
            header_json = json.dumps(header).encode('utf-8')
            header_padded = header_json + b'\x00' * (1024 - len(header_json))
            f.write(header_padded)
            
            # Write data
            for i in range(samples):
                # Timestamp (8 bytes)
                f.write(struct.pack('<Q', i))
                # Sample count (2 bytes)
                f.write(struct.pack('<H', 1))
                # Recording number (2 bytes)
                f.write(struct.pack('<H', 0))
                # Data (4 bytes per channel)
                for ch in range(spec.channels):
                    f.write(struct.pack('<f', data[ch, i]))
                # Marker (1 byte)
                f.write(struct.pack('<B', 0))
        
        # Generate events if specified
        files_created = [str(data_file)]
        
        if spec.has_events:
            events_file = output_dir / "events.txt"
            events = self._generate_events(spec.duration_seconds)
            
            with open(events_file, 'w') as f:
                f.write("timestamp,event_type,event_id,description\n")
                for event in events:
                    f.write(f"{event['timestamp']},{event['type']},{event['id']},{event['description']}\n")
            
            files_created.append(str(events_file))
        
        # Generate metadata if specified
        if spec.has_metadata:
            metadata_file = output_dir / "metadata.json"
            metadata = self._generate_metadata(spec)
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            files_created.append(str(metadata_file))
        
        return {
            "format": "open_ephys",
            "files": files_created,
            "channels": spec.channels,
            "sampling_rate": spec.sampling_rate,
            "duration": spec.duration_seconds,
            "samples": samples
        }
    
    def generate_spikeglx_dataset(self, output_dir: Path, spec: DatasetSpec) -> Dict[str, Any]:
        """Generate synthetic SpikeGLX dataset."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate binary data file
        samples = int(spec.sampling_rate * spec.duration_seconds)
        data = self.rng.randint(-32768, 32767, (samples, spec.channels), dtype=np.int16)
        
        # Add corruption if specified
        if spec.corruption_level > 0:
            corruption_indices = self.rng.random((samples, spec.channels)) < spec.corruption_level
            data[corruption_indices] = 0  # Set corrupted samples to zero
        
        bin_file = output_dir / "test_recording_g0_t0.imec0.ap.bin"
        data.tofile(bin_file)
        
        # Generate meta file
        meta_file = output_dir / "test_recording_g0_t0.imec0.ap.meta"
        meta_content = f"""typeThis=imec
typeImEnabled=1
typeImSampRate={spec.sampling_rate}
typeImMaxInt=512
typeImMinInt=-512
typeImAiRangeMax=0.6
typeImAiRangeMin=-0.6
imDatPrb_dock=0
imDatPrb_port=1
imDatPrb_slot=2
imMaxZ=3840
imDatPrb_type=0
imRoFile=
imRoSNAP=
imSampRate={spec.sampling_rate}
imAiRangeMax=0.6
imAiRangeMin=-0.6
imMaxInt=512
imMinInt=-512
nSavedChans={spec.channels}
snsApLfSy=384,0,1
snsShankMap=1:0:384:1
snsSaveChanSubset=0:383
acqApLfSy=384,0,1
gateMode=Immediate
trigMode=Immediate
userNotes=Synthetic test data generated for testing
"""
        
        with open(meta_file, 'w') as f:
            f.write(meta_content)
        
        files_created = [str(bin_file), str(meta_file)]
        
        # Generate events if specified
        if spec.has_events:
            events_file = output_dir / "events.txt"
            events = self._generate_events(spec.duration_seconds)
            
            with open(events_file, 'w') as f:
                f.write("timestamp,event_type,event_id,description\n")
                for event in events:
                    f.write(f"{event['timestamp']},{event['type']},{event['id']},{event['description']}\n")
            
            files_created.append(str(events_file))
        
        return {
            "format": "spikeglx",
            "files": files_created,
            "channels": spec.channels,
            "sampling_rate": spec.sampling_rate,
            "duration": spec.duration_seconds,
            "samples": samples
        }
    
    def generate_generic_dataset(self, output_dir: Path, spec: DatasetSpec) -> Dict[str, Any]:
        """Generate generic test dataset."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate CSV data file
        samples = int(spec.sampling_rate * spec.duration_seconds)
        data = self.rng.randn(samples, spec.channels)
        
        data_file = output_dir / "recording_data.csv"
        
        # Create header
        header = ["timestamp"] + [f"channel_{i}" for i in range(spec.channels)]
        
        with open(data_file, 'w') as f:
            f.write(",".join(header) + "\n")
            
            for i in range(samples):
                timestamp = i / spec.sampling_rate
                row = [str(timestamp)] + [str(data[i, j]) for j in range(spec.channels)]
                
                # Add corruption if specified
                if spec.corruption_level > 0 and random.random() < spec.corruption_level:
                    # Corrupt some values
                    for j in range(1, len(row)):
                        if random.random() < 0.3:
                            row[j] = "NaN"
                
                f.write(",".join(row) + "\n")
        
        files_created = [str(data_file)]
        
        # Generate metadata
        if spec.has_metadata:
            metadata_file = output_dir / "metadata.json"
            metadata = self._generate_metadata(spec)
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            files_created.append(str(metadata_file))
        
        return {
            "format": "generic",
            "files": files_created,
            "channels": spec.channels,
            "sampling_rate": spec.sampling_rate,
            "duration": spec.duration_seconds,
            "samples": samples
        }
    
    def _generate_events(self, duration_seconds: float) -> List[Dict[str, Any]]:
        """Generate synthetic events."""
        num_events = random.randint(5, 20)
        events = []
        
        event_types = ["stimulus_onset", "stimulus_offset", "response", "trial_start", "trial_end"]
        
        for i in range(num_events):
            timestamp = random.uniform(0, duration_seconds)
            event_type = random.choice(event_types)
            
            events.append({
                "timestamp": round(timestamp, 3),
                "type": event_type,
                "id": i,
                "description": f"Synthetic {event_type} event {i}"
            })
        
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        return events
    
    def _generate_metadata(self, spec: DatasetSpec) -> Dict[str, Any]:
        """Generate synthetic metadata."""
        experimenters = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown"]
        labs = ["Neural Dynamics Lab", "Computational Neuroscience Lab", "Systems Neuroscience Lab"]
        institutions = ["University A", "University B", "Research Institute C"]
        
        return {
            "experimenter": random.choice(experimenters),
            "lab": random.choice(labs),
            "institution": random.choice(institutions),
            "experiment_description": f"Synthetic {spec.format_type} recording for testing",
            "session_description": f"Test session with {spec.channels} channels",
            "session_start_time": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            "identifier": f"test_session_{random.randint(1000, 9999)}",
            "keywords": ["test", "synthetic", spec.format_type],
            "notes": f"Generated with corruption level {spec.corruption_level}",
            "data_collection": {
                "sampling_rate": spec.sampling_rate,
                "channels": spec.channels,
                "duration_seconds": spec.duration_seconds
            }
        }


class TestDatasetFactory:
    """Factory for creating test datasets with different characteristics."""
    
    def __init__(self, generator: Optional[SyntheticDataGenerator] = None):
        self.generator = generator or SyntheticDataGenerator()
    
    def create_clean_dataset(self, output_dir: Path, format_type: str = "open_ephys") -> Dict[str, Any]:
        """Create a clean, well-formed dataset."""
        spec = DatasetSpec(
            format_type=format_type,
            file_count=3,
            total_size_mb=10.0,
            channels=64,
            sampling_rate=30000.0,
            duration_seconds=60.0,
            has_events=True,
            has_metadata=True,
            corruption_level=0.0
        )
        
        return self._generate_dataset(output_dir, spec)
    
    def create_corrupted_dataset(self, output_dir: Path, format_type: str = "open_ephys") -> Dict[str, Any]:
        """Create a dataset with various corruption issues."""
        spec = DatasetSpec(
            format_type=format_type,
            file_count=2,
            total_size_mb=5.0,
            channels=32,
            sampling_rate=25000.0,
            duration_seconds=30.0,
            has_events=True,
            has_metadata=False,  # Missing metadata
            corruption_level=0.1  # 10% corruption
        )
        
        return self._generate_dataset(output_dir, spec)
    
    def create_minimal_dataset(self, output_dir: Path, format_type: str = "generic") -> Dict[str, Any]:
        """Create a minimal dataset for quick testing."""
        spec = DatasetSpec(
            format_type=format_type,
            file_count=1,
            total_size_mb=1.0,
            channels=4,
            sampling_rate=1000.0,
            duration_seconds=10.0,
            has_events=False,
            has_metadata=True,
            corruption_level=0.0
        )
        
        return self._generate_dataset(output_dir, spec)
    
    def create_large_dataset(self, output_dir: Path, format_type: str = "spikeglx") -> Dict[str, Any]:
        """Create a large dataset for performance testing."""
        spec = DatasetSpec(
            format_type=format_type,
            file_count=5,
            total_size_mb=100.0,
            channels=384,
            sampling_rate=30000.0,
            duration_seconds=300.0,  # 5 minutes
            has_events=True,
            has_metadata=True,
            corruption_level=0.0
        )
        
        return self._generate_dataset(output_dir, spec)
    
    def _generate_dataset(self, output_dir: Path, spec: DatasetSpec) -> Dict[str, Any]:
        """Generate dataset based on specification."""
        generators = {
            "open_ephys": self.generator.generate_open_ephys_dataset,
            "spikeglx": self.generator.generate_spikeglx_dataset,
            "generic": self.generator.generate_generic_dataset
        }
        
        generator_func = generators.get(spec.format_type, self.generator.generate_generic_dataset)
        return generator_func(output_dir, spec)