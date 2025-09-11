# Defensive Programming Guidelines

## Core Principle

**Fail fast and fail clearly** rather than providing misleading results. When
critical dependencies are missing, the system should refuse to operate rather
than provide degraded functionality that could mislead users.

## Critical Dependencies vs Optional Dependencies

### Critical Dependencies

Dependencies that are **essential** for core functionality should cause
**immediate failure** when missing:

- `pynwb` for NWB file analysis and quality assessment
- `h5py` for HDF5 file operations
- Core validation libraries for data integrity checks
- Schema validation tools for compliance checking

### Optional Dependencies

Only truly **optional** features should gracefully degrade:

- Visualization libraries for optional charts
- Export formats that are convenience features
- Performance optimization libraries with fallbacks

## Implementation Patterns

### ❌ WRONG - Dangerous Graceful Degradation

```python
try:
    import pynwb
except ImportError:
    logger.warning("pynwb not available, using default scores")
    return 0.8, []  # DANGEROUS - misleading result
```

### ✅ CORRECT - Defensive Programming

```python
try:
    import pynwb
except ImportError:
    raise ImportError(
        "pynwb is required for NWB quality assessment. "
        "Install with: pixi add pynwb"
    )
```

### ✅ CORRECT - Clear Error Messages

```python
class MissingDependencyError(Exception):
    """Raised when a critical dependency is missing."""

    def __init__(self, dependency: str, install_command: str):
        super().__init__(
            f"Critical dependency '{dependency}' is missing. "
            f"This functionality cannot work without it. "
            f"Install with: {install_command}"
        )
```

## Pixi Integration

Since we use pixi for dependency management, missing dependencies typically
indicate:

1. **Incorrect pixi usage** - User not running commands with `pixi run`
2. **Missing dependency declaration** - Package not declared in `pyproject.toml`
3. **Environment issues** - Pixi environment not properly activated

### Error Messages Should Guide Users

```python
def check_critical_dependencies():
    """Check that all critical dependencies are available."""
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
        commands = "\n".join([f"  {cmd}" for _, cmd in missing])

        raise MissingDependencyError(
            f"Critical dependencies missing: {deps}\n"
            f"Install with:\n{commands}\n"
            f"Then run your command with: pixi run <command>"
        )
```

## Quality Assessment Specific Rules

### NWB Quality Assessment Requirements

For NWB file quality assessment, these dependencies are **CRITICAL**:

- `pynwb` - Required for reading NWB files and assessing data integrity
- `h5py` - Required for low-level HDF5 operations
- `numpy` - Required for data analysis

**Without these, quality assessment results are meaningless and dangerous.**

### Implementation Requirements

1. **Check dependencies at initialization** - Fail immediately if missing
2. **Provide clear error messages** - Tell users exactly how to fix the issue
3. **No partial functionality** - Don't provide misleading "partial" assessments
4. **Document requirements clearly** - Make dependency requirements obvious

## Testing with Missing Dependencies

### Test Both Scenarios

```python
def test_missing_pynwb_raises_error():
    """Test that missing pynwb raises clear error."""
    with patch.dict('sys.modules', {'pynwb': None}):
        with pytest.raises(ImportError, match="pynwb is required"):
            QualityAssessmentEngine()

def test_with_pynwb_works():
    """Test that with pynwb, assessment works properly."""
    # Normal functionality test
    pass
```

## Error Message Standards

### Good Error Messages Include

1. **What's missing** - Specific dependency name
2. **Why it's needed** - What functionality requires it
3. **How to fix it** - Exact pixi command to run
4. **Context** - Mention pixi environment usage

### Example Template

```python
f"Cannot perform {functionality} without {dependency}. "
f"This dependency is required for {reason}. "
f"Install with: pixi add {dependency} "
f"Then run with: pixi run {command}"
```

## Benefits of Defensive Programming

1. **Prevents Silent Failures** - Users know immediately when something is wrong
2. **Guides Correct Usage** - Error messages teach proper pixi usage
3. **Maintains Data Integrity** - No misleading quality scores
4. **Improves Reliability** - System behavior is predictable
5. **Easier Debugging** - Clear error messages speed up problem resolution

## When to Use Graceful Degradation

Only use graceful degradation for truly optional features:

- **Visualization** - Charts and plots for convenience
- **Export Formats** - Additional output formats beyond core JSON/text
- **Performance Optimizations** - Faster algorithms with slower fallbacks
- **UI Enhancements** - Better user experience features

**Never use graceful degradation for core functionality that affects
correctness.**

## Implementation Checklist

- [ ] Identify critical vs optional dependencies
- [ ] Add dependency checks at module/class initialization
- [ ] Write clear error messages with pixi commands
- [ ] Test both success and failure scenarios
- [ ] Document dependency requirements clearly
- [ ] Ensure pixi.toml includes all critical dependencies

## Remember

**It's better to fail clearly than to succeed misleadingly.**

Users trust quality assessment results to make important decisions about their
data. Providing inaccurate assessments due to missing dependencies can lead to:

- Publishing low-quality data
- Missing critical data integrity issues
- False confidence in conversion quality
- Wasted time debugging "good" data that's actually problematic

Always choose defensive programming over graceful degradation for core
functionality.
