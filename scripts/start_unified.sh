#!/bin/bash
set -e

# Start SRE Agent Unified Service (FastAPI + Static Frontend)
# It listens on $PORT (defaults to 8080 in Cloud Run)
echo "🚀 Starting Unified SRE Agent on port $PORT..."
python server.py
