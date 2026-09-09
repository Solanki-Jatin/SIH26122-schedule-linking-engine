# Architecture: Popeye - SIH26122

## 1. Naming

**Repo name:** `SIH26122-schedule-linking-engine`
**Display name (PPT/docs):** Intelligent Data Capture & Schedule-Linking Layer
**One-line description:** A system that captures actual site progress from
whatever format it arrives in, links it back to the correct plan activity
even when wording or granularity differs, updates the schedule with a
confidence score and audit trail, and turns closed-out projects into a
queryable record for future planning.

**Team:** Popeye, 5 members, SIH 2026 finals.
**Problem Statement:** SIH26122, Oil India Limited.

## 2. Scope boundary (what this system is and is not)

This system is NOT:
- A replacement for Primavera/MS Project. It reads baseline schedules from
  them, it does not author baseline plans.
- A full OCR/ASR pipeline. The PS explicitly excludes production-grade
  OCR/ASR from the prototype scope; the demo covers 2-3 input formats.
- A predictive ML forecasting system. "At risk" and "forecast completion
  date" are CPM-computed, definitional outputs, not a trained prediction
  model. This distinction matters, it is is a common judge question and
  we should never claim ML forecasting we have not built.

This system IS:
- A linking and reconciliation layer between two things that already
  exist in every OIL project: the baseline plan and the scattered actual
  progress data that never cleanly maps back onto it.

## 3. High level architecture

```
Field data sources (reports, sheets, voice notes)
        |
        v
Layer 1: Data capture
        |
        v
Layer 3: Linking engine  <----- references -----  Layer 2: Schedule graph
        |                                          (baseline DAG + CPM engine)
        v                                                  ^
Layer 4: Recompute engine  ------ writes actuals back ------|
        |
        v
Layer 5: Institutional memory
        |
        v
Layer 6: API + dashboard
```

Layer 2 is drawn to the side deliberately. It is not a pipeline stage
data flows through once, it is the shared schedule state that layer 3
reads from (to know what plan nodes exist) and layer 4 both reads from
and writes back to (actual dates, recomputed CPM values) every time a
new update lands.

## 4. Layer definitions

### Layer 1: Data capture

**Responsibility:** normalize heterogeneous field inputs into one common
shape before anything downstream has to know what format it came from.

**Inputs (prototype covers these 2-3 formats, per PS scope):**
1. Structured CSV/spreadsheet export (discipline-wise progress sheet),
   already carries a task_id.
2. Free-text supervisor note (typed or voice-transcribed via browser
   Web Speech API), no task_id, needs linking.
3. (stretch, if time allows) a simplified Primavera/MS Project export
   parser, same CSV convergence point.

**Output:** `RawReport` - raw_text, report_date, reported_by,
known_task_id (nullable), percent_complete (nullable).

**Explicitly not doing:** entity extraction, discipline classification,
or any NLP beyond simple parsing. That is layer 3's job. Keeping this
boundary clean is what makes layer 3 independently testable.

### Layer 2: Schedule graph model (CPM engine)

**Responsibility:** represent the baseline plan as a DAG of L5/L6
activities and compute Critical Path Method values: early/late
start/finish, total float, critical path.

**Reused from:** graph-engine logic from NexusTrace (prior project),
this is the strongest existing technical asset going into this PS.

**Core data model:** `Task` (task_id, name, discipline, duration_days,
planned_start, planned_end, predecessors, actual_start, actual_end,
percent_complete, status) plus CPM-derived fields (early_start,
early_finish, late_start, late_finish, total_float, is_critical).

**Method:** standard CPM (Kelley & Walker, 1959), implemented on
networkx's topological sort. Effective duration for a task uses actual
duration if actual_start and actual_end are both confirmed, otherwise
falls back to planned duration. This is the mechanism that lets a real
field update change the computed critical path.

**Explicitly not doing:** full PMI relationship types (only
finish-to-start in this PoC, documented as a known simplification, not
hidden). Resource leveling is out of scope.

### Layer 3: Linking engine

