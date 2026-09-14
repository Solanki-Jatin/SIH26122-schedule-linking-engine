/*
 * One row per discipline, a bar split into critical / at-risk / on-track
 * segments by real task counts from the current schedule state. No
 * synthetic risk score, just what the CPM recompute actually flagged.
 */
export default function RiskHeatmap({ tasks }) {
  const disciplines = {};
  tasks.forEach((t) => {
    if (!disciplines[t.discipline]) {
      disciplines[t.discipline] = { total: 0, critical: 0, atRisk: 0 };
    }
    disciplines[t.discipline].total += 1;
    if (t.is_critical) disciplines[t.discipline].critical += 1;
    else if (t.is_at_risk) disciplines[t.discipline].atRisk += 1;
  });

  return (
    <div>
      {Object.entries(disciplines).map(([discipline, counts]) => {
        const onTrack = counts.total - counts.critical - counts.atRisk;
        return (
          <div className="heatmap-row" key={discipline}>
            <div className="heatmap-row__label">{discipline.replace("_", " ")}</div>
            <div className="heatmap-row__track">
              {counts.critical > 0 && (
                <div
                  className="heatmap-cell"
                  style={{
                    width: `${(counts.critical / counts.total) * 100}%`,
                    background: "var(--critical)",
                  }}
                  title={`${counts.critical} critical`}
                />
              )}
              {counts.atRisk > 0 && (
                <div
                  className="heatmap-cell"
                  style={{
                    width: `${(counts.atRisk / counts.total) * 100}%`,
                    background: "var(--at-risk)",
                  }}
                  title={`${counts.atRisk} at risk`}
                />
              )}
              {onTrack > 0 && (
                <div
                  className="heatmap-cell"
                  style={{
                    width: `${(onTrack / counts.total) * 100}%`,
                    background: "var(--on-track)",
                  }}
                  title={`${onTrack} on track`}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
