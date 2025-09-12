#!/usr/bin/env python3
"""
Demonstration of TestDatasetManager functionality.

This script shows how to use the TestDatasetManager to manage test datasets
for the agentic neurodata conversion project.
"""

import json
from pathlib import Path
import shutil
import tempfile

from agentic_neurodata_conversion.data_management.repository_structure import (
    DataLadRepositoryManager,
    TestDatasetManager,
)


def create_sample_datasets(base_dir: Path):
    """Create sample datasets for demonstration."""
    print("Creating sample datasets...")

    # Create Open Ephys-like dataset
    oe_dir = base_dir / "open_ephys_sample"
    oe_dir.mkdir()
    (oe_dir / "100_CH1.continuous").write_bytes(b"fake continuous data channel 1")
    (oe_dir / "100_CH2.continuous").write_bytes(b"fake continuous data channel 2")
    (oe_dir / "100_CH3.continuous").write_bytes(b"fake continuous data channel 3")
    (oe_dir / "100_CH4.continuous").write_bytes(b"fake continuous data channel 4")
    (oe_dir / "events.txt").write_text(
        "1.0 stimulus_on\n2.0 stimulus_off\n3.0 response\n"
    )
    (oe_dir / "metadata.json").write_text(
        json.dumps(
            {
                "format": "open_ephys",
                "channels": 4,
                "sampling_rate": 30000,
                "experiment": "demo_experiment",
            },
            indent=2,
        )
    )

    # Create SpikeGLX-like dataset
    sglx_dir = base_dir / "spikeglx_sample"
    sglx_dir.mkdir()
    (sglx_dir / "demo_g0_t0.imec0.ap.bin").write_bytes(
        b"fake binary neural data" * 1000
    )
    (sglx_dir / "demo_g0_t0.imec0.ap.meta").write_text(
        """nSavedChans=32
sampleRate=30000.0
fileTimeSecs=60.0
imDatPrb_type=0
"""
    )
    (sglx_dir / "metadata.json").write_text(
        json.dumps(
            {
                "format": "spikeglx",
                "channels": 32,
                "sampling_rate": 30000,
                "duration_seconds": 60,
            },
            indent=2,
        )
    )

    # Create generic CSV dataset
    csv_dir = base_dir / "generic_sample"
    csv_dir.mkdir()

    # Generate some sample data
    csv_data = "timestamp,ch1,ch2,ch3,ch4\n"
    for i in range(1000):
        timestamp = i * 0.001  # 1ms intervals
        ch1 = f"{0.1 * (i % 10):.3f}"
        ch2 = f"{0.2 * ((i + 1) % 10):.3f}"
        ch3 = f"{0.15 * ((i + 2) % 10):.3f}"
        ch4 = f"{0.25 * ((i + 3) % 10):.3f}"
        csv_data += f"{timestamp},{ch1},{ch2},{ch3},{ch4}\n"

    (csv_dir / "recording_data.csv").write_text(csv_data)
    (csv_dir / "events.csv").write_text(
        "timestamp,event_type,description\n1.0,stimulus,visual_stimulus\n2.5,response,button_press\n"
    )
    (csv_dir / "metadata.json").write_text(
        json.dumps(
            {
                "format": "generic_csv",
                "channels": 4,
                "sampling_rate": 1000,
                "total_samples": 1000,
            },
            indent=2,
        )
    )

    print(f"Created sample datasets in {base_dir}")
    return oe_dir, sglx_dir, csv_dir


