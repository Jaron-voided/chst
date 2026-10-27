fsw=crates/chst-fs/src/lib.rs; ca=crates/chst-format/tests/support/counting_alloc.rs
ca_users='crates/chst-format/tests/hostile_sizes.rs crates/chst-format/tests/zstd_bombs.rs'
# 1. forbid in every crate root except chst-fs and the two counting-allocator test crates
for f in $(ls crates/*/src/lib.rs crates/*/src/main.rs crates/*/tests/*.rs 2>/dev/null); do
  case " $fsw $ca_users " in *" $f "*) continue;; esac
  grep -qx '#!\[forbid(unsafe_code)\]' "$f" || { echo "missing forbid: $f"; exit 1; }
done
# 2. chst-fs: deny + SAFETY lints; exactly one allow, on the Windows module
grep -qx '#!\[deny(unsafe_code)\]' $fsw
grep -qx '#!\[deny(clippy::undocumented_unsafe_blocks, clippy::missing_safety_doc)\]' $fsw
grep -B1 -A1 'allow(unsafe_code)' $fsw | grep -q 'cfg(windows)'
grep -A1 'allow(unsafe_code)' $fsw | grep -qE '^\s*mod windows;'
# 3. the counting-allocator exception: deny in each of its two users that exists, allow only
#    in the named file. zstd_bombs.rs is Extended-only, so under the Core cut it may be absent;
#    under the Extended cut it must exist (AC-X-ZSTD-2 also requires it).
if grep -qx 'CURRENT_CUT = Extended' ACCEPTANCE.md; then test -f crates/chst-format/tests/zstd_bombs.rs; fi
for f in $ca_users; do
  test -e "$f" || continue
  grep -qx '#!\[deny(unsafe_code)\]' "$f"; grep -q 'counting_alloc' "$f"
done
grep -qx '#!\[allow(unsafe_code)\]' $ca
test "$(grep -rln 'allow(unsafe_code)' crates fuzz --include='*.rs' | sort | tr '\n' ' ')" = "$ca $fsw "
# 4. every unsafe item in the allocator file is preceded by a SAFETY comment
awk '/unsafe/ && !/allow\(unsafe_code\)/ { if (prev !~ /SAFETY:/) { print FILENAME": "FNR": undocumented unsafe"; bad=1 } } { if ($0 !~ /^\s*$/) prev=$0 } END { exit bad }' $ca
# 5. the word unsafe appears nowhere else
grep -rnw 'unsafe' crates fuzz --include='*.rs' > "$W/unsafe-lines" || true
if grep -vE "^($fsw:.*(deny|allow)\(unsafe_code\)|crates/chst-fs/src/windows(\.rs|/)|$ca:|crates/chst-format/tests/(hostile_sizes|zstd_bombs)\.rs:.*deny\(unsafe_code\))" "$W/unsafe-lines"; then exit 1; fi
# 6. fuzz targets: forbid, or the documented exemption (D18 exception 2)
for f in $(ls fuzz/fuzz_targets/*.rs); do
  grep -qx '#!\[forbid(unsafe_code)\]' "$f" || grep -q 'unsafe_code' fuzz/FORBID_EXEMPTION.txt || { echo "fuzz target without forbid or exemption: $f"; exit 1; }
done
