"""
Format detection interface for identifying neuroscience data formats.

This module provides the FormatDetector class for analyzing dataset directories
and identifying data formats, file structures, and basic metadata.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class FormatDetector:
    """Detects neuroscience data formats from file patterns and structures."""
    
    def __init__(self):
        self.supported_formats = {
            'open_ephys': {
                'extensions': ['.continuous', '.spikes', '.events'],
                'patterns': ['continuous', 'spikes', 'events'],
                'required_files': []
            },
            'spikeglx': {
                'extensions': ['.bin', '.meta'],
                'patterns': ['imec', 'nidq'],
                'required_files': []
            },
            'neuralynx': {
                'extensions': ['.ncs', '.nev', '.ntt', '.nse'],
                'patterns': [],
                'required_files': []
            },
            'blackrock': {
                'extensions': ['.ns1', '.ns2', '.ns3', '.ns4', '.ns5', '.ns6', '.nev'],
                'patterns': [],
                'required_files': []
            },
            'intan': {
                'extensions': ['.rhd', '.rhs'],
                'patterns': [],
                'required_files': []
            }
        }
    
    async def analyze_directory(self, dataset_dir: str) -> Dict[str, Any]:
        """
        Analyze a dataset directory to detect formats and structure.
        
        Args:
            dataset_dir: Path to the dataset directory
            
        Returns:
            Dictionary containing analysis results
        """
        dataset_path = Path(dataset_dir)
        
        analysis = {
            'dataset_path': str(dataset_path.absolute()),
            'formats': [],
            'file_count': 0,
            'total_size': 0,
            'structure': {},
            'file_patterns': [],
            'earliest_timestamp': None,
            'latest_timestamp': None
        }
        
        try:
            # Collect all files
            all_files = []
            for file_path in dataset_path.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)
            
            analysis['file_count'] = len(all_files)
            
            # Analyze files
            extensions_found = set()
            patterns_found = set()
            timestamps = []
            
            for file_path in all_files:
                try:
                    # File size
                    file_size = file_path.stat().st_size
                    analysis['total_size'] += file_size
                    
                    # Timestamps
                    mtime = file_path.stat().st_mtime
                    timestamps.append(mtime)
                    
                    # Extensions and patterns
                    extensions_found.add(file_path.suffix.lower())
                    patterns_found.add(file_path.stem.lower())
                    
                except (OSError, PermissionError):
                    logger.warning(f"Could not access file: {file_path}")
                    continue
            
            # Set timestamps
            if timestamps:
                analysis['earliest_timestamp'] = min(timestamps)
                analysis['latest_timestamp'] = max(timestamps)
            
            # Detect formats
            detected_formats = []
            for format_name, format_info in self.supported_formats.items():
                confidence = self._calculate_format_confidence(
                    format_info, extensions_found, patterns_found
                )
                if confidence > 0:
                    detected_formats.append({
                        'format': format_name,
                        'confidence': confidence,
                        'matching_extensions': [
                            ext for ext in format_info['extensions'] 
                            if ext in extensions_found
                        ],
                        'matching_patterns': [
                            pattern for pattern in format_info['patterns']
                            if any(pattern in p for p in patterns_found)
                        ]
                    })
            
            # Sort by confidence
            detected_formats.sort(key=lambda x: x['confidence'], reverse=True)
            analysis['formats'] = detected_formats
            
            # Store patterns for later use
            analysis['file_patterns'] = list(patterns_found)
            
            logger.info(f"Format detection completed: {len(detected_formats)} formats detected")
            
        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _calculate_format_confidence(self, format_info: Dict[str, Any], 
                                   extensions_found: set, 
                                   patterns_found: set) -> float:
        """Calculate confidence score for a format match."""
        confidence = 0.0
        
        # Check extensions
        matching_extensions = [
            ext for ext in format_info['extensions'] 
            if ext in extensions_found
        ]
        if matching_extensions:
            confidence += 0.6 * (len(matching_extensions) / len(format_info['extensions']))
        
        # Check patterns
        matching_patterns = [
            pattern for pattern in format_info['patterns']
            if any(pattern in p for p in patterns_found)
        ]
        if matching_patterns:
            confidence += 0.4 * (len(matching_patterns) / max(len(format_info['patterns']), 1))
        
        return min(confidence, 1.0)