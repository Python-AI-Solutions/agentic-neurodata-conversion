---
inclusion: always
---

# Development Workflow with Pixi

## Project Setup

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd agentic-neurodata-conversion

# Install all dependencies (including dev and test features)
pixi install

# Verify installation
pixi run python --version
pixi list
```

### Environment Activation

```bash
# For interactive development
pixi shell

# For running single commands
pixi run <command>
```

## Development Commands

### Code Quality

```bash
# Lint code
pixi run lint

# Format code
pixi run format

# Type checking
pixi run type-check

# Run all quality checks
pixi run lint && pixi run format && pixi run type-check
```

### Testing

```bash
# Run all tests
pixi run test

# Run with coverage
pixi run test-cov

# Run specific test types
pixi run test-unit
pixi run test-integration
pixi run test-e2e
pixi run test-fast

# Run tests in parallel
pixi run test-parallel

# Run performance tests
pixi run test-benchmark
```

### Server Development

```bash
# Run production server
pixi run run-server

# Run development server with reload
pixi run run-server-dev
```

### Documentation

```bash
# Serve documentation locally
pixi run docs-serve

# Build documentation
pixi run docs-build
```

### Utility Tasks

```bash
# Clean build artifacts
pixi run clean

# Install pre-commit hooks
pixi run pre-commit-install

# Run pre-commit on all files
pixi run pre-commit-run
```

## Adding Dependencies

### Runtime Dependencies

```bash
# Add a new runtime dependency
pixi add numpy>=1.24.0

# Add with specific version
pixi add "pydantic>=2.0.0,<3.0.0"
```

### Development Dependencies

```bash
# Add development dependency
pixi add --feature dev black

# Add test dependency
pixi add --feature test pytest-xdist
```

### Checking Dependencies

```bash
# List all installed packages
pixi list

# Show dependency tree
pixi tree

# Check for updates
pixi update --dry-run
```

## Python Execution

### Running Scripts

```bash
# Run Python scripts
pixi run python script.py
pixi run python -m module_name

# Run with arguments
pixi run python script.py --arg1 value1 --arg2 value2
```

### Interactive Python

```bash
# Start Python REPL
pixi run python

# Start IPython (if installed)
pixi run ipython

# Start Jupyter
pixi run jupyter notebook
```

## Environment Management

### Environment Information

```bash
# Show environment info
pixi info

# Show environment path
pixi run python -c "import sys; print(sys.executable)"

# Show installed packages location
pixi run python -c "import site; print(site.getsitepackages())"
```

### Environment Cleanup

```bash
# Remove environment and reinstall
rm -rf .pixi
pixi install

# Update all dependencies
pixi update
```

## IDE Configuration

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./.pixi/envs/default/bin/python",
  "python.terminal.activateEnvironment": false,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff"
}
```

### PyCharm

1. Go to Settings → Project → Python Interpreter
2. Add New Interpreter → Existing Environment
3. Select `.pixi/envs/default/bin/python`

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Check if package is installed
pixi list | grep package_name

# Add missing package
pixi add package_name

# Reinstall environment (DO NOT modify PYTHONPATH)
rm -rf .pixi && pixi install

# Verify local package is available (via pypi-dependencies editable=true)
pixi run python -c "import agentic_neurodata_conversion; print('Local package imports work')"
```

#### PYTHONPATH Issues

**If you see PYTHONPATH-related problems:**

```bash
# NEVER do this - it breaks pixi isolation
# export PYTHONPATH=/some/path:$PYTHONPATH  # ❌ WRONG

# Instead, ensure proper pixi installation
pixi install                                # ✅ CORRECT
pixi run python -c "import sys; print(sys.path)"  # Check paths

# If imports still fail, check if local package is installed
pixi run pip show agentic-neurodata-conversion
```

#### Version Conflicts

```bash
# Check dependency conflicts
pixi tree

# Update specific package
pixi update package_name

# Check for available versions
pixi search package_name
```

#### Environment Issues

```bash
# Verify pixi environment is active
pixi run which python

# Check environment variables
pixi run env | grep CONDA

# Reset environment
rm -rf .pixi
pixi install
```

### Performance Issues

```bash
# Use parallel installation
pixi install --parallel

# Clear cache
pixi clean cache

# Use local solver
pixi install --solver=local
```

## Best Practices

1. **Always use pixi commands**: Never use system Python or pip directly
2. **Keep pixi.toml updated**: All dependencies should be declared
3. **Use pixi tasks**: Prefer predefined tasks over manual commands
4. **Never manipulate PYTHONPATH**: Pixi handles imports automatically
5. **Test in clean environment**: Regularly test with fresh `pixi install`
6. **Document new tasks**: Add new development tasks to pixi.toml
7. **Version pin important deps**: Pin versions for critical dependencies
8. **Use features for organization**: Separate dev, test, and docs dependencies
9. **Trust pixi's dependency resolution**: No manual path management needed

## Git Integration

### Pre-commit Setup

```bash
# Install pre-commit hooks
pixi run pre-commit-install

# Run on all files
pixi run pre-commit-run

# Update hooks
pixi run pre-commit autoupdate
```

### Ignore Files

Ensure `.gitignore` includes:

```
.pixi/
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/
```

## Continuous Integration

For CI/CD, use pixi in your workflows:

```yaml
# GitHub Actions example
- name: Setup Pixi
  uses: prefix-dev/setup-pixi@v0.4.1

- name: Install dependencies
  run: pixi install

- name: Run tests
  run: pixi run test-cov

- name: Run linting
  run: pixi run lint
```
