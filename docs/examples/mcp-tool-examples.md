# MCP Tool Implementation Examples

This document provides comprehensive examples of implementing MCP tools for the agentic neurodata conversion system.

## Basic Tool Structure

### Simple Tool Example

```python
from agentic_neurodata_conversion.mcp_server.server import mcp
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

@mcp.tool(
    name="simple_example",
    description="A simple example tool that demonstrates basic patterns"
)
async def simple_example(
    input_text: str,
    process_flag: bool = True,
    server=None
) -> Dict[str, Any]:
    """
    Simple example tool implementation.

    Args:
        input_text: Text to process
        process_flag: Whether to apply processing
        server: MCP server instance (injected automatically)

    Returns:
        Dictionary with status and results
    """
    try:
        # Basic processing logic
        if process_flag:
            result = input_text.upper()
        else:
            result = input_text

        logger.info(f"Processed text: {input_text} -> {result}")

        return {
            'status': 'success',
            'result': {
                'original': input_text,
                'processed': result,
                'flag_used': process_flag
            },
            'metadata': {
                'processing_time': 0.001,
                'tool_version': '1.0.0'
            }
        }

    except Exception as e:
        logger.error(f"Simple example tool failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }
```

## Dataset Analysis Tools

### Dataset Structure Analysis

```python
import os
from pathlib import Path
import json

@mcp.tool(
    name="dataset_structure_analysis",
    description="Analyze dataset directory structure and file types"
)
async def dataset_structure_analysis(
    dataset_dir: str,
    max_depth: int = 3,
    include_hidden: bool = False,
    server=None
) -> Dict[str, Any]:
    """
    Analyze dataset directory structure.

    Args:
        dataset_dir: Path to dataset directory
        max_depth: Maximum directory depth to analyze
        include_hidden: Whether to include hidden files/directories
        server: MCP server instance

    Returns:
        Dictionary with structure analysis results
    """
    try:
        dataset_path = Path(dataset_dir)

        if not dataset_path.exists():
            return {
                'status': 'error',
                'message': f'Dataset directory does not exist: {dataset_dir}'
            }

        if not dataset_path.is_dir():
            return {
                'status': 'error',
                'message': f'Path is not a directory: {dataset_dir}'
            }

        # Analyze structure
        structure = _analyze_directory_structure(
            dataset_path,
            max_depth,
            include_hidden
        )

        # Detect file types
        file_types = _detect_file_types(structure['files'])

        # Generate summary
        summary = {
            'total_files': len(structure['files']),
            'total_directories': len(structure['directories']),
            'file_types': file_types,
            'size_mb': structure['total_size'] / (1024 * 1024),
            'depth': structure['max_depth']
        }

        return {
            'status': 'success',
            'result': {
                'structure': structure,
                'summary': summary,
                'recommendations': _generate_structure_recommendations(summary)
            },
            'state_updates': {
                'last_analyzed_dataset': dataset_dir,
                'dataset_summary': summary
            }
        }

    except Exception as e:
        logger.error(f"Dataset structure analysis failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }

def _analyze_directory_structure(path: Path, max_depth: int, include_hidden: bool) -> Dict[str, Any]:
    """Helper function to recursively analyze directory structure."""
    files = []
    directories = []
    total_size = 0
    current_depth = 0

    def _scan_directory(dir_path: Path, depth: int):
        nonlocal total_size, current_depth
        current_depth = max(current_depth, depth)

        if depth > max_depth:
            return

        try:
            for item in dir_path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue

                if item.is_file():
                    file_size = item.stat().st_size
                    files.append({
                        'path': str(item.relative_to(path)),
                        'size': file_size,
                        'extension': item.suffix.lower(),
                        'depth': depth
                    })
                    total_size += file_size

                elif item.is_dir():
                    directories.append({
                        'path': str(item.relative_to(path)),
                        'depth': depth
                    })
                    _scan_directory(item, depth + 1)

        except PermissionError:
            logger.warning(f"Permission denied accessing: {dir_path}")

    _scan_directory(path, 0)

    return {
        'files': files,
        'directories': directories,
        'total_size': total_size,
        'max_depth': current_depth
    }

def _detect_file_types(files: list) -> Dict[str, int]:
    """Detect and count file types by extension."""
    type_counts = {}

    for file_info in files:
        ext = file_info['extension'] or 'no_extension'
        type_counts[ext] = type_counts.get(ext, 0) + 1

    return type_counts

def _generate_structure_recommendations(summary: Dict[str, Any]) -> list:
    """Generate recommendations based on structure analysis."""
    recommendations = []

    if summary['total_files'] > 1000:
        recommendations.append("Large number of files detected. Consider batch processing.")

    if summary['size_mb'] > 1000:
        recommendations.append("Large dataset detected. Ensure sufficient disk space for conversion.")

    if summary['depth'] > 5:
        recommendations.append("Deep directory structure. May need flattening for some formats.")

    # Check for common neuroscience file types
    common_neuro_extensions = {'.dat', '.bin', '.h5', '.hdf5', '.mat', '.ncs', '.nev'}
    found_extensions = set(summary['file_types'].keys())

    if found_extensions & common_neuro_extensions:
        recommendations.append("Neuroscience data files detected. Good candidate for NWB conversion.")
    else:
        recommendations.append("No common neuroscience file types detected. Manual format specification may be needed.")

    return recommendations
```

