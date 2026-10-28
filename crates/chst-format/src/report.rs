//! List, inspect and verify reports as library values (FORMAT_SPEC Appendix B,
//! `chst-report/1`). The CLI renders them as text or JSON (DESIGN D13).
//!
//! List and inspect run §13 steps 1 to 10, and never step 11 (F34). Verify runs all eleven.
//! What the reader implements shapes the report (F33): flags and section types this reader
//! doesn't implement are named `bit<N>` and `unknown`.

use std::borrow::Cow;
use std::io::{Read, Seek};

use crate::blobs::check_blobs;
use crate::error::{Category, Error, detail};
use crate::format::{
    HEADER_LEN, KNOWN_OPTIONAL_FLAGS, KNOWN_REQUIRED_FLAGS, SECTION_BLOB_TABLE,
    SECTION_ENTRY_TABLE, SECTION_HEADER_LEN, SECTION_PATH_POOL, TRAILER_LEN,
};
use crate::limits::Limits;
use crate::reader::{Opened, open};
use crate::sections::section_headers;
use crate::tables::{EntryKind, Purpose, Tables};

/// The flags of §12.1 by bit. A name is used only if the reader implements the flag.
const REQUIRED_FLAG_NAMES: [(u32, &str); 1] = [(0, "ZSTD")];
const OPTIONAL_FLAG_NAMES: [(u32, &str); 2] = [(0, "ENTRY_ATTRS"), (1, "KV_METADATA")];

/// How a blob is stored (§7 `encoding`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Encoding {
    Stored,
    Zstd,
}

impl Encoding {
    /// The name used in reports.
    pub const fn as_str(self) -> &'static str {
        match self {
            Encoding::Stored => "stored",
            Encoding::Zstd => "zstd",
        }
    }
}

/// What a listed entry is.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ListKind {
    Directory,
    File {
        /// The blob's `raw_length`.
        size: u64,
        stored_size: u64,
        encoding: Encoding,
        /// The blob's key.
        blob: [u8; 32],
    },
}

/// One entry of a list report.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ListEntry<'a> {
    pub path: &'a str,
    pub kind: ListKind,
}

/// The result of `list`: the entries, in entry order.
#[derive(Debug)]
pub struct ListReport {
    tables: Tables,
}

impl ListReport {
    pub fn entries(&self) -> impl ExactSizeIterator<Item = ListEntry<'_>> {
        self.tables.entries.iter().map(|e| ListEntry {
            path: self.tables.path(e),
            kind: match e.kind {
                EntryKind::Directory => ListKind::Directory,
                EntryKind::File { blob } => {
                    let b = self.tables.blobs.get(blob);
                    ListKind::File {
                        size: b.map_or(0, |b| b.raw_length),
                        stored_size: b.map_or(0, |b| b.stored_length),
                        // BLB-2 lets through only 0, or 1 for a reader that implements ZSTD.
                        encoding: if b.is_some_and(|b| b.encoding == 1) {
                            Encoding::Zstd
                        } else {
                            Encoding::Stored
                        },
                        blob: b.map_or([0; 32], |b| b.key),
                    }
                }
            },
        })
    }
}

/// The `summary` of a verify report. The byte totals can exceed 2^64 in principle, so they
/// are `u128`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Summary {
    pub entries: u64,
    pub files: u64,
    pub directories: u64,
    pub blobs: u64,
    /// The sum of every blob's `stored_length`.
    pub stored_bytes: u128,
    /// The sum of every blob's `raw_length`.
    pub raw_bytes: u128,
    /// The sum of `raw_length` over file entries, so a shared blob counts once per entry.
    pub extracted_bytes: u128,
    /// The names of the required flags that are set, in bit order.
    pub required_flags: Vec<String>,
    /// The names of the optional flags that are set, in bit order.
    pub optional_flags: Vec<String>,
}

/// The result of `verify`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VerifyReport {
    pub summary: Summary,
}

