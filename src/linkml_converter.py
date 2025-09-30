"""LinkML converter for NWB data.

This module converts NWB file data to LinkML instances.
"""

from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from pynwb import NWBFile
from linkml_runtime.utils.schemaview import SchemaView
import h5py
import json


@dataclass
class LinkMLMetadata:
    """Metadata about LinkML conversion."""
    nwb_version: str
    schema_version: str
    custom_extensions: list[str] = field(default_factory=list)
    conversion_notes: list[str] = field(default_factory=list)


@dataclass
class LinkMLInstances:
    """Collection of LinkML instances from NWB file."""
    instances: list[dict[str, Any]] = field(default_factory=list)
    metadata: LinkMLMetadata = field(default_factory=lambda: LinkMLMetadata("2.5.0", "2.5.0"))


def convert_nwb_to_linkml(nwbfile: NWBFile, schema: SchemaView, hierarchy: Optional[dict[str, Any]] = None) -> LinkMLInstances:
    """Convert NWB file to LinkML instances dynamically.

    Args:
        nwbfile: Loaded NWBFile object
        schema: LinkML SchemaView
        hierarchy: Optional hierarchy data from hierarchical_parser (for complete extraction)

    Returns:
        LinkMLInstances with converted data
    """
    result = LinkMLInstances()

    # If hierarchy provided, use dynamic conversion for complete extraction
    if hierarchy:
        return _convert_from_hierarchy(hierarchy, nwbfile, schema)

    # Fallback to manual conversion (legacy)
    # Convert root NWBFile
    root_instance = _convert_nwbfile(nwbfile, schema)

    # Track all relationships
    acquisition_ids = []
    device_ids = []
    electrode_group_ids = []
    subject_id = None

    # Convert subject
    if hasattr(nwbfile, 'subject') and nwbfile.subject:
        subject_instance = _convert_subject(nwbfile.subject, schema)
        if subject_instance:
            result.instances.append(subject_instance)
            subject_id = subject_instance.get('@id', subject_instance.get('subject_id'))

    # Convert devices
    if hasattr(nwbfile, 'devices'):
        for name, device in nwbfile.devices.items():
            instance = _convert_device(name, device, schema)
            if instance:
                result.instances.append(instance)
                device_ids.append(instance.get('@id', instance.get('name')))

    # Convert electrode groups
    if hasattr(nwbfile, 'electrode_groups'):
        for name, group in nwbfile.electrode_groups.items():
            instance = _convert_electrode_group(name, group, schema)
            if instance:
                result.instances.append(instance)
                electrode_group_ids.append(instance.get('@id', instance.get('name')))

    # Convert acquisition data
    if hasattr(nwbfile, 'acquisition'):
        for name, obj in nwbfile.acquisition.items():
            instance = _convert_timeseries(name, obj, schema)
            if instance:
                result.instances.append(instance)
                acquisition_ids.append(instance.get('@id', instance.get('name')))

    # Convert processing modules
    if hasattr(nwbfile, 'processing'):
        for module_name, module in nwbfile.processing.items():
            for interface_name, interface in module.data_interfaces.items():
                instance = _convert_timeseries(interface_name, interface, schema)
                if instance:
                    result.instances.append(instance)
                    acquisition_ids.append(instance.get('@id', instance.get('name')))

    # Add all references to root instance
    if acquisition_ids:
        root_instance['has_acquisition'] = acquisition_ids
    if device_ids:
        root_instance['has_devices'] = device_ids
    if electrode_group_ids:
        root_instance['has_electrode_groups'] = electrode_group_ids
    if subject_id:
        root_instance['has_subject'] = subject_id

    # Add root instance after collecting all relationships
    result.instances.insert(0, root_instance)

    # Add metadata
    result.metadata.nwb_version = nwbfile.nwb_version if hasattr(nwbfile, 'nwb_version') else "2.5.0"
    result.metadata.schema_version = "2.5.0"

    return result


