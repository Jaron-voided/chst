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

use chst_format::report::{
    Field, FieldValue, InspectReport, ListKind, Record, Region, SectionReport, Summary,
};
use chst_format::{Error, Limits, Purpose};
use serde_json::{Value, json};

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
const REJECTED_THROUGH: [(u8, usize); 4] = [(8, 19), (9, 32), (10, 108), (11, 110)];

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

/// Verify mode, so LIM-5 is evaluated (TODO.md, C-4).
fn reader_through_step_10(file: &mut File, limits: &Limits) -> Result<(), Error> {
    let opened = chst_format::open(file, limits)?;
    let sections = opened.sections(limits)?;
    opened
        .tables(&sections, limits, Purpose::Verify)
        .map(|_| ())
}

/// All eleven steps: what verify runs.
fn reader_through_step_11(file: &mut File, limits: &Limits) -> Result<(), Error> {
    chst_format::verify(file, limits).map(|_| ())
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

#[test]
fn reader_step_10() {
    run_step(10, reader_through_step_10);
}

#[test]
fn reader_step_11() {
    run_step(11, reader_through_step_11);
}

// The `reports` test renders the library's report values by Appendix B's encoding rules and
// compares them with the fixtures' expected reports. Only `message` fields would be excluded,
// and the compared parts have none.

/// An integer as Appendix B encodes it: a number within ±(2^53 − 1), a decimal string beyond.
fn int(n: u128) -> Value {
    const MAX_SAFE: u128 = (1 << 53) - 1;
    if n <= MAX_SAFE {
        json!(n as u64)
    } else {
        json!(n.to_string())
    }
}

fn hex(bytes: &[u8]) -> Value {
    Value::String(bytes.iter().map(|b| format!("{b:02x}")).collect())
}

fn field_json(f: &Field) -> Value {
    let mut v =
        json!({"name": f.name, "offset": int(f.offset.into()), "length": int(f.length.into())});
    if let Some(value) = &f.value {
        v["value"] = match value {
            FieldValue::Int(n) => int((*n).into()),
            FieldValue::Hex(b) => hex(b),
            FieldValue::Text(t) => json!(t),
        };
    }
    v
}

fn fields_json(fields: &[Field]) -> Value {
    Value::Array(fields.iter().map(field_json).collect())
}

fn region_json(r: &Region) -> Value {
    json!({"offset": int(r.offset.into()), "length": int(r.length.into()), "fields": fields_json(&r.fields)})
}

fn record_json(r: &Record) -> Value {
    json!({
        "index": int(r.index.into()),
        "offset": int(r.offset.into()),
        "length": int(r.length.into()),
        "fields": fields_json(&r.fields),
    })
}

fn section_json(s: &SectionReport) -> Value {
    json!({
        "type": format!("{:#010x}", s.ty),
        "name": s.name,
        "offset": int(s.offset.into()),
        "length": int(s.length.into()),
        "record_size": int(s.record_size.into()),
        "record_count": int(s.record_count.into()),
        "fields": fields_json(&s.fields),
        "records": s.records.iter().map(record_json).collect::<Vec<_>>(),
    })
}

fn inspect_json(r: &InspectReport) -> Value {
    json!({
        "file_length": int(r.file_length.into()),
        "header": region_json(&r.header),
        "data": region_json(&r.data),
        "sections": r.sections.iter().map(section_json).collect::<Vec<_>>(),
        "trailer": region_json(&r.trailer),
    })
}

fn summary_json(s: &Summary) -> Value {
    json!({
        "entries": int(s.entries.into()),
        "files": int(s.files.into()),
        "directories": int(s.directories.into()),
        "blobs": int(s.blobs.into()),
        "stored_bytes": int(s.stored_bytes),
        "raw_bytes": int(s.raw_bytes),
        "extracted_bytes": int(s.extracted_bytes),
        "required_flags": s.required_flags,
        "optional_flags": s.optional_flags,
    })
}

fn list_json(r: &chst_format::ListReport) -> Value {
    Value::Array(
        r.entries()
            .map(|e| match e.kind {
                ListKind::Directory => json!({"path": e.path, "type": "dir"}),
                ListKind::File {
                    size,
                    stored_size,
                    encoding,
                    blob,
                } => json!({
                    "path": e.path,
                    "type": "file",
                    "size": int(size.into()),
                    "stored_size": int(stored_size.into()),
                    "encoding": encoding.as_str(),
                    "blob": hex(&blob),
                }),
            })
            .collect(),
    )
}

fn read_json(path: &Path) -> Value {
    serde_json::from_slice(
        &std::fs::read(path).unwrap_or_else(|e| panic!("{}: {e}", path.display())),
    )
    .unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

/// Each container with expected reports, and the paths of its list, verify and inspect JSON.
fn report_cases() -> Vec<(String, PathBuf, [PathBuf; 3])> {
    let root = fixtures();
    let mut out = Vec::new();
    let mut valid: Vec<PathBuf> = std::fs::read_dir(root.join("core/valid"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    valid.sort();
    for d in valid {
        let name = d.file_name().unwrap().to_str().unwrap().to_owned();
        out.push((
            format!("core/valid/{name}"),
            d.join("container.chst"),
            ["list.json", "verify.json", "inspect.json"].map(|f| d.join(f)),
        ));
    }
    let mut compat: Vec<PathBuf> = std::fs::read_dir(root.join("compat"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.to_str().is_some_and(|s| s.ends_with(".list.json")))
        .collect();
    compat.sort();
    for list in compat {
        let stem = list
            .file_name()
            .unwrap()
            .to_str()
            .unwrap()
            .trim_end_matches(".list.json")
            .to_owned();
        let exit = read_json(&list.with_file_name(format!("{stem}.expect.json")))["exit"].as_u64();
        assert_eq!(
            exit,
            Some(0),
            "compat/{stem} has a list.json but doesn't exit 0"
        );
        out.push((
            format!("compat/{stem}"),
            list.with_file_name(format!("{stem}.chst")),
            ["list", "verify", "inspect"].map(|c| list.with_file_name(format!("{stem}.{c}.json"))),
        ));
    }
    out
}

#[test]
fn reports() {
    let limits = Limits::default();
    let cases = report_cases();
    assert_eq!(
        cases.len(),
        16,
        "10 core/valid and 6 exit-0 compat fixtures"
    );
    let mut failures = Vec::new();
    for (label, chst, [list, verify, inspect]) in &cases {
        let open = || File::open(chst).unwrap_or_else(|e| panic!("{label}: {e}"));
        match chst_format::list(&mut open(), &limits) {
            Ok(r) if list_json(&r) == read_json(list)["entries"] => {}
            Ok(_) => failures.push(format!("{label}: list entries differ from list.json")),
            Err(e) => failures.push(format!("{label}: list failed: {e}")),
        }
        match chst_format::verify(&mut open(), &limits) {
            Ok(r) if summary_json(&r.summary) == read_json(verify)["summary"] => {}
            Ok(r) => failures.push(format!(
                "{label}: verify summary {} differs from verify.json",
                summary_json(&r.summary)
            )),
            Err(e) => failures.push(format!("{label}: verify failed: {e}")),
        }
        // Beyond what TODO.md lists for C-5: the inspect report against inspect.json.
        match chst_format::inspect(&mut open(), &limits) {
            Ok(r) => {
                let want = read_json(inspect);
                let got = inspect_json(&r);
                for key in ["file_length", "header", "data", "sections", "trailer"] {
                    if got[key] != want[key] {
                        failures.push(format!("{label}: inspect {key} differs from inspect.json"));
                    }
                }
            }
            Err(e) => failures.push(format!("{label}: inspect failed: {e}")),
        }
    }

    // F34: list and inspect stop after step 10, so they succeed on a file whose only fault is
    // a blob's data; verify reports it.
    let blb6 = fixtures().join("core/invalid/BLB-6.chst");
    let open = || File::open(&blb6).unwrap();
    if let Err(e) = chst_format::list(&mut open(), &limits) {
        failures.push(format!("core/invalid/BLB-6: list failed: {e}"));
    }
    if let Err(e) = chst_format::inspect(&mut open(), &limits) {
        failures.push(format!("core/invalid/BLB-6: inspect failed: {e}"));
    }
    match chst_format::verify(&mut open(), &limits) {
        Err(e) if e.detail() == "blob.hash" && e.exit_code() == 7 => {}
        Err(e) => failures.push(format!("core/invalid/BLB-6: verify gave {e}")),
        Ok(_) => failures.push("core/invalid/BLB-6: verify accepted it".to_owned()),
    }
    assert!(
        failures.is_empty(),
        "{} mismatches:\n{}",
        failures.len(),
        failures.join("\n")
    );
}