def demonstrate_dataset_management():
    """Demonstrate TestDatasetManager functionality."""
    print("=== TestDatasetManager Demonstration ===\n")

    # Create temporary directory for demo
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temporary directory: {temp_dir}")

    try:
        # Create sample source data
        source_dir = temp_dir / "source_data"
        source_dir.mkdir()
        oe_sample, sglx_sample, csv_sample = create_sample_datasets(source_dir)

        # Initialize repository and dataset manager
        print("\n1. Initializing DataLad repository and TestDatasetManager...")
        repo_manager = DataLadRepositoryManager(str(temp_dir / "test_repo"))
        dataset_manager = TestDatasetManager(repo_manager)

        print(f"   Repository path: {dataset_manager.repo_manager.base_path}")
        print(f"   Test data path: {dataset_manager.test_data_path}")
        print(f"   Evaluation data path: {dataset_manager.evaluation_data_path}")
        print(f"   Examples path: {dataset_manager.conversion_examples_path}")

        # Add test datasets
        print("\n2. Adding test datasets...")

        # Add Open Ephys dataset
        result1 = dataset_manager.add_test_dataset(
            dataset_name="demo_open_ephys",
            source_path=str(oe_sample),
            description="Demo Open Ephys dataset for testing electrophysiology conversion",
            metadata={
                "experiment_type": "electrophysiology",
                "species": "mouse",
                "brain_region": "hippocampus",
                "researcher": "Demo User",
            },
        )
        print(f"   Added Open Ephys dataset: {result1}")

        # Add SpikeGLX dataset as evaluation data
        result2 = dataset_manager.add_test_dataset(
            dataset_name="demo_spikeglx",
            source_path=str(sglx_sample),
            description="Demo SpikeGLX dataset for evaluation benchmarks",
            dataset_type="evaluation",
            metadata={
                "experiment_type": "neuropixels",
                "probe_type": "imec0",
                "channels": 32,
            },
        )
        print(f"   Added SpikeGLX evaluation dataset: {result2}")

        # Add CSV dataset as example
        result3 = dataset_manager.add_test_dataset(
            dataset_name="demo_generic_csv",
            source_path=str(csv_sample),
            description="Demo generic CSV dataset showing conversion examples",
            dataset_type="example",
            metadata={"format_type": "generic", "use_case": "tutorial"},
        )
        print(f"   Added generic CSV example dataset: {result3}")

        # List all datasets
        print("\n3. Listing all available datasets...")
        all_datasets = dataset_manager.get_available_datasets()
        print(f"   Total datasets: {len(all_datasets)}")

        for dataset in all_datasets:
            print(
                f"   - {dataset['name']} ({dataset['dataset_type']}, {dataset['format_detected']})"
            )
            print(
                f"     Files: {dataset['file_count']}, Size: {dataset['size_bytes']} bytes"
            )
            print(f"     Description: {dataset['description']}")

        # Demonstrate filtering by type
        print("\n4. Filtering datasets by type...")
        test_datasets = dataset_manager.get_available_datasets(dataset_type="test")
        eval_datasets = dataset_manager.get_available_datasets(
            dataset_type="evaluation"
        )
        example_datasets = dataset_manager.get_available_datasets(
            dataset_type="example"
        )

        print(f"   Test datasets: {len(test_datasets)}")
        for ds in test_datasets:
            print(f"     - {ds['name']}")

        print(f"   Evaluation datasets: {len(eval_datasets)}")
        for ds in eval_datasets:
            print(f"     - {ds['name']}")

        print(f"   Example datasets: {len(example_datasets)}")
        for ds in example_datasets:
            print(f"     - {ds['name']}")

        # Demonstrate format filtering
        print("\n5. Filtering datasets by format...")
        oe_datasets = dataset_manager.get_datasets_by_format("open_ephys")
        sglx_datasets = dataset_manager.get_datasets_by_format("spikeglx")
        csv_datasets = dataset_manager.get_datasets_by_format("generic_csv")

        print(f"   Open Ephys datasets: {[ds['name'] for ds in oe_datasets]}")
        print(f"   SpikeGLX datasets: {[ds['name'] for ds in sglx_datasets]}")
        print(f"   CSV datasets: {[ds['name'] for ds in csv_datasets]}")

        # Demonstrate dataset access
        print("\n6. Accessing dataset files...")
        oe_path = dataset_manager.get_dataset_path("demo_open_ephys")
        if oe_path:
            print(f"   Open Ephys dataset path: {oe_path}")
            files = list(oe_path.iterdir())
            print(f"   Files in dataset: {[f.name for f in files]}")

            # Show metadata
            metadata_file = oe_path / "dataset_metadata.json"
            if metadata_file.exists():
                metadata = json.loads(metadata_file.read_text())
                print(f"   Custom metadata: {metadata.get('custom_metadata', {})}")

        # Demonstrate dataset removal
        print("\n7. Demonstrating dataset removal...")
        print(
            f"   Datasets before removal: {len(dataset_manager.get_available_datasets())}"
        )

        removal_result = dataset_manager.remove_dataset("demo_generic_csv", "example")
        print(f"   Removed demo_generic_csv: {removal_result}")

        print(
            f"   Datasets after removal: {len(dataset_manager.get_available_datasets())}"
        )

        # Show final repository structure
        print("\n8. Final repository structure:")

        def show_tree(path, prefix="", max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return

            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                print(f"{prefix}{current_prefix}{item.name}")

                if item.is_dir() and current_depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    show_tree(item, next_prefix, max_depth, current_depth + 1)

        show_tree(dataset_manager.repo_manager.base_path)

        print("\n=== Demo completed successfully! ===")
        print(f"Repository created at: {dataset_manager.repo_manager.base_path}")

    except Exception as e:
        print(f"Error during demonstration: {e}")
        raise

    finally:
        # Clean up
        print(f"\nCleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    demonstrate_dataset_management()
