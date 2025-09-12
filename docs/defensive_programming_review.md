# Defensive Programming and TDD Review

## Overview

This document summarizes the review and improvements made to the test suite's
defensive programming patterns and TDD practices.

## Current State Analysis

### Test Suite Statistics

- **Total test files**: 24
- **Files with skipif**: 4 (appropriate for external dependencies)
- **Files with xfail**: 1 (improved to 3+ with better patterns)
- **Try-except blocks**: 56 (good error handling coverage)
- **Import error handling**: 19 files (good defensive patterns)

### Key Findings

1. **Good defensive patterns already in place**:
   - Most files have proper import error handling with try-except blocks
   - Availability flags are used consistently
   - Error handling is comprehensive

2. **Areas for improvement**:
   - Too many `skipif` markers compared to `xfail` markers
   - Some tests skip functionality that should be tested with `xfail`
   - Error messages in assertions could be more descriptive

## Improvements Implemented

### 1. Better xfail Usage Patterns

#### Before (skipif for unimplemented functionality):

```python
@pytest.mark.skipif(not FEATURE_AVAILABLE, reason="Feature not implemented yet")
def test_advanced_feature():
    # Test that should define desired behavior
    pass
```

#### After (xfail for TDD):

```python
@pytest.mark.xfail(reason="Advanced feature not implemented yet", strict=False)
def test_advanced_feature():
    """Test advanced feature (defines desired behavior for implementation)."""
    # This test will pass when the feature is implemented
    result = advanced_feature()
    assert result.status == "success"
```

### 2. Defensive Assertions with Better Error Messages

#### Before:

```python
assert result is not None
assert len(items) > 0
assert status == expected
```

#### After:

```python
assert result is not None, f"Expected result to be available, got None"
assert len(items) > 0, f"Expected items to have content, got empty collection"
assert status == expected, f"Expected status {expected}, got {status}"
```

### 3. Proper Use of xfail Strict Mode

```python
# Use strict=False for functionality that might work partially
@pytest.mark.xfail(reason="Feature partially implemented", strict=False)

# Use strict=True for functionality that definitely won't work yet
@pytest.mark.xfail(reason="Feature not started", strict=True)
```

### 4. Conditional xfail for Dynamic Situations

```python
def test_feature_with_conditional_xfail():
    """Test that adapts based on what's available."""
    if not feature_available():
        pytest.xfail("Feature not available in current configuration")

    # Test the feature
    result = use_feature()
    assert result.success
```

## Best Practices Established

### When to Use skipif vs xfail

#### Use `skipif` for:

- Platform-specific functionality only
- Tests that cannot run in current environment due to system constraints

```python
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only functionality")
@pytest.mark.skipif(not shutil.which("docker"), reason="Docker not available")
```

#### NEVER use `skipif` for:

- Missing Python packages or dependencies
- Unimplemented functionality
- Import errors

All dependencies should be properly declared and available. Import errors should
fail fast and clearly.

#### Use `xfail` for:

- Functionality that should exist but isn't implemented yet
- Known bugs that are being worked on
- Features that are partially implemented
- Tests that define desired behavior for TDD

```python
@pytest.mark.xfail(reason="Caching not implemented yet")
@pytest.mark.xfail(reason="Known issue #123 - fix in progress")
@pytest.mark.xfail(reason="Performance optimization pending", strict=False)
```

### Defensive Programming Patterns

#### 1. Fail-Fast Import Handling

```python
# ✅ CORRECT: Direct imports that fail fast
from module import Component

# ❌ WRONG: Graceful degradation that hides real issues
# try:
#     from module import Component
#     COMPONENT_AVAILABLE = True
# except ImportError:
#     Component = None
#     COMPONENT_AVAILABLE = False
```

All dependencies should be properly declared in pyproject.toml. Missing
dependencies indicate a real configuration problem that should be fixed, not
hidden.

#### 2. Graceful Degradation Testing

