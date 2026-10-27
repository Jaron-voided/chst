# Chst Container Format Specification — Version 1.0

> Status: **DRAFT for independent review.** Normative and language-neutral.
> Rationale lives in [`DESIGN.md`](DESIGN.md) (decision IDs D1–D13 are cited in brackets).
> "Chst" is a working name.

## 1. Introduction and conformance

This document specifies the byte format of a Chst container, and the behaviour of
programs that read, write and extract it.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT** and **MAY**
are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they
appear in all capitals.

Conformance classes:

| Class | Must satisfy |
|---|---|
| **Reader** | §§2–13, §16, Appendix A. It MUST detect every reader rule violation. |
| **Writer** | Produce only files in canonical form (§11) that satisfy every reader rule, plus §14 |
| **Extractor** | A reader that writes entries to a filesystem; additionally §15 |
| **Reporting tool** | Additionally, Appendix B for its `--json` reports |

**Rules.** Each requirement a reader checks has a rule ID in bold, such as **HDR-2**.
Every reader rule that can produce an error maps to exactly one error category and one
detail code (§16, Appendix A). A few writer and extractor rules have more than one outcome,
each listed in Appendix A, and some are requirements only, with no error of their own.
A violation of any reader rule makes the file invalid. A reader MUST NOT report success
for an invalid file.

## 2. Conventions

- All integers are unsigned and fixed-width **little-endian**: u8, u16, u32, u64.
  Signed integers (Extended only) are two's-complement little-endian. [D3]
- All offsets are **absolute** byte offsets from the start of the file, except path
  offsets, which are relative to the start of the PATH_POOL payload (§9).
- There is no alignment padding anywhere. Fields can start at any byte offset.
- `H(x)` denotes the hash function selected by the header's `hash_alg` field. In version
  1.0 the only defined algorithm is **SHA-256** (FIPS 180-4), with 32-byte output. [D6]
- `a ‖ b` denotes byte concatenation. Ranges `[s, e)` are half-open.
- "Zero" for a multi-byte field means every byte is `0x00`.

## 3. File layout

A container consists of four regions, in this order, with no gaps: [D1]

| Region | Offset | Length |
|---|---|---|
| Header | 0 | 32 |
| Blob data | 32 | `index_offset − 32` (MAY be 0) |
| Index | `index_offset` | `index_length` |
| Trailer | `file_length − 56` | 56 |

Coverage: every blob's stored bytes are covered by its key (§7). The header, the whole
index and the first 16 bytes of the trailer are covered by the structure hash (§5).

## 4. Header (32 bytes)

| Offset | Size | Field | Value / rule |
|---|---|---|---|
| 0 | 8 | `magic` | `43 48 53 54 0D 0A 1A 00` (ASCII `CHST`, CR, LF, SUB, NUL) |
| 8 | 2 | `major_version` | `1` |
| 10 | 2 | `minor_version` | `0`. Writers MUST write 0 unless a later revision of this specification changes the encoding. Readers MUST accept any value (F32) |
| 12 | 1 | `hash_alg` | `1` = SHA-256 (§12.4) |
| 13 | 3 | `reserved` | Zero |
| 16 | 8 | `required_flags` | Bit set of required features (§12.1). Core files: 0 |
| 24 | 8 | `optional_flags` | Bit set of optional features (§12.1). Core files: 0 |

Rules:

- **HDR-1** The file length MUST be at least 88 bytes (header + trailer).
- **HDR-2** `magic` MUST equal the value above.
- **HDR-3** `major_version` MUST be 1. A reader MUST reject any other value without
  interpreting the rest of the file.
- **HDR-4** `hash_alg` MUST be an algorithm the reader implements. Every `hash_alg` value
  has a 32-byte output, because keys are 32 bytes in every record. A different width needs a
  new major version.
- **HDR-5** `reserved` MUST be zero.
- **HDR-6** Every bit set in `required_flags` MUST be a feature the reader implements.
- Bits set in `optional_flags` that the reader does not know MUST be ignored. That is not
  a violation.

## 5. Trailer (56 bytes, at `file_length − 56`)

| Offset in trailer | Size | Field | Value / rule |
|---|---|---|---|
| 0 | 8 | `index_offset` | Absolute offset of the index |
| 8 | 8 | `index_length` | Length of the index in bytes |
| 16 | 32 | `structure_hash` | `H(header ‖ index ‖ trailer[0..16))` |
| 48 | 8 | `trailer_magic` | `00 1A 0A 0D 54 53 48 43` |

Rules:

- **TRL-1** `trailer_magic` MUST equal the value above.
- **TRL-2** `index_offset ≥ 32`, and `index_offset + index_length + 56 = file_length`.
  The arithmetic MUST NOT overflow; an overflow is a violation.
- **TRL-3** `structure_hash` MUST equal `H(header ‖ index ‖ trailer[0..16))`, computed
  over exactly those 32 + `index_length` + 16 bytes.

## 6. Index and sections

The index is a sequence of **sections** that exactly fills `[index_offset,
index_offset + index_length)`. [D4] Each section is a 16-byte section header followed by
its payload.

| Offset in section | Size | Field |
|---|---|---|
| 0 | 4 | `type`. Bit 31 (`0x80000000`) is the **must-understand** bit |
| 4 | 4 | `record_size`, in bytes |
| 8 | 8 | `record_count` |
| 16 | `record_size × record_count` | payload |

Rules:

- **SEC-1** Each section header MUST lie entirely within the index. `record_size ×
  record_count` MUST be computed without overflow, and the payload MUST lie entirely
  within the index. The next section starts immediately after the payload. The last
  section MUST end exactly at the end of the index.
- **SEC-2** A section whose `type` is unknown to the reader and has the must-understand
  bit set makes the file unsupported. An unknown section without that bit MUST be skipped.
- **SEC-3** The first three sections MUST be `BLOB_TABLE`, `ENTRY_TABLE` and `PATH_POOL`,
  in that order. Sections after the first three MUST have strictly ascending `type` values,
  compared as u32 among themselves, and none of them may have one of the first three types.
- **SEC-4** For each section type the reader implements, `record_size` MUST be at least the
  base size for that type (§12.3). For `PATH_POOL` and `KV_METADATA` it MUST be exactly 1,
  because their payloads are byte streams.
- **SEC-5** If `record_size` satisfies SEC-4 and the reader knows every flag set in the
  header, each known section's `record_size` MUST equal the size defined for those flags
  (§12.3). Otherwise a reader MUST accept a larger `record_size` for BLOB_TABLE and
  ENTRY_TABLE, and ignore the extra bytes in each record.

Sections defined in 1.0 (registry in §12.3):

| Type | Name | Base record size |
|---|---|---|
| `0x80000001` | BLOB_TABLE | 64 |
| `0x80000002` | ENTRY_TABLE | 48 |
| `0x80000003` | PATH_POOL | 1 |
| `0x00000010` | KV_METADATA (Extended) | 1 |

## 7. Blob table

Each BLOB_TABLE record (base size 64) describes one stored byte sequence. [D2]

| Offset in record | Size | Field |
|---|---|---|
| 0 | 32 | `key` = `H(stored bytes)` |
| 32 | 8 | `offset`: absolute offset of the stored bytes |
| 40 | 8 | `stored_length` |
| 48 | 8 | `raw_length`: length after decoding |
| 56 | 1 | `encoding`: 0 = stored, 1 = Zstandard (§12.5) |
| 57 | 7 | `reserved`: zero |

Rules:

- **BLB-1** `reserved` MUST be zero.
- **BLB-2** `encoding` MUST be 0, or 1 when the `ZSTD` required flag is set and the reader
  implements `ZSTD`. No other value is defined. (A reader that doesn't implement `ZSTD`
  never reaches this rule for such a file: HDR-6 stops it first, §13.)
- **BLB-3** If `encoding` is 0, then `stored_length` MUST equal `raw_length`.
- **BLB-4** The blobs MUST tile the data region in table order. Blob 0 has `offset` 32.
  Each next blob's `offset` is the previous `offset + stored_length`. The last blob ends
  exactly at `index_offset`. With zero blobs, `index_offset` MUST be 32. Arithmetic MUST
  NOT overflow.
- **BLB-5** No two records have the same `key`.
- **BLB-6** `key` MUST equal `H` of the `stored_length` bytes at `offset`. This check needs
  the blob data; it is required for verify and extract (§13 step 11).
- **BLB-7** Every blob MUST be referenced by at least one file entry.

A zero-length blob is valid; its key is `H` of the empty string. All empty files share it.

## 8. Entry table

Each ENTRY_TABLE record (base size 48) describes one path.

| Offset in record | Size | Field |
|---|---|---|
| 0 | 8 | `path_offset`: offset into the PATH_POOL payload |
| 8 | 4 | `path_length`: bytes |
| 12 | 1 | `type`: 1 = directory, 2 = regular file |
| 13 | 3 | `reserved`: zero |
| 16 | 32 | `blob_key`: the key of the file's blob, or zero for a directory |

