### Council Investigation

AutoSRE can investigate incidents using a **Council of Experts** — four specialist panels that analyze your system simultaneously, then synthesize their findings into a unified assessment.

### How It Works

1. **Four Panels Run in Parallel**: Trace, Metrics, Logs, and Alerts specialists each examine the incident from their domain.
2. **Synthesis**: Findings are merged into a single assessment with severity, confidence scores, and recommended actions.
3. **Debate Mode** (optional): For critical incidents, a critic challenges the panels' conclusions, driving iterative refinement until consensus is reached.

### Investigation Modes

- **Fast**: Quick single-signal checks. Best for "Are there any alerts?" or "What's the error rate?"
- **Standard**: All four panels analyze in parallel, then synthesize. Best for multi-signal investigations like latency spikes or error surges.
- **Debate**: Panels + adversarial critic loop. Best for P0/P1 production incidents requiring root cause confidence.

### Example Prompts

- "Investigate the latency spike in checkout-service" → Standard mode
- "Quick check — any active alerts?" → Fast mode
- "Deep dive into the payment processing outage, I need high confidence" → Debate mode

### What You See

- **Tool calls** from each panel appear inline in the chat (trace analysis, metric queries, log searches, alert checks).
- **Council tab** in the Investigation Dashboard shows the synthesized result with severity, confidence, and debate rounds.
- **Signal tabs** (Traces, Metrics, Logs, Alerts) populate with data from each panel's analysis.

### Tips

- The agent auto-selects the right mode based on your question. You can also ask explicitly: "use debate mode" or "do a quick check."
- Council findings include confidence scores (0–100%). Debate mode drives confidence higher through iterative refinement.
- Each panel has access to the full set of domain-specific tools, so no signal is left unexamined.
