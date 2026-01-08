# Cloud Trace Analyzer Agent

[![Status](https://img.shields.io/badge/Status-Active-success)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![Framework](https://img.shields.io/badge/Framework-Google%20ADK-red)]()


A Google ADK-based agent that performs deep diff analysis on distributed traces from Cloud Trace. It compares baseline (normal) traces to abnormal traces to identify performance regressions, errors, and behavioral changes using a "squad" of specialized analysis sub-agents.

## Features

- **Parallel Analysis Squads**: Uses **6 specialized agents** divided into Triage (Latency, Error, Structure, Statistics) and Deep Dive (Causality, Service Impact) squads to analyze traces concurrently.
- **Hybrid BigQuery Integration**: Leverages BigQuery via MCP (Model Context Protocol) for statistical analysis over large datasets and long time ranges.
- **Automatic Trace Discovery**: Intelligently identifies representative baseline (P50) and anomaly (P95 or error) traces for comparison.
- **Advanced Trace Filtering**: Supports complex filters including service names, HTTP status codes, min/max latency, and custom attribute matching.
- **Root Cause Synthesis**: Automatically identifies the critical path and performs causal analysis to explain *why* a trace is slow or failing.
- **Cloud Console Integration**: Directly analyze traces by pasting their Google Cloud Console URL.

## Architecture

The agent is built using the Google Agent Development Kit (ADK) and follows a hierarchical orchestration pattern:

```mermaid
flowchart TD
    %% Styles
    classDef primary fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    classDef secondary fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef squad fill:#fff3e0,stroke:#e65100,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    classDef tool fill:#f1f8e9,stroke:#33691e,stroke-width:1px,color:#000

    User([👤 User]) --> Root[🕵️ Trace Detective]
    
    subgraph S1_Group [Stage 1: Triage]
        direction TB
        S1[🚦 Triage Squad]
        L[⏱️ Latency]
        E[💥 Error]
        S[🏗️ Structure]
        ST[📊 Statistics]
        S1 --> L & E & S & ST
    end

    subgraph S2_Group [Stage 2: Deep Dive]
        direction TB
        S2[🔍 Deep Dive Squad]
        C[🔗 Causality]
        SI[🌊 Service Impact]
        S2 --> C & SI
    end

    subgraph Tools [🛠️ Tool Suite]
        TraceAPI[Cloud Trace API]
        BQ[BigQuery MCP]
        Filter[Trace Query Builder]
    end

    %% Flow
    Root ==>|1. Identify| S1
    Root -.->|2. Investigate| S2
    
    %% Tool Usage
    Root -.- Tools
    S1 -.-> Tools
    S2 -.-> Tools

    %% Assign Classes
    class Root primary
    class S1,S2 squad
    class L,E,S,ST,C,SI secondary
    class TraceAPI,BQ,Filter tool
```

### Core Components
- **Trace Detective (Root)**: The orchestrator with a "Detective" persona that synthesizes findings into a "Case File". It uses an interactive workflow, reporting Triage findings first before proceeding to Deep Dive.
- **Triage Squad (Stage 1)**: Rapidly identifies *what* is wrong (Latency, Errors, Structure, Stats).
- **Deep Dive Squad (Stage 2)**: Investigates *why* it happened (Causality) and *who* else is affected (Service Impact).
- **Dynamic MCP Integration**: Uses `ApiRegistry` to lazily load BigQuery tools, ensuring cross-platform stability.

## Setup

### 1. Install Dependencies

The project uses `uv` for high-performance dependency management:

```bash
cd trace_analyzer
uv sync
```

### 2. Configure Environment

Copy the example environment file and configure your Google Cloud project:

```bash
cp .env.example .env
```

Key variables in `.env`:
```bash
# Required for Cloud Trace and BigQuery access
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1

# Agent Engine Configuration
GOOGLE_GENAI_USE_VERTEXAI=1
```

### 3. Ensure IAM Permissions

The authenticated user or service account requires:
- `roles/cloudtrace.user`
- `roles/bigquery.dataViewer`
- `roles/bigquery.jobUser`

## Deployment

### Deployment (Standard ADK CLI)
 
 If you prefer using the standard `adk` CLI, you can pass environment variables via an env file:
 
 ```bash
 # 1. Ensure env vars are in trace_analyzer/telemetry.env
 # 2. Deploy using the --env_file flag
 uv run adk deploy agent_engine \
   --project=your-project \
   --region=us-central1 \
   --staging_bucket=your-bucket \
   --display_name="Trace Analyzer" \
   --env_file trace_analyzer/telemetry.env \
   trace_analyzer
 ```
 
 ### Deployment (Custom Script)
 
 We also provide a custom deployment script that supports direct flags:
 
 ```bash
 # Basic deployment
 uv run python deploy/deploy.py --create
 ```

The script will create a Reasoning Engine (Agent Engine) resource and output its resource name.

## Usage

### Running the Agent

```bash
# Launch the interactive terminal UI
uv run adk run .

# Launch the web-based interface
uv run adk web
```

### Example Prompts

**Trend Analysis & Discovery:**
> "Find example traces in my project from the last 4 hours and show me what's different between a typical request and a slow one."

**Specific Investigation:**
> "Analyze this trace from the production console: https://console.cloud.google.com/traces/details/[TRACE_ID]?project=[PROJECT_ID]"

**Service-Specific Filtering:**
> "Find traces for the 'payment-processor' service with latency > 500ms and compare them to the baseline."

**BigQuery Powered Queries:**
> "Use BigQuery to find the most frequent error patterns in my traces over the last 24 hours."

## Project Structure

```
trace_analyzer/
├── trace_analyzer/
│   ├── agent.py          # Root orchestrator ("Trace Detective")
│   ├── sub_agents/       # Specialized analysis agents
│   │   ├── latency/      # Latency Analyzer
│   │   ├── error/        # Error Analyzer
│   │   ├── structure/    # Structure Analyzer
│   │   ├── statistics/   # Statistics Analyzer
│   │   ├── causality/    # Causality Analyzer
│   │   └── service_impact/ # Service Impact Analyzer
│   ├── tools/
│   │   ├── trace_client.py   # Cloud Trace API wrapper
│   │   ├── trace_filter.py   # Advanced TraceQueryBuilder
│   │   └── ...
│   └── prompt.py         # Advanced multi-turn prompting logic
├── tests/                # Comprehensive test suite
├── deployment/           # Deployment scripts
├── AGENTS.md             # Developer & Contributor guide
├── pyproject.toml        # uv-based build configuration
└── README.md
```

## Reliability & Performance

## Reliability & Performance

- **Lazy MCP Loading**: Implements `LazyMcpRegistryToolset` to prevent session conflicts in ASGI/uvicorn environments, ensuring stable deployment.
- **Observability**: Fully instrumented with OpenTelemetry for tracking tool execution and agent performance.
- **Truncation & Noise Reduction**: Advanced logging patterns ensure that large trace datasets don't overwhelm LLM context windows.

## Troubleshooting

- **`ValueError: stale session`**: This usually happens if the local database state gets out of sync with the running agent. Try clearing the `.adk` directory or restarting the server.
- **Permission Errors**: Ensure you have run `gcloud auth application-default login` and that your user has `roles/cloudtrace.user` and `roles/bigquery.dataViewer`.
- **ASGI Errors**: If you see "ASGI callable returned without completing response", ensure you are using the latest version of the ADK and that `LazyMcpRegistryToolset` is being used for MCP tools.

## Contributing

See [AGENTS.md](./AGENTS.md) for detailed developer workflows, testing instructions, and PR guidelines.

## License

Apache-2.0
