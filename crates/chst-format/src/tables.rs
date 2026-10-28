//! The reader, §13 step 10: the blob table, the entry table, the paths and the canonical form
//! (the Core rules).
//!
//! Each item of step 10 is one pass, (a) to (p) in order, so only the first violation is
//! reported. Per-record items check every rule of one record before moving to the next.
//! Per-blob and per-entry state is allocated only after step 9 has checked the counts
//! against the index (SEC-1) and LIM-3, and every allocation is fallible (§10.3).

use std::cmp::Ordering;
use std::ops::Range;

use crate::error::{Category, Error, detail};
use crate::format::HEADER_LEN;
use crate::limits::Limits;
use crate::paths::{check_path, shown};
use crate::reader::Opened;
use crate::sections::{Sections, Table};

/// What the caller is going to do with the container. It decides whether LIM-5 applies:
/// verify and extract check it, list and inspect don't (§13 step 10 (p)).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Purpose {
    List,
    Inspect,
    Verify,
    Extract,
}

/// A blob record (§7).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Blob {
    pub key: [u8; 32],
    pub offset: u64,
    pub stored_length: u64,
    pub raw_length: u64,
    pub encoding: u8,
}

/// What an entry is (§8, §12.2).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EntryKind {
    Directory,
    /// A regular file, with the index of its blob in the blob table.
    File {
        blob: usize,
    },
}

/// An entry record (§8) that has passed step 10.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entry {
    pub kind: EntryKind,
    /// The path's byte range within the PATH_POOL payload.
    pub path: Range<usize>,
}

/// The blob and entry tables of a container that has passed steps 1 to 10.
#[derive(Debug)]
pub struct Tables {
    pub blobs: Vec<Blob>,
    /// In canonical order (CAN-1).
    pub entries: Vec<Entry>,
    /// The PATH_POOL payload, which is valid UTF-8 once every path has passed PATH-1.
    paths: String,
}

impl Tables {
    /// The path of `entry`, which must be one of this container's entries.
    pub fn path(&self, entry: &Entry) -> &str {
        self.paths.get(entry.path.clone()).unwrap_or_default()
    }
}

const TYPE_DIRECTORY: u8 = 1;
const TYPE_FILE: u8 = 2;

/// An entry record as stored.
struct RawEntry {
    path_offset: u64,
    path_length: u32,
    ty: u8,
    reserved: [u8; 3],
    blob_key: [u8; 32],
}

fn malformed(d: &'static str, message: String) -> Error {
    Error::new(Category::Malformed, d, message)
}

/// An empty vector with room for `len` items, or `io.memory`.
fn try_vec<T>(len: usize, what: &str) -> Result<Vec<T>, Error> {
    let mut v = Vec::new();
    v.try_reserve_exact(len).map_err(|_| {
        Error::new(
            Category::Io,
            detail::IO_MEMORY,
            format!("cannot allocate memory for {len} {what}"),
        )
    })?;
    Ok(v)
}

/// `M` bytes of `record` starting at `at`. The records are at least the base size (SEC-4), so
/// every field is inside; anything beyond would read as zero.
fn bytes<const M: usize>(record: &[u8], at: usize) -> [u8; M] {
    let mut out = [0u8; M];
    for (o, b) in out.iter_mut().zip(record.iter().skip(at)) {
        *o = *b;
    }
    out
}

/// The records of a table. Extra bytes in a record wider than the base size are ignored
/// (SEC-5).
fn records<'a>(index: &'a [u8], table: &Table) -> std::slice::ChunksExact<'a, u8> {
    let size = usize::try_from(table.record_size)
        .unwrap_or(usize::MAX)
        .max(1);
    index
        .get(table.payload.clone())
        .unwrap_or_default()
        .chunks_exact(size)
}

fn path_of<'a>(pool: &'a [u8], range: &Range<usize>) -> &'a [u8] {
    // ENT-5 has put every range inside the pool.
    pool.get(range.clone()).unwrap_or_default()
}

/// Compares two paths by their fold keys (PATH-11): ASCII `A`-`Z` read as `a`-`z`.
fn fold_cmp(a: &[u8], b: &[u8]) -> Ordering {
    a.iter()
        .map(u8::to_ascii_lowercase)
        .cmp(b.iter().map(u8::to_ascii_lowercase))
}

