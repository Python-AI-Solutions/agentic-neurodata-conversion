---
inclusion: always
---

# Never Use PYTHONPATH with Pixi

## Critical Rule: PYTHONPATH is Forbidden

**NEVER manipulate PYTHONPATH when using pixi.** Pixi handles all dependency
management automatically.

## Why PYTHONPATH is Harmful with Pixi

### 1. Breaks Environment Isolation

```bash
# ❌ WRONG - breaks pixi's isolation
export PYTHONPATH="/some/path:$PYTHONPATH"
pixi run python script.py

# ✅ CORRECT - let pixi handle everything
pixi run python script.py
```

### 2. Causes Import Conflicts

- PYTHONPATH can cause imports from wrong environments
- Leads to version conflicts between packages
- Makes debugging extremely difficult
- Breaks reproducibility across systems

### 3. Masks Real Issues

- Hides missing dependencies that should be in pixi.toml
- Prevents proper dependency resolution
- Makes the project non-portable

## What Pixi Does Instead

Pixi automatically handles:

- **Package discovery** through proper conda/pip installation
- **Import resolution** via pypi-dependencies with `editable = true`
- **Environment isolation** without path manipulation
- **Dependency management** through declared dependencies in pixi.toml

## Correct Approaches

### For Package Imports

```python
# ❌ WRONG - manual path manipulation
import sys
sys.path.insert(0, '/path/to/package')
import my_package

# ❌ WRONG - PYTHONPATH manipulation
import os
os.environ['PYTHONPATH'] = '/path/to/package'

# ✅ CORRECT - declare dependency in pixi.toml
# Then just import normally:
import my_package
```

### For Local Development

```bash
# ❌ WRONG - manual PYTHONPATH
export PYTHONPATH=".:$PYTHONPATH"
python script.py

# ❌ WRONG - manual pip install
pip install -e .

# ✅ CORRECT - declare in pixi.toml and use pixi
# In pixi.toml: agentic-neurodata-conversion = { path = ".", editable = true }
pixi run python script.py
```

### For Testing

```python
# ❌ WRONG - test-time path manipulation
import sys
sys.path.insert(0, '../src')
import agentic_neurodata_conversion

# ✅ CORRECT - rely on pixi environment
import agentic_neurodata_conversion  # Works automatically
```

## Troubleshooting Import Issues

### If imports fail, DO NOT use PYTHONPATH. Instead

1. **Check if package is properly installed:**

   ```bash
   pixi list | grep package-name
   ```

2. **Verify editable install:**

   ```bash
   pixi run pip show agentic-neurodata-conversion
   ```

3. **Reinstall if needed:**

   ```bash
   rm -rf .pixi
   pixi install
   ```

4. **Add missing dependencies:**

   ```bash
   pixi add missing-package
   ```

## Common Mistakes to Avoid

### ❌ Setting PYTHONPATH in scripts

```bash
#!/bin/bash
export PYTHONPATH=".:$PYTHONPATH"  # NEVER DO THIS
pixi run python script.py
```

### ❌ Setting PYTHONPATH in activation scripts

```bash
# In scripts/activate.sh
export PYTHONPATH="$CONDA_PREFIX:$PYTHONPATH"  # NEVER DO THIS
```

### ❌ Setting PYTHONPATH in test configuration

```python
# In conftest.py or test files
import os
os.environ['PYTHONPATH'] = '/some/path'  # NEVER DO THIS
```

### ❌ Setting PYTHONPATH in CI/CD

```yaml
# In GitHub Actions or other CI
- name: Set PYTHONPATH # NEVER DO THIS
  run: export PYTHONPATH=".:$PYTHONPATH"
```

## Correct Solutions

### ✅ For local packages

Add to `pixi.toml` (this is the correct pixi way):

```toml
[pypi-dependencies]
my-local-package = { path = "./path/to/package", editable = true }
```

This is how our project is configured:

```toml
[pypi-dependencies]
agentic-neurodata-conversion = { path = ".", editable = true }
```

### ✅ For development dependencies

```bash
pixi add --feature dev my-dev-package
```

### ✅ For test dependencies

```bash
pixi add --feature test my-test-package
```

### ✅ For CI/CD

```yaml
- name: Install with pixi
  run: pixi install

- name: Run tests
  run: pixi run test
```

## Verification

To verify your environment works without PYTHONPATH:

```bash
# Check that imports work
pixi run python -c "import agentic_neurodata_conversion; print('Success')"

# Verify no PYTHONPATH is set
pixi run python -c "import os; print('PYTHONPATH:', os.environ.get('PYTHONPATH', 'Not set'))"

# Check Python path
pixi run python -c "import sys; print('Python executable:', sys.executable)"
```

## The Correct Pixi Way for Local Development

This project follows the proper pixi approach for local package development:

```toml
# In pixi.toml
[pypi-dependencies]
agentic-neurodata-conversion = { path = ".", editable = true }
```

This tells pixi to:

1. Install the local package in editable mode automatically
2. Handle all import resolution without PYTHONPATH
3. Maintain proper environment isolation
4. Make the package available to all pixi commands

## Remember

- **Pixi manages everything** - trust it
- **PYTHONPATH breaks isolation** - never use it
- **Declare dependencies properly** - in pixi.toml
- **Use pypi-dependencies with editable=true** - for local development
- **Never use manual pip install -e** - let pixi handle it
- **Report import issues** - don't work around them with PYTHONPATH
