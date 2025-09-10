# File Organization Guidelines

## Test and Script File Placement

### Never Create Files in Root Directory

**CRITICAL RULE**: Never create test files, throwaway scripts, or temporary files in the project root directory.

### Proper File Locations

#### Test Files
- **Unit tests**: Place in `tests/unit/`
- **Integration tests**: Place in `tests/integration/`
- **End-to-end tests**: Place in `tests/e2e/`
- **Test utilities**: Place in `tests/fixtures/` or `tests/utils/`

#### Scripts and Utilities
- **Development scripts**: Place in `scripts/`
- **Build scripts**: Place in `scripts/build/`
- **Deployment scripts**: Place in `scripts/deploy/`
- **Utility scripts**: Place in `scripts/utils/`

#### Temporary or Throwaway Files
- **Quick test scripts**: Place in `scripts/temp/` or `scripts/debug/`
- **Integration verification**: Add to appropriate test directory
- **Manual testing**: Create in `scripts/manual_testing/`

### Examples

#### ❌ WRONG - Files in root directory
```
project_root/
├── test_something.py          # NEVER DO THIS
├── debug_script.py            # NEVER DO THIS
├── temp_verification.py       # NEVER DO THIS
└── quick_test.py              # NEVER DO THIS
```

#### ✅ CORRECT - Proper organization
```
project_root/
├── tests/
│   ├── unit/
│   │   └── test_logging_integration.py
│   └── integration/
│       └── test_full_workflow.py
├── scripts/
│   ├── debug/
│   │   └── debug_logging.py
│   ├── temp/
│   │   └── verify_integration.py
│   └── utils/
│       └── test_helpers.py
```

### When Creating Files

1. **Always ask**: "Where should this file go?"
2. **Consider the purpose**:
   - Is it a test? → `tests/` directory
   - Is it a script? → `scripts/` directory
   - Is it temporary? → `scripts/temp/` or appropriate test directory
3. **Create directories if needed**: Use `mkdir -p` to create directory structure
4. **Follow naming conventions**: Use descriptive names that indicate purpose

### Directory Creation

If the appropriate directory doesn't exist, create it:

```bash
# Create test directories
mkdir -p tests/unit tests/integration tests/e2e

# Create script directories  
mkdir -p scripts/temp scripts/debug scripts/utils

# Create specific subdirectories as needed
mkdir -p scripts/manual_testing
```

### Cleanup

- Remove temporary files after use
- Don't commit throwaway scripts unless they provide ongoing value
- Use `.gitignore` patterns for temporary directories if needed

## Benefits

1. **Clean root directory**: Keeps project root uncluttered
2. **Easy navigation**: Files are where developers expect them
3. **Better organization**: Related files are grouped together
4. **Maintainability**: Easier to find and manage files
5. **Professional appearance**: Project looks well-organized