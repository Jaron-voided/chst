//! The path rules of FORMAT_SPEC §9 for one path: PATH-1 to PATH-10, in the order of §13
//! step 10 (g). PATH-11 compares paths with each other, so it's in `tables`.

use unicode_normalization::is_nfc;

use crate::error::{Category, Error, detail};

/// PATH-3: the longest path, in bytes.
pub const MAX_PATH_LEN: usize = 4096;
/// PATH-3: the longest segment, in bytes.
pub const MAX_SEGMENT_LEN: usize = 255;
/// PATH-10: the most segments a path may have.
pub const MAX_DEPTH: usize = 256;

/// A path's bytes for a message: escaped, so a hostile name can't change what is shown.
pub(crate) fn shown(path: &[u8]) -> String {
    match std::str::from_utf8(path) {
        Ok(s) => s.escape_default().to_string(),
        Err(_) => path.escape_ascii().to_string(),
    }
}

/// PATH-6: the control and directional-formatting code points.
fn is_control(c: char) -> bool {
    matches!(c,
        '\u{0}'..='\u{1F}' | '\u{7F}'..='\u{9F}'
        | '\u{61C}' | '\u{200E}' | '\u{200F}' | '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}')
}

/// PATH-7: the characters Windows can't hold in a name.
fn is_forbidden(c: char) -> bool {
    matches!(c, '\\' | '<' | '>' | ':' | '"' | '|' | '?' | '*')
}

/// PATH-9: whether a segment's stem is a Windows reserved device name. The stem is the part
/// before the first `.`, without trailing spaces, compared ASCII-case-insensitively.
fn is_reserved_name(segment: &str) -> bool {
    let stem = segment
        .split('.')
        .next()
        .unwrap_or(segment)
        .trim_end_matches(' ');
    if ["con", "prn", "aux", "nul", "conin$", "conout$"]
        .iter()
        .any(|name| stem.eq_ignore_ascii_case(name))
    {
        return true;
    }
    // COM and LPT followed by one digit, or by a superscript one, two or three.
    let (Some(head), Some(tail)) = (stem.get(..3), stem.get(3..)) else {
        return false;
    };
    let mut tail = tail.chars();
    (head.eq_ignore_ascii_case("com") || head.eq_ignore_ascii_case("lpt"))
        && matches!(
            (tail.next(), tail.next()),
            (Some('0'..='9' | '¹' | '²' | '³'), None)
        )
}

