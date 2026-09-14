import { useState } from "react";
import { queryMemory } from "../lib/api.js";

const DISCIPLINES = [
  "civil",
  "piping",
  "static_equipment",
  "rotating_equipment",
  "electrical",
  "instrumentation",
  "hse",
];

/*
 * The layer 5 query surface: real aggregates over whatever has been
 * confirmed so far, and an honest "no data yet" state rather than a
 * fabricated number, matching memory_store.py's guarantee.
 */
export default function MemoryPanel() {
  const [discipline, setDiscipline] = useState("piping");
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleQuery() {
    setLoading(true);
    setError(null);
    try {
      const res = await queryMemory(discipline);
      setStats(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="field">
        <label htmlFor="discipline-select">Discipline</label>
        <select
          id="discipline-select"
          value={discipline}
          onChange={(e) => setDiscipline(e.target.value)}
        >
          {DISCIPLINES.map((d) => (
            <option key={d} value={d}>
              {d.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>
      <button className="btn" onClick={handleQuery} disabled={loading}>
        {loading ? "Querying…" : "Query average delay"}
      </button>
      {error && <p className="error-note">{error}</p>}

      {stats && stats.sample_size === 0 && (
        <p className="empty-note" style={{ marginTop: 14 }}>
          No confirmed events recorded yet for {discipline.replace("_", " ")}.
        </p>
      )}

      {stats && stats.sample_size > 0 && (
        <div className="stat-grid">
          <div className="stat">
            <div className="stat__value">{stats.avg_delay_days}</div>
            <div className="stat__label">avg delay (d)</div>
          </div>
          <div className="stat">
            <div className="stat__value">{stats.max_delay_days}</div>
            <div className="stat__label">max delay (d)</div>
          </div>
          <div className="stat">
            <div className="stat__value">{stats.sample_size}</div>
            <div className="stat__label">sample size</div>
          </div>
        </div>
      )}
    </div>
  );
}
