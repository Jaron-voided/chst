//! Command-line parsing (FORMAT_SPEC Appendix C), with `lexopt`.
//!
//! Any problem with the command line is `usage` (exit 2), and nothing is opened or read.

use std::ffi::OsString;
use std::path::PathBuf;

use chst_format::{Category, Error, Limits};
use lexopt::{Arg, Parser, ValueExt};

/// A limit flag's value isn't a decimal integer from 0 to 2^64 − 1 in canonical form (M12).
pub const USAGE_LIMIT: &str = "usage.limit";
/// The command is missing or unknown.
pub const USAGE_COMMAND: &str = "usage.command";
/// An option the command doesn't take, or a value given to an option that takes none.
pub const USAGE_OPTION: &str = "usage.option";
/// FILE is missing, or there are more operands than the command takes.
pub const USAGE_ARGUMENT: &str = "usage.argument";

/// A command that exists in Appendix C but not yet in this tool.
pub const NOT_IMPLEMENTED: &str = "internal.not-implemented";

/// The commands of Appendix C.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Command {
    Pack,
    List,
    Verify,
    Inspect,
    Extract,
}

impl Command {
    fn from_name(name: &str) -> Option<Command> {
        Some(match name {
            "pack" => Command::Pack,
            "list" => Command::List,
            "verify" => Command::Verify,
            "inspect" => Command::Inspect,
            "extract" => Command::Extract,
            _ => return None,
        })
    }

    /// The name used in reports (`command`).
    pub const fn as_str(self) -> &'static str {
        match self {
            Command::Pack => "pack",
            Command::List => "list",
            Command::Verify => "verify",
            Command::Inspect => "inspect",
            Command::Extract => "extract",
        }
    }
}

/// A parsed command line for a read command: `chst <command> FILE [--json] [limits]`.
#[derive(Debug, PartialEq, Eq)]
pub struct Invocation {
    pub command: Command,
    pub file: PathBuf,
    pub json: bool,
    pub limits: Limits,
}

/// A command line that can't be run, with what was known of it when that was found, so the
/// error can be reported in the form the user asked for.
#[derive(Debug)]
pub struct ParseError {
    pub command: Option<Command>,
    pub json: bool,
    pub error: Error,
}

fn usage(detail: &'static str, message: impl Into<String>) -> Error {
    Error::new(Category::Usage, detail, message)
}

/// A limit flag's value: ASCII digits only, with no sign, no whitespace and no leading zeros
/// (a lone `0` is allowed), from 0 to 2^64 − 1 (M12, N23).
pub fn parse_limit(flag: &str, value: &OsString) -> Result<u64, Error> {
    let bad = || {
        usage(
            USAGE_LIMIT,
            format!(
                "{flag} takes a decimal integer from 0 to 18446744073709551615, not {:?}",
                value.to_string_lossy()
            ),
        )
    };
    let text = value.to_str().ok_or_else(bad)?;
    let canonical = !text.is_empty()
        && text.bytes().all(|b| b.is_ascii_digit())
        && (text == "0" || !text.starts_with('0'));
    if !canonical {
        return Err(bad());
    }
    text.parse::<u64>().map_err(|_| bad())
}

/// Parses `args` (without the program name).
pub fn parse(args: Vec<OsString>) -> Result<Invocation, ParseError> {
    // Whether a failure is reported as JSON doesn't depend on where the error is: `--json`
    // anywhere among the options (before any `--`) asks for it.
    let json = args
        .iter()
        .skip(1)
        .take_while(|a| *a != "--")
        .any(|a| a == "--json");
    let mut state = ParseError {
        command: None,
        json,
        error: usage(USAGE_COMMAND, ""),
    };
    match parse_into(args, &mut state) {
        Ok(inv) => Ok(inv),
        Err(error) => Err(ParseError { error, ..state }),
    }
}

