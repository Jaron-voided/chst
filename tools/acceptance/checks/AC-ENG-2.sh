grep -q '#!\[forbid(unsafe_code)\]' crates/chst-format/src/lib.rs
if grep -rnE 'std::fs|std::env|std::process|std::net|unsafe' crates/chst-format/src \
  | grep -vxE 'crates/chst-format/src/lib\.rs:[0-9]+:#!\[forbid\(unsafe_code\)\]'; then exit 1; fi
cargo tree -p chst-format -e normal --depth 1 --prefix none --no-default-features \
  | tail -n +2 | awk '{print $1}' | sort -u > "$W/deps"
diff "$W/deps" <(printf 'sha2\nunicode-normalization\n')
