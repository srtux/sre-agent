"""Perses-compatible Pydantic dashboard models for SRE Agent.

Provides a comprehensive set of models for defining, creating, and managing
dashboards with support for multiple datasource types including Prometheus,
Cloud Monitoring, BigQuery, and Loki.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DashboardSource(str, Enum):
    """Source of a dashboard definition."""

    LOCAL = "local"
    CLOUD_MONITORING = "cloud_monitoring"


class PanelType(str, Enum):
    """Supported panel visualization types."""

    TIME_SERIES = "time_series"
    GAUGE = "gauge"
    STAT = "stat"
    TABLE = "table"
    LOGS = "logs"
    TRACES = "traces"
    PIE = "pie"
    HEATMAP = "heatmap"
    BAR = "bar"
    TEXT = "text"
    ALERT_CHART = "alert_chart"
    SCORECARD = "scorecard"
    SCATTER = "scatter"
    TREEMAP = "treemap"
    ERROR_REPORTING = "error_reporting"
    INCIDENT_LIST = "incident_list"


class DatasourceType(str, Enum):
    """Supported datasource backends."""

    PROMETHEUS = "prometheus"
    CLOUD_MONITORING = "cloud_monitoring"
    LOKI = "loki"
    BIGQUERY = "bigquery"
    TEMPO = "tempo"


class VariableType(str, Enum):
    """Dashboard variable types."""

    QUERY = "query"
    CUSTOM = "custom"
    CONSTANT = "constant"
    INTERVAL = "interval"
    TEXTBOX = "textbox"


class TimeRangePreset(str, Enum):
    """Predefined time range presets."""

    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    THREE_HOURS = "3h"
    SIX_HOURS = "6h"
    TWELVE_HOURS = "12h"
    TWENTY_FOUR_HOURS = "24h"
    TWO_DAYS = "2d"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    CUSTOM = "custom"


class ThresholdColor(str, Enum):
    """Semantic colors for threshold visualization."""

    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    CRITICAL = "critical"


class PlotType(str, Enum):
    """Plot rendering types for time series panels."""

    LINE = "line"
    BAR = "bar"
    STACKED_BAR = "stacked_bar"
    AREA = "area"
    STACKED_AREA = "stacked_area"
    SCATTER = "scatter"


class AggregationType(str, Enum):
    """Aggregation functions for metric queries."""

    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


class TimeRange(BaseModel):
    """Time range specification with preset or custom bounds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    preset: TimeRangePreset = TimeRangePreset.ONE_HOUR
    start: datetime | None = None
    end: datetime | None = None
    refresh_interval_seconds: int | None = None


class Threshold(BaseModel):
    """Visual threshold marker for panels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float
    color: ThresholdColor = ThresholdColor.RED
    label: str | None = None


class GridPosition(BaseModel):
    """Grid layout position and size for a panel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: int = 0
    y: int = 0
    width: int = 12
    height: int = 4

    @field_validator("x", mode="before")
    @classmethod
    def validate_x(cls, v: Any) -> int:
        """Ensure x is non-negative."""
        if isinstance(v, (int, float)) and v < 0:
            raise ValueError("x must be >= 0")
        return int(v)

    @field_validator("y", mode="before")
    @classmethod
    def validate_y(cls, v: Any) -> int:
        """Ensure y is non-negative."""
        if isinstance(v, (int, float)) and v < 0:
            raise ValueError("y must be >= 0")
        return int(v)

    @field_validator("width", mode="before")
    @classmethod
    def validate_width(cls, v: Any) -> int:
        """Ensure width is between 1 and 24."""
        v = int(v)
        if v < 1 or v > 24:
            raise ValueError("width must be between 1 and 24")
        return v

    @field_validator("height", mode="before")
    @classmethod
    def validate_height(cls, v: Any) -> int:
        """Ensure height is at least 1."""
        v = int(v)
        if v < 1:
            raise ValueError("height must be >= 1")
        return v


class DatasourceRef(BaseModel):
    """Reference to a datasource backend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: DatasourceType
    uid: str | None = None
    project_id: str | None = None


# ---------------------------------------------------------------------------
# Query Models
# ---------------------------------------------------------------------------


class PrometheusQuery(BaseModel):
    """Prometheus / PromQL query specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expr: str
    legend_format: str | None = None
    step: str | None = None


class CloudMonitoringQuery(BaseModel):
    """Google Cloud Monitoring query specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter_str: str | None = None
    aggregation: AggregationType | None = None
    group_by_fields: list[str] | None = None
    mql_query: str | None = None
    promql_query: str | None = None


class LogsQuery(BaseModel):
    """Cloud Logging / Loki query specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter_str: str | None = None
    resource_type: str | None = None
    severity_levels: list[str] | None = None


class BigQueryQuery(BaseModel):
    """BigQuery SQL query specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sql: str
    project_id: str | None = None
    location: str | None = None


class PanelQuery(BaseModel):
    """Unified query wrapper supporting multiple datasource types."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    datasource: DatasourceRef | None = None
    prometheus: PrometheusQuery | None = None
    cloud_monitoring: CloudMonitoringQuery | None = None
    logs: LogsQuery | None = None
    bigquery: BigQueryQuery | None = None
    hidden: bool = False
    ref_id: str | None = None


