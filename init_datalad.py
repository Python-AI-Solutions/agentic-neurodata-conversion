#!/usr/bin/env python
"""Initialize DataLad dataset with proper configuration"""

import datalad.api as dl

# Create dataset with text2git configuration
print('Initializing DataLad dataset with text2git configuration...')
result = dl.create(
    path='.',
    cfg_proc='text2git',
    description='LLM-guided conversion project',
    force=True
)
print('DataLad dataset created successfully')

# Save all files
print('Saving all project files...')
dl.save(
    dataset='.',
    message='Initial commit: LLM-guided conversion project with proper git-annex configuration',
    recursive=True
)
print('All files saved successfully')

# Verify configuration
print('\nVerifying file status (should NOT be symlinks):')
import os
for fname in ['README.md', 'CLAUDE.md', 'pixi.toml', '.gitattributes']:
    if os.path.exists(fname):
        is_link = os.path.islink(fname)
        print(f'  {fname}: {"SYMLINK (ERROR!)" if is_link else "regular file (OK)"}')