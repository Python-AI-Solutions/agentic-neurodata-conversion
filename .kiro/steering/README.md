# Steering Documentation

This directory contains consolidated development guidelines for the Agentic Neurodata Conversion project.

## Files Overview

### Core Development
- **`development-essentials.md`** - Main development workflow, environment setup, code quality standards
- **`testing-guide.md`** - TDD methodology, test categories, commands, and environment setup
- **`pre-commit-guide.md`** - Pre-commit workflow, common fixes, and troubleshooting

### Specific Guidelines  
- **`defensive-programming.md`** - Fail-fast principles, dependency handling, error patterns
- **`file-organization.md`** - Project structure rules, where to place files
- **`python-command-quoting.md`** - Shell command quoting rules for `python -c`

## Quick Start

1. **Setup**: `pixi install && pixi run setup-hooks`
2. **Daily workflow**: `pixi run pre-commit && pixi run pytest -m "unit" --no-cov`
3. **Quality checks**: `pixi run format && pixi run lint`

## Key Principles

- **Pixi-only development** - Never use system Python or PYTHONPATH
- **Pre-commit enforcement** - All code must pass quality checks
- **TDD approach** - Write failing tests first, test real interfaces
- **Defensive programming** - Fail fast with clear error messages
- **Organized structure** - Never create files in project root

## Consolidation Changes

This documentation was consolidated from 12 verbose files into 6 focused guides:

**Removed redundant files:**
- `testing-methodology.md` + `testing-commands.md` → `testing-guide.md`
- `pre-commit-workflow.md` + `pre-commit-quick-fixes.md` → `pre-commit-guide.md`  
- `pixi-environment.md` + `pixi-local-development.md` + `no-pythonpath.md` + `development-workflow.md` + `coding-standards.md` → `development-essentials.md`

**Result**: 50% reduction in files, ~70% reduction in total content while maintaining all essential guidance.