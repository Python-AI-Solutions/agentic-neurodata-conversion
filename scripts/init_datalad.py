#!/usr/bin/env python
# Copyright (c) 2025 Agentic Neurodata Conversion Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Initialize DataLad dataset with proper configuration to avoid annexing development files"""

import os

import datalad.api as dl


def init_datalad_dataset():
    """Initialize DataLad dataset with text2git configuration"""

    # Create dataset with text2git configuration
    print("Initializing DataLad dataset with text2git configuration...")
    dl.create(
        path=".",
        cfg_proc="text2git",
        description="Agentic neurodata conversion project",
        force=True,
    )
    print("DataLad dataset created successfully")

    # Save all files
    print("Saving all project files...")
    dl.save(
        dataset=".",
        message="Initial commit: Agentic neurodata conversion project with proper git-annex configuration",
        recursive=True,
    )
    print("All files saved successfully")

    # Verify configuration
    print("\nVerifying file status (should NOT be symlinks):")
    test_files = ["README.md", "CLAUDE.md", "pixi.toml", ".gitattributes"]
    all_good = True

    for fname in test_files:
        if os.path.exists(fname):
            is_link = os.path.islink(fname)
            status = "SYMLINK (ERROR!)" if is_link else "regular file (OK)"
            print(f"  {fname}: {status}")
            if is_link:
                all_good = False

    if all_good:
        print("\n✓ All development files are properly tracked in git (not annex)")
    else:
        print("\n✗ ERROR: Some files are in annex. Check .gitattributes configuration")

    return all_good


if __name__ == "__main__":
    success = init_datalad_dataset()
    exit(0 if success else 1)
