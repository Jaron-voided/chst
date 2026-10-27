# Chst — TODO

> Status: **DRAFT, part of the plan for `plan-v1`.** Nothing here starts before the owner
> tags `plan-v1`. Precedence and protection are defined only in `CLAUDE.md`; this file
> ranks below FORMAT_SPEC.md, ACCEPTANCE.md and DESIGN.md, and never overrides them.

## How this file works

- Work one task at a time, in order, respecting **Depends**. A task may start only when
  every task it depends on is checked.
- **Checks** lists the acceptance IDs (ACCEPTANCE.md §3) that must report PASS on Linux,
  via `./check.sh --only <IDs>`, before the task is committed. An ID is listed under the
  task that completes it. Earlier tasks may make it pass partly, but a FAIL there doesn't
  block them.
- macOS and Windows statuses come only from CI (ACCEPTANCE.md §2.1). Where a task's IDs
  apply only to macOS or Windows, it's committed when the code builds and lints on Linux.
  Its IDs are then confirmed in the next CI run, and stay unchecked here until that run
  passes them.
- The commit message starts with the task ID. After each task: append to PROGRESS.md, and
  update EVIDENCE.md from `target/acceptance/report.json`.
- **Sub-tasks** are requirements on how a test is written. They interpret ACCEPTANCE.md
  and never relax it. Every sub-task must hold before its parent is checked.
- Anything that needs a decision goes under "Needs decision" in PROGRESS.md (`CLAUDE.md`),
  not here.

Gates, from DESIGN.md §10:

| Gate | Who | Unlocks |
|---|---|---|
| `plan-v1` tag | Owner | Phase H (harness) and CI |
| `checks-v1` approval | Owner | Phase C (Core) |
| `CURRENT_CUT = Extended` | Owner | Phase X (Extended) |

---

## Phase H: acceptance harness (DESIGN §10 checkpoint 5)

These tasks are done when every ID is reported honestly, not when everything passes. Most
IDs will FAIL here, because the features don't exist yet.

- [ ] **H-1 `check.sh` runner core**
  - Depends: `plan-v1`.
  - Builds:
    - the modes in ACCEPTANCE §1: fast, `--full`, `--only`, `--list-ids`;
    - the statuses and exit codes of §1.1;
    - `report.json` (schema `chst-acceptance/1`) and per-ID logs;
    - a fresh `$W` for every ID, removed afterwards;
    - `bash -euo pipefail`;
    - OS detection (`$CHST_OS`).
  - N/A comes only from the two facts in §1.1: `CURRENT_CUT`, read from ACCEPTANCE §2, and
    each ID's **OS** line. A missing check, a check that can't run, and a build failure all
    give FAIL.
  - It rejects any check script with a line starting `! ` (§1.2).
  - Checks: none on its own; H-3 and H-4 cover it.
- [ ] **H-2 Shared shell helpers**
  - Depends: H-1.
  - `tools/acceptance/`: `expect_exit`, `jqn`, `cargo_test_nonempty`, `sha256`,
    `mk_sparse`, `free_bytes`, `fixture_file`, and the `$CHST`, `$CHST_CORE`, `$FX`, `$GEN`,
    `$CHST_BIG_ROOT` and `$CHST_DET_SEED` conventions (§1.2).
  - `cargo_test_nonempty` sums the `N passed` counts and fails on 0, on no `test result:`
    line, or on a cargo failure.
  - Checks: none on its own; H-3 covers it.
- [ ] **H-3 `--self-test`**
  - Depends: H-2.
  - Builds a throwaway crate in a fresh temporary directory and runs the five `SELFTEST-*`
    IDs through the same code path as real IDs. They never appear in `--list-ids` or in
    normal reports.
  - Checks: AC-META-7.
- [ ] **H-4 One check script per acceptance ID**
  - Depends: H-2.
  - Each script is the ACCEPTANCE §3 script exactly as written. A script that is missing
    makes its ID FAIL.
  - Checks: AC-META-1, AC-META-2, AC-META-4, AC-META-5. The last three test only the
    fixtures, which already exist, so they should pass as soon as their scripts do.