fn parse_into(args: Vec<OsString>, seen: &mut ParseError) -> Result<Invocation, Error> {
    let mut it = args.into_iter();
    let name = it.next().ok_or_else(|| {
        usage(
            USAGE_COMMAND,
            "no command given; the commands are pack, list, verify, inspect and extract",
        )
    })?;
    let command = name.to_str().and_then(Command::from_name).ok_or_else(|| {
        usage(
            USAGE_COMMAND,
            format!(
                "unknown command {:?}; the commands are pack, list, verify, inspect and extract",
                name.to_string_lossy()
            ),
        )
    })?;
    seen.command = Some(command);
    // Until their tasks implement them (C-6b, C-6c, C-9, C-14), the other commands fail as
    // the C-1 stub did: `internal`, exit 70, which no check expects.
    if command != Command::Verify {
        return Err(Error::new(
            Category::Internal,
            NOT_IMPLEMENTED,
            format!("{} is not implemented yet", command.as_str()),
        ));
    }

    let mut parser = Parser::from_args(it);
    let mut json = false;
    let mut file: Option<OsString> = None;
    let mut limits = Limits::default();
    loop {
        let arg = parser
            .next()
            .map_err(|e| usage(USAGE_OPTION, e.to_string()))?;
        let Some(arg) = arg else { break };
        match arg {
            Arg::Long("json") => json = true,
            Arg::Long(
                flag @ ("max-entries" | "max-index-bytes" | "max-total-bytes" | "max-ratio"),
            ) => {
                let flag = format!("--{flag}");
                let value = parser
                    .value()
                    .map_err(|_| usage(USAGE_LIMIT, format!("{flag} needs a value")))?;
                let n = parse_limit(&flag, &value)?;
                match flag.as_str() {
                    "--max-entries" => limits.max_entries = n,
                    "--max-index-bytes" => limits.max_index_bytes = n,
                    "--max-total-bytes" => limits.max_total_bytes = n,
                    _ => limits.max_ratio = n,
                }
            }
            Arg::Value(v) if file.is_none() => file = Some(v),
            Arg::Value(v) => {
                return Err(usage(
                    USAGE_ARGUMENT,
                    format!(
                        "{} takes one FILE; {:?} is one too many",
                        command.as_str(),
                        v.string().unwrap_or_else(|_| "?".to_owned())
                    ),
                ));
            }
            other => {
                return Err(usage(
                    USAGE_OPTION,
                    format!(
                        "{} doesn't take the option {}",
                        command.as_str(),
                        other.unexpected()
                    ),
                ));
            }
        }
    }
    let file =
        file.ok_or_else(|| usage(USAGE_ARGUMENT, format!("{} needs a FILE", command.as_str())))?;
    Ok(Invocation {
        command,
        file: PathBuf::from(file),
        json,
        limits,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(a: &[&str]) -> Vec<OsString> {
        a.iter().map(OsString::from).collect()
    }

    fn ok(a: &[&str]) -> Invocation {
        parse(args(a)).unwrap()
    }

    fn fails(a: &[&str], category: Category, detail: &str) -> ParseError {
        let e = parse(args(a)).unwrap_err();
        assert_eq!(
            (e.error.category(), e.error.detail()),
            (category, detail),
            "{a:?}: {}",
            e.error
        );
        e
    }

    #[test]
    fn a_verify_command_line() {
        let inv = ok(&["verify", "f.chst"]);
        assert_eq!(
            inv,
            Invocation {
                command: Command::Verify,
                file: PathBuf::from("f.chst"),
                json: false,
                limits: Limits::default(),
            }
        );
        let inv = ok(&[
            "verify",
            "--max-entries",
            "1",
            "--json",
            "f",
            "--max-index-bytes",
            "2",
            "--max-total-bytes=3",
            "--max-ratio",
            "4",
        ]);
        assert!(inv.json);
        assert_eq!(
            inv.limits,
            Limits {
                max_entries: 1,
                max_index_bytes: 2,
                max_total_bytes: 3,
                max_ratio: 4,
            }
        );
        // After `--`, everything is an operand.
        assert_eq!(
            ok(&["verify", "--", "--json"]).file,
            PathBuf::from("--json")
        );
        assert!(!ok(&["verify", "--", "--json"]).json);
    }

    #[test]
    fn limit_values_are_canonical_decimal_integers() {
        for (v, want) in [
            ("0", 0),
            ("1", 1),
            ("10", 10),
            ("18446744073709551615", u64::MAX),
        ] {
            assert_eq!(
                parse_limit("--max-entries", &OsString::from(v)).unwrap(),
                want
            );
        }
        for v in [
            "",
            "-1",
            "+5",
            "05",
            "00",
            " 5",
            "5 ",
            "0x5",
            "5.0",
            "1e3",
            "18446744073709551616",
            "99999999999999999999",
            "\u{663}",
        ] {
            let e = parse_limit("--max-entries", &OsString::from(v)).unwrap_err();
            assert_eq!(
                (e.category(), e.detail()),
                (Category::Usage, USAGE_LIMIT),
                "{v:?}"
            );
        }
        for flag in [
            "--max-entries",
            "--max-index-bytes",
            "--max-total-bytes",
            "--max-ratio",
        ] {
            fails(&["verify", flag, "05", "f"], Category::Usage, USAGE_LIMIT);
            fails(&["verify", "f", flag], Category::Usage, USAGE_LIMIT);
        }
    }

    #[test]
    fn usage_errors() {
        let e = fails(&[], Category::Usage, USAGE_COMMAND);
        assert_eq!(e.command, None);
        fails(&["frobnicate", "f"], Category::Usage, USAGE_COMMAND);
        fails(&["--json"], Category::Usage, USAGE_COMMAND);
        fails(&["Verify", "f"], Category::Usage, USAGE_COMMAND);
        let e = fails(&["verify"], Category::Usage, USAGE_ARGUMENT);
        assert_eq!(e.command, Some(Command::Verify));
        fails(&["verify", "a", "b"], Category::Usage, USAGE_ARGUMENT);
        fails(&["verify", "--bogus", "f"], Category::Usage, USAGE_OPTION);
        fails(&["verify", "-x", "f"], Category::Usage, USAGE_OPTION);
        fails(
            &["verify", "--json=yes", "f"],
            Category::Usage,
            USAGE_OPTION,
        );
    }

    #[test]
    fn json_is_known_even_when_the_error_comes_first() {
        let e = fails(
            &["verify", "--max-entries", "x", "--json", "f"],
            Category::Usage,
            USAGE_LIMIT,
        );
        assert!(e.json);
        let e = fails(
            &["verify", "--max-entries", "x", "f"],
            Category::Usage,
            USAGE_LIMIT,
        );
        assert!(!e.json);
        let e = fails(
            &["verify", "--", "--json", "a"],
            Category::Usage,
            USAGE_ARGUMENT,
        );
        assert!(!e.json);
    }

    #[test]
    fn commands_not_implemented_yet_are_internal() {
        for c in ["pack", "list", "inspect", "extract"] {
            let e = fails(&[c, "f"], Category::Internal, NOT_IMPLEMENTED);
            assert_eq!(e.command.map(Command::as_str), Some(c));
        }
    }
}
