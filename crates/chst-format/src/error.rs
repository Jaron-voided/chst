//! Error categories and detail codes (FORMAT_SPEC §16 and Appendix A).

use std::fmt;

/// The category of a failure, which fixes the CLI exit code (§16).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Category {
    Usage,
    Io,
    NotAContainer,
    Unsupported,
    Malformed,
    Integrity,
    LimitExceeded,
    Refused,
    Internal,
}

impl Category {
    /// The name used in `error[<category>/<detail>]` and in JSON reports.
    pub const fn as_str(self) -> &'static str {
        match self {
            Category::Usage => "usage",
            Category::Io => "io",
            Category::NotAContainer => "not-a-container",
            Category::Unsupported => "unsupported",
            Category::Malformed => "malformed",
            Category::Integrity => "integrity",
            Category::LimitExceeded => "limit-exceeded",
            Category::Refused => "refused",
            Category::Internal => "internal",
        }
    }

    /// The CLI exit code of this category.
    pub const fn exit_code(self) -> u8 {
        match self {
            Category::Usage => 2,
            Category::Io => 3,
            Category::NotAContainer => 4,
            Category::Unsupported => 5,
            Category::Malformed => 6,
            Category::Integrity => 7,
            Category::LimitExceeded => 8,
            Category::Refused => 9,
            Category::Internal => 70,
        }
    }
}

/// Detail codes, as listed in Appendix A.
pub mod detail {
    pub const HDR_TOO_SHORT: &str = "hdr.too-short";
    pub const HDR_MAGIC: &str = "hdr.magic";
    pub const HDR_MAJOR_VERSION: &str = "hdr.major-version";
    pub const HDR_HASH_ALG: &str = "hdr.hash-alg";
    pub const HDR_RESERVED: &str = "hdr.reserved";
    pub const HDR_REQUIRED_FLAG: &str = "hdr.required-flag";
    pub const TRL_MAGIC: &str = "trl.magic";
    pub const TRL_INDEX_RANGE: &str = "trl.index-range";
    pub const TRL_HASH: &str = "trl.hash";
    pub const SEC_BOUNDS: &str = "sec.bounds";
    pub const SEC_UNKNOWN_CRITICAL: &str = "sec.unknown-critical";
    pub const SEC_LAYOUT: &str = "sec.layout";
    pub const SEC_RECORD_SIZE_MIN: &str = "sec.record-size-min";
    pub const SEC_RECORD_SIZE: &str = "sec.record-size";
    pub const BLOB_RESERVED: &str = "blob.reserved";
    pub const BLOB_ENCODING: &str = "blob.encoding";
    pub const BLOB_RAW_LENGTH: &str = "blob.raw-length";
    pub const BLOB_LAYOUT: &str = "blob.layout";
    pub const BLOB_DUPLICATE_KEY: &str = "blob.duplicate-key";
    pub const BLOB_UNREFERENCED: &str = "blob.unreferenced";
    pub const ENTRY_TYPE: &str = "entry.type";
    pub const ENTRY_RESERVED: &str = "entry.reserved";
    pub const ENTRY_DIR_KEY: &str = "entry.dir-key";
    pub const ENTRY_DANGLING_KEY: &str = "entry.dangling-key";
    pub const ENTRY_PATH_RANGE: &str = "entry.path-range";
    pub const ENTRY_PARENT: &str = "entry.parent";
    pub const PATH_UTF8: &str = "path.utf8";
    pub const PATH_NFC: &str = "path.nfc";
    pub const PATH_LENGTH: &str = "path.length";
    pub const PATH_SLASH: &str = "path.slash";
    pub const PATH_DOT_SEGMENT: &str = "path.dot-segment";
    pub const PATH_CONTROL_CHAR: &str = "path.control-char";
    pub const PATH_FORBIDDEN_CHAR: &str = "path.forbidden-char";
    pub const PATH_TRAILING_DOT_SPACE: &str = "path.trailing-dot-space";
    pub const PATH_RESERVED_NAME: &str = "path.reserved-name";
    pub const PATH_DEPTH: &str = "path.depth";
    pub const PATH_CASE_COLLISION: &str = "path.case-collision";
    pub const CANON_ENTRY_ORDER: &str = "canon.entry-order";
    pub const CANON_BLOB_ORDER: &str = "canon.blob-order";
    pub const CANON_PATH_POOL: &str = "canon.path-pool";
    pub const LIM_INDEX_SIZE: &str = "lim.index-size";
    pub const LIMIT_ENTRIES: &str = "limit.entries";
    pub const LIMIT_INDEX_SIZE: &str = "limit.index-size";
    pub const LIMIT_TOTAL_SIZE: &str = "limit.total-size";
    /// The reader can't read or seek its input (FORMAT_SPEC Appendix A).
    pub const IO_READ: &str = "io.read";
    /// The reader can't allocate the memory it needs (FORMAT_SPEC Appendix A).
    pub const IO_MEMORY: &str = "io.memory";
}

/// A failure: one category, one detail code, and a message for people.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Error {
    category: Category,
    detail: &'static str,
    message: String,
}

impl Error {
    pub fn new(category: Category, detail: &'static str, message: impl Into<String>) -> Self {
        Error {
            category,
            detail,
            message: message.into(),
        }
    }

    /// A failure to read or seek the input.
    pub fn io(err: &std::io::Error) -> Self {
        Error::new(
            Category::Io,
            detail::IO_READ,
            format!("cannot read the input: {err}"),
        )
    }

    pub fn category(&self) -> Category {
        self.category
    }

    pub fn detail(&self) -> &'static str {
        self.detail
    }

    pub fn message(&self) -> &str {
        &self.message
    }

    pub fn exit_code(&self) -> u8 {
        self.category.exit_code()
    }
}

impl fmt::Display for Error {
    /// `error[<category>/<detail>]: <message>`, the CLI's error line without its `chst: `.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "error[{}/{}]: {}",
            self.category.as_str(),
            self.detail,
            self.message
        )
    }
}

impl std::error::Error for Error {}