- [ ] **H-5 Python helper scripts** (standard library only, run as `python3.14 -I`)
  - Depends: H-4.
  - [ ] `trace.py` (AC-META-3)
  - [ ] `spec_hexdump.py` (AC-META-6)
  - [ ] `inspect_check.py` (for AC-POS-3)
  - [ ] `tree_eq.py` (for AC-POS-4)
  - [ ] `flip_sweep.py` (for AC-ROB-1)
  - [ ] `truncate_sweep.py` (for AC-ROB-2)
  - Each one's pass and fail behaviour is exactly as its criterion describes. A helper that
    can't find its target reports FAIL.
  - Checks: AC-META-3, AC-META-6.
  - Re-check: AC-POS-3 and AC-ROB-1, AC-ROB-2 (owned by C-6), and AC-POS-4 (owned by
    C-14). Each must report FAIL here, because the CLI doesn't exist yet.
- [ ] **H-6 `--done` mode**
  - Depends: H-4.
  - Downloads the three `acceptance-report-<os>` reports with `gh` (read-only), imports each
    ID's per-OS status, then runs the done-only check. It exits 0 only if that check
    passes (§2).
  - Checks: none.
  - Re-check: AC-XP-1 (owned by C-20, the only place it can pass).
- [ ] **H-7 First honest local run**
  - Depends: H-1 … H-6.
  - Run `./check.sh` on Linux (WSL), from the Linux filesystem.
  - Fill every EVIDENCE.md Linux cell from `report.json`, with `local` in the CI column.
  - Record in PROGRESS.md which IDs pass.
  - Re-check: AC-META-1, AC-META-2, AC-META-3, AC-META-4, AC-META-5, AC-META-6, AC-META-7
    (owned by H-3, H-4 and H-5) should pass; most others FAIL.
- [ ] **CI-1 CI workflow** (`.github/workflows/check.yml`, D17)
  - Depends: H-7.
  - Triggers: `push`, `pull_request` and `workflow_dispatch`.
  - Runners: `ubuntu-latest`, `macos-latest` and `windows-latest`, all with `shell: bash`.
  - Fast mode (`run: ./check.sh`) on push and PR; `./check.sh --full` on manual trigger.
  - Job result:
    - fast mode: 0 or 2 succeeds;
    - full mode: 2 succeeds only when the done-only check is the sole NOT RUN;
    - 1 always fails.
  - Every runner gets:
    - a `python3.14` command (on Windows, a shim to the interpreter `setup-python` installs);
    - `jq` 1.7 or later;
    - the pinned toolchains (D16), plus the nightly and `cargo-fuzz` 0.13.2 `--locked` for
      full mode;
    - `$CHST_BIG_ROOT`.
  - On Ubuntu, free disk space first (§1.3).
  - Upload each report as `acceptance-report-<os>`.
  - In full mode on Windows, try cargo-fuzz once, as a non-gating, logged step (§1.3).
  - Checks: AC-XP-2.
  - The owner pushes. Claude reads the first run with `gh`, read-only, and records in
    PROGRESS.md what it showed for the open items in DESIGN §9g–§9i: runner feasibility,
    nightly components, and the Windows `FILE_SHARE_DELETE` behaviour (P4, once C-17 exists).

**STOP. `checks-v1`:** the owner reviews `check.sh`, the helper scripts and the workflow.
Nothing below starts before that approval.

---

## Phase C: Core implementation (DESIGN §10 checkpoint 7)

### Workspace and format crate

- [ ] **C-1 Workspace skeleton**
  - Depends: `checks-v1`.
  - `rust-toolchain.toml` (D16), the workspace, and `crates/chst-format`, `crates/chst-fs`
    and `crates/chst-cli` (binary `chst`).
  - `rust-version = "1.99"`, edition 2024, and a committed `Cargo.lock`.
  - Only D15 dependencies.
  - Lint headers per D18:
    - `forbid(unsafe_code)` everywhere;
    - in `chst-fs`: `deny`, plus the single `#[cfg(windows)] #[allow(unsafe_code)] mod
      windows;` and the SAFETY lints.
  - `chst-fs` has the non-default `test-hooks` feature (D13).
  - Extended Cargo features are added in Phase X. Until then, `$CHST` and `$CHST_CORE`
    build the same thing.
  - Checks: AC-ENG-1, AC-ENG-5, AC-ENG-6.
  - Re-check: AC-ENG-7 (owned by C-8). It can't pass yet, because the files it inspects
    don't exist until C-7 and C-8.
