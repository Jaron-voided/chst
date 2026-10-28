# Chst — Design

> Status: **DRAFT for independent review** (revised after review rounds 1–9; see §9, and the full review records in `reviews/`).
> The format is **Chst**, pronounced "chest". Its magic bytes are `CHST`, its file
> extension is `.chst`, and the CLI binary is `chst`.
>
> Companion documents: [`FORMAT_SPEC.md`](FORMAT_SPEC.md) (normative byte format and rules)
> and [`ACCEPTANCE.md`](ACCEPTANCE.md) (acceptance criteria with runnable checks).
> Precedence between documents, and which files are protected, are defined only in
> `CLAUDE.md`.

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
| #13 | Per-blob content hashes plus a structure hash | SHA-256 (D6) |
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
| #28 | Conformance fixtures with expected JSON | Built by an independent generator in `fixtures/gen/` (V1) |
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
| `chst-fs` | Pack: directory walk, path checks, double hashing. Extract: staging, create-new, permissions, Windows long paths. | Re-implement format parsing; use `unsafe` anywhere except its Windows module (D18) |
| `chst-cli` | Argument parsing, text and `--json` rendering, category→exit-code mapping | Contain format or safety logic; use `unsafe` |

All I/O is synchronous and blocking; there is no async runtime.

Planned repository layout, which `ACCEPTANCE.md` commands refer to:

