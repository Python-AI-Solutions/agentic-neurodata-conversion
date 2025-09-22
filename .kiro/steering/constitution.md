# Project Constitution for AI Assistant

## Primary Directives

**ALWAYS:**
1. Use `pixi run` for ALL Python commands - NEVER use system Python
2. Check critical dependencies before operations - fail immediately if missing
3. Place ALL new files in proper directories - NEVER in project root
4. Run `pixi run pre-commit run --all-files` before considering any code complete
5. Write tests BEFORE implementation code

**NEVER:**
1. Return placeholder values when dependencies are missing
2. Create `summary.md` or similar documentation files
3. Use PYTHONPATH modifications
4. Hide missing dependencies with try/except silencing
5. Place test files, scripts, or temporary files in project root

## File Placement Rules

When creating ANY file, use this decision tree:

```
Is it a test?
  → YES: tests/unit/ (for unit tests)
         tests/integration/ (for integration tests)
         tests/e2e/ (for end-to-end tests)
  → NO: Continue...

Is it a script?
  → YES: scripts/temp/ (for temporary/experimental)
         scripts/debug/ (for debugging)
         scripts/utils/ (for reusable utilities)
  → NO: Continue...

Is it source code?
  → YES: Follow existing package structure
  → NO: Ask user for appropriate location
```

## Command Execution Rules

### Python Commands
```bash
# CORRECT - Always use this pattern:
pixi run python -c 'print("Hello World")'
pixi run python scripts/my_script.py

# WRONG - Never do this:
python -c "print('Hello')"
python scripts/my_script.py
/usr/bin/python3 anything.py
```

### Testing Commands (in order of preference)
```bash
# For quick validation:
pixi run test-agent              # Minimal output

# For development:
pixi run pytest -m "unit" --no-cov -x    # Fast unit tests
pixi run pytest tests/unit/test_file.py  # Specific file

# For thorough testing:
pixi run pytest -m "integration"  # Integration tests
pixi run test-cov                 # With coverage
```

## Code Generation Rules

### Dependency Handling
```python
# ALWAYS generate this pattern for critical dependencies:
try:
    import critical_package
except ImportError:
    raise ImportError(
        "critical_package required for [functionality]. "
        "Install: pixi add critical_package"
    )

# For optional features only:
try:
    import optional_package
    HAS_OPTIONAL = True
except ImportError:
    HAS_OPTIONAL = False
```

### Function Signatures
```python
# When parameters are unused, prefix with underscore:
def callback(_event, data):
    return process(data)

# For long signatures, break at 88 chars:
def very_long_function_name(
    parameter1: str,
    parameter2: int,
    parameter3: Optional[Dict] = None,
) -> ResultType:
    pass
```

### Test Structure
```python
# ALWAYS structure tests this way:
import pytest
from actual.module import ActualClass  # Direct import, fail if missing

class TestActualClass:
    @pytest.mark.unit
    def test_expected_behavior(self):
        # Arrange
        instance = ActualClass()
        
        # Act
        result = instance.method()
        
        # Assert
        assert result == expected_value
```

## Pre-commit Compliance

When generating code, ensure it will pass these checks:

1. **Line length**: Maximum 88 characters
2. **Imports**: Sorted, grouped (standard, third-party, local)
3. **Unused variables**: Prefix with underscore or remove
4. **Format**: Use consistent formatting (handled by `pixi run format`)

### Auto-fix Pattern
```bash
# If pre-commit fails, run in this order:
pixi run format                          # Auto-fixes most issues
pixi run lint                            # Shows remaining issues
pixi run pre-commit run --all-files     # Final validation
```

## Error Message Templates

When generating error messages, use these templates:

```python
# For missing dependencies:
f"{package} required for {functionality}. Install: pixi add {package}"

# For invalid operations:
f"Cannot {operation}: {reason}. Expected: {expectation}"

# For configuration issues:
f"Invalid {config_item}: {value}. Must be {requirement}"
```

## Test-Driven Development Protocol

When asked to implement a feature:

1. **First response**: Generate failing test(s)
   ```python
   # tests/unit/test_new_feature.py
   def test_feature_behavior():
       from package.module import NewFeature  # Will fail initially
       assert NewFeature().process(data) == expected
   ```

2. **Second step**: Implement minimum code to pass
3. **Third step**: Refactor if needed
4. **Final step**: Run `pixi run pre-commit run --all-files`

## Quality Checklist for Generated Code

Before presenting code to user, verify:

- [ ] Uses `pixi run` for all Python commands
- [ ] Includes dependency checks with clear errors
- [ ] Places files in correct directories
- [ ] Follows 88-character line limit
- [ ] Prefixes unused parameters with underscore
- [ ] Includes appropriate test markers
- [ ] Provides installation commands for missing packages
- [ ] Uses single quotes for shell, double for Python strings

## Special Instructions for Common Tasks

### Creating New Test Files
```python
# ALWAYS place in tests/ subdirectory
# ALWAYS include proper markers
# ALWAYS import actual implementations

# tests/unit/test_component.py
import pytest
from agentic_neurodata_conversion.component import Component

@pytest.mark.unit
def test_component_initialization():
    component = Component()
    assert component is not None
```

### Creating Scripts
```python
# scripts/temp/verify_something.py
#!/usr/bin/env python
"""Temporary script for verification."""

try:
    import required_package
except ImportError:
    raise ImportError("Install: pixi add required_package")

def main():
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

### Subprocess Calls
```python
# ALWAYS use pixi run in subprocess
import subprocess

# CORRECT:
result = subprocess.run(
    ["pixi", "run", "python", "-c", 'print("test")'],
    capture_output=True,
    text=True
)

# WRONG:
result = subprocess.run(["python", "-c", "print('test')"])
```

## Response Patterns for AI

### When user asks to create a file:
1. Determine correct directory using decision tree
2. Generate code following all patterns above
3. Include command to verify: `pixi run pre-commit run --files <filepath>`

### When user reports an error:
1. Check if it's a missing dependency → provide `pixi add` command
2. Check if it's a formatting issue → suggest `pixi run format`
3. Check if it's in wrong directory → provide correct path
4. Otherwise → request full error output with `pixi run pytest -v`

### When implementing features:
1. Start with test file in `tests/unit/`
2. Create implementation following TDD
3. Verify with `pixi run test-agent`
4. Clean up with `pixi run format`

## Critical Reminders

- **Every Python execution** must use `pixi run`
- **Every file creation** must specify correct subdirectory
- **Every dependency error** must include installation command
- **Every test** must use direct imports (no mocking core functionality)
- **Every code block** must assume pre-commit compliance

---

**Context**: This is a neuroinformatics project using NWB format. Quality assessment results influence important research decisions. Correctness and clarity are paramount.