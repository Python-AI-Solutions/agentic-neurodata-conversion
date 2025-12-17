#!/usr/bin/env python3
"""Agentic Neurodata Conversion - Application Startup Script.

This script handles:
- Configuration validation (via config.py)
- Process management (starting backend/frontend)
- Health checks and status reporting
- User-friendly console output

Usage:
    python3 start_app.py
    # Or make executable:
    chmod +x start_app.py
    ./start_app.py
"""

import argparse
import os
import signal
import socket
import subprocess  # nosec B404 - subprocess needed for process management in dev tool
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from agentic_neurodata_conversion.config import ConfigError, get_settings
except ModuleNotFoundError as e:
    raise SystemExit(
        "Startup script dependencies are missing (failed import: "
        f"{getattr(e, 'name', 'unknown')}). Run via `pixi run start` from the repo root."
    ) from e


# ANSI color codes for pretty output
class Colors:
    """ANSI color codes for console output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")


def docker_daemon_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    try:
        # `docker info` is the most direct "daemon reachable" probe.
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)  # nosec B603,B607 - dev tool
        return result.returncode == 0
    except FileNotFoundError:
        return False


def print_docker_help() -> None:
    """Print actionable help when docker isn't available."""
    print_error("Docker daemon is not reachable.")
    print_info("Fix:")
    print_info("  - macOS: start Docker Desktop (Applications → Docker) and wait until it says 'Running'.")
    print_info("  - Verify: `docker info` should succeed.")
    print_info("  - Workaround (no docker): `pixi run start -- --core none`")


def _mode_badge(mode: str) -> str:
    """Human-friendly mode tag."""
    mode_clean = (mode or "").strip().lower()
    if mode_clean == "docker":
        return "docker"
    if mode_clean == "local":
        return "local"
    return "none"


def print_runtime_topology(*, core_mode: str, api_mode: str, kg_mode: str, frontend_mode: str) -> None:
    """Print a concise view of which components run where."""
    uses_compose = core_mode == "docker" or api_mode == "docker" or kg_mode == "docker" or frontend_mode == "docker"
    neo4j_mode = "docker" if uses_compose else "none"
    seed_mode = "docker" if uses_compose else "none"

    print_header("Runtime Topology")
    print_info(f"Compose stack: {'enabled' if uses_compose else 'disabled'}")
    print_info(f"Neo4j: {neo4j_mode}")
    print_info(f"KG seed job: {seed_mode}")
    print_info(f"KG service: {_mode_badge(kg_mode)}")
    print_info(f"Backend API: {_mode_badge(api_mode)}")
    print_info(f"Frontend: {_mode_badge(frontend_mode)}")
    print()


def kill_process_on_port(port: int) -> bool:
    """Kill any process running on the specified port."""
    try:
        # Find process on port
        result = subprocess.run(f"lsof -ti:{port}", shell=True, capture_output=True, text=True)  # nosec B602 - safe: port is int, no user input

        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(f"kill -9 {pid}", shell=True)  # nosec B602 - safe: pid from lsof output, validated numeric
            print_success(f"Killed process on port {port}")
            return True
        return False
    except Exception as e:
        print_warning(f"Could not kill process on port {port}: {e}")
        return False


