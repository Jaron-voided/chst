allow='chst-format|chst-fs|chst-cli|chst-fuzz|sha2|unicode-normalization|rustix|windows-sys|lexopt|serde_json|zstd|tempfile|libfuzzer-sys'
git ls-files --error-unmatch Cargo.lock fuzz/Cargo.lock > /dev/null       # lockfiles are committed
for m in Cargo.toml fuzz/Cargo.toml; do
  cargo tree --manifest-path $m --workspace --target all --all-features -e normal,build,dev \
    --depth 1 --prefix none | awk 'NF {print $1}' | sort -u > "$W/direct"
  if grep -vxE "$allow" "$W/direct"; then exit 1; fi
done
