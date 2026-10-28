//! The reader, §13 step 9: the sections of the index (SEC-1 to SEC-5) and the entry count
//! (LIM-3).
//!
//! Each rule is a pass over the index, in the order of §13 ("SEC-1, for each section header in
//! turn, framing the whole index; SEC-2, over every section; ..."), so only the first
//! violation is reported. The passes allocate nothing in proportion to the number of sections.

use std::ops::Range;

use crate::error::{Category, Error, detail};
use crate::format::{
    BLOB_RECORD_SIZE, ENTRY_RECORD_SIZE, Header, KNOWN_OPTIONAL_FLAGS, KNOWN_REQUIRED_FLAGS,
    MUST_UNDERSTAND, SECTION_BLOB_TABLE, SECTION_ENTRY_TABLE, SECTION_HEADER_LEN,
    SECTION_PATH_POOL, field,
};
use crate::limits::Limits;

/// One of the three required sections.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Table {
    pub record_size: u32,
    pub record_count: u64,
    /// The payload's byte range within the index. It lies entirely inside the index (SEC-1).
    pub payload: Range<usize>,
}

/// The three required sections, in the order SEC-3 fixes.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Sections {
    pub blob_table: Table,
    pub entry_table: Table,
    pub path_pool: Table,
}

/// A section as framed by SEC-1.
struct Section {
    ty: u32,
    record_size: u32,
    record_count: u64,
    payload: Range<usize>,
}

impl Section {
    fn table(&self) -> Table {
        Table {
            record_size: self.record_size,
            record_count: self.record_count,
            payload: self.payload.clone(),
        }
    }
}

/// Walks the sections of an index, framing each one (SEC-1). After an error it ends.
struct Walk<'a> {
    index: &'a [u8],
    at: usize,
}

fn bounds(at: usize, what: &str) -> Error {
    Error::new(
        Category::Malformed,
        detail::SEC_BOUNDS,
        format!("the section at index offset {at}: {what}"),
    )
}

impl Iterator for Walk<'_> {
    type Item = Result<Section, Error>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.at >= self.index.len() {
            return None;
        }
        let at = self.at;
        let item = frame(self.index, at);
        self.at = match &item {
            Ok(s) => s.payload.end,
            Err(_) => self.index.len(),
        };
        Some(item)
    }
}

/// SEC-1 for the section whose header starts at `at`.
fn frame(index: &[u8], at: usize) -> Result<Section, Error> {
    let start = at
        .checked_add(SECTION_HEADER_LEN)
        .ok_or_else(|| bounds(at, "the header lies beyond the index"))?;
    let header: &[u8; SECTION_HEADER_LEN] = index
        .get(at..start)
        .and_then(|h| h.try_into().ok())
        .ok_or_else(|| bounds(at, "the header is cut off by the end of the index"))?;
    let ty = u32::from_le_bytes(field(header, 0));
    let record_size = u32::from_le_bytes(field(header, 4));
    let record_count = u64::from_le_bytes(field(header, 8));
    let end = u64::from(record_size)
        .checked_mul(record_count)
        .and_then(|len| usize::try_from(len).ok())
        .and_then(|len| start.checked_add(len))
        .filter(|end| *end <= index.len())
        .ok_or_else(|| {
            bounds(
                at,
                &format!("{record_count} records of {record_size} bytes don't fit the index"),
            )
        })?;
    Ok(Section {
        ty,
        record_size,
        record_count,
        payload: start..end,
    })
}

fn walk(index: &[u8]) -> Walk<'_> {
    Walk { index, at: 0 }
}

fn is_known(ty: u32) -> bool {
    [SECTION_BLOB_TABLE, SECTION_ENTRY_TABLE, SECTION_PATH_POOL].contains(&ty)
}

fn layout(message: impl Into<String>) -> Error {
    Error::new(Category::Malformed, detail::SEC_LAYOUT, message)
}

/// The section at `position`, which SEC-3 says must have type `want`.
fn take_required(sections: &mut Walk<'_>, position: usize, want: u32) -> Result<Section, Error> {
    match sections.next().transpose()? {
        Some(s) if s.ty == want => Ok(s),
        Some(s) => Err(layout(format!(
            "section {position} has type {:#010x}; it must be {want:#010x}",
            s.ty
        ))),
        None => Err(layout(format!(
            "the index has {position} sections; the first three are required"
        ))),
    }
}