/// Runs step 10 of §13 over a container that has passed steps 1 to 9.
pub fn parse_tables(
    opened: &Opened,
    sections: &Sections,
    limits: &Limits,
    purpose: Purpose,
) -> Result<Tables, Error> {
    let index = opened.index.as_slice();
    let pool = index
        .get(sections.path_pool.payload.clone())
        .unwrap_or_default();

    let blob_records = records(index, &sections.blob_table);
    let mut blobs: Vec<Blob> = try_vec(blob_records.len(), "blob records")?;
    for (i, record) in blob_records.enumerate() {
        let blob = Blob {
            key: bytes(record, 0),
            offset: u64::from_le_bytes(bytes(record, 32)),
            stored_length: u64::from_le_bytes(bytes(record, 40)),
            raw_length: u64::from_le_bytes(bytes(record, 48)),
            encoding: record.get(56).copied().unwrap_or(0),
        };
        let reserved: [u8; 7] = bytes(record, 57);

        // (a) Per blob record: BLB-1, BLB-2, BLB-3. A Core reader doesn't implement ZSTD, so
        // BLB-2 rejects encoding 1, and ZST-2, ZST-3 and LIM-6 (encoding 1 only) never apply.
        if reserved != [0; 7] {
            return Err(malformed(
                detail::BLOB_RESERVED,
                format!("blob {i}: the reserved bytes are not zero"),
            ));
        }
        if blob.encoding != 0 {
            return Err(malformed(
                detail::BLOB_ENCODING,
                format!("blob {i}: encoding {} is not supported", blob.encoding),
            ));
        }
        if blob.stored_length != blob.raw_length {
            return Err(malformed(
                detail::BLOB_RAW_LENGTH,
                format!(
                    "blob {i}: stored blob of {} bytes has raw length {}",
                    blob.stored_length, blob.raw_length
                ),
            ));
        }
        blobs.push(blob);
    }

    // (b) BLB-4: the blobs tile the data region, in table order.
    let mut next = HEADER_LEN;
    for (i, blob) in blobs.iter().enumerate() {
        if blob.offset != next {
            return Err(malformed(
                detail::BLOB_LAYOUT,
                format!(
                    "blob {i} is at offset {}; it must be at {next}",
                    blob.offset
                ),
            ));
        }
        next = next.checked_add(blob.stored_length).ok_or_else(|| {
            malformed(
                detail::BLOB_LAYOUT,
                format!("blob {i} ends beyond the largest offset"),
            )
        })?;
    }
    if next != opened.trailer.index_offset {
        return Err(malformed(
            detail::BLOB_LAYOUT,
            format!(
                "the blobs end at offset {next}, but the index starts at {}",
                opened.trailer.index_offset
            ),
        ));
    }

    // (c) BLB-5. The blob indexes sorted by key also serve ENT-4's lookup.
    let mut by_key: Vec<usize> = try_vec(blobs.len(), "blob keys")?;
    by_key.extend(0..blobs.len());
    by_key.sort_unstable_by_key(|&i| (blobs.get(i).map(|b| b.key), i));
    for pair in by_key.windows(2) {
        if let [a, b] = *pair
            && blobs.get(a).map(|x| x.key) == blobs.get(b).map(|x| x.key)
        {
            return Err(malformed(
                detail::BLOB_DUPLICATE_KEY,
                format!("blobs {a} and {b} have the same key"),
            ));
        }
    }

    let entry_records = records(index, &sections.entry_table);
    let mut raw: Vec<RawEntry> = try_vec(entry_records.len(), "entry records")?;
    raw.extend(entry_records.map(|record| RawEntry {
        path_offset: u64::from_le_bytes(bytes(record, 0)),
        path_length: u32::from_le_bytes(bytes(record, 8)),
        ty: record.get(12).copied().unwrap_or(0),
        reserved: bytes(record, 13),
        blob_key: bytes(record, 16),
    }));

    // (d) Per entry: ENT-1, ENT-2, ENT-3, ENT-4.
    let mut kinds: Vec<EntryKind> = try_vec(raw.len(), "entries")?;
    for (i, e) in raw.iter().enumerate() {
        if e.ty != TYPE_DIRECTORY && e.ty != TYPE_FILE {
            return Err(malformed(
                detail::ENTRY_TYPE,
                format!("entry {i}: type {} is not defined", e.ty),
            ));
        }
        if e.reserved != [0; 3] {
            return Err(malformed(
                detail::ENTRY_RESERVED,
                format!("entry {i}: the reserved bytes are not zero"),
            ));
        }
        if e.ty == TYPE_DIRECTORY {
            if e.blob_key != [0; 32] {
                return Err(malformed(
                    detail::ENTRY_DIR_KEY,
                    format!("entry {i} is a directory with a blob key"),
                ));
            }
            kinds.push(EntryKind::Directory);
            continue;
        }
        let found = by_key
            .binary_search_by(|&b| {
                blobs
                    .get(b)
                    .map_or(Ordering::Less, |blob| blob.key.cmp(&e.blob_key))
            })
            .ok()
            .and_then(|at| by_key.get(at).copied());
        let Some(blob) = found else {
            return Err(malformed(
                detail::ENTRY_DANGLING_KEY,
                format!("entry {i}: no blob has its key"),
            ));
        };
        kinds.push(EntryKind::File { blob });
    }

    // (e) Per entry: ENT-5.
    let mut ranges: Vec<Range<usize>> = try_vec(raw.len(), "paths")?;
    for (i, e) in raw.iter().enumerate() {
        let range = usize::try_from(e.path_offset)
            .ok()
            .and_then(|start| {
                let end = start.checked_add(usize::try_from(e.path_length).ok()?)?;
                Some(start..end)
            })
            .filter(|r| r.end <= pool.len())
            .ok_or_else(|| {
                malformed(
                    detail::ENTRY_PATH_RANGE,
                    format!(
                        "entry {i}: the path ({} bytes at {}) is not inside the path pool of {} bytes",
                        e.path_length,
                        e.path_offset,
                        pool.len()
                    ),
                )
            })?;
        ranges.push(range);
    }

    // (f) CAN-3: the paths are packed into the pool in entry order, and fill it.
    let mut packed = 0usize;
    for (i, range) in ranges.iter().enumerate() {
        if range.start != packed {
            return Err(malformed(
                detail::CANON_PATH_POOL,
                format!(
                    "entry {i}: its path is at {}; packed in entry order it would be at {packed}",
                    range.start
                ),
            ));
        }
        packed = range.end;
    }
    if packed != pool.len() {
        return Err(malformed(
            detail::CANON_PATH_POOL,
            format!(
                "the paths fill {packed} bytes of the {}-byte path pool",
                pool.len()
            ),
        ));
    }

    // (g) Per entry: PATH-1 ... PATH-10. The paths then make up the pool (CAN-3), and they
    // are copied into one string.
    let mut paths = String::new();
    paths.try_reserve_exact(pool.len()).map_err(|_| {
        Error::new(
            Category::Io,
            detail::IO_MEMORY,
            format!(
                "cannot allocate {} bytes of memory for the paths",
                pool.len()
            ),
        )
    })?;
    for (i, range) in ranges.iter().enumerate() {
        paths.push_str(check_path(i, path_of(pool, range))?);
    }

    // (h) CAN-1: strictly ascending bytewise order.
    for (i, pair) in ranges.windows(2).enumerate() {
        if let [a, b] = pair
            && path_of(pool, a) >= path_of(pool, b)
        {
            return Err(malformed(
                detail::CANON_ENTRY_ORDER,
                format!(
                    "entry {}, \"{}\", does not sort after entry {i}, \"{}\"",
                    i + 1,
                    shown(path_of(pool, b)),
                    shown(path_of(pool, a))
                ),
            ));
        }
    }

    // (i) Per entry: ENT-6. The entries are sorted (CAN-1), so the parent is found by search.
    for (i, range) in ranges.iter().enumerate() {
        let path = path_of(pool, range);
        let Some(slash) = path.iter().rposition(|&b| b == b'/') else {
            continue;
        };
        let parent = path.get(..slash).unwrap_or_default();
        let is_dir = ranges
            .binary_search_by(|r| path_of(pool, r).cmp(parent))
            .ok()
            .and_then(|at| kinds.get(at))
            == Some(&EntryKind::Directory);
        if !is_dir {
            return Err(malformed(
                detail::ENTRY_PARENT,
                format!(
                    "entry {i}, \"{}\": its parent \"{}\" is not a directory entry",
                    shown(path),
                    shown(parent)
                ),
            ));
        }
    }

    // (j) PATH-11: no two fold keys are equal.
    let mut by_fold: Vec<usize> = try_vec(ranges.len(), "fold keys")?;
    by_fold.extend(0..ranges.len());
    let fold_path = |i: usize| ranges.get(i).map_or(&[][..], |r| path_of(pool, r));
    by_fold.sort_unstable_by(|&a, &b| fold_cmp(fold_path(a), fold_path(b)).then(a.cmp(&b)));
    for pair in by_fold.windows(2) {
        if let [a, b] = *pair
            && fold_cmp(fold_path(a), fold_path(b)) == Ordering::Equal
        {
            return Err(malformed(
                detail::PATH_CASE_COLLISION,
                format!(
                    "entries {a} and {b}, \"{}\" and \"{}\", differ only in ASCII case",
                    shown(fold_path(a)),
                    shown(fold_path(b))
                ),
            ));
        }
    }

    // (k) BLB-7: every blob is referenced by a file entry.
    let mut referenced: Vec<bool> = try_vec(blobs.len(), "blob flags")?;
    referenced.resize(blobs.len(), false);
    for kind in &kinds {
        if let EntryKind::File { blob } = kind
            && let Some(r) = referenced.get_mut(*blob)
        {
            *r = true;
        }
    }
    if let Some(i) = referenced.iter().position(|r| !r) {
        return Err(malformed(
            detail::BLOB_UNREFERENCED,
            format!("blob {i} is referenced by no file entry"),
        ));
    }

    // (l) CAN-2: the blobs are in order of first reference. Keys are unique (BLB-5), so a
    // blob's index stands for its key, and the blobs referenced so far are exactly 0 .. seen.
    let mut seen = 0usize;
    for (i, kind) in kinds.iter().enumerate() {
        if let EntryKind::File { blob } = *kind {
            if blob > seen {
                return Err(malformed(
                    detail::CANON_BLOB_ORDER,
                    format!(
                        "entry {i} is the first to reference blob {blob}, but blob {seen} is not referenced yet"
                    ),
                ));
            }
            if blob == seen {
                seen += 1;
            }
        }
    }

    // (m) FLG-1, (n) ATT-1 and (o) KV-1 apply only to flags the reader knows, and a Core
    // reader knows none (KNOWN_REQUIRED_FLAGS and KNOWN_OPTIONAL_FLAGS are 0).

    // (p) LIM-5, for verify and extract: the raw length of every file entry's blob, counted
    // once per entry. A sum of 2^64 or more exceeds every limit.
    if matches!(purpose, Purpose::Verify | Purpose::Extract) {
        let total = kinds.iter().try_fold(0u64, |sum, kind| match kind {
            EntryKind::File { blob } => {
                sum.checked_add(blobs.get(*blob).map_or(0, |b| b.raw_length))
            }
            EntryKind::Directory => Some(sum),
        });
        if total.is_none_or(|t| t > limits.max_total_bytes) {
            return Err(Error::new(
                Category::LimitExceeded,
                detail::LIMIT_TOTAL_SIZE,
                format!(
                    "the files hold {} bytes in all; the limit is {}",
                    total.map_or_else(|| "2^64 or more".to_owned(), |t| t.to_string()),
                    limits.max_total_bytes
                ),
            ));
        }
    }

    let mut entries: Vec<Entry> = try_vec(kinds.len(), "entries")?;
    entries.extend(
        kinds
            .into_iter()
            .zip(ranges)
            .map(|(kind, path)| Entry { kind, path }),
    );
    Ok(Tables {
        blobs,
        entries,
        paths,
    })
}

