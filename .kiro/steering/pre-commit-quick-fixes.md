# Pre-commit Quick Fixes Reference

## Most Common Pre-commit Issues and Fixes

This is a quick reference for the most common pre-commit failures and how to fix them.

### 1. Unused Function Arguments (ARG001)

**Error**: `ARG001 Unused function argument: 'param'`

**Fix**: Prefix unused arguments with underscore
```python
# ❌ Before
def my_function(used_param, unused_param):
    return used_param

# ✅ After  
def my_function(used_param, _unused_param):
    return used_param
```

**Common in**:
- Test functions: `def test_func(_config, items):`
- MCP tools: `async def tool(param, _server=None):`
- **kwargs functions: `def func(**_kwargs):`

### 2. Unused Imports (F401)

**Error**: `F401 'module' imported but unused`

**Fix**: Remove unused imports or add `# noqa: F401`
```python
# ❌ Before
import os
import sys  # unused

# ✅ After - remove unused
import os

# ✅ After - or keep with noqa if needed for testing
import sys  # noqa: F401
```

### 3. Import Sorting (I001)

**Error**: `I001 Import block is un-sorted or un-formatted`

**Fix**: Let ruff handle automatically
```bash
pixi run format
```

**Manual fix pattern**:
```python
# ✅ Correct order
import json
import logging
from pathlib import Path
from typing import Any, Optional

from .types import MyType
```

### 4. Long Lines (E501)

**Error**: Line exceeds 88 characters

**Fix**: Break into multiple lines
```python
# ❌ Before
def very_long_function_name(param1, param2, param3, param4):

# ✅ After
def very_long_function_name(
    param1, param2, param3, param4
):
```

### 5. Manual Counter (SIM113)

**Error**: `SIM113 Use enumerate() for index variable`

**Fix**: Replace manual counter with enumerate
```python
# ❌ Before
counter = 0
for item in items:
    process(item, counter)
    counter += 1

# ✅ After
for counter, item in enumerate(items):
    process(item, counter)
```

### 6. Nested With Statements (SIM117)

**Error**: `SIM117 Use a single with statement`

**Fix**: Combine with statements
```python
# ❌ Before
with open(file1) as f1:
    with open(file2) as f2:
        process(f1, f2)

# ✅ After
with open(file1) as f1, open(file2) as f2:
    process(f1, f2)
```

### 7. Try-Except-Pass (SIM105)

**Error**: `SIM105 Use contextlib.suppress(Exception)`

**Fix**: Use contextlib.suppress
```python
# ❌ Before
try:
    risky_operation()
except Exception:
    pass

# ✅ After
import contextlib

with contextlib.suppress(Exception):
    risky_operation()
```

### 8. Module Import Not at Top (E402)

**Error**: `E402 Module level import not at top of file`

**Fix**: Add `# noqa: E402` for scripts that modify sys.path
```python
# For standalone scripts only
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from my_package import my_module  # noqa: E402
```

## Quick Fix Workflow

### When Pre-commit Fails:

1. **Read the error message** - it tells you exactly what's wrong
2. **Run formatting first**: `pixi run format`
3. **Fix remaining issues manually** using patterns above
4. **Run pre-commit again**: `pixi run pre-commit`
5. **Repeat until it passes**

### Common Commands:

```bash
# Fix most formatting issues automatically
pixi run format

# Check what linting issues remain
pixi run lint

# Run all pre-commit checks (includes --unsafe-fixes)
pixi run pre-commit

# Debug specific files
pixi run ruff check path/to/file.py

# Apply unsafe fixes manually if needed
pixi run ruff check --fix --unsafe-fixes
```

## Test-Specific Patterns

### Pytest Functions
```python
# ✅ Collection modifier
def pytest_collection_modifyitems(_config, items):
    pass

# ✅ Test fixtures  
@pytest.fixture
def my_fixture(_request):
    pass

# ✅ Test functions with unused params
def test_feature(_config, items):
    assert len(items) > 0
```

### MCP Tool Functions
```python
# ✅ Tool with unused server parameter
async def my_tool(param1: str, _server=None):
    return {"result": param1}

# ✅ Tool with unused kwargs
def tool_function(**_kwargs):
    return {"result": "processed"}
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

## Prevention Tips

1. **Configure your IDE** to match pre-commit rules
2. **Run pre-commit frequently** during development
3. **Use underscore prefix** for unused parameters from the start
4. **Let ruff handle formatting** - don't fight it
5. **Follow the patterns** shown in existing code

## IDE Configuration

### VS Code
```json
{
  "python.formatting.provider": "ruff",
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [88]
}
```

### PyCharm
- Enable "Reformat code" on save
- Set right margin to 88 characters
- Configure ruff as external tool

Remember: Pre-commit hooks are there to help maintain code quality. Work with them, not against them!