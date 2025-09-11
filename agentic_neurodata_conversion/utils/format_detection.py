"""
Format detection utilities for the agentic neurodata conversion system.

This module provides functionality to detect and identify various neuroscience
data formats commonly used in the conversion pipeline.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class FormatDetector:
    """
    Utility class for detecting neuroscience data formats.
    
    Provides methods to identify data formats based on file extensions,
    directory structures, and file content analysis.
    """
    
    def __init__(self):
        """Initialize the format detector with known format patterns."""
        self._format_patterns = {
            "spikeglx": {
                "extensions": [".bin", ".meta"],
                "required_files": ["*.ap.bin", "*.ap.meta"],
                "optional_files": ["*.lf.bin", "*.lf.meta"],
                "directory_indicators": ["catgt_", "imec"],
                "description": "SpikeGLX recording format"
            },
            "open_ephys": {
                "extensions": [".continuous", ".events", ".spikes"],
                "required_files": ["*.continuous"],
                "optional_files": ["events.events", "messages.events"],
                "directory_indicators": ["Record Node", "experiment"],
                "description": "Open Ephys recording format"
            },
            "neuralynx": {
                "extensions": [".ncs", ".nev", ".ntt", ".nse"],
                "required_files": ["*.ncs"],
                "optional_files": ["*.nev", "*.ntt"],
                "directory_indicators": [],
                "description": "Neuralynx recording format"
            },
            "blackrock": {
                "extensions": [".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6", ".nev"],
                "required_files": ["*.ns*"],
                "optional_files": ["*.nev"],
                "directory_indicators": [],
                "description": "Blackrock recording format"
            },
            "intan": {
                "extensions": [".rhd", ".rhs"],
                "required_files": ["*.rhd", "*.rhs"],
                "optional_files": ["amplifier.dat", "digitalin.dat"],
                "directory_indicators": [],
                "description": "Intan recording format"
            },
            "mearec": {
                "extensions": [".h5", ".hdf5"],
                "required_files": ["*.h5", "*.hdf5"],
                "optional_files": [],
                "directory_indicators": ["mearec"],
                "description": "MEArec simulated recording format"
            },
            "suite2p": {
                "extensions": [".npy"],
                "required_files": ["F.npy", "Fneu.npy", "iscell.npy"],
                "optional_files": ["spks.npy", "stat.npy"],
                "directory_indicators": ["suite2p", "plane0"],
                "description": "Suite2p segmentation output"
            },
            "caiman": {
                "extensions": [".hdf5", ".h5", ".mat"],
                "required_files": ["*.hdf5", "*.h5"],
                "optional_files": ["*.mat"],
                "directory_indicators": ["caiman"],
                "description": "CaImAn segmentation output"
            },
            "kilosort": {
                "extensions": [".npy", ".tsv"],
                "required_files": ["spike_times.npy", "spike_clusters.npy"],
                "optional_files": ["templates.npy", "channel_map.npy"],
                "directory_indicators": ["kilosort"],
                "description": "Kilosort spike sorting output"
            },
            "nwb": {
                "extensions": [".nwb"],
                "required_files": ["*.nwb"],
                "optional_files": [],
                "directory_indicators": [],
                "description": "Neurodata Without Borders format"
            }
        }
        
        logger.info(f"Format detector initialized with {len(self._format_patterns)} known formats")
    
    def detect_format(
        self,
        data_path: Union[str, Path],
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Detect the data format of files in a given path.
        
        Args:
            data_path: Path to data file or directory
            recursive: Whether to search recursively in subdirectories
            
        Returns:
            Dictionary containing detection results
        """
        data_path = Path(data_path)
        logger.info(f"Detecting format for: {data_path}")
        
        if not data_path.exists():
            return {
                "path": str(data_path),
                "exists": False,
                "detected_formats": [],
                "confidence": 0.0,
                "error": f"Path does not exist: {data_path}"
            }
        
        detection_result = {
            "path": str(data_path),
            "exists": True,
            "is_file": data_path.is_file(),
            "is_directory": data_path.is_dir(),
            "detected_formats": [],
            "confidence": 0.0,
            "file_analysis": {},
            "directory_analysis": {}
        }
        
        if data_path.is_file():
            detection_result["file_analysis"] = self._analyze_single_file(data_path)
            detection_result["detected_formats"] = detection_result["file_analysis"].get("formats", [])
        else:
            detection_result["directory_analysis"] = self._analyze_directory(data_path, recursive)
            detection_result["detected_formats"] = detection_result["directory_analysis"].get("formats", [])
        
        # Calculate overall confidence
        if detection_result["detected_formats"]:
            confidences = [fmt.get("confidence", 0.0) for fmt in detection_result["detected_formats"]]
            detection_result["confidence"] = max(confidences)
        
        logger.info(f"Format detection completed. Found {len(detection_result['detected_formats'])} potential formats")
        return detection_result
    
    def _analyze_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single file for format detection."""
        file_analysis = {
            "file_path": str(file_path),
            "extension": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
            "formats": []
        }
        
        # Check each known format
        for format_name, format_info in self._format_patterns.items():
            confidence = 0.0
            matches = []
            
            # Check file extension
            if file_analysis["extension"] in format_info["extensions"]:
                confidence += 0.5
                matches.append(f"Extension match: {file_analysis['extension']}")
            
            # For single files, we can only do basic extension matching
            if confidence > 0:
                file_analysis["formats"].append({
                    "format": format_name,
                    "confidence": confidence,
                    "description": format_info["description"],
                    "matches": matches
                })
        
        return file_analysis
    
    def _analyze_directory(self, directory: Path, recursive: bool) -> Dict[str, Any]:
        """Analyze a directory for format detection."""
        directory_analysis = {
            "directory_path": str(directory),
            "file_count": 0,
            "subdirectory_count": 0,
            "extensions_found": set(),
            "formats": []
        }
        
        # Collect directory information
        files_found = []
        subdirs_found = []
        
        search_pattern = "**/*" if recursive else "*"
        for item in directory.glob(search_pattern):
            if item.is_file():
                files_found.append(item)
                directory_analysis["extensions_found"].add(item.suffix.lower())
            elif item.is_dir() and item != directory:
                subdirs_found.append(item)
        
        directory_analysis["file_count"] = len(files_found)
        directory_analysis["subdirectory_count"] = len(subdirs_found)
        directory_analysis["extensions_found"] = list(directory_analysis["extensions_found"])
        
        # Check each format against directory contents
        for format_name, format_info in self._format_patterns.items():
            confidence = 0.0
            matches = []
            
            # Check for required files
            required_matches = 0
            for required_pattern in format_info["required_files"]:
                matching_files = list(directory.glob(required_pattern))
                if recursive:
                    matching_files.extend(list(directory.glob(f"**/{required_pattern}")))
                
                if matching_files:
                    required_matches += 1
                    matches.append(f"Required files found: {required_pattern}")
            
            if format_info["required_files"] and required_matches > 0:
                confidence += 0.6 * (required_matches / len(format_info["required_files"]))
            
            # Check for optional files
            optional_matches = 0
            for optional_pattern in format_info["optional_files"]:
                matching_files = list(directory.glob(optional_pattern))
                if recursive:
                    matching_files.extend(list(directory.glob(f"**/{optional_pattern}")))
                
                if matching_files:
                    optional_matches += 1
                    matches.append(f"Optional files found: {optional_pattern}")
            
            if format_info["optional_files"] and optional_matches > 0:
                confidence += 0.2 * (optional_matches / len(format_info["optional_files"]))
            
            # Check directory name indicators
            directory_name = directory.name.lower()
            for indicator in format_info["directory_indicators"]:
                if indicator.lower() in directory_name:
                    confidence += 0.3
                    matches.append(f"Directory name indicator: {indicator}")
            
            # Check extension matches
            extension_matches = 0
            for ext in format_info["extensions"]:
                if ext in directory_analysis["extensions_found"]:
                    extension_matches += 1
            
            if format_info["extensions"] and extension_matches > 0:
                confidence += 0.4 * (extension_matches / len(format_info["extensions"]))
                matches.append(f"Extensions found: {extension_matches}/{len(format_info['extensions'])}")
            
            # Add format if confidence is above threshold
            if confidence > 0.3:  # Minimum confidence threshold
                directory_analysis["formats"].append({
                    "format": format_name,
                    "confidence": min(confidence, 1.0),  # Cap at 1.0
                    "description": format_info["description"],
                    "matches": matches
                })
        
        # Sort formats by confidence
        directory_analysis["formats"].sort(key=lambda x: x["confidence"], reverse=True)
        
        return directory_analysis
    
    def get_supported_formats(self) -> List[Dict[str, Any]]:
        """
        Get list of supported data formats.
        
        Returns:
            List of dictionaries describing supported formats
        """
        supported_formats = []
        
        for format_name, format_info in self._format_patterns.items():
            supported_formats.append({
                "name": format_name,
                "description": format_info["description"],
                "extensions": format_info["extensions"],
                "category": self._get_format_category(format_name)
            })
        
        return supported_formats
    
    def _get_format_category(self, format_name: str) -> str:
        """Get the category for a given format."""
        recording_formats = ["spikeglx", "open_ephys", "neuralynx", "blackrock", "intan", "mearec"]
        sorting_formats = ["kilosort"]
        segmentation_formats = ["suite2p", "caiman"]
        standard_formats = ["nwb"]
        
        if format_name in recording_formats:
            return "recording"
        elif format_name in sorting_formats:
            return "spike_sorting"
        elif format_name in segmentation_formats:
            return "segmentation"
        elif format_name in standard_formats:
            return "standard"
        else:
            return "unknown"
    
    def suggest_interfaces(self, detected_formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggest NeuroConv interfaces based on detected formats.
        
        Args:
            detected_formats: List of detected format dictionaries
            
        Returns:
            List of suggested interface configurations
        """
        interface_suggestions = []
        
        # Mapping from detected formats to NeuroConv interfaces
        format_to_interface = {
            "spikeglx": "SpikeGLXRecordingInterface",
            "open_ephys": "OpenEphysRecordingInterface",
            "neuralynx": "NeuralynxRecordingInterface", 
            "blackrock": "BlackrockRecordingInterface",
            "intan": "IntanRecordingInterface",
            "mearec": "MEArecRecordingInterface",
            "suite2p": "Suite2pSegmentationInterface",
            "caiman": "CaimanSegmentationInterface",
            "kilosort": "KilosortSortingInterface"
        }
        
        for format_info in detected_formats:
            format_name = format_info["format"]
            
            if format_name in format_to_interface:
                interface_suggestions.append({
                    "interface": format_to_interface[format_name],
                    "format": format_name,
                    "confidence": format_info["confidence"],
                    "description": format_info["description"],
                    "category": self._get_format_category(format_name)
                })
        
        # Sort by confidence
        interface_suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        logger.info(f"Generated {len(interface_suggestions)} interface suggestions")
        return interface_suggestions