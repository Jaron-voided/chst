//! The `chst` command-line tool.

#![forbid(unsafe_code)]

use std::process::ExitCode;

fn main() -> ExitCode {
    // No command exists yet. Exit 70 (`internal`), a code no check expects, so that a check
    // can't pass because the stub happens to exit the way the check wants.
    eprintln!("chst: not implemented yet");
    ExitCode::from(70)
}