```
rust-toolchain.toml           # pinned stable Rust (D16)
crates/chst-format  crates/chst-fs  crates/chst-cli   # Rust workspace
fuzz/                         # cargo-fuzz targets over chst-format; own rust-toolchain.toml (nightly, D16)
fixtures/                     # golden + negative fixtures, expected JSON, MANIFEST.sha256
fixtures/gen/                 # independent spec-driven Python generator (V1), stdlib only
tools/acceptance/             # check.sh helper scripts
ts-reader/                    # Extended: TypeScript read-only reader
check.sh                      # acceptance runner
EVIDENCE.md                   # one row per acceptance ID; links CI runs
.github/workflows/check.yml   # CI (D17)
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
- **Prior art (credited; techniques only, not a copied layout):**
  - **The index at the end, found through a fixed-size record at the very end of the
    file.** This is a long-standing technique; ZIP's end-of-central-directory record is the
    best-known example. It was chosen for one-pass writing and to keep append possible.
    Chst's sections, record layouts, trailer fields and hashing are its own, and unlike ZIP
    there are no per-entry local headers (option C was rejected).
  - **The magic's line-ending bytes** (`0D 0A 1A 00` after `CHST`) follow the technique of
    PNG's file signature. A CR/LF pair detects line-ending translation; SUB (`1A`) stops
    the DOS `type` command, and NUL catches text-mode tools. They were chosen because
    archives are often moved through tools that may treat them as text. Only the technique
    is borrowed: the bytes and their position are Chst's.
  - The reviewer can still judge whether either goes beyond using a technique.
- **Amendment (readiness audit after `plan-v1`, owner-approved):** D1 is confirmed for v1,
  after an independent, read-only audit of FORMAT_SPEC.md and the code at 42e318e. There are
  no per-record headers: every name and every blob boundary is reached through the index,
  which only the trailer locates. Damage inside the data region stays local, because each
  blob is checked against its own key (BLB-6). Damage to the index or the trailer, including
  truncation, can't be recovered from within the format, because the names and the blob
  boundaries are lost with it. Recovering damaged archives is out of scope for Chst and is
  left to external tools. FORMAT_SPEC.md Appendix D (non-normative) lists the byte-level
  anchors such a tool can rely on.

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

### D6 — Hashing (amended in review round 2)
- **D6a options:** SHA-256, BLAKE3, or SHA-512/256, each with or without an algorithm ID.
  **Choice: SHA-256 with a hash-algorithm ID in the header** (`hash_alg` = 1). v1 defines
  only SHA-256. A different algorithm would need a new `hash_alg` ID with the same 32-byte
  output; a different width needs a new major version (round 6, F31).
- **D6b options:** one trailer hash, or separate checksums per part. **Choice: one
  structure hash** in the trailer, using the same algorithm. It covers the header, the
  whole index, and the trailer's location fields.
- **History:** round 1 chose BLAKE3. **Round 2 switched to SHA-256**, because of
  `CLAUDE.md`'s rule that fixture hashes come from an implementation independent of the
  Rust code:
  - The official `blake3` Python package and `b3sum` are both built on the same `blake3`
    Rust crate that `chst-format` would use, so they aren't independent of it.
  - With SHA-256, the fixture generator uses Python's `hashlib`, the Rust code uses `sha2`
    (D15), and the TypeScript reader uses `node:crypto`.
- **Rationale:** Independent implementations, available everywhere. One structure hash
  covers every non-blob byte exactly once. SHA-256's collision resistance is ample for dedup
  keys.
- **Consequences:**
  - SHA-256 is slower than BLAKE3, and pack hashes each file twice (D2a). That's
    acceptable at a few GB.
  - **Rust's standard library has no SHA-256,** so Rust still needs one hash crate (`sha2`;
    see D15). Python and Node need none.
  - Python's `hashlib` and `node:crypto` are both normally backed by OpenSSL, so the
    generator and the TypeScript reader may share a SHA-256 implementation. The Rust code
    (`sha2`, pure Rust) is independent of both, which is the independence the oracle rule
    requires.
  - Index corruption is reported as `integrity`, not `malformed`, because the hash is
    checked before structural rules.

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
  - The TypeScript reader needs a Zstandard decoder (D15).
  - **The zstd library is shared on the Rust side, and that's accepted (review round 2).**
    The Rust `zstd` crate wraps C libzstd. The generator writes its own Raw/RLE-block
    frames, and verifies content checksums with its own pure-Python XXH64. It uses the
    standard library's `compression.zstd` (which wraps libzstd) only for one job: decoding
    the single libzstd-made Compressed frame embedded in the catalog, whose output it then
    compares with the known text. So the fixtures depend on libzstd only through that one
    known-answer check (corrected in round 7, N19). Compressed bytes are never compared,
    only decoded content and structure. Blob keys are SHA-256 over the stored bytes, and
    decoded output must match the original content and length.

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
  - NFC uses exactly Unicode 16.0 (round 6, F12; round 1 had said "15.1 or later").
- **Amendment (review round 1): complete platform rules.** FORMAT_SPEC §9, §14, §15 and
  §15.1 now cover:
  - **Windows:** reserved device names, including `CONIN$`/`CONOUT$` and trailing-space
    stems; alternate data streams; junctions and reparse points (pack skips them, extract
    never follows them, even if swapped in mid-extraction); case-insensitive and 8.3
    short-name collisions; long paths.
  - **macOS:** case-insensitive filesystems, and NFC versus NFD names.

  Each concern has a criterion (AC-PACK-7 … AC-PACK-9, AC-SAFE-5 … AC-SAFE-11).

- **Amendment (review round 6):**
  - **PATH-2:** judged with exactly the Unicode 16.0 tables in every reader and writer (F12).
    Code points added after 16.0 may be judged differently by other tools, and the fixture
    `PATH-2-unicode16` documents a 15.x/16.0 difference.
  - **PATH-6:** now also bans the C1 controls (U+0080–U+009F) and the bidirectional
    embedding, override and isolate characters (U+202A–U+202E, U+2066–U+2069), so an
    extracted name can't spoof another in any file manager (F42). `list`'s text output
    escapes the non-printing characters that remain allowed.
  - **PATH-8:** no longer applies to `.` and `..` (F6).

### D9 — Determinism (amended in review round 6: writers write `minor_version` 0 unless a revision changes the encoding, F32)
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

- **Amendment (review round 6):** FORMAT_SPEC §15 now states the threat model: a hostile
  container, plus other local principals who can write to the destination's parent and race
  the extractor. It adds:
  - an unpredictable, create-new, owner-only (0700) staging directory with a fixed name
    pattern (F17, F43);
  - a final rename that never replaces an existing object (F16);
  - cleanup relative to directory handles, never following links (F18);
  - verification while writing, not as a pre-pass (F14);
  - handle-relative reopening of earlier directories (F21);
  - EXT-6's exception for the final rename (F20).

  Pack now walks relative to directory handles and checks file identity in pass 2 (F23),
  decides "output inside source" by file identity (F22), and applies the reader limits
  (W-10, F24).

- **Amendment (review round 8, §9h):** right after creating staging, the extractor confirms
  through its handle that it's the directory just created. On Unix it must be owned by the
  effective user, mode 0700 and empty; on Windows, creating and opening are one step (M1).
  Cleanup removes only objects whose identities the extractor recorded, so "deleted on any
  error" has stated exceptions when someone else's object is involved (M1, M9). Extraction
  reports step 11 exactly as verify would (M2).
- **Amendment (review round 9, §9i):** staging stays 0700 (on Windows, private) until the final
  rename and its identity check have passed, and only then gets its final permissions (P1).
  The staging check first confirms ownership, no group or other bits, and emptiness. Only
  then does it run `fchmod(handle, 0700)` and confirm `st_mode & 0o777` (P2, Q1). Every
  directory the extractor creates has any inherited setgid bit cleared (P2). On Windows, staging is held
  without `FILE_SHARE_DELETE` (P4). Extracting onto filesystems without Unix modes is refused,
  a known v1 limitation (P5) (superseded by Q5: refused or io, non-normative).

### D11 — Resource limits (amended in review rounds 1 and 6)
- **Options:** (A) implementation limits only; (B) hard maxima in the spec only; (C) both.
- **Choice: C.**
  - Spec hard maxima: beyond them a file is `malformed`.
  - Must-support minimums: every conforming reader accepts files within these by default.
  - Library limits are configurable: beyond them the error is `limit-exceeded`.
  - **No allocation or loop proportional to a declared size** before checking
    record count × record size ≤ section length ≤ index length ≤ file length.
- **Numbers:** see `FORMAT_SPEC.md` §10.
- **Amendment (review round 6):**
  - **LIM-1 is retired (F7):** LIM-2 and SEC-4 already cap the entry count at 89,478,485.
  - **LIM-2** has a sparse-recipe fixture.
  - **LIM-6** is defined by multiplication: `raw_length > limit × stored_length`, computed
    without overflow (F8).
  - **LIM-5's sum** is computed without overflow (F9).
  - Every limit has a CLI flag (FORMAT_SPEC Appendix C, F45).
- **Amendment (review round 1):** the references-per-blob limit is **dropped**. It could
  reject legitimate trees, for example many empty files sharing the empty blob. Dedup
  amplification is bounded instead by LIM-5, the total logical size. LIM-5 sums every file
  entry's full `raw_length`, so each reference to a shared blob counts again (AC-LIM-4).
  LIM-5 is checked by both verify and extract.
- **Rationale:** Interoperability plus defence against hostile files, with a testable
  difference between "invalid" and "too big for this reader's configuration".

### D12 — Errors and exit codes (amended in review round 6)
- **Options:** (A) categories only; (B) a code per rule; (C) category plus detail code.
- **Choice: C.**
  - The stable category determines the exit code.
  - The detail code names the spec rule that fired.
  - Each negative fixture has exactly one expected detail: the first rule it breaks in
    FORMAT_SPEC §13's order (round 6). Later rules it also breaks are recorded in
    `also_violates`, for information only.

| Exit | Category | Exit | Category |
|---|---|---|---|
| 0 | success | 6 | `malformed` |
| 2 | `usage` | 7 | `integrity` |
| 3 | `io` | 8 | `limit-exceeded` |
| 4 | `not-a-container` | 9 | `refused` |
| 5 | `unsupported` | 70 | `internal` (a bug; should never happen) |

Warnings, such as skipped special files, go to stderr and the JSON `warnings` array, and
don't change the exit code.

**Amendment (review round 6, F1 and F2):** FORMAT_SPEC §13 is now a total order. A reader
reports only the first violation, so the detail code is deterministic. An unsupported file
(HDR-6, SEC-2) is never reported as anything else. Each negative fixture therefore has
exactly one expected detail, with no lists of acceptable alternatives.

### D13 — Library and CLI architecture
- **Options:** (A) a single crate; (B) format, fs and cli crates; (C) a library crate plus
  a CLI crate.
- **Choice: B,** as in §3.2. Synchronous I/O. The library produces structured reports, and
  the CLI only renders them.
- **Rationale:** The format crate's boundary matches the spec's boundary, so fuzzing and
  conformance evidence is directly about the format. Platform-specific safety code is
  isolated in one place.
- **Test hooks (review round 6, F19):** the race tests (AC-SAFE-3, AC-SAFE-8, AC-SAFE-13 …
  15, AC-PACK-10) need hook points inside `chst-fs`. Those hooks are compiled only with a
  non-default Cargo feature, `test-hooks`, so release builds never contain them. It's a
  feature of `chst-fs`, not a new dependency, so D15 is unaffected.

### D14 — Existing output file (review round 1)
- **Options:** (A) atomically overwrite an existing output; (B) refuse unless `--force`,
  which then replaces atomically.
- **Choice: B.** An existing output gives `refused` / `pack.output-exists` and is left
  untouched. With `--force` it's replaced by an atomic rename, and it stays unchanged if the
  pack fails. `--force` never replaces a directory.
- **Rationale:** Write-once archives are often the only copy of something. Overwriting
  should be deliberate.

### D15 — Approved dependencies (APPROVED in review round 3)
- **Principle:** use the smallest set that works. Anything not listed needs a "Needs
  decision" entry (`CLAUDE.md`). AC-ENG-5, AC-META-4 and AC-X-TS-3 enforce the list.
- **Round 3 changes:** `serde_json` replaces the hand-written JSON emitter. Paths in a
  container are attacker-controlled, so string escaping must come from a well-tested
  library. **`Cargo.lock` is committed** (for the workspace and for `fuzz/`), so every
  dependency version, transitive ones included, is pinned. AC-ENG-5 checks both.
- **Rust: runtime**

| Crate (version at proposal) | Used by | Why it's needed | Considered instead |
|---|---|---|---|
| `sha2` 0.11 | chst-format | SHA-256 (D6). Rust std has none. It's pure Rust, independent of the OpenSSL used by `hashlib` and `node:crypto`. | Hand-written (crypto risk); `ring` or `openssl` (C/asm, may share code with the oracle) |
| `unicode-normalization` 0.1 | chst-format, chst-fs | The NFC check (PATH-2) and pack's NFC conversion (W-3). Rust std has none. | ICU4X (far larger) |
| `rustix` 1.x | chst-fs, Unix only | Handle-relative, no-follow `openat`/`mkdirat` for EXT-2 and EXT-8. Rust std has no `openat`, and `rustix` is a safe API, so no `unsafe` is needed. | `libc` (needs `unsafe`); `cap-std` (bigger, less direct control) |
| `windows-sys` 0.61 | chst-fs, Windows only | Handle-relative opens with `FILE_FLAG_OPEN_REPARSE_POINT`, reparse-point checks and extended-length paths (W-8, EXT-8). | The `windows` crate (heavier) |
| `lexopt` 0.3 | chst-cli | Argument parsing with no transitive dependencies | `clap` (large dependency tree) |
| `serde_json` 1.x | chst-cli | JSON reports (FORMAT_SPEC Appendix B). Entry paths are attacker-controlled, so string escaping must come from a well-tested library. It's used through `serde_json::Value`, with no derive macros; `serde` comes in transitively only. | Hand-written emitter (rejected in round 3) |

- **Rust: Extended**

| Crate | Used by | Why |
|---|---|---|
| `zstd` 0.14 | chst-format (feature `zstd`) | Zstandard encode and decode (D7). Wraps C libzstd, which is accepted (D7). |

- **Rust: dev and test only**

| Crate | Used by | Why |
|---|---|---|
| `tempfile` 3 | Tests in chst-fs and chst-cli | Rust extraction tests must use temporary directories only |
| `libfuzzer-sys` 0.4 | `fuzz/` crate only | Required by cargo-fuzz |

  No `proptest`: AC-DET-3 uses a small seeded generator in test code and prints the seed on
  failure. The counting allocator in AC-LIM-1 is written in test code.
- **Python:**
  - The fixture generator (`fixtures/gen/`) and the helper scripts (`tools/acceptance/`)
    use the **standard library only** (`hashlib`, `struct`, `json`, `unicodedata`,
    `pathlib`, `argparse`). That includes Extended: the generator writes its own
    Raw/RLE-block Zstandard frames, and checks content checksums with its own XXH64. The
    standard library's `compression.zstd` is used only to decode the one embedded
    libzstd-made frame for a known-answer check, so it must be present (D16). (`zstandard`
    was dropped in round 5.)
- **TypeScript reader (Extended):**
  - **No runtime dependencies.** It uses `node:crypto` (SHA-256),
    `String.prototype.normalize` (NFC) and `node:zlib` Zstandard decoding.
  - Node's documentation marks `node:zlib` zstd as **Experimental** (added in v23.8.0 and
    v22.15.0). If it's still experimental when Extended starts, the fallback is `fzstd`,
    which would need its own decision then.
  - Dev only: `typescript` and `@types/node`, for type-checking.
- **Tools:**
  - **Everywhere:** bash, git, coreutils (`sha256sum`, or `shasum -a 256` on macOS), `jq`,
    Python, and `rustup`/`cargo`.
  - **Fuzzing:** `cargo-fuzz` 0.13.2, installed with `--locked`.
  - **The done check:** `gh`, read-only.
  - **Linux only:** GNU `time`, for AC-ROB-6.
  - **Windows built-ins:** `fsutil`, `powershell` and `cmd`.
  - `b3sum` is no longer needed.

### D16 — Environment pins (APPROVED in review round 3)

| Item | Pin | Reason |
|---|---|---|
| Rust stable | `rust-toolchain.toml` with `channel = "1.99.1"` and components `rustfmt`, `clippy`; `rust-version = "1.99"`; edition 2024 | 1.99.1 is the current stable (released 2026-10-13) and is what's installed on the owner's WSL machine |
| Rust nightly (fuzzing only) | `fuzz/rust-toolchain.toml` with `channel = "nightly-2026-10-01"`, invoked as `cargo +<that> fuzz` | A dated nightly, so fuzz builds are reproducible. Not yet confirmed to have every component on all three runners; the first full CI run confirms it. If it doesn't, the fallback is the nearest earlier date that does. |
| cargo-fuzz | 0.13.2 (`cargo install --locked`) | Latest release at proposal time |
| Python | **3.14, always invoked explicitly as `python3.14`**. Its `unicodedata` is exactly Unicode 16.0, which PATH-2 requires (round 6, F12; AC-ENG-6) | Its `unicodedata` is exactly Unicode 16.0, as PATH-2 requires, and it must include the optional `compression.zstd` module, which CPython builds only when libzstd is present; AC-ENG-6 checks both (N19). The system `python3` on the owner's WSL machine is 3.12.3 (Unicode 15.0.0, below the spec minimum), so no check or document may call plain `python3`. The owner has installed 3.14 locally. The CI workflow must provide a `python3.14` command on every runner; on Windows that's a shim to the interpreter `setup-python` installs. |
| Unicode tables | **Exactly 16.0** in every reader (round 6, F12): `unicode-normalization` with 16.0 tables (AC-ENG-8), Python 3.14 (AC-ENG-6), and Node ICU (AC-X-TS-3) | Conforming readers must agree on every path |
| Node (Extended TypeScript reader only) | **24 LTS** | Active LTS. It has `node:zlib` zstd and TypeScript type stripping. |
| jq | 1.7 or later | Has `walk`, which `jqn` uses |

Python 3.14 and `jq` are now installed on the owner's WSL machine. Still missing there: a
nightly toolchain, `cargo-fuzz`, and Node (needed only for Extended).

### D17 — CI triggers (review round 2)
- **Choice:** CI runs **fast mode on every push and pull request**, and **full mode on
  manual trigger** (`workflow_dispatch`). The final done run is a manually triggered full
  run.
- **Mechanics:** each job's result follows `check.sh`'s exit code.
  - A fast job succeeds on exit 2, which is expected because full-only checks are NOT RUN.
  - A full job succeeds on exit 2 only if AC-XP-1 is the sole NOT RUN.
  - Any exit 1 fails the job.
- The owner creates the GitHub repository and pushes. Claude uses `gh` read-only to inspect
  runs.

### D18 — Unsafe code policy (review rounds 3–4)
- **Rule:**
  - **`chst-fs`** uses `#![deny(unsafe_code)]`. Its only allowed module is the Windows one,
    `#[cfg(windows)] #[allow(unsafe_code)] mod windows;`, which calls `windows-sys`. It also
    denies `clippy::undocumented_unsafe_blocks` and `clippy::missing_safety_doc`, so every
    `unsafe` block there needs a `// SAFETY:` comment explaining why it's sound. (`forbid`
    can't be relaxed for a single module, so this crate uses `deny` plus one `allow`.)
  - **Every other crate** uses `#![forbid(unsafe_code)]`. That means `chst-format`,
    `chst-cli`, every integration-test crate and every fuzz target, apart from the two
    exceptions below.
