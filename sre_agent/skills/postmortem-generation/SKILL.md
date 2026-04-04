---
name: postmortem-generation
description: "Generate a blameless postmortem report from investigation findings. Use after completing an incident investigation to produce a structured, actionable postmortem following Google SRE practices."
---

## Postmortem Generation Workflow

Use this skill to generate a blameless postmortem after an incident investigation is complete.

### Prerequisites

Before generating a postmortem, ensure you have:
- Completed an investigation (ideally using the `incident-investigation` skill)
- Identified the root cause and contributing factors
- Documented the timeline of events

### Step 1: Gather Investigation Data

1. Use `get_investigation_summary` to retrieve the current investigation findings
2. Use `search_memory` to find related past incidents and patterns
3. Collect key data points:
   - **Incident start time**: When the issue was first detected
   - **Detection method**: How the incident was detected (alert, customer report, etc.)
   - **Impact duration**: Total time of user-facing impact
   - **Affected services**: Which services and users were impacted
   - **Root cause**: The underlying technical cause

### Step 2: Generate the Postmortem

1. Use `generate_postmortem` with the investigation findings to create a structured postmortem
2. The postmortem follows the template in `assets/postmortem-template.md` and includes:
   - Executive summary
   - Impact assessment (duration, scope, severity)
   - Timeline of events
   - Root cause analysis
   - Contributing factors
   - Action items with owners and deadlines

### Step 3: Generate Remediation Plan

1. Use `generate_remediation_suggestions` to get specific remediation recommendations
2. Use `estimate_remediation_risk` to assess each proposed change
3. Categorize action items:
   - **Immediate** (P0): Prevent recurrence of this specific incident
   - **Short-term** (P1): Address contributing factors within 1-2 weeks
   - **Long-term** (P2): Systemic improvements within 1-3 months

### Step 4: Review and Finalize

1. Ensure the postmortem is **blameless**: Focus on systems and processes, not individuals
2. Verify all action items are:
   - **Specific**: Clear description of what needs to be done
   - **Measurable**: Has a definition of done
   - **Assigned**: Has an owner
   - **Time-bound**: Has a deadline
3. Document lessons learned with `add_finding_to_memory` for future reference

### Key Principles

- **Blameless**: Focus on systemic issues, not individual mistakes
- **Actionable**: Every postmortem must produce concrete action items
- **Measurable**: Include SLO impact and error budget consumption
- **Reusable**: Findings should help prevent future incidents

### Reference

See `assets/postmortem-template.md` for the full postmortem template structure.
