# conversion_agent.py
import os, json, subprocess, sys
from typing import Dict, Any, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# 🔹 Extended NeuroConv context (condensed from docs, tutorials, and API references)
NEUROCONV_CONTEXT = """
NeuroConv Overview
------------------
NeuroConv is a Python library for converting neuroscience data formats into the NWB (Neurodata Without Borders) standard.
It provides:
- Built-in DataInterfaces for many formats (SpikeGLX, OpenEphys, Intan, Blackrock, etc.)
- Tools to define custom DataInterfaces when your format is not supported.
- An NWBConverter class to register interfaces and merge metadata.

Key Concepts
------------
1. DataInterface:
   - Wraps one data source (e.g., ephys, ophys, behavior).
   - Must define:
       __init__(self, **source_data)
       get_metadata(self)
       run_conversion(self, nwbfile, metadata, stub=False, overwrite=False)

2. NWBConverter:
   - Holds a dict mapping names → DataInterface classes.
   - Usage:
       class MyConverter(NWBConverter):
           data_interface_classes = dict(
               ecephys=SpikeGLXRecordingInterface,
               behavior=CSVTimeSeriesInterface,
           )
       converter = MyConverter(source_data={...})

   - converter.get_metadata() merges all metadata from interfaces.
   - converter.run_conversion("output.nwb", metadata, overwrite=True)

3. Metadata merging:
   - Always prefer user-provided metadata if conflicts with interface metadata.
   - Ensure required fields: session_description, identifier, session_start_time, subject.species, general.lab/institution/experimenter.

4. Example: Custom CSVTimeSeriesInterface
   from neuroconv.datainterfaces import BaseDataInterface
   from pynwb.base import TimeSeries

   class CSVTimeSeriesInterface(BaseDataInterface):
       def __init__(self, file_path: str):
           super().__init__(extractor=None)
           self.source_data = dict(file_path=file_path)

       def get_metadata(self):
           return dict(nwbfile=dict(session_description="CSV timeseries"), acquisition=[])

       def run_conversion(self, nwbfile, metadata, stub=False, overwrite=False):
           import csv
           data, timestamps = [], []
           with open(self.source_data["file_path"], "r", encoding="utf-8") as f:
               r = csv.DictReader(f)
               for row in r:
                   timestamps.append(float(row["timestamp"]))
                   data.append(float(row["value"]))
           ts = TimeSeries(name="csv_signal", data=data, unit="a.u.", timestamps=timestamps)
           nwbfile.add_acquisition(ts)

5. Validation:
   - Schema validation with pynwb.validate
   - Best practices with NWB Inspector:
       from nwbinspector import inspect_nwb
       issues = list(inspect_nwb("output.nwb"))
       for issue in issues:
           print(issue["severity"], issue["message"])

6. Supported Formats:
   - Ephys: SpikeGLX, OpenEphys, Intan, TDT, Axona, Blackrock
   - Ophys: TIF stacks, miniscope
   - Behavior: videos, CSV logs

Usage Summary
-------------
1. Define DataInterfaces.
2. Define an NWBConverter with those interfaces.
3. Merge metadata: user metadata + interface metadata.
4. Run conversion: converter.run_conversion("output.nwb", metadata, overwrite=True).
5. Validate the output.
"""

SYSTEM_PROMPT = """You are a senior NeuroConv engineer.
Given (A) normalized NWB metadata and (B) a files map, generate a runnable Python script that:
- Defines any needed DataInterfaces (e.g., CSVTimeSeriesInterface).
- Defines an NWBConverter that registers them.
- Merges user metadata with interface metadata.
- Writes an NWB file to the output path.
- Optionally validates with NWB Inspector.
Output must be pure Python code.
"""

def synthesize_conversion_script(
    normalized_metadata: Dict[str, Any],
    files_map: Dict[str, Any],
    output_nwb_path: str,
    model: Optional[str] = None,
) -> str:
    model = model or os.getenv("LLM_MODEL", "gpt-5")
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI is None or not api_key:
        return _fallback_csv_only_script(normalized_metadata, files_map, output_nwb_path)

    client = OpenAI(api_key=api_key)
    user_prompt = f"""
NEUROCONV_CONTEXT:
{NEUROCONV_CONTEXT}

METADATA:
{json.dumps(normalized_metadata, indent=2)}

FILES_MAP:
{json.dumps(files_map, indent=2)}

OUTPUT_NWB_PATH:
{output_nwb_path}
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ],
        temperature=0.2,
    )
    code = resp.choices[0].message.content or ""
    return code


def _fallback_csv_only_script(metadata: Dict[str, Any], files_map: Dict[str, Any], out_path: str) -> str:
    return f'''# generated_conversion.py (fallback CSV-only)
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