def clean_temp_directories() -> None:
    """Clean temporary upload and conversion directories."""
    import shutil
    import tempfile

    temp_dir = tempfile.gettempdir()
    upload_dir = Path(temp_dir) / "nwb_uploads"
    conversion_dir = Path(temp_dir) / "nwb_conversions"

    cleaned = False

    # Clean upload directory
    if upload_dir.exists():
        try:
            shutil.rmtree(upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
            print_success(f"Cleaned upload directory: {upload_dir}")
            cleaned = True
        except Exception as e:
            print_warning(f"Could not clean upload directory: {e}")

    # Clean conversion directory
    if conversion_dir.exists():
        try:
            shutil.rmtree(conversion_dir)
            conversion_dir.mkdir(parents=True, exist_ok=True)
            print_success(f"Cleaned conversion directory: {conversion_dir}")
            cleaned = True
        except Exception as e:
            print_warning(f"Could not clean conversion directory: {e}")

    if not cleaned:
        print_info("No temp directories to clean")


def is_port_in_use(port: int) -> bool:
    """Return True if the port is accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("localhost", port)) == 0


def perform_cleanup() -> None:
    """Best-effort cleanup: stop ports and clear temp dirs."""
    import tempfile

    temp_dir = Path(tempfile.gettempdir())
    upload_dir = temp_dir / "nwb_uploads"
    conversion_dir = temp_dir / "nwb_conversions"

    ports_in_use = [port for port in (8000, 8001, 3000) if is_port_in_use(port)]
    dirs_to_clean = [path for path in (upload_dir, conversion_dir) if path.exists()]

    print_header("Startup Cleanup")

    cleanup_targets: list[str] = []
    if ports_in_use:
        cleanup_targets.append(f"stop processes on ports {', '.join(str(p) for p in ports_in_use)}")
    if dirs_to_clean:
        cleanup_targets.append(f"delete temp dirs: {', '.join(str(p) for p in dirs_to_clean)}")

    if not cleanup_targets:
        print_info("No ports or temp directories need cleanup; skipping.")
        return

    if ports_in_use:
        print_info(f"Stopping processes on ports {', '.join(str(p) for p in ports_in_use)}...")
        for port in ports_in_use:
            kill_process_on_port(port)
        time.sleep(2)  # Give OS time to release ports

    if dirs_to_clean:
        print_header("Cleaning Temp Directories")
        clean_temp_directories()
        time.sleep(1)


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be available."""
    import urllib.request

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)  # nosec B310 - safe: health check URLs are hardcoded localhost only
            return True
        except Exception:
            time.sleep(0.5)
    return False


def validate_configuration() -> None:
    """Validate required configuration is present before starting services."""
    print_header("Configuration Validation")

    settings = get_settings()
    try:
        settings.require_api()
        settings.require_kg_client()
    except ConfigError as e:
        print_error(str(e))
        print_info("Fix:")
        print_info("  1) cp .env.example .env")
        print_info("  2) edit .env as needed")
        raise SystemExit(1) from e

    print_success("Required configuration present")


def require_dotenv_files(env_file: str, *, require_docker_env: bool) -> None:
    """Require dotenv files to exist; suggest copying templates if missing."""
    env_path = Path(env_file)
    if not env_path.exists():
        print_error(f"Missing env file: {env_path}")
        example = env_path.with_name(".env.example")
        if example.exists():
            print_info(f"Create it with: cp {example} {env_path}")
        else:
            print_info("Create it by copying the template: cp .env.example .env")
        raise SystemExit(1)

    if not require_docker_env:
        return

    docker_env = env_path.with_name(".env.docker")
    if not docker_env.exists():
        print_error(f"Missing docker env overrides: {docker_env}")
        docker_example = env_path.with_name(".env.docker.example")
        if docker_example.exists():
            print_info(f"Create it with: cp {docker_example} {docker_env}")
        else:
            print_info("Create it by copying the template: cp .env.docker.example .env.docker")
        raise SystemExit(1)


def _run_compose(args: list[str]) -> int:
    """Run docker compose command and return exit code."""
    cmd = ["docker", "compose", "--env-file", os.environ.get("COMPOSE_ENV_FILE", ".env")]
    cmd += ["-f", "compose.yaml"]
    if Path("compose.override.yaml").exists():
        cmd += ["-f", "compose.override.yaml"]
    cmd += args
    return subprocess.call(cmd)  # nosec B603,B607 - dev tool, fixed args


def wait_for_compose_seed(*, base_cmd: list[str], timeout_s: int = 300) -> bool:
    """Wait for `kg-seed` to exit successfully (best-effort)."""
    start = time.time()
    while time.time() - start < timeout_s:
        ps = subprocess.run([*base_cmd, "ps", "-a", "kg-seed"], capture_output=True, text=True, check=False)
        out = (ps.stdout or "") + (ps.stderr or "")

        if "no such service" in out.lower():
            return True

        if "Exited (0)" in out:
            return True

        if "Exited (" in out and "Exited (0)" not in out:
            print_error("kg-seed exited non-zero; check logs with `docker compose logs kg-seed`.")
            return False

        time.sleep(2)

    print_error("Timed out waiting for kg-seed to complete")
    return False


