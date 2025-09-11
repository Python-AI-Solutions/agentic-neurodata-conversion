---
inclusion: always
---

# Development Essentials

## Response Guidelines

**Do not create summary documents** - Avoid creating files like `summary.md` or
`task_completion_summary.md` that describe what was done in a conversation.
Focus on updating actual project documentation (README files, code comments,
etc.) instead.

## Environment & Dependencies

### Pixi-Only Development

- **Always use `pixi run <command>`** - Never use system Python or direct
  commands
- **Local package**: Configured via `pypi-dependencies` with `editable = true`
- **Never use PYTHONPATH** - Pixi handles all imports automatically
- **Add dependencies**: `pixi add <package>` or
  `pixi add --feature dev <package>`

### Quick Commands

```bash
# Setup (one-time)
pixi install && pixi run setup-hooks

# Daily workflow
pixi run pre-commit -- --all-files     # Quality checks on all files
pixi run pytest -m "unit" --no-cov    # Fast tests
pixi run format && pixi run lint       # Fix code issues
```

## Code Quality Standards

### Pre-commit Integration

**All code must pass `pixi run pre-commit -- --all-files` before committing.**

Auto-fixes: formatting, import sorting, trailing whitespace Manual fixes needed:
unused arguments (prefix with `_`), unused imports, long lines (>88 chars)

### Common Patterns

```python
# ✅ Unused parameters
def test_func(_config, items): pass
async def tool(param, _server=None): pass

# ✅ Import handling
try:
    import optional_dep  # noqa: F401
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

# ✅ Line breaks (88 char limit)
def long_function_name(
    param1, param2, param3
):
    pass
```

## Testing Strategy

### TDD Approach

1. **Write failing tests first** - Define expected behavior
2. **Test real interfaces** - Not mocks
3. **Skip until implemented** - Use `pytest.mark.skipif`
4. **Run pre-commit** - Before and after implementation with explicit flags

### Test Categories (by resource cost)

```bash
pixi run pytest -m "unit"                    # Fastest - no dependencies
pixi run pytest -m "unit or mock_llm"        # Fast - mocked LLMs
pixi run pytest -m "integration"             # Medium - real components
pixi run pytest -m "performance"             # Slow - resource intensive
```

### Test Organization

- `tests/unit/` - Pure functionality, no external deps
- `tests/integration/` - Multiple components working together
- `tests/e2e/` - End-to-end workflows
- Never create test files in project root

## File Organization

### Strict Rules

- **Never create files in project root** - Use appropriate subdirectories
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **Scripts**: `scripts/`, `scripts/temp/`, `scripts/debug/`
- **Utilities**: `scripts/utils/`, `tests/fixtures/`

## Defensive Programming

### Critical vs Optional Dependencies

**Critical dependencies** (pynwb, h5py) - **Fail fast with clear errors**
**Optional dependencies** (visualization) - Graceful degradation OK

```python
# ✅ Critical dependency check
try:
    import pynwb
except ImportError:
    raise ImportError(
        "pynwb is required for NWB quality assessment. "
        "Install with: pixi add pynwb"
    )

# ❌ Never return misleading results for missing critical deps
```

## Shell Commands

### Python -c Quoting

**Always use single quotes for outer command, double quotes inside:**

```bash
# ✅ Correct
pixi run python -c 'print("Hello World")'
pixi run python -c 'import sys; print(sys.version)'

# ❌ Wrong
pixi run python -c "print('Hello World')"
```

## Quick Reference

### Daily Commands

```bash
# Quality workflow
pixi run pre-commit -- --all-files           # Before committing (all files)
pixi run pre-commit                          # Before committing (staged files only)
pixi run format                              # Fix formatting
pixi run lint                                # Check linting

# Testing workflow
pixi run pytest -m "unit" --no-cov -x       # Fast tests, stop on first failure
pixi run pytest tests/unit/test_file.py -v  # Specific test file

# Development workflow
pixi shell                                   # Interactive environment
pixi run python -c 'import pkg; pkg.test()' # Quick Python commands
```

### Troubleshooting

- **Import errors**: Check `pixi list`, run `pixi install`, never use PYTHONPATH
- **Pre-commit fails**: Read errors, run `pixi run format`, fix manually, retry
  with `pixi run pre-commit -- --all-files`
- **Pre-commit arguments**: Use `--` separator for pre-commit flags:
  `pixi run pre-commit -- --files file.py`
- **Test failures**: Use `-v` for verbose, `-x` to stop on first failure, `-s`
  for print output

### IDE Setup (VS Code)

```json
{
  "python.formatting.provider": "ruff",
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "python.defaultInterpreterPath": "./.pixi/envs/default/bin/python"
}
```

Remember: **Pixi manages everything, pre-commit enforces quality, tests drive
design.**
