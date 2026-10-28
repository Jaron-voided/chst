//! Encoding, decoding and validation of the chst container format.
//!
//! This crate never touches the filesystem (DESIGN D13).

#![forbid(unsafe_code)]

pub mod blobs;
pub mod error;
pub mod format;
pub mod limits;
pub mod paths;
pub mod reader;
pub mod report;
pub mod sections;
pub mod tables;

pub use blobs::check_blobs;
pub use error::{Category, Error};
pub use limits::Limits;
pub use reader::{Opened, open};
pub use report::{InspectReport, ListReport, VerifyReport, inspect, list, verify};
pub use sections::{SectionHeader, Sections, Table, parse_sections, section_headers};
pub use tables::{Blob, Entry, EntryKind, Purpose, Tables, parse_tables};
