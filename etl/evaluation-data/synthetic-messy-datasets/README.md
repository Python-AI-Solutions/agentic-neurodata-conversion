# Synthetic Messy Datasets

This directory contains synthetic "messy" datasets created for testing and
evaluation of the LLM conversion tool.

## Directory Structure

```
synthetic-messy-datasets/
├── datasets/           # Messy dataset files
│   ├── level-1/       # Simple issues (single problem type)
│   ├── level-2/       # Moderate complexity (2-3 issues)
│   └── level-3/       # Complex (multiple interrelated issues)
├── ground-truth/       # Original clean NWB files
├── transformations/    # Applied transformation logs
└── metrics/           # Evaluation metrics for each dataset
```

## Dataset Categories

### Level 1 - Simple Issues

- Missing metadata fields
- Incorrect units
- Wrong file extensions
- Simple naming inconsistencies

### Level 2 - Moderate Complexity

- Multiple metadata issues
- Structural problems + metadata
- Time format inconsistencies
- Missing relationships

### Level 3 - Complex Issues

- Deeply nested structural problems
- Multiple format conversions needed
- Complex metadata inference required
- Ambiguous data relationships

## File Naming Convention

`<original_dandi_id>_<transformation_type>_<complexity_level>_<version>`

Example: `000001_metadata_missing_L1_v1`

## Ground Truth Mapping

Each messy dataset has a corresponding entry in `ground-truth/` containing:

- Original clean NWB file
- Transformation log
- Expected conversion output
- Validation criteria

## Usage

These datasets are used by:

- `tests/evaluation-tests/` for automated testing
- Benchmarking scripts for model comparison
- Development testing during implementation

## Generation

Created by: `etl/workflows/create-synthetic-messy-datasets/`

## Storage

Large datasets are managed with DataLad and stored on gin.g-node.org
