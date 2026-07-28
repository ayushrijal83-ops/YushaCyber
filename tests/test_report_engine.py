"""Tests for YC-031.3 — Universal Report Engine.

Covers: types, builder, models, templates, renderer, export,
services, and backward compatibility.
"""

from __future__ import annotations

import json
import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0313-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_report.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.report import (  # noqa: E402
    OutputFormat,
    Report,
    ReportBuilder,
    ReportKind,
    ReportSection,
    build_report,
    create_report,
    export_report,
    get_template,
    render_report,
    report_from_dict,
    report_from_state,
    report_summary,
    template_names,
)


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_report_kind_enum(self):
        assert ReportKind.INVESTIGATION.value == "investigation"
        assert ReportKind.BLUE_TEAM.value == "blue_team"

    def test_output_format_enum(self):
        assert OutputFormat.HTML.value == "html"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.JSON.value == "json"

    def test_report_to_dict(self):
        r = Report(title="Test", report_type="lab", score=85)
        d = r.to_dict()
        assert d["title"] == "Test"
        assert d["score"] == 85

    def test_section_to_dict(self):
        s = ReportSection(kind="findings", title="Findings",
                          content="Found malware.", order=1)
        d = s.to_dict()
        assert d["kind"] == "findings"
        assert d["content"] == "Found malware."

    def test_section_by_kind(self):
        r = Report(sections=[
            ReportSection(kind="timeline", title="TL"),
            ReportSection(kind="findings", title="F"),
        ])
        assert r.section_by_kind("findings").title == "F"
        assert r.section_by_kind("nonexistent") is None


# ===========================================================================
# Builder
# ===========================================================================
class TestBuilder:
    def test_fluent_build(self):
        report = (ReportBuilder("Investigation Report")
                  .set_type("investigation")
                  .set_student(1)
                  .set_scenario(42)
                  .add_executive_summary("A breach was detected.")
                  .add_timeline([{"at": "02:00", "event": "VPN login"}])
                  .add_evidence([{"ref": "dns-log"}])
                  .add_findings([{"finding": "C2 domain found"}])
                  .add_root_cause("Phishing led to credential theft.")
                  .add_mitre([{"technique_id": "T1059.001",
                               "technique_name": "PowerShell"}])
                  .add_containment("Isolated affected hosts.")
                  .add_recovery("Restored from backups.")
                  .add_recommendations(["Enable MFA", "Block C2"])
                  .set_score(85, "B", 200)
                  .build())
        assert report.title == "Investigation Report"
        assert report.report_type == "investigation"
        assert report.student_id == 1
        assert report.scenario_id == 42
        assert len(report.sections) == 9
        assert report.score == 85
        assert report.grade == "B"
        assert report.xp == 200
        assert len(report.mitre_mapping) == 1
        assert len(report.recommendations) == 2

    def test_empty_build(self):
        report = ReportBuilder().build()
        assert report.title == "Report"
        assert report.sections == []

    def test_appendix(self):
        report = (ReportBuilder("R")
                  .add_appendix("Raw logs here")
                  .build())
        assert report.section_by_kind("appendix") is not None


# ===========================================================================
# Models
# ===========================================================================
class TestModels:
    def test_report_from_dict(self):
        r = report_from_dict({
            "title": "Test Report",
            "report_type": "incident",
            "score": 90,
            "sections": [
                {"kind": "executive_summary", "title": "Summary",
                 "content": "Breach found.", "order": 1},
            ],
        })
        assert r.title == "Test Report"
        assert r.report_type == "incident"
        assert len(r.sections) == 1

    def test_report_from_state(self):
        state = {
            "report": "Executive summary of the investigation.",
            "ir_score": {"total": 75, "rating": "Good"},
            "hunt_mitre_mapped": ["T1059", "T1053"],
            "hunt_bookmarks": [{"ref": "b1", "label": "DNS"}],
            "forensics": {"case": {"timeline": [
                {"at": "02:00", "desc": "VPN login"},
            ]}},
        }
        r = report_from_state(state, "investigation", "SOC Report")
        assert r.title == "SOC Report"
        assert r.grade == "Good"
        assert r.score == 75
        assert len(r.mitre_mapping) == 2
        assert len(r.evidence) == 1
        assert len(r.timeline) == 1


