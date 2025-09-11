"""
mcp_server.py

Unified MCP server that wires together:
- conversationAgent (dataset analysis)
- conversionagent (conversion script generation / runner)
- evaluation_agent_combined (NWB evaluation, TTL/KG generation, context/report writers)

It exposes:
- a minimal MCP-style @mcp.tool decorator to register "tools"
- a FastAPI app with a POST /tool/{tool_name} to call registered tools (JSON body -> kwargs)
- pipeline_state for sharing data between tools
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# FastAPI for a lightweight RPC surface
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except Exception:
    FastAPI = None
    HTTPException = Exception
    uvicorn = None

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# Try to import user modules (case-insensitive fallback)
def try_import(module_name_variants):
    for nm in module_name_variants:
        try:
            m = __import__(nm)
            logger.info(f"Imported module: {nm}")
            return m
        except Exception:
            continue
    logger.warning(f"Could not import any of: {module_name_variants}")
    return None

conversationAgent = try_import(["conversationAgent", "conversationagent"])
conversionagent = try_import(["conversionagent", "conversionAgent"])
# Combined evaluation agent should be present (we produced this file earlier)
evaluation_agent_combined = try_import(["evaluation_agent_combined", "evaluationAgentCombined", "evaluationagent_combined"])

# If the imported modules have different attribute names, we'll check below before calling.

# Minimal MCP registry
class _MCPRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self, name: Optional[str] = None):
        def decorator(fn):
            tool_name = name or fn.__name__
            if tool_name in self.tools:
                logger.warning(f"Overwriting existing tool: {tool_name}")
            self.tools[tool_name] = fn
            logger.info(f"Registered tool: {tool_name} -> {fn}")
            return fn
        return decorator

mcp = _MCPRegistry()

# Shared pipeline state
pipeline_state: Dict[str, Any] = {
    "initialized": False,
    "config": {},
    "conversion_script": None,
    "evaluation_results": None,
    "analysis_report": None,
    "workflow_history": []
}

# --------------------------------------------------------------------
# EvaluationAgent wrapper using evaluation_agent_combined
# --------------------------------------------------------------------
class EvaluationAgent:
    """
    Thin wrapper around evaluation_agent_combined.EvaluationAgent (if available).
    Provides:
      - validate_nwb(nwb_path)
      - generate_outputs(nwb_path, out_dir, include_data, ...)
      - write_context_and_report(nwb_path, eval_results, outputs, out_dir)
    """

    def __init__(self, base_cache_dir: Optional[str] = None):
        impl_cls = None
        if evaluation_agent_combined:
            impl_cls = getattr(evaluation_agent_combined, "EvaluationAgent", None)
        if impl_cls:
            try:
                self._impl = impl_cls(base_cache_dir)  # type: ignore
            except Exception as e:
                logger.exception("Failed to instantiate combined EvaluationAgent: %s", e)
                self._impl = None
        else:
            self._impl = None

    def validate_nwb(self, nwb_path: str) -> Dict[str, Any]:
        if self._impl is None:
            # best-effort fallback using nwbinspector if installed at runtime
            try:
                import nwbinspector
                messages = list(nwbinspector.inspect_nwbfile(nwbfile_path=nwb_path))
                formatted = nwbinspector.format_messages(messages=messages)
                counts = {}
                for m in messages:
                    level = m.importance.name
                    counts[level] = counts.get(level, 0) + 1
                failing_levels = {"CRITICAL", "BEST_PRACTICE_VIOLATION", "PYNWB_VALIDATION", "ERROR"}
                passed = not any(counts.get(level, 0) > 0 for level in failing_levels)
                return {"passed": passed, "counts": counts, "formatted_report": "\n".join(formatted), "total_issues": len(messages)}
            except Exception as e:
                logger.exception("Validation fallback failed: %s", e)
                return {"passed": False, "counts": {"ERROR": 1}, "formatted_report": f"Validation error: {e}", "total_issues": 1}
        else:
            try:
                res = self._impl.validate_nwb(nwb_path)
                return res
            except Exception as e:
                logger.exception("EvaluationAgent.validate_nwb failed: %s", e)
                return {"passed": False, "formatted_report": str(e), "summary": "error"}

    def generate_outputs(self, nwb_path: str, out_dir: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        if self._impl is None:
            return {"status": "error", "message": "evaluation agent implementation not available"}
        try:
            return self._impl.generate_ttl_and_outputs(nwb_path, out_dir=out_dir, **kwargs)
        except Exception as e:
            logger.exception("generate_outputs failed: %s", e)
            return {"status": "error", "message": str(e)}

    def write_context_and_report(self, nwb_path: str, eval_results: Dict[str, Any], outputs: Optional[Dict[str, str]] = None, out_dir: Optional[str] = None) -> Dict[str, Any]:
        if self._impl is None:
            return {"status": "error", "message": "evaluation agent implementation not available"}
        try:
            return self._impl.write_context_and_report(nwb_path, eval_results, outputs=outputs, out_dir=out_dir)
        except Exception as e:
            logger.exception("write_context_and_report failed: %s", e)
            return {"status": "error", "message": str(e)}

# --------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------

@mcp.tool()
async def initialize_pipeline(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Initialize pipeline state. Provide config dict with keys like:
    - output_dir: where to store results
    - use_llm: bool
    - openai_model, ollama_model, etc.
    """
    cfg = config or {}
    pipeline_state["initialized"] = True
    pipeline_state["config"] = cfg
    pipeline_state["workflow_history"].append({"step": "initialize", "timestamp": datetime.utcnow().isoformat(), "config": cfg})
    logger.info("Pipeline initialized with config: %s", cfg)
    return {"status": "ok", "config": cfg}

