"""Test SpikeGLX metadata extraction."""

from pathlib import Path
from neuroconv.datainterfaces import SpikeGLXRecordingInterface

# Path to real data
dataset_path = Path("./real_data")
ap_bin_files = list(dataset_path.glob("*.ap.bin"))

if not ap_bin_files:
    print("ERROR: No .ap.bin file found")
    exit(1)

print(f"Found {len(ap_bin_files)} .ap.bin file(s)")
print(f"Using: {ap_bin_files[0]}")

# Create interface
interface = SpikeGLXRecordingInterface(file_path=str(ap_bin_files[0]))

# Get metadata
metadata = interface.get_metadata()

# Print structure
print("\n=== Metadata Structure ===")
for key in metadata.keys():
    print(f"\n{key}:")
    if isinstance(metadata[key], dict):
        for subkey in metadata[key].keys():
            print(f"  {subkey}: {type(metadata[key][subkey])}")
            if subkey == "Ecephys" and isinstance(metadata[key][subkey], dict):
                for ecephys_key in metadata[key][subkey].keys():
                    print(f"    {ecephys_key}: {metadata[key][subkey][ecephys_key]}")
    else:
        print(f"  {metadata[key]}")

# Check for ElectrodeGroup
if "Ecephys" in metadata:
    print("\n=== Ecephys Metadata ===")
    print(f"Keys: {list(metadata['Ecephys'].keys())}")
    if "ElectrodeGroup" in metadata["Ecephys"]:
        print(f"ElectrodeGroup: {metadata['Ecephys']['ElectrodeGroup']}")
    if "Device" in metadata["Ecephys"]:
        print(f"Device: {metadata['Ecephys']['Device']}")
