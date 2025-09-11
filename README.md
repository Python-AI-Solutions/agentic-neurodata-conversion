# Agentic Neurodata Conversion Project

An agentic tool for converting neuroscience data to standardized formats
(initially NWB), leveraging LLMs and agentic workflows to guide data conversion,
prompt for metadata, and validate outputs.

## 🚀 Quick Start

### Prerequisites

- Python 3.9-3.13
- [pixi](https://pixi.sh/latest/) package manager
- git

### Installation & Setup

#### Option 1: Clone with DataLad (Recommended - includes data management)

```bash
# Clone from GitHub (code only)
datalad clone https://github.com/Python-AI-Solutions/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion

# Or clone from GIN (includes annex capabilities)
gin get leej3/agentic-neurodata-conversion
# or
datalad clone https://gin.g-node.org/leej3/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion
```

#### Option 2: Clone with git (basic)

```bash
git clone https://github.com/Python-AI-Solutions/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion
```

2. **Install dependencies with pixi**:

```bash
pixi install
```

## 📦 DataLad Integration & Data Storage

This project uses DataLad for reproducible data management with dual repository
setup:

- **GitHub**: Code, documentation, and configuration files
- **GIN (G-Node Infrastructure)**: Large data files and annex content

### Repository Locations

- **GitHub**:
  <https://github.com/Python-AI-Solutions/agentic-neurodata-conversion>
- **GIN**: <https://gin.g-node.org/leej3/agentic-neurodata-conversion>

**Important**: Always use the Python API for DataLad operations, not CLI
commands.

```python
# Using DataLad Python API (recommended)
import datalad.api as dl

# Check dataset status
status = dl.status(dataset=".", return_type='list')

# Save changes
dl.save(dataset=".", message="Update project files", recursive=True)

# Install subdatasets (e.g., conversion repositories)
dl.install(dataset=".", path="etl/input-data/catalystneuro-conversions/IBL-to-nwb")

# Get specific files from annexed content
dl.get(path="path/to/large/file.nwb")

# Add a new subdataset
dl.install(dataset=".", path="path/to/new/subdataset", source="https://github.com/org/repo")
```

### Working with Subdatasets

If subdatasets haven't been properly initialized:

```python
import datalad.api as dl

# Install all subdatasets recursively
dl.install(dataset=".", recursive=True, get_data=False)

# Or install specific subdatasets
subdatasets = [
    "etl/input-data/catalystneuro-conversions/IBL-to-nwb",
    "etl/input-data/catalystneuro-conversions/buzsaki-lab-to-nwb"
]
for subds in subdatasets:
    dl.install(dataset=".", path=subds)
```

### Working with Large Data Files

Large files (>10MB) are managed via git-annex and stored on GIN:

```python
import datalad.api as dl

# Get large files from GIN
dl.get(path="path/to/large/file.nwb")

# Push large files to GIN (requires write access)
dl.push(to="gin", path="path/to/large/file.nwb")

# Or use git-annex directly
# git annex copy --to gin path/to/large/file.nwb
```

## 🤖 Agentic Conversion

The project supports agentic AI-powered data conversion:

1. **Automated Metadata Extraction**: Parse experimental protocols
2. **Schema Mapping**: Map custom formats to NWB
3. **Validation**: Ensure compliance with NWB standards
4. **Interactive Guidance**: Step-by-step conversion support

## 📊 Data Specifications

### NWB Core Schema

- TimeSeries data
- ElectricalSeries for ephys
- ImageSeries for imaging
- SpatialSeries for tracking

### LinkML Integration (stretch goal)

- Generate JSON Schema from LinkML
- Validate metadata structure
- Type-safe conversions

## 🧪 Testing

Run the test suite:

```bash
# Unit tests
pixi run pytest tests/unit/

# Evaluation tests
pixi run pytest tests/evaluation/

# Specific conversion test
pixi run pytest tests/unit/test_ibl_conversion.py
```

## 🔗 Resources

### Documentation

- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [NWB Overview](https://www.nwb.org/)
- [PyNWB API](https://pynwb.readthedocs.io/)
- [DataLad Handbook](https://handbook.datalad.org/)

### Tutorials

- [NWB Tutorials](https://nwb.org/tutorials/)
- [CatalystNeuro Examples](https://github.com/catalystneuro/neuroconv/tree/main/docs/conversion_examples_gallery)

## 🎯 Project Goals

1. **Standardization**: Prototype converting diverse neuroscience data to NWB
   format using agentic workflows.
2. **Automation**: Reduce manual effort in data conversion
3. **Validation**: Ensure data quality, standards and some. Valid NWB doesn't
   mean useful data.
4. **Accessibility**: Make conversions easy for researchers and eventually try
   to catch omitted metadata early in the process.
5. **Reproducibility**: Track data provenance with DataLad

## 📄 License

This project follows the licensing of the included CatalystNeuro tools
(typically BSD-3-Clause or MIT).

## 🙏 Acknowledgments

- CatalystNeuro team for conversion tools, and open source conversions. This
  approach doesn't work without that openly shared expertise.
- NWB community for the standard
- DataLad team for data management tools