def start_compose_services(*, profiles: list[str], reset_db: bool) -> bool:
    """Start docker compose services and wait for readiness."""
    print_header("Starting Docker Services")
    print_info("CLI options: --core docker|none, --kg docker, --frontend docker, --api docker, --reset-db")
    print_info(f"Mode: docker (profiles: {', '.join(profiles) if profiles else 'core-only'})")

    if not docker_daemon_available():
        print_docker_help()
        return False

    env_file = os.environ.get("COMPOSE_ENV_FILE", ".env")
    base = ["docker", "compose", "--env-file", env_file, "-f", "compose.yaml"]
    override = Path("compose.override.yaml")
    if override.exists():
        base += ["-f", str(override)]

    profile_args: list[str] = []
    for profile in profiles:
        profile_args += ["--profile", profile]

    if reset_db:
        print_warning("Resetting compose volumes (dev only)...")
        subprocess.call([*base, *profile_args, "down", "-v", "--remove-orphans"])  # nosec B603,B607 - dev tool

    print_info("Bringing compose stack up...")
    rc = subprocess.call([*base, *profile_args, "up", "-d", "--build", "--remove-orphans"])  # nosec B603,B607
    if rc != 0:
        print_error("docker compose up failed")
        return False

    settings = get_settings()
    neo4j_ready = wait_for_server(f"http://localhost:{settings.compose.neo4j_http_port}", timeout=180)
    if not neo4j_ready:
        print_error("Neo4j did not become ready")
        return False

    # Wait for seed to complete (best-effort). Prefer `ps` parsing over `docker compose wait`
    # since `wait` is not consistently available across compose versions.
    print_info("Waiting for kg-seed to complete...")
    if not wait_for_compose_seed(base_cmd=base, timeout_s=300):
        return False

    if "kg" in profiles:
        if not wait_for_server(f"http://localhost:{settings.compose.kg_service_port}/health", timeout=300):
            print_error("kg-service did not become healthy")
            return False

    if "frontend" in profiles:
        if not wait_for_server(f"http://localhost:{settings.compose.frontend_port}", timeout=60):
            print_warning("frontend did not become reachable")

    print_success("Docker services ready")
    return True


def start_kg_service(*, no_install: bool) -> subprocess.Popen | None:
    """Start the KG service (FastAPI + Uvicorn)."""
    print_header("Starting Knowledge Graph Service")
    print_info("CLI options: --kg local|docker|none, --no-reload, --no-install")
    print_info("Mode: local")

    settings = get_settings()
    kg_port = settings.kg_service.port

    if is_port_in_use(kg_port):
        print_warning(f"Port {kg_port} is already in use; assuming KG service is already running.")
        return None

    try:
        reload_flag = "--reload" if getattr(start_kg_service, "_reload", True) else ""
        pixi_prefix = "pixi run --no-install" if no_install else "pixi run"
        pixi_cmd = (
            f"{pixi_prefix} uvicorn agentic_neurodata_conversion.kg_service.main:app "
            f"{reload_flag} --host {settings.kg_service.host} --port {settings.kg_service.port}"
        ).strip()
        print_info(f"Starting KG service with: {pixi_cmd}")

        log_file = open("/tmp/kg-service.log", "w")  # nosec B108 - temporary log file for dev tool  # noqa: SIM115

        child_env = os.environ.copy()
        process = subprocess.Popen(  # nosec B607, B602 - safe: pixi command is hardcoded, no user input
            pixi_cmd,
            shell=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
            env=child_env,
        )

        print_info("Waiting for KG service to initialize...")
        time.sleep(5)

        if wait_for_server(f"http://localhost:{kg_port}/health", timeout=15):
            print_success("KG service started successfully!")
            print_info(f"KG service URL: http://localhost:{kg_port}")
            return process

        print_warning("KG service did not become healthy; continuing without it.")
        log_file.close()
        return None

    except Exception as e:
        print_warning(f"Failed to start KG service: {e}")
        return None


