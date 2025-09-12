#!/usr/bin/env python3
"""CLI script to run the MCP server."""

import asyncio
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agentic_neurodata_conversion.mcp_server.mcp_adapter import main  # noqa: E402

if __name__ == "__main__":
    print("Starting Agentic Neurodata Conversion MCP Server...")
    print("Use Ctrl+C to stop the server")
    asyncio.run(main())
