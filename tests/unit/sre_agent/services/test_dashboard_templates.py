"""Tests for dashboard templates module."""

from sre_agent.services.dashboard_templates import (
    get_template,
    get_template_ids,
    list_templates,
)


class TestListTemplates:
    def test_returns_four_templates(self) -> None:
        templates = list_templates()
        assert len(templates) == 4

    def test_each_template_has_required_fields(self) -> None:
        templates = list_templates()
        for t in templates:
            assert "id" in t
            assert "display_name" in t
            assert "description" in t
            assert "service" in t
            assert "panel_count" in t
            assert "labels" in t

    def test_template_ids_match_expected_services(self) -> None:
        ids = {t["id"] for t in list_templates()}
        assert ids == {
            "ootb-gke",
            "ootb-cloud-run",
            "ootb-bigquery",
            "ootb-vertex-agent-engine",
        }

    def test_all_templates_have_panels(self) -> None:
        for t in list_templates():
            assert t["panel_count"] > 0, f"Template {t['id']} has no panels"


class TestGetTemplate:
    def test_gke_template_has_panels(self) -> None:
        template = get_template("ootb-gke")
        assert template is not None
        assert len(template["panels"]) > 0
        assert template["display_name"] == "GKE Overview"
        assert template["service"] == "gke"

    def test_cloud_run_template_has_panels(self) -> None:
        template = get_template("ootb-cloud-run")
        assert template is not None
        assert len(template["panels"]) > 0
        assert template["display_name"] == "Cloud Run Overview"
        assert template["service"] == "cloud_run"

    def test_bigquery_template_has_panels(self) -> None:
        template = get_template("ootb-bigquery")
        assert template is not None
        assert len(template["panels"]) > 0
        assert template["display_name"] == "BigQuery Overview"
        assert template["service"] == "bigquery"

    def test_vertex_agent_engine_template_has_panels(self) -> None:
        template = get_template("ootb-vertex-agent-engine")
        assert template is not None
        assert len(template["panels"]) > 0
        assert template["display_name"] == "Vertex Agent Engine Overview"
        assert template["service"] == "vertex_agent_engine"

    def test_nonexistent_template_returns_none(self) -> None:
        result = get_template("nonexistent")
        assert result is None

    def test_each_template_has_metrics_logs_traces(self) -> None:
        """Every OOTB template must include metric, log, and trace panels."""
        for template_id in get_template_ids():
            template = get_template(template_id)
            assert template is not None, f"Template {template_id} not found"

            panel_types = {p["type"] for p in template["panels"]}
            assert "time_series" in panel_types or "gauge" in panel_types, (
                f"Template {template_id} missing metric panels"
            )
            assert "logs" in panel_types, f"Template {template_id} missing log panels"
            assert "traces" in panel_types, (
                f"Template {template_id} missing trace panels"
            )

    def test_panels_have_queries(self) -> None:
        """Non-text panels should have query definitions."""
        for template_id in get_template_ids():
            template = get_template(template_id)
            assert template is not None
            for panel in template["panels"]:
                if panel["type"] != "text":
                    assert "queries" in panel, (
                        f"Panel '{panel['title']}' in {template_id} missing queries"
                    )
                    assert len(panel["queries"]) > 0

    def test_panels_have_grid_positions(self) -> None:
        """All panels should have grid_position."""
        for template_id in get_template_ids():
            template = get_template(template_id)
            assert template is not None
            for panel in template["panels"]:
                assert "grid_position" in panel, (
                    f"Panel '{panel['title']}' in {template_id} missing grid_position"
                )
                pos = panel["grid_position"]
                assert "x" in pos
                assert "y" in pos
                assert "width" in pos
                assert "height" in pos

    def test_metric_panels_have_filter_str(self) -> None:
        """Metric panels should have filter_str in their queries."""
        for template_id in get_template_ids():
            template = get_template(template_id)
            assert template is not None
            for panel in template["panels"]:
                if panel["type"] in ("time_series", "gauge", "stat"):
                    for query in panel.get("queries", []):
                        cm = query.get("cloud_monitoring", {})
                        assert "filter_str" in cm, (
                            f"Metric panel '{panel['title']}' in "
                            f"{template_id} missing filter_str"
                        )


class TestGetTemplateIds:
    def test_returns_four_ids(self) -> None:
        ids = get_template_ids()
        assert len(ids) == 4

    def test_ids_are_strings(self) -> None:
        for tid in get_template_ids():
            assert isinstance(tid, str)

    def test_all_ids_resolve_to_templates(self) -> None:
        for tid in get_template_ids():
            assert get_template(tid) is not None
