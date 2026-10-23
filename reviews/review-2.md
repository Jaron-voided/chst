# Review 2: second independent review (round 7)

Part 1 is the reviewer's report, verbatim. Part 2 is the planner's closure table, for the next reviewer to verify.

> **Note:** the report below is verbatim, except that each invisible bidirectional or C1 control character it quoted is shown as `⟨U+XXXX⟩`, so it can't spoof the surrounding text.

---

## Part 1: the report

# Chst independent re-review (round 7): documents, fixtures and generator

**Summary.** Every fixture is correct. My spec-only reader decoded all 153 fixtures and agreed with every `expect.json` and every expected report: 228 comparisons, 0 mismatches. The generator regenerates the committed fixtures byte for byte. Most of the 56 previous items are closed. But the fixes introduced 23 new problems, **2 of them blocking**:

- **N1:** the step-11 Zstandard order can't be implemented consistently. Two readers that both follow the spec give exit 6 and exit 7 on the same file. I demonstrated this with code.
- **N2:** the staging directory itself may be handled by name. A correct implementation can then chmod or rename an attacker's object outside staging.

Two should-fix items deserve attention first. W-10 omits LIM-6, so pack can write files its own verify rejects (N8). And AC-NEG-1's claim that FLG-1 can't be reached for `ENTRY_ATTRS` is false; behind it is a forward-compatibility defect (N9).

## 1. Method

- **Read:** FORMAT_SPEC, DESIGN, ACCEPTANCE, PREVIOUS_REPORT and CLOSURE. I wrote nothing outside `review-work/` and modified no provided file. The fixture manifest still verifies afterwards.
- **My reader (`review-work/rdr.py`), written from FORMAT_SPEC only, before I opened `fixtures/gen/`:**
  - all of §13, in its stated order;
  - a Core view and an Extended view;
  - limits;
  - list, verify and inspect reports per Appendix B;
  - its own RFC 8878 frame-header and block walker;
  - its own XXH64 for content checksums.
  - Only Compressed blocks are decoded through `compression.zstd` (libzstd).
- **Fixtures, all of them, not a sample** (`review-work/run.py`):
  - 128 bad-fixture `expect.json` files (core/invalid with the LIM-2 sparse recipe, extended/invalid, attacks, hostile, hostile64, extract-cases): rule, category, detail and exit match, and list mode behaves correctly (step 11 skipped).
  - 10 core/valid fixtures in both the Core and Extended view, 4 extended/valid, and the sparse huge-5g fixture: list, verify and inspect reports match.
  - 10 compat fixtures in the Core view, including all 15 Core-view reports.
  - Total: **228 checks, 0 mismatches.**
- **Content:** every valid fixture's decoded content equals its `tree.json`, 14 trees (`content.py`).
- **The real Compressed frame (`zstd-compressed`):** decoded by libzstd to exactly `tree.json`'s 8,800 bytes. My own XXH64 over the tree content equals the frame's stored checksum (`30d919c1`), so the checksum check doesn't depend on libzstd. `ZST-2-checksum` differs from it only in the checksum byte, the key and the structure hash.
- **Sweeps on the worked example:**
  - all 556 truncations: 88 give `hdr.too-short`, 468 give `trl.magic`;
  - two append cases;
  - 2 × 1,112 single-byte flips. Plain mode: 7 codes, of which 1,024 are `trl.hash`. Rehash mode: 26 distinct codes, which matches CLOSURE's 26.
- **Also checked with code:**
  - the §18 hex dump equals the fixture, with its size, file hash, structure hash and keys;
  - §18.4's JSON equals `list.json`;
  - LIM-2/3/4/5 boundary values;
  - HFS+ 127 × U+0390 = 254 bytes in NFC and 381 UTF-16 units in NFD;
  - ⌊2³²/48⌋ = 89,478,485;
  - `x`+U+0301+U+113CE is NFC under Unicode 15.0 (system python3 3.12) and not NFC under 16.0 (python3.14);
  - AC-LIM-4's amplify file: 122,736 bytes, 65,536,000 logical;
  - `synth-entries` for 1,048,576 and 1,048,577 entries: 3.4 / 3.6 s (but 1 GiB RSS), and the result is valid or LIM-3 respectively.
