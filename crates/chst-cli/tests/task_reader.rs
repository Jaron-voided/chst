//! Development evidence for the reader tasks (TODO.md, "Task-evidence tests").
//!
//! This is not conformance evidence. Conformance is decided only by the CLI fixture
//! comparisons in ACCEPTANCE.md.
//!
//! `reader_step_N` runs the reader through §13 step N on every fixture that has an expected
//! result, plus the valid fixtures, and checks that each file is rejected with exactly its
//! expected detail if its first violation is at a step of N or lower, and passes otherwise.

#![forbid(unsafe_code)]

use std::fs::File;
use std::path::{Path, PathBuf};

use chst_format::{Error, Limits};
use serde_json::Value;

/// Directories whose `*.expect.json` files make up the fixture set (TODO.md).
const EXPECT_DIRS: [&str; 6] = [
    "core/invalid",
    "core/hostile",
    "core/hostile64",
    "core/attacks",
    "core/extract-cases",
    "compat",
];

/// Every `*.expect.json` file in `EXPECT_DIRS`, and every `core/valid/*/container.chst`.
const EXPECT_FILES: usize = 118;
const VALID_FILES: usize = 10;

/// The number of files whose first violation is at step N or lower (TODO.md).
const REJECTED_THROUGH: [(u8, usize); 2] = [(8, 19), (9, 32)];

struct Case {
    label: String,
    path: PathBuf,
    /// `None` for the valid fixtures.
    expect: Option<Expect>,
    limits: Limits,
}

struct Expect {
    rule: Option<String>,
    category: Option<String>,
    detail: Option<String>,
    exit: u8,
}

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../fixtures")
}

fn str_field(v: &Value, key: &str) -> Option<String> {
    v.get(key).and_then(Value::as_str).map(str::to_owned)
}

/// The limits named by an `args` array such as `["--max-entries", "4"]`.
fn limits_from(args: &Value, label: &str) -> Limits {
    let mut limits = Limits::default();
    let Some(args) = args.as_array() else {
        return limits;
    };
    let mut it = args
        .iter()
        .map(|a| a.as_str().unwrap_or_else(|| panic!("{label}: bad args")));
    while let Some(flag) = it.next() {
        let value: u64 = it
            .next()
            .unwrap_or_else(|| panic!("{label}: {flag} has no value"))
            .parse()
            .unwrap_or_else(|_| panic!("{label}: {flag} is not a number"));
        match flag {
            "--max-entries" => limits.max_entries = value,
            "--max-index-bytes" => limits.max_index_bytes = value,
            "--max-total-bytes" => limits.max_total_bytes = value,
            "--max-ratio" => limits.max_ratio = value,
            other => panic!("{label}: unknown flag {other}"),
        }
    }
    limits
}

/// The input of an expectation file: the `.chst` beside it, or for the sparse LIM-2 recipe
/// the file named by `$CHST_LIM2`, which the Verify line creates with `fixture_file`.
fn input_of(expect_path: &Path, label: &str) -> PathBuf {
    let name = expect_path.file_name().unwrap().to_str().unwrap();
    let stem = name.strip_suffix(".expect.json").unwrap();
    let chst = expect_path.with_file_name(format!("{stem}.chst"));
    if chst.is_file() {
        return chst;
    }
    if expect_path
        .with_file_name(format!("{stem}.recipe.json"))
        .is_file()
    {
        let lim2 = std::env::var_os("CHST_LIM2")
            .unwrap_or_else(|| panic!("{label} is a sparse recipe and $CHST_LIM2 is not set"));
        let lim2 = PathBuf::from(lim2);
        assert!(
            lim2.is_file(),
            "{label}: $CHST_LIM2 ({}) is not a file",
            lim2.display()
        );
        return lim2;
    }
    panic!("{label}: no .chst or .recipe.json beside the expectation");
}

fn load_cases() -> Vec<Case> {
    let root = fixtures();
    let mut cases = Vec::new();
    for dir in EXPECT_DIRS {
        let mut paths: Vec<PathBuf> = std::fs::read_dir(root.join(dir))
            .unwrap_or_else(|e| panic!("{dir}: {e}"))
            .map(|e| e.unwrap().path())
            .filter(|p| p.to_str().is_some_and(|s| s.ends_with(".expect.json")))
            .collect();
        paths.sort();
        for path in paths {
            let label = format!(
                "{dir}/{}",
                path.file_name()
                    .unwrap()
                    .to_str()
                    .unwrap()
                    .trim_end_matches(".expect.json")
            );
            let v: Value = serde_json::from_slice(&std::fs::read(&path).unwrap())
                .unwrap_or_else(|e| panic!("{label}: {e}"));
            let exit = v
                .get("exit")
                .and_then(Value::as_u64)
                .unwrap_or_else(|| panic!("{label}: no exit"));
            let expect = Expect {
                rule: str_field(&v, "rule"),
                category: str_field(&v, "category"),
                detail: str_field(&v, "detail"),
                exit: u8::try_from(exit).unwrap_or_else(|_| panic!("{label}: exit {exit}")),
            };
            cases.push(Case {
                limits: limits_from(v.get("args").unwrap_or(&Value::Null), &label),
                path: input_of(&path, &label),
                label,
                expect: Some(expect),
            });
        }
    }
    let mut valid: Vec<PathBuf> = std::fs::read_dir(root.join("core/valid"))
        .unwrap()
        .map(|e| e.unwrap().path().join("container.chst"))
        .collect();
    valid.sort();
    for path in valid {
        assert!(path.is_file(), "{} is missing", path.display());
        let label = format!(
            "core/valid/{}",
            path.parent()
                .unwrap()
                .file_name()
                .unwrap()
                .to_str()
                .unwrap()
        );
        cases.push(Case {
            label,
            path,
            expect: None,
            limits: Limits::default(),
        });
    }
    cases
}

