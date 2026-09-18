import { useEffect, useState, useCallback } from "react";
import { getSchedule } from "./lib/api.js";
import GanttChart from "./components/GanttChart.jsx";
import ScheduleTable from "./components/ScheduleTable.jsx";
import GraphView from "./components/GraphView.jsx";
import RiskHeatmap from "./components/RiskHeatmap.jsx";
import ReportIntake from "./components/ReportIntake.jsx";
import MemoryPanel from "./components/MemoryPanel.jsx";

export default function App() {
  const [schedule, setSchedule] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(() => {
    getSchedule()
      .then(setSchedule)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (error) {
    return (
      <div className="app">
        <p className="error-note">
          Could not reach the backend at the configured API URL: {error}. Confirm
          `uvicorn app.layer6_api.main:app --reload` is running in backend/.
        </p>
      </div>
    );
  }

  if (!schedule) {
    return (
      <div className="app">
        <p className="loading-note">Loading schedule…</p>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="topbar">
        <div>
          <div className="topbar__title">SIH26122 - Schedule-linking engine</div>
          <div className="topbar__subtitle">
            {schedule.tasks.length} L5/L6 activities · critical path length{" "}
            {schedule.critical_path.length}
          </div>
        </div>
        <div className="topbar__metric">
          <div className="topbar__metric-value">{schedule.forecast_completion_date}</div>
          <div className="topbar__metric-label">forecast completion</div>
        </div>
      </div>

      <div className="grid">
        <div>
          <div className="panel">
            <div className="panel__header">
              <span className="panel__title">Gantt view</span>
            </div>
            <div className="panel__body">
              <GanttChart tasks={schedule.tasks} />
            </div>
          </div>

          <div className="panel">
            <div className="panel__header">
              <span className="panel__title">Schedule</span>
            </div>
            <div className="panel__body" style={{ padding: 0 }}>
              <ScheduleTable tasks={schedule.tasks} />
            </div>
          </div>
        </div>

        <div>
          <div className="panel">
            <div className="panel__header">
              <span className="panel__title">Submit field report</span>
            </div>
            <div className="panel__body">
              <ReportIntake onApplied={refresh} />
            </div>
          </div>

          <div className="panel">
            <div className="panel__header">
              <span className="panel__title">Risk by discipline</span>
            </div>
            <div className="panel__body">
              <RiskHeatmap tasks={schedule.tasks} />
            </div>
          </div>

          <div className="panel">
            <div className="panel__header">
              <span className="panel__title">Institutional memory</span>
            </div>
            <div className="panel__body">
              <MemoryPanel />
            </div>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="panel__header">
          <span className="panel__title">Dependency graph</span>
        </div>
        <div className="panel__body" style={{ overflowX: "auto" }}>
          <GraphView tasks={schedule.tasks} />
        </div>
      </div>
    </div>
  );
}
