#!/usr/bin/env python3
"""
Deployment script for Agentic Neurodata Conversion.

This script handles deployment to different environments using Docker Compose.
"""

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Optional


class DeploymentManager:
    """Manages deployment operations for the Agentic Neurodata Conversion system."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compose_file = project_root / "docker-compose.yml"
        self.env_file = project_root / ".env"

    def run_command(
        self, command: list[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a shell command with proper error handling."""
        print(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                check=check,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            if e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            if check:
                sys.exit(1)
            return e

    def check_prerequisites(self) -> bool:
        """Check if Docker and Docker Compose are available."""
        try:
            self.run_command(["docker", "--version"])
            self.run_command(["docker", "compose", "version"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Docker and Docker Compose are required but not found.")
            print("Please install Docker Desktop or Docker Engine with Compose plugin.")
            return False

    def setup_environment(self, environment: str) -> None:
        """Set up environment configuration."""
        env_template = self.project_root / ".env.docker"

        if not self.env_file.exists() and env_template.exists():
            print("Creating .env file from template...")
            import shutil

            shutil.copy(env_template, self.env_file)
            print("Please review and customize the .env file before deployment.")

        # Update environment in .env file
        if self.env_file.exists():
            content = self.env_file.read_text()
            lines = []
            env_updated = False

            for line in content.split("\n"):
                if line.startswith("AGENTIC_CONVERTER_ENV="):
                    lines.append(f"AGENTIC_CONVERTER_ENV={environment}")
                    env_updated = True
                else:
                    lines.append(line)

            if not env_updated:
                lines.append(f"AGENTIC_CONVERTER_ENV={environment}")

            self.env_file.write_text("\n".join(lines))

    def create_directories(self) -> None:
        """Create necessary directories for deployment."""
        directories = [
            self.project_root / "data",
            self.project_root / "temp",
            self.project_root / "logs",
            self.project_root / "test-results",
        ]

        for directory in directories:
            directory.mkdir(exist_ok=True)
            print(f"Created directory: {directory}")

    def build_images(self, no_cache: bool = False) -> None:
        """Build Docker images."""
        command = ["docker", "compose", "build"]
        if no_cache:
            command.append("--no-cache")

        self.run_command(command)

    def deploy_development(self, services: Optional[list[str]] = None) -> None:
        """Deploy development environment."""
        print("Deploying development environment...")

        self.setup_environment("development")
        self.create_directories()

        command = ["docker", "compose", "up", "-d"]
        if services:
            command.extend(services)

        self.run_command(command)

        print("\nDevelopment environment deployed!")
        print("Services available at:")
        print("  - MCP Server: http://localhost:8000")
        print("  - HTTP Server: http://localhost:8080 (if enabled)")
        print("  - API Docs: http://localhost:8080/docs (if HTTP server enabled)")

    def deploy_production(self) -> None:
        """Deploy production environment."""
        print("Deploying production environment...")

        self.setup_environment("production")
        self.create_directories()

        # Use production override
        command = [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.prod.yml",
            "up",
            "-d",
        ]

        self.run_command(command)

        print("\nProduction environment deployed!")
        print("Services available at:")
        print("  - MCP Server: http://localhost:8000")

    def deploy_testing(self) -> None:
        """Deploy testing environment."""
        print("Deploying testing environment...")

        self.setup_environment("test")
        self.create_directories()

        command = [
            "docker",
            "compose",
            "--profile",
            "test",
            "up",
            "--build",
            "test-runner",
        ]

        self.run_command(command)

    def stop_services(self, remove_volumes: bool = False) -> None:
        """Stop all services."""
        print("Stopping services...")

        command = ["docker", "compose", "down"]
        if remove_volumes:
            command.append("--volumes")

        self.run_command(command)

        # Also stop production override if it exists
        prod_command = [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.prod.yml",
            "down",
        ]
        self.run_command(prod_command, check=False)

    def show_status(self) -> None:
        """Show status of all services."""
        print("Service status:")
        self.run_command(["docker", "compose", "ps"])

        print("\nService logs (last 20 lines):")
        self.run_command(["docker", "compose", "logs", "--tail=20"])

    def show_logs(self, service: Optional[str] = None, follow: bool = False) -> None:
        """Show logs for services."""
        command = ["docker", "compose", "logs"]
        if follow:
            command.append("-f")
        if service:
            command.append(service)

        self.run_command(command)


def main():
    """Main deployment script entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy Agentic Neurodata Conversion system"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Development deployment
    dev_parser = subparsers.add_parser("dev", help="Deploy development environment")
    dev_parser.add_argument("--services", nargs="*", help="Specific services to deploy")
    dev_parser.add_argument(
        "--no-cache", action="store_true", help="Build without cache"
    )

    # Production deployment
    prod_parser = subparsers.add_parser("prod", help="Deploy production environment")
    prod_parser.add_argument(
        "--no-cache", action="store_true", help="Build without cache"
    )

    # Testing deployment
    subparsers.add_parser("test", help="Run tests in container")

    # Management commands
    stop_parser = subparsers.add_parser("stop", help="Stop all services")
    stop_parser.add_argument(
        "--remove-volumes", action="store_true", help="Remove volumes when stopping"
    )

    subparsers.add_parser("status", help="Show service status")

    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("--service", help="Show logs for specific service")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow logs")

    subparsers.add_parser("build", help="Build Docker images")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize deployment manager
    project_root = Path(__file__).parent.parent
    manager = DeploymentManager(project_root)

    # Check prerequisites
    if not manager.check_prerequisites():
        return

    # Execute command
    try:
        if args.command == "dev":
            if hasattr(args, "no_cache") and args.no_cache:
                manager.build_images(no_cache=True)
            manager.deploy_development(args.services)

        elif args.command == "prod":
            if hasattr(args, "no_cache") and args.no_cache:
                manager.build_images(no_cache=True)
            manager.deploy_production()

        elif args.command == "test":
            manager.deploy_testing()

        elif args.command == "stop":
            manager.stop_services(args.remove_volumes)

        elif args.command == "status":
            manager.show_status()

        elif args.command == "logs":
            manager.show_logs(args.service, args.follow)

        elif args.command == "build":
            manager.build_images()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