#[cfg(test)]
mod tests {
    use sha2::{Digest, Sha256};

    use super::*;
    use crate::format::{
        Header, MAGIC, SECTION_BLOB_TABLE, SECTION_ENTRY_TABLE, SECTION_PATH_POOL, TRAILER_MAGIC,
        Trailer,
    };
    use crate::sections::parse_sections;

    struct B {
        key: [u8; 32],
        offset: u64,
        stored: u64,
        raw: u64,
        encoding: u8,
        reserved: [u8; 7],
    }

    struct E {
        offset: u64,
        length: u32,
        ty: u8,
        reserved: [u8; 3],
        key: [u8; 32],
    }

    /// A container as step 10 sees it. Blob data is never read in step 10, so only its
    /// declared lengths matter.
    struct C {
        blobs: Vec<B>,
        entries: Vec<E>,
        pool: Vec<u8>,
        index_offset: u64,
        /// Record sizes, and the header's optional flags (SEC-5 lets an unknown flag widen
        /// the records).
        blob_record_size: u32,
        entry_record_size: u32,
        optional_flags: u64,
    }

    fn key(content: &[u8]) -> [u8; 32] {
        Sha256::digest(content).into()
    }

    /// The canonical container of `tree`: (path, None) for a directory, (path, Some(content))
    /// for a file. The tree must be given in canonical order.
    fn canonical(tree: &[(&str, Option<&str>)]) -> C {
        let mut c = C {
            blobs: Vec::new(),
            entries: Vec::new(),
            pool: Vec::new(),
            index_offset: 32,
            blob_record_size: 64,
            entry_record_size: 48,
            optional_flags: 0,
        };
        for (path, content) in tree {
            let k = match content {
                None => [0; 32],
                Some(text) => {
                    let k = key(text.as_bytes());
                    if !c.blobs.iter().any(|b| b.key == k) {
                        let len = text.len() as u64;
                        c.blobs.push(B {
                            key: k,
                            offset: c.index_offset,
                            stored: len,
                            raw: len,
                            encoding: 0,
                            reserved: [0; 7],
                        });
                        c.index_offset += len;
                    }
                    k
                }
            };
            c.entries.push(E {
                offset: c.pool.len() as u64,
                length: path.len() as u32,
                ty: if content.is_some() { 2 } else { 1 },
                reserved: [0; 3],
                key: k,
            });
            c.pool.extend_from_slice(path.as_bytes());
        }
        c
    }