- **Generator** (read after the reader was finished):
  - `gen.py --out` reproduces `fixtures/` exactly (`diff -r` empty), with the manifest intact;
  - AC-META-4's checks pass;
  - with `compression.zstd` blocked, the build aborts.
- **Crafted inputs** (`review-work/{A,B,C,flg1-*}.chst`) demonstrate N1 and N9.
- **Not verified:**
  - anything OS- or filesystem-specific (Windows, macOS, 8.3 names, DACLs, renameat2/renameatx_np support);
  - every CLI, pack and extract scenario (no implementation exists);
  - Node 24's ICU Unicode version and `node:zlib`'s windowLogMax option;
  - `unicode-normalization`'s Unicode version;
  - Compressed-block decoding independent of libzstd.

## 2. Closure verification

| ID | Status | Reason |
|---|---|---|
| F1 | closed | Steps 1–9 are in order; HDR-6/SEC-2 stop evaluation; BLB-2 reworded. The Core reader gives 5 for `zstd-required-flag` (code). |
| F2 | closed | A total order exists and each fixture has one `detail`, all matched by code. Step 11 has a new defect, see F10/F11 and N1. |
| F3 | closed | Step 6 order fixed; index-length-huge gives TRL-2, LIM-2 gives LIM-2 (code). |
| F4 | closed | The SEC-4 fixture reports SEC-4 only. |
| F5 | closed | The BLB-5 and BLB-7 fixtures no longer give CAN-2. |
| F6 | closed | PATH-8 exempts `.` and `..`; PATH-4 is checked before PATH-3 (owner decision). |
| F7 | closed | LIM-1 retired; the LIM-2 recipe works (code, sparse 4 GiB); `fixture_file` added. |
| F8 | closed | LIM-6 defined by multiplication; ZST-2 `<4` is in step 10; `--max-ratio` added. |
| F9 | closed | Sum without overflow; decimal strings. |
| F10 | closed, new defect | The window cap, dictionary ban, `windowLogMax` and RSS measurement are done. The added ZST-2/ZST-1 order is inconsistent (N1). There's no fixture for the output cap without an FCS (N10). |
| F11 | partially closed | FCS ≠ `raw_length` is now ZST-1, but its order against the other ZST-2 conditions is ambiguous (N1). |
| F12 | closed | Exactly Unicode 16.0; the fixture is verified against 15.0 and 16.0 by code. Stale "15.1 or later" text remains in D8 and D16 (N20). |
| F13 | partially closed | Rehash sweep and fuzz target added; 26 codes confirmed. The `--rehash` pass rule fails on structure-hash bytes (N14). |
| F14 | closed | EXT-7 is streaming; the AC-SAFE-3 hook was added. |
| F15 | closed | AC-SAFE-12. |
| F16 | closed, new defect | No-replace rename and the dangling-symlink case are done. EXT-4's cleanup clause now contradicts the dest-exists outcome (N3). |
| F17 | partially closed | Name, mode, create-new and the threat model are in. Operations on staging by name are unsafe (N2). The name can exceed 255 bytes (N4). The EEXIST outcome (N5) and the final mode and Windows ACL (N6) are unspecified. |
| F18 | closed | Handle-relative cleanup. Minor gap with read-only directories (N17). |
| F19 | closed | Hook points defined; `test-hooks` feature in D13. |
| F20 | closed | |
| F21 | closed | |
| F22 | closed | |
| F23 | closed | |
| F24 | partially closed | W-10 omits LIM-6 (N8) and LIM-2 (N23). |
| F25 | closed (minor residual) | Bracket-expression edge cases are undefined (N16). |
| F26 | closed | |
| F27 | closed | Cleanup interaction is noted in N17. |
| F28 | closed | `KV-1-empty` verified. |
| F29 | closed | `SEC-3-repeat` verified. |
| F30 | closed | `SEC-4-kv` verified. |
| F31 | closed | |
| F32 | closed | |
| F33 | closed | All 15 Core-view compat reports match my independent Core view. |
| F34 | closed | BLB-6 is invisible to list (code). |
| F35 | partially closed | 40 sub-condition fixtures exist and all verify (24 Core and 16 Extended named in AC-NEG-1 / AC-X-NEG-1; CLOSURE says 39). But FLG-1 for `ENTRY_ATTRS` is reachable, against the "unreachable" claim (N9). ZST-1 without an FCS and several ZST-2 conditions have no fixture (N10, N11). |
| F36 | closed | 3.6 s for 1,048,577 entries (RSS is still about 1 GiB). |
| F37 | closed | Seeded, seed printed, never merges. ("Deepest first" is reverse-lexicographic order plus ancestors, which is adequate.) |
| F38 | closed | `fsutil set` plus a required exit 9; feasibility unverified. |
| F39 | closed | Real Compressed block with a checksum, verified. |
| F40 | closed | Numbers verified by code. |
| F41 | closed | |
| F42 | closed (minor residual) | Ban, escaping and fixtures verified. The Cn version is unpinned, and U+061C/200E/200F are allowed (N15). |
| F43 | closed | |
| F44 | closed | §1.2's table matches every directory's actual fields. |
| F45 | closed (minor residuals) | Appendix C exists; see N15 and N23. |
| F46 | closed | |
| G1 | partially closed | `check.py` returns before step 11 whenever an earlier violation exists, so `also_violates` never shows BLB-6 or ZST rules. For example, the BLB-4 and hostile64 blob0 fixtures also break BLB-6, and that isn't listed. The README's "evaluates every step-8 to step-11 rule" is inaccurate (N18). |
| G2 | closed | Follows F5's wording. Dangling keys are excluded from K, a defensible reading. |
| G3 | closed | |
| G4 | closed | |
| G5 | closed | Rules for attacks and hostile fixtures are written in the catalog. |
| G6 | partially closed | Headers are parsed per RFC 8878. No Block_Size check. The frame's decoded content is never asserted against `COMPRESSED_TEXT`. There's a hard, unpinned dependency on CPython's optional `_zstd` (N18, N19). |
| G7 | closed | 3.4–3.6 s measured. |
| G8 | closed | |
| G9 | closed | My independent reports match every report the generator produced. |
| G10 | closed (doc nit) | AC-META-4 passes, but D7/D15's "no zstd library at all" is now untrue (N19). |

