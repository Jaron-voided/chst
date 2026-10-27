# Review 6: final bounded check (round 11)

This is the checker's report, verbatim. No finding was blocking, so nothing was changed in
response, and there's no closure table. The owner's rule for this last round: non-blocking
findings go into TODO.md.

> **Note:** the report below is verbatim. Any invisible bidirectional or C1 control character it quoted would be shown as `⟨U+XXXX⟩`, so it can't spoof the surrounding text; this report quoted none.
>
> **Scope:** the checker had only `git diff -U40 ef5f23e c549aea` of FORMAT_SPEC.md, ACCEPTANCE.md and DESIGN.md. It checked (1) that Q1–Q7 were applied as decided, and (2) that the changed EXT-4, AC-SAFE-8/14/15 and AC-X-ATTR-3 text has no internal contradiction and no step where a spec-following implementation fails its own acceptance test. The owner set this as the final fresh review.

---

# Chst final bounded check: Q1–Q7

**Summary.** All seven decisions (Q1–Q7) appear in the added lines and match the owner's table in DESIGN §9i. I found **0 blocking findings**. Within the scoped text, nothing as written would let a conforming implementation write outside staging or follow a link. No acceptance check, as written, would fail a correct implementation. There are four non-blocking findings. Two are about wording around P5 (Q5). Two are about edge cases in the hook-based tests (Q2, Q3, Q6) that the test author has to pin down.

## 1. Presence check
| ID | Applied as decided? | Where (the diff's file and the section or added line) |
|---|---|---|
| Q1 | Yes | FORMAT_SPEC §15 EXT-4 "Holding it": steps 1–5 (check before `fchmod`, `st_mode & 0o077 == 0`, empty, then `fchmod(handle, 0700)`, then confirm `& 0o777 == 0700`). Also the "Nothing under that name is touched on a refusal (Q1)" bullets, the amended refusal bullet, and Cleanup's first exception. DESIGN D10 round-9 amendment rewritten to match. |
| Q2 | Yes | ACCEPTANCE AC-X-ATTR-3, third assertion: "except in the macOS swap case below (Q2). There the planted symlink, `d` and staging remain…" |
| Q3 | Yes | ACCEPTANCE AC-X-ATTR-3, "The check-then-chmod race (P1)": "On macOS… it runs immediately before the `fchmodat` on `x` (Q3)." |
| Q4 | Yes | FORMAT_SPEC EXT-4 Cleanup, "The staging name itself (M9)": "After a successful final rename… the same identity check, then removal, apply to the destination name (Q4)." |
| Q5 | Yes | FORMAT_SPEC EXT-4 "Filesystems without Unix modes (P5)": the "*Non-normative (Q5)*" sub-bullets, ending in "refused or `io`". |
| Q6 | Yes | ACCEPTANCE AC-SAFE-8 and AC-SAFE-15: "…is gone, except the directories on the path to the planted link (Q6)". |
| Q7 | Yes | ACCEPTANCE AC-SAFE-14 `staging_props`: "and held, that is, after EXT-4's holding steps: the checks, `fchmod(handle, 0700)` and the confirming `fstat` (F17, Q7)". |

## 2. Findings
| ID | Section | Severity | Problem | Proposed fix |
|---|---|---|---|---|
| R1 | FORMAT_SPEC EXT-4, P5 note (Q5) | non-blocking | The example is likely wrong. On vfat, `quiet` makes chmod report success even when it changes nothing. With `dmask=077,quiet`, steps 3–5 pass, and the final-permissions `fchmod` also "succeeds" without effect. The likely outcome is then a successful extraction with modes set by the mount, not `io`. `io` is what you'd expect with `dmask=077` *without* `quiet`. Also, a refusal can come from step 4 (`fchmod` returning EPERM), not only from step 3 or 5. The text is non-normative, so no conformance outcome depends on it, but it misdescribes what happens. | Either drop `quiet` from the `io` example, or add a third outcome: "with `quiet`, extraction may complete with modes fixed by the mount." Say "from step 3, 4 or 5". |
| R2 | DESIGN D10 round-9 amendment (the edited paragraph); §9i P5 row and "Known v1 limitation (P5)" line | non-blocking | These still say extraction onto filesystems without Unix modes "is refused". After Q5, FORMAT_SPEC says "refused or `io`". Precedence settles it (FORMAT_SPEC wins), and the Q5 row records the change, but the D10 amendment reads as current state. | Append "(or `io`; see Q5)" to the D10 amendment sentence and to the known-limitation line. |
| R3 | ACCEPTANCE AC-X-ATTR-3, hook point (Q3, and the Linux wording) | non-blocking | The hook point exists only when cleanup changes `x`'s mode by name. EXT-4 Cleanup lets an implementation keep `x`'s handle open and use `fchmod` instead. The section's own last paragraph anticipates this ("Unless cleanup kept that directory's handle open…"). For such an implementation, on either OS, there is no `fchmodat` on `x` and no identity check before it, so the hook never fires. A test that requires the hook to fire would fail a correct implementation. | Define the hook point as "immediately before cleanup changes `x`'s mode, by `fchmod` or `fchmodat`". The Linux identity-check wording then applies only on the by-name path. |
| R4 | ACCEPTANCE AC-X-ATTR-3 (Q2), AC-SAFE-8 and AC-SAFE-15 (Q6) | non-blocking | "Every other object the extractor created is gone" also counts the object the hook swapped out: the original `x`, or in AC-SAFE-8 the directory from `mkdirat`. Cleanup can't remove it if the hook moved it rather than deleting it. In AC-SAFE-8 the extractor never even recorded that directory's identity, because the `openat` failed. Depending on how the hook disposes of the original, the assertion could fail a correct implementation. | State that the hook removes the swapped-out original, which is an empty directory, or exclude it explicitly from "every other object". |

## 3. Verdict
**ready**. Q1–Q7 are all applied as decided, and none of the scoped text lets an implementation act outside staging or follow a link, or makes an acceptance check fail a correct implementation. R1–R4 are worth fixing in the wording, but none is blocking.
