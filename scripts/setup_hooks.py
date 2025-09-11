"""Set up pre-commit hooks for the project."""

from pathlib import Path
import subprocess
import sys


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {' '.join(command)}")
        print(f"   Error: {e.stderr}")
        return False


def main() -> int:
    """Main setup function."""
    print("Setting up development environment...")

    # Check if we're in a pixi environment
    if not Path("pixi.toml").exists():
        print("❌ pixi.toml not found. Please run from project root.")
        return 1

    success = True

    # Install pre-commit hooks
    success &= run_command(
        ["pixi", "run", "pre-commit", "install"], "Installing pre-commit hooks"
    )

    # Install pre-push hooks
    success &= run_command(
        ["pixi", "run", "pre-commit", "install", "--hook-type", "pre-push"],
        "Installing pre-push hooks",
    )

    # Run pre-commit on all files to ensure everything works
    success &= run_command(
        ["pixi", "run", "pre-commit", "run", "--all-files"],
        "Running pre-commit on all files",
    )

    if success:
        print("\n🎉 Development environment setup complete!")
        print("\nNext steps:")
        print("  1. Make your changes")
        print("  2. Run 'pixi run pre-commit' before committing")
        print("  3. Run 'pixi run pytest tests/unit/ --no-cov' for fast tests")
        return 0
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
