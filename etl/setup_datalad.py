#!/usr/bin/env python3
"""
DataLad Setup Script for ETL Directory

This script initializes DataLad configuration and sets up the ETL directory
structure for data management and provenance tracking.
"""

import logging
from pathlib import Path
from typing import Any, Optional

# DataLad imports with availability check
try:
    import datalad.api as dl

    DATALAD_AVAILABLE = True
except ImportError:
    DATALAD_AVAILABLE = False
    dl = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataLadETLSetup:
    """Setup class for DataLad integration in ETL directory."""

    def __init__(self, etl_path: Optional[Path] = None):
        """Initialize setup with ETL directory path."""
        if not DATALAD_AVAILABLE:
            raise ImportError(
                "DataLad is not available. Install with: pip install datalad"
            )

        self.etl_path = etl_path or Path(__file__).parent
        self.project_root = self.etl_path.parent

        logger.info(f"Initializing DataLad setup for ETL directory: {self.etl_path}")

    def setup_etl_dataset(self) -> bool:
        """
        Set up the main ETL dataset structure.

        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Check if project root is already a DataLad dataset
            if not (self.project_root / ".datalad").exists():
                logger.info("Creating DataLad dataset at project root")
                dl.create(dataset=self.project_root, annex=True)
            else:
                logger.info("Project root is already a DataLad dataset")

            # Ensure ETL subdirectories exist
            self._create_etl_structure()

            # Configure git-annex for large files
            self._configure_annex()

            # Set up subdatasets for major ETL components
            self._setup_subdatasets()

            # Save initial setup
            dl.save(
                dataset=self.project_root,
                path="etl/",
                message="Initialize ETL directory structure with DataLad",
            )

            logger.info("ETL DataLad setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup ETL dataset: {e}")
            return False

    def _create_etl_structure(self) -> None:
        """Create ETL directory structure."""
        directories = [
            "input-data",
            "workflows",
            "evaluation-data",
            "prompt-input-data",
        ]

        for directory in directories:
            dir_path = self.etl_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")

    def _configure_annex(self) -> None:
        """Configure git-annex settings for ETL data."""
        try:
            # Set up .gitattributes for large file handling
            gitattributes_path = self.etl_path / ".gitattributes"

            gitattributes_content = """
# DataLad ETL Configuration
# Large files (>10MB) go to git-annex
* annex.largefiles=((mimeencoding=binary)and(largerthan=10MB))

# Always track these files in git (not annex)
*.md !annex.largefiles
*.txt !annex.largefiles
*.py !annex.largefiles
*.yaml !annex.largefiles
*.yml !annex.largefiles
*.json !annex.largefiles
*.toml !annex.largefiles
*.cfg !annex.largefiles
*.ini !annex.largefiles

# Workflow and configuration files
workflows/**/*.py !annex.largefiles
workflows/**/*.yaml !annex.largefiles
workflows/**/*.json !annex.largefiles

# Small test fixtures
evaluation-data/test-fixtures/**/* !annex.largefiles