/// Checks the sections of `index` (§13 step 9) under the flags of `header` and `limits`.
pub fn parse_sections(index: &[u8], header: &Header, limits: &Limits) -> Result<Sections, Error> {
    // SEC-1, for each section header in turn, framing the whole index.
    for section in walk(index) {
        section?;
    }

    // SEC-2, over every section.
    for section in walk(index) {
        let section = section?;
        if !is_known(section.ty) && section.ty & MUST_UNDERSTAND != 0 {
            return Err(Error::new(
                Category::Unsupported,
                detail::SEC_UNKNOWN_CRITICAL,
                format!(
                    "section type {:#010x} must be understood and isn't",
                    section.ty
                ),
            ));
        }
    }

    // SEC-3. The first three sections are the required ones, in order. Any after them have
    // strictly ascending types, and none repeats one of the required types.
    let mut sections = walk(index);
    let blob = take_required(&mut sections, 0, SECTION_BLOB_TABLE)?;
    let entry = take_required(&mut sections, 1, SECTION_ENTRY_TABLE)?;
    let path = take_required(&mut sections, 2, SECTION_PATH_POOL)?;
    let mut previous: Option<u32> = None;
    for section in sections {
        let section = section?;
        if is_known(section.ty) {
            return Err(layout(format!(
                "section type {:#010x} appears again after the first three sections",
                section.ty
            )));
        }
        if previous.is_some_and(|p| section.ty <= p) {
            return Err(layout(format!(
                "section type {:#010x} is not above the one before it",
                section.ty
            )));
        }
        previous = Some(section.ty);
    }

    // SEC-4 for every section in file order, then SEC-5 for every section in file order.
    for section in walk(index) {
        let section = section?;
        let too_small = match section.ty {
            SECTION_BLOB_TABLE => section.record_size < BLOB_RECORD_SIZE,
            SECTION_ENTRY_TABLE => section.record_size < ENTRY_RECORD_SIZE,
            SECTION_PATH_POOL => section.record_size != 1,
            _ => false,
        };
        if too_small {
            return Err(Error::new(
                Category::Malformed,
                detail::SEC_RECORD_SIZE_MIN,
                format!(
                    "section type {:#010x} has record size {}, below what its type needs",
                    section.ty, section.record_size
                ),
            ));
        }
    }
    let knows_every_flag = header.required_flags & !KNOWN_REQUIRED_FLAGS == 0
        && header.optional_flags & !KNOWN_OPTIONAL_FLAGS == 0;
    if knows_every_flag {
        for section in walk(index) {
            let section = section?;
            let wrong = match section.ty {
                SECTION_BLOB_TABLE => section.record_size != BLOB_RECORD_SIZE,
                SECTION_ENTRY_TABLE => section.record_size != ENTRY_RECORD_SIZE,
                _ => false,
            };
            if wrong {
                return Err(Error::new(
                    Category::Malformed,
                    detail::SEC_RECORD_SIZE,
                    format!(
                        "section type {:#010x} has record size {}, but the header's flags fix it",
                        section.ty, section.record_size
                    ),
                ));
            }
        }
    }

    // LIM-3, on the entry count, before anything is allocated per entry.
    if entry.record_count > limits.max_entries {
        return Err(Error::new(
            Category::LimitExceeded,
            detail::LIMIT_ENTRIES,
            format!(
                "the container has {} entries; the limit is {}",
                entry.record_count, limits.max_entries
            ),
        ));
    }
    Ok(Sections {
        blob_table: blob.table(),
        entry_table: entry.table(),
        path_pool: path.table(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::format::MAGIC;

    const MAX: u32 = u32::MAX;

    fn header(required: u64, optional: u64) -> Header {
        Header {
            magic: MAGIC,
            major_version: 1,
            minor_version: 0,
            hash_alg: 1,
            reserved: [0; 3],
            required_flags: required,
            optional_flags: optional,
        }
    }

    /// A section with a zeroed payload of `record_size * record_count` bytes.
    fn sec(ty: u32, record_size: u32, record_count: u64) -> Vec<u8> {
        let mut s = Vec::new();
        s.extend_from_slice(&ty.to_le_bytes());
        s.extend_from_slice(&record_size.to_le_bytes());
        s.extend_from_slice(&record_count.to_le_bytes());
        s.resize(16 + (u64::from(record_size) * record_count) as usize, 0);
        s
    }

    fn index(sections: &[Vec<u8>]) -> Vec<u8> {
        sections.concat()
    }

    fn required() -> Vec<Vec<u8>> {
        vec![
            sec(SECTION_BLOB_TABLE, 64, 0),
            sec(SECTION_ENTRY_TABLE, 48, 0),
            sec(SECTION_PATH_POOL, 1, 0),
        ]
    }

    fn parse(i: &[u8]) -> Result<Sections, Error> {
        parse_sections(i, &header(0, 0), &Limits::default())
    }

    fn fails(i: &[u8], category: Category, d: &str) {
        let e = parse(i).unwrap_err();
        assert_eq!((e.category(), e.detail()), (category, d), "{e}");
    }

    #[test]
    fn the_three_required_sections_are_returned_with_their_payloads() {
        let i = index(&[
            sec(SECTION_BLOB_TABLE, 64, 1),
            sec(SECTION_ENTRY_TABLE, 48, 2),
            sec(SECTION_PATH_POOL, 1, 5),
        ]);
        let s = parse(&i).unwrap();
        assert_eq!(s.blob_table.payload, 16..80);
        assert_eq!(s.entry_table.payload, 96..192);
        assert_eq!(
            (s.entry_table.record_size, s.entry_table.record_count),
            (48, 2)
        );
        assert_eq!(s.path_pool.payload, 208..213);
        assert_eq!(i.len(), 213);
    }

    #[test]
    fn sec_1_frames_the_whole_index() {
        // A header cut off by the end, a payload past the end, and an overflowing product.
        let mut cut = index(&required());
        cut.extend_from_slice(&[0; 8]);
        fails(&cut, Category::Malformed, detail::SEC_BOUNDS);
        let mut past = required();
        past[2] = sec(SECTION_PATH_POOL, 1, 0);
        past[2][8] = 44;
        fails(&index(&past), Category::Malformed, detail::SEC_BOUNDS);
        let mut huge = required();
        huge[0] = sec(SECTION_BLOB_TABLE, 0, 0);
        huge[0][4..8].copy_from_slice(&MAX.to_le_bytes());
        huge[0][8..16].copy_from_slice(&u64::MAX.to_le_bytes());
        fails(&index(&huge), Category::Malformed, detail::SEC_BOUNDS);
        // 65536 * 2^48 is exactly 2^64. A wrapping product would be 0 and accept an empty payload.
        let mut wrap = required();
        wrap[0] = sec(SECTION_BLOB_TABLE, 0, 0);
        wrap[0][4..8].copy_from_slice(&65536u32.to_le_bytes());
        wrap[0][8..16].copy_from_slice(&(1u64 << 48).to_le_bytes());
        fails(&index(&wrap), Category::Malformed, detail::SEC_BOUNDS);
        // 2^60 records of 64 bytes overflow u64 only when multiplied; 2^32 do not.
        let mut big = required();
        big[1][8..16].copy_from_slice(&(1u64 << 32).to_le_bytes());
        fails(&index(&big), Category::Malformed, detail::SEC_BOUNDS);
    }

    #[test]
    fn sec_1_comes_before_sec_2() {
        // An unknown must-understand section first, then a header cut off at the end.
        let mut s = required();
        s.push(sec(0xFFFF_FFF0, 1, 0));
        let mut i = index(&s);
        i.extend_from_slice(&[0; 4]);
        fails(&i, Category::Malformed, detail::SEC_BOUNDS);
    }

    #[test]
    fn sec_2_rejects_an_unknown_must_understand_section_and_skips_the_rest() {
        let mut s = required();
        s.push(sec(0xFFFF_FFF0, 1, 0));
        fails(
            &index(&s),
            Category::Unsupported,
            detail::SEC_UNKNOWN_CRITICAL,
        );
        // Without the bit, an unknown section is skipped (so is KV_METADATA in a Core reader).
        for ty in [0x10, 0x7FFF_FFF0] {
            let mut s = required();
            s.push(sec(ty, 1, 3));
            parse(&index(&s)).unwrap();
        }
    }

    #[test]
    fn sec_2_comes_before_sec_3() {
        let s = vec![
            sec(SECTION_PATH_POOL, 1, 0),
            sec(0xFFFF_FFF0, 1, 0),
            sec(SECTION_BLOB_TABLE, 64, 0),
        ];
        fails(
            &index(&s),
            Category::Unsupported,
            detail::SEC_UNKNOWN_CRITICAL,
        );
    }

    #[test]
    fn sec_3_fixes_the_layout() {
        fails(&[], Category::Malformed, detail::SEC_LAYOUT);
        let mut two = required();
        two.pop();
        fails(&index(&two), Category::Malformed, detail::SEC_LAYOUT);
        let mut swapped = required();
        swapped.swap(1, 2);
        fails(&index(&swapped), Category::Malformed, detail::SEC_LAYOUT);
        let mut repeat = required();
        repeat.push(sec(SECTION_BLOB_TABLE, 64, 0));
        fails(&index(&repeat), Category::Malformed, detail::SEC_LAYOUT);
        for extra in [[0x20, 0x10], [0x20, 0x20]] {
            let mut s = required();
            s.extend(extra.map(|ty| sec(ty, 1, 0)));
            fails(&index(&s), Category::Malformed, detail::SEC_LAYOUT);
        }
        let mut ascending = required();
        ascending.extend([0x10, 0x20, 0x7FFF_FFFF].map(|ty| sec(ty, 1, 0)));
        parse(&index(&ascending)).unwrap();
    }

    #[test]
    fn sec_4_sets_a_minimum_and_sec_4_comes_before_sec_5() {
        let mut small = required();
        small[0] = sec(SECTION_BLOB_TABLE, 63, 0);
        fails(
            &index(&small),
            Category::Malformed,
            detail::SEC_RECORD_SIZE_MIN,
        );
        small[0] = sec(SECTION_BLOB_TABLE, 64, 0);
        small[1] = sec(SECTION_ENTRY_TABLE, 47, 0);
        fails(
            &index(&small),
            Category::Malformed,
            detail::SEC_RECORD_SIZE_MIN,
        );
        let mut pool = required();
        pool[2] = sec(SECTION_PATH_POOL, 2, 0);
        fails(
            &index(&pool),
            Category::Malformed,
            detail::SEC_RECORD_SIZE_MIN,
        );
        // The blob table violates SEC-5 and the entry table SEC-4: SEC-4 is reported.
        let mut both = required();
        both[0] = sec(SECTION_BLOB_TABLE, 72, 0);
        both[1] = sec(SECTION_ENTRY_TABLE, 40, 0);
        fails(
            &index(&both),
            Category::Malformed,
            detail::SEC_RECORD_SIZE_MIN,
        );
    }

    #[test]
    fn sec_5_fixes_the_record_size_unless_a_flag_is_unknown() {
        let mut wide = required();
        wide[0] = sec(SECTION_BLOB_TABLE, 72, 0);
        fails(&index(&wide), Category::Malformed, detail::SEC_RECORD_SIZE);
        let mut wide_entry = required();
        wide_entry[1] = sec(SECTION_ENTRY_TABLE, 64, 0);
        fails(
            &index(&wide_entry),
            Category::Malformed,
            detail::SEC_RECORD_SIZE,
        );
        // An optional flag this reader doesn't know lets both tables be wider.
        let mut both = required();
        both[0] = sec(SECTION_BLOB_TABLE, 72, 1);
        both[1] = sec(SECTION_ENTRY_TABLE, 64, 1);
        let i = index(&both);
        parse_sections(&i, &header(0, 1 << 63), &Limits::default()).unwrap();
    }

    #[test]
    fn lim_3_checks_the_entry_count_after_the_layout() {
        let s = vec![
            sec(SECTION_BLOB_TABLE, 64, 0),
            sec(SECTION_ENTRY_TABLE, 48, 5),
            sec(SECTION_PATH_POOL, 1, 0),
        ];
        let i = index(&s);
        let limits = |n| Limits {
            max_entries: n,
            ..Limits::default()
        };
        let e = parse_sections(&i, &header(0, 0), &limits(4)).unwrap_err();
        assert_eq!(
            (e.category(), e.detail()),
            (Category::LimitExceeded, detail::LIMIT_ENTRIES)
        );
        parse_sections(&i, &header(0, 0), &limits(5)).unwrap();
        // A layout violation comes first, even when the count is over the limit.
        let mut bad = s;
        bad.swap(1, 2);
        let e = parse_sections(&index(&bad), &header(0, 0), &limits(0)).unwrap_err();
        assert_eq!(e.detail(), detail::SEC_LAYOUT);
    }
}
