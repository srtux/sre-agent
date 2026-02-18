"""Tests for council session state key constants (sre_agent.council.state)."""

from sre_agent.council import state


class TestPanelFindingKeys:
    """Panel output key constants."""

    def test_all_finding_keys_are_strings(self) -> None:
        for key in state.ALL_PANEL_FINDING_KEYS:
            assert isinstance(key, str)
            assert len(key) > 0

    def test_all_panel_finding_keys_tuple_contains_five_entries(self) -> None:
        assert len(state.ALL_PANEL_FINDING_KEYS) == 5

    def test_individual_keys_in_tuple(self) -> None:
        assert state.TRACE_FINDING in state.ALL_PANEL_FINDING_KEYS
        assert state.METRICS_FINDING in state.ALL_PANEL_FINDING_KEYS
        assert state.LOGS_FINDING in state.ALL_PANEL_FINDING_KEYS
        assert state.ALERTS_FINDING in state.ALL_PANEL_FINDING_KEYS
        assert state.DATA_FINDING in state.ALL_PANEL_FINDING_KEYS

    def test_no_duplicate_panel_keys(self) -> None:
        keys = list(state.ALL_PANEL_FINDING_KEYS)
        assert len(keys) == len(set(keys))


class TestAllConstants:
    """All exported string constants are non-empty strings with no duplicates."""

    _all_string_constants = [
        "TRACE_FINDING",
        "METRICS_FINDING",
        "LOGS_FINDING",
        "ALERTS_FINDING",
        "DATA_FINDING",
        "COUNCIL_SYNTHESIS",
        "CRITIC_REPORT",
        "DEBATE_CONVERGENCE_HISTORY",
        "INVESTIGATION_QUERIES",
        "CURRENT_ALERT_SEVERITY",
        "REMAINING_TOKEN_BUDGET",
        "PREVIOUS_INVESTIGATION_MODES",
        "PANEL_COMPLETIONS",
        "SESSION_STATE_ACCESS_TOKEN_KEY",
        "SESSION_STATE_PROJECT_ID_KEY",
        "MODEL_CALL_START_TIME_KEY",
    ]

    def test_all_constants_are_non_empty_strings(self) -> None:
        for name in self._all_string_constants:
            value = getattr(state, name)
            assert isinstance(value, str), f"{name} should be str, got {type(value)}"
            assert len(value) > 0, f"{name} should be non-empty"

    def test_no_duplicate_values(self) -> None:
        values = [getattr(state, name) for name in self._all_string_constants]
        assert len(values) == len(set(values)), "State key constants must be unique"


class TestDebateKeys:
    """Debate-specific key constants."""

    def test_convergence_history_key(self) -> None:
        assert state.DEBATE_CONVERGENCE_HISTORY == "debate_convergence_history"

    def test_critic_report_key(self) -> None:
        assert state.CRITIC_REPORT == "critic_report"

    def test_council_synthesis_key(self) -> None:
        assert state.COUNCIL_SYNTHESIS == "council_synthesis"


class TestPanelCompletionsKey:
    """Panel progress tracking key."""

    def test_panel_completions_starts_with_underscore(self) -> None:
        """Internal keys use underscore prefix by convention."""
        assert state.PANEL_COMPLETIONS.startswith("_")

    def test_panel_completions_value(self) -> None:
        assert state.PANEL_COMPLETIONS == "_panel_completions"
