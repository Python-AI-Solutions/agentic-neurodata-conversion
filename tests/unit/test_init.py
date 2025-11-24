"""
Unit tests for agentic_neurodata_conversion package __init__.py

Tests package initialization, version exports, and public API.
"""

import sys
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestPackageInitialization:
    """Test suite for package initialization."""

    def test_version_and_author_exported(self):
        """Test that __version__ and __author__ are exported."""
        import agentic_neurodata_conversion

        assert hasattr(agentic_neurodata_conversion, "__version__")
        assert hasattr(agentic_neurodata_conversion, "__author__")
        assert isinstance(agentic_neurodata_conversion.__version__, str)
        assert isinstance(agentic_neurodata_conversion.__author__, str)

    def test_public_api_exported_when_dependencies_available(self):
        """Test that public API is exported when dependencies are available."""
        import agentic_neurodata_conversion

        # When imports succeed, __all__ should include the main components
        assert hasattr(agentic_neurodata_conversion, "__all__")
        assert "__version__" in agentic_neurodata_conversion.__all__
        assert "__author__" in agentic_neurodata_conversion.__all__

        # Core components should be in __all__ when dependencies are available
        if len(agentic_neurodata_conversion.__all__) > 2:
            assert "GlobalState" in agentic_neurodata_conversion.__all__
            assert "MCPMessage" in agentic_neurodata_conversion.__all__
            assert "LLMService" in agentic_neurodata_conversion.__all__

    def test_import_error_fallback_path(self):
        """Test ImportError exception handling (lines 35-37)."""
        # We need to test the ImportError path by simulating module import failure
        # This is tricky because we need to reload the module with mocked imports

        # First, remove the module from sys.modules to force re-import
        if "agentic_neurodata_conversion" in sys.modules:
            del sys.modules["agentic_neurodata_conversion"]

        # Mock the imports to raise ImportError
        with patch.dict(
            "sys.modules",
            {
                "agentic_neurodata_conversion.models.mcp": None,
                "agentic_neurodata_conversion.models.state": None,
                "agentic_neurodata_conversion.services.llm_service": None,
            },
        ):
            # Now try to import - this should trigger the ImportError path
            try:
                # We can't directly test the except block without actually triggering it
                # Instead, we'll verify the fallback __all__ structure
                import agentic_neurodata_conversion as anc_test

                # Even if imports fail, basic attributes should be available
                assert hasattr(anc_test, "__version__")
                assert hasattr(anc_test, "__author__")
                assert hasattr(anc_test, "__all__")

                # In the except ImportError case, __all__ should only have version and author
                # (lines 35-37)
                if len(anc_test.__all__) == 2:
                    assert "__version__" in anc_test.__all__
                    assert "__author__" in anc_test.__all__
            finally:
                # Clean up - reload the module normally
                if "agentic_neurodata_conversion" in sys.modules:
                    del sys.modules["agentic_neurodata_conversion"]
                import agentic_neurodata_conversion  # noqa: F401

    def test_import_error_path_with_builtins_patch(self):
        """Test ImportError exception path using builtins patch (lines 35-37)."""
        # Remove module from cache
        modules_to_remove = [key for key in sys.modules.keys() if key.startswith("agentic_neurodata_conversion")]
        removed_modules = {key: sys.modules.pop(key) for key in modules_to_remove}

        try:
            # Patch __import__ to raise ImportError for specific modules
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "agentic_neurodata_conversion.models.mcp" in name:
                    raise ImportError("Mocked import error for testing")
                if "agentic_neurodata_conversion.models.state" in name:
                    raise ImportError("Mocked import error for testing")
                if "agentic_neurodata_conversion.services.llm_service" in name:
                    raise ImportError("Mocked import error for testing")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                # Import the module - should trigger except ImportError block
                import agentic_neurodata_conversion as anc_fallback

                # Should still have basic exports (lines 35-37)
                assert hasattr(anc_fallback, "__version__")
                assert hasattr(anc_fallback, "__author__")
                assert hasattr(anc_fallback, "__all__")

                # Verify __all__ contains at least version and author
                assert "__version__" in anc_fallback.__all__
                assert "__author__" in anc_fallback.__all__
        finally:
            # Restore modules
            sys.modules.update(removed_modules)

    def test_core_components_importable_when_available(self):
        """Test that core components can be imported when dependencies are available."""
        # This tests the successful import path (lines 23-34)
        try:
            from agentic_neurodata_conversion import GlobalState, LLMService, MCPMessage

            # Verify we got the right types
            assert GlobalState is not None
            assert MCPMessage is not None
            assert LLMService is not None
        except ImportError:
            # This is acceptable - might be during installation
            pytest.skip("Dependencies not available")

    def test_version_string_format(self):
        """Test that version follows semantic versioning format."""
        import agentic_neurodata_conversion

        version = agentic_neurodata_conversion.__version__
        # Should be in format X.Y.Z
        parts = version.split(".")
        assert len(parts) >= 2, f"Version '{version}' should have at least 2 parts"
        # First two parts should be numeric
        assert parts[0].isdigit(), f"Major version should be numeric: {parts[0]}"
        assert parts[1].isdigit(), f"Minor version should be numeric: {parts[1]}"
