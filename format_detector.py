# tools/format_detector.py
from pathlib import Path
import fnmatch

SIGNATURES = [
    # (glob, interface_name, modality, hints)
    ("**/*.bin",   "SpikeGLXRecordingInterface", "ephys_recording", {"folder_param":"folder_path"}),
    ("**/*.rhd",   "IntanRecordingInterface",    "ephys_recording", {"file_param":"file_path"}),
    ("**/*.continuous", "OpenEphysRecordingInterface", "ephys_recording", {"folder_param":"folder_path"}),
    ("**/*.plx",   "PlexonRecordingInterface",   "ephys_recording", {"file_param":"file_path"}),
    ("**/*.ns6",   "NeuralynxRecordingInterface","ephys_recording", {"folder_param":"folder_path"}),
    ("**/*dlc*.csv","DeepLabCutInterface",       "behavior_tracking",{"file_param":"file_path"}),
    ("**/*sleap*.h5","SLEAPInterface",           "behavior_tracking",{"file_param":"file_path"}),
    ("**/*.tif",   "ScanImageImagingInterface",  "optical_imaging",  {"folder_param":"folder_path"}),
    ("**/*.tiff",  "ScanImageImagingInterface",  "optical_imaging",  {"folder_param":"folder_path"}),
    ("**/*.mes",   "MesoscopeImagingInterface",  "optical_imaging",  {"folder_param":"folder_path"}),
    ("**/*.tsq",   "TdtRecordingInterface",      "ephys_recording",  {"folder_param":"folder_path"}),
    # add more as you learn a lab…
]

def detect_formats(root: Path):
    matches = []
    for glob, iface, modality, hints in SIGNATURES:
        for f in root.glob(glob):
            matches.append({
                "path": str(f if f.is_file() else f.parent),
                "interface": iface,
                "modality": modality,
                "hints": hints
            })
    # de-duplicate by parent folder or file
    uniq = {(m["interface"], Path(m["path"]).resolve()): m for m in matches}
    return list(uniq.values())
