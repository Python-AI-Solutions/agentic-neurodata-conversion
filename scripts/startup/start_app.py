#!/usr/bin/env python3
"""Agentic Neurodata Conversion - Application Startup Script.

This script handles:
- Environment configuration (API key setup)
- Process management (killing old processes, starting new ones)
- Health checks and status reporting
- User-friendly console output

Usage:
    python3 start_app.py
    # Or make executable:
    chmod +x start_app.py
    ./start_app.py
"""

import os
import signal
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
    """Interactive setup for .env file with API key."""
    print_header("Environment Configuration")

    env_path = Path(".env")
    env_example_path = Path(".env.example")

    # Check if .env already exists with valid key
    if check_env_file():
        print_info(".env file already configured with API key")
        response = input(f"\n{Colors.YELLOW}Do you want to update the API key? (y/N): {Colors.END}").strip().lower()
        if response != "y":
            print_success("Using existing .env configuration")
            return True

    # Get API key from user
    print_info("You need an Anthropic API key to use this application")
    print_info("Get your key from: https://console.anthropic.com")
    print()

    api_key = input(f"{Colors.BOLD}Enter your Anthropic API key (or press Enter to skip): {Colors.END}").strip()

    if not api_key:
        print_warning("No API key provided. Application will start without LLM features.")
        return False

    if not api_key.startswith("sk-ant-"):
        print_error("Invalid API key format. Key should start with 'sk-ant-'")
        return False

    # Create .env file from example or create new
    if env_example_path.exists():
        with open(env_example_path) as f:
            content = f.read()

        # Replace placeholder with actual key
        content = content.replace("ANTHROPIC_API_KEY=sk-ant-REPLACE-WITH-YOUR-KEY", f"ANTHROPIC_API_KEY={api_key}")
    else:
        # Create minimal .env
        content = f"ANTHROPIC_API_KEY={api_key}\n"

    # Write .env file
    with open(env_path, "w") as f:
        f.write(content)

    print_success(".env file created successfully!")
    return True


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


def start_backend() -> subprocess.Popen | None:
    """Start the backend server."""
    print_header("Starting Backend Server")

    try:
        # Start backend with pixi
        print_info("Starting backend with pixi run dev...")

        process = subprocess.Popen(  # nosec B607, B602 - safe: pixi command is hardcoded, no user input
            "pixi run dev",
            shell=True,  # Required for pixi subprocess management
            stdout=subprocess.PIPE,
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

        # Change to frontend/public directory and start server
        process = subprocess.Popen(  # nosec B607, B602 - safe: python3 command and port are hardcoded, no user input
            "cd frontend/public && python3 -m http.server 3000",
            shell=True,  # Required for module execution and cd command
            stdout=subprocess.PIPE,
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
            return None

    except Exception as e:
        print_error(f"Failed to start frontend: {e}")
        return None


def display_status() -> None:
    """Display application status and URLs."""
    print_header("Application Status")

    print(f"{Colors.BOLD}{Colors.GREEN}✅ Application is running!{Colors.END}\n")

    print(f"{Colors.BOLD}Backend:{Colors.END}")
    print(f"  • API:          {Colors.CYAN}http://localhost:8000{Colors.END}")
    print(f"  • Health:       {Colors.CYAN}http://localhost:8000/api/health{Colors.END}")
    print(f"  • Docs:         {Colors.CYAN}http://localhost:8000/docs{Colors.END}")
    print(f"  • WebSocket:    {Colors.CYAN}ws://localhost:8000/ws{Colors.END}")
    print()

    print(f"{Colors.BOLD}Frontend:{Colors.END}")
    print(f"  • Chat UI:      {Colors.CYAN}http://localhost:3000/chat-ui.html{Colors.END}")
    print()

    print(f"{Colors.BOLD}Logs:{Colors.END}")
    print(f"  • Backend:      {Colors.CYAN}/tmp/backend.log{Colors.END}")  # nosec B108 - display only, not actual file operation
    print(f"  • Frontend:     {Colors.CYAN}/tmp/frontend.log{Colors.END}")  # nosec B108 - display only, not actual file operation
    print()

    print(f"{Colors.YELLOW}Press Ctrl+C to stop all servers{Colors.END}")
    print()


def main() -> None:
    """Main startup routine."""
    # Print welcome banner
    print_header("Agentic Neurodata Conversion - Startup Script")

    print(f"{Colors.BOLD}This script will:{Colors.END}")
    print("  1. Configure your environment (.env file)")
    print("  2. Clean up old processes")
    print("  3. Start backend server (FastAPI + Uvicorn)")
    print("  4. Start frontend server (HTTP server)")
    print("  5. Display application URLs")
    print()

    backend_process = None
    frontend_process = None

    try:
        # Step 1: Setup environment
        setup_env_file()

        # Step 2: Kill old processes
        print_header("Cleaning Up Old Processes")
        print_info("Checking for processes on ports 8000 and 3000...")

        killed_8000 = kill_process_on_port(8000)
        killed_3000 = kill_process_on_port(3000)

        if not killed_8000 and not killed_3000:
            print_info("No old processes found")

        time.sleep(2)  # Give OS time to release ports

        # Step 3: Start backend
        backend_process = start_backend()
        if not backend_process:
            print_error("Cannot continue without backend server")
            sys.exit(1)

        # Step 4: Start frontend
        frontend_process = start_frontend()
        if not frontend_process:
            print_warning("Frontend failed to start, but backend is running")

        # Step 5: Display status
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