/// The value of an inspect field.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FieldValue {
    /// An unsigned little-endian integer.
    Int(u64),
    /// Raw bytes, rendered as lowercase hex.
    Hex(Vec<u8>),
    /// UTF-8 text (the PATH_POOL payload).
    Text(String),
}

/// One field of an inspect report: a byte range of the file and what it holds.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Field {
    pub name: Cow<'static, str>,
    /// Absolute.
    pub offset: u64,
    pub length: u64,
    /// `None` only for blob data.
    pub value: Option<FieldValue>,
}

/// The header, the data region or the trailer.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Region {
    pub offset: u64,
    pub length: u64,
    pub fields: Vec<Field>,
}

/// A record of the blob table or the entry table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Record {
    pub index: u64,
    pub offset: u64,
    pub length: u64,
    pub fields: Vec<Field>,
}

/// One section, in file order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SectionReport {
    pub ty: u32,
    /// `BLOB_TABLE`, `ENTRY_TABLE`, `PATH_POOL`, or `unknown` for a type this reader doesn't
    /// implement.
    pub name: &'static str,
    /// Of the section header.
    pub offset: u64,
    /// `16 + record_size × record_count`.
    pub length: u64,
    pub record_size: u32,
    pub record_count: u64,
    /// The section header's fields, then the payload for sections without records.
    pub fields: Vec<Field>,
    /// Empty except for the blob and entry tables.
    pub records: Vec<Record>,
}

/// The result of `inspect`: every byte of the file is covered by exactly one field.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InspectReport {
    pub file_length: u64,
    pub header: Region,
    pub data: Region,
    pub sections: Vec<SectionReport>,
    pub trailer: Region,
}

/// Steps 1 to 10 of §13.
fn read_tables<R: Read + Seek>(
    src: &mut R,
    limits: &Limits,
    purpose: Purpose,
) -> Result<(Opened, Tables), Error> {
    let opened = open(src, limits)?;
    let sections = opened.sections(limits)?;
    let tables = opened.tables(&sections, limits, purpose)?;
    Ok((opened, tables))
}

/// `list`: steps 1 to 10, then the entries.
pub fn list<R: Read + Seek>(src: &mut R, limits: &Limits) -> Result<ListReport, Error> {
    let (_, tables) = read_tables(src, limits, Purpose::List)?;
    Ok(ListReport { tables })
}

/// `verify`: all eleven steps, then the summary.
pub fn verify<R: Read + Seek>(src: &mut R, limits: &Limits) -> Result<VerifyReport, Error> {
    let (opened, tables) = read_tables(src, limits, Purpose::Verify)?;
    check_blobs(src, &tables)?;
    Ok(VerifyReport {
        summary: summary(&opened, &tables),
    })
}

/// `inspect`: steps 1 to 10, then every byte of the file.
pub fn inspect<R: Read + Seek>(src: &mut R, limits: &Limits) -> Result<InspectReport, Error> {
    let (opened, tables) = read_tables(src, limits, Purpose::Inspect)?;
    inspect_report(&opened, &tables)
}

fn count(n: usize) -> u64 {
    u64::try_from(n).unwrap_or(u64::MAX)
}

/// The names of the bits set in `bits`, in bit order: the §12.1 name of a flag in `known`,
/// otherwise `bit<N>`.
fn flag_names(bits: u64, known: u64, names: &[(u32, &str)]) -> Vec<String> {
    (0..64u32)
        .filter(|bit| bits >> bit & 1 == 1)
        .map(|bit| {
            names
                .iter()
                .find(|(b, _)| *b == bit && known >> bit & 1 == 1)
                .map_or_else(|| format!("bit{bit}"), |(_, name)| (*name).to_owned())
        })
        .collect()
}