# Documentation
**/README.md !annex.largefiles
"""

            with open(gitattributes_path, "w") as f:
                f.write(gitattributes_content.strip())

            logger.info("Configured git-annex settings")

        except Exception as e:
            logger.error(f"Failed to configure git-annex: {e}")

    def _setup_subdatasets(self) -> None:
        """Set up subdatasets for major ETL components."""
        # Note: This would typically install external subdatasets
        # For now, we'll just document the structure

        subdatasets_info = {
            "input-data/catalystneuro-conversions": {
                "description": "CatalystNeuro conversion repositories",
                "type": "external_collection",
            },
            "evaluation-data": {
                "description": "Evaluation and test datasets",
                "type": "internal_collection",
            },
            "workflows": {
                "description": "ETL workflow definitions",
                "type": "internal_code",
            },
        }

        # Create subdataset info file
        info_path = self.etl_path / "subdatasets_info.json"
        import json

        with open(info_path, "w") as f:
            json.dump(subdatasets_info, f, indent=2)

        logger.info("Created subdataset information file")

    def install_catalystneuro_conversions(self, repos: Optional[list] = None) -> bool:
        """
        Install CatalystNeuro conversion repositories as subdatasets.

        Args:
            repos: List of repository names to install (None for default set)

        Returns:
            True if installation successful, False otherwise
        """
        if repos is None:
            # Default set of important conversion repositories
            repos = ["IBL-to-nwb", "buzsaki-lab-to-nwb", "allen-oephys-to-nwb"]

        base_url = "https://github.com/catalystneuro"
        conversions_path = self.etl_path / "input-data" / "catalystneuro-conversions"

        success_count = 0
        for repo in repos:
            try:
                repo_url = f"{base_url}/{repo}"
                local_path = conversions_path / repo

                logger.info(f"Installing {repo} from {repo_url}")

                dl.install(dataset=self.project_root, path=local_path, source=repo_url)

                success_count += 1
                logger.info(f"Successfully installed {repo}")

            except Exception as e:
                logger.error(f"Failed to install {repo}: {e}")

        logger.info(f"Installed {success_count}/{len(repos)} conversion repositories")
        return success_count == len(repos)

    def create_evaluation_datasets(self) -> bool:
        """Create structure for evaluation datasets."""
        try:
            eval_path = self.etl_path / "evaluation-data"

            # Create subdirectories
            subdirs = [
                "synthetic-messy-datasets",
                "benchmark-datasets",
                "edge-case-datasets",
                "validation-datasets",
                "test-fixtures",
            ]

            for subdir in subdirs:
                subdir_path = eval_path / subdir
                subdir_path.mkdir(parents=True, exist_ok=True)

                # Create placeholder README if it doesn't exist
                readme_path = subdir_path / "README.md"
                if not readme_path.exists():
                    readme_content = f"# {subdir.replace('-', ' ').title()}\n\nPlaceholder for {subdir} datasets.\n"
                    with open(readme_path, "w") as f:
                        f.write(readme_content)

            logger.info("Created evaluation dataset structure")
            return True

        except Exception as e:
            logger.error(f"Failed to create evaluation datasets: {e}")
            return False

    def verify_setup(self) -> dict[str, Any]:
        """
        Verify DataLad setup is working correctly.

        Returns:
            Dictionary with verification results
        """
        results = {
            "datalad_available": DATALAD_AVAILABLE,
            "project_is_dataset": False,
            "etl_structure_exists": False,
            "annex_configured": False,
            "subdatasets_info": False,
        }

        try:
            # Check if project root is DataLad dataset
            if (self.project_root / ".datalad").exists():
                results["project_is_dataset"] = True

            # Check ETL structure
            required_dirs = ["input-data", "workflows", "evaluation-data"]
            if all((self.etl_path / d).exists() for d in required_dirs):
                results["etl_structure_exists"] = True

            # Check annex configuration
            if (self.etl_path / ".gitattributes").exists():
                results["annex_configured"] = True

            # Check subdatasets info
            if (self.etl_path / "subdatasets_info.json").exists():
                results["subdatasets_info"] = True

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            results["error"] = str(e)

        return results


def main():
    """Main setup function."""
    logger.info("Starting DataLad ETL setup")

    # Initialize setup
    setup = DataLadETLSetup()

    # Run setup
    if setup.setup_etl_dataset():
        logger.info("Basic ETL dataset setup completed")
    else:
        logger.error("ETL dataset setup failed")
        return 1

    # Create evaluation datasets structure
    if setup.create_evaluation_datasets():
        logger.info("Evaluation datasets structure created")
    else:
        logger.error("Failed to create evaluation datasets structure")

    # Verify setup
    verification = setup.verify_setup()
    logger.info(f"Setup verification: {verification}")

    # Optionally install CatalystNeuro conversions
    # Uncomment the following lines to install conversion repositories
    # if setup.install_catalystneuro_conversions():
    #     logger.info("CatalystNeuro conversions installed")
    # else:
    #     logger.warning("Some CatalystNeuro conversions failed to install")

    logger.info("DataLad ETL setup completed")
    return 0


if __name__ == "__main__":
    exit(main())
