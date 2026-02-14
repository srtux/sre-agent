"""Self-Healing Agent Playbook.

Defines a structured playbook for the SRE Agent's autonomous
self-improvement cycle. Follows the OODA loop pattern:
Observe (trace analysis) -> Orient (code research) ->
Decide (fix strategy) -> Act (create PR).
"""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the self-healing agent playbook."""
    return Playbook(
        playbook_id="agent-self-healing",
        service_name="AutoSRE Agent",
        display_name="Agent Self-Healing",
        category=PlaybookCategory.OBSERVABILITY,
        description=(
            "Autonomous self-improvement playbook for the SRE Agent. "
            "Guides the agent through analyzing its own traces, "
            "identifying inefficiencies, researching fixes, and "
            "submitting pull requests to improve itself."
        ),
        issues=[
            _excessive_retries(),
            _token_waste(),
            _tool_syntax_errors(),
            _slow_investigation(),
        ],
        general_diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Analyze Recent Agent Traces",
                description=(
                    "Query the agent's own execution traces from the last 24 hours "
                    "to identify patterns of failure, inefficiency, or anti-patterns."
                ),
                tool_name="analyze_and_learn_from_traces",
                tool_params={
                    "trace_project_id": "{project_id}",
                    "hours_back": 24,
                    "focus_on_errors": True,
                },
                expected_outcome="List of recent agent traces with error/efficiency metrics",
            ),
            DiagnosticStep(
                step_number=2,
                title="Detect Anti-Patterns",
                description=(
                    "Run anti-pattern detection on interesting traces to find "
                    "excessive retries, token waste, long chains, and redundant calls."
                ),
                tool_name="detect_agent_anti_patterns",
                tool_params={"trace_id": "{trace_id}"},
                expected_outcome="List of detected anti-patterns with severity and recommendations",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Memory for Known Patterns",
                description=(
                    "Search memory for previously identified issues and their "
                    "resolutions to avoid duplicate work."
                ),
                tool_name="search_memory",
                tool_params={"query": "agent anti-pattern fix"},
                expected_outcome="Known patterns and past resolutions",
            ),
            DiagnosticStep(
                step_number=4,
                title="Research Fix Strategy",
                description=(
                    "Search Google for best practices and documentation related "
                    "to the identified issue."
                ),
                tool_name="search_google",
                tool_params={"query": "{issue_description} best practice"},
                expected_outcome="Relevant documentation or best practices",
            ),
            DiagnosticStep(
                step_number=5,
                title="Read Relevant Source Code",
                description=(
                    "Read the specific source files involved in the anti-pattern "
                    "to understand the current implementation."
                ),
                tool_name="github_read_file",
                tool_params={"file_path": "{source_file_path}"},
                expected_outcome="Current source code for the affected module",
            ),
            DiagnosticStep(
                step_number=6,
                title="Create Fix PR",
                description=(
                    "Create a draft pull request with the proposed fix. "
                    "Include clear description, motivation, and test plan."
                ),
                tool_name="github_create_pull_request",
                tool_params={
                    "title": "{pr_title}",
                    "description": "{pr_description}",
                    "branch_name": "auto-fix/{fix_slug}",
                    "file_changes": "{file_changes}",
                    "draft": True,
                },
                expected_outcome="Draft PR created with agent-generated label",
            ),
            DiagnosticStep(
                step_number=7,
                title="Record Findings to Memory",
                description=(
                    "Store the analysis findings and fix details in memory "
                    "so the agent can track whether the fix was effective."
                ),
                tool_name="add_finding_to_memory",
                tool_params={
                    "description": "{finding_summary}",
                    "source_tool": "self_healing_playbook",
                },
                expected_outcome="Finding persisted for future reference",
            ),
        ],
        best_practices=[
            "Always create PRs as drafts — human review is required before merge",
            "Include test updates with any code changes",
            "Focus on one issue per PR for clear review scope",
            "Add clear commit messages explaining the motivation",
            "Check memory before researching to avoid duplicate work",
            "Verify fixes by checking anti-pattern counts in subsequent analysis",
            "Label all agent-generated PRs with 'agent-generated' and 'auto-fix'",
            "Prefer minimal, targeted fixes over broad refactoring",
        ],
        key_metrics=[
            "agent_anti_pattern_count (from detect_agent_anti_patterns)",
            "tool_retry_rate (from after_tool_memory_callback)",
            "mean_investigation_duration_ms (from agent traces)",
            "token_output_input_ratio (from analyze_agent_token_usage)",
            "prs_created_by_agent (from github_create_pull_request)",
            "prs_merged_successfully (from GitHub API)",
        ],
        key_logs=[
            "Agent execution traces in BigQuery otel._AllSpans table",
            "Tool failure patterns in memory (search_memory query: 'tool_error_pattern')",
            "Memory learning events (category: failure, success, pattern)",
        ],
        related_services=[
            "Cloud Trace (agent execution observability)",
            "BigQuery (trace storage and analysis)",
            "GitHub (source code management and PR workflow)",
            "Cloud Build (CI/CD pipeline for auto-deployment)",
        ],
        documentation_urls=[
            "https://github.com/srtux/sre-agent",
            "https://google.github.io/adk-docs/",
            "https://docs.github.com/en/rest",
        ],
    )


def _excessive_retries() -> TroubleshootingIssue:
    return TroubleshootingIssue(
        issue_id="agent-excessive-retries",
        title="Agent Excessive Tool Retries",
        description=(
            "The agent calls the same tool more than 3 times under a single "
            "parent span, indicating it is not learning from failures within "
            "a single investigation turn."
        ),
        symptoms=[
            "Same tool called >3 times in a single trace",
            "Tool failures followed by identical calls",
            "High token usage relative to investigation complexity",
        ],
        root_causes=[
            "Missing input validation in tool (invalid args pass through silently)",
            "Poor error message not guiding the agent to correct syntax",
            "Missing memory lookup for known tool error patterns",
            "Prompt not instructing agent to try different approaches after 2 failures",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Identify Retry Pattern",
                description="Use detect_agent_anti_patterns to find excessive_retries type",
                tool_name="detect_agent_anti_patterns",
                tool_params={"trace_id": "{trace_id}"},
                expected_outcome="Anti-pattern details with affected tool and span IDs",
            ),
            DiagnosticStep(
                step_number=2,
                title="Read Tool Source",
                description="Read the tool implementation to check for input validation",
                tool_name="github_read_file",
                tool_params={"file_path": "{tool_source_path}"},
                expected_outcome="Source code showing validation (or lack thereof)",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Add Input Validation",
                description="Add parameter validation to the tool to return clear errors",
                tool_name="github_create_pull_request",
                tool_params={
                    "title": "fix: add input validation to {tool_name}",
                    "branch_name": "auto-fix/validate-{tool_name}",
                },
                expected_outcome="Draft PR with validation improvements",
            ),
        ],
        prevention_tips=[
            "All tools should validate inputs and return descriptive error messages",
            "Use record_tool_failure_pattern to share corrections globally",
            "Add the constraint 'If a tool fails twice with the same error, try a different approach' to prompts",
        ],
    )


def _token_waste() -> TroubleshootingIssue:
    return TroubleshootingIssue(
        issue_id="agent-token-waste",
        title="Agent Token Waste",
        description=(
            "The agent generates excessively long outputs relative to input, "
            "indicating verbose reasoning, unnecessary repetition, or failing "
            "to summarize intermediate results."
        ),
        symptoms=[
            "Output tokens >5x input tokens on intermediate LLM calls",
            "High overall token cost for simple investigations",
            "Long reasoning chains without tool use",
        ],
        root_causes=[
            "Prompt does not instruct concise intermediate reasoning",
            "Agent repeating full context on each turn instead of summarizing",
            "Missing context compaction for long investigations",
            "Sub-agent returning full raw data instead of summaries",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Analyze Token Breakdown",
                description="Get token usage breakdown by agent and model",
                tool_name="analyze_agent_token_usage",
                tool_params={"trace_id": "{trace_id}"},
                expected_outcome="Token usage per agent showing which agent is wasteful",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Optimize Prompt",
                description="Add conciseness instructions to the agent's system prompt",
                tool_name="github_read_file",
                tool_params={"file_path": "sre_agent/prompt.py"},
                expected_outcome="Current prompt content for review",
            ),
        ],
        prevention_tips=[
            "Include 'Be concise in intermediate reasoning' in system prompts",
            "Use skip_summarization=True for structured data tools",
            "Enable context compaction for long investigations",
        ],
    )


def _tool_syntax_errors() -> TroubleshootingIssue:
    return TroubleshootingIssue(
        issue_id="agent-tool-syntax-errors",
        title="Recurring Tool Syntax Errors",
        description=(
            "The agent repeatedly makes the same API syntax mistakes "
            "(e.g., invalid metric filters, wrong resource types) because "
            "corrections are not being learned or retrieved effectively."
        ),
        symptoms=[
            "Same error message appearing across multiple investigations",
            "Tool error patterns in memory not being retrieved",
            "Invalid filter or argument errors in tool responses",
        ],
        root_causes=[
            "Memory not being searched before tool calls",
            "Tool failure patterns not being recorded",
            "Prompt not instructing proactive memory lookup",
            "Memory search query not matching stored patterns",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Search for Known Patterns",
                description="Check if this error pattern exists in memory",
                tool_name="search_memory",
                tool_params={"query": "tool_error_pattern {tool_name}"},
                expected_outcome="Existing patterns or empty results",
            ),
            DiagnosticStep(
                step_number=2,
                title="Research Correct Syntax",
                description="Search Google for the correct API syntax",
                tool_name="search_google",
                tool_params={
                    "query": "{tool_name} {error_message} correct syntax",
                    "site_restrict": "cloud.google.com",
                },
                expected_outcome="Documentation with correct syntax examples",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Record Error Pattern",
                description="Store the correction for future use",
                tool_name="record_tool_failure_pattern",
                tool_params={
                    "tool_name": "{tool_name}",
                    "error_message": "{error_message}",
                    "wrong_input": "{wrong_input}",
                    "correct_input": "{correct_input}",
                    "resolution_summary": "{resolution}",
                },
                expected_outcome="Pattern stored globally for all agents",
            ),
        ],
        prevention_tips=[
            "Always call search_memory for tool error patterns before executing tools",
            "Use record_tool_failure_pattern immediately after discovering correct syntax",
            "Include common filter examples in tool docstrings",
        ],
    )


def _slow_investigation() -> TroubleshootingIssue:
    return TroubleshootingIssue(
        issue_id="agent-slow-investigation",
        title="Slow Investigation Performance",
        description=(
            "Investigations take longer than expected due to suboptimal "
            "tool selection, excessive data retrieval, or failure to use "
            "recommended investigation strategies."
        ),
        symptoms=[
            "Investigation duration >5 minutes for common issues",
            "Many tool calls that don't contribute to resolution",
            "Agent not using get_recommended_investigation_strategy",
        ],
        root_causes=[
            "Agent not checking memory for recommended strategies",
            "Fetching too much data before narrowing the investigation",
            "Not using the 3-stage pipeline (aggregate → triage → deep dive)",
            "Missing or outdated investigation patterns in memory",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="List Recent Traces",
                description="Find slow investigations in recent traces",
                tool_name="list_agent_traces",
                tool_params={
                    "reasoning_engine_id": "{engine_id}",
                    "hours_back": 24,
                },
                expected_outcome="List of agent runs sorted by duration",
            ),
            DiagnosticStep(
                step_number=2,
                title="Reconstruct Slow Trace",
                description="Rebuild the full interaction tree for the slow trace",
                tool_name="reconstruct_agent_interaction",
                tool_params={"trace_id": "{trace_id}"},
                expected_outcome="Full span tree showing tool calls and timing",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Learn Investigation Pattern",
                description="Record the optimal tool sequence for this symptom type",
                tool_name="complete_investigation",
                tool_params={
                    "symptom_type": "{symptom_type}",
                    "root_cause_category": "{root_cause}",
                    "resolution_summary": "{resolution}",
                },
                expected_outcome="Investigation pattern learned for future use",
            ),
        ],
        prevention_tips=[
            "Always call get_recommended_investigation_strategy at investigation start",
            "Follow the 3-stage pipeline: aggregate data → triage → deep dive",
            "Use route_request to select the optimal routing tier",
            "Record successful investigation patterns with complete_investigation",
        ],
    )