fn summary(opened: &Opened, tables: &Tables) -> Summary {
    let files = tables
        .entries
        .iter()
        .filter(|e| matches!(e.kind, EntryKind::File { .. }))
        .count();
    let extracted_bytes = tables
        .entries
        .iter()
        .filter_map(|e| match e.kind {
            EntryKind::File { blob } => tables.blobs.get(blob),
            EntryKind::Directory => None,
        })
        .map(|b| u128::from(b.raw_length))
        .sum();
    Summary {
        entries: count(tables.entries.len()),
        files: count(files),
        directories: count(tables.entries.len().saturating_sub(files)),
        blobs: count(tables.blobs.len()),
        stored_bytes: tables
            .blobs
            .iter()
            .map(|b| u128::from(b.stored_length))
            .sum(),
        raw_bytes: tables.blobs.iter().map(|b| u128::from(b.raw_length)).sum(),
        extracted_bytes,
        required_flags: flag_names(
            opened.header.required_flags,
            KNOWN_REQUIRED_FLAGS,
            &REQUIRED_FLAG_NAMES,
        ),
        optional_flags: flag_names(
            opened.header.optional_flags,
            KNOWN_OPTIONAL_FLAGS,
            &OPTIONAL_FLAG_NAMES,
        ),
    }
}

fn no_memory(what: &str) -> Error {
    Error::new(
        Category::Io,
        detail::IO_MEMORY,
        format!("cannot allocate memory for {what}"),
    )
}

fn try_vec<T>(len: usize, what: &str) -> Result<Vec<T>, Error> {
    let mut v = Vec::new();
    v.try_reserve_exact(len).map_err(|_| no_memory(what))?;
    Ok(v)
}

fn try_copy(bytes: &[u8], what: &str) -> Result<Vec<u8>, Error> {
    let mut v = try_vec(bytes.len(), what)?;
    v.extend_from_slice(bytes);
    Ok(v)
}

fn int(name: &'static str, offset: u64, length: u64, value: u64) -> Field {
    Field {
        name: Cow::Borrowed(name),
        offset,
        length,
        value: Some(FieldValue::Int(value)),
    }
}

fn hex(name: &'static str, offset: u64, bytes: &[u8]) -> Field {
    Field {
        name: Cow::Borrowed(name),
        offset,
        length: count(bytes.len()),
        value: Some(FieldValue::Hex(bytes.to_vec())),
    }
}

#[derive(Clone, Copy)]
enum Kind {
    Int,
    Hex,
}

/// Lays out consecutive fields over `bytes`, which start at absolute offset `base`.
struct Fields<'a> {
    bytes: &'a [u8],
    at: usize,
    base: u64,
    out: Vec<Field>,
}

impl<'a> Fields<'a> {
    fn new(bytes: &'a [u8], base: u64) -> Self {
        Fields {
            bytes,
            at: 0,
            base,
            out: Vec::new(),
        }
    }

    fn offset(&self) -> u64 {
        self.base.saturating_add(count(self.at))
    }

    /// The next `len` bytes. They lie inside `bytes`: every caller's layout fits the record
    /// or section that step 9 framed.
    fn next(&mut self, len: usize) -> &'a [u8] {
        let end = self.at.saturating_add(len).min(self.bytes.len());
        let b = self.bytes.get(self.at..end).unwrap_or_default();
        self.at = end;
        b
    }

    fn take(&mut self, name: &'static str, len: usize, kind: Kind) {
        let offset = self.offset();
        let b = self.next(len);
        self.out.push(match kind {
            Kind::Int => {
                let mut le = [0u8; 8];
                for (o, x) in le.iter_mut().zip(b) {
                    *o = *x;
                }
                int(name, offset, count(b.len()), u64::from_le_bytes(le))
            }
            Kind::Hex => hex(name, offset, b),
        });
    }

    /// The rest of the bytes as one field named `name`, unless there are none.
    fn rest(&mut self, name: &'static str, text: bool) -> Result<(), Error> {
        let offset = self.offset();
        let b = self.next(self.bytes.len().saturating_sub(self.at));
        if b.is_empty() {
            return Ok(());
        }
        let value = if text {
            // The PATH_POOL payload is made of paths that passed PATH-1 (CAN-3), so it is
            // valid UTF-8.
            let s = std::str::from_utf8(b).unwrap_or_default();
            let mut t = String::new();
            t.try_reserve_exact(s.len())
                .map_err(|_| no_memory("the path pool"))?;
            t.push_str(s);
            FieldValue::Text(t)
        } else {
            FieldValue::Hex(try_copy(b, "a section payload")?)
        };
        self.out.push(Field {
            name: Cow::Borrowed(name),
            offset,
            length: count(b.len()),
            value: Some(value),
        });
        Ok(())
    }
}