## 3. Fixture re-check results

- **core/invalid** (69, including the LIM-2 recipe), all PASS:
  - every new sub-condition fixture: TRL-2-low, TRL-2-overflow, SEC-1-straddle, SEC-3-repeat, SEC-5-entry, BLB-4-zero-blobs, BLB-4-short-last, ENT-1-type0, PATH-2-unicode16, PATH-3-empty, PATH-3-2, PATH-6-c1, PATH-6-bidi, PATH-6-isolate, the PATH-9 variants (-2, -3, com0, and the six superscripts), ENT-6-2;
  - I decoded each mutation and it matches its description: for example PATH-3-2 is 4,097 bytes, PATH-6-c1 contains U+0085, PATH-3-empty has an empty path, and SEC-3-repeat adds a fourth 0x80000001 section with zero records.
- **extended/invalid** (23), all PASS: ZST-1 (FCS 8193, RLE 8193), ZST-2 (one trailing byte), -window (2³¹), -dictid (1), -short (3 bytes), -checksum, ZST-3, LIM-6 (77 stored for 2,097,152 raw, which is 27,235:1), ATT-1 ×3, KV-1 ×8, FLG-1 ×3, SEC-4-kv.
- **attacks** (23), all PASS, including c1-control (`a\u0085b`) and bidi-override (`invoice⟨U+202E⟩fdp.exe`). They cover every path in AC-SAFE-1's table.
- **hostile** (4), **hostile64** (6) and **extract-cases** (3): all PASS. hostile64 matches AC-ROB-8's table.
- **Valid fixtures, all reports PASS:**
  - core/valid, both views;
  - extended/valid: attrs, kv, zstd-mixed (RLE frame), and zstd-compressed (real Compressed block with checksum);
  - sparse huge-5g (5 GiB hashed);
  - compat in the Core view: 5 fixtures at exit 0 with list, verify and inspect, and 5 at exit 5 with the expected detail.
