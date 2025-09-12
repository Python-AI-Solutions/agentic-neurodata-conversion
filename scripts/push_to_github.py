#!/usr/bin/env python
"""Push DataLad repository to GitHub"""

import subprocess
import sys

import datalad.api as dl


def push_to_github():
    """Push DataLad repository to GitHub, handling subdatasets properly"""

    print("Pushing DataLad repository to GitHub...")

    # First, push just the git part (not annex content) to GitHub
    print("\n1. Pushing main dataset to GitHub (git only, not annex content)...")
    try:
        # Push the main branch to GitHub
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error pushing to GitHub: {result.stderr}")
            return False
        print("✓ Main dataset pushed successfully")
    except Exception as e:
        print(f"Error: {e}")
        return False

    # Create a GitHub sibling for DataLad
    print("\n2. Creating DataLad GitHub sibling...")
    try:
        # This creates a sibling that tracks the GitHub remote
        dl.siblings(
            action="add",
            dataset=".",
            name="github",
            url="git@github.com:Python-AI-Solutions/agentic-neurodata-conversion.git",
            pushurl="git@github.com:Python-AI-Solutions/agentic-neurodata-conversion.git",
        )
        print("✓ GitHub sibling configured")
    except Exception as e:
        # Sibling might already exist, which is fine
        print(f"Note: {e}")

    # Push git-annex branch
    print("\n3. Pushing git-annex branch...")
    try:
        result = subprocess.run(
            ["git", "push", "origin", "git-annex"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Warning: Could not push git-annex branch: {result.stderr}")
            print("This is expected for the first push to a new repository")
        else:
            print("✓ git-annex branch pushed")
    except Exception as e:
        print(f"Warning: {e}")

    print("\n4. Subdatasets information:")
    print(
        "Note: Subdatasets (catalystneuro conversions) are registered but not pushed."
    )
    print("They remain as references to their original repositories.")
    print("This is the intended behavior for DataLad subdatasets.")

    print("\n✓ Push to GitHub completed!")
    print("\nRepository is now available at:")
    print("https://github.com/Python-AI-Solutions/agentic-neurodata-conversion")

    print("\nTo clone this repository elsewhere:")
    print(
        "datalad clone git@github.com:Python-AI-Solutions/agentic-neurodata-conversion.git"
    )

    return True


if __name__ == "__main__":
    success = push_to_github()
    sys.exit(0 if success else 1)