### Metadata Extraction Tool

```python
import yaml
import json
from datetime import datetime

@mcp.tool(
    name="metadata_extraction",
    description="Extract metadata from dataset files and directories"
)
async def metadata_extraction(
    dataset_dir: str,
    metadata_files: list = None,
    extract_from_filenames: bool = True,
    server=None
) -> Dict[str, Any]:
    """
    Extract metadata from various sources in the dataset.

    Args:
        dataset_dir: Path to dataset directory
        metadata_files: List of specific metadata files to check
        extract_from_filenames: Whether to extract info from filenames
        server: MCP server instance

    Returns:
        Dictionary with extracted metadata
    """
    try:
        dataset_path = Path(dataset_dir)

        if not dataset_path.exists():
            return {
                'status': 'error',
                'message': f'Dataset directory does not exist: {dataset_dir}'
            }

        # Default metadata files to look for
        if metadata_files is None:
            metadata_files = [
                'metadata.json', 'metadata.yaml', 'metadata.yml',
                'info.json', 'info.yaml', 'info.yml',
                'session_info.json', 'experiment_info.json',
                'README.md', 'README.txt'
            ]

        extracted_metadata = {}

        # Extract from metadata files
        file_metadata = _extract_from_metadata_files(dataset_path, metadata_files)
        if file_metadata:
            extracted_metadata['from_files'] = file_metadata

        # Extract from filenames
        if extract_from_filenames:
            filename_metadata = _extract_from_filenames(dataset_path)
            if filename_metadata:
                extracted_metadata['from_filenames'] = filename_metadata

        # Extract from directory structure
        structure_metadata = _extract_from_structure(dataset_path)
        if structure_metadata:
            extracted_metadata['from_structure'] = structure_metadata

        # Normalize and consolidate metadata
        normalized_metadata = _normalize_metadata(extracted_metadata)

        return {
            'status': 'success',
            'result': {
                'raw_metadata': extracted_metadata,
                'normalized_metadata': normalized_metadata,
                'extraction_summary': {
                    'sources_found': len(extracted_metadata),
                    'total_fields': len(normalized_metadata),
                    'extraction_time': datetime.now().isoformat()
                }
            },
            'state_updates': {
                'extracted_metadata': normalized_metadata,
                'metadata_sources': list(extracted_metadata.keys())
            }
        }

    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }

def _extract_from_metadata_files(dataset_path: Path, metadata_files: list) -> Dict[str, Any]:
    """Extract metadata from known metadata files."""
    metadata = {}

    for filename in metadata_files:
        file_path = dataset_path / filename
        if file_path.exists():
            try:
                if filename.endswith(('.json',)):
                    with open(file_path, 'r') as f:
                        metadata[filename] = json.load(f)
                elif filename.endswith(('.yaml', '.yml')):
                    with open(file_path, 'r') as f:
                        metadata[filename] = yaml.safe_load(f)
                elif filename.endswith(('.md', '.txt')):
                    with open(file_path, 'r') as f:
                        metadata[filename] = f.read()
            except Exception as e:
                logger.warning(f"Failed to read {filename}: {e}")

    return metadata

def _extract_from_filenames(dataset_path: Path) -> Dict[str, Any]:
    """Extract metadata from filename patterns."""
    filename_info = {
        'subjects': set(),
        'sessions': set(),
        'dates': set(),
        'file_patterns': {}
    }

    # Common patterns in neuroscience filenames
    import re

    patterns = {
        'subject': r'(?:sub|subject)[-_]?(\w+)',
        'session': r'(?:ses|session)[-_]?(\w+)',
        'date': r'(\d{4}[-_]\d{2}[-_]\d{2})',
        'time': r'(\d{2}[-_]\d{2}[-_]\d{2})',
        'run': r'(?:run)[-_]?(\d+)',
        'task': r'(?:task)[-_]?(\w+)'
    }

    for file_path in dataset_path.rglob('*'):
        if file_path.is_file():
            filename = file_path.name

            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, filename, re.IGNORECASE)
                if matches:
                    if pattern_name not in filename_info['file_patterns']:
                        filename_info['file_patterns'][pattern_name] = set()
                    filename_info['file_patterns'][pattern_name].update(matches)

    # Convert sets to lists for JSON serialization
    for key, value in filename_info['file_patterns'].items():
        filename_info['file_patterns'][key] = list(value)

    return filename_info

def _extract_from_structure(dataset_path: Path) -> Dict[str, Any]:
    """Extract metadata from directory structure."""
    structure_info = {
        'has_subjects_dir': False,
        'has_sessions_dir': False,
        'directory_patterns': []
    }

    # Look for common directory patterns
    for item in dataset_path.iterdir():
        if item.is_dir():
            dir_name = item.name.lower()

            if 'sub' in dir_name or 'subject' in dir_name:
                structure_info['has_subjects_dir'] = True

            if 'ses' in dir_name or 'session' in dir_name:
                structure_info['has_sessions_dir'] = True

            structure_info['directory_patterns'].append(dir_name)

    return structure_info

def _normalize_metadata(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize extracted metadata into standard format."""
    normalized = {
        'dataset_name': None,
        'subjects': [],
        'sessions': [],
        'experiment_description': None,
        'experimenter': None,
        'institution': None,
        'lab': None,
        'session_start_time': None,
        'file_create_date': None
    }

    # Extract common fields from various sources
    for source, data in raw_metadata.items():
        if isinstance(data, dict):
            # Look for standard fields
            for key, value in data.items():
                key_lower = key.lower()

                if 'name' in key_lower or 'title' in key_lower:
                    if not normalized['dataset_name']:
                        normalized['dataset_name'] = value

                if 'description' in key_lower:
                    if not normalized['experiment_description']:
                        normalized['experiment_description'] = value

                if 'experimenter' in key_lower or 'researcher' in key_lower:
                    if not normalized['experimenter']:
                        normalized['experimenter'] = value

                if 'institution' in key_lower or 'university' in key_lower:
                    if not normalized['institution']:
                        normalized['institution'] = value

                if 'lab' in key_lower or 'laboratory' in key_lower:
                    if not normalized['lab']:
                        normalized['lab'] = value

    # Extract from filename patterns
    if 'from_filenames' in raw_metadata:
        filename_data = raw_metadata['from_filenames']
        if 'file_patterns' in filename_data:
            patterns = filename_data['file_patterns']

            if 'subject' in patterns:
                normalized['subjects'] = patterns['subject']

            if 'session' in patterns:
                normalized['sessions'] = patterns['session']

    # Remove None values
    normalized = {k: v for k, v in normalized.items() if v is not None}

    return normalized
```