- [ ] **C-2 Header, trailer and structure hash** (§13 steps 1–8)
  - Depends: C-1.
  - Covers:
    - integer decoding (D3);
    - HDR-1 … HDR-6 and TRL-1 … TRL-3;
    - LIM-2 and LIM-4 before the index is read;
    - the error type with §16 categories and detail codes;
    - the configurable limits of §10.2 with their defaults.
  - All arithmetic is checked, and nothing is allocated before its size is validated (§10.3).
  - Checks: AC-ENG-2, AC-ENG-4.
- [ ] **C-3 Sections** (§13 step 9)
  - Depends: C-2.
  - SEC-1 … SEC-5, then LIM-3 before any per-entry allocation. Stop at HDR-6 and SEC-2
    (unsupported, never malformed).
- [ ] **C-4 Blobs, entries, paths and canonical form** (§13 step 10, the Core rules)
  - Depends: C-3.
  - Step 10 (a) … (p), in that exact order. FLG-1, ATT-1 and KV-1 apply only where the
    reader knows the flag, which a Core reader doesn't.
  - The PATH-2 NFC check uses `unicode-normalization` with Unicode 16.0 tables.
  - Checks: AC-ENG-8.
- [ ] **C-5 Step 11 and structured reports**
  - Depends: C-4.
  - Streaming BLB-6 per blob in table order, with bounded memory (G6).
  - List and inspect stop after step 10 (F34).
  - List, inspect and verify reports as library values (Appendix B, `chst-report/1`),
    including "what the reader implements shapes its report".

### CLI, read side

- [ ] **C-6 CLI: `list`, `inspect`, `verify`**
  - Depends: C-5.
  - `lexopt` parsing per Appendix C:
    - limit flags take ASCII digits only, with no sign, no whitespace, and no leading zeros
      (M12);
    - usage errors exit 2.
  - Text and `--json` output via `serde_json::Value`, and the category → exit code mapping
    (§16).
  - `list` text output escapes non-printing characters (PATH-6).
  - The CLI holds no format or safety logic (D13).
  - Checks:
    - AC-ENG-3;
    - AC-POS-2, AC-POS-3;
    - AC-NEG-1, AC-NEG-2, AC-NEG-3, AC-NEG-4;
    - AC-CLI-1, AC-CLI-3;
    - AC-COMPAT-1;
    - AC-LIM-3;
    - AC-ROB-1, AC-ROB-2, AC-ROB-8, AC-ROB-9.
- [ ] **C-7 Library robustness tests**
  - Depends: C-5.
  - `damage_sweep` (AC-ROB-3).
  - `hostile_sizes` with `tests/support/counting_alloc.rs` (D18 exception 1; the only
    `unsafe` outside `chst-fs::windows`, with SAFETY comments) (AC-LIM-1).
  - Checks: AC-ROB-3, AC-LIM-1.
  - Re-check: AC-ENG-7 (owned by C-8).
- [ ] **C-8 Fuzzing, and the unsafe-code audit**
  - Depends: C-7.
  - `fuzz/` with its own `rust-toolchain.toml` (the nightly pin) and `Cargo.lock`, and
    targets over `chst-format`.
  - `fuzz_regressions` test over `fixtures/fuzz-regressions/` (AC-ROB-5).
  - `random_sweep` for the Windows fallback.
  - If `fuzz_target!` trips `forbid(unsafe_code)`, commit the compiler error as
    `fuzz/FORBID_EXEMPTION.txt` (D18 exception 2). Never write `unsafe` by hand.
  - Any crash is minimised into `fixtures/fuzz-regressions/`. Changing `fixtures/` after
    `plan-v1` needs the owner's approval, so a crash is logged under "Needs decision" first.
  - Checks: AC-ROB-5, AC-ENG-7.
  - Re-check: AC-ROB-4 and AC-ROB-4W (owned by C-20). They're full-only, so a short local
    run here is only a smoke test.
  - AC-ENG-7 checks only the counting-allocator users that exist, so `zstd_bombs.rs` (X-1)
    isn't needed under the Core cut (DESIGN §9i, post-review edit).