# ===========================================================================
# Templates
# ===========================================================================
class TestTemplates:
    def test_get_investigation_template(self):
        t = get_template("investigation")
        assert "executive_summary" in t
        assert "timeline" in t
        assert "root_cause" in t
        assert "recommendations" in t

    def test_get_blue_team_template(self):
        t = get_template("blue_team")
        assert "mitre" in t
        assert "appendix" in t

    def test_fallback_to_lab(self):
        t = get_template("nonexistent_type")
        assert t == get_template("lab")

    def test_template_names(self):
        names = template_names()
        assert "investigation" in names
        assert "blue_team" in names
        assert len(names) >= 8


# ===========================================================================
# Renderer
# ===========================================================================
class TestRenderer:
    def _sample_report(self):
        return (ReportBuilder("Test Report")
                .set_type("investigation")
                .add_executive_summary("A breach occurred.")
                .add_findings([{"finding": "Malware detected"}])
                .add_recommendations(["Patch systems"])
                .set_score(80, "B")
                .build())

    def test_render_markdown(self):
        md = render_report(self._sample_report(), "markdown")
        assert "# Test Report" in md
        assert "## Executive Summary" in md
        assert "A breach occurred." in md
        assert "**Grade:** B" in md

    def test_render_html(self):
        html = render_report(self._sample_report(), "html")
        assert '<h1>Test Report</h1>' in html
        assert 'report-section--executive_summary' in html
        assert '&' not in html or '&amp;' in html  # escaped

    def test_render_json(self):
        j = render_report(self._sample_report(), "json")
        data = json.loads(j)
        assert data["title"] == "Test Report"
        assert data["score"] == 80
        assert len(data["sections"]) == 3


# ===========================================================================
# Export
# ===========================================================================
class TestExport:
    def _sample(self):
        return (ReportBuilder("Export Test")
                .add_executive_summary("Summary.")
                .build())

    def test_export_html(self):
        html = export_report(self._sample(), "html")
        assert "<article" in html

    def test_export_markdown(self):
        md = export_report(self._sample(), "markdown")
        assert "# Export Test" in md

    def test_export_json(self):
        j = export_report(self._sample(), "json")
        assert '"title": "Export Test"' in j


# ===========================================================================
# Services
# ===========================================================================
class TestServices:
    def test_create_report(self):
        r = create_report("My Report", "lab", student_id=1)
        assert r.title == "My Report"
        assert r.student_id == 1
        assert r.created_at != ""

    def test_build_report_returns_builder(self):
        b = build_report("IR Report", "investigation")
        assert isinstance(b, ReportBuilder)
        report = b.add_executive_summary("Test").build()
        assert report.report_type == "investigation"

    def test_report_summary(self):
        report = (ReportBuilder("Summary Test")
                  .add_executive_summary("S")
                  .add_findings([{"f": 1}, {"f": 2}])
                  .add_recommendations(["R1"])
                  .set_score(90, "A")
                  .build())
        s = report_summary(report)
        assert s["title"] == "Summary Test"
        assert s["grade"] == "A"
        assert s["sections"] == 3
        assert s["findings"] == 2
        assert s["recommendations"] == 1


# ===========================================================================
# Backward compatibility
# ===========================================================================
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        from app.labs.forensics.seed import seed_forensics_labs
        seed_forensics_labs()
    yield application


class TestBackwardCompat:
    def test_existing_soc_score_engine(self, app):
        with app.app_context():
            from app.simulators.soc.score_engine import compute_final_score
            decisions = [{"correct": True, "points": 10}] * 3
            score = compute_final_score(decisions, "Report text " * 20,
                                        3, hints_used=0)
            assert score["rating"] in ("Excellent", "Good",
                                       "Needs Improvement")

    def test_existing_hunt_scoring(self, app):
        with app.app_context():
            from app.simulators.soc.hunt_engine import score_hunt_report
            score = score_hunt_report("Executive summary. " * 10,
                                      3, 3, 3, hints_used=0)
            assert score["rating"] in ("Excellent", "Good",
                                       "Pass", "Fail")

    def test_report_from_state_with_real_data(self, app):
        with app.app_context():
            state = {
                "report": "Investigation complete.",
                "ir_score": {"total": 80, "rating": "Good"},
            }
            r = report_from_state(state)
            assert r.grade == "Good"
            assert r.score == 80