## Conversion Tools

### NeuroConv Script Generation

```python
from pathlib import Path
import tempfile
import subprocess

@mcp.tool(
    name="neuroconv_script_generation",
    description="Generate NeuroConv conversion script from metadata and file mappings"
)
async def neuroconv_script_generation(
    normalized_metadata: Dict[str, Any],
    files_map: Dict[str, str],
    output_nwb_path: str = None,
    conversion_options: Dict[str, Any] = None,
    server=None
) -> Dict[str, Any]:
    """
    Generate and optionally execute NeuroConv conversion script.

    Args:
        normalized_metadata: Normalized dataset metadata
        files_map: Mapping of data types to file paths
        output_nwb_path: Path for output NWB file
        conversion_options: Additional conversion options
        server: MCP server instance

    Returns:
        Dictionary with script generation results
    """
    try:
        # Validate inputs
        if not files_map:
            return {
                'status': 'error',
                'message': 'files_map cannot be empty'
            }

        # Generate output path if not provided
        if not output_nwb_path:
            dataset_name = normalized_metadata.get('dataset_name', 'converted_data')
            output_nwb_path = f"{dataset_name}.nwb"

        # Set default conversion options
        if conversion_options is None:
            conversion_options = {
                'compression': 'gzip',
                'compression_opts': 9,
                'shuffle': True,
                'fletcher32': True
            }

        # Generate conversion script
        script_content = _generate_neuroconv_script(
            normalized_metadata,
            files_map,
            output_nwb_path,
            conversion_options
        )

        # Save script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name

        # Validate script syntax
        validation_result = _validate_script_syntax(script_path)
        if not validation_result['valid']:
            return {
                'status': 'error',
                'message': f'Generated script has syntax errors: {validation_result["error"]}'
            }

        return {
            'status': 'success',
            'result': {
                'script_content': script_content,
                'script_path': script_path,
                'output_nwb_path': output_nwb_path,
                'validation': validation_result,
                'metadata_used': normalized_metadata,
                'files_mapped': files_map
            },
            'state_updates': {
                'generated_script_path': script_path,
                'target_nwb_path': output_nwb_path,
                'conversion_ready': True
            }
        }

    except Exception as e:
        logger.error(f"NeuroConv script generation failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }

def _generate_neuroconv_script(
    metadata: Dict[str, Any],
    files_map: Dict[str, str],
    output_path: str,
    options: Dict[str, Any]
) -> str:
    """Generate the actual NeuroConv script content."""

    # Detect data interfaces based on file extensions and types
    interfaces = _detect_neuroconv_interfaces(files_map)

    script_template = '''#!/usr/bin/env python
"""
Auto-generated NeuroConv conversion script.
Generated by agentic neurodata conversion system.
"""

from pathlib import Path
from datetime import datetime
from neuroconv import NWBConverter
{interface_imports}

class CustomNWBConverter(NWBConverter):
    """Custom converter for this dataset."""

    data_interface_classes = {{
{interface_classes}
    }}

def main():
    """Main conversion function."""

    # File paths
    source_data = {{
{source_data_mapping}
    }}

    # Conversion options
    conversion_options = {{
{conversion_options}
    }}

    # Metadata
    metadata = {{
{metadata_dict}
    }}

    # Initialize converter
    converter = CustomNWBConverter(source_data=source_data)

    # Add metadata
    converter.add_to_nwbfile_description(metadata.get('experiment_description', 'Converted dataset'))

    # Set session info
    if 'session_start_time' in metadata:
        converter.add_to_nwbfile_session_start_time(metadata['session_start_time'])
    else:
        converter.add_to_nwbfile_session_start_time(datetime.now())

    # Add experimenter info
    if 'experimenter' in metadata:
        converter.add_to_nwbfile_experimenter(metadata['experimenter'])

    if 'institution' in metadata:
        converter.add_to_nwbfile_institution(metadata['institution'])

    if 'lab' in metadata:
        converter.add_to_nwbfile_lab(metadata['lab'])

    # Run conversion
    output_path = Path("{output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Starting conversion to {{output_path}}")
    converter.run_conversion(
        nwbfile_path=output_path,
        conversion_options=conversion_options,
        overwrite=True
    )

    print(f"Conversion completed successfully!")
    print(f"Output file: {{output_path}}")
    print(f"File size: {{output_path.stat().st_size / (1024*1024):.2f}} MB")

if __name__ == "__main__":
    main()
'''

    # Format the template
    formatted_script = script_template.format(
        interface_imports=_generate_interface_imports(interfaces),
        interface_classes=_generate_interface_classes(interfaces),
        source_data_mapping=_generate_source_data_mapping(files_map),
        conversion_options=_generate_conversion_options(options),
        metadata_dict=_generate_metadata_dict(metadata),
        output_path=output_path
    )

    return formatted_script

def _detect_neuroconv_interfaces(files_map: Dict[str, str]) -> Dict[str, str]:
    """Detect appropriate NeuroConv interfaces based on file types."""
    interfaces = {}

    interface_mapping = {
        '.dat': 'SpikeGLXRecordingInterface',
        '.bin': 'SpikeGLXRecordingInterface',
        '.rhd': 'IntanRecordingInterface',
        '.rhs': 'IntanRecordingInterface',
        '.ncs': 'NeuralynxRecordingInterface',
        '.nev': 'BlackrockRecordingInterface',
        '.ns1': 'BlackrockRecordingInterface',
        '.ns2': 'BlackrockRecordingInterface',
        '.ns3': 'BlackrockRecordingInterface',
        '.ns4': 'BlackrockRecordingInterface',
        '.ns5': 'BlackrockRecordingInterface',
        '.ns6': 'BlackrockRecordingInterface',
        '.h5': 'HDF5RecordingInterface',
        '.hdf5': 'HDF5RecordingInterface',
        '.mat': 'MatlabRecordingInterface'
    }

    for data_type, file_path in files_map.items():
        file_ext = Path(file_path).suffix.lower()
        if file_ext in interface_mapping:
            interfaces[data_type] = interface_mapping[file_ext]
        else:
            # Default to generic interface
            interfaces[data_type] = 'RecordingInterface'

    return interfaces

def _generate_interface_imports(interfaces: Dict[str, str]) -> str:
    """Generate import statements for required interfaces."""
    unique_interfaces = set(interfaces.values())
    imports = []

    for interface in unique_interfaces:
        imports.append(f"from neuroconv.datainterfaces import {interface}")

    return '\n'.join(imports)

def _generate_interface_classes(interfaces: Dict[str, str]) -> str:
    """Generate interface class mapping."""
    lines = []
    for data_type, interface_class in interfaces.items():
        lines.append(f'        "{data_type}": {interface_class},')

    return '\n'.join(lines)

def _generate_source_data_mapping(files_map: Dict[str, str]) -> str:
    """Generate source data mapping."""
    lines = []
    for data_type, file_path in files_map.items():
        lines.append(f'        "{data_type}": "{file_path}",')

    return '\n'.join(lines)

def _generate_conversion_options(options: Dict[str, Any]) -> str:
    """Generate conversion options."""
    lines = []
    for key, value in options.items():
        if isinstance(value, str):
            lines.append(f'        "{key}": "{value}",')
        else:
            lines.append(f'        "{key}": {value},')

    return '\n'.join(lines)

def _generate_metadata_dict(metadata: Dict[str, Any]) -> str:
    """Generate metadata dictionary."""
    lines = []
    for key, value in metadata.items():
        if isinstance(value, str):
            lines.append(f'        "{key}": "{value}",')
        elif isinstance(value, list):
            lines.append(f'        "{key}": {value},')
        else:
            lines.append(f'        "{key}": {repr(value)},')

    return '\n'.join(lines)

def _validate_script_syntax(script_path: str) -> Dict[str, Any]:
    """Validate the generated script syntax."""
    try:
        with open(script_path, 'r') as f:
            script_content = f.read()

        # Compile to check syntax
        compile(script_content, script_path, 'exec')

        return {
            'valid': True,
            'message': 'Script syntax is valid'
        }

    except SyntaxError as e:
        return {
            'valid': False,
            'error': str(e),
            'line': e.lineno,
            'offset': e.offset
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }
```

