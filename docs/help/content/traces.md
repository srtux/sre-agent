### Getting Started with Traces
Traces visualize the lifecycle of a request across microservices.
- **Tool**: `fetch_trace` OR paste a Trace ID.
- **What to look for**: Long horizontal bars (latency) or red segments (errors).

### Example Workflow:
1. "Fetch trace `82e3...`"
2. The agent identifies the **Critical Path**.
3. It highlights the specific DB call causing a 2s delay.
4. It suggests checking the `billing-db` indexes.