The root of the packed tree is not an entry. Paths are relative to it. A file's content
is the decoded content of the blob whose `key` equals `blob_key`. Its size is that blob's
`raw_length`.

Rules:

- **ENT-1** `type` MUST be 1 or 2.
- **ENT-2** `reserved` MUST be zero.
- **ENT-3** For a directory, `blob_key` MUST be zero.
- **ENT-4** For a file, `blob_key` MUST equal the `key` of some blob record.
- **ENT-5** `[path_offset, path_offset + path_length)` MUST lie within the PATH_POOL
  payload, computed without overflow.
- **ENT-6** For every entry whose path contains `/`, the path formed by removing its last
  segment MUST be the path of a **directory** entry. Every ancestor directory is therefore
  explicit. [D10b]

## 9. Path pool and path rules

The PATH_POOL payload (record size 1) is the concatenation of all entry paths, in entry
order, with no separators or terminators.

A **path** is a byte string that MUST satisfy all of the following. [D8] "Segment" means a
maximal substring between `/` characters.

- **PATH-1** The path MUST be valid UTF-8 (no overlong forms, surrogates or values above
  U+10FFFF).
- **PATH-2** The path MUST be in Unicode Normalization Form C (NFC): unchanged by NFC
  normalisation using **exactly the Unicode 16.0 tables**. Every reader and writer MUST use
  those tables, so conforming tools agree on every path. Tools outside this specification
  (operating systems, file managers, newer libraries) may judge code points added after
  Unicode 16.0 differently. The fixture `core/invalid/PATH-2-unicode16` holds a path that
  Unicode 15.x and 16.0 judge differently: `x` U+0301 U+113CE is NFC under 15.x, but not
  under 16.0.
- **PATH-3** The path length MUST be 1–4096 bytes, and every segment 1–255 bytes.
- **PATH-4** The path MUST NOT begin or end with `/`, and MUST NOT contain `//`.
- **PATH-5** No segment may be `.` or `..`.
- **PATH-6** No control or directional-formatting code point:
  - U+0000–U+001F, U+007F and the C1 controls U+0080–U+009F;
  - every bidirectional control character: U+061C ARABIC LETTER MARK, U+200E and U+200F
    (the left-to-right and right-to-left marks), the embedding and override characters
    U+202A–U+202E, and the isolate characters U+2066–U+2069 (N15).

  The bidirectional characters can make an extracted name display as something else in
  every file manager (for example `invoice` + U+202E + `fdp.exe` displays as `invoiceexe.pdf`). Ordinary right-to-left names use
  right-to-left letters, not these characters, so they're unaffected. (For bytes that aren't
  valid UTF-8, PATH-1 applies first.)
