"""
Tests for the CPM engine against hand-calculable small graphs, so we can
actually claim 'tested' rather than 'looked right when we ran it once'.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.layer2_schedule_graph.cpm_engine import ScheduleGraph
from app.layer2_schedule_graph.models import DisciplineType, Task


def make_task(task_id, duration, predecessors=None):
    return Task(
        task_id=task_id,
        name=task_id,
        discipline=DisciplineType.CIVIL,
        duration_days=duration,
        planned_start=date(2026, 1, 1),
        planned_end=date(2026, 1, 1),
        predecessors=predecessors or [],
    )


def test_single_chain_critical_path():
    """A -> B -> C with no branching: all three are critical, total
    duration is the sum of durations."""
    tasks = [
        make_task("A", 3),
        make_task("B", 4, ["A"]),
        make_task("C", 2, ["B"]),
    ]
    graph = ScheduleGraph(tasks)
    graph.compute()

    assert graph.project_duration() == 9
    assert graph.critical_path() == ["A", "B", "C"]
    for t in tasks:
        assert t.total_float == 0


def test_parallel_paths_only_longer_one_critical():
    """A branches into B (long) and C (short), both feed into D.
    Only the longer path should be critical; the shorter one has float."""
    tasks = [
        make_task("A", 2),
        make_task("B", 10, ["A"]),
        make_task("C", 3, ["A"]),
        make_task("D", 1, ["B", "C"]),
    ]
    graph = ScheduleGraph(tasks)
    graph.compute()

    assert graph.project_duration() == 13  # A(2) + B(10) + D(1)
    critical = set(graph.critical_path())
    assert critical == {"A", "B", "D"}

    task_c = next(t for t in tasks if t.task_id == "C")
    assert task_c.total_float == 7  # 10 - 3, the slack B has over C
    assert task_c.is_critical is False


def test_cycle_raises_error():
    """A schedule graph with a cycle is not a valid DAG and should be
    rejected loudly, not silently produce wrong CPM results."""
    tasks = [
        make_task("A", 1, ["B"]),
        make_task("B", 1, ["A"]),
    ]
    try:
        ScheduleGraph(tasks)
        assert False, "expected ValueError for cyclic graph"
    except ValueError as e:
        assert "cycle" in str(e).lower()


def test_actual_duration_overrides_planned_for_completed_task():
    """Once a task has actual_start and actual_end set, CPM should use
    the actual duration instead of the planned duration."""
    tasks = [
        make_task("A", 3),
        make_task("B", 4, ["A"]),
    ]
    task_a = tasks[0]
    task_a.actual_start = date(2026, 1, 1)
    task_a.actual_end = date(2026, 1, 8)  # actually took 7 days, not 3

    graph = ScheduleGraph(tasks)
    graph.compute()

    assert graph.project_duration() == 11  # 7 (actual A) + 4 (planned B)
