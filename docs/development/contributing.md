# Contributing Guidelines

This document outlines the contribution process and guidelines for the agentic neurodata conversion project.

## Getting Started

1. **Fork the repository** and clone your fork
2. **Set up the development environment** following `setup.md`
3. **Create a feature branch** from `develop`
4. **Make your changes** following the coding standards
5. **Test your changes** thoroughly
6. **Submit a pull request**

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature development branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Critical production fixes

### Branch Naming

```bash
# Feature branches
git checkout -b feature/mcp-tool-enhancement
git checkout -b feature/agent-optimization

# Bug fixes
git checkout -b bugfix/conversion-error-handling
git checkout -b bugfix/memory-leak-fix

# Hotfixes
git checkout -b hotfix/critical-security-patch
```

## Code Standards

### Quality Checks

All code must pass these checks before submission:

```bash
# Run all quality checks
pixi run pre-commit run --all-files

# Individual checks
pixi run format      # Auto-format code
pixi run lint        # Check linting
pixi run type-check  # Type checking
```

### Code Style

- **Line length**: 88 characters (Black default)
- **Import organization**: Use `ruff` for import sorting
- **Type hints**: Required for all public functions
- **Docstrings**: Required for all public classes and functions

```python
# ✅ Good example
def process_dataset(
    dataset_path: str,
    output_format: str = "nwb"
) -> Dict[str, Any]:
    """
    Process a dataset and convert to specified format.

    Args:
        dataset_path: Path to the input dataset
        output_format: Target output format (default: "nwb")

    Returns:
        Dictionary containing processing results and metadata

    Raises:
        ValueError: If dataset_path is invalid
        ProcessingError: If conversion fails
    """
    # Implementation here
    pass
```

### Testing Requirements

- **Unit tests** required for all new functionality
- **Integration tests** for MCP tools and agent interactions
- **Test coverage** should not decrease
- **Tests must pass** in CI pipeline

```python
# Test naming convention
def test_mcp_tool_registration():
    """Test that MCP tools register correctly."""
    pass

def test_agent_dataset_analysis_success():
    """Test successful dataset analysis by conversation agent."""
    pass

def test_conversion_error_handling():
    """Test proper error handling during conversion."""
    pass
```

## MCP Server Development

### Adding New Tools

1. **Create the tool function** with proper decorator
2. **Add comprehensive tests** (unit and integration)
3. **Update documentation** in `docs/api/`
4. **Add usage examples** in `docs/examples/`

```python
# Example tool implementation
@mcp.tool(
    name="new_analysis_tool",
    description="Performs new type of dataset analysis"
)
async def new_analysis_tool(
    dataset_path: str,
    analysis_type: str = "standard",
    server=None
) -> Dict[str, Any]:
    """Implementation with proper error handling."""
    pass
```

### Agent Development

1. **Inherit from BaseAgent** for consistency
2. **Implement required methods** according to interface
3. **Add configuration options** to agent config
4. **Register in MCP server** initialization

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Code passes quality checks
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] No merge conflicts with target branch

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
```

### Review Process

1. **Automated checks** must pass (CI pipeline)
2. **Code review** by at least one maintainer
3. **Testing verification** in review environment
4. **Documentation review** for completeness
5. **Approval and merge** by maintainer

## Issue Reporting

### Bug Reports

Use the bug report template and include:
- **Environment details** (OS, Python version, pixi version)
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Error messages and logs**
- **Minimal reproduction case**

### Feature Requests

Use the feature request template and include:
- **Use case description** and motivation
- **Proposed solution** or approach
- **Alternative solutions** considered
- **Impact assessment** on existing functionality

## Documentation

### Required Documentation

- **API documentation** for new MCP tools
- **Architecture documentation** for significant changes
- **Usage examples** for new features
- **Migration guides** for breaking changes

### Documentation Standards

- **Clear and concise** language
- **Code examples** with expected output
- **Cross-references** to related documentation
- **Version information** for API changes

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** - Breaking changes
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] Release notes prepared
- [ ] Tagged release created

## Community Guidelines

- **Be respectful** and inclusive
- **Provide constructive feedback** in reviews
- **Help newcomers** get started
- **Share knowledge** through documentation and examples
- **Follow the code of conduct**

## Getting Help

- **Documentation** - Check existing docs first
- **Issues** - Search existing issues before creating new ones
- **Discussions** - Use GitHub Discussions for questions
- **Code review** - Ask for specific feedback in PR comments