    fn worked_example() -> C {
        canonical(&[
            ("docs", None),
            ("docs/a.txt", Some("hello\n")),
            ("docs/b.txt", Some("hello\n")),
            ("docs/empty", None),
            ("notes.txt", Some("hi\n")),
        ])
    }

    fn section(ty: u32, record_size: u32, count: usize, payload: &[u8]) -> Vec<u8> {
        let mut s = Vec::new();
        s.extend_from_slice(&ty.to_le_bytes());
        s.extend_from_slice(&record_size.to_le_bytes());
        s.extend_from_slice(&(count as u64).to_le_bytes());
        s.extend_from_slice(payload);
        s
    }

    fn run(c: &C, limits: &Limits, purpose: Purpose) -> Result<Tables, Error> {
        let mut blobs = Vec::new();
        for b in &c.blobs {
            blobs.extend_from_slice(&b.key);
            blobs.extend_from_slice(&b.offset.to_le_bytes());
            blobs.extend_from_slice(&b.stored.to_le_bytes());
            blobs.extend_from_slice(&b.raw.to_le_bytes());
            blobs.push(b.encoding);
            blobs.extend_from_slice(&b.reserved);
            // Bytes beyond the base size are filled, to show they are ignored.
            blobs.resize(blobs.len() + c.blob_record_size as usize - 64, 0xEE);
        }
        let mut entries = Vec::new();
        for e in &c.entries {
            entries.extend_from_slice(&e.offset.to_le_bytes());
            entries.extend_from_slice(&e.length.to_le_bytes());
            entries.push(e.ty);
            entries.extend_from_slice(&e.reserved);
            entries.extend_from_slice(&e.key);
            entries.resize(entries.len() + c.entry_record_size as usize - 48, 0xEE);
        }
        let index = [
            section(
                SECTION_BLOB_TABLE,
                c.blob_record_size,
                c.blobs.len(),
                &blobs,
            ),
            section(
                SECTION_ENTRY_TABLE,
                c.entry_record_size,
                c.entries.len(),
                &entries,
            ),
            section(SECTION_PATH_POOL, 1, c.pool.len(), &c.pool),
        ]
        .concat();
        let header = Header {
            magic: MAGIC,
            major_version: 1,
            minor_version: 0,
            hash_alg: 1,
            reserved: [0; 3],
            required_flags: 0,
            optional_flags: c.optional_flags,
        };
        let index_length = index.len() as u64;
        let opened = Opened {
            file_length: c.index_offset + index_length + 56,
            header,
            trailer: Trailer {
                index_offset: c.index_offset,
                index_length,
                structure_hash: [0; 32],
                trailer_magic: TRAILER_MAGIC,
            },
            index,
        };
        let sections = parse_sections(&opened.index, &opened.header, limits).unwrap();
        parse_tables(&opened, &sections, limits, purpose)
    }

