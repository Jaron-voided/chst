# Review 4: fourth independent review (round 9)

Part 1 is the reviewer's report, verbatim. Part 2 is the planner's closure table, for the next reviewer to verify.

> **Note:** the report below is verbatim. Any invisible bidirectional or C1 control character it quoted would be shown as `⟨U+XXXX⟩`, so it can't spoof the surrounding text; this report quoted none.

---

## Part 1: the report

# Chst independent re-review (round 9): fixes for M1–M15

**Summary.** Fifteen of the sixteen closures check out in the text and fixtures. M5's fix brings in a new safety defect. The generator rebuilds `fixtures/` byte for byte, the manifest verifies and lists every file, and my updated reader gives 540 comparisons with 0 mismatches. That includes the new Extended-view compat results, `zstd-corrupt-block`, the two new ZST-2 fixtures and the 1 TiB time bomb. I found 5 new problems, **1 of them blocking**:
- **P1 (EXT-4 Cleanup, "Restrictive modes", Extended on Linux):** the `fstatat`-then-`fchmodat`-without-the-flag fallback is a check-then-use race (TOCTOU). It is safe only if staging is private, but the spec makes staging `0755 & ~umask` before the rename, and stored directory modes can be 0o777. The cleanup that matters runs after a dest-exists failure, which any parent-writer can trigger. The approved `rustix` 1.x always returns EOPNOTSUPP for `AT_SYMLINK_NOFOLLOW` on Linux, so the fallback is the only path there. glibc also returns it whenever the name is a symlink. **Demonstrated:** a file outside staging went from 0600 to 0777.

