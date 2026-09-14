import { useState } from "react";
import { submitTextReport, confirmReport } from "../lib/api.js";

/*
 * The low-friction "time agent" input the PS asks for, text only in
 * this UI (voice capture via Web Speech API feeds into the same text
 * field client-side, not yet wired here). Shows the real confidence
 * score and every candidate, never just the top pick, so a reviewer can
 * see why the engine chose what it chose.
 */
export default function ReportIntake({ onApplied }) {
  const [text, setText] = useState("");
  const [reportDate, setReportDate] = useState("2026-01-29");
  const [reportedBy, setReportedBy] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) {
      setError("Enter a report first");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await submitTextReport({
        text,
        report_date: reportDate,
        reported_by: reportedBy || undefined,
      });
      setResult(res);
      if (res.applied) onApplied();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleManualConfirm(candidate) {
    setConfirming(true);
    setError(null);
    try {
      await confirmReport({
        task_id: candidate.task_id,
        actual_start: reportDate,
        actual_end: reportDate,
        percent_complete: 100,
        confidence: candidate.confidence,
        matched_by: "manual",
        source_text: text,
      });
      setResult({ ...result, applied: true, needs_review: false });
      onApplied();
    } catch (err) {
      setError(err.message);
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="report-text">Field report</label>
          <textarea
            id="report-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. spool erected on the 24 inch inlet line, done today"
          />
        </div>
        <div className="field">
          <label htmlFor="report-date">Date</label>
          <input
            id="report-date"
            type="date"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="reported-by">Reported by (optional)</label>
          <input
            id="reported-by"
            type="text"
            value={reportedBy}
            onChange={(e) => setReportedBy(e.target.value)}
            placeholder="Supervisor name"
          />
        </div>
        {error && <p className="error-note">{error}</p>}
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Linking…" : "Submit report"}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: 18 }}>
          {result.applied && (
            <div className="result-banner result-banner--applied">
              Linked to {result.best_match.task_id} at{" "}
              {(result.best_match.confidence * 100).toFixed(0)}% confidence, schedule updated.
            </div>
          )}
          {result.needs_review && (
            <div className="result-banner result-banner--review">
              Below auto-link threshold, needs manual confirmation.
            </div>
          )}
          {result.all_candidates.map((c) => (
            <div className="candidate-row" key={c.task_id}>
              <span>
                <span className="mono">{c.task_id}</span> {c.task_name}
              </span>
              <span style={{ display: "flex", alignItems: "center" }}>
                <span className="mono">{(c.confidence * 100).toFixed(0)}%</span>
                <span className="confidence-bar">
                  <span
                    className="confidence-bar__fill"
                    style={{ width: `${c.confidence * 100}%` }}
                  />
                </span>
                {result.needs_review && (
                  <button
                    className="btn"
                    style={{ marginLeft: 10, padding: "4px 10px", fontSize: 12 }}
                    onClick={() => handleManualConfirm(c)}
                    disabled={confirming}
                  >
                    Confirm
                  </button>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