    fn ok(c: &C) -> Tables {
        run(c, &Limits::default(), Purpose::Verify).unwrap()
    }

    fn fails(c: &C, d: &str) {
        let e = run(c, &Limits::default(), Purpose::Verify).unwrap_err();
        assert_eq!(e.detail(), d, "{e}");
        let category = if d == detail::LIMIT_TOTAL_SIZE {
            Category::LimitExceeded
        } else {
            Category::Malformed
        };
        assert_eq!(e.category(), category, "{e}");
    }

    #[test]
    fn the_worked_example_passes_with_its_tables() {
        let t = ok(&worked_example());
        assert_eq!(t.blobs.len(), 2);
        assert_eq!(
            (
                t.blobs[0].offset,
                t.blobs[0].stored_length,
                t.blobs[1].offset
            ),
            (32, 6, 38)
        );
        let listed: Vec<(&str, EntryKind)> =
            t.entries.iter().map(|e| (t.path(e), e.kind)).collect();
        assert_eq!(
            listed,
            [
                ("docs", EntryKind::Directory),
                ("docs/a.txt", EntryKind::File { blob: 0 }),
                ("docs/b.txt", EntryKind::File { blob: 0 }),
                ("docs/empty", EntryKind::Directory),
                ("notes.txt", EntryKind::File { blob: 1 }),
            ]
        );
    }

    #[test]
    fn an_empty_container_and_an_empty_file_pass() {
        let t = ok(&canonical(&[]));
        assert!(t.blobs.is_empty() && t.entries.is_empty());
        let t = ok(&canonical(&[("e", Some("")), ("f", Some(""))]));
        assert_eq!(t.blobs.len(), 1);
        assert_eq!(t.blobs[0].key, key(b""));
    }

    #[test]
    fn blob_rules_run_per_record_in_order() {
        // Within one record: BLB-1, then BLB-2, then BLB-3.
        let mut c = worked_example();
        c.blobs[0].reserved[6] = 1;
        c.blobs[0].encoding = 1;
        c.blobs[0].raw = 7;
        fails(&c, detail::BLOB_RESERVED);
        c.blobs[0].reserved[6] = 0;
        fails(&c, detail::BLOB_ENCODING);
        c.blobs[0].encoding = 0;
        fails(&c, detail::BLOB_RAW_LENGTH);
        // Record 0's BLB-3 comes before record 1's BLB-1.
        c.blobs[1].reserved[0] = 1;
        fails(&c, detail::BLOB_RAW_LENGTH);
        // Every encoding but 0 is unknown to a Core reader.
        let mut c = worked_example();
        for encoding in [1, 2, 255] {
            c.blobs[1].encoding = encoding;
            fails(&c, detail::BLOB_ENCODING);
        }
    }

    #[test]
    fn blb_4_tiles_the_data_region_without_overflow() {
        let mut c = worked_example();
        c.blobs[0].offset = 31;
        // (a) comes before (b), even for a later record.
        c.blobs[1].reserved[0] = 1;
        fails(&c, detail::BLOB_RESERVED);
        c.blobs[1].reserved[0] = 0;
        fails(&c, detail::BLOB_LAYOUT);
        let mut c = worked_example();
        c.index_offset += 1;
        fails(&c, detail::BLOB_LAYOUT);
        let mut c = canonical(&[]);
        c.index_offset = 33;
        fails(&c, detail::BLOB_LAYOUT);
        // A length that wraps the running offset to the next blob's offset.
        let mut c = worked_example();
        c.blobs[0].stored = u64::MAX - 25;
        c.blobs[0].raw = u64::MAX - 25;
        c.blobs[1].offset = 6;
        fails(&c, detail::BLOB_LAYOUT);
        // A length that wraps the running offset round to a tiling that would otherwise fit:
        // 32 + (2^64 - 26) wraps to 6, and blob 1 at 6 with 35 bytes ends at the index, 41.
        let mut c = canonical(&[("a", Some("x")), ("b", Some("y"))]);
        c.blobs[0].stored = u64::MAX - 25;
        c.blobs[0].raw = u64::MAX - 25;
        c.blobs[1].offset = 6;
        c.blobs[1].stored = 35;
        c.blobs[1].raw = 35;
        c.index_offset = 41;
        let e = run(&c, &Limits::default(), Purpose::List).unwrap_err();
        assert_eq!(e.detail(), detail::BLOB_LAYOUT, "{e}");
        // Huge blobs that tile exactly are fine: their data is never read in step 10. (List,
        // so LIM-5 doesn't apply.)
        let mut c = canonical(&[("a", Some("x")), ("b", Some("y"))]);
        c.blobs[0].stored = 1 << 62;
        c.blobs[0].raw = 1 << 62;
        c.blobs[1].offset = 32 + (1 << 62);
        c.index_offset = 32 + (1 << 62) + 1;
        run(&c, &Limits::default(), Purpose::List).unwrap();
    }

