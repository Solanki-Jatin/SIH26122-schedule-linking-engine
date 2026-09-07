"""
Layer 6: FastAPI application.

Wires layers 1-5 together into the HTTP contract documented in
docs/architecture.md section 6. Routes are intentionally thin, all real
logic lives in the layer modules, this file only does request parsing,
calling the right engine, and shaping the response.

Run with:
    cd backend
    uvicorn app.layer6_api.main:app --reload
"""

from datetime import datetime
from io import StringIO

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.layer1_capture.report_intake import parse_csv_reports, parse_free_text_report
from app.layer4_recompute.recompute_engine import ActualUpdate

from .schemas import (
    ConfirmReportRequest,
    DisciplineDelayStatsResponse,
    LinkResultResponse,
    MatchCandidateResponse,
    RecomputeDiffResponse,
    ScheduleStateResponse,
    TaskStateResponse,
    TextReportRequest,
)
from .state import app_state

app = FastAPI(
    title="SIH26122 Schedule-Linking Engine API",
    description=(
        "Data capture, linking, recompute, and institutional memory "
        "for infrastructure project actual progress tracking."
    ),
    version="0.1.0",
)

# Permissive CORS for the demo/dev frontend. Tighten to a specific
# origin list before any real deployment, noted here rather than left
# as a silent gap.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schedule", response_model=ScheduleStateResponse)
def get_schedule():
    graph = app_state.current_schedule_graph()
    tasks_out = []
    for task in app_state.tasks:
        tasks_out.append(
            TaskStateResponse(
                task_id=task.task_id,
                name=task.name,
                discipline=task.discipline.value,
                duration_days=task.duration_days,
                planned_start=task.planned_start,
                planned_end=task.planned_end,
                predecessors=task.predecessors,
                actual_start=task.actual_start,
                actual_end=task.actual_end,
                percent_complete=task.percent_complete,
                status=task.status.value,
                early_start=task.early_start,
                early_finish=task.early_finish,
                late_start=task.late_start,
                late_finish=task.late_finish,
                total_float=task.total_float,
                is_critical=task.is_critical,
                is_at_risk=app_state.recompute_engine.is_at_risk(task, graph),
            )
        )

    from datetime import timedelta

    forecast_completion = app_state.recompute_engine.project_start + timedelta(
        days=graph.project_duration()
    )

    return ScheduleStateResponse(
        project_start=app_state.recompute_engine.project_start,
        project_duration_days=graph.project_duration(),
        forecast_completion_date=forecast_completion,
        critical_path=graph.critical_path(),
        tasks=tasks_out,
    )


@app.post("/reports/text", response_model=LinkResultResponse)
def submit_text_report(payload: TextReportRequest):
    report = parse_free_text_report(
        payload.text, report_date=payload.report_date, reported_by=payload.reported_by
    )
    result = app_state.linking_engine.link(report.raw_text)

    applied = False
    if result.auto_linked and result.best_match is not None:
        _apply_and_record(
            task_id=result.best_match.task_id,
            actual_start=payload.report_date,
            actual_end=payload.report_date,
            percent_complete=100.0,
            confidence=result.best_match.confidence,
            matched_by="auto",
            source_text=report.raw_text,
        )
        applied = True

    return LinkResultResponse(
        report_text=result.report_text,
        best_match=(
            MatchCandidateResponse(**vars(result.best_match))
            if result.best_match
            else None
        ),
        all_candidates=[MatchCandidateResponse(**vars(c)) for c in result.all_candidates],
        auto_linked=result.auto_linked,
        needs_review=result.needs_review,
        applied=applied,
    )


@app.post("/reports/confirm", response_model=RecomputeDiffResponse)
def confirm_report(payload: ConfirmReportRequest):
    if app_state.task_by_id(payload.task_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id {payload.task_id}")

    diff = _apply_and_record(
        task_id=payload.task_id,
        actual_start=payload.actual_start,
        actual_end=payload.actual_end,
        percent_complete=payload.percent_complete,
        confidence=payload.confidence,
        matched_by=payload.matched_by,
        source_text=payload.source_text,
    )
    return RecomputeDiffResponse(**vars(diff))


@app.post("/reports/csv")
async def submit_csv_reports(file: UploadFile):
    content = (await file.read()).decode("utf-8")
    rows = parse_csv_reports(content)

    linked = []
    flagged_for_review = []
    for row in rows:
        if row.known_task_id and app_state.task_by_id(row.known_task_id):
            diff = _apply_and_record(
                task_id=row.known_task_id,
                actual_start=row.report_date,
                actual_end=row.report_date,
                percent_complete=row.percent_complete or 100.0,
                confidence=1.0,  # structured input with an explicit task_id, not fuzzy-matched
                matched_by="auto",
                source_text=row.raw_text,
            )
            linked.append({"task_id": row.known_task_id, "diff": vars(diff)})
        else:
            flagged_for_review.append({"raw_text": row.raw_text, "row": row.known_task_id})

    return {"linked": linked, "flagged_for_review": flagged_for_review}


@app.get("/memory/query", response_model=DisciplineDelayStatsResponse)
def query_memory(discipline: str):
    stats = app_state.memory.query_delay_by_discipline(discipline)
    return DisciplineDelayStatsResponse(**vars(stats))


@app.get("/memory/summary", response_model=list[DisciplineDelayStatsResponse])
def memory_summary():
    return [
        DisciplineDelayStatsResponse(**vars(s))
        for s in app_state.memory.all_disciplines_summary()
    ]


def _apply_and_record(
    task_id: str,
    actual_start,
    actual_end,
    percent_complete: float,
    confidence: float,
    matched_by: str,
    source_text: str,
):
    """
    Shared by /reports/text (auto path), /reports/confirm (manual path),
    and /reports/csv: applies the update via the recompute engine, then
    records the confirmed event into institutional memory. Keeping this
    in one place guarantees every path that changes the schedule also
    writes an audit-trail entry, none of them can silently skip it.
    """
    task = app_state.task_by_id(task_id)
    planned_duration = task.duration_days
    discipline = task.discipline.value

    update = ActualUpdate(
        task_id=task_id,
        actual_start=actual_start,
        actual_end=actual_end,
        percent_complete=percent_complete,
        source_confidence=confidence,
    )
    diff = app_state.recompute_engine.apply_update(update)

    actual_duration = (actual_end - actual_start).days
    app_state.memory.record_event(
        project_id="DEMO-PROJECT",
        task_id=task_id,
        task_name=task.name,
        discipline=discipline,
        planned_duration_days=planned_duration,
        actual_duration_days=actual_duration,
        confidence=confidence,
        matched_by=matched_by,
        source_text=source_text,
        closed_date=actual_end,
    )
    return diff
