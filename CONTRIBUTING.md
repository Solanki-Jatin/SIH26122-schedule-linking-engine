# Contributing

Internal guide for the five of us working on this repo in parallel with SIH26099.

## Branching

- `main` stays deployable. Work on a branch per layer or feature:
  `layer5-memory`, `frontend-gantt`, `fix-linking-threshold`, etc.
- Open a PR into `main` even solo; it keeps a review trail before finals.

## Commit style

We use conventional prefixes, already consistent through the repo's history:

- `feat(layerN): ...` new functionality in a specific layer
- `fix: ...` bug fix
- `refactor: ...` no behavior change
- `test: ...` test additions or changes
- `docs: ...` README, architecture doc, diagrams
- `chore: ...` tooling, deps, repo structure

## Before opening a PR

```bash
cd backend && python -m pytest tests/ -v
cd frontend && npm run build
```

Both must pass clean. If you touch `docs/architecture.md`'s data model or
API contracts, update the corresponding code in the same PR, they should
never drift apart.

## Standards that apply to every contribution

These carry through code, docs, and any slide content pulled from this
repo, see `docs/architecture.md` section 7 for the full statement:

- No number is stated as measured/achieved unless it came out of an
  actual test or run in this repo. Otherwise, label it projected/target.
- Confidence thresholds and score weights are documented as design
  choices, not tuned accuracy claims, until real pilot data exists.
- Any citation added to docs links to a real, checkable source.
- Every schedule mutation goes through the recompute engine's audit
  trail (`InstitutionalMemory.record_event`), no silent overwrites.
