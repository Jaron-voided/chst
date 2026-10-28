//! The `chst` command-line tool (FORMAT_SPEC Appendix C).
//!
//! It parses the command line, calls `chst-format`, and renders the result. It holds no
//! format or safety logic (DESIGN D13).

#![forbid(unsafe_code)]

mod args;
mod render;

use std::ffi::OsString;
use std::fs::File;
use std::io::Write;
use std::process::ExitCode;

use args::{Command, Invocation, parse};
use chst_format::{Category, Error};

/// The output could not be written (FORMAT_SPEC §16, `io`).
const IO_WRITE: &str = "io.write";

/// What a run prints on stdout, or the error that ends it.
type Outcome = Result<String, Error>;

fn main() -> ExitCode {
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();
    let (command, json, outcome) = match parse(args) {
        Ok(inv) => (Some(inv.command), inv.json, run(&inv)),
        Err(e) => (e.command, e.json, Err(e.error)),
    };
    let (stdout, error) = match outcome {
        Ok(out) => (out, None),
        // On failure, a JSON report is printed only when the command is known (Appendix B's
        // `command` field needs it).
        Err(e) => {
            let out = match (json, command) {
                (true, Some(c)) => line(&render::failure_json(c.as_str(), &e)),
                _ => String::new(),
            };
            (out, Some(e))
        }
    };
    let mut io = std::io::stdout().lock();
    let written = io.write_all(stdout.as_bytes()).and_then(|()| io.flush());
    let error = match (error, written) {
        (Some(e), _) => Some(e),
        (None, Ok(())) => None,
        (None, Err(w)) => Some(Error::new(
            Category::Io,
            IO_WRITE,
            format!("cannot write the output: {w}"),
        )),
    };
    match error {
        None => ExitCode::SUCCESS,
        Some(e) => {
            // If even stderr can't be written, the exit code still says what happened.
            let _ = writeln!(std::io::stderr().lock(), "chst: {e}");
            ExitCode::from(e.exit_code())
        }
    }
}

/// A JSON value on one line.
fn line(v: &serde_json::Value) -> String {
    format!("{v}\n")
}

fn run(inv: &Invocation) -> Outcome {
    let mut file = File::open(&inv.file).map_err(|e| {
        Error::new(
            Category::Io,
            chst_format::error::detail::IO_READ,
            format!("cannot open {}: {e}", inv.file.display()),
        )
    })?;
    match inv.command {
        Command::Verify => {
            let report = chst_format::verify(&mut file, &inv.limits)?;
            Ok(if inv.json {
                line(&render::verify_json(&report.summary))
            } else {
                render::verify_text(&report.summary)
            })
        }
        // The parser lets through only the commands that are implemented.
        other => Err(Error::new(
            Category::Internal,
            args::NOT_IMPLEMENTED,
            format!("{} is not implemented yet", other.as_str()),
        )),
    }
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use chst_format::Limits;

    use super::*;

    fn worked_example() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../fixtures/core/valid/worked-example/container.chst")
    }

    fn verify(json: bool, limits: Limits) -> Outcome {
        run(&Invocation {
            command: Command::Verify,
            file: worked_example(),
            json,
            limits,
        })
    }

    #[test]
    fn verify_prints_json_only_when_asked() {
        let out = verify(true, Limits::default()).unwrap();
        assert!(out.ends_with("}\n") && out.lines().count() == 1, "{out}");
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert_eq!(v["ok"], true);
        assert_eq!(v["summary"]["entries"], 5);
        let text = verify(false, Limits::default()).unwrap();
        assert!(text.starts_with("ok: 5 entries"), "{text}");
    }

    #[test]
    fn verify_uses_the_given_limits() {
        let e = verify(
            false,
            Limits {
                max_entries: 4,
                ..Limits::default()
            },
        )
        .unwrap_err();
        assert_eq!((e.category(), e.exit_code()), (Category::LimitExceeded, 8));
    }

    #[test]
    fn a_file_that_cannot_be_opened_is_io_read() {
        let e = run(&Invocation {
            command: Command::Verify,
            file: worked_example().with_file_name("no-such-file"),
            json: false,
            limits: Limits::default(),
        })
        .unwrap_err();
        assert_eq!((e.category(), e.detail()), (Category::Io, "io.read"));
    }
}
