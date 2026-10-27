# Review 5: final narrow check (round 10)

Part 1 is the checker's report, verbatim. Part 2 is the planner's closure table.

> **Note:** the report below is verbatim. Any invisible bidirectional or C1 control character it quoted would be shown as `⟨U+XXXX⟩`, so it can't spoof the surrounding text; this report quoted none.
>
> **Scope:** the checker had only `git diff -U40 259e8dc ef5f23e` of FORMAT_SPEC.md, ACCEPTANCE.md and DESIGN.md. It checked that P1–P5 were present, and looked for new contradictions in EXT-4, §12.6, AC-SAFE-14 and AC-X-ATTR-3. The owner set this as the last review round before `plan-v1`.

---

## Part 1: the report

# Chst final check: round-9 fixes (P1–P5)

**Summary.** P1–P5 and the AC-SAFE-8/15 wording fix are all in the added lines, and they match §9i. The P3 arithmetic checks out: 54738112978366623 × 337 = 2⁶⁴ + 335, so a wrapping multiply gives 335, and the value is ⌈2⁶⁴/337⌉. However, two of the changes create new contradictions between FORMAT_SPEC and ACCEPTANCE, and in both cases the acceptance check as written would fail an implementation that follows the spec. **2 blocking findings** and 5 non-blocking.

