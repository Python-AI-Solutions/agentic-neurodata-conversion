# Requirements Document

## Introduction

The current pre-commit configuration has been degraded through recent changes,
removing important security checks, downgrading tool versions, and adding
problematic hooks that slow down the development workflow. We need to restore a
comprehensive, fast, and flexible pre-commit setup that maintains code quality
while supporting efficient development.

## Requirements

### Requirement 1: Comprehensive Code Quality Checks

**User Story:** As a developer, I want pre-commit to catch common issues
automatically, so that I can maintain high code quality without manual checking.

#### Acceptance Criteria

1. WHEN pre-commit runs THEN it SHALL check for trailing whitespace, end-of-file
   issues, and file formatting
2. WHEN pre-commit runs THEN it SHALL validate YAML, JSON, and TOML syntax
3. WHEN pre-commit runs THEN it SHALL check for merge conflicts and case
   conflicts
4. WHEN pre-commit runs THEN it SHALL detect large files (>1MB) to prevent
   accidental commits
5. WHEN pre-commit runs THEN it SHALL verify executable files have proper
   shebangs

### Requirement 2: Python Code Quality and Security

**User Story:** As a developer, I want automated Python code quality and
security checks, so that I can catch issues early in development.

#### Acceptance Criteria

1. WHEN pre-commit runs THEN it SHALL use the latest stable version of ruff for
   linting and formatting
2. WHEN pre-commit runs THEN it SHALL automatically fix safe issues with ruff
3. WHEN pre-commit runs THEN it SHALL detect private keys and AWS credentials
4. WHEN pre-commit runs THEN it SHALL check for debug statements in production
   code
5. WHEN pre-commit runs THEN it SHALL validate test file naming conventions

### Requirement 3: Documentation and File Consistency

**User Story:** As a developer, I want consistent documentation and file
formatting, so that the codebase remains professional and readable.

#### Acceptance Criteria

1. WHEN pre-commit runs THEN it SHALL format YAML, JSON, and Markdown files
   consistently
2. WHEN pre-commit runs THEN it SHALL check for common spelling errors
3. WHEN pre-commit runs THEN it SHALL strip Jupyter notebook outputs
4. WHEN pre-commit runs THEN it SHALL validate shell scripts with shellcheck
5. WHEN pre-commit runs THEN it SHALL fix mixed line endings to LF

### Requirement 4: Flexible Command Interface

**User Story:** As a developer, I want flexible pre-commit commands that support
different workflows, so that I can run appropriate checks for different
situations.

#### Acceptance Criteria

1. WHEN I run `pixi run pre-commit` THEN it SHALL run on staged files only
   (default git behavior)
2. WHEN I run `pixi run pre-commit -- --all-files` THEN it SHALL run on all
   files in the repository
3. WHEN I run `pixi run pre-commit -- --files file1.py file2.py` THEN it SHALL
   run only on specified files
4. WHEN I run `pixi run pre-commit-update` THEN it SHALL update all hook
   versions to latest
5. WHEN pre-commit fails THEN it SHALL provide clear error messages with fix
   suggestions

### Requirement 5: Performance and Exclusions

**User Story:** As a developer, I want pre-commit to run quickly and skip
irrelevant files, so that my development workflow remains efficient.

#### Acceptance Criteria

1. WHEN pre-commit runs THEN it SHALL exclude generated directories like
   `results/`, `mvp-example/`, `.pixi/`
2. WHEN pre-commit runs THEN it SHALL exclude lock files, logs, and HTML files
   from secret detection
3. WHEN pre-commit runs THEN it SHALL NOT run expensive operations like full
   test suites by default
4. WHEN pre-commit runs THEN it SHALL complete basic checks in under 30 seconds
   for typical changes
5. WHEN pre-commit runs THEN it SHALL support parallel execution where possible

### Requirement 6: Integration with Development Tools

**User Story:** As a developer, I want pre-commit to integrate well with our
pixi-based development environment, so that all tools work together seamlessly.

#### Acceptance Criteria

1. WHEN pre-commit runs custom hooks THEN it SHALL use `pixi run` commands for
   consistency
2. WHEN pre-commit validates configuration THEN it SHALL check our JSON config
   files
3. WHEN pre-commit runs THEN it SHALL respect our Python version constraints
   (3.12+)
4. WHEN pre-commit runs THEN it SHALL work with our editable package
   installation
5. WHEN pre-commit runs THEN it SHALL integrate with our CI/CD pipeline
   requirements