    #[test]
    fn blb_5_rejects_a_repeated_key_before_the_entries() {
        // BLB-4 comes before BLB-5.
        let mut c = worked_example();
        c.blobs[1].key = c.blobs[0].key;
        c.index_offset += 1;
        fails(&c, detail::BLOB_LAYOUT);
        let mut c = worked_example();
        c.blobs[1].key = c.blobs[0].key;
        c.entries[0].ty = 9;
        fails(&c, detail::BLOB_DUPLICATE_KEY);
        // Equal keys anywhere in the table, not only next to each other.
        let mut c = canonical(&[("a", Some("1")), ("b", Some("2")), ("c", Some("3"))]);
        c.blobs[2].key = c.blobs[0].key;
        fails(&c, detail::BLOB_DUPLICATE_KEY);
    }

    #[test]
    fn entry_rules_run_per_record_in_order() {
        let mut c = worked_example();
        c.entries[1].ty = 3;
        c.entries[1].reserved[2] = 1;
        fails(&c, detail::ENTRY_TYPE);
        c.entries[1].ty = 2;
        fails(&c, detail::ENTRY_RESERVED);
        c.entries[1].reserved[2] = 0;
        // A directory with a key, then a file with a key no blob has.
        c.entries[0].key = c.blobs[0].key;
        c.entries[4].key = key(b"missing");
        fails(&c, detail::ENTRY_DIR_KEY);
        c.entries[0].key = [0; 32];
        fails(&c, detail::ENTRY_DANGLING_KEY);
        // A file with the zero key has no blob either.
        c.entries[4].key = [0; 32];
        fails(&c, detail::ENTRY_DANGLING_KEY);
        // Record 1's ENT-4 comes before record 2's ENT-1.
        let mut c = worked_example();
        c.entries[1].key = key(b"missing");
        c.entries[2].ty = 0;
        fails(&c, detail::ENTRY_DANGLING_KEY);
        // The (d) rules come before ENT-5.
        let mut c = worked_example();
        c.entries[0].offset = u64::MAX;
        c.entries[4].ty = 0;
        fails(&c, detail::ENTRY_TYPE);
    }

    #[test]
    fn every_key_is_found_whatever_its_place_in_the_table() {
        // Keys in table order are not sorted; each file must still find its blob.
        let tree: Vec<(String, String)> = (0..40)
            .map(|i| (format!("f{i:02}"), format!("content {i}")))
            .collect();
        let tree: Vec<(&str, Option<&str>)> = tree
            .iter()
            .map(|(p, x)| (p.as_str(), Some(x.as_str())))
            .collect();
        let t = ok(&canonical(&tree));
        for (i, e) in t.entries.iter().enumerate() {
            assert_eq!(e.kind, EntryKind::File { blob: i });
        }
    }

    #[test]
    fn ent_5_checks_the_range_without_overflow_before_can_3() {
        let mut c = worked_example();
        c.entries[1].offset = u64::MAX;
        fails(&c, detail::ENTRY_PATH_RANGE);
        c.entries[1].offset = u64::MAX - 5;
        fails(&c, detail::ENTRY_PATH_RANGE);
        let mut c = worked_example();
        c.entries[4].length = u32::MAX;
        fails(&c, detail::ENTRY_PATH_RANGE);
        // The last path ending exactly at the end of the pool is inside it.
        let mut c = worked_example();
        c.entries[4].length += 1;
        fails(&c, detail::ENTRY_PATH_RANGE);
        // ENT-5 for a later entry comes before CAN-3 for an earlier one.
        let mut c = worked_example();
        c.entries[1].offset = 5;
        c.entries[3].length = 100;
        fails(&c, detail::ENTRY_PATH_RANGE);
        c.entries[3].length = 10;
        fails(&c, detail::CANON_PATH_POOL);
    }

    #[test]
    fn can_3_packs_the_pool_in_entry_order_and_fills_it() {
        // A gap, an overlap, and unused bytes at the end.
        let mut c = worked_example();
        c.entries[1].offset += 1;
        fails(&c, detail::CANON_PATH_POOL);
        let mut c = worked_example();
        c.entries[1].offset -= 1;
        fails(&c, detail::CANON_PATH_POOL);
        let mut c = worked_example();
        c.pool.push(b'x');
        fails(&c, detail::CANON_PATH_POOL);
        // Paths that share pool bytes: 'ab' and 'bc' in the 3-byte pool 'abc'. They end
        // exactly at the end of the pool, so only the offset check finds the overlap.
        let mut c = canonical(&[("ab", None), ("bc", None)]);
        c.pool = b"abc".to_vec();
        c.entries[1].offset = 1;
        fails(&c, detail::CANON_PATH_POOL);
        // A gap: 'a' and 'c' in the pool 'axc', the unused byte between them.
        let mut c = canonical(&[("a", None), ("c", None)]);
        c.pool = b"axc".to_vec();
        c.entries[1].offset = 2;
        fails(&c, detail::CANON_PATH_POOL);
        // CAN-3 comes before the path rules.
        let mut c = worked_example();
        c.pool[0] = 0xff;
        c.entries[1].offset += 1;
        fails(&c, detail::CANON_PATH_POOL);
        c.entries[1].offset -= 1;
        fails(&c, detail::PATH_UTF8);
    }

