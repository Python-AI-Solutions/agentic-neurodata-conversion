# Coding Standards and Style Guidelines

## Line Length Standard

**CRITICAL RULE**: Use 88 characters as the maximum line length for all Python code.

### Why 88 Characters?

- **Black compatibility**: 88 is the default line length for Black formatter
- **Readability**: Provides good balance between readability and screen real estate
- **Modern standard**: Widely adopted in the Python community
- **Tool consistency**: Works well with most editors and IDEs

### Configuration

All tools are configured to use 88 characters:

#### Ruff Configuration (pyproject.toml)
```toml
[tool.ruff]
line-length = 88
```

#### Pre-commit isort Configuration
```yaml
args: [--profile=black, --line-length=88]
```

## Code Formatting Standards

### Ruff Formatter Settings

```toml
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

### Import Sorting

- Use isort with Black profile for consistency
- Line length matches code formatting (88 characters)
- Known first-party packages: `agentic_neurodata_conversion`

## Linting Rules

### Enabled Rules
- `E`: pycodestyle errors
- `W`: pycodestyle warnings  
- `F`: pyflakes
- `I`: isort
- `B`: flake8-bugbear
- `C4`: flake8-comprehensions
- `UP`: pyupgrade
- `ARG`: flake8-unused-arguments
- `SIM`: flake8-simplify
- `TCH`: flake8-type-checking

### Ignored Rules
- `E501`: Line too long (handled by formatter)
- `B008`: Function calls in argument defaults (common pattern)
- `C901`: Too complex (handled case-by-case)
- `ARG002`: Unused method argument (common in interfaces)

## Development Workflow

### Pre-commit Integration

All formatting and linting is enforced via pre-commit hooks:

```bash
# Install hooks
pixi run pre-commit-install

# Run manually
pixi run pre-commit-run

# Format code
pixi run format

# Check linting
pixi run lint
```

### IDE Configuration

#### VS Code Settings
```json
{
  "python.formatting.provider": "ruff",
  "editor.rulers": [88],
  "python.linting.ruffEnabled": true
}
```

#### PyCharm Settings
- Code Style → Python → Right margin: 88
- Tools → External Tools → Configure Ruff

## Code Quality Standards

### Type Hints
- Use type hints for all public functions and methods
- Use `from __future__ import annotations` for forward references
- Configure mypy for strict type checking

### Docstrings
- Use NumPy style docstrings
- Document all public functions, classes, and modules
- Include parameter types and return types

### Error Handling
- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately

## Consistency Rules

1. **Always use 88 characters**: Never override line length locally
2. **Trust the formatter**: Don't manually format code that ruff handles
3. **Follow pre-commit**: All code must pass pre-commit checks
4. **Use pixi commands**: Always use `pixi run format` and `pixi run lint`
5. **No manual overrides**: Don't use `# noqa` unless absolutely necessary

## Examples

### Good Line Length Usage

```python
# ✅ GOOD - Within 88 characters
def process_neurodata_conversion(
    input_file: Path, output_file: Path, metadata: Dict[str, Any]
) -> ConversionResult:
    """Process neuroscience data conversion with proper line breaks."""
    pass

# ✅ GOOD - Proper string formatting
error_message = (
    f"Failed to convert {input_file.name} to NWB format. "
    f"Error: {error_details}"
)
```

### Avoid These Patterns

```python
# ❌ BAD - Exceeds 88 characters
def process_neurodata_conversion_with_very_long_parameter_names(input_file_path: Path, output_file_path: Path, conversion_metadata: Dict[str, Any]) -> ConversionResult:
    pass

# ❌ BAD - Long string without breaks
error_message = f"Failed to convert {input_file.name} to NWB format due to validation errors in the metadata schema"
```

## Tool Integration

### Pixi Tasks
- `pixi run format`: Format all code with ruff
- `pixi run lint`: Check code with ruff linter
- `pixi run type-check`: Run mypy type checking
- `pixi run pre-commit-run`: Run all pre-commit hooks

### CI/CD Integration
All formatting and linting checks run in CI/CD pipeline to ensure consistency across the team.

## Benefits

1. **Consistency**: All code follows the same formatting standards
2. **Readability**: 88 characters provides optimal readability
3. **Tool compatibility**: Works seamlessly with Black, ruff, and other tools
4. **Team efficiency**: No time wasted on formatting discussions
5. **Quality assurance**: Automated enforcement via pre-commit hooks

Remember: The goal is consistent, readable code that follows modern Python standards.