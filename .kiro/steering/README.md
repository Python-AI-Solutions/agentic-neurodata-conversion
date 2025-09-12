# Steering Documentation

Concise development guidelines optimized for agentic usage.

## Files

- **`development-essentials.md`** - Core workflow, environment, quality standards
- **`testing-guide.md`** - TDD methodology, test categories, commands
- **`pre-commit-guide.md`** - Pre-commit workflow and common fixes
- **`defensive-programming.md`** - Fail-fast principles, dependency handling
- **`file-organization.md`** - Project structure rules
- **`python-command-quoting.md`** - Shell command quoting for `python -c`

## Quick Start

```bash
pixi install && pixi run setup-hooks                    # Setup
pixi run pre-commit run --all-files                     # Quality checks
pixi run pytest -m "unit" --no-cov                      # Fast tests
```

## Key Principles

- **Pixi-only** - Never system Python/PYTHONPATH
- **Pre-commit enforcement** - All code must pass checks
- **TDD** - Write failing tests first, test real interfaces  
- **Fail fast** - Clear errors for missing critical deps
- **Organized structure** - Never create files in project root

## Optimization

Reduced from 12 verbose files to 6 concise guides (~80% content reduction) while preserving all essential guidance for agent consumption.
