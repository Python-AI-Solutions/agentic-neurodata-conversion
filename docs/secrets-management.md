# Secrets Management

This document explains how to handle secrets detection and false positives in
the Agentic Neurodata Converter project.

## Overview

The project uses `detect-secrets` to prevent accidental commits of sensitive
information like API keys, passwords, and tokens. However, configuration files
often contain field names that trigger false positives.

## Current Configuration

### Files Involved

- `.secrets.baseline` - Baseline file containing known false positives
- `.pre-commit-config.yaml` - Pre-commit hook configuration (currently commented
  out)
- `scripts/manage_secrets.py` - Helper script for managing secrets detection

### False Positives Identified

The following are known false positives that have been baselined:

1. **Configuration field names**: `api_key_header` in config files
2. **Test data**: Base64 encoded data in HTML result files
3. **Generated files**: Content in the `results/` directory

## Setup Instructions

### Option 1: Enable Full Secrets Detection (Recommended for Production)

1. **Install detect-secrets**:

   ```bash
   pip install detect-secrets
   # or
   pixi add detect-secrets
   ```

2. **Enable pre-commit hook**: Uncomment the detect-secrets section in
   `.pre-commit-config.yaml`:

   ```yaml
   # Secret detection
   - repo: https://github.com/Yelp/detect-secrets
     rev: v1.4.0
     hooks:
       - id: detect-secrets
         args: ["--baseline", ".secrets.baseline"]
         exclude: ^(results/.*|.*\.lock|.*\.log|.*\.html)$
   ```

3. **Update baseline**:

   ```bash
   detect-secrets scan --baseline .secrets.baseline
   ```

4. **Audit baseline** (review all flagged items):
   ```bash
   detect-secrets audit .secrets.baseline
   ```

### Option 2: Manual Secrets Review (Current Setup)

The current setup has secrets detection disabled in pre-commit but provides:

- Baseline file for reference
- Management script for handling false positives
- Documentation of known issues
- Exclusion patterns for generated files

## Managing False Positives

### Using the Management Script

Run the helper script to check current status:

```bash
pixi run python scripts/manage_secrets.py
```

### Manual Baseline Updates

1. **Scan for new secrets**:

   ```bash
   detect-secrets scan --baseline .secrets.baseline
   ```

2. **Review and audit**:

   ```bash
   detect-secrets audit .secrets.baseline
   ```

3. **Mark as false positive**: During audit, press 'n' for false positives

### Inline Allowlist Comments

For configuration files, you can add inline comments:

```json
{
  "api_key_header": "X-API-Key" // pragma: allowlist secret
}
```

## Best Practices

### For Developers

1. **Never commit real secrets**: Use environment variables or external secret
   management
2. **Use placeholder values**: In configuration files, use obvious placeholders
3. **Review baseline changes**: When the baseline is updated, review what was
   added
4. **Test locally**: Run secrets detection before pushing changes

### For Configuration Files

1. **Use descriptive placeholders**:

   ```json
   {
     "api_key": "your-api-key-here",
     "database_password": "REPLACE_WITH_ACTUAL_PASSWORD"
   }
   ```

2. **Document secret requirements**: In README files, document what secrets are
   needed

3. **Provide example files**: Create `.example` versions of config files with
   placeholders

### For CI/CD

1. **Use GitHub Secrets**: Store real secrets in GitHub repository secrets
2. **Environment-specific configs**: Use different config files for different
   environments
3. **Validate in CI**: Run secrets detection as part of CI pipeline

## Troubleshooting

### Common Issues

1. **"detect-secrets command not found"**:
   - Install detect-secrets: `pip install detect-secrets`
   - Or add to pixi dependencies: `pixi add detect-secrets`

2. **Pre-commit hook fails**:
   - Check if baseline file exists: `.secrets.baseline`
   - Update baseline: `detect-secrets scan --baseline .secrets.baseline`
   - Audit new findings: `detect-secrets audit .secrets.baseline`

3. **Too many false positives**:
   - Add exclusion patterns to `.pre-commit-config.yaml`
   - Use inline allowlist comments
   - Update baseline file

### Debug Commands

```bash
# Check current baseline status
pixi run python scripts/manage_secrets.py

# Validate pre-commit configuration
pixi run pre-commit validate-config

# Test secrets detection manually
detect-secrets scan config/

# Show baseline contents
cat .secrets.baseline | jq .
```

## Security Considerations

### What Gets Detected

- API keys and tokens
- Database passwords
- Private keys and certificates
- High entropy strings (potential passwords)
- AWS access keys
- GitHub tokens
- JWT tokens

### What Doesn't Get Detected

- Secrets in environment variables (good practice)
- Secrets in external secret management systems
- Encrypted secrets
- Secrets in files excluded by `.gitignore`

### Recommendations

1. **Use environment variables**: For all runtime secrets
2. **Use secret management**: For production deployments
3. **Rotate secrets regularly**: Don't rely on detection alone
4. **Audit access**: Review who has access to secrets
5. **Monitor usage**: Track secret usage in logs (without logging the secrets)

## Integration with CI/CD

The secrets detection is integrated into the CI/CD pipeline through:

1. **Pre-commit hooks**: Prevent commits with secrets
2. **GitHub Actions**: Run detection in CI pipeline
3. **Security scanning**: Regular vulnerability assessments
4. **Baseline management**: Automated baseline updates

See `.github/workflows/quality-checks.yml` for the CI implementation.

## Further Reading

- [detect-secrets documentation](https://github.com/Yelp/detect-secrets)
- [GitHub Secrets documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Insufficient_Cryptography)
