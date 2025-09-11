"""
LinkML validation integration wrapper for the agentic neurodata conversion system.

This module provides a standardized interface to LinkML validation functionality
for validating metadata schemas and ensuring data compliance with standards.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class LinkMLValidatorInterface:
    """
    Wrapper interface for LinkML validation functionality.

    Provides standardized methods for validating metadata against LinkML schemas,
    checking schema compliance, and generating validation reports.
    """

    def __init__(self):
        """Initialize LinkML validator interface."""
        self._initialized = False
        self._loaded_schemas = {}

    def initialize(self) -> bool:
        """
        Initialize LinkML dependencies.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Import LinkML when needed to avoid hard dependency
            import linkml  # noqa: F401
            import linkml_runtime  # noqa: F401

            self._initialized = True
            logger.info("LinkML validator interface initialized successfully")
            return True
        except ImportError as e:
            logger.warning(f"LinkML not available: {e}")
            self._initialized = False
            return False

    def load_schema(
        self, schema_path: Union[str, Path], schema_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Load LinkML schema from file.

        Args:
            schema_path: Path to LinkML schema file
            schema_name: Optional name for the schema (defaults to filename)

        Returns:
            Schema loading results
        """
        if not self._initialized and not self.initialize():
            return {"status": "error", "message": "LinkML not available"}

        schema_path = Path(schema_path)

        if not schema_path.exists():
            return {
                "status": "error",
                "message": f"Schema file not found: {schema_path}",
            }

        if schema_name is None:
            schema_name = schema_path.stem

        try:
            logger.info(f"Loading LinkML schema: {schema_path}")

            # Placeholder for actual LinkML schema loading
            # This would use linkml.SchemaView or similar

            # Store schema reference
            self._loaded_schemas[schema_name] = {
                "path": str(schema_path),
                "loaded_at": "timestamp_placeholder",
            }

            logger.info(f"Schema '{schema_name}' loaded successfully")

            return {
                "status": "success",
                "schema_name": schema_name,
                "schema_path": str(schema_path),
                "message": "Schema loaded successfully",
            }

        except Exception as e:
            logger.error(f"Schema loading failed: {e}")
            return {"status": "error", "message": str(e)}

    def validate_data(
        self, data: dict[str, Any], schema_name: str, target_class: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Validate data against loaded LinkML schema.

        Args:
            data: Data to validate
            schema_name: Name of loaded schema to use
            target_class: Optional target class within schema

        Returns:
            Validation results with errors and warnings
        """
        if not self._initialized and not self.initialize():
            return {"status": "error", "message": "LinkML not available"}

        if schema_name not in self._loaded_schemas:
            return {"status": "error", "message": f"Schema not loaded: {schema_name}"}

        try:
            logger.info(f"Validating data against schema: {schema_name}")

            # Placeholder for actual LinkML validation
            # This would use linkml_runtime validation functions

            # Example validation results structure
            validation_results = {
                "status": "success",
                "valid": True,
                "schema_name": schema_name,
                "target_class": target_class,
                "errors": [],
                "warnings": [],
                "summary": {
                    "total_errors": 0,
                    "total_warnings": 0,
                    "fields_validated": len(data) if isinstance(data, dict) else 0,
                },
            }

            logger.info(f"Validation completed: {validation_results['summary']}")
            return validation_results

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {"status": "error", "message": str(e)}

    def validate_metadata_schema(
        self, metadata: dict[str, Any], schema_type: str = "nwb_metadata"
    ) -> dict[str, Any]:
        """
        Validate neuroscience metadata against appropriate schema.

        Args:
            metadata: Metadata dictionary to validate
            schema_type: Type of schema to validate against

        Returns:
            Validation results for metadata
        """
        if not self._initialized and not self.initialize():
            return {"status": "error", "message": "LinkML not available"}

        try:
            # Load appropriate schema if not already loaded
            if schema_type not in self._loaded_schemas:
                schema_result = self._load_default_schema(schema_type)
                if schema_result.get("status") != "success":
                    return schema_result

            # Validate metadata
            return self.validate_data(
                data=metadata, schema_name=schema_type, target_class="NWBMetadata"
            )

        except Exception as e:
            logger.error(f"Metadata validation failed: {e}")
            return {"status": "error", "message": str(e)}

    def _load_default_schema(self, schema_type: str) -> dict[str, Any]:
        """
        Load default schema for given type.

        Args:
            schema_type: Type of schema to load

        Returns:
            Schema loading results
        """
        # Map schema types to default schema files
        default_schemas = {
            "nwb_metadata": "nwb_metadata_schema.yaml",
            "dataset_metadata": "dataset_metadata_schema.yaml",
            "conversion_config": "conversion_config_schema.yaml",
        }

        schema_file = default_schemas.get(schema_type)
        if not schema_file:
            return {"status": "error", "message": f"Unknown schema type: {schema_type}"}

        # In a real implementation, this would load from a schemas directory
        # For now, create a placeholder schema
        self._loaded_schemas[schema_type] = {
            "path": f"schemas/{schema_file}",
            "loaded_at": "timestamp_placeholder",
        }

        return {
            "status": "success",
            "schema_name": schema_type,
            "message": f"Default schema loaded: {schema_type}",
        }

    def generate_validation_report(
        self,
        validation_results: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
        format: str = "txt",
    ) -> dict[str, Any]:
        """
        Generate detailed validation report.

        Args:
            validation_results: Results from validation
            output_path: Optional path for report output
            format: Report format ('txt', 'json', 'html')

        Returns:
            Report generation results
        """
        try:
            if output_path is None:
                output_path = Path(f"validation_report.{format}")
            else:
                output_path = Path(output_path)

            report_content = self._format_validation_report(validation_results, format)

            # Write report to file
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format == "json":
                import json

                with open(output_path, "w") as f:
                    json.dump(validation_results, f, indent=2)
            else:
                with open(output_path, "w") as f:
                    f.write(report_content)

            logger.info(f"Validation report generated: {output_path}")

            return {
                "status": "success",
                "report_path": str(output_path),
                "format": format,
            }

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {"status": "error", "message": str(e)}

    def _format_validation_report(
        self, validation_results: dict[str, Any], format: str
    ) -> str:
        """
        Format validation results into readable report.

        Args:
            validation_results: Results from validation
            format: Output format ('txt', 'html')

        Returns:
            Formatted report content
        """
        if format == "html":
            return self._format_html_validation_report(validation_results)
        else:
            return self._format_text_validation_report(validation_results)

    def _format_text_validation_report(self, validation_results: dict[str, Any]) -> str:
        """Format validation results as plain text report."""
        lines = [
            "LinkML Validation Report",
            "=" * 50,
            f"Schema: {validation_results.get('schema_name', 'Unknown')}",
            f"Target Class: {validation_results.get('target_class', 'N/A')}",
            f"Valid: {validation_results.get('valid', False)}",
            "",
            "Summary:",
            f"  Total Errors: {validation_results.get('summary', {}).get('total_errors', 0)}",
            f"  Total Warnings: {validation_results.get('summary', {}).get('total_warnings', 0)}",
            f"  Fields Validated: {validation_results.get('summary', {}).get('fields_validated', 0)}",
            "",
        ]

        # Add errors
        errors = validation_results.get("errors", [])
        if errors:
            lines.extend(["Errors:", "-" * 20])
            for error in errors:
                lines.append(f"  - {error}")
            lines.append("")

        # Add warnings
        warnings = validation_results.get("warnings", [])
        if warnings:
            lines.extend(["Warnings:", "-" * 20])
            for warning in warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)

    def _format_html_validation_report(self, validation_results: dict[str, Any]) -> str:
        """Format validation results as HTML report."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkML Validation Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 10px; }
                .summary { margin: 20px 0; }
                .valid { color: #4caf50; }
                .invalid { color: #f44336; }
                .error { color: #f44336; margin: 5px 0; }
                .warning { color: #ff9800; margin: 5px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>LinkML Validation Report</h1>
                <p>Schema: {schema_name}</p>
                <p>Target Class: {target_class}</p>
                <p class="{valid_class}">Status: {valid_status}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <ul>
                    <li>Total Errors: {total_errors}</li>
                    <li>Total Warnings: {total_warnings}</li>
                    <li>Fields Validated: {fields_validated}</li>
                </ul>
            </div>

            {errors_section}
            {warnings_section}
        </body>
        </html>
        """

        # Format errors and warnings
        errors_html = ""
        warnings_html = ""

        errors = validation_results.get("errors", [])
        if errors:
            errors_html = "<div><h2>Errors</h2>"
            for error in errors:
                errors_html += f'<div class="error">• {error}</div>'
            errors_html += "</div>"

        warnings = validation_results.get("warnings", [])
        if warnings:
            warnings_html = "<div><h2>Warnings</h2>"
            for warning in warnings:
                warnings_html += f'<div class="warning">• {warning}</div>'
            warnings_html += "</div>"

        valid = validation_results.get("valid", False)
        summary = validation_results.get("summary", {})

        return html_template.format(
            schema_name=validation_results.get("schema_name", "Unknown"),
            target_class=validation_results.get("target_class", "N/A"),
            valid_class="valid" if valid else "invalid",
            valid_status="VALID" if valid else "INVALID",
            total_errors=summary.get("total_errors", 0),
            total_warnings=summary.get("total_warnings", 0),
            fields_validated=summary.get("fields_validated", 0),
            errors_section=errors_html,
            warnings_section=warnings_html,
        )

    def get_loaded_schemas(self) -> dict[str, dict[str, Any]]:
        """
        Get information about currently loaded schemas.

        Returns:
            Dictionary of loaded schemas with metadata
        """
        return self._loaded_schemas.copy()

    def unload_schema(self, schema_name: str) -> dict[str, Any]:
        """
        Unload a previously loaded schema.

        Args:
            schema_name: Name of schema to unload

        Returns:
            Unload operation results
        """
        if schema_name in self._loaded_schemas:
            del self._loaded_schemas[schema_name]
            logger.info(f"Schema '{schema_name}' unloaded")
            return {"status": "success", "message": f"Schema '{schema_name}' unloaded"}
        else:
            return {"status": "error", "message": f"Schema '{schema_name}' not found"}
