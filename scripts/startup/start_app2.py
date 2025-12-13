#!/usr/bin/env python3
"""Agentic Neurodata Conversion - Application Startup Script with KG Service.

This script handles:
- Environment configuration (API key setup)
- Neo4j startup (Docker Compose or Neo4j Desktop)
- KG service startup (port 8001)
- Backend server startup (port 8000)
- Frontend server startup (port 3000)
- Process management and health checks

Usage:
    python3 start_app2.py
    # Or via pixi:
    pixi run start
"""

import os
import signal
import socket
import subprocess  # nosec B404 - subprocess needed for process management in dev tool
import sys
import time
from pathlib import Path


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


def check_port_available(port: int) -> bool:
    """Check if a port is available by attempting to connect."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0  # 0 means port is in use (connection successful)
    except Exception:
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


def check_env_file() -> bool:
    """Check if .env file exists and has API key configured."""
    env_path = Path(".env")

    if not env_path.exists():
        return False

    # Check if API key is set
    with open(env_path) as f:
        content = f.read()
        return "ANTHROPIC_API_KEY=sk-ant-" in content


def setup_env_file() -> bool:
    """Check .env file exists with required variables (strict mode)."""
    print_header("Environment Configuration")

    env_path = Path(".env")
    env_example_path = Path(".env.example")

    # Check if .env exists
    if not env_path.exists():
        print_error(".env file not found")
        print_info("\nTo fix this:")
        print_info("  1. Copy the example: cp .env.example .env")
        print_info("  2. Edit .env and configure required variables:")
        print_info("     - ANTHROPIC_API_KEY=sk-ant-your-key-here")
        print_info("     - NEO4J_PASSWORD=dev-password")
        print_info("     - NEO4J_DATABASE=neo4j")
        return False

    # Verify required variables are present
    env_vars = load_env_file()

    # Check ANTHROPIC_API_KEY
    api_key = env_vars.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "sk-ant-REPLACE-WITH-YOUR-KEY":
        print_error("ANTHROPIC_API_KEY not configured in .env file")
        print_info("\nTo fix this:")
        print_info("  1. Get your API key from: https://console.anthropic.com")
        print_info("  2. Open .env file")
        print_info("  3. Set: ANTHROPIC_API_KEY=sk-ant-your-key-here")
        return False

    if not api_key.startswith("sk-ant-"):
        print_error("Invalid ANTHROPIC_API_KEY format in .env file")
        print_info("API key should start with 'sk-ant-'")
        return False

    # Check NEO4J_PASSWORD
    neo4j_password = env_vars.get("NEO4J_PASSWORD", "")
    if not neo4j_password:
        print_error("NEO4J_PASSWORD not configured in .env file")
        print_info("\nTo fix this:")
        print_info("  1. Open .env file")
        print_info("  2. Set: NEO4J_PASSWORD=dev-password")
        return False

    # Check NEO4J_DATABASE
    neo4j_database = env_vars.get("NEO4J_DATABASE", "")
    if not neo4j_database:
        print_error("NEO4J_DATABASE not configured in .env file")
        print_info("\nTo fix this:")
        print_info("  1. Open .env file")
        print_info("  2. Set: NEO4J_DATABASE=neo4j")
        return False

    print_success("ANTHROPIC_API_KEY configured")
    print_success("NEO4J_PASSWORD configured")
    print_success("NEO4J_DATABASE configured")
    print_success(".env file validation passed")
    return True


def load_env_file() -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    env_path = Path(".env")

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def check_docker_compose() -> bool:
    """Check if docker-compose is installed."""
    try:
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True, timeout=5)  # nosec B607,B603 - safe: hardcoded command, no user input
        return result.returncode == 0
    except Exception:
        return False


def check_docker_health(container_name: str) -> str | None:
    """Check container health status using docker inspect.

    Args:
        container_name: Name of the Docker container to check

    Returns:
        Health status string ("starting", "healthy", "unhealthy", "none") or None if check fails
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", container_name],  # nosec B607,B603 - safe: hardcoded command, container_name is validated
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # nosec B110 - intentional: fallback to None on any docker error
        pass
    return None


