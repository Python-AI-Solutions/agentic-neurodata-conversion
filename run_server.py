#!/usr/bin/env python
"""
Server startup script that sets up Python path correctly.
"""
import os
import sys
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print(f"Loading environment variables from: {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value
                    if key.strip() == "ANTHROPIC_API_KEY":
                        print(f"  ✓ Loaded ANTHROPIC_API_KEY: {value[:15]}...")
else:
    print(f"Warning: No .env file found at {env_file}")
    print("  LLM features will not work without ANTHROPIC_API_KEY")

# Add backend/src to Python path
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_src)],
    )
