#!/usr/bin/env python3
"""Run a command with the core docker-compose stack up.

Starts the core stack (Neo4j + seed), waits for readiness, runs the given
command, and optionally tears the stack down.

Usage:
  pixi run python scripts/compose/run_with_compose.py -- pytest tests -v

Environment:
  COMPOSE_FILES="compose.yaml,compose.override.yaml" (comma-separated list)
  COMPOSE_PROJECT_NAME="agentic-neurodata-conversion" (optional)
  COMPOSE_DOWN=1 (tear down after command; default: in CI only)
  COMPOSE_WAIT_SEED=1 (wait for kg-seed success; default: 1)
  COMPOSE_PROFILES="kg" (comma-separated list; default: "kg")
  NEO4J_HTTP_PORT (override readiness probe port)
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - dev/CI orchestration
import sys
import time
import urllib.request
from pathlib import Path

from agentic_neurodata_conversion.config import get_settings


def _compose_base_cmd() -> list[str]:
    files = [
        f.strip() for f in os.getenv("COMPOSE_FILES", "compose.yaml,compose.override.yaml").split(",") if f.strip()
    ]
    cmd = ["docker", "compose"]

    # Ensure `docker compose` reads the repo's `.env` even when invoked from other CWDs.
    env_file = Path(os.getenv("COMPOSE_ENV_FILE", ".env"))
    if env_file.exists():
        cmd += ["--env-file", str(env_file)]

    for f in files:
        cmd += ["-f", f]
    profiles = [p.strip() for p in os.getenv("COMPOSE_PROFILES", "kg").split(",") if p.strip()]
    for profile in profiles:
        cmd += ["--profile", profile]
    project = os.getenv("COMPOSE_PROJECT_NAME")
    if project:
        cmd += ["-p", project]
    return cmd


def _http_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:  # nosec B310 - controlled localhost URLs
            return bool(resp.status == 200)
    except Exception:
        return False


def _wait_for_url(url: str, timeout_s: int) -> None:
    start = time.time()
    last_log = 0.0
    while time.time() - start < timeout_s:
        if _http_ready(url):
            return
        now = time.time()
        if now - last_log > 5:
            last_log = now
            print(f"Waiting for {url} ... ({int(now - start)}s elapsed)")
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {url}")


def _seed_completed_successfully(compose: list[str], timeout_s: int) -> None:
    """Wait for kg-seed to exit 0, if present in the compose project."""
    start = time.time()
    while time.time() - start < timeout_s:
        # `docker compose ps` exits 0 even if the service doesn't exist; check output.
        ps = subprocess.run([*compose, "ps", "-a", "kg-seed"], capture_output=True, text=True, check=False)
        out = (ps.stdout or "") + (ps.stderr or "")
        if "no such service" in out.lower():
            return
        # Compose formats like: "... kg-seed-1  Exited (0) ..."
        if "Exited (0)" in out:
            return
        if "Exited (" in out and "Exited (0)" not in out:
            raise RuntimeError(f"kg-seed exited non-zero:\n{out.strip()}")
        time.sleep(2)
    raise TimeoutError("Timed out waiting for kg-seed to complete")


def _service_exited(compose: list[str], service: str) -> str | None:
    """Return a short status string if `service` is exited/restarting; otherwise None."""
    ps = subprocess.run([*compose, "ps", "-a", service], capture_output=True, text=True, check=False)
    out = (ps.stdout or "") + (ps.stderr or "")
    lowered = out.lower()
    if "no such service" in lowered:
        return None
    if "exited" in lowered:
        return out.strip()
    if "restarting" in lowered:
        return out.strip()
    return None


def _print_recent_logs(compose: list[str], service: str, *, tail: int = 200) -> None:
    logs = subprocess.run([*compose, "logs", "--tail", str(tail), service], capture_output=True, text=True, check=False)
    text = (logs.stdout or "") + (logs.stderr or "")
    if text.strip():
        print(f"\n--- docker compose logs --tail={tail} {service} ---\n{text.strip()}\n--- end logs ---\n")


def main() -> int:
    """Entrypoint for running a command with the compose stack up."""
    if "--" in sys.argv:
        cmd = sys.argv[sys.argv.index("--") + 1 :]
    else:
        cmd = sys.argv[1:]

    if not cmd:
        raise SystemExit("Expected a command after `--` (e.g., `-- pytest tests -v`)")

    # Ensure config.py and docker compose both read the repo's `.env` consistently.
    if "ENV_FILE" not in os.environ and Path(".env").exists():
        os.environ["ENV_FILE"] = str(Path(".env").resolve())
    if "COMPOSE_ENV_FILE" not in os.environ and Path(".env").exists():
        os.environ["COMPOSE_ENV_FILE"] = str(Path(".env").resolve())

    compose = _compose_base_cmd()

    subprocess.run([*compose, "up", "-d", "--build"], check=True)

    settings = get_settings()
    neo4j_http_port = settings.compose.neo4j_http_port
    kg_service_port = settings.compose.kg_service_port

    print(f"Waiting for Neo4j on http://localhost:{neo4j_http_port} ...")
    _wait_for_url(f"http://localhost:{neo4j_http_port}", timeout_s=180)

    wait_seed = os.getenv("COMPOSE_WAIT_SEED", "1").lower() in ("1", "true", "yes")
    if wait_seed:
        print("Waiting for kg-seed to complete ...")
        _seed_completed_successfully(compose, timeout_s=300)

    # Default to waiting for kg-service since CI is expected to have the full stack.
    wait_kg = os.getenv("COMPOSE_WAIT_KG", "1").lower() in ("1", "true", "yes")
    if wait_kg:
        print(f"Waiting for kg-service on http://localhost:{kg_service_port}/health ...")
        url = f"http://localhost:{kg_service_port}/health"
        start = time.time()
        while True:
            if _http_ready(url):
                break
            status = _service_exited(compose, "kg-service")
            if status:
                print("kg-service is not running cleanly; aborting wait.")
                print(status)
                _print_recent_logs(compose, "kg-service", tail=200)
                raise RuntimeError("kg-service failed to start; see logs above.")
            if time.time() - start > 300:
                _print_recent_logs(compose, "kg-service", tail=200)
                raise TimeoutError(f"Timed out waiting for {url}")
            # progress logging (same cadence as `_wait_for_url`)
            elapsed = int(time.time() - start)
            if elapsed % 5 == 0:
                print(f"Waiting for {url} ... ({elapsed}s elapsed)")
            time.sleep(1)

    teardown = os.getenv("COMPOSE_DOWN")
    if teardown is None:
        teardown = "1" if os.getenv("CI", "").lower() in ("1", "true", "yes") else "0"

    try:
        env = os.environ.copy()
        if "ENV_FILE" not in env and Path(".env").exists():
            env["ENV_FILE"] = str(Path(".env").resolve())
        return subprocess.call(cmd, env=env)
    finally:
        if teardown.lower() in ("1", "true", "yes"):
            subprocess.run([*compose, "down", "--remove-orphans"], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
