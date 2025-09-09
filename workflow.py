import requests
import json
from pathlib import Path

class MCPPipeline:
    def __init__(self, api_url="http://127.0.0.1:8000", output_dir="test_outputs", use_llm=False):
        self.api_url = api_url.rstrip("/")
        self.output_dir = output_dir
        self.use_llm = use_llm
        self.nwb_path = None
        self.normalized_metadata = {}

    def _call_tool(self, tool_name, payload=None):
        url = f"{self.api_url}/tool/{tool_name}"
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

    def initialize_pipeline(self):
        cfg = {"output_dir": self.output_dir, "use_llm": self.use_llm}
        res = self._call_tool("initialize_pipeline", {"config": cfg})
        print("\n[initialize_pipeline]\n", json.dumps(res, indent=2))
        return res

    def analyze_dataset(self, dataset_dir):
        res = self._call_tool("analyze_dataset", {"dataset_dir": dataset_dir, "use_llm": self.use_llm})
        print("\n[analyze_dataset]\n", json.dumps(res, indent=2))
        if res and res.get("status") == "success":
            self.normalized_metadata = res.get("result", {})
        return res

    def generate_conversion_script(self, files_map):
        res = self._call_tool("generate_conversion_script", {
            "normalized_metadata": self.normalized_metadata,
            "files_map": files_map
        })
        print("\n[generate_conversion_script]\n", json.dumps(res, indent=2))
        if res and res.get("status") == "success":
            self.nwb_path = res.get("output_nwb_path")
        return res

    def evaluate_nwb_file(self):
        if self.nwb_path and Path(self.nwb_path).exists():
            res = self._call_tool("evaluate_nwb_file", {"nwb_path": self.nwb_path, "generate_report": True})
            print("\n[evaluate_nwb_file]\n", json.dumps(res, indent=2))
            return res
        print("\n[evaluate_nwb_file skipped] No NWB file available yet.")
        return None

    def generate_knowledge_graph(self):
        if self.nwb_path and Path(self.nwb_path).exists():
            res = self._call_tool("generate_knowledge_graph", {"nwb_path": self.nwb_path})
            print("\n[generate_knowledge_graph]\n", json.dumps(res, indent=2))
            return res
        print("\n[generate_knowledge_graph skipped] No NWB file available yet.")
        return None

    def get_status(self):
        res = requests.get(f"{self.api_url}/status")
        print("\n[status]\n", json.dumps(res.json(), indent=2))
        return res.json()

    def run(self, dataset_dir, files_map):
        """Run the full pipeline step by step"""
        self.initialize_pipeline()
        self.analyze_dataset(dataset_dir)
        self.generate_conversion_script(files_map)
        self.evaluate_nwb_file()
        self.generate_knowledge_graph()
        return self.get_status()
