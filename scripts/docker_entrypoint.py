#!/usr/bin/env python3
"""
Docker entrypoint script for Agentic Neurodata Conversion.

This script handles container initialization, environment setup,
and service startup with proper error handling.
"""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Optional


class DockerEntrypoint:
    """Manages Docker container initialization and service startup."""

    def __init__(self):
        self.project_root = Path("/app")
        self.shutdown_requested = False

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def check_environment(self) -> bool:
        """Check that required environment variables are set."""
        required_vars = [
            "AGENTIC_CONVERTER_ENV",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.log(
                f"Missing required environment variables: {', '.join(missing_vars)}",
                "ERROR",
            )
            return False

        return True

    def setup_directories(self) -> bool:
        """Create and set up required directories."""
        directories = [
            self.project_root / "data",
            self.project_root / "temp",
            self.project_root / "logs",
        ]

        try:
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                self.log(f"Ensured directory exists: {directory}")
            return True
        except Exception as e:
            self.log(f"Failed to create directories: {e}", "ERROR")
            return False

    def validate_configuration(self) -> bool:
        """Validate configuration file exists and is readable."""
        config_file = os.getenv("AGENTIC_CONVERTER_CONFIG_FILE")

        if not config_file:
            self.log("No configuration file specified", "WARNING")
            return True  # May use defaults

        config_path = Path(config_file)
        if not config_path.exists():
            self.log(f"Configuration file not found: {config_file}", "ERROR")
            return False

        try:
            import json

            with open(config_path) as f:
                json.load(f)
            self.log(f"Configuration file validated: {config_file}")
            return True
        except Exception as e:
            self.log(f"Invalid configuration file: {e}", "ERROR")
            return False

    def wait_for_dependencies(self) -> bool:
        """Wait for external dependencies to be ready."""
        # Check if we need to wait for database
        db_url = os.getenv("AGENTIC_CONVERTER_DATABASE__URL")
        if db_url and "postgres" in db_url:
            self.log("Waiting for PostgreSQL to be ready...")
            return self._wait_for_postgres()

        # Check if we need to wait for Redis
        redis_url = os.getenv("AGENTIC_CONVERTER_REDIS_URL")
        if redis_url:
            self.log("Waiting for Redis to be ready...")
            return self._wait_for_redis()

        return True

    def _wait_for_postgres(self, max_attempts: int = 30) -> bool:
        """Wait for PostgreSQL to be ready."""
        import time

        for attempt in range(max_attempts):
            if self.shutdown_requested:
                return False

            try:
                # Try to connect using psycopg2 if available
                import psycopg2

                db_url = os.getenv("AGENTIC_CONVERTER_DATABASE__URL")
                conn = psycopg2.connect(db_url)
                conn.close()
                self.log("PostgreSQL is ready")
                return True
            except ImportError:
                self.log("psycopg2 not available, skipping PostgreSQL check", "WARNING")
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.log(
                        f"PostgreSQL not ready (attempt {attempt + 1}/{max_attempts}): {e}"
                    )
                    time.sleep(2)
                else:
                    self.log(f"PostgreSQL failed to become ready: {e}", "ERROR")
                    return False

        return False

    def _wait_for_redis(self, max_attempts: int = 30) -> bool:
        """Wait for Redis to be ready."""
        import time

        for attempt in range(max_attempts):
            if self.shutdown_requested:
                return False

            try:
                import redis

                redis_url = os.getenv("AGENTIC_CONVERTER_REDIS_URL")
                r = redis.from_url(redis_url)
                r.ping()
                self.log("Redis is ready")
                return True
            except ImportError:
                self.log("redis not available, skipping Redis check", "WARNING")
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.log(
                        f"Redis not ready (attempt {attempt + 1}/{max_attempts}): {e}"
                    )
                    time.sleep(2)
                else:
                    self.log(f"Redis failed to become ready: {e}", "ERROR")
                    return False

        return False

    def run_migrations(self) -> bool:
        """Run database migrations if needed."""
        # Placeholder for future database migrations
        self.log("Checking for database migrations...")
        return True

    def start_service(self, command: list[str]) -> Optional[subprocess.Popen]:
        """Start the main service process."""
        self.log(f"Starting service: {' '.join(command)}")

        try:
            process = subprocess.Popen(
                command, cwd=self.project_root, stdout=sys.stdout, stderr=sys.stderr
            )
            return process
        except Exception as e:
            self.log(f"Failed to start service: {e}", "ERROR")
            return None

    def run(self, command: list[str]) -> int:
        """Main entrypoint execution."""
        self.log("Starting Agentic Neurodata Conversion container...")

        # Environment check
        if not self.check_environment():
            return 1

        # Setup directories
        if not self.setup_directories():
            return 1

        # Validate configuration
        if not self.validate_configuration():
            return 1

        # Wait for dependencies
        if not self.wait_for_dependencies():
            return 1

        # Run migrations
        if not self.run_migrations():
            return 1

        # Start the service
        process = self.start_service(command)
        if not process:
            return 1

        self.log("Service started successfully")

        # Wait for process or shutdown signal
        try:
            while not self.shutdown_requested:
                if process.poll() is not None:
                    # Process has terminated
                    return_code = process.returncode
                    self.log(f"Service process terminated with code {return_code}")
                    return return_code

                time.sleep(1)

            # Graceful shutdown requested
            self.log("Initiating graceful shutdown...")
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=30)
                self.log("Service shut down gracefully")
            except subprocess.TimeoutExpired:
                self.log("Service did not shut down gracefully, forcing termination")
                process.kill()
                process.wait()

            return 0

        except KeyboardInterrupt:
            self.log("Received keyboard interrupt")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            return 130


def main():
    """Main entrypoint function."""
    if len(sys.argv) < 2:
        print("Usage: docker_entrypoint.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1:]
    entrypoint = DockerEntrypoint()

    exit_code = entrypoint.run(command)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
