#!/usr/bin/env python3
"""
Environment setup script for deployment.
"""

import argparse
from pathlib import Path
import shutil


def setup_development():
    """Setup development environment."""
    print("Setting up development environment...")

    project_root = Path(__file__).parent.parent
    env_template = project_root / ".env.docker"
    env_file = project_root / ".env"

    if not env_file.exists() and env_template.exists():
        shutil.copy(env_template, env_file)
        print("Created .env file from template")
    else:
        print(".env file already exists")

    print("Development environment ready!")
    print("Run 'pixi run deploy-dev' to start services")


def setup_production():
    """Setup production environment."""
    print("Setting up production environment...")

    project_root = Path(__file__).parent.parent
    env_template = project_root / ".env.docker"
    env_file = project_root / ".env"

    if not env_file.exists() and env_template.exists():
        shutil.copy(env_template, env_file)
        print("Created .env file from template")
    else:
        print(".env file already exists")

    print("Please edit .env file with production settings")
    print("Then run 'pixi run deploy-prod' to start services")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup deployment environment")
    parser.add_argument(
        "environment", choices=["dev", "prod"], help="Environment to setup"
    )

    args = parser.parse_args()

    if args.environment == "dev":
        setup_development()
    elif args.environment == "prod":
        setup_production()


if __name__ == "__main__":
    main()
