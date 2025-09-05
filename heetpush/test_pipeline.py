# test_pipeline.py
import os, json, tempfile, csv, random, math
from pathlib import Path
from conversationAgent import analyze_dataset
from conversionagent import synthesize_conversion_script, write_generated_script, run_generated_script

def make_dummy_dataset(root: str):
    ds = Path(root) / "dummy_dataset"
    ds.mkdir(parents=True, exist_ok=True)
    csv_path = ds / "signal.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["timestamp","value"])
        t = 0.0
        for i in range(1000):
            t += 0.01
            w.writerow([t, math.sin(t) + 0.1*random.random()])
    meta = {
        "nwbfile": {"session_description": "Dummy sine wave session"},
        "general": {"lab": "Demo Lab"},
        "subject": {}
    }
    with open(ds / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return str(ds), str(csv_path)

def main():
    work = tempfile.mkdtemp(prefix="nwb_test_")
    print("Workdir:", work)
    ds_dir, csv_path = make_dummy_dataset(work)
    analysis = analyze_dataset(ds_dir)
    print("Missing:", analysis["missing"])
    files_map = {"csv_timeseries": csv_path}
    normalized = analysis["normalized_metadata"]
    out_nwb = os.path.join(work, "dummy_output.nwb")
    code = synthesize_conversion_script(normalized, files_map, out_nwb)
    script_path = os.path.join(work, "generated_conversion.py")
    write_generated_script(code, script_path)
    rc = run_generated_script(script_path)
    print("Return code:", rc)
    if os.path.exists(out_nwb):
        print("Wrote NWB:", out_nwb)

if __name__ == "__main__":
    main()