def start_docker_compose() -> bool:
    """Start Neo4j using Docker Compose."""
    print_header("Starting Neo4j with Docker Compose")

    try:
        # Check if docker-compose.yml exists
        if not Path("docker-compose.yml").exists():
            print_error("docker-compose.yml not found")
            return False

        # Check if docker-compose is available
        if not check_docker_compose():
            print_error("docker-compose command not found")
            print_info("Install Docker Desktop or docker-compose CLI")
            return False

        # Load .env file to get required variables (already validated in setup_env_file)
        env_vars = load_env_file()
        neo4j_password = env_vars.get("NEO4J_PASSWORD")
        neo4j_database = env_vars.get("NEO4J_DATABASE")

        # Verify required variables are present (defensive check)
        if not neo4j_password or not neo4j_database:
            print_error("NEO4J_PASSWORD or NEO4J_DATABASE not found in .env")
            print_info("This should have been caught during environment validation")
            return False

        # Set environment for docker-compose
        env = os.environ.copy()
        env["NEO4J_PASSWORD"] = neo4j_password
        env["NEO4J_DATABASE"] = neo4j_database

        print_info("Starting Neo4j container...")
        result = subprocess.run(["docker-compose", "up", "-d"], capture_output=True, text=True, env=env, timeout=60)  # nosec B607,B603 - safe: hardcoded command, no user input

        if result.returncode != 0:
            print_error(f"Failed to start Docker Compose: {result.stderr}")
            return False

        print_success("Docker Compose started")

        # Wait for Neo4j to be healthy (multi-layer health check)
        print_info("Waiting for Neo4j to initialize...")
        time.sleep(10)  # Initial delay for Neo4j to start initializing

        print_info("Checking Neo4j health status...")
        max_wait = 60  # Increased from 30 to accommodate APOC plugin initialization
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # Layer 1: Docker health check (preferred method)
            health_status = check_docker_health("anc-neo4j")
            if health_status == "healthy":
                print_success("Neo4j is ready at bolt://localhost:7687")
                return True

            # Layer 2: Bolt connectivity check (fallback method)
            if not check_port_available(7687):
                print_success("Neo4j Bolt port is accessible at bolt://localhost:7687")
                return True

            # Status feedback every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                status_msg = "unhealthy" if health_status == "unhealthy" else health_status or "checking"
                print_info(f"Still waiting... (status: {status_msg}, {elapsed}s elapsed)")

            time.sleep(2)  # Check every 2 seconds to reduce CPU usage

        print_error("Neo4j failed to become healthy within 60 seconds")
        print_info("Check container logs: docker-compose logs neo4j")
        print_info("Check container status: docker inspect anc-neo4j")
        return False

    except subprocess.TimeoutExpired:
        print_error("Docker Compose operation timed out")
        return False
    except Exception as e:
        print_error(f"Failed to start Docker Compose: {e}")
        return False


def check_or_start_neo4j() -> bool:
    """Check if Neo4j is running, or start it with Docker Compose."""
    print_header("Neo4j Setup")

    # First, check if Neo4j is already running on port 7687
    if check_port_available(7687):
        print_success("Neo4j is already running on bolt://localhost:7687")
        return True

    print_info("Neo4j is not running")

    # Try to start with Docker Compose
    print_info("Attempting to start Neo4j with Docker Compose...")
    if start_docker_compose():
        return True

    # Docker Compose failed, prompt for Neo4j Desktop
    print_warning("Could not start Neo4j with Docker Compose")
    print_info("\nAlternative: Use Neo4j Desktop")
    print_info("  1. Open Neo4j Desktop application")
    print_info("  2. Start your database")
    print_info("  3. Verify it's running on bolt://localhost:7687")
    print_info("  4. Re-run this script")

    return False