/// The layout of a blob record (Appendix B).
const BLOB_FIELDS: [(&str, usize, Kind); 6] = [
    ("key", 32, Kind::Hex),
    ("offset", 8, Kind::Int),
    ("stored_length", 8, Kind::Int),
    ("raw_length", 8, Kind::Int),
    ("encoding", 1, Kind::Int),
    ("reserved", 7, Kind::Hex),
];

/// The layout of an entry record for a reader that doesn't implement ENTRY_ATTRS
/// (Appendix B): anything beyond 48 bytes is `extra`.
const ENTRY_FIELDS: [(&str, usize, Kind); 5] = [
    ("path_offset", 8, Kind::Int),
    ("path_length", 4, Kind::Int),
    ("type", 1, Kind::Int),
    ("reserved", 3, Kind::Hex),
    ("blob_key", 32, Kind::Hex),
];

fn records(
    payload: &[u8],
    base: u64,
    record_size: u32,
    layout: &[(&'static str, usize, Kind)],
) -> Result<Vec<Record>, Error> {
    let size = usize::try_from(record_size).unwrap_or(usize::MAX).max(1);
    let chunks = payload.chunks_exact(size);
    let mut out = try_vec(chunks.len(), "inspect records")?;
    let mut offset = base;
    for (i, record) in chunks.enumerate() {
        let mut f = Fields::new(record, offset);
        for &(name, len, kind) in layout {
            f.take(name, len, kind);
        }
        f.rest("extra", false)?;
        out.push(Record {
            index: count(i),
            offset,
            length: u64::from(record_size),
            fields: f.out,
        });
        offset = offset.saturating_add(u64::from(record_size));
    }
    Ok(out)
}

fn inspect_report(opened: &Opened, tables: &Tables) -> Result<InspectReport, Error> {
    let h = &opened.header;
    let t = &opened.trailer;
    let index_offset = t.index_offset;

    let header = Region {
        offset: 0,
        length: HEADER_LEN,
        fields: vec![
            hex("magic", 0, &h.magic),
            int("major_version", 8, 2, u64::from(h.major_version)),
            int("minor_version", 10, 2, u64::from(h.minor_version)),
            int("hash_alg", 12, 1, u64::from(h.hash_alg)),
            hex("reserved", 13, &h.reserved),
            int("required_flags", 16, 8, h.required_flags),
            int("optional_flags", 24, 8, h.optional_flags),
        ],
    };

    let mut data_fields = try_vec(tables.blobs.len(), "inspect fields")?;
    for (i, b) in tables.blobs.iter().enumerate() {
        data_fields.push(Field {
            name: Cow::Owned(format!("blob[{i}].data")),
            offset: b.offset,
            length: b.stored_length,
            value: None,
        });
    }
    let data = Region {
        offset: HEADER_LEN,
        length: index_offset.saturating_sub(HEADER_LEN),
        fields: data_fields,
    };

    let index = opened.index.as_slice();
    let mut sections = Vec::new();
    for s in section_headers(index) {
        let offset = index_offset.saturating_add(count(s.at));
        let payload = index.get(s.payload.clone()).unwrap_or_default();
        let payload_offset = offset.saturating_add(count(SECTION_HEADER_LEN));
        let mut f = Fields::new(index.get(s.at..s.payload.end).unwrap_or_default(), offset);
        f.take("type", 4, Kind::Int);
        f.take("record_size", 4, Kind::Int);
        f.take("record_count", 8, Kind::Int);
        // Only the three required types are implemented by a Core reader, so KV_METADATA is
        // `unknown` (F33).
        let (name, records) = match s.ty {
            SECTION_BLOB_TABLE => (
                "BLOB_TABLE",
                records(payload, payload_offset, s.record_size, &BLOB_FIELDS)?,
            ),
            SECTION_ENTRY_TABLE => (
                "ENTRY_TABLE",
                records(payload, payload_offset, s.record_size, &ENTRY_FIELDS)?,
            ),
            SECTION_PATH_POOL => {
                f.rest("payload", true)?;
                ("PATH_POOL", Vec::new())
            }
            _ => {
                f.rest("payload", false)?;
                ("unknown", Vec::new())
            }
        };
        sections.push(SectionReport {
            ty: s.ty,
            name,
            offset,
            length: count(s.payload.end.saturating_sub(s.at)),
            record_size: s.record_size,
            record_count: s.record_count,
            fields: f.out,
            records,
        });
    }

    let trailer_offset = opened.file_length.saturating_sub(TRAILER_LEN);
    let trailer = Region {
        offset: trailer_offset,
        length: TRAILER_LEN,
        fields: vec![
            int("index_offset", trailer_offset, 8, t.index_offset),
            int(
                "index_length",
                trailer_offset.saturating_add(8),
                8,
                t.index_length,
            ),
            hex(
                "structure_hash",
                trailer_offset.saturating_add(16),
                &t.structure_hash,
            ),
            hex(
                "trailer_magic",
                trailer_offset.saturating_add(48),
                &t.trailer_magic,
            ),
        ],
    };

    Ok(InspectReport {
        file_length: opened.file_length,
        header,
        data,
        sections,
        trailer,
    })
}

/// Builds complete container files for the unit tests of this module and of `blobs`.
#[cfg(test)]
pub(crate) mod build {
    use sha2::{Digest, Sha256};

    use crate::format::{
        MAGIC, SECTION_BLOB_TABLE, SECTION_ENTRY_TABLE, SECTION_PATH_POOL, TRAILER_MAGIC,
    };

    pub struct Spec<'a> {
        /// (path, None) for a directory, (path, Some(content)) for a file, in canonical order.
        pub tree: &'a [(&'a str, Option<&'a [u8]>)],
        pub blob_record_size: u32,
        pub entry_record_size: u32,
        pub optional_flags: u64,
        /// Sections after the three required ones: (type, record_size, payload).
        pub more: &'a [(u32, u32, &'a [u8])],
    }

    impl<'a> Spec<'a> {
        pub fn new(tree: &'a [(&'a str, Option<&'a [u8]>)]) -> Self {
            Spec {
                tree,
                blob_record_size: 64,
                entry_record_size: 48,
                optional_flags: 0,
                more: &[],
            }
        }
    }

    fn section(out: &mut Vec<u8>, ty: u32, record_size: u32, count: usize, payload: &[u8]) {
        out.extend_from_slice(&ty.to_le_bytes());
        out.extend_from_slice(&record_size.to_le_bytes());
        out.extend_from_slice(&(count as u64).to_le_bytes());
        out.extend_from_slice(payload);
    }

    /// The canonical container of `spec`. Record bytes beyond the base sizes are 0xEE.
    pub fn file(spec: &Spec) -> Vec<u8> {
        let mut data = Vec::new();
        let mut blobs = Vec::new();
        let mut keys: Vec<[u8; 32]> = Vec::new();
        let mut entries = Vec::new();
        let mut pool = Vec::new();
        for (path, content) in spec.tree {
            let key = match content {
                None => [0; 32],
                Some(c) => {
                    let k: [u8; 32] = Sha256::digest(c).into();
                    if !keys.contains(&k) {
                        keys.push(k);
                        blobs.extend_from_slice(&k);
                        blobs.extend_from_slice(&(32 + data.len() as u64).to_le_bytes());
                        blobs.extend_from_slice(&(c.len() as u64).to_le_bytes());
                        blobs.extend_from_slice(&(c.len() as u64).to_le_bytes());
                        blobs.resize(blobs.len() + 8, 0);
                        blobs.resize(blobs.len() + spec.blob_record_size as usize - 64, 0xEE);
                        data.extend_from_slice(c);
                    }
                    k
                }
            };
            entries.extend_from_slice(&(pool.len() as u64).to_le_bytes());
            entries.extend_from_slice(&(path.len() as u32).to_le_bytes());
            entries.push(if content.is_some() { 2 } else { 1 });
            entries.extend_from_slice(&[0; 3]);
            entries.extend_from_slice(&key);
            entries.resize(entries.len() + spec.entry_record_size as usize - 48, 0xEE);
            pool.extend_from_slice(path.as_bytes());
        }
        let mut index = Vec::new();
        section(
            &mut index,
            SECTION_BLOB_TABLE,
            spec.blob_record_size,
            keys.len(),
            &blobs,
        );
        section(
            &mut index,
            SECTION_ENTRY_TABLE,
            spec.entry_record_size,
            spec.tree.len(),
            &entries,
        );
        section(&mut index, SECTION_PATH_POOL, 1, pool.len(), &pool);
        for (ty, size, payload) in spec.more {
            section(
                &mut index,
                *ty,
                *size,
                payload.len() / *size as usize,
                payload,
            );
        }

        let mut header = Vec::new();
        header.extend_from_slice(&MAGIC);
        header.extend_from_slice(&1u16.to_le_bytes());
        header.extend_from_slice(&0u16.to_le_bytes());
        header.extend_from_slice(&[1, 0, 0, 0]);
        header.extend_from_slice(&0u64.to_le_bytes());
        header.extend_from_slice(&spec.optional_flags.to_le_bytes());
        let mut trailer = Vec::new();
        trailer.extend_from_slice(&(32 + data.len() as u64).to_le_bytes());
        trailer.extend_from_slice(&(index.len() as u64).to_le_bytes());
        let mut h = Sha256::new();
        h.update(&header);
        h.update(&index);
        h.update(&trailer);
        trailer.extend_from_slice(&h.finalize());
        trailer.extend_from_slice(&TRAILER_MAGIC);
        [header, data, index, trailer].concat()
    }
}

