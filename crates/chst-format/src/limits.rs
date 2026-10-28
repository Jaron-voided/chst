//! The configurable limits of FORMAT_SPEC §10.2.

/// Default for LIM-3, the number of entries.
pub const DEFAULT_MAX_ENTRIES: u64 = 1_048_576;
/// Default for LIM-4, `index_length` (256 MiB).
pub const DEFAULT_MAX_INDEX_BYTES: u64 = 268_435_456;
/// Default for LIM-5, the total logical size (64 GiB).
pub const DEFAULT_MAX_TOTAL_BYTES: u64 = 68_719_476_736;
/// Default for LIM-6, the compression ratio of an encoded blob.
pub const DEFAULT_MAX_RATIO: u64 = 1000;

/// The four configurable limits. A violation is `limit-exceeded`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Limits {
    /// LIM-3
    pub max_entries: u64,
    /// LIM-4
    pub max_index_bytes: u64,
    /// LIM-5
    pub max_total_bytes: u64,
    /// LIM-6
    pub max_ratio: u64,
}

impl Default for Limits {
    fn default() -> Self {
        Limits {
            max_entries: DEFAULT_MAX_ENTRIES,
            max_index_bytes: DEFAULT_MAX_INDEX_BYTES,
            max_total_bytes: DEFAULT_MAX_TOTAL_BYTES,
            max_ratio: DEFAULT_MAX_RATIO,
        }
    }
}
