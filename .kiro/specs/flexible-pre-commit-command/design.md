# Design Document

## Overview

This design modifies the pixi.toml configuration to make the pre-commit command
flexible by removing hardcoded flags and allowing argument passing. The solution
is simple: change the pre-commit task definition to accept and forward arguments
directly to the pre-commit command.

## Architecture

### Current State

```toml
pre-commit = "pre-commit run --all-files"
```

### Proposed State

```toml
pre-commit = "pre-commit run"
```

This change allows pixi to pass additional arguments using the `--` separator:

- `pixi run pre-commit` → `pre-commit run`
- `pixi run pre-commit -- --all-files` → `pre-commit run --all-files`
- `pixi run pre-commit -- --files file1.py` → `pre-commit run --files file1.py`

## Components and Interfaces

### Modified Component: pixi.toml Task Definition

**Location:** `pixi.toml` file, `[tasks]` section

**Current Interface:**

```toml
pre-commit = "pre-commit run --all-files"
```

**New Interface:**

```toml
pre-commit = "pre-commit run"
```

### Command Usage Patterns

1. **Default behavior (no arguments):**

   ```bash
   pixi run pre-commit
   # Executes: pre-commit run
   ```

2. **All files (explicit):**

   ```bash
   pixi run pre-commit -- --all-files
   # Executes: pre-commit run --all-files
   ```

3. **Specific files:**

   ```bash
   pixi run pre-commit -- --files file1.py file2.py
   # Executes: pre-commit run --files file1.py file2.py
   ```

4. **Hook-specific execution:**
   ```bash
   pixi run pre-commit -- --hook-stage manual
   # Executes: pre-commit run --hook-stage manual
   ```

## Data Models

No data models are involved in this change. This is purely a configuration
modification.

## Error Handling

### Pre-commit Command Errors

- **Invalid arguments:** Pre-commit will handle invalid arguments and display
  appropriate error messages
- **Missing files:** Pre-commit will report file not found errors
- **Hook failures:** Pre-commit will report which hooks failed and why

### Pixi Argument Passing

- **Argument separator:** Users must use `--` to separate pixi arguments from
  pre-commit arguments
- **No arguments:** When no arguments are provided, pre-commit runs with its
  default behavior (staged files)

## Testing Strategy

### Manual Testing

1. **Test default behavior:**

   ```bash
   pixi run pre-commit
   ```

   Should run pre-commit on staged files (default pre-commit behavior)

2. **Test all files:**

   ```bash
   pixi run pre-commit -- --all-files
   ```

   Should run pre-commit on all files in the repository

3. **Test specific files:**

   ```bash
   pixi run pre-commit -- --files agentic_neurodata_conversion/core/config.py
   ```

   Should run pre-commit only on the specified file

4. **Test invalid arguments:**
   ```bash
   pixi run pre-commit -- --invalid-flag
   ```
   Should display pre-commit error message for invalid flag

### Documentation Updates

The following documentation files need to be updated to reflect the new usage:

- `.kiro/steering/pre-commit-guide.md` - Update command examples
- `.kiro/steering/development-essentials.md` - Update quick commands section

### Migration Notes

- **Breaking change:** Users who relied on the automatic `--all-files` behavior
  will need to explicitly add `-- --all-files`
- **Benefit:** Much more flexible pre-commit usage for all users and agents
- **Documentation:** All steering guides should be updated to show the new
  explicit usage patterns