def start_backend(*, no_install: bool) -> subprocess.Popen | None:
    """Start the backend server."""
    print_header("Starting Backend Server")
    print_info("CLI options: --api local|docker|none, --no-reload, --no-install")
    print_info("Mode: local")

    try:
        settings = get_settings()
        api_port = settings.api.port
        reload_flag = "--reload" if getattr(start_backend, "_reload", True) else ""
        pixi_prefix = "pixi run --no-install" if no_install else "pixi run"
        pixi_cmd = (
            f"{pixi_prefix} uvicorn agentic_neurodata_conversion.api.main:app "
            f"{reload_flag} --host {settings.api.host} --port {settings.api.port}"
        ).strip()
        print_info(f"Starting backend with: {pixi_cmd}")

        # Open log file for output
        log_file = open("/tmp/backend.log", "w")  # nosec B108 - temporary log file for dev tool  # noqa: SIM115

        child_env = os.environ.copy()
        process = subprocess.Popen(  # nosec B607, B602 - safe: pixi command is hardcoded, no user input
            pixi_cmd,
            shell=True,  # Required for pixi subprocess management
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,  # Create new process group
            env=child_env,
        )

        # Wait for server to be ready
        print_info("Waiting for backend to initialize...")
        time.sleep(5)

        # Check if server is running
        if wait_for_server(f"http://localhost:{api_port}/api/health", timeout=10):
            print_success("Backend server started successfully!")
            print_info(f"Backend URL: http://localhost:{api_port}")
            print_info(f"API Docs: http://localhost:{api_port}/docs")
            return process
        else:
            print_error("Backend server failed to start (health check failed)")
            log_file.close()
            return None

    except Exception as e:
        print_error(f"Failed to start backend: {e}")
        return None


def start_frontend() -> subprocess.Popen | None:
    """Start the frontend server."""
    print_header("Starting Frontend Server")
    print_info("CLI options: --frontend local|docker|none")
    print_info("Mode: local")

    try:
        # Check if chat-ui.html exists in frontend/public
        frontend_path = Path("frontend/public")
        chat_ui_path = frontend_path / "chat-ui.html"

        if not chat_ui_path.exists():
            print_error(f"chat-ui.html not found at {chat_ui_path}")
            print_info("Expected location: frontend/public/chat-ui.html")
            return None

        print_info("Starting frontend HTTP server...")

        # Open log file for output
        log_file = open("/tmp/frontend.log", "w")  # nosec B108 - temporary log file for dev tool  # noqa: SIM115

        settings = get_settings()
        port = settings.compose.frontend_port

        # Change to frontend/public directory and start server
        process = subprocess.Popen(  # nosec B607, B602 - safe: python3 command and port are hardcoded, no user input
            f"cd frontend/public && python3 -m http.server {port}",
            shell=True,  # Required for module execution and cd command
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,  # Create new process group
            env=os.environ.copy(),
        )

        # Wait for server to be ready
        time.sleep(2)

        if wait_for_server(f"http://localhost:{port}/chat-ui.html", timeout=5):
            print_success("Frontend server started successfully!")
            print_info(f"Frontend URL: http://localhost:{port}/chat-ui.html")
            return process
        else:
            print_error("Frontend server failed to start")
            log_file.close()
            return None

    except Exception as e:
        print_error(f"Failed to start frontend: {e}")
        return None


