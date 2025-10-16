"""
Integration tests for metadata skip workflow.

Tests the complete workflow:
1. Upload file
2. System asks for metadata
3. User says "skip for now" / "skip this one" / "ask one by one"
4. System proceeds with conversion

This tests the bug fix where system now properly uses pending_conversion_input_path
to resume conversion after metadata skip.
"""
import asyncio
import os
import pytest
from pathlib import Path

from models.state import GlobalState, ConversionStatus, LogLevel
from models.mcp import MCPMessage
from agents import register_conversation_agent, register_conversion_agent, register_evaluation_agent
from services import MCPServer, MockLLMService, reset_mcp_server


@pytest.fixture
def mcp_server_with_agents():
    """Create MCP server with all agents registered."""
    reset_mcp_server()
    server = MCPServer()

    # Use mock LLM service for testing to avoid API calls
    mock_llm = MockLLMService()

    # Register all agents
    register_conversion_agent(server)
    register_evaluation_agent(server, llm_service=mock_llm)
    register_conversation_agent(server, llm_service=mock_llm)

    yield server
    reset_mcp_server()


@pytest.fixture
def global_state():
    """Create fresh global state for each test."""
    return GlobalState()


@pytest.fixture
def test_file():
    """Path to test data file."""
    test_data_path = Path(__file__).parent.parent.parent.parent / "test_data" / "spikeglx" / "Noise4Sam_g0_t0.imec0.ap.bin"
    if not test_data_path.exists():
        pytest.skip(f"Test data file not found: {test_data_path}")
    return str(test_data_path)


@pytest.mark.asyncio
async def test_upload_skip_for_now_conversion(mcp_server_with_agents, test_file):
    """
    Test: Upload → "skip for now" → Conversion proceeds

    Verifies:
    1. pending_conversion_input_path is stored when metadata conversation starts
    2. System uses pending_conversion_input_path when user says "skip for now"
    3. No 500 errors or crashes
    4. Conversion proceeds successfully
    """
    global_state = mcp_server_with_agents.global_state

    # Step 1: Start conversion (simulates upload)
    start_message = MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={
            "input_path": test_file,
            "metadata": {},
        },
    )

    response = await mcp_server_with_agents.send_message(start_message)

    # Verify: System asks for metadata
    assert response.success
    assert global_state.status == ConversionStatus.AWAITING_USER_INPUT

    # Verify: pending_conversion_input_path is stored
    assert global_state.pending_conversion_input_path == test_file
    assert global_state.pending_conversion_input_path is not None

    # Step 2: User says "skip for now"
    skip_message = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={
            "user_message": "skip for now",
        },
    )

    response = await mcp_server_with_agents.send_message(skip_message)

    # Verify: System proceeds with conversion (no 500 error)
    assert response.success
    # Status should transition to CONVERTING or beyond
    assert global_state.status != ConversionStatus.AWAITING_USER_INPUT

    # Verify: No errors in logs
    error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
    # Filter out expected validation errors from NWB Inspector
    critical_errors = [
        log for log in error_logs
        if "Cannot restart conversion" in log.message
        or "input_path not available" in log.message
    ]
    assert len(critical_errors) == 0, f"Found critical errors: {critical_errors}"


@pytest.mark.asyncio
async def test_upload_skip_this_one_next_field(conversation_agent, global_state, test_file):
    """
    Test: Upload → "skip this one" → Ask next field

    Verifies:
    1. System stores pending_conversion_input_path
    2. When user skips one field, system asks for next field
    3. Uses pending_conversion_input_path correctly
    """
    # Step 1: Start conversion
    start_message = MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={
            "input_path": test_file,
            "metadata": {},
        },
    )

    response = await conversation_agent.handle_start_conversion(start_message, global_state)

    assert response.success
    assert global_state.pending_conversion_input_path == test_file

    # Step 2: User says "skip this one"
    skip_message = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={
            "user_message": "skip this one",
        },
    )

    response = await conversation_agent.handle_conversational_response(skip_message, global_state)

    # Verify: No crash or error
    assert response.success

    # Verify: No critical errors
    error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
    critical_errors = [
        log for log in error_logs
        if "Cannot restart conversion" in log.message
    ]
    assert len(critical_errors) == 0


