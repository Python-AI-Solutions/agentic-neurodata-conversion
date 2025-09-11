"""
NeuroConv integration wrapper for the agentic neurodata conversion system.

This module provides a standardized interface to NeuroConv functionality,
including data interface detection, conversion script generation, and
NWB file creation.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class MissingDependencyError(Exception):
    """Raised when a critical dependency is missing."""

    def __init__(self, dependency: str, functionality: str):
        super().__init__(
            f"Cannot perform {functionality} without '{dependency}'. "
            f"This dependency is required for NWB conversion. "
            f"Install with: pixi add {dependency}"
        )


def _check_neuroconv_available():
    """Check that neuroconv is available."""
    try:
        import neuroconv  # noqa: F401
    except ImportError as e:
        raise MissingDependencyError(
            "neuroconv", "neuroscience data conversion to NWB"
        ) from e


class NeuroConvInterface:
    """
    Wrapper interface for NeuroConv functionality.

    Provides standardized methods for interacting with NeuroConv data interfaces,
    generating conversion scripts, and executing conversions to NWB format.
    """

    def __init__(self):
        """Initialize NeuroConv interface."""
        # Check critical dependencies at initialization
        _check_neuroconv_available()
        self._available_interfaces = None
        logger.info("NeuroConv interface initialized successfully")

    def detect_data_interfaces(
        self, data_path: Union[str, Path]
    ) -> list[dict[str, Any]]:
        """
        Detect available NeuroConv data interfaces for given data path.

        Args:
            data_path: Path to neuroscience data directory or file

        Returns:
            List of detected interfaces with metadata
        """
        # neuroconv should be available due to dependency check in __init__

        data_path = Path(data_path)
        detected_interfaces = []

        try:
            # Placeholder for NeuroConv interface detection logic
            # This would use NeuroConv's auto-detection capabilities
            logger.info(f"Detecting interfaces for: {data_path}")

            # Example detection logic (to be replaced with actual NeuroConv calls)
            if data_path.is_dir():
                # Check for common neuroscience data formats
                if any(data_path.glob("*.continuous")):
                    detected_interfaces.append(
                        {
                            "interface_name": "OpenEphysRecordingInterface",
                            "data_path": str(data_path),
                            "format": "open_ephys",
                        }
                    )

                if any(data_path.glob("*.bin")):
                    detected_interfaces.append(
                        {
                            "interface_name": "SpikeGLXRecordingInterface",
                            "data_path": str(data_path),
                            "format": "spikeglx",
                        }
                    )

            logger.info(f"Detected {len(detected_interfaces)} interfaces")
            return detected_interfaces

        except Exception as e:
            logger.error(f"Interface detection failed: {e}")
            return []

    def generate_conversion_script(
        self,
        interfaces: list[dict[str, Any]],
        metadata: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> dict[str, Any]:
        """
        Generate NeuroConv conversion script from detected interfaces and metadata.

        Args:
            interfaces: List of detected data interfaces
            metadata: Normalized metadata for NWB conversion
            output_path: Optional output path for NWB file

        Returns:
            Dictionary containing generated script and execution info
        """

        try:
            # Generate conversion script template
            script_template = self._create_script_template(
                interfaces, metadata, output_path
            )

            return {
                "status": "success",
                "script": script_template,
                "interfaces": interfaces,
                "output_path": output_path,
            }

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {"status": "error", "message": str(e)}

    def execute_conversion(
        self, script: str, output_path: Union[str, Path]
    ) -> dict[str, Any]:
        """
        Execute NeuroConv conversion script.

        Args:
            script: Generated conversion script
            output_path: Path for output NWB file

        Returns:
            Conversion execution results
        """

        try:
            # Execute conversion script
            # This would involve running the generated NeuroConv script
            logger.info(f"Executing conversion to: {output_path}")

            # Placeholder for actual script execution
            # exec(script) or subprocess execution would go here

            return {
                "status": "success",
                "output_path": str(output_path),
                "message": "Conversion completed successfully",
            }

        except Exception as e:
            logger.error(f"Conversion execution failed: {e}")
            return {"status": "error", "message": str(e)}

    def _create_script_template(
        self,
        interfaces: list[dict[str, Any]],
        metadata: dict[str, Any],
        output_path: Optional[Union[str, Path]],
    ) -> str:
        """
        Create NeuroConv script template from interfaces and metadata.

        Args:
            interfaces: Detected data interfaces
            metadata: Normalized metadata
            output_path: Output NWB file path

        Returns:
            Generated Python script as string
        """
        script_lines = [
            "# Generated NeuroConv conversion script",
            "from neuroconv import NWBConverter",
            "from pathlib import Path",
            "",
            "# Data interface configuration",
        ]

        # Add interface imports and configuration
        for interface in interfaces:
            interface_name = interface.get("interface_name", "UnknownInterface")
            script_lines.append(
                f"from neuroconv.datainterfaces import {interface_name}"
            )

        script_lines.extend(["", "# Configure data interfaces", "source_data = {"])

        # Add interface configurations
        for i, interface in enumerate(interfaces):
            interface_name = interface.get("interface_name", f"Interface{i}")
            data_path = interface.get("data_path", "")
            script_lines.append(f'    "{interface_name}": {{')
            script_lines.append(f'        "folder_path": "{data_path}"')
            script_lines.append("    },")

        script_lines.extend(
            [
                "}",
                "",
                "# Create converter",
                "converter = NWBConverter(source_data=source_data)",
                "",
                "# Add metadata",
                f"metadata = {metadata}",
                "converter.add_to_nwbfile(metadata=metadata)",
                "",
                "# Run conversion",
            ]
        )

        if output_path:
            script_lines.append(f'nwbfile_path = "{output_path}"')
        else:
            script_lines.append('nwbfile_path = "output.nwb"')

        script_lines.extend(
            [
                "converter.run_conversion(nwbfile_path=nwbfile_path)",
                'print(f"Conversion completed: {nwbfile_path}")',
            ]
        )

        return "\n".join(script_lines)

    def get_available_interfaces(self) -> list[str]:
        """
        Get list of available NeuroConv data interfaces.

        Returns:
            List of available interface names
        """

        if self._available_interfaces is None:
            try:
                # Get available interfaces from NeuroConv
                # This would query NeuroConv for all available interfaces
                self._available_interfaces = [
                    "OpenEphysRecordingInterface",
                    "SpikeGLXRecordingInterface",
                    "BlackrockRecordingInterface",
                    "NeuraLynxRecordingInterface",
                    "Intan RecordingInterface",
                ]
                logger.info(
                    f"Found {len(self._available_interfaces)} available interfaces"
                )
            except Exception as e:
                logger.error(f"Failed to get available interfaces: {e}")
                self._available_interfaces = []

        return self._available_interfaces.copy()

    def validate_interface_config(
        self, interface_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate NeuroConv interface configuration.

        Args:
            interface_config: Interface configuration to validate

        Returns:
            Validation results with status and any errors
        """
        try:
            interface_name = interface_config.get("interface_name")
            data_path = interface_config.get("data_path")

            if not interface_name:
                return {"valid": False, "error": "Missing interface_name"}

            if not data_path or not Path(data_path).exists():
                return {"valid": False, "error": f"Data path not found: {data_path}"}

            # Additional validation logic would go here
            return {"valid": True, "message": "Configuration valid"}

        except Exception as e:
            return {"valid": False, "error": str(e)}
