# constitution.md

## Core Philosophy
- **Fail fast, fail clearly** – never provide misleading results.  
- **Pixi is law** – all installs, runs, and commands must go through `pixi`.  
- **Tests drive design** – quality enforced by TDD, pre-commit, and CI.  
- **Clean structure, professional organization** – no clutter in project root.  

---

## Dependencies & Defensive Programming
- **Critical deps** (fail immediately): `pynwb`, `h5py`, `numpy`  
- **Optional deps** (graceful degradation): visualization, export, performance  
- Always raise clear errors with **pixi install instructions**.  
- Never allow partial/incorrect functionality.  

```python
raise ImportError("pynwb required. Install: pixi add pynwb")
```

---

## Development Essentials
- **No `summary.md` files**.  
- **Never use system Python or PYTHONPATH** – always `pixi run <command>`.  
- All code must pass:
  ```bash
  pixi run pre-commit run --all-files
  ```

### Daily Workflow
```bash
pixi install && pixi run setup-hooks      # One-time setup
pixi run pre-commit run --all-files       # Quality checks
pixi run pytest -m "unit" --no-cov        # Fast tests
pixi run format && pixi run lint          # Fix issues
```

---

## File Organization
- **Never create files in project root**.  
- Tests: `tests/{unit,integration,e2e,fixtures}`  
- Scripts: `scripts/{temp,debug,utils}`.  
- Decision Guide:  
  - Test → `tests/`  
  - Script → `scripts/`  
  - Temporary → `scripts/temp/`  
  - Debugging → `scripts/debug/`  

---

## Pre-commit Rules
- Run hooks with:
  ```bash
  pixi run setup-hooks
  pixi run pre-commit run --all-files
  ```
- **Auto-fixed**: whitespace, imports, formatting (88 chars), YAML/JSON.  
- **Manual fixes**: unused args/imports, long lines, code simplifications.  
- Use underscore prefix `_unused` for ignored params.  

---

## Python Command Quoting
- **Always**: single quotes outside, double quotes inside.  
  ```bash
  pixi run python -c 'print("Hello")'
  ```
- For complex code, create a script in `scripts/temp/`.  

---

## Testing Rules
### TDD Principles
1. Write failing tests first.  
2. Test **real interfaces**, fail fast if missing.  
3. Tests guide design decisions.  

### Categories
- Unit (`@pytest.mark.unit`) – highest priority  
- Integration, performance, LLM-specific (`mock_llm`, `small_model`, etc.)  

### Commands
```bash
pixi run test-agent       # Minimal for agents/CI
pixi run test-unit        # Unit tests only
pixi run test-verbose     # Standard output
pixi run test-debug       # Debug with pdb
pixi run test-ci          # CI pipeline
```

### Patterns
- Prefix unused params with `_`.  
- Use `pixi` for subprocesses, never system Python.  
- Expected exceptions must be explicitly tested.  

---

## Constitution Checklist
- [ ] Identify and enforce critical vs optional dependencies  
- [ ] Use only `pixi` for installs, runs, tests  
- [ ] Keep root directory clean  
- [ ] Pass pre-commit before commit  
- [ ] Quote correctly in `python -c`  
- [ ] Write failing tests first, organize by cost  

---

**Key Principle**:  
Better to fail clearly than succeed misleadingly.  
Pixi manages everything, pre-commit enforces quality, and tests define design.  