### Writer and pack

- [ ] **C-9 Canonical writer** (`chst-format`)
  - Depends: C-5.
  - Covers:
    - §14 writer requirements: bytewise-sorted entries, dedup, and blobs in
      first-reference order (D2, D9);
    - `minor_version` 0;
    - the structure hash;
    - W-10: refuse to write anything its own verify would reject, with the limits checked
      in W-10's order.
  - Works over any byte sink.
- [ ] **C-10 Pack (Unix)**
  - Depends: C-9, C-6.
  - The walk never follows a link, and skips symlinks and special files with warnings (W-5).
  - Converts names to NFC and checks them, refusing the whole pack on any violation (W-3).
  - Hashes twice (W-4).
  - Writes to a temporary file next to the output, then renames it (G5, W-2, W-7).
  - `--force` (D14). An output inside the source tree is refused (W-6).
  - CLI `pack`.
  - Checks:
    - AC-POS-1;
    - AC-DET-1, AC-DET-2;
    - AC-PACK-1, AC-PACK-2, AC-PACK-4, AC-PACK-5, AC-PACK-6, AC-PACK-9, AC-PACK-11;
    - AC-CLI-2.
- [ ] **C-11 Pack race and classification tests**
  - Depends: C-10.
  - `source_changed` (AC-PACK-3).
  - `walk_race`, under `test-hooks` (AC-PACK-10).
  - `skip_classification` (AC-PACK-12).
  - Checks: AC-PACK-3, AC-PACK-10, AC-PACK-12.
- [ ] **C-12 Pack (Windows)**
  - Depends: C-10.
  - In the `windows` module: skip junctions and other reparse points
    (`FILE_FLAG_OPEN_REPARSE_POINT`), never pack alternate data streams, and use
    extended-length paths (W-8).
  - Checks (CI): AC-PACK-7, AC-PACK-8.

### Extract

- [ ] **C-13 Staging (EXT-4) and the create layer**
  - Depends: C-6.
  - **Unix holding steps**, in order:
    1. `mkdirat(0700)`;
    2. `openat(O_DIRECTORY|O_NOFOLLOW)`;
    3. `fstat`: owner = euid, `st_mode & 0o077 == 0`, empty;
    4. `fchmod(handle, 0700)`;
    5. confirm `st_mode & 0o777 == 0700`.
  - **Windows:** `NtCreateFile` with `FILE_CREATE`, without `FILE_SHARE_DELETE`, and with
    `DELETE` access.
  - The handle's identity is recorded. Every later operation goes through handles; nothing
    is reopened by name.
  - The create layer (EXT-2, EXT-6, EXT-8) refuses hostile names on its own.
  - Every directory the extractor creates has any inherited setgid bit cleared (EXT-5).
  - Checks: AC-SAFE-12.
- [ ] **C-14 Extract end to end**
  - Depends: C-13.
  - The destination must not exist (EXT-1).
  - Full structural validation and LIM-5 before anything is written.
  - Step 11 while writing each file, reporting exactly as verify does (EXT-7, M2).
  - Identity checks immediately before and after the final rename.
  - Final permissions (`0755 & ~umask`) only after both pass. If they fail: `io`, with
    cleanup through the same handle.
  - **Cleanup:**
    - removes only recorded identities;
    - the M9 name check, which applies to the destination after the rename (Q4);
    - restrictive modes are handled with `fchmodat`, relative to the parent's handle.
  - CLI `extract`.
  - Checks:
    - AC-POS-4;
    - AC-SAFE-1, AC-SAFE-2, AC-SAFE-4, AC-SAFE-6, AC-SAFE-7;
    - AC-LIM-2, AC-LIM-4;
    - AC-DET-3 (`roundtrip_prop`, seeded generator);
    - AC-ROB-6.
