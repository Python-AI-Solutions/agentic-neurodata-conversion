# CI/CD Configuration

This directory contains the complete CI/CD pipeline configuration for the
Agentic Neurodata Converter project.

## Workflows

### Core CI Pipeline (`ci.yml`)

**Triggers**: Push to `main`/`develop`, Pull Requests to `main`

**Jobs**:

- **Test**: Multi-version Python testing (3.9, 3.10, 3.11)
- **Lint**: Code quality checks with ruff and mypy
- **Build**: Package building and installation verification
- **Security**: Security analysis with bandit

**Key Features**:

- Pixi-based dependency management
- Coverage reporting to Codecov
- Artifact uploads for build outputs

### Quality Checks (`quality-checks.yml`)

**Triggers**: Push to `main`/`develop`, Pull Requests to `main`

**Jobs**:

- **Code Quality**: Formatting, linting, type checking, security analysis
- **Documentation**: Link checking, configuration validation
- **Dependency Check**: Vulnerability scanning with safety

### Extended Testing (`test-extended.yml`)

**Triggers**: Nightly schedule, Manual dispatch

**Jobs**:

- **Extended Tests**: Integration, performance, mock LLM, small model tests
- **Configurable**: Choose test level via workflow dispatch

### Release Pipeline (`release.yml`)

**Triggers**: Git tags matching `v*`

**Jobs**:

- **Release**: Full test suite, package building, GitHub release creation, PyPI
  publishing

### Dependency Updates (`dependency-updates.yml`)

**Triggers**: Weekly schedule (Mondays 9 AM UTC), Manual dispatch

**Jobs**:

- **Update Dependencies**: Automated pixi dependency updates with PR creation
- **Security Audit**: Weekly security vulnerability scanning

## Issue Templates

### Bug Report (`bug_report.yml`)

Structured bug reporting with:

- Component selection
- Environment details
- Reproduction steps
- Log output capture

### Feature Request (`feature_request.yml`)

Feature suggestion template with:

- Problem description
- Solution proposal
- Priority assessment
- Use case documentation

### Question (`question.yml`)

Support template with:

- Documentation check verification
- Category selection
- Context gathering

### Configuration (`config.yml`)

- Disables blank issues
- Provides links to documentation and discussions

## Pull Request Template

Comprehensive PR template including:

- Change type classification
- Component impact assessment
- Testing verification
- Documentation requirements
- Breaking change documentation

## Pre-commit Configuration

### Hooks Included

1. **Basic File Checks**:
   - Trailing whitespace removal
   - End-of-file fixing
   - YAML/JSON/TOML validation
   - Merge conflict detection
   - Large file prevention

2. **Python Code Quality**:
   - Ruff linting with auto-fix
   - Ruff formatting
   - MyPy type checking

3. **Security**:
   - Bandit security analysis
   - Secret detection with detect-secrets

4. **Documentation**:
   - Markdown linting with auto-fix

5. **Custom Hooks**:
   - Configuration file validation
   - Pixi lock file verification
   - Fast test execution (pre-push)

### Pre-commit.ci Integration

- Auto-fixes applied to PRs
- Weekly dependency updates
- Configurable skip options

## Development Workflow

### Setup (One-time)

```bash
pixi install
pixi run python scripts/setup_hooks.py
```

### Daily Development

```bash
# Before making changes
pixi run pre-commit

# Fast feedback loop
pixi run pytest tests/unit/ --no-cov -x

# Before committing
pixi run pre-commit
pixi run pytest tests/unit/ tests/integration/
```

### Quality Assurance

```bash
# Full quality check
pixi run pre-commit run --all-files

# Security audit
pixi run bandit -r agentic_neurodata_conversion/

# Configuration validation
pixi run python scripts/validate_config.py
```

## CI/CD Features

### Automated Quality Gates

1. **Pre-commit Enforcement**: All code must pass pre-commit checks
2. **Multi-version Testing**: Python 3.9, 3.10, 3.11 compatibility
3. **Security Scanning**: Automated vulnerability detection
4. **Coverage Tracking**: Code coverage monitoring with Codecov
5. **Dependency Management**: Automated updates with testing

### Performance Optimizations

1. **Pixi Caching**: Fast dependency installation
2. **Parallel Jobs**: Concurrent execution where possible
3. **Selective Testing**: Different test categories for different triggers
4. **Artifact Caching**: Build artifact reuse across jobs

### Security Measures

1. **Secret Scanning**: Prevent credential leaks
2. **Dependency Auditing**: Regular vulnerability checks
3. **Code Analysis**: Static security analysis with bandit
4. **Automated Updates**: Security patch automation

### Release Automation

1. **Semantic Versioning**: Tag-based release triggers
2. **Automated Building**: Package creation and validation
3. **Multi-target Publishing**: GitHub Releases and PyPI
4. **Release Notes**: Automated changelog generation

## Monitoring and Alerts

### Success Metrics

- Test pass rates across Python versions
- Code coverage trends
- Security vulnerability counts
- Dependency freshness

### Failure Handling

- Detailed error reporting in CI logs
- Artifact preservation for debugging
- Automatic issue creation for security vulnerabilities
- PR creation for dependency updates

## Customization

### Adding New Workflows

1. Create `.yml` file in `.github/workflows/`
2. Follow existing patterns for pixi integration
3. Add appropriate triggers and jobs
4. Test with workflow dispatch before merging

### Modifying Pre-commit Hooks

1. Update `.pre-commit-config.yaml`
2. Test locally with `pixi run pre-commit run --all-files`
3. Consider impact on development workflow
4. Document changes in this README

### Issue Template Updates

1. Modify YAML files in `.github/ISSUE_TEMPLATE/`
2. Test template rendering in GitHub UI
3. Update links and references as needed
4. Consider user experience and information gathering needs

## Troubleshooting

### Common Issues

1. **Pixi Environment**: Ensure all commands use `pixi run`
2. **Pre-commit Failures**: Run `pixi run pre-commit run --all-files` locally
3. **Test Failures**: Use `-v` flag for verbose output, `-x` to stop on first
   failure
4. **Dependency Issues**: Check `pixi list` and run `pixi install`

### Debug Commands

```bash
# Validate workflows locally
pixi run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"

# Test pre-commit configuration
pixi run pre-commit validate-config

# Check configuration files
pixi run python scripts/validate_config.py

# Verify package building
pixi run python -m build
```

This CI/CD configuration provides a robust, automated development and deployment
pipeline that ensures code quality, security, and reliability while maintaining
developer productivity.
