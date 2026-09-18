"""
Layer 2: Schedule Graph Model

Represents the baseline project schedule as a directed acyclic graph (DAG)
of L5/L6 activities. Each node is one executable activity. Edges represent
finish-to-start dependencies (extendable to other PMI relationship types
later if needed).

This module defines the data model only. CPM computation lives in
cpm_engine.py, kept separate so the model stays reusable across the
recompute engine (layer 4) and institutional memory (layer 5).
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class DisciplineType(str, Enum):
    CIVIL = "civil"
    PIPING = "piping"
    STATIC_EQUIPMENT = "static_equipment"
    ROTATING_EQUIPMENT = "rotating_equipment"
    ELECTRICAL = "electrical"
    INSTRUMENTATION = "instrumentation"
    HSE = "hse"


@dataclass
class Task:
    """
    A single L5/L6 activity node in the schedule DAG.

    task_id: stable identifier matching the Primavera/MS Project activity ID.
    name: plan description, e.g. 'Erect Line 24"-XX'.
    discipline: which reporting discipline owns this activity.
    duration_days: planned duration, used for forward/backward pass.
    planned_start / planned_end: baseline dates from the imported schedule.
    actual_start / actual_end: filled in as field data is linked and
        confirmed (layer 3 + layer 4). None until confirmed.
    percent_complete: 0-100, latest known actual progress.
    status: derived/set based on actual dates and percent_complete.
    predecessors: task_ids that must finish before this task starts
        (finish-to-start only in this PoC; documented as a known
        simplification, not a claimed full PMI relationship model).
    """

    task_id: str
    name: str
    discipline: DisciplineType
    duration_days: int
    planned_start: date
    planned_end: date
    predecessors: list[str] = field(default_factory=list)

    actual_start: date | None = None
    actual_end: date | None = None
    percent_complete: float = 0.0
    status: TaskStatus = TaskStatus.NOT_STARTED

    # CPM outputs, populated by cpm_engine.compute(). Not set at construction
    # time because they depend on the full graph, not just this node.
    early_start: int | None = None
    early_finish: int | None = None
    late_start: int | None = None
    late_finish: int | None = None
    total_float: int | None = None
    is_critical: bool | None = None

    def is_delayed(self) -> bool:
        """
        A task is delayed if its actual (or currently forecast) finish
        pushes past the planned finish. Used by layer 4 to flag at-risk
        downstream tasks. This is a definition, not a measured claim.
        """
        if self.actual_end is not None:
            return self.actual_end > self.planned_end
        return False
