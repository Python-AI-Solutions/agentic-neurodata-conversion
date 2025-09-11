# Pre-commit Workflow and Quality Assurance

## Pre-commit Hook Integration

This project uses pre-commit hooks to ensure code quality and consistency. All code must pass these checks before being committed.

### Setup (One-time)

```bash
# Install pre-commit hooks
pixi run setup-hooks
```

### Daily Workflow

```bash
# Before committing any code
pixi run pre-commit

# If there are failures, the hooks will often fix them automatically
# Run again to confirm everything passes
pixi run pre-commit
```

## What Pre-commit Checks

### File Quality Checks
- Trim trailing whitespace
- Fix end of files
- Check YAML/JSON/TOML syntax
- Check for large files (>1MB)
- Check for merge conflicts
- Detect private keys and AWS credentials

### Python Code Quality
- **Ruff linter**: Comprehensive Python linting
- **Ruff formatter**: Code formatting (replaces Black)
- **Import sorting**: Handled by ruff (replaces isort)

### Documentation and Scripts
- Format YAML/JSON/Markdown with prettier
- Check shell scripts with shellcheck
- Check spelling with codespell
- Validate GitHub Actions workflows

## Common Pre-commit Fixes

### Automatic Fixes (No Action Needed)
These are fixed automatically by pre-commit:
- Trailing whitespace removal
- End-of-file fixes
- Import sorting
- Code formatting
- YAML/JSON formatting

### Manual Fixes Required

#### Unused Function Arguments
```python
# ❌ Will fail pre-commit
def my_function(used_param, unused_param):
    return used_param

# ✅ Fix by prefixing with underscore
def my_function(used_param, _unused_param):
    return used_param
```

#### Unused Imports
```python
# ❌ Will fail pre-commit
import os
import sys  # unused

def get_cwd():
    return os.getcwd()

# ✅ Fix by removing unused import
import os

def get_cwd():
    return os.getcwd()

# ✅ Or add noqa if needed for testing
import sys  # noqa: F401
```

#### Long Lines (>88 characters)
```python
# ❌ Will fail pre-commit
def very_long_function_name_that_exceeds_the_line_limit(parameter_one, parameter_two, parameter_three):
    pass

# ✅ Fix by breaking into multiple lines
def very_long_function_name_that_exceeds_the_line_limit(
    parameter_one, parameter_two, parameter_three
):
    pass
```

#### Simplification Suggestions
```python
# ❌ Manual counter (SIM113)
counter = 0
for item in items:
    process(item, counter)
    counter += 1

# ✅ Use enumerate
for counter, item in enumerate(items):
    process(item, counter)

# ❌ Nested with statements (SIM117)
with open(file1) as f1:
    with open(file2) as f2:
        process(f1, f2)

# ✅ Combined with statement
with open(file1) as f1, open(file2) as f2:
    process(f1, f2)
```

## Test Function Patterns

### Unused Parameters in Tests
Test functions often have unused parameters. Handle them properly:

```python
# ✅ GOOD - Prefix unused parameters with underscore
@pytest.mark.unit
def test_my_feature(_config, items):
    """Test function where config is unused."""
    assert len(items) > 0

# ✅ GOOD - Test functions with **kwargs
def test_function(**_kwargs):
    """Test function that accepts any kwargs."""
    return {"result": "test"}

# ✅ GOOD - MCP tool functions with unused server parameter
async def my_tool(param1: str, _server=None):
    """Tool function where server parameter is unused."""
    return {"result": param1}
```

## Script Patterns

### Import After Path Manipulation
For standalone scripts that modify sys.path:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path modification - add noqa comment
from my_package import my_module  # noqa: E402
```

### Exception Handling
```python
# ❌ Avoid try-except-pass
try:
    risky_operation()
except Exception:
    pass

# ✅ Use contextlib.suppress
import contextlib

with contextlib.suppress(Exception):
    risky_operation()
```

## Troubleshooting Pre-commit

### If Pre-commit Keeps Failing

1. **Read the error messages**: Pre-commit tells you exactly what's wrong
2. **Run individual tools**:
   ```bash
   pixi run format      # Fix formatting
   pixi run lint        # Check linting issues
   pixi run type-check  # Check types
   ```
3. **Check specific files**: Look at the files mentioned in error messages
4. **Fix manually**: Some issues require manual fixes (unused arguments, etc.)
5. **Run again**: `pixi run pre-commit` until it passes

### Common Error Patterns

#### Import Conflicts
If you see import sorting conflicts, it's usually because:
- Files were edited while pre-commit was running
- Solution: Run `pixi run format` then `pixi run pre-commit`

#### Persistent Failures
If the same files keep failing:
- Check if they have syntax errors
- Ensure they're valid Python files
- Look for encoding issues

## IDE Integration

### VS Code
Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "ruff",
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true
}
```

### PyCharm
- Enable "Reformat code" on save
- Set right margin to 88 characters
- Configure external tool for ruff

## CI/CD Integration

Pre-commit hooks also run in CI/CD to ensure code quality:
- All PRs must pass pre-commit checks
- Automated formatting is not applied in CI
- Developers must fix issues locally

## Benefits

1. **Consistent code style**: All code follows the same standards
2. **Early error detection**: Catch issues before they reach CI/CD
3. **Automated fixes**: Many issues are fixed automatically
4. **Team efficiency**: No manual code review for style issues
5. **Quality assurance**: Comprehensive checks for multiple file types

## Best Practices

1. **Run pre-commit frequently**: Don't wait until commit time
2. **Fix issues promptly**: Address pre-commit failures immediately
3. **Understand the rules**: Learn what each check does
4. **Use IDE integration**: Configure your editor to match pre-commit rules
5. **Keep hooks updated**: Regularly update pre-commit hook versions

Remember: Pre-commit hooks are your friend - they catch issues early and maintain code quality automatically.