/// Checks PATH-1 to PATH-10 for the path of entry `entry`, and returns it as text.
pub fn check_path(entry: usize, path: &[u8]) -> Result<&str, Error> {
    let fail = |d: &'static str, what: &str| {
        Error::new(
            Category::Malformed,
            d,
            format!("entry {entry}, path \"{}\": {what}", shown(path)),
        )
    };

    // PATH-1
    let text = std::str::from_utf8(path).map_err(|_| fail(detail::PATH_UTF8, "not valid UTF-8"))?;
    // PATH-2, with exactly the Unicode 16.0 tables (D16)
    if !is_nfc(text) {
        return Err(fail(
            detail::PATH_NFC,
            "not in Unicode Normalization Form C",
        ));
    }
    // PATH-4, before PATH-3, so an empty segment is reported as this more specific rule.
    if text.starts_with('/') || text.ends_with('/') || text.contains("//") {
        return Err(fail(
            detail::PATH_SLASH,
            "begins or ends with '/', or has an empty segment",
        ));
    }
    // PATH-3. PATH-4 has ruled out empty segments in a non-empty path.
    if text.is_empty() || text.len() > MAX_PATH_LEN {
        return Err(fail(
            detail::PATH_LENGTH,
            &format!("{} bytes; a path is 1 to {MAX_PATH_LEN}", text.len()),
        ));
    }
    if text.split('/').any(|s| s.len() > MAX_SEGMENT_LEN) {
        return Err(fail(
            detail::PATH_LENGTH,
            &format!("a segment is longer than {MAX_SEGMENT_LEN} bytes"),
        ));
    }
    // PATH-5
    if text.split('/').any(|s| s == "." || s == "..") {
        return Err(fail(detail::PATH_DOT_SEGMENT, "has a '.' or '..' segment"));
    }
    // PATH-6
    if let Some(c) = text.chars().find(|c| is_control(*c)) {
        return Err(fail(
            detail::PATH_CONTROL_CHAR,
            &format!(
                "holds the control or directional character U+{:04X}",
                u32::from(c)
            ),
        ));
    }
    // PATH-7
    if let Some(c) = text.chars().find(|c| is_forbidden(*c)) {
        return Err(fail(
            detail::PATH_FORBIDDEN_CHAR,
            &format!("holds the character '{c}'"),
        ));
    }
    // PATH-8. PATH-5 has already rejected the segments `.` and `..`.
    if text
        .split('/')
        .any(|s| s.ends_with('.') || s.ends_with(' '))
    {
        return Err(fail(
            detail::PATH_TRAILING_DOT_SPACE,
            "a segment ends in '.' or ' '",
        ));
    }
    // PATH-9
    if let Some(s) = text.split('/').find(|s| is_reserved_name(s)) {
        return Err(fail(
            detail::PATH_RESERVED_NAME,
            &format!(
                "the segment \"{}\" is a Windows device name",
                s.escape_default()
            ),
        ));
    }
    // PATH-10
    let depth = text.split('/').count();
    if depth > MAX_DEPTH {
        return Err(fail(
            detail::PATH_DEPTH,
            &format!("{depth} segments; the most is {MAX_DEPTH}"),
        ));
    }
    Ok(text)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rejects(path: &[u8], d: &str) {
        let e = check_path(0, path).unwrap_err();
        assert_eq!((e.category(), e.detail()), (Category::Malformed, d), "{e}");
    }

    fn accepts(path: &str) {
        assert_eq!(check_path(0, path.as_bytes()).unwrap(), path);
    }

    #[test]
    fn ordinary_paths_pass() {
        for p in [
            "a",
            "docs/a.txt",
            ".hidden",
            "a..b",
            "x.y.z",
            "\u{5d0}\u{5d1}",
            "\u{e9}x",
            "CONSOLE",
            "con2",
            "com10",
            "lpt",
            "comx",
            "com\u{2074}",
            "nul_",
            " con",
            "a b",
            "\u{a0}",
            "\u{2065}",
            "\u{206a}",
            "\u{202f}",
            "\u{200d}",
        ] {
            accepts(p);
        }
    }

    #[test]
    fn path_1_and_2() {
        rejects(b"notes\xff.txt", detail::PATH_UTF8);
        rejects(b"\xc0\xaf", detail::PATH_UTF8);
        rejects(b"\xed\xa0\x80", detail::PATH_UTF8);
        rejects(b"\xf4\x90\x80\x80", detail::PATH_UTF8);
        rejects("e\u{301}".as_bytes(), detail::PATH_NFC);
        rejects("x\u{301}\u{113ce}".as_bytes(), detail::PATH_NFC);
        // An invalid byte is PATH-1 even in a path that also breaks every later rule.
        rejects(b"/../con\xff", detail::PATH_UTF8);
        rejects("/e\u{301}".as_bytes(), detail::PATH_NFC);
    }

    #[test]
    fn path_4_comes_before_path_3() {
        for p in ["/a", "a/", "a//b", "/", "//"] {
            rejects(p.as_bytes(), detail::PATH_SLASH);
        }
        let long = format!("/{}", "a".repeat(MAX_PATH_LEN + 1));
        rejects(long.as_bytes(), detail::PATH_SLASH);
        rejects(b"", detail::PATH_LENGTH);
    }

    #[test]
    fn path_3_limits_the_path_and_each_segment() {
        let seg = "a".repeat(MAX_SEGMENT_LEN);
        accepts(&seg);
        rejects(format!("{seg}a").as_bytes(), detail::PATH_LENGTH);
        rejects(format!("x/{seg}a/y").as_bytes(), detail::PATH_LENGTH);
        // 16 segments of 255 bytes and their 15 slashes are 4095 bytes. With the last
        // segment one byte shorter, '/z' makes 4096 and '/zz' 4097.
        let p = vec![seg.as_str(); 16].join("/");
        assert_eq!(p.len(), 4095);
        let q = &p[..4094];
        accepts(&format!("{q}/z"));
        rejects(format!("{q}/zz").as_bytes(), detail::PATH_LENGTH);
        rejects(format!("{p}/z").as_bytes(), detail::PATH_LENGTH);
        // A long path over PATH-3 is reported before the later rules.
        rejects(format!("{p}/../:").as_bytes(), detail::PATH_LENGTH);
    }

    #[test]
    fn path_5_to_8() {
        for p in [".", "..", "a/.", "a/../b", "./a"] {
            rejects(p.as_bytes(), detail::PATH_DOT_SEGMENT);
        }
        rejects(b"../\x01", detail::PATH_DOT_SEGMENT);
        for c in [
            '\u{0}', '\u{1}', '\u{1f}', '\u{7f}', '\u{80}', '\u{85}', '\u{9f}', '\u{61c}',
            '\u{200e}', '\u{200f}', '\u{202a}', '\u{202e}', '\u{2066}', '\u{2069}',
        ] {
            rejects(format!("a{c}b").as_bytes(), detail::PATH_CONTROL_CHAR);
        }
        rejects("a\u{1}:".as_bytes(), detail::PATH_CONTROL_CHAR);
        for c in ['\\', '<', '>', ':', '"', '|', '?', '*'] {
            rejects(format!("a{c}b").as_bytes(), detail::PATH_FORBIDDEN_CHAR);
        }
        rejects(b"con:.", detail::PATH_FORBIDDEN_CHAR);
        for p in ["x.", "x ", "a/x./b", "a/b ", "con."] {
            rejects(p.as_bytes(), detail::PATH_TRAILING_DOT_SPACE);
        }
    }

    #[test]
    fn path_9_reserved_device_names() {
        for p in [
            "CON",
            "con",
            "Prn",
            "aux",
            "NUL",
            "CONIN$",
            "conout$",
            "COM0",
            "com9",
            "LPT0",
            "lpt9",
            "COM¹",
            "com²",
            "Com³",
            "LPT¹",
            "lpt²",
            "LPT³",
            "con.txt",
            "con .txt",
            "CON  .tar.gz",
            "a/nul/b",
            "AUX.",
        ] {
            if p.ends_with('.') {
                // PATH-8 comes first.
                rejects(p.as_bytes(), detail::PATH_TRAILING_DOT_SPACE);
            } else {
                rejects(p.as_bytes(), detail::PATH_RESERVED_NAME);
            }
        }
        rejects(b"a/b/CON", detail::PATH_RESERVED_NAME);
    }

    #[test]
    fn path_10_limits_the_depth() {
        let deep = vec!["a"; MAX_DEPTH].join("/");
        accepts(&deep);
        rejects(format!("{deep}/a").as_bytes(), detail::PATH_DEPTH);
        // PATH-9 comes before PATH-10.
        rejects(format!("{deep}/con").as_bytes(), detail::PATH_RESERVED_NAME);
    }

    #[test]
    fn hostile_names_are_escaped_in_messages() {
        let e = check_path(7, "a\u{202e}b".as_bytes()).unwrap_err();
        assert!(!e.message().contains('\u{202e}'), "{}", e.message());
        assert!(e.message().contains("entry 7"));
        let e = check_path(0, b"a\xff\x1b").unwrap_err();
        assert!(!e.message().contains('\u{1b}'), "{}", e.message());
    }
}