#[cfg(test)]
mod tests {
    use std::io::Cursor;

    use super::build::{Spec, file};
    use super::*;

    const TREE: &[(&str, Option<&[u8]>)] = &[
        ("d", None),
        ("d/a", Some(b"same")),
        ("d/b", Some(b"same")),
        ("d/e", Some(b"")),
        ("z", Some(b"other!")),
    ];

    fn src(bytes: &[u8]) -> Cursor<Vec<u8>> {
        Cursor::new(bytes.to_vec())
    }

    #[test]
    fn list_gives_every_entry_in_order() {
        let r = list(&mut src(&file(&Spec::new(TREE))), &Limits::default()).unwrap();
        let got: Vec<(&str, ListKind)> = r.entries().map(|e| (e.path, e.kind)).collect();
        let file = |c: &[u8]| ListKind::File {
            size: c.len() as u64,
            stored_size: c.len() as u64,
            encoding: Encoding::Stored,
            blob: sha2::Sha256::digest(c).into(),
        };
        use sha2::Digest;
        assert_eq!(
            got,
            [
                ("d", ListKind::Directory),
                ("d/a", file(b"same")),
                ("d/b", file(b"same")),
                ("d/e", file(b"")),
                ("z", file(b"other!")),
            ]
        );
        assert_eq!(Encoding::Stored.as_str(), "stored");
        assert_eq!(Encoding::Zstd.as_str(), "zstd");
    }