- **PATH-7** None of the characters `\ < > : " | ? *`.
- **PATH-8** No segment other than `.` and `..` may end in `.` or ` ` (U+0020). (`.` and
  `..` are PATH-5's concern.)
- **PATH-9** No segment's **stem** may be a Windows reserved device name. The stem is the
  part before the first `.` (or the whole segment if it has none), with any trailing
  spaces removed, so `CON .txt` counts as `CON`. The comparison is ASCII-case-insensitive,
  against: `CON`, `PRN`, `AUX`, `NUL`, `CONIN$`, `CONOUT$`, `COM0`–`COM9`,
  `LPT0`–`LPT9`, `COM¹`, `COM²`, `COM³`, `LPT¹`, `LPT²`, `LPT³`.
- **PATH-10** The number of segments (the depth) MUST be at most 256.
- **PATH-11** No two entries may have equal **fold keys**. A fold key is the path with
  ASCII letters `A`–`Z` mapped to `a`–`z`, the path already being NFC. Exact duplicates
  are caught by CAN-1.

Non-ASCII case collisions are not a format violation. Extractors catch them on
case-insensitive filesystems through EXT-2. Because PATH-7 forbids `:`, no path can name
an NTFS alternate data stream (`f.txt:s`, `f.txt::$DATA`) or a drive (`C:`). §15.1 lists
the per-platform consequences.

## 10. Limits [D11]

### 10.1 Hard maxima (violation → `malformed`)

| Rule | Quantity | Maximum |
|---|---|---|
| **LIM-2** | `index_length` | 2³² bytes |
| PATH-3 | Path length / segment length | 4096 / 255 bytes |
| PATH-10 | Path depth | 256 |

Blob lengths are bounded only by u64 and TRL-2/BLB-4.

**LIM-1 is retired (F7).** The entry count is already bounded by LIM-2 together with SEC-4:
at most ⌊2³² / 48⌋ = 89,478,485 entries fit in an index. The rule ID isn't reused.

### 10.2 Configurable limits (violation → `limit-exceeded`)

A reader MUST support configuring each of these limits. Its **defaults MUST be at least**
the values shown, so every conforming reader accepts files within the defaults.

| Rule | Quantity | Default (must-support minimum) | Checked by |
|---|---|---|---|
| **LIM-3** | Number of entries | 1,048,576 | all |
| **LIM-4** | `index_length` | 268,435,456 (256 MiB) | all |
| **LIM-5** | Total logical size: the sum, over **every file entry**, of the `raw_length` of the blob it references, computed without overflow (a sum of 2⁶⁴ or more exceeds every limit) | 68,719,476,736 (64 GiB) | verify, extract |
| **LIM-6** | Compression ratio of an encoded blob (Extended): violated if and only if `raw_length > limit × stored_length`, computed exactly, in at least 128 bits: both factors are below 2⁶⁴, so the product always fits (M3) | 1000 | all |

The CLI flag for each limit is in Appendix C.

**LIM-5 counts each reference again.** If 1,000 file entries share one 1 MiB blob, they
contribute 1,000 MiB, not 1 MiB, even though the blob is stored once. This is the only
defence against dedup amplification, because there is no per-blob reference limit.
`verify` reports the same sum as `summary.extracted_bytes`.

### 10.3 Allocation discipline

Before allocating memory or iterating in proportion to any declared quantity, a reader
MUST check it against both the actual bytes available (TRL-2, SEC-1) and the limits above.
In particular, `index_length` MUST be checked against LIM-2 and LIM-4 before the index is
read into memory.

## 11. Canonical form [D9]

A writer MUST produce, and a reader MUST require, exactly one encoding per input tree:

- **CAN-1** Entries MUST be in strictly ascending order of their path bytes, compared as
  unsigned bytes. A shorter prefix sorts first. Strictness forbids duplicates. Because a
  parent's path is a prefix of its children's paths, parents always precede their
  descendants.
- **CAN-2** Let K be the distinct keys referenced by file entries, in order of first
  reference (walking entries in entry order). The first |K| blob records MUST have exactly
  the keys K, in that order. Any further records are unreferenced (BLB-7) or have duplicate
  keys (BLB-5), and aren't CAN-2 violations.
- **CAN-3** Each entry's `path_offset` MUST equal the sum of the `path_length`s of all
  preceding entries. The PATH_POOL payload length MUST equal the sum of all `path_length`s.
- **FLG-1** A writer MUST set a known flag if and only if the file uses the corresponding
  feature, and a reader MUST check this for every flag it knows:
  - `ZSTD` ⇔ at least one blob has `encoding` 1.
  - `ENTRY_ATTRS` set ⇒ ENTRY_TABLE `record_size` ≥ 64. This is one direction only (N9,
    M4): a record size of 64 or more without `ENTRY_ATTRS` isn't an FLG-1 violation, because
    a future optional flag may widen entry records (§17). When the reader knows every flag
    that's set, SEC-5 enforces the exact size.
  - `KV_METADATA` ⇔ a KV_METADATA section is present.
- Section order is fixed by SEC-3.
- Core files contain no timestamps, tool identity or other environment-derived data.

## 12. Registries

### 12.1 Feature flags

| Flag | Bit | Set | Feature | Section |
|---|---|---|---|---|
| `ZSTD` | 0 | required | Zstandard-encoded blobs | §12.5 |
| `ENTRY_ATTRS` | 0 | optional | Entry modification time and permission bits | §12.6 |
| `KV_METADATA` | 1 | optional | Container key/value metadata section | §12.7 |

All other bits are unassigned. A writer MUST NOT set unassigned bits.

### 12.2 Entry types

`1` directory · `2` regular file · `3` reserved for symlinks (Later; a future required
flag) · all others undefined.

### 12.3 Section types and record sizes

| Type | Name | Record size | Required |
|---|---|---|---|
| `0x80000001` | BLOB_TABLE | 64 | always |
| `0x80000002` | ENTRY_TABLE | 48; 64 if `ENTRY_ATTRS` | always |
| `0x80000003` | PATH_POOL | 1 | always |
| `0x00000010` | KV_METADATA | 1 | iff `KV_METADATA` |

### 12.4 Hash algorithms

`1` = SHA-256 (FIPS 180-4), 32-byte output. All other values are undefined.

### 12.5 Extended: Zstandard blobs (`ZSTD`, required) [D7]

- A blob with `encoding` 1 contains exactly one complete Zstandard frame (RFC 8878),
  consuming exactly `stored_length` bytes. Skippable frames and trailing bytes are not
  allowed.
- **ZST-1** If the frame header has a Frame_Content_Size, it MUST equal `raw_length`. This
  is judged from the header alone, before any block is decoded (N1).
- **ZST-2** Every other way an encoded blob can fail is ZST-2 (N1):
  - `stored_length` < 4. This is checked in step 10, so no decoder ever sees a shorter blob.
  - A bad frame header: wrong magic (including a skippable frame), the reserved bit set,
    a header longer than the blob, Window_Size over 8 MiB (8,388,608 bytes; with
    Single_Segment_Flag set, the window is Frame_Content_Size), or a Dictionary_ID other
    than absent or 0.
  - Anything found while decoding: a reserved block type, a Block_Size over
    min(Window_Size, 128 KiB), a truncated block, a corrupt Compressed block, output that
    would exceed `raw_length`, output shorter than `raw_length`, any byte after the frame
    (including a truncated checksum), or a content checksum that doesn't match.
  - Decoding is one pass with output capped at `raw_length`: the decoder stops at the first
    byte beyond it. Decoders MUST be configured to refuse larger windows (libzstd
    `ZSTD_d_windowLogMax` = 23), so memory is bounded whatever the header claims.
- **ZST-3** For `encoding` 1, `stored_length < raw_length` MUST hold. A writer stores a blob
  compressed only if the result is strictly smaller.
- The key still hashes the stored (compressed) bytes, so BLB-6 is checked without decoding.

### 12.6 Extended: entry attributes (`ENTRY_ATTRS`, optional)

The ENTRY_TABLE record size becomes 64. Bytes 0–47 are unchanged, followed by:

| Offset in record | Size | Field |
|---|---|---|
| 48 | 8 | `mtime_seconds`: signed i64, seconds since 1970-01-01T00:00:00Z |
| 56 | 4 | `mtime_nanos`: u32 |
| 60 | 2 | `mode`: u16 permission bits |
| 62 | 2 | `reserved`: zero |

- **ATT-1** `mtime_nanos` MUST be < 1,000,000,000. `mode` MUST be ≤ `0o777`. `reserved`
  MUST be zero.
- Extractors MUST NOT set setuid, setgid or sticky bits.
- **Applying attributes (F27).** An extractor applies each file's `mode` with `fchmod` on the
  open handle, after writing its content. It applies directory modes, and every mtime
  (files and directories), only after all entries are written, in reverse canonical order,
  so creating children can't change a parent's mtime and a read-only directory can't block
  its own children. Stored modes are applied as stored, masked with 0o777, and are **not**
  subject to the umask. On Windows, modes are ignored and mtimes are applied.
  - All of this happens inside staging, before the final rename. Staging's own mode stays
    0700 throughout (EXT-4, "Staging stays private", P1), so a stored mode of 0o777 on a
    directory inside it never exposes that directory to other users before extraction has
    finished.

### 12.7 Extended: KV metadata (`KV_METADATA`, optional)

The KV_METADATA payload (record size 1) is a sequence of pairs. Each pair is
`key_length` (u16) ‖ key (UTF-8) ‖ `value_length` (u32) ‖ value (UTF-8).

- **KV-1** The payload MUST contain at least one pair: an empty section would be a second
  encoding of "no metadata". Each key MUST be 1–255 bytes of valid UTF-8, and each value at
  most 65,536 bytes of valid UTF-8. Pairs MUST be in strictly ascending bytewise key order,
  which forbids duplicates. The pairs MUST exactly fill the payload.
- Defined keys: `creator`, `comment`. Others MAY be used.

### 12.8 Extended: selective extract (#6) and exclude patterns (#7)

These features change no bytes of the format. They define tool behaviour only.

- **Patterns.** A pattern is converted to NFC, then matched against whole entry paths, which
  are NFC. Matching works on code points and is case-sensitive.
  - `*` matches any run of code points (possibly none) other than `/`.
  - `?` matches exactly one code point other than `/`.
  - `[...]` matches one code point from a set of literal code points and `x-y` ranges,
    ordered by code point. A leading `!` negates the set. A class never matches `/`.
    - A `]` straight after `[` or `[!` is a literal, not the end of the class, so `[]]`
      matches `]` and `[!]]` matches anything but `]`. That is also how to match a literal
      `[` inside a class: `[[]`.
    - A `-` first or last in the class is a literal, and so is a `-` straight after a
      range: `[a-c-e]` is the set {`a`–`c`, `-`, `e`} (M13).
    - An unterminated `[` or a range with x > y is `usage` / `usage.pattern` (N16). Because
      of the `]` rule, `[]` and `[!]` are unterminated, so a class is never empty.
  - `**` as a complete segment matches zero or more whole segments, so `a/**` matches `a`
    and everything under it.
  - A pattern with no wildcard matches exactly that path.
  - There's no escape character. A pattern containing `\` is `usage` / `usage.pattern`.
- **Selective extract.** An entry is **selected** if a pattern matches it, or if it's under a
  selected directory. Ancestor directories of selected entries are also created, so
  selected entries have their parents, but an ancestor added this way **isn't itself
  selected**, so its other children aren't included. EXT-1 … EXT-10 apply unchanged,
  including the fresh-destination rule. LIM-5 counts only the selected file entries.
  Step 11 covers only the blobs referenced by selected file entries, checked while they're
  written (EXT-7); a damaged blob that isn't selected doesn't fail the extraction (N7).
- **SEL-1** If any given pattern matches no entry, the extractor MUST fail with
  `refused` / `extract.no-match` before creating anything. The message names the first
  unmatched pattern in command-line order.
- **Exclude.** Pack drops every source path that matches any exclude pattern, along with
  everything under an excluded directory. Exclusion is applied during the walk, before W-3:
  an excluded name is never checked for portability, and an excluded directory is never
  opened or descended. The remaining tree is packed canonically. An exclude pattern that
  matches nothing is not an error.

## 13. Reader algorithm

**A reader MUST evaluate the rules in exactly the order below, and report only the first
violation it finds** (F2). This makes every failure's category and detail code
deterministic, so two conforming readers report the same error for the same file.

- **Order inside an item:** for an item marked *per record*, records are scanned in table
  order. For each record, the listed rules are checked in the listed order before moving to
  the next record.
- **Stop at unsupported files:** a reader that finds HDR-6 or SEC-2 reports it and evaluates
  nothing further. A file it can't interpret is never reported as `malformed` (F1).
- **Step 11:** verify and extract perform all steps. List and inspect perform steps 1–10
  and **MUST NOT** perform step 11 (F34).

1. HDR-1 (length).
2. HDR-2 (magic).
3. HDR-3 (major version).
4. HDR-4 (hash algorithm).
5. TRL-1 (trailer magic).
6. TRL-2, then LIM-2, then LIM-4: the index's location and size, before the index is read.
7. Read the index and check TRL-3 (structure hash).
8. HDR-6, then HDR-5.
9. In order:
   - SEC-1, for each section header in turn, framing the whole index;
   - SEC-2, over every section;
   - SEC-3;
   - SEC-4 for every section in file order; then SEC-5 for every section in file order;
   - LIM-3, on the entry count, before allocating per-entry state.
10. In order:
    - (a) *Per blob record:* BLB-1, BLB-2, BLB-3, ZST-2 (only its `stored_length` ≥ 4
      condition), ZST-3, LIM-6.
    - (b) BLB-4.
    - (c) BLB-5.
    - (d) *Per entry:* ENT-1, ENT-2, ENT-3, ENT-4.
    - (e) *Per entry:* ENT-5.
    - (f) CAN-3.
    - (g) *Per entry:* PATH-1, PATH-2, PATH-4, PATH-3, PATH-5, PATH-6, PATH-7, PATH-8,
      PATH-9, PATH-10. PATH-4 comes before PATH-3, so an empty segment (`a//b`, `/a`, `a/`)
      is reported as the more specific PATH-4.
    - (h) CAN-1.
    - (i) *Per entry:* ENT-6.
    - (j) PATH-11.
    - (k) BLB-7.
    - (l) CAN-2.
    - (m) FLG-1, for `ZSTD`, then `ENTRY_ATTRS`, then `KV_METADATA`, each only if the reader
      knows it.
    - (n) *Per entry:* ATT-1.
    - (o) KV-1.
    - (p) LIM-5, for verify and extract only: over all file entries, or over the selected
      entries for a selective extract (§12.8).
11. *Per blob record, in table order* (for a selective extract, only the selected blobs):
    BLB-6. Then, for an encoded blob (§12.5, N1):
    - the frame header: ZST-2;
    - Frame_Content_Size ≠ `raw_length`: ZST-1;
    - one decoding pass with output capped at `raw_length`: any failure is ZST-2.

    An extractor performs step 11 while it writes each file (EXT-7), and reports the same
    rule a verifier would for that blob (§15, "Step 11 while writing", M2).

Because step 7 comes before every structural check, any change to header bytes 10–11 or
13–31, or to the index, is reported as `integrity` (TRL-3), unless it also breaks an earlier
step.

## 14. Writer requirements

- **W-1** A writer MUST emit canonical form (§11) and satisfy every reader rule.
- **W-2** A writer of a file into a filesystem path MUST write to a temporary file in the
  same directory, and atomically rename it into place only after the trailer is written and
  flushed. On any failure, the output path is exactly as it was before: absent, or, under
  W-7 `--force`, the previous file unchanged. No temporary file remains.
- **W-3** Pack tools MUST refuse source names that cannot form valid paths. They MUST
  convert names to NFC before checking, and refuse any resulting PATH-11 collision.
  (`refused` / `pack.unportable-name`)
- **W-4** A writer that dedups MUST hash each source before copying it, and re-hash while
  copying. A mismatch is `refused` / `pack.source-changed`, and no output is produced.
- **W-5** Pack tools MUST NOT follow symlinks. Symlinks and special files (devices, FIFOs,
  sockets) are skipped with warning `pack.skipped`. Hard-linked names are packed as
  independent regular files.
  - **The walk is handle-relative (F23):** each directory and file is opened relative to an
    already-open handle of its parent, with no-follow semantics, never through a full path
    string. A directory swapped for a link during the walk is then never followed, and paths
    beyond PATH_MAX work.
  - **Pass 2 must see the same file:** it MUST check that the opened file has the same
    identity as in pass 1 (device and inode, or the Windows volume serial number and file
    ID). Otherwise the result is `refused` / `pack.source-changed`.
- **W-6** Pack tools MUST refuse an output path located inside the source tree
  (`refused` / `pack.output-in-source`). "Inside" is decided by file identity, not by path
  strings (F22): compare the identity of the output's parent directory, and of each of its
  ancestors, with the source root's identity. That catches symlinked, `..`, bind-mounted
  and case-aliased routes to the same directory.
- **W-7** If the output path already exists, pack MUST refuse
  (`refused` / `pack.output-exists`) and leave it untouched, unless `--force` is given.
  With `--force`, the existing file is replaced atomically through W-2's rename. It stays
  intact until that rename, and stays unchanged if the pack fails. `--force` never replaces
  a directory (`refused` / `pack.output-exists`).
- **W-8** Pack tools MUST NOT traverse reparse points. On Windows, any directory or file with
  the reparse-point attribute (symbolic links, junctions, mount points and other reparse
  tags) is skipped with warning `pack.skipped`, the same as a symlink under W-5.
  Cloud-file placeholders, such as OneDrive files not stored locally, are skipped with the
  distinct warning `pack.skipped-placeholder`, so whole folders can't vanish unnoticed
  behind the generic warning (F46). The pack report counts every skip in
  `summary.skipped`.
  Alternate data streams, extended attributes and ACLs of source files are not stored.
  Only a file's unnamed main data stream is packed.
- **W-9** Pack tools MUST read each source file through the name the operating system
  returned, and store its NFC form (W-3). On macOS, names may come back decomposed (HFS+
  stores a decomposed form; APFS preserves whatever form was used to create the file).
- **W-10** Pack MUST refuse to write a container that a reader with the same limit settings
  would reject under LIM-3 … LIM-5 (F24). The error is `limit-exceeded`, with the same
  detail codes. It also refuses an index over LIM-2's 2³² bytes, as `malformed` /
  `lim.index-size`, whatever `--max-index-bytes` says (N23). Pack accepts the same `--max-*`
  flags as the readers (Appendix C), and no output file is written. When several of these
  limits are exceeded, pack reports the one a reader would report first: LIM-2, then LIM-4,
  then LIM-3, then LIM-5 (M10). A writer MUST NOT emit
  an encoded blob that violates LIM-6 under its `--max-ratio` (default 1000): it stores that
  blob with `encoding` 0 instead (N8).

## 15. Extractor requirements [D10]

**Threat model (F17).** These rules defend against two things: a hostile container, and
other local principals who can write to the destination's parent directory and race the
extractor. They don't defend against a principal who can already write to the destination
itself, or who has the extractor's own privileges. A parent-writer can always replace the
destination after extraction finishes; the guarantees are that nothing is written outside
staging and that no link is ever followed (N2).

**Order of extractor checks (N12, M2, M8).** An extractor checks, in this order: command-line
usage; opening and reading the input file (`io`); EXT-1; §13 steps 1–10, with LIM-5; SEL-1
(selective extract); creating and holding the staging directory (EXT-4); then, per entry in
canonical order, EXT-2 and EXT-8 as it's created, followed by §13 step 11 for its blob while
the file is written (EXT-7); then the final rename and its identity check; then the final
permissions (EXT-4, P1). The first failure is the one reported.

**Step 11 while writing (M2).** For each blob, the extractor reports step 11's rules in step
11's order, so it reports what a verifier would. If the frame fails (ZST-1 or ZST-2, whether
found in the header or while decoding), the extractor stops writing that file but still
reads and hashes the rest of the blob's stored bytes. If the key doesn't match, it reports
BLB-6; otherwise it reports the ZST rule.