def display_status() -> None:
    """Display application status and URLs."""
    print_header("Application Status")

    print(f"{Colors.BOLD}{Colors.GREEN}✅ Application is running!{Colors.END}\n")

    settings = get_settings()
    api_port = settings.api.port
    kg_port = settings.kg_service.port
    fe_port = settings.compose.frontend_port

    print(f"{Colors.BOLD}Backend:{Colors.END}")
    print(f"  • API:          {Colors.CYAN}http://localhost:{api_port}{Colors.END}")
    print(f"  • Health:       {Colors.CYAN}http://localhost:{api_port}/api/health{Colors.END}")
    print(f"  • Docs:         {Colors.CYAN}http://localhost:{api_port}/docs{Colors.END}")
    print(f"  • WebSocket:    {Colors.CYAN}ws://localhost:{api_port}/ws{Colors.END}")
    print()

    print(f"{Colors.BOLD}Frontend:{Colors.END}")
    print(f"  • Chat UI:      {Colors.CYAN}http://localhost:{fe_port}/chat-ui.html{Colors.END}")
    print()

    print(f"{Colors.BOLD}Knowledge Graph:{Colors.END}")
    print(f"  • Service:      {Colors.CYAN}http://localhost:{kg_port}{Colors.END}")
    print()

    print(f"{Colors.BOLD}Logs:{Colors.END}")
    print(f"  • Backend:      {Colors.CYAN}/tmp/backend.log{Colors.END}")  # nosec B108 - display only, not actual file operation
    print(f"  • Frontend:     {Colors.CYAN}/tmp/frontend.log{Colors.END}")  # nosec B108 - display only, not actual file operation
    print(f"  • KG Service:   {Colors.CYAN}/tmp/kg-service.log{Colors.END}")  # nosec B108 - display only, not actual file operation
    print()

    print(f"{Colors.YELLOW}Press Ctrl+C to stop all servers{Colors.END}")
    print()