    #[test]
    fn the_summary_counts_shared_blobs_once_and_files_per_entry() {
        let r = verify(&mut src(&file(&Spec::new(TREE))), &Limits::default()).unwrap();
        assert_eq!(
            r.summary,
            Summary {
                entries: 5,
                files: 4,
                directories: 1,
                blobs: 3,
                stored_bytes: 10,
                raw_bytes: 10,
                extracted_bytes: 14,
                required_flags: vec![],
                optional_flags: vec![],
            }
        );
    }

    #[test]
    fn flags_this_reader_does_not_implement_are_named_by_bit() {
        let spec = Spec {
            optional_flags: 1 | 2 | 1 << 63,
            ..Spec::new(TREE)
        };
        let r = verify(&mut src(&file(&spec)), &Limits::default()).unwrap();
        assert_eq!(r.summary.optional_flags, ["bit0", "bit1", "bit63"]);
        assert!(r.summary.required_flags.is_empty());
        // A flag the reader implements gets its §12.1 name; one it doesn't, its bit.
        assert_eq!(
            flag_names(0b11, 0b01, &OPTIONAL_FLAG_NAMES),
            ["ENTRY_ATTRS", "bit1"]
        );
        assert_eq!(
            flag_names(0b11, 0b10, &OPTIONAL_FLAG_NAMES),
            ["bit0", "KV_METADATA"]
        );
        assert_eq!(flag_names(1, 1, &REQUIRED_FLAG_NAMES), ["ZSTD"]);
        assert_eq!(flag_names(1 << 5, u64::MAX, &REQUIRED_FLAG_NAMES), ["bit5"]);
    }

