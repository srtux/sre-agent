from server import TOOL_WIDGET_MAP
from sre_agent.tools.analysis import genui_adapter


def test_list_time_series_adaptation():
    """Test that list_time_series output (list) is correctly adapted for x-sre-metric-chart."""

    # 1. Setup - no pending calls needed for this unit test of adapter logic

    # 2. Define the sample Data (simplified list from user report)
    # The list format is what we want to verify is handled correctly
    raw_data = [
        {
            "metric": {
                "type": "run.googleapis.com/request_count",
                "labels": {"response_code": "200"},
            },
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "autosre"},
            },
            "points": [
                {"timestamp": "2026-01-17T05:56:00+00:00", "value": 1.0},
                {"timestamp": "2026-01-17T05:55:00+00:00", "value": 0.0},
            ],
        }
    ]

    # 3. Simulate the tool response processing logic from server.py's event generator
    # Note: _create_tool_response_events only creates the TOOL LOG update.
    # The WIDGET update logic is separate in the server.py event loop.
    # We need to test the ADAPTER logic specifically, or reproduce the logic block from server.py

    # Since we can't easily reproduce the server.py event loop here without copy-paste or extensive mocking,
    # we will verify the logic block that was problematic:
    # if isinstance(data, (dict, list)): ...

    tool_name = "list_time_series"
    component_name = TOOL_WIDGET_MAP[tool_name]

    # Assert earlier logic in server.py
    assert component_name == "x-sre-metric-chart"

    # This is the logic we patched in server.py
    data = raw_data
    transformed_data = None

    if isinstance(data, dict | list):
        if component_name == "x-sre-metric-chart":
            transformed_data = genui_adapter.transform_metrics(data)

    # 4. Verify transformation happened
    assert transformed_data is not None
    assert transformed_data["metric_name"] == "run.googleapis.com/request_count"
    assert len(transformed_data["points"]) == 2
    assert transformed_data["points"][0]["value"] == 1.0

    # Verify labels were merged
    assert transformed_data["labels"]["response_code"] == "200"
    assert transformed_data["labels"]["service_name"] == "autosre"