@pytest.mark.asyncio
async def test_upload_ask_one_by_one_sequential(conversation_agent, global_state, test_file):
    """
    Test: Upload → "ask one by one" → Sequential mode

    Verifies:
    1. System stores pending_conversion_input_path
    2. Sequential preference is saved
    3. System uses pending_conversion_input_path correctly
    """
    # Step 1: Start conversion
    start_message = MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={
            "input_path": test_file,
            "metadata": {},
        },
    )

    response = await conversation_agent.handle_start_conversion(start_message, global_state)

    assert response.success
    assert global_state.pending_conversion_input_path == test_file

    # Step 2: User says "ask one by one"
    sequential_message = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={
            "user_message": "ask one by one",
        },
    )

    response = await conversation_agent.handle_conversational_response(sequential_message, global_state)

    # Verify: Sequential preference set
    assert global_state.user_wants_sequential is True

    # Verify: No crash or error
    assert response.success

    # Verify: No critical errors
    error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
    critical_errors = [
        log for log in error_logs
        if "Cannot restart conversion" in log.message
    ]
    assert len(critical_errors) == 0


@pytest.mark.asyncio
async def test_pending_path_fallback_to_input_path(conversation_agent, global_state, test_file):
    """
    Test: Verify fallback logic when pending_conversion_input_path is None

    Verifies:
    1. If pending_conversion_input_path is None but input_path is set, system uses input_path
    2. Fallback logic: conversion_path = state.pending_conversion_input_path or state.input_path
    """
    # Manually set state as if metadata conversation started without pending_path
    global_state.input_path = test_file
    global_state.pending_conversion_input_path = None  # Simulate old behavior
    global_state.status = ConversionStatus.AWAITING_USER_INPUT

    # User says "skip for now"
    skip_message = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={
            "user_message": "skip for now",
        },
    )

    response = await conversation_agent.handle_conversational_response(skip_message, global_state)

    # Verify: System still works (fallback to input_path)
    assert response.success

    # Verify: No critical errors
    error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
    critical_errors = [
        log for log in error_logs
        if "Cannot restart conversion" in log.message
    ]
    assert len(critical_errors) == 0


@pytest.mark.asyncio
async def test_missing_both_paths_returns_error(conversation_agent, global_state):
    """
    Test: Verify error when both pending_conversion_input_path and input_path are None

    Verifies:
    1. System returns proper error response
    2. No crash (500 error)
    3. Clear error message to user
    """
    # Manually set state with no paths
    global_state.input_path = None
    global_state.pending_conversion_input_path = None
    global_state.status = ConversionStatus.AWAITING_USER_INPUT

    # User says "skip for now"
    skip_message = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={
            "user_message": "skip for now",
        },
    )

    response = await conversation_agent.handle_conversational_response(skip_message, global_state)

    # Verify: Error response (not crash)
    assert not response.success
    assert response.error_code == "INVALID_STATE"
    assert "file path is not available" in response.error_message.lower()

    # Verify: Error logged
    error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
    assert len(error_logs) > 0
    assert any("Cannot restart conversion" in log.message for log in error_logs)


@pytest.mark.asyncio
async def test_none_string_path_returns_error(conversation_agent, global_state):
    """
    Test: Verify error when input_path is string "None" (the original bug)

    Verifies:
    1. System detects string "None" as invalid
    2. Returns proper error response
    3. No attempt to use "None" as file path
    """
    # Simulate the original bug: str(None) → "None"
    global_state.input_path = "None"
    global_state.pending_conversion_input_path = None
    global_state.status = ConversionStatus.AWAITING_USER_INPUT

    # User says "skip for now"
    skip_message = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={
            "user_message": "skip for now",
        },
    )

    response = await conversation_agent.handle_conversational_response(skip_message, global_state)

    # Verify: Error response (not crash)
    assert not response.success
    assert response.error_code == "INVALID_STATE"

    # Verify: Error logged with both paths
    error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
    assert len(error_logs) > 0
    assert any("Cannot restart conversion" in log.message for log in error_logs)
