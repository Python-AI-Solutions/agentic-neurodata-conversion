#!/usr/bin/env python3
"""
Analyze the structure of the NWB file to understand what properties we can extract.
"""

import pynwb
from pathlib import Path
import sys

def analyze_nwb_file(nwb_path):
    """Analyze the structure and content of an NWB file."""

    print("🧬 Analyzing NWB File Structure")
    print("=" * 50)
    print(f"📁 File: {nwb_path}")

    try:
        with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
            nwb_file = io.read()

            print(f"✅ Successfully opened NWB file")
            print()

            # Basic file info
            print("📊 Basic File Information:")
            print(f"├─ Session ID: {nwb_file.session_id}")
            print(f"├─ Session Description: {nwb_file.session_description}")
            print(f"├─ Session Start Time: {nwb_file.session_start_time}")
            print(f"├─ Timestamps Reference Time: {nwb_file.timestamps_reference_time}")
            print(f"├─ Identifier: {nwb_file.identifier}")
            print()

            # Subject information
            if nwb_file.subject:
                print("🐭 Subject Information:")
                print(f"├─ Subject ID: {nwb_file.subject.subject_id}")
                print(f"├─ Description: {nwb_file.subject.description}")
                print(f"├─ Species: {nwb_file.subject.species}")
                print(f"├─ Sex: {nwb_file.subject.sex}")
                print(f"├─ Age: {nwb_file.subject.age}")
                print(f"├─ Weight: {nwb_file.subject.weight}")
                print(f"├─ Date of Birth: {nwb_file.subject.date_of_birth}")
                print()

            # Institution and lab info
            print("🏢 Institution & Lab:")
            print(f"├─ Institution: {nwb_file.institution}")
            print(f"├─ Lab: {nwb_file.lab}")
            print(f"├─ Experimenter: {nwb_file.experimenter}")
            print(f"├─ Experiment Description: {nwb_file.experiment_description}")
            print()

            # Acquisition data
            print("📡 Acquisition Data:")
            if nwb_file.acquisition:
                for name, data in nwb_file.acquisition.items():
                    print(f"├─ {name}: {type(data).__name__}")
                    if hasattr(data, 'description'):
                        print(f"│  └─ Description: {data.description}")
                    if hasattr(data, 'data') and hasattr(data.data, 'shape'):
                        print(f"│  └─ Shape: {data.data.shape}")
                    if hasattr(data, 'rate'):
                        print(f"│  └─ Rate: {data.rate} Hz")
            else:
                print("├─ No acquisition data found")
            print()

            # Processing modules
            print("⚙️ Processing Modules:")
            if nwb_file.processing:
                for name, module in nwb_file.processing.items():
                    print(f"├─ {name}: {module.description}")
                    for data_name, data_obj in module.data_interfaces.items():
                        print(f"│  └─ {data_name}: {type(data_obj).__name__}")
            else:
                print("├─ No processing modules found")
            print()

            # Devices
            print("🔧 Devices:")
            if nwb_file.devices:
                for name, device in nwb_file.devices.items():
                    print(f"├─ {name}: {device.description}")
            else:
                print("├─ No devices found")
            print()

            # Electrode groups
            print("🔌 Electrode Groups:")
            if nwb_file.electrode_groups:
                for name, group in nwb_file.electrode_groups.items():
                    print(f"├─ {name}:")
                    print(f"│  ├─ Description: {group.description}")
                    print(f"│  ├─ Location: {group.location}")
                    print(f"│  └─ Device: {group.device.name if group.device else 'None'}")
            else:
                print("├─ No electrode groups found")
            print()

            # Electrodes table
            print("📊 Electrodes Table:")
            if nwb_file.electrodes is not None:
                print(f"├─ Number of electrodes: {len(nwb_file.electrodes)}")
                print(f"├─ Columns: {list(nwb_file.electrodes.colnames)}")
                if len(nwb_file.electrodes) > 0:
                    print("├─ Sample electrode data:")
                    for i, row in enumerate(nwb_file.electrodes.to_dataframe().head(3).iterrows()):
                        print(f"│  └─ Electrode {i}: {dict(row[1])}")
            else:
                print("├─ No electrodes table found")
            print()

            # Units (if present)
            print("🧠 Units/Neurons:")
            if nwb_file.units is not None:
                print(f"├─ Number of units: {len(nwb_file.units)}")
                print(f"├─ Columns: {list(nwb_file.units.colnames)}")
            else:
                print("├─ No units found")
            print()

            # Trials (if present)
            print("🎯 Trials:")
            if nwb_file.trials is not None:
                print(f"├─ Number of trials: {len(nwb_file.trials)}")
                print(f"├─ Columns: {list(nwb_file.trials.colnames)}")
            else:
                print("├─ No trials found")
            print()

            # Generate extractable properties summary
            print("🔍 Extractable Properties Summary:")
            extractable = get_extractable_properties(nwb_file)
            for category, properties in extractable.items():
                print(f"├─ {category}:")
                for prop, value in properties.items():
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"│  └─ {prop}: {value}")
            print()

            return extractable

    except Exception as e:
        print(f"❌ Error analyzing NWB file: {e}")
        return None

