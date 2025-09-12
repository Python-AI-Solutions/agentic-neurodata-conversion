---
inclusion: always
---

# Pre-commit Guide

## Setup & Usage
```bash
pixi run setup-hooks                           # One-time setup
pixi run pre-commit run --all-files            # Check all files
pixi run pre-commit run                        # Check staged files only
pixi run pre-commit run --files file1.py       # Specific files
```

## What Gets Checked

**Auto-fixed**: Whitespace, imports, formatting (88 chars), YAML/JSON
**Manual fixes**: Unused args/imports, long lines, code simplifications

## Common Fixes

```python
# ✅ Unused arguments - prefix with underscore
def func(used, _unused): return used

# ✅ Unused imports - remove or add noqa
import sys  # noqa: F401

# ✅ Long lines - break into multiple lines  
def long_name(
    param1, param2, param3
): pass

# ✅ Use enumerate instead of manual counter
for i, item in enumerate(items):
    process(item, i)

# ✅ Combine with statements
with open(f1) as a, open(f2) as b:
    process(a, b)

# ✅ Use contextlib.suppress
with contextlib.suppress(Exception):
    risky_operation()
```

## Test Patterns

```python
# ✅ Pytest functions with unused params
def pytest_collection_modifyitems(_config, items): pass
def test_feature(_config, items): pass
async def tool(param, _server=None): pass

# ✅ Optional imports
try:
    import datalad  # noqa: F401
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
```

## Fix Workflow

1. Read error messages
2. `pixi run format` (auto-fixes most issues)
3. Fix remaining manually using patterns above
4. `pixi run pre-commit run --all-files`
5. Repeat until passes

## Debug Commands
```bash
pixi run format                        # Auto-fix formatting
pixi run lint                          # Check linting
pixi run ruff check file.py            # Debug specific file
```

**Key**: Configure IDE to match rules, use underscore prefix for unused params, let ruff handle formatting.
