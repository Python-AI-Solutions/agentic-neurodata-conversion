#!/usr/bin/env python3
"""CLI script to run the HTTP server."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agentic_neurodata_conversion.mcp_server.http_adapter import main

if __name__ == "__main__":
    print("Starting Agentic Neurodata Conversion HTTP Server...")
    print("API documentation will be available at: http://127.0.0.1:8000/docs")
    print("Use Ctrl+C to stop the server")
    asyncio.run(main())