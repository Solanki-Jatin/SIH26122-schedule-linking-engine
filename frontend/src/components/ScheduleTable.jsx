/*
 * Dense, scannable table of every L5/L6 task and its computed CPM
 * state. This is the "what does the plan actually look like right now"
 * view, complementary to the Gantt bars.
 */
export default function ScheduleTable({ tasks }) {
  return (
    <table className="schedule-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Discipline</th>
          <th>Planned</th>
          <th>Actual</th>
          <th>% complete</th>
          <th>Float (d)</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((t) => (
          <tr
            key={t.task_id}
            className={[t.is_critical && "is-critical", t.is_at_risk && "is-at-risk"]
              .filter(Boolean)
              .join(" ")}
          >
            <td>
              <span className="mono">{t.task_id}</span> {t.name}
            </td>
            <td>{t.discipline.replace("_", " ")}</td>
            <td className="mono">{t.planned_start} - {t.planned_end}</td>
            <td className="mono">
              {t.actual_start ? `${t.actual_start} - ${t.actual_end}` : "—"}
            </td>
            <td className="mono">{t.percent_complete.toFixed(0)}%</td>
            <td className="mono">{t.total_float ?? "—"}</td>
            <td>
              {t.is_critical && <span className="badge badge--critical">critical</span>}{" "}
              {t.is_at_risk && <span className="badge badge--at-risk">at risk</span>}
              {!t.is_critical && !t.is_at_risk && (
                <span className="badge badge--ok">on track</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
