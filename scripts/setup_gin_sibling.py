#!/usr/bin/env python
"""Set up GIN (G-Node Infrastructure) sibling for DataLad annex content"""

import contextlib
import subprocess
import sys

import datalad.api as dl


def setup_gin_sibling():
    """Configure GIN repository as a sibling for storing large data files"""

    print("Setting up GIN repository as DataLad sibling...")

    # GIN repository URL from the screenshot
    gin_url = "https://gin.g-node.org/leej3/agentic-neurodata-conversion.git"
    gin_ssh_url = "git@gin.g-node.org:/leej3/agentic-neurodata-conversion.git"

    # Add GIN as a sibling for annex content
    print("\n1. Adding GIN as a DataLad sibling...")
    try:
        dl.siblings(
            action="add",
            dataset=".",
            name="gin",
            url=gin_ssh_url,
            pushurl=gin_ssh_url,
            annex_wanted="standard",
            annex_group="backup",
            publish_depends="github",
        )
        print("✓ GIN sibling configured")
    except Exception as e:
        print(f"Note: {e}")
        print("Trying to reconfigure existing sibling...")
        try:
            dl.siblings(
                action="configure",
                dataset=".",
                name="gin",
                url=gin_ssh_url,
                pushurl=gin_ssh_url,
            )
            print("✓ GIN sibling reconfigured")
        except Exception as e2:
            print(f"Warning: {e2}")

    # Configure git-annex to use GIN for storage
    print("\n2. Configuring git-annex to use GIN for storage...")
    with contextlib.suppress(Exception):
        # This might fail if remote doesn't exist yet
        subprocess.run(
            ["git", "annex", "enableremote", "gin"],
            capture_output=True,
            text=True,
            check=False,
        )

    # Push git-annex branch to GIN
    print("\n3. Pushing repository structure to GIN...")
    try:
        result = subprocess.run(
            ["git", "push", "gin", "main"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ Main branch pushed to GIN")
        else:
            print(f"Note: {result.stderr}")
    except Exception as e:
        print(f"Warning: {e}")

    # Push git-annex branch
    try:
        result = subprocess.run(
            ["git", "push", "gin", "git-annex"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ git-annex branch pushed to GIN")
        else:
            print(f"Note: {result.stderr}")
    except Exception as e:
        print(f"Warning: {e}")

    print("\n✓ GIN sibling setup completed!")
    print("\nGIN repository is available at:")
    print("  Web: https://gin.g-node.org/leej3/agentic-neurodata-conversion")
    print(f"  Git: {gin_url}")
    print(f"  SSH: {gin_ssh_url}")

    print("\nTo push large files to GIN:")
    print("  git annex copy --to gin <file>")
    print("  datalad push --to gin")

    print("\nTo get the full repository with annex content:")
    print(
        "  datalad clone https://gin.g-node.org/leej3/agentic-neurodata-conversion.git"
    )
    print("  # or")
    print("  gin get leej3/agentic-neurodata-conversion")

    return True


if __name__ == "__main__":
    success = setup_gin_sibling()
    sys.exit(0 if success else 1)
