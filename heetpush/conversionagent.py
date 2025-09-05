# conversion_agent.py
import os, json, subprocess, sys
from typing import Dict, Any, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

NEUROCONV_CONTEXT = """
NeuroConv quick notes (condensed):
- Custom DataInterfaces subclass BaseDataInterface.
- Register them with an NWBConverter.
- Call run_conversion() with merged metadata.
"""

SYSTEM_PROMPT = "You are a senior NeuroConv engineer. Generate a runnable Python script using NeuroConv given metadata and files_map."


def synthesize_conversion_script(
    normalized_metadata: Dict[str, Any], files_map: Dict[str, Any], output_nwb_path: str, model: Optional[str] = None
) -> str:
    model = model or os.getenv("LLM_MODEL", "gpt-5")
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI is None or not api_key:
        return _fallback_csv_only_script(normalized_metadata, files_map, output_nwb_path)
    client = OpenAI(api_key=api_key)
    user = f"NEUROCONV_CONTEXT:\\n{NEUROCONV_CONTEXT}\\nMETADATA:\\n{json.dumps(normalized_metadata)}\\nFILES_MAP:\\n{json.dumps(files_map)}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": [{"type": "text", "text": user}]}],
        temperature=0.2,
    )
    code = resp.choices[0].message.content or ""
    return code


def _fallback_csv_only_script(metadata: Dict[str, Any], files_map: Dict[str, Any], out_path: str) -> str:
    return f'''# generated_conversion.py (fallback)
import os, csv, json
from datetime import datetime
from pynwb import NWBFile, NWBHDF5IO
from pynwb.base import TimeSeries

METADATA = {json.dumps(metadata, indent=2)}
CSV_PATH = {json.dumps(files_map.get("csv_timeseries") or "")}
OUT_PATH = {json.dumps(out_path)}

def make_nwb():
    nf = METADATA.get("nwbfile", {{}})
    nwbfile = NWBFile(
        session_description=nf.get("session_description", "demo"),
        identifier=nf.get("identifier", "auto"),
        session_start_time=datetime.now(),
    )
    if CSV_PATH and os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            data, ts = [], []
            for row in r:
                ts.append(float(row.get("timestamp", len(ts))))
                data.append(float(row.get("value", 0)))
        nwbfile.add_acquisition(TimeSeries(name="csv_signal", data=data, unit="a.u.", timestamps=ts))
    with NWBHDF5IO(OUT_PATH, "w") as io:
        io.write(nwbfile)
    print("Wrote", OUT_PATH)

if __name__ == "__main__":
    make_nwb()
'''


def write_generated_script(code: str, out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    return out_path


def run_generated_script(script_path: str) -> int:
    return subprocess.call([sys.executable, script_path])