def _convert_nwbfile(nwbfile: NWBFile, schema: SchemaView) -> dict[str, Any]:
    """Convert NWBFile to LinkML instance.

    Args:
        nwbfile: NWBFile object
        schema: LinkML schema

    Returns:
        Dictionary representing NWBFile instance
    """
    instance = {
        "@type": "NWBFile",
        "@id": nwbfile.identifier,
        "identifier": nwbfile.identifier,
        "session_description": nwbfile.session_description,
        "session_start_time": str(nwbfile.session_start_time)
    }

    # Optional fields
    if hasattr(nwbfile, 'experimenter') and nwbfile.experimenter:
        instance["experimenter"] = nwbfile.experimenter

    if hasattr(nwbfile, 'institution') and nwbfile.institution:
        instance["institution"] = nwbfile.institution

    if hasattr(nwbfile, 'lab') and nwbfile.lab:
        instance["lab"] = nwbfile.lab

    return instance


def _convert_subject(subject: Any, schema: SchemaView) -> Optional[dict[str, Any]]:
    """Convert Subject to LinkML instance.

    Args:
        subject: Subject object
        schema: LinkML schema

    Returns:
        Dictionary representing Subject instance
    """
    try:
        instance = {
            "@type": "Subject",
            "@id": getattr(subject, 'subject_id', 'subject')
        }

        # Add subject fields
        if hasattr(subject, 'subject_id') and subject.subject_id:
            instance["subject_id"] = subject.subject_id
        if hasattr(subject, 'species') and subject.species:
            instance["species"] = subject.species
        if hasattr(subject, 'sex') and subject.sex:
            instance["sex"] = subject.sex
        if hasattr(subject, 'age') and subject.age:
            instance["age"] = subject.age
        if hasattr(subject, 'description') and subject.description:
            instance["description"] = subject.description

        return instance
    except Exception as e:
        return None


def _convert_device(name: str, device: Any, schema: SchemaView) -> Optional[dict[str, Any]]:
    """Convert Device to LinkML instance.

    Args:
        name: Device name
        device: Device object
        schema: LinkML schema

    Returns:
        Dictionary representing Device instance
    """
    try:
        instance = {
            "@type": "Device",
            "@id": name,
            "name": name
        }

        # Add device fields
        if hasattr(device, 'description') and device.description:
            instance["description"] = device.description
        if hasattr(device, 'manufacturer') and device.manufacturer:
            instance["manufacturer"] = device.manufacturer

        return instance
    except Exception as e:
        return None


def _convert_electrode_group(name: str, group: Any, schema: SchemaView) -> Optional[dict[str, Any]]:
    """Convert ElectrodeGroup to LinkML instance.

    Args:
        name: Electrode group name
        group: ElectrodeGroup object
        schema: LinkML schema

    Returns:
        Dictionary representing ElectrodeGroup instance
    """
    try:
        instance = {
            "@type": "ElectrodeGroup",
            "@id": name,
            "name": name
        }

        # Add electrode group fields
        if hasattr(group, 'description') and group.description:
            instance["description"] = group.description
        if hasattr(group, 'location') and group.location:
            instance["location"] = group.location

        # Link to device
        if hasattr(group, 'device') and group.device:
            device_name = getattr(group.device, 'name', None)
            if device_name:
                instance["has_device"] = device_name

        return instance
    except Exception as e:
        return None


def _convert_timeseries(name: str, obj: Any, schema: SchemaView) -> Optional[dict[str, Any]]:
    """Convert TimeSeries or similar object to LinkML instance.

    Args:
        name: Name of the object
        obj: pynwb object (TimeSeries, etc.)
        schema: LinkML schema

    Returns:
        Dictionary representing instance, or None if not convertible
    """
    try:
        instance = {
            "@type": "TimeSeries",
            "@id": name,
            "name": name
        }

        # Add data information (metadata only, not actual data arrays)
        if hasattr(obj, 'data'):
            data = obj.data
            if hasattr(data, 'shape'):
                instance["data_shape"] = str(data.shape)
            if hasattr(data, 'dtype'):
                instance["data_dtype"] = str(data.dtype)

        # Add timestamps information
        if hasattr(obj, 'timestamps'):
            ts = obj.timestamps
            if ts is not None and hasattr(ts, 'shape'):
                instance["timestamps_shape"] = str(ts.shape)

        # Add description if available
        if hasattr(obj, 'description') and obj.description:
            instance["description"] = obj.description

        # Add unit if available
        if hasattr(obj, 'unit') and obj.unit:
            instance["unit"] = obj.unit

        return instance

    except Exception as e:
        # Skip objects that can't be converted
        return None


