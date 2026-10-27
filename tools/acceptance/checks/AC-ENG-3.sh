cargo tree -p chst-cli -e normal --depth 1 --prefix none > "$W/cli-deps"
if grep -E '^(sha2|unicode-normalization|zstd) ' "$W/cli-deps"; then exit 1; fi
