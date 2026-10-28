//! AC-ENG-8: the reader uses exactly the Unicode 16.0 tables (D16, PATH-2).

#![forbid(unsafe_code)]

use std::fs::File;
use std::path::PathBuf;

use chst_format::{Category, Limits, Purpose, open};
use unicode_normalization::char::canonical_combining_class;
use unicode_normalization::{UNICODE_VERSION, is_nfc};

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../fixtures")
        .join(name)
}

#[test]
fn the_normalization_tables_are_unicode_16_0() {
    assert_eq!(UNICODE_VERSION, (16, 0, 0));
    // U+113CE was assigned in 16.0, with canonical combining class 9. Older tables give 0.
    assert_eq!(canonical_combining_class('\u{113CE}'), 9);
}

/// The paths of a container that has passed steps 1 to 9, read from its entry table and
/// path pool (§8, §9) without the step-10 checks.
fn raw_paths(name: &str) -> Vec<Vec<u8>> {
    let limits = Limits::default();
    let opened = open(&mut File::open(fixture(name)).unwrap(), &limits).unwrap();
    let sections = opened.sections(&limits).unwrap();
    let pool = &opened.index[sections.path_pool.payload.clone()];
    let entries = &opened.index[sections.entry_table.payload.clone()];
    entries
        .chunks_exact(sections.entry_table.record_size as usize)
        .map(|r| {
            let offset = u64::from_le_bytes(r[0..8].try_into().unwrap()) as usize;
            let length = u32::from_le_bytes(r[8..12].try_into().unwrap()) as usize;
            pool[offset..offset + length].to_vec()
        })
        .collect()
}

#[test]
fn the_path_2_unicode16_path_is_not_nfc() {
    let name = "core/invalid/PATH-2-unicode16.chst";
    let paths = raw_paths(name);
    let not_nfc: Vec<&str> = paths
        .iter()
        .map(|p| std::str::from_utf8(p).unwrap())
        .filter(|p| !is_nfc(p))
        .collect();
    // Exactly the fixture's added path: `x` U+0301 U+113CE, which is NFC under 15.x only.
    assert_eq!(not_nfc, ["docs/x\u{301}\u{113CE}"]);

    // The reader rejects the file at that path, as PATH-2, in every purpose.
    let limits = Limits::default();
    for purpose in [
        Purpose::List,
        Purpose::Inspect,
        Purpose::Verify,
        Purpose::Extract,
    ] {
        let opened = open(&mut File::open(fixture(name)).unwrap(), &limits).unwrap();
        let sections = opened.sections(&limits).unwrap();
        let e = opened.tables(&sections, &limits, purpose).unwrap_err();
        assert_eq!(
            (e.category(), e.detail()),
            (Category::Malformed, "path.nfc"),
            "{e}"
        );
    }
}
