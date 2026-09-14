/*
 * Thin fetch wrapper over the layer 6 API. Kept as one module so every
 * component hits the backend through the same contract, matching
 * docs/architecture.md section 6.
 */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export function getSchedule() {
  return request("/schedule");
}

export function submitTextReport({ text, report_date, reported_by }) {
  return request("/reports/text", {
    method: "POST",
    body: JSON.stringify({ text, report_date, reported_by }),
  });
}

export function confirmReport(payload) {
  return request("/reports/confirm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function queryMemory(discipline) {
  return request(`/memory/query?discipline=${encodeURIComponent(discipline)}`);
}

export function getMemorySummary() {
  return request("/memory/summary");
}
