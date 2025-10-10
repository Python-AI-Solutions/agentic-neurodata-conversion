### CRITICAL: DataLad Repository Initialization

**IMPORTANT**: When initializing this project as a DataLad dataset, you MUST
configure git-annex properly BEFORE adding any files to avoid development files
being annexed:

1. **Set up .gitattributes FIRST** (before any DataLad operations):

```bash
# Create .gitattributes with proper annex configuration
cat > .gitattributes << 'EOF'
# Only use annex for large data files (>10MB)
* annex.backend=MD5E
**/.git* annex.largefiles=nothing

# Keep all development files in git (not annex)
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.yml annex.largefiles=nothing
*.yaml annex.largefiles=nothing
*.toml annex.largefiles=nothing
*.json annex.largefiles=nothing
*.sh annex.largefiles=nothing
*.cfg annex.largefiles=nothing
*.ini annex.largefiles=nothing
*.rst annex.largefiles=nothing
*.ipynb annex.largefiles=nothing
.gitignore annex.largefiles=nothing
.gitmodules annex.largefiles=nothing
.pre-commit-config.yaml annex.largefiles=nothing

# Default: only annex files larger than 10MB
* annex.largefiles=(largerthan=10mb)
EOF
```

2. **Initialize DataLad with text2git mode**:

```python
import datalad.api as dl

# Create dataset with text2git configuration
dl.create(
    path=".",
    cfg_proc="text2git",  # CRITICAL: Ensures text files stay in git
    description="Agentic neurodata conversion project",
    force=True
)
```

3. **Verify configuration before saving**:

```bash
# Check that development files are NOT symlinks
ls -la *.md *.toml *.py
# These should be regular files, not symlinks to .git/annex/
```
