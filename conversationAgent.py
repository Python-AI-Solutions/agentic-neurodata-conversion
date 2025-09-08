# conversation_agent.py
from __future__ import annotations
import os, re, json, glob, uuid
from typing import Dict, Any, Optional
import yaml

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

NWB_REQUIRED_FIELDS = {
    "nwbfile": ["session_description", "identifier", "session_start_time"],
    "subject": ["species"],
    "general": ["lab", "institution", "experimenter"],
}

NWB_RECOMMENDED_FIELDS = {
    "subject": ["age", "sex", "description", "weight"],
    "general": ["device", "notes"],
}

PROVENANCE_USER = "user"
PROVENANCE_SOURCE = "source"
PROVENANCE_LLM = "llm-suggested"


def _load_sidecar_metadata(dataset_dir: str) -> Dict[str, Any]:
    meta = {}
    for pattern in (
        "*metadata*.json",
        "*meta*.json",
        "*.metadata.json",
        "*.json",
        "*metadata*.yml",
        "*metadata*.yaml",
        "*.yml",
        "*.yaml",
    ):
        for path in glob.glob(os.path.join(dataset_dir, pattern)):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    if path.endswith((".yml", ".yaml")):
                        doc = yaml.safe_load(f)
                    else:
                        doc = json.load(f)
                if isinstance(doc, dict):
                    meta.update(doc)
            except Exception:
                pass
    return meta


def _coerce_identifier(candidate: Dict[str, Any]) -> str:
    for k in ("identifier", "session_id", "id"):
        v = candidate.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return f"auto-{uuid.uuid4()}"


SYSTEM_PROMPT = "You are a meticulous NWB metadata auditor. Output compact JSON with keys: 'normalized','suggested','questions'."


def _call_llm_map_and_infer(hints: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    model = model or os.getenv("LLM_MODEL", "gpt-5")
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI is None or not api_key:
        return {
            "normalized": {},
            "suggested": {},
            "questions": ["What is the species?", "What is the lab?"],
        }
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": json.dumps(hints)}]},
        ],
        temperature=0.2,
    )
    txt = resp.choices[0].message.content
    try:
        return json.loads(txt)
    except Exception:
        return {
            "normalized": {},
            "suggested": {},
            "questions": ["Please provide missing NWB metadata."],
        }


def analyze_dataset(dataset_dir: str, out_report_json: Optional[str] = None) -> Dict[str, Any]:
    if not os.path.isdir(dataset_dir):
        raise FileNotFoundError(f"Dataset folder not found: {dataset_dir}")
    sidecar = _load_sidecar_metadata(dataset_dir)

    present = {"nwbfile": {}, "subject": {}, "general": {}}
    missing = {"nwbfile": [], "subject": [], "general": []}

    identifier = _coerce_identifier(sidecar)
    present["nwbfile"]["identifier"] = {"value": identifier, "source": PROVENANCE_SOURCE}

    if "session_description" in sidecar:
        present["nwbfile"]["session_description"] = {
            "value": sidecar["session_description"],
            "source": PROVENANCE_SOURCE,
        }
    else:
        missing["nwbfile"].append("session_description")

    if "subject" not in sidecar or "species" not in sidecar.get("subject", {}):
        missing["subject"].append("species")

    llm_out = _call_llm_map_and_infer(sidecar)
    normalized = llm_out.get("normalized", {})
    suggested = llm_out.get("suggested", {})
    questions = llm_out.get("questions", [])

    analysis = {
        "present": present,
        "missing": missing,
        "questions": questions,
        "normalized_metadata": normalized,
        "suggested_metadata": suggested,
    }

    if out_report_json:
        with open(out_report_json, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
    return analysis


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("dataset_dir")
    p.add_argument("--out", default="metadata_analysis.json")
    args = p.parse_args()
    result = analyze_dataset(args.dataset_dir, out_report_json=args.out)
    print(json.dumps(result, indent=2))
