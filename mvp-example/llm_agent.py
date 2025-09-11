#!/usr/bin/env python3
import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional
from urllib import request as _urlreq
from urllib.error import HTTPError as _HTTPError
from urllib.error import URLError as _URLError

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PY = REPO_ROOT / "evaluation_agent" / "eval" / "bin" / "python"
RUN_SCRIPT = REPO_ROOT / "evaluation_agent_final" / "run_single_agent.py"


def pick_python() -> Path:
    if DEFAULT_PY.exists():
        return DEFAULT_PY
    return Path(sys.executable)


def ensure_paths() -> None:
    if not RUN_SCRIPT.exists():
        raise SystemExit(f"run_single_agent.py not found at: {RUN_SCRIPT}")


def build_command(args: argparse.Namespace) -> tuple[list[str], str]:
    py = str(pick_python())
    cmd: list[str] = [py, str(RUN_SCRIPT)]

    if args.out_dir:
        cmd.extend(["--out-dir", str(Path(args.out_dir).expanduser().resolve())])
    if args.overwrite:
        cmd.append("--overwrite")
    if args.data:
        cmd.extend(["--data", args.data])
    if args.sample_limit is not None:
        cmd.extend(["--sample-limit", str(int(args.sample_limit))])
    if args.max_bytes is not None:
        cmd.extend(["--max-bytes", str(int(args.max_bytes))])
    if args.stats_inline_limit is not None:
        cmd.extend(["--stats-inline-limit", str(int(args.stats_inline_limit))])
    if args.ontology:
        cmd.extend(["--ontology", args.ontology])
    if args.linkml:
        cmd.append("--linkml")
    if args.offline:
        cmd.append("--offline")
    if args.cache_dir:
        cmd.extend(["--cache-dir", str(Path(args.cache_dir).expanduser().resolve())])

    nwb_path = str(Path(args.nwb).expanduser().resolve())
    if not Path(nwb_path).exists():
        raise SystemExit(f"NWB file not found: {nwb_path}")

    return cmd, nwb_path + "\n"


def run_once(args: argparse.Namespace) -> int:
    ensure_paths()
    cmd, stdin_payload = build_command(args)
    try:
        proc = subprocess.run(cmd, input=stdin_payload, text=True)
        return int(proc.returncode or 0)
    except KeyboardInterrupt:
        return 130


def parse_natural_language(prompt: str) -> dict[str, object]:
    opts: dict[str, object] = {}
    m = re.search(r"(?P<quote>['\"]).*?\.nwb(?P=quote)", prompt)
    if m is None:
        m = re.search(r"\s(\S+\.nwb)\b", prompt)
    if m:
        path = m.group(0).strip().strip("'\"")
        if path.lower().endswith(".nwb"):
            opts["nwb"] = path

    if re.search(r"\bfull\s+data\b", prompt, re.I) or re.search(
        r"\bdata\s*:\s*full\b", prompt, re.I
    ):
        opts["data"] = "full"
    elif re.search(r"\bsample\b", prompt, re.I):
        opts["data"] = "sample"
    elif re.search(r"\bstats\b", prompt, re.I):
        opts["data"] = "stats"
    elif re.search(r"\bno\s*data\b|\bdata\s*:\s*none\b", prompt, re.I):
        opts["data"] = "none"

    if re.search(r"\bontology\s*:\s*full\b|\bfull\s+ontology\b", prompt, re.I):
        opts["ontology"] = "full"
    elif re.search(r"\bno\s*ontology\b|\bontology\s*:\s*none\b", prompt, re.I):
        opts["ontology"] = "none"

    sm = re.search(r"sample[-_\s]*limit\s*[:=]?\s*(\d+)", prompt, re.I)
    if sm:
        opts["sample_limit"] = int(sm.group(1))
    mm = re.search(r"max[-_\s]*bytes\s*[:=]?\s*(\d+)", prompt, re.I)
    if mm:
        opts["max_bytes"] = int(mm.group(1))
    si = re.search(r"stats[-_\s]*inline[-_\s]*limit\s*[:=]?\s*(\d+)", prompt, re.I)
    if si:
        opts["stats_inline_limit"] = int(si.group(1))

    if re.search(r"\boverwrite\b", prompt, re.I):
        opts["overwrite"] = True

    outm = re.search(r"out[-_\s]*dir\s*[:=]?\s*([^\n]+)$", prompt, re.I)
    if outm:
        candidate = outm.group(1).strip().strip("'\"")
        if candidate:
            opts["out_dir"] = candidate

    if re.search(r"\boffline\b", prompt, re.I):
        opts["offline"] = True
    if re.search(r"\blinkml\b", prompt, re.I):
        opts["linkml"] = True

    return opts


