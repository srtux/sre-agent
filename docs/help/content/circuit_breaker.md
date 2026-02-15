### Circuit Breaker Pattern

AutoSRE implements the **Circuit Breaker** pattern to protect your cloud resources during outages. When GCP APIs or backend services start failing, the circuit breaker prevents "retry storms" that would worsen the situation.

### How It Works

The circuit breaker tracks the health of each tool's backend independently. It transitions between three states:

```
CLOSED (normal) --[failures >= threshold]--> OPEN (fast-fail)
                                              |
                                    [recovery timeout elapsed]
                                              |
                                              v
                                         HALF_OPEN (testing)
                                         /            \
                              [success >= threshold]  [any failure]
                                        |                |
                                        v                v
                                     CLOSED            OPEN
```

### States

| State | Behavior | When |
|-------|----------|------|
| **CLOSED** | Normal operation. All calls pass through. Failures are counted. | Default state; also restored after successful recovery. |
| **OPEN** | Calls fail immediately without execution (`CircuitBreakerOpenError`). No requests sent to the failing service. | Entered after 5 consecutive failures (configurable). |
| **HALF_OPEN** | A limited number of test calls are allowed to check if the service has recovered. | Entered after the recovery timeout (60 seconds by default) elapses. |

### Configuration

Each tool can have custom circuit breaker settings, or use the defaults:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Number of consecutive failures before opening the circuit |
| `recovery_timeout_seconds` | 60.0 | Seconds to wait in OPEN state before transitioning to HALF_OPEN |
| `half_open_max_calls` | 1 | Maximum test calls allowed in HALF_OPEN state |
| `success_threshold` | 2 | Successful calls in HALF_OPEN needed to close the circuit |

### State Transitions

**CLOSED to OPEN:**
- Each failure increments the failure counter.
- When the counter reaches the `failure_threshold` (default 5), the circuit opens.
- All subsequent calls fail fast with a `CircuitBreakerOpenError` that includes the retry-after time.

**OPEN to HALF_OPEN:**
- After `recovery_timeout_seconds` (default 60) elapse since the last failure, the next call attempt transitions to HALF_OPEN.
- In HALF_OPEN, a limited number of calls (`half_open_max_calls`, default 1) are allowed through as test probes.

**HALF_OPEN to CLOSED (Recovery):**
- If `success_threshold` (default 2) consecutive calls succeed in HALF_OPEN, the circuit closes and normal operation resumes.
- The failure counter is reset to zero.

**HALF_OPEN to OPEN (Recovery Failed):**
- If any call fails during HALF_OPEN, the circuit immediately re-opens.
- The recovery timeout restarts.

### Self-Healing Behavior

In CLOSED state, the circuit breaker supports gradual recovery:
- Each successful call decrements the failure counter by 1 (if it was above zero).
- This means intermittent single failures do not trigger the circuit if successes outnumber them.

### What You See

When a circuit opens, the agent:
1. Reports that the tool is temporarily unavailable.
2. Provides the retry-after time.
3. May fall back to alternative data sources (e.g., MCP to direct API fallback).
4. Continues the investigation using available tools from other domains.

### Monitoring Circuit Status

The registry provides observability into all circuit breakers:

- **Per-tool status**: Current state, failure count, total calls, total failures, total short-circuits.
- **Open circuits list**: Quick view of all tools with open circuits.
- **All status**: Dashboard of every tracked circuit breaker.

### Why This Matters

Without circuit breakers, a failing API can cause:
- **API Quota Exhaustion**: Repeated retries consume your Cloud API quota rapidly.
- **Cascading Failures**: A failure in one service propagates to all dependent tools.
- **Slow Investigations**: Instead of failing fast, the agent waits for timeouts on every call.
- **Cost Overruns**: Each failed API call still consumes LLM tokens for the retry logic.

The circuit breaker ensures the agent degrades gracefully, focusing on available data sources rather than hammering a broken API.
