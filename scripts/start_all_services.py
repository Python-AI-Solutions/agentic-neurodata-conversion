#!/usr/bin/env python
"""
Start All Services - Orchestrator for Multi-Agent NWB Conversion Pipeline

This script starts all required services in the correct order:
1. MCP Server (orchestrator)
2. Conversation Agent
3. Conversion Agent
4. Evaluation Agent

Usage:
    python scripts/start_all_services.py

Requirements:
    - Redis running on localhost:6379
    - API key in .env file (ANTHROPIC_API_KEY or OPENAI_API_KEY)
    - Ports 8000, 3001, 3002, 3003 available

The script will:
    - Start all services as background processes
    - Wait for them to be ready
    - Print status information
    - Handle graceful shutdown on Ctrl+C
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Colors:
    """ANSI color codes."""
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


class ServiceOrchestrator:
    """Orchestrates startup and shutdown of all services."""

    def __init__(self):
        """Initialize orchestrator."""
        self.processes = {}
        self.mcp_server_url = "http://localhost:8000"
        self.agents = {
            "conversation_agent": {"port": 3001, "url": "http://localhost:3001"},
            "conversion_agent": {"port": 3002, "url": "http://localhost:3002"},
            "evaluation_agent": {"port": 3003, "url": "http://localhost:3003"},
        }

    def log(self, message: str, level: str = "INFO"):
        """Log with color coding."""
        if level == "HEADER":
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{message.center(80)}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
        elif level == "STEP":
            print(f"{Colors.BOLD}{Colors.GREEN}[STEP] {message}{Colors.END}")
        elif level == "INFO":
            print(f"  - {message}")
        elif level == "SUCCESS":
            print(f"{Colors.GREEN}  [OK] {message}{Colors.END}")
        elif level == "ERROR":
            print(f"{Colors.RED}  [ERROR] {message}{Colors.END}")
        elif level == "WARN":
            print(f"{Colors.YELLOW}  ! {message}{Colors.END}")

    def check_redis(self) -> bool:
        """Check if Redis is running."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
            r.ping()
            return True
        except Exception:
            return False

    def check_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return True
            except OSError:
                return False

    async def wait_for_service(self, url: str, name: str, max_wait: int = 30) -> bool:
        """Wait for a service to be ready."""
        self.log(f"Waiting for {name} to be ready...")

        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < max_wait:
                try:
                    response = await client.get(f"{url}/health", timeout=2.0)
                    if response.status_code == 200:
                        self.log(f"{name} is ready", "SUCCESS")
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)

        self.log(f"Timeout waiting for {name}", "ERROR")
        return False

    def start_mcp_server(self):
        """Start the MCP server."""
        self.log("Starting MCP Server", "STEP")

        # Start uvicorn with the FastAPI app
        cmd = [
            sys.executable, "-m", "uvicorn",
            "agentic_neurodata_conversion.mcp_server.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--log-level", "info"
        ]

        # Pass current environment (including .env variables)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()  # Pass environment variables
        )

        self.processes["mcp_server"] = process
        self.log(f"MCP Server started (PID: {process.pid})", "SUCCESS")

    def start_agent(self, agent_name: str):
        """Start an agent."""
        self.log(f"Starting {agent_name}", "STEP")

        # Extract agent type from name (e.g., "conversation_agent" -> "conversation")
        agent_type = agent_name.replace("_agent", "")

        cmd = [
            sys.executable, "-m",
            "agentic_neurodata_conversion.agents",
            agent_type
        ]

        # Pass current environment (including .env variables)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()  # Pass environment variables
        )

        self.processes[agent_name] = process
        self.log(f"{agent_name} started (PID: {process.pid})", "SUCCESS")

    async def start_all(self):
        """Start all services."""
        self.log("Multi-Agent NWB Conversion Pipeline - Service Orchestrator", "HEADER")

        # Check prerequisites
        self.log("Checking Prerequisites", "STEP")

        if not self.check_redis():
            self.log("Redis is not running", "ERROR")
            self.log("Please start Redis: wsl bash -c 'sudo service redis-server start'", "WARN")
            return False
        self.log("Redis is running", "SUCCESS")

        # Check API keys
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if anthropic_key and anthropic_key.startswith("sk-ant-"):
            self.log(f"Found ANTHROPIC_API_KEY in .env", "SUCCESS")
        elif openai_key and openai_key.startswith("sk-"):
            self.log(f"Found OPENAI_API_KEY in .env", "SUCCESS")
        else:
            self.log("No valid API key found in .env file", "ERROR")
            return False

        # Check ports
        ports_to_check = [8000, 3001, 3002, 3003]
        for port in ports_to_check:
            if not self.check_port_available(port):
                self.log(f"Port {port} is already in use", "ERROR")
                return False
        self.log("All ports available", "SUCCESS")

        # Start MCP server
        self.start_mcp_server()
        if not await self.wait_for_service(self.mcp_server_url, "MCP Server"):
            return False

        # Start agents
        for agent_name in self.agents.keys():
            self.start_agent(agent_name)
            await asyncio.sleep(2)  # Give agent time to start

            # Wait for agent to be ready
            agent_url = self.agents[agent_name]["url"]
            if not await self.wait_for_service(agent_url, agent_name):
                return False

        self.log("All Services Started Successfully", "HEADER")
        self.log(f"MCP Server: {self.mcp_server_url}")
        for agent_name, config in self.agents.items():
            self.log(f"{agent_name}: {config['url']}")

        print(f"\n{Colors.GREEN}System is ready!{Colors.END}")
        print(f"You can now run: python scripts/run_full_demo.py\n")
        print(f"Press Ctrl+C to stop all services\n")

        return True

    def stop_all(self):
        """Stop all services."""
        self.log("Stopping All Services", "STEP")

        for name, process in self.processes.items():
            if process.poll() is None:  # Process is still running
                self.log(f"Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    self.log(f"{name} stopped", "SUCCESS")
                except subprocess.TimeoutExpired:
                    self.log(f"Force killing {name}...", "WARN")
                    process.kill()
                    process.wait()

        self.processes.clear()
        self.log("All services stopped", "SUCCESS")


async def main():
    """Main entry point."""
    orchestrator = ServiceOrchestrator()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\n")
        orchestrator.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start all services
        success = await orchestrator.start_all()

        if not success:
            orchestrator.stop_all()
            sys.exit(1)

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

            # Check if any process died
            for name, process in list(orchestrator.processes.items()):
                if process.poll() is not None:
                    orchestrator.log(f"{name} died unexpectedly!", "ERROR")
                    orchestrator.stop_all()
                    sys.exit(1)

    except KeyboardInterrupt:
        print("\n")
        orchestrator.stop_all()
    except Exception as e:
        orchestrator.log(f"Error: {e}", "ERROR")
        orchestrator.stop_all()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
