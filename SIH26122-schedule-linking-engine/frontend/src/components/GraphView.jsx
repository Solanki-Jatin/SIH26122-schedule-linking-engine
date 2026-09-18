import { scaleBand } from "d3";

/*
 * Renders the schedule as a dependency graph rather than a timeline.
 * Tasks are grouped into columns by their computed early_start (CPM
 * output), so the horizontal position reflects actual schedule logic,
 * not just a manual layout. Edges are drawn from every predecessor to
 * its successor, following the same DAG the CPM engine computed over.
 */
export default function GraphView({ tasks }) {
  const colWidth = 190;
  const rowHeight = 56;
  const nodeWidth = 160;
  const nodeHeight = 40;
  const margin = 40;

  const columns = {};
  tasks.forEach((t) => {
    const key = t.early_start ?? 0;
    if (!columns[key]) columns[key] = [];
    columns[key].push(t);
  });
  const sortedKeys = Object.keys(columns)
    .map(Number)
    .sort((a, b) => a - b);

  const xScale = scaleBand()
    .domain(sortedKeys.map(String))
    .range([margin, margin + sortedKeys.length * colWidth]);

  const positions = {};
  sortedKeys.forEach((key) => {
    columns[key].forEach((t, i) => {
      positions[t.task_id] = {
        x: xScale(String(key)),
        y: margin + i * rowHeight,
      };
    });
  });

  const maxRows = Math.max(...Object.values(columns).map((c) => c.length));
  const width = margin * 2 + sortedKeys.length * colWidth;
  const height = margin * 2 + maxRows * rowHeight;

  const statusColor = (t) =>
    t.is_critical ? "var(--critical)" : t.is_at_risk ? "var(--at-risk)" : "var(--accent)";

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Task dependency graph">
      <defs>
        <marker
          id="graph-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M2 1L8 5L2 9" fill="none" stroke="var(--border-strong)" strokeWidth="1.5" />
        </marker>
      </defs>

      {tasks.map((t) =>
        t.predecessors.map((predId) => {
          const from = positions[predId];
          const to = positions[t.task_id];
          if (!from || !to) return null;
          const x1 = from.x + nodeWidth;
          const y1 = from.y + nodeHeight / 2;
          const x2 = to.x;
          const y2 = to.y + nodeHeight / 2;
          const midX = (x1 + x2) / 2;
          return (
            <path
              key={`${predId}-${t.task_id}`}
              d={`M${x1},${y1} C${midX},${y1} ${midX},${y2} ${x2},${y2}`}
              fill="none"
              stroke="var(--border-strong)"
              strokeWidth="1"
              markerEnd="url(#graph-arrow)"
            />
          );
        })
      )}

      {tasks.map((t) => {
        const pos = positions[t.task_id];
        if (!pos) return null;
        return (
          <g key={t.task_id}>
            <rect
              x={pos.x}
              y={pos.y}
              width={nodeWidth}
              height={nodeHeight}
              rx="4"
              fill="var(--surface)"
              stroke={statusColor(t)}
              strokeWidth="1.5"
            />
            <text
              x={pos.x + 8}
              y={pos.y + 16}
              fontFamily="var(--font-mono)"
              fontSize="11"
              fill="var(--text-secondary)"
            >
              {t.task_id}
            </text>
            <text
              x={pos.x + 8}
              y={pos.y + 31}
              fontFamily="var(--font-sans)"
              fontSize="11"
              fill="var(--text-primary)"
            >
              {t.name.length > 22 ? t.name.slice(0, 22) + "…" : t.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
