import requests
import time
import json
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

def call_tool(tool_name, payload=None):
    url = f"{API_URL}/tool/{tool_name}"
    resp = requests.post(url, json=payload or {})
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] {tool_name} failed: {e} -> {resp.text}")
        return None
    try:
        return resp.json()
    except Exception:
        return resp.text

def main():
    print("=== MCP Pipeline Test ===")

    # 1. Initialize pipeline
    cfg = {"output_dir": "test_outputs", "use_llm": False}
    res = call_tool("initialize_pipeline", {"config": cfg})
    print("\n[initialize_pipeline]\n", json.dumps(res, indent=2))

    # 2. Analyze dataset (replace with a real dataset directory path!)
    dataset_dir = str(Path("sample_dataset"))  # adjust path to your dataset
    res = call_tool("analyze_dataset", {"dataset_dir": dataset_dir, "use_llm": False})
    print("\n[analyze_dataset]\n", json.dumps(res, indent=2))

    # Save normalized metadata if available
    normalized_metadata = {}
    if res and res.get("status") == "success":
        normalized_metadata = res.get("result", {})

    # 3. Generate conversion script
    files_map = {"data_file": "example.dat"}  # adjust mapping for your dataset
    res = call_tool("generate_conversion_script", {
        "normalized_metadata": normalized_metadata,
        "files_map": files_map
    })
    print("\n[generate_conversion_script]\n", json.dumps(res, indent=2))

    # 4. Evaluate NWB file (after conversion script runs and NWB exists)
    #    For testing, you may need to point to a real NWB file
    nwb_path = None
    if res and res.get("status") == "success":
        nwb_path = res.get("output_nwb_path")
    if nwb_path and Path(nwb_path).exists():
        res = call_tool("evaluate_nwb_file", {"nwb_path": nwb_path, "generate_report": True})
        print("\n[evaluate_nwb_file]\n", json.dumps(res, indent=2))
    else:
        print("\n[evaluate_nwb_file skipped] No NWB file available yet.")

    # 5. Generate knowledge graph explicitly
    if nwb_path and Path(nwb_path).exists():
        res = call_tool("generate_knowledge_graph", {"nwb_path": nwb_path})
        print("\n[generate_knowledge_graph]\n", json.dumps(res, indent=2))
    else:
        print("\n[generate_knowledge_graph skipped] No NWB file available yet.")

    # 6. Check pipeline status
    res = requests.get(f"{API_URL}/status")
    print("\n[status]\n", json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    main()
