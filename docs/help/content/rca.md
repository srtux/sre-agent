### The Detective Methodology
AutoSRE uses a structured loop to diagnose issues:
1. **Triage**: Gather all Golden Signals (Latency, Traffic, Errors, Saturation).
2. **Hypothesize**: "Is it a memory leak?" or "Database lock contention?"
3. **Deep Dive**: Check container memory limits or DB query logs.
4. **Conclusion**: Scores causes by confidence levels.

### Example Workflow:
1. "Service `API` is slow."
2. Agent starts an Investigation Rail.
3. Conclusion: "Resource Exhaustion (CPU) - 92% confidence."
