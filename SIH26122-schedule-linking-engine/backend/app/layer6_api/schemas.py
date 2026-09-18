"""
Layer 6: API schemas.

Pydantic models matching the request/response contracts documented in
docs/architecture.md section 6. Kept in a separate module from routes so
the contract shape is easy to read and diff on its own.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class TextReportRequest(BaseModel):
    text: str
    report_date: date
    reported_by: str | None = None


class ConfirmReportRequest(BaseModel):
    task_id: str
    actual_start: date
    actual_end: date
    percent_complete: float
    confidence: float
    matched_by: Literal["auto", "manual"] = "manual"
    source_text: str = ""


class MatchCandidateResponse(BaseModel):
    task_id: str
    task_name: str
    fuzzy_score: float
    semantic_score: float
    confidence: float


class LinkResultResponse(BaseModel):
    report_text: str
    best_match: MatchCandidateResponse | None
    all_candidates: list[MatchCandidateResponse]
    auto_linked: bool
    needs_review: bool
    applied: bool  # True if auto_linked and the update was applied immediately


class RecomputeDiffResponse(BaseModel):
    project_start: date
    previous_completion_date: date
    new_completion_date: date
    slip_days: int
    newly_critical: list[str]
    no_longer_critical: list[str]
    newly_at_risk: list[str]
    critical_path: list[str]


class TaskStateResponse(BaseModel):
    task_id: str
    name: str
    discipline: str
    duration_days: int
    planned_start: date
    planned_end: date
    predecessors: list[str]
    actual_start: date | None
    actual_end: date | None
    percent_complete: float
    status: str
    early_start: int | None
    early_finish: int | None
    late_start: int | None
    late_finish: int | None
    total_float: int | None
    is_critical: bool | None
    is_at_risk: bool


class ScheduleStateResponse(BaseModel):
    project_start: date
    project_duration_days: int
    forecast_completion_date: date
    critical_path: list[str]
    tasks: list[TaskStateResponse]


class DisciplineDelayStatsResponse(BaseModel):
    discipline: str
    sample_size: int
    avg_delay_days: float | None
    max_delay_days: int | None
    min_delay_days: int | None
