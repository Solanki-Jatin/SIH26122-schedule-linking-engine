"""
Loads a baseline schedule from CSV, simulating a Primavera/MS Project
export, into a list of Task objects for the schedule graph.

Real Primavera/MS Project exports (XER, XML, MPX) have more fields than
this. For the prototype we normalize to this CSV shape, which is one of
the 2-3 input formats the PS scope calls for. A production version would
add a dedicated XER/MPX parser as a separate loader in this same module,
converging to the same Task model.
"""

import csv
from datetime import date
from pathlib import Path

from .models import DisciplineType, Task


def load_schedule_csv(path: str | Path) -> list[Task]:
    tasks = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            predecessors = (
                [p for p in row["predecessors"].split(";") if p]
                if row.get("predecessors")
                else []
            )
            tasks.append(
                Task(
                    task_id=row["task_id"],
                    name=row["name"],
                    discipline=DisciplineType(row["discipline"]),
                    duration_days=int(row["duration_days"]),
                    planned_start=date.fromisoformat(row["planned_start"]),
                    planned_end=date.fromisoformat(row["planned_end"]),
                    predecessors=predecessors,
                )
            )
    return tasks