def get_extractable_properties(nwb_file):
    """Extract all meaningful properties from NWB file for knowledge graph."""

    extractable = {
        "session": {},
        "subject": {},
        "institution": {},
        "data_summary": {},
        "technical": {}
    }

    # Session properties
    extractable["session"]["session_id"] = nwb_file.session_id
    extractable["session"]["session_description"] = nwb_file.session_description
    extractable["session"]["session_start_time"] = str(nwb_file.session_start_time)
    extractable["session"]["identifier"] = nwb_file.identifier

    # Subject properties
    if nwb_file.subject:
        extractable["subject"]["subject_id"] = nwb_file.subject.subject_id
        extractable["subject"]["species"] = nwb_file.subject.species
        extractable["subject"]["sex"] = nwb_file.subject.sex
        extractable["subject"]["age"] = nwb_file.subject.age
        extractable["subject"]["weight"] = nwb_file.subject.weight
        if nwb_file.subject.description:
            extractable["subject"]["description"] = nwb_file.subject.description

    # Institution properties
    extractable["institution"]["institution"] = nwb_file.institution
    extractable["institution"]["lab"] = nwb_file.lab
    extractable["institution"]["experimenter"] = str(nwb_file.experimenter) if nwb_file.experimenter else None
    extractable["institution"]["experiment_description"] = nwb_file.experiment_description

    # Data summary
    extractable["data_summary"]["num_electrodes"] = len(nwb_file.electrodes) if nwb_file.electrodes else 0
    extractable["data_summary"]["num_units"] = len(nwb_file.units) if nwb_file.units else 0
    extractable["data_summary"]["num_trials"] = len(nwb_file.trials) if nwb_file.trials else 0
    extractable["data_summary"]["acquisition_interfaces"] = len(nwb_file.acquisition) if nwb_file.acquisition else 0
    extractable["data_summary"]["processing_modules"] = len(nwb_file.processing) if nwb_file.processing else 0
    extractable["data_summary"]["devices"] = len(nwb_file.devices) if nwb_file.devices else 0

    # Technical details
    if nwb_file.electrodes is not None and len(nwb_file.electrodes) > 0:
        df = nwb_file.electrodes.to_dataframe()
        extractable["technical"]["electrode_locations"] = list(df['location'].unique()) if 'location' in df.columns else []
        extractable["technical"]["electrode_groups"] = list(df['group_name'].unique()) if 'group_name' in df.columns else []

    # Remove None values
    for category in extractable:
        extractable[category] = {k: v for k, v in extractable[category].items() if v is not None}

    return extractable

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_nwb_structure.py <nwb_file_path>")
        sys.exit(1)

    nwb_path = sys.argv[1]
    if not Path(nwb_path).exists():
        print(f"❌ File not found: {nwb_path}")
        sys.exit(1)

    extractable = analyze_nwb_file(nwb_path)

    if extractable:
        print("🎯 Analysis complete! Use this data to enhance the knowledge graph.")

if __name__ == "__main__":
    main()