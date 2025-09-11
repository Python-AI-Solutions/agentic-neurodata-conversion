# Input Data

This directory contains raw neuroscience datasets used for testing, development,
and validation of the agentic conversion pipeline.

## Purpose

The input-data directory serves as the central repository for:

- **Raw Datasets**: Unprocessed neuroscience data in various formats
- **Conversion Examples**: Real-world datasets from CatalystNeuro conversions
- **Test Cases**: Curated datasets for testing specific conversion scenarios
- **Format Samples**: Representative examples of different data acquisition
  systems

## Directory Structure

```
input-data/
├── catalystneuro-conversions/    # CatalystNeuro conversion repositories
│   ├── IBL-to-nwb/              # International Brain Laboratory data
│   ├── buzsaki-lab-to-nwb/      # Buzsaki Lab datasets
│   ├── allen-oephys-to-nwb/     # Allen Institute optical physiology
│   └── ...                      # Additional lab-specific conversions
└── [future directories for other data sources]
```

## Data Sources

### CatalystNeuro Conversions

The `catalystneuro-conversions/` subdirectory contains conversion repositories
from various neuroscience laboratories. These provide:

- **Real-world Examples**: Actual conversion scripts used in production
- **Format Diversity**: Coverage of multiple data acquisition systems
- **Best Practices**: Proven approaches to common conversion challenges
- **Metadata Templates**: Standard metadata structures for different experiment
  types

### Supported Data Formats

The input datasets cover a wide range of neuroscience data formats:

- **Electrophysiology**: SpikeGLX, Open Ephys, Blackrock, Neuralynx
- **Optical Physiology**: Suite2p, CaImAn, CNMF-E
- **Behavioral Data**: DeepLabCut, SLEAP, custom tracking systems
- **Stimulation Data**: Optogenetics, electrical stimulation protocols

## DataLad Integration

All input data is managed through DataLad for:

- **Version Control**: Track changes to datasets over time
- **Efficient Storage**: Large files stored in git-annex with metadata in git
- **Distributed Access**: Data available from multiple storage backends
- **Provenance Tracking**: Complete history of data origins and modifications

### Working with Input Data

```python
import datalad.api as dl

# Install a specific conversion repository
dl.install(dataset=".", path="etl/input-data/catalystneuro-conversions/IBL-to-nwb")

# Get actual data files (may be large)
dl.get(path="etl/input-data/catalystneuro-conversions/IBL-to-nwb/src/ibl_to_nwb/datainterfaces")

# Check what data is available
status = dl.status(dataset="etl/input-data", return_type='list')
```

## Usage Guidelines

1. **Read-Only Access**: Treat input data as immutable reference material
2. **Copy for Modification**: Create working copies in appropriate directories
3. **Document Sources**: Maintain clear attribution for all datasets
4. **Respect Licenses**: Follow licensing terms for each dataset
5. **Use DataLad**: Always use DataLad API for data operations

## Adding New Datasets

To add new input datasets:

1. **Create Subdirectory**: Organize by source or format type
2. **Add DataLad Dataset**: Use `dl.install()` for external repositories
3. **Document Structure**: Include README with dataset description
4. **Update Index**: Add entry to this README file
5. **Commit Changes**: Use DataLad to track additions

## Integration with Conversion Pipeline

Input data integrates with the conversion pipeline through:

- **Format Detection**: Automated identification of data acquisition systems
- **Metadata Extraction**: Parsing of experimental protocols and parameters
- **Conversion Templates**: Mapping to appropriate NeuroConv interfaces
- **Validation**: Testing converted outputs against known good examples

## Quality Assurance

All input datasets should include:

- **Documentation**: Clear description of experimental setup
- **Metadata**: Complete parameter specifications
- **Format Information**: Details about data acquisition system
- **Expected Outputs**: Reference NWB files when available

## Related Resources

- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [CatalystNeuro GitHub](https://github.com/catalystneuro)
- [DataLad Handbook](https://handbook.datalad.org/)
- [ETL Main README](../README.md)
