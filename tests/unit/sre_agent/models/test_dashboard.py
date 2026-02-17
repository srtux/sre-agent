"""Tests for dashboard Pydantic models."""

import pytest
from pydantic import ValidationError

from sre_agent.models.dashboard import (
    BigQueryQuery,
    CloudMonitoringQuery,
    CreateDashboardRequest,
    Dashboard,
    DashboardMetadata,
    DashboardSource,
    DashboardSummary,
    DashboardVariable,
    DatasourceRef,
    DatasourceType,
    GridPosition,
    LogsQuery,
    Panel,
    PanelDisplay,
    PanelQuery,
    PanelType,
    PrometheusQuery,
    TextContent,
    Threshold,
    ThresholdColor,
    TimeRange,
    TimeRangePreset,
    UpdateDashboardRequest,
    VariableType,
)


class TestEnums:
    def test_dashboard_source_values(self) -> None:
        assert DashboardSource.LOCAL.value == "local"
        assert DashboardSource.CLOUD_MONITORING.value == "cloud_monitoring"

    def test_panel_type_values(self) -> None:
        assert PanelType.TIME_SERIES.value == "time_series"
        assert PanelType.GAUGE.value == "gauge"
        assert PanelType.LOGS.value == "logs"
        assert PanelType.TRACES.value == "traces"
        assert PanelType.HEATMAP.value == "heatmap"
        assert len(PanelType) == 16

    def test_datasource_type_values(self) -> None:
        assert DatasourceType.PROMETHEUS.value == "prometheus"
        assert DatasourceType.CLOUD_MONITORING.value == "cloud_monitoring"
        assert DatasourceType.BIGQUERY.value == "bigquery"

    def test_time_range_preset_values(self) -> None:
        assert TimeRangePreset.ONE_HOUR.value == "1h"
        assert TimeRangePreset.CUSTOM.value == "custom"


class TestGridPosition:
    def test_default_values(self) -> None:
        pos = GridPosition()
        assert pos.x == 0
        assert pos.y == 0
        assert pos.width == 12
        assert pos.height == 4

    def test_custom_values(self) -> None:
        pos = GridPosition(x=6, y=2, width=18, height=8)
        assert pos.x == 6
        assert pos.y == 2
        assert pos.width == 18
        assert pos.height == 8

    def test_negative_x_raises(self) -> None:
        with pytest.raises(ValidationError):
            GridPosition(x=-1)

    def test_width_max_24(self) -> None:
        pos = GridPosition(width=24)
        assert pos.width == 24

    def test_width_over_24_raises(self) -> None:
        with pytest.raises(ValidationError):
            GridPosition(width=25)

    def test_frozen(self) -> None:
        pos = GridPosition()
        with pytest.raises(ValidationError):
            pos.x = 5  # type: ignore[misc]

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            GridPosition(extra_field="bad")  # type: ignore[call-arg]


class TestTimeRange:
    def test_default_preset(self) -> None:
        tr = TimeRange()
        assert tr.preset == TimeRangePreset.ONE_HOUR

    def test_custom_preset(self) -> None:
        tr = TimeRange(
            preset=TimeRangePreset.CUSTOM,
            start="2024-01-01T00:00:00Z",
            end="2024-01-02T00:00:00Z",
        )
        assert tr.preset == TimeRangePreset.CUSTOM
        assert tr.start is not None

    def test_refresh_interval(self) -> None:
        tr = TimeRange(refresh_interval_seconds=30)
        assert tr.refresh_interval_seconds == 30


class TestThreshold:
    def test_basic_threshold(self) -> None:
        t = Threshold(value=90.0, color=ThresholdColor.RED)
        assert t.value == 90.0
        assert t.color == ThresholdColor.RED

    def test_with_label(self) -> None:
        t = Threshold(value=50.0, color=ThresholdColor.YELLOW, label="Warning")
        assert t.label == "Warning"


class TestDatasourceRef:
    def test_prometheus_datasource(self) -> None:
        ds = DatasourceRef(type=DatasourceType.PROMETHEUS)
        assert ds.type == DatasourceType.PROMETHEUS
        assert ds.uid is None

    def test_cloud_monitoring_with_project(self) -> None:
        ds = DatasourceRef(
            type=DatasourceType.CLOUD_MONITORING,
            project_id="my-project",
        )
        assert ds.project_id == "my-project"


