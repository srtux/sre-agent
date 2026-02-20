# --- Builder Stage for Flutter Web ---
FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y \
    curl git unzip xz-utils libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter
RUN git clone https://github.com/flutter/flutter.git -b stable /flutter
ENV PATH="/flutter/bin:$PATH"
RUN flutter doctor

WORKDIR /app
COPY autosre/ ./autosre/
WORKDIR /app/autosre
RUN flutter pub get
RUN flutter pub run build_runner build --delete-conflicting-outputs
RUN flutter build web --release

# --- Builder Stage for React Agent Graph UI ---
FROM node:20-slim AS react-builder

WORKDIR /app/agent_graph_ui
COPY agent_graph_ui/package.json agent_graph_ui/package-lock.json* ./
RUN npm ci
COPY agent_graph_ui/ .
RUN npm run build

# --- Production Stage ---
FROM python:3.11-slim

# 1. Setup Python Backend
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY sre_agent/ ./sre_agent/
COPY server.py .
COPY README.md .
COPY docs/ ./docs/

# Install dependencies and the local package
RUN uv pip install --system --no-cache . uvicorn fastapi google-adk google-cloud-aiplatform nest-asyncio mcp pydantic-core

# 2. Setup Flutter Web Frontend (from builder)
COPY --from=builder /app/autosre/build/web ./web/

# 3. Setup React Agent Graph UI (from react-builder)
COPY --from=react-builder /app/agent_graph_ui/dist ./agent_graph_web/

# 4. Startup Script
COPY scripts/start_unified.sh .
RUN chmod +x start_unified.sh

# Build metadata (injected by Cloud Build / docker build --build-arg)
ARG BUILD_SHA="unknown"
ARG BUILD_TIMESTAMP=""
ENV BUILD_SHA=${BUILD_SHA}
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Environment variables
ENV PORT=8080
ENV HOSTNAME="0.0.0.0"
ENV SRE_AGENT_URL="http://127.0.0.1:8001"
ENV PYTHONUNBUFFERED=1

CMD ["./start_unified.sh"]
