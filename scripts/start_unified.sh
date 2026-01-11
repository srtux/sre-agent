#!/bin/bash
set -e

# 1. Start Python Backend (Tools API) in background
# It listens on 8000
echo "🚀 Starting Python Tools API on port 8000..."
uvicorn server:app --host 127.0.0.1 --port 8000 &

# 2. Start Next.js Frontend in foreground
# It listens on $PORT (defaults to 8080 in Cloud Run)
echo "🚀 Starting Next.js Frontend on port $PORT..."
cd web
node server.js