- **Exception 1: the counting allocator (round 4).**
  - The only file outside `chst-fs`'s Windows module that may contain `unsafe` is
    **`crates/chst-format/tests/support/counting_alloc.rs`**. It holds the counting global
    allocator (`unsafe impl GlobalAlloc`) that AC-LIM-1 and AC-X-ZSTD-2 use to measure peak
    heap. It starts with `#![allow(unsafe_code)]`, and each `unsafe` item in it has a
    `// SAFETY:` comment.
  - Only the two test crates that include it,
    `crates/chst-format/tests/hostile_sizes.rs` and
    `crates/chst-format/tests/zstd_bombs.rs`, use `#![deny(unsafe_code)]` instead of
    `forbid`. Every other test crate uses `forbid`.
- **Exception 2: the fuzz crate (round 4).**
  - If cargo-fuzz's `fuzz_target!` macro trips the `unsafe_code` lint, the **fuzz crate
    only** is exempt from `forbid`. It's a test harness that never ships.
  - The exemption covers the attribute only: fuzz sources still contain no hand-written
    `unsafe`, and the library code they call keeps its own rule.
  - To use the exemption, commit the compiler error that shows the lint firing, as
    `fuzz/FORBID_EXEMPTION.txt`. AC-ENG-7 accepts a missing `forbid` in fuzz targets only
    when that file exists and contains the `unsafe_code` lint error.
