---
inclusion: always
---

# Pixi Local Development Best Practices

## The Correct Pixi Way

This project follows the **official pixi approach** for local package development as documented in the [pixi Python tutorial](https://pixi.sh/latest/python/tutorial/).

### Local Package Configuration

```toml
# In pixi.toml - this is the CORRECT way
[pypi-dependencies]
agentic-neurodata-conversion = { path = ".", editable = true }
```

This single line tells pixi to:
- Install the local package in editable mode
- Handle all import resolution automatically
- Maintain proper environment isolation
- Make the package available to all pixi commands

### What This Replaces

```bash
# ❌ WRONG - manual pip commands
pip install -e .
pip install -e .[dev]

# ❌ WRONG - PYTHONPATH manipulation
export PYTHONPATH=".:$PYTHONPATH"

# ❌ WRONG - sys.path manipulation
import sys
sys.path.insert(0, '.')
```

### How It Works

When you run `pixi install`, pixi automatically:
1. Reads the `pypi-dependencies` section
2. Installs the local package with `editable = true`
3. Sets up proper import paths within the environment
4. Ensures the package is available to all tasks

### Verification

```bash
# Check that the package is installed
pixi run pip show agentic-neurodata-conversion

# Verify imports work
pixi run python -c "import agentic_neurodata_conversion; print('Success')"

# Check installation location
pixi run python -c "import agentic_neurodata_conversion; print(agentic_neurodata_conversion.__file__)"
```

## Development Workflow

### 1. Initial Setup
```bash
git clone <repo>
cd agentic-neurodata-conversion
pixi install  # Automatically handles local package
```

### 2. Development
```bash
# Edit code in agentic_neurodata_conversion/
# Changes are immediately available (editable install)

pixi run python -m agentic_neurodata_conversion.some_module
pixi run pytest tests/
```

### 3. No Manual Steps Needed
- No `pip install -e .` required
- No PYTHONPATH manipulation needed
- No sys.path modifications required
- Just edit code and run with `pixi run`

## Task Configuration

Our pixi tasks are simplified because the package is always available:

```toml
# Simple tasks - no setup dependencies needed
dev = "python -m agentic_neurodata_conversion.mcp_server --reload --debug"
server = "python -m agentic_neurodata_conversion.mcp_server"
test = "pytest tests/ -v --no-cov"
```

## Common Mistakes to Avoid

### ❌ Don't Add Manual Setup Tasks
```toml
# WRONG - not needed with pixi
setup = "pip install -e ."
setup-dev = "pip install -e .[dev]"
```

### ❌ Don't Use Task Dependencies for Local Package
```toml
# WRONG - creates unnecessary complexity
server = { cmd = "python -m app.server", depends-on = ["setup"] }

# CORRECT - package is always available
server = "python -m app.server"
```

### ❌ Don't Manipulate Python Path
```bash
# WRONG - breaks pixi isolation
export PYTHONPATH=".:$PYTHONPATH"
pixi run python script.py

# CORRECT - trust pixi
pixi run python script.py
```

## Benefits of This Approach

1. **Simplicity**: One line in pixi.toml handles everything
2. **Consistency**: Same approach across all environments
3. **Isolation**: No global Python path pollution
4. **Reliability**: No manual setup steps to forget
5. **Portability**: Works the same on all systems
6. **Official**: Follows pixi documentation exactly

## Troubleshooting

### If imports fail:
1. Check pixi.toml has the local package declared
2. Run `pixi install` to ensure proper setup
3. Verify with `pixi run pip show <package-name>`
4. Never resort to PYTHONPATH manipulation

### If package changes aren't reflected:
- With `editable = true`, changes should be immediate
- If not, try `pixi install` to refresh
- Check that you're using `pixi run` commands

## References

- [Pixi Python Tutorial](https://pixi.sh/latest/python/tutorial/)
- [Pixi PyPI Dependencies](https://pixi.sh/latest/reference/pypi_dependencies/)
- [Pixi Project Configuration](https://pixi.sh/latest/reference/project_configuration/)