//! Rendering reports as `chst-report/1` JSON (FORMAT_SPEC Appendix B) and as text.
//!
//! Every JSON report goes through `serde_json::Value` (DESIGN D15), so strings from the
//! container are escaped by a well-tested library.

use chst_format::Error;
use chst_format::report::Summary;
use serde_json::{Map, Value, json};

/// The largest integer a JSON number carries exactly; larger ones are decimal strings.
const MAX_SAFE_INTEGER: u128 = (1 << 53) - 1;

/// An integer as Appendix B encodes it.
pub fn int(n: impl Into<u128>) -> Value {
    let n = n.into();
    match u64::try_from(n) {
        Ok(small) if n <= MAX_SAFE_INTEGER => Value::from(small),
        _ => Value::String(n.to_string()),
    }
}

/// The common fields of every report (Appendix B). `error` is `None` on success.
fn envelope(command: &str, error: Option<&Error>) -> Map<String, Value> {
    let mut m = Map::new();
    m.insert("schema".into(), json!("chst-report/1"));
    m.insert("command".into(), json!(command));
    m.insert("ok".into(), json!(error.is_none()));
    m.insert(
        "error".into(),
        error.map_or(Value::Null, |e| {
            json!({
                "category": e.category().as_str(),
                "detail": e.detail(),
                "message": e.message(),
            })
        }),
    );
    m.insert("warnings".into(), json!([]));
    m
}

/// A failure report: only the common fields.
pub fn failure_json(command: &str, error: &Error) -> Value {
    Value::Object(envelope(command, Some(error)))
}

fn summary_json(s: &Summary) -> Value {
    json!({
        "entries": int(s.entries),
        "files": int(s.files),
        "directories": int(s.directories),
        "blobs": int(s.blobs),
        "stored_bytes": int(s.stored_bytes),
        "raw_bytes": int(s.raw_bytes),
        "extracted_bytes": int(s.extracted_bytes),
        "required_flags": s.required_flags,
        "optional_flags": s.optional_flags,
    })
}

/// A successful verify report.
pub fn verify_json(summary: &Summary) -> Value {
    let mut m = envelope("verify", None);
    m.insert("summary".into(), summary_json(summary));
    Value::Object(m)
}

/// A successful verify, as text.
pub fn verify_text(s: &Summary) -> String {
    let mut out = format!(
        "ok: {} entries ({} files, {} directories), {} blobs, {} stored bytes, {} bytes when extracted\n",
        s.entries, s.files, s.directories, s.blobs, s.stored_bytes, s.extracted_bytes
    );
    for (which, flags) in [
        ("required", &s.required_flags),
        ("optional", &s.optional_flags),
    ] {
        if !flags.is_empty() {
            out.push_str(&format!("{which} flags: {}\n", flags.join(", ")));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn integers_beyond_2_53_minus_1_are_strings() {
        assert_eq!(int(0u64), json!(0));
        assert_eq!(int(MAX_SAFE_INTEGER), json!(9007199254740991u64));
        assert_eq!(int(MAX_SAFE_INTEGER + 1), json!("9007199254740992"));
        assert_eq!(int(u64::MAX), json!("18446744073709551615"));
        assert_eq!(int(u128::MAX), json!(u128::MAX.to_string()));
    }

    fn summary() -> Summary {
        Summary {
            entries: 5,
            files: 3,
            directories: 2,
            blobs: 2,
            stored_bytes: 9,
            raw_bytes: 9,
            extracted_bytes: 15,
            required_flags: vec![],
            optional_flags: vec!["bit1".to_owned()],
        }
    }

    #[test]
    fn a_verify_report_has_the_common_fields_and_the_summary() {
        let v = verify_json(&summary());
        assert_eq!(
            v,
            json!({
                "schema": "chst-report/1",
                "command": "verify",
                "ok": true,
                "error": null,
                "warnings": [],
                "summary": {
                    "entries": 5, "files": 3, "directories": 2, "blobs": 2,
                    "stored_bytes": 9, "raw_bytes": 9, "extracted_bytes": 15,
                    "required_flags": [], "optional_flags": ["bit1"],
                },
            })
        );
    }

    #[test]
    fn a_failure_report_has_only_the_common_fields() {
        let e = Error::new(chst_format::Category::Integrity, "blob.hash", "bad");
        assert_eq!(
            failure_json("verify", &e),
            json!({
                "schema": "chst-report/1",
                "command": "verify",
                "ok": false,
                "error": {"category": "integrity", "detail": "blob.hash", "message": "bad"},
                "warnings": [],
            })
        );
    }

    #[test]
    fn verify_text_names_the_flags_that_are_set() {
        let t = verify_text(&summary());
        assert_eq!(
            t,
            "ok: 5 entries (3 files, 2 directories), 2 blobs, 9 stored bytes, 15 bytes when extracted\n\
             optional flags: bit1\n"
        );
    }
}
