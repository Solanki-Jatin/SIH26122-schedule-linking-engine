"""
Tests for the linking engine: exact-ish matches should score high and
auto-link, unrelated text should score low and be flagged for review
rather than silently dropped or wrongly matched.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.layer2_schedule_graph.models import DisciplineType, Task
from app.layer3_linking.linking_engine import LinkingEngine


def make_task(task_id, name):
    return Task(
        task_id=task_id,
        name=name,
        discipline=DisciplineType.PIPING,
        duration_days=1,
        planned_start=date(2026, 1, 1),
        planned_end=date(2026, 1, 2),
    )


def test_close_paraphrase_auto_links_to_correct_task():
    tasks = [
        make_task("PIP-002", "Erect Line 24 inch XX inlet spool"),
        make_task("CIV-001", "Excavate foundation pit for pump house"),
    ]
    engine = LinkingEngine(tasks)
    result = engine.link("spool erected on the 24 inch inlet line")

    assert result.auto_linked is True
    assert result.best_match.task_id == "PIP-002"


def test_unrelated_report_is_flagged_not_dropped():
    tasks = [
        make_task("PIP-002", "Erect Line 24 inch XX inlet spool"),
        make_task("CIV-001", "Excavate foundation pit for pump house"),
    ]
    engine = LinkingEngine(tasks)
    result = engine.link("completely unrelated text about lunch orders")

    # Regardless of confidence, the engine must never return a null/empty
    # result. It always surfaces a best guess plus a needs_review flag so
    # nothing is silently dropped, per the PS's explicit requirement.
    assert result.best_match is not None
    assert result.needs_review is True
    assert result.auto_linked is False


def test_all_candidates_returned_are_sorted_descending():
    tasks = [
        make_task("A", "Erect Line 24 inch XX inlet spool"),
        make_task("B", "Fabricate spool for Line 24 inch XX inlet"),
        make_task("C", "Excavate foundation pit for pump house"),
    ]
    engine = LinkingEngine(tasks)
    result = engine.link("spool erected 24 inch inlet", top_k=3)

    scores = [c.confidence for c in result.all_candidates]
    assert scores == sorted(scores, reverse=True)