- **Mismatches: none.**
  - The `also_violates` differences are informational only (they come from G1).
  - ENT-4's fixture also breaks CAN-2 under the literal F5 wording, if the dangling key counts in K.
  - The PATH-4 and attack co-violations are as listed.

## 4. New findings

| ID | Section | Severity | Problem | Proposed fix |
|---|---|---|---|---|
| N1 | §12.5, §13 step 11 | **blocking** (Extended) | "ZST-2, then ZST-1" can't be implemented consistently. Some ZST-2 conditions (the checksum, a complete frame) need decoding past `raw_length`, which ZST-1 forbids. Other ZST-2 conditions (trailing bytes) can be found by walking block headers, or not until after decoding. **Demonstrated:** on files A (FCS 8193 plus a trailing byte), B (no FCS, RLE 8193 > raw 8192, trailing byte) and C (Compressed frame, FCS 8800 with `raw_length` 8799, bad checksum), the generator's `check.py` gives ZST-2, ZST-2, ZST-1 and my reader gives ZST-1, ZST-1, ZST-2. The exit codes differ (6 vs 7). | Make decode-time failures a single rule: **ZST-1** = "Frame_Content_Size present and ≠ `raw_length`", checked from the header. **Everything else is ZST-2**, including decoded output that exceeds or falls short of `raw_length`. Rewrite step 11 for an encoded blob as: BLB-6; frame header (magic, reserved bit, header length, Window ≤ 8 MiB, Dictionary_ID) → ZST-2; FCS ≠ `raw_length` → ZST-1; then a single pass that walks blocks and decodes with output capped at `raw_length`: any failure (reserved block type, Block_Size > min(Window, 128 KiB), truncation, output over the cap, corrupt block, bytes after the frame, short output, checksum mismatch) → ZST-2. Update Appendix A, AC-X-ZSTD-2 and the generator to match. |
| N2 | §15 EXT-4, EXT-6, EXT-8 | **blocking** | Nothing requires operations on the staging directory itself to use its handle. EXT-8 covers only objects *under* staging. A parent-writer (inside the stated threat model) can rename staging away and plant a symlink under its name. Then `fchmodat(parent, name, …)` for the "final mode" (Linux follows symlinks) changes an object outside staging, breaking EXT-6. The by-name final rename moves the attacker's object into the destination, reports success, and leaves the real staging behind. | Add to EXT-4: "Right after creating staging, the extractor opens it with no-follow directory semantics and records its identity. Every later operation on it (writes, the final mode via `fchmod` on the handle or `SetSecurityInfo` on the handle, and cleanup) uses that handle. Immediately before the final rename, the name MUST resolve (lstat / `AT_SYMLINK_NOFOLLOW`) to that identity, and immediately after it the destination MUST. On mismatch the result is `refused` / `extract.unsafe-object`, staging is emptied through the handle, and nothing found at either name is touched." Add to the threat model: "a parent-writer can always replace the destination after extraction; the guarantees are no writes outside staging and no followed links." |
| N3 | §15 EXT-4 | should fix | Cleanup says "the destination MUST NOT exist afterwards", but the rename-time dest-exists case requires cleanup and the destination does exist. AC-SAFE-13 requires the planted object to be unchanged. | Replace with: "…and the extractor MUST NOT leave behind a destination it created; an object someone else created at the destination is left untouched." |
| N4 | §15 EXT-4 | minor | `.<name>.chst-<32 hex>` adds 39 bytes, so any destination name of 217 bytes or more makes the staging name exceed 255 bytes (ENAMETOOLONG), and extraction fails for a valid destination. | "If the staging name would exceed 255 bytes (Windows: 255 UTF-16 units), `<name>` is truncated to its longest prefix that fits, at a character boundary." Adjust AC-SAFE-14's regex. |
| N5 | §15 EXT-4, App. A | minor | No error is defined for when creating staging fails because the name exists. AC-SAFE-14 just says "creation fails". | "If the staging name exists, the result is `refused` / `extract.collision`, and nothing else is created." No retry. |
| N6 | §15 EXT-4 | should fix | "The staging directory's final mode" isn't defined, yet AC-SAFE-4 requires the destination root to be 755 under umask 022. On Windows, the owner-only DACL on staging is inherited by every extracted object (inherited ACEs are copied at creation and not recomputed on rename), so the whole extracted tree stays private. | Unix: the final mode is `0755 & ~umask` (Core and Extended). Windows: the staging DACL is protected, with a non-inheritable owner-only ACE. Each extracted object is created with the inheritable ACEs of the destination's parent. Before the rename, the staging DACL is replaced through the handle by an unprotected DACL that inherits from that parent. |
| N7 | §12.8, §13 step 11, EXT-7 | should fix (Extended) | For a selective extract, whether step 11 checks unselected blobs is unspecified. Step 11 says "per blob record", but EXT-7 checks only what's written. Two extractors can disagree (exit 7 vs 0) on an archive with a corrupt unselected blob. | "For a selective extract, step 11 covers only blobs referenced by selected file entries, verified while writing (EXT-7)." |
| N8 | §14 W-10, §10.2 LIM-6, §12.5 | should fix (Extended) | W-10 covers only LIM-3 … LIM-5. Compressible data easily exceeds a 1000:1 ratio: the repo's own LIM-6 fixture stores 2 MiB of zeros in 77 bytes (27,235:1, measured). So `pack --compress zstd` can write a file that default `verify` rejects with `limit.ratio`. | Extend W-10: "A writer MUST NOT emit an encoded blob that violates LIM-6 under its `--max-ratio` (default 1000); it stores that blob with `encoding` 0 instead." Add a 2 MiB-zeros case to AC-X-ZSTD-1 that expects `stored`. |
| N9 | §11 FLG-1, §17, AC-NEG-1, gen README | should fix | FLG-1 for `ENTRY_ATTRS` is reachable whenever an unknown optional flag disables SEC-5. **Demonstrated:** the flag set plus bit 63 with 48-byte records, and bit 63 alone with 64-byte records, both give FLG-1 from my reader and from `check.py` (and 0 from the Core reader). AC-ROB-1's own sweep produces the first case (byte 24 XOR 0xFF). The second case is a forward-compatibility bug: any future optional flag that widens entry records to 64 bytes or more without `ENTRY_ATTRS` is rejected as `malformed` by Extended 1.0 readers but accepted by Core readers, against §17's "wider records". | Change FLG-1's line to "`ENTRY_ATTRS` set ⇒ ENTRY_TABLE `record_size` ≥ 64". The "clear ⇒ 48" direction is already SEC-5's job when every flag is known. Add `extended/invalid/FLG-1-attrs-short` (flag plus bit 63, 48-byte records) and a valid compat fixture (bit 63, 64-byte records, no flag). Delete the "unreachable" bullet from AC-NEG-1 and the README. |
| N10 | AC-X-NEG-1, AC-X-ZSTD-2 | should fix (Extended) | The decoder output cap, which is the decompression-bomb defence, is untested. The only ZST-1 fixture has an FCS, and the only FCS-less fixture is rejected by its window header. A reader that trusts the FCS and never counts output passes everything. | Add `ZST-1-no-fcs` (no FCS, RLE output of `raw_length` + 1) and a bomb variant (`raw_length` 1 MiB, about 1 GiB of RLE blocks) to AC-X-NEG-1 and AC-X-ZSTD-2, with the RSS and time limits. They become ZST-2 if N1 is adopted. |
| N11 | AC-X-NEG-1 | minor (Extended) | ZST-2 sub-conditions with no fixture: reserved FHD bit, reserved block type, Block_Size > min(Window, 128 KiB), truncated frame, skippable frame. | Add one fixture for each. |
| N12 | §15 | should fix | The order of extractor errors relative to §13 isn't defined: EXT-1 vs malformed input vs SEL-1 vs usage. An invalid archive extracted to an existing destination may give exit 9 or exit 6. | "An extractor checks, in order: usage; EXT-1; §13 steps 1–10 (with LIM-5); SEL-1; staging creation; then, per entry in canonical order, EXT-2/EXT-8 at creation and EXT-7 while writing; then the final rename." |
| N13 | §13 step 9 | minor | "SEC-4, then SEC-5, each for every section" could be read section by section. With BLOB 72 and ENTRY 40, that reading gives SEC-5, while the rule-by-rule reading (mine and the generator's) gives SEC-4. | "SEC-4 for every section in file order; then SEC-5 for every section in file order." |
| N14 | AC-ROB-1 | minor | In `--rehash` mode, flips in trailer bytes 16–47 rehash to the original file. That's 64 exit-0 runs (measured), which the stated pass rule ("exit 0 only for a *different* valid container") fails. | "`--rehash` skips trailer bytes 16–47." |
| N15 | App. C, PATH-6 | minor | The Cn set isn't pinned to a Unicode version. PATH-6 says "directional-formatting" but allows the other Bidi_Control characters U+061C, U+200E and U+200F. | "General_Category per Unicode 16.0." Either add U+061C, U+200E and U+200F to PATH-6, or state that they're intentionally allowed (list escapes them as Cf). |
| N16 | §12.8 | minor (Extended) | Bracket-expression edge cases are undefined: an unterminated `[`, `]` first, `-` first or last, a reversed range, `[]`, `[!]`. There's also no way to match a literal `[`. | "`]` right after `[` or `[!` is literal; `-` first or last is literal; an unterminated `[` or a range with x > y is `usage` / `usage.pattern`." |
| N17 | §12.6, EXT-4 | minor (Extended) | Directory modes 0o555 or 0o000 applied before a late failure (for example, dest-exists at the rename) make unlink-based cleanup fail. | "Cleanup first restores owner rwx with `fchmod` on each directory handle before removing its children." |
| N18 | gen `check.py` | minor | Three things. (a) Step 11 is skipped when any earlier violation exists, so `also_violates` is incomplete and the README overclaims. (b) No Block_Size ≤ min(Window, 128 KiB) check. (c) `COMPRESSED_FRAME`'s decoded content is never compared with `COMPRESSED_TEXT`. I confirmed they're equal via libzstd plus my own XXH64. | Evaluate step 11 in collecting mode as well. Add the Block_Size check. Assert decode == `COMPRESSED_TEXT`. |
| N19 | gen, D7, D15, D16, AC-ENG-6 | should fix | `compression.zstd` is an optional CPython module (built only when libzstd is present). With it blocked, `gen.py --out` aborts with ModuleNotFoundError (tested), so AC-META-5 depends on how CI's python3.14 was built, and nothing checks it. The oracle also decodes Compressed blocks with the same libzstd as Rust, which contradicts D7's "fixtures don't depend on libzstd either". | Add `import compression.zstd` to AC-ENG-6's Python assertion and to D16. Correct the D7 and D15 text. Verify checksums in `check.py` with a pure-Python XXH64 (about 40 lines), so the one libzstd-made frame is cross-checked independently. |
| N20 | §1, §16, D8, D12, D16, ENT-6-2 | minor | Stale or contradictory text: D8 "15.1 or later"; D16 "meets PATH-2's 15.1 minimum"; D12 "each negative fixture violates exactly one rule"; §1 "exactly one category and detail" per rule, whereas EXT-4 has two outcomes, W-10 has three codes, and EXT-7 shares `blob.hash`; §16's `refused` list includes EXT-4's `io` case; ENT-6-2's `base` names a fixture that doesn't exist. | Reword each one. |
| N21 | D16, AC-X-TS-3 | minor (unverified) | `v24.*` isn't an exact pin. A later 24.x may ship newer ICU (Unicode 17), so AC-X-TS-3 would fail, or PATH-2 would diverge if the check were relaxed. | Pin an exact Node version in D16. |
| N22 | App. B, `inspect` | none | All 15 inspect reports matched my independent reading. | (no action; noted for completeness) |
| N23 | W-10, App. C | minor | With `--max-index-bytes` > 2³², pack can exceed LIM-2, and no error is defined for that. Limit-flag ranges and the meaning of 0 are unspecified. | W-10 also refuses LIM-2 (`malformed` / `lim.index-size`). Limit flags take values 0 to 2⁶⁴−1; anything else is `usage`. |

## 5. Anything else

- The two blocking items:
  - N1 is Extended-only and can be fixed in text plus the generator.
  - N2 is Core and needs a normative sentence in EXT-4, plus a test: an AC-SAFE-14 variant that swaps the staging name before the final chmod and rename.
- Crafted demonstration files are in `/tmp/claude-1000/-home-jaron-projects-container-format-rs/e937457e-5049-490d-9241-b7fa1e66df9b/scratchpad/chst-review-2/review-work/`:
  - `A.chst`, `B.chst`, `C.chst` for N1;
  - `flg1-attrs-rs48.chst` and `flg1-noattrs-rs64.chst` for N9.
- My reader is `rdr.py` in that folder, with `run.py`, `content.py` and `sweep.py` alongside.
- Still open as CLOSURE states: runner feasibility, the Node ICU version, `node:zlib` being Experimental, and `unicode-normalization`'s Unicode version. None was verifiable here.


---

## Part 2: closure table


How each finding was closed, as claimed by the planner. A later review verifies these claims.

| ID | Decision | Closed by |
|---|---|---|
| N1 | Accepted | §12.5 and §13 step 11: ZST-1 now means only "Frame_Content_Size in the header ≠ `raw_length`", judged before any block is decoded. Every other failure is ZST-2, found in one decoding pass capped at `raw_length`: a bad header, reserved block type, Block_Size over min(Window, 128 KiB), truncation, output too long or too short, trailing bytes, or a bad checksum. The checker follows the same order. Of the reviewer's three demonstration files, A and C now give ZST-1 and B gives ZST-2, each a single deterministic answer. |
| N2 | Accepted | EXT-4 "Holding it": the staging directory is opened with no-follow semantics right after creation, and its identity is recorded. Every later operation goes through that handle. Before the rename the staging name must still resolve to that identity, and after it the destination must; otherwise `refused/extract.unsafe-object`. The threat-model sentence is added to §15. New AC-SAFE-14 test `staging_swap`. |
| N3 | Accepted | EXT-4 cleanup: the extractor must not leave behind a destination it created; an object someone else created there is left untouched. |
| N4 | Applied | EXT-4: a staging name over 255 bytes (255 UTF-16 units on Windows) truncates `<destination name>` at a character boundary. AC-SAFE-14 adds a 250-byte destination case. |
| N5 | Applied | EXT-4: a staging name that already exists gives `refused/extract.collision`, with no retry; Appendix A updated. AC-SAFE-14 expects that outcome. |
| N6 | Accepted | EXT-4 "Final permissions": `0755 & ~umask` on Unix. On Windows, a protected owner-only DACL on staging, extracted objects created with the destination parent's inheritable ACEs, and the staging DACL replaced by an inheriting one before the rename. AC-SAFE-14 checks both. |
| N7 | Applied | §12.8 and §13 step 11: a selective extract checks only the selected blobs. AC-X-SEL-1 extracts `docs/*.txt` from `late-blob-hash` (exit 0), and `notes.txt` from it (exit 7). |
| N8 | Accepted | W-10: a writer never emits an encoded blob over its `--max-ratio`; it stores it instead. The generator follows the same rule. AC-X-ZSTD-1 packs 2 MiB of zeros and expects `stored`, then a passing verify. The LIM-6 fixture is now built directly, without relying on the compression choice. |
| N9 | Accepted | FLG-1 is now one direction: `ENTRY_ATTRS` set ⇒ `record_size` ≥ 64. New `extended/invalid/FLG-1-attrs-short` and valid `compat/unknown-optional-wider-entries`. The "unreachable" claim is removed from AC-NEG-1 and the generator README. |
| N10 | Applied | New `ZST-2-no-fcs-overflow` (no content size, output one byte over) and `ZST-2-bomb` (1 MiB `raw_length`, about 1 GiB of RLE blocks), both in AC-X-NEG-1 and in AC-X-ZSTD-2's RSS loop, with a 10-second timeout. They are ZST-2 under N1. |
| N11 | Applied | New fixtures: `ZST-2-reserved-fhd`, `ZST-2-block-type`, `ZST-2-block-size`, `ZST-2-truncated`, `ZST-2-skippable`. |
| N12 | Accepted | §15 "Order of extractor checks": usage, EXT-1, steps 1–10 with LIM-5, SEL-1, staging creation, then per entry EXT-2, EXT-8 and EXT-7, then the final rename. |
| N13 | Applied | §13 step 9: "SEC-4 for every section in file order; then SEC-5 for every section in file order". |
| N14 | Applied | AC-ROB-1: `--rehash` skips trailer bytes 16–47. |
| N15 | Decided (ban) | PATH-6 also bans U+061C, U+200E and U+200F. Appendix C's escaping uses General_Category per Unicode 16.0. New fixtures `PATH-6-rlm` and `PATH-6-alm`, listed in AC-NEG-1. |
| N16 | Applied | §12.8: `]` right after `[` or `[!` is a literal (so `[[]` matches `[`), and `-` first or last is a literal. An unterminated `[`, an empty class, or a reversed range is `usage/usage.pattern`. AC-X-SEL-1 adds a reversed-range case. |
| N17 | Applied | EXT-4 cleanup restores the owner's rwx with `fchmod` on each directory handle before removing its children. |
| N18 | Applied | The checker evaluates step 11 even after earlier violations, checks Block_Size, and caps output. The generator asserts that the embedded Compressed frame decodes to exactly `COMPRESSED_TEXT`. README corrected. |
| N19 | Decided (narrower fix) | AC-ENG-6 imports `compression.zstd`; D16 requires it. D7 and D15 are corrected to say libzstd is used only to decode the one embedded frame, as a known-answer check. A pure-Python XXH64 verifies content checksums; it matches libzstd's checksums across 15 input sizes. |
| N20 | Applied | Fixed in §1 (reader rules have one outcome; some extractor and writer rules have several), §16 (`io` names EXT-4's `no-atomic-rename`; `refused` names EXT-4's two refusals), D8 and D16 (Unicode 16.0, no "15.1"), and D12 (one expected detail, with `also_violates`). ENT-6-2's `base` is now "none (a synthetic two-file tree)". |
| N21 | Dropped | No change; the exact Node version will be pinned when Extended starts, if needed. |
| N22 | Nothing to do | — |
| N23 | Applied | W-10 also refuses an index over LIM-2 (`malformed/lim.index-size`). Appendix C: limit values are 0 to 2⁶⁴−1, anything else is `usage/usage.limit`, and 0 means none allowed. AC-CLI-1 adds out-of-range and boundary cases. |