/// The §13 step of the first violation named by a rule ID.
fn step_of_rule(rule: &str) -> Option<u8> {
    Some(match rule {
        "HDR-1" => 1,
        "HDR-2" => 2,
        "HDR-3" => 3,
        "HDR-4" => 4,
        "TRL-1" => 5,
        "TRL-2" | "LIM-2" | "LIM-4" => 6,
        "TRL-3" => 7,
        "HDR-6" | "HDR-5" => 8,
        "SEC-1" | "SEC-2" | "SEC-3" | "SEC-4" | "SEC-5" | "LIM-3" => 9,
        "BLB-6" => 11,
        r if [
            "BLB-", "ENT-", "PATH-", "CAN-", "FLG-", "ATT-", "KV-", "ZST-",
        ]
        .iter()
        .any(|p| r.starts_with(p))
            || ["LIM-5", "LIM-6"].contains(&r) =>
        {
            10
        }
        _ => return None,
    })
}

/// The step of a file's first violation, or `None` if it has none.
fn first_violation_step(case: &Case) -> Option<u8> {
    let expect = case.expect.as_ref()?;
    if expect.exit == 0 {
        return None;
    }
    if let Some(rule) = &expect.rule {
        return Some(
            step_of_rule(rule).unwrap_or_else(|| panic!("{}: unknown rule {rule}", case.label)),
        );
    }
    // The compat fixtures name a detail code, not a rule.
    let detail = expect
        .detail
        .as_deref()
        .unwrap_or_else(|| panic!("{}: neither a rule nor a detail", case.label));
    if detail.starts_with("hdr.") {
        Some(8)
    } else if detail == "sec.unknown-critical" {
        Some(9)
    } else {
        panic!("{}: cannot classify detail {detail}", case.label)
    }
}

/// Checks one rejection against the expectation; returns a description of any mismatch.
fn compare(case: &Case, err: &Error) -> Option<String> {
    let expect = case.expect.as_ref()?;
    let mut bad = Vec::new();
    if Some(err.detail()) != expect.detail.as_deref() {
        bad.push(format!(
            "detail {} (wanted {:?})",
            err.detail(),
            expect.detail
        ));
    }
    if err.exit_code() != expect.exit {
        bad.push(format!("exit {} (wanted {})", err.exit_code(), expect.exit));
    }
    if let Some(cat) = &expect.category
        && err.category().as_str() != cat
    {
        bad.push(format!(
            "category {} (wanted {cat})",
            err.category().as_str()
        ));
    }
    (!bad.is_empty()).then(|| format!("{}: {}", case.label, bad.join(", ")))
}

fn reader_through_step_8(file: &mut File, limits: &Limits) -> Result<(), Error> {
    chst_format::open(file, limits).map(|_| ())
}

fn reader_through_step_9(file: &mut File, limits: &Limits) -> Result<(), Error> {
    chst_format::open(file, limits)?
        .sections(limits)
        .map(|_| ())
}

fn run_step(n: u8, reader: fn(&mut File, &Limits) -> Result<(), Error>) {
    let cases = load_cases();
    assert_eq!(
        cases.len(),
        EXPECT_FILES + VALID_FILES,
        "the fixture set changed"
    );
    let wanted_rejected = REJECTED_THROUGH
        .iter()
        .find(|(step, _)| *step == n)
        .unwrap_or_else(|| panic!("no running total for step {n}"))
        .1;

    let mut rejected = 0;
    let mut failures = Vec::new();
    for case in &cases {
        let should_reject = first_violation_step(case).is_some_and(|s| s <= n);
        let mut file = File::open(&case.path).unwrap_or_else(|e| panic!("{}: {e}", case.label));
        match (reader(&mut file, &case.limits), should_reject) {
            (Err(err), true) => {
                rejected += 1;
                failures.extend(compare(case, &err));
            }
            (Ok(()), false) => {}
            (Ok(()), true) => {
                failures.push(format!("{}: accepted, but it must be rejected", case.label))
            }
            (Err(err), false) => failures.push(format!(
                "{}: rejected but should pass steps 1 to {n}: {err}",
                case.label
            )),
        }
    }
    assert!(
        failures.is_empty(),
        "{} mismatches:\n{}",
        failures.len(),
        failures.join("\n")
    );
    assert_eq!(rejected, wanted_rejected, "files rejected through step {n}");
}

#[test]
fn reader_step_8() {
    run_step(8, reader_through_step_8);
}

#[test]
fn reader_step_9() {
    run_step(9, reader_through_step_9);
}