def main() -> None:
    """Main startup routine."""
    parser = argparse.ArgumentParser(description="Start app + frontend for local development.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Stop anything on ports 8000/8001/3000 and delete temp dirs under /tmp.",
    )
    parser.add_argument("--core", choices=["docker", "none"], default="docker", help="Core services (neo4j + seed).")
    parser.add_argument("--api", choices=["local", "docker", "none"], default="local", help="API service mode.")
    parser.add_argument("--kg", choices=["local", "docker", "none"], default="local", help="KG service mode.")
    parser.add_argument(
        "--frontend",
        choices=["local", "docker", "none"],
        default="local",
        help="Frontend service mode (static chat UI).",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Dotenv file to load for Python config and docker compose (default: .env).",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable hot reload for local uvicorn processes.",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Do not install/update the pixi environment before running (faster if already installed).",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset docker volumes (Neo4j data) before starting (dev only).",
    )
    parser.add_argument(
        "--allow-missing-anthropic-key",
        action="store_true",
        help="Allow starting without CORE__ANTHROPIC_API_KEY (useful for some tests).",
    )
    args = parser.parse_args()

    # Print welcome banner
    print_header("Agentic Neurodata Conversion - Startup Script")

    print_header("Startup Options")
    print_info("Re-run with different modes using:")
    print_info("  pixi run start -- --help")
    print_info("Examples:")
    print_info("  - Default: core docker, api/kg/frontend local: `pixi run start`")
    print_info("  - Full docker: `pixi run start -- --kg docker --frontend docker`")
    print_info("  - No docker: `pixi run start -- --core none`")
    print_info("  - Clean ports/temp: `pixi run start -- --clean`")
    print()
    print_info(f"Selected modes: core={args.core}, api={args.api}, kg={args.kg}, frontend={args.frontend}")
    if args.no_reload:
        print_info("Hot reload: disabled (--no-reload)")
    else:
        print_info("Hot reload: enabled (default)")
    if args.no_install:
        print_info("Pixi install/update: disabled (--no-install)")
    print()

    print_runtime_topology(core_mode=args.core, api_mode=args.api, kg_mode=args.kg, frontend_mode=args.frontend)

    print(f"{Colors.BOLD}This script will:{Colors.END}")
    steps: list[str] = ["Validate configuration (via config.py)"]
    if args.clean:
        steps.append("Clean ports 8000/8001/3000 and temp dirs")
    if args.core == "docker" or args.api == "docker" or args.kg == "docker" or args.frontend == "docker":
        steps.append("Start docker compose services")
    if args.kg == "local":
        steps.append("Start KG service (FastAPI + Uvicorn)")
    if args.api == "local":
        steps.append("Start backend server (FastAPI + Uvicorn)")
    if args.frontend == "local":
        steps.append("Start frontend server (HTTP server)")
    steps.append("Display application URLs")
    for i, step in enumerate(steps, start=1):
        print(f"  {i}. {step}")
    print()

    backend_process = None
    frontend_process = None
    kg_process = None
    started_compose = False

    try:
        # Ensure all child processes use the same env file for config.py.
        env_file_path = str(Path(args.env_file).expanduser().resolve())
        os.environ["ENV_FILE"] = env_file_path
        os.environ["COMPOSE_ENV_FILE"] = env_file_path

        uses_docker = args.core == "docker" or args.api == "docker" or args.kg == "docker" or args.frontend == "docker"
        require_dotenv_files(env_file_path, require_docker_env=uses_docker)

        if args.allow_missing_anthropic_key:
            os.environ["CORE__ALLOW_MISSING_ANTHROPIC_API_KEY"] = "true"

        if args.api == "docker" and args.kg != "docker":
            print_error("--api docker requires --kg docker (container networking uses service-name URLs).")
            sys.exit(2)

        # Step 1: Validate config
        validate_configuration()

        # Step 2: Optional cleanup
        if args.clean:
            perform_cleanup()

        docker_profiles: list[str] = []
        if args.kg == "docker":
            docker_profiles.append("kg")
        if args.frontend == "docker":
            docker_profiles.append("frontend")
        if args.api == "docker":
            docker_profiles.append("app")

        if args.core == "docker" or docker_profiles:
            ok = start_compose_services(profiles=docker_profiles, reset_db=bool(args.reset_db))
            if not ok:
                sys.exit(1)
            started_compose = True

        # Start local services
        start_kg_service._reload = not args.no_reload  # type: ignore[attr-defined]
        if args.kg == "local":
            kg_process = start_kg_service(no_install=bool(args.no_install))

        # Step 4: Start backend
        start_backend._reload = not args.no_reload  # type: ignore[attr-defined]
        if args.api == "local":
            backend_process = start_backend(no_install=bool(args.no_install))
            if not backend_process:
                print_error("Cannot continue without backend server")
                sys.exit(1)

        # Step 5: Start frontend (optional)
        if args.frontend == "local":
            frontend_process = start_frontend()
            if not frontend_process:
                print_warning("Frontend failed to start, but backend is running")

        # Step 6: Display status
        display_status()

        # Keep script running and monitor processes
        while True:
            time.sleep(1)

            # Check if processes are still running
            if backend_process and backend_process.poll() is not None:
                print_error("Backend process died unexpectedly!")
                break

            if frontend_process and frontend_process.poll() is not None:
                print_warning("Frontend process died unexpectedly!")
                # Don't break, backend might still be running

    except KeyboardInterrupt:
        print_header("Shutting Down")
        print_info("Stopping servers...")

        # Cleanup processes
        if kg_process:
            try:
                os.killpg(os.getpgid(kg_process.pid), signal.SIGTERM)
                print_success("KG service stopped")
            except Exception:  # nosec B110 - intentional: cleanup errors can be safely ignored
                pass

        if backend_process:
            try:
                os.killpg(os.getpgid(backend_process.pid), signal.SIGTERM)
                print_success("Backend stopped")
            except Exception:  # nosec B110 - intentional: cleanup errors can be safely ignored
                pass

        if frontend_process:
            try:
                os.killpg(os.getpgid(frontend_process.pid), signal.SIGTERM)
                print_success("Frontend stopped")
            except Exception:  # nosec B110 - intentional: cleanup errors can be safely ignored
                pass

        # Kill processes on ports as backup
        kill_process_on_port(8000)
        kill_process_on_port(8001)
        kill_process_on_port(3000)

        if started_compose:
            print_info(
                "Docker services remain running; stop with `docker compose --env-file .env -f compose.yaml -f compose.override.yaml down`."
            )

        print_success("Shutdown complete")
        print()

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if running from correct directory
    if not Path("pyproject.toml").exists():
        print_error("Please run this script from the project root directory")
        sys.exit(1)

    main()