## 1. Presence check
| ID | Present and matches §9i? | Where (the diff's file and the section or added line) |
|---|---|---|
| P1 | Yes | FORMAT_SPEC §15 order-of-checks line; EXT-4 "Staging stays private until it's the destination (P1)"; "Final permissions (N6, P1) … only after the final rename has succeeded and the post-rename identity check has passed"; the new `io` outcome; Cleanup "Restrictive modes" now relies on "Staging stays private"; §12.6 new sub-bullet; ACCEPTANCE AC-SAFE-14 second hook and the "set only after the rename" bullet; AC-X-ATTR-3 "The check-then-chmod race (P1)"; DESIGN D10 amendment and the §9h "Settled in round 9" note |
| P2 | Yes | FORMAT_SPEC EXT-4 "Holding it", Unix: `fchmod(handle, 0700)`, `st_mode & 0o777`; EXT-5 "Inherited setgid (P2)"; ACCEPTANCE AC-SAFE-4 Linux setgid-parent block and note; AC-SAFE-14 umask-0277 / setgid bullet |
| P3 | Yes | ACCEPTANCE AC-X-ZSTD-2: `--max-ratio 54738112978366623` line, expecting exit 0, plus its explanation |
| P4 | Yes | FORMAT_SPEC EXT-4 "Holding it", Windows: ShareAccess MUST NOT include `FILE_SHARE_DELETE`, handle has `DELETE`; ACCEPTANCE AC-SAFE-14 Windows branches of `staging_swap`, `staging_open_race` and `staging_rename_race`, plus the "unverified until the first Windows CI run" note |
| P5 | Yes | FORMAT_SPEC EXT-4 "Filesystems without Unix modes (P5)"; §15.1 Linux and WSL rows; DESIGN §9i "Known v1 limitation" |
| AC-SAFE-8/15 | Yes | ACCEPTANCE AC-SAFE-8 paragraph after the hook points; AC-SAFE-15 last sentences |

## 2. Findings
| ID | Section | Severity | Problem | Proposed fix |
|---|---|---|---|---|
| Q1 | FORMAT_SPEC EXT-4 "Holding it" (Unix) vs ACCEPTANCE AC-SAFE-14 `staging_open_race` | **blocking** | The spec now runs `fchmod(handle, 0700)` *before* the `fstat` checks. Take `staging_open_race`'s first case: an empty, same-user directory with mode 0755 is swapped in between create and open. The `fchmod` succeeds and changes it to 0700. `fstat` then sees a directory owned by the effective user, with mode 0700 and no entries, so every check passes and extraction goes ahead into the swapped-in directory. The test requires `refused/extract.unsafe-object` with the object's permissions unchanged, so a spec-following implementation fails AC-SAFE-14. The spec's own rule "nothing found under that name is touched" is also broken. | Check before you chmod. After `openat`, `fstat` MUST show a directory owned by the effective user ID, with no group or other bits (`st_mode & 0o077 == 0`; `mkdirat(0700)` can never produce them), and no entries. Only then call `fchmod(handle, 0700)`, which makes the umask irrelevant and clears setgid, and confirm `st_mode & 0o777 == 0700`. This keeps §9i P2's `fchmod` and `& 0o777` comparison. |
| Q2 | ACCEPTANCE AC-X-ATTR-3 (P1 hook) vs its own assertion list and FORMAT_SPEC EXT-4 Cleanup "Only what it created" | **blocking** | On macOS, the new hook swaps `x` for a symlink in the same run that asserts "staging is gone completely". The spec says cleanup leaves an unrecorded object in place, along with the directory holding it (`d`) and, as a result, staging. So a correct macOS implementation fails AC-X-ATTR-3. This is the same contradiction round 9 fixed in AC-SAFE-8/15. | Add an exception to the assertion list: "except in the macOS swap case, where the planted symlink, `d` and staging remain, and every other object the extractor created is gone." Or run the swap as a separate extraction with its own assertions. |
| Q3 | ACCEPTANCE AC-X-ATTR-3 (macOS branch) vs FORMAT_SPEC "Restrictive modes" | non-blocking | The hook runs "between the identity check on `x` and the chmod". Where `AT_SYMLINK_NOFOLLOW` is supported (macOS), the spec requires no identity check before `fchmodat`, so that hook point may not exist. | On macOS, define the hook point as "immediately before the `fchmodat` on `x`". |
| Q4 | FORMAT_SPEC EXT-4 "Final permissions", new `io` outcome, vs Cleanup "The staging name itself (M9)" | non-blocking | After the rename, the M9 step still says to check and remove the *staging* name, which no longer exists. One implementation could remove the destination by name after an identity check, and another could leave an empty 0700 destination behind. Both report `io`, but they leave different state, and the second contradicts "MUST NOT leave behind a destination it created". | State that in this case the M9 step applies to the destination name: an `fstatat(AT_SYMLINK_NOFOLLOW)` identity check, then removal. |
| Q5 | FORMAT_SPEC EXT-4 P5 note | non-blocking | The claim that the `fchmod` or the mode check "can't succeed" isn't always true. On vfat mounted with `dmask=077,quiet`, both succeed, and Core extraction then fails later at the final `fchmod(0755 & ~umask)` with `io`. An implementation that detects the filesystem type would report `refused` instead. Exit 9 vs exit 3. | Say whether refusal requires detecting the filesystem type, or describe the result as "refused or `io`" and mark it non-normative. |
| Q6 | ACCEPTANCE AC-SAFE-8, AC-SAFE-15 | non-blocking | "Every object the extractor created *inside* staging is gone" still conflicts with "any directory on the path to the link must remain" when the hooked directory is nested: its ancestors were created by the extractor. A reader can resolve it from the "That means" sentence, but the wording is still contradictory. | Change it to "…is gone, except the directories on the path to the planted link". |
| Q7 | ACCEPTANCE AC-SAFE-14 `staging_props` (umask 0277 bullet) | non-blocking | The first hook fires "right after the staging directory is created". If it fires before the `fchmod`, umask 0277 gives mode 0500 and the 0700 assertion fails a correct implementation. | Place that hook after the holding checks (after `fchmod` and `fstat`). |

## 3. Verdict
**not ready**. Q1 and Q2 each make an acceptance check fail an implementation that follows FORMAT_SPEC as written: Q1 because `fchmod` comes before the checks it would otherwise fail, and Q2 because of an unconditional "staging is gone" assertion. Both need small wording fixes before plan-v1.

---

## Part 2: closure table

How each finding was closed, as claimed by the planner. Each row's **Verified by** gives the
exact place changed, at the closing commit. The planner re-grepped every file:line claim
below after applying everything.

The planner also swept every line mentioning `fchmod` or 0700 in FORMAT_SPEC EXT-4, EXT-5
and §12.6, and in ACCEPTANCE AC-SAFE-14 and AC-X-ATTR-3: 30 lines. None contradicts the new
order:
- FORMAT_SPEC:596's "Its mode is 0700" describes staging once held.
- ACCEPTANCE:971 describes step 4's effect.
- ACCEPTANCE:996's 0755 and non-empty-0700 cases are refused at step 3, before any `fchmod`.
- The Cleanup lines refer to the separate restrictive-modes step.

No fixture changed in this round. The owner made this the last review round, so these
closures aren't re-reviewed before `plan-v1`.

| ID | Decision | Closed by | Verified by |
|---|---|---|---|
| Q1 | Accepted | EXT-4 "Holding it", Unix, is now five numbered steps: `mkdirat(0700)`; `openat`; check owner = euid, `st_mode & 0o077 == 0` and empty; only then `fchmod(handle, 0700)`; then confirm `st_mode & 0o777 == 0700`. A "Nothing under that name is touched on a refusal" bullet explains every refusal path. The refusal bullet and Cleanup's first exception name step 4 as the one, safe, exception. | FORMAT_SPEC.md:606 (the ordered steps), 609 (step 3), 614 (step 4), 616 (step 5), 618 (refusal-path bullet), 633 (refusal bullet), 710 (Cleanup exception). The sweep above found no remaining fchmod-before-check text. |
| Q2 | Accepted (exception in the assertion list) | AC-X-ATTR-3's "staging is gone completely" now excepts the macOS swap case: there the planted symlink, `d` and staging remain, and every other object the extractor created is gone. | ACCEPTANCE.md:1480. |
| Q3 | Accepted | The AC-X-ATTR-3 hook point is between the identity check and the chmod on Linux, and immediately before the `fchmodat` on `x` on macOS. | ACCEPTANCE.md:1488. |
| Q4 | Accepted | Cleanup's "The staging name itself (M9)": after a successful final rename, the same identity check and removal apply to the destination name. | FORMAT_SPEC.md:707. |
| Q5 | Accepted | The P5 note is now marked non-normative: usually `refused` / `extract.unsafe-object`, but some mount options give `io` at the final permissions, so "refused or `io`"; no filesystem detection required. | FORMAT_SPEC.md:639, 643. |
| Q6 | Accepted | AC-SAFE-8 and AC-SAFE-15: "…is gone, except the directories on the path to the planted link". | ACCEPTANCE.md:889 (AC-SAFE-8), 1031 (AC-SAFE-15). |
| Q7 | Accepted | `staging_props`'s first hook pauses after EXT-4's holding steps (the checks, `fchmod(handle, 0700)` and the confirming `fstat`). | ACCEPTANCE.md:963. |

DESIGN.md:894 records Q1–Q7 in §9i, and DESIGN.md:441 updates the round-9 D10 amendment to
the new order. EVIDENCE.md still lists exactly the ACCEPTANCE IDs, in order.