class TestQueryModels:
    def test_prometheus_query(self) -> None:
        q = PrometheusQuery(expr="rate(http_requests_total[5m])")
        assert q.expr == "rate(http_requests_total[5m])"

    def test_cloud_monitoring_query(self) -> None:
        q = CloudMonitoringQuery(
            filter_str='metric.type="compute.googleapis.com/instance/cpu/utilization"',
        )
        assert (
            q.filter_str.startswith("compute.googleapis.com")
            or "compute.googleapis.com" in q.filter_str
        )

    def test_logs_query(self) -> None:
        q = LogsQuery(filter_str='severity="ERROR"')
        assert q.filter_str == 'severity="ERROR"'

    def test_bigquery_query(self) -> None:
        q = BigQueryQuery(sql="SELECT * FROM dataset.table LIMIT 10")
        assert "SELECT" in q.sql

    def test_panel_query_with_prometheus(self) -> None:
        pq = PanelQuery(
            datasource=DatasourceRef(type=DatasourceType.PROMETHEUS),
            prometheus=PrometheusQuery(expr="up"),
        )
        assert pq.prometheus is not None
        assert pq.datasource is not None


class TestPanel:
    def test_basic_panel(self) -> None:
        p = Panel(id="p1", title="Test Panel", type=PanelType.TIME_SERIES)
        assert p.id == "p1"
        assert p.type == PanelType.TIME_SERIES

    def test_text_panel(self) -> None:
        p = Panel(
            id="p2",
            title="Info",
            type=PanelType.TEXT,
            text_content=TextContent(content="# Hello"),
        )
        assert p.text_content is not None
        assert p.text_content.content == "# Hello"

    def test_panel_with_queries(self) -> None:
        p = Panel(
            id="p3",
            title="CPU",
            type=PanelType.TIME_SERIES,
            queries=[
                PanelQuery(
                    datasource=DatasourceRef(type=DatasourceType.PROMETHEUS),
                    prometheus=PrometheusQuery(expr="cpu_usage"),
                )
            ],
        )
        assert len(p.queries) == 1

    def test_panel_display_defaults(self) -> None:
        d = PanelDisplay()
        assert d.transparent is False


class TestDashboardVariable:
    def test_query_variable(self) -> None:
        v = DashboardVariable(
            name="region",
            type=VariableType.QUERY,
            query="label_values(up, region)",
        )
        assert v.name == "region"
        assert v.type == VariableType.QUERY

    def test_custom_variable_with_values(self) -> None:
        v = DashboardVariable(
            name="env",
            type=VariableType.CUSTOM,
            values=["prod", "staging", "dev"],
            default_value="prod",
        )
        assert len(v.values) == 3
        assert v.default_value == "prod"


class TestDashboardMetadata:
    def test_default_metadata(self) -> None:
        m = DashboardMetadata()
        assert m.version == 1
        assert m.starred is False
        assert m.tags == []

    def test_metadata_with_values(self) -> None:
        m = DashboardMetadata(
            created_by="user@example.com",
            version=3,
            tags=["sre", "production"],
            starred=True,
        )
        assert m.version == 3
        assert m.starred is True
        assert len(m.tags) == 2


class TestDashboard:
    def test_minimal_dashboard(self) -> None:
        d = Dashboard(
            id="d1",
            display_name="Test Dashboard",
        )
        assert d.id == "d1"
        assert d.source == DashboardSource.LOCAL
        assert d.grid_columns == 24
        assert d.panels == []

    def test_dashboard_with_panels(self) -> None:
        d = Dashboard(
            id="d2",
            display_name="Panels Dashboard",
            panels=[
                Panel(id="p1", title="Panel 1", type=PanelType.TIME_SERIES),
                Panel(id="p2", title="Panel 2", type=PanelType.GAUGE),
            ],
        )
        assert len(d.panels) == 2

    def test_dashboard_with_variables(self) -> None:
        d = Dashboard(
            id="d3",
            display_name="Variables Dashboard",
            variables=[
                DashboardVariable(name="region", type=VariableType.QUERY),
            ],
        )
        assert len(d.variables) == 1

    def test_dashboard_cloud_monitoring_source(self) -> None:
        d = Dashboard(
            id="d4",
            display_name="Cloud Dashboard",
            source=DashboardSource.CLOUD_MONITORING,
            project_id="my-project",
        )
        assert d.source == DashboardSource.CLOUD_MONITORING

    def test_dashboard_frozen(self) -> None:
        d = Dashboard(id="d5", display_name="Frozen")
        with pytest.raises(ValidationError):
            d.id = "changed"  # type: ignore[misc]

    def test_dashboard_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Dashboard(
                id="d6",
                display_name="Bad",
                unknown_field="value",  # type: ignore[call-arg]
            )


class TestRequestModels:
    def test_create_dashboard_request(self) -> None:
        req = CreateDashboardRequest(display_name="New Dashboard")
        assert req.display_name == "New Dashboard"
        assert req.panels == []

    def test_update_dashboard_request_partial(self) -> None:
        req = UpdateDashboardRequest(display_name="Updated Name")
        assert req.display_name == "Updated Name"
        assert req.description is None

    def test_dashboard_summary(self) -> None:
        s = DashboardSummary(
            id="s1",
            display_name="Summary",
            source=DashboardSource.LOCAL,
            panel_count=5,
        )
        assert s.panel_count == 5
