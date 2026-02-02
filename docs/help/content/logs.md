### Log Intelligence
AutoSRE clusters logs using AI to find patterns rather than just raw text.
- **Tool**: `summarize_log_patterns`
- **Utility**: Compare logs between two time windows (e.g., before and after a release).

### Example Workflow:
1. "Check logs for `checkout-service` from 10:00 to 11:00."
2. Agent: "Identified 5 rare `ConnectionTimeout` errors not present yesterday."
3. Agent: "These correlate with a 3x spike in latency."
