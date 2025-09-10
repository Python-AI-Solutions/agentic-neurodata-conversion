"""
Sample unit tests demonstrating the testing infrastructure.

This module shows how to use the testing infrastructure components
and serves as a template for other unit tests.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from tests.fixtures.data_generators import TestDatasetFactory, DatasetSpec
from tests.fixtures.mock_services import MockLLMClient, MockNeuroConvInterface
from tests.fixtures.test_utilities import (
    TestTimer, AssertionHelper, temporary_directory, 
    create_sample_nwb_metadata, MockPatcher
)
from tests.fixtures.cleanup import TestCleanupManager, isolated_test_environment
from tests.test_config import TestConfig, TestEnvironment


class TestInfrastructureDemo:
    """Demonstrate testing infrastructure capabilities."""
    
    def test_basic_assertions(self):
        """Test basic assertion helpers."""
        # Test dict contains assertion
        actual = {"a": 1, "b": 2, "c": 3}
        expected = {"a": 1, "b": 2}
        
        AssertionHelper.assert_dict_contains(actual, expected)
        
        # Test list contains assertion
        actual_list = [1, 2, 3, 4, 5]
        expected_items = [2, 4]
        
        AssertionHelper.assert_list_contains_items(actual_list, expected_items)
    
    def test_temporary_directory(self):
        """Test temporary directory utility."""
        with temporary_directory() as temp_dir:
            # Create a test file
            test_file = temp_dir / "test.txt"
            test_file.write_text("test content")
            
            AssertionHelper.assert_file_exists(test_file)
        
        # File should be cleaned up after context
        AssertionHelper.assert_file_not_exists(test_file)
    
    def test_timer_utility(self):
        """Test timing utility."""
        timer = TestTimer()
        timer.start()
        
        # Simulate some work
        import time
        time.sleep(0.01)
        
        elapsed = timer.stop()
        assert elapsed >= 0.01
        assert elapsed < 0.1  # Should be quick
    
    def test_mock_patcher(self):
        """Test mock patcher utility."""
        with MockPatcher() as patcher:
            # Add some patches
            mock_func = patcher.add_patch('builtins.open', return_value=Mock())
            mock_async = patcher.add_async_patch('asyncio.sleep')
            
            # Test that patches are active
            import builtins
            result = builtins.open("test")
            assert result == mock_func.return_value
            
            # Async mock should be available
            assert mock_async.called is False
    
    def test_cleanup_manager(self):
        """Test cleanup manager."""
        cleanup_manager = TestCleanupManager()
        
        # Create temporary files
        temp_file = cleanup_manager.create_temp_file(suffix=".txt", content=b"test")
        temp_dir = cleanup_manager.create_temp_dir()
        
        # Verify they exist
        assert temp_file.exists()
        assert temp_dir.exists()
        
        # Clean up
        cleanup_manager.cleanup_all()
        
        # Verify they're gone
        assert not temp_file.exists()
        assert not temp_dir.exists()
    
    def test_isolated_environment(self):
        """Test isolated test environment."""
        import os
        original_env = os.environ.get("TEST_VAR")
        
        with isolated_test_environment() as env:
            cleanup_manager = env["cleanup_manager"]
            temp_dir = env["temp_dir"]
            
            # Environment should be set up
            assert os.environ.get("AGENTIC_CONVERTER_ENV") == "test"
            assert temp_dir.exists()
            
            # Create some test files
            test_file = cleanup_manager.create_temp_file()
            assert test_file.exists()
        
        # Environment should be restored
        assert os.environ.get("TEST_VAR") == original_env
        assert not test_file.exists()


class TestDataGeneration:
    """Test data generation utilities."""
    
    def test_dataset_factory_clean_dataset(self):
        """Test creating clean dataset."""
        factory = TestDatasetFactory()
        
        with temporary_directory() as temp_dir:
            dataset_info = factory.create_clean_dataset(temp_dir, "open_ephys")
            
            assert dataset_info["format"] == "open_ephys"
            assert dataset_info["channels"] == 64
            assert dataset_info["sampling_rate"] == 30000.0
            assert len(dataset_info["files"]) >= 1
            
            # Verify files exist
            for file_path in dataset_info["files"]:
                assert Path(file_path).exists()
    
    def test_dataset_factory_corrupted_dataset(self):
        """Test creating corrupted dataset."""
        factory = TestDatasetFactory()
        
        with temporary_directory() as temp_dir:
            dataset_info = factory.create_corrupted_dataset(temp_dir, "spikeglx")
            
            assert dataset_info["format"] == "spikeglx"
            assert dataset_info["channels"] == 32
            assert len(dataset_info["files"]) >= 1
    
    def test_dataset_factory_minimal_dataset(self):
        """Test creating minimal dataset."""
        factory = TestDatasetFactory()
        
        with temporary_directory() as temp_dir:
            dataset_info = factory.create_minimal_dataset(temp_dir, "generic")
            
            assert dataset_info["format"] == "generic"
            assert dataset_info["channels"] == 4
            assert dataset_info["duration"] == 10.0


class TestMockServices:
    """Test mock service utilities."""
    
    @pytest.mark.asyncio
    async def test_mock_llm_client(self):
        """Test mock LLM client."""
        responses = {
            "completion": "Mock completion response",
            "questions": [
                {
                    "field": "test_field",
                    "question": "Test question?",
                    "explanation": "Test explanation",
                    "priority": "high"
                }
            ]
        }
        
        client = MockLLMClient(responses)
        
        # Test completion
        completion = await client.generate_completion("test prompt")
        assert completion == "Mock completion response"
        
        # Test questions
        questions = await client.generate_questions("test context")
        assert len(questions) == 1
        assert questions[0]["field"] == "test_field"
        
        # Verify call tracking
        assert client.call_count == 2
        assert len(client.call_history) == 2
    
    def test_mock_neuroconv_interface(self):
        """Test mock NeuroConv interface."""
        responses = {
            "metadata": {"test": "metadata"},
            "validation_errors": ["Test error"]
        }
        
        interface = MockNeuroConvInterface(responses)
        
        # Test metadata
        metadata = interface.get_metadata()
        assert metadata == {"test": "metadata"}
        
        # Test validation
        errors = interface.validate()
        assert errors == ["Test error"]
        
        # Test conversion tracking
        with temporary_directory() as temp_dir:
            nwb_path = temp_dir / "test.nwb"
            interface.run_conversion(str(nwb_path), {"test": "metadata"})
            
            assert len(interface.conversion_calls) == 1
            assert interface.conversion_calls[0]["nwbfile_path"] == str(nwb_path)
            assert nwb_path.exists()  # Mock creates the file


class TestConfigurationSystem:
    """Test configuration system."""
    
    def test_test_config_creation(self):
        """Test test configuration creation."""
        config = TestConfig.for_environment(TestEnvironment.UNIT)
        
        assert config.environment == TestEnvironment.UNIT
        assert config.use_real_llm is False
        assert config.use_real_datasets is False
        assert config.timeout == 30
        assert config.parallel_workers == 4
    
    def test_integration_config(self):
        """Test integration configuration."""
        config = TestConfig.for_environment(TestEnvironment.INTEGRATION)
        
        assert config.environment == TestEnvironment.INTEGRATION
        assert config.use_real_llm is False
        assert config.use_real_datasets is True
        assert config.timeout == 120
    
    def test_e2e_config(self):
        """Test end-to-end configuration."""
        config = TestConfig.for_environment(TestEnvironment.E2E)
        
        assert config.environment == TestEnvironment.E2E
        assert config.use_real_llm is True
        assert config.use_real_datasets is True
        assert config.timeout == 600


@pytest.mark.unit
class TestMarkerSystem:
    """Test pytest marker system."""
    
    @pytest.mark.slow
    def test_slow_operation(self):
        """Test marked as slow."""
        # This test would be skipped with -m "not slow"
        import time
        time.sleep(0.01)  # Simulate slow operation
        assert True
    
    @pytest.mark.requires_llm
    def test_llm_dependent_operation(self):
        """Test that requires LLM."""
        # This test would be skipped without LLM access
        assert True
    
    @pytest.mark.requires_datasets
    def test_dataset_dependent_operation(self):
        """Test that requires datasets."""
        # This test would be skipped without datasets
        assert True


class TestPerformanceMeasurement:
    """Test performance measurement utilities."""
    
    def test_execution_time_assertion(self):
        """Test execution time assertion."""
        def fast_function():
            return "result"
        
        # This should pass
        result = AssertionHelper.assert_execution_time_under(fast_function, 1.0)
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_async_execution_time_assertion(self):
        """Test async execution time assertion."""
        async def fast_async_function():
            await asyncio.sleep(0.001)
            return "async_result"
        
        # This should pass
        result = await AssertionHelper.assert_async_execution_time_under(fast_async_function, 1.0)
        assert result == "async_result"


@pytest.mark.integration
class TestFixtureIntegration:
    """Test integration between different fixtures."""
    
    def test_sample_metadata_creation(self, sample_metadata):
        """Test sample metadata fixture."""
        assert "identifier" in sample_metadata
        assert "session_description" in sample_metadata
        assert "experimenter" in sample_metadata
        
        # Validate using utility
        from tests.fixtures.test_utilities import DataValidator
        issues = DataValidator.validate_nwb_metadata(sample_metadata)
        assert len(issues) == 0
    
    def test_sample_files_map_creation(self, sample_files_map):
        """Test sample files map fixture."""
        assert "recording" in sample_files_map
        assert "events" in sample_files_map
        
        # Verify files exist
        for file_path in sample_files_map.values():
            assert Path(file_path).exists()
    
    def test_mock_settings_fixture(self, mock_settings):
        """Test mock settings fixture."""
        assert mock_settings.environment == "test"
        assert mock_settings.debug is True
        assert mock_settings.server.host == "127.0.0.1"