# Chst — Design

> Status: **DRAFT for independent review** (revised after review round 1, see §9).
> The format is **Chst**, pronounced "chest". Its magic bytes are `CHST`, its file
> extension is `.chst`, and the CLI binary is `chst`.
>
> Companion documents: [`FORMAT_SPEC.md`](FORMAT_SPEC.md) (normative byte format and rules)
> and [`ACCEPTANCE.md`](ACCEPTANCE.md) (acceptance criteria with runnable checks).
> Where this document and `FORMAT_SPEC.md` disagree, `FORMAT_SPEC.md` wins.

## 1. Purpose and framing

Chst is a new, versioned container file format for **general file archives**: bundling a
directory tree into a single file, listing it, verifying it, and extracting it safely. It
ships as a Rust library and a thin CLI. The format is a fresh design; existing formats
are mentioned only to explain trade-offs.

Framing decisions (made before the architecture decisions):

| Topic | Decision |
|---|---|
| Primary use case | General file archive (pack / list / verify / extract of directory trees) |
| Mutability | **Write-once.** A container is built in one go and then only read. Edits mean rewriting. |
| Scale target | Up to a few GB of data and about 1M entries. The whole index can be held in memory. |
| Platforms | Unix (Linux, macOS) and Windows. Archives are portable by construction. |
| Delivery | Build **Core v1** first, then add Extended features one at a time through the same validation loop. |
| Core vs Extended | **One wire format version.** Extended features are optional capabilities flagged per file (D5). Adding one never forces a redesign. |

## 2. Feature set

**Core v1** is a smaller but complete format. **Extended v1** is Core plus the rows marked
Extended. IDs `#n` come from the original candidate list. IDs `Gn` are gaps added during
triage, and `Nn` are non-goals.

### 2.1 Core v1

| ID | Feature | Notes |
|---|---|---|
| #1 | `pack` a directory tree into one container | |
| #2 | `list` entries with metadata | |
| #3 | `extract` everything | Into a fresh destination only (D10) |
| #4 | `verify` structure and checksums without extracting | |
| #5 | `inspect`: header and index fields with byte offsets | |
| #8 | `--json` output for list, verify, inspect | Versioned schema (G9) |
| #13 | Per-blob content hashes plus a structure hash | BLAKE3 (D6) |
| #14 | Index for random access | Index at end (D1), typed sections (D4) |
| #15 | 64-bit sizes and offsets | D3 |
| #17 | Preserve empty directories | Explicit directory entries (D10b) |
| #18a | Extension *mechanism* (feature flags, skippable sections) | Split from #18; D5 |
| #19 | Deterministic output | Canonical form is mandatory (D9) |
| #21 | Deduplication: identical content stored once | **Moved from Stretch to Core**: falls out of D2/D2a |
| #23 | Safe extraction rules | D10 |
| #24 | Configurable resource limits | D11 |
| #25 | Stable error categories and exit codes | D12 |
| #26 | Never panic on malformed input | Fuzzed (V6) |
| #27 | Library crates with a thin CLI | D13 |
| #28 | Conformance fixtures with expected JSON | Built by an independent generator (V1) |
| G1 | Path encoding and normalisation rules | D8 |
| G2 | Format version and forward-compatibility policy | D5 |
| G3 | Duplicate and colliding path rules | D8, D9 |
| G4 | Extraction-destination conflict policy | D10 |
| G5 | Atomic container write (no partial output on failure) | Writer requirement |
| G6 | Bounded memory: entry data streamed, never fully buffered | Implementation requirement |
| G7 | Negative fixtures, each with its expected error | V3 |
| G8 | Fuzz targets for the reader | V6 |
| G9 | Versioned JSON report schema | `FORMAT_SPEC.md` Appendix B |

### 2.2 Extended v1 (Core plus these)

| ID | Feature | How it fits (see §6) |
|---|---|---|
| #6 | Selective extract by path or glob | CLI/library only; canonical sorting gives binary search |
| #7 | Exclude patterns when packing | Writer only |
| #12 | Per-blob compression: Zstandard or stored | Required flag `ZSTD` |
| #16 | Modification time and permission bits (never setuid) | Optional flag `ENTRY_ATTRS` (wider entry records) |
| #18b | Container key/value metadata (creator, comment) | Optional flag `KV_METADATA` (new skippable section) |
| TS | Read-only TypeScript reader that passes the conformance fixtures | Separate implementation; proves the spec is language-neutral |