- **EXT-1** The destination path MUST NOT exist when extraction starts. The check doesn't
  follow a final symlink, so a dangling symlink also counts as existing. Otherwise the
  result is `refused` / `extract.dest-exists`, and nothing is written.
- **EXT-2** Every directory and file MUST be created with create-new semantics, failing if
  the name already exists. Failure is `refused` / `extract.collision`. This also catches
  collisions PATH-11 cannot see:
  - non-ASCII case collisions on case-insensitive filesystems (the default on NTFS and on
    macOS APFS and HFS+);
  - an entry equal to the Windows 8.3 short name generated for an earlier entry (for
    example, `ABCDEFGHIJ` followed by `ABCDEF~1`).
- **EXT-3** Steps 1–10 of §13, plus LIM-5, MUST pass before anything is created.
- **EXT-4** Entries MUST be created inside a new staging directory, in the destination's
  parent directory (so on the same filesystem).
  - **Creating it (F17):** create-new semantics, with an unpredictable name of the form
    `.<destination name>.chst-<32 lowercase hex digits from a cryptographically secure
    random source>`. Its mode is 0700 (on Windows, see below).
    - If that name would exceed 255 bytes (on Windows, 255 UTF-16 units), `<destination
      name>` is truncated to its longest prefix that fits (N4, M14): at a UTF-8 character
      boundary if the name is valid UTF-8, otherwise at a byte boundary; on Windows, at a
      code point boundary. On macOS the name must also fit HFS+, which stores names
      decomposed: its NFD form must be at most 255 UTF-16 units.
    - If the name already exists, the result is `refused` / `extract.collision`; there's no
      retry, and nothing else is created (N5).
  - **Holding it (N2, M1):** the extractor holds the staging directory by an open handle,
    and confirms that the handle is the directory it just created:
    - Unix, in this order (Q1):
      1. `mkdirat` with mode 0700, relative to the parent's handle.
      2. `openat` of the same name with `O_DIRECTORY | O_NOFOLLOW`.
      3. **Check before changing anything:** `fstat` on the handle MUST show a directory
         owned by the effective user ID, with no group or other permission bits
         (`st_mode & 0o077 == 0`; `mkdirat(0700)` never produces them, whatever the
         umask), and reading it through the handle MUST find no entries other than `.`
         and `..`.
      4. Only then `fchmod(handle, 0700)`, so the umask can't matter and an inherited
         setgid bit is cleared (P2).
      5. Confirm with `fstat` that `st_mode & 0o777` is 0700. setuid, setgid and sticky
         are ignored by this comparison.
    - **Nothing under that name is touched on a refusal (Q1):**
      - A failure at step 2 or 3 happens before anything has been changed.
      - Step 4 runs only on a directory that passed step 3: empty, owned by the extractor's
        user, with no group or other access. That's what the extractor's own new directory
        looks like, and no other user can produce it.
      - A failure at step 4 or 5 therefore leaves only that directory, which is covered
        by Cleanup's first exception.
    - Windows: create and open in one step, with `NtCreateFile` relative to the parent's
      handle, `FILE_CREATE`, `FILE_DIRECTORY_FILE` and `FILE_OPEN_REPARSE_POINT`, passing
      the private DACL (below) in its security descriptor. Its ShareAccess MUST NOT include
      `FILE_SHARE_DELETE` (P4), so no other process can rename or delete staging while the
      extractor holds it. The handle includes `DELETE` access, so the extractor's own rename
      through it still works. No other object can be opened in its place.
    - If the open fails (including at a link: `ELOOP`), or any of these checks fails, the
      result is `refused` / `extract.unsafe-object`. Nothing found under that name is
      touched or removed, apart from step 4's `fchmod` on a directory that has already
      passed step 3 (above).
    - **Filesystems without Unix modes (P5):** on vfat, exFAT, CIFS, or a WSL drvfs mount
      (`/mnt/<drive>`) without the `metadata` option, modes are fixed by mount options, so
      the checks above usually can't succeed. Extraction onto them is a known v1
      limitation (§15.1), not a format rule.
      - *Non-normative (Q5):* the usual result is `refused` / `extract.unsafe-object`,
        from step 3, 4 or 5.
      - Some mount options (for example vfat with `dmask=077`) let those checks pass,
        and the failure then comes later, at the final permissions, as `io`.
      - With `quiet`, chmod reports success without changing anything, so extraction may
        complete with modes fixed by the mount.
      - So the result on such a filesystem is "refused or `io`", or a completed extraction
        with the mount's modes. An extractor isn't required to detect the filesystem type.
    - The extractor records the handle's identity (device and inode, or volume serial
      number and file ID). Every later operation on staging uses that handle: the writes
      under it, its final permissions, and cleanup.
    - Immediately before the final rename, the staging name MUST still resolve, without
      following links, to that identity; immediately after it, the destination MUST. On a
      mismatch the result is `refused` / `extract.unsafe-object`, and cleanup applies, with
      the exceptions listed there.
  - **Staging stays private until it's the destination (P1).** Staging's own mode stays
    0700 (on Windows, its private DACL) from creation until the final rename has succeeded
    and the post-rename identity check has passed. So no other user can reach any name
    inside it during extraction or during any cleanup, whatever modes §12.6 has applied to
    directories inside it.
  - **Final permissions (N6, P1),** set through the handle only after the final rename has
    succeeded and the post-rename identity check has passed:
    - Unix: mode `0755 & ~umask`, in Core and Extended alike.
    - Windows: the staging directory's DACL is protected, with one non-inheritable ACE
      granting access only to the current user. Each object extracted into it is created
      with the inheritable ACEs of the destination's parent, so it doesn't inherit the
      private ACE. After the rename and the identity check, the staging DACL is replaced,
      through the handle, by an unprotected DACL that inherits from the destination's
      parent.
    - If setting the final permissions fails, the result is `io`, and cleanup applies to
      the renamed directory through the same handle. It's still mode 0700, and its name
      is now the destination's.
  - **Finishing (F16):** on success, the staging directory is renamed to the destination
    with a rename that **MUST NOT replace an existing object**: `renameat2(RENAME_NOREPLACE)`
    on Linux, `renameatx_np(RENAME_EXCL)` on macOS, and
    `SetFileInformationByHandle(FileRenameInfo)` with `ReplaceIfExists = FALSE` on Windows.
    - If the destination exists by then (for example, created after the EXT-1 check), the
      result is `refused` / `extract.dest-exists`, and cleanup applies.
    - If the filesystem doesn't support a no-replace rename, the result is `io` /
      `extract.no-atomic-rename`, and cleanup applies.
  - **Cleanup (F18, M1, M5, M9):** on any error, including integrity, the staging directory
    and everything the extractor created in it MUST be removed, except as listed below. The
    extractor MUST NOT leave behind a destination it created; an object someone else created
    at the destination is left untouched (N3).
    - **Only what it created:** the extractor records the identity of every object it
      creates under staging. Cleanup walks from the staging handle and checks each name
      without following links (`fstatat` with `AT_SYMLINK_NOFOLLOW`, or a Windows
      handle-relative open with `FILE_FLAG_OPEN_REPARSE_POINT`). It removes an object only
      if its identity is one it recorded; anything else is left in place, and so is the
      directory holding it.
    - **How:** removal is relative to open directory handles (`unlinkat`, or Windows
      handle-relative deletion). It never follows a link or reparse point, and never
      re-resolves a full path.
    - **Restrictive modes (N17, M5):** before removing a directory's children, cleanup
      restores the owner's read, write and search permissions on that directory, so modes
      applied earlier (§12.6) can't block it. It uses `fchmod` if it holds an open handle to
      the directory. Otherwise it uses `fchmodat` on the directory's name, relative to the
      parent's held handle, with `AT_SYMLINK_NOFOLLOW` where the platform supports that
      flag. Where it doesn't (the call fails with `EOPNOTSUPP` or `ENOTSUP`), the extractor
      first checks with `fstatat(AT_SYMLINK_NOFOLLOW)` that the name is a directory with
      the recorded identity, then calls `fchmodat` without the flag. That's safe because
      staging's own mode is 0700 whenever cleanup runs ("Staging stays private", P1), so no
      other user can change names inside it between the check and the call. On Linux with
      `rustix`, the approved crate, this fallback is always the path taken: rustix returns
      `EOPNOTSUPP` for `AT_SYMLINK_NOFOLLOW` on `fchmodat`.
    - **The staging name itself (M9):** last, cleanup removes the staging directory's own
      name from the parent, after checking with `fstatat(AT_SYMLINK_NOFOLLOW)` that the
      name still has staging's recorded identity. If it doesn't, the name is left alone.
      After a successful final rename (the `io` outcome of "Final permissions"), the name
      is the destination's: the same identity check, then removal, apply to the
      destination name (Q4).
    - **Exceptions (M9):**
      - If the open or the checks right after creating staging fail, nothing under the
        staging name is touched (apart from step 4's `fchmod` on a directory that passed
        step 3, Q1), and nothing is removed. The directory the extractor created may
        remain, empty, wherever it was moved, or under the staging name if step 4 or 5
        failed.
      - If the staging name stops leading to staging (a mismatch before the final rename),
        staging is emptied through its handle but can't be removed by name. It remains,
        empty, wherever it was moved.
      - If the mismatch is found just after the final rename, the object now at the
        destination was moved there by the extractor's rename but isn't the extractor's.
        It's left untouched. This is the one case where an object the extractor moved stays
        at the destination. Staging is emptied through its handle, as above.
  - **After a crash (F43):** a crash can leave a staging directory behind. It's recognised
    by the name pattern above, and can be deleted by hand.
