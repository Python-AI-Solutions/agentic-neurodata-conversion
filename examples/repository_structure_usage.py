#!/usr/bin/env python3
"""Example usage of DataLad repository structure management."""

from pathlib import Path

from agentic_neurodata_conversion.data_management.repository_structure import (
    DataLadRepositoryManager,
    TestDatasetManager,
)


def main():
    """Demonstrate repository structure management."""
    print("DataLad Repository Structure Management Example")
    print("=" * 50)

    # Initialize repository manager
    repo_manager = DataLadRepositoryManager(base_path=".")

    print("1. Setting up directory structure...")
    # This will create the ETL directory structure if it doesn't exist
    repo_manager._setup_directory_structure(None)

    print("2. Configuring git attributes...")
    # This will create/update .gitattributes for proper file handling
    repo_manager._configure_git_attributes(None)

    print("3. Initializing test dataset manager...")
    dataset_manager = TestDatasetManager(repo_manager)

    print("4. Listing available datasets...")
    datasets = dataset_manager.get_available_datasets()
    print(f"Found {len(datasets)} datasets:")
    for dataset in datasets:
        print(f"  - {dataset['name']}: {dataset['description']}")

    print("\n5. Directory structure created:")
    etl_path = Path("etl")
    if etl_path.exists():
        for item in etl_path.iterdir():
            if item.is_dir():
                print(f"  etl/{item.name}/")
                readme_path = item / "README.md"
                if readme_path.exists():
                    print("    └── README.md")

    print("\n6. Git attributes configured:")
    gitattributes_path = Path(".gitattributes")
    if gitattributes_path.exists():
        print("  .gitattributes file created with proper annexing rules")
        print("  - Development files stay in git")
        print("  - Large data files (>10MB) are annexed")
        print("  - NWB files are always annexed")

    print("\nRepository structure setup complete!")


if __name__ == "__main__":
    main()
