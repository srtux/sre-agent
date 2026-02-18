"""Typed session state key constants for the council pipeline.

Single source of truth for all session state keys used across the council
architecture. Centralising these prevents string-literal typos and makes
state schema refactors safe — update here and let the type-checker guide
all downstream fixes.

Usage::

    from sre_agent.council.state import TRACE_FINDING, COUNCIL_SYNTHESIS

    finding = session.state.get(TRACE_FINDING)
    synthesis = session.state.get(COUNCIL_SYNTHESIS)
"""

# ---------------------------------------------------------------------------
# Panel output keys — written by each panel agent via output_key=
# ---------------------------------------------------------------------------

TRACE_FINDING: str = "trace_finding"
"""Session state key written by the trace panel agent."""

METRICS_FINDING: str = "metrics_finding"
"""Session state key written by the metrics panel agent."""

LOGS_FINDING: str = "logs_finding"
"""Session state key written by the logs panel agent."""

ALERTS_FINDING: str = "alerts_finding"
"""Session state key written by the alerts panel agent."""

DATA_FINDING: str = "data_finding"
"""Session state key written by the data/BigQuery panel agent."""

#: Ordered list of all panel finding keys, matching ParallelAgent panel order.
ALL_PANEL_FINDING_KEYS: tuple[str, ...] = (
    TRACE_FINDING,
    METRICS_FINDING,
    LOGS_FINDING,
    ALERTS_FINDING,
    DATA_FINDING,
)

# ---------------------------------------------------------------------------
# Synthesis and critic keys
# ---------------------------------------------------------------------------

COUNCIL_SYNTHESIS: str = "council_synthesis"
"""Session state key written by the synthesizer agent."""

CRITIC_REPORT: str = "critic_report"
"""Session state key written by the critic agent."""

# ---------------------------------------------------------------------------
# Debate state keys
# ---------------------------------------------------------------------------

DEBATE_CONVERGENCE_HISTORY: str = "debate_convergence_history"
"""Session state key holding the list of convergence records across debate rounds."""

# ---------------------------------------------------------------------------
# Investigation context keys — populated by CouncilOrchestrator
# ---------------------------------------------------------------------------

INVESTIGATION_QUERIES: str = "investigation_queries"
"""Recent user queries, used to build ClassificationContext."""

CURRENT_ALERT_SEVERITY: str = "current_alert_severity"
"""Alert severity string (e.g. 'critical'), used by adaptive classifier."""

REMAINING_TOKEN_BUDGET: str = "remaining_token_budget"
"""Remaining token budget, forwarded to adaptive classifier for DEBATE downgrade."""

PREVIOUS_INVESTIGATION_MODES: str = "previous_investigation_modes"
"""List of InvestigationMode values used in prior turns this session."""

# ---------------------------------------------------------------------------
# Panel progress tracking
# ---------------------------------------------------------------------------

PANEL_COMPLETIONS: str = "_panel_completions"
"""Dict of {panel_name: {severity, confidence, summary}} written by each panel's
``after_agent_callback`` as it completes.  Downstream consumers (dashboard channel,
API streaming) can poll this key to emit progressive UI updates."""

# ---------------------------------------------------------------------------
# EUC / credential propagation keys — set by middleware, read by tools
# ---------------------------------------------------------------------------

SESSION_STATE_ACCESS_TOKEN_KEY: str = "_user_access_token"
"""Encrypted access token stored in session state for Agent Engine mode."""

SESSION_STATE_PROJECT_ID_KEY: str = "_user_project_id"
"""GCP project ID stored in session state."""

# ---------------------------------------------------------------------------
# Internal callback timing keys
# ---------------------------------------------------------------------------

MODEL_CALL_START_TIME_KEY: str = "_model_call_start_time"
"""Per-turn timestamp stored by before_model_callback, consumed by after_model_callback."""
