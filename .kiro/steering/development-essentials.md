---
inclusion: always
---

# Development Essentials

## Core Rules

- **No summary documents** - Don't create `summary.md` files
- **Always use `pixi run <command>`** - Never system Python or PYTHONPATH
- **All code must pass `pre-commit run --all-files`**

## Setup & Daily Commands

```bash
# One-time setup
pixi install && pixi run setup-hooks

# Daily workflow  
pixi run pre-commit run --all-files     # Quality checks
pixi run pytest -m "unit" --no-cov     # Fast tests
pixi run format && pixi run lint        # Fix issues
```

## Code Patterns

```python
# ✅ Unused parameters - prefix with underscore
def test_func(_config, items): pass

# ✅ Line breaks at 88 chars
def long_function_name(
    param1, param2, param3
): pass
```

## Testing

**TDD**: Write failing tests first, test real interfaces, fail fast

```bash
pixi run pytest -m "unit"              # Fastest
pixi run pytest -m "integration"       # Medium  
pixi run pytest -m "performance"       # Slow
```

**Organization**: `tests/unit/`, `tests/integration/`, `tests/e2e/` - never in root

## File Organization

**Never create files in project root**
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Scripts: `scripts/`, `scripts/temp/`, `scripts/debug/`

## Shell Commands

**Python -c quoting**: Single quotes outside, double inside
```bash
pixi run python -c 'print("Hello")'  # ✅
pixi run python -c "print('Hello')"  # ❌
```

## Quick Reference

```bash
# Quality
pixi run pre-commit run --all-files     # All files
pixi run format && pixi run lint        # Fix issues

# Testing  
pixi run pytest -m "unit" --no-cov -x  # Fast, stop on failure
pixi run pytest file.py -v             # Specific file

# Development
pixi shell                              # Interactive
pixi run python -c 'code'              # Quick commands
```

## Troubleshooting

- **Import errors**: `pixi install`, never PYTHONPATH
- **Pre-commit fails**: `pixi run format`, fix manually, retry
- **Test failures**: Use `-v` verbose, `-x` stop on failure

**Key**: Pixi manages everything, pre-commit enforces quality, tests drive design.
