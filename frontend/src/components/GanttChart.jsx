import { useEffect, useRef } from "react";
import Gantt from "frappe-gantt";
import "frappe-gantt/dist/frappe-gantt.css";

/*
 * Wraps frappe-gantt, the library named in docs/architecture.md's tech
 * stack table. Uses actual dates where confirmed, falling back to
 * planned dates otherwise, so the bar chart reflects real progress as
 * soon as a field report has been linked and applied.
 */
export default function GanttChart({ tasks }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || tasks.length === 0) return;

    const ganttTasks = tasks.map((t) => ({
      id: t.task_id,
      name: `${t.task_id} ${t.name}`,
      start: t.actual_start || t.planned_start,
      end: t.actual_end || t.planned_end,
      progress: t.percent_complete,
      dependencies: t.predecessors.join(","),
      custom_class: t.is_critical
        ? "bar-critical"
        : t.is_at_risk
        ? "bar-at-risk"
        : "",
    }));

    containerRef.current.innerHTML = "";
    new Gantt(containerRef.current, ganttTasks, {
      view_mode: "Day",
      date_format: "YYYY-MM-DD",
      readonly: true,
    });
  }, [tasks]);

  return <div className="gantt-container" ref={containerRef} />;
}
