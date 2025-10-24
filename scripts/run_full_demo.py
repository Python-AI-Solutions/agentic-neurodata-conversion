#!/usr/bin/env python
"""
Complete Multi-Agent NWB Conversion Pipeline - Full Demo with Real Execution

This script:
1. Checks for Redis (provides setup instructions if missing)
2. Prompts for LLM API keys (Anthropic or OpenAI)
3. Starts the MCP server
4. Runs the complete pipeline with test data
5. Generates a real NWB file
6. Shows validation results

Usage:
    python scripts/run_full_demo.py

Requirements:
    - Redis server running (instructions provided if not found)
    - Anthropic API key OR OpenAI API key

Output:
    - Real NWB file in ./demo_output/nwb_files/
    - Validation report in ./demo_output/reports/
    - Session context in ./demo_output/sessions/
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Colors:
    """ANSI color codes."""
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


class FullPipelineDemo:
    """Complete pipeline demonstration with real execution."""

    def __init__(self, api_key: str, provider: str = "anthropic"):
        """Initialize demo with API credentials."""
        self.api_key = api_key
        self.provider = provider
        self.server_process = None
        self.server_url = "http://localhost:8000"
        self.session_id = None

        # Configure output directories
        self.output_base = Path("./demo_output")
        self.sessions_dir = self.output_base / "sessions"
        self.nwb_dir = self.output_base / "nwb_files"
        self.reports_dir = self.output_base / "reports"

    def log(self, message: str, level: str = "INFO"):
        """Log with color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if level == "HEADER":
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{message.center(80)}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
        elif level == "STEP":
            print(f"\n{Colors.BOLD}{Colors.GREEN}[{timestamp}] >> {message}{Colors.END}")
        elif level == "SUBSTEP":
            print(f"{Colors.YELLOW}  -> {message}{Colors.END}")
        elif level == "DATA":
            print(f"     {message}")
        elif level == "ERROR":
            print(f"{Colors.RED}[ERROR] {message}{Colors.END}")
        elif level == "SUCCESS":
            print(f"{Colors.GREEN}  [OK] {message}{Colors.END}")
        else:
            print(f"[{timestamp}] {message}")

    def check_redis(self) -> bool:
        """Check if Redis is running."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
            r.ping()
            return True
        except Exception:
            return False

    def setup_redis_instructions(self):
        """Show Redis setup instructions."""
        self.log("Redis Setup Instructions", "HEADER")

        print("Redis is required to run this demo. Please install and start Redis:\n")

        print(f"{Colors.BOLD}Windows:{Colors.END}")
        print("  1. Download Redis for Windows:")
        print("     https://github.com/microsoftarchive/redis/releases")
        print("  2. Extract and run: redis-server.exe")
        print("  OR use WSL:")
        print("     wsl sudo service redis-server start\n")

        print(f"{Colors.BOLD}macOS:{Colors.END}")
        print("  brew install redis")
        print("  brew services start redis\n")

        print(f"{Colors.BOLD}Linux:{Colors.END}")
        print("  sudo apt-get install redis-server")
        print("  sudo systemctl start redis\n")

        print(f"{Colors.BOLD}Docker (All Platforms):{Colors.END}")
        print("  docker run -d -p 6379:6379 redis:alpine\n")

        print("After starting Redis, run this script again.\n")

    def setup_directories(self):
        """Create output directories."""
        self.log("Setting Up Output Directories", "STEP")

        for directory in [self.output_base, self.sessions_dir, self.nwb_dir, self.reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            self.log(f"Created: {directory}", "SUBSTEP")

    async def start_mcp_server(self):
        """Start the MCP server in the background."""
        self.log("Starting MCP Server", "STEP")

        # Set environment variables
        os.environ["REDIS_URL"] = "redis://localhost:6379"
        os.environ["FILESYSTEM_BASE_PATH"] = str(self.sessions_dir)

        if self.provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = self.api_key
            os.environ.pop("OPENAI_API_KEY", None)
            self.log("Using Anthropic Claude API", "SUBSTEP")
        else:
            os.environ["OPENAI_API_KEY"] = self.api_key
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.log("Using OpenAI GPT-4 API", "SUBSTEP")

        # Import and start server
        from agentic_neurodata_conversion.mcp_server.main import app
        import uvicorn

        # Configure uvicorn
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="error",  # Reduce noise
        )

        server = uvicorn.Server(config)

        # Start server in background task
        self.server_task = asyncio.create_task(server.serve())

        # Wait for server to be ready
        self.log("Waiting for server to start...", "SUBSTEP")
        await asyncio.sleep(3)

        # Check if server is running
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    self.log("MCP Server started successfully", "SUCCESS")
                    self.log(f"Server URL: {self.server_url}", "DATA")
                    return True
        except Exception as e:
            self.log(f"Server failed to start: {e}", "ERROR")
            return False

    async def initialize_session(self, dataset_path: str):
        """Initialize a new session."""
        self.log("PHASE 1: Initialize Session", "HEADER")

        self.log("Sending HTTP Request", "STEP")
        self.log(f"POST {self.server_url}/api/v1/sessions/initialize", "DATA")

        payload = {"dataset_path": dataset_path}
        self.log(f"Request body: {json.dumps(payload, indent=2)}", "DATA")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/api/v1/sessions/initialize",
                json=payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                self.log("Session initialized successfully", "SUCCESS")
                self.log(f"Session ID: {self.session_id}", "DATA")
                self.log(f"Workflow Stage: {data['workflow_stage']}", "DATA")
                return data
            else:
                self.log(f"Failed to initialize session: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return None

    async def poll_session_progress(self):
        """Poll session progress until completed."""
        self.log("PHASE 2-4: Processing Pipeline", "HEADER")

        self.log("Monitoring Pipeline Progress", "STEP")

        max_wait = 120  # 2 minutes max
        start_time = time.time()

        while time.time() - start_time < max_wait:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{self.server_url}/api/v1/sessions/{self.session_id}/progress",
                        timeout=10.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        stage = data.get("workflow_stage", "unknown")

                        # Show progress
                        stage_descriptions = {
                            "initialized": "Initializing session...",
                            "collecting_metadata": "ConversationAgent: Extracting metadata from dataset...",
                            "converting": "ConversionAgent: Converting to NWB format...",
                            "evaluating": "EvaluationAgent: Validating NWB file...",
                            "completed": "Pipeline completed successfully!",
                        }

                        description = stage_descriptions.get(stage, f"Stage: {stage}")
                        self.log(description, "SUBSTEP")

                        if stage == "completed":
                            self.log("All agents completed their work", "SUCCESS")
                            return True

                        # Check for errors
                        if data.get("errors"):
                            self.log(f"Errors detected: {data['errors']}", "ERROR")
                            return False

                except Exception as e:
                    self.log(f"Error polling progress: {e}", "ERROR")

            await asyncio.sleep(2)  # Poll every 2 seconds

        self.log("Timeout waiting for completion", "ERROR")
        return False

    async def get_results(self):
        """Get final results."""
        self.log("PHASE 5: Retrieve Results", "HEADER")

        self.log("Fetching Final Results", "STEP")
        self.log(f"GET {self.server_url}/api/v1/sessions/{self.session_id}/result", "DATA")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.server_url}/api/v1/sessions/{self.session_id}/result",
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                self.log("Results retrieved successfully", "SUCCESS")
                return data
            else:
                self.log(f"Failed to get results: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return None

    def display_results(self, results: dict):
        """Display final results."""
        self.log("FINAL RESULTS", "HEADER")

        self.log("Pipeline Summary", "STEP")
        self.log(f"Session ID: {results.get('session_id', 'N/A')}", "DATA")
        self.log(f"Final Stage: {results.get('workflow_stage', 'N/A')}", "DATA")
        self.log(f"Overall Status: {results.get('overall_status', 'N/A')}", "DATA")

        # NWB File
        self.log("Generated NWB File", "STEP")
        nwb_path = results.get("nwb_file_path")
        if nwb_path and Path(nwb_path).exists():
            size_mb = Path(nwb_path).stat().st_size / (1024 * 1024)
            self.log(f"Path: {nwb_path}", "DATA")
            self.log(f"Size: {size_mb:.2f} MB", "DATA")
            self.log("NWB file successfully created!", "SUCCESS")
        else:
            self.log("NWB file not found", "ERROR")

        # Validation Report
        self.log("Validation Report", "STEP")
        report_path = results.get("validation_report_path")
        if report_path and Path(report_path).exists():
            self.log(f"Path: {report_path}", "DATA")

            # Load and display report summary
            with open(report_path) as f:
                report = json.load(f)

            self.log(f"Metadata Completeness: {report.get('metadata_completeness_score', 0)}/100", "DATA")
            self.log(f"Best Practices Score: {report.get('best_practices_score', 0)}/100", "DATA")

            issue_count = report.get("issue_count", {})
            self.log(f"Issues Found:", "DATA")
            self.log(f"  - Critical: {issue_count.get('CRITICAL', 0)}", "DATA")
            self.log(f"  - Violations: {issue_count.get('BEST_PRACTICE_VIOLATION', 0)}", "DATA")
            self.log(f"  - Suggestions: {issue_count.get('BEST_PRACTICE_SUGGESTION', 0)}", "DATA")

        # LLM Summary
        self.log("Validation Summary (LLM-Generated)", "STEP")
        summary = results.get("llm_validation_summary", "No summary available")
        for line in summary.split('\n'):
            self.log(line, "DATA")

        # Validation Issues
        issues = results.get("validation_issues", [])
        if issues:
            self.log(f"Validation Issues ({len(issues)} total)", "STEP")
            for i, issue in enumerate(issues[:5], 1):  # Show first 5
                self.log(f"{i}. [{issue['severity']}] {issue['message']}", "DATA")
                self.log(f"   Location: {issue.get('location', 'N/A')}", "DATA")

            if len(issues) > 5:
                self.log(f"... and {len(issues) - 5} more issues", "DATA")

    async def cleanup(self):
        """Cleanup resources."""
        self.log("Shutting down MCP Server", "STEP")
        if hasattr(self, 'server_task'):
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        self.log("Cleanup complete", "SUCCESS")

    async def run(self, dataset_path: str):
        """Run complete demonstration."""
        try:
            # Setup
            self.setup_directories()

            # Start server
            if not await self.start_mcp_server():
                return False

            # Run pipeline
            if not await self.initialize_session(dataset_path):
                return False

            if not await self.poll_session_progress():
                return False

            # Get results
            results = await self.get_results()
            if results:
                self.display_results(results)
                return True

            return False

        except Exception as e:
            self.log(f"Error during execution: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()


def get_api_credentials():
    """Get API credentials from .env file or prompt user."""
    print("\n" + "="*80)
    print("  LLM API Configuration".center(80))
    print("="*80 + "\n")

    # Check environment variables (from .env file or system)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    # Filter out placeholder values from .env.example
    if anthropic_key and (anthropic_key.startswith("sk-ant-your-") or anthropic_key == "sk-ant-your-api-key-here"):
        anthropic_key = None
    if openai_key and (openai_key.startswith("sk-your-") or openai_key == "sk-your-openai-api-key-here"):
        openai_key = None

    # If valid key found in .env, use it
    if anthropic_key and anthropic_key.startswith("sk-ant-"):
        print(f"{Colors.GREEN}Found valid ANTHROPIC_API_KEY in .env file{Colors.END}")
        print(f"Key: {anthropic_key[:15]}...{anthropic_key[-4:]}")
        try:
            use_env = input("\nUse this key? [Y/n]: ").strip().lower()
        except EOFError:
            # Non-interactive mode, auto-accept
            use_env = 'y'
        if use_env in ('', 'y', 'yes'):
            return anthropic_key, "anthropic"

    if openai_key and openai_key.startswith("sk-"):
        print(f"{Colors.GREEN}Found valid OPENAI_API_KEY in .env file{Colors.END}")
        print(f"Key: {openai_key[:10]}...{openai_key[-4:]}")
        try:
            use_env = input("\nUse this key? [Y/n]: ").strip().lower()
        except EOFError:
            # Non-interactive mode, auto-accept
            use_env = 'y'
        if use_env in ('', 'y', 'yes'):
            return openai_key, "openai"

    # No valid key in .env, prompt user
    print(f"{Colors.YELLOW}No valid API key found in .env file{Colors.END}\n")
    print("This demo requires an LLM API key for metadata extraction and validation.\n")
    print("To avoid this prompt in the future:")
    print("  1. Copy .env.example to .env")
    print("  2. Add your API key to the .env file\n")
    print("You can use either:")
    print("  1. Anthropic Claude (recommended)")
    print("  2. OpenAI GPT-4\n")

    # Prompt for key
    print("Enter your API key:")
    print("  - For Anthropic: Get key from https://console.anthropic.com/")
    print("  - For OpenAI: Get key from https://platform.openai.com/api-keys\n")

    api_key = input("API Key: ").strip()
    if not api_key:
        print(f"{Colors.RED}No API key provided. Exiting.{Colors.END}")
        sys.exit(1)

    # Detect provider
    if api_key.startswith("sk-ant-"):
        provider = "anthropic"
        print(f"{Colors.GREEN}Detected Anthropic API key{Colors.END}")
    elif api_key.startswith("sk-"):
        provider = "openai"
        print(f"{Colors.GREEN}Detected OpenAI API key{Colors.END}")
    else:
        print("\nWhich provider is this key for?")
        print("  1. Anthropic Claude")
        print("  2. OpenAI GPT-4")
        choice = input("Choice (1 or 2): ").strip()
        provider = "anthropic" if choice == "1" else "openai"

    return api_key, provider


async def main():
    """Main entry point."""
    print("\n")
    print("="*80)
    print("  Multi-Agent NWB Conversion Pipeline - Full Demo".center(80))
    print("  Real Execution with Redis + LLM".center(80))
    print("="*80)
    print("\n")

    # Initialize demo
    demo = FullPipelineDemo("", "")

    # Check Redis
    demo.log("Checking Prerequisites", "HEADER")
    demo.log("Checking Redis connection...", "STEP")

    if not demo.check_redis():
        demo.log("Redis is not running", "ERROR")
        demo.setup_redis_instructions()
        sys.exit(1)

    demo.log("Redis is running", "SUCCESS")

    # Get API credentials
    api_key, provider = get_api_credentials()

    # Create demo with credentials
    demo = FullPipelineDemo(api_key, provider)

    # Use test dataset
    dataset_path = "./tests/data/synthetic_openephys"

    if not Path(dataset_path).exists():
        demo.log(f"Dataset not found: {dataset_path}", "ERROR")
        demo.log("Please run from the project root directory", "ERROR")
        sys.exit(1)

    print(f"\nUsing test dataset: {dataset_path}")
    print(f"Output directory: ./demo_output/\n")

    try:
        input("Press Enter to start the demo...")
    except EOFError:
        # Non-interactive mode, auto-start
        print("Starting demo automatically (non-interactive mode)...")

    # Run demo
    success = await demo.run(dataset_path)

    # Final summary
    print("\n" + "="*80)
    if success:
        print(f"{Colors.GREEN}  DEMO COMPLETED SUCCESSFULLY!{Colors.END}".center(80))
    else:
        print(f"{Colors.RED}  DEMO FAILED{Colors.END}".center(80))
    print("="*80 + "\n")

    if success:
        print("Generated files:")
        print(f"  - NWB File: ./demo_output/nwb_files/*.nwb")
        print(f"  - Validation Report: ./demo_output/reports/*.json")
        print(f"  - Session Context: ./demo_output/sessions/*.json")
        print("\nFor more information, see: docs/INFORMATION_FLOW.md\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user{Colors.END}\n")
        sys.exit(0)
