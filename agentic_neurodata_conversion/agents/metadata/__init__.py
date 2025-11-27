"""Metadata-related modules for intelligent metadata handling.

This package contains modules for:
- Intelligent metadata parsing and mapping
- Metadata inference from files
- Metadata collection strategies
- NWB/DANDI schema definitions
- Predictive metadata suggestions
"""

from .inference import MetadataInferenceEngine
from .intelligent_mapper import IntelligentMetadataMapper
from .intelligent_parser import IntelligentMetadataParser
from .predictive import PredictiveMetadataSystem
from .schema import MetadataFieldSchema, NWBDANDISchema
from .strategy import MetadataRequestStrategy

__all__ = [
    "MetadataInferenceEngine",
    "IntelligentMetadataMapper",
    "IntelligentMetadataParser",
    "PredictiveMetadataSystem",
    "MetadataFieldSchema",
    "NWBDANDISchema",
    "MetadataRequestStrategy",
]
