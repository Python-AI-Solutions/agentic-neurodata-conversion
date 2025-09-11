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

"""
Script to install CatalystNeuro NWB conversions.
Downloads and sets up conversion repositories from the CatalystNeuro organization.

Usage: pixi run python install_catalystneuro_conversions.py [options]
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import requests

COOKIECUTTER_TEMPLATE = "cookiecutter-my-lab-to-nwb-template"


def fetch_catalystneuro_repos():
    """Fetch all CatalystNeuro repositories containing 'to-nwb' in the name."""
    print("🔍 Fetching CatalystNeuro repositories from GitHub...")

    all_repos = []
    page = 1
    per_page = 100

    while True:
        try:
            # GitHub API endpoint for organization repos
            url = "https://api.github.com/orgs/catalystneuro/repos"
            params = {"page": page, "per_page": per_page, "type": "all"}

            response = requests.get(url, params=params)

            if response.status_code == 403:
                # Rate limit hit
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                if reset_time:
                    wait_time = reset_time - int(time.time()) + 1
                    print(f"⏳ Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

            response.raise_for_status()
            repos = response.json()

            if not repos:
                break

            all_repos.extend(repos)

            # Check if there are more pages
            if len(repos) < per_page:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching repositories: {e}")
            return []

    # Filter for repos containing 'to-nwb'
    nwb_conversions = [
        repo["name"]
        for repo in all_repos
        if "to-nwb" in repo["name"].lower() and not repo["archived"]
    ]

    print(f"✅ Found {len(nwb_conversions)} active conversion repositories")

    # Sort alphabetically for consistency
    nwb_conversions.sort()

    return nwb_conversions


def check_dependencies():
    """Check if required dependencies are installed."""
    dependencies = ["git", "pixi"]
    missing = []

    for dep in dependencies:
        try:
            subprocess.run([dep, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(dep)

    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Please install them before running this script.")
        return False
    return True


def setup_datalad(base_path):
    """Initialize datalad dataset for data management."""
    print("\n📦 Setting up DataLad for data management...")

    data_path = base_path / "etl" / "input-data"

    try:
        # Check if datalad is available through pixi
        result = subprocess.run(
            ["pixi", "run", "datalad", "--version"], capture_output=True, text=True
        )

        if result.returncode == 0:
            # Initialize datalad dataset
            subprocess.run(
                ["pixi", "run", "datalad", "create", "-c", "text2git", str(data_path)],
                check=True,
            )
            print("✅ DataLad dataset initialized")
            return True
        else:
            print(
                "⚠️  DataLad not available in pixi environment, skipping initialization"
            )
            return False

    except Exception as e:
        print(f"⚠️  Could not initialize DataLad: {e}")
        return False


def clone_conversion(repo_name, target_dir, use_https=True, update_existing=False):
    """Clone a single conversion repository or update if it exists."""
    if use_https:
        url = f"https://github.com/catalystneuro/{repo_name}.git"
    else:
        url = f"git@github.com:catalystneuro/{repo_name}.git"

    target_path = Path(target_dir) / repo_name

    if target_path.exists():
        if update_existing:
            # Pull latest changes
            try:
                print(f"  🔄 Updating {repo_name}...")
                result = subprocess.run(
                    ["git", "-C", str(target_path), "pull", "--ff-only"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if "Already up to date" in result.stdout:
                    print(f"  ✅ {repo_name} is already up to date")
                else:
                    print(f"  ✅ {repo_name} updated successfully")
                return True
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️  Failed to update {repo_name}: {e}")
                return True  # Don't fail the whole process
        else:
            # Skip existing repos when not updating
            return "existing"

    try:
        print(f"  📥 Cloning new repository: {repo_name}...")
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(target_path)],
            check=True,
            capture_output=True,
        )
        return "new"
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to clone {repo_name}: {e}")
        return False


def install_conversion_dependencies(conversion_path):
    """Install dependencies for a conversion if it has requirements."""
    requirements_files = [
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "environment.yml",
    ]

    for req_file in requirements_files:
        req_path = conversion_path / req_file
        if req_path.exists():
            if req_file == "requirements.txt":
                try:
                    subprocess.run(
                        ["pixi", "run", "pip", "install", "-r", str(req_path)],
                        check=True,
                        capture_output=True,
                    )
                    return True
                except subprocess.CalledProcessError:
                    pass
            elif req_file == "setup.py":
                try:
                    subprocess.run(
                        ["pixi", "run", "pip", "install", "-e", str(conversion_path)],
                        check=True,
                        capture_output=True,
                    )
                    return True
                except subprocess.CalledProcessError:
                    pass
    return False


def create_conversion_summary(base_path):
    """Create a summary JSON file of all installed conversions."""
    conversions_dir = base_path / "etl" / "input-data" / "catalystneuro-conversions"
    summary = {"total_conversions": 0, "conversions": []}

    for item in conversions_dir.iterdir():
        if item.is_dir() and item.name.endswith("-to-nwb"):
            conversion_info = {
                "name": item.name,
                "path": str(item),
                "has_requirements": (item / "requirements.txt").exists(),
                "has_setup": (item / "setup.py").exists(),
                "has_pyproject": (item / "pyproject.toml").exists(),
            }
            summary["conversions"].append(conversion_info)

    summary["total_conversions"] = len(summary["conversions"])

    summary_path = base_path / "conversions_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n📊 Summary saved to {summary_path}")
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Install CatalystNeuro NWB conversions"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Base path for the project (default: current directory)",
    )
    parser.add_argument(
        "--use-ssh",
        action="store_true",
        help="Use SSH instead of HTTPS for git cloning",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Try to install dependencies for each conversion",
    )
    parser.add_argument(
        "--conversions",
        nargs="+",
        help="Specific conversions to install (default: all)",
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="Fetch all 'to-nwb' repos from CatalystNeuro GitHub",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing repositories with latest changes",
    )

    args = parser.parse_args()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    base_path = args.base_path
    # Updated path to match current structure
    conversions_dir = base_path / "etl" / "input-data" / "catalystneuro-conversions"

    # Ensure directory exists
    conversions_dir.mkdir(parents=True, exist_ok=True)

    # Setup DataLad if available
    setup_datalad(base_path)

    # Determine which conversions to install
    if args.conversions:
        conversions_to_install = args.conversions
    elif args.fetch_all:
        conversions_to_install = fetch_catalystneuro_repos()
        if not conversions_to_install:
            print("❌ No conversions found or error fetching from GitHub")
            sys.exit(1)
    else:
        # Default: fetch from GitHub
        conversions_to_install = fetch_catalystneuro_repos()
        if not conversions_to_install:
            print("❌ No conversions found or error fetching from GitHub")
            sys.exit(1)

    print(f"\n🚀 Processing {len(conversions_to_install)} CatalystNeuro conversions...")
    if args.update:
        print("📊 Mode: Update existing and add new repositories")
    else:
        print("📊 Mode: Add new repositories only (skip existing)")
    print(f"📁 Target directory: {conversions_dir}\n")

    # Track statistics
    stats = {"new": [], "existing": [], "updated": [], "failed": []}

    # Clone cookiecutter template first
    print("📋 Processing cookiecutter template...")
    result = clone_conversion(
        COOKIECUTTER_TEMPLATE,
        conversions_dir,
        use_https=not args.use_ssh,
        update_existing=args.update,
    )
    if result == "new":
        stats["new"].append(COOKIECUTTER_TEMPLATE)
    elif result == "existing":
        stats["existing"].append(COOKIECUTTER_TEMPLATE)
        print(f"  ✓ {COOKIECUTTER_TEMPLATE} already exists")
    elif result:  # Updated
        stats["updated"].append(COOKIECUTTER_TEMPLATE)
    elif not result:
        stats["failed"].append(COOKIECUTTER_TEMPLATE)

    print("\n📥 Processing conversion repositories...")
    for repo_name in conversions_to_install:
        result = clone_conversion(
            repo_name,
            conversions_dir,
            use_https=not args.use_ssh,
            update_existing=args.update,
        )

        if result == "new":
            stats["new"].append(repo_name)

            if args.install_deps:
                conversion_path = conversions_dir / repo_name
                if install_conversion_dependencies(conversion_path):
                    print(f"  ✅ Installed dependencies for {repo_name}")
        elif result == "existing":
            stats["existing"].append(repo_name)
            print(f"  ✓ {repo_name} already exists")
        elif result:  # Updated
            stats["updated"].append(repo_name)
        elif not result:
            stats["failed"].append(repo_name)

    # Create summary
    summary = create_conversion_summary(base_path)

    # Print results
    print("\n" + "=" * 50)
    print("📊 Installation Summary:")
    print("=" * 50)

    if stats["new"]:
        print(f"✨ New repositories installed: {len(stats['new'])}")
        if len(stats["new"]) <= 10:
            for repo in stats["new"]:
                print(f"   - {repo}")

    if stats["existing"]:
        print(f"✓ Existing repositories (skipped): {len(stats['existing'])}")

    if stats["updated"]:
        print(f"🔄 Repositories updated: {len(stats['updated'])}")
        if len(stats["updated"]) <= 10:
            for repo in stats["updated"]:
                print(f"   - {repo}")

    if stats["failed"]:
        print(f"❌ Failed operations: {len(stats['failed'])}")
        for repo in stats["failed"]:
            print(f"   - {repo}")

    print(f"\n📁 Conversions directory: {conversions_dir}")
    print(f"📊 Total conversions available: {summary['total_conversions']}")

    # Print next steps based on what happened
    print("\n📝 Next steps:")
    if stats["new"]:
        print(
            "1. Review the new conversions in etl/input-data/catalystneuro-conversions/"
        )
        print("2. Install neuroconv: pixi run pip install neuroconv")
        print("3. Explore specific conversion examples")
    else:
        print("1. All conversions are up to date!")
        print("2. Run with --update flag to pull latest changes")
        print("3. Check GitHub periodically for new conversions")

    if not args.update:
        print("\n💡 Tip: Run with --update flag to update existing repositories")


if __name__ == "__main__":
    main()
