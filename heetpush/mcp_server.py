# mcp_server.py
import json, os, tempfile
from mcp.server.fastmcp import FastMCP
from conversationAgent import analyze_dataset
from conversionagent import synthesize_conversion_script, write_generated_script, run_generated_script

mcp = FastMCP("NWB-MCP-Server")

@mcp.tool()
def analyze_data(dataset_dir: str):
    return analyze_dataset(dataset_dir)

@mcp.tool()
def convert_to_nwb(metadata_json: str, files_map_json: str, out_nwb_path: str, emit_only: bool=False):
    md = json.loads(metadata_json)
    fm = json.loads(files_map_json)
    code = synthesize_conversion_script(md, fm, out_nwb_path)
    script_path = os.path.join(tempfile.gettempdir(), "generated_conversion.py")
    write_generated_script(code, script_path)
    rc = 0 if emit_only else run_generated_script(script_path)
    return {"script_path": script_path, "return_code": rc}

@mcp.tool()
def handoff(dataset_dir: str, out_nwb_path: str):
    analysis = analyze_dataset(dataset_dir)
    md = analysis["normalized_metadata"]
    fm = {}
    csvs = [f for f in os.listdir(dataset_dir) if f.endswith(".csv")]
    if csvs:
        fm["csv_timeseries"] = os.path.join(dataset_dir, csvs[0])
    code = synthesize_conversion_script(md, fm, out_nwb_path)
    script_path = os.path.join(tempfile.gettempdir(), "generated_conversion.py")
    write_generated_script(code, script_path)
    rc = run_generated_script(script_path)
    return {"analysis": analysis, "out_nwb_path": out_nwb_path, "return_code": rc}

if __name__ == "__main__":
    mcp.run_stdio()
