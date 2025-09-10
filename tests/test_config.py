"""
Test configuration and environment management.

This module provides configuration classes and utilities for managing
different test environments and scenarios.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum


class TestEnvironment(Enum):
    """Test environment types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    CI = "ci"


@dataclass
class TestConfig:
    """Configuration for test execution."""
    environment: TestEnvironment
    use_real_llm: bool = False
    use_real_datasets: bool = False
    enable_logging: bool = True
    log_level: str = "DEBUG"
    timeout: int = 300
    parallel_workers: int = 1
    temp_dir: Optional[Path] = None
    
    @classmethod
    def for_environment(cls, env: TestEnvironment) -> "TestConfig":
        """Create configuration for specific test environment."""
        configs = {
            TestEnvironment.UNIT: cls(
                environment=env,
                use_real_llm=False,
                use_real_datasets=False,
                timeout=30,
                parallel_workers=4
            ),
            TestEnvironment.INTEGRATION: cls(
                environment=env,
                use_real_llm=False,
                use_real_datasets=True,
                timeout=120,
                parallel_workers=2
            ),
            TestEnvironment.E2E: cls(
                environment=env,
                use_real_llm=True,
                use_real_datasets=True,
                timeout=600,
                parallel_workers=1
            ),
            TestEnvironment.PERFORMANCE: cls(
                environment=env,
                use_real_llm=False,
                use_real_datasets=True,
                timeout=1800,
                parallel_workers=1
            ),
            TestEnvironment.CI: cls(
                environment=env,
                use_real_llm=False,
                use_real_datasets=False,
                timeout=300,
                parallel_workers=2
            )
        }
        return configs[env]


class TestDataManager:
    """Manages test data and cleanup."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self._temp_files: list[Path] = []
        self._temp_dirs: list[Path] = []
    
    def create_temp_file(self, suffix: str = "", content: bytes = b"") -> Path:
        """Create a temporary file for testing."""
        import tempfile
        
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        
        temp_path = Path(path)
        if content:
            temp_path.write_bytes(content)
        
        self._temp_files.append(temp_path)
        return temp_path
    
    def create_temp_dir(self) -> Path:
        """Create a temporary directory for testing."""
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp())
        self._temp_dirs.append(temp_dir)
        return temp_dir
    
    def cleanup(self):
        """Clean up all temporary files and directories."""
        import shutil
        
        for temp_file in self._temp_files:
            if temp_file.exists():
                temp_file.unlink()
        
        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        self._temp_files.clear()
        self._temp_dirs.clear()


class MockServiceManager:
    """Manages mock services for testing."""
    
    def __init__(self):
        self._mocks: Dict[str, Any] = {}
    
    def register_mock(self, name: str, mock_obj: Any):
        """Register a mock service."""
        self._mocks[name] = mock_obj
    
    def get_mock(self, name: str) -> Any:
        """Get a registered mock service."""
        return self._mocks.get(name)
    
    def clear_mocks(self):
        """Clear all registered mocks."""
        self._mocks.clear()


def get_test_config() -> TestConfig:
    """Get test configuration from environment variables."""
    env_name = os.getenv("TEST_ENVIRONMENT", "unit").lower()
    
    try:
        environment = TestEnvironment(env_name)
    except ValueError:
        environment = TestEnvironment.UNIT
    
    config = TestConfig.for_environment(environment)
    
    # Override with environment variables if present
    if os.getenv("USE_REAL_LLM", "").lower() in ("true", "1", "yes"):
        config.use_real_llm = True
    
    if os.getenv("USE_REAL_DATASETS", "").lower() in ("true", "1", "yes"):
        config.use_real_datasets = True
    
    if timeout := os.getenv("TEST_TIMEOUT"):
        config.timeout = int(timeout)
    
    if workers := os.getenv("TEST_PARALLEL_WORKERS"):
        config.parallel_workers = int(workers)
    
    return config


def skip_if_no_llm(config: TestConfig):
    """Skip test if LLM is required but not available."""
    import pytest
    
    if not config.use_real_llm:
        pytest.skip("Test requires real LLM service")


def skip_if_no_datasets(config: TestConfig):
    """Skip test if datasets are required but not available."""
    import pytest
    
    if not config.use_real_datasets:
        pytest.skip("Test requires real datasets")


def requires_gpu():
    """Skip test if GPU is not available."""
    import pytest
    
    try:
        import torch
        if not torch.cuda.is_available():
            pytest.skip("Test requires GPU")
    except ImportError:
        pytest.skip("Test requires PyTorch with CUDA")


def requires_network():
    """Skip test if network access is not available."""
    import pytest
    import socket
    
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
    except OSError:
        pytest.skip("Test requires network access")