    #[test]
    fn the_path_rules_run_per_entry_before_can_1() {
        // Entry 1 breaks PATH-9, entry 3 PATH-6; and the order breaks CAN-1.
        let mut c = canonical(&[
            ("z", None),
            ("z/con", None),
            ("z/b", None),
            ("z/\u{1}", None),
        ]);
        fails(&c, detail::PATH_RESERVED_NAME);
        c.pool[3] = b'x';
        fails(&c, detail::PATH_CONTROL_CHAR);
        let last = c.pool.len() - 1;
        c.pool[last] = b'y';
        fails(&c, detail::CANON_ENTRY_ORDER);
    }

    #[test]
    fn can_1_requires_strictly_ascending_bytes() {
        fails(
            &canonical(&[("b", None), ("a", None)]),
            detail::CANON_ENTRY_ORDER,
        );
        fails(
            &canonical(&[("a", None), ("a", None)]),
            detail::CANON_ENTRY_ORDER,
        );
        fails(
            &canonical(&[("ab", None), ("a", None)]),
            detail::CANON_ENTRY_ORDER,
        );
        // Unsigned bytes: 'é' (0xC3 0xA9) sorts after 'z'.
        ok(&canonical(&[("a", None), ("z", None), ("\u{e9}", None)]));
        fails(
            &canonical(&[("\u{e9}", None), ("z", None)]),
            detail::CANON_ENTRY_ORDER,
        );
        // A parent sorts before its children, and '-' (0x2D) before '/' (0x2F).
        ok(&canonical(&[("a", None), ("a-b", None), ("a/b", None)]));
        // CAN-1 comes before ENT-6: 'a/b' before 'a' breaks CAN-1, and 'b' then 'a/x', with
        // no 'a', breaks both.
        fails(
            &canonical(&[("b", None), ("a/x", None)]),
            detail::CANON_ENTRY_ORDER,
        );
        fails(
            &canonical(&[("a/b", None), ("a", None)]),
            detail::CANON_ENTRY_ORDER,
        );
    }

    #[test]
    fn ent_6_needs_every_parent_as_a_directory() {
        fails(&canonical(&[("a/b", None)]), detail::ENTRY_PARENT);
        fails(
            &canonical(&[("a", Some("x")), ("a/b", None)]),
            detail::ENTRY_PARENT,
        );
        // Only the immediate parent is looked up; every level must exist.
        fails(
            &canonical(&[("a", None), ("a/b/c", None)]),
            detail::ENTRY_PARENT,
        );
        // A parent found in the middle of a longer sorted run.
        ok(&canonical(&[
            ("a", None),
            ("a/b", None),
            ("a/b/c", Some("1")),
            ("a/b/d", None),
            ("a/b/d/e", Some("2")),
            ("a/c", None),
            ("b", None),
            ("b/x", Some("3")),
        ]));
        // ENT-6 comes before PATH-11.
        let c = canonical(&[("A", None), ("a", None), ("q/r", None)]);
        fails(&c, detail::ENTRY_PARENT);
    }

    #[test]
    fn path_11_compares_ascii_fold_keys_only() {
        fails(
            &canonical(&[("A", None), ("a", None)]),
            detail::PATH_CASE_COLLISION,
        );
        // Not next to each other in canonical order.
        fails(
            &canonical(&[("B", None), ("a", None), ("b", None)]),
            detail::PATH_CASE_COLLISION,
        );
        fails(
            &canonical(&[("D", None), ("D/X", None), ("d", None), ("d/x", None)]),
            detail::PATH_CASE_COLLISION,
        );
        // Non-ASCII case isn't folded: 'É' and 'é' may coexist (EXT-2 catches them).
        ok(&canonical(&[("\u{c9}", None), ("\u{e9}", None)]));
        // Same length but different letters, and prefixes, don't collide.
        ok(&canonical(&[("AB", None), ("a", None), ("ac", None)]));
        // PATH-11 comes before BLB-7.
        let mut c = canonical(&[("A", None), ("a", None), ("f", Some("x"))]);
        orphan(&mut c, "orphan");
        fails(&c, detail::PATH_CASE_COLLISION);
    }

    fn orphan(c: &mut C, content: &str) {
        c.blobs.push(B {
            key: key(content.as_bytes()),
            offset: c.index_offset,
            stored: content.len() as u64,
            raw: content.len() as u64,
            encoding: 0,
            reserved: [0; 7],
        });
        c.index_offset += content.len() as u64;
    }