## Evaluation Tools

### NWB File Validation

```python
import h5py
from pynwb import NWBHDF5IO
from pynwb.validate import validate

@mcp.tool(
    name="nwb_file_validation",
    description="Validate NWB file structure and content"
)
async def nwb_file_validation(
    nwb_file_path: str,
    validation_level: str = "standard",
    generate_report: bool = True,
    server=None
) -> Dict[str, Any]:
    """
    Validate NWB file for compliance and quality.

    Args:
        nwb_file_path: Path to NWB file
        validation_level: Level of validation (basic, standard, strict)
        generate_report: Whether to generate detailed report
        server: MCP server instance

    Returns:
        Dictionary with validation results
    """
    try:
        nwb_path = Path(nwb_file_path)

        if not nwb_path.exists():
            return {
                'status': 'error',
                'message': f'NWB file does not exist: {nwb_file_path}'
            }

        validation_results = {
            'file_info': _get_file_info(nwb_path),
            'structure_validation': None,
            'content_validation': None,
            'quality_checks': None
        }

        # Basic file structure validation
        structure_result = _validate_file_structure(nwb_path)
        validation_results['structure_validation'] = structure_result

        if not structure_result['valid']:
            return {
                'status': 'error',
                'message': 'File structure validation failed',
                'result': validation_results
            }

        # Content validation using PyNWB
        if validation_level in ['standard', 'strict']:
            content_result = _validate_file_content(nwb_path)
            validation_results['content_validation'] = content_result

        # Quality checks
        if validation_level == 'strict':
            quality_result = _perform_quality_checks(nwb_path)
            validation_results['quality_checks'] = quality_result

        # Generate summary
        summary = _generate_validation_summary(validation_results)

        # Generate detailed report if requested
        report = None
        if generate_report:
            report = _generate_validation_report(validation_results, summary)

        return {
            'status': 'success',
            'result': {
                'validation_results': validation_results,
                'summary': summary,
                'report': report,
                'validation_level': validation_level
            },
            'state_updates': {
                'last_validated_file': nwb_file_path,
                'validation_passed': summary['overall_valid'],
                'validation_summary': summary
            }
        }

    except Exception as e:
        logger.error(f"NWB file validation failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }

def _get_file_info(nwb_path: Path) -> Dict[str, Any]:
    """Get basic file information."""
    stat = nwb_path.stat()

    return {
        'file_path': str(nwb_path),
        'file_size_mb': stat.st_size / (1024 * 1024),
        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
    }

def _validate_file_structure(nwb_path: Path) -> Dict[str, Any]:
    """Validate basic HDF5 file structure."""
    try:
        with h5py.File(nwb_path, 'r') as f:
            # Check for required root groups
            required_groups = ['acquisition', 'analysis', 'general', 'processing', 'stimulus']
            missing_groups = []

            for group in required_groups:
                if group not in f:
                    missing_groups.append(group)

            # Check file format version
            file_format = f.attrs.get('nwb_version', 'unknown')

            return {
                'valid': len(missing_groups) == 0,
                'missing_groups': missing_groups,
                'nwb_version': file_format,
                'root_groups': list(f.keys()),
                'total_datasets': _count_datasets(f)
            }

    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

def _validate_file_content(nwb_path: Path) -> Dict[str, Any]:
    """Validate file content using PyNWB validator."""
    try:
        # Use PyNWB's built-in validator
        validation_errors = validate(str(nwb_path))

        return {
            'valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'error_count': len(validation_errors)
        }

    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

def _perform_quality_checks(nwb_path: Path) -> Dict[str, Any]:
    """Perform additional quality checks."""
    quality_issues = []

    try:
        with NWBHDF5IO(str(nwb_path), 'r') as io:
            nwbfile = io.read()

            # Check for empty datasets
            empty_datasets = _check_empty_datasets(nwbfile)
            if empty_datasets:
                quality_issues.extend(empty_datasets)

            # Check metadata completeness
            metadata_issues = _check_metadata_completeness(nwbfile)
            if metadata_issues:
                quality_issues.extend(metadata_issues)

            # Check data consistency
            consistency_issues = _check_data_consistency(nwbfile)
            if consistency_issues:
                quality_issues.extend(consistency_issues)

        return {
            'quality_score': max(0, 100 - len(quality_issues) * 10),
            'issues': quality_issues,
            'issue_count': len(quality_issues)
        }

    except Exception as e:
        return {
            'quality_score': 0,
            'error': str(e),
            'error_type': type(e).__name__
        }

def _count_datasets(h5_group) -> int:
    """Recursively count datasets in HDF5 group."""
    count = 0

    def _count_recursive(group):
        nonlocal count
        for key in group.keys():
            item = group[key]
            if hasattr(item, 'keys'):  # It's a group
                _count_recursive(item)
            else:  # It's a dataset
                count += 1

    _count_recursive(h5_group)
    return count

def _check_empty_datasets(nwbfile) -> list:
    """Check for empty datasets."""
    issues = []

    # Check acquisition data
    if hasattr(nwbfile, 'acquisition'):
        for name, data in nwbfile.acquisition.items():
            if hasattr(data, 'data') and data.data is not None:
                if hasattr(data.data, 'shape') and 0 in data.data.shape:
                    issues.append(f"Empty acquisition dataset: {name}")

    return issues

def _check_metadata_completeness(nwbfile) -> list:
    """Check for missing important metadata."""
    issues = []

    # Required fields
    if not nwbfile.session_description:
        issues.append("Missing session description")

    if not nwbfile.experimenter:
        issues.append("Missing experimenter information")

    if not nwbfile.institution:
        issues.append("Missing institution information")

    return issues

def _check_data_consistency(nwbfile) -> list:
    """Check for data consistency issues."""
    issues = []

    # Check timestamp consistency
    # This is a simplified check - real implementation would be more thorough

    return issues

def _generate_validation_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate validation summary."""
    overall_valid = True
    total_errors = 0
    total_warnings = 0

    # Check structure validation
    if results['structure_validation']:
        if not results['structure_validation']['valid']:
            overall_valid = False
            total_errors += 1

    # Check content validation
    if results['content_validation']:
        if not results['content_validation']['valid']:
            overall_valid = False
            total_errors += results['content_validation'].get('error_count', 1)

    # Check quality
    if results['quality_checks']:
        quality_score = results['quality_checks'].get('quality_score', 0)
        issue_count = results['quality_checks'].get('issue_count', 0)
        total_warnings += issue_count

        if quality_score < 70:  # Threshold for acceptable quality
            overall_valid = False

    return {
        'overall_valid': overall_valid,
        'total_errors': total_errors,
        'total_warnings': total_warnings,
        'quality_score': results.get('quality_checks', {}).get('quality_score', 100),
        'file_size_mb': results['file_info']['file_size_mb']
    }

def _generate_validation_report(results: Dict[str, Any], summary: Dict[str, Any]) -> str:
    """Generate detailed validation report."""
    report_lines = [
        "# NWB File Validation Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"Overall Valid: {'✅ Yes' if summary['overall_valid'] else '❌ No'}",
        f"Total Errors: {summary['total_errors']}",
        f"Total Warnings: {summary['total_warnings']}",
        f"Quality Score: {summary['quality_score']}/100",
        f"File Size: {summary['file_size_mb']:.2f} MB",
        ""
    ]

    # Add detailed results
    if results['structure_validation']:
        report_lines.extend([
            "## Structure Validation",
            f"Valid: {'✅' if results['structure_validation']['valid'] else '❌'}",
            f"NWB Version: {results['structure_validation'].get('nwb_version', 'unknown')}",
            ""
        ])

    if results['content_validation']:
        report_lines.extend([
            "## Content Validation",
            f"Valid: {'✅' if results['content_validation']['valid'] else '❌'}",
            f"Errors: {results['content_validation'].get('error_count', 0)}",
            ""
        ])

        if results['content_validation'].get('errors'):
            report_lines.append("### Validation Errors:")
            for error in results['content_validation']['errors']:
                report_lines.append(f"- {error}")
            report_lines.append("")

    if results['quality_checks']:
        report_lines.extend([
            "## Quality Checks",
            f"Score: {results['quality_checks'].get('quality_score', 0)}/100",
            f"Issues: {results['quality_checks'].get('issue_count', 0)}",
            ""
        ])

        if results['quality_checks'].get('issues'):
            report_lines.append("### Quality Issues:")
            for issue in results['quality_checks']['issues']:
                report_lines.append(f"- {issue}")

    return '\n'.join(report_lines)
```

These examples demonstrate comprehensive MCP tool implementations covering dataset analysis, metadata extraction, conversion script generation, and NWB file validation. Each tool follows the established patterns for error handling, logging, state management, and structured responses.
