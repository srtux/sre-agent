"""Unit tests for the reporting tool."""

import pytest

from sre_agent.tools.reporting import synthesize_report


@pytest.mark.asyncio
async def test_synthesize_report_full_data():
    """Test report synthesis with all data provided."""
    root_cause = {
        "results": {
            "causality": {"result": "The database is the root cause."},
            "change_detective": {"result": "A deployment happened 5 mins ago."},
            "service_impact": {"result": "5 services affected."},
        }
    }
    triage = {
        "results": {
            "latency": {"status": "success", "result": "Latency spiked by 500ms."},
            "error": {"status": "success", "result": "Error rate is 5%."},
        }
    }
    aggregate = {"result": "Traffic increased by 20%."}
    log_analysis = {"result": "Log errors found in logs."}

    report = await synthesize_report(
        root_cause_analysis=root_cause,
        triage_results=triage,
        aggregate_results=aggregate,
        log_analysis=log_analysis,
    )

    assert "# Root Cause Investigation Report" in report["report"]
    assert "The database is the root cause." in report["report"]
    assert "A deployment happened 5 mins ago." in report["report"]
    assert "5 services affected." in report["report"]
    assert "Latency spiked by 500ms." in report["report"]
    assert "Error rate is 5%." in report["report"]
    assert "Traffic increased by 20%." in report["report"]
    assert "Log errors found in logs." in report["report"]
    assert "## Executive Summary" in report["report"]
    assert "## Evidence" in report["report"]
    assert "## Trace Forensics" in report["report"]
    assert "## Impact Assessment" in report["report"]


@pytest.mark.asyncio
async def test_synthesize_report_minimal_data():
    """Test report synthesis with minimal/missing data."""
    root_cause = {}
    triage = {}

    report = await synthesize_report(
        root_cause_analysis=root_cause, triage_results=triage
    )

    assert "# Root Cause Investigation Report" in report["report"]
    assert "Analysis Inconclusive" in report["report"]
    assert "No change detection data" in report["report"]
    assert "Unknown Impact" in report["report"]
    assert "## Trace Forensics" in report["report"]
    # Should NOT have sections for missing data
    assert "Aggregate Patterns" not in report["report"]
    assert "Log Patterns" not in report["report"]
