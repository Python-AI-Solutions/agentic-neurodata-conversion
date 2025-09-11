#!/usr/bin/env python3
"""
DataLad Integration Workflow Template

This template provides standardized patterns for integrating DataLad
data management capabilities into conversion workflows.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Optional, Union

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


@dataclass
class DataLadConfig:
    """Configuration for DataLad integration."""

    dataset_path: Union[str, Path]
    enable_provenance: bool = True
    auto_save: bool = True
    save_message_template: str = "Workflow execution: {workflow_name} at {timestamp}"
    git_annex_backend: str = "SHA256E"
    create_if_missing: bool = False


@dataclass
class DataLadResult:
    """Result of DataLad operations."""

    success: bool
    dataset_path: Optional[Path] = None
    operations_performed: list[str] = None
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None

    def __post_init__(self):
        if self.operations_performed is None:
            self.operations_performed = []


class DataLadIntegrationWorkflow:
    """
    Template class for integrating DataLad with conversion workflows.

    Provides standardized patterns for data management, provenance tracking,
    and version control integration.
    """

    def __init__(self, config: DataLadConfig):
        """Initialize DataLad integration with configuration."""
        if not DATALAD_AVAILABLE:
            raise ImportError(
                "DataLad is not available. Install with: pip install datalad"
            )

        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize paths
        self.dataset_path = Path(config.dataset_path)

        # DataLad state
        self.dataset = None
        self.operations = []

    def initialize_dataset(self) -> DataLadResult:
        """
        Initialize or connect to DataLad dataset.

        Returns:
            DataLadResult with initialization status
        """
        self.logger.info(f"Initializing DataLad dataset: {self.dataset_path}")

        try:
            if self.dataset_path.exists() and (self.dataset_path / ".datalad").exists():
                # Dataset already exists, connect to it
                self.logger.info("Connecting to existing DataLad dataset")
                self.dataset = dl.Dataset(self.dataset_path)
                self.operations.append("connected_to_existing")

            elif self.config.create_if_missing:
                # Create new dataset
                self.logger.info("Creating new DataLad dataset")
                self.dataset = dl.create(
                    dataset=self.dataset_path, annex=True, return_type="item-or-list"
                )
                self.operations.append("created_new")

            else:
                raise FileNotFoundError(
                    f"DataLad dataset not found: {self.dataset_path}"
                )

            return DataLadResult(
                success=True,
                dataset_path=self.dataset_path,
                operations_performed=self.operations.copy(),
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize DataLad dataset: {e}")
            return DataLadResult(success=False, error_message=str(e))

    def install_subdataset(self, path: Union[str, Path], source: str) -> DataLadResult:
        """
        Install a subdataset from external source.

        Args:
            path: Local path for subdataset
            source: Source URL or path for subdataset

        Returns:
            DataLadResult with installation status
        """
        self.logger.info(f"Installing subdataset: {path} from {source}")

        try:
            dl.install(
                dataset=self.dataset_path,
                path=path,
                source=source,
                return_type="item-or-list",
            )

            self.operations.append(f"installed_subdataset:{path}")

            return DataLadResult(
                success=True,
                dataset_path=self.dataset_path,
                operations_performed=[f"installed_subdataset:{path}"],
            )

        except Exception as e:
            self.logger.error(f"Failed to install subdataset: {e}")
            return DataLadResult(success=False, error_message=str(e))

    def get_data(
        self, paths: Union[str, Path, list[Union[str, Path]]]
    ) -> DataLadResult:
        """
        Get data files from DataLad dataset.

        Args:
            paths: Path or list of paths to retrieve

        Returns:
            DataLadResult with retrieval status
        """
        if isinstance(paths, (str, Path)):
            paths = [paths]

        self.logger.info(f"Getting data files: {paths}")

        try:
            results = dl.get(dataset=self.dataset_path, path=paths, return_type="list")

            successful_paths = [r["path"] for r in results if r.get("status") == "ok"]
            self.operations.extend([f"retrieved:{path}" for path in successful_paths])

            return DataLadResult(
                success=len(successful_paths) == len(paths),
                dataset_path=self.dataset_path,
                operations_performed=[f"retrieved:{len(successful_paths)}_files"],
            )

        except Exception as e:
            self.logger.error(f"Failed to get data files: {e}")
            return DataLadResult(success=False, error_message=str(e))

    def save_changes(
        self,
        paths: Optional[list[Union[str, Path]]] = None,
        message: Optional[str] = None,
    ) -> DataLadResult:
        """
        Save changes to DataLad dataset.

        Args:
            paths: Specific paths to save (None for all changes)
            message: Commit message (uses template if None)

        Returns:
            DataLadResult with save status
        """
        if not self.config.auto_save:
            self.logger.info("Auto-save disabled, skipping save operation")
            return DataLadResult(success=True, operations_performed=["save_skipped"])

        # Generate commit message if not provided
        if message is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = self.config.save_message_template.format(
                workflow_name=self.__class__.__name__, timestamp=timestamp
            )

        self.logger.info(f"Saving changes to DataLad dataset: {message}")

        try:
            save_kwargs = {
                "dataset": self.dataset_path,
                "message": message,
                "return_type": "list",
            }

            if paths:
                save_kwargs["path"] = paths

            results = dl.save(**save_kwargs)

            # Extract commit hash if available
            commit_hash = None
            for result in results:
                if result.get("action") == "save" and "commit" in result:
                    commit_hash = result["commit"]
                    break

            self.operations.append(f"saved_changes:{commit_hash or 'unknown'}")

            return DataLadResult(
                success=True,
                dataset_path=self.dataset_path,
                operations_performed=["saved_changes"],
                commit_hash=commit_hash,
            )

        except Exception as e:
            self.logger.error(f"Failed to save changes: {e}")
            return DataLadResult(success=False, error_message=str(e))

    def run_with_provenance(
        self,
        command: str,
        inputs: list[Union[str, Path]],
        outputs: list[Union[str, Path]],
        message: Optional[str] = None,
    ) -> DataLadResult:
        """
        Run command with DataLad provenance tracking.

        Args:
            command: Command to execute
            inputs: Input files/directories
            outputs: Output files/directories
            message: Description of the operation

        Returns:
            DataLadResult with execution status
        """
        if not self.config.enable_provenance:
            self.logger.info("Provenance tracking disabled")
            return DataLadResult(
                success=True, operations_performed=["provenance_disabled"]
            )

        self.logger.info(f"Running command with provenance: {command}")

        try:
            result = dl.run(
                dataset=self.dataset_path,
                cmd=command,
                inputs=inputs,
                outputs=outputs,
                message=message or f"Execute: {command}",
                return_type="item-or-list",
            )

            commit_hash = result.get("commit") if isinstance(result, dict) else None
            self.operations.append(f"run_with_provenance:{commit_hash or 'unknown'}")

            return DataLadResult(
                success=True,
                dataset_path=self.dataset_path,
                operations_performed=["run_with_provenance"],
                commit_hash=commit_hash,
            )

        except Exception as e:
            self.logger.error(f"Failed to run command with provenance: {e}")
            return DataLadResult(success=False, error_message=str(e))

    def check_dataset_status(self) -> dict[str, Any]:
        """
        Check status of DataLad dataset.

        Returns:
            Dictionary with dataset status information
        """
        self.logger.info("Checking DataLad dataset status")

        try:
            status_results = dl.status(dataset=self.dataset_path, return_type="list")

            # Summarize status
            status_summary = {
                "total_files": len(status_results),
                "modified_files": len(
                    [r for r in status_results if r.get("state") == "modified"]
                ),
                "untracked_files": len(
                    [r for r in status_results if r.get("state") == "untracked"]
                ),
                "clean": len(status_results) == 0,
                "details": status_results,
            }

            return status_summary

        except Exception as e:
            self.logger.error(f"Failed to check dataset status: {e}")
            return {"error": str(e)}

    def create_workflow_branch(self, branch_name: str) -> DataLadResult:
        """
        Create a new branch for workflow execution.

        Args:
            branch_name: Name of the branch to create

        Returns:
            DataLadResult with branch creation status
        """
        self.logger.info(f"Creating workflow branch: {branch_name}")

        try:
            # Use git directly through DataLad's runner
            from datalad.cmd import WitlessRunner

            runner = WitlessRunner()

            # Create and checkout new branch
            runner.run(["git", "checkout", "-b", branch_name], cwd=self.dataset_path)

            self.operations.append(f"created_branch:{branch_name}")

            return DataLadResult(
                success=True,
                dataset_path=self.dataset_path,
                operations_performed=[f"created_branch:{branch_name}"],
            )

        except Exception as e:
            self.logger.error(f"Failed to create branch: {e}")
            return DataLadResult(success=False, error_message=str(e))

    def cleanup_workflow_data(self, patterns: list[str]) -> DataLadResult:
        """
        Clean up temporary workflow data.

        Args:
            patterns: List of file patterns to clean up

        Returns:
            DataLadResult with cleanup status
        """
        self.logger.info(f"Cleaning up workflow data: {patterns}")

        try:
            removed_files = []

            for pattern in patterns:
                matching_files = list(self.dataset_path.glob(pattern))
                for file_path in matching_files:
                    if file_path.exists():
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            import shutil

                            shutil.rmtree(file_path)
                        removed_files.append(str(file_path))

            self.operations.append(f"cleaned_up:{len(removed_files)}_files")

            return DataLadResult(
                success=True,
                dataset_path=self.dataset_path,
                operations_performed=[f"cleaned_up:{len(removed_files)}_files"],
            )

        except Exception as e:
            self.logger.error(f"Failed to cleanup workflow data: {e}")
            return DataLadResult(success=False, error_message=str(e))


def main():
    """Example usage of DataLad integration workflow."""

    # Example configuration
    config = DataLadConfig(
        dataset_path="example_dataset",
        enable_provenance=True,
        auto_save=True,
        create_if_missing=True,
    )

    # Initialize workflow
    workflow = DataLadIntegrationWorkflow(config)

    # Initialize dataset
    init_result = workflow.initialize_dataset()
    if not init_result.success:
        print(f"Failed to initialize dataset: {init_result.error_message}")
        return

    # Check dataset status
    status = workflow.check_dataset_status()
    print(f"Dataset status: {status}")

    # Example: Install a subdataset
    # install_result = workflow.install_subdataset(
    #     path="input_data/example_conversion",
    #     source="https://github.com/example/conversion-repo"
    # )

    # Example: Save changes
    save_result = workflow.save_changes(message="Example workflow execution")
    if save_result.success:
        print(f"Changes saved with commit: {save_result.commit_hash}")

    print("DataLad integration workflow completed")


if __name__ == "__main__":
    main()
