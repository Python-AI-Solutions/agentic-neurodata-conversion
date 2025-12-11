"""Central registry of supported NeuroConv formats for this project.

This project uses human-friendly, disambiguated format names (e.g. `BlackrockRecording`
vs `BlackrockSorting`) as the internal "format" identifier.

The mapping is kept in one place so:
- format detection can validate LLM outputs against the supported set
- conversion can map the chosen format to the correct NeuroConv class name
"""

from __future__ import annotations

FORMAT_TO_NEUROCONV_CLASS: dict[str, str] = {
    # Electrophysiology Recording (24 formats)
    "AlphaOmegaRecording": "AlphaOmegaRecordingInterface",
    "Axon": "AbfInterface",  # .abf files - Axon Instruments pCLAMP
    "AxonRecording": "AxonRecordingInterface",
    "AxonaRecording": "AxonaRecordingInterface",
    "AxonaUnitRecording": "AxonaUnitRecordingInterface",
    "BiocamRecording": "BiocamRecordingInterface",
    "BlackrockRecording": "BlackrockRecordingInterface",
    "CellExplorerRecording": "CellExplorerRecordingInterface",
    "EDFRecording": "EDFRecordingInterface",
    "IntanRecording": "IntanRecordingInterface",
    "MCSRawRecording": "MCSRawRecordingInterface",
    "MEArecRecording": "MEArecRecordingInterface",
    "MaxOneRecording": "MaxOneRecordingInterface",
    "NeuralynxRecording": "NeuralynxRecordingInterface",
    "Neuropixels": "SpikeGLXRecordingInterface",  # Alias for SpikeGLX
    "NeuroScopeRecording": "NeuroScopeRecordingInterface",
    "OpenEphys": "OpenEphysRecordingInterface",
    "OpenEphysBinary": "OpenEphysBinaryRecordingInterface",
    "OpenEphysLegacyRecording": "OpenEphysLegacyRecordingInterface",
    "Plexon2Recording": "Plexon2RecordingInterface",
    "PlexonRecording": "PlexonRecordingInterface",
    "Spike2Recording": "Spike2RecordingInterface",
    "SpikeGLX": "SpikeGLXRecordingInterface",
    "SpikeGadgetsRecording": "SpikeGadgetsRecordingInterface",
    "TdtRecording": "TdtRecordingInterface",
    "WhiteMatterRecording": "WhiteMatterRecordingInterface",
    # Spike Sorting (8 formats)
    "BlackrockSorting": "BlackrockSortingInterface",
    "CellExplorerSorting": "CellExplorerSortingInterface",
    "KiloSortSorting": "KiloSortSortingInterface",
    "NeuralynxSorting": "NeuralynxSortingInterface",
    "NeuroScopeSorting": "NeuroScopeSortingInterface",
    "OpenEphysSorting": "OpenEphysSortingInterface",
    "PhySorting": "PhySortingInterface",
    "PlexonSorting": "PlexonSortingInterface",
    # Imaging (13 formats)
    "BrukerTiffMultiPlaneImaging": "BrukerTiffMultiPlaneImagingInterface",
    "BrukerTiffSinglePlaneImaging": "BrukerTiffSinglePlaneImagingInterface",
    "FemtonicsImaging": "FemtonicsImagingInterface",
    "Hdf5Imaging": "Hdf5ImagingInterface",
    "InscopixImaging": "InscopixImagingInterface",
    "MicroManagerTiffImaging": "MicroManagerTiffImagingInterface",
    "MiniscopeImaging": "MiniscopeImagingInterface",
    "SbxImaging": "SbxImagingInterface",
    "ScanImageImaging": "ScanImageImagingInterface",
    "ScanImageLegacyImaging": "ScanImageLegacyImagingInterface",
    "ScanImageMultiFileImaging": "ScanImageMultiFileImagingInterface",
    "ThorImaging": "ThorImagingInterface",
    "TiffImaging": "TiffImagingInterface",
    # Segmentation (7 formats)
    "CaimanSegmentation": "CaimanSegmentationInterface",
    "CnmfeSegmentation": "CnmfeSegmentationInterface",
    "ExtractSegmentation": "ExtractSegmentationInterface",
    "InscopixSegmentation": "InscopixSegmentationInterface",
    "MinianSegmentation": "MinianSegmentationInterface",
    "SimaSegmentation": "SimaSegmentationInterface",
    "Suite2pSegmentation": "Suite2pSegmentationInterface",
    # Behavior/Video (11 formats)
    "AxonaPositionData": "AxonaPositionDataInterface",
    "DeepLabCut": "DeepLabCutInterface",
    "ExternalVideo": "ExternalVideoInterface",
    "FicTracData": "FicTracDataInterface",
    "InternalVideo": "InternalVideoInterface",
    "LightningPoseData": "LightningPoseDataInterface",
    "MiniscopeBehavior": "MiniscopeBehaviorInterface",
    "NeuralynxNvt": "NeuralynxNvtInterface",
    "SLEAP": "SLEAPInterface",
    "Video": "VideoInterface",
    "Audio": "AudioInterface",
    # LFP/Analog/Other (14 formats)
    "AxonaLFPData": "AxonaLFPDataInterface",
    "CellExplorerLFP": "CellExplorerLFPInterface",
    "CsvTimeIntervals": "CsvTimeIntervalsInterface",
    "EDFAnalog": "EDFAnalogInterface",
    "ExcelTimeIntervals": "ExcelTimeIntervalsInterface",
    "Image": "ImageInterface",
    "IntanAnalog": "IntanAnalogInterface",
    "MedPC": "MedPCInterface",
    "NeuroScopeLFP": "NeuroScopeLFPInterface",
    "OpenEphysBinaryAnalog": "OpenEphysBinaryAnalogInterface",
    "PlexonLFP": "PlexonLFPInterface",
    "SpikeGLXNIDQ": "SpikeGLXNIDQInterface",
    "TDTFiberPhotometry": "TDTFiberPhotometryInterface",
    # Converters (7 formats)
    "BrukerTiffMultiPlane": "BrukerTiffMultiPlaneConverter",
    "BrukerTiffSinglePlane": "BrukerTiffSinglePlaneConverter",
    "LightningPose": "LightningPoseConverter",
    "Miniscope": "MiniscopeConverter",
    "SortedRecording": "SortedRecordingConverter",
    "SortedSpikeGLX": "SortedSpikeGLXConverter",
    "SpikeGLXConverter": "SpikeGLXConverterPipe",
}

SUPPORTED_FORMATS: list[str] = sorted(FORMAT_TO_NEUROCONV_CLASS.keys())
