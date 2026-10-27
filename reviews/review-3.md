# Review 3: third independent review (round 8)

Part 1 is the reviewer's report, verbatim. Part 2 is the planner's closure table, for the next reviewer to verify.

> **Note:** the report below is verbatim, except that each invisible bidirectional character it quoted is shown as `⟨U+XXXX⟩`, so it can't spoof the surrounding text.

---

## Part 1: the report

# Chst independent re-review (round 8): fixes for N1–N23

**Summary.** The Zstandard fix (N1) works. Under the new step 11, A/B/C.chst give ZST-1, ZST-2 and ZST-1, and a further 36 crafted frames plus 5,860 mutated frames gave the same rule from my reader and from the generator's checker every time (0 differences). Every fixture still matches: 524 comparisons, 0 mismatches. The generator rebuilds `fixtures/` byte for byte, and the manifest verifies and lists every file.

Three closure claims don't hold up in full:
- **N9 is not closed.** FORMAT_SPEC §11 still says "`ENTRY_ATTRS` ⇔ `record_size` ≥ 64".
- **N2 and N17 are only partly closed.** Details are in M1 and M5.

I found 15 new problems, **3 of them blocking**:
- **M1 (N2 residual, Core):** the staging directory is opened by name *after* it is created, and nothing checks that the opened directory is the one just created. A parent-writer can slip in their own directory between the two steps. All of EXT-4's identity checks then pass on the attacker's directory, and cleanup deletes a tree that was outside staging. Demonstrated in a simulation.
- **M2 (Extended):** the extract order doesn't say where ZST-1/ZST-2 come relative to BLB-6. On an ordinary bit-flip in a compressed blob, verify gives `blob.hash` (exit 7). An extractor that reports the decode failure as it happens gives `zstd.frame` (exit 6). Demonstrated with two files.
- **M3 (Extended, narrow):** LIM-6 says "violated iff raw > limit × stored" and also "(an overflow is a violation)". Appendix C now allows `--max-ratio 18446744073709551615`. With that value, `zstd-compressed` gives exit 0 under exact arithmetic (the generator's reading) and exit 8 under a checked 64-bit multiply.

## 1. Method

- **What I read:** FORMAT_SPEC, ACCEPTANCE, DESIGN (§9g), `reviews/review-2.md`, the review-2 artifacts, and `git diff 368f5b1 3853421` for the four document and fixture paths. I didn't read `reviews/review-1.md`.
- **My reader, `rdr8.py`:** adapted from the round-7 `rdr.py` and brought up to the current spec before I opened `fixtures/gen/`. It covers:
  - the new step 11: BLB-6; frame header → ZST-2; Frame_Content_Size ≠ `raw_length` → ZST-1; then one decoding pass capped at `raw_length`, where every failure is ZST-2. The pass checks Block_Size ≤ min(Window, 128 KiB) for all block types, truncation, trailing bytes, short output and the checksum (my own XXH64). libzstd is used only for Compressed blocks.
  - PATH-6 with U+061C, U+200E and U+200F added.
  - FLG-1 in two modes: `spec` (the literal "⇔" text) and `closure` (the one-direction "⇒" the closure table describes).
  - selective step 11 (N7), and the list, verify and inspect reports.
- **What I ran:**
  - `run8.py`: every fixture group, in both FLG-1 modes.
  - `adv.py` / `adv2.py`: 36 crafted frames, compared across my reader, the generator's `check.py` and libzstd (streaming and one-shot).
  - `fuzz11.py`: a 5,860-case differential over mutated frames, including the real Compressed frame.
  - `describe.py`: decodes every ZST and LIM-6 fixture frame.
  - an XXH64 cross-check against libzstd checksums on 130 sizes (0 mismatches, both my XXH64 and the generator's).
  - `gen.py --out` plus `diff -r`; `sha256sum -c` on the manifest, plus a check that it lists every file; AC-META-4 and the AC-ENG-6 Python assertion, both pass.
  - `n2_race.py`: a spec-literal EXT-4 skeleton with a racing parent-writer.
  - `n17_handle.py`, `bomb_uncapped.py`, `lax_oneshot.py`, `lim6_overflow.py`, `blb6_vs_zst.py`.
- **Not verified:**
  - anything on Windows or macOS: the DACL sequence in N6, `SetSecurityInfo`'s inheritance behaviour, macOS hard-link rules;
  - real multi-user privilege effects (my N2 simulation runs as one user);
  - every CLI, pack and extract scenario (no implementation exists);
  - which glob engine Rust will use;
  - whether the `zstd` crate's defaults accept legacy frames.
- **Repository state:** importing `check.py` briefly created an untracked `fixtures/gen/__pycache__/`. I deleted it. `git status` is clean and the manifest still verifies.

## 2. Closure verification

| ID | Status | Reason |
|---|---|---|
| N1 | closed | Step 11 and §12.5 now give one answer. A/B/C → ZST-1/ZST-2/ZST-1, the same from my reader and `check.py`. 36 crafted frames (FCS ≠ raw combined with a window over 8 MiB, a dictionary ID, a reserved block type, a truncated header, header-only frames, single-segment windows, the 128 KiB block limit, and so on) and 5,860 mutated frames: 0 differences. The extract-side order is a separate gap (M2). |
| N2 | partially closed | Holding by handle, the identity checks and the threat-model sentence are in. But the open-by-name right after `mkdir` is unprotected, and what happens if that open fails is unspecified (M1). AC-SAFE-14's swap test covers only the window before the final permissions are set. |
| N3 | closed (minor residual) | Cleanup wording is fixed. It conflicts with N2's mismatch path (M10). |
| N4 | closed (minor residual) | "Character boundary" is undefined for destination names that aren't UTF-8 (M15). |
| N5 | closed | EXT-4, Appendix A and AC-SAFE-14 all say `refused/extract.collision`. |
| N6 | closed | Unix `0755 & ~umask` and the AC-SAFE-14 checks are in. The Windows DACL sequence is unverified. |
| N7 | closed | §12.8 and step 11 are consistent. My reader gives exit 0 for `docs/*.txt` and BLB-6/7 for `notes.txt` on `late-blob-hash`, as AC-X-SEL-1 expects. |
| N8 | closed | W-10 text, `encode_blob`'s ratio guard and AC-X-ZSTD-1's 2 MiB-zeros case are in. The LIM-6 fixture is now built directly (77 stored for 2 MiB raw). |
| N9 | **not closed** | FORMAT_SPEC line 307 still reads "`ENTRY_ATTRS` ⇔ ENTRY_TABLE `record_size` ≥ 64". Under that text `flg1-noattrs-rs64.chst` and the new `compat/unknown-optional-wider-entries` give FLG-1 to an Extended reader; under the closure reading (which `check.py`, AC-NEG-1 and the README use) they're valid. The forward-compatibility defect remains in the normative text (M4). `FLG-1-attrs-short` is correct under both readings. |
| N10 | partially closed | Both fixtures exist and are correct. But the bomb only catches decoders that buffer the whole output: a streaming decoder with no cap finishes it in 0.08 s at 24 MiB RSS and still reports ZST-2 (M6). |
| N11 | closed | All five fixtures are present and decode as described. No fixture covers a *trailing* second frame or skippable frame (M7). |
| N12 | partially closed | The order paragraph is in, but it leaves out ZST-1/ZST-2 during extraction (M2) and opening the archive (M8). |
| N13 | closed | Step 9 wording fixed. |
| N14 | closed | AC-ROB-1 skips trailer bytes 16–47 in `--rehash` mode. |
| N15 | closed | PATH-6 adds U+061C, U+200E and U+200F; Appendix C pins Unicode 16.0. PATH-6-rlm and PATH-6-alm hold U+200F and U+061C respectively, and are listed in AC-NEG-1. |
| N16 | closed (minor residual) | A `-` after a range (`[a-c-e]`) is undefined, and the "empty class" case can't occur given the `]` rule (M14). |
| N17 | partially closed | "fchmod on its handle" can't be done for a directory whose stored mode lacks owner read: opening it O_RDONLY gives EACCES, and an O_PATH handle gives EBADF on `fchmod` (measured). See M5. |
| N18 | closed | `check.py` evaluates step 11 after earlier violations, checks Block_Size, and the build asserts `COMPRESSED_FRAME` decodes to `COMPRESSED_TEXT`. `BLB-4.also_violates` now lists `blob.hash`. |
| N19 | closed | AC-ENG-6 imports `compression.zstd` (it runs). D7, D15 and D16 are corrected. XXH64 is verified (130 sizes match libzstd). |
| N20 | closed (minor residual) | §1, D8, D12, D16 and ENT-6-2 are fixed. §16's `refused` row omits EXT-4's `unsafe-object` outcome (M11). |
| N21 | closed | Dropped by owner decision (§9g). |
| N22 | closed | Nothing to do. |
| N23 | closed (minor residuals) | The W-10 LIM-2 clause, the Appendix C range and the AC-CLI-1 cases are in; the empty fixture passes `--max-entries 0`. But it makes the LIM-6 overflow clause reachable (M3), and value syntax (M13) and the order among W-10's limits (M12) are undefined. |

## 3. Fixture re-check results

- **All fixture groups (`run8.py`): 524 comparisons, 0 mismatches,** in both FLG-1 modes. The groups:
  - core/invalid in the Core view and the Extended view, with the LIM-2 recipe materialised sparse by my own code;
  - extended/invalid, attacks, hostile, and hostile64 (including `details`);
  - list mode for every bad fixture (step 11 skipped: BLB-6, ZST-1 and step-11 ZST-2 fixtures list cleanly; the rest give their rule);
  - extract-cases;
  - the N7 selective cases;
  - list, verify and inspect reports for core/valid (both views) and extended/valid;
  - compat in the Core view (exit, detail and all reports).
- **ZST fixtures (`describe.py`, 15 frames):** each frame matches its stated mutation and rule.
  - `-no-fcs-overflow`: window 16 KiB, one RLE block of 8,193 → output cap.
  - `-bomb`: 8,192 RLE blocks of 128 KiB (1 GiB), `raw_length` 1 MiB, window 8 MiB, no FCS.
  - `-reserved-fhd`: frame header descriptor 0x08.
  - `-block-type`: block type 3.
  - `-block-size`: an 8,192-byte RLE block in a 1 KiB window.
  - `-truncated`: the RLE body byte is missing.
  - `-skippable`: a skippable frame (`502a4d18…`) placed before the real frame.
  - `ZST-1`: single-segment frame with FCS 8,193 against `raw_length` 8,192.
  - `-checksum`: real Compressed frame; libzstd and my XXH64 both reject it.
  - `-window`, `-dictid`, `-short`, `ZST-2` (one trailing byte) and `ZST-3`: as described.
  - `LIM-6`: 77 stored bytes for 2,097,152 raw.
- **FLG-1-attrs-short:** optional flags `0x8000000000000001` with 48-byte entry records → FLG-1 under both readings; the Core view finds no violation.
- **compat/unknown-optional-wider-entries:** bit 63 with 64-byte records whose tails are zero.
  - Core view: exit 0, and its reports match.
  - Extended view: FLG-1 under the spec text, valid under the closure (M4). No acceptance check compares the Extended view.
- **PATH-6-rlm / PATH-6-alm:** paths `docs/a⟨U+200F⟩b` and `docs/a⟨U+061C⟩b` → PATH-6.
- **Changed expect files:**
  - `SEC-5-entry` no longer lists `flag.mismatch` (consistent with the closure reading);
  - `ENT-6-2`'s `base` text is updated;
  - `LIM-6`'s `mutation` text is updated.
- **Generator:** `gen.py --out` reproduces everything (`diff -r` shows only `gen/`, which the README says isn't regenerated). The manifest verifies, and every file is listed.
- **Adversarial and differential:** 36 crafted frames and 5,860 mutated frames, 0 differences between my reader and `check.py`.

## 4. New findings

| ID | Section | Severity | Problem | Proposed fix |
|---|---|---|---|---|
| M1 | §15 EXT-4 "Holding it", AC-SAFE-14 | **blocking** | EXT-4 says to create staging with `mkdir`, then "right after" open it by name. Nothing checks that the opened object is the directory just created. A parent-writer can rename the new staging away and put their own directory under its name; the extractor then records the *attacker's* identity, and every later identity check passes. **Demonstrated** (`n2_race.py`, a spec-literal skeleton): with a forced EXT-2 collision, the handle-based cleanup (with N17's fchmod) deleted `victim/sub/precious.txt`, which the attacker had moved in from outside staging. Without an error, extraction reports success with the attacker's directory as the destination. The real staging is left behind. What happens if the open finds a symlink (ELOOP) or a non-directory is also unspecified: `io` or `refused`. The `staging_swap` test only swaps before the final permissions are set. | After the open, require `fstat` to show a directory owned by the effective user, with mode 0700 (on Windows: owner SID, DACL as created) and no entries; or create and open in one step where the OS allows it (Windows `NtCreateFile` with `FILE_CREATE`). Any mismatch or failed open → `refused/extract.unsafe-object`, and nothing under that name is touched. Optionally, cleanup removes only objects whose identities the extractor recorded. Add AC-SAFE-14 hooks between create and open, and between the pre-rename check and the rename. |
| M2 | §13 step 11, §15 order (N12), EXT-7, §12.5 | **blocking** (Extended) | Corruption in a compressed blob usually breaks both BLB-6 and the frame. §13 puts BLB-6 first, but EXT-7 requires checking while writing ("not in a separate pass before writing"), and §15's order ("EXT-7 while each file is written … the first failure is the one reported") never mentions ZST-1 or ZST-2. **Demonstrated:** in `M-early-corrupt.chst` the first block's type is flipped to 3 in a 100,040-byte blob; in `M-bitflip-compressed.chst` one byte of the real Compressed frame is flipped. verify → BLB-6 (exit 7). An extractor that reports the decode failure when it happens → ZST-2 (exit 6); in the first file that happens at stored byte 6. The same applies to ZST-1 found from the header against a bad hash (detail `zstd.raw-length` vs `blob.hash`). | Add to §15: "For each blob, the extractor reports step 11's rules in step 11's order. If decoding fails, it still hashes the rest of the blob's stored bytes and reports BLB-6 if the key doesn't match; otherwise the ZST rule." Place step 11 for each entry after EXT-2/EXT-8. Add an Extended extract-case (a bit-flipped compressed blob → 7/`blob.hash`). |
| M3 | §10.2 LIM-6, App. C (N23) | **blocking** (Extended, narrow) | LIM-6 says "violated if and only if raw_length > limit × stored_length, computed without overflow (an overflow is a violation)". An overflowing product is mathematically > raw_length, so the two halves contradict. N23 now allows `--max-ratio` up to 2⁶⁴−1. **Demonstrated** (`lim6_overflow.py`): `verify --max-ratio 18446744073709551615` on `zstd-compressed` gives exit 0 under exact arithmetic (my reader and `check.py`) and exit 8 under a checked u64 multiply. | Replace the parenthetical with "(compute in at least 128 bits, or treat an overflowing product as not violated)". Add that boundary to AC-CLI-1. |
| M4 | §11 FLG-1 (N9) | should fix | The N9 fix never reached FORMAT_SPEC; line 307 still says ⇔. FORMAT_SPEC outranks the other documents, so an Extended reader must reject `compat/unknown-optional-wider-entries` (the forward-compatibility bug N9 described). Meanwhile AC-NEG-1, the README and `check.py` describe one direction. Under AC-X-TS-2 ("behaves as a Core reader unless it implements the feature"), a TypeScript reader that follows the spec may be judged against an expected exit 0. | Change line 307 to "`ENTRY_ATTRS` set ⇒ ENTRY_TABLE `record_size` ≥ 64 (the clear case is SEC-5's job when every flag is known)". Optionally add an Extended-view expectation for this compat fixture. |
| M5 | EXT-4 Cleanup (N17), §12.6 | should fix (Extended) | "Restores the owner's rwx with `fchmod` on its handle" can't be done after a directory has received a stored mode without owner read (0o000, 0o300) unless every directory handle stays open from creation onward, which can mean up to about 1M descriptors. **Measured:** O_RDONLY open → EACCES; an O_PATH handle → `fchmod` EBADF; only a by-name `fchmodat(parent, name, AT_SYMLINK_NOFOLLOW)` works. A late failure (a dest-exists race at the rename) then leaves staging behind, against the MUST. | Allow `fchmodat(parent handle, name, AT_SYMLINK_NOFOLLOW)` (macOS: the same flag) inside staging, which is safe because staging is private. Or require keeping directory handles open until the rename. Add an Extended AC-SAFE-13 case with a 0o000 directory. |
| M6 | AC-X-ZSTD-2 (N10) | should fix (Extended) | The bomb catches only decoders that buffer the whole output. A streaming decoder with no output cap decodes all 1 GiB in 0.08 s at 24 MiB RSS and then reports ZST-2 from the length (`bomb_uncapped.py`). The text "only the decoder's output cap can catch them" is wrong, and the "stops at the first byte beyond it" rule stays untested. | Add a time bomb that needs the cap: about 4–32 MiB of RLE blocks (128 KiB each, 4 bytes stored), i.e. 128 GiB to 1 TiB of output with `raw_length` just above `stored_length`. Ship it as a `$GEN synth-*` recipe if size matters. Correct the sentence. |
| M7 | AC-X-NEG-1, §12.5 | should fix (Extended) | No fixture has a valid frame followed by a second frame or by a skippable frame. libzstd's one-shot decode accepts both. A reader with its own header check plus a one-shot decode passes **every** ZST fixture but accepts `adv/T.chst` and `adv/U.chst` (`lax_oneshot.py`). `ZST-2-skippable` puts the skippable frame first, and plain trailing bytes are rejected by one-shot anyway. | Add `ZST-2-second-frame` and `ZST-2-trailing-skippable`. |
| M8 | §15 order (N12) | should fix | Opening and reading the archive (`io`) has no place relative to EXT-1. `chst extract missing.chst -C existing-dir` can give exit 3 or exit 9. | "usage; opening the input (`io`); EXT-1; …" |
| M9 | EXT-4 | minor | Three wording conflicts. (a) The mismatch path "empties" staging but doesn't remove it, while Cleanup says it MUST be removed. (b) After a post-rename mismatch, the attacker's object that the extractor's own rename put at the destination is left there, against "MUST NOT leave behind a destination it created". (c) Removing the staging directory's own name in ordinary cleanup is by name, with no identity check stated. | State the exceptions explicitly. Check identity with lstat before the final `rmdir` of the staging name. |
| M10 | §14 W-10 | minor | The order is undefined when several limits apply, for example 1,048,576 entries with paths of about 4 KiB: LIM-2 (exit 6), LIM-4 (8) or LIM-3 (8). | "Pack reports the first that a reader would: LIM-2, LIM-4, LIM-3, LIM-5." |
| M11 | §16 | minor | The `refused` row lists EXT-4's `dest-exists` and `collision` outcomes but not `unsafe-object` (Appendix A has it). | Add it. |
| M12 | App. C (N23) | minor | "Decimal integer" doesn't settle `+5`, `007` or surrounding whitespace. Rust's `u64::from_str` accepts `+5`, so the result could be exit 2 or 0. | "ASCII digits only, no sign, no whitespace" (and say whether leading zeros are allowed). |
| M13 | §12.8 (N16) | minor (Extended) | A `-` after a range (`[a-c-e]`) is undefined. bash and Python both read it as {a–c, `-`, `e`}; unverified for Rust glob crates. "An empty class" can't occur given the `]` rule (`[]` is unterminated). | Say that `-` immediately after a range is a literal. Drop "empty class" or define it. |
| M14 | EXT-4 (N4) | minor | "Character boundary" is undefined for Unix destination names that aren't valid UTF-8. HFS+ NFD expansion can push the staging name over 255 UTF-16 units. | "At a UTF-8 boundary if the name is valid UTF-8, otherwise at a byte boundary". Note the HFS+ case. |
| M15 | fixtures expect.json, catalog | minor | The `mutation` text of PATH-6-rlm, -alm, -bidi and -isolate holds raw invisible bidi characters (U+200F, U+061C, U+202E, U+2066). That's the same display-spoofing risk the review records escape. | Write them as `⟨U+200F⟩`-style escapes (e.g. `ensure_ascii=True`). |

## 5. Anything else

- The blocking items:
  - M1 needs a normative sentence plus test hooks. It's Core.
  - M2 and M3 are Extended-only text fixes, plus one extract fixture and one CLI boundary case.
  - M4 is a one-line FORMAT_SPEC edit the closure table says was made but wasn't.
- The closure table says XXH64 was "cross-checked across 15 sizes". That check isn't in the build. On every build, XXH64 is checked against libzstd only through `COMPRESSED_FRAME`'s stored checksum. My 130-size run matched. (none)
- A legacy zstd magic (`27 b5 2f fd`) is ZST-2 by the spec's "wrong magic" rule, and the system libzstd rejects it too. No fixture covers it; it matters only if the `zstd` crate's default `legacy` feature stays on (unverified).
- The Windows final-DACL sequence (N6) and `SetSecurityInfo`'s inheritance behaviour weren't verifiable here.
- **Files**, all in `/tmp/claude-1000/-home-jaron-projects-container-format-rs/4f10aca6-5add-4ba5-ac04-c19ddee93f25/scratchpad/chst-review-3/review-work/`:
  - Reader and runners:
    - `rdr8.py` (my reader)
    - `rdr7_orig.py` (round-7 reader, unchanged copy)
    - `run8.py` (usage: `python3.14 run8.py <fixtures> spec|closure`)
    - `mk.py` (independent container and frame builder)
    - `adv.py`
    - `adv2.py`
    - `fuzz11.py`
    - `describe.py`
  - Demonstration scripts:
    - `n2_race.py` (M1)
    - `blb6_vs_zst.py` (M2)
    - `lim6_overflow.py` (M3)
    - `n17_handle.py` (M5)
    - `bomb_uncapped.py` (M6)
    - `lax_oneshot.py` (M7)
  - Demonstration files:
    - `M-early-corrupt.chst` (M2)
    - `M-bitflip-compressed.chst` (M2)
    - the 31 crafted frames in `adv/` (`T.chst` and `U.chst` are the M7 cases)
    - copies of the round-7 files: `A.chst`, `B.chst`, `C.chst`, `flg1-attrs-rs48.chst` and `flg1-noattrs-rs64.chst`
  - I didn't modify any repository file (`git status` is clean).

---

## Part 2: closure table

How each finding was closed, as claimed by the planner. A later review verifies these claims.
Each row's **Verified by** gives the exact place changed, at the closing commit, and the
command or fixture that shows it. After applying everything, the planner re-grepped every
claim below.

> **Note on Part 1's cross-references.** Some rows of the reviewer's closure-verification
> table point to the wrong M finding. Part 1 is left verbatim; the correct references are:
> - N3 → **M9** (Part 1 says M10);
> - N4 → **M14** (Part 1 says M15);
> - N16 → **M13** (Part 1 says M14);
> - N23 → **M10** (W-10's limit order), **M12** (value syntax) and **M3** (Part 1 says M12
>   for the order and M13 for the syntax).

The N findings Part 1 rated less than closed are closed through these rows: N2 by M1, N9 by
M4, N10 by M6, N12 by M2 and M8, N17 by M5.

All rows are checked by the commands below, which were run at the closing commit:
- `python3.14 -I fixtures/gen/gen.py`, which builds 167 fixtures and runs every self-check
  named below;
- `python3.14 -I fixtures/gen/gen.py --out DIR` then `diff -r -x gen fixtures DIR`, which is
  empty;
- `(cd fixtures && sha256sum --check --quiet MANIFEST.sha256)`, which passes, and the
  manifest lists every file;
- `cd reviews/review-3-artifacts && python3.14 run8.py ../../fixtures closure`, the reviewer's
  own runner: 528 comparisons, 0 mismatches.

| ID | Decision | Closed by | Verified by |
|---|---|---|---|
| M1 | Accepted (`fstat` route) | EXT-4 "Holding it": Unix `mkdirat` + `openat(O_DIRECTORY\|O_NOFOLLOW)`, then `fstat` must show a directory owned by the effective user, mode exactly 0700, and empty. Windows: `NtCreateFile` with `FILE_CREATE` creates and opens in one step. A failed open or check is `refused/extract.unsafe-object`, with nothing under the name touched. Cleanup removes only objects whose identities were recorded. AC-SAFE-14 adds `staging_open_race` and `staging_rename_race`. AC-SAFE-8 and AC-SAFE-15 now expect a planted link to be left in place. | FORMAT_SPEC.md:599–618 (Holding it; 603 the `fstat` checks, 606 `FILE_CREATE`); FORMAT_SPEC.md:638 ("Only what it created"); FORMAT_SPEC.md:962 (Appendix A). ACCEPTANCE.md:948–949 (commands), 972 (`staging_open_race`), 985 (`staging_rename_race`), 882 (AC-SAFE-8), 1007 (AC-SAFE-15). DESIGN.md:433 (D10 amendment). No fixture: these are Rust tests, run once the implementation exists. |
| M2 | Accepted (proposed wording) | §15 "Step 11 while writing": per blob, step 11's rules in step 11's order. After a frame failure the extractor still hashes the rest and reports BLB-6 on a mismatch, otherwise the ZST rule. The check order puts step 11 after EXT-2/EXT-8 per entry. §13 step 11 and EXT-7 point to it. New Extended extract-case `zstd-corrupt-block`. | FORMAT_SPEC.md:564–568 (order), 570 (Step 11 while writing), 494 (§13), 680 (EXT-7). Fixture `fixtures/extended/extract-cases/zstd-corrupt-block.chst`: built at catalog.py:446 (`M2_CORRUPT_FRAME`). The build requires that its frame alone fails ZST-2 (gen.py:252) and that the file's first violation is BLB-6. `rdr8.py` independently gives `('BLB-6', 'integrity', 'blob.hash', 7)`. Checked by ACCEPTANCE.md:1362 (AC-X-ZSTD-1: verify and extract both exit 7). |
| M3 | Accepted (exact, ≥128 bits) | LIM-6 is computed exactly, in at least 128 bits; the overflow parenthetical is removed. TRL-2 is unchanged. | FORMAT_SPEC.md:274. `grep -c 'an overflow is a violation' FORMAT_SPEC.md` returns 1 (TRL-2's line 97 only). ACCEPTANCE.md:1211–1212 (AC-CLI-1: `--max-ratio` 2⁶⁴−1 parses, 2⁶⁴ is usage); ACCEPTANCE.md:1390 (AC-X-ZSTD-2: `--max-ratio 18446744073709551615` on `zstd-compressed` must exit 0; its frame is 337 bytes, and (2⁶⁴−1)×337 overflows u64). |
| M4 | Accepted | FLG-1 is one-way in FORMAT_SPEC. Every compat `expect.json` now records the Extended result under `extended`, and AC-X-NEG-1 checks it. | FORMAT_SPEC.md:307 (`ENTRY_ATTRS` set ⇒ …; `grep -c '⇔ ENTRY_TABLE' FORMAT_SPEC.md` returns 0). gen.py:222 writes `extended`. `fixtures/compat/unknown-optional-wider-entries.expect.json` has `"extended": {"exit": 0, "detail": null}`. ACCEPTANCE.md:1341 (the AC-X-NEG-1 loop). `rdr8.py` with `flg1='closure'` gives None for that fixture and FLG-1 for `FLG-1-attrs-short`. |
| M5 | Accepted | EXT-4 Cleanup "Restrictive modes": `fchmod` on a held handle, otherwise `fchmodat` relative to the parent's handle with `AT_SYMLINK_NOFOLLOW`. Where that flag isn't supported, an `fstatat` NOFOLLOW identity check comes first. The 0o000-directory case is the new Extended ID AC-X-ATTR-3 (see the note below), and AC-SAFE-13 points to it. | FORMAT_SPEC.md:647–655. ACCEPTANCE.md:1438 (AC-X-ATTR-3), 941 (pointer). EVIDENCE.md:93 (new row; the EVIDENCE IDs equal the ACCEPTANCE IDs, in order). Platform: `python3.14 -I reviews/review-3-artifacts/n17_handle.py` on WSL (kernel 6.6.87, glibc 2.39) prints `fchmodat(parent, "d", AT_SYMLINK_NOFOLLOW): ok`. CI runners are unverified (DESIGN §9h). |
| M6 | Accepted | `$GEN synth-zstd-bomb FILE`: 2²³ RLE blocks of 128 KiB (1 TiB of output) in 33,554,438 stored bytes, with `raw_length` one more. AC-X-ZSTD-2 runs it with a 10 s timeout and 64 MiB RSS. The wrong sentence is replaced. | catalog.py:464 (`zstd_time_bomb`); gen.py:485 (command); gen.py:261 (each build requires it to be ZST-2). ACCEPTANCE.md:1386 (the check), 1403 (corrected text; `grep -c "only the decoder's output cap can catch" ACCEPTANCE.md` returns 0). `rdr8.py` gives ZST-2 on it in 0.1 s. A Python uncapped streaming decode measured 0.6 GiB/s, about 29 min for 1 TiB. |
| M7 | Accepted | New `ZST-2-second-frame` (a valid frame plus a second, empty frame) and `ZST-2-trailing-skippable` (a valid frame plus a skippable frame), listed in AC-X-NEG-1. | catalog.py:435, 437. ACCEPTANCE.md:1329. libzstd's one-shot `decompress` returns exactly 8,192 bytes (= `raw_length`) for both, so a lax reader would accept them. `check.py` and `rdr8.py` both give ZST-2. |
| M8 | Applied | The extractor check order now has "opening and reading the input file (`io`)" before EXT-1. | FORMAT_SPEC.md:565. |
| M9 | Applied | Cleanup states its exceptions: a failed open after create; a mismatch before the rename (staging emptied, not removable by name); a mismatch after the rename (the object at the destination is left). The staging name is removed only after a `fstatat` identity check. | FORMAT_SPEC.md:656 (the staging name itself), 659 (exceptions). |
| M10 | Applied | W-10 reports LIM-2, then LIM-4, then LIM-3, then LIM-5. | FORMAT_SPEC.md:550. |
| M11 | Applied | §16's `refused` row lists EXT-4's `unsafe-object`. | FORMAT_SPEC.md:731. |
| M12 | Applied (owner's variant) | ASCII digits only: no sign, no whitespace, no leading zeros; a lone `0` is allowed. | FORMAT_SPEC.md:1075. ACCEPTANCE.md:1208 (AC-CLI-1 rejects `+5`, `05`, `00`, ` 5`, `5 `, `0x5` and the empty value; `--max-entries 0` still passes). |
| M13 | Applied | A `-` straight after a range is a literal (`[a-c-e]`). "Empty class" is dropped, since `[]` and `[!]` are unterminated. | FORMAT_SPEC.md:414, 417. |
| M14 | Applied | Truncation is at a UTF-8 boundary for a valid UTF-8 name, otherwise at a byte boundary, and at a code point boundary on Windows. On macOS, the NFD form must also fit 255 UTF-16 units (HFS+). | FORMAT_SPEC.md:593. |
| M15 | Applied | The mutation texts of PATH-6-c1, -bidi, -isolate, -rlm and -alm use `\\uXXXX` escapes; fixtures regenerated. PATH-6-c1 holds a C1 control rather than a bidi character, and is escaped too. | catalog.py:324–333 (e.g. line 330). `fixtures/core/invalid/PATH-6-rlm.expect.json:7`. A grep for raw C1, U+061C, U+200E/F, U+202A–E and U+2066–9 over every `.md`, `.py` and `.json` file in the repo finds nothing (the `tree.json` paths are excluded as data). The `.chst` bytes are unchanged, since only `expect.json` text changed. |
| XXH64 | Accepted | Every build runs `xxh64_cross_check`: for 79 sizes (0–64 and 14 larger, up to 1,000,000), a Raw-block frame carrying `check.py`'s XXH64 must decode with libzstd, and the same frame with one checksum bit flipped must be rejected. This replaces round 7's unbuilt "15 sizes" claim. | gen.py:277 (function), 236 (call). fixtures/gen/README.md ("XXH64 cross-check, on every build"). The build passes, so all 79 sizes matched and all 79 bad checksums were rejected. |

**Placement notes.**
- **M5 and M3.** The owner asked for the 0o000-directory case in AC-SAFE-13 and the LIM-6
  boundary in AC-CLI-1. Both are Core IDs, and statuses are per ID (ACCEPTANCE §1.1), so an
  Extended-only case inside them would FAIL in the Core cut. So:
  - the 0o000 case is the new Extended ID AC-X-ATTR-3, with a pointer from AC-SAFE-13;
  - AC-CLI-1 has the Core-side parse boundary, and the encoded-blob overflow boundary is in
    AC-X-ZSTD-2.
- **M1's cleanup rule** changed two existing criteria: AC-SAFE-8 and AC-SAFE-15 no longer
  require staging to be gone when a hook has planted a link inside it.
