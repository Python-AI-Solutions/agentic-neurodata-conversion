---
inclusion: always
---

# Defensive Programming

## Core Principle

**Fail fast and clearly** - Don't provide misleading results when critical dependencies are missing.

## Dependencies

**Critical** (fail immediately): `pynwb`, `h5py`, validation libraries
**Optional** (graceful degradation): visualization, export formats, performance optimizations

## Patterns

```python
# ❌ WRONG - Misleading results
try:
    import pynwb
except ImportError:
    return 0.8, []  # DANGEROUS

# ✅ CORRECT - Fail fast with clear message
try:
    import pynwb
except ImportError:
    raise ImportError("pynwb required. Install: pixi add pynwb")

# ✅ Custom error class
class MissingDependencyError(Exception):
    def __init__(self, dep: str, cmd: str):
        super().__init__(f"{dep} missing. Install: {cmd}")
```

## Dependency Checking

```python
def check_critical_dependencies():
    missing = []
    
    try:
        import pynwb
    except ImportError:
        missing.append(("pynwb", "pixi add pynwb"))
    
    try:
        import h5py  
    except ImportError:
        missing.append(("h5py", "pixi add h5py"))
    
    if missing:
        deps = ", ".join([dep for dep, _ in missing])
        cmds = "\n".join([f"  {cmd}" for _, cmd in missing])
        raise MissingDependencyError(
            f"Missing: {deps}\nInstall:\n{cmds}\nRun: pixi run <command>"
        )
```

## NWB Quality Assessment

**Critical deps**: `pynwb`, `h5py`, `numpy` - Without these, results are meaningless

**Requirements**:
1. Check deps at initialization
2. Clear error messages with fix instructions  
3. No partial functionality
4. Document requirements

## Testing Missing Dependencies

```python
def test_missing_dep_raises_error():
    with patch.dict('sys.modules', {'pynwb': None}):
        with pytest.raises(ImportError, match="pynwb required"):
            QualityAssessmentEngine()

def test_with_dep_works():
    # Normal functionality test
    pass
```

## Error Message Template

```python
f"Cannot {functionality} without {dependency}. "
f"Required for {reason}. "
f"Install: pixi add {dependency}"
```

## When to Use Graceful Degradation

**Only for optional features**: visualization, export formats, performance optimizations, UI enhancements
**Never for core functionality** that affects correctness

## Checklist

- [ ] Identify critical vs optional deps
- [ ] Check deps at initialization  
- [ ] Clear error messages with pixi commands
- [ ] Test success and failure scenarios
- [ ] Document requirements
- [ ] Ensure pixi.toml includes critical deps

**Key**: Better to fail clearly than succeed misleadingly. Users trust quality assessment results for important decisions.