def _convert_from_hierarchy(hierarchy: Any, nwbfile: NWBFile, schema: SchemaView) -> LinkMLInstances:
    """Convert NWB data dynamically using hierarchy information.

    This extracts ALL groups, datasets, and attributes from the hierarchy,
    making the conversion truly dynamic and complete.

    Args:
        hierarchy: HierarchyTree from hierarchical_parser
        nwbfile: NWBFile object (for metadata)
        schema: LinkML schema

    Returns:
        LinkMLInstances with complete data
    """
    result = LinkMLInstances()

    # Create root node
    root_instance = {
        "@type": "NWBFile",
        "@id": nwbfile.identifier if hasattr(nwbfile, 'identifier') else "root",
        "identifier": nwbfile.identifier if hasattr(nwbfile, 'identifier') else "root",
        "path": "/"
    }

    # Add basic NWBFile attributes
    if hasattr(nwbfile, 'session_description'):
        root_instance["session_description"] = nwbfile.session_description
    if hasattr(nwbfile, 'session_start_time'):
        root_instance["session_start_time"] = str(nwbfile.session_start_time)

    # Track child relationships
    children = {}

    # Process all groups from hierarchy (HierarchyTree object)
    for group in hierarchy.groups:
        path = group.path
        name = group.name
        parent_path = group.parent_path

        # Create node for this group
        node_id = path.replace('/', '_') if path != '/' else 'root'

        instance = {
            "@type": _infer_type_from_path(path),
            "@id": node_id,
            "name": name,
            "path": path
        }

        # Add attributes if present
        if group.attributes:
            for attr_name, attr_value in group.attributes.items():
                if not attr_name.startswith('_') and attr_value is not None:
                    # Clean attribute value
                    if isinstance(attr_value, (str, int, float, bool)):
                        instance[attr_name] = attr_value
                    else:
                        instance[attr_name] = str(attr_value)

        # Track parent-child relationships
        if parent_path != path:  # Not root
            if parent_path not in children:
                children[parent_path] = []
            children[parent_path].append(node_id)

        # Skip root (already created above)
        if path != '/':
            result.instances.append(instance)

    # Process all datasets from hierarchy
    for dataset in hierarchy.datasets:
        path = dataset.path
        name = dataset.name
        parent_path = dataset.parent_path

        # Create node for this dataset
        node_id = path.replace('/', '_')

        instance = {
            "@type": _infer_type_from_path(path),
            "@id": node_id,
            "name": name,
            "path": path
        }

        # Add dataset properties
        instance['data_shape'] = str(dataset.shape)
        instance['data_dtype'] = str(dataset.dtype)
        instance['size_bytes'] = dataset.size_bytes

        # Track parent-child relationship
        if parent_path not in children:
            children[parent_path] = []
        children[parent_path].append(node_id)

        result.instances.append(instance)

    # Add child relationships to all instances
    for instance in result.instances:
        path = instance.get('path', '')
        if path in children:
            instance['has_children'] = children[path]

    # Add children to root
    if '/' in children:
        root_instance['has_children'] = children['/']

    # Insert root at beginning
    result.instances.insert(0, root_instance)

    # Add metadata
    result.metadata.nwb_version = nwbfile.nwb_version if hasattr(nwbfile, 'nwb_version') else "2.5.0"
    result.metadata.schema_version = "2.5.0"
    result.metadata.conversion_notes.append("Dynamic conversion from complete hierarchy")

    return result


def _infer_type_from_path(path: str) -> str:
    """Infer NWB type from path.

    Args:
        path: HDF5 path

    Returns:
        Inferred type string
    """
    if path == '/':
        return "NWBFile"

    path_lower = path.lower()

    # Check path components
    if '/acquisition/' in path:
        return "TimeSeries"
    elif '/devices/' in path:
        return "Device"
    elif '/electrode' in path_lower and 'group' in path_lower:
        return "ElectrodeGroup"
    elif '/general/subject' in path:
        return "Subject"
    elif '/processing/' in path:
        return "ProcessingModule"
    elif '/analysis/' in path:
        return "Analysis"
    elif '/stimulus/' in path:
        return "TimeSeries"
    elif 'electrode' in path_lower:
        return "Electrodes"
    elif '/general/' in path:
        return "General"
    else:
        # Default to Group
        return "Group"