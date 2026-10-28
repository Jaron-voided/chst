//! Encoding, decoding and validation of the chst container format.
//!
//! This crate never touches the filesystem (DESIGN D13).

#![forbid(unsafe_code)]

pub mod error;
pub mod format;
pub mod limits;
pub mod paths;
pub mod reader;
pub mod sections;
pub mod tables;

pub use error::{Category, Error};
pub use limits::Limits;
pub use reader::{Opened, open};
pub use sections::{Sections, Table, parse_sections};
pub use tables::{Blob, Entry, EntryKind, Purpose, Tables, parse_tables};
