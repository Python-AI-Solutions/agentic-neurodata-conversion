"""Direct test of SpikeGLX conversion with metadata merging."""

from pathlib import Path
from neuroconv.datainterfaces import SpikeGLXRecordingInterface

# Path to real data
dataset_path = Path("./real_data")
ap_bin_files = list(dataset_path.glob("*.ap.bin"))

if not ap_bin_files:
    print("ERROR: No .ap.bin file found")
    exit(1)

print(f"Found: {ap_bin_files[0]}")

# Create interface
interface = SpikeGLXRecordingInterface(file_path=str(ap_bin_files[0]))

# Get metadata from interface
interface_metadata = interface.get_metadata()
print("\n=== Interface Metadata Keys ===")
print(list(interface_metadata.keys()))

# Simulate user metadata (with all required fields)
user_metadata = {
    "Subject": {
        "subject_id": "unknown_subject",
        "species": "Homo sapiens",  # Required by NWB
        "sex": "U"  # Required by NWB (U = Unknown)
    },
    "NWBFile": {
        "session_description": "SpikeGLX recording session",
        "identifier": "test-session-001",
        "session_start_time": "2020-11-03T10:35:10Z"
    }
}

print("\n=== User Metadata Keys ===")
print(list(user_metadata.keys()))

# Test deep merge function (simplified version)
def deep_merge(base, override):
    result = dict(base)  # Convert DeepDict to regular dict
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # For Ecephys, preserve Device and ElectrodeGroup
            if key == "Ecephys":
                result_ecephys = dict(result[key])
                for k, v in value.items():
                    if k not in ("Device", "ElectrodeGroup"):
                        result_ecephys[k] = v
                result[key] = result_ecephys
            else:
                result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

# Merge metadata
merged_metadata = deep_merge(interface_metadata, user_metadata)

print("\n=== Merged Metadata Keys ===")
print(list(merged_metadata.keys()))
print(f"\nEcephys keys: {list(merged_metadata.get('Ecephys', {}).keys())}")

# Test conversion
print("\n=== Testing Conversion ===")
output_path = Path("./output/nwb_files/test_spikeglx.nwb")
output_path.parent.mkdir(parents=True, exist_ok=True)

try:
    interface.run_conversion(
        nwbfile_path=str(output_path),
        metadata=merged_metadata,
        overwrite=True
    )
    print(f"✓ SUCCESS! NWB file created: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
except Exception as e:
    print(f"✗ FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