- [ ] **C-15 Extract (Windows and macOS specifics)**
  - Depends: C-14.
  - Windows:
    - long paths;
    - no alternate data streams created (EXT-9);
    - 8.3 short-name aliasing caught (EXT-2).
  - macOS: decomposed names round-trip as NFC (W-9).
  - Case collisions are caught by the filesystem (EXT-2).
  - Checks (CI): AC-SAFE-5, AC-SAFE-9, AC-SAFE-10, AC-SAFE-11.

### Extract race tests (`test-hooks`)

Each hook is compiled only with `test-hooks`. Each test asserts what its criterion says, in
its own `$W`.

- [ ] **C-16 `swap_race`** (AC-SAFE-8)
  - Depends: C-14.
  - [ ] **R4 (review-6):** the hook **deletes** the empty directory created by `mkdirat`
    (`rmdir`), then plants the symlink (a junction on Windows). It never moves the
    directory aside. That way the extractor never leaves behind an object it created but
    couldn't record (its `openat` failed), and "every object the extractor created *inside*
    staging is gone, except the directories on the path to the planted link" holds as
    written.
  - Checks: AC-SAFE-8.
- [ ] **C-17 Staging tests:** `staging_props`, `staging_swap`, `staging_open_race`,
  `staging_rename_race` (AC-SAFE-14)
  - Depends: C-14.
  - `staging_props`'s first hook fires after the holding steps (Q7).
  - The Windows branches expect the swap to be refused, then the extractor's own rename
    through its handle to succeed (P4).
  - Checks: AC-SAFE-14.
- [ ] **C-18 `dest_race`** (AC-SAFE-13)
  - Depends: C-14.
  - Checks: AC-SAFE-13.
- [ ] **C-19 `cleanup_race`** (AC-SAFE-15)
  - Depends: C-14.
  - `late_failure` (AC-SAFE-3) shares the BLB-6 `late-blob-hash` failure.
  - [ ] **R4 (review-6):** the hook replaces an **empty** directory inside staging. It
    deletes that directory (`rmdir`), never moves it, then plants the symlink (a junction
    on Windows) to the sentinel directory. So no object the extractor created survives
    outside cleanup's reach, and the "every object the extractor created inside staging is
    gone, except…" assertion holds as written. The test tree includes such an empty
    directory, ordered so the hook can fire before cleanup.
  - Checks: AC-SAFE-15, AC-SAFE-3.

### Done

- [ ] **C-20 Core done run**
  - Depends: every C task, and CI fast runs passing on all three OSes.
  - The owner triggers a full-mode CI run of one clean commit (`workflow_dispatch`).
    AC-ROB-4, AC-ROB-4W and AC-ROB-7 run there.
  - Update every EVIDENCE.md row from that run's reports, with the commit and the run link.
  - Then `./check.sh --done <ci-run-id>` must exit 0 (ACCEPTANCE §2).
  - Checks: AC-ROB-4, AC-ROB-4W, AC-ROB-7, AC-XP-1.

---

## Phase X: Extended (only after the owner sets `CURRENT_CUT = Extended`)

Until then, every ID below is N/A. Each feature is added behind a default-on Cargo feature,
so `$CHST_CORE` (`--no-default-features`) stays Core-only. Each task re-checks AC-COMPAT-1
(owned by C-6).