### 2.3 Later

#9 extract one entry to stdout · #10 dry-run extract · #11 streaming (pack to stdout,
read from stdin by spooling) · #20 symlinks (required flag + new entry type) · #22 append
(new data, then a new index and trailer) · #29 compare a container against a directory ·
extract-merge and `--overwrite` · secondary checksum of the original (uncompressed) content.

### 2.4 Non-goals

| ID | Non-goal | Behaviour |
|---|---|---|
| N1 | Encryption, signatures, authenticity | Hashes detect accidental corruption only |
| N2 | Hard links (as links) and special files (devices, FIFOs, sockets) | Special files are skipped with a warning; hard-linked names are packed as independent files |
| N3 | Multi-volume or split containers | |
| N4 | Salvage or repair of corrupted containers | Readers fail cleanly; `verify` reports the error |
| N5 | In-place editing | Follows from write-once |
| N6 | Sparse files | Stored as their full logical content |
| N7 | Extended attributes, ACLs and NTFS alternate data streams | Not stored; only a file's main data stream is packed |
| N8 | Owner and group IDs | Not stored |
| N9 | Anything over a network | |

Symlinks (#20) are *Later*, not a non-goal. In v1, pack skips them with a warning and never
follows them.

## 3. Architecture overview

### 3.1 File layout (D1)

```
offset 0                                                          end of file
┌──────────┬──────────────────────────────┬─────────────────────┬──────────┐
│ Header   │ Blob data                    │ Index               │ Trailer  │
│ 32 bytes │ blob 0 | blob 1 | ...        │ sections:           │ 56 bytes │
│ magic,   │ contiguous, first-reference  │  BLOB_TABLE         │ index    │
│ version, │ order, no gaps               │  ENTRY_TABLE        │ offset & │
│ flags,   │                              │  PATH_POOL          │ length,  │
│ hash alg │                              │  [optional sections]│ struct.  │
│          │                              │                     │ hash,    │
│          │                              │                     │ magic    │
└──────────┴──────────────────────────────┴─────────────────────┴──────────┘
  ▲ covered by structure hash ─────────────▲─────────────────────▲ (first 16 B)
                 each blob covered by its own content hash (its key)
```

- Every byte of the file is covered by some hash. Blob bytes are covered by their content
  hash, which is also their key. Header, index and trailer location fields are covered by
  the structure hash in the trailer. The trailer's own hash and magic are checked directly.
- **Entries** (path, type, blob key) are separate from **blobs** (stored bytes, location,
  lengths, encoding). Several entries may share one blob, which is how dedup works.

### 3.2 Crates and responsibilities (D13)

| Crate | Responsibility | Must not |
|---|---|---|
| `chst-format` | Encode and decode the byte format, every validation rule in `FORMAT_SPEC.md`, structured reports (list, inspect, verify). Works over any seekable byte source and any byte sink. | Touch the filesystem, walk directories, use `unsafe` |
| `chst-fs` | Pack: directory walk, path checks, double hashing. Extract: staging, create-new, permissions, Windows long paths. | Re-implement format parsing |
| `chst-cli` | Argument parsing, text and `--json` rendering, category→exit-code mapping | Contain format or safety logic |

All I/O is synchronous and blocking; there is no async runtime.

Planned repository layout, which `ACCEPTANCE.md` commands refer to:

```
crates/chst-format  crates/chst-fs  crates/chst-cli   # Rust workspace
fuzz/                         # cargo-fuzz targets over chst-format
tools/fixturegen/             # independent spec-driven Python generator (V1)
fixtures/                     # golden + negative fixtures, expected JSON, MANIFEST
ts-reader/                    # Extended: TypeScript read-only reader
check.sh                      # acceptance runner
EVIDENCE.md                   # ledger of claimed results; links CI runs
.github/workflows/            # CI: ./check.sh --full on Linux, macOS, Windows
```

### 3.3 Data flow

**Pack** (`chst-fs` → `chst-format` writer):
1. Walk the source tree without following symlinks. Skip symlinks, Windows junctions and
   other reparse points, and special files, each with a warning. Hard-linked names are packed as ordinary independent files (their content
   dedups to one blob).
2. Convert each relative path to NFC and check it against the path rules. Refuse the whole
   pack on any violation (`refused` / `pack.unportable-name`).
3. Sort all entries bytewise (canonical order). Hash each file (pass 1) to find the blob
   keys and duplicates.
4. Write the header. Then, in first-reference order, copy each unique blob while hashing it
   again (pass 2). If the second hash differs from the first → `refused` / `pack.source-changed`.
5. Write the index, then the trailer with the structure hash. Write to a temporary file
   next to the output and rename it into place only on success (G5).

**Verify** (`chst-format`):
1. Check the header and trailer. Bounds-check the index location against the file size and
   limits.
2. Read the index and check the structure hash.
3. Validate the sections, blobs, entries, paths and canonical form.
4. Stream every blob and check its content hash. Report.

**Extract** (`chst-fs`):
1. The destination must not exist.
2. Run full structural validation (verify steps 1–3) and the total-size limit before writing
   anything.
3. Create a fresh sibling staging directory and create entries in canonical order (parents
   come first) with create-new semantics. Stream each blob, checking its hash.
4. On success, rename the staging directory to the destination. On any error, delete the
   staging directory.

## 4. Decision log

Each decision records the options considered, the choice, why, and the consequences.
Detailed byte layouts live in `FORMAT_SPEC.md`.

### D1 — Index placement and overall layout
- **Options:** (A) header, data, index, fixed trailer; (B) index at front; (C) per-entry
  local headers plus an index at the end; (D) header pointer patched after writing.
- **Choice: A.**
- **Rationale:** One-pass writing with no need to know sizes in advance. Random access is
  one seek to the trailer plus one index read. There is a single source of truth for
  metadata. Pack-to-stdout (#11) and append (#22) stay possible later.
- **Rejected:** B forces two passes or a temp file to learn sizes before writing. C stores
  metadata twice, and when the copies disagree, different tools may trust different copies
  (a known source of security bugs). D needs seekable output and has no advantage over A.
- **Consequences:** Readers need seekable input; reading from stdin (Later) must spool to a
  temp file. Truncation is detected immediately, because the trailer magic or location
  check fails. The header still carries magic, version and flags, so a file can be
  identified from its first bytes.

### D2 — Entry→data mapping: content-addressed blobs
- **Options:** (A) each entry owns one data region; (B) entry table plus a numbered blob
  table; (C) blobs keyed by cryptographic hash; (D) chunked files.
- **Choice: C.** Entries refer to blobs by their 32-byte content hash.
- **Rationale:** Dedup is built in, and the key doubles as the integrity check. The user
  preferred the hash as identity over numeric references.
- **D2a — Unique keys, writer hashes before copying.** Keys must be unique in the blob
  table, and readers reject duplicate or unreferenced blobs. Because writing is one pass,
  the writer hashes each source file first (pass 1), then copies it while re-hashing
  (pass 2). A mismatch means the source changed during packing, and the pack is refused.
  **Dedup (#21) moves to Core.** *Rejected:* allowing duplicates gives weaker `verify`
  rules. Rewinding the output on a duplicate needs seekable output, which rules out
  pack-to-stdout.
- **D2b — The key hashes the stored bytes.** *Rejected:* hashing the original
  (uncompressed) content would make the identity independent of compression. Stored-byte
  hashing was chosen so `verify` never needs to decompress.
- **Consequences:**
  - In Core, stored bytes equal the original content, so nothing is lost.
  - In Extended, hashing before copying means compressing twice, or compressing to a temp
    file. That's a writer choice, not a format concern.
  - Dedup only matches blobs compressed with identical encoder settings.
  - Decoder-output corruption isn't covered by the key. It's mitigated by the mandatory
    original length (decoder output of a different length is an `integrity` error); a
    secondary checksum of the original content is Later.
  - One blob referenced many times can amplify extraction, which is bounded by the D11
    limits.

### D3 — Integer encoding
- **Options:** (A) fixed-width little-endian; (B) fixed-width big-endian; (C) varints;
  (D) fixed header with a varint index.
- **Choice: A.** All sizes and offsets are u64.
- **Rationale:** Field offsets are constant, which keeps `inspect` and the worked example
  simple and gives a small fuzz surface. The space cost is small next to the 32-byte keys.
- **Consequences:** Overlong encodings can't exist, so there are no canonical-integer rules.

### D4 — Index encoding
- **Options:** (A) fixed records plus a string pool; (B) TLV fields per record; (C) typed
  sections of fixed-size records; (D) an embedded CBOR or protobuf index.
- **Choice: C.** The index is a sequence of sections, each with a type, record size and
  record count. Core has `BLOB_TABLE`, `ENTRY_TABLE` and `PATH_POOL`.
- **Rationale:** Fixed field offsets as in A, plus two extension routes: new section types,
  or wider records with appended fields. `inspect` maps directly onto it.
- **Rejected:** B has variable offsets and needs ordering rules. D adds an external spec
  dependency and a canonical-encoding requirement, which doesn't suit a fresh design.

### D5 — Extensibility and compatibility
- **Options:** (A) version number only; (B) major version plus required and optional
  feature flags; (C) a must-understand bit per section only; (D) flags plus a minimum
  reader version.
- **Choice: B.**
  - **Major version:** changes only for incompatible restructures. Minor version is
    informational.
  - **Flags:** an unknown *required* flag means reject at open (`unsupported`); unknown
    *optional* flags are ignored.
  - **Sections:** section type IDs carry a must-understand bit. Unknown non-critical
    sections are skipped.
  - **Records:** bytes beyond a reader's known record size are optional data and are skipped.
  - **Strictness:** reserved bytes and bits must be zero. Flags must match actual use in
    both directions.
- **Rationale:** Core readers fail early with a precise reason, or degrade safely.
  Extended features can ship independently, in any order. A rejects files for no reason;
  C finds in-record features late; D forces a linear upgrade path.
- **Consequences:** Every compatibility rule needs a negative fixture. See §6 for the
  feature mapping.

### D6 — Hashing
- **D6a options:** SHA-256, BLAKE3, or SHA-512/256, each with or without an algorithm ID.
  **Choice: BLAKE3-256 with a hash-algorithm ID in the header.** v1 defines only BLAKE3. A
  new algorithm would be a new ID, gated by a required flag.
- **D6b options:** one trailer hash, or separate checksums per part. **Choice: one
  structure hash** in the trailer, using the same algorithm. It covers the header, the
  whole index, and the trailer's location fields.
- **Rationale:** Fast, and the hash ID leaves room for change. One structure hash means
  every non-blob byte is covered exactly once.
- **Consequences:** The TypeScript reader needs a BLAKE3 library (pure-JS options exist);
  the Rust side uses the `blake3` crate. Index corruption is reported as `integrity`, not
  `malformed`, because the hash is checked before structural rules.

### D7 — Compression (Extended #12)
- **Options:** (A) Zstandard; (B) DEFLATE; (C) LZ4; (D) Zstandard plus DEFLATE.
- **Choice: A.**
  - One complete Zstandard frame per blob.
  - The writer keeps the compressed form only if it is strictly smaller; otherwise the blob
    is stored uncompressed.
  - Decoder output is capped at the declared original length.
- **Rationale:** Best balance of ratio and speed.
- **Consequences:**
  - Zstandard output may differ across library versions. Byte determinism for compressed
    blobs is promised only for the same tool version and settings.
  - Compressed-file fixtures compare decoded content and structure, not compressed bytes.
    Core fixtures stay byte-exact.
  - The TypeScript reader needs a Zstandard decoder.

### D8 — Paths
- **Options:** (A) strict portable rules; (B) portable without normalisation; (C) raw bytes;
  (D) minimal rules plus a "portable" flag.
- **Choice: A.**
  - Paths are relative, `/`-separated, UTF-8 in NFC form, with no empty, `.` or `..`
    segments.
  - Control characters, Windows-illegal characters, a trailing dot or space, and Windows
    reserved names are banned everywhere.
  - Collisions under NFC plus ASCII case-folding are rejected. Paths are sorted bytewise.
- **Rationale:** A valid archive extracts identically on every supported platform, and
  `verify` can prove it.
- **Consequences:**
  - Some legal Unix trees can't be packed (for example, names containing `:` or names that
    aren't UTF-8). Pack refuses them with a clear error.
  - Non-ASCII case collisions (for example, Turkish dotless i) aren't detected by the
    format. Create-new extraction (D10) catches them on case-insensitive filesystems.
  - Rust needs a Unicode normalisation library; TypeScript has `String.prototype.normalize`.
  - NFC uses Unicode 15.1 or later (confirmed in review round 1).
- **Amendment (review round 1): complete platform rules.** FORMAT_SPEC §9, §14, §15 and
  §15.1 now cover:
  - **Windows:** reserved device names, including `CONIN$`/`CONOUT$` and trailing-space
    stems; alternate data streams; junctions and reparse points (pack skips them, extract
    never follows them, even if swapped in mid-extraction); case-insensitive and 8.3
    short-name collisions; long paths.
  - **macOS:** case-insensitive filesystems, and NFC versus NFD names.

  Each concern has a criterion (AC-PACK-7 … AC-PACK-9, AC-SAFE-5 … AC-SAFE-11).

### D9 — Determinism
- **Options:** (A) canonical form mandatory and enforced by readers; (B) canonical order
  only recommended; (C) an opt-in deterministic mode.
- **Choice: A.**
  - Entries are strictly ascending by path bytes.
  - Blobs are in first-reference order and tile the data region.
  - Path pool contents are in entry order.
  - Sections are in a fixed order, and Core has no timestamps or tool identity.
  - Readers reject non-canonical files.
- **Rationale:** Each input tree has exactly one valid Core encoding. Determinism becomes a
  checkable property, fixtures are byte-exact independent of the writer, and selective
  extract (#6) gets binary search for free.
- **Consequences:**
  - Writers must collect and sort the whole tree before writing, which is fine at ≤1M
    entries.
  - The CLI `--deterministic` flag affects Extended fields that come from the environment
    only:
    - mtime is set to a caller-given value, default 0.
    - Modes are normalised to 0644 or 0755.
    - Creator and comment are omitted unless given.

### D10 — Safe extraction
- **D10a options:** (A) fresh destination via a staging directory; (B) merge, never
  overwrite; (C) merge plus `--overwrite`. **Choice: A.**
  - The destination must not exist.
  - Full structural validation and the total-size limit come before any write.
  - Extraction goes into a fresh sibling staging directory with create-new semantics, and
    content hashes are checked while streaming.
  - On success the staging directory is renamed into place; on any error it is deleted.
  - setuid, setgid and sticky bits are never set. Core modes are 0644 for files and 0755
    for directories, minus the umask; modes are ignored on Windows.
- **D10b options:** explicit or implicit parent entries. **Choice: explicit.** Every
  parent directory must have its own directory entry. A missing parent, or a file used as a
  parent, is malformed.
- **Rationale:** No pre-existing files, symlinks or reparse points can be exploited, and
  all-or-nothing behaviour is easy to test. Explicit parents make empty directories
  natural and keep the index canonical.
- **Consequences:**
  - Extracting into an existing folder isn't supported (merge and overwrite are Later, with
    no format change).
  - Staging needs space on the destination's filesystem.
  - Selective extract (#6) has the same fresh-destination rule.

### D11 — Resource limits (amended in review round 1)
- **Options:** (A) implementation limits only; (B) hard maxima in the spec only; (C) both.
- **Choice: C.**
  - Spec hard maxima: beyond them a file is `malformed`.
  - Must-support minimums: every conforming reader accepts files within these by default.
  - Library limits are configurable: beyond them the error is `limit-exceeded`.
  - **No allocation or loop proportional to a declared size** before checking
    record count × record size ≤ section length ≤ index length ≤ file length.
- **Numbers:** see `FORMAT_SPEC.md` §10.
- **Amendment (review round 1):** the references-per-blob limit is **dropped**. It could
  reject legitimate trees, for example many empty files sharing the empty blob. Dedup
  amplification is bounded instead by LIM-5, the total logical size. LIM-5 sums every file
  entry's full `raw_length`, so each reference to a shared blob counts again (AC-LIM-4).
  LIM-5 is checked by both verify and extract.
- **Rationale:** Interoperability plus defence against hostile files, with a testable
  difference between "invalid" and "too big for this reader's configuration".

### D12 — Errors and exit codes
- **Options:** (A) categories only; (B) a code per rule; (C) category plus detail code.
- **Choice: C.**
  - The stable category determines the exit code.
  - The detail code names the spec rule that fired.
  - Each negative fixture violates exactly one rule, so the expected detail code is
    unambiguous.

| Exit | Category | Exit | Category |
|---|---|---|---|
| 0 | success | 6 | `malformed` |
| 2 | `usage` | 7 | `integrity` |
| 3 | `io` | 8 | `limit-exceeded` |
| 4 | `not-a-container` | 9 | `refused` |
| 5 | `unsupported` | 70 | `internal` (a bug; should never happen) |

Warnings, such as skipped special files, go to stderr and the JSON `warnings` array, and
don't change the exit code.

### D13 — Library and CLI architecture
- **Options:** (A) a single crate; (B) format, fs and cli crates; (C) a library crate plus
  a CLI crate.
- **Choice: B,** as in §3.2. Synchronous I/O. The library produces structured reports, and
  the CLI only renders them.
- **Rationale:** The format crate's boundary matches the spec's boundary, so fuzzing and
  conformance evidence is directly about the format. Platform-specific safety code is
  isolated in one place.

### D14 — Existing output file (review round 1)
- **Options:** (A) atomically overwrite an existing output; (B) refuse unless `--force`,
  which then replaces atomically.
- **Choice: B.** An existing output gives `refused` / `pack.output-exists` and is left
  untouched. With `--force` it's replaced by an atomic rename, and it stays unchanged if the
  pack fails. `--force` never replaces a directory.
- **Rationale:** Write-once archives are often the only copy of something. Overwriting
  should be deliberate.

## 5. Implementation requirements that aren't byte format

These are normative for the Rust implementation and checked in `ACCEPTANCE.md`:

- **G5** Pack writes to a temporary file in the output's directory and renames it on
  success. On any failure the output path is exactly as it was before, and no temporary
  file remains (W-2, W-7).
- **G6** Memory use during pack, verify and extract is bounded by the index size plus a
  fixed buffer. Blob data is streamed and never fully buffered.
- **#26** No panic, abort or unbounded allocation on any input. `chst-format` contains no
  `unsafe`.
- **D13** `chst-format` has no filesystem access (enforced by its dependency list and API
  review; see AC-ENG-2).
- Pack refuses an output path inside the source tree (`refused` / `pack.output-in-source`).

## 6. Extended roll-out map

| Feature | Format mechanism | Core reader behaviour | Determinism note |
|---|---|---|---|
| #12 Zstandard | Required flag bit 0 `ZSTD`; blob `encoding` = 1 | Rejects at open: `unsupported` / `hdr.required-flag` | Byte-exact per tool version only |
| #16 mtime + mode | Optional flag bit 0 `ENTRY_ATTRS`; entry records become 64 bytes | Reads the first 48 bytes, ignores the tail, extracts with default modes | `--deterministic` clamps mtime and normalises mode |
| #18b KV metadata | Optional flag bit 1 `KV_METADATA`; section `KV_METADATA` without the must-understand bit | Skips the section | Keys sorted; creator and comment only if given |
| #6 selective extract | None (binary search over sorted entries) | n/a | n/a |
| #7 exclude patterns | None (writer input filter) | n/a | Filtered tree is canonical as usual |
| TS reader | None | n/a | Must match Rust JSON reports exactly |
| #20 symlinks (Later) | A future required flag plus entry type 3 | Rejects at open | |

## 7. Validation strategy (summary)

Two layers, detailed in `ACCEPTANCE.md`:

- **Layer A: proving the format and implementation work.**
  - V1 independent golden fixtures from a spec-driven Python generator.
  - V2 positive conformance (exact JSON).
  - V3 negative conformance (one fixture per reader rule).
  - V4 properties: round-trip, determinism, dedup.
  - V5 exhaustive byte-flip and truncation sweep.
  - V6 fuzzing.
  - V7 extraction attacks.
  - V8 hostile declared sizes with a memory cap.
  - V9 Core-reader compatibility with Extended files.
  - V10 Linux, macOS and Windows CI; macOS and Windows evidence comes only from CI.
    `EVIDENCE.md` links the run.
  - V11 TypeScript reader (Extended).
- **Layer B: evidence of success.**
  - Every acceptance criterion has a runnable command and an observable pass condition.
  - `./check.sh` writes a machine-readable report. It exits 0 only when every criterion
    passed, fuzzing included (`--full`).
  - Done means a passing full run on Linux, macOS and Windows CI for the same commit,
    recorded in `EVIDENCE.md`.

## 8. Glossary

- **Entry:** a path in the archive, either a file or a directory.
- **Blob:** a stored byte sequence, identified by its key.
- **Key:** the BLAKE3-256 hash of a blob's stored bytes.
- **Structure hash:** the BLAKE3-256 hash over the header, the index, and the trailer's
  location fields.
- **Canonical form:** the single valid encoding of a given input tree (D9).
- **Staging directory:** the temporary sibling directory that extraction writes into.

## 9. Review round 1 decisions

| # | Item | Owner decision |
|---|---|---|
| 1 | Name and magic | **Chst** ("chest"). Header magic `43 48 53 54 0D 0A 1A 00` (`CHST`, CR, LF, SUB, NUL), trailer magic `00 1A 0A 0D 54 53 48 43`. `.chst`, `chst`. |
| 2 | Fixed 32-byte header, no alignment padding | Accepted. Readers must not cast memory directly. New header-level data goes into sections. |
| 3 | References-per-blob limit | Dropped. LIM-5 counts every reference's full size (D11 amendment). |
| 4 | Unicode version for NFC | "Unicode 15.1 or later" kept. |
| 5 | 5 GiB test | Accepted as full-only (AC-ROB-7). Fast mode covers 64-bit sizes through small fixtures (AC-ROB-8, AC-ROB-9). |
| 6 | Existing output file | Refuse unless `--force`, then replace atomically (D14). |
| 7 | `pack --json` report and `extract.no-match` | Defined in FORMAT_SPEC Appendix B and §12.8. Selective-extract criteria are Extended. |
| 8 | Fixture checksum pinned by the owner | Accepted. |
| 9 | Helper scripts | Early tasks after `plan-v1`, reviewed together with `check.sh` at `checks-v1` (§10). |
| 10 | BLAKE3 in the generator | Must be the official `blake3` Python package (or `b3sum`), never hand-written (AC-META-4). The worked example was re-verified with official `b3sum` 1.8.7. |
| 11 | Platforms | Linux, macOS and Windows are all v1. Done means a passing full run on all three in CI for the same commit. macOS and Windows evidence comes only from CI, linked in `EVIDENCE.md`. |
| 12 | Platform rule completeness | D8 amendment; FORMAT_SPEC §15.1. |

Still-open drafting choices, for the reviewer:

- **Empty container.** Zero entries and zero blobs is valid. Packing an empty directory
  produces one.
- **Hard links (N2).** Each hard-linked name is packed as an independent regular file, and
  its content dedups to one blob.
- **`ENTRY_ATTRS` layout** (seconds + nanoseconds + 9-bit mode) is a proposal; see
  FORMAT_SPEC §12.6.
- **Windows reparse points.** Skipping every reparse point also skips cloud placeholder
  files, such as OneDrive files not stored locally. That's acceptable for v1, and pack
  warns about each one.
- **Runner feasibility** for AC-ROB-4 (fuzzing) and AC-ROB-7 (5 GiB) is unconfirmed until
  the first CI run. ACCEPTANCE.md §1.2 gives each runner's expected status, the FAIL-not-N/A
  rule, and proposed relocations that need owner approval.

## 10. Checkpoints and early tasks

This is not a task list. It records the checkpoints the owner named, and the work that
must come before any Rust format code.

- **`plan-v1`:** the owner tags it after the independent review approves these three
  documents.
- **Early tasks after `plan-v1`:**
  1. **GitHub repository and Actions workflow.**
     - A matrix of `ubuntu-latest`, `macos-latest` and `windows-latest`, each running
       `./check.sh --full`. On Windows it uses the runner's bash (`shell: bash`).
     - Install pinned Python plus the official `blake3`, `b3sum`, `jq`, stable and nightly
       Rust, and `cargo-fuzz`.
     - Set `$CHST_BIG_TMP` per runner, and free disk on Linux.
     - Log `df -h` and `cargo +nightly fuzz --version`.
     - Upload `target/acceptance/report.json` as `acceptance-report-<os>`.

     Its first run is what confirms (or refutes) runner feasibility (ACCEPTANCE.md §1.2).
  2. **`check.sh` and the six helper scripts:** `trace.py`, `inspect_check.py`,
     `tree_eq.py` (including `--nfc`), `flip_sweep.py`, `truncate_sweep.py` and
     `spec_hexdump.py`.
  3. **The fixture generator** (`tools/fixturegen`, official `blake3` only) and the first
     fixture set, for the owner to approve and pin (ACCEPTANCE.md §5).
  4. **`EVIDENCE.md`,** kept current from the first CI run onward.
- **`checks-v1`:** the owner reviews `check.sh`, the helper scripts, the workflow and the
  fixtures together, before implementation of `chst-format` begins.
