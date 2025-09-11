# Design Document

## Overview

This design optimizes the test suite verbosity configuration to provide minimal
output by default while preserving full debugging capabilities when needed. The
solution involves modifying pytest configuration defaults and restructuring pixi
task commands to use appropriate verbosity levels for different use cases.

## Architecture

### Configuration Layers

1. **Default Configuration (pyproject.toml)**
   - Minimal verbosity settings for automated execution
   - Essential markers and filtering preserved
   - Coverage reporting optimized for CI/CD

2. **Task-Specific Overrides (pixi.toml)**
   - Quiet defaults for general testing
   - Verbose options for debugging scenarios
   - Specialized commands for different contexts

3. **Command-Line Flexibility**
   - Easy verbosity escalation via flags
   - Developer-friendly debug commands

## Components and Interfaces

### Pytest Configuration Updates

**Default Settings (pyproject.toml)**

```toml
[tool.pytest.ini_options]
addopts = [
    "-q",                    # Quiet mode by default
    "--tb=line",            # Minimal traceback format
    "--no-header",          # Remove pytest header
    "--disable-warnings",   # Suppress warnings by default
    # Coverage and other essential options preserved
]
```

**Verbosity Control**

- Default: Quiet mode with minimal output
- Debug mode: Full verbosity with detailed tracebacks
- Coverage mode: Balanced output for reporting

### Pixi Task Restructuring

**Default Tasks (Minimal Output)**

```bash
test = "pytest tests/ -q"
test-unit = "pytest tests/unit/ -q -m unit --no-cov"
test-integration = "pytest tests/integration/ -q -m integration --no-cov"
test-fast = "pytest tests/ -q -m 'not slow and not requires_llm and not requires_datasets' --no-cov"
```

**Debug Tasks (Verbose Output)**

```bash
test-debug = "pytest tests/ -v -s --tb=long --pdb --no-cov"
test-verbose = "pytest tests/ -v --tb=short"
test-detailed = "pytest tests/ -vv --tb=long"
```

**Specialized Tasks**

```bash
test-summary = "pytest tests/ -q --tb=no"  # Minimal for agents
test-ci = "pytest tests/ -q --tb=line"     # CI-friendly
test-dev = "pytest tests/ -v"              # Developer default
```

## Data Models

### Output Format Specifications

**Minimal Output Format**

```
================================ test session starts ================================
collected 45 items

tests/unit ..................                                              [ 40%]
tests/integration ..........                                               [100%]

========================== 45 passed, 2 skipped in 12.34s ==========================
```

**Failure Output Format**

```
================================ test session starts ================================
collected 45 items

tests/unit ..................F.....                                       [ 40%]
tests/integration ..........                                               [100%]

=================================== FAILURES ===================================
tests/unit/test_example.py::test_function FAILED                    [100%]

========================== 1 failed, 44 passed in 12.34s ==========================
```

### Configuration Schema

**Verbosity Levels**

- Level 0 (Default): Summary only, minimal failures
- Level 1 (-v): Standard pytest verbose
- Level 2 (-vv): Extra verbose with detailed info
- Debug Mode: Full diagnostics with pdb integration

## Error Handling

### Failure Reporting Strategy

**Default Behavior**

- Show only essential failure information
- Preserve test names and basic error messages
- Minimize stack trace noise
- Maintain parseable output format

**Debug Escalation**

- Easy transition to verbose mode
- Preserve all diagnostic information
- Support interactive debugging
- Maintain backward compatibility

### Warning Management

**Default Suppression**

- Hide deprecation warnings by default
- Suppress third-party library warnings
- Preserve critical error messages
- Allow warning escalation when needed

## Testing Strategy

### Validation Approach

**Output Format Testing**

- Verify minimal output format consistency
- Test verbosity flag behavior
- Validate backward compatibility
- Ensure CI/CD integration works

**Performance Testing**

- Measure token consumption reduction
- Validate execution time impact
- Test with various test suite sizes
- Benchmark against current configuration

### Compatibility Testing

**Existing Workflow Validation**

- Test all current pixi tasks
- Verify coverage reporting works
- Validate CI/CD pipeline compatibility
- Ensure debugging workflows function

## Implementation Phases

### Phase 1: Core Configuration

- Update pyproject.toml pytest settings
- Modify default pixi task verbosity
- Preserve essential functionality

### Phase 2: Task Restructuring

- Create specialized task variants
- Add debug-specific commands
- Implement verbosity escalation paths

### Phase 3: Documentation and Migration

- Update testing guide documentation
- Provide migration guidance
- Add usage examples for different scenarios

## Benefits

### Token Efficiency

- Reduced output volume for automated agents
- Faster test result processing
- Improved agent performance in test-driven workflows

### Developer Experience

- Cleaner default output for quick feedback
- Easy access to verbose information when needed
- Preserved debugging capabilities

### CI/CD Optimization

- Faster pipeline execution
- Cleaner build logs
- Maintained reporting functionality
