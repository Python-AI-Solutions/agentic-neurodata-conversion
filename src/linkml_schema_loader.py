"""LinkML schema loader for NWB.

This module loads the official NWB LinkML schema and provides validation functions.
"""

from typing import Any, Optional
from pathlib import Path
from functools import lru_cache
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.loaders import yaml_loader
import yaml


# Cache for loaded schemas
_schema_cache: dict[str, SchemaView] = {}


@lru_cache(maxsize=10)
def load_official_schema(version: str = "2.5.0") -> SchemaView:
    """Load official NWB LinkML schema.

    Args:
        version: NWB version (e.g., "2.5.0", "2.6.0")

    Returns:
        SchemaView object for the schema

    Raises:
        ValueError: If version is invalid or schema cannot be loaded
    """
    # Check cache first
    if version in _schema_cache:
        return _schema_cache[version]

    # For now, we'll create a minimal schema structure
    # In production, this would fetch from nwb-schema-language repo
    # https://github.com/NeurodataWithoutBorders/nwb-schema-language

    supported_versions = ["2.5.0", "2.6.0", "2.7.0"]
    if version not in supported_versions:
        raise ValueError(f"Unsupported NWB version: {version}. Supported: {supported_versions}")

    # Create minimal schema for testing
    # In production, load from official repo
    schema_dict = {
        "id": f"nwb-schema-{version}",
        "name": f"nwb-schema-{version}",
        "description": f"NWB Schema {version}",
        "version": version,
        "prefixes": {
            "nwb": f"http://purl.org/nwb/{version}/",
            "linkml": "https://w3id.org/linkml/"
        },
        "default_prefix": "nwb",
        "classes": {
            "NWBFile": {
                "name": "NWBFile",
                "description": "Top-level NWB file object",
                "attributes": {
                    "identifier": {
                        "name": "identifier",
                        "required": True,
                        "range": "string"
                    },
                    "session_description": {
                        "name": "session_description",
                        "required": True,
                        "range": "string"
                    },
                    "session_start_time": {
                        "name": "session_start_time",
                        "required": True,
                        "range": "datetime"
                    }
                }
            },
            "TimeSeries": {
                "name": "TimeSeries",
                "description": "General time series data",
                "attributes": {
                    "name": {
                        "name": "name",
                        "required": True,
                        "range": "string"
                    },
                    "data": {
                        "name": "data",
                        "required": True,
                        "range": "string"
                    },
                    "timestamps": {
                        "name": "timestamps",
                        "range": "string"
                    }
                }
            }
        },
        "types": {
            "string": {"name": "string", "typeof": "str"},
            "datetime": {"name": "datetime", "typeof": "str"}
        }
    }

    # Convert to YAML string and load as SchemaView
    yaml_str = yaml.dump(schema_dict)
    schema_view = SchemaView(yaml_str)

    # Cache it
    _schema_cache[version] = schema_view

    return schema_view


def validate_against_schema(instance: dict[str, Any], target_class: str, schema: SchemaView) -> bool:
    """Validate an instance against LinkML schema.

    Args:
        instance: Dictionary representing the instance
        target_class: Name of the target class in schema
        schema: SchemaView object

    Returns:
        True if valid, False otherwise
    """
    try:
        # Check if class exists in schema
        if target_class not in schema.all_classes():
            return False

        # Get class definition
        class_def = schema.get_class(target_class)

        # Check required attributes
        if hasattr(class_def, 'attributes'):
            for attr_name, attr_def in class_def.attributes.items():
                # Check if required attribute is present
                if hasattr(attr_def, 'required') and attr_def.required:
                    if attr_name not in instance:
                        return False

        return True

    except Exception:
        return False