## 1. Method
- **What I read:** CLAUDE.md, the changed parts of FORMAT_SPEC, ACCEPTANCE and DESIGN (§9h, the D10 amendment, D15), `reviews/review-3.md`, the review-3 artifacts README, `git diff 51c6a39 259e8dc`, and the generator changes (`gen.py`, `catalog.py`, README).
- **My reader, `rdr9.py`:** `rdr8.py` with FLG-1 made one-way (`ENTRY_ATTRS` set and `record_size` < 64 is the only `ENTRY_ATTRS` violation). I checked its SEC-5 logic against the current SEC-5 and FLG-1 text. It covers step 11 as rdr8 did, PATH-6 and the reports.
- **My runner, `run9.py`:** adds the compat Extended view (against `expect.json`'s `extended`), `extended/extract-cases`, and per-group counts.
- **`extra9.py`:** the synthesized time bomb, the LIM-6 boundary under exact, wrapping, checked and saturating 64-bit multiplies, libzstd one-shot decodes of the two new M7 fixtures, and the structure of `zstd-corrupt-block`.
- **Generator:** I ran `python3.14 -I fixtures/gen/gen.py --out <tmp>` then `diff -r -x gen`. The diff is empty. `sha256sum --check` on the manifest passes, and the manifest lists all 400 fixture files plus the `gen/` sources.
- **XXH64 mutation test:** in a copy of the repo, I made `check.xxh64` wrong for 4,097-byte inputs. The build then failed inside `xxh64_cross_check`, so the cross-check really runs.
- **Demonstrations:** `p1_chmod_race.py` (a spec-literal EXT-4 skeleton plus attacker hooks) and `p2_setgid_umask.py`.
- **Source check:** I read rustix 1.1.4's `chmodat` (from `~/.cargo/registry`): both Linux backends return `OPNOTSUPP` for `SYMLINK_NOFOLLOW` (linux_raw `syscalls.rs:130`), and `fchmodat2` appears in `not_implemented.rs`.
- **Not verified:**
  - anything on Windows: share modes, renaming open directories (P4);
  - macOS;
  - a real second user: P1's swap was done by a hook running as the same user, and its legality for another user rests on the permission bits plus Linux rename rules;
  - vfat, exFAT, CIFS or drvfs behaviour (P5);
  - whether rustix versions later than 1.1.4 add `fchmodat2`.

## 2. Closure verification
| ID | Status | Reason |
|---|---|---|
| M1 | closed with a new defect | §15 EXT-4 "Holding it": `mkdirat`, `openat(O_DIRECTORY\|O_NOFOLLOW)`, `fstat` showing owner = euid, permission bits exactly 0700, and no entries; Windows `NtCreateFile` with `FILE_CREATE`; failures give `unsafe-object` with the name untouched. Recorded-identity cleanup, Appendix A, D10 amendment, and AC-SAFE-14 `staging_open_race`/`staging_rename_race` are all present. The new "exactly 0700" check is ambiguous in setgid parents and fails under some umasks (P2, demonstrated). |
| M2 | closed | §15 order paragraph and "Step 11 while writing", the §13 step 11 note, and EXT-7 match §9h. CAN-2 keeps per-entry order equal to blob-table order, so extract and verify agree across blobs. `zstd-corrupt-block`: the key mismatches, the frame alone gives ZST-2 at byte 7 (0x1f, block type 3), and rdr9 gives `BLB-6/blob.hash/7`. AC-X-ZSTD-1 checks both verify and extract. |
| M3 | closed (minor residual) | LIM-6 (FORMAT_SPEC §10.2) says "exactly, in at least 128 bits". The phrase "an overflow is a violation" now appears only in TRL-2. AC-CLI-1 has the parse boundaries; AC-X-ZSTD-2 has 2⁶⁴−1 on `zstd-compressed` (337 stored, 8,800 raw), and the exact result is pass. A wrapping multiply also passes that case (P3). |
| M4 | closed | §11 FLG-1 reads "`ENTRY_ATTRS` set ⇒ … ≥ 64"; `⇔ ENTRY_TABLE` occurs 0 times. All 11 compat `expect.json` files carry `extended`. rdr9 matches all 11; `unknown-optional-wider-entries` gives 0. The AC-X-NEG-1 loop is present. |
| M5 | closed with a new defect | EXT-4 Cleanup "Restrictive modes", AC-X-ATTR-3 (linux, macos), the AC-SAFE-13 pointer and the EVIDENCE row are present. The fallback's safety claim ("staging is private (mode 0700)") is false when it matters, and on Linux the fallback is always taken (P1). |
| M6 | closed | `synth-zstd-bomb` gives 33,554,438 stored bytes, `raw_length` one more, a 2²³-block RLE frame with an 8 MiB window and no FCS, and passes LIM-6. rdr9 gives ZST-2 in 0.10 s. The build asserts ZST-2. The wrong sentence is gone from ACCEPTANCE. |
| M7 | closed | `ZST-2-second-frame` and `ZST-2-trailing-skippable` exist and are listed in AC-X-NEG-1. rdr9 gives ZST-2 for both; libzstd's one-shot decode returns exactly 8,192 bytes (= `raw_length`) for both. |
| M8 | closed | §15 order has "opening and reading the input file (`io`)" before EXT-1. |
| M9 | closed | The Cleanup exceptions (three bullets) and the identity-checked removal of the staging name are present. |
| M10 | closed | §14 W-10 gives LIM-2, then LIM-4, then LIM-3, then LIM-5, which matches reader steps 6, 9 and 10(p). |
| M11 | closed | The §16 `refused` row includes `unsafe-object`. |
| M12 | closed | Appendix C: ASCII digits only, no sign, no whitespace, no leading zeros, lone `0` allowed. AC-CLI-1 loops over `+5 05 00 ' 5' '5 ' 0x5 ''`. |
| M13 | closed | §12.8: `[a-c-e]` is defined, and "empty class" is replaced by the `[]`/`[!]` remark. |
| M14 | closed | EXT-4 "Creating it": UTF-8 boundary, otherwise byte boundary; code point boundary on Windows; the HFS+ NFD note. |
| M15 | closed | A scan of every `.md`, `.py` and `.json` file in the repo finds 0 raw C1, U+061C, U+200E/F, U+202A–E or U+2066–9 characters. The PATH-6 mutation texts use `\\uXXXX`. |
| XXH64 | closed | `gen.py` `xxh64_cross_check` covers 79 sizes and is called from `build()`. The mutation test shows a wrong XXH64 fails the build. |

## 3. Fixture re-check results
- **Overall (`run9.py`, one-way FLG-1): 540 comparisons, 0 mismatches.**
- core/invalid in the Core view: 71, 0 mismatches.
- Extended view of core/invalid, attacks, hostile and hostile64: 104, 0 mismatches. hostile64 `details`: 6, 0 mismatches. The LIM-2 recipe was materialised sparse by my own code.
- extended/invalid: 33, 0 mismatches. This includes `ZST-2-second-frame` and `ZST-2-trailing-skippable` (both ZST-2).
- List mode for every bad fixture (step 11 skipped): 208, 0 mismatches.
- core/extract-cases: 3, 0 mismatches. N7 selective cases: 2, 0 mismatches.
- extended/extract-cases (`zstd-corrupt-block`, giving 7, BLB-6, `blob.hash`): 1, 0 mismatches.
- list, verify and inspect reports: core/valid in both views 60, extended/valid 12; 0 mismatches.
- compat in the Core view (exit, detail and reports): 29, 0 mismatches. compat in the Extended view (the new `extended` field): 11, 0 mismatches.
- Time bomb: ZST-2 (`zstd.frame`, exit 6) in 0.10 s. `--max-ratio 18446744073709551615` on `zstd-compressed` gives no violation under exact arithmetic.
- Generator: rebuilds byte for byte, and the manifest verifies and is complete.

## 4. New findings
| ID | Section | Severity | Problem | Proposed fix |
|---|---|---|---|---|
| P1 | FORMAT_SPEC §15 EXT-4 Cleanup "Restrictive modes"; §12.6; EXT-4 "Final permissions"; DESIGN §9h | **blocking** (Extended, Linux) | **The safety claim is false when it matters.** The fallback checks with `fstatat(AT_SYMLINK_NOFOLLOW)`, then calls `fchmodat` *without* the flag, which follows symlinks. The spec says that's safe "because staging is private (mode 0700)". But §12.6 applies stored directory modes (up to 0o777) and then "Final permissions" sets staging to `0755 & ~umask`, both before the rename. The late failures that need this cleanup all come after that point: dest-exists (which a parent-writer can trigger at will), no-atomic-rename, and both identity-mismatch cases. Any local user can then traverse staging and rename names inside a 0o777 directory.<br>**The fallback always runs on Linux.** rustix 1.x is the approved crate, and chst-fs can't use `unsafe` on Unix. rustix 1.1.4 returns `EOPNOTSUPP` for `SYMLINK_NOFOLLOW` on Linux every time. glibc returns `ENOTSUP` (the same value) whenever the name is a symlink, so an attacker can force the fallback there too. This settles §9h's open question: rustix doesn't expose the flag.<br>**Demonstrated** (`p1_chmod_race.py`): the tree has `d` (0o777) holding `x` (0o077), and the dest-exists cleanup runs. A `RENAME_EXCHANGE` of `x` with a symlink, between the check and the chmod, changed an outside file from 0600 to **0777**, with both the rustix-style and the glibc paths. Without the swap, nothing outside changed.<br>**Impact:** the new mode is "owner rwx restored" OR'd onto a mode the archive chose (0o077 gives 0o777). Run as root, this makes any file world-writable, for example `/etc/shadow`. A hostile archive can contain up to LIM-3 such directories, so one cleanup gives the attacker many chances to win the race. | 1. Keep staging 0700 until the final rename has succeeded and the post-rename identity check has passed, then set the final permissions through the handle. That makes the "private" premise true for every cleanup.<br>2. Also remove the follow-the-link fallback. On Linux, open the name with `O_PATH\|O_NOFOLLOW` relative to the parent's handle, compare the identity with `fstat`, and chmod through `/proc/self/fd/N`. Or treat `EOPNOTSUPP`/`ENOTSUP`/`ENOSYS` as "leave it in place".<br>3. Add an AC-X-ATTR-3 hook that does this swap between the check and the chmod, and asserts the outside file is unchanged. |
| P2 | §15 EXT-4 "Holding it" (M1) | should fix | "Permission bits exactly 0700" breaks in two environments.<br>**Setgid parent:** Linux makes the new directory inherit S_ISGID, so `fstat` shows 0o2700. A reader that uses `& 0o777` succeeds; one that uses `S_IMODE` (`& 0o7777`) refuses every extraction there with exit 9. **Demonstrated** (`p2_setgid_umask.py`). The spec's own §12.6 use of "permission bits" (≤ 0o777) favours the first reading, but it isn't stated here.<br>**Umask:** a umask that masks owner bits (for example 0277) gives 0o500, so every extraction is refused (demonstrated).<br>**Related:** with a setgid staging directory, the kernel also sets S_ISGID on every directory created under it, which conflicts with EXT-5's "setgid MUST NOT be set". Implementations that clear it explicitly and those that rely on the `mkdirat` mode will produce different trees. | Say "`st_mode & 0o777` is 0700 (setuid, setgid and sticky are ignored)". Either create with `mkdirat` and then `fchmod(handle, 0700)` before the checks, or say that a umask masking owner bits is refused. Say whether extracted directories must have an inherited S_ISGID cleared. |
| P3 | ACCEPTANCE AC-X-ZSTD-2 (M3) | should fix (Extended) | The only overflow case, 2⁶⁴−1 × 337, catches "overflow is a violation". It doesn't catch a wrapping or saturating u64 multiply, and wrapping is what a plain `*` does in a Rust release build. A wrapping reader passes every LIM-6 test but is wrong on other values. **Computed** (`extra9.py`): `--max-ratio 54738112978366623` on `zstd-compressed` wraps the product to 335 < 8,800, a spurious violation (exit 8); the exact answer is exit 0. | Add `expect_exit 0 $CHST verify --max-ratio 54738112978366623 $FX/extended/valid/zstd-compressed/container.chst` (that's ⌈2⁶⁴/337⌉). |
| P4 | AC-SAFE-14 `staging_rename_race` and `staging_swap` (Windows); EXT-4 "Holding it" | should fix (unverified on Windows) | The spec doesn't give the `NtCreateFile` ShareAccess. If staging is opened without `FILE_SHARE_DELETE` (the safer choice), Windows refuses the hook's rename of the open directory. `staging_open_race` allows "or success if Windows refuses the swap". `staging_rename_race` (Windows: "outside directory unchanged under the staging name") and `staging_swap` (it requires `unsafe-object`) don't, so a correct, stricter Windows extractor fails AC-SAFE-14. | Specify the ShareAccess. Denying `FILE_SHARE_DELETE` is recommended: the extractor's own rename through its handle still works. Give both tests the same "refused swap → success, nothing outside changes" branch. |
| P5 | EXT-4 "Holding it"; §15.1 Linux and WSL rows | minor (unverified) | On filesystems without Unix modes (vfat, exFAT, CIFS, and drvfs `/mnt/c` without `metadata`; this machine's `/mnt/c` is drvfs over 9p), modes are fixed by mount options. `mkdirat(0700)` can't produce 0700 there, so the exact check refuses every extraction onto them. §15.1 names vfat, CIFS and WSL drives as places where extraction runs. Neither extractor would disagree with another, but extraction onto those filesystems is impossible. | State the outcome (refused, with a documented limitation), or limit the mode check to filesystems that honour modes, relying on the ownership and emptiness checks elsewhere. |

## 5. Anything else
- The two "Still open" items in §9h:
  - The rustix question is now settled: rustix 1.1.4 doesn't support the flag on Linux (P1).
  - The ownership check is still untestable by a single user, as §9h says.
- Wording only, not counted: AC-SAFE-8 and AC-SAFE-15 say "nothing the extractor created may remain" and also that staging, which the extractor created, must be left in place.
- **Files**, all in `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/`:
  - `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/rdr9.py` (reader, FLG-1 one-way)
  - `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/run9.py` (usage: `python3.14 -I run9.py <fixtures>`; it writes `sparse-LIM-2` next to itself, so delete that afterwards)
  - `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/extra9.py` (needs `tb.chst`, which I deleted after running; recreate it with `python3.14 -I fixtures/gen/gen.py synth-zstd-bomb tb.chst` from that folder)
  - `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/p1_chmod_race.py` and its output `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/p1_chmod_race.out`
  - `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/p2_setgid_umask.py` and its output `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-4/review-work/p2_setgid_umask.out`
  - copies of the round-8 artifacts, unchanged, in the same folder
- Repository: I modified no file. No `__pycache__` was created, and `git status --porcelain` is empty.

## 6. Verdict
**not ready**: P1 is a demonstrated way for an Extended Linux extractor that follows the spec to chmod a file outside staging. The spec's own safety argument doesn't hold, and the approved `rustix` dependency makes the unsafe fallback the only path on Linux.

---

## Part 2: closure table

How each finding was closed, as claimed by the planner. A later review verifies these claims.
Each row's **Verified by** gives the exact place changed, at the closing commit, and the
check that shows it. The planner re-grepped every file:line claim below after applying
everything. Nothing under `fixtures/` changed in this round, and it was checked like this:
- `python3.14 -I fixtures/gen/gen.py` builds 167 fixtures, with no change shown by
  `git status fixtures/`;
- `python3.14 -I fixtures/gen/gen.py --out DIR` then `diff -r -x gen fixtures DIR` is empty;
- `(cd fixtures && sha256sum --check --quiet MANIFEST.sha256)` passes.

| ID | Decision | Closed by | Verified by |
|---|---|---|---|
| P1 | Accepted: fix 1 and fix 3, not fix 2 | Staging stays 0700 (on Windows, its private DACL) until the final rename and the post-rename identity check have passed. Only then are the final permissions set, through the handle. If that fails, the result is `io` and cleanup runs through the same handle. §12.6, the §15 order, Cleanup's "Restrictive modes" and DESIGN §9h agree. AC-X-ATTR-3 gets the check-then-chmod hook: it asserts staging is 0700 on Linux and macOS, and performs the real swap on macOS (see the note below). AC-SAFE-14 asserts 0700 just before the rename and moves `staging_swap`'s hook point. | FORMAT_SPEC.md:634 ("Staging stays private"), 639 ("Final permissions (N6, P1)", only after the rename), 648 (`io` outcome), 680 (the fallback's justification), 389 (§12.6), 572 (§15 order). `grep -c -i 'before the rename' FORMAT_SPEC.md` returns 0; the only `0755 & ~umask` is at 641, inside "Final permissions". ACCEPTANCE.md:1478 (AC-X-ATTR-3 hook), 971 and 977 (AC-SAFE-14), 981 (`staging_swap`). DESIGN.md:846 (§9h reconciled), 852 (§9i), 439 (D10 amendment). |
| P2 | Accepted | Holding it: `mkdirat`, `openat`, then `fchmod(handle, 0700)`, and the check is `st_mode & 0o777` = 0700. EXT-5: every created directory has an inherited S_ISGID cleared with `fchmod`. AC-SAFE-4 adds a Linux setgid-parent case. AC-SAFE-14 asserts 0700 under umask 0277 and under a setgid parent. | FORMAT_SPEC.md:607 (`fchmod(handle, 0700)`), 609 (`& 0o777`), 703 (EXT-5 "Inherited setgid"). ACCEPTANCE.md:830 (AC-SAFE-4 `if [ "$CHST_OS" = linux ]` block), 968 (AC-SAFE-14). The reviewer's `p2_setgid_umask.out` (in `reviews/review-4-artifacts/`) shows the old behaviour the fix addresses: 0o2700 under a setgid parent, and 0o500 under umask 0277. |
| P3 | Accepted | AC-X-ZSTD-2 adds `--max-ratio 54738112978366623` on `zstd-compressed`, expecting exit 0, with an explanation. | ACCEPTANCE.md:1414 (command), 1433 (explanation). `python3.14 -c 'print(-(-2**64//337), (54738112978366623*337) % 2**64)'` prints `54738112978366623 335`: that's ⌈2⁶⁴/337⌉, and the wrapped product is 335 < 8,800. |
| P4 | Accepted | On Windows, staging's `NtCreateFile` ShareAccess excludes `FILE_SHARE_DELETE`, and the handle has `DELETE` access. Each Windows branch of `staging_open_race`, `staging_swap` and `staging_rename_race` now reads: the swap is refused, then the extractor's own rename succeeds, and nothing outside staging changes. Marked unverified until Windows CI. | FORMAT_SPEC.md:615. ACCEPTANCE.md:988 (`staging_swap`), 999 (`staging_open_race`), 1013 (`staging_rename_race`), 1018 (unverified note). DESIGN.md §9i "Still open". |
| P5 | Accepted | Extraction onto filesystems without Unix modes (vfat, exFAT, CIFS, drvfs without `metadata`) is refused with `extract.unsafe-object`. It's documented in EXT-4 and §15.1, and recorded as a known v1 limitation to revisit after v1. | FORMAT_SPEC.md:622 (EXT-4), 746 (§15.1 Linux row), 747 (§15.1 WSL row). DESIGN.md:882 ("Known v1 limitation (P5)"). |
| AC-SAFE-8 and AC-SAFE-15 wording | Accepted | Both now say that every object the extractor created *inside* staging must be gone, while the planted link, and the staging directory holding it, stay. | ACCEPTANCE.md:888 (AC-SAFE-8), 1028 (AC-SAFE-15). |

**Notes on how decisions were applied.**
- **P1, fix 3 without fix 2.** The owner skipped fix 2, so Linux cleanup keeps the fallback
  that follows links: rustix always takes it. A test hook runs as the extractor's own user,
  whom staging's 0700 mode doesn't stop. A same-user swap on Linux would therefore change the
  outside file even in a correct implementation. So the AC-X-ATTR-3 hook:
  - asserts on Linux and macOS that staging is still 0700 and owned by the extractor's user,
    which is what stops every other user;
  - performs the real swap only on macOS, where `fchmodat` honours `AT_SYMLINK_NOFOLLOW`;
  - requires that nothing outside staging changed.

  The Linux swap itself needs a second user, and it's listed as open in DESIGN §9i.
- **P4 also changed `staging_rename_race`'s Windows branch.** The owner named `staging_open_race`
  and `staging_swap`. `staging_rename_race`'s old Windows branch assumed the hook's rename
  succeeds, which is impossible without `FILE_SHARE_DELETE`.
- **P1 moved `staging_swap`'s hook point.** It used to fire "just before the final permissions",
  which now come after the rename. It now fires just before the pre-rename identity check.
