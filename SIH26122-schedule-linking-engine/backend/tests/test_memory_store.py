"""
Tests for the institutional memory store. Uses an in-memory SQLite DB
per test so nothing touches disk or leaks state between tests.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.layer5_memory.memory_store import InstitutionalMemory


def make_memory():
    return InstitutionalMemory(db_url="sqlite:///:memory:")


def test_empty_discipline_returns_none_not_zero():
    """No data must never be reported as a measured zero. This is the
    guardrail against fake-precision claims when the store is empty."""
    memory = make_memory()
    stats = memory.query_delay_by_discipline("piping")

    assert stats.sample_size == 0
    assert stats.avg_delay_days is None
    assert stats.max_delay_days is None
    assert stats.min_delay_days is None


def test_record_and_query_single_discipline():
    memory = make_memory()
    memory.record_event(
        project_id="PROJ-1",
        task_id="PIP-002",
        task_name="Erect Line 24 inch XX inlet spool",
        discipline="piping",
        planned_duration_days=4,
        actual_duration_days=7,
        confidence=0.72,
        matched_by="auto",
        source_text="spool erected on the 24 inch inlet line",
        closed_date=date(2026, 1, 30),
    )
    memory.record_event(
        project_id="PROJ-1",
        task_id="PIP-005",
        task_name="Erect Line 12 inch YY outlet spool",
        discipline="piping",
        planned_duration_days=3,
        actual_duration_days=3,
        confidence=0.81,
        matched_by="auto",
        source_text="12 inch outlet spool done on time",
        closed_date=date(2026, 2, 2),
    )

    stats = memory.query_delay_by_discipline("piping")
    assert stats.sample_size == 2
    assert stats.avg_delay_days == 1.5  # (3 + 0) / 2
    assert stats.max_delay_days == 3
    assert stats.min_delay_days == 0
    assert memory.event_count() == 2


def test_disciplines_do_not_bleed_into_each_other():
    memory = make_memory()
    memory.record_event(
        project_id="PROJ-1", task_id="PIP-002", task_name="x",
        discipline="piping", planned_duration_days=4, actual_duration_days=9,
        confidence=0.7, matched_by="auto", source_text="x",
        closed_date=date(2026, 1, 1),
    )
    memory.record_event(
        project_id="PROJ-1", task_id="CIV-001", task_name="y",
        discipline="civil", planned_duration_days=4, actual_duration_days=4,
        confidence=0.9, matched_by="manual", source_text="y",
        closed_date=date(2026, 1, 1),
    )

    piping_stats = memory.query_delay_by_discipline("piping")
    civil_stats = memory.query_delay_by_discipline("civil")

    assert piping_stats.sample_size == 1
    assert piping_stats.avg_delay_days == 5
    assert civil_stats.sample_size == 1
    assert civil_stats.avg_delay_days == 0


def test_all_disciplines_summary_covers_every_recorded_discipline():
    memory = make_memory()
    memory.record_event(
        project_id="PROJ-1", task_id="PIP-002", task_name="x",
        discipline="piping", planned_duration_days=4, actual_duration_days=5,
        confidence=0.7, matched_by="auto", source_text="x",
        closed_date=date(2026, 1, 1),
    )
    memory.record_event(
        project_id="PROJ-1", task_id="ELE-001", task_name="y",
        discipline="electrical", planned_duration_days=2, actual_duration_days=2,
        confidence=0.9, matched_by="manual", source_text="y",
        closed_date=date(2026, 1, 1),
    )

    summary = memory.all_disciplines_summary()
    disciplines_seen = {s.discipline for s in summary}
    assert disciplines_seen == {"piping", "electrical"}
