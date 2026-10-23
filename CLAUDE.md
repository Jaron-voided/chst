# Project instructions

## Current phase: PLANNING
Change to IMPLEMENTATION only after I approve the plan and it's tagged plan-v1.

In PLANNING:
- For each design decision, give options, trade-offs, and a recommendation, then wait for my
  choice and record it in the decision log in DESIGN.md.
- Draft only the planning documents (DESIGN.md, FORMAT_SPEC.md, ACCEPTANCE.md, TODO.md,
  EVIDENCE.md) and fixtures/.
- Do not write implementation code. The one exception is the fixture generator in fixtures/gen/.
- Open items go in DESIGN.md §9 until plan-v1. From plan-v1 on, they go under "Needs decision"
  in PROGRESS.md.

## What this project is
A new, versioned container file format and a Rust library + CLI that implement it.
Design from the requirements in DESIGN.md. Do not adopt the layout of any existing
archive or container format; mention existing formats only to explain a trade-off.

## Fixtures are the independent test oracle
- The generator in fixtures/gen/ builds every fixture and its expected JSON directly from
  FORMAT_SPEC.md. It uses only the Python standard library (SHA-256 from hashlib), and
  writes its own Zstandard frames for Extended fixtures. Hashes never come from the Rust code.
- The generator shares no code with the Rust implementation, and never invokes or reads it.
- Conformance is checked by the CLI-based fixture comparisons in ACCEPTANCE.md. There is no
  separate cargo conformance suite. Never use the Rust code to generate fixtures or their
  expected values.

## Sources of truth (highest first)
This section and the next are the only definitions of precedence and protection. The other
documents refer here instead of restating them.
1. FORMAT_SPEC.md  2. ACCEPTANCE.md  3. DESIGN.md (including the decision log)  4. TODO.md
If the code and the spec disagree, the spec wins. From plan-v1 on, if you think the spec is wrong,
log it under "Needs decision"; don't change it.

## Protected (from plan-v1 on, change only with my approval)
FORMAT_SPEC.md, ACCEPTANCE.md, DESIGN.md, fixtures/ (including fixtures/gen/), and every existing check in check.sh.
DESIGN.md may be edited only to record decisions I've approved. It holds the approved dependency
list (D15) and the environment pins (D16), so they can't change without me.
From checks-v1 on, also the helper scripts in tools/acceptance/ and .github/workflows/check.yml.
You may add new checks; changing or removing an existing one needs my approval.

## Implementation rules (IMPLEMENTATION phase only)
- Run everything in the pinned environment of DESIGN.md D16. Locally that's Linux (WSL), run
  from the Linux filesystem. macOS and Windows run only in CI.
- Always call Python as `python3.14`. The system `python3` is 3.12, which is below the spec's
  Unicode minimum.
- I create the GitHub repository and push. You may use `gh` read-only to check CI runs.
- The first tasks in TODO.md are check.sh with its helper scripts, then the CI workflow file
  (.github/workflows/check.yml). check.sh runs the check for every ID in ACCEPTANCE.md and reports
  exactly the statuses ACCEPTANCE.md §1.1 defines: PASS, FAIL, NOT RUN or N/A. A missing check, a
  check that can't run, or one that ran zero tests reports FAIL. NOT RUN means a mode wasn't
  selected. check.sh never decides N/A on its own. Most IDs will FAIL at first because the
  features don't exist yet; that's expected. These tasks are done when every ID is reported
  honestly, not when everything passes. When they're done, stop completely until I approve
  them at checks-v1.
- Then work one task at a time from TODO.md, respecting its dependencies. Commit when the task's
  checks pass; the commit message starts with the task ID.
- You may add implementation tasks needed to meet approved requirements. Never add features or expand scope.
- Never delete, skip, ignore, or loosen a test or check to make it pass. Placeholder or empty tests
  never count as passing.
- EVIDENCE.md is the only record of check results: one row per acceptance ID, with a status for
  each OS (PASS / FAIL / NOT RUN / N/A), the command, the commit, and the CI run link. macOS and
  Windows statuses come only from the linked CI run. Never mark anything passing if its check
  didn't run.
- The definition of done is ACCEPTANCE.md §2, and only there.
- Parse defensively: validate magic, version, lengths, and counts before allocating; use checked
  arithmetic; never panic on any input.
- Unsafe code (DESIGN.md D18):
  - chst-fs uses `#![deny(unsafe_code)]`, and only its Windows module (which calls windows-sys) is
    allowed unsafe code.
  - Every other crate uses `#![forbid(unsafe_code)]`, with two exceptions: the test-only file
    crates/chst-format/tests/support/counting_alloc.rs (the counting allocator), and the fuzz crate
    if fuzz_target! trips the unsafe lint.
  - Every unsafe block has a `// SAFETY:` comment explaining why it's sound.
- Every check and test creates its own fresh temporary directory and removes it afterward.
  Run extraction tests only inside temporary directories.
- Approved dependencies: the list in DESIGN.md D15. Anything else: propose it under "Needs decision".
  Cargo.lock is committed, so every dependency version is pinned.

## Stop and ask (log under "Needs decision" in PROGRESS.md, with options and a recommendation)
- The spec leaves a real product decision open.
- A new feature or any other scope change.
- Any change to the on-disk format or to a protected file.
- Moving a check to another OS, changing a per-OS variant, or changing CURRENT_CUT in ACCEPTANCE.md.
- A dependency not on the approved list, or a change to an environment pin.
- The same failure after 3 fix attempts.
- Anything needing access outside this repo, or new permissions. Read-only `gh` for CI runs is
  already allowed.
Then continue with other unblocked tasks. Stop when the definition of done (ACCEPTANCE.md §2) is met or all
remaining work is blocked.

## Progress log (PROGRESS.md)
- After each task, append: task ID, what changed, commit, open issues, and the acceptance IDs it
  affected. Point to EVIDENCE.md for results; don't repeat them here.
- When a check fails, record what failed, how you found the cause, and the fix. Record only failures
  that actually happened; never create one for the record.
- If a session ends with work unfinished, leave it unchecked in TODO.md and note where you stopped.
- If your context was reset, re-read this file, PROGRESS.md, TODO.md, and EVIDENCE.md before doing anything else.

## Final report
When I ask for it at the end, write FINAL_REPORT.md. It ends with a retrospective built from
PROGRESS.md and EVIDENCE.md: the decisions I made, what you completed on your own, the real failures
verification caught and how you fixed them, where you needed my judgment, and what the independent
reviewer and the second-language reader found.