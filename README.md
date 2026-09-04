# SIH26122 - Schedule-Linking Engine

**Intelligent Data Capture and Schedule-Linking Layer for Infrastructure Project Management: Real-Time Actual Progress Tracking**

| | |
|---|---|
| Problem Statement | SIH26122 |
| Organization | Oil India Limited |
| Event | Smart India Hackathon 2026 (Finals) |
| Team | Popeye |
| Status | Core pipeline (layers 1-5) built and tested. API layer and dashboard in progress. |

---

## Table of contents

- [Overview](#overview)
- [Problem statement summary](#problem-statement-summary)
- [System architecture](#system-architecture)
- [Tech stack](#tech-stack)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Running the demo](#running-the-demo)
- [Running tests](#running-tests)
- [Project status](#project-status)
- [Design and documentation standards](#design-and-documentation-standards)
- [Documentation](#documentation)
- [Team](#team)

---

## Overview

Infrastructure project schedules are planned top-down in Primavera or MS
Project down to L5/L6 executable activities. Actual execution data comes
back bottom-up through daily progress reports, discipline-wise
spreadsheets, and verbal supervisor updates, each in its own format and
vocabulary, disconnected from the plan's activity IDs. Reconciling the
two today is manual, slow, and inconsistent, and everything learned about
how a project actually ran is typically lost after project closure
instead of feeding future planning.

This system closes that loop. It captures actual progress in whatever
format it arrives in, links it back to the correct plan node even when
field wording or granularity differs from the plan, updates the schedule
with a confidence score and a full audit trail, and builds a queryable
record of how projects actually executed, for use in future project
planning.

## Problem statement summary

Oil India Limited's infrastructure projects span multiple disciplines
(civil, piping, static and rotating equipment, electrical,
instrumentation, HSE), each reporting progress independently and in
different formats. Field execution is often more granular than the plan,
and disciplines describe the same activity differently (for example,
"spool erected" against the plan's "Erect Line 24-inch XX inlet"). The
result is fragmented, delayed, and inconsistent actual progress data,
slow manual reconciliation, and poor downstream forecasting.

The expected solution ingests heterogeneous inputs, uses a
conversational or voice-based logging interface for low-friction
supervisor input, fuzzy-matches field descriptions to the correct L5/L6
plan node while flagging unmatched items for review rather than dropping
them, auto-updates actual dates with a confidence score and audit trail,
and builds a structured, queryable institutional memory of real
execution patterns.

## System architecture

Six layers. Layer 2 (the schedule graph and CPM engine) is shared state
referenced by layers 3 and 4, not a sequential pipeline stage.

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

| Layer | Responsibility | Status |
|---|---|---|
| 1. Data capture | Normalizes CSV/spreadsheet and free-text/voice field reports into a common shape | Built, tested |
| 2. Schedule graph model | DAG of L5/L6 activities, Critical Path Method (CPM) computation | Built, tested |
| 3. Linking engine | Fuzzy string match + TF-IDF semantic similarity, confidence-scored, never silently drops unmatched items | Built, tested |
| 4. Recompute engine | Applies confirmed updates, re-runs CPM, diffs critical path and at-risk tasks, computes new forecast completion | Built, tested |
| 5. Institutional memory | Structured, queryable store of confirmed execution events across projects | Built, tested |
| 6. API + dashboard | FastAPI routes and a React dashboard (Gantt, graph view, risk heatmap) | In progress |

Full technical detail, including the exact data model, API contracts,
and the reasoning behind each design choice, is in
[`docs/architecture.md`](docs/architecture.md).

## Tech stack

| Concern | Choice | Reasoning |
|---|---|---|
| Backend framework | Python, FastAPI | Async, fast to build, strong typing |
| Graph and CPM | networkx | Mature, exact algorithm, not a black box |
| Fuzzy matching | rapidfuzz | Fast, C-optimized Levenshtein family |
| Semantic matching | scikit-learn (TF-IDF) | No external model download needed at demo time, fully explainable |
| Database | SQLite (prototype/demo), PostgreSQL (production target) | Zero setup risk during judging, same SQLAlchemy schema, one-line connection string swap |
| Frontend | React | Team familiarity |
| Gantt view | frappe-gantt / dhtmlx-gantt | Off the shelf, no need to build a Gantt renderer from scratch |
| Graph view | vis.js / d3 | DAG visualization |
| Voice input (demo) | Browser Web Speech API | No ASR infrastructure needed for the prototype |

## Repository structure

```
backend/
  app/
    layer1_capture/          report intake (CSV, free-text)
    layer2_schedule_graph/   DAG model, CPM engine, schedule loader
    layer3_linking/          fuzzy + semantic linking engine
    layer4_recompute/        recompute + diff engine
    layer5_memory/           institutional memory store (SQLAlchemy)
    layer6_api/               FastAPI routes (in progress)
  data/
    sample_schedules/        sample baseline schedule CSV
    sample_reports/          sample field report inputs
  tests/                      pytest suite, 11/11 passing
  scripts/
    demo_flow.py              end-to-end runnable demo of the full pipeline
  requirements.txt
frontend/                     dashboard (in progress)
docs/
  architecture.md             full architecture spec, data model, API contracts
README.md
```

## Getting started

Requires Python 3.12+.

```bash
git clone https://github.com/<org>/SIH26122-schedule-linking-engine.git
cd SIH26122-schedule-linking-engine/backend
pip install -r requirements.txt
```

## Running the demo

Runs the full planned demo flow end to end: load baseline schedule, feed
in a free-text field report, extract and link it with a confidence
score, apply the update, recompute the critical path, flag downstream
at-risk tasks, and query institutional memory.

```bash
cd backend
python -m scripts.demo_flow
```

## Running tests

```bash
cd backend
python -m pytest tests/ -v
```

Current suite: 11 tests, all passing, covering CPM correctness (single
chains, parallel paths, cycle detection, actual-duration overrides),
linking engine behavior (correct matches, unmatched items flagged not
dropped, sorted candidates), and institutional memory (real aggregates,
disciplines isolated correctly, empty-store queries return `None` rather
than a fabricated number).

## Project status

Layers 1 through 5 are built, wired together, and covered by a passing
test suite. `backend/scripts/demo_flow.py` is a real, runnable
walkthrough of the core value proposition, not a mockup. Remaining work:
layer 6 (FastAPI routes per the contracts in `docs/architecture.md`),
the React dashboard, voice input wiring, and the demo video.

## Design and documentation standards

This repository follows a strict rule carried through every layer, every
test, and every document: no number is ever stated as a measured or
achieved result unless it came out of an actual run in this repo.
Confidence thresholds and scoring weights are documented as design
choices, not tuned or tested accuracy claims, until real pilot data
exists. Any citation in `docs/` links to a real, checkable source. This
applies equally to the PPT and the drive documentation built from this
codebase.

## Documentation

- [`docs/architecture.md`](docs/architecture.md): full architecture
  specification, layer-by-layer responsibilities, data model, API
  contracts, and the reasoning behind every technical decision.

## Team

**Popeye** - Smart India Hackathon 2026.
