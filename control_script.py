import subprocess
import json
import os

def call_conversion_agent(input_folder, metadata_file):
    """
    Calls Conversion Agent with NeuroConv to generate NWB file.
    input_folder: path to raw dataset (e.g., spike data, behavioral logs).
    metadata_file: path to user-provided metadata.json.
    """
    return subprocess.run(
        ["python", "conversion_agent.py", input_folder, metadata_file],
        capture_output=True, text=True
    ).stdout

def call_evaluation_agent(nwb_file):
    """
    Calls Evaluation Agent to validate generated NWB file.
    """
    return subprocess.run(
        ["python", "evaluation_agent.py", nwb_file],
        capture_output=True, text=True
    ).stdout

def inspect_raw_metadata(input_folder):
    """
    Basic inspection of raw dataset before NWB conversion.
    - Looks for common files (e.g., *.mat, *.edf, *.ns6, *.csv)
    - Returns 'detected' structure
    """
    file_summary = {}
    for root, _, files in os.walk(input_folder):
        for f in files:
            ext = os.path.splitext(f)[1]
            file_summary.setdefault(ext, 0)
            file_summary[ext] += 1
    return file_summary

def query_metadata(input_folder, metadata_file=None):
    """
    Queries 'available metadata' before conversion.
    Priority:
      1. User-provided metadata JSON
      2. Auto-inspection of raw files
    """
    metadata = {}

    # 1. Check if user metadata file exists
    if metadata_file and os.path.exists(metadata_file):
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

    # 2. Add auto-detected info if missing
    file_summary = inspect_raw_metadata(input_folder)
    metadata["raw_file_summary"] = file_summary

    # If still missing key fields → Conversation Agent should ask user
    required_fields = ["subject_id", "session_start_time", "experimenter"]
    missing = [f for f in required_fields if f not in metadata]

    return {
        "metadata": metadata,
        "missing_fields": missing
    }
