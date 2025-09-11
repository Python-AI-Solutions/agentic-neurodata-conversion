#!/usr/bin/env python3
"""
Batch Processing Workflow Template

This template provides a standardized structure for processing multiple datasets
in batch mode with parallel execution and comprehensive reporting.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

from .basic_conversion_workflow import (
    BasicConversionWorkflow,
    ConversionConfig,
    ConversionResult,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing workflow."""

    datasets: list[dict[str, Any]]
    output_directory: Union[str, Path]
    parallel_workers: int = 4
    continue_on_error: bool = True
    generate_report: bool = True
    report_format: str = "json"  # json, html, csv
    log_level: str = "INFO"
    global_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result of batch processing execution."""

    total_datasets: int
    successful_conversions: int
    failed_conversions: int
    processing_time: float
    results: list[ConversionResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    report_path: Optional[Path] = None


class BatchProcessingWorkflow:
    """
    Template class for batch processing of neuroscience datasets.

    Provides parallel processing capabilities with comprehensive error handling
    and reporting for large-scale data conversion operations.
    """

    def __init__(self, config: BatchConfig):
        """Initialize batch workflow with configuration."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, config.log_level.upper()))

        # Initialize paths
        self.output_directory = Path(config.output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

        # Workflow state
        self.start_time = None
        self.results = []
        self.errors = []

    def execute(self) -> BatchResult:
        """
        Execute batch processing workflow.

        Returns:
            BatchResult with execution summary and individual results
        """
        self.start_time = datetime.now()
        self.logger.info(
            f"Starting batch processing: {len(self.config.datasets)} datasets"
        )

        try:
            # Validate batch configuration
            self._validate_batch_config()

            # Process datasets
            if self.config.parallel_workers > 1:
                self._process_parallel()
            else:
                self._process_sequential()

            # Generate report
            report_path = None
            if self.config.generate_report:
                report_path = self._generate_report()

            # Calculate summary statistics
            processing_time = (datetime.now() - self.start_time).total_seconds()
            successful = sum(1 for r in self.results if r.success)
            failed = len(self.results) - successful

            return BatchResult(
                total_datasets=len(self.config.datasets),
                successful_conversions=successful,
                failed_conversions=failed,
                processing_time=processing_time,
                results=self.results,
                errors=self.errors,
                report_path=report_path,
            )

        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            processing_time = (datetime.now() - self.start_time).total_seconds()

            return BatchResult(
                total_datasets=len(self.config.datasets),
                successful_conversions=0,
                failed_conversions=len(self.config.datasets),
                processing_time=processing_time,
                errors=[str(e)],
            )

    def _validate_batch_config(self) -> None:
        """Validate batch configuration parameters."""
        self.logger.info("Validating batch configuration...")

        if not self.config.datasets:
            raise ValueError("No datasets specified for batch processing")

        # Validate each dataset configuration
        for i, dataset in enumerate(self.config.datasets):
            if "input_path" not in dataset:
                raise ValueError(f"Dataset {i}: missing 'input_path'")

            if "output_filename" not in dataset:
                # Generate default output filename
                input_path = Path(dataset["input_path"])
                dataset["output_filename"] = f"{input_path.name}.nwb"

        self.logger.info("Batch configuration validated")

    def _process_sequential(self) -> None:
        """Process datasets sequentially."""
        self.logger.info("Processing datasets sequentially...")

        for i, dataset_config in enumerate(self.config.datasets):
            self.logger.info(f"Processing dataset {i + 1}/{len(self.config.datasets)}")

            try:
                result = self._process_single_dataset(dataset_config)
                self.results.append(result)

                if not result.success and not self.config.continue_on_error:
                    self.logger.error("Stopping batch processing due to error")
                    break

            except Exception as e:
                error_msg = f"Dataset {i + 1} failed: {e}"
                self.logger.error(error_msg)
                self.errors.append(error_msg)

                if not self.config.continue_on_error:
                    break

    def _process_parallel(self) -> None:
        """Process datasets in parallel using ThreadPoolExecutor."""
        self.logger.info(
            f"Processing datasets in parallel (workers: {self.config.parallel_workers})..."
        )

        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            # Submit all tasks
            future_to_dataset = {
                executor.submit(self._process_single_dataset, dataset): i
                for i, dataset in enumerate(self.config.datasets)
            }

            # Collect results as they complete
            for future in as_completed(future_to_dataset):
                dataset_index = future_to_dataset[future]

                try:
                    result = future.result()
                    self.results.append(result)

                    status = "SUCCESS" if result.success else "FAILED"
                    self.logger.info(f"Dataset {dataset_index + 1} completed: {status}")

                except Exception as e:
                    error_msg = f"Dataset {dataset_index + 1} failed: {e}"
                    self.logger.error(error_msg)
                    self.errors.append(error_msg)

    def _process_single_dataset(
        self, dataset_config: dict[str, Any]
    ) -> ConversionResult:
        """
        Process a single dataset.

        Args:
            dataset_config: Configuration for individual dataset

        Returns:
            ConversionResult for the dataset
        """
        # Prepare conversion configuration
        input_path = Path(dataset_config["input_path"])
        output_path = self.output_directory / dataset_config["output_filename"]

        # Merge global and dataset-specific metadata
        metadata = self.config.global_metadata.copy()
        metadata.update(dataset_config.get("metadata", {}))

        # Create conversion configuration
        conversion_config = ConversionConfig(
            input_path=input_path,
            output_path=output_path,
            metadata=metadata,
            validation_enabled=dataset_config.get("validation_enabled", True),
            overwrite_existing=dataset_config.get("overwrite_existing", False),
            log_level=self.config.log_level,
        )

        # Execute conversion
        workflow = BasicConversionWorkflow(conversion_config)
        return workflow.execute()

    def _generate_report(self) -> Path:
        """
        Generate batch processing report.

        Returns:
            Path to generated report file
        """
        self.logger.info("Generating batch processing report...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.config.report_format.lower() == "json":
            return self._generate_json_report(timestamp)
        elif self.config.report_format.lower() == "html":
            return self._generate_html_report(timestamp)
        elif self.config.report_format.lower() == "csv":
            return self._generate_csv_report(timestamp)
        else:
            raise ValueError(f"Unsupported report format: {self.config.report_format}")

    def _generate_json_report(self, timestamp: str) -> Path:
        """Generate JSON format report."""
        report_path = self.output_directory / f"batch_report_{timestamp}.json"

        # Prepare report data
        report_data = {
            "batch_summary": {
                "timestamp": timestamp,
                "total_datasets": len(self.config.datasets),
                "successful_conversions": sum(1 for r in self.results if r.success),
                "failed_conversions": sum(1 for r in self.results if not r.success),
                "processing_time": (datetime.now() - self.start_time).total_seconds(),
                "parallel_workers": self.config.parallel_workers,
            },
            "dataset_results": [],
            "errors": self.errors,
        }

        # Add individual dataset results
        for i, result in enumerate(self.results):
            dataset_result = {
                "dataset_index": i,
                "input_path": str(self.config.datasets[i]["input_path"]),
                "output_path": str(result.output_path) if result.output_path else None,
                "success": result.success,
                "processing_time": result.processing_time,
                "error_message": result.error_message,
                "warnings": result.warnings,
                "metadata_fields": len(result.metadata_extracted),
                "validation_passed": result.validation_results.get("valid", False)
                if result.validation_results
                else False,
            }
            report_data["dataset_results"].append(dataset_result)

        # Write report
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        self.logger.info(f"JSON report generated: {report_path}")
        return report_path

    def _generate_html_report(self, timestamp: str) -> Path:
        """Generate HTML format report."""
        report_path = self.output_directory / f"batch_report_{timestamp}.html"

        # TODO: Implement HTML report generation
        # This would create a formatted HTML report with tables and charts

        # Placeholder implementation
        html_content = f"""
        <html>
        <head><title>Batch Processing Report - {timestamp}</title></head>
        <body>
        <h1>Batch Processing Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Total Datasets: {len(self.config.datasets)}</p>
        <p>Successful: {sum(1 for r in self.results if r.success)}</p>
        <p>Failed: {sum(1 for r in self.results if not r.success)}</p>
        </body>
        </html>
        """

        with open(report_path, "w") as f:
            f.write(html_content)

        self.logger.info(f"HTML report generated: {report_path}")
        return report_path

    def _generate_csv_report(self, timestamp: str) -> Path:
        """Generate CSV format report."""
        report_path = self.output_directory / f"batch_report_{timestamp}.csv"

        # TODO: Implement CSV report generation
        # This would create a CSV file with dataset results

        # Placeholder implementation
        csv_content = "dataset_index,input_path,output_path,success,processing_time,error_message\n"

        for i, result in enumerate(self.results):
            csv_content += f"{i},{self.config.datasets[i]['input_path']},{result.output_path},{result.success},{result.processing_time},{result.error_message or ''}\n"

        with open(report_path, "w") as f:
            f.write(csv_content)

        self.logger.info(f"CSV report generated: {report_path}")
        return report_path


def main():
    """Example usage of the batch processing workflow template."""

    # Example batch configuration
    datasets = [
        {
            "input_path": "path/to/dataset1",
            "output_filename": "dataset1.nwb",
            "metadata": {"subject_id": "subject_001"},
        },
        {
            "input_path": "path/to/dataset2",
            "output_filename": "dataset2.nwb",
            "metadata": {"subject_id": "subject_002"},
        },
    ]

    config = BatchConfig(
        datasets=datasets,
        output_directory="batch_output",
        parallel_workers=2,
        continue_on_error=True,
        generate_report=True,
        report_format="json",
        global_metadata={
            "experiment_description": "Batch conversion example",
            "lab": "Example Lab",
        },
    )

    # Execute batch workflow
    workflow = BatchProcessingWorkflow(config)
    result = workflow.execute()

    # Print results
    print("Batch processing completed:")
    print(f"  Total datasets: {result.total_datasets}")
    print(f"  Successful: {result.successful_conversions}")
    print(f"  Failed: {result.failed_conversions}")
    print(f"  Processing time: {result.processing_time:.2f} seconds")

    if result.report_path:
        print(f"  Report generated: {result.report_path}")


if __name__ == "__main__":
    main()