- **Rationale:** the format parser handles hostile input and must be memory-safe by
  construction. Raw OS calls are confined to one reviewable module. The test and fuzz
  exceptions never ship.
- **Enforcement:** AC-ENG-7. The `// SAFETY:` lints run on the Windows CI runner through
  AC-ENG-1, because the Windows module only compiles there.

## 5. Implementation requirements that aren't byte format

These are normative for the Rust implementation and checked in `ACCEPTANCE.md`:

- **G5** Pack writes to a temporary file in the output's directory and renames it on
  success. On any failure the output path is exactly as it was before, and no temporary
  file remains (W-2, W-7).
- **G6** Memory use during pack, verify and extract is bounded by the index size plus a
  fixed buffer. Blob data is streamed and never fully buffered.
- **#26** No panic, abort or unbounded allocation on any input.
- **D18** No `unsafe` code except in `chst-fs`'s Windows module and the two exceptions
  named in D18. Each `unsafe` block carries a `// SAFETY:` comment.
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
  - V1 independent golden fixtures from a spec-driven Python generator in `fixtures/gen/`
    (standard library only, with SHA-256 from `hashlib`).
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
  - `./check.sh` writes a machine-readable report with statuses PASS, FAIL, NOT RUN and
    N/A, and exits 0, 2 or 1 (ACCEPTANCE.md §1).
  - The definition of done is ACCEPTANCE.md §2, and only there.

