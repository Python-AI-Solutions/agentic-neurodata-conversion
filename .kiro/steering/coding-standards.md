# Coding Standards and Style Guidelines

## Automated Code Quality with Pre-commit

**CRITICAL RULE**: All code must pass pre-commit hooks before committing. Use `pixi run pre-commit` to check your code.

### Pre-commit Workflow

```bash
# Install pre-commit hooks (one-time setup)
pixi run setup-hooks

# Before committing, run all checks
pixi run pre-commit

# Or run individual quality checks
pixi run format      # Format code with ruff
pixi run lint        # Check linting with ruff
pixi run type-check  # Type checking with mypy
```

## Line Length Standard

**CRITICAL RULE**: Use 88 characters as the maximum line length for all Python code.

### Why 88 Characters?

- **Ruff compatibility**: 88 is the default line length for ruff formatter
- **Readability**: Provides good balance between readability and screen real estate
- **Modern standard**: Widely adopted in the Python community
- **Tool consistency**: Works well with most editors and IDEs

### Configuration

All tools are configured to use 88 characters:

```toml
[tool.ruff]
line-length = 88

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

## Code Formatting Standards

### Ruff Handles Everything

We use **ruff** for both linting and formatting. It handles:
- Code formatting (replaces Black)
- Import sorting (replaces isort)
- Linting (replaces flake8, pyflakes, etc.)

### Import Sorting

Ruff automatically sorts imports with these rules:
- Known first-party packages: `agentic_neurodata_conversion`
- Force sort within sections
- Compatible with Black style

## Linting Rules

### Enabled Rules
- `E`: pycodestyle errors
- `W`: pycodestyle warnings  
- `F`: pyflakes
- `I`: isort (import sorting)
- `B`: flake8-bugbear
- `C4`: flake8-comprehensions
- `UP`: pyupgrade
- `ARG`: flake8-unused-arguments
- `SIM`: flake8-simplify
- `TCH`: flake8-type-checking

### Ignored Rules
- `E501`: Line too long (handled by formatter)
- `B008`: Function calls in argument defaults (common pattern)
- `C901`: Too complex (handled case-by-case)
- `ARG002`: Unused method argument (common in interfaces)

## Common Pre-commit Fixes

### Unused Function Arguments

Prefix unused arguments with underscore:

```python
# ✅ GOOD - Unused arguments prefixed with _
def tool_function(param1: str, _param2: int = 42, _server=None):
    return {"result": param1}

# ✅ GOOD - Test functions with unused kwargs
def test_function(**_kwargs):
    return {"result": "test"}
```

### Import Issues

Let ruff handle import sorting automatically:

```python
# ✅ GOOD - Ruff will sort these automatically
import json
import logging
from pathlib import Path
from typing import Any, Optional

from .types import DatasetMetadata
```

### Unused Imports

Remove unused imports or add `# noqa: F401` for intentional imports:

```python
# ✅ GOOD - Remove if truly unused
# import unused_module

# ✅ GOOD - Keep with noqa if needed for testing
import datalad  # noqa: F401
```

### Simplification Suggestions

Follow ruff's simplification suggestions:

```python
# ❌ BAD - Manual counter
event_id = 0
for item in items:
    process(item, event_id)
    event_id += 1

# ✅ GOOD - Use enumerate
for event_id, item in enumerate(items):
    process(item, event_id)

# ❌ BAD - Nested with statements
with open(file1) as f1:
    with open(file2) as f2:
        process(f1, f2)

# ✅ GOOD - Combined with statement
with open(file1) as f1, open(file2) as f2:
    process(f1, f2)

# ❌ BAD - try-except-pass
try:
    risky_operation()
except Exception:
    pass

# ✅ GOOD - Use contextlib.suppress
import contextlib

with contextlib.suppress(Exception):
    risky_operation()
```

## Development Workflow

### Pre-commit Integration

All formatting and linting is enforced via pre-commit hooks. The hooks will:
1. Fix formatting issues automatically
2. Sort imports automatically  
3. Report linting errors that need manual fixes
4. Ensure consistent code style

### IDE Configuration

#### VS Code Settings
```json
{
  "python.formatting.provider": "ruff",
  "editor.rulers": [88],
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "python.linting.enabled": true
}
```

#### PyCharm Settings
- Code Style → Python → Right margin: 88
- Tools → External Tools → Configure Ruff
- Enable "Reformat code" on save

## Code Quality Standards

### Type Hints
- Use type hints for all public functions and methods
- Use `from __future__ import annotations` for forward references
- Configure mypy for strict type checking

### Docstrings
- Use NumPy style docstrings
- Document all public functions, classes, and modules
- Include parameter types and return types

### Error Handling
- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately

## Consistency Rules

1. **Always run pre-commit**: Use `pixi run pre-commit` before committing
2. **Trust the formatter**: Don't manually format code that ruff handles
3. **Follow pre-commit suggestions**: Fix issues reported by pre-commit
4. **Use pixi commands**: Always use `pixi run format` and `pixi run lint`
5. **Minimal noqa usage**: Only use `# noqa` when absolutely necessary

## Examples

### Good Line Length Usage

```python
# ✅ GOOD - Within 88 characters
def process_neurodata_conversion(
    input_file: Path, output_file: Path, metadata: Dict[str, Any]
) -> ConversionResult:
    """Process neuroscience data conversion with proper line breaks."""
    pass

# ✅ GOOD - Proper string formatting
error_message = (
    f"Failed to convert {input_file.name} to NWB format. "
    f"Error: {error_details}"
)
```

### Avoid These Patterns

```python
# ❌ BAD - Exceeds 88 characters
def process_neurodata_conversion_with_very_long_parameter_names(input_file_path: Path, output_file_path: Path, conversion_metadata: Dict[str, Any]) -> ConversionResult:
    pass

# ❌ BAD - Long string without breaks
error_message = f"Failed to convert {input_file.name} to NWB format due to validation errors in the metadata schema"
```

## Tool Integration

### Pixi Tasks
- `pixi run pre-commit`: Run all pre-commit hooks
- `pixi run format`: Format all code with ruff
- `pixi run lint`: Check code with ruff linter
- `pixi run type-check`: Run mypy type checking
- `pixi run quality`: Run lint + format-check + type-check

### CI/CD Integration
All formatting and linting checks run in CI/CD pipeline to ensure consistency across the team.

## Troubleshooting Pre-commit Issues

### If pre-commit fails:
1. Read the error messages carefully
2. Run `pixi run format` to fix formatting issues
3. Run `pixi run lint` to see remaining issues
4. Fix any remaining issues manually
5. Run `pixi run pre-commit` again

### Common fixes:
- Unused arguments: prefix with `_`
- Unused imports: remove or add `# noqa: F401`
- Long lines: break into multiple lines
- Import sorting: let ruff handle automatically

## Benefits

1. **Consistency**: All code follows the same formatting standards
2. **Automation**: Pre-commit hooks catch issues before they're committed
3. **Quality**: Automated enforcement ensures high code quality
4. **Team efficiency**: No time wasted on formatting discussions
5. **Modern tooling**: Uses ruff for fast, comprehensive code checking

Remember: The goal is consistent, readable code that follows modern Python standards with automated quality enforcement.