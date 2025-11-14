"""Command-line interface for Agentic Neurodata Conversion.

Usage:
    nwb-convert --help
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="nwb-convert",
        description="AI-powered neurophysiology data conversion to NWB format",
        epilog="For more information, visit: https://github.com/your-org/agentic-neurodata-conversion",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the FastAPI server")
    server_parser.add_argument(
        "--host",
        default="0.0.0.0",  # nosec B104 - required for Docker/network access, configurable via CLI
        help="Host to bind the server (default: 0.0.0.0)",
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server (default: 8000)",
    )
    server_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # Convert command (placeholder for future direct conversion)
    convert_parser = subparsers.add_parser("convert", help="Convert files directly (coming soon)")
    convert_parser.add_argument("input", help="Input file or directory")
    convert_parser.add_argument("output", help="Output NWB file")
    convert_parser.add_argument(
        "--format",
        help="Source format (auto-detected if not specified)",
    )

    args = parser.parse_args()

    if args.command == "server":
        start_server(args.host, args.port, args.reload)
    elif args.command == "convert":
        print("Direct conversion is not yet implemented.")
        print("Please use the web interface by running: nwb-convert server")
        sys.exit(1)
    else:
        parser.print_help()


def start_server(host: str, port: int, reload: bool):
    """Start the FastAPI server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed.")
        print("Install it with: pip install uvicorn")
        sys.exit(1)

    # Get the path to the FastAPI app
    Path(__file__).parent.parent.parent / "backend" / "src"

    print("🚀 Starting Agentic Neurodata Conversion Server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    print(f"   Access at: http://{host}:{port}")
    print()

    uvicorn.run(
        "agentic_neurodata_conversion.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
