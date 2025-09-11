---
inclusion: always
---

# Pre-commit Guide

## Essential Workflow

### Setup (One-time)

```bash
pixi run setup-hooks
```

### Daily Usage

```bash
# Before every commit - runs on staged files (default behavior)
pixi run pre-commit

# Run on all files explicitly
pixi run pre-commit -- --all-files

# If failures occur, hooks often auto-fix - run again
pixi run pre-commit -- --all-files
```

### Advanced Usage with Custom Arguments

**Note**: Use `--` to separate pixi arguments from pre-commit arguments.

```bash
# Run on specific files only
pixi run pre-commit -- --files agentic_neurodata_conversion/core/config.py

# Run on multiple specific files
pixi run pre-commit -- --files file1.py file2.py

# Run specific hooks only
pixi run pre-commit -- --hook-stage manual

# Run with verbose output
pixi run pre-commit -- --verbose

# Run from a specific commit
pixi run pre-commit -- --from-ref HEAD~1

# Run to a specific commit
pixi run pre-commit -- --to-ref HEAD

# Combine multiple arguments
pixi run pre-commit -- --all-files --verbose
```

## What Pre-commit Checks

### Auto-Fixed (No Action Needed)

- Trailing whitespace removal
- End-of-file fixes
- Import sorting
- Code formatting (88 char line length)
- YAML/JSON formatting

### Manual Fixes Required

- Unused function arguments
- Unused imports
- Long lines (>88 characters)
- Code simplification suggestions

## Common Fixes

### 1. Unused Arguments (ARG001)

```python
# ❌ Before
def my_function(used_param, unused_param):
    return used_param

# ✅ After - prefix with underscore
def my_function(used_param, _unused_param):
    return used_param
```

**Common in**: Test functions, MCP tools, \*\*kwargs functions

### 2. Unused Imports (F401)

```python
# ❌ Before
import os
import sys  # unused

# ✅ After - remove unused
import os

# ✅ Or keep with noqa if needed
import sys  # noqa: F401
```

### 3. Long Lines (E501)

```python
# ❌ Before
def very_long_function_name(param1, param2, param3, param4):

# ✅ After - break into multiple lines
def very_long_function_name(
    param1, param2, param3, param4
):
```

### 4. Code Simplifications

#### Manual Counter (SIM113)

```python
# ❌ Before
counter = 0
for item in items:
    process(item, counter)
    counter += 1

# ✅ After - use enumerate
for counter, item in enumerate(items):
    process(item, counter)
```

#### Nested With Statements (SIM117)

```python
# ❌ Before
with open(file1) as f1:
    with open(file2) as f2:
        process(f1, f2)

# ✅ After - combine
with open(file1) as f1, open(file2) as f2:
    process(f1, f2)
```

#### Try-Except-Pass (SIM105)

```python
# ❌ Before
try:
    risky_operation()
except Exception:
    pass

# ✅ After - use contextlib.suppress
import contextlib

with contextlib.suppress(Exception):
    risky_operation()
```

## Test-Specific Patterns

### Pytest Functions

```python
# ✅ Collection modifier
def pytest_collection_modifyitems(_config, items):
    pass

# ✅ Test functions with unused params
def test_feature(_config, items):
    assert len(items) > 0

# ✅ MCP tool functions
async def my_tool(param1: str, _server=None):
    return {"result": param1}
```

### Import Patterns for Tests

```python
# ✅ Conditional imports with availability check
try:
    from my_module import Component
    COMPONENT_AVAILABLE = True
except ImportError:
    Component = None
    COMPONENT_AVAILABLE = False

# ✅ Keep test-only imports with noqa
try:
    import datalad  # noqa: F401
    DATALAD_AVAILABLE = True
except ImportError:
    DATALAD_AVAILABLE = False
```

## Quick Fix Workflow

### When Pre-commit Fails

1. **Read error messages** - They tell you exactly what's wrong
2. **Run formatting first**: `pixi run format`
3. **Fix remaining issues manually** using patterns above
4. **Run pre-commit again**: `pixi run pre-commit -- --all-files` (or with your
   original arguments)
5. **Repeat until passes**

### Debug Commands

```bash
# Fix most formatting automatically
pixi run format

# Check specific linting issues
pixi run lint

# Debug specific files
pixi run ruff check path/to/file.py

# Apply unsafe fixes if needed
pixi run ruff check --fix --unsafe-fixes
```

## IDE Integration

### VS Code Settings

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

### PyCharm Settings

- Enable "Reformat code" on save
- Set right margin to 88 characters
- Configure ruff as external tool

## Troubleshooting

### Persistent Failures

- Check for syntax errors in mentioned files
- Ensure files are valid Python
- Look for encoding issues
- Run individual tools to isolate problems

### Import Conflicts

- Usually caused by editing files while pre-commit runs
- Solution: `pixi run format` then `pixi run pre-commit -- --all-files`

## Benefits

1. **Consistent code style** - All code follows same standards
2. **Early error detection** - Catch issues before CI/CD
3. **Automated fixes** - Many issues fixed automatically
4. **Team efficiency** - No manual code review for style
5. **Quality assurance** - Comprehensive multi-file checks

## Prevention Tips

1. **Configure IDE** to match pre-commit rules
2. **Run frequently** during development
3. **Use underscore prefix** for unused parameters from start
4. **Let ruff handle formatting** - don't fight it
5. **Follow existing patterns** in codebase

Remember: **Pre-commit hooks help maintain quality - work with them, not against
them.**