    #[test]
    fn blb_7_needs_every_blob_referenced_before_can_2() {
        let mut c = worked_example();
        orphan(&mut c, "orphan\n");
        fails(&c, detail::BLOB_UNREFERENCED);
        // Referenced only by a directory doesn't count: that is ENT-3 first.
        let mut c = canonical(&[]);
        orphan(&mut c, "x");
        fails(&c, detail::BLOB_UNREFERENCED);
        // An unreferenced first blob and blobs out of order: BLB-7 is reported.
        let mut c = canonical(&[("a", Some("2"))]);
        c.blobs[0].offset += 1;
        c.blobs.insert(
            0,
            B {
                key: key(b"1"),
                offset: 32,
                stored: 1,
                raw: 1,
                encoding: 0,
                reserved: [0; 7],
            },
        );
        c.index_offset += 1;
        fails(&c, detail::BLOB_UNREFERENCED);
    }

    #[test]
    fn can_2_orders_blobs_by_first_reference() {
        let mut c = worked_example();
        c.blobs.swap(0, 1);
        c.blobs[0].offset = 32;
        c.blobs[1].offset = 35;
        fails(&c, detail::CANON_BLOB_ORDER);
        // Repeated references to earlier blobs, in any order, are fine.
        ok(&canonical(&[
            ("a", Some("1")),
            ("b", Some("2")),
            ("c", Some("1")),
            ("d", Some("3")),
            ("e", Some("2")),
            ("f", Some("1")),
        ]));
        // The third blob referenced before the second.
        let mut c = canonical(&[("a", Some("1")), ("b", Some("2")), ("c", Some("3"))]);
        c.entries[1].key = c.blobs[2].key;
        c.entries[2].key = c.blobs[1].key;
        fails(&c, detail::CANON_BLOB_ORDER);
        // A repeated reference doesn't count as a new blob: here the second distinct blob
        // referenced is blob 2.
        let mut r = canonical(&[
            ("a", Some("1")),
            ("b", Some("1")),
            ("c", Some("2")),
            ("d", Some("3")),
        ]);
        r.entries[2].key = r.blobs[2].key;
        r.entries[3].key = r.blobs[1].key;
        fails(&r, detail::CANON_BLOB_ORDER);
        // CAN-2 comes before LIM-5.
        let limits = Limits {
            max_total_bytes: 0,
            ..Limits::default()
        };
        let e = run(&c, &limits, Purpose::Verify).unwrap_err();
        assert_eq!(e.detail(), detail::CANON_BLOB_ORDER);
    }

    #[test]
    fn lim_5_counts_every_reference_for_verify_and_extract_only() {
        // The worked example has 15 logical bytes: 6 + 6 + 3.
        let c = worked_example();
        let limits = |n| Limits {
            max_total_bytes: n,
            ..Limits::default()
        };
        for purpose in [Purpose::Verify, Purpose::Extract] {
            let e = run(&c, &limits(14), purpose).unwrap_err();
            assert_eq!(
                (e.category(), e.detail()),
                (Category::LimitExceeded, detail::LIMIT_TOTAL_SIZE),
                "{e}"
            );
            run(&c, &limits(15), purpose).unwrap();
        }
        for purpose in [Purpose::List, Purpose::Inspect] {
            run(&c, &limits(0), purpose).unwrap();
        }
        // Two references to a blob of 2^63 bytes sum to 2^64, which exceeds every limit.
        let mut c = canonical(&[("a", Some("x")), ("b", Some("x"))]);
        c.blobs[0].stored = 1 << 63;
        c.blobs[0].raw = 1 << 63;
        c.index_offset = 32 + (1 << 63);
        let e = run(&c, &limits(u64::MAX), Purpose::Verify).unwrap_err();
        assert_eq!(e.detail(), detail::LIMIT_TOTAL_SIZE, "{e}");
        run(&c, &limits(u64::MAX), Purpose::List).unwrap();
        // One reference fits under u64::MAX.
        let mut c = canonical(&[("a", Some("x"))]);
        c.blobs[0].stored = u64::MAX - 32;
        c.blobs[0].raw = u64::MAX - 32;
        c.index_offset = u64::MAX;
        run(&c, &limits(u64::MAX - 32), Purpose::Verify).unwrap();
        let e = run(&c, &limits(u64::MAX - 33), Purpose::Verify).unwrap_err();
        assert_eq!(e.detail(), detail::LIMIT_TOTAL_SIZE, "{e}");
    }

    #[test]
    fn wider_records_are_read_at_their_size_when_a_flag_is_unknown() {
        let mut c = worked_example();
        c.blob_record_size = 72;
        c.entry_record_size = 64;
        c.optional_flags = 1 << 63;
        let t = ok(&c);
        assert_eq!(t.blobs[1].offset, 38);
        assert_eq!(t.blobs[1].key, key(b"hi\n"));
        let listed: Vec<(&str, EntryKind)> =
            t.entries.iter().map(|e| (t.path(e), e.kind)).collect();
        assert_eq!(
            listed,
            [
                ("docs", EntryKind::Directory),
                ("docs/a.txt", EntryKind::File { blob: 0 }),
                ("docs/b.txt", EntryKind::File { blob: 0 }),
                ("docs/empty", EntryKind::Directory),
                ("notes.txt", EntryKind::File { blob: 1 }),
            ]
        );
    }
}
