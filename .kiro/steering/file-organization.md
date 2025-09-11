---
inclusion: always
---

# File Organization

## Critical Rule

**Never create files in the project root directory.**

## Proper Locations

### Tests

- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/e2e/` - End-to-end tests
- `tests/fixtures/` - Test utilities

### Scripts

- `scripts/` - Development scripts
- `scripts/temp/` - Temporary/throwaway scripts
- `scripts/debug/` - Debug utilities
- `scripts/utils/` - Utility scripts

## Examples

### ❌ Wrong - Root Directory

```
project_root/
├── test_something.py          # NEVER
├── debug_script.py            # NEVER
└── temp_verification.py       # NEVER
```

### ✅ Correct - Organized

```
project_root/
├── tests/unit/test_component.py
├── tests/integration/test_workflow.py
├── scripts/temp/verify_integration.py
└── scripts/debug/debug_logging.py
```

## Quick Setup

```bash
# Create directories as needed
mkdir -p tests/{unit,integration,e2e,fixtures}
mkdir -p scripts/{temp,debug,utils}
```

## Decision Guide

- **Is it a test?** → `tests/` directory
- **Is it a script?** → `scripts/` directory
- **Is it temporary?** → `scripts/temp/`
- **Is it for debugging?** → `scripts/debug/`

**Benefits**: Clean root, easy navigation, professional organization.