```python
def test_with_graceful_degradation():
    """Test that works with or without optional components."""
    component = Component()

    if hasattr(component, 'advanced_feature'):
        result = component.advanced_feature()
        assert result.advanced_mode is True
    else:
        # Test basic functionality
        result = component.basic_feature()
        assert result.basic_mode is True
```

#### 3. Comprehensive Error Testing

```python
def test_error_handling():
    """Test all error conditions defensively."""
    component = Component()

    # Test expected errors
    with pytest.raises(ValueError, match="Invalid input"):
        component.process(None)

    # Test unexpected errors with context
    try:
        component.risky_operation()
    except Exception as e:
        pytest.fail(f"Unexpected error: {type(e).__name__}: {e}")
```

## Example: Improved Integration Test

```python
class TestMCPServerIntegration:
    """Example of improved integration test with defensive programming."""

    @pytest.mark.xfail(reason="Full MCP integration not complete", strict=False)
    async def test_complete_workflow(self, mcp_server):
        """Test complete MCP workflow (defines target behavior)."""
        # This test will pass when full integration is complete

        # Start server with defensive checks
        mcp_server.start()
        assert mcp_server.is_running(), "Server should start successfully"

        # Test tool execution with detailed error messages
        result = await mcp_server.execute_tool("echo", message="test")
        assert result["status"] == "success", (
            f"Echo tool should work, got status: {result.get('status')} "
            f"with message: {result.get('message', 'No message')}"
        )

        # Test pipeline state with conditional checks
        if hasattr(mcp_server, 'pipeline_state'):
            state = mcp_server.get_pipeline_state()
            assert isinstance(state, dict), "Pipeline state should be a dictionary"
        else:
            pytest.xfail("Pipeline state management not implemented yet")

    def test_basic_functionality_that_works(self, mcp_server):
        """Test functionality that should already work."""
        # No xfail - this should pass
        assert mcp_server is not None
        assert hasattr(mcp_server, 'start')
        assert hasattr(mcp_server, 'stop')
```

## Benefits of Improved Approach

### 1. Better TDD Workflow

- `xfail` tests show what needs to be implemented
- Tests turn from red (xfail) to green (pass) as features are completed
- Clear progress tracking for development

### 2. More Informative Test Results

- Better error messages help debug failures quickly
- Conditional xfail provides context about partial implementations
- Strict mode prevents false positives

### 3. Cleaner Test Organization

- `skipif` only for environmental issues
- `xfail` for implementation status
- Clear separation of concerns

### 4. Enhanced Debugging

- Detailed assertion messages
- Context about what was expected vs. received
- Better error handling for edge cases

## Implementation Guidelines

### For New Tests

1. Use `xfail` for unimplemented functionality you want to test
2. Add `strict=False` if the functionality might partially work
3. Include detailed reasons in xfail markers
4. Write comprehensive assertions with error messages

### For Existing Tests

1. Review `skipif` markers - convert to `xfail` if appropriate
2. Add better error messages to assertions
3. Include defensive checks for prerequisites
4. Use conditional xfail for dynamic situations

### For Integration Tests

1. Always use defensive assertions
2. Check prerequisites before running expensive operations
3. Provide context in error messages
4. Use xfail to define target behavior for complex workflows

## Monitoring and Maintenance

### Regular Reviews

- Run `scripts/review_defensive_testing.py` periodically
- Check xfail tests that start passing unexpectedly
- Update reasons in markers as implementation progresses

### Metrics to Track

- Ratio of xfail to skipif markers
- Number of tests with detailed error messages
- Coverage of defensive programming patterns
- Progress of xfail tests becoming passing tests

## Conclusion

The improved defensive programming approach provides:

- Better TDD workflow with clear implementation targets
- More informative test failures and debugging
- Cleaner separation between environmental and implementation issues
- Enhanced test reliability and maintainability

This approach supports the project's goal of using tests to drive development
while maintaining robust error handling and clear feedback about implementation
progress.
