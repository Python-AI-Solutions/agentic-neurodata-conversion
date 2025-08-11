# LLM-Guided Data Conversion Project

An LLM-assisted tool for converting experimental neuroscience data to standardized formats (primarily NWB), leveraging AI to guide data conversion, prompt for metadata, and validate outputs.

## 🚀 Quick Start

### Prerequisites

- Python 3.9-3.13
- [pixi](https://pixi.sh/latest/) package manager
- git

### Installation & Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd llm-guided-conversion
```

2. **Install dependencies with pixi**:
```bash
pixi install
```

3. **Initialize as DataLad dataset** (for version control and data management):
```bash
# CRITICAL: Set up proper git-annex configuration FIRST
cat > .gitattributes << 'EOF'
# Only use annex for large data files (>10MB)
* annex.backend=MD5E
**/.git* annex.largefiles=nothing

# Keep all development files in git (not annex)
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.yml annex.largefiles=nothing
*.yaml annex.largefiles=nothing
*.toml annex.largefiles=nothing
*.json annex.largefiles=nothing
*.sh annex.largefiles=nothing
*.cfg annex.largefiles=nothing
*.ini annex.largefiles=nothing
*.rst annex.largefiles=nothing
*.ipynb annex.largefiles=nothing
.gitignore annex.largefiles=nothing
.gitmodules annex.largefiles=nothing
.pre-commit-config.yaml annex.largefiles=nothing

# Default: only annex files larger than 10MB
* annex.largefiles=(largerthan=10mb)
EOF

# Initialize DataLad dataset with text2git configuration
pixi run python -c "
import datalad.api as dl
dl.create(
    path='.',
    cfg_proc='text2git',
    description='LLM-guided conversion project',
    force=True
)
dl.save(message='Initial DataLad setup', recursive=True)
"

# Verify files are not symlinks (should show regular files)
ls -la *.md *.toml
```

4. **Install CatalystNeuro conversions** (optional):
```bash
pixi run python scripts/install_catalystneuro_conversions.py
```

## 📁 Project Structure

```
nwb-conversion-project/
├── etl/                                    # ETL (Extract, Transform, Load) pipeline
│   ├── workflows/                          # Data processing workflows
│   │   ├── condense_nwb_spec/             # NWB specification condensation
│   │   ├── condense_nwb_linkml_spec/      # LinkML specification condensation
│   │   ├── create_synthetic_datasets/      # Synthetic test data generation
│   │   └── create_evaluation_rubric/       # Evaluation criteria
│   │
│   ├── data/                               # DataLad-managed data repository
│   │   ├── specifications/                 # Format specifications
│   │   │   ├── nwb/                       # NWB core specifications
│   │   │   └── nwb-linkml/                # LinkML representations
│   │   │
│   │   ├── conversions/                    # CatalystNeuro conversion tools
│   │   │   ├── cookiecutter-my-lab-to-nwb-template/
│   │   │   ├── IBL-to-nwb/
│   │   │   ├── ahrens-lab-to-nwb/
│   │   │   └── [50+ lab-specific conversions...]
│   │   │
│   │   └── pre-existing-conversions/       # Reference conversions
│   │
│   ├── prompt-input-data/                  # LLM prompt engineering data
│   │   ├── condensed_nwb_spec/
│   │   └── condensed_nwb_linkml_spec/
│   │
│   └── evaluation-data/                    # Test and benchmark datasets
│       └── synthetic_messy_datasets/
│
├── llm-assisted-conversion-tool/           # AI-powered conversion assistant
│   ├── prompt/                             # LLM prompts and templates
│   └── cli/                                # Command-line interface
│
├── tests/                                   # Testing suite
│   ├── unit/                               # Unit tests
│   └── evaluation/                         # Integration and evaluation tests
│
├── pixi.toml                               # Pixi package configuration
├── setup_project.sh                        # Main setup script
├── install_catalystneuro_conversions.py   # Conversion installer
└── conversions_summary.json               # Generated conversion inventory
```

## 🧠 Available CatalystNeuro Conversions

The project includes 50+ lab-specific NWB conversion implementations:

### Notable Conversions

- **IBL-to-nwb**: International Brain Laboratory data
- **buzsaki-lab-to-nwb**: Buzsáki Lab hippocampal recordings
- **allen-institute-to-nwb**: Allen Institute datasets
- **janelia-to-nwb**: Janelia Research Campus data

### Conversion Categories

1. **Electrophysiology**: Neuropixels, tetrodes, silicon probes
2. **Calcium Imaging**: Two-photon, miniscope data
3. **Behavior**: Video tracking, task events
4. **Multimodal**: Combined ephys + imaging + behavior

## 📦 DataLad Integration

This project uses DataLad for reproducible data management. **Important**: Always use the Python API for DataLad operations, not CLI commands.

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

## 🔧 Usage Examples

### 1. Create a New Conversion

Use the cookiecutter template:

```bash
cd etl/data/conversions
pixi run cookiecutter cookiecutter-my-lab-to-nwb-template
```

### 2. Run an Existing Conversion

```python
from neuroconv import NWBConverter

# Import specific lab converter
from ibl_to_nwb import IBLConverter

# Configure and run
converter = IBLConverter(source_data={...})
converter.run_conversion(nwbfile_path="output.nwb")
```

### 3. Install Specific Conversions

```bash
pixi run python install_catalystneuro_conversions.py \
    --conversions IBL-to-nwb buzsaki-lab-to-nwb \
    --install-deps
```

## 🤖 LLM-Assisted Conversion

The project supports AI-powered data conversion assistance:

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

### LinkML Integration
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

## 📝 Development Workflow

1. **Setup Environment**
   ```bash
   ./setup_project.sh
   ```

2. **Explore Conversions**
   ```bash
   ls etl/data/conversions/
   cat conversions_summary.json
   ```

3. **Start Jupyter Lab**
   ```bash
   pixi run jupyter
   ```

4. **Develop Conversion**
   - Use cookiecutter template
   - Implement interfaces
   - Test with sample data
   - Validate NWB output

## 🔗 Resources

### Documentation
- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [NWB Overview](https://www.nwb.org/)
- [PyNWB API](https://pynwb.readthedocs.io/)
- [DataLad Handbook](https://handbook.datalad.org/)

### Tutorials
- [NWB Tutorials](https://nwb.org/tutorials/)
- [CatalystNeuro Examples](https://github.com/catalystneuro/neuroconv/tree/main/docs/conversion_examples_gallery)

### Community
- [NWB Help Desk](https://github.com/NeurodataWithoutBorders/helpdesk)
- [NeuroConv Issues](https://github.com/catalystneuro/neuroconv/issues)

## 🎯 Project Goals

1. **Standardization**: Convert diverse neuroscience data to NWB format
2. **Automation**: Reduce manual effort in data conversion
3. **Validation**: Ensure data quality and compliance
4. **Accessibility**: Make conversions easy for researchers
5. **Reproducibility**: Track data provenance with DataLad

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your conversion
4. Add tests
5. Submit a pull request

## 📄 License

This project follows the licensing of the included CatalystNeuro tools (typically BSD-3-Clause or MIT).

## 🙏 Acknowledgments

- CatalystNeuro team for conversion tools
- NWB community for the standard
- DataLad team for data management tools
- Contributors to individual lab conversions