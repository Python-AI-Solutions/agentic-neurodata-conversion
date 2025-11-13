"""
Test data factories for programmatic test data generation.

Eliminates external data dependencies by providing factories to generate:
- Mock NWB files
- Mock neuroscience data files (SpikeGLX, etc.)
- Mock metadata
- Mock validation results

Addresses Phase 3 (Week 8-9): Test Data Factories from TEST_STRATEGY.
"""

from .file_factory import FileFactory
from .metadata_factory import MetadataFactory
from .state_factory import StateFactory
from .validation_factory import ValidationFactory

__all__ = [
    "MetadataFactory",
    "FileFactory",
    "ValidationFactory",
    "StateFactory",
]
