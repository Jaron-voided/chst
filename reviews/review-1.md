# Review 1: first independent review (round 6)

Part 1 is the reviewer's report, verbatim. Part 2 is the planner's closure table, given to the next reviewer to verify.

---

## Part 1: the report

# Chst independent review: documents and fixtures

The fixtures are correct, but the spec isn't ready for `plan-v1`. Every fixture I decoded with a reader written from the spec alone matched byte for byte. Every bad fixture fails for its intended reason. The problems are in the spec and the acceptance criteria: 46 findings, 5 of them blocking (F1, F10, F16, F17, F18).

**I could not save `review-work/REPORT.md`.** The harness refused the Write call ("Subagents should return findings as text"), and I didn't work around that. The full report is below; it needs saving from here.

All paths are relative to the review directory `/tmp/claude-1000/-home-jaron-projects-container-format-rs/e937457e-5049-490d-9241-b7fa1e66df9b/scratchpad/chst-review`.

## 1. Method

- **Read first:** FORMAT_SPEC.md, DESIGN.md and ACCEPTANCE.md, in full.
- **Then a decoder written from the spec alone:** `review-work/chst_ref.py`, written before I opened `fixtures/gen/`. It uses only the Python 3.14 standard library: `hashlib` for SHA-256, `unicodedata` 16.0 for NFC, and `compression.zstd` (libzstd 1.5.5) for decoding. The generator writes its own frames, so libzstd is an independent decoder here.
  - **Steps 1–7** run strictly in order and stop at the first failure.
  - **Steps 8–10** may run in any order (§13), so the decoder evaluates every rule it can and returns the full set of violated rules. I compared that set with each fixture's acceptable `details`.
  - **Modes:** an Extended reader (knows ZSTD, ENTRY_ATTRS, KV_METADATA) and a Core reader (knows no flags or optional sections). An extra "collect-all" mode keeps going past HDR-6 and SEC-2.
  - **Reports:** list, verify and inspect, built from Appendix B, compared with each expected JSON after removing `message` (the `jqn` rule).
- **Scripts** (all under `review-work/`):
  - `run_fixtures.py`: every fixture.
  - `worked.py`: §18.
  - `compat_all.py`: Core-reader violation sets.
  - `mutdiff.py`: byte diff of each bad fixture against its base.
  - `misc.py`: paths and contents.
  - `sweeps.py`: flip, truncation and limit sweeps.
  - `zstdwalk.py`: a frame-header walker of my own.
  - `sparse.py`: the 5 GiB recipe, as a virtual sparse source.
- **Counts:** I checked **every fixture**, not a sample:
  - 13 valid fixture directories (9 core, 3 extended, plus the core ones re-run with a Core reader);
  - 1 sparse recipe;
  - 48 core/invalid, 21 attacks, 4 hostile, 6 hostile64, 3 extract-cases, 7 extended/invalid and 10 compat.
  - I also ran exhaustive single-byte flip sweeps (XOR 0x01 and 0xFF) on worked-example, empty and dedup; every truncation prefix of the worked example; and AC-LIM-2's boundary values.
- **Only after recording those results** did I read `fixtures/gen/*`, and review it against the spec (§3).
- **Manifest:** `sha256sum --check` passes, and the listing equals the file set. The SHA-256 of `MANIFEST.sha256` as it stands is `9662cf06c971917e09902ddbd6ed26653e990334362c599cb7cc7aacf22681fc`. That's for information only; I recommend fixing the findings before pinning it.
- **Not verified with code:**
  - behaviour on Windows or macOS (8.3 names, case-insensitive filesystems, junctions, ADS, HFS+);
  - any extraction, pack or CLI scenario (there is no implementation);
  - the TypeScript reader;
  - real Zstandard Compressed blocks (no fixture contains one).

  Everything else in §2 was checked by code.

## 2. Fixture verification results

### 2.1 Worked example (§18): PASS, all by code

- The §18.3 hex dump parses to 556 bytes. They are identical to `core/valid/worked-example/container.chst`, and the ASCII column matches too.
- SHA-256 of the file is `1939236c…e33332`, as the spec states.
- The structure hash, computed over the stated 507 bytes, is `13e9dfcb…16e6fb9a`, matching both the dump and §18.2.
- The blob keys `5891b5b5…f6be03` and `98ea6e4f…107be4` are the SHA-256 of `hello\n` and `hi\n`.
- Every §18.2 row's offset, decimal = hex, size and value matches the bytes.
- The size arithmetic holds: 144 + 256 + 59 = 459, and 32 + 9 + 459 + 56 = 556.
- §18.4's JSON equals `list.json`.

### 2.2 Valid fixtures: all PASS, no mismatches

My list, verify and inspect reports equal the expected JSON exactly for:

- core/valid: worked-example, empty, empty-file, dirs-only, dedup, unicode, deep, long-names, sort-edge. Each also passes with a Core-only reader.
- extended/valid: attrs, kv, zstd-mixed.
- core/sparse/huge-5g: list, inspect and verify all pass. This included SHA-256 over 5 GiB of virtual zeros, so the key `7f06c623…` is confirmed.

Decoded contents equal `tree.json` in every case, zstd included.

