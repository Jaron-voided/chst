grep -qxE 'channel = "1\.99\.1"' rust-toolchain.toml
test "$(rustc --version | cut -d' ' -f2)" = 1.99.1
grep -qxE 'channel = "nightly-2026-10-01"' fuzz/rust-toolchain.toml
command -v python3.14 > /dev/null
python3.14 -I -c 'import sys, unicodedata, compression.zstd       # N19: the generator needs compression.zstd
assert sys.version_info[:2] == (3, 14), sys.version
assert unicodedata.unidata_version == "16.0.0", unicodedata.unidata_version'
jq --version | grep -qE '^jq-1\.([7-9]|[1-9][0-9])'