- **EXT-5** In Core, files are created with mode 0644 and directories with 0755, both
  subject to the process umask. Modes are ignored on Windows. setuid, setgid and sticky
  bits MUST NOT be set.
  - **Inherited setgid (P2):** on Linux, a directory created under a setgid directory
    inherits S_ISGID. So the extractor checks every directory it creates with `fstat` on its
    handle, and clears an inherited S_ISGID with `fchmod`, in Core and Extended alike.
    Staging's own setgid bit is already cleared by EXT-4's `fchmod(handle, 0700)`.
- **EXT-6** No filesystem object outside the staging directory may be created or modified,
  except the destination created by EXT-4's final rename (F20).
- **EXT-7** Each file's content MUST be checked against its key (BLB-6) **while it is
  written, not in a separate pass before writing** (F14). On mismatch the error is
  `integrity` / `blob.hash`, and EXT-4 cleanup applies. For an encoded blob, the ZST rules
  are checked in the same pass, and the rule reported follows "Step 11 while writing"
  above (M2).
- **EXT-8** Extractors MUST NOT follow a symlink, junction or other reparse point anywhere
  under the staging directory, even one that appears during extraction (for example,
  through a concurrent swap).
  - Each object is created or opened relative to an already-open handle of its parent
    directory, never by re-resolving a full path string.
  - On Unix: `openat`/`mkdirat` with `O_NOFOLLOW` and `O_DIRECTORY` for directories.
  - On Windows: handle-relative opens with `FILE_FLAG_OPEN_REPARSE_POINT`, then a check
    that the opened object has no `FILE_ATTRIBUTE_REPARSE_POINT`.
  - Finding a link or reparse point is `refused` / `extract.unsafe-object`, and EXT-4
    cleanup applies.
  - **Reopening (F21):** canonical order isn't depth-first (`a`, `a-b`, `a.b`, `a/b`), so an
    extractor may need a directory it created earlier. It MAY reopen one only by walking
    from the staging root's handle one segment at a time, with no-follow directory opens,
    checking each opened object as above.
- **EXT-9** Extractors MUST write file content only to the unnamed main data stream, and
  MUST NOT create alternate data streams.
- **EXT-10** Entries MUST be created in canonical order, so parents exist before their
  children. Attributes (Extended) are applied as in §12.6.

### 15.1 Platform notes (normative)