# ---------------------------------------------------------------------------
# Panel Configuration
# ---------------------------------------------------------------------------


class AxisConfig(BaseModel):
    """Axis configuration for chart panels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str | None = None
    min_val: float | None = None
    max_val: float | None = None
    unit: str | None = None
    decimals: int | None = None
    log_base: int | None = None


class LegendConfig(BaseModel):
    """Legend display configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    visible: bool = True
    placement: str | None = None
    values: list[str] | None = None


class TooltipConfig(BaseModel):
    """Tooltip behavior configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: str | None = None
    sort: str | None = None


class PanelDisplay(BaseModel):
    """Panel display and styling options."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title_size: str | None = None
    transparent: bool = False
    description: str | None = None
    links: list[str] | None = None


class TextContent(BaseModel):
    """Content for text / markdown panels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content: str
    mode: str = "markdown"

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: Any) -> str:
        """Ensure mode is markdown or html."""
        if v not in ("markdown", "html"):
            raise ValueError("mode must be 'markdown' or 'html'")
        return str(v)


# ---------------------------------------------------------------------------
# Main Models
# ---------------------------------------------------------------------------


class Panel(BaseModel):
    """A single dashboard panel with queries and display settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str | None = None
    title: str
    type: PanelType
    description: str | None = None
    grid_position: GridPosition | None = None
    queries: list[PanelQuery] | None = None
    thresholds: list[Threshold] | None = None
    display: PanelDisplay | None = None
    text_content: TextContent | None = None
    datasource: DatasourceRef | None = None
    min_val: float | None = None
    max_val: float | None = None
    unit: str | None = None
    decimals: int | None = None
    color_scheme: str | None = None
    options: dict[str, Any] | None = None


class DashboardVariable(BaseModel):
    """Dashboard template variable for dynamic filtering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    type: VariableType
    label: str | None = None
    description: str | None = None
    datasource: DatasourceRef | None = None
    query: str | None = None
    values: list[str] | None = None
    default_value: str | None = None
    multi: bool = False
    include_all: bool = False
    refresh_on_time_change: bool = False
    hide: bool = False


class DashboardFilter(BaseModel):
    """Dashboard-level filter for narrowing displayed data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    value: str
    operator: str = "="
    label: str | None = None

    @field_validator("operator", mode="before")
    @classmethod
    def validate_operator(cls, v: Any) -> str:
        """Ensure operator is one of the supported comparison operators."""
        allowed = ("=", "!=", "=~", "!~")
        if v not in allowed:
            raise ValueError(f"operator must be one of {allowed}")
        return str(v)


class Annotation(BaseModel):
    """Dashboard annotation overlay for marking events on panels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    datasource: DatasourceRef | None = None
    expr: str | None = None
    color: str | None = None
    enabled: bool = True


class DashboardMetadata(BaseModel):
    """Metadata for dashboard provenance and organization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    version: int = 1
    tags: list[str] = []
    starred: bool = False
    folder: str | None = None


class Dashboard(BaseModel):
    """Complete dashboard definition, Perses-compatible."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str | None = None
    name: str | None = None
    display_name: str
    description: str | None = None
    source: DashboardSource = DashboardSource.LOCAL
    project_id: str | None = None
    panels: list[Panel] = []
    variables: list[DashboardVariable] | None = None
    filters: list[DashboardFilter] | None = None
    annotations: list[Annotation] | None = None
    time_range: TimeRange | None = None
    labels: dict[str, str] | None = None
    grid_columns: int = 24
    metadata: DashboardMetadata | None = None


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------


class CreateDashboardRequest(BaseModel):
    """Request payload for creating a new dashboard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str
    description: str | None = None
    panels: list[Panel] = []
    variables: list[DashboardVariable] | None = None
    filters: list[DashboardFilter] | None = None
    time_range: TimeRange | None = None
    labels: dict[str, str] | None = None
    project_id: str | None = None


class UpdateDashboardRequest(BaseModel):
    """Request payload for updating an existing dashboard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str | None = None
    description: str | None = None
    panels: list[Panel] | None = None
    variables: list[DashboardVariable] | None = None
    filters: list[DashboardFilter] | None = None
    time_range: TimeRange | None = None
    labels: dict[str, str] | None = None


class AddPanelRequest(BaseModel):
    """Request payload for adding a panel to an existing dashboard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    type: PanelType
    description: str | None = None
    grid_position: GridPosition | None = None
    queries: list[PanelQuery] | None = None
    thresholds: list[Threshold] | None = None
    datasource: DatasourceRef | None = None
    text_content: TextContent | None = None


class DashboardSummary(BaseModel):
    """Lightweight dashboard summary for list views."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    display_name: str
    description: str | None = None
    source: DashboardSource | None = None
    panel_count: int = 0
    metadata: DashboardMetadata | None = None
    labels: dict[str, str] | None = None


class DashboardListResponse(BaseModel):
    """Paginated response for dashboard listing endpoints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dashboards: list[DashboardSummary]
    total_count: int = 0
    next_page_token: str | None = None