## 8. Glossary

- **Entry:** a path in the archive, either a file or a directory.
- **Blob:** a stored byte sequence, identified by its key.
- **Key:** the SHA-256 hash of a blob's stored bytes.
- **Structure hash:** the SHA-256 hash over the header, the index, and the trailer's
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
| 9 | Helper scripts | Written with `check.sh` as the first implementation task, and reviewed at `checks-v1` (§10). *Timing amended in round 2.* |
| 10 | BLAKE3 in the generator | *Superseded in round 2:* the format now uses SHA-256, and the generator uses `hashlib`. |
| 11 | Platforms | Linux, macOS and Windows are all v1. Done means a passing full run on all three in CI for the same commit. macOS and Windows evidence comes only from CI, linked in `EVIDENCE.md`. |
| 12 | Platform rule completeness | D8 amendment; FORMAT_SPEC §15.1. |

## 9b. Review round 2 decisions

| # | Item | Owner decision |
|---|---|---|
| 1 | Hash | D6 switched to **SHA-256**. The generator uses `hashlib`, Rust uses `sha2`, and the TypeScript reader uses `node:crypto`. Dedup keys, criteria and the worked example are updated. |
| 2 | zstd in Extended | The shared C library is accepted, because compressed bytes aren't compared (D7). |
| 3 | Generator location | `fixtures/gen/`, so it's protected together with the fixtures. |
| 4 | Generator timing | The generator and all fixtures are built during PLANNING, and the worked example is regenerated from the generator. This replaces round 1 #9's "after `plan-v1`". |
| 5 | First implementation tasks | `check.sh` and its helper scripts, then the CI workflow file. Then stop for the `checks-v1` review. The owner creates the GitHub repository and pushes; Claude uses `gh` read-only. |
| 6 | Check statuses and exit codes | PASS, FAIL, NOT RUN and N/A, with exit codes 0, 2 and 1. N/A only where ACCEPTANCE.md fixes it in advance (ACCEPTANCE.md §1). |
| 7 | Definition of done | ACCEPTANCE.md §2 only. `CLAUDE.md` points to it. |
| 8 | EVIDENCE.md | One row per acceptance ID: a status per OS, the command, the commit, and the CI run link for macOS and Windows. |
| 9 | Conformance mechanism | The CLI-based fixture comparisons are enough. There's no separate cargo conformance suite. |
| 10 | Zero-test guard | Every cargo test check must see at least one test run. AC-META-7 proves the harness reports FAIL for an empty test target. |
| 11 | Dependencies and environment | Proposed as D15 and D16, awaiting approval. |
| 12 | Open items | Kept in §9 until `plan-v1`. From then on, under "Needs decision" in PROGRESS.md, including moving a check to another OS. |
| 13 | Protection and precedence | Defined only in `CLAUDE.md`. From `checks-v1` on, the helper scripts and the CI workflow file are protected too. |
| 14 | Temporary directories | Every check creates and removes its own fresh temporary directory, including the large-file one. Rust extraction tests use temporary directories only. |
| 15 | §10 | Lists only checkpoints and their order. Tasks go in TODO.md. |
| 16 | Prior art | The index at the end and the magic's line-ending bytes are credited in D1. |
| 17 | Large-file test | 4 GiB + 1 MiB on macOS, and on Windows if needed (ACCEPTANCE.md AC-ROB-7). No paid runners. |
| 18 | Windows fuzzing | The fallback (AC-ROB-4W) is approved provisionally, until the first full CI run. **Confirmed** by the owner after full-mode run 40689182770 (commit b94ca41): cargo-fuzz works on Linux and macOS, and on Windows the fuzz binary exits `0xc0000135` before running. So cargo-fuzz covers Linux and macOS (AC-ROB-4), and Windows uses the fallback (AC-ROB-4W). |
| 19 | CI triggers | Fast on push and pull request, full on manual trigger and for the final done run (D17). |

## 9c. Review round 3 decisions

| # | Item | Owner decision |
|---|---|---|
| 1 | `CLAUDE.md` changes | Approved and applied. **DESIGN.md is protected from `plan-v1` on,** and may be edited only to record decisions the owner has approved. Otherwise D15 and D16, and the list AC-ENG-5 checks against, could change without the owner. |
| 2 | D15 | Approved, plus `serde_json` for JSON output (attacker-controlled paths need well-tested escaping) and a committed `Cargo.lock`. |
| 3 | Unsafe code | `#![forbid(unsafe_code)]` in every crate except `chst-fs`'s Windows module, which calls `windows-sys`. Each `unsafe` block there has a comment explaining why it's sound (D18, AC-ENG-7). |
| 4 | D16 | Approved as proposed. Python is called as `python3.14` everywhere, because the system `python3` is 3.12. |

