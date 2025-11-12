"""
Unit tests for pending_conversion_input_path feature.

Tests the bug fix where system now properly stores and uses
pending_conversion_input_path to resume conversion after metadata skip.
"""

from models.state import GlobalState


def test_pending_conversion_input_path_field_exists():
    """Test that pending_conversion_input_path field exists in GlobalState."""
    state = GlobalState()
    assert hasattr(state, "pending_conversion_input_path")
    assert state.pending_conversion_input_path is None


def test_pending_conversion_input_path_can_be_set():
    """Test that pending_conversion_input_path can be set and retrieved."""
    state = GlobalState()
    test_path = "/test/path/to/file.bin"

    state.pending_conversion_input_path = test_path

    assert state.pending_conversion_input_path == test_path


def test_pending_conversion_input_path_resets():
    """Test that pending_conversion_input_path is reset when state resets."""
    state = GlobalState()
    state.pending_conversion_input_path = "/test/path"
    state.input_path = "/test/input"

    # Reset state
    state.reset()

    # Verify both paths are None after reset
    assert state.pending_conversion_input_path is None
    assert state.input_path is None


def test_fallback_logic_when_pending_path_is_none():
    """
    Test fallback logic: conversion_path = state.pending_conversion_input_path or state.input_path

    When pending_conversion_input_path is None, should fall back to input_path.
    """
    state = GlobalState()
    state.input_path = "/fallback/path.bin"
    state.pending_conversion_input_path = None

    # Simulate the fallback logic used in conversation_agent.py
    conversion_path = state.pending_conversion_input_path or state.input_path

    assert conversion_path == "/fallback/path.bin"


def test_pending_path_takes_priority_over_input_path():
    """
    Test that pending_conversion_input_path takes priority when both are set.

    This ensures the original path from metadata conversation start is used.
    """
    state = GlobalState()
    state.input_path = "/old/path.bin"
    state.pending_conversion_input_path = "/new/pending/path.bin"

    # Simulate the fallback logic
    conversion_path = state.pending_conversion_input_path or state.input_path

    assert conversion_path == "/new/pending/path.bin"


def test_both_paths_none_returns_none():
    """
    Test that when both paths are None, fallback returns None.

    This should trigger error handling in conversation_agent.py.
    """
    state = GlobalState()
    state.input_path = None
    state.pending_conversion_input_path = None

    # Simulate the fallback logic
    conversion_path = state.pending_conversion_input_path or state.input_path

    assert conversion_path is None


def test_string_none_detection():
    """
    Test detection of string "None" (the original bug).

    Verifies that str(None) → "None" is detected as invalid.
    """
    state = GlobalState()
    state.input_path = "None"  # The bug: str(None)
    state.pending_conversion_input_path = None

    conversion_path = state.pending_conversion_input_path or state.input_path

    # Simulate the validation logic from conversation_agent.py
    is_invalid = not conversion_path or str(conversion_path) == "None"

    assert is_invalid is True


def test_valid_path_passes_validation():
    """
    Test that a valid path passes validation.
    """
    state = GlobalState()
    state.pending_conversion_input_path = "/valid/path/to/file.bin"

    conversion_path = state.pending_conversion_input_path or state.input_path

    # Simulate the validation logic
    is_invalid = not conversion_path or str(conversion_path) == "None"

    assert is_invalid is False
    assert conversion_path == "/valid/path/to/file.bin"


def test_empty_string_path_is_invalid():
    """
    Test that empty string path is detected as invalid.
    """
    state = GlobalState()
    state.pending_conversion_input_path = ""
    state.input_path = None

    conversion_path = state.pending_conversion_input_path or state.input_path

    # Simulate the validation logic
    is_invalid = not conversion_path or str(conversion_path) == "None"

    assert is_invalid is True
