# Create Synthetic Messy Datasets

This workflow generates synthetic "messy" datasets for testing the LLM
conversion tool.

## Purpose

- Take clean DANDI datasets as ground truth
- Programmatically introduce common data issues
- Create test cases with known solutions
- Enable quantitative evaluation of conversion quality

## Types of Data Issues Introduced

1. **Metadata Issues**
   - Missing required fields
   - Inconsistent naming conventions
   - Incorrect units or data types
   - Time format inconsistencies

2. **Structural Issues**
   - Non-standard file organization
   - Mixed data formats
   - Incorrect file extensions
   - Nested directory structures

3. **Content Issues**
   - Corrupted timestamps
   - Missing electrode information
   - Incomplete behavioral data
   - Misaligned trial structures

## Workflow Steps

1. Download clean NWB files from DANDI
2. Apply transformation functions to introduce issues
3. Document the transformations applied
4. Save messy datasets with ground truth mapping

## Output

- Synthetic datasets: `etl/evaluation-data/synthetic-messy-datasets/`
- Ground truth mappings:
  `etl/evaluation-data/synthetic-messy-datasets/ground-truth/`
- Transformation logs: `etl/evaluation-data/synthetic-messy-datasets/logs/`

## Usage

```bash
pixi run python create_synthetic_datasets.py --dandi-id <dandiset_id>
```

## Dependencies

- dandi
- pynwb
- numpy
- pandas
