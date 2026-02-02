### Telemetry Integration
The agent is a thin layer on top of your existing Observability stack:

- **GCP Cloud Logging & Monitoring**: Primary source for metrics and logs.
- **Cloud Trace**: For request-level debugging.
- **Kubernetes API**: To understand cluster state.
- **GitHub/GitLab**: (Optional) For change correlation and code analysis.

**Note**: The agent does not store your telemetry. It fetches it in real-time, analyzes it, and then discards the raw data once the conversation session ends.
