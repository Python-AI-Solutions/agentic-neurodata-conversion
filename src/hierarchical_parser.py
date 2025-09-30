"""Hierarchical HDF5 structure parser.

This module performs deep traversal of NWB file HDF5 structure to extract
complete metadata about groups, datasets, attributes, and links.
"""

from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from pynwb import NWBFile
import h5py


@dataclass
class DatasetInfo:
    """Information about an HDF5 dataset."""
    name: str
    path: str
    parent_path: str
    shape: tuple
    dtype: str
    size_bytes: int
    chunks: Optional[tuple] = None
    compression: Optional[str] = None


@dataclass
class GroupInfo:
    """Information about an HDF5 group."""
    name: str
    path: str
    parent_path: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkInfo:
    """Information about an HDF5 link."""
    name: str
    path: str
    link_type: str  # 'soft' or 'external'
    target: str


@dataclass
class HierarchyTree:
    """Complete hierarchical structure of NWB file."""
    root: str
    groups: list[GroupInfo] = field(default_factory=list)
    datasets: list[DatasetInfo] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    links: list[LinkInfo] = field(default_factory=list)


def parse_hdf5_structure(nwbfile: NWBFile) -> HierarchyTree:
    """Parse complete HDF5 structure from NWB file.

    Args:
        nwbfile: Loaded NWBFile object

    Returns:
        HierarchyTree with complete metadata
    """
    # Get the underlying HDF5 file path
    h5_path = None
    if hasattr(nwbfile, '_io'):
        # Try different attributes for the file path
        if hasattr(nwbfile._io, 'path'):
            h5_path = nwbfile._io.path
        elif hasattr(nwbfile._io, '_file'):
            # Get from the underlying h5py file object
            if hasattr(nwbfile._io._file, 'filename'):
                h5_path = nwbfile._io._file.filename
        elif hasattr(nwbfile._io, 'source'):
            h5_path = nwbfile._io.source

    if h5_path is None:
        raise ValueError("Cannot determine HDF5 file path from NWBFile object")

    hierarchy = HierarchyTree(root='/')

    # Open HDF5 file directly for deep traversal
    with h5py.File(h5_path, 'r') as h5file:
        # Get root attributes
        hierarchy.attributes = dict(h5file.attrs)

        # Recursively traverse
        _traverse_group(h5file, '/', hierarchy)

    return hierarchy


def _traverse_group(h5obj: h5py.Group, parent_path: str, hierarchy: HierarchyTree) -> None:
    """Recursively traverse HDF5 group structure.

    Args:
        h5obj: HDF5 Group or File object
        parent_path: Path to parent group
        hierarchy: HierarchyTree to populate
    """
    for key in h5obj.keys():
        obj = h5obj[key]
        obj_path = f"{parent_path}{key}" if parent_path == '/' else f"{parent_path}/{key}"

        # Check if it's a link
        link_info = h5obj.get(key, getlink=True)
        if isinstance(link_info, h5py.SoftLink):
            link = LinkInfo(
                name=key,
                path=obj_path,
                link_type='soft',
                target=link_info.path
            )
            hierarchy.links.append(link)
            continue
        elif isinstance(link_info, h5py.ExternalLink):
            link = LinkInfo(
                name=key,
                path=obj_path,
                link_type='external',
                target=f"{link_info.filename}:{link_info.path}"
            )
            hierarchy.links.append(link)
            continue

        # Process groups
        if isinstance(obj, h5py.Group):
            group = GroupInfo(
                name=key,
                path=obj_path,
                parent_path=parent_path,
                attributes=dict(obj.attrs)
            )
            hierarchy.groups.append(group)

            # Recurse into subgroups
            _traverse_group(obj, obj_path, hierarchy)

        # Process datasets
        elif isinstance(obj, h5py.Dataset):
            dataset = DatasetInfo(
                name=key,
                path=obj_path,
                parent_path=parent_path,
                shape=obj.shape,
                dtype=str(obj.dtype),
                size_bytes=obj.nbytes if hasattr(obj, 'nbytes') else 0,
                chunks=obj.chunks,
                compression=obj.compression
            )
            hierarchy.datasets.append(dataset)