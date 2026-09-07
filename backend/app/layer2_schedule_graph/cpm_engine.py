"""
Layer 2: Critical Path Method (CPM) engine.

Builds a networkx DAG from a list of Task objects and computes:
  - early start / early finish (forward pass)
  - late start / late finish (backward pass)
  - total float
  - critical path (tasks with zero float)

This is standard CPM (Kelley & Walker, 1959 method), implemented on top of
networkx's topological sort. Duration units are days, start of project is
day 0.

Design note: this engine is intentionally stateless with respect to actual
dates. It computes on planned durations by default, but layer 4
(recompute engine) calls it again after substituting actual/forecast
durations for confirmed tasks, which is how a delay propagates.
"""

import networkx as nx

from .models import Task


class ScheduleGraph:
    def __init__(self, tasks: list[Task]):
        self.tasks: dict[str, Task] = {t.task_id: t for t in tasks}
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        for task_id, task in self.tasks.items():
            self.graph.add_node(task_id)
        for task_id, task in self.tasks.items():
            for pred_id in task.predecessors:
                if pred_id not in self.tasks:
                    raise ValueError(
                        f"Task {task_id} references unknown predecessor {pred_id}"
                    )
                self.graph.add_edge(pred_id, task_id)

        if not nx.is_directed_acyclic_graph(self.graph):
            cycle = nx.find_cycle(self.graph)
            raise ValueError(f"Schedule graph has a cycle, not a valid DAG: {cycle}")

    def _duration(self, task_id: str) -> int:
        """
        Effective duration for CPM purposes. Uses actual duration if the
        task is confirmed complete (actual_start and actual_end both set),
        otherwise falls back to planned duration. This is what lets
        layer 4 feed in real field data and get a recomputed critical path.
        """
        task = self.tasks[task_id]
        if task.actual_start is not None and task.actual_end is not None:
            return (task.actual_end - task.actual_start).days
        return task.duration_days

    def compute(self) -> None:
        """
        Runs forward pass, backward pass, float, and critical path
        determination. Mutates the Task objects in place with the results.
        """
        order = list(nx.topological_sort(self.graph))

        # Forward pass: early start / early finish
        for task_id in order:
            preds = list(self.graph.predecessors(task_id))
            task = self.tasks[task_id]
            if not preds:
                task.early_start = 0
            else:
                task.early_start = max(
                    self.tasks[p].early_finish for p in preds
                )
            task.early_finish = task.early_start + self._duration(task_id)

        project_duration = max(t.early_finish for t in self.tasks.values())

        # Backward pass: late finish / late start
        for task_id in reversed(order):
            succs = list(self.graph.successors(task_id))
            task = self.tasks[task_id]
            if not succs:
                task.late_finish = project_duration
            else:
                task.late_finish = min(
                    self.tasks[s].late_start for s in succs
                )
            task.late_start = task.late_finish - self._duration(task_id)

        # Float and critical path
        for task in self.tasks.values():
            task.total_float = task.late_start - task.early_start
            task.is_critical = task.total_float == 0

    def critical_path(self) -> list[str]:
        """Returns task_ids on the critical path, in topological order."""
        order = list(nx.topological_sort(self.graph))
        return [tid for tid in order if self.tasks[tid].is_critical]

    def project_duration(self) -> int:
        return max(t.early_finish for t in self.tasks.values())

    def downstream_of(self, task_id: str) -> list[str]:
        """All tasks reachable from task_id, i.e. everything a delay here
        can potentially push. Used by layer 4 to scope which tasks to
        re-flag as at-risk without recomputing full CPM for a quick
        preview, though the demo path uses a full recompute for accuracy.
        """
        return list(nx.descendants(self.graph, task_id))