**Responsibility:** given a `RawReport` with no known task_id, find the
correct L5/L6 plan node, even when the report uses different wording or
a different granularity than the plan ("spool erected" -> "Erect Line
24-inch XX inlet spool").

**Method:** combined score from two signals.
1. Token-level fuzzy string match (rapidfuzz, `token_sort_ratio`).
2. TF-IDF cosine similarity (scikit-learn) over plan task names, as the
   semantic-match component.

Combined into one confidence score (0.0-1.0), default weighting 0.4
fuzzy / 0.6 semantic. **This weighting is a design choice, not a
tuned/tested result**, to be validated once we have pilot data.

**Threshold behavior:** confidence >= 0.55 (design choice, tunable) auto
links. Below that, the report is never dropped, it is returned with
`needs_review=True` and the top-k candidates attached, for a human to
confirm. This directly satisfies the PS requirement to never silently
drop unmatched items.

**On SBERT (documented honestly for the PPT/doc):** the PS expects
handling of genuine wording/granularity mismatches, i.e. semantic
matching, not just lexical. SBERT (Reimers & Gurevych, 2019,
https://arxiv.org/abs/1908.10084) is the correct production upgrade for
this. The prototype uses TF-IDF cosine similarity instead of a live
SBERT model because SBERT requires pulling pretrained weights from a
model hub at runtime, which we cannot guarantee works in every judge or
demo environment. We are not claiming SBERT is running when it is not.

### Layer 4: Recompute engine

**Responsibility:** when a confirmed actual update lands, apply it to the
schedule graph, re-run CPM, and produce a diff against the prior state:
tasks that flipped onto/off the critical path, downstream tasks that
became at-risk, and the new forecast completion date.

**"At risk" definition (stated explicitly since judges will ask):** a
task is at risk if its currently computed early_finish (forecast, from
CPM) would land after its planned_end, and it is not yet complete. This
is a definition applied to a computed value, not a prediction model.

**Audit trail requirement:** every applied update records what raw text
produced it, which task_id it was matched to, the confidence score, and
whether the match was auto-accepted or manually confirmed. Nothing
overwrites the plan silently.

### Layer 5: Institutional memory

**Status: not yet built.** Responsibility: persist every confirmed
actual event (not just the current state, the full history) in a
structured, queryable store, so patterns can be queried after project
closure, e.g. "average delay for civil foundation work across past
projects," which is the piece meant to differentiate us from teams that
stop at "we updated the schedule."

**Shape:** table of confirmed events (task_id, task_name, discipline,
project_id, planned_duration_days, actual_duration_days, delay_days,
confidence, matched_by, source_text, recorded_at), queried via layer 6's
API. Built with SQLAlchemy against SQLite for the prototype/demo (zero
setup risk, single file, no service dependency during judging) with
PostgreSQL as the documented production target, same ORM models, only
the connection string changes. Delay figures reported from this layer
are always real aggregates over whatever data actually exists in the
store, never a placeholder number, and return an explicit "no data yet"
rather than a fabricated average when the store is empty.

### Layer 6: API + dashboard

**Status: not yet built.** FastAPI routes exposing: schedule state,
submit-report endpoint (triggers layer 1 -> 3 -> 4), recompute diff
endpoint, institutional memory query endpoint. React frontend consumes
these for Gantt view (frappe-gantt or dhtmlx-gantt), DAG/graph view
(vis.js or d3), and a risk heatmap over the current schedule.

## 5. Tech stack (final)

| Concern | Choice | Why |
|---|---|---|
| Backend framework | Python + FastAPI | async, fast to build, good typing |
| Graph + CPM | networkx | mature, exact algorithm, not a black box |
| Fuzzy match | rapidfuzz | fast, C-optimized Levenshtein family |
| Semantic match | scikit-learn TF-IDF | no external model download needed, explainable |
| Database | SQLite for prototype/demo, PostgreSQL for production | zero setup risk during judging, same SQLAlchemy schema, one-line connection string swap to Postgres later |
| Frontend | React | team familiarity |
| Gantt | frappe-gantt or dhtmlx-gantt | off the shelf, no need to build a Gantt renderer |
| Graph view | vis.js or d3 | DAG visualization |
| Voice input (demo only) | browser Web Speech API | no ASR infra needed for prototype |

## 6. API contracts (draft, layer 6 will implement)

```
POST /reports/csv
  body: CSV file matching layer 1 schema
  -> { linked: [...], flagged_for_review: [...] }

POST /reports/text
  body: { text: str, report_date: date, reported_by?: str }
  -> LinkResult (best_match, all_candidates, auto_linked, needs_review)

POST /reports/confirm
  body: { task_id: str, actual_start, actual_end, percent_complete }
  -> RecomputeDiff (previous/new completion date, newly_critical,
     newly_at_risk, critical_path)

GET /schedule
  -> current full schedule state with CPM values

GET /memory/query?discipline=piping&metric=avg_delay
  -> aggregate from layer 5, computed from real stored data only
```

## 7. Non-functional standards (carried from the working agreement)

- No number in any slide, doc, or demo narration is stated as a measured
  result unless it came out of an actual run in this repo. Everything
  else is labeled projected/target/design choice.
- Confidence threshold (0.55) and score weights (0.4/0.6) are design
  choices, defensible on their own logic, not claimed as tuned/tested
  accuracy.
- Any citation (SBERT paper, CPM method, any benchmark) links to a real,
  checkable source.
- Audit trail is non-negotiable: every auto-linked or manually confirmed
  update is traceable back to its raw source text and confidence score.

## 8. Build order (what's left)

1. Layer 5: institutional memory store + query logic (PostgreSQL schema,
   aggregate queries).
2. Layer 6: FastAPI routes wiring layers 1-5 together per the contracts
   above.
3. Frontend: Gantt + graph view + risk heatmap consuming the API.
4. Voice input wired into the free-text path via Web Speech API.
5. PPT content, using this document as the technical source of truth.
6. Demo video script, once the full pipeline is demoable through the UI.
