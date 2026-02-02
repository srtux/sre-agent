### The AutoSRE Gold Path
The agent is designed to follow the standard SRE incident response lifecycle:

1.  **Detection**: An alert is triggered (or you report an issue).
2.  **Triage**: The agent gathers "Golden Signals" (Latency, Errors, Traffic, Saturation).
3.  **RCA**: The agent investigates recent changes, traces, and logs.
4.  **Mitigation**: The agent suggests remediation steps (Rollbacks, Restarts).
5.  **Resolution**: You verify the fix using the agent's telemetry tools.
6.  **Postmortem**: The agent generates a draft incident report.

To see this in action, simply say: *"Help me investigate the spike in checkout errors."*
