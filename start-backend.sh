#!/bin/bash

# Neurodata Converter - Backend Startup Script
# This script ensures only ONE server instance runs

set -e

PROJECT_ROOT="/Users/adityapatane/agentic-neurodata-conversion-14"
BACKEND_DIR="$PROJECT_ROOT/backend/src"
PORT=8000

echo "🔧 Neurodata Converter - Starting Backend..."

# Step 1: Kill any existing servers
echo "1️⃣ Checking for existing servers..."
existing_pids=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$existing_pids" ]; then
    echo "   ⚠️  Found existing server(s) on port $PORT: $existing_pids"
    echo "   🔪 Killing existing servers..."
    echo "$existing_pids" | xargs kill -9 2>/dev/null || true
    sleep 2
    echo "   ✅ Killed existing servers"
else
    echo "   ✅ No existing servers found"
fi

# Step 2: Reset backend state
echo "2️⃣ Resetting backend state..."
curl -X POST http://localhost:$PORT/api/reset 2>/dev/null || echo "   ⚠️  Server not running (will start fresh)"

# Step 3: Navigate to backend directory
echo "3️⃣ Navigating to backend directory..."
cd "$BACKEND_DIR" || exit 1

# Step 4: Start the server
echo "4️⃣ Starting uvicorn server on port $PORT..."
pixi run python -m uvicorn api.main:app --reload --host 0.0.0.0 --port $PORT