    #[test]
    fn list_and_inspect_do_not_apply_the_total_size_limit() {
        let bytes = file(&Spec::new(TREE));
        let limits = Limits {
            max_total_bytes: 13,
            ..Limits::default()
        };
        assert!(list(&mut src(&bytes), &limits).is_ok());
        assert!(inspect(&mut src(&bytes), &limits).is_ok());
        let e = verify(&mut src(&bytes), &limits).unwrap_err();
        assert_eq!(e.detail(), detail::LIMIT_TOTAL_SIZE);
    }

    #[test]
    fn list_and_inspect_do_not_check_blob_data() {
        let mut bytes = file(&Spec::new(TREE));
        bytes[32] ^= 1;
        let l = Limits::default();
        assert!(list(&mut src(&bytes), &l).is_ok());
        assert!(inspect(&mut src(&bytes), &l).is_ok());
        let e = verify(&mut src(&bytes), &l).unwrap_err();
        assert_eq!(
            (e.category(), e.detail()),
            (Category::Integrity, detail::BLOB_HASH)
        );
    }

    /// Every field of the report, sorted by offset.
    fn all_fields(r: &InspectReport) -> Vec<&Field> {
        let mut v: Vec<&Field> = r.header.fields.iter().collect();
        v.extend(&r.data.fields);
        for s in &r.sections {
            v.extend(&s.fields);
            for rec in &s.records {
                v.extend(&rec.fields);
            }
        }
        v.extend(&r.trailer.fields);
        v.sort_by_key(|f| (f.offset, f.length));
        v
    }

    fn assert_covers_every_byte(r: &InspectReport) {
        let mut at = 0;
        for f in all_fields(r) {
            assert_eq!(f.offset, at, "{} starts at {}, not {at}", f.name, f.offset);
            at += f.length;
        }
        assert_eq!(at, r.file_length);
    }

