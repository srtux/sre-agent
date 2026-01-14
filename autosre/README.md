# AutoSRE

A next-generation operation dashboard for SREs, built with **Flutter** and **GenUI**.

## Overview
AutoSRE connects to the SRE Agent (Python/ADK) and renders dynamic, generative UIs for distributed tracing, metric analysis, and incident remediation.

## Prerequisites
- **Flutter SDK**: [Install Flutter](https://docs.flutter.dev/get-started/install/macos)
- **SRE Agent**: Running locally on port 8001.

## Getting Started

1.  **Install Dependencies**:
    ```bash
    cd autosre
    flutter pub get
    ```

2.  **Run the App**:
    For macOS desktop:
    ```bash
    flutter run -d macos
    ```
    For Web (Chrome):
    ```bash
    flutter run -d chrome
    ```

## Architecture
- **Framework**: Flutter
- **Protocol**: [GenUI](https://github.com/flutter/genui) + [A2UI](https://a2ui.org)
- **State Management**: Provider
- **Entry Point**: `lib/main.dart`
- **App Configuration**: `lib/app.dart` & `lib/theme/app_theme.dart`
- **Catalog Registry**: `lib/catalog.dart`
- **Screens**: `lib/pages/`
- **Agent Connection**: `lib/agent/adk_content_generator.dart`

## Key Widgets
- `TraceWaterfall`: Gantt chart for distributed traces.
- `MetricCorrelationChart`: Timeline of metrics with anomaly detection.
- `LogPatternViewer`: Visualizes aggregated log patterns.
- `RemediationPlan`: Interactive checklist for fix actions.