- [ ] **X-1 Zstandard blobs (#12)**
  - Depends: C-20, the cut change.
  - `zstd` feature in `chst-format`: ZST-1 … ZST-3, and step 11's order:
    1. BLB-6;
    2. the frame header (ZST-2);
    3. Frame_Content_Size ≠ `raw_length` (ZST-1);
    4. one decoding pass capped at `raw_length` (ZST-2).
  - LIM-6 is computed exactly in at least 128 bits.
  - A blob is compressed only when that's smaller (ZST-3).
  - `crates/chst-format/tests/zstd_bombs.rs` with the counting allocator: `deny(unsafe_code)`,
    and no `unsafe` of its own. It holds the real counting-allocator bomb tests: they decode
    the Extended bomb fixtures through `chst-format` and assert the peak Rust heap. It never
    holds an empty or placeholder test. AC-X-ZSTD-2 fails without the file, and runs it
    with `cargo_test_nonempty`, so at least one test must run and pass.
  - Checks: AC-X-ZSTD-1, AC-X-ZSTD-2.
  - Re-check: AC-ENG-7 (owned by C-8). Under the Extended cut it requires `zstd_bombs.rs`.
- [ ] **X-2 Entry attributes (#16)**
  - Depends: X-1.
  - `ENTRY_ATTRS`: 64-byte entry records (FLG-1 is one-way), ATT-1, mtime and mode, and
    never setuid.
  - Modes are applied as stored, after the children are written (F27).
  - `--deterministic` (AC-X-ATTR-2).
  - Cleanup restores owner permissions with `fchmodat` relative to the parent's handle:
    - with `AT_SYMLINK_NOFOLLOW` where it works;
    - otherwise an `fstatat` identity check first, then the fallback that follows links.
  - Checks: AC-X-ATTR-1, AC-X-ATTR-2.
- [ ] **X-3 `cleanup_modes`** (AC-X-ATTR-3)
  - Depends: X-2.
  - [ ] **R3 (review-6):** the second hook point is "**immediately before cleanup changes
    `x`'s mode**", whether by `fchmodat` relative to the parent or by `fchmod` on a handle
    cleanup kept open. The hook's assertions apply only when it fires:
    - staging is still 0700 and owned by the extractor's user;
    - on macOS, the swap of `x`;
    - the mode and contents of the outside file.

    An extractor that keeps `x`'s handle open and uses `fchmod` on it must pass. On that
    path there's no by-name change and no identity check, so the Linux "between the
    identity check on `x` and the chmod" wording applies only to the by-name path. The
    test never requires the hook to have fired. Whether or not it fired, it still asserts
    `refused/extract.dest-exists`, that the planted directory is unchanged, the staging
    outcome, and that nothing outside staging changed.
  - [ ] **R4 (review-6):** in the macOS swap case, the hook **deletes** the empty original
    `x` (`rmdir`; `d` is mode 0o777), never moves it, then plants the symlink. So the Q2
    exception holds as written: the planted symlink, `d` and staging remain, and every
    other object the extractor created is gone.
  - Checks: AC-X-ATTR-3.
- [ ] **X-4 Key/value metadata (#18b)**
  - Depends: X-1.
  - The `KV_METADATA` section (skippable) and KV-1. It's written only when given.
  - Checks: AC-X-KV-1.
- [ ] **X-5 Selective extract (#6)**
  - Depends: X-1.
  - Path and glob selection by the §12.8 rules, with binary search over sorted entries.
  - LIM-5 and step 11 apply only to the selected entries, so a damaged blob that isn't
    selected doesn't fail (N7).
  - Checks: AC-X-SEL-1.
- [ ] **X-6 Exclude patterns (#7)**
  - Depends: X-1.
  - The writer's input filter, using the §12.8 glob rules.
  - Checks: AC-X-EXCL-1.
- [ ] **X-7 Extended negative fixtures complete**
  - Depends: X-1, X-2, X-4.
  - Checks: AC-X-NEG-1.
- [ ] **X-8 TypeScript reader**
  - Depends: X-7.
  - `ts-reader/`: read-only, with no runtime dependencies. It uses `node:crypto`,
    `String.prototype.normalize` and `node:zlib` zstd.
  - Node 24 LTS, and its ICU must be Unicode 16.0.
  - If `node:zlib` zstd is still experimental, or Node's ICU isn't 16.0, log it under
    "Needs decision" first (DESIGN §9g; the `fzstd` fallback needs its own decision).
  - Checks: AC-X-TS-1, AC-X-TS-2, AC-X-TS-3.
- [ ] **X-9 Extended done run:** as C-20, with the Extended cut.

---

## Review-6 findings (`reviews/review-6.md`)

| ID | Disposition |
|---|---|
| R1 | Applied in 3ce9cae: the P5 note's `io` example no longer uses `quiet`; with `quiet`, extraction may complete with the mount's modes; a refusal comes from step 3, 4 or 5. |
| R2 | Applied in 3ce9cae: the DESIGN D10 amendment and the §9i known-limitation line say "(superseded by Q5: refused or io, non-normative)". |
| R3 | Sub-task of X-3. |
| R4 | Sub-tasks of C-16, C-19 and X-3. |