    fn by_name<'a>(fields: &'a [Field], name: &str) -> &'a Field {
        fields.iter().find(|f| f.name == name).unwrap()
    }

    #[test]
    fn inspect_covers_every_byte_with_its_value() {
        let bytes = file(&Spec::new(TREE));
        let r = inspect(&mut src(&bytes), &Limits::default()).unwrap();
        assert_covers_every_byte(&r);
        assert_eq!(r.file_length, bytes.len() as u64);
        // Each field's value is the bytes it covers.
        for f in all_fields(&r) {
            let b = &bytes[f.offset as usize..(f.offset + f.length) as usize];
            match &f.value {
                Some(FieldValue::Int(n)) => {
                    let mut le = [0u8; 8];
                    le[..b.len()].copy_from_slice(b);
                    assert_eq!(*n, u64::from_le_bytes(le), "{}", f.name);
                }
                Some(FieldValue::Hex(h)) => assert_eq!(h, b, "{}", f.name),
                Some(FieldValue::Text(t)) => assert_eq!(t.as_bytes(), b, "{}", f.name),
                None => assert!(f.name.ends_with(".data"), "{}", f.name),
            }
        }
        let names: Vec<&str> = r.sections.iter().map(|s| s.name).collect();
        assert_eq!(names, ["BLOB_TABLE", "ENTRY_TABLE", "PATH_POOL"]);
        let pool = &r.sections[2];
        assert_eq!(
            by_name(&pool.fields, "payload").value,
            Some(FieldValue::Text("dd/ad/bd/ez".to_owned()))
        );
        let blobs = &r.sections[0];
        assert_eq!((blobs.offset, blobs.length), (42, 16 + 3 * 64));
        assert_eq!(blobs.records.len(), 3);
        assert_eq!(
            (blobs.records[2].index, blobs.records[2].offset),
            (2, 42 + 16 + 128)
        );
        let names: Vec<&str> = r.data.fields.iter().map(|f| f.name.as_ref()).collect();
        assert_eq!(names, ["blob[0].data", "blob[1].data", "blob[2].data"]);
        assert_eq!((r.data.offset, r.data.length), (32, 10));
        assert_eq!(
            (r.trailer.offset, r.trailer.length),
            (bytes.len() as u64 - 56, 56)
        );
    }

    #[test]
    fn inspect_shows_wider_records_and_unknown_sections() {
        let spec = Spec {
            blob_record_size: 72,
            entry_record_size: 64,
            optional_flags: 1,
            more: &[(0x10, 1, b"kv"), (0x11, 4, b""), (0x12, 4, b"abcdefgh")],
            ..Spec::new(TREE)
        };
        let r = inspect(&mut src(&file(&spec)), &Limits::default()).unwrap();
        assert_covers_every_byte(&r);
        let extra = |rec: &Record| by_name(&rec.fields, "extra").clone();
        let blob_extra = extra(&r.sections[0].records[0]);
        assert_eq!(blob_extra.length, 8);
        assert_eq!(blob_extra.value, Some(FieldValue::Hex(vec![0xEE; 8])));
        // A Core reader doesn't implement ENTRY_ATTRS, so bytes 48 to 63 are `extra`.
        let entry_extra = extra(&r.sections[1].records[4]);
        assert_eq!(entry_extra.length, 16);
        assert_eq!(entry_extra.value, Some(FieldValue::Hex(vec![0xEE; 16])));
        assert_eq!(r.sections[1].records[4].fields.len(), 6);
        assert_eq!(r.sections[1].records[4].length, 64);

        let more = &r.sections[3..];
        let names: Vec<&str> = more.iter().map(|s| s.name).collect();
        assert_eq!(names, ["unknown"; 3]);
        assert_eq!(
            by_name(&more[0].fields, "payload").value,
            Some(FieldValue::Hex(b"kv".to_vec()))
        );
        // An empty payload has no field.
        assert_eq!(more[1].fields.len(), 3);
        assert_eq!((more[2].record_size, more[2].record_count), (4, 2));
        assert_eq!(more[2].length, 16 + 8);
        assert!(more.iter().all(|s| s.records.is_empty()));
    }

    #[test]
    fn an_empty_container_is_inspected() {
        let r = inspect(&mut src(&file(&Spec::new(&[]))), &Limits::default()).unwrap();
        assert_covers_every_byte(&r);
        assert!(r.data.fields.is_empty() && r.data.length == 0);
        assert!(
            r.sections
                .iter()
                .all(|s| s.records.is_empty() && s.fields.len() == 3)
        );
    }
}
