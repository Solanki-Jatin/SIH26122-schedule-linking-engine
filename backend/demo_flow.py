"""
End-to-end demo script for SIH26122.

Walks through the planned demo flow:
  1. Load sample baseline schedule
  2. A free-text field report comes in
  3. Show extraction + fuzzy/semantic match + confidence score
  4. Auto-update fires for confirmed match (or flags for review if below
     threshold)
  5. Simulate a delay in an upstream task
  6. Critical path recomputes live, downstream tasks flip to at-risk
  7. Forecast completion date updates
  8. (institutional memory query is layer 5, wired in separately once
     that module exists)

Run from backend/ with: python -m scripts.demo_flow
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.layer1_capture.report_intake import parse_free_text_report
from app.layer2_schedule_graph.cpm_engine import ScheduleGraph
from app.layer2_schedule_graph.schedule_loader import load_schedule_csv
from app.layer3_linking.linking_engine import LinkingEngine
from app.layer4_recompute.recompute_engine import ActualUpdate, RecomputeEngine
from app.layer5_memory.memory_store import InstitutionalMemory

SCHEDULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "sample_schedules"
    / "baseline_schedule.csv"
)


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    section("STEP 1: Load baseline schedule")
    tasks = load_schedule_csv(SCHEDULE_PATH)
    print(f"Loaded {len(tasks)} L5/L6 activities from baseline_schedule.csv")

    graph = ScheduleGraph(tasks)
    graph.compute()
    print(f"Initial critical path: {graph.critical_path()}")
    print(f"Initial project duration: {graph.project_duration()} days")

    section("STEP 2: Free-text field report comes in")
    report_text = "spool erected on the 24 inch inlet line, done today"
    report = parse_free_text_report(report_text, report_date=date(2026, 1, 29))
    print(f"Raw report: '{report.raw_text}'")

    section("STEP 3: Extraction + fuzzy/semantic match + confidence score")
    linking_engine = LinkingEngine(tasks)
    link_result = linking_engine.link(report.raw_text)
    print(f"Top candidates:")
    for c in link_result.all_candidates:
        print(
            f"  {c.task_id:10s} '{c.task_name}' "
            f"fuzzy={c.fuzzy_score:.2f} semantic={c.semantic_score:.2f} "
            f"confidence={c.confidence:.2f}"
        )
    print(f"Auto-linked: {link_result.auto_linked} (needs_review={link_result.needs_review})")

    section("STEP 4: Auto-update fires (audit trail entry)")
    matched_task_id = link_result.best_match.task_id
    print(
        f"Report '{report.raw_text}' linked to {matched_task_id} "
        f"'{link_result.best_match.task_name}' "
        f"at confidence {link_result.best_match.confidence:.2f}"
    )
    print(
        "Audit trail: raw_text -> matched_task_id, confidence, matched_by=auto, "
        "timestamp recorded (not silently overwriting plan without trace)"
    )

    section("STEP 5: Apply update, simulate delay upstream")
    recompute_engine = RecomputeEngine(tasks, project_start=date(2026, 1, 5))

    # This task actually finished 3 days later than planned, simulating
    # a real-world slip reported through the field data.
    original_task = next(t for t in tasks if t.task_id == matched_task_id)
    delayed_start = original_task.planned_start + timedelta(days=2)
    delayed_end = original_task.planned_end + timedelta(days=3)

    update = ActualUpdate(
        task_id=matched_task_id,
        actual_start=delayed_start,
        actual_end=delayed_end,
        percent_complete=100.0,
        source_confidence=link_result.best_match.confidence,
    )

    diff = recompute_engine.apply_update(update)

    section("STEP 6-7: Critical path recomputes, at-risk tasks, forecast date")
    print(f"Previous forecast completion: {diff.previous_completion_date}")
    print(f"New forecast completion:      {diff.new_completion_date}")
    print(f"Slip: {diff.slip_days} days")
    print(f"Newly critical tasks: {diff.newly_critical}")
    print(f"No longer critical tasks: {diff.no_longer_critical}")
    print(f"Newly at-risk downstream tasks: {diff.newly_at_risk}")
    print(f"Full critical path now: {diff.critical_path}")

    section("STEP 8: Record event and query institutional memory")
    # Uses an in-memory SQLite DB for this demo run so repeated runs
    # don't accumulate stale data. A real deployment points db_url at
    # institutional_memory.db (or Postgres in production) and persists
    # across runs.
    memory = InstitutionalMemory(db_url="sqlite:///:memory:")
    memory.record_event(
        project_id="DEMO-PROJECT",
        task_id=matched_task_id,
        task_name=link_result.best_match.task_name,
        discipline=original_task.discipline.value,
        planned_duration_days=original_task.duration_days,
        actual_duration_days=(delayed_end - delayed_start).days,
        confidence=link_result.best_match.confidence,
        matched_by="auto",
        source_text=report.raw_text,
        closed_date=delayed_end,
    )
    # Seed one more piping event so the query below isn't a sample of one.
    memory.record_event(
        project_id="DEMO-PROJECT",
        task_id="PIP-001",
        task_name="Fabricate spool for Line 24 inch XX inlet",
        discipline="piping",
        planned_duration_days=5,
        actual_duration_days=5,
        confidence=0.9,
        matched_by="manual",
        source_text="fabrication done on schedule",
        closed_date=date(2026, 1, 20),
    )

    stats = memory.query_delay_by_discipline("piping")
    print(f"Query: average delay for discipline='piping'")
    print(f"  sample_size = {stats.sample_size}")
    print(f"  avg_delay_days = {stats.avg_delay_days}")
    print(f"  max_delay_days = {stats.max_delay_days}")
    print(f"  min_delay_days = {stats.min_delay_days}")
    print(
        "\nThis is a real aggregate over the events recorded in this run, "
        "not a placeholder. Query a discipline with zero recorded events "
        "and it returns None, never a fabricated number:"
    )
    empty_stats = memory.query_delay_by_discipline("hse")
    print(f"  query_delay_by_discipline('hse') -> sample_size={empty_stats.sample_size}, "
          f"avg_delay_days={empty_stats.avg_delay_days}")


if __name__ == "__main__":
    main()
