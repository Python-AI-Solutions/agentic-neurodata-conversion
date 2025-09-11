"""
Domain knowledge base for neuroscience data conversion.

This module provides the DomainKnowledgeBase class that contains
knowledge about neuroscience experiments, data formats, and metadata requirements.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DomainKnowledgeBase:
    """Knowledge base for neuroscience domain information."""
    
    def __init__(self):
        """Initialize the domain knowledge base."""
        self.experimental_types = {
            'electrophysiology': {
                'keywords': ['ephys', 'electrode', 'spike', 'lfp', 'neural'],
                'formats': ['open_ephys', 'spikeglx', 'neuralynx', 'blackrock', 'intan'],
                'required_metadata': ['sampling_rate', 'channel_count', 'electrode_info']
            },
            'calcium_imaging': {
                'keywords': ['calcium', 'imaging', 'fluorescence', 'roi'],
                'formats': ['tiff', 'hdf5'],
                'required_metadata': ['imaging_rate', 'roi_info', 'indicator']
            },
            'behavior': {
                'keywords': ['behavior', 'tracking', 'position', 'movement'],
                'formats': ['csv', 'json', 'video'],
                'required_metadata': ['tracking_method', 'coordinate_system']
            }
        }
        
        self.species_mapping = {
            'mouse': ['mouse', 'mus', 'musculus'],
            'rat': ['rat', 'rattus', 'norvegicus'],
            'human': ['human', 'homo', 'sapiens'],
            'macaque': ['macaque', 'macaca', 'mulatta'],
            'zebrafish': ['zebrafish', 'danio', 'rerio']
        }
        
        self.device_mapping = {
            'open_ephys': {
                'name': 'Open Ephys',
                'type': 'electrophysiology',
                'manufacturer': 'Open Ephys'
            },
            'spikeglx': {
                'name': 'SpikeGLX',
                'type': 'electrophysiology',
                'manufacturer': 'Janelia Research Campus'
            },
            'neuralynx': {
                'name': 'Neuralynx',
                'type': 'electrophysiology',
                'manufacturer': 'Neuralynx'
            },
            'blackrock': {
                'name': 'Blackrock',
                'type': 'electrophysiology',
                'manufacturer': 'Blackrock Microsystems'
            },
            'intan': {
                'name': 'Intan',
                'type': 'electrophysiology',
                'manufacturer': 'Intan Technologies'
            }
        }
    
    def infer_experimental_type(self, formats: List[str], 
                              file_patterns: List[str]) -> Optional[str]:
        """
        Infer experimental type from formats and file patterns.
        
        Args:
            formats: List of detected data formats
            file_patterns: List of file name patterns
            
        Returns:
            Inferred experimental type or None
        """
        scores = {}
        
        for exp_type, info in self.experimental_types.items():
            score = 0
            
            # Check format matches
            for format_name in formats:
                if format_name in info['formats']:
                    score += 2
            
            # Check keyword matches in file patterns
            for pattern in file_patterns:
                for keyword in info['keywords']:
                    if keyword in pattern.lower():
                        score += 1
            
            if score > 0:
                scores[exp_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    def infer_species(self, directory_path: str, 
                     file_patterns: List[str]) -> Optional[str]:
        """
        Infer species from directory path and file patterns.
        
        Args:
            directory_path: Path to the dataset directory
            file_patterns: List of file name patterns
            
        Returns:
            Inferred species or None
        """
        path_lower = directory_path.lower()
        patterns_lower = [p.lower() for p in file_patterns]
        
        for species, keywords in self.species_mapping.items():
            for keyword in keywords:
                if keyword in path_lower:
                    return species
                for pattern in patterns_lower:
                    if keyword in pattern:
                        return species
        
        return None
    
    def infer_device_from_format(self, formats: List[str]) -> Optional[Dict[str, Any]]:
        """
        Infer recording device from detected formats.
        
        Args:
            formats: List of detected data formats
            
        Returns:
            Device information dictionary or None
        """
        for format_name in formats:
            if format_name in self.device_mapping:
                return self.device_mapping[format_name]
        
        return None
    
    def get_required_metadata_for_type(self, experimental_type: str) -> List[str]:
        """
        Get required metadata fields for an experimental type.
        
        Args:
            experimental_type: The experimental type
            
        Returns:
            List of required metadata field names
        """
        if experimental_type in self.experimental_types:
            return self.experimental_types[experimental_type]['required_metadata']
        return []