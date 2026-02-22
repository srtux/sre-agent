# AgentOps Documentation

This directory contains all documentation related to the Auto SRE AgentOps ecosystem, which provides fleet-wide observability, debugging, and visualization for our multi-agent orchestration architecture.

The AgentOps ecosystem includes the React-based frontend UI, the underlying BigQuery property graph models, the OpenTelemetry tracking pipeline, and the theory of multi-agent observablity.

## Table of Contents

### 1. Theory & Concepts
Understanding the "why" behind Agent Graph and the observability problem space.
- [Multi-Agent Observability Theory](observability_theory.md)
- [Agent Graph Architecture & Theory](architecture.md)

### 2. UI & Dashboards
Navigating the human-facing operational surfaces.
- [AgentOps Dashboard (Fleet-Wide)](dashboard.md)
- [Observability Explorer UI (Logs/Metrics/Traces)](explorer_ui.md)
- [Legacy Dashboards Concepts](dashboards_legacy.md)

### 3. Backend & Data Pipeline
Understanding the schema, database setup, and telemetry ingestion.
- [BigQuery Schema & OpenTelemetry Extraction](bq_schema.md)
- [Agent Graph Fast Setup](setup.md)
- [BigQuery Agent Graph Deep Dive Setup](bigquery_setup.md)

---
*For general architecture or development guides, return to the [main documentation index](../README.md).*