def try_llm_extract(prompt: str) -> Optional[dict[str, object]]:
    """Use an LLM (OpenAI) to extract structured options. Returns None if unavailable."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import openai  # type: ignore
    except Exception:
        return None

    try:
        openai.api_key = api_key
        sys_prompt = (
            "You extract structured parameters for an NWB evaluation pipeline. "
            "Output ONLY compact JSON with keys: nwb, data, ontology, overwrite, sample_limit, max_bytes, stats_inline_limit, out_dir, linkml, offline. "
            "Booleans must be true/false, integers as numbers, strings or null. If a value is unspecified, use null (or false for booleans)."
        )
        user_prompt = prompt
        resp = openai.ChatCompletion.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=0,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = resp["choices"][0]["message"]["content"].strip()
        # Some models may wrap in code fences; strip them
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9]*", "", content).strip()
            if content.endswith("```"):
                content = content[:-3].strip()
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        # Normalize expected keys
        out: dict[str, object] = {}
        for key in [
            "nwb",
            "data",
            "ontology",
            "overwrite",
            "sample_limit",
            "max_bytes",
            "stats_inline_limit",
            "out_dir",
            "linkml",
            "offline",
        ]:
            out[key] = data.get(key)
        return out
    except Exception:
        return None


def try_ollama_extract(prompt: str) -> Optional[dict[str, object]]:
    """Use local Ollama to extract structured options. Returns None if unavailable."""
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b").strip()
    url = os.environ.get("OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat").strip()
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract structured parameters for an NWB evaluation pipeline. "
                    "Output ONLY compact JSON with keys: nwb, data, ontology, overwrite, sample_limit, max_bytes, stats_inline_limit, out_dir, linkml, offline. "
                    "Booleans must be true/false, integers as numbers, strings or null. If a value is unspecified, use null (or false for booleans)."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0},
    }
    data = json.dumps(payload).encode("utf-8")
    req = _urlreq.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with _urlreq.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            j = json.loads(body)
            content = None
            if isinstance(j, dict):
                # Chat endpoint returns { message: { content }, ... }
                msg = j.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                # Generate endpoint returns { response: "..." }
                if content is None:
                    content = j.get("response")
            if not isinstance(content, str):
                return None
            s = content.strip()
            if s.startswith("```"):
                s = re.sub(r"^```[a-zA-Z0-9]*", "", s).strip()
                if s.endswith("```"):
                    s = s[:-3].strip()
            obj = json.loads(s)
            if not isinstance(obj, dict):
                return None
            out: dict[str, object] = {}
            for key in [
                "nwb",
                "data",
                "ontology",
                "overwrite",
                "sample_limit",
                "max_bytes",
                "stats_inline_limit",
                "out_dir",
                "linkml",
                "offline",
            ]:
                out[key] = obj.get(key)
            return out
    except (_HTTPError, _URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def ollama_chat_response(prompt: str) -> Optional[str]:
    """Free-form assistant reply via Ollama, if available."""
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b").strip()
    url = os.environ.get("OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat").strip()
    script_path = str(RUN_SCRIPT)
    py_path = str(pick_python())
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a friendly CLI assistant for an NWB evaluation agent. "
                    "Be concise, helpful, and conversational. Prefer actionable guidance that works inside this project. "
                    'CRITICAL: When suggesting how to run checks, FIRST suggest the chat command: /run "/path/file.nwb". '
                    f"If you give a CLI example, ALWAYS use: {py_path} {script_path} (no placeholders), and mention that it will prompt for the NWB path. "
                    "Never show placeholders like <your_nwb_file_path>. Use quoted example paths if needed. "
                    "Suggest /help, /status, /set as appropriate."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.3},
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = _urlreq.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with _urlreq.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            j = json.loads(body)
            msg = j.get("message") if isinstance(j, dict) else None
            content = (msg or {}).get("content") if isinstance(msg, dict) else None
            if isinstance(content, str) and content.strip():
                return content.strip()
            content = j.get("response") if isinstance(j, dict) else None
            if isinstance(content, str) and content.strip():
                return content.strip()
    except Exception:
        return None
    return None


def openai_chat_response(prompt: str) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import openai  # type: ignore
    except Exception:
        return None
    try:
        openai.api_key = api_key
        script_path = str(RUN_SCRIPT)
        py_path = str(pick_python())
        sys_prompt = (
            "You are a friendly CLI assistant for an NWB evaluation agent. "
            "Be concise, helpful, and conversational. Prefer actionable guidance that works inside this project. "
            'CRITICAL: When suggesting how to run checks, FIRST suggest the chat command: /run "/path/file.nwb". '
            f"If you give a CLI example, ALWAYS use: {py_path} {script_path} (no placeholders), and mention that it will prompt for the NWB path. "
            "Never show placeholders like <your_nwb_file_path>. Use quoted example paths if needed. "
            "Suggest /help, /status, /set as appropriate."
        )
        resp = openai.ChatCompletion.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=0.3,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9]*", "", content).strip()
            if content.endswith("```"):
                content = content[:-3].strip()
        return content
    except Exception:
        return None


def llm_summarize_context(text: str) -> Optional[str]:
    """Ask Ollama or OpenAI to produce a detailed, human-readable summary of the context file."""
    system_msg = (
        "You are summarizing an NWB evaluation context. Write a clear, human-readable report with sections: "
        "1) Overall Status (PASS/FAIL), 2) Inspector Counts (concise), 3) Data Outputs (TTL/JSON-LD/triples if present), "
        "4) Notable Issues/Findings (group and bullet key messages), 5) Next Steps."
    )
    user_msg = (
        "Summarize the following context into a detailed report for a non-expert user. "
        "Prefer short sentences and bullets. Do not include raw stack traces.\n\n"
        + text
    )

    # Try Ollama first
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b").strip()
    url = os.environ.get("OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat").strip()
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "options": {"temperature": 0.2},
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = _urlreq.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with _urlreq.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            j = json.loads(body)
            msg = j.get("message") if isinstance(j, dict) else None
            content = (msg or {}).get("content") if isinstance(msg, dict) else None
            if isinstance(content, str) and content.strip():
                return content.strip()
            content = j.get("response") if isinstance(j, dict) else None
            if isinstance(content, str) and content.strip():
                return content.strip()
    except Exception:
        pass

    # Try OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            import openai  # type: ignore

            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            content = resp["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```[a-zA-Z0-9]*", "", content).strip()
                if content.endswith("```"):
                    content = content[:-3].strip()
            return content
        except Exception:
            pass
    return None


def local_summarize_context(text: str) -> str:
    """Fallback detailed summary without LLM."""
    lines = text.splitlines()
    decision = next(
        (
            line.split(":", 1)[-1].strip()
            for line in lines
            if line.startswith("Decision:")
        ),
        None,
    )
    counts = next(
        (
            line.split(":", 1)[-1].strip()
            for line in lines
            if line.startswith("Inspector counts:")
        ),
        None,
    )
    # Data outputs block
    artifacts = []
    try:
        if "Data outputs:" in lines:
            idx = lines.index("Data outputs:")
            for ln in lines[idx + 1 : idx + 6]:
                if ln.strip().startswith("-"):
                    artifacts.append(ln.strip().lstrip("- "))
                else:
                    break
    except Exception:
        pass
    # Inspector report lines
    report = []
    try:
        if "=== Inspector Report (verbatim) ===" in lines:
            idx = lines.index("=== Inspector Report (verbatim) ===") + 1
            report = [ln for ln in lines[idx:] if ln.strip()]
    except Exception:
        pass
    # Heuristic for notable messages
    notable = [
        ln
        for ln in report
        if any(
            k in ln for k in ("CRITICAL", "ERROR", "BEST_PRACTICE", "WARNING", "PYNWB")
        )
    ]
    if not notable:
        notable = report[:20]

    out = []
    out.append("Detailed Report")
    if decision:
        out.append(f"- Status: {decision}")
    if counts:
        out.append(f"- Inspector counts: {counts}")
    if artifacts:
        out.append("- Data outputs:")
        for a in artifacts:
            out.append(f"  - {a}")
    if notable:
        out.append("- Notable findings:")
        for ln in notable[:50]:
            out.append(f"  - {ln}")
    return "\n".join(out)


def chat_loop() -> None:
    ensure_paths()
    # Stylized banner
    BOLD = "\033[1m"
    RESET = "\033[0m"
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    print(
        f"{BOLD}{BLUE}NWB Agent{RESET} — chat interface. Type {BOLD}/help{RESET} for commands; {BOLD}quit{RESET} to exit."
    )

    # Conversation context and defaults
    defaults = {
        "out_dir": str((REPO_ROOT / "evaluation_agent_final" / "results").resolve()),
        "data": "stats",
        "ontology": "none",
        "overwrite": False,
        "sample_limit": None,
        "max_bytes": None,
        "stats_inline_limit": None,
        "linkml": False,
        "offline": False,
        "cache_dir": str(
            (REPO_ROOT / "evaluation_agent_final" / ".nwb_linkml_cache").resolve()
        ),
    }
    last_args: Optional[argparse.Namespace] = None

    def summarize_run(args: argparse.Namespace) -> None:
        try:
            out_dir = Path(args.out_dir)
            stem = Path(str(args.nwb)).expanduser().resolve().stem
            # Find most recent data TTL for this stem
            ttl_candidates = sorted(
                out_dir.glob(f"{stem}.data*.ttl"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if ttl_candidates:
                ttl = ttl_candidates[0]
                html = ttl.with_suffix(".html")
                jsonld = ttl.with_suffix(".jsonld")
                nt = ttl.with_suffix(".nt")
                triples = ttl.with_suffix(".triples.txt")
                print(f"{GREEN}Outputs:{RESET}")
                print(f" - TTL: {ttl}")
                if jsonld.exists():
                    print(f" - JSON-LD: {jsonld}")
                if nt.exists():
                    print(f" - N-Triples: {nt}")
                if triples.exists():
                    print(f" - triples.txt: {triples}")
                if html.exists():
                    print(f" - KG HTML: {html}")
            else:
                print(
                    f"{YELLOW}No TTL found in {out_dir} for {stem}. Check logs above.{RESET}"
                )

            # Find and summarize latest context file
            ctx_candidates = sorted(
                out_dir.glob(f"{stem}_context*.txt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if ctx_candidates:
                ctx = ctx_candidates[0]
                try:
                    text = ctx.read_text(encoding="utf-8", errors="ignore")
                    # Extract Decision line
                    decision = None
                    counts = None
                    for line in text.splitlines():
                        if line.startswith("Decision:"):
                            decision = line.split(":", 1)[-1].strip()
                        elif line.startswith("Inspector counts:"):
                            counts = line.split(":", 1)[-1].strip()
                    if decision:
                        if decision.upper().startswith("PASS"):
                            print(f"{GREEN}Check: PASS{RESET}")
                            if counts:
                                print(f" Inspector counts: {counts}")
                        else:
                            print(f"{YELLOW}Check: {decision}{RESET}")
                    print(f" Context: {ctx}")

                    # Offer concise summary
                    try:
                        want = (
                            input(
                                "Show summary of context? [n=skip, c=concise, d=detailed]: "
                            )
                            .strip()
                            .lower()
                        )
                    except Exception:
                        want = "n"
                    if want in {"c", "y", "yes"}:
                        print("Concise Summary:")
                        if decision:
                            tag = (
                                GREEN if decision.upper().startswith("PASS") else YELLOW
                            )
                            print(f" {tag}Decision:{RESET} {decision}")
                        if counts:
                            print(f" Counts: {counts}")
                        if ttl_candidates:
                            print(" Artifacts:")
                            print(f"  - TTL: {ttl}")
                            if html.exists():
                                print(f"  - KG HTML: {html}")
                    elif want == "d":
                        print("Detailed Summary:")
                        summary = llm_summarize_context(
                            text
                        ) or local_summarize_context(text)
                        print(summary)
                except Exception:
                    pass
        except Exception:
            pass

    def show_status():
        print("Current defaults:")
        for k, v in defaults.items():
            print(f" - {k}: {v}")
        if last_args is not None:
            print("Last run:")
            for k, v in vars(last_args).items():
                print(f"   {k}: {v}")

    def parse_set(cmd: str) -> None:
        # /set key=value
        m = re.match(r"/set\s+(\w+)\s*=\s*(.+)$", cmd, re.I)
        if not m:
            print("Usage: /set key=value")
            return
        key, val = m.group(1), m.group(2)
        if key not in defaults:
            print(f"Unknown setting: {key}")
            return
        if key in {"overwrite", "linkml", "offline"}:
            defaults[key] = str(val).strip().lower() in {"1", "true", "yes", "y", "on"}
        elif key in {"sample_limit", "max_bytes", "stats_inline_limit"}:
            try:
                defaults[key] = int(val)
            except ValueError:
                print("Expected integer value")
                return
        else:
            defaults[key] = val
        print(f"Set {key} = {defaults[key]}")

    while True:
        try:
            prompt = input("agent> ").strip()
        except EOFError:
            break
        if not prompt:
            continue
        if prompt.lower() in {"q", "quit", "exit"}:
            break

        # Commands
        if prompt.startswith("/help"):
            print(
                "Commands:\n"
                " /help                 Show this help\n"
                " /status               Show defaults and last run\n"
                " /set k=v              Set a default (e.g., /set data=sample)\n"
                ' /run "/path.nwb"    Run with current defaults and this NWB\n'
                " /repeat               Re-run the last invocation\n"
                " /examples             Show example prompts\n"
            )
            continue
        if prompt.startswith("/status"):
            show_status()
            continue
        if prompt.startswith("/set"):
            parse_set(prompt)
            continue
        if prompt.startswith("/examples"):
            print(
                "Examples:\n"
                ' process "/data/sample.nwb" with sample data and full ontology overwrite\n'
                ' set data to full, then run "/data/file.nwb"\n'
                " /set out_dir=./results_fast\n"
                ' /run "/abs/path/to/file with spaces.nwb"\n'
            )
            continue
        if prompt.startswith("/repeat"):
            if last_args is None:
                print("Nothing to repeat yet.")
                continue
            print("Re-running last job...")
            code = run_once(last_args)
            print(f"Done with code {code}.")
            summarize_run(last_args)
            continue
        if prompt.startswith("/run"):
            m = re.search(r"\"([^\"]+\.nwb)\"|\s(\S+\.nwb)\b", prompt)
            if not m:
                print('Usage: /run "/abs/path/file.nwb"')
                continue
            nwb_path = (m.group(1) or m.group(2)).strip()
            args = argparse.Namespace(
                nwb=nwb_path,
                out_dir=defaults["out_dir"],
                overwrite=bool(defaults["overwrite"]),
                data=defaults["data"],
                sample_limit=defaults["sample_limit"],
                max_bytes=defaults["max_bytes"],
                stats_inline_limit=defaults["stats_inline_limit"],
                ontology=defaults["ontology"],
                linkml=bool(defaults["linkml"]),
                offline=bool(defaults["offline"]),
                cache_dir=defaults["cache_dir"],
            )
            # Confirm
            print(f"{CYAN}About to run with:{RESET}")
            for k, v in vars(args).items():
                print(f" - {k}: {v}")
            ok = input(f"{BOLD}Proceed?{RESET} [y/N]: ").strip().lower() in {"y", "yes"}
            if not ok:
                print("Cancelled.")
                continue
            code = run_once(args)
            last_args = args
            print(f"Done with code {code}.")
            summarize_run(args)
            continue

        # If the user just pasted a path, treat as run
        if prompt.endswith(".nwb") and Path(prompt.strip("\"'")).expanduser().exists():
            args = argparse.Namespace(
                nwb=prompt.strip("\"'"),
                out_dir=defaults["out_dir"],
                overwrite=bool(defaults["overwrite"]),
                data=defaults["data"],
                sample_limit=defaults["sample_limit"],
                max_bytes=defaults["max_bytes"],
                stats_inline_limit=defaults["stats_inline_limit"],
                ontology=defaults["ontology"],
                linkml=bool(defaults["linkml"]),
                offline=bool(defaults["offline"]),
                cache_dir=defaults["cache_dir"],
            )
            print(f"{CYAN}About to run with:{RESET}")
            for k, v in vars(args).items():
                print(f" - {k}: {v}")
            ok = input(f"{BOLD}Proceed?{RESET} [y/N]: ").strip().lower() in {"y", "yes"}
            if not ok:
                print("Cancelled.")
                continue
            code = run_once(args)
            last_args = args
            print(f"Done with code {code}.")
            summarize_run(args)
            continue

        # Natural language: Prefer structured extraction; otherwise chat back helpfully
        opts = try_ollama_extract(prompt) or try_llm_extract(prompt)
        if not opts:
            # Provide a friendly response instead of the same error
            reply = ollama_chat_response(prompt) or openai_chat_response(prompt)
            if reply:
                print(reply)
                # Also hint actionable next steps
                print(
                    'Hint: use /run "/path/file.nwb" to start, or /help for commands.'
                )
                continue
            # Fallback minimal guidance
            print('I can run NWB evaluations. Try: /run "/abs/path/file.nwb" or /help.')
            continue
        # If we got partial options but no nwb, try regex fallback to pick a path; otherwise just update defaults
        if "nwb" not in opts:
            rx_opts = parse_natural_language(prompt)
            if "nwb" in rx_opts:
                opts["nwb"] = rx_opts["nwb"]
            else:
                # Treat as preference update
                provided_keys = {
                    k for k, v in opts.items() if v not in (None, False, "")
                }
                option_keys = {
                    "data",
                    "ontology",
                    "overwrite",
                    "sample_limit",
                    "max_bytes",
                    "stats_inline_limit",
                    "out_dir",
                    "linkml",
                    "offline",
                }
                if provided_keys.intersection(option_keys):
                    for k in option_keys:
                        if k in opts and opts[k] not in (None, ""):
                            if k in {"overwrite", "linkml", "offline"}:
                                defaults[k] = bool(opts[k])
                            elif k in {
                                "sample_limit",
                                "max_bytes",
                                "stats_inline_limit",
                            }:
                                with contextlib.suppress(Exception):
                                    defaults[k] = (
                                        int(opts[k]) if opts[k] is not None else None
                                    )
                            else:
                                defaults[k] = opts[k]
                    print(f"{GREEN}Updated defaults.{RESET}")
                    show_status()
                    continue
                # Otherwise just friendly reply
                reply = (
                    ollama_chat_response(prompt)
                    or openai_chat_response(prompt)
                    or 'I can run NWB evaluations. Try: /run "/abs/path/file.nwb" or /help.'
                )
                print(reply)
                continue

        # If only options were provided, update defaults and confirm
        provided_keys = {k for k, v in opts.items() if v not in (None, False, "")}
        option_keys = {
            "data",
            "ontology",
            "overwrite",
            "sample_limit",
            "max_bytes",
            "stats_inline_limit",
            "out_dir",
            "linkml",
            "offline",
        }
        if "nwb" not in opts and provided_keys.intersection(option_keys):
            # Apply to defaults
            for k in option_keys:
                if k in opts and opts[k] not in (None, ""):
                    if k in {"overwrite", "linkml", "offline"}:
                        defaults[k] = bool(opts[k])
                    elif k in {"sample_limit", "max_bytes", "stats_inline_limit"}:
                        with contextlib.suppress(Exception):
                            defaults[k] = int(opts[k]) if opts[k] is not None else None
                    else:
                        defaults[k] = opts[k]
            print(f"{GREEN}Updated defaults.{RESET}")
            show_status()
            continue

        if "nwb" not in opts:
            print(
                "Please include a path to an .nwb file in quotes or as a token, or use /run."
            )
            continue

        # Merge with defaults
        merged = {
            "nwb": opts.get("nwb"),
            "out_dir": opts.get("out_dir") or defaults["out_dir"],
            "overwrite": bool(opts.get("overwrite", defaults["overwrite"])),
            "data": opts.get("data") or defaults["data"],
            "sample_limit": opts.get("sample_limit", defaults["sample_limit"]),
            "max_bytes": opts.get("max_bytes", defaults["max_bytes"]),
            "stats_inline_limit": opts.get(
                "stats_inline_limit", defaults["stats_inline_limit"]
            ),
            "ontology": opts.get("ontology") or defaults["ontology"],
            "linkml": bool(opts.get("linkml", defaults["linkml"])),
            "offline": bool(opts.get("offline", defaults["offline"])),
            "cache_dir": defaults["cache_dir"],
        }

        # Ask for confirmation if critical options are missing
        missing = []
        if not merged.get("nwb"):
            missing.append("nwb path")
        if missing:
            print("Missing:", ", ".join(missing))
            continue

        args = argparse.Namespace(**merged)
        print(f"{CYAN}About to run with:{RESET}")
        for k, v in vars(args).items():
            print(f" - {k}: {v}")
        ok = input(f"{BOLD}Proceed?{RESET} [y/N]: ").strip().lower() in {"y", "yes"}
        if not ok:
            print("Cancelled.")
            continue
        code = run_once(args)
        last_args = args
        print(f"Done with code {code}.")
        summarize_run(args)


def main() -> None:
    p = argparse.ArgumentParser(description="Agent wrapper around run_single_agent.py")
    sub = p.add_subparsers(dest="mode")

    prun = sub.add_parser("run", help="Run once with explicit arguments")
    prun.add_argument("nwb", type=str, help="Path to NWB file")
    prun.add_argument(
        "--out-dir",
        type=str,
        default=str((REPO_ROOT / "evaluation_agent_final" / "results").resolve()),
    )
    prun.add_argument("--overwrite", action="store_true")
    prun.add_argument(
        "--data", choices=["none", "stats", "sample", "full"], default="stats"
    )
    prun.add_argument("--sample-limit", type=int, default=None)
    prun.add_argument("--max-bytes", type=int, default=None)
    prun.add_argument("--stats-inline-limit", type=int, default=None)
    prun.add_argument("--ontology", choices=["none", "full"], default="none")
    prun.add_argument("--linkml", action="store_true")
    prun.add_argument("--offline", action="store_true")
    prun.add_argument(
        "--cache-dir",
        type=str,
        default=str(
            (REPO_ROOT / "evaluation_agent_final" / ".nwb_linkml_cache").resolve()
        ),
    )

    sub.add_parser("chat", help="Interactive natural-language mode")

    args = p.parse_args()
    if args.mode == "run":
        sys.exit(run_once(args))
    else:
        chat_loop()


if __name__ == "__main__":
    main()