- `attrs/tree.json` also carries `mtime_seconds`, `mtime_nanos` and `mode`, consistent with `list.json`. That's informational, not a mismatch.
- The ACCEPTANCE §3.3 content requirements hold:
  - dedup: 103 files and 2 blobs (AC-DET-2's predicate holds);
  - deep: depth 256;
  - long-names: a 255-byte segment and a 4096-byte path;
  - sort-edge: order `a, a-b, a.b, a/b`;
  - unicode: `café.txt`, `日本語/テキスト.txt`, `😀.txt`.
- The compat fixtures with exit 0 (entry-attrs, kv-metadata, minor-65535, unknown-noncritical-section, unknown-optional-bit63) are accepted by my Core reader, and their `list.json` matches.

### 2.3 Bad fixtures

Every bad fixture fails with the intended category and exit code, and its intended detail is among my violations. There are no wrong-reason failures. Where my set has **additional** violations under a literal reading of the spec, they are listed as mismatches.

| Fixture | Result | Notes |
|---|---|---|
| HDR-1…6, TRL-1…3, SEC-1, SEC-2, SEC-3, SEC-5, BLB-1…4, BLB-6, ENT-1…4, ENT-6, ENT-6-2, PATH-1, PATH-2, PATH-3, PATH-3-2, PATH-6…11, PATH-9-2, PATH-9-3, CAN-1…3, LIM-3/4/5 (with their `args`) | match, single violation | The mutations were confirmed by byte diff against the base: only the named field and the structure hash differ. |
| ENT-5, PATH-4, PATH-5 | match | My sets equal the listed `details` exactly. |
| **BLB-5** | **MISMATCH (extra violation)** | Also violates **CAN-2** under the literal text ("the first reference to each not-yet-seen key gives the next blob" gives 2 blobs; the table has 3). It passes only under the generator's reading (README item 2), which also silently de-duplicates keys. |
| **BLB-7** | **MISMATCH (extra violation)** | Also violates **CAN-2** literally (the orphan blob isn't in the first-reference sequence). This is the DESIGN §9 open item 3. |
| **SEC-4** | **MISMATCH (extra violation)** | `record_size` 63 also violates **SEC-5**: no flags are set, so the reader "knows every flag" and 63 ≠ 64. The generator's checker returns on SEC-4 before evaluating SEC-5, so it never saw this. |
| hostile/path-length-max | match, with a caveat | `path_length` 2³²−1 also exceeds PATH-3's 4096. A reader that checks lengths before slicing the pool would report `path.length`, which isn't listed. The spec doesn't say whether PATH rules apply to out-of-range paths. |
| Other hostile and hostile64 fixtures (entries-2e32, index-length-huge, record-count-2e60, blob-table-count, blob0-offset, blob0-raw, blob0-stored-and-raw, entry1-path-offset, trailer-index-offset) | match | All are under 1 KiB, and the AC-ROB-8 table is fully covered. Caveat for index-length-huge: it also breaks LIM-2 and LIM-4, and nothing fixes the order inside step 6 (F3). A reader checking LIM-4 first exits 8, not 6. |
| All 21 attacks | match | The paths cover every row of the AC-SAFE-1 table. |
| extract-cases: late-blob-hash | match | BLB-6. The corrupted blob is the one the last entry references. |
| extract-cases: short-name, unicode-case | match | Both valid. |
| extended: ATT-1, FLG-1, KV-1, LIM-6, ZST-1, ZST-2, ZST-3 | match | ZST-2: my frame walker finds 1 trailing byte, and libzstd reports unused data. ZST-1: the frame declares FCS 8193 against `raw_length` 8192. LIM-6: 2,097,152 / 77 ≈ 27,236. |
| compat (Core reader), with exit 5 | match | |
| **compat/zstd-required-flag, Core reader, any order** | **MISMATCH risk** | With HDR-6 and step-10 checks in any order (§13), a Core reader reading BLB-2 as "ZSTD known to the reader" also finds **BLB-2**, so it may exit **6** (`blob.encoding`) instead of 5. The same happens for every zstd fixture under a Core reader ({BLB-2, HDR-6} gives exits {5, 6}). See F1. |

### 2.4 Sweeps (by code, my reader)

- **Truncation:** every prefix shorter than 88 bytes gives `hdr.too-short`, and every longer prefix gives `trl.magic`, as AC-ROB-2 requires. Appending 1 byte or 4096 bytes gives `trl.magic`.
- **Flips:** no single-byte flip is accepted. Histogram for worked-example (1112 flips): `trl.hash` 1024, `blob.hash` 18, `trl.index-range` 32, `hdr.magic` 16, `trl.magic` 16, `hdr.major-version` 4, `hdr.hash-alg` 2. Every flip inside the index stops at TRL-3 (F13).
- **AC-LIM-2 boundaries:** 4 fails / 5 passes, 458 / 459, 14 / 15, as stated.

### 2.5 Two facts established by code

- **Unicode versions disagree on PATH-2.** The path `"x́\U000113CE"` is NFC under Unicode 15.0 (system `python3` 3.12) and **not** NFC under 16.0 (`python3.14`). U+113CE is a new combining mark with ccc 9. Unicode 15.1 added only CJK ideographs, so a 15.1 reader behaves like 15.0 here. Two conforming readers disagree (F12).
- **NFD expansion on HFS+.** 127 × U+0390 is a valid 254-byte NFC segment. In NFD it is 381 UTF-16 units, which exceeds HFS+'s 255-unit limit (F40).

## 3. Generator review against the spec

The generator (`chst.py`, `check.py`, `catalog.py`, `reports.py`, `gen.py`) agrees with my independent decoder on every byte and report. Issues:

1. **The checker stops early and hides co-violations.**
   - `check.py` returns at SEC-4 before SEC-5 is checked; this is the SEC-4 mismatch.
   - It returns at HDR-6 and SEC-2 before any step-10 rule; this hides the BLB-2 / HDR-6 problem.
   - So README's guarantee ("finds the targeted rule and nothing else") doesn't hold for SEC-4 or for compat.
2. **CAN-2 interpretation.** `first` de-duplicates the table's keys before comparing, which goes beyond README item 2's stated reading. That is how BLB-5 avoids a CAN-2 violation. Either adopt the wording in F5, or list `canon.blob-order` in BLB-5's and BLB-7's `details`.
3. **Stricter than the spec.** The checker requires KV_METADATA `record_size == 1` and reports it as SEC-4. The spec only requires ≥ 1 (SEC-4), with SEC-5 when flags are known. No fixture is affected; see F30.
4. **No Core-reader mode.** `check()` is an Extended reader. The compat expectations ("Core-only reader") are asserted by a hand-written condition in `gen.py`, never by a Core-mode check. My Core-mode run confirms them, but the generator doesn't prove them. Add a `known_flags` parameter to `check()`.
5. **Self-fulfilling expectations.** For attacks and hostile fixtures, `details` is whatever `check()` returned; hostile fixtures are only required to be "all malformed". Write the expected detail sets into `catalog.py` and assert they are equal.
6. **`zstd_decode` accepts only its own frame shape** (`desc == 0xE0`, Raw/RLE blocks). Any other valid RFC 8878 frame would be classed as ZST-2. That's fine for its own fixtures, but it isn't a spec-level ZST-2 check, and no fixture has a Compressed block (F39).
7. **`synth-entries` is quadratic.** `relayout` builds the pool with `bytes +=`. Measured: 65,536 entries took 2.8 s; 262,144 took 37.8 s; 1,048,577 took **641 s with 1.0 GiB RSS**. AC-LIM-3 runs it twice, so about 21 minutes in fast mode, on every push. Use `b"".join`.
8. **`materialize --reverse` is weaker than AC-DET-1 claims.**
   - It uses unseeded `random.Random()` and doesn't log the seed, so failures aren't reproducible.
   - `_mkdirs` creates ancestors in forward order whatever the list order.
   - It swallows `FileExistsError`, so on a case-insensitive filesystem the unicode-case tree would silently merge.
9. **Reports.** `reports.py` always names section 0x10 `KV_METADATA` and always emits attribute fields when the flag is set; there's no Core view for inspect or verify. It falls back to hex for a non-UTF-8 PATH_POOL. Appendix B defines none of these (F33).
10. **Correct and independent.** The checks pass: SHA-256 comes only from `hashlib`, nothing invokes the Rust code, the worked example is cross-checked against the spec's hex dump, and categories and exits are parsed from the spec. Building the sparse key needs Python to hash 5 GiB at build time, which is acceptable.

## 4. Findings

Severity: **B** = blocking (fix before `plan-v1`), **S** = should fix, **M** = minor.

| ID | Spec section | Sev | Problem | Proposed fix |
|---|---|---|---|---|
| F1 | §13, HDR-6, SEC-2, BLB-2 | B | Steps 8–10 "MAY be performed in any order", so an unsupported file (an unknown required flag or critical section) can be reported as `malformed`. Verified: a Core reader may give exit 6 for every ZSTD file, against AC-COMPAT-1's 5. A future required flag may also change how the index is interpreted, so structural checks on it are meaningless. | Replace the step-ordering sentence with: "Steps 1–9 MUST be performed in order. Within step 9, SEC-2 MUST be evaluated over every section header (after SEC-1 framing) before SEC-3…SEC-5. A reader MUST NOT report any step-10 or step-11 rule for a file that violates HDR-6 or SEC-2." Reword BLB-2 as: "`encoding` MUST be 0, or 1 when the `ZSTD` flag is set and the reader implements it." |
| F2 | §13, §16, AC-NEG-2 | S | For multi-violation files, the reported detail (and sometimes the exit code: malformed vs limit-exceeded) isn't deterministic. That weakens D12's "the detail code names the rule that fired", forces `details` lists, and makes Rust-vs-TS parity on real corrupt files untestable. | Make step 10 a total order: "Report the first violation found in this order, scanning records in table order within each item: (a) BLB-1, BLB-2, BLB-3, ZST-3, LIM-6 per blob record; (b) BLB-4; (c) BLB-5; (d) ENT-1, ENT-2, ENT-3, ENT-4 per entry; (e) ENT-5; (f) CAN-3; (g) PATH-1…PATH-10 per entry, in rule order; (h) CAN-1; (i) ENT-6; (j) PATH-11; (k) BLB-7; (l) CAN-2; (m) FLG-1; (n) ATT-1; (o) KV-1; (p) LIM-5." Then each fixture has exactly one `detail`. This also settles DESIGN §9 open item 2. |
| F3 | §13 step 6 | S | The order of TRL-2, LIM-2 and LIM-4 isn't stated. hostile/index-length-huge violates all three (exit 6 vs 8). | "6. TRL-2, then LIM-2, then LIM-4, in that order, before reading the index." |
| F4 | §6 SEC-4/SEC-5 | S | `record_size` below the base also violates SEC-5 when all flags are known (the SEC-4 fixture does). | SEC-5: "…if `record_size` satisfies SEC-4 and the reader knows every flag set…". Or rely on F2's order. |
| F5 | §11 CAN-2 | S | Literal CAN-2 is also violated by the BLB-5 and BLB-7 fixtures (verified). | "CAN-2: let K be the distinct keys referenced by file entries, in order of first reference. The first \|K\| blob records MUST have exactly the keys K, in that order. Any further records are unreferenced (BLB-7) or duplicate keys (BLB-5), and are not CAN-2 violations." |
| F6 | §9 PATH-3/4/5/8, ENT-5/6, CAN-3 | S | The overlaps are built into the rules (DESIGN §9 item 2). The ENT-5 / PATH-3 overlap also exists for path-length-max. | PATH-3: "path length at most 4096 bytes, and every segment at most 255 bytes" (emptiness belongs to PATH-4; PATH-4 also forbids the empty path). PATH-8: "No segment other than `.` and `..` may end in…". ENT-6 and PATH-* are "evaluated only for entries satisfying ENT-5". CAN-3: "evaluated only when ENT-5 holds for every entry". Or adopt F2's order. |
| F7 | §10.1 LIM-1, LIM-2 | M | LIM-1 can't be reached. LIM-2 (≤ 2³²) plus SEC-4 (≥ 48) caps the entry count at 89,478,485, below 2³²−1. LIM-2 has no fixture. | Delete LIM-1 and add the derived bound as a note. Keep LIM-2. After F3, add a sparse invalid recipe containing only a header and a trailer with `index_offset` 32 and `index_length` 2³²+1 (`file_length` 2³²+89); LIM-2 fires before the index is read. Teach AC-NEG-1/2 to materialise `*.recipe.json`. |
| F8 | §10.2 LIM-6, §12.5 | S | "`raw_length / stored_length`" is undefined for `stored_length` 0 (division by zero at step 10, before step 11's ZST-2), and the arithmetic isn't specified. The generator silently skips `stored == 0`. | "LIM-6 is violated iff `raw_length > limit × stored_length`, computed without overflow (an overflow is a violation). `encoding` 1 with `stored_length` < 4 is ZST-2, checked in step 10." Name the CLI flag (`--max-ratio`). |
| F9 | §10.2 LIM-5, App. B | S | The sum of `raw_length` over all references can exceed u64: zstd raw sizes go up to 1000× stored, times 10⁶ references. | "LIM-5's sum MUST be computed without overflow; a sum ≥ 2⁶⁴ exceeds every limit." State that `summary.*_bytes` may need decimal strings. |
| F10 | §12.5, AC-X-ZSTD-2 | B (Extended) | Zstandard memory isn't bounded. A frame may declare a Window_Size of terabytes or a large single-segment FCS. libzstd's default cap (2²⁷) differs from other decoders, so readers diverge, and memory can reach 128 MiB+. AC-X-ZSTD-2's counting `GlobalAlloc` **doesn't see libzstd's C `malloc`**, so "peak heap < 8 MiB" proves nothing about the decoder. | Add to ZST-2: "Window_Size (or Frame_Content_Size when Single_Segment_Flag is 1) MUST be ≤ 8 MiB; Dictionary_ID MUST be absent or 0; if Frame_Content_Size is present it MUST equal `raw_length` (otherwise ZST-1)." Readers set `windowLogMax = 23`. Change AC-X-ZSTD-2 to measure process RSS (`/usr/bin/time -f %M` on the CLI) with a hostile max-window frame. |
| F11 | §12.5 ZST-1/ZST-2 | M | It's unclear whether a header FCS that disagrees with `raw_length` (the ZST-1 fixture declares 8193) is ZST-1 or ZST-2. Decoders that stop at `raw_length` see "output too long". | Covered by F10's wording (FCS ≠ `raw_length` gives ZST-1). |
| F12 | §9 PATH-2, D8, D16 | S | "Unicode 15.1 or later" lets conforming readers disagree. Verified: `x́\U000113CE` is NFC under 15.x and not under 16.0. Rust's crate, Python 3.14 and Node's ICU each ship their own version, and the next Python moves to Unicode 17. | Pin it: "PATH-2 uses exactly Unicode 16.0. A path containing a code point unassigned (General_Category Cn) in Unicode 16.0 violates PATH-2; W-3 refuses such names." Pin the Rust `unicode-normalization` version with 16.0 tables and assert it in AC-ENG-6, alongside the Node ICU Unicode version for TS. Add a fixture with the string above. |
| F13 | AC-ROB-1, -3, -4 | S | Raw byte damage stops at TRL-3. Verified: 1024 of 1112 flips give `trl.hash`, and none reaches a section, entry, path or canonical rule. libFuzzer can't forge SHA-256, so AC-ROB-4 hardly fuzzes the structural parser at all. AC-ROB-4W already recomputes the hash; AC-ROB-4 doesn't. | Fuzz targets take an index body and synthesise the header, trailer and correct structure hash before calling the reader (`open_verify_rehash`, plus the existing raw target). AC-ROB-3 adds hash-recomputed mutations. AC-ROB-1 additionally asserts, on a hash-recomputing sweep, that at least 15 distinct detail codes occur. |
| F14 | AC-SAFE-3, EXT-4/7 | S | It can pass without proving the cleanup of a partially filled staging directory. EXT-3 doesn't forbid running step 11 before writing, and an extractor that pre-verifies writes nothing. | Either require streaming in EXT-7 ("content MUST be verified while it is written, not in a separate pre-pass"), or add a `chst-fs` test with a hook asserting that ≥ 1 file existed in staging when the BLB-6 error was raised, and that staging is gone afterwards. |
| F15 | AC-SAFE-1 | M | Every attack is rejected at step 10, before any filesystem call, so only the validator is tested. There's no evidence the extractor's create layer resists a name that slipped through. | Add a `chst-fs` unit test that feeds hostile names (`..`, `/x`, `a/../..`, `C:`) directly to the create-entry layer and asserts refusal with nothing created. |
| F16 | §15 EXT-1, EXT-4 | B | Destination race. The final rename uses plain `rename`/`MoveFileEx`: on POSIX that **silently replaces an empty directory**, or a symlink, created at the destination after the EXT-1 check. It's also unspecified whether EXT-1 uses lstat (a dangling symlink at the destination). | EXT-1: "…MUST NOT exist (checked without following a final symlink)". EXT-4: "The final rename MUST NOT replace an existing object: `renameat2(RENAME_NOREPLACE)` on Linux, `renameatx_np(RENAME_EXCL)` on macOS, `SetFileInformationByHandle(FileRenameInfo, ReplaceIfExists=FALSE)` on Windows. If the destination exists by then, the result is `refused` / `extract.dest-exists` and cleanup applies. If the filesystem doesn't support a no-replace rename, the result is `io`." |
| F17 | §15 EXT-4/EXT-8 | B | Staging-directory safety isn't specified: its name, how it's created, its permissions, and the threat model. In a shared parent (for example `/tmp/x`), another user could predict or pre-create the name, or, while the extractor holds a directory handle, rename that directory **out of staging**, so later writes land outside it (breaking EXT-6) even though no link is ever followed. | "The staging directory MUST be created with create-new semantics, with an unpredictable name (`.<dest>.chst-<random 128-bit hex>`) in the destination's parent, and with mode 0700 (Windows: a DACL granting only the current user). Its final mode is set just before the rename." State the threat model: "EXT-8 defends against other local principals who can write to the destination's parent." |
| F18 | §15 EXT-4 | B | Cleanup ("staging and all its contents MUST be removed") doesn't say it mustn't follow links. A link swapped in during cleanup turns a recursive delete into deletion outside staging. | "Cleanup MUST remove entries relative to open directory handles (`unlinkat`, or Windows handle-relative delete), never follow a link or reparse point, and never re-resolve a full path." |
| F19 | AC-SAFE-8, EXT-8 | S | The expected outcome depends on the implementation. An extractor holding the directory handle, as EXT-8 requires, never sees a symlink swapped in under the old name: it writes into the moved directory (success) or gets ENOENT (`io`), not `extract.unsafe-object`. On Windows, NtCreateFile returns the handle atomically, so there's no window at all. Also, a test hook isn't visible to an integration test through `cfg(test)`. | Define the hook point: on Unix, between `mkdirat` and the `openat(O_NOFOLLOW\|O_DIRECTORY)` that obtains the handle, which must then fail with ELOOP or ENOTDIR and give `unsafe-object`. On Windows, between creating a directory and reopening it by name, if the implementation ever reopens. Assert "nothing outside staging; result is `refused/extract.unsafe-object` or, where no reopen happens, success with all files inside staging". Gate the hook behind a non-default cargo feature (`test-hooks`) and state that in D13/D15. |
| F20 | §15 EXT-6 | M | It contradicts EXT-4: the final rename creates the destination, which is outside staging. | "…except the destination created by EXT-4's final rename". |
| F21 | §15 EXT-8 | M | Canonical order isn't depth-first (`a`, `a-b`, `a.b`, `a/b`), so an extractor must reopen earlier directories. How it does so safely isn't specified. | "A previously created directory MAY be reopened only by walking from the staging root handle, one segment at a time, with no-follow directory opens, checking each opened object as in EXT-8." |
| F22 | §14 W-6 | S | How "inside the source tree" is decided isn't specified: symlinks, `..`, bind mounts, case-insensitive aliases. | "Determined by comparing the file identity (st_dev/st_ino, or the Windows volume serial number and file ID) of the output's parent directory and each of its ancestors with the source root." |
| F23 | §14 W-4, W-5 | S | The walk and the second read are TOCTOU-prone: a directory swapped for a symlink mid-walk makes a path-based walk pack outside files (W-5's intent, but the mechanism isn't stated). This is also DESIGN §9 item 4. | W-5: "The walk MUST open each directory and file relative to its parent's handle, with no-follow semantics. Pass 2 MUST verify that the opened file has the same identity as in pass 1; otherwise `pack.source-changed`." |
| F24 | §14 | S | Pack doesn't apply reader limits. A 100 GiB tree, or one with 2M entries, packs successfully, then `verify` with default limits fails `limit-exceeded`. | Add W-10: "Pack MUST refuse (`limit-exceeded`, same detail codes) to write a container that a reader with the same limit settings would reject under LIM-3…LIM-5. It accepts the same `--max-*` flags." |
| F25 | §12.8 | S (Extended) | Pattern semantics are ambiguous: `?` "one character" against "byte-for-byte"; `[...]` (negation? ranges by code point?); escaping; whether the pattern is NFC-normalised; whether `a/**` matches `a`. **Contradiction:** if added ancestors count as "selected", then `docs/*.txt` selects `docs`, whose subtree includes `docs/empty`, but AC-X-SEL-1 expects `docs/empty` to be excluded. | "Patterns are NFC-normalised before matching. `?` matches one code point other than `/`. `[...]` matches one code point from a set of literals and `x-y` ranges (by code point); a leading `!` negates; `/` never matches. There is no escape character, and a pattern containing `\` is a usage error. `**` as a whole segment matches zero or more segments, so `a/**` matches `a` and everything under it. Directories added only as ancestors are not themselves selected." |
| F26 | §12.8 Exclude | M | It's unclear whether an excluded but unportable name is still refused (W-3), and whether excluded directories are traversed. | "Exclusion is applied during the walk, before W-3. Excluded directories are not opened or descended." |
| F27 | §12.6, EXT-5 | S (Extended) | How modes and mtimes are applied isn't specified. A directory with mode 0555 applied at creation blocks its children; directory mtimes change as children are created; umask interaction isn't stated. | "Extractors apply file modes with `fchmod` on the open handle, and apply directory modes and all mtimes after all entries are written, in reverse canonical order. Modes are applied as stored, masked with 0o777 and not subject to the umask." Or state the opposite explicitly. |
| F28 | §12.7 KV-1, §11 | M | An empty KV section (zero pairs) is valid, giving two encodings of "no metadata". | KV-1: "…the payload MUST contain at least one pair." |
| F29 | §6 SEC-3 | M | It's unclear whether "further sections ascending" compares only the further sections (so KV 0x10 may follow 0x80000003), and that the first three types can't recur. | "Sections after the first three MUST have strictly ascending `type` values, compared as u32 among themselves, and none may have one of the first three types." |
| F30 | §6 SEC-4/SEC-5 | S | Under an unknown optional flag, SEC-5's relaxation lets KV_METADATA's `record_size` exceed 1 ("ignore extra bytes per record"), which is meaningless for a byte stream. | SEC-4: "For PATH_POOL and KV_METADATA it MUST be exactly 1." This matches the generator's current behaviour. |
| F31 | §4 HDR-4, D6 | M | The key width is fixed at 32 bytes in every record, so `hash_alg` can't really change. D6's "new ID gated by a required flag" duplicates HDR-4. | "Every `hash_alg` value MUST have a 32-byte output; a different width needs a new major version." Drop "gated by a required flag" from D6. |
| F32 | §4 `minor_version`, D9 | M | This field exists only by convention. Because writers record the spec revision, two writers following 1.0 and 1.1 produce different bytes for the same tree, which contradicts D9's "exactly one encoding per input tree". | Either "Writers MUST write `minor_version` 0 unless the revision changes the encoding", or state that canonical form is per `minor_version`. |
| F33 | App. B | S | Undefined report cases: names for unknown flag bits in `summary.*_flags`; whether a Core reader's inspect names section 0x10 `KV_METADATA` or `unknown`; whether a Core reader's inspect shows attribute fields when `ENTRY_ATTRS` is set; negative integers below −(2⁵³−1); `ok`/`warnings` for verify. The compat fixtures compare only `list`. | "Unknown flag bits are named `bit<N>`. `name` is `unknown` for any type the reader doesn't implement. Attribute fields appear only if the reader implements `ENTRY_ATTRS`. Integers outside ±(2⁵³−1) are decimal strings." Add `verify.json` and `inspect.json` for every compat fixture with exit 0. |
| F34 | §13 step 11 | M | BLB-6 is optional for list and inspect, so the Rust and TS readers may disagree (one succeeds, one fails) on the same file. | "List and inspect MUST NOT perform step 11." |
| F35 | AC-NEG-1, compound rules | S | One fixture per rule ID leaves sub-conditions unproved: ATT-1 (mode > 0o777, reserved ≠ 0); KV-1 (bad UTF-8, key length 0 or > 255, value > 65,536, truncated pair, duplicate key); BLB-4 (zero blobs with `index_offset` ≠ 32, a short last blob); TRL-2 (`index_offset` < 32, overflow); SEC-1 (a header straddling the index end); PATH-3 (empty path, `path_length` 0); ENT-1 (type 0); PATH-9 (each superscript, `COM0`); FLG-1 (each of its three flags, both directions); SEC-5 for ENTRY_TABLE 64 without the flag. | Make AC-NEG-1 require one fixture per sub-condition ID (for example `ATT-1-mode`) listed in a table in ACCEPTANCE §3.4, and add those fixtures. |
| F36 | AC-LIM-3, generator | S | `synth-entries 1048577` took 641 s and 1 GiB RSS (measured). AC-LIM-3 runs two such builds in fast mode on every push, about 21 minutes. | Build the pool with `b"".join` and stream records. Target under 30 s. |
| F37 | AC-DET-1, `gen materialize --reverse` | M | The randomisation is unseeded and its seed isn't logged; creation order isn't actually reversed for nested directories. | Seed from `$CHST_DET_SEED` (default fixed), log it, and create the deepest directories first using `makedirs` of the reversed list. |
| F38 | AC-SAFE-10 | S | On GitHub Windows runners, 8.3 generation is normally disabled on the data volume, so only the trivial "no collision" branch runs. The criterion passes without testing EXT-2's short-name case. | Before extracting, enable it (`fsutil 8dot3name set <vol> 0`; runners are admin) or use a VHD with 8.3 enabled, and require the collision branch (exit 9) in CI. Log `fsutil 8dot3name query`. |
| F39 | AC-X-TS-1, extended fixtures | S (Extended) | Every zstd fixture uses RLE blocks, single segment and no checksum. A TS reader that decodes only Raw/RLE passes AC-X-TS-1, and nothing tests Compressed blocks, windows or checksums against the readers. | Add an extended valid fixture with a constant, pre-computed Compressed-block frame (with checksum), embedded as hex in `catalog.py`. Its decoded content is checked against the tree, so independence is kept. |
| F40 | §15.1 macOS row | M | HFS+ limits names to 255 UTF-16 units **after NFD**. A valid 254-byte segment (127 × U+0390) becomes 381 units (verified), so a valid archive fails to extract on HFS+. | Note it in §15.1 as a known `io` failure. Or add PATH-3b: "NFD form of each segment ≤ 255 UTF-16 code units". |
| F41 | §15.1 Linux and WSL rows | M | "Linux: case-sensitive" is false for ext4 casefold directories and vfat, ntfs3 and CIFS mounts. "WSL: use the Windows rows" isn't actionable for a Linux binary. | "Linux: depends on the filesystem; EXT-2 handles case-insensitive directories. WSL `/mnt/<drive>`: the Linux build applies only the Unix rules; the format rules already make archives safe there." |
| F42 | §9 PATH-6 | M | C1 controls (U+0080–009F) and bidi overrides (U+202A–202E, U+2066–2069) are allowed. They enable filename spoofing in `list` text output. | Either add them to PATH-6, or require the text renderer to escape them. |
| F43 | §15 EXT-4 | M | A crash leaves the staging directory, and nothing tells the user how to recognise it. | Specify the name pattern (F17) and document manual cleanup. |
| F44 | ACCEPTANCE §1.2 | M | The expect.json schema differs per directory (attacks and hostile have no `detail`; compat has no `rule` or `category`), against §1.2's single schema. | Document each directory's schema, or unify them. |
| F45 | §10.2 CLI flags | M | `--max-entries`, `--max-index-bytes` and `--max-total-bytes` appear only in ACCEPTANCE, and LIM-6 has no flag. | List the CLI flags normatively, in a CLI section or Appendix B, including `--max-ratio`. |
| F46 | DESIGN §9 (Windows reparse) | M | Skipping OneDrive placeholders can silently drop whole folders of user data, with only a warning and exit 0. | Use a distinct warning detail (`pack.skipped-placeholder`) and include a `skipped` count in `summary`. Consider `--strict`, which makes any skip an error. |

## 5. Recommendations on DESIGN.md §9 open items

1. **LIM-1 and LIM-2 without fixtures.**
   - **LIM-1:** option (c), delete it. It is implied by LIM-2 + SEC-4 (≤ 89,478,485 entries), so it's untestable by construction. Option (a) would distort the step order.
   - **LIM-2:** option (b), plus F3's fixed order inside step 6. The recipe needs only a header and a trailer, because LIM-2 fires before the index is read. With LIM-2 checked before LIM-4, no `--max-index-bytes` argument is needed.
2. **Overlapping rules.** Tighten them, preferably with F2's total order, which also fixes SEC-4/SEC-5, CAN-2/BLB-5/BLB-7, step-6 ambiguity and future overlaps. If you prefer per-rule wording, use F6.
3. **CAN-2 and unreferenced blobs.** Agree with adding a sentence, but use F5's wording. The generator's reading also has to cover duplicate keys (BLB-5), which the proposed sentence doesn't.
4. **PATH_MAX.** Agree, and make it normative: handle-relative walking for pack (F23), and handle-relative reopen for extract (F21). The tools' `dir_fd` approach is right.
5. **Empty container.** Agree it's valid. The 136-byte fixture is verified.
6. **Hard links (N2).** Agree. Also say that pass 2 checks file identity (F23).
7. **ENTRY_ATTRS layout.** The layout is fine. Specify how attributes are applied (F27) and the JSON encoding for negative mtimes (F33). Add fixtures for negative mtime and for nanos = 999,999,999.
8. **Reparse points and cloud placeholders.** Accept for v1, with F46's distinct warning and count.
9. **Runner feasibility.** Accept, but add AC-SAFE-10's 8.3 setup (F38) to the first full CI run's checklist.
10. **`node:zlib` zstd being experimental.** Decide now rather than at Extended, because it determines whether AC-X-TS-3's "no runtime dependencies" can hold. I'd accept `node:zlib` on Node 24 with a pinned minor version, as long as F10's window limit can be enforced through it (`ZSTD_d_windowLogMax`). If it can't, approve `fzstd` now. Either way, F39's Compressed-block fixture is needed to prove the choice works.

## 6. Anything else the plan missed

- **Threat model:** say who EXT-8 defends against (F17). Without that, the race requirements can't be judged, and the most effective control (a 0700 staging directory) is missing.
- **Data-loss paths are tested less than the format is:**
  - destination replacement (F16);
  - cleanup following links (F18);
  - pack silently dropping skipped content (F46);
  - pack producing files its own verify rejects (F24).
- **Several acceptance criteria can pass without proving their claim:**
  - AC-ROB-1, -3, -4 (stop at TRL-3, F13);
  - AC-SAFE-3 (F14);
  - AC-SAFE-10 (F38);
  - AC-X-ZSTD-2 (C allocations invisible, F10);
  - AC-X-TS-1 for zstd (F39);
  - AC-NEG-1 for compound rules (F35).
- **Prior-art choices justified mainly by convention:**
  - `minor_version` (F32);
  - the redundant `index_offset`/`index_length` pair. TRL-2 makes one of them derivable. Keeping both as a cross-check is fine, but it's a convention, not a need;
  - `hash_alg` alongside required flags (F31).

  The PNG-style magic is cheap and defensible.
- **Fixtures are correct.** No byte or report mismatch was found in any valid fixture, the sparse recipe or the worked example. Every bad fixture fails for its intended reason. The open problems are the spec ambiguities above, which let a conforming reader disagree with three expectations (BLB-5, BLB-7, SEC-4) and with AC-COMPAT-1's zstd case.

## Files

All the scratch scripts and outputs are in `/tmp/claude-1000/-home-jaron-projects-container-format-rs/e937457e-5049-490d-9241-b7fa1e66df9b/scratchpad/chst-review/review-work/`:
- chst_ref.py
- run_fixtures.py
- run1.txt
- worked.py
- compat_all.py
- mutdiff.py
- misc.py
- sweeps.py
- zstdwalk.py
- sparse.py
- ccc16.json
- demo.txt

The temporary synth container was deleted. Nothing outside `review-work/` was modified.

---

## Part 2: closure table

### How each round 6 finding was closed (planner's claims)

Owner decisions that shaped the closures:
- F1, F2 with F5, F10, F16, F17, F18 and all ten generator fixes were accepted as proposed.
- **F6:** only the PATH-8 exemption for `.` and `..` was taken. PATH-3's literal wording
  still covers empty segments, so §13 checks PATH-4 *before* PATH-3 to keep PATH-4
  reachable. This deviates from F2's "PATH-1…PATH-10 in rule order".
- **F12:** the cheaper option. Exactly Unicode 16.0 tables in every reader. Code points
  added after 16.0 may be judged differently by other tools, and fixture `PATH-2-unicode16`
  documents that. No General_Category (Cn) rule was added.
- **F42:** the characters are banned (PATH-6), and `list`'s text output escapes the
  non-printing characters that remain allowed.
- **F40** is documented only; **F44** is done as per-directory schemas; **F46** has no
  `--strict`.
- **Node zstd:** `node:zlib` is kept, based on Node's documentation listing
  `ZSTD_d_windowLogMax`. That wasn't verified by running Node.

| ID | Closed by (claimed) |
|---|---|
| F1 | §13: steps 1–9 in order. HDR-6 and SEC-2 stop evaluation. BLB-2 now requires the reader to implement ZSTD. |
| F2 | §13 is a total order, with only the first violation reported; §16 and D12 updated. Each bad fixture has one exact `detail`, so `details` lists are gone from AC-NEG-2. |
| F3 | §13 step 6: TRL-2, then LIM-2, then LIM-4. |
| F4 | SEC-5 applies only when SEC-4 holds. |
| F5 | CAN-2 reworded as proposed; the checker implements that wording. |
| F6 | PATH-8 exempts `.` and `..`. The rest is superseded by F2 (PATH-4 is checked before PATH-3). |
| F7 | LIM-1 retired, with the derived bound of 89,478,485 noted. A sparse LIM-2 recipe fixture added. AC-NEG-1/2 can now use sparse-recipe fixtures (`fixture_file` helper). |
| F8 | LIM-6 defined as `raw > limit × stored`, with no overflow. ZST-2 catches blobs shorter than 4 bytes in step 10. `--max-ratio` added. |
| F9 | LIM-5's sum must not overflow, and large integers are decimal strings in every report. |
| F10 | ZST-2 caps the window at 8 MiB, requires no dictionary, checks the checksum, and sets `windowLogMax` = 23; a content size that disagrees with `raw_length` is ZST-1. AC-X-ZSTD-2 measures process peak RSS. New `ZST-2-window` and `ZST-2-dictid` fixtures. |
| F11 | Covered by F10's content-size rule. |
| F12 | Exactly Unicode 16.0 in every reader (AC-ENG-6, new AC-ENG-8, AC-X-TS-3). Post-16.0 differences documented. New fixture `PATH-2-unicode16`. |
| F13 | AC-ROB-1 adds a `--rehash` sweep needing at least 15 distinct codes (the generator's checker finds 26). Accepted flips are allowed only where they create a different valid file. AC-ROB-3 adds hash-recomputed mutations, and AC-ROB-4 a new `open_verify_rehash` fuzz target. |
| F14 | EXT-7 requires verification while writing; AC-SAFE-3 adds a hook test that a file was already in staging. |
| F15 | New AC-SAFE-12: test the create-entry layer on its own. |
| F16 | EXT-1 doesn't follow a final symlink. EXT-4's final rename never replaces anything (named calls per OS). AC-SAFE-2 adds a dangling-symlink case; new AC-SAFE-13 tests a destination created mid-extract. |
| F17 | Threat model stated in §15. Staging is create-new, owner-only (0700) and unpredictably named (`.<dest>.chst-<32 hex>`). New AC-SAFE-14. |
| F18 | Cleanup works relative to directory handles and never follows a link. New AC-SAFE-15. |
| F19 | AC-SAFE-8's hook points defined per OS. Hooks are behind a non-default `test-hooks` Cargo feature (D13). |
| F20 | EXT-6 excepts the final rename. |
| F21 | EXT-8: earlier directories are reopened only by walking from the staging root. |
| F22 | W-6 decides "inside the source" by file identity. AC-PACK-5 adds `..` and symlink routes. |
| F23 | W-5: the walk is relative to directory handles, and pass 2 checks file identity. AC-PACK-3 adds a same-bytes, different-file case; new AC-PACK-10 tests a walk race. |
| F24 | New W-10: pack applies the reader limits. New AC-PACK-11. |
| F25 | §12.8's pattern rules spelled out; ancestor directories created for a match aren't themselves selected. AC-X-SEL-1 adds `?`, `[...]`, `[!...]`, `**` and backslash cases. |
| F26 | Exclusion happens during the walk, before W-3. AC-X-EXCL-1 adds an excluded, unreadable directory holding an unportable name. |
| F27 | §12.6 says how and when modes and mtimes are applied. AC-X-ATTR-1 adds read-only-directory, umask and mtime cases. |
| F28 | KV-1 requires at least one pair. New `KV-1-empty` fixture. |
| F29 | SEC-3 reworded. New `SEC-3-repeat` fixture. |
| F30 | SEC-4 requires exactly 1 for PATH_POOL and KV_METADATA. New `SEC-4-kv` fixture. |
| F31 | HDR-4 fixes the hash width at 32 bytes; D6's "gated by a required flag" removed. |
| F32 | Writers write `minor_version` 0 unless a revision changes the encoding (§4, D9). |
| F33 | Appendix B: unknown flag bits named `bit<N>`, unimplemented sections named `unknown`, attribute fields only if implemented, integers outside ±(2⁵³−1) as strings. Compat fixtures gain the Core reader's verify and inspect reports, and AC-COMPAT-1 compares all three. |
| F34 | List and inspect MUST NOT run step 11. AC-NEG-3 checks they succeed on the BLB-6 fixture. |
| F35 | 39 sub-condition fixtures added (23 Core, 16 Extended), and AC-NEG-1 and AC-X-NEG-1 list each one. Two FLG-1 conditions are documented as unreachable. |
| F36 | The path pool is built with a join: 641 s → 3.8 s for 1,048,577 entries. |
| F37 | `materialize --reverse` is seeded (`CHST_DET_SEED`), prints the seed, and creates directories deepest-first. |
| F38 | AC-SAFE-10 enables 8.3 names and requires the collision branch; if 8.3 can't be enabled, the check FAILs. |
| F39 | New `extended/valid/zstd-compressed`: a real Compressed-block frame with a checksum, stored as fixed bytes. |
| F40 | §15.1 documents the HFS+ limit only. |
| F41 | §15.1's Linux and WSL rows rewritten. |
| F42 | PATH-6 bans C1 and the bidi characters; Appendix C requires `list`'s text output to escape the non-printing characters that remain allowed. New PATH-6 fixtures (C1, override, isolate), two new attacks (`c1-control`, `bidi-override`), a `nonprinting` valid fixture, and new AC-CLI-3. |
| F43 | The staging name pattern and manual cleanup after a crash are documented in EXT-4. |
| F44 | Each fixture directory's `expect.json` schema documented in ACCEPTANCE §1.2. |
| F45 | New FORMAT_SPEC Appendix C defines the CLI's commands, flags, errors and text output. |
| F46 | New `pack.skipped-placeholder` warning, and `summary.skipped` in the pack report (no `--strict`). New AC-PACK-12; AC-CLI-2 checks the count. |

**The ten generator fixes (claimed):**
1. The checker no longer stops early; co-violations are recorded in `also_violates`.
2. CAN-2 follows F5's wording.
3. KV record size 1 now matches the spec (F30).
4. There's a Core-reader mode, used to prove the compat expectations.
5. Expected rules for attacks and hostile fixtures are written in the catalog, not taken
   from the checker.
6. Frame headers are parsed per RFC 8878, with decoding through the standard library's
   `compression.zstd`.
7. The path pool is built in linear time (F36).
8. `materialize` is seeded and reversed, and never merges two names.
9. Reports are produced per reader view (F33).
10. The independence guarantees were re-checked.

Known unverified items (claimed open):
- runner feasibility (fuzzing on Windows, the dated nightly, disk for AC-ROB-7, and
  `fsutil 8dot3name set` on the runner);
- `unicode-normalization`'s Unicode version, and Node 24's ICU Unicode version;
- `node:zlib` zstd is marked Experimental.
