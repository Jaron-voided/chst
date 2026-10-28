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
    pub const LIM_INDEX_SIZE: &str = "lim.index-size";
    pub const LIMIT_ENTRIES: &str = "limit.entries";
    pub const LIMIT_INDEX_SIZE: &str = "limit.index-size";
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
