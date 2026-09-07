"""
Tests for the layer 6 FastAPI routes. Uses TestClient against the real
app with the real (SQLite) institutional memory, no mocking, so a pass
here means the endpoints actually work end to end, not just that the
underlying layer functions do.

Note: these tests share app_state's SQLite file across the test session
(same as the real app), so tests that record events and query memory are
written to be independent of exact prior counts, they check "at least"
conditions rather than exact totals.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.layer6_api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_schedule_returns_all_tasks_with_cpm_values():
    resp = client.get("/schedule")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_duration_days"] > 0
    assert len(body["critical_path"]) > 0
    assert len(body["tasks"]) == 12  # matches baseline_schedule.csv
    # Every task must carry computed CPM fields, not nulls, once /schedule
    # has run compute() over the graph.
    for task in body["tasks"]:
        assert task["early_start"] is not None
        assert task["total_float"] is not None


def test_submit_text_report_links_and_may_auto_apply():
    resp = client.post(
        "/reports/text",
        json={
            "text": "spool erected on the 24 inch inlet line",
            "report_date": "2026-01-29",
            "reported_by": "Suresh",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["best_match"] is not None
    assert body["best_match"]["task_id"] == "PIP-002"
    assert body["auto_linked"] is True
    assert body["applied"] is True


def test_unrelated_text_report_is_flagged_not_applied():
    resp = client.post(
        "/reports/text",
        json={
            "text": "lunch order delivered to the site office",
            "report_date": "2026-01-29",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is True
    assert body["applied"] is False


def test_confirm_report_unknown_task_returns_404():
    resp = client.post(
        "/reports/confirm",
        json={
            "task_id": "NOT-A-REAL-TASK",
            "actual_start": "2026-01-01",
            "actual_end": "2026-01-02",
            "percent_complete": 100,
            "confidence": 0.9,
            "matched_by": "manual",
            "source_text": "test",
        },
    )
    assert resp.status_code == 404


def test_confirm_report_known_task_applies_and_returns_diff():
    resp = client.post(
        "/reports/confirm",
        json={
            "task_id": "ELE-001",
            "actual_start": "2026-01-20",
            "actual_end": "2026-01-24",
            "percent_complete": 100,
            "confidence": 1.0,
            "matched_by": "manual",
            "source_text": "manual confirmation in test",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "new_completion_date" in body
    assert "critical_path" in body


def test_memory_query_for_discipline_with_no_data_returns_none():
    resp = client.get("/memory/query", params={"discipline": "static_equipment"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discipline"] == "static_equipment"
    # Might be 0 if nothing recorded this discipline yet in this run.
    if body["sample_size"] == 0:
        assert body["avg_delay_days"] is None


def test_memory_summary_reflects_recorded_events():
    # By this point, prior tests in this module have recorded at least
    # one piping and one electrical event via confirm/text endpoints.
    resp = client.get("/memory/summary")
    assert resp.status_code == 200
    body = resp.json()
    disciplines = {s["discipline"] for s in body}
    assert "piping" in disciplines
    assert "electrical" in disciplines
