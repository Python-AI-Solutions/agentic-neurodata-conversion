from pathlib import Path

import pytest
import requests

API_URL = "http://127.0.0.1:8000"


def call_tool(tool_name, payload=None):
    """Helper to call MCP tool endpoint."""
    url = f"{API_URL}/tool/{tool_name}"
    resp = requests.post(url, json=payload or {})
    resp.raise_for_status()
    return resp.json()


@pytest.mark.order(1)
def test_initialize_pipeline():
    cfg = {"output_dir": "test_outputs", "use_llm": False}
    res = call_tool("initialize_pipeline", {"config": cfg})
    assert res["status"] == "ok"
    assert res["config"]["output_dir"] == "test_outputs"


@pytest.mark.order(2)
def test_analyze_dataset():
    # Replace with an actual dataset directory
    dataset_dir = str(Path("sample_dataset"))
    Path(dataset_dir).mkdir(exist_ok=True)

    res = call_tool("analyze_dataset", {"dataset_dir": dataset_dir, "use_llm": False})
    assert res["status"] in ("success", "error")
    # Store for later tests
    pytest.normalized_metadata = res.get("result", {})


@pytest.mark.order(3)
def test_generate_conversion_script():
    files_map = {"data_file": "example.dat"}  # adjust to your files
    res = call_tool(
        "generate_conversion_script",
        {
            "normalized_metadata": getattr(pytest, "normalized_metadata", {}),
            "files_map": files_map,
        },
    )
    assert res["status"] == "success"
    pytest.nwb_path = res["output_nwb_path"]


@pytest.mark.order(4)
def test_evaluate_nwb_file():
    nwb_path = getattr(pytest, "nwb_path", None)
    if not nwb_path or not Path(nwb_path).exists():
        pytest.skip("No NWB file available to evaluate")
    res = call_tool(
        "evaluate_nwb_file", {"nwb_path": nwb_path, "generate_report": True}
    )
    assert res["status"] == "success"
    assert "validation" in res


@pytest.mark.order(5)
def test_generate_knowledge_graph():
    nwb_path = getattr(pytest, "nwb_path", None)
    if not nwb_path or not Path(nwb_path).exists():
        pytest.skip("No NWB file available to generate KG")
    res = call_tool("generate_knowledge_graph", {"nwb_path": nwb_path})
    assert res["status"] == "success"
    assert "outputs" in res


@pytest.mark.order(6)
def test_status_endpoint():
    resp = requests.get(f"{API_URL}/status")
    resp.raise_for_status()
    res = resp.json()
    assert "initialized" in res
    assert "workflow_history_tail" in res