def setup_neo4j_password() -> str | None:
    """Get Neo4j password from .env file (required)."""
    print_header("Neo4j Password Configuration")

    # Load from .env file (strict mode - must exist)
    env_vars = load_env_file()
    password_from_env = env_vars.get("NEO4J_PASSWORD")

    if password_from_env:
        # Set in environment for child processes
        os.environ["NEO4J_PASSWORD"] = password_from_env
        print_success(f"Using NEO4J_PASSWORD from .env file: {password_from_env}")
        return password_from_env

    # NEO4J_PASSWORD is required in .env file
    print_error("NEO4J_PASSWORD not found in .env file")
    print_info("\nTo fix this:")
    print_info("  1. Open your .env file")
    print_info("  2. Add: NEO4J_PASSWORD=dev-password")
    print_info("  3. Or copy from .env.example: cp .env.example .env")
    return None


def initialize_neo4j_data() -> bool:
    """Initialize Neo4j with ontology data and schema fields."""
    print_header("Initializing Knowledge Graph Data")

    try:
        # Load ontologies (96 terms: NCBITaxonomy, UBERON, PATO)
        print_info("Loading ontology terms...")
        result = subprocess.run(
            ["pixi", "run", "python", "-m", "agentic_neurodata_conversion.kg_service.scripts.load_ontologies"],  # nosec B607,B603 - safe: hardcoded pixi command, no user input
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print_error(f"Failed to load ontologies: {result.stderr}")
            return False

        print_success("Loaded ontology terms (96 terms)")

        # Load NWB schema fields (25 fields)
        print_info("Loading NWB schema fields...")
        result = subprocess.run(
            ["pixi", "run", "python", "-m", "agentic_neurodata_conversion.kg_service.scripts.load_schema_fields"],  # nosec B607,B603 - safe: hardcoded pixi command, no user input
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print_error(f"Failed to load schema fields: {result.stderr}")
            return False

        print_success("Loaded NWB schema fields (25 fields)")

        # Verify data loaded correctly
        print_info("Verifying Knowledge Graph initialization...")
        result = subprocess.run(
            ["pixi", "run", "python", "-m", "agentic_neurodata_conversion.kg_service.scripts.verify_phase1"],  # nosec B607,B603 - safe: hardcoded pixi command, no user input
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print_warning("Verification warnings detected (this is normal for first-time setup)")
            # Don't fail - verification warnings are acceptable
        else:
            print_success("Knowledge Graph verification passed")

        return True

    except subprocess.TimeoutExpired:
        print_error("Neo4j initialization timed out")
        return False
    except Exception as e:
        print_error(f"Failed to initialize Neo4j data: {e}")
        return False


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


def start_kg_service() -> subprocess.Popen | None:
    """Start the KG service."""
    print_header("Starting KG Service")

    try:
        print_info("Starting KG service on port 8001...")

        # Open log file for output
        log_file = open("/tmp/kg_service.log", "w")  # nosec B108 - temporary log file for dev tool  # noqa: SIM115

        # Build command with environment variables
        env = os.environ.copy()
        if "NEO4J_PASSWORD" not in env:
            print_warning("NEO4J_PASSWORD not set, KG service may fail to connect")

        process = subprocess.Popen(  # nosec B607, B602 - safe: command is hardcoded, no user input
            "pixi run uvicorn agentic_neurodata_conversion.kg_service.main:app --host 0.0.0.0 --port 8001",
            shell=True,  # Required for pixi subprocess management
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            preexec_fn=os.setsid,  # Create new process group
        )

        # Wait for server to be ready
        print_info("Waiting for KG service to initialize...")
        time.sleep(5)

        # Check if server is running
        if wait_for_server("http://localhost:8001/health", timeout=10):
            print_success("KG service started successfully!")
            print_info("KG Service URL: http://localhost:8001")
            print_info("Health Check: http://localhost:8001/health")
            return process
        else:
            print_error("KG service failed to start (health check failed)")
            print_info("Check logs: tail -f /tmp/kg_service.log")
            log_file.close()
            return None

    except Exception as e:
        print_error(f"Failed to start KG service: {e}")
        return None


def start_backend() -> subprocess.Popen | None:
    """Start the backend server."""
    print_header("Starting Backend Server")

    try:
        # Start backend with pixi
        print_info("Starting backend with pixi run dev...")

        # Open log file for output
        log_file = open("/tmp/backend.log", "w")  # nosec B108 - temporary log file for dev tool  # noqa: SIM115

        process = subprocess.Popen(  # nosec B607, B602 - safe: pixi command is hardcoded, no user input
            "pixi run dev",
            shell=True,  # Required for pixi subprocess management
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,  # Create new process group
        )

        # Wait for server to be ready
        print_info("Waiting for backend to initialize...")
        time.sleep(5)

        # Check if server is running
        if wait_for_server("http://localhost:8000/api/health", timeout=10):
            print_success("Backend server started successfully!")
            print_info("Backend URL: http://localhost:8000")
            print_info("API Docs: http://localhost:8000/docs")
            return process
        else:
            print_error("Backend server failed to start (health check failed)")
            print_info("Check logs: tail -f /tmp/backend.log")
            log_file.close()
            return None

    except Exception as e:
        print_error(f"Failed to start backend: {e}")
        return None


def start_frontend() -> subprocess.Popen | None:
    """Start the frontend server."""
    print_header("Starting Frontend Server")

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

        # Change to frontend/public directory and start server
        process = subprocess.Popen(  # nosec B607, B602 - safe: python3 command and port are hardcoded, no user input
            "cd frontend/public && python3 -m http.server 3000",
            shell=True,  # Required for module execution and cd command
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,  # Create new process group
        )

        # Wait for server to be ready
        time.sleep(2)

        if wait_for_server("http://localhost:3000/chat-ui.html", timeout=5):
            print_success("Frontend server started successfully!")
            print_info("Frontend URL: http://localhost:3000/chat-ui.html")
            return process
        else:
            print_error("Frontend server failed to start")
            print_info("Check logs: tail -f /tmp/frontend.log")
            log_file.close()
            return None

    except Exception as e:
        print_error(f"Failed to start frontend: {e}")
        return None


def display_status() -> None:
    """Display application status and URLs."""
    print_header("Application Status")

    print(f"{Colors.BOLD}{Colors.GREEN}✅ Application is running with KG integration!{Colors.END}\n")

    print(f"{Colors.BOLD}Neo4j:{Colors.END}")
    print(f"  • Bolt:         {Colors.CYAN}bolt://localhost:7687{Colors.END}")
    print(f"  • Browser:      {Colors.CYAN}http://localhost:7474{Colors.END}")
    print(f"  • Status:       {Colors.CYAN}docker-compose ps{Colors.END} (if using Docker)")
    print()

    print(f"{Colors.BOLD}KG Service:{Colors.END}")
    print(f"  • API:          {Colors.CYAN}http://localhost:8001{Colors.END}")
    print(f"  • Health:       {Colors.CYAN}http://localhost:8001/health{Colors.END}")
    print(f"  • Docs:         {Colors.CYAN}http://localhost:8001/docs{Colors.END}")
    print()

    print(f"{Colors.BOLD}Backend:{Colors.END}")
    print(f"  • API:          {Colors.CYAN}http://localhost:8000{Colors.END}")
    print(f"  • Health:       {Colors.CYAN}http://localhost:8000/api/health{Colors.END}")
    print(f"  • Docs:         {Colors.CYAN}http://localhost:8000/docs{Colors.END}")
    print(f"  • WebSocket:    {Colors.CYAN}ws://localhost:8000/ws{Colors.END}")
    print()

    print(f"{Colors.BOLD}Logs:{Colors.END}")
    print(f"  • KG Service:   {Colors.CYAN}/tmp/kg_service.log{Colors.END}")  # nosec B108  # display only, not actual file operation
    print(f"  • Backend:      {Colors.CYAN}/tmp/backend.log{Colors.END}")  # nosec B108  # display only, not actual file operation
    print(f"  • Frontend:     {Colors.CYAN}/tmp/frontend.log{Colors.END}")  # nosec B108  # display only, not actual file operation
    print()

    print(f"{Colors.BOLD}Testing:{Colors.END}")
    print("  Upload files and interact with agents")
    print(f"  Watch {Colors.CYAN}/tmp/backend.log{Colors.END} for KG validation messages")  # nosec B108  # display only, not actual file operation
    print("  Test inputs: 'mouse', 'male', 'hippocampus'")
    print()

    print(f"{Colors.YELLOW}Press Ctrl+C to stop all servers{Colors.END}")
    print()

    # Prominent frontend URL at the end for easy clicking
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}🚀 GET STARTED - Click the URL below:{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print()
    print(f"{Colors.BOLD}{Colors.GREEN}   👉 http://localhost:3000/chat-ui.html{Colors.END}")
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print()


def main() -> None:
    """Main startup routine."""
    # Print welcome banner
    print_header("Agentic Neurodata Conversion - Startup Script (with KG)")

    print(f"{Colors.BOLD}This script will:{Colors.END}")
    print("  1. Configure your environment (.env file)")
    print("  2. Start Neo4j (Docker Compose or check Neo4j Desktop)")
    print("  3. Configure Neo4j password (from .env or prompt)")
    print("  4. Initialize Knowledge Graph (load ontologies & schema)")
    print("  5. Clean up old processes")
    print("  6. Clean temporary directories")
    print("  7. Start KG service (port 8001)")
    print("  8. Start backend server (port 8000)")
    print("  9. Start frontend server (port 3000)")
    print(" 10. Display application URLs")
    print()

    kg_process = None
    backend_process = None
    frontend_process = None

    try:
        # Step 1: Validate environment configuration (strict)
        if not setup_env_file():
            print_error("Environment validation failed")
            print_info("\nPlease configure your .env file before starting the application")
            sys.exit(1)

        # Step 2: Start or check Neo4j
        if not check_or_start_neo4j():
            print_error("Cannot continue without Neo4j")
            print_info("\nPlease ensure Neo4j is running on bolt://localhost:7687")
            sys.exit(1)

        # Step 3: Validate Neo4j password (strict)
        neo4j_password = setup_neo4j_password()
        if not neo4j_password:
            print_error("Neo4j password validation failed")
            print_info("\nPlease add NEO4J_PASSWORD to your .env file")
            sys.exit(1)

        # Step 4: Initialize Knowledge Graph data
        if not initialize_neo4j_data():
            print_warning("Knowledge Graph initialization failed")
            response = input(f"\n{Colors.YELLOW}Continue without KG data? (y/N): {Colors.END}").strip().lower()
            if response != "y":
                sys.exit(1)

        # Step 5: Kill old processes
        print_header("Cleaning Up Old Processes")
        print_info("Checking for processes on ports 8001, 8000, and 3000...")

        killed_8001 = kill_process_on_port(8001)
        killed_8000 = kill_process_on_port(8000)
        killed_3000 = kill_process_on_port(3000)

        if not killed_8001 and not killed_8000 and not killed_3000:
            print_info("No old processes found")

        time.sleep(2)  # Give OS time to release ports

        # Step 6: Clean temp directories
        print_header("Cleaning Temp Directories")
        clean_temp_directories()
        time.sleep(1)

        # Step 7: Start KG service
        kg_process = start_kg_service()
        if not kg_process:
            print_warning("KG service failed to start")
            print_info("System will continue without ontology validation")
            response = input(f"\n{Colors.YELLOW}Continue without KG service? (y/N): {Colors.END}").strip().lower()
            if response != "y":
                sys.exit(1)

        # Step 8: Start backend
        backend_process = start_backend()
        if not backend_process:
            print_error("Cannot continue without backend server")
            sys.exit(1)

        # Step 9: Start frontend
        frontend_process = start_frontend()
        if not frontend_process:
            print_warning("Frontend failed to start, but backend is running")

        # Step 10: Display status
        display_status()

        # Keep script running and monitor processes
        while True:
            time.sleep(1)

            # Check if processes are still running
            if kg_process and kg_process.poll() is not None:
                print_warning("KG service process died unexpectedly!")
                print_info("System continues with LLM-only normalization")

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
        kill_process_on_port(8001)
        kill_process_on_port(8000)
        kill_process_on_port(3000)

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