@mcp.tool()
async def analyze_dataset(dataset_dir: str, out_report_json: Optional[str] = None, use_llm: bool = False) -> Dict[str, Any]:
    """
    Run dataset analysis using conversationAgent.analyze_dataset (if available).
    Returns the analysis json (and writes to out_report_json if provided).
    """
    if conversationAgent is None:
        return {"status": "error", "message": "conversationAgent module not available."}
    try:
        analyze_fn = getattr(conversationAgent, "analyze_dataset", None)
        if analyze_fn is None:
            return {"status": "error", "message": "analyze_dataset function not found in conversationAgent."}
        res = analyze_fn(dataset_dir, out_report_json=out_report_json)  # respects user's function signature
        pipeline_state["analysis_report"] = res
        pipeline_state["workflow_history"].append({"step": "analyze_dataset", "timestamp": datetime.utcnow().isoformat(), "dataset_dir": dataset_dir})
        return {"status": "success", "result": res}
    except Exception as e:
        logger.exception("analyze_dataset failed: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def generate_conversion_script(normalized_metadata: Dict[str, Any], files_map: Dict[str, str], output_nwb_path: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Use conversionagent to synthesize a conversion script. Returns metadata including output path.
    """
    if conversionagent is None:
        return {"status": "error", "message": "conversionagent module not available."}
    try:
        synth = getattr(conversionagent, "synthesize_conversion_script", None)
        write_fn = getattr(conversionagent, "write_generated_script", None)
        run_fn = getattr(conversionagent, "run_generated_script", None)
        if synth is None:
            return {"status": "error", "message": "synthesize_conversion_script not found in conversionagent."}
        # Default output path if none
        if not output_nwb_path:
            out_dir = Path(pipeline_state.get("config", {}).get("output_dir", ".")) / "converted"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_nwb_path = str(out_dir / f"{normalized_metadata.get('dataset_name', 'converted')}.nwb")
        script_text = synth(normalized_metadata, files_map, output_nwb_path, model=model)
        # attempt to write script (if helper exists) or write ourselves
        script_path = None
        if write_fn:
            script_path = write_fn(script_text)
        else:
            # write to default temp file
            tmp = Path(pipeline_state.get("config", {}).get("output_dir", ".")) / "conversion_scripts"
            tmp.mkdir(parents=True, exist_ok=True)
            script_path = tmp / f"conversion_{int(datetime.utcnow().timestamp())}.py"
            script_path.write_text(script_text, encoding="utf-8")
            script_path = str(script_path)
        # Optionally run the script if run_generated_script exists (we won't run automatically here)
        pipeline_state["conversion_script"] = {"script_path": script_path, "output_path": output_nwb_path}
        pipeline_state["workflow_history"].append({"step": "generate_conversion_script", "timestamp": datetime.utcnow().isoformat(), "script": script_path, "nwb": output_nwb_path})
        return {"status": "success", "script_path": script_path, "output_nwb_path": output_nwb_path}
    except Exception as e:
        logger.exception("generate_conversion_script failed: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def evaluate_nwb_file(nwb_path: Optional[str] = None, generate_report: bool = True, output_dir: Optional[str] = None, include_data: str = "stats") -> Dict[str, Any]:
    """
    Validate and (optionally) generate knowledge graph / context for an NWB file.
    """
    if not pipeline_state["initialized"]:
        return {"status": "error", "message": "Pipeline not initialized."}
    # determine NWB path fallback
    if not nwb_path:
        conv = pipeline_state.get("conversion_script")
        if conv and isinstance(conv, dict):
            nwb_path = conv.get("output_path")
    if not nwb_path:
        return {"status": "error", "message": "No nwb_path provided or available from conversion_script."}
    if not Path(nwb_path).exists():
        return {"status": "error", "message": f"NWB file not found at: {nwb_path}"}
    try:
        ev = EvaluationAgent(base_cache_dir=pipeline_state.get("config", {}).get("output_dir"))
        validation_results = ev.validate_nwb(nwb_path)
        outputs = None
        out_dir = output_dir or str(Path(nwb_path).parent / "evaluation_results")
        if generate_report:
            outputs = ev.generate_outputs(nwb_path, out_dir=out_dir, include_data=include_data)
            ctx = ev.write_context_and_report(nwb_path, validation_results, outputs=outputs.get("files") if isinstance(outputs, dict) else None, out_dir=out_dir)
        pipeline_state["evaluation_results"] = {
            "nwb_path": nwb_path,
            "validation": validation_results,
            "outputs": outputs,
            "context": ctx if generate_report else None
        }
        pipeline_state["workflow_history"].append({"step": "evaluate_nwb", "timestamp": datetime.utcnow().isoformat(), "nwb": nwb_path, "passed": validation_results.get("passed")})
        return {"status": "success", "validation": validation_results, "outputs": outputs}
    except Exception as e:
        logger.exception("evaluate_nwb_file failed: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def generate_knowledge_graph(nwb_path: Optional[str] = None, out_dir: Optional[str] = None, include_data: str = "stats") -> Dict[str, Any]:
    """
    Generate instance graph and TTL/JSON-LD files for the NWB file. Uses EvaluationAgent.generate_outputs.
    """
    if not pipeline_state["initialized"]:
        return {"status": "error", "message": "Pipeline not initialized."}
    if not nwb_path:
        conv = pipeline_state.get("conversion_script")
        if conv and isinstance(conv, dict):
            nwb_path = conv.get("output_path")
    if not nwb_path:
        return {"status": "error", "message": "No nwb_path provided."}
    try:
        ev = EvaluationAgent(base_cache_dir=pipeline_state.get("config", {}).get("output_dir"))
        out = ev.generate_outputs(nwb_path, out_dir=out_dir, include_data=include_data)
        pipeline_state["workflow_history"].append({"step": "generate_kg", "timestamp": datetime.utcnow().isoformat(), "nwb": nwb_path})
        return {"status": "success", "outputs": out}
    except Exception as e:
        logger.exception("generate_knowledge_graph failed: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def run_full_pipeline(dataset_dir: str, files_map: Optional[Dict[str, str]] = None, output_dir: Optional[str] = None, use_llm: bool = False) -> Dict[str, Any]:
    """
    High-level runner that executes:
      1) analyze_dataset
      2) generate_conversion_script (user must still run the script or conversionagent may run it)
      3) evaluate_nwb_file (if generated NWB exists)
    Note: This is a convenience wrapper and not a transactionally safe pipeline.
    """
    if not pipeline_state["initialized"]:
        return {"status": "error", "message": "Pipeline not initialized."}
    try:
        # analyze
        analysis = await analyze_dataset(dataset_dir, out_report_json=None, use_llm=use_llm)
        # If conversationAgent returned normalized metadata, pass to conversion
        normalized = {}
        if isinstance(analysis, dict) and analysis.get("status") == "success":
            normalized = analysis.get("result", {})  # adapt if your analyze_dataset uses different key
        # generate conversion script
        conv = await generate_conversion_script(normalized_metadata=normalized, files_map=files_map or {}, output_nwb_path=None, model=None)
        # try to run conversion script (if conversionagent exposes runner)
        conv_out = {}
        try:
            if conversionagent:
                run_fn = getattr(conversionagent, "run_generated_script", None)
                if run_fn and pipeline_state.get("conversion_script"):
                    script_path = pipeline_state["conversion_script"].get("script_path")
                    if script_path:
                        run_res = run_fn(script_path)
                        conv_out = {"run_result": run_res}
        except Exception:
            logger.exception("Running conversion script failed; continuing.")
        # evaluate if NWB produced
        nwb_path = pipeline_state.get("conversion_script", {}).get("output_path")
        eval_res = None
        if nwb_path and Path(nwb_path).exists():
            eval_res = await evaluate_nwb_file(nwb_path=nwb_path, generate_report=True, output_dir=output_dir)
        pipeline_state["workflow_history"].append({"step": "run_full_pipeline", "timestamp": datetime.utcnow().isoformat()})
        return {"status": "success", "analysis": analysis, "conversion": conv, "conversion_run": conv_out, "evaluation": eval_res}
    except Exception as e:
        logger.exception("run_full_pipeline failed: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def status() -> Dict[str, Any]:
    """Return current pipeline_state summary"""
    return {
        "initialized": pipeline_state.get("initialized", False),
        "config": pipeline_state.get("config"),
        "conversion_script": pipeline_state.get("conversion_script"),
        "evaluation_results": pipeline_state.get("evaluation_results"),
        "analysis_report": pipeline_state.get("analysis_report"),
        "workflow_history_tail": pipeline_state.get("workflow_history")[-10:]
    }

@mcp.tool()
async def clear_state() -> Dict[str, Any]:
    """Reset pipeline state (keeps history in logs)."""
    pipeline_state["initialized"] = False
    pipeline_state["config"] = {}
    pipeline_state["conversion_script"] = None
    pipeline_state["evaluation_results"] = None
    pipeline_state["analysis_report"] = None
    pipeline_state["workflow_history"].append({"step": "clear_state", "timestamp": datetime.utcnow().isoformat()})
    return {"status": "ok"}

# --------------------------------------------------------------------
# FastAPI wrapper to call registered mcp tools remotely
# --------------------------------------------------------------------
app = None
if FastAPI is not None:
    app = FastAPI(title="MCP Server (light)", version="0.1.0")
    # allow local CORS for convenience
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/tool/{tool_name}")
    async def call_tool(tool_name: str, body: Optional[Dict[str, Any]] = None):
        body = body or {}
        tool = mcp.tools.get(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
        try:
            # tools are async functions in this file; call them accordingly
            result = await tool(**body)
            # ensure JSON serializable
            try:
                json.dumps(result)
            except Exception:
                # try to coerce to str
                result = {"result_repr": str(result)}
            return result
        except Exception as e:
            logger.exception("Tool %s failed: %s", tool_name, e)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/tools")
    def list_tools():
        return {"tools": list(mcp.tools.keys())}

    @app.get("/status")
    async def http_status():
        return await status()

# --------------------------------------------------------------------
# If run as script, start uvicorn server (if available)
# --------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("MCP_SERVER_PORT", 8000))
    host = os.environ.get("MCP_SERVER_HOST", "127.0.0.1")
    if uvicorn is None or app is None:
        print("FastAPI / uvicorn not available. This module defines tools and pipeline_state for import.")
        print("To run a HTTP server install fastapi and uvicorn and run this file again.")
        sys.exit(0)
    print(f"Starting MCP server on http://{host}:{port} (tools: {list(mcp.tools.keys())})")
    uvicorn.run(app, host=host, port=port)