## 9d. Review round 4 decisions

| # | Item | Owner decision |
|---|---|---|
| 1 | Test-only `unsafe` | Option (a): one named test-only file, `crates/chst-format/tests/support/counting_alloc.rs`, may contain `unsafe impl GlobalAlloc`, with `// SAFETY:` comments (D18, AC-ENG-7). |
| 2 | Fuzz targets and the unsafe lint | If `fuzz_target!` trips the lint, the fuzz crate only is exempt (D18). |
| 3 | `CLAUDE.md` wording | Aligned with D18. |

## 9e. Review round 5 decisions

| # | Item | Owner decision |
|---|---|---|
| 1 | `zstandard` | Dropped from D15. The generator writes its own Raw/RLE-block Zstandard frames, so it uses the standard library only, for Extended too. |
| 2 | `inspect` report shape | Copied into FORMAT_SPEC Appendix B as the normative definition. The generator follows the spec. |
| 3 | Other §9 items | Left for the independent review. |

## 9f. Review round 6 decisions (independent review: 46 findings)

| # | Item | Owner decision |
|---|---|---|
| 1 | F1, F2 with F5, F10, F16, F17, F18, and all ten generator fixes | Accepted as proposed. |
| 2 | F6 | Only its PATH-8 exemption for `.` and `..`. The rest of F6 is superseded by F2's order. Because PATH-3's literal wording still covers empty segments, §13 checks PATH-4 before PATH-3 so the PATH-4 fixture stays reachable. |
| 3 | F12 | The cheaper option: exactly Unicode 16.0 tables in every reader. It's documented that code points added after 16.0 may be judged differently, with fixture `PATH-2-unicode16`. |
| 4 | F42 | Ban the characters: PATH-6 adds C1 (U+0080–U+009F) and the bidi characters (U+202A–U+202E, U+2066–U+2069). `list`'s text output also escapes the non-printing characters that remain allowed. |
| 5 | §9 item 10 (Node zstd) | Node's documentation lists `ZSTD_d_windowLogMax` as a `node:zlib` zstd decompressor option, so the TypeScript reader uses `node:zlib`, with no D15 change. That's confirmed from the documentation only, because Node isn't installed locally. The `ZST-2-window` fixture under AC-X-TS-2 exercises it. Node marks zstd as Experimental, which remains a known risk for Extended. |
| 6 | F3, F4, F7–F9, F11, F13–F15, F19–F41, F43–F46 | Applied as proposed. F40 is documented only, F44 is applied as per-directory schemas, and F46 without `--strict`. |
| 7 | `CLAUDE.md` | Protected now. Claude only proposes changes to it, and the owner applies them. |

The reviewer's §9 recommendations, as applied:
- **LIM-1 and LIM-2:** retired; sparse recipe.
- **Overlapping rules:** F2's order.
- **CAN-2:** F5's wording.
- **PATH_MAX:** made normative (W-5 and EXT-8 reopening).
- **Empty container** and **hard links:** accepted as drafted.
- **`ENTRY_ATTRS` layout:** kept, with F27's rules for applying attributes.
- **Reparse points:** F46.
- **Runner feasibility:** includes enabling 8.3 names (F38).
- **Node zstd:** item 5 above.

## 9g. Review round 7 decisions (second independent review: 23 new findings)

| # | Item | Owner decision |
|---|---|---|
| 1 | N1, N2 | Accepted as proposed. N1: ZST-1 means only "content size in the header ≠ `raw_length`"; every decoding failure is ZST-2, in one capped pass. N2: the staging directory is held by handle, with identity checks around the rename, plus the threat-model sentence and an AC-SAFE-14 staging-swap test. |
| 2 | N3, N6, N8, N9, N12 | Accepted as proposed. |
| 3 | N15 | Ban U+061C, U+200E and U+200F in PATH-6 too, for the same reason as F42, and pin General_Category to Unicode 16.0. |
| 4 | N19 | The narrower fix: AC-ENG-6 checks that `compression.zstd` is present; D7 and D15 are corrected; content checksums are verified with a pure-Python XXH64; and the one Compressed frame's output is compared with the known text. |
| 5 | N21 | Dropped. Pin the exact Node version when Extended starts, if needed. |
| 6 | N4, N5, N7, N10, N11, N13, N14, N16, N17, N18, N20, N23 | Applied as proposed. N22 needed nothing. |
| 7 | Review records | Each review's report and closure table is kept in `reviews/` (`review-1.md`, `review-2.md`, and so on for every later review). |

Still open, for the next reviewer (until `plan-v1`):

- **Runner feasibility** is unconfirmed until the first full CI run:
  - AC-ROB-4 on Windows (the provisional fallback is in place);
  - the dated nightly (D16);
  - disk for AC-ROB-7 (ACCEPTANCE.md §1.3);
  - whether `fsutil 8dot3name set` works on the Windows runner (AC-SAFE-10).
- **Unverified pins:** `unicode-normalization`'s Unicode version (AC-ENG-8) and Node 24's
  ICU Unicode version (AC-X-TS-3) are expected to be 16.0, but nothing has run them yet.
- **`node:zlib` zstd** is Experimental in Node's documentation.

## 9h. Review round 8 decisions (third independent review: 15 new findings)

