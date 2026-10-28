//! Pack and extract: directory walking, staging and the platform-specific safety code.

#![deny(unsafe_code)]
#![deny(clippy::undocumented_unsafe_blocks, clippy::missing_safety_doc)]

#[cfg(windows)]
#[allow(unsafe_code)]
mod windows;