| Platform | Concern | How this spec handles it |
|---|---|---|
| Windows | Reserved device names | PATH-9 (stem rule, trailing spaces, `CONIN$`/`CONOUT$`, superscript digits) |
| Windows | Trailing `.` or space silently stripped by the OS | PATH-8 |
| Windows | Alternate data streams | PATH-7 forbids `:`; W-8 (not packed); EXT-9 (never created) |
| Windows | Junctions, symlinks, mount points, reparse points | W-8 (pack skips them); EXT-8 (extract never follows them) |
| Windows | Case-insensitive names, 8.3 short names | PATH-11 for ASCII; EXT-2 for everything else |
| Windows | Long paths | Extractors MUST use extended-length paths (`\\?\` prefix) or an equivalent, for any length up to PATH-3's 4096 bytes plus the destination prefix. A 255-byte UTF-8 segment never exceeds NTFS's 255 UTF-16 code-unit limit. |
| macOS | Case-insensitive APFS/HFS+ (default) | PATH-11 for ASCII; EXT-2 for everything else |
| macOS | NFC vs NFD names | PATH-2 stores NFC only. W-9 handles decomposed source names. On extract, names are created in NFC; HFS+ may then list them decomposed, which is expected, not an error. Any tool comparing an extracted tree with an archive on macOS MUST compare NFC-normalised names. Since stored paths are unique NFC strings, normalisation-insensitive filesystems cannot produce a normalisation-only collision. |
| macOS | HFS+ limits names to 255 UTF-16 units **after** decomposition (F40) | A valid segment can exceed that once decomposed: 127 × U+0390 is 254 bytes in NFC and 381 UTF-16 units in NFD. Extracting it onto HFS+ fails with `io`. That's a documented limitation, not a format rule. APFS has no such limit. |
| Linux | Depends on the filesystem (F41) | Most Linux filesystems are case-sensitive with no normalisation, so a tree can hold both `é` and `É`. ext4 casefold directories and vfat, ntfs3 and CIFS mounts are case-insensitive, and EXT-2 catches collisions there. Filesystems without Unix modes (vfat, exFAT, CIFS) can't hold a 0700 staging directory, so **extracting onto them is refused** (`refused` / `extract.unsafe-object`; EXT-4, P5). That's a known v1 limitation. Packing from them works. |
| WSL | Windows drives under `/mnt/<drive>` (F41) | The Linux build applies the Unix rules only. The format's portability rules (PATH-7, PATH-9 and others) already make archives safe there. A drvfs mount without the `metadata` option has no Unix modes, so extracting onto it is refused, as on vfat (P5, a known v1 limitation). Run checks from the Linux filesystem. |

## 16. Error model [D12]

Every failure is reported as one **category** and one **detail code**. When a file violates
several rules, a reader MUST report the first one in §13's order, and only that one.

| Category | Meaning | CLI exit code |
|---|---|---|
| `usage` | Invalid command-line usage | 2 |
| `io` | Operating-system I/O failure, including EXT-4's `extract.no-atomic-rename` | 3 |
| `not-a-container` | HDR-1, HDR-2 | 4 |
| `unsupported` | HDR-3, HDR-4, HDR-6, SEC-2 | 5 |
| `malformed` | A structural, path, canonical or hard-limit rule | 6 |
| `integrity` | TRL-3, BLB-6, ZST-1 | 7 |
| `limit-exceeded` | LIM-3 … LIM-6, W-10 | 8 |
| `refused` | A policy refusal on otherwise valid input (EXT-1, EXT-2, EXT-4's `dest-exists`, `collision` and `unsafe-object` outcomes, EXT-8, W-3, W-4, W-6, W-7, SEL-1) | 9 |
| `internal` | An implementation bug; MUST NOT occur | 70 |

Success is exit code 0. Warnings never change the exit code. The full mapping is in
Appendix A.

CLI error line (stderr, first line): `chst: error[<category>/<detail>]: <message>`.

## 17. Versioning policy [D5]

- New optional capabilities are added as optional flags, non-critical sections, or wider
  records (SEC-5). They stay within major version 1.
- New capabilities that older readers must not misinterpret are added as required flags or
  critical sections. They stay within major version 1, and older readers report
  `unsupported`.
- `minor_version` records the spec revision the writer followed. It never affects parsing.
- `major_version` changes only when the header, trailer or section framing changes
  incompatibly.

## 18. Worked example

### 18.1 Input tree

```
docs/            (directory)
docs/a.txt       "hello\n"   (6 bytes)
docs/b.txt       "hello\n"   (identical, so deduplicated)
docs/empty/      (empty directory)
notes.txt        "hi\n"      (3 bytes)
```

Canonical entry order (CAN-1): `docs`, `docs/a.txt`, `docs/b.txt`, `docs/empty`,
`notes.txt`.

Blob keys:

| Blob | Content | Key = SHA-256(content) |
|---|---|---|
| 0 | `hello\n` | `5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03` |
| 1 | `hi\n` | `98ea6e4f216f2fb4b69fff9b3a44842c38686ca685f3f55dc48c5d3fb1107be4` |

Blob 0 is first referenced by `docs/a.txt` and blob 1 by `notes.txt`, so that is the table
order (CAN-2). `docs/b.txt` reuses blob 0.

Sizes: header 32 + data 9 + index 459 (BLOB_TABLE 144 + ENTRY_TABLE 256 + PATH_POOL 59) +
trailer 56 = **556 bytes**.

### 18.2 Field map

| Offset (dec / hex) | Size | Field | Value |
|---|---|---|---|
| 0 / 0x000 | 8 | header.magic | `43 48 53 54 0D 0A 1A 00` |
| 8 / 0x008 | 2 | header.major_version | 1 |
| 10 / 0x00A | 2 | header.minor_version | 0 |
| 12 / 0x00C | 1 | header.hash_alg | 1 (SHA-256) |
| 13 / 0x00D | 3 | header.reserved | 0 |
| 16 / 0x010 | 8 | header.required_flags | 0 |
| 24 / 0x018 | 8 | header.optional_flags | 0 |
| 32 / 0x020 | 6 | blob 0 data | `hello\n` |
| 38 / 0x026 | 3 | blob 1 data | `hi\n` |
| 41 / 0x029 | 4 | BLOB_TABLE.type | `0x80000001` |
| 45 / 0x02D | 4 | BLOB_TABLE.record_size | 64 |
| 49 / 0x031 | 8 | BLOB_TABLE.record_count | 2 |
| 57 / 0x039 | 32 | blob[0].key | `5891b5b5…f6be03` |
| 89 / 0x059 | 8 | blob[0].offset | 32 |
| 97 / 0x061 | 8 | blob[0].stored_length | 6 |
| 105 / 0x069 | 8 | blob[0].raw_length | 6 |
| 113 / 0x071 | 1 | blob[0].encoding | 0 (stored) |
| 114 / 0x072 | 7 | blob[0].reserved | 0 |
| 121 / 0x079 | 32 | blob[1].key | `98ea6e4f…107be4` |
| 153 / 0x099 | 8 | blob[1].offset | 38 |
| 161 / 0x0A1 | 8 | blob[1].stored_length | 3 |
| 169 / 0x0A9 | 8 | blob[1].raw_length | 3 |
| 177 / 0x0B1 | 1 | blob[1].encoding | 0 |
| 178 / 0x0B2 | 7 | blob[1].reserved | 0 |
| 185 / 0x0B9 | 4 | ENTRY_TABLE.type | `0x80000002` |
| 189 / 0x0BD | 4 | ENTRY_TABLE.record_size | 48 |
| 193 / 0x0C1 | 8 | ENTRY_TABLE.record_count | 5 |
| 201 / 0x0C9 | 48 | entry[0] | path_offset 0, path_length 4, type 1 (dir), key zero → `docs` |
| 249 / 0x0F9 | 48 | entry[1] | path_offset 4, path_length 10, type 2, key blob 0 → `docs/a.txt` |
| 297 / 0x129 | 48 | entry[2] | path_offset 14, path_length 10, type 2, key blob 0 → `docs/b.txt` |
| 345 / 0x159 | 48 | entry[3] | path_offset 24, path_length 10, type 1, key zero → `docs/empty` |
| 393 / 0x189 | 48 | entry[4] | path_offset 34, path_length 9, type 2, key blob 1 → `notes.txt` |
| 441 / 0x1B9 | 4 | PATH_POOL.type | `0x80000003` |
| 445 / 0x1BD | 4 | PATH_POOL.record_size | 1 |
| 449 / 0x1C1 | 8 | PATH_POOL.record_count | 43 |
| 457 / 0x1C9 | 43 | PATH_POOL payload | `docsdocs/a.txtdocs/b.txtdocs/emptynotes.txt` |
| 500 / 0x1F4 | 8 | trailer.index_offset | 41 |
| 508 / 0x1FC | 8 | trailer.index_length | 459 |
| 516 / 0x204 | 32 | trailer.structure_hash | `13e9dfcb077661f8dcc8b76d922f47bd656c282e62e746e92dfb9f4c16e6fb9a` |
| 548 / 0x224 | 8 | trailer.trailer_magic | `00 1A 0A 0D 54 53 48 43` |

Each entry record is laid out as `path_offset` (+0, 8 bytes), `path_length` (+8, 4),
`type` (+12, 1), `reserved` (+13, 3), `blob_key` (+16, 32).

The structure hash is SHA-256 over 507 bytes: header (0–31), index (41–499) and trailer
bytes 500–515.

SHA-256 of the whole 556-byte file, for fixture checking only:
`1939236c4b281cf517f7ca1b1746b93b75a0e6afb485107f56d1eea1a7e33332`.

### 18.3 Hex dump

```
00000000  43 48 53 54 0d 0a 1a 00 01 00 00 00 01 00 00 00  |CHST............|
00000010  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|
00000020  68 65 6c 6c 6f 0a 68 69 0a 01 00 00 80 40 00 00  |hello.hi.....@..|
00000030  00 02 00 00 00 00 00 00 00 58 91 b5 b5 22 d5 df  |.........X..."..|
00000040  08 6d 0f f0 b1 10 fb d9 d2 1b b4 fc 71 63 af 34  |.m..........qc.4|
00000050  d0 82 86 a2 e8 46 f6 be 03 20 00 00 00 00 00 00  |.....F... ......|
00000060  00 06 00 00 00 00 00 00 00 06 00 00 00 00 00 00  |................|
00000070  00 00 00 00 00 00 00 00 00 98 ea 6e 4f 21 6f 2f  |...........nO!o/|
00000080  b4 b6 9f ff 9b 3a 44 84 2c 38 68 6c a6 85 f3 f5  |.....:D.,8hl....|
00000090  5d c4 8c 5d 3f b1 10 7b e4 26 00 00 00 00 00 00  |]..]?..{.&......|
000000a0  00 03 00 00 00 00 00 00 00 03 00 00 00 00 00 00  |................|
000000b0  00 00 00 00 00 00 00 00 00 02 00 00 80 30 00 00  |.............0..|
000000c0  00 05 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|
000000d0  00 04 00 00 00 01 00 00 00 00 00 00 00 00 00 00  |................|
000000e0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|
000000f0  00 00 00 00 00 00 00 00 00 04 00 00 00 00 00 00  |................|
00000100  00 0a 00 00 00 02 00 00 00 58 91 b5 b5 22 d5 df  |.........X..."..|
00000110  08 6d 0f f0 b1 10 fb d9 d2 1b b4 fc 71 63 af 34  |.m..........qc.4|
00000120  d0 82 86 a2 e8 46 f6 be 03 0e 00 00 00 00 00 00  |.....F..........|
00000130  00 0a 00 00 00 02 00 00 00 58 91 b5 b5 22 d5 df  |.........X..."..|
00000140  08 6d 0f f0 b1 10 fb d9 d2 1b b4 fc 71 63 af 34  |.m..........qc.4|
00000150  d0 82 86 a2 e8 46 f6 be 03 18 00 00 00 00 00 00  |.....F..........|
00000160  00 0a 00 00 00 01 00 00 00 00 00 00 00 00 00 00  |................|
00000170  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|
00000180  00 00 00 00 00 00 00 00 00 22 00 00 00 00 00 00  |........."......|
00000190  00 09 00 00 00 02 00 00 00 98 ea 6e 4f 21 6f 2f  |...........nO!o/|
000001a0  b4 b6 9f ff 9b 3a 44 84 2c 38 68 6c a6 85 f3 f5  |.....:D.,8hl....|
000001b0  5d c4 8c 5d 3f b1 10 7b e4 03 00 00 80 01 00 00  |]..]?..{........|
000001c0  00 2b 00 00 00 00 00 00 00 64 6f 63 73 64 6f 63  |.+.......docsdoc|
000001d0  73 2f 61 2e 74 78 74 64 6f 63 73 2f 62 2e 74 78  |s/a.txtdocs/b.tx|
000001e0  74 64 6f 63 73 2f 65 6d 70 74 79 6e 6f 74 65 73  |tdocs/emptynotes|
000001f0  2e 74 78 74 29 00 00 00 00 00 00 00 cb 01 00 00  |.txt)...........|
00000200  00 00 00 00 13 e9 df cb 07 76 61 f8 dc c8 b7 6d  |.........va....m|
00000210  92 2f 47 bd 65 6c 28 2e 62 e7 46 e9 2d fb 9f 4c  |./G.el(.b.F.-..L|
00000220  16 e6 fb 9a 00 1a 0a 0d 54 53 48 43              |........TSHC|
```

### 18.4 Expected `list --json` (Appendix B)

```json
{
  "schema": "chst-report/1",
  "command": "list",
  "ok": true,
  "error": null,
  "warnings": [],
  "entries": [
    {"path": "docs",       "type": "dir"},
    {"path": "docs/a.txt", "type": "file", "size": 6, "stored_size": 6, "encoding": "stored",
     "blob": "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"},
    {"path": "docs/b.txt", "type": "file", "size": 6, "stored_size": 6, "encoding": "stored",
     "blob": "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"},
    {"path": "docs/empty", "type": "dir"},
    {"path": "notes.txt",  "type": "file", "size": 3, "stored_size": 3, "encoding": "stored",
     "blob": "98ea6e4f216f2fb4b69fff9b3a44842c38686ca685f3f55dc48c5d3fb1107be4"}
  ]
}
```

## Appendix A — Rule index

| Rule | Category | Detail code |
|---|---|---|
| **HDR-1** | not-a-container | `hdr.too-short` |
| **HDR-2** | not-a-container | `hdr.magic` |
| **HDR-3** | unsupported | `hdr.major-version` |
| **HDR-4** | unsupported | `hdr.hash-alg` |
| **HDR-5** | malformed | `hdr.reserved` |
| **HDR-6** | unsupported | `hdr.required-flag` |
| **TRL-1** | malformed | `trl.magic` |
| **TRL-2** | malformed | `trl.index-range` |
| **TRL-3** | integrity | `trl.hash` |
| **SEC-1** | malformed | `sec.bounds` |
| **SEC-2** | unsupported | `sec.unknown-critical` |
| **SEC-3** | malformed | `sec.layout` |
| **SEC-4** | malformed | `sec.record-size-min` |
| **SEC-5** | malformed | `sec.record-size` |
| **BLB-1** | malformed | `blob.reserved` |
| **BLB-2** | malformed | `blob.encoding` |
| **BLB-3** | malformed | `blob.raw-length` |
| **BLB-4** | malformed | `blob.layout` |
| **BLB-5** | malformed | `blob.duplicate-key` |
| **BLB-6** | integrity | `blob.hash` |
| **BLB-7** | malformed | `blob.unreferenced` |
| **ENT-1** | malformed | `entry.type` |
| **ENT-2** | malformed | `entry.reserved` |
| **ENT-3** | malformed | `entry.dir-key` |
| **ENT-4** | malformed | `entry.dangling-key` |
| **ENT-5** | malformed | `entry.path-range` |
| **ENT-6** | malformed | `entry.parent` |
| **PATH-1** | malformed | `path.utf8` |
| **PATH-2** | malformed | `path.nfc` |
| **PATH-3** | malformed | `path.length` |
| **PATH-4** | malformed | `path.slash` |
| **PATH-5** | malformed | `path.dot-segment` |
| **PATH-6** | malformed | `path.control-char` |
| **PATH-7** | malformed | `path.forbidden-char` |
| **PATH-8** | malformed | `path.trailing-dot-space` |
| **PATH-9** | malformed | `path.reserved-name` |
| **PATH-10** | malformed | `path.depth` |
| **PATH-11** | malformed | `path.case-collision` |
| **CAN-1** | malformed | `canon.entry-order` |
| **CAN-2** | malformed | `canon.blob-order` |
| **CAN-3** | malformed | `canon.path-pool` |
| **FLG-1** | malformed | `flag.mismatch` |
| **LIM-2** | malformed | `lim.index-size` |
| **LIM-3** | limit-exceeded | `limit.entries` |
| **LIM-4** | limit-exceeded | `limit.index-size` |
| **LIM-5** | limit-exceeded | `limit.total-size` |
| **LIM-6** | limit-exceeded | `limit.ratio` |
| **ZST-1** | integrity | `zstd.raw-length` |
| **ZST-2** | malformed | `zstd.frame` |
| **ZST-3** | malformed | `zstd.not-smaller` |
| **ATT-1** | malformed | `attrs.range` |
| **KV-1** | malformed | `kv.format` |
| **W-3** | refused | `pack.unportable-name` |
| **W-4** | refused | `pack.source-changed` |
| **W-5** | (warning) | `pack.skipped` |
| **W-6** | refused | `pack.output-in-source` |
| **W-7** | refused | `pack.output-exists` |
| **W-8** | (warning) | `pack.skipped`, or `pack.skipped-placeholder` for cloud-file placeholders |
| **W-10** | limit-exceeded | the LIM-3 … LIM-5 detail codes (`limit.entries`, `limit.index-size`, `limit.total-size`); `malformed` / `lim.index-size` for LIM-2 |
| **SEL-1** | refused | `extract.no-match` |
| **EXT-1** | refused | `extract.dest-exists` |
| **EXT-2** | refused | `extract.collision` |
| **EXT-7** | integrity | `blob.hash` |
| **EXT-8** | refused | `extract.unsafe-object` |
| **EXT-4** | refused | `extract.dest-exists` (at the final rename); `extract.collision` (staging name exists); `extract.unsafe-object` (staging can't be confirmed as the directory just created, or a staging identity mismatch); `io` / `extract.no-atomic-rename` |
| **W-1**, **W-2**, **W-9**, **EXT-3**, **EXT-5**, **EXT-6**, **EXT-9**, **EXT-10** | (requirement; no error of its own) | — |
| *(retired)* LIM-1 | — | — (§10.1) |

Reader rules are those with prefixes HDR, TRL, SEC, BLB, ENT, PATH, CAN, FLG, LIM, ZST,
ATT and KV. Each has a negative fixture (`ACCEPTANCE.md`, AC-NEG-1 and AC-X-NEG-1). W,
EXT and SEL rules are tested through CLI scenarios.

## Appendix B — Report schema `chst-report/1` (normative for reporting tools)

The schema is versioned independently of the container format (G9). Any incompatible
change to it requires `chst-report/2`.

Common fields of every `--json` report (stdout, a single JSON object):

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | `"chst-report/1"` |
| `command` | string | `"pack"`, `"list"`, `"verify"` or `"inspect"` |
| `ok` | bool | true iff exit code 0 |
| `error` | null or object | `{"category", "detail", "message"}` |
| `warnings` | array | `[{"detail", "message"}]` |

On failure, a report contains only the common fields.

Encoding conventions:
- Integers are JSON numbers when they lie within ±(2⁵³ − 1), and decimal strings otherwise.
  That applies to `summary.*_bytes` too, which can exceed 2⁵³ (F9).
- Hashes and keys are lowercase hex.
- Raw byte fields such as magic and reserved bytes are lowercase hex strings.
- Object key order is not significant. Array order is significant.
- `message` fields are free text and are excluded from conformance comparison.
- **What the reader implements shapes its report (F33):**
  - `name` is `"unknown"` for any section type the reader doesn't implement. A Core-only
    reader names KV_METADATA `unknown`.
  - Flag names in `summary.required_flags` and `summary.optional_flags` come from §12.1.
    Any set bit the reader doesn't implement is named `bit<N>`, where N is the bit number,
    for example `bit63`; a Core-only reader names `ENTRY_ATTRS` `bit0`.
  - Attribute fields (`mtime_seconds`, `mtime_nanos`, `mode`, and inspect's
    `attrs_reserved`) appear only if the reader implements `ENTRY_ATTRS`. Otherwise inspect
    shows those bytes as `extra`.

Command-specific fields:

- **list:** `entries`, in entry order.
  - Every entry has `{"path", "type": "dir" | "file"}`.
  - File entries add `size` (the `raw_length`), `stored_size`, `encoding`
    (`"stored"` | `"zstd"`) and `blob` (the key).
  - With `ENTRY_ATTRS`, every entry adds `mtime_seconds`, `mtime_nanos` and `mode`.
- **pack:** `output` (the output path as given on the command line), plus `summary` with
  the same fields as verify's, describing the container just written. Pack's `summary` also
  has `skipped`: the number of source objects skipped with a `pack.skipped*` warning (F46). Warnings such as
  `pack.skipped` carry a `path` field with the source-relative path (as UTF-8, with any
  undecodable bytes escaped as `\xHH`). When pack fails (for example,
  `pack.output-exists`), the report has only the common fields, as for any other failure.
- **verify:** `summary`:

  | Field | Meaning |
  |---|---|
  | `entries` | Number of entries |
  | `files` | Number of file entries |
  | `directories` | Number of directory entries |
  | `blobs` | Number of blobs |
  | `stored_bytes` | Sum of `stored_length` |
  | `raw_bytes` | Sum of blob `raw_length` |
  | `extracted_bytes` | Sum over file entries |
  | `required_flags` | Names of the required flags set |
  | `optional_flags` | Names of the optional flags set |

- **inspect:** adds `file_length` (integer), `header`, `data`, `sections` and `trailer`,
  defined in the table below.

  **Every byte of the file is covered by exactly one field.** Take the fields of `header`,
  `data`, `trailer`, every section, and every section's records, and sort them by
  `offset`: each field starts where the previous one ends, the first starts at 0, and the
  last ends at `file_length`.

  - **Field object:** `{"name", "offset", "length", "value"}`.
    - `offset` is absolute; `offset` and `length` are integers.
    - `value` depends on the field's kind:
      - **int:** the unsigned little-endian integer. `mtime_seconds` is the exception: it's
        signed.
      - **hex:** the raw bytes as lowercase hex.
      - **text:** a UTF-8 string.
    - Blob data fields have no `value`.
  - **Region object:** `{"offset", "length", "fields"}`.
  - **Order:** `fields` within an object are in ascending `offset` order. `sections` are in
    file order, and `records` in ascending `index` order.

  | Key | Contents |
  |---|---|
  | `header` | A region with `offset` 0 and `length` 32. Fields: `magic` (8, hex), `major_version` (2, int), `minor_version` (2, int), `hash_alg` (1, int), `reserved` (3, hex), `required_flags` (8, int), `optional_flags` (8, int). |
  | `data` | A region with `offset` 32 and `length` `index_offset − 32`. One field per blob record, in blob-table order, named `blob[i].data`, with that blob's `offset` and `stored_length` and no `value`. |
  | `sections[]` | One object per section, in file order. Keys: `type` (the type as an 8-digit lowercase hex string such as `"0x80000001"`), `name` (`BLOB_TABLE`, `ENTRY_TABLE`, `PATH_POOL`, `KV_METADATA`, or `"unknown"`), `offset` (of the section header), `length` (`16 + record_size × record_count`), `record_size`, `record_count`, `fields` and `records`. Its `fields` are the section header, `type` (4, int), `record_size` (4, int) and `record_count` (8, int), followed for sections without records by one `payload` field covering the whole payload. That field is omitted when the payload is empty. The payload's `value` is text for PATH_POOL and hex for KV_METADATA and unknown sections. |
  | BLOB_TABLE `records[]` | `{"index", "offset", "length" (= record_size), "fields"}`. Fields: `key` (32, hex), `offset` (8, int), `stored_length` (8, int), `raw_length` (8, int), `encoding` (1, int), `reserved` (7, hex). If `record_size` > 64, they're followed by `extra` (`record_size − 64`, hex). |
  | ENTRY_TABLE `records[]` | The same record shape. Fields: `path_offset` (8, int), `path_length` (4, int), `type` (1, int), `reserved` (3, hex), `blob_key` (32, hex). If `ENTRY_ATTRS` is set, the reader implements it, and `record_size` ≥ 64, they're followed by `mtime_seconds` (8, int, signed), `mtime_nanos` (4, int), `mode` (2, int) and `attrs_reserved` (2, hex), then `extra` (hex) for any bytes beyond 64. Otherwise, if `record_size` > 48, they're followed by `extra` (`record_size − 48`, hex). |
  | Other sections | `records` is `[]`. The payload appears as the `payload` field above. |
  | `trailer` | A region with `offset` `file_length − 56` and `length` 56. Fields: `index_offset` (8, int), `index_length` (8, int), `structure_hash` (32, hex), `trailer_magic` (8, hex). |

## Appendix C — Command-line interface (normative for the `chst` tool) [F45]

This appendix defines the CLI that ACCEPTANCE.md exercises. Other tools may expose the same
behaviour differently, but must keep the limits configurable (§10.2).

| Command | Synopsis |
|---|---|
| pack | `chst pack SRC -o OUT [--force] [--json] [limits]`; Extended adds `[--compress zstd] [--attrs] [--deterministic] [--mtime N] [--meta KEY=VALUE]… [--exclude PATTERN]…` |
| list | `chst list FILE [--json] [limits]` |
| verify | `chst verify FILE [--json] [limits]` |
| inspect | `chst inspect FILE [--json] [limits]` |
| extract | `chst extract FILE -C DEST [limits]`; Extended adds `[PATTERN]…` (§12.8) |

**Limit flags**, accepted by every command. Each takes a decimal integer from 0 to 2⁶⁴ − 1,
written in ASCII digits only: no sign, no whitespace, and no leading zeros, though a lone
`0` is allowed (M12). Any other value is `usage` / `usage.limit`. A limit of 0 means nothing of that kind is
allowed, for example `--max-entries 0` accepts only an empty container (N23).

| Flag | Sets | Default |
|---|---|---|
| `--max-entries N` | LIM-3 | 1,048,576 |
| `--max-index-bytes N` | LIM-4 | 268,435,456 |
| `--max-total-bytes N` | LIM-5 | 68,719,476,736 |
| `--max-ratio N` | LIM-6 | 1000 |

**Errors and exit codes.**
- The first line of stderr on failure is `chst: error[<category>/<detail>]: <message>`.
- Exit codes are those of §16.
- Usage errors use detail codes beginning `usage.`, for example `usage.pattern` (§12.8).

**Text output.** Without `--json`, `list` prints one entry per line.
- Before printing a path, it MUST escape every code point that PATH-6 allows but that isn't
  printable (F42): General_Category, per Unicode 16.0 (N15), Cc, Cf, Zl, Zp, Co, Cn or Zs
  other than U+0020. Each is
  written as `\u{X}`, with X in lowercase hex and no leading zeros.
- `\` itself is written as `\\`.
- So U+200B ZERO WIDTH SPACE appears as `\u{200b}`.