| # | Item | Owner decision |
|---|---|---|
| 1 | M1 | The `fstat` route. After opening staging, it must be a directory owned by the effective user, with mode 0700, and empty. On Windows, create and open in one step (`NtCreateFile` with `FILE_CREATE`). Any failed open or mismatch is `refused/extract.unsafe-object`, and nothing under that name is touched. Both AC-SAFE-14 hooks are added (between create and open, and between the pre-rename check and the rename). Cleanup removes only objects whose identities the extractor recorded. |
| 2 | M2 | The proposed wording: per blob, step 11's rules in step 11's order. If decoding fails, the extractor still hashes the remaining stored bytes and reports BLB-6 on a mismatch, otherwise the ZST rule. Plus an Extended extract-case. |
| 3 | M3 | Compute LIM-6 exactly, in at least 128 bits, and remove the overflow parenthetical. Add the boundary to AC-CLI-1. TRL-2 is unchanged. |
| 4 | M4 | FLG-1 becomes one-way in FORMAT_SPEC (`ENTRY_ATTRS` set ⇒ `record_size` ≥ 64), with an Extended-view expectation for `compat/unknown-optional-wider-entries`. |
| 5 | M5 | Allow `fchmodat` on a name relative to a held parent handle, inside private staging, with `AT_SYMLINK_NOFOLLOW` where the platform has it. Where it doesn't, check with `fstatat` NOFOLLOW first. Add the 0o000-directory case to AC-SAFE-13. |
| 6 | M6 | The 32 MiB / 1 TiB RLE time bomb as a `$GEN synth-*` recipe, and the sentence corrected. |
| 7 | M7 | Add `ZST-2-second-frame` and `ZST-2-trailing-skippable`. |
| 8 | M8–M11, M13, M14 | Applied as proposed. |
| 9 | M12 | Limit values: ASCII digits only, no sign, no whitespace, no leading zeros (a lone `0` is allowed). |
| 10 | M15 | Escape the bidi characters in `expect.json` and the catalog, and regenerate the fixtures. |
| 11 | XXH64 | Add the multi-size libzstd cross-check to the generator build. |

How two of these were placed:
- **M5 and M3 test placement.** AC-SAFE-13 and AC-CLI-1 are Core IDs, and statuses are per ID
  (ACCEPTANCE §1.1). An Extended-only case inside them would FAIL in the Core cut. So:
  - The 0o000-directory case is a new Extended ID, AC-X-ATTR-3 (OS linux, macos), and
    AC-SAFE-13 points to it.
  - AC-CLI-1 gets the Core-side parse boundary for `--max-ratio`. The overflow boundary on
    an encoded blob is in AC-X-ZSTD-2.
- **M1's recorded-identity cleanup** changes two existing criteria. AC-SAFE-8 and AC-SAFE-15
  plant a link inside staging, which cleanup now leaves in place, so "staging must be gone"
  became "nothing the extractor created remains".

Still open, for the next reviewer (until `plan-v1`), in addition to §9g's list:

- **M1's ownership check** (the reason for the `fstat` route) can't be exercised by a
  single-user test. AC-SAFE-14 tests mode, emptiness, links and non-directories only.
- **M5's `AT_SYMLINK_NOFOLLOW` support.** D16 doesn't pin runner kernels.
  - Linux honours the flag for `fchmodat` only through `fchmodat2` (kernel 6.6 or later), or
    glibc's emulation.
  - On the owner's WSL machine (kernel 6.6.87, glibc 2.39), the reviewer's `n17_handle.py`
    shows it works.
  - Whether `rustix` exposes it, and what `ubuntu-latest` and `macos-latest` do, is
    unverified until the first CI run. The spec's fallback covers a platform without it.
  - **Settled in round 9 (§9i, P1):** rustix 1.1.4 doesn't expose it on Linux, so the
    fallback is always taken there. The fallback's original justification ("staging is
    private") was false, because staging became 0755 before the rename. Since P1, staging
    stays 0700 until after the rename and its identity check, which makes the
    justification true.

## 9i. Review round 9 decisions (fourth independent review: 5 new findings)

| # | Item | Owner decision |
|---|---|---|
| 1 | P1 | Fix 1. Staging stays at 0700 (on Windows, its private DACL) until the final rename has succeeded and the post-rename identity check has passed. Only then are the final permissions applied, through the handle. Fix 2 (removing the follow-the-link fallback) is skipped. Fix 3's hook is added to AC-X-ATTR-3. §12.6, "Final permissions", Cleanup's "Restrictive modes" and §9h now agree, and nothing says staging is 0755 before the rename. |
| 2 | P2 | Compare `st_mode & 0o777` with 0700, so setuid, setgid and sticky are ignored. After `mkdirat`, call `fchmod(handle, 0700)`, so the umask can't matter. The extractor clears any inherited S_ISGID on every directory it creates (EXT-5), and the spec says so. A Linux test with a setgid parent is added (AC-SAFE-4). |
| 3 | P3 | AC-X-ZSTD-2 adds `--max-ratio 54738112978366623` on `zstd-compressed`, expecting exit 0. |
| 4 | P4 | On Windows, staging is opened without `FILE_SHARE_DELETE`. The Windows branches of the staging-race tests say: the swap is refused, then the extractor's own rename through its handle succeeds, and nothing outside staging changes. |
| 5 | P5 | On filesystems without Unix modes (vfat, exFAT, CIFS, drvfs `/mnt/c` without `metadata`), extraction is refused with `extract.unsafe-object`, with a documented note. |
| 6 | AC-SAFE-8, AC-SAFE-15 | The contradictory wording about whether staging must be gone is fixed. |

