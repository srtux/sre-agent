### Blameless Postmortem Generation

AutoSRE can generate structured, blameless postmortem reports following Google SRE best practices. Postmortems are designed to capture what happened, why it happened, and what will prevent recurrence -- without assigning blame to individuals.

### How It Works

Use the `generate_postmortem` tool at the end of an investigation. The agent collects all findings, timeline events, and root cause analysis into a comprehensive report.

### What the Postmortem Includes

**Header**:
- Title, date, and status (DRAFT or COMPLETE)
- Severity assessment based on user impact, error budget consumption, duration, and revenue impact

**Incident Details**:
- Duration calculation with human-readable formatting
- Affected services list
- Detection method and timing
- Incident category

**Impact Assessment**:
- Percentage of users affected
- Error budget consumed
- Revenue impact flag
- Duration-based severity escalation

**Timing Metrics**:
- **Time to Detect (TTD)**: How long between incident start and detection
- **Time to Mitigate (TTM)**: How long between detection and mitigation
- **Total Duration**: Full incident window

**Root Cause Analysis**:
- Primary root cause description
- Contributing factors
- Investigation findings from the agent's analysis
- Incident category classification

**Action Items** (auto-generated based on root cause):
- **P0 -- Fix**: Address the root cause directly
- **P1 -- Detection**: Improve monitoring and alerting for this failure mode (target: reduce TTD by 50%)
- **P1 -- Process**: Category-specific improvements (e.g., canary deployments for deployment incidents, capacity planning for scaling incidents, config validation for configuration incidents)
- **P2 -- Improvement**: Address each contributing factor
- **P2 -- Documentation**: Update runbooks with lessons learned

**Lessons Learned**:
- What went well (detection method, response time)
- What went poorly (slow detection, manual mitigation)
- Where we got lucky

### Severity Assessment

The postmortem automatically assesses severity using multiple signals:

| Signal | Critical | High | Medium |
|--------|----------|------|--------|
| User Impact | 50%+ affected | 10--50% affected | 1--10% affected |
| Error Budget | 50%+ consumed | 20--50% consumed | 5--20% consumed |
| Duration | -- | 4+ hours | 1--4 hours |
| Revenue | Any revenue impact | -- | -- |

### Example Usage

```
"Generate a postmortem for the checkout latency incident that started at 2:00 PM today"
```

The agent will compile all investigation data from the session into a structured postmortem, including the timeline of events, root cause, and prioritized action items.

### Tips

- Generate the postmortem after completing the investigation for the most comprehensive report.
- The agent auto-populates the timeline from investigation state events.
- Action items include suggested owners (SRE Team, Service Owner, Platform Team) and due dates.
- If TTD exceeds 15 minutes, the report flags it as an area for improvement.
- If mitigation took longer than 30 minutes, the report suggests automating common mitigations.
- If the incident was detected by users rather than monitoring, the report recommends improving alerting coverage.
