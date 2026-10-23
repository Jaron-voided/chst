# Project instructions

## Current phase: PLANNING
Change to IMPLEMENTATION only after I approve the plan and it's tagged plan-v1.

In PLANNING:
- For each design decision, give options, trade-offs, and a recommendation, then wait for my
  choice and record it in the decision log in DESIGN.md.
- Draft only the planning documents (DESIGN.md, FORMAT_SPEC.md, ACCEPTANCE.md, TODO.md) and fixtures/.
- Do not write implementation code. The one exception is the fixture-generation script in fixtures/.

## What this project is
A new, versioned container file format and a Rust library + CLI that implement it.
Design from the requirements in DESIGN.md. Do not adopt the layout of any existing
archive or container format; mention existing formats only to explain a trade-off.

## Fixtures are the independent test oracle
- The generator script in fixtures/ builds every fixture and its expected JSON directly from
  FORMAT_SPEC.md. Checksums and hashes come from an independent, widely used implementation
  (for example Python's hashlib or zlib), never from the Rust code.
- The script shares no code with the Rust implementation.
- Rust conformance tests read these fixtures and compare against their expected JSON.
  Never use the Rust code to generate fixtures or their expected values.

## Sources of truth (highest first)
1. FORMAT_SPEC.md  2. ACCEPTANCE.md  3. DESIGN.md (including the decision log)  4. TODO.md
If the code and the spec disagree, the spec wins. From plan-v1 on, if you think the spec is wrong,
log it under "Needs decision"; don't change it.

## Protected (from plan-v1 on, change only with my approval)
FORMAT_SPEC.md, ACCEPTANCE.md, fixtures/ (including the generator script), and every existing check in check.sh.
You may add new checks; changing or removing an existing one needs my approval.

## Implementation rules (IMPLEMENTATION phase only)
- Run everything in: [environment from Step 0.5].
- The first task in TODO.md is check.sh. It runs the check for every ID in ACCEPTANCE.md and reports
  PASS or FAIL for each. A missing check, a check that can't run, or a test filter matching zero tests
  reports FAIL. Most IDs will FAIL at first because the features don't exist yet; that's expected.
  The check.sh task is done when every ID is reported honestly, not when everything passes.
  When it's done, stop completely until I approve it.
- Then work one task at a time from TODO.md, respecting its dependencies. Commit when the task's
  checks pass; the commit message starts with the task ID.
- You may add implementation tasks needed to meet approved requirements. Never add features or expand scope.
- Never delete, skip, ignore, or loosen a test or check to make it pass. Placeholder or empty tests
  never count as passing.
- EVIDENCE.md is the only record of check results: one row per acceptance ID with status
  (pass / fail / not run), command, and commit. Never mark anything passing if its check didn't run.
- ./check.sh passing for every acceptance ID is the definition of done.
- Parse defensively: validate magic, version, lengths, and counts before allocating; use checked
  arithmetic; never panic on any input.
- Run extraction tests only inside temporary directories.
- Approved dependencies: [fill in from decision 12]. Anything else: propose it under "Needs decision".

## Stop and ask (log under "Needs decision" in PROGRESS.md, with options and a recommendation)
- The spec leaves a real product decision open.
- A new feature or any other scope change.
- Any change to the on-disk format or to a protected file.
- A dependency not on the approved list.
- The same failure after 3 fix attempts.
- Anything needing access outside this repo, or new permissions.
Then continue with other unblocked tasks. Stop when every acceptance ID passes or all remaining work is blocked.

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