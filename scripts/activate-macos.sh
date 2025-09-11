#!/bin/bash
# macOS activation script for pixi environment

# Set environment variables for neuroscience tools
export HDF5_USE_FILE_LOCKING=FALSE
export NUMBA_CACHE_DIR="$CONDA_PREFIX/tmp/numba_cache"

# Create cache directories if they don't exist
mkdir -p "$CONDA_PREFIX/tmp/numba_cache"

echo "Activated agentic-neurodata-conversion environment for macOS"
