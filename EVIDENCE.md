# Chst — Evidence Ledger

Each row records one claimed result. The format is defined in
[`ACCEPTANCE.md`](ACCEPTANCE.md) §2.1, and AC-XP-1 checks the rows mechanically.

- **macOS and Windows results come only from CI.** Every row that claims them MUST link the
  GitHub Actions run (`https://github.com/<owner>/<repo>/actions/runs/<id>`). The run's
  head commit must equal the row's commit.
- Local runs on the owner's Linux (WSL) machine may be recorded for Linux only, marked
  `run: local`. They never stand in for CI.
- Write OS cells exactly as `linux: PASS`, `macos: FAIL` and so on, because AC-XP-1 greps for them.
- Never edit or delete a row; add a new one. A FAIL is recorded as faithfully as a PASS.

## Results

| Date | Commit | Scope | CI run | Linux | macOS | Windows |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

_No results yet: no implementation or CI workflow exists. The first row comes from the
first CI run (DESIGN.md §10, early task 1), which also confirms runner feasibility
(ACCEPTANCE.md §1.2)._