How these were applied, where the planner had to choose:
- **P1's fix-3 hook versus skipping fix 2.** With fix 2 skipped, Linux cleanup uses the
  fallback that follows links, and the hook runs as the extractor's own user, whom 0700
  doesn't stop. A same-user swap on Linux would therefore change the outside file even in a
  correct implementation. So AC-X-ATTR-3's hook:
  - asserts on Linux and macOS that staging is still 0700 and owned by the extractor's user
    at that moment, which is what stops every other user;
  - performs the real swap only on macOS, where `fchmodat` honours `AT_SYMLINK_NOFOLLOW`;
  - requires that nothing outside staging changed, in every case.
- **P4 also covers `staging_rename_race`.** Its Windows branch assumed the hook's rename
  succeeds. Without `FILE_SHARE_DELETE` it can't, so it now gets the same "swap refused,
  then success" branch as `staging_open_race` and `staging_swap`.
- **P1 moves `staging_swap`'s hook point.** It used to fire "just before the final
  permissions are set", but the final permissions now come after the rename. It now fires
  just before the pre-rename identity check.
- **P1 adds an outcome.** If setting the final permissions fails after the rename, the
  result is `io`, and cleanup applies through the same handle. The directory is still 0700
  at that point.

Known v1 limitation (P5): **extracting onto filesystems without Unix modes** (vfat, exFAT,
CIFS, drvfs without `metadata`) is refused (superseded by Q5: refused or io, non-normative).
To be revisited after v1.

Still open, for the next reviewer (until `plan-v1`), in addition to §9g's and §9h's lists:

- **P4's Windows behaviour** is unverified until the first Windows CI run: that a handle
  opened without `FILE_SHARE_DELETE` makes another process's rename fail, and that the
  extractor's own `FileRenameInfo` rename through that handle succeeds.
- **The Linux check-then-chmod swap** in AC-X-ATTR-3 isn't exercised, because it needs a
  second user. Its safety rests on staging's 0700 mode, which the hook does assert.

**Final check (`reviews/review-5.md`): Q1–Q7, all accepted and applied.** This was the last
review round before `plan-v1`.

| # | Item | Owner decision |
|---|---|---|
| 1 | Q1 | Check before you chmod. After `openat`, `fstat` must show a directory owned by the effective user ID, with `st_mode & 0o077 == 0`, and no entries. Only then `fchmod(handle, 0700)`, then confirm `st_mode & 0o777 == 0700`. P2's `fchmod` and the `& 0o777` comparison are kept, and "nothing under that name is touched" holds on every refusal path. |
| 2 | Q2 | AC-X-ATTR-3's assertion list gets an exception: in the macOS swap case, the planted symlink, `d` and staging remain, and every other object the extractor created is gone. |
| 3 | Q3 | On macOS, AC-X-ATTR-3's hook point is "immediately before the `fchmodat` on `x`". |
| 4 | Q4 | After the rename, the M9 step applies to the destination name: an `fstatat(AT_SYMLINK_NOFOLLOW)` identity check, then removal. |
| 5 | Q5 | P5's result is described as "refused or `io`", marked non-normative. |
| 6 | Q6 | AC-SAFE-8 and AC-SAFE-15: "…is gone, except the directories on the path to the planted link". |
| 7 | Q7 | `staging_props`'s first hook moves to after the holding checks. |

How Q1's "nothing under that name is touched" was kept:
- Step 4's `fchmod` runs only on a directory that has passed step 3: empty, owned by the
  extractor's user, with no group or other access. No other user can produce that.
- FORMAT_SPEC states this as the one exception to "touched" on a refusal path.
- Cleanup's first exception notes that the extractor's own directory may remain under the
  staging name if step 4 or 5 fails.

**Post-review edit (owner decision, after review 6): AC-ENG-7 is conditional on the
counting-allocator users that exist.** This wasn't raised by a reviewer. It was found while
drafting TODO.md.
- The problem: AC-ENG-7 part 3 grepped `crates/chst-format/tests/zstd_bombs.rs`, a test
  crate that exists only for Extended (AC-X-ZSTD-2). Under the Core cut it fails, so Core
  could never be done. **Reason for the change: Core must not need an Extended-only test file.**
- AC-ENG-7 now checks each counting-allocator user that exists, and still fails if any file
  has unsafe code outside the D18 exceptions. Under the Extended cut it also requires
  `zstd_bombs.rs` to exist.
- AC-X-ZSTD-2 MUST fail if `zstd_bombs.rs` doesn't exist, doesn't use the counting
  allocator, or fails AC-ENG-7's checks for an allocator user. So the file can't be absent
  in Extended, and neither ID can pass by skipping it.
- AC-X-ZSTD-2 also runs `zstd_bombs.rs` with `cargo_test_nonempty`, so at least one real
  counting-allocator bomb test must run and pass. The file can't be satisfied by an empty or
  placeholder test.

## 10. Checkpoints

Checkpoints and their order only. Tasks live in TODO.md once it exists.

1. **PLANNING, documents:** this document, FORMAT_SPEC.md and ACCEPTANCE.md, revised through
   review rounds 1 and 2.
2. **PLANNING, fixtures:** the generator in `fixtures/gen/` and all fixtures are built.
   The worked example is regenerated from the generator and matches FORMAT_SPEC §18 byte
   for byte (AC-META-6). The fixture checksum stays unset until the owner approves the
   fixtures.
3. **Independent review** of the documents and fixtures.
4. **`plan-v1`:** the owner tags it. The phase changes to IMPLEMENTATION.
5. **First implementation tasks:** `check.sh` with its helper scripts, then the CI workflow
   file. Stop.
6. **`checks-v1`:** the owner reviews `check.sh`, the helper scripts and the workflow. The
   first full CI run confirms runner feasibility.
7. **Core implementation,** task by task from TODO.md, until Core is done (ACCEPTANCE.md §2).
8. **Extended,** after the owner changes the cut to Extended.
