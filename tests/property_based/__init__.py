"""
Property-based testing module.

Uses Hypothesis for automated test case generation.

Hypothesis is installed via pixi.toml dependencies.

To run property-based tests (excluded from default test run):
    pixi run python -m pytest "test scripts/property_based/" -v --no-cov

Note: Use 'python -m pytest' instead of 'pytest' to ensure hypothesis plugin loads correctly.

These tests are excluded from the default test suite because:
1. They test invariant properties rather than code coverage
2. They generate hundreds of random test cases which can be slow
3. Coverage metrics don't apply to property-based testing patterns
"""
