"""
Layer 6: application state.

Wires up layers 2-5 once at startup: loads the baseline schedule, builds
the linking engine over it, and creates the recompute engine and
institutional memory store. Kept as a single module-level object rather
than a database-backed session store because this is a hackathon
prototype serving one demo schedule at a time, not a multi-tenant
production service. Swapping this for per-project state is the natural
next step, noted in docs/architecture.md, not hidden.
"""

from datetime import date
from pathlib import Path

from app.layer2_schedule_graph.cpm_engine import ScheduleGraph
from app.layer2_schedule_graph.schedule_loader import load_schedule_csv
from app.layer3_linking.linking_engine import LinkingEngine
from app.layer4_recompute.recompute_engine import RecomputeEngine
from app.layer5_memory.memory_store import InstitutionalMemory

SCHEDULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "sample_schedules"
    / "baseline_schedule.csv"
)
PROJECT_START = date(2026, 1, 5)


class AppState:
    def __init__(self):
        self.tasks = load_schedule_csv(SCHEDULE_PATH)
        self.linking_engine = LinkingEngine(self.tasks)
        self.recompute_engine = RecomputeEngine(self.tasks, project_start=PROJECT_START)
        self.memory = InstitutionalMemory(db_url="sqlite:///institutional_memory.db")

    def current_schedule_graph(self) -> ScheduleGraph:
        """
        Recomputes CPM fresh over the current task states every call.
        Cheap for a schedule this size, and guarantees GET /schedule
        always reflects the latest applied actuals rather than a stale
        cached graph.
        """
        graph = ScheduleGraph(self.tasks)
        graph.compute()
        return graph

    def task_by_id(self, task_id: str):
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None


app_state = AppState()
