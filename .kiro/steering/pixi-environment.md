---
inclusion: always
---

# Pixi Environment Management

This project uses **pixi** for environment management. Never use system Python or other package managers.

## Environment Rules

### Always Use Pixi Commands
- Use `pixi run <command>` instead of direct command execution
- Use `pixi shell` to activate the environment for interactive work
- Use `pixi add <package>` to add dependencies
- Use `pixi install` to install dependencies

### Testing Commands
- **Run tests**: `pixi run test` (not `python -m pytest` or `pytest`)
- **Run with coverage**: `pixi run test-cov`
- **Run unit tests**: `pixi run test-unit`
- **Run integration tests**: `pixi run test-integration`
- **Run e2e tests**: `pixi run test-e2e`
- **Run fast tests**: `pixi run test-fast`

### Development Commands
- **Install dev dependencies**: `pixi install` (automatically installs dev feature)
- **Run linting**: `pixi run lint`
- **Run formatting**: `pixi run format`
- **Run type checking**: `pixi run type-check`
- **Start server**: `pixi run run-server`
- **Start dev server**: `pixi run run-server-dev`

### Python Execution
- **Run Python scripts**: `pixi run python <script.py>`
- **Run modules**: `pixi run python -m <module>`
- **Interactive Python**: `pixi run python` or `pixi shell` then `python`

### Package Management
- **Add runtime dependency**: `pixi add <package>`
- **Add dev dependency**: `pixi add --feature dev <package>`
- **Add test dependency**: `pixi add --feature test <package>`
- **Remove dependency**: `pixi remove <package>`

## Environment Activation

### For Interactive Work
```bash
# Activate pixi shell
pixi shell

# Now you can use python, pytest, etc. directly
python --version
pytest --version
```

### For Script Execution
```bash
# Always prefix with pixi run
pixi run python script.py
pixi run pytest tests/
pixi run mypy agentic_neurodata_conversion/
```

## Important Notes

1. **Never use system Python**: The system Python may have different versions and missing dependencies
2. **Never use pip directly**: Use `pixi add` instead of `pip install`
3. **Never use conda/mamba directly**: Pixi manages conda environments automatically
4. **Never manipulate PYTHONPATH**: Pixi handles dependency resolution automatically
5. **Always check pixi.toml**: All dependencies and tasks are defined there
6. **Use pixi tasks**: Prefer predefined tasks in pixi.toml over manual commands
7. **Trust pixi's dependency management**: No need for manual path manipulation

## Environment Verification

To verify you're using the correct environment:

```bash
# Check Python path (should be in .pixi directory)
pixi run python -c "import sys; print(sys.executable)"

# Check package locations
pixi run python -c "import pytest; print(pytest.__file__)"

# List installed packages
pixi list

# Verify no PYTHONPATH manipulation is needed
pixi run python -c "import agentic_neurodata_conversion; print('Package imports work without PYTHONPATH')"
```

## Why PYTHONPATH is Not Needed

Pixi automatically handles:
- Package discovery through proper installation
- Import resolution via pypi-dependencies with `editable = true`
- Environment isolation without path manipulation
- Dependency management through conda/pip integration

Our project uses the correct pixi approach:
```toml
[pypi-dependencies]
agentic-neurodata-conversion = { path = ".", editable = true }
```

**Never set PYTHONPATH** - it can cause:
- Import conflicts between environments
- Unpredictable behavior across systems
- Masking of actual dependency issues
- Breaking pixi's environment isolation

## Troubleshooting

### If tests fail with import errors:
1. Check if you're using `pixi run pytest` instead of direct `pytest`
2. Verify dependencies are in pixi.toml
3. Run `pixi install` to ensure all dependencies are installed
4. Use `pixi shell` for interactive debugging

### If packages are missing:
1. Add them with `pixi add <package>` or `pixi add --feature dev <package>`
2. Never use `pip install` directly
3. Never modify PYTHONPATH - pixi handles imports automatically
4. Check pixi.toml for the correct feature group

### If environment seems corrupted:
1. Remove `.pixi` directory: `rm -rf .pixi`
2. Reinstall: `pixi install`
3. Verify with: `pixi run python --version`